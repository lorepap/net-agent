#!/bin/bash
# Script to serve the fine-tuned network agent model using vLLM
# This provides an OpenAI-compatible API endpoint for low-latency inference.

MODEL_PATH="./llama-3-8b-network-expert"
PORT=8000

# Check if model exists (after fine-tuning)
if [ ! -d "$MODEL_PATH" ]; then
    echo "⚠️  Fine-tuned model not found at $MODEL_PATH"
    echo "    Using base model 'meta-llama/Meta-Llama-3-8B-Instruct' for demonstration."
    MODEL_PATH="meta-llama/Meta-Llama-3-8B-Instruct"
fi

echo "🚀 Starting vLLM Inference Server..."
echo "Model: $MODEL_PATH"
echo "Port: $PORT"

# Run vLLM (Optimized for T4)
# --quantization awq/gptq could be added if model was quantized
python3 -m vllm.entrypoints.openai.api_server \
    --model $MODEL_PATH \
    --port $PORT \
    --dtype float16 \
    --gpu-memory-utilization 0.9 \
    --max-model-len 4096

# Usage:
# curl http://localhost:8000/v1/chat/completions \
#   -H "Content-Type: application/json" \
#   -d '{
#     "model": "llama-3-8b-network-expert",
#     "messages": [{"role": "user", "content": "Diagnose high latency on cs-core-01"}]
#   }'
