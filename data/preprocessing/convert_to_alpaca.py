
import json
import argparse
from pathlib import Path

def format_prompt(incident_data):
    """Format the input text for the LLM."""
    query = "diagnose why h1 can't ping h2" if incident_data["scenario"] == "missing_rules" else "check network status"
    
    # Construct context from logs
    context = "SYSTEM LOGS:\n"
    try:
        with open(incident_data["logs"]["syslog"], "r") as f:
            # Take last 10 lines to fit in context
            lines = f.readlines()[-10:]
            context += "".join(lines)
    except Exception as e:
        context += f"[Error reading logs: {e}]\n"
        
    prompt = f"""You are an autonomous network repair agent.

CORE INSTRUCTION:
You must DIAGNOSE and FIX network issues automatically.

CONTEXT:
{context}

USER QUERY:
{query}
"""
    return prompt

def format_completion(incident_data):
    """Format the expected output (Chain of Thought + Action)."""
    gt = incident_data["ground_truth"]
    
    if incident_data["scenario"] == "missing_rules":
        # Simulate the ReAct thought process
        completion = f"""
🔧 Calling tool 'read_p4_register'
   Args: {{'register_name': 'packet_counter'}}
   
📊 Tool result: RuntimeCmd: packet_counter[0]= 0

📋 FINAL DIAGNOSIS:
Based on the output, it appears that there are no forwarding rules installed in the switch (packet_counter is 0).

To resolve this issue, I will install basic forwarding rules using the `apply_config_change` tool.
"""
    else:
        completion = """
🔧 Calling tool 'read_p4_register'
   Args: {{'register_name': 'packet_counter'}}
   
📊 Tool result: RuntimeCmd: packet_counter[0]= 1500

📋 FINAL DIAGNOSIS:
Network appears to be operating normally. Traffic is flowing (packet counter > 0).
"""
    return completion

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="data/custom_dataset")
    parser.add_argument("--output-file", default="data/training_data.json")
    args = parser.parse_args()
    
    dataset = []
    input_dir = Path(args.input_dir)
    
    # Find all report.json files
    reports = list(input_dir.glob("**/report.json"))
    
    for report_path in reports:
        with open(report_path, "r") as f:
            data = json.load(f)
            
        # Update relative paths to absolute or correct relative from script execution
        # Assuming script run from project root
        data["logs"]["syslog"] = str(report_path.parent / "syslog.log")
            
        entry = {
            "instruction": format_prompt(data),
            "input": "", # Context is embedded in instruction
            "output": format_completion(data)
        }
        dataset.append(entry)
        
    with open(args.output_file, "w") as f:
        json.dump(dataset, f, indent=2)
        
    print(f"Converted {len(dataset)} incidents to {args.output_file}")

if __name__ == "__main__":
    main()
