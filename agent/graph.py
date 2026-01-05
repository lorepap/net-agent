import json
from typing import Dict, Any, List
# In a real environment, we would import these:
# from langgraph.graph import StateGraph, END
# from langchain_core.messages import HumanMessage, AIMessage

# Mocking LangGraph for the purpose of this demonstration since we cannot install packages
class StateGraph:
    def __init__(self, state_schema):
        self.nodes = {}
        self.edges = {}
        self.entry_point = None
        
    def add_node(self, name, func):
        self.nodes[name] = func
        
    def add_edge(self, start, end):
        if start not in self.edges:
            self.edges[start] = []
        self.edges[start].append(end)
        
    def set_entry_point(self, name):
        self.entry_point = name
        
    def add_conditional_edges(self, start, condition_func, map_outputs):
        # Simplified mock
        self.edges[start] = (condition_func, map_outputs)

    def compile(self):
        return CompiledGraph(self)

class CompiledGraph:
    def __init__(self, graph):
        self.graph = graph
        
    def invoke(self, inputs):
        current_node = self.graph.entry_point
        state = inputs
        print(f"--- Starting Agent Execution with input: {inputs.get('input')} ---")
        
        while current_node != "end":
            print(f"-> Executing Node: {current_node}")
            node_func = self.graph.nodes[current_node]
            result = node_func(state)
            
            # Update state (simple merge for mock)
            state.update(result)
            
            # Determine next node
            if current_node in self.graph.edges:
                edge_info = self.graph.edges[current_node]
                if isinstance(edge_info, list):
                    current_node = edge_info[0] # Simple linear for now if list
                elif isinstance(edge_info, tuple):
                    # Conditional
                    condition, mapping = edge_info
                    outcome = condition(state)
                    current_node = mapping[outcome]
            else:
                current_node = "end"
                
        return state

END = "end"

# Import our tools and state
from agent.state import AgentState
from agent.tools import tool_registry

# --- Agent Nodes ---

def router_node(state: AgentState):
    """
    Decides which tool to call based on input.
    In prod, this is the LLM.
    """
    input_text = state["input"].lower()
    last_step = state.get("intermediate_steps", [])
    
    # Simple heuristic "brain" for the demo
    if not last_step:
        if "latency" in input_text or "spike" in input_text:
            return {"next_action": "fetch_logs", "args": {"device_id": "cs-core-01"}}
        elif "drop" in input_text or "loss" in input_text:
             return {"next_action": "read_p4_register", "args": {"device_id": "cs-core-01", "register_name": "drop_counter"}}
        elif "interface" in input_text or "down" in input_text:
             return {"next_action": "check_interface_status", "args": {"device_id": "cs-access-01", "interface": "GigabitEthernet0/0/1"}}
        else:
            return {"next_action": "final_response", "args": {"response": "I cannot diagnose this issue."}}
    
    # If we have steps, assume we have info and want to propose a fix
    prev_action = last_step[-1][0]
    prev_output = last_step[-1][1]
    
    if prev_action == "fetch_logs":
        return {"next_action": "propose_config_change", "args": {"device_id": "cs-core-01", "config_commands": ["int gi0/0", "ip ospf cost 100"]}}
    elif prev_action == "read_p4_register":
         return {"next_action": "propose_config_change", "args": {"device_id": "cs-core-01", "config_commands": ["policy-map QoS", "class match-all VOICE", "priority percent 20"]}}
    elif prev_action == "check_interface_status":
         if "down" in str(prev_output):
             return {"next_action": "propose_config_change", "args": {"device_id": "cs-access-01", "config_commands": ["interface GigabitEthernet0/0/1", "no shutdown"]}}
         else:
             return {"next_action": "final_response", "args": {"response": "Interface appears UP. No changes needed."}}
             
    return {"next_action": "final_response", "args": {"response": "Diagnosis complete."}}

def tool_execution_node(state: AgentState):
    """Executes the selected tool."""
    action = state["next_action"]
    args = state["args"]
    
    print(f"   [Tool Call] {action} with args {args}")
    
    tool_func = tool_registry.get(action)
    if tool_func:
        output = tool_func(**args)
    else:
        output = "Error: Tool not found"
        
    print(f"   [Tool Output] {str(output)[:100]}...")
    
    steps = state.get("intermediate_steps", [])
    steps.append((action, output))
    
    return {"intermediate_steps": steps}

def final_answer_node(state: AgentState):
    return {"final_output": state["args"].get("response", "Done")}

# --- Conditional Logic ---

def should_continue(state: AgentState):
    if state["next_action"] == "final_response":
        return "end"
    return "continue"

# --- Graph Definition ---

def create_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("router", router_node)
    workflow.add_node("executor", tool_execution_node)
    workflow.add_node("responder", final_answer_node)
    
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges(
        "router",
        should_continue,
        {
            "continue": "executor",
            "end": "responder"
        }
    )
    
    workflow.add_edge("executor", "router")
    workflow.add_edge("responder", END)
    
    return workflow.compile()

if __name__ == "__main__":
    app = create_agent()
    
    # Test Scenario 1: Interface Down
    out = app.invoke({"input": "The interface on cs-access-01 is down", "intermediate_steps": []})
    print(f"\nFinal Result: {out['final_output']}\n")
    
    # Test Scenario 2: Latency Spike
    out = app.invoke({"input": "We are seeing a latency spike on core", "intermediate_steps": []})
    print(f"\nFinal Result: {out['final_output']}\n")
