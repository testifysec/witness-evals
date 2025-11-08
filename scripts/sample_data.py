#!/usr/bin/env python3
"""Sample training data to show what the model is learning"""

import json
import random

with open('data/synthetic/train.jsonl', 'r') as f:
    lines = f.readlines()

# Sample 5 random examples
samples = random.sample(range(len(lines)), 5)

for i, idx in enumerate(sorted(samples), 1):
    ex = json.loads(lines[idx])

    print(f"{'='*80}")
    print(f"Example #{i} (line {idx})")
    print(f"{'='*80}")
    print(f"\n👤 USER:")
    print(ex['messages'][1]['content'][:300])
    print(f"\n🤖 ASSISTANT:")
    print(ex['messages'][2]['content'][:500])
    print(f"\n... (truncated)")
    print()
