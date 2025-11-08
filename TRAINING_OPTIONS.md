# Training Options for Witness Expert Model

You have several options for fine-tuning, depending on your needs:

## Option 1: OpenAI API (Easiest, Small Cost)

**Pros**: Dead simple, fast, production-ready
**Cons**: Costs ~$1-2 for this dataset, requires API key
**Time**: 10-20 minutes

```bash
# Install OpenAI SDK
pip3 install --user --break-system-packages openai

# Set API key
export OPENAI_API_KEY='sk-...'

# Run fine-tuning
python3 finetune_openai.py
```

## Option 2: Ollama + Local Model (Free, Local)

**Pros**: Free, completely local, easy
**Cons**: No true fine-tuning (uses model customization), requires manual setup
**Time**: 5 minutes

```bash
# Pull a small model
ollama pull llama3.2:3b

# Create custom model with system prompt
cat > Modelfile <<EOF
FROM llama3.2:3b

SYSTEM """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
EOF

# Create the model
ollama create witness-expert -f Modelfile

# Test it
ollama run witness-expert "How do I attest a Go build with witness?"
```

**Note**: This doesn't truly fine-tune, but gives the model context about Witness.

## Option 3: MLX (Apple Silicon, Free, Local)

**Pros**: Free, fast on M4 Max, true fine-tuning
**Cons**: Requires Python 3.9-3.12 (you have 3.14)
**Time**: 15-30 minutes

```bash
# Install Python 3.12 via Homebrew
brew install python@3.12

# Create venv with Python 3.12
/opt/homebrew/bin/python3.12 -m venv venv-mlx
source venv-mlx/bin/activate

# Install MLX
pip install mlx mlx-lm

# Run fine-tuning
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/train.jsonl \
  --valid-data data/val.jsonl \
  --lora-layers 16 \
  --batch-size 2 \
  --iters 100 \
  --learning-rate 2e-5 \
  --adapter-path ./witness-llama-3.2-3b-lora-mlx
```

## Option 4: Hugging Face Transformers (Free, Local, GPU/CPU)

**Pros**: Free, flexible, works on any hardware
**Cons**: Slow on CPU, requires more setup
**Time**: 1-3 hours on M4 Max

```bash
# Install dependencies
pip3 install --user --break-system-packages torch transformers datasets accelerate peft

# Run training
python3 train_witness_model.py
```

## Recommendation for Quick Start

Given your setup (M4 Max, no GPU):

### Best Option: Ollama Custom Model (5 minutes)

This won't fine-tune but will give you a working Witness expert immediately:

```bash
cd /Users/nkennedy/proj/witness-evals

# Create Modelfile with Witness expertise
cat > Modelfile <<'EOF'
FROM llama3.2:3b

SYSTEM """You are an expert in the Witness supply chain attestation framework.

Core Commands:
- witness run: Execute and attest commands
- witness verify: Verify attestations against policies

Common Attestors:
- git: Repository state
- commandrun: Command execution with optional tracing
- environment: System info and env vars
- material: Input files
- product: Output files
- oci: Container images
- github: GitHub Actions
- gitlab: GitLab CI

Policy Structure:
{
  "expires": "2025-12-31T23:59:59Z",
  "publickeys": {...},
  "steps": {
    "build": {
      "name": "build",
      "attestations": [...],
      "functionaries": [...]
    }
  }
}

Rego Validation:
package attestor_name
import rego.v1
deny contains msg if {
  # validation rules
}

You help users:
1. Write witness run commands
2. Create policy documents
3. Write Rego validation rules
4. Design multi-step workflows
5. Troubleshoot attestation issues
"""

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
EOF

# Create the model
ollama create witness-expert -f Modelfile

echo "✓ Witness Expert model created!"
echo ""
echo "Test it:"
echo "  ollama run witness-expert 'How do I attest a Go build?'"
```

### If You Want True Fine-Tuning

The easiest true fine-tuning options:

1. **OpenAI API** (~$1-2, fastest, production-ready)
2. **Install Python 3.12 + MLX** (free, local, 30 mins)

Would you like me to set up one of these options?
