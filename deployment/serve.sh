#!/bin/bash

# Serve script for Network Agent
echo "Starting vLLM Inference Server..."

# Check if docker is installed
if ! command -v docker &> /dev/null
then
    echo "Docker could not be found. Please install Docker."
    exit 1
fi

# Build
echo "Building Docker image..."
docker build -t network-agent-vllm ./deployment

# Run
echo "Running Container..."
# Using --gpus all for CUDA
docker run --gpus all -p 8000:8000 -v $(pwd)/fine_tuning/results:/model network-agent-vllm

echo "Server running at http://localhost:8000"
