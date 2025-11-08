#!/usr/bin/env python3
"""
Automated knowledge gap Q/A generator using GPT-5.

For each underrepresented topic:
1. GPT-5 generates diverse, specific questions
2. Human (or GPT-5) provides answers
3. Answers are verified if possible
4. Saves to dataset

Targets the 18 attestors with 0 examples.
"""

import json
import os
from pathlib import Path
from openai import OpenAI
import sys

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Underrepresented attestors (0 examples currently)
GAP_ATTESTORS = [
    "github", "gitlab", "jenkins",
    "docker", "oci",
    "sbom", "vex", "sarif", "secretscan",
    "lockfiles", "maven",
    "aws-iid", "aws-codebuild", "gcp-iit",
    "k8smanifest", "system-packages", "slsa", "jwt", "omnitrail"
]

def generate_questions_for_attestor(attestor: str, count: int = 20) -> list:
    """Use GPT-5 to generate diverse questions about an attestor"""

    prompt = f"""Generate {count} diverse, specific questions about the {attestor} attestor in Witness.

Questions should cover:
- What fields it captures
- When to use it
- How to configure it
- Integration examples
- Rego validation patterns
- Troubleshooting
- Real-world use cases
- Security implications

Make questions natural and varied (beginner to expert level).

Output as JSON array of strings:
["question 1", "question 2", ...]"""

    response = client.chat.completions.create(
        model='gpt-5',
        messages=[
            {'role': 'system', 'content': 'You generate diverse technical questions.'},
            {'role': 'user', 'content': prompt}
        ],
        max_completion_tokens=2000
    )

    try:
        content = response.choices[0].message.content
        # Extract JSON array
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
    except:
        pass

    return []

def generate_answer_for_question(attestor: str, question: str) -> str:
    """Use GPT-5 to generate answer"""

    # Get attestor schema first
    import subprocess
    result = subprocess.run(
        ['witness', 'attestors', 'schema', attestor],
        capture_output=True,
        text=True
    )

    schema = result.stdout if result.returncode == 0 else "Schema not available"

    prompt = f"""Answer this question about the {attestor} attestor in Witness:

Question: {question}

Attestor schema:
{schema[:1000]}

Provide a complete, practical answer with:
- Code examples
- Rego policies if relevant
- Real-world usage
- Best practices

Make it informative and actionable."""

    response = client.chat.completions.create(
        model='gpt-5',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt}
        ],
        max_completion_tokens=1500
    )

    return response.choices[0].message.content

def main():
    output_file = Path("data/gap_filled/auto_generated.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    target_per_attestor = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    print("="*70)
    print("Automated Gap-Filling Q/A Generator")
    print("="*70)
    print(f"Attestors with gaps: {len(GAP_ATTESTORS)}")
    print(f"Target per attestor: {target_per_attestor}")
    print(f"Total to generate: {len(GAP_ATTESTORS) * target_per_attestor}")
    print()

    total_generated = 0

    for attestor in GAP_ATTESTORS:
        print(f"\n{attestor}:")
        print(f"  Generating {target_per_attestor} questions...")

        questions = generate_questions_for_attestor(attestor, target_per_attestor)

        print(f"  Generated {len(questions)} questions")
        print(f"  Generating answers...")

        for i, question in enumerate(questions, 1):
            print(f"    {i}/{len(questions)}", end='\r')

            answer = generate_answer_for_question(attestor, question)

            example = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                    {"role": "assistant", "content": answer}
                ],
                "_metadata": {
                    "attestor": attestor,
                    "source": "gpt-5-generated",
                    "gap_filling": True
                }
            }

            with open(output_file, 'a') as f:
                f.write(json.dumps(example) + '\n')

            total_generated += 1

        print(f"  ✓ Completed {attestor}")

    print()
    print("="*70)
    print(f"✅ Generated {total_generated} gap-filling Q/A")
    print(f"   Output: {output_file}")
    print("="*70)

if __name__ == "__main__":
    main()
