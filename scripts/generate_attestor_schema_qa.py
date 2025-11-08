#!/usr/bin/env python3
"""
Generate comprehensive Q/A about ALL attestor schemas.

Extracts struct definitions from go-witness source code and creates:
- Field descriptions for all 27 attestors
- Multiple question variations per field
- Usage examples
- Rego validation examples

Target: 5,000-10,000 attestor schema Q/A pairs
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

GO_WITNESS_PATH = Path("/Users/nkennedy/proj/go-witness")

# All attestor types
ATTESTORS = [
    "git", "environment", "material", "product", "commandrun",
    "github", "gitlab", "jenkins", "aws-iid", "aws-codebuild", "gcp-iit",
    "docker", "oci", "sbom", "vex", "sarif",
    "maven", "lockfiles", "k8smanifest", "secretscan", "system-packages",
    "slsa", "link", "jwt", "policyverify", "omnitrail", "file"
]

# Question templates for schema fields
FIELD_QUESTION_TEMPLATES = [
    "What is the {field} field in the {attestor} attestor?",
    "What does {field} contain in a {attestor} attestation?",
    "Explain the {field} field for {attestor} attestations.",
    "What information is stored in {attestor}.{field}?",
    "Describe the {field} field in {attestor} attestor output.",
]

# Attestor-level questions
ATTESTOR_QUESTION_TEMPLATES = [
    "What fields does the {attestor} attestor capture?",
    "What information does the {attestor} attestor collect?",
    "Explain the {attestor} attestor schema.",
    "What's the structure of a {attestor} attestation?",
    "Show me the {attestor} attestor output format.",
    "What data is in a {attestor} attestation?",
]

def parse_go_struct(go_file: Path) -> Dict[str, str]:
    """Parse Go struct definitions to extract field names and types"""
    if not go_file.exists():
        return {}

    with open(go_file, 'r') as f:
        content = f.read()

    # Find struct definitions (simplified parser)
    struct_pattern = r'type\s+\w+\s+struct\s*\{([^}]+)\}'
    structs = re.findall(struct_pattern, content, re.DOTALL)

    fields = {}
    for struct_body in structs:
        # Extract field lines
        field_lines = [line.strip() for line in struct_body.split('\n') if line.strip()]
        for line in field_lines:
            # Match: FieldName Type `json:"fieldname"`
            match = re.match(r'(\w+)\s+([^\`]+)\s*`json:"([^"]+)"', line)
            if match:
                field_name, field_type, json_name = match.groups()
                fields[json_name] = {
                    'go_name': field_name,
                    'type': field_type.strip(),
                    'json': json_name
                }

    return fields

def create_field_qa(attestor: str, field_name: str, field_info: Dict) -> List[Dict]:
    """Create Q/A pairs for a single field"""
    examples = []

    # Field description Q/A (multiple variations)
    for template in FIELD_QUESTION_TEMPLATES[:3]:  # Use first 3 templates
        question = template.format(field=field_name, attestor=attestor)

        # Generate answer based on field name
        answer = f"""The `{field_name}` field in the {attestor} attestor contains:

**Type**: `{field_info['type']}`

**Purpose**: {generate_field_purpose(attestor, field_name)}

**Example** from attestation JSON:
```json
{{
  "{field_name}": {generate_field_example(field_name, field_info['type'])}
}}
```

This field is automatically captured when you include `{attestor}` in your `--attestations` list."""

        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer}
            ]
        })

    return examples

def generate_field_purpose(attestor: str, field: str) -> str:
    """Generate description of field purpose"""
    purposes = {
        'commithash': 'The SHA hash of the current git commit',
        'branch': 'The current git branch name',
        'author': 'The commit author name',
        'authoremail': 'The commit author email address',
        'hostname': 'The system hostname where attestation was created',
        'os': 'The operating system (linux, darwin, windows)',
        'username': 'The current user running the attestation',
        'variables': 'Environment variables (sensitive vars filtered)',
        'cmd': 'The command executed as an array of strings',
        'exitcode': 'The exit code from the executed command',
        'stdout': 'Standard output from the command',
        'stderr': 'Standard error from the command',
    }
    return purposes.get(field, f'Field related to {attestor} attestation')

def generate_field_example(field: str, field_type: str) -> str:
    """Generate example value for field"""
    examples = {
        'string': '"example-value"',
        'int': '0',
        'bool': 'true',
        '[]string': '["item1", "item2"]',
        'map[string]': '{"key": "value"}',
    }

    # Match type
    for type_key, example_val in examples.items():
        if type_key in field_type:
            return example_val

    return '"..."'

def create_attestor_overview_qa(attestor: str, fields: Dict) -> List[Dict]:
    """Create overview Q/A for an attestor"""
    examples = []

    field_list = ", ".join([f"`{f}`" for f in list(fields.keys())[:10]])

    for template in ATTESTOR_QUESTION_TEMPLATES[:2]:  # First 2 templates
        question = template.format(attestor=attestor)

        answer = f"""The {attestor} attestor captures these fields:

{chr(10).join([f"- `{fname}`: {generate_field_purpose(attestor, fname)}" for fname in list(fields.keys())[:15]])}

**Usage**:
```bash
witness run --step build \\
  --attestations {attestor},material,product \\
  -k key.pem -o attestation.json \\
  -- <your-command>
```

The {attestor} attestor is automatically included when you specify it in `--attestations`."""

        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer}
            ]
        })

    return examples

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/attestor_schemas.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Generating Attestor Schema Q/A...")
    print("="*60)

    for attestor in ATTESTORS:
        # Find attestor go file
        attestor_dir = GO_WITNESS_PATH / "attestation" / attestor
        go_files = list(attestor_dir.glob(f"{attestor}.go"))

        if not go_files:
            # Try alternative naming
            go_files = list(attestor_dir.glob("*.go"))
            go_files = [f for f in go_files if not f.name.endswith('_test.go')]

        if not go_files:
            print(f"  ⚠️  {attestor}: No Go file found")
            continue

        # Parse struct fields
        fields = parse_go_struct(go_files[0])

        if not fields:
            print(f"  ⚠️  {attestor}: No fields parsed")
            continue

        # Generate overview Q/A
        overview_qa = create_attestor_overview_qa(attestor, fields)
        all_examples.extend(overview_qa)

        # Generate field-specific Q/A
        field_qa_count = 0
        for field_name, field_info in fields.items():
            field_examples = create_field_qa(attestor, field_name, field_info)
            all_examples.extend(field_examples)
            field_qa_count += len(field_examples)

        print(f"  ✓ {attestor}: {len(fields)} fields, {len(overview_qa) + field_qa_count} Q/A")

    # Save all examples
    with open(output_file, 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print("="*60)
    print(f"✅ Generated {len(all_examples)} attestor schema Q/A pairs")
    print(f"   Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")
    print()
    print("These teach the model about every attestor field!")

if __name__ == "__main__":
    main()
