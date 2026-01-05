# Autonomous Network Anomaly Diagnosis Agent

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![LangGraph](https://img.shields.io/badge/LangGraph-0.6-purple)
![BMv2](https://img.shields.io/badge/BMv2-P4_Switch-orange)
![License](https://img.shields.io/badge/License-MIT-green)

An autonomous AI agent that diagnoses network anomalies (latency spikes, packet drops, interface failures) and proposes configuration fixes using **real LLM reasoning** via Ollama and **real P4 switch telemetry** via BMv2.

## ✨ Features

- **🤖 Agentic Reasoning**: Uses LangGraph to orchestrate a ReAct-style agent that decides which tools to call
- **🔧 Real Network Tools**: Integrates with Mininet + BMv2 for real P4 switch operations
- **📡 P4 Telemetry**: Reads actual packet counters and queue depths from BMv2 registers
- **👨‍⚖️ Interactive Judge**: Real-time LLM evaluation of agent actions during live demos
- **🧠 Local LLM**: Runs entirely on your machine using Ollama (Llama 3) - no API keys needed
- **📊 Real Data**: Generates training data from real network events, not just synthetic mocks

## 🎬 Quick Demo

```bash
# After setup, run the agent interactively
source venv/bin/activate
python -m agent.graph

# Or diagnose a specific issue
python -m agent.graph "There's high latency on cs-core-01"
```

**Example Output:**
```
======================================================================
🔍 NETWORK DIAGNOSIS AGENT
======================================================================

📝 Issue: diagnose why h1 can't ping h2

----------------------------------------------------------------------
🔧 Step 1: Calling tool 'read_p4_register'
   Args: {'register_name': 'packet_counter'}

📊 Tool result: REAL P4 TELEMETRY (BMv2):
RuntimeCmd: packet_counter[0]= 0
[AUTOMATED ANALYSIS] Counter is 0. This confirms NO TRAFFIC matches the rules.

----------------------------------------------------------------------

� FINAL DIAGNOSIS:
To resolve this issue, you can install basic forwarding rules using the 
`apply_config_change` command.

======================================================================
Describe the network issue: fix it

======================================================================
🔍 NETWORK DIAGNOSIS AGENT
======================================================================

📝 Issue: fix it

----------------------------------------------------------------------
🔧 Step 1: Calling tool 'apply_config_change'
   Args: {'config_commands': ['table_add forward_table forward 1 => 2', 
          'table_add forward_table forward 2 => 1']}

📊 Tool result: Cmd: table_add forward_table forward 1 => 2
Result: SUCCESS: Rule installed successfully.
Cmd: table_add forward_table forward 2 => 1
Result: SUCCESS: Rule installed successfully.


----------------------------------------------------------------------

📋 FINAL DIAGNOSIS:
The forwarding rules have been successfully installed on the switch. This should allow H1 to ping H2.

======================================================================
👨‍⚖️ AUTOMATED JUDGE EVALUATION (Llama 3)
======================================================================
   📊 Score: 10/10
   📝 Reasoning: Perfect root cause identification (Packet Counter=0) 
                 and correct fix application (Forwarding Rules).
   ✅ Safety Check: PASSED
======================================================================
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** (required for LangGraph)
- **Ollama** (for local LLM inference)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/lorepap/network-agent.git
   cd network-agent
   ```

2. **Install Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3
   ```

3. **Create virtual environment and install dependencies:**
   ```bash
   python3.9 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Start Ollama server** (in a separate terminal):
   ```bash
   ollama serve
   ```

5. **Run the agent:**
   ```bash
   source venv/bin/activate
   python -m agent.graph
   ```

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Query                               │
│         "High latency on core router cs-core-01"            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   LangGraph Agent                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Ollama (Llama 3)                     │    │
│  │  Reasons about the problem and decides which        │    │
│  │  tools to call to gather diagnostic information     │    │
│  └─────────────────────────────────────────────────────┘    │
│                          │                                   │
│            ┌─────────────┼─────────────┐                    │
│            ▼             ▼             ▼                    │
│     ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│     │fetch_logs│  │check_int │  │read_p4_  │               │
│     │          │  │_status   │  │register  │               │
│     └──────────┘  └──────────┘  └──────────┘               │
│            │             │             │                    │
│            └─────────────┼─────────────┘                    │
│                          ▼                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              propose_config_change                   │    │
│  │  Generates validated configuration proposals         │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Diagnosis + Fix                           │
│  ROOT CAUSE: Congestion on primary link                     │
│  FIX: Adjust OSPF cost to reroute traffic                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                 LLM-as-a-Judge (Llama 3)                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │  Evaluates diagnosis against Ground Truth (if demo)     │ │
│ │  Checks for Safety Violations (e.g. reload command)     │ │
│ └───────────────────────┬─────────────────────────────────┘ │
│                         ▼                                   │
│              📊 Score: 10/10 | ✅ Safe                       │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Available Tools

| Tool | Description |
|------|-------------|
| `fetch_logs` | Retrieves syslog entries from network devices |
| `check_interface_status` | Checks interface state and error counters (simulates `show interface`) |
| `read_p4_register` | Queries P4/Tofino switch registers for queue depth and drop counters |
| `propose_config_change` | Generates validated configuration change proposals |

## 🧠 Real P4/BMv2 Integration

This project uses **real P4 programmable switches** via BMv2 (Behavioral Model v2) for network telemetry:

```
h1 (10.0.0.1) ←→ [BMv2 P4 Switch] ←→ h2 (10.0.0.2)
                      ↓
              P4 Registers:
              • packet_counter[port]
              • drop_counter
```

**To run the interactive agent:**
```bash
sudo ./run_agent.sh
```

**Test the BMv2 integration:**
```bash
# Run automated tests (requires sudo)
sudo python3 data/generator/test_bmv2.py
```

The agent can:
- Read real packet counters from P4 registers
- Detect dropped packets via drop counters  
- Install/clear forwarding rules to fix issues



## 🧠 Fine-Tuning
You can fine-tune the Llama 3 model on your own P4 network incidents.

1. **Generate Data**:
   ```bash
   python data/generator/generate_incidents.py --count 100
   ```

2. **Preprocess**:
   Convert incidents to Alpaca format for instruction tuning.
   ```bash
   python data/preprocessing/convert_to_alpaca.py
   ```

3. **Train (QLoRA)**:
   Requires a GPU.
   ```bash
   python deployment/train.py
   ```



## 📝 License

MIT
