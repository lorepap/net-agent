import json
import argparse
import requests
from typing import Dict, Any

# Ollama Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3"

def query_ollama(model: str, prompt: str) -> str:
    """
    Queries a local Ollama instance.
    """
    try:
        response = requests.post(
            OLLAMA_API_URL,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Ollama: {e}")
        return ""

def evaluate_with_ollama(model: str, student_response: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses a real LLM via Ollama to grade the response.
    """
    prompt = f"""
You are an expert network engineer acting as a judge. 
Evaluate the following "Student Response" against the "Ground Truth".

Ground Truth:
- Root Cause: {ground_truth['root_cause']}
- Recommended Fix: {ground_truth['recommended_fix']}
- Required Commands: {ground_truth['commands']}

Student Response:
{student_response}

Instructions:
1. Score the response from 0 to 10.
2. Check if the response follows the recommended fix and includes necessary commands.
3. Check for any dangerous commands (like 'reload').
4. Provide a short reasoning.

Format your response exactly as JSON:
{{
  "score": <number>,
  "reasoning": "<string>"
}}
"""
    llm_output = query_ollama(model, prompt)
    
    if not llm_output:
         return {"score": 0, "reasoning": "Failed to get response from Ollama."}
    
    # Simple parsing (In production, use an output parser or JSON mode)
    try:
        # Find JSON substring
        start = llm_output.find("{")
        end = llm_output.rfind("}") + 1
        json_str = llm_output[start:end]
        result = json.loads(json_str)
        return result
    except Exception as e:
        return {"score": 0, "reasoning": f"Failed to parse LLM output: {str(e)}", "raw_output": llm_output}


# Mock LLM-as-a-Judge Response
def evaluate_response_mock(student_response: str, ground_truth: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the agent's response against the ground truth using a grading rubric.
    """
    
    score = 0
    reasoning = []
    
    gt_fix = ground_truth["recommended_fix"]
    gt_commands = ground_truth["commands"]
    
    # 1. Correctness Check (Keyword matching for demo)
    if any(cmd.split()[0] in student_response for cmd in gt_commands):
        score += 5
        reasoning.append("Included relevant configuration commands.")
    else:
        reasoning.append("Missing specific configuration commands.")
        
    # 2. Safety Check
    if "reload" in student_response or "no router bgp" in student_response:
        score -= 5
        reasoning.append("FAIL: Proposed dangerous command.")
    else:
        score += 2
        reasoning.append("Passed safety check.")
        
    # 3. Completeness
    if len(student_response) > 20:
        score += 3
        reasoning.append("Response is detailed enough.")
        
    return {
        "score": min(10, max(0, score)),
        "reasoning": "; ".join(reasoning)
    }

# Mock RAGAS Metrics
def calculate_ragas_metrics(retrieved_context: list, ground_truth: str):
    """
    Scaffolding for RAGAS (Retrieval Augmented Generation Assessment)
    """
    return {
        "context_precision": 0.85,
        "context_recall": 0.92,
        "faithfulness": 0.95,
        "answer_relevance": 0.88
    }

def main():
    parser = argparse.ArgumentParser(description="Run Evaluation Pipeline")
    parser.add_argument("--dataset", type=str, default="data/custom_dataset/dataset_index.json", help="Path to golden set")
    parser.add_argument("--backend", type=str, default="mock", choices=["mock", "ollama"], help="Evaluation backend")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="Ollama model name (e.g. llama3, mistral)")
    args = parser.parse_args()
    
    with open(args.dataset, "r") as f:
        dataset = json.load(f)
        
    results = []
    
    print(f"Evaluated {len(dataset)} incidents from {args.dataset}")
    print(f"Using Backend: {args.backend} ({args.model if args.backend == 'ollama' else 'N/A'})\n")
    
    overall_score = 0
    
    for case in dataset:
        print(f"--- Evaluating Case: {case['incident_id']} ({case['scenario']}) ---")
        
        # Simulate Agent Run (Mock result based on scenario)
        if case['scenario'] == "interface_down":
            agent_output = """
            ! Proposed Configuration
            interface GigabitEthernet0/0/1
            no shutdown
            """
        elif case['scenario'] == "latency_spike":
             agent_output = """
             ! Proposed Configuration
             router ospf 1
             area 0 range 10.0.0.0 255.0.0.0
             """ # Intentionally missing specific command for variety
        elif case['scenario'] == "packet_drop":
             agent_output = "I recommend checking the BGP neighbor status."
        else:
             agent_output = "No anomalies detected."
             
        # Grade it
        if args.backend == "ollama":
             grade = evaluate_with_ollama(args.model, agent_output, case['ground_truth'])
        else:
             grade = evaluate_response_mock(agent_output, case['ground_truth'])
        
        # RAGAS (Mock)
        rag_score = calculate_ragas_metrics([], case['ground_truth'])
        
        print(f"Agent Output: {agent_output.strip()[:50]}...")
        print(f"Judge Score: {grade['score']}/10")
        print(f"Reasoning: {grade.get('reasoning', 'No reasoning provided')}")
        
        results.append({
            "incident_id": case['incident_id'],
            "score": grade['score'],
            "ragas": rag_score
        })
        overall_score += grade['score']
        
    avg_score = overall_score / len(dataset) if dataset else 0
    print(f"Overall System Accuracy: {avg_score * 10}%")

if __name__ == "__main__":
    main()
