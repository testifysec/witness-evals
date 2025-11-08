#!/usr/bin/env python3
"""
Validate Witness training dataset JSONL files.

Checks:
- Valid JSON format
- Required fields present
- Message structure correct
- No duplicate examples
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set


class DatasetValidator:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.errors = []
        self.warnings = []
        self.total_examples = 0
        self.seen_prompts: Set[str] = set()

    def validate_message_structure(self, example: Dict, file_path: Path, line_num: int) -> bool:
        """Validate message structure matches OpenAI format"""
        if "messages" not in example:
            self.errors.append(f"{file_path}:{line_num} - Missing 'messages' field")
            return False

        messages = example["messages"]
        if not isinstance(messages, list):
            self.errors.append(f"{file_path}:{line_num} - 'messages' must be a list")
            return False

        if len(messages) != 3:
            self.errors.append(
                f"{file_path}:{line_num} - Expected 3 messages (system, user, assistant), got {len(messages)}"
            )
            return False

        # Validate roles
        expected_roles = ["system", "user", "assistant"]
        for i, (msg, expected_role) in enumerate(zip(messages, expected_roles)):
            if not isinstance(msg, dict):
                self.errors.append(f"{file_path}:{line_num} - Message {i} is not a dict")
                return False

            if "role" not in msg:
                self.errors.append(f"{file_path}:{line_num} - Message {i} missing 'role'")
                return False

            if msg["role"] != expected_role:
                self.errors.append(
                    f"{file_path}:{line_num} - Message {i} has role '{msg['role']}', expected '{expected_role}'"
                )
                return False

            if "content" not in msg:
                self.errors.append(f"{file_path}:{line_num} - Message {i} missing 'content'")
                return False

            if not isinstance(msg["content"], str):
                self.errors.append(f"{file_path}:{line_num} - Message {i} content must be string")
                return False

            if len(msg["content"].strip()) == 0:
                self.errors.append(f"{file_path}:{line_num} - Message {i} content is empty")
                return False

        return True

    def check_duplicate(self, example: Dict, file_path: Path, line_num: int):
        """Check for duplicate user prompts"""
        user_prompt = example["messages"][1]["content"]

        if user_prompt in self.seen_prompts:
            self.warnings.append(f"{file_path}:{line_num} - Duplicate user prompt: '{user_prompt[:50]}...'")
        else:
            self.seen_prompts.add(user_prompt)

    def validate_content_quality(self, example: Dict, file_path: Path, line_num: int):
        """Validate content quality"""
        assistant_msg = example["messages"][2]["content"]

        # Check for code blocks
        if "```" in assistant_msg:
            # Ensure code blocks are properly closed
            if assistant_msg.count("```") % 2 != 0:
                self.errors.append(f"{file_path}:{line_num} - Unclosed code block in assistant response")

        # Check minimum length
        if len(assistant_msg) < 100:
            self.warnings.append(f"{file_path}:{line_num} - Assistant response is very short ({len(assistant_msg)} chars)")

        # Check for witness commands
        if "witness run" not in assistant_msg and "witness verify" not in assistant_msg:
            self.warnings.append(f"{file_path}:{line_num} - No witness commands in response")

    def validate_file(self, file_path: Path) -> int:
        """Validate a single JSONL file"""
        print(f"Validating {file_path.relative_to(self.data_dir.parent)}...")

        if not file_path.exists():
            self.errors.append(f"{file_path} - File does not exist")
            return 0

        examples_count = 0

        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    example = json.loads(line)
                except json.JSONDecodeError as e:
                    self.errors.append(f"{file_path}:{line_num} - Invalid JSON: {e}")
                    continue

                if self.validate_message_structure(example, file_path, line_num):
                    self.check_duplicate(example, file_path, line_num)
                    self.validate_content_quality(example, file_path, line_num)
                    examples_count += 1

        self.total_examples += examples_count
        print(f"  ✓ {examples_count} examples")
        return examples_count

    def validate_all(self):
        """Validate all JSONL files"""
        print("Validating Witness training dataset...")
        print("=" * 60)

        # Find all JSONL files
        jsonl_files = list(self.data_dir.rglob("*.jsonl"))

        if not jsonl_files:
            self.errors.append(f"No JSONL files found in {self.data_dir}")
            return False

        for jsonl_file in sorted(jsonl_files):
            self.validate_file(jsonl_file)

        print("=" * 60)
        print(f"Total examples: {self.total_examples}")
        print(f"Unique prompts: {len(self.seen_prompts)}")

        if self.warnings:
            print(f"\n⚠ Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  {warning}")

        if self.errors:
            print(f"\n✗ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"  {error}")
            return False
        else:
            print("\n✓ All validations passed!")
            return True

    def print_stats(self):
        """Print dataset statistics"""
        print("\nDataset Statistics:")
        print("-" * 60)

        # Count examples per file
        for jsonl_file in sorted(self.data_dir.rglob("*.jsonl")):
            with open(jsonl_file, 'r') as f:
                count = sum(1 for line in f if line.strip())
            category = jsonl_file.parent.name
            filename = jsonl_file.stem
            print(f"  {category}/{filename}: {count} examples")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"

    validator = DatasetValidator(data_dir)
    valid = validator.validate_all()
    validator.print_stats()

    sys.exit(0 if valid else 1)
