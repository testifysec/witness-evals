#!/bin/bash
# Test suite for witness-expert model

echo "=========================================="
echo "Witness Expert Model Test Suite"
echo "=========================================="
echo ""

# Test cases
declare -a tests=(
    "How do I attest a Go build with witness?"
    "Write a Rego policy to enforce builds from the main branch"
    "How do I create a witness policy for a multi-step pipeline?"
    "What attestors should I use for a container build?"
    "How do I validate that files aren't tampered between build and test steps?"
)

for i in "${!tests[@]}"; do
    num=$((i+1))
    echo "Test $num/${#tests[@]}: ${tests[$i]}"
    echo "----------------------------------------"

    ollama run witness-expert "${tests[$i]}" 2>/dev/null | head -50

    echo ""
    echo "=========================================="
    echo ""
done

echo "✓ All tests complete!"
