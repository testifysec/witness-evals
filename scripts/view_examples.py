#!/usr/bin/env python3
"""
View and browse training examples from the Witness dataset.

Usage:
    python scripts/view_examples.py                    # Show all examples
    python scripts/view_examples.py --category attestors  # Filter by category
    python scripts/view_examples.py --random 5          # Show 5 random examples
    python scripts/view_examples.py --search "git"      # Search examples
"""

import json
import sys
import random
import argparse
from pathlib import Path
from typing import List, Dict


class ExampleViewer:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.examples = []
        self.load_examples()

    def load_examples(self):
        """Load all examples from JSONL files"""
        for jsonl_file in sorted(self.data_dir.rglob("*.jsonl")):
            category = jsonl_file.parent.name
            filename = jsonl_file.stem

            with open(jsonl_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue

                    try:
                        example = json.loads(line)
                        example["_meta"] = {
                            "category": category,
                            "file": filename,
                            "line": line_num
                        }
                        self.examples.append(example)
                    except json.JSONDecodeError:
                        print(f"Warning: Invalid JSON at {jsonl_file}:{line_num}", file=sys.stderr)

        print(f"Loaded {len(self.examples)} examples\n")

    def display_example(self, example: Dict, index: int = None):
        """Display a single example in readable format"""
        meta = example["_meta"]

        print("=" * 80)
        if index is not None:
            print(f"Example #{index + 1} of {len(self.examples)}")
        print(f"Category: {meta['category']}/{meta['file']}")
        print(f"Location: {meta['file']}.jsonl:{meta['line']}")
        print("=" * 80)

        messages = example["messages"]

        # System message
        print("\n📋 SYSTEM:")
        print("-" * 80)
        print(messages[0]["content"])

        # User message
        print("\n❓ USER:")
        print("-" * 80)
        print(messages[1]["content"])

        # Assistant message
        print("\n🤖 ASSISTANT:")
        print("-" * 80)
        print(messages[2]["content"])

        print("\n" + "=" * 80 + "\n")

    def filter_by_category(self, category: str) -> List[Dict]:
        """Filter examples by category"""
        return [ex for ex in self.examples if ex["_meta"]["category"] == category]

    def search(self, query: str) -> List[Dict]:
        """Search examples by query string"""
        query_lower = query.lower()
        results = []

        for ex in self.examples:
            # Search in user and assistant messages
            user_content = ex["messages"][1]["content"].lower()
            assistant_content = ex["messages"][2]["content"].lower()

            if query_lower in user_content or query_lower in assistant_content:
                results.append(ex)

        return results

    def show_stats(self):
        """Display dataset statistics"""
        categories = {}
        for ex in self.examples:
            cat = ex["_meta"]["category"]
            categories[cat] = categories.get(cat, 0) + 1

        print("Dataset Statistics")
        print("=" * 80)
        print(f"Total examples: {len(self.examples)}\n")
        print("Examples by category:")
        for cat, count in sorted(categories.items()):
            print(f"  {cat:20s}: {count:3d} examples")
        print()

    def interactive_browse(self):
        """Interactive browsing mode"""
        if not self.examples:
            print("No examples to browse")
            return

        index = 0
        while True:
            self.display_example(self.examples[index], index)

            print("Commands: [n]ext | [p]revious | [r]andom | [q]uit | [s]tats | [number]")
            cmd = input(">>> ").strip().lower()

            if cmd == 'q' or cmd == 'quit':
                break
            elif cmd == 'n' or cmd == 'next' or cmd == '':
                index = (index + 1) % len(self.examples)
            elif cmd == 'p' or cmd == 'prev' or cmd == 'previous':
                index = (index - 1) % len(self.examples)
            elif cmd == 'r' or cmd == 'random':
                index = random.randint(0, len(self.examples) - 1)
            elif cmd == 's' or cmd == 'stats':
                self.show_stats()
            elif cmd.isdigit():
                new_index = int(cmd) - 1
                if 0 <= new_index < len(self.examples):
                    index = new_index
                else:
                    print(f"Invalid index. Must be between 1 and {len(self.examples)}")
            else:
                print("Unknown command")


def main():
    parser = argparse.ArgumentParser(description="View Witness training examples")
    parser.add_argument(
        "--category",
        help="Filter by category (attestors, policies, workflows, security)"
    )
    parser.add_argument(
        "--search",
        help="Search examples by query string"
    )
    parser.add_argument(
        "--random",
        type=int,
        help="Show N random examples"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show dataset statistics"
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive browsing mode"
    )

    args = parser.parse_args()

    # Find data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / "data"

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)

    viewer = ExampleViewer(data_dir)

    if args.stats:
        viewer.show_stats()
        return

    # Filter examples
    examples = viewer.examples

    if args.category:
        examples = viewer.filter_by_category(args.category)
        print(f"Filtered to {len(examples)} examples in category '{args.category}'\n")

    if args.search:
        examples = viewer.search(args.search)
        print(f"Found {len(examples)} examples matching '{args.search}'\n")

    if not examples:
        print("No examples found matching criteria")
        return

    # Display mode
    if args.interactive:
        viewer.examples = examples
        viewer.interactive_browse()
    elif args.random:
        count = min(args.random, len(examples))
        random_examples = random.sample(examples, count)
        for i, ex in enumerate(random_examples):
            viewer.display_example(ex, i)
    else:
        # Show all filtered examples
        for i, ex in enumerate(examples):
            viewer.display_example(ex, i)


if __name__ == "__main__":
    main()
