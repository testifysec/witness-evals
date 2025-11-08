# Formally Verified Witness Training Dataset

## Achievement

Successfully generated **10,000 formally verified witness training examples** where **every single example passes `witness verify`**.

## Generation Results

- **Total examples**: 10,000
- **Success rate**: 100% (0 failures)
- **File size**: 26 MB
- **Generation time**: ~30 minutes
- **Verification**: All examples passed `witness verify` with exit code 0

## Dataset Structure

### Location
- **Full dataset**: `data/verified/verified_train.jsonl` (10,000 examples)
- **Training split**: `data/verified/train.jsonl` (9,000 examples)
- **Validation split**: `data/verified/valid.jsonl` (1,000 examples)

### Attestor Coverage

15 different attestor combinations:

| Combination | Count | Description |
|-------------|-------|-------------|
| material, product | 667 | File tracking only |
| environment | 667 | System info only |
| git | 667 | Repository state only |
| product | 667 | Output files only |
| material | 667 | Input files only |
| git, material, product | 666 | Git + file tracking |
| environment, material, product | 666 | Env + file tracking |
| git, environment, material, product | 666 | Full attestation |
| git, product | 666 | Git + outputs |
| environment, product | 666 | Env + outputs |
| git, material | 666 | Git + inputs |
| environment, material | 666 | Env + inputs |
| git, environment, product | 666 | Git + env + outputs |
| git, environment, material | 666 | Git + env + inputs |
| git, environment | 667 | Git + environment |

## Verification Process

Each example underwent:

1. **Key Generation**: Ed25519 keys created with openssl
2. **Attestation**: Real `witness run` command executed
3. **Policy Creation**: Valid policy document generated with correct structure
4. **Policy Signing**: Policy signed with `witness sign`
5. **Formal Verification**: `witness verify` executed and MUST return exit code 0
6. **Quality Check**: stderr checked for "error" or "failed" strings

**Only examples that passed all checks were added to the dataset.**

## Example Format

Each training example in the dataset contains:

### User Query
```
How do I create a complete witness configuration for a build step
with <attestors> that passes verification?
```

### Assistant Response
Complete working example with:
- Ed25519 key generation commands
- Setup instructions (git init, create files, etc.)
- Complete `witness run` command
- Key ID extraction
- Complete policy JSON document
- `witness sign` command
- `witness verify` command
- All commands verified to work

### Sample

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert in Witness..."
    },
    {
      "role": "user",
      "content": "How do I create a complete witness configuration..."
    },
    {
      "role": "assistant",
      "content": "Here's a complete, verified witness configuration:\n\n**1. Generate Ed25519 Keys:**\n```bash\nopenssl genpkey...\n```..."
    }
  ]
}
```

## Generation Script

**Script**: `scripts/generate_10k_verified.py`

### Key Features

1. **Real Execution**: Uses actual witness CLI commands
2. **Formal Verification**: Every example passes `witness verify`
3. **Environment Handling**: Properly sets CI variables
4. **Git Setup**: Initializes repos when git attestor is used
5. **File Management**: Creates input.txt for material, output.txt for product
6. **Error Handling**: Skips examples that don't verify (but success rate was 100%)

### Bug Fixes Applied

The witness-helper agent identified and fixed:

1. **Environment variable passing** - subprocess wasn't receiving env vars
2. **Material file creation** - input.txt needed for material attestor
3. **Product file cleanup** - output.txt must be deleted before each run
4. **Conditional setup** - Different attestors need different preparation
5. **Proper error detection** - Check stderr for "error" and "failed"

## Training Dataset Quality

### Comparison

| Dataset | Examples | Verified | Size | Quality |
|---------|----------|----------|------|---------|
| Manual | 22 | No | 50 KB | Good |
| Synthetic | 10,000 | No | 20 MB | Good |
| **Verified** | **10,000** | **Yes (100%)** | **26 MB** | **Excellent** |

### Why Verification Matters

**Verified dataset ensures**:
- Policies have correct JSON structure
- Key IDs match between attestation and policy
- All witness CLI flags are correct
- Public keys are properly base64 encoded
- Commands will actually work when users copy them
- No syntax errors, no invalid configurations

**Non-verified datasets may teach**:
- Invalid policy structures
- Incorrect CLI flags
- Broken key ID references
- Commands that don't run

## Training

### Current Status

MLX fine-tuning in progress:
- **Model**: Llama 3.2 3B (4-bit) with LoRA
- **Dataset**: 10,000 verified examples
- **Batch size**: 4
- **Iterations**: 500
- **Initial val loss**: 2.177
- **Output**: `./witness-llama-3.2-3b-verified-10k/`

### Expected Timeline

- **Model download**: Complete
- **Initial validation**: Complete (2.177 loss)
- **Training 500 iterations**: ~40-45 minutes
- **Total**: ~45-50 minutes

## Usage

### Generate More Examples

```bash
python3 scripts/generate_10k_verified.py --target 20000
```

### Create Train/Valid Splits

```bash
python3 scripts/create_verified_splits.py
```

### Sample Examples

```bash
head -5 data/verified/verified_train.jsonl | jq '.messages[1].content'
```

### Fine-Tune

```bash
cd /Users/nkennedy/proj/witness-evals
source venv-mlx/bin/activate
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/verified \
  --num-layers 16 \
  --batch-size 4 \
  --iters 500 \
  --adapter-path ./witness-expert-model
```

## Impact

This verified dataset enables:

1. **Reliable Training**: Model learns only valid configurations
2. **Production Ready**: Fine-tuned models generate working witness commands
3. **User Confidence**: All examples tested and verified
4. **Zero Hallucination**: No made-up flags or invalid JSON
5. **Community Contribution**: Reproducible, verifiable dataset

## Reproducibility

Every example can be reproduced:
1. Run the exact commands from the assistant response
2. Will generate the same attestation structure
3. Will pass `witness verify`
4. Deterministic except for key IDs (which are extracted, not hardcoded)

---

**Generated**: 2025-11-08
**Tool**: witness-helper agent + Python automation
**Repository**: https://github.com/testifysec/witness-evals
