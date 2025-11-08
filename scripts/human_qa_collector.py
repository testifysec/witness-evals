#!/usr/bin/env python3
"""
Interactive app to collect human Q/A for underrepresented topics.

Guides humans to contribute Q/A in knowledge gap areas:
- CI/CD platforms (GitHub, GitLab, Jenkins)
- Containers (Docker, OCI)
- SBOM generation
- Security scanning
- Cloud attestors
- Package managers
"""

import json
from pathlib import Path
import sys

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Knowledge gap areas
GAP_AREAS = {
    "1": {
        "name": "GitHub Actions Integration",
        "description": "How to use witness in GitHub Actions workflows",
        "example_questions": [
            "How do I integrate witness into my GitHub Actions workflow?",
            "What GitHub environment variables does the github attestor capture?",
            "Show me a complete GitHub Actions workflow with witness attestations"
        ]
    },
    "2": {
        "name": "Container/Docker Workflows",
        "description": "Docker builds, OCI images, container attestations",
        "example_questions": [
            "How do I attest a Docker build with witness?",
            "What does the oci attestor capture?",
            "How do I verify container image attestations?"
        ]
    },
    "3": {
        "name": "SBOM Generation",
        "description": "Software Bill of Materials with Syft, CycloneDX",
        "example_questions": [
            "How do I generate an SBOM with witness?",
            "How do I use syft with the sbom attestor?",
            "What fields does the sbom attestor capture?"
        ]
    },
    "4": {
        "name": "Security Scanning",
        "description": "Secret detection, SARIF, vulnerability scanning",
        "example_questions": [
            "How do I detect secrets with the secretscan attestor?",
            "What is SARIF and how does witness use it?",
            "How do I attest security scan results?"
        ]
    },
    "5": {
        "name": "Cloud Platform Attestors",
        "description": "AWS, GCP identity attestations",
        "example_questions": [
            "How does the aws-iid attestor work?",
            "What GCP metadata does gcp-iit capture?",
            "How do I verify cloud instance identity?"
        ]
    },
    "6": {
        "name": "Package Managers",
        "description": "Maven, lockfiles, dependency tracking",
        "example_questions": [
            "How do I attest a Maven build?",
            "What does the lockfiles attestor capture?",
            "How do I track dependency changes with witness?"
        ]
    },
    "7": {
        "name": "Advanced Rego Policies",
        "description": "Complex validation, multiple conditions, security enforcement",
        "example_questions": [
            "How do I write Rego with multiple conditions (AND/OR)?",
            "Show me Rego to validate multiple attestor fields together",
            "How do I use regex in Rego policies?"
        ]
    },
    "8": {
        "name": "Troubleshooting",
        "description": "Common errors, debugging, solutions",
        "example_questions": [
            "Why does witness verify fail with 'no verifiers present'?",
            "How do I debug a Rego policy that's failing?",
            "What does 'predicate type is not a collection' mean?"
        ]
    },
}

def show_menu():
    print("\n" + "="*70)
    print("Witness Training Data - Human Q/A Collector")
    print("="*70)
    print("\nKnowledge Gap Areas (choose one):")
    for key, area in GAP_AREAS.items():
        print(f"\n{key}. {area['name']}")
        print(f"   {area['description']}")

    print("\n0. Exit")
    print("="*70)

def collect_qa_for_area(area_key):
    area = GAP_AREAS[area_key]

    print(f"\n{'='*70}")
    print(f"Collecting Q/A for: {area['name']}")
    print(f"{'='*70}")
    print(f"\n{area['description']}\n")
    print("Example questions:")
    for i, eq in enumerate(area['example_questions'], 1):
        print(f"  {i}. {eq}")

    print(f"\n{'='*70}")
    print("Enter your question (or 'back' to return):")
    question = input("> ").strip()

    if question.lower() == 'back' or not question:
        return None

    print("\nEnter the answer (multi-line, end with empty line):")
    answer_lines = []
    while True:
        line = input()
        if not line:
            break
        answer_lines.append(line)

    answer = "\n".join(answer_lines)

    if not answer:
        print("Answer cannot be empty")
        return None

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer}
        ],
        "_metadata": {
            "source": "human",
            "gap_area": area['name']
        }
    }

def main():
    output_file = Path("data/human_contributed/qa_pairs.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    collected = []

    while True:
        show_menu()
        choice = input("\nChoose area (0-8): ").strip()

        if choice == '0':
            break

        if choice not in GAP_AREAS:
            print("Invalid choice")
            continue

        qa = collect_qa_for_area(choice)
        if qa:
            collected.append(qa)
            print(f"\n✓ Added! Total collected: {len(collected)}")

            # Save incrementally
            with open(output_file, 'a') as f:
                f.write(json.dumps(qa) + '\n')

    print(f"\n{'='*70}")
    print(f"Session complete!")
    print(f"Collected: {len(collected)} Q/A pairs")
    print(f"Saved to: {output_file}")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
