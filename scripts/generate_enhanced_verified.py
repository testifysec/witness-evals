#!/usr/bin/env python3
"""
Generate enhanced, diverse verified witness examples.

Diversity dimensions:
1. 31 attestor combinations (vs 15 before)
2. 10 step names (vs 1 before)
3. 7 question templates (vs 1 before)
4. 5 command patterns (vs 1 before)
5. Optional Rego policies (new!)

This creates maximum diversity to improve model generalization and reduce loss.
"""

import json
import subprocess
import tempfile
import os
import sys
import random
import base64
from pathlib import Path
from typing import List

# Use the base generator from the working 10K version
sys.path.insert(0, str(Path(__file__).parent))

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Safe attestors (no mocking needed)
SAFE_ATTESTORS = ["git", "environment", "material", "product", "file"]

# Generate all combinations
ATTESTOR_COMBINATIONS = []
for att in SAFE_ATTESTORS:
    ATTESTOR_COMBINATIONS.append([att])
for i, att1 in enumerate(SAFE_ATTESTORS):
    for att2 in SAFE_ATTESTORS[i+1:]:
        ATTESTOR_COMBINATIONS.append(sorted([att1, att2]))
for i, att1 in enumerate(SAFE_ATTESTORS):
    for j, att2 in enumerate(SAFE_ATTESTORS[i+1:], i+1):
        for att3 in SAFE_ATTESTORS[j+1:]:
            ATTESTOR_COMBINATIONS.append(sorted([att1, att2, att3]))
for i, att1 in enumerate(SAFE_ATTESTORS):
    for j, att2 in enumerate(SAFE_ATTESTORS[i+1:], i+1):
        for k, att3 in enumerate(SAFE_ATTESTORS[j+1:], j+1):
            for att4 in SAFE_ATTESTORS[k+1:]:
                ATTESTOR_COMBINATIONS.append(sorted([att1, att2, att3, att4]))
ATTESTOR_COMBINATIONS.append(SAFE_ATTESTORS)

STEP_NAMES = [
    "build", "test", "package", "deploy", "scan",
    "compile", "lint", "security-check", "analyze", "verify"
]

USER_QUESTION_TEMPLATES = [
    "How do I create a complete witness configuration for a {step} step with {attestors} attestors that passes verification?",
    "What's the complete setup for using witness with {attestors} attestors in my {step} step?",
    "Show me a working witness example for {attestors} attestors in a {step} step.",
    "I need a verified witness configuration for {step} with {attestors}. How do I set it up?",
    "Can you provide a complete witness run and verify example using {attestors} for {step}?",
    "Walk me through creating witness attestations with {attestors} in my {step} step.",
    "How do I instrument my {step} step with witness using {attestors} attestors?",
]

COMMAND_PATTERNS = [
    'echo "Success" > output.txt',
    'cat input.txt > output.txt',
    'echo "Build complete" > output.txt',
    'cp input.txt output.txt && echo "Done" >> output.txt',
    'echo "Processing..." > output.txt',
]

print(f"Enhanced Diversity Statistics:")
print(f"  Attestor combinations: {len(ATTESTOR_COMBINATIONS)}")
print(f"  Step names: {len(STEP_NAMES)}")
print(f"  Question templates: {len(USER_QUESTION_TEMPLATES)}")
print(f"  Command patterns: {len(COMMAND_PATTERNS)}")
print(f"  Total variations: {len(ATTESTOR_COMBINATIONS) * len(STEP_NAMES) * len(USER_QUESTION_TEMPLATES) * len(COMMAND_PATTERNS):,}")
print()
print("This will be integrated into the verified generator...")
print("Run with: python3 scripts/generate_10k_verified.py --target 20000 --use-diversity")
