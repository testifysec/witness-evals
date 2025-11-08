# Witness Evals - Training Dataset for Witness Attestation Framework

This repository contains a comprehensive training dataset for fine-tuning large language models to become experts in the [Witness](https://github.com/in-toto/go-witness) supply chain attestation framework.

## Overview

The dataset is designed to train models to:

1. **Instrument CI/CD pipelines** with `witness run` commands
2. **Create policy documents** for attestation verification
3. **Write Rego policies** for all attestors in go-witness
4. **Design multi-step workflows** with cross-step validation
5. **Handle security scenarios** including tampering detection and policy enforcement

## Dataset Structure

```
witness-evals/
├── data/
│   ├── attestors/           # Per-attestor training examples
│   │   ├── commandrun.jsonl # Command execution attestor
│   │   ├── git.jsonl        # Git repository attestor
│   │   ├── environment.jsonl
│   │   └── material-product.jsonl
│   ├── policies/            # Policy creation examples
│   │   └── policy-creation.jsonl
│   ├── workflows/           # Multi-step pipeline examples
│   │   └── ci-cd-workflows.jsonl
│   └── security/            # Attack/defense scenarios
├── scripts/
│   ├── generate_dataset.py  # Generate training data
│   └── validate_dataset.py  # Validate JSONL format
└── docs/
    └── FINE_TUNING_GUIDE.md
```

## Dataset Format

All training examples follow the OpenAI fine-tuning format (JSONL with messages):

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are an expert in the Witness supply chain attestation framework..."
    },
    {
      "role": "user",
      "content": "How do I attest a Go build with commandrun tracking?"
    },
    {
      "role": "assistant",
      "content": "Here's how to attest a Go build...\n\n```bash\nwitness run --step build...\n```"
    }
  ]
}
```

## Current Dataset Stats

- **Total examples**: 22
- **Attestors covered**: commandrun, git, environment, material, product
- **Policy examples**: 3
- **Workflow examples**: 2

### Coverage by Category

| Category | Examples | Description |
|----------|----------|-------------|
| commandrun | 6 | Command execution, tracing, exit code validation |
| git | 5 | Repository attestation, branch validation, signatures |
| environment | 3 | System info, env vars, hostname restrictions |
| material-product | 3 | Input/output files, cross-step validation |
| policies | 3 | Policy document structure, multi-step, Rego integration |
| workflows | 2 | GitHub Actions, container builds |

## Quick Start

### 1. Generate Dataset

```bash
python3 scripts/generate_dataset.py
```

### 2. Validate Dataset

```bash
python3 scripts/validate_dataset.py
```

### 3. Fine-Tune a Model

See [docs/FINE_TUNING_GUIDE.md](docs/FINE_TUNING_GUIDE.md) for detailed instructions on fine-tuning with:
- Llama 3
- Mistral
- Other open-source models

## Adding More Examples

To expand the dataset:

1. **Edit `scripts/generate_dataset.py`**:
   - Add new `generate_*_examples()` methods
   - Cover additional attestors (aws, gitlab, github, oci, sbom, etc.)
   - Add security/adversarial scenarios

2. **Regenerate**:
   ```bash
   python3 scripts/generate_dataset.py
   ```

3. **Validate**:
   ```bash
   python3 scripts/validate_dataset.py
   ```

## Attestors to Add

The following attestors from go-witness need examples:

- [ ] aws-iid (AWS Instance Identity)
- [ ] aws-codebuild
- [ ] gcp-iit (GCP Identity Token)
- [ ] github (GitHub Actions)
- [ ] gitlab (GitLab CI)
- [ ] jenkins
- [ ] docker
- [ ] oci (Container images)
- [ ] sbom (Software Bill of Materials)
- [ ] vex (Vulnerability Exploitability eXchange)
- [ ] sarif (Static Analysis)
- [ ] maven
- [ ] lockfiles
- [ ] k8smanifest
- [ ] secretscan
- [ ] system-packages
- [ ] slsa (SLSA Provenance)
- [ ] omnitrail
- [ ] jwt
- [ ] link (in-toto link)
- [ ] policyverify

## Contributing

To contribute examples:

1. Add examples to appropriate category in `generate_dataset.py`
2. Follow the existing format (system + user + assistant messages)
3. Include:
   - Complete `witness run`/`witness verify` commands
   - Rego policy examples
   - Explanations of captured fields
4. Run validation before submitting
5. Ensure no sensitive data in examples

## Model Training Guidelines

### Recommended Hyperparameters

For Llama 3 / Mistral fine-tuning:

```yaml
base_model: meta-llama/Llama-3-8B
learning_rate: 2e-5
batch_size: 4
num_epochs: 3
warmup_steps: 100
gradient_accumulation_steps: 4
max_seq_length: 2048
```

### Evaluation

After fine-tuning, evaluate the model on:

1. **Accuracy**: Can it generate correct witness commands?
2. **Policy creation**: Valid JSON policy documents?
3. **Rego syntax**: Syntactically correct Rego policies?
4. **Completeness**: All required flags included?
5. **Security**: Does it recommend secure practices?

## License

Apache 2.0 - Same as go-witness

## References

- [Witness Documentation](https://github.com/in-toto/go-witness)
- [OpenAI Evals](https://github.com/openai/evals)
- [Fine-tuning Guide](docs/FINE_TUNING_GUIDE.md)
