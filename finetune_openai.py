#!/usr/bin/env python3
"""
Fine-tune using OpenAI's API (easiest method for small datasets).

This is the simplest approach:
- Upload training data
- Start fine-tuning job
- Wait for completion
- Test the model

Requirements:
    - OpenAI API key (export OPENAI_API_KEY=sk-...)
    - pip install openai

Cost estimate for 22 examples on GPT-4o-mini:
    - Training: ~$0.50-1.00
    - Inference: $0.00015 per 1K tokens

Alternative free/local options in other scripts:
    - train_mlx.py (Apple Silicon, requires Python 3.9-3.12)
    - train_witness_model.py (GPU with PyTorch)
    - Use pre-trained models from Ollama
"""

import os
import json
import time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not installed!")
    print("\nInstall with: pip3 install --user --break-system-packages openai")
    exit(1)

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    print("❌ OPENAI_API_KEY not set!")
    print("\nSet your API key:")
    print("  export OPENAI_API_KEY='sk-...'")
    print("\nOr pass it when running:")
    print("  OPENAI_API_KEY='sk-...' python3 finetune_openai.py")
    exit(1)

client = OpenAI()

print("=" * 80)
print("🤖 Witness Expert Model Fine-Tuning (OpenAI API)")
print("=" * 80)
print("Base Model: gpt-4o-mini-2024-07-18")
print("Training Data: data/train.jsonl (17 examples)")
print("Validation Data: data/val.jsonl (5 examples)")
print("=" * 80)

# Step 1: Upload training file
print("\n📤 Uploading training data...")
with open("data/train.jsonl", "rb") as f:
    train_file = client.files.create(
        file=f,
        purpose="fine-tune"
    )

print(f"  ✓ Training file uploaded: {train_file.id}")

# Step 2: Upload validation file
print("📤 Uploading validation data...")
with open("data/val.jsonl", "rb") as f:
    val_file = client.files.create(
        file=f,
        purpose="fine-tune"
    )

print(f"  ✓ Validation file uploaded: {val_file.id}")

# Step 3: Create fine-tuning job
print("\n🚀 Starting fine-tuning job...")
job = client.fine_tuning.jobs.create(
    training_file=train_file.id,
    validation_file=val_file.id,
    model="gpt-4o-mini-2024-07-18",
    suffix="witness-expert",
    hyperparameters={
        "n_epochs": 3,  # With small dataset, 3 epochs is good
    }
)

print(f"  ✓ Job created: {job.id}")
print(f"  Status: {job.status}")

# Step 4: Monitor progress
print("\n⏳ Monitoring fine-tuning progress...")
print("  (This typically takes 10-20 minutes)")
print()

while True:
    job = client.fine_tuning.jobs.retrieve(job.id)
    print(f"  [{time.strftime('%H:%M:%S')}] Status: {job.status}", end="")

    if job.status == "succeeded":
        print(" ✅")
        break
    elif job.status == "failed":
        print(" ❌")
        print(f"\nError: {job.error}")
        exit(1)
    elif job.status == "cancelled":
        print(" 🚫")
        print("\nJob was cancelled")
        exit(1)
    else:
        print(f" (estimated time: {job.estimated_finish or 'calculating...'})")
        time.sleep(30)  # Check every 30 seconds

# Step 5: Get results
print("\n" + "=" * 80)
print("✅ Fine-tuning complete!")
print("=" * 80)

fine_tuned_model = job.fine_tuned_model
print(f"\nFine-tuned model: {fine_tuned_model}")
print(f"Training file: {train_file.id}")
print(f"Validation file: {val_file.id}")
print(f"Job ID: {job.id}")

# Save model info
model_info = {
    "model_id": fine_tuned_model,
    "job_id": job.id,
    "train_file_id": train_file.id,
    "val_file_id": val_file.id,
    "created_at": job.created_at,
    "finished_at": job.finished_at,
}

with open("model_info.json", "w") as f:
    json.dump(model_info, f, indent=2)

print("\n💾 Model info saved to: model_info.json")

# Step 6: Test the model
print("\n" + "=" * 80)
print("🧪 Testing the model...")
print("=" * 80)

test_prompt = "How do I attest a Go build with witness?"

print(f"\nTest prompt: {test_prompt}\n")
print("Response:")
print("-" * 80)

response = client.chat.completions.create(
    model=fine_tuned_model,
    messages=[
        {"role": "system", "content": "You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."},
        {"role": "user", "content": test_prompt}
    ],
    max_tokens=500,
    temperature=0.7
)

print(response.choices[0].message.content)
print("-" * 80)

print("\n" + "=" * 80)
print("🎉 All done!")
print("=" * 80)
print("\nNext steps:")
print(f"  1. Test more examples: python3 test_openai_model.py {fine_tuned_model}")
print("  2. Use in production with the model ID above")
print("  3. Monitor usage at: https://platform.openai.com/finetune")
print("=" * 80)
