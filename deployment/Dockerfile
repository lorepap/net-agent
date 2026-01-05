# Base image with CUDA support
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

# Install python and pip
RUN apt-get update && apt-get install -y python3 python3-pip git

# Install vLLM (Simulated version command)
# In production: pip install vllm
RUN pip install --no-cache-dir vllm

# Copy model files (assuming they are mounted or copied)
# COPY ./fine_tuning/results /model

# Expose port
EXPOSE 8000

# Entrypoint to serve the model
# Using a model that exists on HF for demo purposes if local not present
ENV MODEL_NAME="meta-llama/Meta-Llama-3-8B-Instruct"

ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server", \
            "--model", "meta-llama/Meta-Llama-3-8B-Instruct", \
            "--dtype", "half", \
            "--host", "0.0.0.0", \
            "--port", "8000"]
