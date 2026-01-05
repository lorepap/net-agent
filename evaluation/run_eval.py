"""
Evaluation Orchestrator.

Runs the agent against the dataset and uses the Judge to evaluate performance.
"""
import json
import argparse
import sys
import os
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.judge import NetworkJudge, EvaluationResult

# Try to import Real Agent, fallback to Mock
try:
    from agent.graph import run_agent
    AGENT_AVAILABLE = True
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Warning: Could not import agent: {e}")
    AGENT_AVAILABLE = False


class MockAgent:
    """Simulates the agent for testing the pipeline when Ollama is offline."""
    
    def run(self, query: str) -> str:
        if "interface" in query.lower():
            return """
📋 ROOT CAUSE: Interface GigabitEthernet0/0/1 is administratively down
🔧 RECOMMENDED FIX: Enable the interface
Config:
interface GigabitEthernet0/0/1
no shutdown
"""
        elif "latency" in query.lower():
            return """
📋 ROOT CAUSE: Congestion on primary link due to backup
🔧 RECOMMENDED FIX: Reroute traffic via secondary path
Config:
router ospf 1
interface TenGigabitEthernet1/0/1
ip ospf cost 1000
"""
        else:
            return "Unable to diagnose the issue."


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Run Agent Evaluation")
    parser.add_argument("--dataset", default="data/custom_dataset/dataset_index.json", help="Path to dataset index")
    parser.add_argument("--agent-mode", choices=["real", "mock"], default="mock", help="Use 'real' agent or 'mock' response")
    parser.add_argument("--judge-model", default="llama3.1", help="Ollama model for judge")
    parser.add_argument("--mock-judge", action="store_true", help="Use rule-based judge instead of LLM")
    parser.add_argument("--limit", type=int, default=3, help="Max incidents to evaluate")
    args = parser.parse_args()
    
    # 1. Load Data
    if not os.path.exists(args.dataset):
        print(f"❌ Dataset not found: {args.dataset}")
        print("Run: python data/generator/generate_incidents.py")
        sys.exit(1)
        
    dataset = load_dataset(args.dataset)
    print(f"📚 Loaded {len(dataset)} incidents from {args.dataset}")
    
    # 2. Init Agent
    if args.agent_mode == "real":
        if not AGENT_AVAILABLE:
            print("❌ Real agent not available (check imports/dependencies)")
            sys.exit(1)
        print("🤖 Using REAL Agent")
    else:
        agent = MockAgent()
        print("🎭 Using MOCK Agent")
        
    # 3. Init Judge
    print(f"👨‍⚖️ Initializing Judge (Model: {args.judge_model})")
    judge = NetworkJudge(model_name=args.judge_model)
    if args.mock_judge:
        print("🎭 Using MOCK Judge (Rule-based)")
    
    # 4. Run Loop
    results = []
    
    print("\n" + "="*60)
    print("STARTING EVALUATION")
    print("="*60)
    
    for i, incident in enumerate(dataset[:args.limit]):
        print(f"\n🔹 Incident {i+1}: {incident['scenario']} (ID: {incident['incident_id']})")
        print(f"   Query: {incident['ground_truth']['description']}")
        
        # Run Agent
        try:
            if args.agent_mode == "real":
                print("   Running Agent...", end="", flush=True)
                # Suppress stdout for cleaner logs
                # saved_stdout = sys.stdout
                # sys.stdout = open(os.devnull, 'w')
                response = run_agent(incident['ground_truth']['description'])
                # sys.stdout = saved_stdout
                print(" Done.")
            else:
                response = agent.run(incident['ground_truth']['description'])
                print("   Agent (Mock) responded.")
        except Exception as e:
            print(f"   ❌ Agent failed: {e}")
            response = str(e)
            
        # Grade
        print("   Grading...", end="", flush=True)
        if args.mock_judge:
            eval_result = judge.evaluate_mock(incident, response)
        else:
            eval_result = judge.evaluate(incident, response)
        print(" Done.")
        
        print(f"   📊 Score: {eval_result.score}/10")
        print(f"   📝 Reasoning: {eval_result.reasoning}")
        
        results.append({
            "incident": incident['incident_id'],
            "score": eval_result.score,
            "result": eval_result.model_dump()
        })
        
    # 5. Summary
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    avg_score = sum(r['score'] for r in results) / len(results) if results else 0
    print(f"Total Incidents: {len(results)}")
    print(f"Average Score: {avg_score:.1f}/10")
    
    # Save results
    with open("evaluation_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results saved to evaluation_report.json")


if __name__ == "__main__":
    main()
