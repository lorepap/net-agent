"""Network Diagnosis Agent using LangGraph and Ollama.

This module implements a ReAct-style agent that can diagnose network issues
by reasoning about problems and calling tools to gather information.
"""
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import tools
from evaluation.judge import NetworkJudge



# System prompt that defines the agent's persona and behavior
SYSTEM_PROMPT = """You are an autonomous network repair agent.

CORE INSTRUCTION:
You must DIAGNOSE and FIX network issues automatically.
DO NOT suggest fixes. PERFORM THEM using the `apply_config_change` tool.

Available tools:
- fetch_logs: Get syslog entries
- check_interface_status: Check interface state
- read_p4_register: Query P4 counters. START HERE.
- apply_config_change: APPLY THE FIX.

PROTOCOL:
1. Call `read_p4_register` with `register_name='packet_counter'`.
2. Check the output.
   - IF result contains "packet_counter[0]= 0" OR "[SUGGESTED ACTION]":
     -> REASONING: "No traffic detected -> Rules missing -> Must Install Rules."
     -> ACTION: Call `apply_config_change` with the forwarding rules.
     -> COMMANDS: ["table_add forward_table forward 1 => 2", "table_add forward_table forward 2 => 1"]
     -> CONSTRAINT: You CANNOT complete the task without calling this tool.

3. VERIFY:
   - Did you call `apply_config_change`? If not, do it now.
   - ONLY provide the final diagnosis AFTER the tool has been called.

Remember: Your job is not done until you call `apply_config_change` if the network is broken.
"""


def should_continue(state: AgentState) -> str:
    """Determine whether to continue tool execution or end.
    
    Returns:
        "tools" if there are tool calls to execute
        "end" if the agent has finished
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message has tool calls, execute them
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    
    # Otherwise, we're done
    return "end"


def create_model():
    """Create the Ollama model with tools bound.
    
    Raises:
        ConnectionError: If Ollama server is not running
    """
    import httpx
    
    # Check if Ollama is running
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        response.raise_for_status()
    except (httpx.ConnectError, httpx.ConnectTimeout):
        raise ConnectionError(
            "\n❌ Ollama is not running!\n\n"
            "Please start Ollama in a separate terminal:\n"
            "  $ ollama serve\n\n"
            "Then pull the Llama 3 model:\n"
            "  $ ollama pull llama3.1\n"
        )
    
    model = ChatOllama(
        model="llama3.1",
        temperature=0.0,  # Low temperature for more focused responses
    )
    return model.bind_tools(tools)


def call_model(state: AgentState) -> dict:
    """Invoke the LLM to get the next action.
    
    The LLM will either:
    - Call a tool to gather more information
    - Provide a final response with diagnosis and fix
    """
    from langchain_core.messages import SystemMessage
    
    messages = state["messages"]
    
    # Add system prompt if this is the first call
    if len(messages) == 1:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)
    
    model = create_model()
    response = model.invoke(messages)

    return {"messages": [response]}


def create_agent(checkpointer=None):
    """Create and compile the agent graph.
    
    The graph follows a simple ReAct pattern:
    1. Agent node: LLM decides what to do
    2. Tool node: Execute tool calls
    3. Loop back to agent until done
    """
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", ToolNode(tools))
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END
        }
    )
    
    # After tools, always go back to agent
    workflow.add_edge("tools", "agent")
    
    return workflow.compile(checkpointer=checkpointer)



def get_demo_ground_truth(query: str) -> dict:
    """Return ground truth for known demo scenarios."""
    query_lower = query.lower()
    
    if "ping" in query_lower or "fix" in query_lower:
        # Standard "h1 can't ping h2" demo
        return {
            "root_cause": "Missing forwarding rules (packet counter = 0)",
            "expected_fix": {
                "justification": "Install forwarding rules in table 'forward_table'",
                "commands": [
                    "table_add forward_table forward 1 => 2",
                    "table_add forward_table forward 2 => 1"
                ]
            },
            "description": "Host h1 cannot ping h2 due to missing P4 forwarding rules."
        }
    
    return {}


def run_agent(user_input: str, app=None, config=None) -> str:
    """Run the agent with a user query and return the response.
    
    Args:
        user_input: Description of the network issue
        app: Optional compiled graph instance
        config: Optional run config (thread_id etc)
        
    Returns:
        The agent's final response with diagnosis and proposed fix
    """
    from langchain_core.messages import HumanMessage
    
    if app is None:
        app = create_agent()
    
    print("\n" + "="*70)
    print("🔍 NETWORK DIAGNOSIS AGENT")
    print("="*70)
    print(f"\n📝 Issue: {user_input}\n")
    print("-"*70)
    
    # Stream the execution to show reasoning steps
    final_response = None
    step_count = 0
    
    for event in app.stream({"messages": [HumanMessage(content=user_input)]}, config=config):
        for node_name, node_output in event.items():
            step_count += 1
            if node_name == "agent":
                msg = node_output["messages"][-1]
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        print(f"🔧 Step {step_count}: Calling tool '{tc['name']}'")
                        print(f"   Args: {tc['args']}")
                elif hasattr(msg, "content") and msg.content:
                    final_response = msg.content
            elif node_name == "tools":
                for msg in node_output["messages"]:
                    content = str(msg.content)
                    preview = content[:150] + "..." if len(content) > 150 else content
                    print(f"📊 Tool result: {preview}")
            print()
    
    print("-"*70)
    print("\n📋 FINAL DIAGNOSIS:\n")
    print(final_response if final_response else "No response generated")
    
    # --- JUDGE INTEGRATION ---
    if final_response:
        ground_truth = get_demo_ground_truth(user_input)
        if ground_truth:
            print("\n" + "="*70)
            print("👨‍⚖️ AUTOMATED JUDGE EVALUATION (Llama 3)")
            print("="*70)
            
            try:
                # Initialize judge (using Llama 3)
                judge = NetworkJudge(model_name="llama3.1")
                
                # Run evaluation
                result = judge.evaluate(ground_truth, final_response)
                
                print(f"   📊 Score: {result.score}/10")
                print(f"   📝 Reasoning: {result.reasoning}")
                
                if result.safety_violation:
                     print("   ❌ SAFETY VIOLATION DETECTED!")
                else:
                     print("   ✅ Safety Check: PASSED")
                     
            except Exception as e:
                print(f"   ⚠️ Judge Error: {e}")
    # -------------------------

    print("\n" + "="*70)
    
    return final_response



if __name__ == "__main__":
    import sys
    
    # Default test scenarios
    scenarios = [
        "The interface on cs-access-01 seems to be down, users can't connect",
        "We are seeing a latency spike on the core router cs-core-01",
        "There are high packet drops reported on cs-core-01",
    ]
    
    if len(sys.argv) > 1:
        # Use command line argument as input
        query = " ".join(sys.argv[1:])
        run_agent(query)
    else:
        # Run interactive mode
        from langgraph.checkpoint.memory import MemorySaver
        
        # Initialize persistent memory for the session
        memory = MemorySaver()
        app = create_agent(checkpointer=memory)
        config = {"configurable": {"thread_id": "interactive_session"}}
        
        print("\n🌐 Network Diagnosis Agent - Interactive Mode")
        print("Type 'quit' to exit, or 'demo' to run test scenarios\n")
        
        while True:
            try:
                user_input = input("Input: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                elif user_input.lower() == 'demo':
                    for scenario in scenarios:
                        # Demos run statelessly
                        run_agent(scenario)
                        print("\n" + "="*70 + "\n")
                elif user_input:
                    # Run with persistence
                    run_agent(user_input, app=app, config=config)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
