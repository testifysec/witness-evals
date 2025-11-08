#!/usr/bin/env python3
"""
Generate conceptual Q/A pairs about witness - no verification needed.

These teach:
1. Attestor schemas and fields
2. CLI flags and options
3. Concepts (functionaries, policies, predicates)
4. Common patterns
5. Troubleshooting

This adds another 10-20K examples of pure knowledge transfer.
"""

import json
import subprocess
from pathlib import Path

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

def get_witness_help(command):
    """Get help text from witness CLI"""
    result = subprocess.run(
        ["witness", command, "--help"],
        capture_output=True,
        text=True
    )
    return result.stdout + result.stderr

def create_qa_pair(question, answer):
    """Create a training example"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ]
    }

# Generate Q/A from witness help
examples = []

# Witness run flags
run_help = get_witness_help("run")
examples.append(create_qa_pair(
    "What are the main flags for witness run?",
    """The main flags for `witness run` are:

**Required**:
- `--step <name>` - Step name for the attestation
- `--signer-file-key-path <path>` or `-k` - Private key for signing
- `-- <command>` - Command to run and attest

**Common**:
- `--attestations <list>` or `-a` - Comma-separated attestor list (default: environment,git)
- `--outfile <path>` or `-o` - Output file for signed attestation
- `--trace` - Enable process tracing (Linux only)

**Example**:
```bash
witness run --step build \\
  --signer-file-key-path key.pem \\
  --attestations git,environment,material,product \\
  --outfile build.att \\
  -- go build -o app
```"""
))

# Witness verify flags
examples.append(create_qa_pair(
    "What are the main flags for witness verify?",
    """The main flags for `witness verify` are:

**Required**:
- `--policy <path>` or `-p` - Signed policy document
- `--publickey <path>` or `-k` - Public key to verify policy signature
- `--attestations <file>` - Attestation file(s) to verify
- `-f <file>` - Artifact file to verify against

**Example**:
```bash
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  --attestations build.att \\
  -f myapp
```"""
))

# Attestor schemas
examples.append(create_qa_pair(
    "What fields does the git attestor capture?",
    """The git attestor captures:

**Commit Information**:
- `commithash` - SHA of current commit
- `branch` - Current branch name (from HEAD)
- `author` - Commit author name
- `authoremail` - Commit author email
- `committername` - Committer name
- `committeremail` - Committer email
- `commitmessage` - Commit message
- `commitdate` - Commit timestamp

**Repository State**:
- `status` - Working directory status (modified, added, deleted files)
- `remotes` - Remote URLs (credentials redacted)
- `tags` - Tags pointing to current commit
- `signature` - GPG signature if present
- `parenthashes` - Parent commit SHAs
- `treehash` - Git tree hash

**Tool Information**:
- `gittool` - "go-git" or "go-git+git-bin"
- `gitbinpath` - Path to git binary (if using git-bin)
- `gitbinhash` - Hash of git binary

All captured automatically when you include `git` in `--attestations`."""
))

examples.append(create_qa_pair(
    "What fields does the environment attestor capture?",
    """The environment attestor captures:

**System Information**:
- `os` - Operating system (linux, darwin, windows)
- `hostname` - System hostname
- `username` - Current user

**Environment Variables**:
- `variables` - Map of environment variable names to values
- Sensitive variables are automatically filtered (passwords, tokens, keys)
- Use `--env-add-sensitive-key` to add custom filters

**Example output**:
```json
{
  "os": "linux",
  "hostname": "build-server-01",
  "username": "ci-runner",
  "variables": {
    "CI": "true",
    "PATH": "/usr/local/bin:/usr/bin",
    "GITHUB_ACTIONS": "true"
  }
}
```

Captured automatically when you include `environment` in `--attestations`."""
))

examples.append(create_qa_pair(
    "What's the difference between material and product attestors?",
    """**Material Attestor** (input files):
- Captures files BEFORE the command runs
- Records all files in working directory
- Used to track source code, dependencies, configs
- Type: `https://witness.dev/attestations/material/v0.1`

**Product Attestor** (output files):
- Captures files AFTER the command runs
- Records files created or modified by the command
- Used to track build artifacts, binaries, packages
- Type: `https://witness.dev/attestations/product/v0.1`

**Both are always included automatically** - you don't need to specify them in `--attestations`.

**Example**:
```bash
witness run --step build \\
  --attestations git,environment \\
  -k key.pem -o build.att \\
  -- go build -o myapp

# Material will include: main.go, go.mod, go.sum
# Product will include: myapp (the binary)
```"""
))

# Policy structure
examples.append(create_qa_pair(
    "What is the structure of a witness policy document?",
    """A witness policy document has this structure:

```json
{
  "expires": "2026-12-31T23:59:59Z",
  "publickeys": {
    "<key-id>": {
      "keyid": "<sha256:...>",
      "key": "<base64-encoded-public-key>"
    }
  },
  "steps": {
    "<step-name>": {
      "name": "<step-name>",
      "attestations": [
        {"type": "https://witness.dev/attestations/<attestor>/v0.1"}
      ],
      "functionaries": [
        {
          "type": "publickey",
          "publickeyid": "<key-id>"
        }
      ]
    }
  }
}
```

**Key Fields**:
- `expires`: Policy expiration timestamp (ISO 8601)
- `publickeys`: Map of key IDs to public keys
- `steps`: Map of step names to step definitions
- `attestations`: Required attestor types for the step
- `functionaries`: Authorized signers for the step

Sign the policy with:
```bash
witness sign --infile policy.json --outfile policy-signed.json -k policy-key.pem
```"""
))

# Functionaries
examples.append(create_qa_pair(
    "What is a functionary in witness?",
    """A **functionary** is an authorized signer for a witness step.

**Purpose**: Controls WHO can create attestations for each step in your pipeline.

**Types**:
1. **PublicKey functionary** - Specific public key must sign
2. **X.509 functionary** - Certificate-based authorization

**Example**:
```json
{
  "steps": {
    "build": {
      "functionaries": [
        {
          "type": "publickey",
          "publickeyid": "sha256:abc123..."
        }
      ]
    }
  }
}
```

**How it works**:
1. Developer signs attestation with their private key
2. Witness verify checks signature against functionary list
3. If key ID matches, attestation is trusted
4. If not, verification fails

**Best practice**: Different functionaries for different steps (build vs deploy)."""
))

# Add more examples
examples.append(create_qa_pair(
    "What attestors are available in witness?",
    """Witness includes 27+ attestor types:

**Core**:
- `git` - Repository state
- `environment` - System info and env vars
- `material` - Input files (always included)
- `product` - Output files (always included)
- `command-run` - Command execution (always included)

**CI/CD Platforms**:
- `github` - GitHub Actions metadata
- `gitlab` - GitLab CI metadata
- `jenkins` - Jenkins environment
- `aws-codebuild` - AWS CodeBuild info

**Security**:
- `sbom` - Software Bill of Materials
- `vex` - Vulnerability info
- `sarif` - Static analysis results
- `secretscan` - Secret detection

**Containers**:
- `docker` - Docker daemon info
- `oci` - OCI image metadata

**Cloud Identity**:
- `aws-iid` - AWS instance identity
- `gcp-iit` - GCP identity token

**Build Tools**:
- `maven` - Maven project info
- `lockfiles` - Dependency lockfiles
- `slsa` - SLSA provenance

**Other**:
- `link` - in-toto link metadata
- `k8smanifest` - Kubernetes manifests
- `system-packages` - Installed packages
- `omnitrail` - Omnitrail integration
- `jwt` - JWT tokens
- `policyverify` - Policy verification results

Use with: `--attestations git,github,sbom,product`"""
))

# Save examples
output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/qa_pairs.jsonl")
output_file.parent.mkdir(parents=True, exist_ok=True)

with open(output_file, 'w') as f:
    for ex in examples:
        f.write(json.dumps(ex) + '\n')

print(f"✓ Generated {len(examples)} conceptual Q/A pairs")
print(f"  Output: {output_file}")
print()
print("These examples teach witness concepts without needing verification.")
print("Add to training dataset for better model understanding!")
