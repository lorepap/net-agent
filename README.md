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

📝 Issue: The interface on cs-access-01 seems to be down

----------------------------------------------------------------------
🔧 Step 1: Calling tool 'fetch_logs'
   Args: {'device_id': 'cs-access-01'}
📊 Tool result: <189> Jan 05 10:00:00 cs-access-01 %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1...

🔧 Step 2: Calling tool 'check_interface_status'
   Args: {'device_id': 'cs-access-01', 'interface': 'GigabitEthernet0/0/1'}
📊 Tool result: Interface GigabitEthernet0/0/1 ... Admin status: administratively down...

🔧 Step 3: Calling tool 'propose_config_change'
   Args: {'device_id': 'cs-access-01', 'config_commands': ['interface GigabitEthernet0/0/1', 'no shutdown']}

----------------------------------------------------------------------

📋 FINAL DIAGNOSIS:

📋 ROOT CAUSE: Interface GigabitEthernet0/0/1 is administratively shut down
🔧 RECOMMENDED FIX: Enable the interface using 'no shutdown' command

[Proposed configuration displayed]
======================================================================
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.9+** (required for LangGraph)
- **Ollama** (for local LLM inference)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/network-agent.git
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

**Test the BMv2 integration:**
```bash
# Run automated tests (requires sudo)
sudo python3 data/generator/test_bmv2.py
```

The agent can:
- Read real packet counters from P4 registers
- Detect dropped packets via drop counters  
- Install/clear forwarding rules to fix issues

## 📂 Project Structure

```
├── agent/                  # Agent logic (LangGraph)
│   ├── graph.py            # ReAct agent implementation
│   ├── tools.py            # Network diagnostic tools
│   └── state.py            # Agent state definition
├── p4src/                  # P4 switch programs
│   ├── basic_forward.p4    # L2 forwarding with counters
│   └── basic_forward.json  # Compiled P4 program
├── data/                   # Data generation
│   └── generator/          # Mininet + BMv2 scripts
│       ├── test_bmv2.py    # BMv2 integration tests
│       └── simple_bmv2_topo.py
├── evaluation/             # LLM-as-a-Judge pipeline
│   └── judge.py            # Evaluation with Ollama or mock
├── deployment/             # Docker + vLLM serving
└── requirements.txt        # Python dependencies
```

## 🧪 Additional Commands

**Generate synthetic incidents:**
```bash
python data/generator/generate_incidents.py --count 5
```

**Run evaluation pipeline:**
```bash
# Mock evaluation (fast, rule-based)
python evaluation/judge.py --backend mock

# LLM evaluation (requires Ollama)
python evaluation/judge.py --backend ollama --model llama3
```

## 📝 License

MIT
