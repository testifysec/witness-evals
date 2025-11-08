#!/usr/bin/env python3
"""
Generate edge case examples - boundary conditions and unusual scenarios.

Edge cases:
- Empty fields
- Null/missing values
- Very long strings
- Special characters
- Array edge cases (empty, single item, many items)
- Type mismatches
- Encoding issues
"""

import json
from pathlib import Path

SYSTEM_PROMPT = """You are an expert in the Witness supply chain attestation framework. You help users instrument CI/CD pipelines with witness, create policy documents, and write Rego policies to validate attestations. You understand all attestors in go-witness and how to use them effectively."""

EDGE_CASES = [
    {
        "case": "empty_commit_message",
        "question": "How do I handle empty commit messages in Rego policies?",
        "answer": """Handle empty commit messages by checking string length:

```rego
package git

import rego.v1

# Require non-empty commit message
deny contains msg if {
    count(input.commitmessage) == 0
    msg := "Commit message cannot be empty"
}

# Or enforce minimum length
deny contains msg if {
    count(input.commitmessage) < 10
    msg := sprintf("Commit message too short: %d chars", [count(input.commitmessage)])
}
```

**Edge cases to handle**:
- Empty string: `""`
- Whitespace only: `"   "`
- Single character: `"x"`

**Robust validation**:
```rego
import strings

deny contains msg if {
    trimmed := trim_space(input.commitmessage)
    count(trimmed) == 0
    msg := "Commit message is empty or whitespace"
}
```"""
    },

    {
        "case": "no_remote_urls",
        "question": "What if git.remotes is empty in my attestation?",
        "answer": """Handle empty git remotes array:

```rego
package git

import rego.v1

# Allow empty remotes for local repos
# Or require at least one remote for production builds

deny contains msg if {
    count(input.remotes) == 0
    msg := "No git remotes configured - not a cloned repository"
}

# Validate remote URL format
deny contains msg if {
    some remote in input.remotes
    not startswith(remote, "https://")
    not startswith(remote, "git@")
    msg := sprintf("Invalid remote URL: %s", [remote])
}
```

**When remotes are empty**:
- Local `git init` repositories
- Detached working trees
- Submodules

**Production recommendation**: Require remotes to ensure builds are from version-controlled code."""
    },

    {
        "case": "status_map_empty",
        "question": "How do I validate git.status when it might be empty?",
        "answer": """The `status` field is a map that can be empty (clean working directory) or contain modified files:

```rego
package git

import rego.v1

# Clean working directory (status is empty map)
deny contains msg if {
    count(input.status) > 0
    msg := "Working directory must be clean"
}

# Or allow specific files
allowed_modified := {"go.sum", "package-lock.json"}

deny contains msg if {
    some file, status in input.status
    not file in allowed_modified
    msg := sprintf("Unexpected modified file: %s", [file])
}
```

**Edge cases**:
- `status: {}` - Clean directory (valid)
- `status: {"file.go": {"worktree": "modified"}}` - Has changes
- `status: null` - Should not happen

**Type-safe check**:
```rego
deny contains msg if {
    not is_object(input.status)
    msg := "status must be an object"
}
```"""
    },

    {
        "case": "exitcode_negative",
        "question": "Can exitcode be negative or very large?",
        "answer": """Exit codes are typically 0-255, but Rego should handle edge cases:

```rego
package commandrun

import rego.v1

# Standard validation
deny contains msg if {
    input.exitcode != 0
    msg := sprintf("Command failed: exit code %d", [input.exitcode])
}

# Handle edge cases
deny contains msg if {
    input.exitcode < 0
    msg := sprintf("Invalid negative exit code: %d", [input.exitcode])
}

deny contains msg if {
    input.exitcode > 255
    msg := sprintf("Exit code out of range: %d", [input.exitcode])
}
```

**Possible values**:
- 0: Success
- 1-255: Standard errors
- -1: Sometimes returned by process errors (rare)
- 128+N: Killed by signal N

**Robust validation**:
```rego
valid_exitcode(code) if {
    code >= 0
    code <= 255
}

deny contains msg if {
    not valid_exitcode(input.exitcode)
    msg := "Exit code outside valid range"
}
```"""
    },

    {
        "case": "array_fields_empty",
        "question": "How do I handle empty arrays in attestations?",
        "answer": """Many attestor fields are arrays that might be empty:

**Git arrays**:
- `parenthashes`: Empty for initial commit
- `tags`: Empty if no tags point to commit
- `refs`: Usually non-empty

```rego
package git

import rego.v1

# Handle empty parent hashes (initial commit)
is_initial_commit if {
    count(input.parenthashes) == 0
}

deny contains msg if {
    is_initial_commit
    input.branch != "main"
    msg := "Initial commit must be on main branch"
}

# Require at least one tag for releases
deny contains msg if {
    count(input.tags) == 0
    msg := "Release builds must have git tags"
}

# Safe array iteration
deny contains msg if {
    count(input.remotes) > 0  # Check not empty first
    some remote in input.remotes
    not contains(remote, "github.com")
    msg := "Must use GitHub remotes"
}
```

**Pattern**: Always check `count(array) > 0` before iterating."""
    },

    {
        "case": "special_characters",
        "question": "How do I handle special characters in fields like branch names?",
        "answer": """Handle special characters with string functions and regex:

```rego
package git

import rego.v1

# Allow alphanumeric and hyphens/underscores
valid_branch_name(name) if {
    regex.match(`^[a-zA-Z0-9/_-]+$`, name)
}

deny contains msg if {
    not valid_branch_name(input.branch)
    msg := sprintf("Invalid characters in branch name: %s", [input.branch])
}

# Handle slashes in branch names (feature/foo)
deny contains msg if {
    startswith(input.branch, "feature/")
    msg := "Feature branches not allowed in production"
}

# Escape special chars in error messages
deny contains msg if {
    contains(input.branch, " ")
    msg := sprintf("Branch name contains spaces: '%s'", [input.branch])
}
```

**Common special cases**:
- Slashes: `feature/auth`, `release/v1.0`
- Underscores: `build_artifacts`
- Hyphens: `bug-fix-123`
- Dots: `release-1.0.0`

**Validation tip**: Use regex for strict validation."""
    },
]

def main():
    output_file = Path("/Users/nkennedy/proj/witness-evals/data/conceptual/edge_cases.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    examples = []
    for case_data in EDGE_CASES:
        examples.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": case_data['question']},
                {"role": "assistant", "content": case_data['answer']}
            ]
        })

    with open(output_file, 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + '\n')

    print(f"✓ Generated {len(examples)} edge case examples")
    print(f"  Output: {output_file}")

if __name__ == "__main__":
    main()
