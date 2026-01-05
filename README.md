# Autonomous Network Anomaly Diagnosis Agent

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Prototype-orange)

An autonomous multi-agent system capable of diagnosing network anomalies (latency spikes, packet drops) and proposing configuration fixes by interacting with a simulated network environment. 

This project demonstrates the application of **Agentic AI** in the domain of **Network Engineering**, showcasing:
- **Synthetic Data Generation**: Creating realistic Syslog and NetFlow datasets.
- **Agentic Reasoning**: Using LangGraph to orchestrate tool usage.
- **Domain Specific Tools**: Simulating CLI commands (`show interface`) and P4/Tofino register queries.
- **Automated Evaluation**: Implementing an "LLM-as-a-Judge" pipeline with RAGAS metrics.

## 🏗 Architecture

The system consists of four main components:

1.  **Data Generator**: Creates "Incidents" (pairs of network logs and ground truth root causes).
2.  **Agent Core**: A LangGraph agent that can fetch logs, check interface status, and propose fixes.
3.  **Evaluator**: A pipeline that grades the agent's proposed fixes against the ground truth using a Judge model (local or mock).
4.  **Deployment**: Docker configurations for serving the fine-tuned model with vLLM.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Docker (optional, for deployment)
- [Ollama](https://ollama.com) (optional, for local LLM evaluation)

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/network-agent.git
    cd network-agent
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## 🛠 Usage

### 1. Generate Synthetic Data
Create a dataset of network incidents (logs + ground truth).
```bash
python3 data/generator/generate_incidents.py --count 5
```
This will create incident folders in `data/custom_dataset/`.

### 2. Run the Agent (Demo Mode)
Run the agent against the simulated environment.
```bash
export PYTHONPATH=$PYTHONPATH:.
python3 -m agent.graph
```

### 3. Evaluate Performance
Run the LLM-as-a-Judge pipeline.

**Using Mock Judge (Fast, Rule-based):**
```bash
python3 evaluation/judge.py --backend mock
```

**Using Local LLM (Recommended):**
1.  Ensure Ollama is running (`ollama serve`).
2.  Pull a model: `ollama pull llama3`.
3.  Run the judge:
    ```bash
    python3 evaluation/judge.py --backend ollama --model llama3
    ```

### 4. Run Mininet Simulation (Linux Only)
If you have Mininet installed, you can run the live network simulation.
```bash
sudo python3 data/generator/mininet_topology.py
```
This will:
1. Start a 3-router topology.
2. Start a background script simulating "P4 Drop Counters" related to R1.
3. Open a Mininet CLI.

## 📂 Project Structure

```
├── agent/                  # Agent logic (LangGraph)
│   ├── graph.py            # Main application graph
│   ├── tools.py            # Network simulation tools
│   └── state.py            # Agent state definition
├── data/                   # Data generation scripts
│   ├── generator/          # Scripts to generate logs
│   └── custom_dataset/     # Output directory for datasets
├── deployment/             # Deployment artifacts
│   ├── Dockerfile          # vLLM container definition
│   └── serve.sh            # Serving script
├── evaluation/             # Evaluation pipeline
│   └── judge.py            # LLM-as-a-Judge script
├── fine_tuning/            # Model training
│   └── train.py            # QLoRA fine-tuning script
└── requirements.txt        # Project dependencies
```

## 🧠 "The Twist"
This project includes a specialized tool `read_p4_register` in `agent/tools.py`. This simulates querying a **Tofino P4 switch's hardware registers** (e.g., for micro-burst detection), bridging the gap between high-level intent-based networking and low-level data plane telemetry.

## 📝 License
MIT
