#!/usr/bin/env python3
"""
Synthetic Data Generator for Witness Training Dataset

Generates thousands of valid attestation + policy + Rego examples by:
1. Creating realistic attestation JSON for all attestor types
2. Generating matching policy documents
3. Creating Rego validation rules
4. Producing diverse training scenarios

Usage:
    python3 scripts/synthetic_data_generator.py --examples 10000
"""

import json
import random
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Callable
import argparse

# Seed for reproducibility
random.seed(42)

# System prompt for all examples
SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""


class FakeDataGenerator:
    """Generate realistic fake data for attestations"""

    @staticmethod
    def sha1() -> str:
        return hashlib.sha1(str(random.random()).encode()).hexdigest()

    @staticmethod
    def sha256() -> str:
        return hashlib.sha256(str(random.random()).encode()).hexdigest()

    @staticmethod
    def email() -> str:
        names = ["alice", "bob", "charlie", "diana", "eve", "frank"]
        domains = ["example.com", "company.com", "org.com"]
        return f"{random.choice(names)}.{random.choice(names)}@{random.choice(domains)}"

    @staticmethod
    def git_branch() -> str:
        return random.choice([
            "main", "master", "develop", "staging",
            "feature/auth", "feature/api", "bugfix/security",
            "release/v1.0", "hotfix/critical"
        ])

    @staticmethod
    def command() -> List[str]:
        commands = [
            ["go", "build", "-o", "myapp"],
            ["go", "test", "./..."],
            ["npm", "run", "build"],
            ["make", "all"],
            ["docker", "build", "-t", "app:latest", "."],
            ["python", "setup.py", "install"],
            ["cargo", "build", "--release"],
        ]
        return random.choice(commands)

    @staticmethod
    def hostname() -> str:
        prefixes = ["build", "ci", "runner", "agent"]
        suffixes = ["01", "02", "prod", "dev"]
        return f"{random.choice(prefixes)}-{random.choice(suffixes)}.company.com"

    @staticmethod
    def os_name() -> str:
        return random.choice(["linux", "darwin", "windows"])

    @staticmethod
    def file_path() -> str:
        files = [
            "main.go", "app.py", "index.js", "Makefile", "Dockerfile",
            "package.json", "go.mod", "requirements.txt", "README.md"
        ]
        return random.choice(files)


class AttestorSchemas:
    """Schema definitions for all Witness attestors"""

    @staticmethod
    def git() -> Dict[str, Any]:
        """Generate git attestor data"""
        fake = FakeDataGenerator()
        author = fake.email()
        return {
            "type": "https://witness.dev/attestations/git/v0.1",
            "attestation": {
                "commithash": fake.sha1(),
                "branch": fake.git_branch(),
                "author": author.split('@')[0],
                "authoremail": author,
                "committername": author.split('@')[0],
                "committeremail": author,
                "commitmessage": random.choice([
                    "feat: add new feature",
                    "fix: resolve bug",
                    "chore: update dependencies",
                    "refactor: improve code structure"
                ]),
                "status": {} if random.random() > 0.3 else {
                    "modified.go": {"worktree": "modified"}
                },
                "signature": "" if random.random() > 0.5 else "-----BEGIN PGP SIGNATURE-----\n...",
                "remotes": ["https://github.com/org/repo.git"]
            }
        }

    @staticmethod
    def commandrun() -> Dict[str, Any]:
        """Generate commandrun attestor data"""
        fake = FakeDataGenerator()
        cmd = fake.command()
        exitcode = random.choice([0, 0, 0, 0, 1])  # 80% success rate

        return {
            "type": "https://witness.dev/attestations/command-run/v0.1",
            "attestation": {
                "cmd": cmd,
                "exitcode": exitcode,
                "stdout": "Build successful" if exitcode == 0 else "",
                "stderr": "" if exitcode == 0 else "Error: build failed",
            }
        }

    @staticmethod
    def environment() -> Dict[str, Any]:
        """Generate environment attestor data"""
        fake = FakeDataGenerator()
        return {
            "type": "https://witness.dev/attestations/environment/v0.1",
            "attestation": {
                "os": fake.os_name(),
                "hostname": fake.hostname(),
                "username": random.choice(["runner", "ci", "buildbot"]),
                "variables": {
                    "CI": "true",
                    "PATH": "/usr/local/bin:/usr/bin:/bin",
                    "HOME": "/home/runner",
                }
            }
        }

    @staticmethod
    def material() -> Dict[str, Any]:
        """Generate material attestor data"""
        fake = FakeDataGenerator()
        num_files = random.randint(3, 10)
        materials = {}
        for _ in range(num_files):
            materials[fake.file_path()] = {
                f"sha256:{fake.sha256()}": {}
            }

        return {
            "type": "https://witness.dev/attestations/material/v0.1",
            "attestation": materials
        }

    @staticmethod
    def product() -> Dict[str, Any]:
        """Generate product attestor data"""
        fake = FakeDataGenerator()
        products = {
            "myapp": {f"sha256:{fake.sha256()}": {}},
        }

        # Sometimes include additional artifacts
        if random.random() > 0.5:
            products["myapp.tar.gz"] = {f"sha256:{fake.sha256()}": {}}

        return {
            "type": "https://witness.dev/attestations/product/v0.1",
            "attestation": products
        }

    @staticmethod
    def github() -> Dict[str, Any]:
        """Generate GitHub Actions attestor data"""
        return {
            "type": "https://witness.dev/attestations/github/v0.1",
            "attestation": {
                "repository": "org/repo",
                "workflow": "build.yml",
                "runid": str(random.randint(1000000, 9999999)),
                "actor": FakeDataGenerator().email().split('@')[0],
            }
        }


class RegoGenerator:
    """Generate Rego policy rules based on attestation data"""

    @staticmethod
    def git_rules(attestation: Dict[str, Any]) -> str:
        """Generate Rego rules for git attestation"""
        branch = attestation.get("branch", "main")
        has_status = len(attestation.get("status", {})) > 0

        rules = [
            "package git",
            "",
            "import rego.v1",
            "",
        ]

        # Branch enforcement
        rules.extend([
            "# Enforce builds from specific branch",
            "deny contains msg if {",
            f'    input.branch != "{branch}"',
            f'    msg := sprintf("Must build from {branch} branch, got: %s", [input.branch])',
            "}",
            "",
        ])

        # Clean working directory
        if not has_status:
            rules.extend([
                "# Require clean working directory",
                "deny contains msg if {",
                "    count(input.status) > 0",
                '    msg := "Working directory must be clean (no uncommitted changes)"',
                "}",
                "",
            ])

        # Author validation
        rules.extend([
            "# Validate commit author",
            "approved_authors := {",
            '    "alice.smith@example.com",',
            '    "bob.jones@company.com",',
            '    "ci-bot@company.com"',
            "}",
            "",
            "deny contains msg if {",
            "    not input.authoremail in approved_authors",
            '    msg := sprintf("Unauthorized commit author: %s", [input.authoremail])',
            "}",
        ])

        return "\n".join(rules)

    @staticmethod
    def commandrun_rules(attestation: Dict[str, Any]) -> str:
        """Generate Rego rules for commandrun attestation"""
        rules = [
            "package commandrun",
            "",
            "import rego.v1",
            "",
            "# Ensure command succeeded",
            "deny contains msg if {",
            "    input.exitcode != 0",
            '    msg := sprintf("Command failed with exit code %d", [input.exitcode])',
            "}",
            "",
            "# Check for errors in stderr",
            "deny contains msg if {",
            "    contains(lower(input.stderr), \"error\")",
            '    msg := "Command produced errors in stderr"',
            "}",
        ]

        return "\n".join(rules)

    @staticmethod
    def environment_rules(attestation: Dict[str, Any]) -> str:
        """Generate Rego rules for environment attestation"""
        os_name = attestation.get("os", "linux")

        rules = [
            "package environment",
            "",
            "import rego.v1",
            "",
            "# Ensure correct OS",
            "deny contains msg if {",
            f'    input.os != "{os_name}"',
            f'    msg := sprintf("Must run on {os_name}, got: %s", [input.os])',
            "}",
            "",
            "# Require CI environment",
            "deny contains msg if {",
            '    not "CI" in input.variables',
            '    msg := "Must run in CI environment (CI variable not set)"',
            "}",
        ]

        return "\n".join(rules)


class PolicyGenerator:
    """Generate policy documents from attestations"""

    @staticmethod
    def generate_policy(step_name: str, attestors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a policy document for given attestations"""
        fake = FakeDataGenerator()

        policy = {
            "expires": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publickeys": {
                "build-key": {
                    "keyid": f"sha256:{fake.sha256()}",
                    "key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
                }
            },
            "steps": {
                step_name: {
                    "name": step_name,
                    "attestations": [
                        {"type": att["type"]} for att in attestors
                    ],
                    "functionaries": [
                        {
                            "type": "publickey",
                            "publickeyid": "build-key"
                        }
                    ]
                }
            }
        }

        return policy


class SyntheticExampleGenerator:
    """Main generator that creates complete training examples"""

    def __init__(self):
        self.attestor_schemas = AttestorSchemas()
        self.rego_generator = RegoGenerator()
        self.policy_generator = PolicyGenerator()

    def generate_single_step_example(self) -> Dict[str, Any]:
        """Generate a single-step attestation scenario"""
        # Pick 1-5 random attestors
        attestor_types = ["git", "commandrun", "environment", "material", "product", "github"]
        num_attestors = random.randint(1, 5)
        selected = random.sample(attestor_types, num_attestors)

        # Generate attestations
        attestations = []
        for attestor_type in selected:
            if hasattr(self.attestor_schemas, attestor_type):
                attestations.append(getattr(self.attestor_schemas, attestor_type)())

        # Generate policy
        policy = self.policy_generator.generate_policy("build", attestations)

        # Generate Rego rules for first attestor
        rego_rules = ""
        if attestations:
            first_att = attestations[0]
            attestor_name = first_att["type"].split("/")[-2]
            if hasattr(self.rego_generator, f"{attestor_name}_rules"):
                rego_rules = getattr(self.rego_generator, f"{attestor_name}_rules")(
                    first_att["attestation"]
                )

        # Create user prompt
        attestor_list = ", ".join(selected)
        user_prompt = f"How do I create a witness policy for a build step that uses these attestors: {attestor_list}?"

        # Create assistant response
        policy_json = json.dumps(policy, indent=2)
        assistant_response = f"""Here's a complete witness policy for your build step with {attestor_list} attestors:

**Policy Document:**
```json
{policy_json}
```

**Witness Run Command:**
```bash
witness run --step build \\
  --attestations {','.join(selected)} \\
  --outfile build-attestation.json \\
  --key signing-key.pem \\
  -- <your-build-command>
```

**Rego Validation Rules:**
```rego
{rego_rules}
```

**Verification:**
```bash
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  -a build-attestation.json \\
  --subject <artifact>
```
"""

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ]
        }

    def generate_multi_step_example(self) -> Dict[str, Any]:
        """Generate a multi-step pipeline scenario"""
        # Define pipeline steps
        steps = {
            "build": ["git", "commandrun", "product"],
            "test": ["material", "commandrun"],
            "package": ["material", "product"]
        }

        # Generate policy for all steps
        policy = {
            "expires": (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publickeys": {
                "ci-key": {
                    "keyid": f"sha256:{FakeDataGenerator().sha256()}",
                    "key": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
                }
            },
            "steps": {}
        }

        for step_name, attestor_list in steps.items():
            attestations = []
            for attestor_type in attestor_list:
                if hasattr(self.attestor_schemas, attestor_type):
                    attestations.append(getattr(self.attestor_schemas, attestor_type)())

            policy["steps"][step_name] = {
                "name": step_name,
                "attestations": [{"type": att["type"]} for att in attestations],
                "functionaries": [{"type": "publickey", "publickeyid": "ci-key"}]
            }

        user_prompt = "How do I create a multi-step witness policy for a build → test → package pipeline?"

        policy_json = json.dumps(policy, indent=2)
        assistant_response = f"""Here's a complete multi-step witness policy for your pipeline:

**Policy Document:**
```json
{policy_json}
```

**Pipeline Commands:**

```bash
# Step 1: Build
witness run --step build \\
  --attestations git,commandrun,product \\
  -o build.json --key ci-key.pem \\
  -- go build -o myapp

# Step 2: Test
witness run --step test \\
  --attestations material,commandrun \\
  -o test.json --key ci-key.pem \\
  -- go test ./...

# Step 3: Package
witness run --step package \\
  --attestations material,product \\
  -o package.json --key ci-key.pem \\
  -- tar czf myapp.tar.gz myapp

# Verify entire pipeline
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  -a build.json -a test.json -a package.json
```
"""

        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ]
        }

    def generate_examples(self, num_examples: int) -> List[Dict[str, Any]]:
        """Generate a mix of example types"""
        examples = []

        # 70% single-step, 30% multi-step
        single_step_count = int(num_examples * 0.7)
        multi_step_count = num_examples - single_step_count

        print(f"Generating {single_step_count} single-step examples...")
        for i in range(single_step_count):
            if i % 100 == 0:
                print(f"  {i}/{single_step_count}")
            examples.append(self.generate_single_step_example())

        print(f"\nGenerating {multi_step_count} multi-step examples...")
        for i in range(multi_step_count):
            if i % 100 == 0:
                print(f"  {i}/{multi_step_count}")
            examples.append(self.generate_multi_step_example())

        return examples


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic Witness training data")
    parser.add_argument("--examples", type=int, default=1000, help="Number of examples to generate")
    parser.add_argument("--output", type=str, default="data/synthetic", help="Output directory")
    args = parser.parse_args()

    print("=" * 80)
    print("Witness Synthetic Data Generator")
    print("=" * 80)
    print(f"Generating {args.examples} training examples...")
    print()

    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate examples
    generator = SyntheticExampleGenerator()
    examples = generator.generate_examples(args.examples)

    # Shuffle for better training
    random.shuffle(examples)

    # Split into train/val (90/10)
    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]

    # Write train set
    train_file = output_dir / "train.jsonl"
    with open(train_file, 'w') as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + '\n')

    # Write validation set
    val_file = output_dir / "valid.jsonl"
    with open(val_file, 'w') as f:
        for ex in val_examples:
            f.write(json.dumps(ex) + '\n')

    print()
    print("=" * 80)
    print("✅ Generation Complete!")
    print("=" * 80)
    print(f"Train examples: {len(train_examples)}")
    print(f"Validation examples: {len(val_examples)}")
    print(f"Output directory: {output_dir}")
    print()
    print(f"Train file: {train_file}")
    print(f"Validation file: {val_file}")
    print()
    print("Next steps:")
    print("  1. Inspect examples: python3 scripts/view_examples.py --random 5")
    print("  2. Fine-tune model: Run MLX training with this dataset")
    print("=" * 80)


if __name__ == "__main__":
    main()
