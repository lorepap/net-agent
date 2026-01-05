"""
Fine-Tuning Script using QLoRA.

This script fine-tunes Llama 3 on the generated network incident dataset.
It uses 4-bit quantization (QLoRA) to run efficiently on T4/Consumer GPUs.
"""
import os
import sys
import json
import torch
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    logging,
)
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer

# Configuration
MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct" 
NEW_MODEL_NAME = "llama-3-8b-network-expert"
DATASET_PATH = "data/custom_dataset/dataset_index.json"
OUTPUT_DIR = "./results"

def load_custom_dataset(path: str) -> Dataset:
    """Load and format the custom dataset for SFT."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset not found at {path}")
        
    with open(path, "r") as f:
        raw_data = json.load(f)
        
    # Flatten the dataset for training
    formatted_data = []
    for item in raw_data:
        # Load logs content
        syslog_path = item["logs"]["syslog"]
        try:
            with open(syslog_path, "r") as f:
                logs = f.read()
            # Truncate logs if too long (simple heuristic)
            if len(logs) > 4000:
                logs = logs[:4000] + "\n...[TRUNCATED]"
        except Exception:
            logs = "Logs unavailable."

        formatted_data.append({
            "instruction": f"Analyze the following logs to diagnose the network issue: {item['ground_truth']['description']}",
            "input": logs,
            "output": f"Likely Root Cause: {item['ground_truth']['root_cause']}\nRecommended Fix: {item['ground_truth']['recommended_fix']}\nSuggested Commands:\n" + "\n".join(item['ground_truth']['commands'])
        })
        
    return Dataset.from_list(formatted_data)

def main():
    print(f"🚀 Starting QLoRA Fine-tuning on {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    
    # 1. Load Dataset
    print(f"Loading dataset from {DATASET_PATH}...")
    dataset = load_custom_dataset(DATASET_PATH)
    print(f"Loaded {len(dataset)} training examples.")

    # 2. QLoRA Config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=False,
    )

    # 3. Load Base Model
    print(f"Loading base model: {MODEL_NAME}")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto"
    )
    model.config.use_cache = False
    model.config.pretraining_tp = 1

    # 4. Load Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right" # Fix for FP16

    # 5. LoRA Adapter Config
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj"] # Target attention & MLP
    )

    # 6. Training Arguments
    training_args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=3,
        per_device_train_batch_size=2, # Low batch size for T4
        gradient_accumulation_steps=2,
        optim="paged_adamw_32bit",
        save_steps=25,
        logging_steps=10,
        learning_rate=2e-4,
        weight_decay=0.001,
        fp16=False,
        bf16=False, # Use fp16 for T4 if possible, usually safe
        max_grad_norm=0.3,
        max_steps=-1,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
        report_to="tensorboard"
    )

    # 7. Trainer
    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        peft_config=peft_config,
        dataset_text_field="output", # Using SFTTrainer's simple mode, usually needs formatting_func
        max_seq_length=2048,
        tokenizer=tokenizer,
        args=training_args,
        packing=False,
        formatting_func=lambda x: [f"### Instruction: {x['instruction']}\n### Input: {x['input']}\n### Response: {x['output']}" for x in dataset]
    )

    print("Training started...")
    trainer.train()
    
    # 8. Save
    print(f"Saving model to {NEW_MODEL_NAME}")
    trainer.model.save_pretrained(NEW_MODEL_NAME)
    print("✅ Fine-tuning complete!")

if __name__ == "__main__":
    main()
