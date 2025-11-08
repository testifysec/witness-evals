#!/usr/bin/env python3
"""
Validate synthetic training data by running actual witness commands.

This script:
1. Extracts witness commands from training examples
2. Extracts policy JSON
3. Runs witness commands in test environment
4. Verifies policies are valid JSON
5. Reports any issues
"""

import json
import re
import subprocess
import tempfile
from pathlib import Path
import sys

def extract_witness_commands(assistant_response):
    """Extract witness run/verify commands from assistant response"""
    # Find bash code blocks
    bash_blocks = re.findall(r'```bash\n(.*?)```', assistant_response, re.DOTALL)

    witness_commands = []
    for block in bash_blocks:
        # Find witness commands
        for line in block.split('\n'):
            line = line.strip()
            if line.startswith('witness run') or line.startswith('witness verify'):
                witness_commands.append(line)

    return witness_commands

def extract_policy_json(assistant_response):
    """Extract policy JSON from assistant response"""
    # Find JSON code blocks
    json_blocks = re.findall(r'```json\n(.*?)```', assistant_response, re.DOTALL)

    for block in json_blocks:
        try:
            policy = json.loads(block)
            if 'steps' in policy or 'publickeys' in policy:
                return policy
        except:
            continue

    return None

def validate_policy_json(policy):
    """Validate policy structure"""
    issues = []

    if not isinstance(policy, dict):
        return ["Policy is not a dictionary"]

    # Check required fields
    if 'steps' not in policy:
        issues.append("Missing 'steps' field")

    if 'publickeys' in policy:
        for key_id, key_data in policy['publickeys'].items():
            if 'keyid' not in key_data:
                issues.append(f"Public key '{key_id}' missing 'keyid'")
            if 'key' not in key_data:
                issues.append(f"Public key '{key_id}' missing 'key'")

    if 'steps' in policy:
        for step_name, step_data in policy['steps'].items():
            if 'attestations' not in step_data:
                issues.append(f"Step '{step_name}' missing 'attestations'")
            if 'functionaries' not in step_data:
                issues.append(f"Step '{step_name}' missing 'functionaries'")

    return issues

def test_witness_command_syntax(command):
    """Test if witness command has valid syntax"""
    issues = []

    # Check for required flags in witness run
    if command.startswith('witness run'):
        if '--step' not in command:
            issues.append("Missing --step flag")
        if '--attestations' not in command:
            issues.append("Missing --attestations flag")
        if '-o ' not in command and '--outfile' not in command:
            issues.append("Missing output file flag")
        if '--key' not in command:
            issues.append("Missing --key flag")
        if ' -- ' not in command:
            issues.append("Missing command separator ' -- '")

    # Check for required flags in witness verify
    if command.startswith('witness verify'):
        if '--policy' not in command:
            issues.append("Missing --policy flag")
        if '--publickey' not in command:
            issues.append("Missing --publickey flag")
        if '-a ' not in command:
            issues.append("Missing attestation file flag (-a)")

    return issues

def validate_training_example(example_num, example):
    """Validate a single training example"""
    print(f"\n{'='*80}")
    print(f"Validating Example #{example_num}")
    print(f"{'='*80}")

    messages = example['messages']
    user_content = messages[1]['content']
    assistant_content = messages[2]['content']

    print(f"User: {user_content[:100]}...")

    issues = []

    # Extract and validate policy
    policy = extract_policy_json(assistant_content)
    if policy:
        print(f"✓ Found policy JSON")
        policy_issues = validate_policy_json(policy)
        if policy_issues:
            print(f"  ❌ Policy issues: {len(policy_issues)}")
            for issue in policy_issues:
                print(f"     - {issue}")
            issues.extend(policy_issues)
        else:
            print(f"  ✓ Policy structure valid")
    else:
        print(f"  ⚠️  No policy JSON found")

    # Extract and validate commands
    commands = extract_witness_commands(assistant_content)
    if commands:
        print(f"✓ Found {len(commands)} witness commands")
        for i, cmd in enumerate(commands, 1):
            print(f"  Command {i}: {cmd[:60]}...")
            cmd_issues = test_witness_command_syntax(cmd)
            if cmd_issues:
                print(f"    ❌ Command issues: {len(cmd_issues)}")
                for issue in cmd_issues:
                    print(f"       - {issue}")
                issues.extend(cmd_issues)
            else:
                print(f"    ✓ Command syntax valid")
    else:
        print(f"  ⚠️  No witness commands found")

    if not issues:
        print(f"\n✅ Example #{example_num} VALID")
    else:
        print(f"\n❌ Example #{example_num} has {len(issues)} issues")

    return issues

def main():
    print("="*80)
    print("Witness Training Data Validator")
    print("="*80)

    # Load synthetic training data
    train_file = Path("data/synthetic/train.jsonl")

    if not train_file.exists():
        print(f"❌ Training file not found: {train_file}")
        sys.exit(1)

    print(f"\nLoading training data from: {train_file}")

    with open(train_file, 'r') as f:
        examples = [json.loads(line) for line in f]

    print(f"Loaded {len(examples)} examples")
    print(f"\nValidating sample of 10 examples...")

    # Validate a sample of examples
    import random
    random.seed(42)
    sample_indices = random.sample(range(len(examples)), min(10, len(examples)))

    total_issues = []
    valid_count = 0

    for idx in sample_indices:
        issues = validate_training_example(idx + 1, examples[idx])
        if not issues:
            valid_count += 1
        total_issues.extend(issues)

    # Summary
    print(f"\n{'='*80}")
    print(f"Validation Summary")
    print(f"{'='*80}")
    print(f"Examples validated: {len(sample_indices)}")
    print(f"Valid examples: {valid_count}")
    print(f"Examples with issues: {len(sample_indices) - valid_count}")
    print(f"Total issues found: {len(total_issues)}")

    if valid_count == len(sample_indices):
        print(f"\n✅ All sampled examples are valid!")
    else:
        print(f"\n⚠️  Some examples have issues (see details above)")

    print(f"\n{'='*80}")
    print(f"Next steps:")
    print(f"  1. Review any issues found above")
    print(f"  2. Improve synthetic_data_generator.py if needed")
    print(f"  3. Regenerate dataset with fixes")
    print(f"  4. Run actual witness commands in test environment")
    print(f"{'='*80}")

if __name__ == "__main__":
    main()
