#!/bin/bash
# Wrapper to run the agent with correct python path
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")
cd "$PROJECT_ROOT"
export PYTHONPATH=$PYTHONPATH:.
source venv/bin/activate
python3 agent/graph.py "$@"
