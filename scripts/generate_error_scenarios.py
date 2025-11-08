#!/usr/bin/env python3
"""
Generate error scenario examples - what SHOULD FAIL

These teach the model:
1. What makes attestations fail
2. How Rego policies catch attacks
3. Common security violations
4. Troubleshooting failed verifications

Each example:
- Creates attestation that VIOLATES a policy
- Shows the Rego that catches it
- Explains WHY it fails
- Shows how to fix it

Target: 5,000 error scenario examples
"""

import json
import subprocess
import tempfile
from pathlib import Path
import base64

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Error scenarios based on supply chain attack research
ERROR_SCENARIOS = [
    {
        "name": "wrong_branch",
        "attestor": "git",
        "description": "Build from unauthorized branch",
        "user_question": "Why would witness verification fail if I build from a feature branch?",
        "policy_rego": """package git

import rego.v1

deny contains msg if {
    input.branch != "main"
    msg := sprintf("Must build from main branch, got: %s", [input.branch])
}""",
        "explanation": """Verification fails because the Rego policy enforces building only from the 'main' branch.

**Attack scenario prevented**: Attacker creating malicious code on a feature branch and trying to deploy it.

**Policy enforcement**:
```rego
input.branch != "main"  # Detects non-main branches
```

**How to fix**:
- Switch to main branch: `git checkout main`
- Or update policy to allow your branch
- Or merge feature to main first

**This is a security feature** - policies can restrict builds to specific branches to prevent unauthorized code."""
    },

    {
        "name": "dirty_working_directory",
        "attestor": "git",
        "description": "Uncommitted changes in working directory",
        "user_question": "Why does verification fail when I have uncommitted files?",
        "policy_rego": """package git

import rego.v1

deny contains msg if {
    count(input.status) > 0
    msg := "Working directory must be clean"
}""",
        "explanation": """Verification fails because the working directory has uncommitted changes.

**Attack scenario prevented**: Attacker modifying source code after commit but before build, leaving no git trail.

**Policy enforcement**:
```rego
count(input.status) > 0  # Detects modified/added/deleted files
```

**How to fix**:
- Commit your changes: `git add . && git commit -m "message"`
- Or stash them: `git stash`
- Or update policy to allow dirty working directory (not recommended)

**This is a security feature** - ensures builds are from committed code only."""
    },

    {
        "name": "build_failed",
        "attestor": "command-run",
        "description": "Command exited with non-zero code",
        "user_question": "Why does verification fail when my build command fails?",
        "policy_rego": """package commandrun

import rego.v1

deny contains msg if {
    input.exitcode != 0
    msg := sprintf("Build failed with exit code %d", [input.exitcode])
}""",
        "explanation": """Verification fails because the command exited with a non-zero exit code (failure).

**Policy enforcement**:
```rego
input.exitcode != 0  # Detects failed commands
```

**Common exit codes**:
- 0: Success
- 1: General failure
- 2: Misuse of command
- 127: Command not found

**How to fix**:
- Fix the build error
- Check stderr in attestation: `jq '.predicate.attestations[] | select(.type | contains("command-run")) | .attestation.stderr' attestation.json`
- Run command locally to debug

**Why this matters**: Failed builds shouldn't pass verification - you want to catch build failures."""
    },

    {
        "name": "unauthorized_signer",
        "attestor": "git",
        "description": "Attestation signed by unauthorized key",
        "user_question": "Why does verification fail with 'unauthorized functionary'?",
        "policy_rego": """# This is enforced by witness verify, not Rego
# The policy specifies which public keys are authorized""",
        "explanation": """Verification fails because the attestation was signed by a key not in the policy's functionaries list.

**Attack scenario prevented**: Attacker with stolen/different key trying to create fraudulent attestations.

**Policy structure**:
```json
{
  "publickeys": {
    "allowed-key-id": {
      "keyid": "sha256:abc123...",
      "key": "-----BEGIN PUBLIC KEY-----..."
    }
  },
  "steps": {
    "build": {
      "functionaries": [{
        "type": "publickey",
        "publickeyid": "allowed-key-id"
      }]
    }
  }
}
```

**How to fix**:
- Use the correct signing key
- Or add your key to policy's publickeys
- Extract key ID: `jq -r '.signatures[0].keyid' attestation.json`

**This is a critical security feature** - only authorized keys can create trusted attestations."""
    },

    {
        "name": "missing_ci_environment",
        "attestor": "environment",
        "description": "Not running in CI environment",
        "user_question": "Why does verification fail with 'Must run in CI environment'?",
        "policy_rego": """package environment

import rego.v1

deny contains msg if {
    not "CI" in input.variables
    msg := "Must run in CI environment"
}""",
        "explanation": """Verification fails because the CI environment variable is not set.

**Attack scenario prevented**: Attacker running builds on their local machine instead of trusted CI.

**Policy enforcement**:
```rego
not "CI" in input.variables  # Checks for CI env var
```

**How to fix**:
- Run in actual CI (GitHub Actions, GitLab CI, etc.)
- CI systems automatically set CI=true
- For local testing, temporarily remove this policy

**Why this matters**: Ensures builds only happen in controlled, auditable CI environments."""
    },

    {
        "name": "malicious_command",
        "attestor": "command-run",
        "description": "Unauthorized build command detected",
        "user_question": "Why does verification fail with 'Unauthorized build command'?",
        "policy_rego": """package commandrun

import rego.v1

approved_commands := {
    ["go", "build", "-o", "app"],
    ["make", "all"]
}

deny contains msg if {
    not input.cmd in approved_commands
    msg := sprintf("Unauthorized command: %v", [input.cmd])
}""",
        "explanation": """Verification fails because the command doesn't match the allowlist.

**Attack scenario prevented**: Attacker modifying CI to run malicious commands (data exfiltration, backdoors).

**Policy enforcement**:
```rego
not input.cmd in approved_commands  # Strict command allowlist
```

**Examples of blocked commands**:
- `["curl", "evil.com"]` - Data exfiltration
- `["rm", "-rf", "/"]` - Destructive
- `["wget", "malware.sh"]` - Malware download

**How to fix**:
- Use an approved build command
- Or add your command to the allowlist (if legitimate)

**This is a critical security feature** - prevents command injection attacks."""
    },
]

def create_error_qa(scenario: Dict) -> Dict:
    """Create Q/A for error scenario"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario['user_question']},
            {"role": "assistant", "content": scenario['explanation'] + f"\n\n**Policy that detects this**:\n```rego\n{scenario['policy_rego']}\n```"}
        ],
        "_metadata": {
            "scenario": scenario['name'],
            "attestor": scenario['attestor'],
            "error_type": "security_violation"
        }
    }

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/error_scenarios.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("Generating Error Scenario Examples")
    print("="*70)

    examples = []
    for scenario in ERROR_SCENARIOS:
        # Create 10 variations with different question phrasings
        base_qa = create_error_qa(scenario)
        examples.append(base_qa)

        # Add related questions
        related_questions = [
            f"How do I prevent {scenario['description']}?",
            f"What Rego policy detects {scenario['description']}?",
            f"Why is {scenario['description']} a security risk?",
        ]

        for q in related_questions:
            examples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": q},
                    {"role": "assistant", "content": scenario['explanation'] + f"\n\n**Detection policy**:\n```rego\n{scenario['policy_rego']}\n```"}
                ]
            })

    print(f"Base scenarios: {len(ERROR_SCENARIOS)}")
    print(f"Total examples: {len(examples)}")

    with open(output_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + '\n')

    print()
    print("="*70)
    print(f"✅ Generated {len(examples)} error scenario examples")
    print(f"   Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")
    print()
    print("Teaches model how to detect and prevent supply chain attacks!")

if __name__ == "__main__":
    main()
