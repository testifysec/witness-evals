# Fine-Tuning Guide for Witness Expert Models

This guide explains how to fine-tune open-source language models on the Witness attestation framework using the training dataset in this repository.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Choosing a Base Model](#choosing-a-base-model)
3. [Data Preparation](#data-preparation)
4. [Fine-Tuning Methods](#fine-tuning-methods)
5. [Training with Different Frameworks](#training-with-different-frameworks)
6. [Evaluation](#evaluation)
7. [Deployment](#deployment)

## Prerequisites

### Hardware Requirements

**Minimum (for 7-8B models)**:
- 24GB VRAM (RTX 3090, A5000, A6000)
- 32GB RAM
- 100GB disk space

**Recommended**:
- 40GB+ VRAM (A100, H100)
- 64GB+ RAM
- 500GB NVMe SSD

### Software Requirements

```bash
# Python 3.10+
python3 --version

# PyTorch with CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Hugging Face libraries
pip install transformers datasets accelerate bitsandbytes
pip install peft  # For LoRA fine-tuning
pip install wandb  # For experiment tracking (optional)
```

## Choosing a Base Model

### Recommended Base Models

| Model | Size | License | Best For |
|-------|------|---------|----------|
| **Llama 3.1 8B Instruct** | 8B | Llama 3 | General purpose, good instruction following |
| **Mistral 7B Instruct** | 7B | Apache 2.0 | Efficient, commercially friendly |
| **CodeLlama 7B Instruct** | 7B | Llama 2 | Code-heavy tasks |
| **Qwen 2.5 7B Instruct** | 7B | Apache 2.0 | Strong reasoning |

### Selection Criteria

- **Task alignment**: Instruction-tuned models work better
- **License**: Apache 2.0 for commercial use
- **Size**: 7-8B models balance quality and inference speed
- **Community support**: Popular models have better tooling

## Data Preparation

### 1. Generate Full Dataset

```bash
cd witness-evals
python3 scripts/generate_dataset.py
python3 scripts/validate_dataset.py
```

### 2. Merge JSONL Files

Create a single training file:

```bash
cat data/attestors/*.jsonl \
    data/policies/*.jsonl \
    data/workflows/*.jsonl \
    > data/witness-train.jsonl
```

### 3. Create Train/Validation Split

```python
import json
import random
from pathlib import Path

# Load all examples
with open('data/witness-train.jsonl', 'r') as f:
    examples = [json.loads(line) for line in f]

# Shuffle and split (90/10)
random.seed(42)
random.shuffle(examples)
split_idx = int(len(examples) * 0.9)

train = examples[:split_idx]
val = examples[split_idx:]

# Write splits
with open('data/train.jsonl', 'w') as f:
    for ex in train:
        f.write(json.dumps(ex) + '\n')

with open('data/val.jsonl', 'w') as f:
    for ex in val:
        f.write(json.dumps(ex) + '\n')

print(f"Train: {len(train)}, Val: {len(val)}")
```

## Fine-Tuning Methods

### Method 1: Full Fine-Tuning

**Pros**: Best quality, full control
**Cons**: Expensive (requires lots of VRAM), slow

### Method 2: LoRA (Recommended)

**Pros**: Fast, VRAM-efficient, good quality
**Cons**: Slightly lower quality than full fine-tuning

### Method 3: QLoRA

**Pros**: Can run on smaller GPUs (12GB+)
**Cons**: Slowest, quantization quality loss

**We recommend LoRA** for most users.

## Training with Different Frameworks

### Option 1: Hugging Face Transformers (Recommended)

Create `train_witness.py`:

```python
#!/usr/bin/env python3
"""Fine-tune a model on Witness dataset using LoRA"""

import json
from pathlib import Path
from datasets import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from peft import LoraConfig, get_peft_model, TaskType
import torch

# Configuration
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
OUTPUT_DIR = "./witness-llama-3.1-8b-lora"
DATA_DIR = "./data"

# LoRA configuration
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,  # Rank
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Llama 3 modules
    bias="none"
)

# Load tokenizer and model
print(f"Loading {BASE_MODEL}...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True
)

# Apply LoRA
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load dataset
def load_jsonl(file_path):
    """Load JSONL file into list of dicts"""
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

# Load and format data
train_data = load_jsonl(Path(DATA_DIR) / "train.jsonl")
val_data = load_jsonl(Path(DATA_DIR) / "val.jsonl")

train_dataset = Dataset.from_list(train_data).map(format_chat)
val_dataset = Dataset.from_list(val_data).map(format_chat)

# Tokenize
def tokenize_function(examples):
    return tokenizer(
        examples["text"],
        truncation=True,
        max_length=2048,
        padding="max_length"
    )

train_dataset = train_dataset.map(tokenize_function, batched=True)
val_dataset = val_dataset.map(tokenize_function, batched=True)

# Training arguments
training_args = TrainingArguments(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    weight_decay=0.01,
    warmup_steps=100,
    logging_steps=10,
    save_steps=100,
    eval_steps=100,
    evaluation_strategy="steps",
    save_strategy="steps",
    load_best_model_at_end=True,
    fp16=False,
    bf16=True,
    optim="adamw_torch",
    report_to=["wandb"],  # Remove if not using W&B
    run_name="witness-llama-3.1-lora"
)

# Data collator
data_collator = DataCollatorForLanguageModeling(
    tokenizer=tokenizer,
    mlm=False
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    data_collator=data_collator
)

# Train
print("Starting training...")
trainer.train()

# Save final model
print(f"Saving model to {OUTPUT_DIR}")
trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)

print("✓ Training complete!")
```

Run training:

```bash
python3 train_witness.py
```

### Option 2: Axolotl (Advanced)

Axolotl provides a YAML-based configuration approach.

Install:
```bash
pip install axolotl
```

Create `axolotl_config.yml`:

```yaml
base_model: meta-llama/Llama-3.1-8B-Instruct
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer

load_in_8bit: false
load_in_4bit: false
strict: false

datasets:
  - path: data/train.jsonl
    type: chat_template
    split: train

val_set_size: 0.1

output_dir: ./witness-llama-axolotl

adapter: lora
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - k_proj
  - v_proj
  - o_proj

sequence_len: 2048
sample_packing: false

micro_batch_size: 4
gradient_accumulation_steps: 4
num_epochs: 3
optimizer: adamw_torch
lr_scheduler: cosine
learning_rate: 2e-4

train_on_inputs: false
group_by_length: false

bf16: auto
fp16: false
tf32: true

gradient_checkpointing: true
early_stopping_patience: 3

logging_steps: 10
eval_steps: 100
save_steps: 100

warmup_steps: 100
evals_per_epoch: 4
saves_per_epoch: 2

wandb_project: witness-fine-tuning
wandb_run_id: llama-3.1-lora
```

Run:
```bash
accelerate launch -m axolotl.cli.train axolotl_config.yml
```

### Option 3: LM Studio (GUI, Easiest)

1. Download [LM Studio](https://lmstudio.ai/)
2. Load base model (e.g., Llama 3.1 8B)
3. Import training data (JSONL format)
4. Configure LoRA settings
5. Click "Start Training"

## Evaluation

### 1. Automated Evaluation

Create `eval_model.py`:

```python
#!/usr/bin/env python3
"""Evaluate fine-tuned model on Witness tasks"""

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch
import json

MODEL_PATH = "./witness-llama-3.1-8b-lora"
BASE_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

# Load model
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
base_model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto"
)
model = PeftModel.from_pretrained(base_model, MODEL_PATH)

# Test prompts
test_cases = [
    "How do I attest a Go build with commandrun?",
    "Write a Rego policy to enforce builds from the main branch",
    "How do I create a witness policy for a multi-step pipeline?"
]

for prompt in test_cases:
    messages = [
        {"role": "system", "content": "You are an expert in Witness..."},
        {"role": "user", "content": prompt}
    ]

    inputs = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True
    ).to(model.device)

    outputs = model.generate(
        inputs,
        max_new_tokens=512,
        temperature=0.7,
        do_sample=True,
        top_p=0.9
    )

    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\nPrompt: {prompt}")
    print(f"Response: {response}\n")
    print("=" * 80)
```

### 2. Manual Evaluation Criteria

Test the model on:

- ✅ **Command accuracy**: Does it generate valid `witness run` commands?
- ✅ **Flag completeness**: Are all required flags included?
- ✅ **Rego syntax**: Is the Rego policy syntactically correct?
- ✅ **Policy structure**: Are JSON policies valid?
- ✅ **Explanation quality**: Does it explain what each part does?
- ✅ **Security awareness**: Does it recommend secure practices?

### 3. Benchmark Against Base Model

Compare fine-tuned vs. base model on:
- Command generation accuracy
- Rego policy correctness
- Response relevance

## Deployment

### Option 1: Local Inference

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Load fine-tuned model
tokenizer = AutoTokenizer.from_pretrained("./witness-llama-3.1-8b-lora")
base_model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B-Instruct")
model = PeftModel.from_pretrained(base_model, "./witness-llama-3.1-8b-lora")

# Inference
def ask_witness_expert(question: str) -> str:
    messages = [
        {"role": "system", "content": "You are an expert in Witness..."},
        {"role": "user", "content": question}
    ]
    inputs = tokenizer.apply_chat_template(messages, return_tensors="pt")
    outputs = model.generate(inputs, max_new_tokens=512)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)
```

### Option 2: vLLM (Fast Inference)

```bash
pip install vllm

python -m vllm.entrypoints.openai.api_server \
    --model ./witness-llama-3.1-8b-lora \
    --served-model-name witness-expert \
    --port 8000
```

### Option 3: Ollama (Easy Deployment)

```bash
# Create Modelfile
cat > Modelfile <<EOF
FROM llama3.1:8b-instruct
ADAPTER ./witness-llama-3.1-8b-lora
SYSTEM "You are an expert in the Witness supply chain attestation framework..."
EOF

# Create model
ollama create witness-expert -f Modelfile

# Run
ollama run witness-expert
```

## Troubleshooting

### Out of Memory Errors

1. **Reduce batch size**: `per_device_train_batch_size=1`
2. **Increase gradient accumulation**: `gradient_accumulation_steps=8`
3. **Enable gradient checkpointing**: `gradient_checkpointing=True`
4. **Use QLoRA**: Load model in 4-bit quantization

### Slow Training

1. **Enable bf16**: `bf16=True`
2. **Use flash attention**: `pip install flash-attn`
3. **Reduce sequence length**: `max_length=1024`
4. **Use multiple GPUs**: `accelerate launch`

### Poor Quality

1. **More epochs**: Increase from 3 to 5
2. **Better data**: Add more diverse examples
3. **Larger LoRA rank**: Increase `r` from 16 to 32
4. **Lower learning rate**: Try `1e-4` instead of `2e-4`

## Next Steps

1. **Expand dataset**: Add examples for all 21+ attestors
2. **Add security scenarios**: Tampering detection, attack prevention
3. **Multi-task training**: Include general coding abilities
4. **Evaluation suite**: Automated testing of generated commands
5. **Community contributions**: Share your fine-tuned models!

## Resources

- [Hugging Face Fine-Tuning Tutorial](https://huggingface.co/docs/transformers/training)
- [LoRA Paper](https://arxiv.org/abs/2106.09685)
- [Axolotl Documentation](https://github.com/OpenAccess-AI-Collective/axolotl)
- [Witness Documentation](https://github.com/in-toto/go-witness)
