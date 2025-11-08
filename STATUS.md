# Status Report: Witness-Evals Fine-Tuning

**Last Updated**: 2025-11-08 ~12:00 PM

## 🎉 Major Achievements

### 1. Generated 10,000 Formally Verified Examples ✅
- **Success rate**: 100% (10,000/10,000)
- **File size**: 26 MB
- **Generation time**: ~30 minutes
- **Verification**: Every example passed `witness verify`

### 2. Training In Progress 🔥
- **Model**: Llama 3.2 3B (4-bit) with LoRA
- **Framework**: MLX (Apple Silicon optimized)
- **Dataset**: 9,000 train, 1,000 validation (verified examples)
- **Status**: Running in background
- **Output**: `witness-llama-3.2-3b-verified-10k/`

### 3. Repository Committed ✅
- **GitHub**: https://github.com/testifysec/witness-evals
- **Commits**: 2 (initial + verified dataset)
- **Files**: Scripts, documentation, 10K examples

## 📊 Training Progress

### Current Status
```
Iteration: 1/500 (starting)
Initial Val Loss: 2.177
ETA: ~45-50 minutes
```

Training will automatically:
- Save checkpoints every 100 iterations
- Evaluate on validation set every 100 iterations
- Complete after 500 iterations
- Save final model to `./witness-llama-3.2-3b-verified-10k/`

### Expected Loss Trajectory
Based on previous training run with synthetic data:
- Iter 100: ~0.35-0.40
- Iter 200: ~0.33-0.35
- Iter 300: ~0.32-0.34
- Iter 500: ~0.30-0.33 (final)

## 📁 Dataset Breakdown

### Verified Dataset (PRIMARY - Now Training)
```
data/verified/
├── verified_train.jsonl    # 10,000 verified examples
├── train.jsonl              # 9,000 training examples
└── valid.jsonl              # 1,000 validation examples
```

**Quality**: HIGHEST - Every example passed formal verification

### Synthetic Dataset (COMPLETED)
```
data/synthetic/
├── train.jsonl              # 9,000 examples
└── valid.jsonl              # 1,000 examples
```

**Quality**: HIGH - Programmatically generated, syntactically valid

### Manual Dataset (BASELINE)
```
data/attestors/*.jsonl       # 22 hand-written examples
data/policies/*.jsonl
data/workflows/*.jsonl
```

**Quality**: GOOD - Human-crafted examples

## 🔧 Key Scripts

1. **generate_10k_verified.py** - Generates formally verified examples
2. **create_verified_splits.py** - Creates train/val splits
3. **synthetic_data_generator.py** - Generates synthetic examples
4. **validate_dataset.py** - Validates JSONL format

## 🎯 What Happens Next (Automated)

The training will complete in ~45-50 minutes and:

1. Save final model to `witness-llama-3.2-3b-verified-10k/`
2. Generate training metrics
3. Model will be ready to test

## 🧪 Testing Plan (When You Return)

1. **Test the fine-tuned model**:
   ```bash
   cd /Users/nkennedy/proj/witness-evals
   source venv-mlx/bin/activate
   mlx_lm.generate \
     --model witness-llama-3.2-3b-verified-10k \
     --prompt "How do I attest a Go build with witness?" \
     --max-tokens 500
   ```

2. **Compare vs base model**:
   - Test same prompts on base Llama 3.2 3B
   - Compare quality, accuracy, completeness

3. **Validate generated policies**:
   - Extract policy JSON from model outputs
   - Validate with `jq`
   - Test Rego syntax

4. **Deploy with Ollama** (easy inference):
   ```bash
   # Convert to Ollama format
   ollama create witness-expert-verified \
     -f Modelfile-verified
   ```

## 📈 Progress Tracking

To check progress:
```bash
# Check training output
tail -f /tmp/training-verified.log

# Check iteration count
ls -lt witness-llama-3.2-3b-verified-10k/*.safetensors

# Monitor progress
watch -n 60 'ls -lt witness-llama-3.2-3b-verified-10k/ | head -5'
```

## Summary for User

When you return in ~1 hour:

✅ **10,000 verified examples generated** (100% success)
✅ **Committed to GitHub**
🔄 **Training in progress** (~45-50 min total)
📊 **Expected completion**: ~45 minutes from start
🎯 **Next step**: Test the fine-tuned model

Everything is running automatically. The model will be ready to test when you return!

---

**Training Command**:
```bash
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/verified \
  --num-layers 16 \
  --batch-size 4 \
  --iters 500 \
  --adapter-path ./witness-llama-3.2-3b-verified-10k
```

**Background Process ID**: d4051c
