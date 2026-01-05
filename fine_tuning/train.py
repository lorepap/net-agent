import os
import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    pipeline,
    logging,
)
from peft import LoraConfig, PEFTConfig
from trl import SFTTrainer

# Configuration
MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct" # Or "microsoft/Phi-3-mini-4k-instruct"
NEW_MODEL_NAME = "llama-3-8b-network-expert"
DATASET_PATH = "data/custom_dataset/dataset_index.json" # Needs pre-processing to jsonl or similar

# QLoRA Config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)

def format_instruction(sample):
	return f"""### Instruction:
Analyze the following network logs and identify the root cause and recommended fix.

### Input:
{sample['logs']}

### Response:
Root Cause: {sample['ground_truth']['root_cause']}
Fix: {sample['ground_truth']['recommended_fix']}
"""

def main():
    # Load Model
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto"
    )
    model.config.use_cache = False
    model.config.pretraining_tp = 1

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    # LoRA Config
    peft_config = LoraConfig(
        lora_alpha=16,
        lora_dropout=0.1,
        r=64,
        bias="none",
        task_type="CAUSAL_LM",
    )

    # Training Arguments
    training_arguments = TrainingArguments(
        output_dir="./results",
        num_train_epochs=1,
        per_device_train_batch_size=4,
        gradient_accumulation_steps=1,
        optim="paged_adamw_32bit",
        save_steps=25,
        logging_steps=25,
        learning_rate=2e-4,
        weight_decay=0.001,
        fp16=False,
        bf16=False,
        max_grad_norm=0.3,
        max_steps=-1,
        warmup_ratio=0.03,
        group_by_length=True,
        lr_scheduler_type="constant",
    )

    # Mock dataset loading for scaffolding (In real usage, we'd load jsonl)
    # dataset = load_dataset("json", data_files=DATASET_PATH, split="train")
    # For now, we assume dataset is pre-processed

    print("Starting Training (Mock)...")
    # trainer = SFTTrainer(
    #     model=model,
    #     train_dataset=dataset,
    #     peft_config=peft_config,
    #     dataset_text_field="text",
    #     max_seq_length=None,
    #     tokenizer=tokenizer,
    #     args=training_arguments,
    #     packing=False,
    # )

    # trainer.train()
    # trainer.model.save_pretrained(NEW_MODEL_NAME)
    print("Training Complete (Mock)")

if __name__ == "__main__":
    main()
