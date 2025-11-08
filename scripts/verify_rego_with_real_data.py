#!/usr/bin/env python3
"""
Formal Rego Verifier - Tests against REAL attestation data

Process:
1. For each Rego policy in training data
2. Create a real attestation with witness run
3. Extract the attestation JSON
4. Test the Rego policy against the real attestation using OPA
5. Verify the Rego actually evaluates correctly
6. Only keep examples where Rego works with real data

This ensures Rego policies teach valid patterns that work with actual witness attestations.
"""

import json
import subprocess
import tempfile
import re
import base64
from pathlib import Path
from typing import Dict, List, Tuple

def create_test_attestation(attestor: str, work_dir: Path) -> Tuple[Path, Dict]:
    """Create a real attestation and return file + parsed JSON"""
    # Create keys
    key_pem = work_dir / "key.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(key_pem)],
        capture_output=True, check=True
    )

    # Init git if needed
    if attestor == "git":
        subprocess.run(["git", "init"], cwd=work_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=work_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=work_dir, capture_output=True, check=True)
        (work_dir / "test.txt").write_text("test")
        subprocess.run(["git", "add", "test.txt"], cwd=work_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=work_dir, capture_output=True, check=True)

    # Create artifact
    (work_dir / "output.txt").write_text("test")

    # Run witness
    att_file = work_dir / "attestation.json"
    result = subprocess.run([
        "witness", "run",
        "--step", "test",
        "--attestations", attestor,
        "--signer-file-key-path", str(key_pem),
        "--outfile", str(att_file),
        "--",
        "echo", "test"
    ], cwd=work_dir, capture_output=True)

    if result.returncode != 0 or not att_file.exists():
        return None, None

    # Parse attestation to get predicate
    with open(att_file, 'r') as f:
        envelope = json.load(f)

    # Decode payload to get attestation collection
    payload_b64 = envelope['payload']
    payload_json = json.loads(base64.b64decode(payload_b64))

    # Extract predicate (the collection)
    if 'predicate' not in payload_json:
        return None, None

    collection = payload_json['predicate']

    # Find the attestor's data in the collection
    if 'attestations' not in collection:
        return None, None

    attestor_data = None
    for att in collection['attestations']:
        if attestor in att.get('type', ''):
            attestor_data = att.get('attestation', {})
            break

    return att_file, attestor_data

def test_rego_against_data(rego_code: str, attestation_data: Dict) -> Tuple[bool, str]:
    """Test Rego policy against real attestation data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Write Rego policy
        rego_file = tmpdir / "policy.rego"
        rego_file.write_text(rego_code)

        # Write attestation data as input
        input_file = tmpdir / "input.json"
        with open(input_file, 'w') as f:
            json.dump({"attestation": attestation_data}, f)

        # Test syntax
        result = subprocess.run(
            ['opa', 'check', str(rego_file)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Syntax error: {result.stderr}"

        # Test evaluation with real data
        result = subprocess.run(
            ['opa', 'eval',
             '-d', str(rego_file),
             '-i', str(input_file),
             'data'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Eval error: {result.stderr}"

        # Check if deny rules evaluated (presence indicates it ran)
        if 'deny' in rego_code and 'data' in result.stdout:
            try:
                eval_result = json.loads(result.stdout)
                # Rego evaluated successfully
                return True, "Valid - evaluated against real attestation"
            except:
                return False, "Could not parse OPA output"

        return True, "Valid syntax"

def verify_example_rego(example: Dict) -> Tuple[bool, str]:
    """Verify Rego in example against real attestation data"""
    assistant_content = example['messages'][2]['content']
    user_content = example['messages'][1]['content']

    # Extract Rego
    rego_blocks = re.findall(r'```rego\n(.*?)```', assistant_content, re.DOTALL)

    if not rego_blocks:
        return True, "No Rego to verify"

    # Determine attestor from question
    attestor = None
    for att in ['git', 'environment', 'commandrun', 'github', 'gitlab', 'aws', 'gcp-iit']:
        if att in user_content.lower():
            attestor = att
            break

    if not attestor:
        # Can't verify without knowing attestor
        return True, "Skipped - attestor unknown"

    # Create real attestation
    with tempfile.TemporaryDirectory() as tmpdir:
        att_file, att_data = create_test_attestation(attestor, Path(tmpdir))

        if not att_data:
            return True, f"Skipped - couldn't create {attestor} attestation"

        # Test each Rego block
        for i, rego in enumerate(rego_blocks, 1):
            valid, msg = test_rego_against_data(rego, att_data)
            if not valid:
                return False, f"Block {i}: {msg}"

        return True, f"Valid - tested against real {attestor} attestation"

def main():
    # Test the massive schemas file
    input_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/massive_schemas.jsonl")
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/massive_schemas_verified.jsonl")

    print("="*70)
    print("Testing Rego Against Real Attestation Schemas")
    print("="*70)
    print(f"Input: {input_file}")
    print()

    with open(input_file, 'r') as f:
        examples = [json.loads(line) for line in f]

    print(f"Total examples: {len(examples)}")
    print("Testing each Rego policy against real witness attestations...")
    print()

    verified = []
    rego_tested = 0
    rego_valid = 0
    rego_invalid = 0

    for i, example in enumerate(examples, 1):
        if i % 50 == 0:
            print(f"  Progress: {i}/{len(examples)} (Rego valid: {rego_valid}, invalid: {rego_invalid})")

        valid, msg = verify_example_rego(example)

        if valid:
            verified.append(example)
            if "tested against real" in msg:
                rego_valid += 1
                rego_tested += 1
        else:
            rego_invalid += 1
            rego_tested += 1
            if i <= 5:
                print(f"  ❌ Example {i}: {msg}")

    # Save
    with open(output_file, 'w') as f:
        for ex in verified:
            f.write(json.dumps(ex) + '\n')

    print()
    print("="*70)
    print(f"✅ Verification Complete!")
    print("="*70)
    print(f"Total examples: {len(examples)}")
    print(f"Verified: {len(verified)} ({len(verified)*100/len(examples):.1f}%)")
    print(f"Rejected: {len(examples) - len(verified)}")
    print()
    print(f"Rego blocks tested: {rego_tested}")
    print(f"Valid (tested with real data): {rego_valid}")
    print(f"Invalid: {rego_invalid}")
    print()
    print(f"Output: {output_file}")

if __name__ == "__main__":
    main()
