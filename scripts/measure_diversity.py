#!/usr/bin/env python3
"""
Measure actual diversity using embeddings.

For each Q/A pair:
1. Embed user question + assistant answer
2. Calculate pairwise cosine distances
3. Identify duplicates/near-duplicates
4. Visualize clustering
5. Report diversity metrics
"""

import json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import sys

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')  # Small, fast

# Load backup data
data_file = Path("data/diverse-100k/train_backup.jsonl")
print(f"Loading {data_file}...")

with open(data_file, 'r') as f:
    examples = [json.loads(line) for line in f]

print(f"Loaded {len(examples)} examples")

# Sample for speed (embedding 36K takes time)
sample_size = min(5000, len(examples))
print(f"Analyzing {sample_size} examples...")

import random
random.seed(42)
sampled = random.sample(examples, sample_size)

# Create text for embedding (user Q + assistant A)
texts = []
for ex in sampled:
    user_q = ex['messages'][1]['content']
    assistant_a = ex['messages'][2]['content'][:500]  # First 500 chars
    combined = user_q + " " + assistant_a
    texts.append(combined)

print("Generating embeddings...")
embeddings = model.encode(texts, show_progress_bar=True)

print(f"Embedding shape: {embeddings.shape}")

# Calculate pairwise cosine similarities
print("Calculating pairwise similarities...")
similarities = cosine_similarity(embeddings)

# Get upper triangle (avoid diagonal and duplicates)
triu_indices = np.triu_indices_from(similarities, k=1)
pairwise_sims = similarities[triu_indices]

# Statistics
print("\n" + "="*70)
print("Diversity Analysis")
print("="*70)
print(f"Mean similarity: {pairwise_sims.mean():.4f}")
print(f"Median similarity: {np.median(pairwise_sims):.4f}")
print(f"Min similarity: {pairwise_sims.min():.4f}")
print(f"Max similarity: {pairwise_sims.max():.4f}")
print(f"Std similarity: {pairwise_sims.std():.4f}")

# Find near-duplicates
thresholds = [0.95, 0.90, 0.85, 0.80]
print(f"\nNear-duplicates (cosine similarity):")
for thresh in thresholds:
    count = (pairwise_sims > thresh).sum()
    pct = count * 100 / len(pairwise_sims)
    print(f"  > {thresh}: {count:,} pairs ({pct:.2f}%)")

# Diversity score (lower similarity = higher diversity)
diversity_score = 1 - pairwise_sims.mean()
print(f"\nDiversity score: {diversity_score:.4f} (higher = more diverse)")
print("  0.0 = all identical")
print("  1.0 = maximally diverse")

# Find most similar pairs (potential duplicates)
print(f"\nMost similar pairs:")
most_similar_idx = np.argsort(pairwise_sims)[-5:][::-1]
for idx in most_similar_idx:
    i, j = triu_indices[0][idx], triu_indices[1][idx]
    sim = pairwise_sims[idx]
    print(f"  Similarity {sim:.4f}:")
    print(f"    Q1: {sampled[i]['messages'][1]['content'][:60]}...")
    print(f"    Q2: {sampled[j]['messages'][1]['content'][:60]}...")

print("="*70)
