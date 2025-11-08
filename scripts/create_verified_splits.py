#!/usr/bin/env python3
"""Create train/valid splits from verified dataset"""

import json
import random
from pathlib import Path

random.seed(42)

input_file = Path("data/verified/verified_train.jsonl")
output_dir = Path("data/verified")

# Load all examples
print(f"Loading {input_file}...")
with open(input_file, 'r') as f:
    examples = [json.loads(line) for line in f]

print(f"Total examples: {len(examples)}")

# 90/10 split
random.shuffle(examples)
split_idx = int(len(examples) * 0.9)

train = examples[:split_idx]
valid = examples[split_idx:]

# Write splits
train_file = output_dir / "train.jsonl"
valid_file = output_dir / "valid.jsonl"

with open(train_file, 'w') as f:
    for ex in train:
        f.write(json.dumps(ex) + '\n')

with open(valid_file, 'w') as f:
    for ex in valid:
        f.write(json.dumps(ex) + '\n')

print(f"\n✅ Splits created:")
print(f"  Train: {len(train):,} examples -> {train_file}")
print(f"  Valid: {len(valid):,} examples -> {valid_file}")
print(f"\nReady for MLX training!")
