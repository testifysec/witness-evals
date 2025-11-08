#!/usr/bin/env python3
"""Generate troubleshooting Q/A from common witness errors"""

import json
import subprocess
from pathlib import Path

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

TROUBLESHOOTING_QA = [
    {
        "q": "Why do I get 'unknown flag: --key'?",
        "a": """The correct flag is `--signer-file-key-path` or `-k`, not `--key`.

**Correct usage**:
```bash
witness run --step build \\
  --signer-file-key-path key.pem \\
  -o build.att \\
  -- go build
```

**Short form**:
```bash
witness run --step build -k key.pem -o build.att -- go build
```"""
    },
    {
        "q": "How do I fix 'failed to load any signers'?",
        "a": """This error means witness couldn't load a signing key. Check:

1. **Key file exists**: `ls -la key.pem`
2. **Key file permissions**: `chmod 600 key.pem`
3. **Key format is correct**: Ed25519 or RSA

**Generate Ed25519 key**:
```bash
openssl genpkey -algorithm ed25519 -out key.pem
```

**Generate RSA key**:
```bash
openssl genrsa -out key.pem 2048
```

Then use with `-k key.pem`"""
    },
    {
        "q": "What does 'attestor not found' mean?",
        "a": """Attestor name is incorrect. Use exact name from `witness attestors list`.

**Common mistakes**:
- `commandrun` → Correct: `command-run` (with hyphen)
- `aws-iid` → Correct: `aws` (no -iid suffix)

**Check available attestors**:
```bash
witness attestors list
```

**Correct usage**:
```bash
witness run --step build -a git,environment,material,product -k key.pem -o build.att -- go build
```"""
    },
    {
        "q": "Why does verification fail with 'no verifiers present to validate against collection verifiers'?",
        "a": """This usually means the public key in your policy doesn't match the signing key.

**Debug steps**:

1. **Extract key ID from attestation**:
```bash
jq -r '.signatures[0].keyid' build.att
```

2. **Check policy has that key ID**:
```bash
jq '.publickeys | keys' policy.json
```

3. **Ensure key IDs match**:
The `publickeyid` in functionaries must match a key in `publickeys`.

**Fix**: Regenerate policy with correct key ID extracted from attestation."""
    },
    {
        "q": "How do I debug Rego policy failures?",
        "a": """Test Rego policies with OPA before adding to witness:

**1. Save Rego to file**:
```bash
cat > policy.rego <<'EOF'
package git
import rego.v1
deny contains msg if {
    input.branch != "main"
    msg := "Wrong branch"
}
EOF
```

**2. Create test input from attestation**:
```bash
jq '.predicate.attestations[] | select(.type | contains("git")) | .attestation' build.att > test-input.json
```

**3. Test with OPA**:
```bash
opa eval -d policy.rego -i test-input.json 'data.git.deny'
```

**4. Check output**:
- Empty result `{}` - policy passed
- Has values - shows denial messages

This lets you test Rego before running full witness verify."""
    },
]

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/troubleshooting.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    examples = []
    for item in TROUBLESHOOTING_QA:
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": item['q']},
                {"role": "assistant", "content": item['a']}
            ]
        })

    with open(output_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + '\n')

    print(f"✓ Generated {len(examples)} troubleshooting examples")
    print(f"  Output: {output_file}")

if __name__ == "__main__":
    main()
