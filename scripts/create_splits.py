#!/usr/bin/env python3
"""Create train/validation splits from witness-train.jsonl"""

import json
import random
from pathlib import Path

random.seed(42)

# Load all examples
with open('data/witness-train.jsonl', 'r') as f:
    examples = [json.loads(line) for line in f]

print(f"Total examples: {len(examples)}")

# With only 22 examples, we'll do an 80/20 split (18 train, 4 val)
random.shuffle(examples)
split_idx = int(len(examples) * 0.8)

train = examples[:split_idx]
val = examples[split_idx:]

# Write splits
with open('data/train.jsonl', 'w') as f:
    for ex in train:
        f.write(json.dumps(ex) + '\n')

with open('data/val.jsonl', 'w') as f:
    for ex in val:
        f.write(json.dumps(ex) + '\n')

print(f"Train: {len(train)} examples")
print(f"Validation: {len(val)} examples")
print(f"\n✓ Splits created:")
print(f"  - data/train.jsonl")
print(f"  - data/val.jsonl")
