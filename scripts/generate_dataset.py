#!/usr/bin/env python3
"""
Generate training dataset for fine-tuning an LLM on Witness attestation framework.

This script generates JSONL files in OpenAI fine-tuning format with examples of:
- witness run commands for all attestors
- Policy document creation
- Rego policies for attestor validation
- Multi-step workflows
- Security scenarios

Output: data/attestors/*.jsonl, data/workflows/*.jsonl, etc.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

# Base system prompt for all examples
SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

class WitnessDatasetGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_message(self, user_prompt: str, assistant_response: str) -> Dict[str, Any]:
        """Create a single training example in OpenAI format"""
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ]
        }

    def write_jsonl(self, filename: str, examples: List[Dict]):
        """Write examples to JSONL file"""
        filepath = self.output_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, 'w') as f:
            for example in examples:
                f.write(json.dumps(example) + '\n')

        print(f"✓ Generated {len(examples)} examples -> {filepath}")

    def generate_commandrun_examples(self) -> List[Dict]:
        """Generate examples for commandrun attestor"""
        examples = []

        # Example 1: Basic usage
        examples.append(self.create_message(
            "How do I attest a Go build with the commandrun attestor?",
            """To attest a Go build with commandrun, use:

```bash
witness run --step build \\
  --attestations commandrun,material,product \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp
```

This captures:
- The command executed (`go build -o myapp`)
- Exit code
- Stdout/stderr
- Input files (materials) and output files (products)

The corresponding Rego policy to validate the build succeeded:

```rego
package commandrun

import rego.v1

deny contains msg if {
    input.exitcode != 0
    msg := sprintf("Build failed with exit code %d", [input.exitcode])
}
```"""
        ))

        # Example 2: With tracing enabled
        examples.append(self.create_message(
            "How can I track all processes spawned during a build?",
            """Enable tracing with the `--trace` flag (Linux only):

```bash
witness run --step build \\
  --attestations commandrun \\
  --trace \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- make all
```

This captures detailed process information:
- All processes spawned (PIDs, parent PIDs)
- Files opened by each process
- Process digests (hashes of executables)
- Command lines and environment variables

Rego policy to ensure only approved programs were executed:

```rego
package commandrun

import rego.v1

# Whitelist of allowed programs
approved_programs := {
    "/usr/bin/gcc",
    "/usr/bin/ld",
    "/bin/sh"
}

deny contains msg if {
    some process in input.processes
    not process.program in approved_programs
    msg := sprintf("Unauthorized program executed: %s", [process.program])
}
```"""
        ))

        # Example 3: Silent mode
        examples.append(self.create_message(
            "How do I run a command without printing its output to the console?",
            """Use the attestor's silent mode by configuring it in code, or capture output in the attestation only:

```bash
# The command output will still be in the attestation JSON
witness run --step build \\
  --attestations commandrun \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp 2>&1
```

The stdout and stderr are captured in the attestation fields:
- `"stdout"`: Standard output content
- `"stderr"`: Standard error content
- `"exitcode"`: Process exit code

Rego policy to validate no errors in stderr:

```rego
package commandrun

import rego.v1

deny contains msg if {
    count(input.stderr) > 0
    contains(lower(input.stderr), "error")
    msg := "Build produced errors in stderr"
}
```"""
        ))

        # Example 4: Checking exit codes
        examples.append(self.create_message(
            "How do I ensure a test command passed in my policy?",
            """Here's a comprehensive Rego policy for validating test execution:

```rego
package commandrun

import rego.v1

# Deny if exit code is non-zero
deny contains msg if {
    input.exitcode != 0
    msg := sprintf("Tests failed with exit code %d", [input.exitcode])
}

# Deny if stderr contains failure keywords
deny contains msg if {
    failure_keywords := ["FAIL", "ERROR", "FATAL", "panic"]
    some keyword in failure_keywords
    contains(input.stderr, keyword)
    msg := sprintf("Tests produced failure output: %s", [keyword])
}

# Ensure tests actually ran (stdout not empty)
deny contains msg if {
    count(input.stdout) == 0
    msg := "No test output detected - tests may not have run"
}
```

Apply this in your witness policy document under the test step."""
        ))

        # Example 5: Multi-command validation
        examples.append(self.create_message(
            "Can I validate that specific commands were run in sequence?",
            """Yes, by checking the command field in your attestations. Here's a Rego policy:

```rego
package commandrun

import rego.v1

# Expected build command
expected_cmd := ["go", "build", "-o", "myapp"]

deny contains msg if {
    input.cmd != expected_cmd
    msg := sprintf("Unexpected build command. Expected %v, got %v", [expected_cmd, input.cmd])
}

# Ensure certain flags are present
deny contains msg if {
    not "-trimpath" in input.cmd
    msg := "Build must use -trimpath flag for reproducibility"
}

# Ensure dangerous flags are not used
deny contains msg if {
    some arg in input.cmd
    contains(arg, "-ldflags")
    contains(arg, "-X main.secret")
    msg := "Build must not embed secrets via ldflags"
}
```"""
        ))

        # Example 6: Process tracking
        examples.append(self.create_message(
            "How do I write a policy to validate all spawned processes?",
            """When using `--trace`, you can validate all processes in the `processes` array:

```rego
package commandrun

import rego.v1

# Deny if any process exited with non-zero
deny contains msg if {
    some process in input.processes
    process.exitcode != 0
    msg := sprintf("Process %s (PID %d) failed with exit code %d",
                   [process.program, process.processid, process.exitcode])
}

# Validate process integrity - ensure known programs
deny contains msg if {
    some process in input.processes
    count(process.programdigest) == 0
    process.program != ""
    msg := sprintf("Process %s has no digest - cannot verify integrity", [process.program])
}

# Check for suspicious file access
suspicious_paths := ["/etc/shadow", "/root/.ssh", "/etc/passwd"]

deny contains msg if {
    some process in input.processes
    some file_path, _ in process.openedfiles
    some suspicious in suspicious_paths
    contains(file_path, suspicious)
    msg := sprintf("Process %s accessed suspicious file: %s", [process.program, file_path])
}
```"""
        ))

        return examples

    def generate_git_examples(self) -> List[Dict]:
        """Generate examples for git attestor"""
        examples = []

        # Example 1: Basic git attestation
        examples.append(self.create_message(
            "How do I attest git repository information?",
            """The git attestor automatically captures repository state:

```bash
witness run --step build \\
  --attestations git,commandrun,product \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp
```

The git attestor captures:
- Commit hash
- Author and committer information
- Branch name
- Commit message
- Parent commits
- Git tags
- Remote URLs (with credentials redacted)
- Working directory status

Rego policy to enforce builds from main branch:

```rego
package git

import rego.v1

deny contains msg if {
    input.branch != "main"
    msg := sprintf("Builds must be from main branch, got: %s", [input.branch])
}
```"""
        ))

        # Example 2: Validate clean working directory
        examples.append(self.create_message(
            "How do I ensure builds are from a clean git repository?",
            """Use a Rego policy to check the `status` field:

```rego
package git

import rego.v1

# Deny if working directory has uncommitted changes
deny contains msg if {
    count(input.status) > 0
    msg := "Working directory must be clean (no uncommitted changes)"
}

# List all modified files if any
deny contains msg if {
    count(input.status) > 0
    modified_files := [file | some file, status in input.status]
    msg := sprintf("Uncommitted files: %v", [modified_files])
}
```

In your witness policy:

```json
{
  "steps": {
    "build": {
      "attestations": [
        {"type": "https://witness.dev/attestations/git/v0.1"}
      ]
    }
  }
}
```"""
        ))

        # Example 3: Validate commit signature
        examples.append(self.create_message(
            "How can I enforce that commits are GPG signed?",
            """Check the `signature` field in your Rego policy:

```rego
package git

import rego.v1

# Require GPG signature on commits
deny contains msg if {
    count(input.signature) == 0
    msg := "Commit must be GPG signed"
}

# Validate signature format (PGP)
deny contains msg if {
    not startswith(input.signature, "-----BEGIN PGP SIGNATURE-----")
    msg := "Invalid GPG signature format"
}
```

Note: Witness validates the signature presence, not its validity. Use git's built-in verification for cryptographic validation."""
        ))

        # Example 4: Author validation
        examples.append(self.create_message(
            "How do I restrict who can author commits?",
            """Use a Rego policy to validate commit authors:

```rego
package git

import rego.v1

# Approved commit authors (email addresses)
approved_authors := {
    "alice@example.com",
    "bob@example.com",
    "ci-bot@example.com"
}

deny contains msg if {
    not input.authoremail in approved_authors
    msg := sprintf("Unauthorized commit author: %s", [input.authoremail])
}

# Ensure committer matches author (no commit forgery)
deny contains msg if {
    input.authoremail != input.committeremail
    msg := sprintf("Author (%s) and committer (%s) mismatch",
                   [input.authoremail, input.committeremail])
}
```"""
        ))

        # Example 5: Tag validation
        examples.append(self.create_message(
            "How do I validate that a release build is from a tagged commit?",
            """Check the `tags` array in git attestation:

```rego
package git

import rego.v1

# Ensure commit has at least one tag
deny contains msg if {
    count(input.tags) == 0
    msg := "Release builds must be from tagged commits"
}

# Validate tag name format (semantic versioning)
deny contains msg if {
    some tag in input.tags
    not regex.match(`^v[0-9]+\\.[0-9]+\\.[0-9]+$`, tag.name)
    msg := sprintf("Tag must follow semver format (vX.Y.Z), got: %s", [tag.name])
}

# Require signed tags
deny contains msg if {
    some tag in input.tags
    count(tag.pgpsignature) == 0
    msg := sprintf("Tag %s must be GPG signed", [tag.name])
}
```"""
        ))

        return examples

    def generate_environment_examples(self) -> List[Dict]:
        """Generate examples for environment attestor"""
        examples = []

        # Example 1: Basic usage
        examples.append(self.create_message(
            "How do I capture environment information in an attestation?",
            """The environment attestor captures system and environment variables:

```bash
witness run --step build \\
  --attestations environment,commandrun \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp
```

Captured information:
- Operating system (os)
- Hostname
- Username
- Environment variables

Rego policy to validate build environment:

```rego
package environment

import rego.v1

# Ensure builds happen on Linux
deny contains msg if {
    input.os != "linux"
    msg := sprintf("Builds must run on Linux, got: %s", [input.os])
}

# Validate specific environment variables are set
deny contains msg if {
    not "CI" in input.variables
    msg := "Must run in CI environment (CI variable not set)"
}
```"""
        ))

        # Example 2: Environment variable validation
        examples.append(self.create_message(
            "How do I enforce required environment variables in my build?",
            """Use Rego to validate the `variables` map:

```rego
package environment

import rego.v1

# Required environment variables
required_vars := ["CI", "BUILD_ID", "COMMIT_SHA"]

deny contains msg if {
    some var in required_vars
    not var in input.variables
    msg := sprintf("Required environment variable missing: %s", [var])
}

# Deny dangerous variables
deny contains msg if {
    "DISABLE_TESTS" in input.variables
    input.variables["DISABLE_TESTS"] == "true"
    msg := "Cannot disable tests in production builds"
}

# Validate CI provider
deny contains msg if {
    not "GITHUB_ACTIONS" in input.variables
    not "GITLAB_CI" in input.variables
    msg := "Must run in GitHub Actions or GitLab CI"
}
```"""
        ))

        # Example 3: Hostname restrictions
        examples.append(self.create_message(
            "Can I restrict which machines can perform builds?",
            """Yes, validate the hostname field:

```rego
package environment

import rego.v1

# Approved build servers
approved_hosts := {
    "build-server-01.example.com",
    "build-server-02.example.com",
    "github-runner-*"  # Wildcard pattern
}

deny contains msg if {
    not hostname_approved(input.hostname)
    msg := sprintf("Unauthorized build host: %s", [input.hostname])
}

hostname_approved(hostname) if {
    some approved in approved_hosts
    hostname == approved
}

hostname_approved(hostname) if {
    some approved in approved_hosts
    contains(approved, "*")
    prefix := trim_suffix(approved, "*")
    startswith(hostname, prefix)
}
```"""
        ))

        return examples

    def generate_material_product_examples(self) -> List[Dict]:
        """Generate examples for material/product attestors"""
        examples = []

        # Example 1: Material attestor
        examples.append(self.create_message(
            "How do I attest input files (materials) for a build?",
            """Use the material attestor to record all input files:

```bash
witness run --step build \\
  --attestations material,commandrun,product \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp
```

Materials capture all files in the working directory before the command runs.

Rego policy to validate specific files exist:

```rego
package material

import rego.v1

# Required source files
required_files := ["main.go", "go.mod", "go.sum"]

deny contains msg if {
    some file in required_files
    not file in input
    msg := sprintf("Required source file missing: %s", [file])
}

# Deny if sensitive files are present
deny contains msg if {
    ".env" in input
    msg := "Material must not include .env files (secrets)"
}
```"""
        ))

        # Example 2: Product attestor
        examples.append(self.create_message(
            "How do I attest output files (products) from a build?",
            """Use the product attestor to record all output files:

```bash
witness run --step build \\
  --attestations commandrun,product \\
  --outfile build-attestation.json \\
  --key key.pem \\
  -- go build -o myapp
```

Products capture all files created or modified by the command.

Rego policy to validate expected outputs:

```rego
package product

import rego.v1

# Expected output binary
deny contains msg if {
    not "myapp" in input
    msg := "Build must produce 'myapp' binary"
}

# Validate file hash
expected_hashes := {
    "myapp": "sha256:abc123..."
}

deny contains msg if {
    some file, digests in input
    file in expected_hashes
    not expected_hashes[file] in digests
    msg := sprintf("File %s has unexpected hash", [file])
}
```"""
        ))

        # Example 3: Cross-step validation
        examples.append(self.create_message(
            "How do I verify that files aren't tampered with between build and test steps?",
            """Use the new cross-step attestation access feature in policies:

```json
{
  "steps": {
    "build": {
      "name": "build",
      "attestations": [
        {"type": "https://witness.dev/attestations/product/v0.1"}
      ]
    },
    "test": {
      "name": "test",
      "attestations": [
        {"type": "https://witness.dev/attestations/material/v0.1"}
      ]
    }
  }
}
```

Rego policy with cross-step validation:

```rego
package test

import rego.v1

# Access build step's products
build_products := input.attestations["build"]["https://witness.dev/attestations/product/v0.1"]

# Access test step's materials
test_materials := input.attestations["test"]["https://witness.dev/attestations/material/v0.1"]

# Ensure test uses the exact binary from build
deny contains msg if {
    some file, build_hash in build_products
    file == "myapp"
    not file in test_materials
    msg := sprintf("Test step missing file from build: %s", [file])
}

deny contains msg if {
    some file in ["myapp"]
    build_hash := build_products[file]
    test_hash := test_materials[file]
    build_hash != test_hash
    msg := sprintf("File %s was modified between build and test", [file])
}
```"""
        ))

        return examples

    def generate_policy_examples(self) -> List[Dict]:
        """Generate examples for policy document creation"""
        examples = []

        # Example 1: Basic policy structure
        examples.append(self.create_message(
            "How do I create a basic witness policy document?",
            """Here's a complete witness policy structure:

```json
{
  "expires": "2025-12-31T23:59:59Z",
  "roots": {
    "root-key-id": {
      "certificate": "-----BEGIN CERTIFICATE-----\\n...\\n-----END CERTIFICATE-----",
      "intermediates": []
    }
  },
  "publickeys": {
    "build-key-id": {
      "keyid": "sha256:abc123...",
      "key": "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
    }
  },
  "steps": {
    "build": {
      "name": "build",
      "attestations": [
        {"type": "https://witness.dev/attestations/git/v0.1"},
        {"type": "https://witness.dev/attestations/environment/v0.1"},
        {"type": "https://witness.dev/attestations/command-run/v0.1"},
        {"type": "https://witness.dev/attestations/product/v0.1"}
      ],
      "functionaries": [
        {
          "type": "publickey",
          "publickeyid": "build-key-id"
        }
      ]
    }
  }
}
```

Save this as `policy.json` and sign it:

```bash
witness sign --infile policy.json --outfile policy-signed.json --key policy-key.pem
```"""
        ))

        # Example 2: Multi-step policy
        examples.append(self.create_message(
            "How do I create a policy for a multi-step CI/CD pipeline?",
            """Here's a complete build→test→package policy:

```json
{
  "expires": "2025-12-31T23:59:59Z",
  "publickeys": {
    "ci-key": {
      "keyid": "sha256:abc123...",
      "key": "-----BEGIN PUBLIC KEY-----\\n...\\n-----END PUBLIC KEY-----"
    }
  },
  "steps": {
    "build": {
      "name": "build",
      "attestations": [
        {"type": "https://witness.dev/attestations/git/v0.1"},
        {"type": "https://witness.dev/attestations/command-run/v0.1"},
        {"type": "https://witness.dev/attestations/product/v0.1"}
      ],
      "functionaries": [{"type": "publickey", "publickeyid": "ci-key"}]
    },
    "test": {
      "name": "test",
      "attestations": [
        {"type": "https://witness.dev/attestations/material/v0.1"},
        {"type": "https://witness.dev/attestations/command-run/v0.1"}
      ],
      "functionaries": [{"type": "publickey", "publickeyid": "ci-key"}]
    },
    "package": {
      "name": "package",
      "attestations": [
        {"type": "https://witness.dev/attestations/material/v0.1"},
        {"type": "https://witness.dev/attestations/oci/v0.1"},
        {"type": "https://witness.dev/attestations/product/v0.1"}
      ],
      "functionaries": [{"type": "publickey", "publickeyid": "ci-key"}]
    }
  }
}
```

Each step creates attestations:

```bash
# Build step
witness run --step build \\
  --attestations git,commandrun,product \\
  -o build.json --key ci-key.pem \\
  -- go build -o myapp

# Test step
witness run --step test \\
  --attestations material,commandrun \\
  -o test.json --key ci-key.pem \\
  -- go test ./...

# Package step
witness run --step package \\
  --attestations material,oci,product \\
  -o package.json --key ci-key.pem \\
  -- docker build -t myapp:latest .
```

Verify the complete pipeline:

```bash
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  -a build.json -a test.json -a package.json \\
  -f myapp
```"""
        ))

        # Example 3: Policy with Rego rules
        examples.append(self.create_message(
            "How do I add Rego validation rules to my policy?",
            """Add a `rego` field to each attestation in your policy:

```json
{
  "steps": {
    "build": {
      "name": "build",
      "attestations": [
        {
          "type": "https://witness.dev/attestations/git/v0.1",
          "rego": "package git\\nimport rego.v1\\n\\ndeny contains msg if {\\n  input.branch != \\"main\\"\\n  msg := \\"Must build from main branch\\"\\n}"
        },
        {
          "type": "https://witness.dev/attestations/command-run/v0.1",
          "rego": "package commandrun\\nimport rego.v1\\n\\ndeny contains msg if {\\n  input.exitcode != 0\\n  msg := \\"Build failed\\"\\n}"
        }
      ]
    }
  }
}
```

Or reference external Rego files:

```json
{
  "steps": {
    "build": {
      "attestations": [
        {
          "type": "https://witness.dev/attestations/git/v0.1",
          "regofile": "policies/git.rego"
        }
      ]
    }
  }
}
```

The Rego policies are evaluated during `witness verify`."""
        ))

        return examples

    def generate_workflow_examples(self) -> List[Dict]:
        """Generate multi-step workflow examples"""
        examples = []

        # Example 1: GitHub Actions workflow
        examples.append(self.create_message(
            "How do I integrate Witness into a GitHub Actions workflow?",
            """Here's a complete GitHub Actions workflow with Witness:

```yaml
name: Build with Witness

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Witness
        run: |
          curl -LO https://github.com/in-toto/go-witness/releases/latest/download/witness-linux-amd64
          chmod +x witness-linux-amd64
          sudo mv witness-linux-amd64 /usr/local/bin/witness

      - name: Load signing key
        run: echo "${{ secrets.WITNESS_KEY }}" > key.pem

      - name: Build with attestation
        run: |
          witness run --step build \\
            --attestations git,github,environment,commandrun,product \\
            -o build-attestation.json \\
            --key key.pem \\
            -- go build -o myapp

      - name: Test with attestation
        run: |
          witness run --step test \\
            --attestations material,commandrun \\
            -o test-attestation.json \\
            --key key.pem \\
            -- go test ./...

      - name: Upload attestations
        uses: actions/upload-artifact@v4
        with:
          name: attestations
          path: |
            build-attestation.json
            test-attestation.json

  verify:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Download attestations
        uses: actions/download-artifact@v4
        with:
          name: attestations

      - name: Verify attestations
        run: |
          witness verify \\
            --policy policy-signed.json \\
            --publickey policy-key.pub \\
            -a build-attestation.json \\
            -a test-attestation.json \\
            -f myapp
```"""
        ))

        # Example 2: Container build workflow
        examples.append(self.create_message(
            "How do I attest a Docker container build?",
            """Use the OCI attestor for container builds:

```bash
# Build and attest container
witness run --step package \\
  --attestations material,oci,product \\
  -o package.json \\
  --key key.pem \\
  -- docker build -t myapp:latest .

# Push container
docker push myapp:latest

# Verify before deployment
witness verify \\
  --policy policy-signed.json \\
  --publickey policy-key.pub \\
  -a package.json \\
  -f myapp:latest
```

The OCI attestor captures:
- Base image digests
- Layers added
- Image manifest
- Image digest

Rego policy to validate base image:

```rego
package oci

import rego.v1

approved_bases := [
    "docker.io/library/alpine:3.19",
    "gcr.io/distroless/static-debian12"
]

deny contains msg if {
    not base_image_approved(input.baseimage)
    msg := sprintf("Unauthorized base image: %s", [input.baseimage])
}

base_image_approved(image) if {
    some approved in approved_bases
    image == approved
}
```"""
        ))

        return examples

    def generate_all_datasets(self):
        """Generate all training datasets"""
        print("Generating Witness training datasets...")
        print("=" * 60)

        # Generate attestor-specific examples
        self.write_jsonl("data/attestors/commandrun.jsonl", self.generate_commandrun_examples())
        self.write_jsonl("data/attestors/git.jsonl", self.generate_git_examples())
        self.write_jsonl("data/attestors/environment.jsonl", self.generate_environment_examples())
        self.write_jsonl("data/attestors/material-product.jsonl", self.generate_material_product_examples())

        # Generate policy examples
        self.write_jsonl("data/policies/policy-creation.jsonl", self.generate_policy_examples())

        # Generate workflow examples
        self.write_jsonl("data/workflows/ci-cd-workflows.jsonl", self.generate_workflow_examples())

        print("=" * 60)
        print("✓ Dataset generation complete!")
        print(f"\nOutput directory: {self.output_dir}")
        print("\nNext steps:")
        print("1. Review generated JSONL files")
        print("2. Add more examples for other attestors")
        print("3. Validate with: python scripts/validate_dataset.py")
        print("4. Fine-tune your model with the generated data")


if __name__ == "__main__":
    generator = WitnessDatasetGenerator(Path(__file__).parent.parent)
    generator.generate_all_datasets()
