#!/usr/bin/env python3
"""
Generate 10,000 formally verified witness training examples.

Each example:
1. Runs actual witness run -> creates attestation
2. Creates policy document
3. Signs policy with witness sign
4. Verifies with witness verify (MUST PASS)
5. Only adds to dataset if verification succeeds

This ensures 100% of training data teaches valid, working witness configurations.
"""

import json
import subprocess
import tempfile
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import base64

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Attestor scenarios to generate
ATTESTOR_COMBINATIONS = [
    ["git", "environment"],
    ["material", "product"],
    ["environment"],
    ["git"],
    ["product"],
    ["material"],
    ["git", "material", "product"],
    ["environment", "material", "product"],
    ["git", "environment", "material", "product"],
    ["git", "product"],
    ["environment", "product"],
    ["git", "material"],
    ["environment", "material"],
    ["git", "environment", "product"],
    ["git", "environment", "material"],
]


class VerifiedExampleGenerator:
    def __init__(self, output_file: Path):
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.success_count = 0
        self.fail_count = 0

    def run_command(self, cmd: List[str], cwd: Path, env=None) -> Tuple[bool, str, str]:
        """Run command and return (success, stdout, stderr)"""
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            env=env
        )
        return result.returncode == 0, result.stdout, result.stderr

    def create_keys(self, work_dir: Path) -> Tuple[Path, Path]:
        """Generate Ed25519 signing keys"""
        key_pem = work_dir / "key.pem"
        key_pub = work_dir / "pub.pem"

        # Generate private key
        subprocess.run([
            "openssl", "genpkey",
            "-algorithm", "ed25519",
            "-out", str(key_pem)
        ], check=True, capture_output=True)

        # Extract public key
        subprocess.run([
            "openssl", "pkey",
            "-in", str(key_pem),
            "-pubout",
            "-out", str(key_pub)
        ], check=True, capture_output=True)

        return key_pem, key_pub

    def init_git_repo(self, work_dir: Path):
        """Initialize git repository"""
        subprocess.run(["git", "init"], cwd=str(work_dir),
                      capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                      cwd=str(work_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"],
                      cwd=str(work_dir), capture_output=True, check=True)

        # Create initial commit
        test_file = work_dir / "test.txt"
        test_file.write_text("test\n")
        subprocess.run(["git", "add", "test.txt"],
                      cwd=str(work_dir), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"],
                      cwd=str(work_dir), capture_output=True, check=True)

    def generate_example(self, example_num: int, attestors: List[str]) -> bool:
        """Generate a single verified example"""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            step_name = "build"

            try:
                # Step 1: Create keys
                key_pem, key_pub = self.create_keys(work_dir)

                # Step 2: Init git if needed
                if "git" in attestors:
                    self.init_git_repo(work_dir)

                # Step 3: Set environment variables if needed
                env = os.environ.copy()
                if "environment" in attestors:
                    env["CI"] = "true"
                    env["BUILD_ID"] = str(example_num)

                # Step 4: Create material file if needed
                if "material" in attestors:
                    material_file = work_dir / "input.txt"
                    material_file.write_text("source data\n")

                # Step 5: Run witness attestation (creates artifact)
                artifact = work_dir / "output.txt"
                att_file = work_dir / "build.att"
                attestor_str = ",".join(attestors)

                # CRITICAL: Delete output.txt if exists (product attestor only captures NEW files)
                if artifact.exists():
                    artifact.unlink()

                # Build command based on whether material file exists
                if "material" in attestors:
                    bash_cmd = f"cat {work_dir}/input.txt > {artifact}"
                else:
                    bash_cmd = f"echo 'Building...' > {artifact}"

                success, stdout, stderr = self.run_command([
                    "witness", "run",
                    "--step", step_name,
                    "--signer-file-key-path", str(key_pem),
                    "--outfile", str(att_file),
                    "--attestations", attestor_str,
                    "--",
                    "bash", "-c", bash_cmd
                ], work_dir, env=env)

                if not success:
                    return False

                # Step 6: Extract key ID from attestation
                with open(att_file, 'r') as f:
                    att_data = json.load(f)

                key_id = att_data['signatures'][0]['keyid']

                # Step 7: Create policy
                with open(key_pub, 'rb') as f:
                    pub_key_b64 = base64.b64encode(f.read()).decode('ascii')

                attestation_types = [
                    {"type": f"https://witness.dev/attestations/{att}/v0.1"}
                    for att in attestors
                ]

                policy = {
                    "expires": "2026-12-31T23:59:59Z",
                    "steps": {
                        step_name: {
                            "name": step_name,
                            "attestations": attestation_types,
                            "functionaries": [
                                {
                                    "type": "publickey",
                                    "publickeyid": key_id
                                }
                            ]
                        }
                    },
                    "publickeys": {
                        key_id: {
                            "keyid": key_id,
                            "key": pub_key_b64
                        }
                    }
                }

                policy_file = work_dir / "policy.json"
                with open(policy_file, 'w') as f:
                    json.dump(policy, f, indent=2)

                # Step 8: Sign policy
                policy_signed = work_dir / "policy-signed.json"
                success, stdout, stderr = self.run_command([
                    "witness", "sign",
                    "--signer-file-key-path", str(key_pem),
                    "--infile", str(policy_file),
                    "--outfile", str(policy_signed)
                ], work_dir)

                if not success:
                    return False

                # Step 9: VERIFY with witness verify
                success, stdout, stderr = self.run_command([
                    "witness", "verify",
                    "--policy", str(policy_signed),
                    "--publickey", str(key_pub),
                    "--attestations", str(att_file),
                    "-f", str(artifact)
                ], work_dir)

                # Check if verification actually passed
                # NOTE: witness writes all output to stderr, so only check returncode
                if not success:
                    return False

                # Double-check for verification success message
                if "Verification succeeded" not in stderr:
                    return False

                # Step 10: Verification PASSED! Create training example
                attestor_list = ", ".join(attestors)
                policy_json = json.dumps(policy, indent=2)

                # Build setup sections based on attestors
                setup_sections = []

                # Git setup if needed
                if "git" in attestors:
                    setup_sections.append("""**Setup Git Repository:**
```bash
git init
git config user.email "test@example.com"
git config user.name "Test User"
echo "test" > test.txt
git add test.txt
git commit -m "initial commit"
```
""")

                # Environment setup if needed
                if "environment" in attestors:
                    setup_sections.append("""**Set Environment Variables:**
```bash
export CI=true
export BUILD_ID=12345
```
""")

                # Material file if needed
                if "material" in attestors:
                    setup_sections.append("""**Create Material File:**
```bash
echo "source data" > input.txt
```
""")
                    training_bash_cmd = "cat input.txt > output.txt"
                else:
                    training_bash_cmd = "echo 'Building...' > output.txt"

                setup_text = "".join(setup_sections)

                training_example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": f"How do I create a complete witness configuration for a {step_name} step with {attestor_list} attestors that passes verification?"
                        },
                        {
                            "role": "assistant",
                            "content": f"""Here's a complete, verified witness configuration:

**1. Generate Ed25519 Keys:**
```bash
openssl genpkey -algorithm ed25519 -out key.pem
openssl pkey -in key.pem -pubout -out pub.pem
```

{setup_text}**2. Run Witness Attestation:**
```bash
witness run --step {step_name} \\
  --signer-file-key-path key.pem \\
  --outfile build.att \\
  --attestations {attestor_str} \\
  -- bash -c "{training_bash_cmd}"
```

**3. Extract Key ID and Create Policy:**
```bash
KEYID=$(jq -r '.signatures[0].keyid' build.att)
PUBKEY_B64=$(base64 < pub.pem | tr -d '\\n')
```

**Policy Document:**
```json
{policy_json}
```

**4. Sign Policy:**
```bash
witness sign --signer-file-key-path key.pem \\
  --infile policy.json \\
  --outfile policy-signed.json
```

**5. Verify:**
```bash
witness verify \\
  --policy policy-signed.json \\
  --publickey pub.pem \\
  --attestations build.att \\
  -f output.txt
```

This configuration has been formally verified to pass witness verify."""
                        }
                    ]
                }

                # Append to JSONL file
                with open(self.output_file, 'a') as f:
                    f.write(json.dumps(training_example) + '\n')

                self.success_count += 1
                return True

            except Exception as e:
                self.fail_count += 1
                return False

    def generate_dataset(self, target: int = 10000):
        """Generate target number of verified examples"""
        print("=" * 80)
        print(f"Generating {target:,} Formally Verified Witness Examples")
        print("=" * 80)
        print(f"Output: {self.output_file}")
        print()

        for i in range(1, target + 1):
            if i % 100 == 1 or i <= 10:
                print(f"Progress: {i:,}/{target:,} (Success: {self.success_count:,}, Failed: {self.fail_count:,})")

            # Cycle through attestor combinations
            attestors = ATTESTOR_COMBINATIONS[i % len(ATTESTOR_COMBINATIONS)]

            if self.generate_example(i, attestors):
                if i <= 10:
                    print(f"  ✅ Example {i} verified: {', '.join(attestors)}")
            else:
                if i <= 10:
                    print(f"  ❌ Example {i} failed: {', '.join(attestors)}")

        print()
        print("=" * 80)
        print("Generation Complete!")
        print("=" * 80)
        print(f"Total attempts: {target:,}")
        print(f"Successful: {self.success_count:,}")
        print(f"Failed: {self.fail_count:,}")
        print(f"Success rate: {(self.success_count * 100 / target):.1f}%")
        print()
        if self.output_file.exists():
            print(f"Output: {self.output_file}")
            print(f"File size: {self.output_file.stat().st_size / 1024 / 1024:.1f} MB")
            with open(self.output_file, 'r') as f:
                lines = sum(1 for _ in f)
            print(f"Examples: {lines:,}")
        else:
            print(f"No output file created (all examples failed)")
        print("=" * 80)


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate formally verified witness training examples"
    )
    parser.add_argument(
        "--target",
        type=int,
        default=10,
        help="Number of examples to generate (default: 10, use 10000 for full dataset)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="/Users/nkennedy/proj/witness-evals/data/verified/verified_train.jsonl",
        help="Output JSONL file"
    )
    args = parser.parse_args()

    generator = VerifiedExampleGenerator(Path(args.output))
    generator.generate_dataset(args.target)


if __name__ == "__main__":
    main()
