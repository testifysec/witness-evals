#!/usr/bin/env python3
"""
Fine-tune Llama 3.2 3B on Witness dataset using MLX (Apple Silicon optimized).

MLX is Apple's machine learning framework optimized for Apple Silicon.
It's much faster than PyTorch on M1/M2/M3 Macs.

Installation:
    pip3 install mlx mlx-lm transformers datasets

Usage:
    python3 train_mlx.py
"""

import json
import time
from pathlib import Path

try:
    import mlx.core as mx
    from mlx_lm import load, generate
    from mlx_lm.tuner import train as mlx_train
    from mlx_lm.tuner.utils import build_schedule
except ImportError:
    print("❌ MLX not installed!")
    print("\nInstall with: pip3 install mlx mlx-lm transformers datasets")
    exit(1)

# Configuration
MODEL_NAME = "mlx-community/Llama-3.2-3B-Instruct-4bit"  # Pre-quantized for speed
OUTPUT_DIR = "./witness-llama-3.2-3b-lora-mlx"
DATA_DIR = Path("./data")

print("=" * 80)
print("🍎 Witness Expert Model Fine-Tuning (MLX)")
print("=" * 80)
print(f"Base Model: {MODEL_NAME}")
print(f"Output: {OUTPUT_DIR}")
print(f"Device: Apple Silicon (MLX)")
print("=" * 80)

# Step 1: Convert JSONL to MLX format
print("\n📚 Preparing training data...")

def load_jsonl(file_path):
    """Load JSONL file"""
    with open(file_path, 'r') as f:
        return [json.loads(line) for line in f]

def convert_to_mlx_format(examples):
    """Convert examples to MLX chat format"""
    converted = []
    for ex in examples:
        # MLX expects {"messages": [...]} format
        converted.append({"messages": ex["messages"]})
    return converted

# Load and convert
train_data = load_jsonl(DATA_DIR / "train.jsonl")
val_data = load_jsonl(DATA_DIR / "val.jsonl")

print(f"  Train: {len(train_data)} examples")
print(f"  Val: {len(val_data)} examples")

# Save in MLX format
mlx_train_path = DATA_DIR / "train_mlx.jsonl"
mlx_val_path = DATA_DIR / "val_mlx.jsonl"

with open(mlx_train_path, 'w') as f:
    for ex in convert_to_mlx_format(train_data):
        f.write(json.dumps(ex) + '\n')

with open(mlx_val_path, 'w') as f:
    for ex in convert_to_mlx_format(val_data):
        f.write(json.dumps(ex) + '\n')

print(f"  ✓ Converted to MLX format")

# Step 2: Configure training parameters
print("\n⚙️  Training Configuration:")

config = {
    "model": MODEL_NAME,
    "train": True,
    "data": str(mlx_train_path),
    "valid_data": str(mlx_val_path),
    "lora_layers": 16,  # Number of layers to apply LoRA
    "batch_size": 2,
    "iters": 100,  # Number of training iterations
    "steps_per_eval": 20,
    "val_batches": 5,
    "learning_rate": 2e-5,
    "adapter_path": OUTPUT_DIR,
    "save_every": 50,
    "test": False,
    "test_batches": 5,
    "max_seq_length": 2048,
}

for key, value in config.items():
    if key not in ["model", "data", "valid_data", "adapter_path"]:
        print(f"  {key}: {value}")

# Step 3: Run training
print("\n" + "=" * 80)
print("🚀 Starting MLX fine-tuning...")
print("=" * 80)
print("\nThis will:")
print("  1. Download Llama 3.2 3B (4-bit quantized) if needed")
print("  2. Apply LoRA adapters to the model")
print("  3. Fine-tune on 17 training examples")
print("  4. Validate on 5 examples")
print("  5. Save adapters to", OUTPUT_DIR)
print("\nEstimated time: 5-15 minutes (depending on your Mac)")
print("=" * 80)

start_time = time.time()

try:
    # Note: mlx_train expects command-line style arguments
    # We'll need to use the CLI instead
    print("\n⚠️  Please run the following command instead:\n")

    cmd = f"""mlx_lm.lora \\
  --model {MODEL_NAME} \\
  --train \\
  --data {mlx_train_path} \\
  --valid-data {mlx_val_path} \\
  --lora-layers 16 \\
  --batch-size 2 \\
  --iters 100 \\
  --steps-per-eval 20 \\
  --learning-rate 2e-5 \\
  --adapter-path {OUTPUT_DIR} \\
  --save-every 50 \\
  --max-seq-length 2048"""

    print(cmd)
    print("\nOr use the wrapper script: ./train_mlx.sh\n")

    # Create wrapper script
    with open("train_mlx.sh", "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("# MLX fine-tuning script for Witness Expert Model\n\n")
        f.write(cmd + "\n")

    import os
    os.chmod("train_mlx.sh", 0o755)

    print("✓ Created train_mlx.sh wrapper script")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nFalling back to CLI command...")

elapsed = time.time() - start_time

print("\n" + "=" * 80)
print("📝 Next Steps:")
print("=" * 80)
print("\n1. Install MLX if not already:")
print("   pip3 install mlx mlx-lm")
print("\n2. Run the training script:")
print("   ./train_mlx.sh")
print("\n3. Or use the mlx_lm command directly (see above)")
print("\n4. Test the model:")
print("   python3 test_mlx_model.py")
print("\n" + "=" * 80)
