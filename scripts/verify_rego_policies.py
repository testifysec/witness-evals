#!/usr/bin/env python3
"""
Formal Rego Policy Verifier

Tests every Rego policy in training data with OPA (Open Policy Agent):
1. Extracts Rego code blocks from Q/A pairs
2. Tests with `opa check` for syntax errors
3. Tests with `opa eval` for runtime errors
4. Only includes examples with verified Rego
5. Ensures 100% valid Rego in training data

This is critical - invalid Rego would teach the model bad syntax.
"""

import json
import subprocess
import tempfile
import re
from pathlib import Path
from typing import List, Tuple

def extract_rego_blocks(text: str) -> List[str]:
    """Extract all Rego code blocks from text"""
    # Match ```rego ... ``` blocks
    rego_blocks = re.findall(r'```rego\n(.*?)```', text, re.DOTALL)
    return rego_blocks

def verify_rego_syntax(rego_code: str) -> Tuple[bool, str]:
    """Verify Rego syntax with OPA"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.rego', delete=False) as f:
        f.write(rego_code)
        rego_file = f.name

    try:
        # Check syntax
        result = subprocess.run(
            ['opa', 'check', rego_file],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Syntax error: {result.stderr}"

        # Test evaluation with empty input
        result = subprocess.run(
            ['opa', 'eval', '-d', rego_file, '-i', '{}', 'data'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Eval error: {result.stderr}"

        return True, "Valid"

    finally:
        Path(rego_file).unlink()

def verify_training_example(example: Dict) -> Tuple[bool, List[str]]:
    """Verify all Rego in a training example"""
    assistant_content = example['messages'][2]['content']

    rego_blocks = extract_rego_blocks(assistant_content)

    if not rego_blocks:
        # No Rego in this example - that's fine
        return True, []

    errors = []
    for i, rego in enumerate(rego_blocks, 1):
        valid, msg = verify_rego_syntax(rego)
        if not valid:
            errors.append(f"Block {i}: {msg}")

    return len(errors) == 0, errors

def verify_dataset(input_file: Path, output_file: Path):
    """Verify all Rego in dataset, only keep valid examples"""
    print("="*70)
    print("Formal Rego Policy Verification")
    print("="*70)
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print()

    with open(input_file, 'r') as f:
        examples = [json.loads(line) for line in f]

    print(f"Total examples: {len(examples)}")

    verified_examples = []
    rego_count = 0
    valid_rego = 0
    invalid_rego = 0

    for i, example in enumerate(examples, 1):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(examples)} (Valid Rego: {valid_rego}, Invalid: {invalid_rego})")

        valid, errors = verify_training_example(example)

        if valid:
            verified_examples.append(example)
            assistant_content = example['messages'][2]['content']
            rego_blocks = extract_rego_blocks(assistant_content)
            if rego_blocks:
                valid_rego += len(rego_blocks)
                rego_count += len(rego_blocks)
        else:
            invalid_rego += len(errors)
            rego_count += len(errors)
            if i <= 10:  # Show first few errors
                print(f"  ❌ Example {i}: {errors[0]}")

    # Save verified examples
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        for ex in verified_examples:
            f.write(json.dumps(ex) + '\n')

    print()
    print("="*70)
    print("Verification Complete!")
    print("="*70)
    print(f"Total examples: {len(examples)}")
    print(f"Verified examples: {len(verified_examples)}")
    print(f"Rejected: {len(examples) - len(verified_examples)}")
    print(f"Success rate: {len(verified_examples) * 100 / len(examples):.1f}%")
    print()
    print(f"Total Rego blocks: {rego_count}")
    print(f"Valid Rego: {valid_rego}")
    print(f"Invalid Rego: {invalid_rego}")
    print(f"Rego validity: {valid_rego * 100 / rego_count if rego_count > 0 else 100:.1f}%")
    print()
    print(f"✅ Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Verify Rego policies in training data")
    parser.add_argument("--input", required=True, help="Input JSONL file")
    parser.add_argument("--output", required=True, help="Output JSONL file (verified only)")
    args = parser.parse_args()

    verify_dataset(Path(args.input), Path(args.output))

if __name__ == "__main__":
    main()
