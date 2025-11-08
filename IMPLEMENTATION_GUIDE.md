# 100K Diverse Witness Training Examples - Implementation Guide

## Quick Start

This guide provides **executable commands** to generate 100K diverse, formally verified witness training examples.

---

## Prerequisites Check

```bash
cd /Users/nkennedy/proj/witness-evals

# Check witness is installed
witness version

# Check Go
go version

# Check Node.js
node --version && npm --version

# Check Python
python3 --version

# Check OpenSSL
openssl version
```

---

## Phase 1: Setup (30 minutes)

### Step 1.1: Install SBOM Tools

```bash
# Run the setup script
./scripts/setup_sbom_tools.sh
```

This installs:
- **Syft** - Universal SBOM generator
- **CycloneDX** - Node.js SBOM generator
- **CycloneDX** - Python SBOM generator

**Verification**:
```bash
syft version
```

### Step 1.2: Test Project Templates

```bash
# Test that all language templates work
python3 scripts/project_templates.py
```

Expected output:
```
Testing go template...
  ✓ Created: ['go.mod', 'main.go', 'go.sum']
  ✓ Build command: go build -o app main.go
Testing node template...
  ✓ Created: ['package.json', 'index.js', 'package-lock.json', 'node_modules']
  ✓ Build command: npm run build || echo 'No build script'
...
```

### Step 1.3: Verify Current 10K Dataset

```bash
# Check existing dataset
wc -l data/verified/*.jsonl

# Sample an example
head -1 data/verified/train.jsonl | jq .
```

---

## Phase 2: Generate 20K Diverse Dataset (TEST RUN)

Before generating 100K, let's validate the approach with 20K diverse examples.

### Why Start with 20K?

1. **Validates diversity strategy** - Ensures attestor combinations work
2. **Tests SBOM integration** - Confirms syft/cyclonedx work
3. **Measures success rate** - Identifies issues early
4. **Faster iteration** - 2-3 hours vs 12+ hours

### Step 2.1: Create Enhanced Generator

The enhanced generator is already created at `scripts/generate_enhanced_verified.py`. Let's review its features:

```bash
python3 scripts/generate_enhanced_verified.py --help
```

**Key Features**:
- 11 attestor types (git, environment, material, product, commandrun, link, lockfiles, sbom, maven, secretscan, sarif)
- 10 step names (build, test, package, deploy, scan, compile, lint, security-check, analyze, verify)
- 20 command patterns (real go/npm/python/make commands)
- 15 question phrasings
- 6 Rego policy types (none, git, environment, product, commandrun, combined)
- Real SBOM generation for Go, Node, Python, Java, Rust
- Real lockfile detection

### Step 2.2: Run 20K Generation

```bash
# Create output directory
mkdir -p data/diverse-20k

# Generate 20K diverse examples (2-3 hours)
python3 scripts/generate_enhanced_verified.py \
  --target 20000 \
  --output data/diverse-20k/diverse_train.jsonl \
  --parallel 8

# Monitor progress (in another terminal)
watch -n 30 'wc -l data/diverse-20k/diverse_train.jsonl'
```

**Expected output**:
```
🎯 Generating 20,000 diverse examples...
📊 Attestors: 11 (Tier 1 + Tier 2)
📊 Potential combinations: 1,485
📊 Step names: 10
📊 Command patterns: 20
📊 Question templates: 15
📊 Policy types: 6
📊 Languages: 5 (for SBOM)

Progress: 100/20000 (2 failed, 98% success rate)
Progress: 200/20000 (5 failed, 97.5% success rate)
...
```

### Step 2.3: Analyze Diversity

```bash
# Analyze what was generated
python3 scripts/analyze_diversity.py data/diverse-20k/diverse_train.jsonl
```

**Expected metrics**:
```
Diversity Analysis:
==================
Total examples: 20,000

Attestor Combinations:
  Unique combinations: 847 (of 1,485 possible)
  Most common: git,environment,material,product (234 examples)
  Least common: sbom,sarif (12 examples)

Step Names:
  build: 2,034
  test: 1,998
  package: 2,001
  deploy: 1,987
  ...

Command Patterns:
  go build: 1,543
  npm install: 1,489
  python -m pytest: 1,501
  ...

Policy Types:
  none: 6,789 (33.9%)
  git: 2,543 (12.7%)
  environment: 2,498 (12.5%)
  product: 2,501 (12.5%)
  commandrun: 2,489 (12.4%)
  combined: 3,180 (15.9%)

Languages (SBOM):
  go: 1,234
  node: 1,198
  python: 1,245
  java: 1,187
  rust: 1,201
```

### Step 2.4: Create Train/Valid Splits

```bash
python3 scripts/create_verified_splits.py \
  --input data/diverse-20k/diverse_train.jsonl \
  --train-ratio 0.9

# Creates:
#   data/diverse-20k/train.jsonl (18,000 examples)
#   data/diverse-20k/valid.jsonl (2,000 examples)
```

---

## Phase 3: Train on 20K Diverse Dataset

### Step 3.1: Activate MLX Environment

```bash
source venv-mlx/bin/activate
```

### Step 3.2: Run Training

```bash
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/diverse-20k \
  --num-layers 32 \
  --batch-size 8 \
  --iters 1000 \
  --learning-rate 1e-5 \
  --steps-per-eval 100 \
  --val-batches 25 \
  --adapter-path ./witness-llama-3.2-3b-diverse-20k \
  --save-every 200
```

**Training Parameters**:
- **Model**: Llama 3.2 3B (4-bit quantized)
- **Method**: LoRA (Low-Rank Adaptation)
- **Batch size**: 8 (larger for diverse data)
- **Iterations**: 1000
- **Learning rate**: 1e-5
- **Dataset**: 18,000 train, 2,000 validation

**Expected timeline**: 6-8 hours on M4 Max

**Expected loss trajectory**:
```
Iter 0: Val loss 2.177 (baseline)
Iter 100: Val loss 0.65
Iter 200: Val loss 0.48
Iter 400: Val loss 0.38
Iter 600: Val loss 0.32
Iter 800: Val loss 0.28
Iter 1000: Val loss 0.25-0.27 (target!)
```

### Step 3.3: Monitor Training

```bash
# In another terminal
watch -n 60 'ls -lt witness-llama-3.2-3b-diverse-20k/*.safetensors | head -5'
```

---

## Phase 4: Evaluate Results

### Step 4.1: Test Model Quality

```bash
# Test with diverse prompts
mlx_lm.generate \
  --model witness-llama-3.2-3b-diverse-20k \
  --prompt "How do I attest a Go build with git, sbom, and lockfiles?" \
  --max-tokens 800

mlx_lm.generate \
  --model witness-llama-3.2-3b-diverse-20k \
  --prompt "Create a witness policy with Rego for environment validation" \
  --max-tokens 600

mlx_lm.generate \
  --model witness-llama-3.2-3b-diverse-20k \
  --prompt "Show me a Node.js build attestation with SBOM generation" \
  --max-tokens 700
```

### Step 4.2: Compare vs 10K Model

```bash
# Test same prompt on both models
PROMPT="How do I create a witness configuration for a build step with git and environment attestors?"

echo "=== 10K Model ===" mlx_lm.generate \
  --model witness-llama-3.2-3b-verified-10k \
  --prompt "$PROMPT" \
  --max-tokens 500

echo "=== 20K Diverse Model ==="
mlx_lm.generate \
  --model witness-llama-3.2-3b-diverse-20k \
  --prompt "$PROMPT" \
  --max-tokens 500
```

**Evaluation criteria**:
- ✅ Generates valid JSON policies
- ✅ Uses correct witness CLI flags
- ✅ Handles diverse attestor combinations
- ✅ Includes SBOM generation when appropriate
- ✅ Adds Rego policies when requested
- ✅ Uses realistic command patterns

### Step 4.3: Quantitative Evaluation

```bash
# Test on 100 random prompts
python3 scripts/evaluate_model.py \
  --model witness-llama-3.2-3b-diverse-20k \
  --test-set data/diverse-20k/valid.jsonl \
  --num-samples 100
```

**Expected metrics**:
```
Evaluation Results (100 samples):
=================================

Valid JSON: 98/100 (98%)
Valid Rego: 47/50 (94% of those with Rego)
Correct attestor types: 96/100 (96%)
Correct CLI flags: 94/100 (94%)
SBOM generation present: 18/20 (90% of SBOM examples)
Lockfiles detection: 15/15 (100%)

Overall quality: 🟢 Excellent (95% accuracy)
```

---

## Phase 5: Scale to 100K (IF 20K IS SUCCESSFUL)

### Step 5.1: Review 20K Results

**Decision criteria**:
- ✅ Training loss < 0.30
- ✅ Model generates valid configs
- ✅ Diversity metrics look good
- ✅ Success rate > 95%

**If criteria met, proceed to 100K**:

```bash
# Generate 100K diverse examples (12-16 hours with 10-12 cores)
python3 scripts/generate_enhanced_verified.py \
  --target 100000 \
  --output data/diverse-100k/diverse_train.jsonl \
  --parallel 12

# Create splits
python3 scripts/create_verified_splits.py \
  --input data/diverse-100k/diverse_train.jsonl \
  --train-ratio 0.9

# Train (16-20 hours)
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/diverse-100k \
  --num-layers 32 \
  --batch-size 8 \
  --iters 2000 \
  --learning-rate 1e-5 \
  --steps-per-eval 100 \
  --val-batches 50 \
  --adapter-path ./witness-llama-3.2-3b-diverse-100k \
  --save-every 200
```

**Expected 100K results**:
- Val loss: **0.23-0.25** (vs 0.50 for 10K)
- Training time: 16-20 hours
- Model quality: Production-ready

---

## Phase 6: Production Deployment

### Step 6.1: Convert to Ollama Format

```bash
# Create Modelfile
cat > Modelfile-diverse <<EOF
FROM ./witness-llama-3.2-3b-diverse-20k
SYSTEM """You are a Witness expert trained on 20,000 diverse, formally verified examples covering:
- 11 attestor types (git, environment, material, product, commandrun, link, lockfiles, sbom, maven, secretscan, sarif)
- 5 programming languages (Go, Node.js, Python, Java, Rust)
- Real SBOM generation with syft and cyclonedx
- Rego policy validation
- Real-world CI/CD patterns

You help users:
- Create witness configurations that pass verification
- Generate SBOMs for different languages
- Write Rego policies for supply chain security
- Integrate witness into CI/CD pipelines

All your examples are formally verified to work."""
EOF

# Build Ollama model
ollama create witness-expert-diverse -f Modelfile-diverse

# Test
ollama run witness-expert-diverse "How do I attest a Python build with SBOM?"
```

### Step 6.2: Upload to Hugging Face (Optional)

```bash
# Install huggingface-cli
pip install huggingface_hub

# Login
huggingface-cli login

# Upload model
huggingface-cli upload \
  testifysec/witness-expert-llama-3.2-3b \
  ./witness-llama-3.2-3b-diverse-20k \
  --repo-type model
```

---

## Troubleshooting

### Issue: Syft not found

```bash
# Install via Homebrew
brew install syft

# Or via install script
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
```

### Issue: Generation success rate < 90%

Check logs for common failures:
```bash
grep "ERROR" generation.log | sort | uniq -c | sort -rn
```

Common issues:
- Go mod download failures → Check internet connection
- npm install timeouts → Increase timeout
- SBOM generation fails → Check syft installation

### Issue: Training loss not decreasing

Possible causes:
1. **Not enough diversity** - Check diversity analysis
2. **Learning rate too high** - Try 5e-6 instead of 1e-5
3. **Batch size too small** - Try batch_size=16
4. **Need more iterations** - Try 1500-2000 iterations

### Issue: Model generates invalid JSON

This usually means:
- Training loss too high (> 0.35)
- Not enough training iterations
- Need more diverse examples

Solution: Train longer or generate more examples

---

## Success Metrics

### 10K Baseline (CURRENT)
- Attestor combinations: 15
- Step names: 1
- Loss: **0.50**
- SBOM examples: 0
- Rego policies: 0

### 20K Diverse (TARGET)
- Attestor combinations: 800+
- Step names: 10
- Loss: **0.25-0.30**
- SBOM examples: 4,000+ (20%)
- Rego policies: 10,000+ (50%)

### 100K Diverse (STRETCH)
- Attestor combinations: 1,400+
- Step names: 10
- Loss: **0.23-0.25**
- SBOM examples: 20,000+ (20%)
- Rego policies: 50,000+ (50%)

---

## Timeline Summary

| Phase | Duration | Parallelizable | Blocking |
|-------|----------|----------------|----------|
| Setup | 30 min | No | Yes |
| Generate 20K | 2-3 hours | Yes (8 cores) | No |
| Train 20K | 6-8 hours | No | Yes |
| Evaluate | 30 min | No | Yes |
| Generate 100K | 12-16 hours | Yes (12 cores) | No |
| Train 100K | 16-20 hours | No | Yes |

**Total for 20K**: ~9-12 hours
**Total for 100K**: ~29-37 hours

---

## Next Steps

**Recommended approach**:

1. ✅ Run setup (30 min)
2. ✅ Generate 20K diverse examples (2-3 hours)
3. ✅ Analyze diversity to validate approach (10 min)
4. ✅ Train on 20K (6-8 hours)
5. ✅ Evaluate results (1 hour)
6. **IF SUCCESSFUL** → Scale to 100K
7. **IF NOT** → Iterate on diversity strategy

**Start now**:
```bash
cd /Users/nkennedy/proj/witness-evals
./scripts/setup_sbom_tools.sh
```
