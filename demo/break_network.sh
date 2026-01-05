#!/bin/bash
# Simulates a network incident by clearing forwarding rules
echo "🔥 SIMULATING NETWORK INCIDENT..."
echo "Clearling forwarding table on switch s1..."
echo "table_clear forward_table" | simple_switch_CLI --thrift-port 9090
echo "❌ Connectivity Broken! Use the Agent to fix it."
