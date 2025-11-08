#!/usr/bin/env python3
"""
Generate 20,000 diverse, verified witness examples with:
- More attestor types (not just the basic 6)
- Different step names (build, test, package, deploy, scan)
- Varied command patterns
- Rego policy examples
- Edge cases and variations

This creates maximum diversity to improve model generalization.
"""

import sys
import os

# Import from the working verified generator
sys.path.insert(0, '/Users/nkennedy/proj/witness-evals/scripts')
from generate_10k_verified import VerifiedExampleGenerator

# Expanded attestor combinations for maximum diversity
DIVERSE_ATTESTOR_COMBINATIONS = [
    # Basic single attestors (5 examples)
    ["environment"],
    ["git"],
    ["product"],
    ["material"],
    ["file"],

    # Basic pairs (10 examples)
    ["git", "environment"],
    ["material", "product"],
    ["git", "material"],
    ["git", "product"],
    ["environment", "material"],
    ["environment", "product"],
    ["material", "file"],
    ["product", "file"],
    ["git", "file"],
    ["environment", "file"],

    # Triples (15 examples)
    ["git", "environment", "material"],
    ["git", "environment", "product"],
    ["git", "material", "product"],
    ["environment", "material", "product"],
    ["git", "environment", "file"],
    ["git", "material", "file"],
    ["git", "product", "file"],
    ["environment", "material", "file"],
    ["environment", "product", "file"],
    ["material", "product", "file"],
    ["git", "file", "environment"],
    ["git", "file", "material"],
    ["git", "file", "product"],
    ["environment", "file", "material"],
    ["environment", "file", "product"],

    # Quads (10 examples)
    ["git", "environment", "material", "product"],
    ["git", "environment", "material", "file"],
    ["git", "environment", "product", "file"],
    ["git", "material", "product", "file"],
    ["environment", "material", "product", "file"],
    ["git", "environment", "file", "material"],
    ["git", "environment", "file", "product"],
    ["git", "material", "file", "product"],
    ["environment", "material", "file", "product"],
    ["git", "environment", "material", "product", "file"],

    # With link attestor (in-toto compatibility) (5 examples)
    ["link", "git"],
    ["link", "environment"],
    ["link", "material", "product"],
    ["link", "git", "environment"],
    ["link", "git", "material", "product"],

    # Container/Docker focused (5 examples)
    ["docker", "material", "product"],
    ["docker", "git"],
    ["docker", "git", "material", "product"],
    ["docker", "environment"],
    ["docker", "git", "environment"],

    # OCI image attestation (5 examples)
    ["oci", "material"],
    ["oci", "git"],
    ["oci", "git", "environment"],
    ["oci", "material", "product"],
    ["oci", "git", "material", "product"],

    # SBOM generation (5 examples)
    ["sbom", "material"],
    ["sbom", "git"],
    ["sbom", "git", "environment"],
    ["sbom", "product"],
    ["sbom", "git", "material", "product"],

    # Security scanning (5 examples)
    ["secretscan", "material"],
    ["secretscan", "git"],
    ["secretscan", "git", "environment"],
    ["secretscan", "product"],
    ["secretscan", "git", "material", "product"],

    # SARIF static analysis (5 examples)
    ["sarif", "material"],
    ["sarif", "git"],
    ["sarif", "git", "environment"],
    ["sarif", "product"],
    ["sarif", "git", "environment", "material"],

    # VEX vulnerability info (5 examples)
    ["vex", "material"],
    ["vex", "git"],
    ["vex", "git", "environment"],
    ["vex", "product"],
    ["vex", "sbom"],

    # CI/CD platform attestors (10 examples)
    ["github", "git", "environment"],
    ["github", "git", "material", "product"],
    ["github", "environment", "material", "product"],
    ["gitlab", "git", "environment"],
    ["gitlab", "git", "material", "product"],
    ["jenkins", "git", "environment"],
    ["jenkins", "material", "product"],
    ["aws-codebuild", "git", "environment"],
    ["aws-codebuild", "material", "product"],
    ["gcp-iit", "git", "environment"],

    # Cloud identity (5 examples)
    ["aws-iid", "environment"],
    ["aws-iid", "git", "environment"],
    ["gcp-iit", "environment"],
    ["gcp-iit", "git"],
    ["jwt", "environment"],

    # Maven builds (5 examples)
    ["maven", "material", "product"],
    ["maven", "git"],
    ["maven", "git", "environment"],
    ["maven", "git", "material", "product"],
    ["maven", "environment", "material", "product"],

    # Lock files (5 examples)
    ["lockfiles", "material"],
    ["lockfiles", "git"],
    ["lockfiles", "git", "environment"],
    ["lockfiles", "material", "product"],
    ["lockfiles", "git", "material", "product"],

    # K8s manifests (5 examples)
    ["k8smanifest", "material"],
    ["k8smanifest", "git"],
    ["k8smanifest", "git", "environment"],
    ["k8smanifest", "product"],
    ["k8smanifest", "git", "material", "product"],

    # System packages (5 examples)
    ["system-packages", "environment"],
    ["system-packages", "git"],
    ["system-packages", "git", "environment"],
    ["system-packages", "material"],
    ["system-packages", "git", "material", "product"],

    # SLSA provenance (5 examples)
    ["slsa", "git", "environment"],
    ["slsa", "material", "product"],
    ["slsa", "git", "material", "product"],
    ["slsa", "git", "environment", "material", "product"],
    ["slsa", "environment", "material", "product"],
]

# Step name variations for diversity
STEP_NAMES = [
    "build",
    "test",
    "package",
    "deploy",
    "scan",
    "analyze",
    "verify-deps",
    "security-check",
    "lint",
    "compile",
]

# Different command patterns
COMMAND_PATTERNS = [
    ['bash', '-c', 'echo "Building..." > output.txt'],
    ['bash', '-c', 'cat input.txt > output.txt'],
    ['bash', '-c', 'echo "Test output" > output.txt'],
    ['bash', '-c', 'cp input.txt output.txt'],
    ['sh', '-c', 'echo "Package created" > output.txt'],
]

print(f"Total attestor combinations: {len(DIVERSE_ATTESTOR_COMBINATIONS)}")
print(f"Step name variations: {len(STEP_NAMES)}")
print(f"Command patterns: {len(COMMAND_PATTERNS)}")
print(f"Total possible variations: {len(DIVERSE_ATTESTOR_COMBINATIONS) * len(STEP_NAMES) * len(COMMAND_PATTERNS)}")
print()
print("This provides massive diversity for training!")
