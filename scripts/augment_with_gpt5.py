#!/usr/bin/env python3
"""
Augment verified examples with GPT-5 to create diverse variations.

Takes verified witness examples and uses GPT-5 to:
1. Rephrase questions in multiple styles
2. Restructure answers in different formats
3. Keep all witness commands/policies IDENTICAL (verified)
4. Create 5-10x more examples from same verified content
"""

import json
import os
from pathlib import Path
from openai import OpenAI
import sys

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

def augment_example(example: dict, variations: int = 5) -> list:
    """Use GPT-5 to create variations of a verified example"""

    orig_question = example['messages'][1]['content']
    orig_answer = example['messages'][2]['content']

    # Extract the verified witness commands (must preserve exactly)
    import re
    witness_commands = re.findall(r'```bash\n(witness.*?)```', orig_answer, re.DOTALL)
    policy_json = re.findall(r'```json\n(\{.*?\})```', orig_answer, re.DOTALL)
    rego_code = re.findall(r'```rego\n(.*?)```', orig_answer, re.DOTALL)

    prompt = f"""Create {variations} diverse variations of this witness training example.

CRITICAL: Keep ALL code blocks EXACTLY as-is (they're formally verified):
- Witness commands
- Policy JSON
- Rego code

Only vary:
- Question phrasing (beginner, intermediate, expert, troubleshooting)
- Answer structure (step-by-step, concise, detailed, reference)
- Explanation style
- Section organization

Original Q: {orig_question}

Original A: {orig_answer}

Output {variations} variations as a JSON array:
[
  {{"question": "...", "answer": "..."}},
  ...
]

Make each variation feel natural and different while preserving exact code."""

    response = client.chat.completions.create(
        model='gpt-5',
        messages=[
            {'role': 'system', 'content': 'You create diverse training data variations.'},
            {'role': 'user', 'content': prompt}
        ],
        max_completion_tokens=8000
    )

    # Parse JSON response
    try:
        content = response.choices[0].message.content
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            variations_list = json.loads(json_match.group(0))

            # Convert to training format
            result = []
            for var in variations_list:
                result.append({
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": var['question']},
                        {"role": "assistant", "content": var['answer']}
                    ],
                    "_metadata": {
                        "augmented": True,
                        "source": "gpt-5"
                    }
                })
            return result
    except Exception as e:
        print(f"  ⚠️ Parse error: {e}")
        return []

def main():
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/diverse-100k/train_backup.jsonl")
    output_file = Path("data/augmented/gpt5_augmented.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Load examples
    with open(input_file, 'r') as f:
        examples = [json.loads(line) for line in f]

    print(f"Augmenting {len(examples)} examples with GPT-5...")
    print(f"Target: {len(examples) * 5} augmented examples")
    print(f"Output: {output_file}")
    print()

    # Process examples
    total_generated = 0

    with open(output_file, 'w') as out:
        for i, ex in enumerate(examples, 1):
            if i % 10 == 0:
                print(f"  {i}/{len(examples)} ({total_generated} variations generated)")

            variations = augment_example(ex, variations=5)

            for var in variations:
                out.write(json.dumps(var) + '\n')
                total_generated += 1

    print()
    print(f"✅ Generated {total_generated} augmented examples")
    print(f"   Original: {len(examples)}")
    print(f"   Multiplier: {total_generated / len(examples):.1f}x")
    print(f"   Output: {output_file}")

if __name__ == "__main__":
    main()
