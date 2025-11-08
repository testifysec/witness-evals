#!/usr/bin/env python3
"""
Fine-tune Llama 3.2 3B on Witness dataset using Unsloth for fast, efficient training.

Requirements:
    pip install "unsloth[colab-new] @ git+https://github.com/unslothai/unsloth.git"
    pip install --no-deps "xformers<0.0.27" "trl<0.9.0" peft accelerate bitsandbytes
"""

import json
import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel

# Configuration
MAX_SEQ_LENGTH = 2048
DTYPE = None  # Auto-detect
LOAD_IN_4BIT = True  # Use 4-bit quantization for memory efficiency

MODEL_NAME = "unsloth/Llama-3.2-3B-Instruct"
OUTPUT_DIR = "./witness-llama-3.2-3b-lora"

print("=" * 80)
print("Witness Expert Model Fine-Tuning")
print("=" * 80)
print(f"Base Model: {MODEL_NAME}")
print(f"Training Examples: 17")
print(f"Validation Examples: 5")
print(f"Output: {OUTPUT_DIR}")
print("=" * 80)

# Step 1: Load model and tokenizer
print("\n📦 Loading model and tokenizer...")
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_NAME,
    max_seq_length=MAX_SEQ_LENGTH,
    dtype=DTYPE,
    load_in_4bit=LOAD_IN_4BIT,
)

# Step 2: Configure LoRA
print("🔧 Configuring LoRA adapters...")
model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_alpha=16,
    lora_dropout=0,  # Optimized to 0
    bias="none",
    use_gradient_checkpointing="unsloth",  # Very long context
    random_state=42,
    use_rslora=False,
    loftq_config=None,
)

# Step 3: Load and format dataset
print("📚 Loading training data...")

def load_jsonl(file_path):
    """Load JSONL file"""
    with open(file_path, 'r') as f:
        return [json.loads(line) for line in f]

def format_chat(example):
    """Format messages into chat template"""
    text = tokenizer.apply_chat_template(
        example["messages"],
        tokenize=False,
        add_generation_prompt=False
    )
    return {"text": text}

# Load data
train_data = load_jsonl("data/train.jsonl")
val_data = load_jsonl("data/val.jsonl")

# Convert to Dataset and format
train_dataset = Dataset.from_list(train_data).map(format_chat)
val_dataset = Dataset.from_list(val_data).map(format_chat)

print(f"  Train: {len(train_dataset)} examples")
print(f"  Val: {len(val_dataset)} examples")

# Step 4: Configure training
print("⚙️  Configuring training parameters...")
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4,  # Effective batch size = 8
    warmup_steps=10,
    num_train_epochs=3,  # With small dataset, 3 epochs is reasonable
    learning_rate=2e-4,
    fp16=not torch.cuda.is_bf16_supported(),
    bf16=torch.cuda.is_bf16_supported(),
    logging_steps=5,
    optim="adamw_8bit",
    weight_decay=0.01,
    lr_scheduler_type="linear",
    seed=42,
    save_strategy="epoch",
    eval_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    report_to="none",  # Disable W&B for simplicity
)

# Step 5: Create trainer
print("🏋️  Creating trainer...")
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    dataset_text_field="text",
    max_seq_length=MAX_SEQ_LENGTH,
    args=training_args,
)

# Step 6: Train!
print("\n" + "=" * 80)
print("🚀 Starting training...")
print("=" * 80)

trainer_stats = trainer.train()

print("\n" + "=" * 80)
print("✅ Training complete!")
print("=" * 80)

# Step 7: Save model
print(f"\n💾 Saving model to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("\n📊 Training Statistics:")
print(f"  Final Loss: {trainer_stats.training_loss:.4f}")
print(f"  Training Time: {trainer_stats.metrics['train_runtime']:.2f}s")
print(f"  Samples/sec: {trainer_stats.metrics['train_samples_per_second']:.2f}")

print("\n" + "=" * 80)
print("🎉 Fine-tuning complete!")
print("=" * 80)
print(f"\nModel saved to: {OUTPUT_DIR}")
print("\nNext steps:")
print("  1. Test the model: python3 test_model.py")
print("  2. Merge adapters: python3 merge_adapters.py")
print("  3. Deploy with Ollama or vLLM")
print("=" * 80)
