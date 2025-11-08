#!/usr/bin/env python3
"""
Create a formally verified dataset using actual witness commands.

This script:
1. Generates signing keys
2. Creates real attestations using `witness run`
3. Creates matching policies
4. Verifies with `witness verify`
5. Collects successful examples as training data

This ensures our training data teaches the model to create
ACTUALLY VALID witness configurations that pass verification.
"""

import json
import subprocess
import tempfile
import os
from pathlib import Path
import hashlib

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""


class VerifiedDatasetCreator:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.examples = []

    def create_signing_keys(self, key_dir: Path):
        """Create Ed25519 signing keys (smallest keys witness supports)"""
        key_dir.mkdir(parents=True, exist_ok=True)

        attestation_key = key_dir / "attestation-key.pem"
        attestation_pub = key_dir / "attestation-key.pub"
        policy_key = key_dir / "policy-key.pem"
        policy_pub = key_dir / "policy-key.pub"

        # Generate attestation signing key (Ed25519)
        if not attestation_key.exists():
            subprocess.run([
                "openssl", "genpkey",
                "-algorithm", "ed25519",
                "-out", str(attestation_key)
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)

            subprocess.run([
                "openssl", "pkey",
                "-in", str(attestation_key),
                "-pubout",
                "-out", str(attestation_pub)
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)

        # Generate policy signing key (Ed25519)
        if not policy_key.exists():
            subprocess.run([
                "openssl", "genpkey",
                "-algorithm", "ed25519",
                "-out", str(policy_key)
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)

            subprocess.run([
                "openssl", "pkey",
                "-in", str(policy_key),
                "-pubout",
                "-out", str(policy_pub)
            ], check=True, capture_output=True, stderr=subprocess.DEVNULL)

        return attestation_key, attestation_pub, policy_key, policy_pub

    def init_git_repo(self, work_dir: Path):
        """Initialize a git repository for git attestor"""
        subprocess.run(["git", "init"], cwd=str(work_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"],
                      cwd=str(work_dir), capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"],
                      cwd=str(work_dir), capture_output=True, check=True)

        # Create initial commit
        test_file = work_dir / "README.md"
        test_file.write_text("# Test Project\n")
        subprocess.run(["git", "add", "README.md"], cwd=str(work_dir), capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"],
                      cwd=str(work_dir), capture_output=True, check=True)

    def create_test_artifact(self, work_dir: Path) -> Path:
        """Create a simple test artifact"""
        artifact = work_dir / "test-app"
        artifact.write_text("#!/bin/sh\necho 'Hello from test app'\n")
        artifact.chmod(0o755)
        return artifact

    def run_witness_attestation(self, work_dir: Path, attestation_key: Path,
                                attestors: list, step_name: str = "build") -> Path:
        """Run witness to create an actual attestation"""
        output_file = work_dir / f"{step_name}-attestation.json"

        # Create artifact
        artifact = self.create_test_artifact(work_dir)

        # Run witness run
        cmd = [
            "witness", "run",
            "--step", step_name,
            "--attestations", ",".join(attestors),
            "--outfile", str(output_file),
            "--signer-file-key-path", str(attestation_key),
            "--",
            "echo", "Building..."
        ]

        result = subprocess.run(cmd, cwd=str(work_dir), capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"witness run failed: {result.stderr}")

        return output_file

    def extract_public_key_id(self, pub_key_path: Path) -> str:
        """Extract key ID from public key"""
        with open(pub_key_path, 'r') as f:
            key_content = f.read()

        # Calculate SHA256 of key
        key_hash = hashlib.sha256(key_content.encode()).hexdigest()
        return f"sha256:{key_hash}"

    def create_policy(self, work_dir: Path, attestors: list, pub_key: Path,
                     step_name: str = "build") -> Path:
        """Create a policy document"""
        policy_file = work_dir / "policy.json"

        # Read public key
        with open(pub_key, 'r') as f:
            pub_key_content = f.read()

        key_id = self.extract_public_key_id(pub_key)

        policy = {
            "expires": "2026-12-31T23:59:59Z",
            "publickeys": {
                "attestation-key": {
                    "keyid": key_id,
                    "key": pub_key_content
                }
            },
            "steps": {
                step_name: {
                    "name": step_name,
                    "attestations": [
                        {"type": f"https://witness.dev/attestations/{att}/v0.1"}
                        for att in attestors
                    ],
                    "functionaries": [
                        {
                            "type": "publickey",
                            "publickeyid": "attestation-key"
                        }
                    ]
                }
            }
        }

        with open(policy_file, 'w') as f:
            json.dump(policy, f, indent=2)

        return policy_file

    def sign_policy(self, policy_file: Path, policy_key: Path) -> Path:
        """Sign policy with witness"""
        signed_policy = policy_file.parent / "policy-signed.json"

        cmd = [
            "witness", "sign",
            "--infile", str(policy_file),
            "--outfile", str(signed_policy),
            "--signer-file-key-path", str(policy_key)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"witness sign failed: {result.stderr}")

        return signed_policy

    def verify_attestation(self, attestation_file: Path, signed_policy: Path,
                          policy_pub_key: Path, artifact: Path) -> bool:
        """Verify attestation with witness verify"""
        cmd = [
            "witness", "verify",
            "--policy", str(signed_policy),
            "--publickey", str(policy_pub_key),
            "-a", str(attestation_file),
            "-f", str(artifact)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        return result.returncode == 0

    def create_training_example(self, attestors: list, attestation_file: Path,
                               policy_file: Path, step_name: str = "build") -> dict:
        """Create a training example from verified witness run"""

        # Read actual attestation
        with open(attestation_file, 'r') as f:
            attestation = json.load(f)

        # Read policy
        with open(policy_file, 'r') as f:
            policy = json.load(f)

        attestor_list = ", ".join(attestors)
        policy_json = json.dumps(policy, indent=2)

        user_prompt = f"How do I create a witness policy for a {step_name} step with these attestors: {attestor_list}? I need the complete policy and commands."

        assistant_response = f"""Here's a complete, verified witness configuration for {step_name} with {attestor_list}:

**Step 1: Create Policy Document**
```json
{policy_json}
```

**Step 2: Run Attestation**
```bash
witness run --step {step_name} \\
  --attestations {','.join(attestors)} \\
  --outfile {step_name}-attestation.json \\
  --key attestation-key.pem \\
  -- <your-build-command>
```

**Step 3: Sign Policy**
```bash
witness sign \\
  --infile policy.json \\
  --outfile policy-signed.json \\
  --key policy-key.pem
```

**Step 4: Verify**
```bash
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  -a {step_name}-attestation.json \\
  -f <artifact>
```

This configuration has been verified to work with witness {self.get_witness_version()}."""

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ],
            "_metadata": {
                "verified": True,
                "attestors": attestors,
                "step": step_name,
                "witness_version": self.get_witness_version()
            }
        }

    def get_witness_version(self) -> str:
        """Get witness version"""
        result = subprocess.run(["witness", "version"], capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else "unknown"

    def create_verified_example(self, attestors: list, step_name: str = "build"):
        """Create a single verified example"""
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)

            print(f"\n{'='*80}")
            print(f"Creating verified example: {step_name} with {attestors}")
            print(f"{'='*80}")

            try:
                # Step 1: Initialize git repo if git attestor is used
                if "git" in attestors:
                    print("1. Initializing git repository...")
                    self.init_git_repo(work_dir)
                    print("   ✓ Git repo initialized")

                # Step 2: Create keys
                print("2. Creating signing keys...")
                att_key, att_pub, pol_key, pol_pub = self.create_signing_keys(work_dir / "keys")
                print("   ✓ Keys created")

                # Step 3: Create artifact
                print("3. Creating test artifact...")
                artifact = self.create_test_artifact(work_dir)
                print(f"   ✓ Artifact created: {artifact}")

                # Step 4: Run attestation
                print(f"4. Running witness attestation...")
                attestation_file = self.run_witness_attestation(
                    work_dir, att_key, attestors, step_name
                )
                print(f"   ✓ Attestation created: {attestation_file.name}")

                # Step 5: Create policy
                print("5. Creating policy...")
                policy_file = self.create_policy(work_dir, attestors, att_pub, step_name)
                print(f"   ✓ Policy created")

                # Step 6: Sign policy
                print("6. Signing policy...")
                signed_policy = self.sign_policy(policy_file, pol_key)
                print(f"   ✓ Policy signed")

                # Step 7: Verify
                print("7. Verifying with witness...")
                verified = self.verify_attestation(attestation_file, signed_policy, pol_pub, artifact)

                if verified:
                    print("   ✅ VERIFICATION PASSED!")

                    # Step 7: Create training example
                    example = self.create_training_example(
                        attestors, attestation_file, policy_file, step_name
                    )
                    self.examples.append(example)
                    print(f"   ✓ Training example created")
                    return True
                else:
                    print("   ❌ VERIFICATION FAILED")
                    return False

            except Exception as e:
                print(f"   ❌ Error: {e}")
                return False

    def generate_dataset(self, num_examples: int = 10):
        """Generate verified dataset"""
        print("="*80)
        print("Witness Verified Dataset Creator")
        print("="*80)
        print(f"Target: {num_examples} verified examples")
        print()

        # Define test scenarios (sorted by complexity)
        scenarios = [
            (["environment"], "build"),  # Simplest - no git, no command
            (["git"], "build"),  # Just git
            (["environment", "git"], "build"),  # Two simple attestors
            (["product"], "build"),  # Just products
            (["material"], "test"),  # Just materials
            (["environment", "product"], "build"),  # Environment + products
            (["git", "product"], "build"),  # Git + products
            (["git", "environment"], "build"),  # Git + environment
            (["git", "environment", "product"], "build"),  # Three attestors
            (["git", "environment", "material", "product"], "build"),  # Full set
        ]

        success_count = 0
        for i, (attestors, step) in enumerate(scenarios[:num_examples], 1):
            print(f"\nExample {i}/{num_examples}")
            if self.create_verified_example(attestors, step):
                success_count += 1

        # Save dataset
        output_file = self.output_dir / "verified_train.jsonl"
        with open(output_file, 'w') as f:
            for example in self.examples:
                f.write(json.dumps(example) + '\n')

        print(f"\n{'='*80}")
        print(f"Dataset Creation Complete!")
        print(f"{'='*80}")
        print(f"Successful examples: {success_count}/{num_examples}")
        print(f"Output file: {output_file}")
        print(f"{'='*80}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create verified witness training dataset")
    parser.add_argument("--examples", type=int, default=10, help="Number of examples to generate")
    parser.add_argument("--output", type=str, default="data/verified", help="Output directory")
    args = parser.parse_args()

    creator = VerifiedDatasetCreator(Path(args.output))
    creator.generate_dataset(args.examples)


if __name__ == "__main__":
    main()
