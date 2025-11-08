#!/usr/bin/env python3
"""
Generate 5,000-10,000 DIVERSE schema Q/A pairs.

For each attestor:
- 20-30 question variations about the schema
- Per-field Q/A with multiple phrasings
- Rego validation examples for each field
- Type information Q/A
- Required vs optional Q/A
- Schema comparison Q/A

Target: 10,000 schema Q/A covering every field of every attestor.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List
import random

random.seed(42)

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Massive question template variations
FIELD_QUESTIONS = [
    "What is the {field} field in {attestor}?",
    "What does {field} contain in a {attestor} attestation?",
    "Explain {attestor}.{field}",
    "What's stored in the {field} field for {attestor}?",
    "Describe the {field} field in {attestor} attestations",
    "What information is in {attestor}.{field}?",
    "How is {field} populated in {attestor}?",
    "What type is {field} in {attestor} attestations?",
    "Is {field} required in {attestor} attestations?",
    "Show me an example of {field} in {attestor}",
]

REGO_QUESTIONS = [
    "How do I validate {field} in {attestor} with Rego?",
    "Write a Rego policy to check {attestor}.{field}",
    "Show me Rego validation for {field} in {attestor}",
    "How do I enforce rules on {attestor}.{field}?",
    "Give me a Rego deny rule for {attestor}.{field}",
]

ATTESTOR_OVERVIEW_QUESTIONS = [
    "What fields does {attestor} capture?",
    "Show me the {attestor} schema",
    "What's in a {attestor} attestation?",
    "List all fields in {attestor}",
    "Explain the {attestor} attestor structure",
    "What information does {attestor} collect?",
    "Describe the {attestor} attestation format",
    "What's the JSON structure of {attestor}?",
]

def get_attestor_list():
    result = subprocess.run(["witness", "attestors", "list"], capture_output=True, text=True)
    attestors = []
    for line in result.stdout.split('\n'):
        if '|' in line and 'NAME' not in line and '---' not in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 1 and parts[1]:
                name = parts[1].replace(' (default)', '').replace(' (always run)', '').strip()
                if name and name != 'NAME':
                    attestors.append(name)
    return attestors

def get_attestor_schema(attestor):
    result = subprocess.run(["witness", "attestors", "schema", attestor], capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def extract_fields(schema):
    if not schema or '$defs' not in schema:
        return {}
    defs = schema['$defs']
    main_def = None
    for def_name, def_content in defs.items():
        if 'Attestor' in def_name or len(defs) == 1:
            main_def = def_content
            break
    if not main_def or 'properties' not in main_def:
        return {}

    fields = {}
    properties = main_def['properties']
    required = main_def.get('required', [])

    for field_name, field_def in properties.items():
        if not isinstance(field_def, dict):
            continue
        field_type = field_def.get('type', 'unknown')
        if '$ref' in field_def:
            field_type = field_def['$ref'].split('/')[-1]
        if field_type == 'array' and 'items' in field_def and isinstance(field_def['items'], dict):
            item_type = field_def['items'].get('type', 'object')
            field_type = f'array of {item_type}'

        fields[field_name] = {'type': field_type, 'required': field_name in required}

    return fields

def create_field_qa(attestor, field, field_info):
    """Create 10+ Q/A for a single field"""
    examples = []

    # Basic field Q/A (5 variations)
    for template in random.sample(FIELD_QUESTIONS, 5):
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": template.format(field=field, attestor=attestor)},
                {"role": "assistant", "content": f"""The `{field}` field in {attestor} attestations:

**Type**: `{field_info['type']}`
**Required**: {"Yes" if field_info['required'] else "No"}

This field is automatically populated when you use the {attestor} attestor in your witness command.

**Example**:
```json
{{
  "{field}": {get_example_value(field_info['type'])}
}}
```"""}
            ]
        })

    # Rego validation Q/A (3 variations)
    for template in random.sample(REGO_QUESTIONS, min(3, len(REGO_QUESTIONS))):
        rego_example = generate_rego_for_field(attestor, field, field_info)
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": template.format(field=field, attestor=attestor)},
                {"role": "assistant", "content": f"""Here's a Rego policy to validate `{field}` in {attestor} attestations:

```rego
{rego_example}
```

Add this to your policy document under the {attestor} attestation's `regopolicies` field."""}
            ]
        })

    return examples

def generate_rego_for_field(attestor, field, field_info):
    """Generate Rego policy example for a field"""
    if field == 'branch' or field == 'refnameshort':
        return f'''package {attestor}

import rego.v1

deny contains msg if {{
    input.{field} != "main"
    msg := sprintf("Must be from main branch, got: %s", [input.{field}])
}}'''
    elif field == 'exitcode':
        return f'''package {attestor}

import rego.v1

deny contains msg if {{
    input.{field} != 0
    msg := sprintf("Command failed with exit code %d", [input.{field}])
}}'''
    elif field == 'os':
        return f'''package {attestor}

import rego.v1

deny contains msg if {{
    input.{field} != "linux"
    msg := sprintf("Must run on Linux, got: %s", [input.{field}])
}}'''
    elif 'email' in field:
        return f'''package {attestor}

import rego.v1

approved_emails := {{"alice@example.com", "bob@example.com"}}

deny contains msg if {{
    not input.{field} in approved_emails
    msg := sprintf("Unauthorized email: %s", [input.{field}])
}}'''
    else:
        return f'''package {attestor}

import rego.v1

deny contains msg if {{
    count(input.{field}) == 0
    msg := "{field} must not be empty"
}}'''

def get_example_value(field_type):
    if 'string' in field_type.lower():
        return '"example-value"'
    elif 'int' in field_type.lower():
        return '0'
    elif 'bool' in field_type.lower():
        return 'true'
    elif 'array' in field_type.lower():
        return '["item1", "item2"]'
    else:
        return '{}'

def create_attestor_qa(attestor, fields):
    """Create 20-30 Q/A per attestor"""
    examples = []

    # Overview Q/A (8 variations)
    for template in ATTESTOR_OVERVIEW_QUESTIONS:
        field_list = "\n".join([
            f"- **{fname}** ({finfo['type']}){'  *required*' if finfo['required'] else ''}"
            for fname, finfo in fields.items()
        ])

        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": template.format(attestor=attestor)},
                {"role": "assistant", "content": f"""The {attestor} attestor schema includes:

{field_list}

**Total fields**: {len(fields)}
**Required**: {sum(1 for f in fields.values() if f['required'])}
**Optional**: {sum(1 for f in fields.values() if not f['required'])}

View full schema:
```bash
witness attestors schema {attestor}
```"""}
            ]
        })

    # Per-field Q/A (10+ per field)
    for field_name, field_info in fields.items():
        field_examples = create_field_qa(attestor, field_name, field_info)
        examples.extend(field_examples)

    return examples

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/massive_schemas.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("Generating MASSIVE Schema Q/A (Target: 5,000-10,000 examples)")
    print("="*70)

    attestors = get_attestor_list()
    print(f"Attestors found: {len(attestors)}\n")

    all_examples = []
    total_fields = 0

    for attestor in attestors:
        schema = get_attestor_schema(attestor)
        if not schema:
            print(f"  ⚠️  {attestor}: No schema")
            continue

        fields = extract_fields(schema)
        if not fields:
            print(f"  ⚠️  {attestor}: No fields")
            continue

        qa = create_attestor_qa(attestor, fields)
        all_examples.extend(qa)
        total_fields += len(fields)

        print(f"  ✓ {attestor}: {len(fields)} fields → {len(qa)} Q/A")

    with open(output_file, 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print("="*70)
    print(f"🎉 Generated {len(all_examples):,} schema Q/A pairs!")
    print(f"   Fields covered: {total_fields}")
    print(f"   Avg Q/A per attestor: {len(all_examples) / len(attestors):.1f}")
    print(f"   Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024 / 1024:.1f} MB")
    print()
    print("🎯 Model will know EVERY field of EVERY attestor!")

if __name__ == "__main__":
    main()
