"""Network Diagnosis Agent using LangGraph and Ollama.

This module implements a ReAct-style agent that can diagnose network issues
by reasoning about problems and calling tools to gather information.
"""
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import tools


# System prompt that defines the agent's persona and behavior
SYSTEM_PROMPT = """You are an expert network engineer assistant specializing in diagnosing network anomalies.

Your job is to:
1. Analyze the user's description of a network issue
2. Use the available tools to gather diagnostic information
3. Identify the root cause
4. Propose a configuration fix

Available tools:
- fetch_logs: Get syslog entries from a device
- check_interface_status: Check if an interface is up/down and view error counters
- read_p4_register: Query P4 switch registers for queue depth or drop counters
- propose_config_change: Generate a configuration change proposal

IMPORTANT GUIDELINES:
- Always start by gathering information before proposing fixes
- Use device IDs like "cs-core-01", "cs-core-02", "cs-access-01"
- Common interfaces: GigabitEthernet0/0/1, TenGigabitEthernet1/0/1
- When you identify the root cause, use propose_config_change to suggest a fix
- Be concise but thorough in your analysis

After gathering enough information, provide your diagnosis in this format:
📋 ROOT CAUSE: [one line description]
🔧 RECOMMENDED FIX: [brief explanation]
Then call propose_config_change with the appropriate commands."""


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
            "  $ ollama pull llama3\n"
        )
    
    model = ChatOllama(
        model="llama3",
        temperature=0.1,  # Low temperature for more focused responses
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


def create_agent():
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
    
    return workflow.compile()


def run_agent(user_input: str) -> str:
    """Run the agent with a user query and return the response.
    
    Args:
        user_input: Description of the network issue
        
    Returns:
        The agent's final response with diagnosis and proposed fix
    """
    from langchain_core.messages import HumanMessage
    
    app = create_agent()
    
    print("\n" + "="*70)
    print("🔍 NETWORK DIAGNOSIS AGENT")
    print("="*70)
    print(f"\n📝 Issue: {user_input}\n")
    print("-"*70)
    
    # Stream the execution to show reasoning steps
    final_response = None
    step_count = 0
    
    for event in app.stream({"messages": [HumanMessage(content=user_input)]}):
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
        print("\n🌐 Network Diagnosis Agent - Interactive Mode")
        print("Type 'quit' to exit, or 'demo' to run test scenarios\n")
        
        while True:
            try:
                user_input = input("Describe the network issue: ").strip()
                
                if user_input.lower() == 'quit':
                    print("Goodbye!")
                    break
                elif user_input.lower() == 'demo':
                    for scenario in scenarios:
                        run_agent(scenario)
                        print("\n" + "="*70 + "\n")
                elif user_input:
                    run_agent(user_input)
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
