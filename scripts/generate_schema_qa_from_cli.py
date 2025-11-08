#!/usr/bin/env python3
"""
Generate comprehensive attestor schema Q/A using `witness attestors schema`.

Uses the official JSON schemas from witness CLI to generate:
- 10-20 Q/A per attestor
- Field-level questions
- Type information
- Required vs optional fields
- Multiple question variations

Target: 5,000-10,000 schema Q/A pairs from official source of truth.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

# Get attestor list from witness CLI
def get_attestor_list() -> List[str]:
    """Get list of all attestors from witness"""
    result = subprocess.run(
        ["witness", "attestors", "list"],
        capture_output=True,
        text=True
    )

    attestors = []
    for line in result.stdout.split('\n'):
        if '|' in line and 'NAME' not in line and '---' not in line:
            parts = [p.strip() for p in line.split('|')]
            if len(parts) > 1 and parts[1]:
                name = parts[1].replace(' (default)', '').replace(' (always run)', '').strip()
                if name and name != 'NAME':
                    attestors.append(name)

    return attestors

def get_attestor_schema(attestor: str) -> Dict:
    """Get JSON schema for an attestor"""
    result = subprocess.run(
        ["witness", "attestors", "schema", attestor],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except:
        return None

def extract_fields_from_schema(schema: Dict) -> Dict[str, Dict]:
    """Extract field names, types, and required status from JSON schema"""
    if not schema or '$defs' not in schema:
        return {}

    # Get main definition (usually first one or named after attestor)
    defs = schema['$defs']
    main_def = None

    # Try to find Attestor definition
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
        # Handle boolean field_def (additionalProperties: true/false)
        if not isinstance(field_def, dict):
            continue

        field_type = field_def.get('type', 'unknown')

        # Handle references
        if '$ref' in field_def:
            ref = field_def['$ref'].split('/')[-1]
            field_type = ref

        # Handle arrays
        if field_type == 'array' and 'items' in field_def:
            if isinstance(field_def['items'], dict):
                item_type = field_def['items'].get('type', 'object')
                field_type = f'array of {item_type}'

        fields[field_name] = {
            'type': field_type,
            'required': field_name in required
        }

    return fields

def create_attestor_qa(attestor: str, fields: Dict[str, Dict]) -> List[Dict]:
    """Create comprehensive Q/A for an attestor"""
    examples = []

    # Q1: Overview - What fields does attestor capture?
    field_list = "\n".join([
        f"- `{fname}` ({finfo['type']}){'  **required**' if finfo['required'] else ''}"
        for fname, finfo in fields.items()
    ])

    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"What fields does the {attestor} attestor capture?"},
            {"role": "assistant", "content": f"""The {attestor} attestor captures these fields:

{field_list}

**Usage**:
```bash
witness run --step build \\
  --attestations {attestor} \\
  -k key.pem -o attestation.json \\
  -- <your-command>
```

All fields are automatically captured when you include `{attestor}` in `--attestations`."""}
        ]
    })

    # Q2: Schema structure
    examples.append({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Show me the JSON schema for {attestor} attestations."},
            {"role": "assistant", "content": f"""The {attestor} attestor has {len(fields)} fields:

**Required fields**:
{chr(10).join([f"- `{f}`" for f, info in fields.items() if info['required']])}

**Optional fields**:
{chr(10).join([f"- `{f}`" for f, info in fields.items() if not info['required']])}

**Full schema** can be viewed with:
```bash
witness attestors schema {attestor}
```

**Example attestation**:
```json
{{
  {chr(10).join([f'  "{fname}": {get_example_value(finfo["type"])},' for fname, finfo in list(fields.items())[:5]])}
  ...
}}
```"""}
        ]
    })

    # Q3-N: Individual field questions
    for field_name, field_info in list(fields.items())[:20]:  # Limit to top 20 fields
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"What is the {field_name} field in {attestor} attestations?"},
                {"role": "assistant", "content": f"""The `{field_name}` field in {attestor} attestations:

**Type**: `{field_info['type']}`
**Required**: {"Yes" if field_info['required'] else "No"}

{get_field_description(attestor, field_name)}

**Accessed in Rego**:
```rego
package {attestor}

import rego.v1

deny contains msg if {{
    # Access the field
    value := input.{field_name}
    # Your validation logic here
}}
```"""}
            ]
        })

    return examples

def get_example_value(field_type: str) -> str:
    """Get example JSON value for a type"""
    examples = {
        'string': '"example"',
        'integer': '0',
        'boolean': 'true',
        'array': '[]',
        'object': '{}',
    }

    for type_key, ex_val in examples.items():
        if type_key in field_type.lower():
            return ex_val

    return '"..."'

def get_field_description(attestor: str, field: str) -> str:
    """Get description of what a field contains"""
    descriptions = {
        'commithash': '**Purpose**: The SHA hash of the current git commit\n**Example**: "a1b2c3d4e5f6..."',
        'branch': '**Purpose**: The current git branch name\n**Example**: "main", "develop", "feature/auth"',
        'author': '**Purpose**: The git commit author name\n**Example**: "John Doe"',
        'authoremail': '**Purpose**: The git commit author email\n**Example**: "john@example.com"',
        'hostname': '**Purpose**: The system hostname where attestation was created\n**Example**: "build-server-01.company.com"',
        'os': '**Purpose**: The operating system\n**Example**: "linux", "darwin", "windows"',
        'username': '**Purpose**: The current user\n**Example**: "ci-runner", "buildbot"',
        'cmd': '**Purpose**: The command executed as array\n**Example**: ["go", "build", "-o", "app"]',
        'exitcode': '**Purpose**: Exit code from command\n**Example**: 0 (success), 1 (failure)',
        'stdout': '**Purpose**: Standard output from command\n**Example**: "Build successful"',
        'stderr': '**Purpose**: Standard error from command\n**Example**: Error messages if any',
    }

    return descriptions.get(field, f'**Purpose**: Part of {attestor} attestation data')

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/schemas_from_cli.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print("Generating Schema Q/A from witness CLI...")
    print("="*60)

    # Get all attestors
    attestors = get_attestor_list()
    print(f"Found {len(attestors)} attestors\n")

    all_examples = []
    total_fields = 0

    for attestor in attestors:
        # Get schema
        schema = get_attestor_schema(attestor)

        if not schema:
            print(f"  ⚠️  {attestor}: No schema available")
            continue

        # Extract fields
        fields = extract_fields_from_schema(schema)

        if not fields:
            print(f"  ⚠️  {attestor}: No fields extracted")
            continue

        # Generate Q/A
        qa_examples = create_attestor_qa(attestor, fields)
        all_examples.extend(qa_examples)
        total_fields += len(fields)

        print(f"  ✓ {attestor}: {len(fields)} fields, {len(qa_examples)} Q/A")

    # Save
    with open(output_file, 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')

    print("="*60)
    print(f"✅ Generated {len(all_examples):,} schema Q/A pairs")
    print(f"   Total fields documented: {total_fields}")
    print(f"   Output: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")
    print()
    print("🎯 This teaches the model ALL attestor schemas from official source!")

if __name__ == "__main__":
    main()
