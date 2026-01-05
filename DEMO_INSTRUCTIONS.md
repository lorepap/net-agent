# 🚀 Network Agent Demo Instructions

Follow these steps to run the "Autonomous Network Anomaly Diagnosis Agent" demo.

## Phase 1: Setup (Do this once)

### 1. Start Ollama Server
Open **Terminal 1** and run:
```bash
ollama serve
```
*Keep this terminal open.*

### 2. Pull the Model
Open **Terminal 2** and run:
```bash
ollama pull llama3.1
```
*Wait for this to complete (4.9GB).*

---

## Phase 2: Live Demo (The Show using Real Mininet/BMv2)

### 1. Start the Network Simulation
In **Terminal 2**, run the interactive demo environment:
```bash
sudo python3 demo/start_demo_v2.py
```
*   This sets up the network `h1 <-> s1 <-> h2`.
*   Ping OK initially.
*   **Leave this terminal open.**

### 2. Break the Network (Simulate Incident)
In **Terminal 3**, run:
```bash
./demo/break_network.sh
```
*   This clears the forwarding rules.
*   Ping should now fail.

### 3. Run the Autonomous Agent
In **Terminal 3**, run the agent wrapper script:
```bash
./run_agent.sh
```
*   **Interactive Mode**: It will ask for input. Type: "Diagnose why h1 cannot ping h2".
*   **Watch**: The agent will call `read_p4_register` and `apply_config_change`.

---

## Phase 3: Evaluation (The Benchmark using Synthetic Data)

Run the LLM-as-a-Judge pipeline against the 8 generated scenarios:
```bash
source venv/bin/activate
python3 evaluation/run_eval.py --agent-mode real
```
*   **Target**: 100% Score.
*   **Metric**: RAGAS Faithfulness & Answer Relevancy.

---

## Phase 4: Advanced CV Features (Show & Tell)
Show the code for these advanced implementations:
1.  **Fine-Tuning**: `fine_tuning/train.py` (QLoRA implementation).
2.  **vLLM Serving**: `deployment/serve.sh` (Edge deployment script).
