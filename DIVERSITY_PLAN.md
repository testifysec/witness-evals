# Diversity Enhancement Plan for Witness Training Data

## Current State (10K Examples)

### Limited Diversity
- **15 attestor combinations** (cycling through same patterns)
- **1 step name** (always "build")
- **1 question format**
- **1 command pattern**
- **No Rego policies**

**Result**: Model sees same patterns repeatedly → Loss plateaus at 0.50

## Enhanced Diversity Strategy

### Dimension 1: Attestor Combinations
**Current**: 15 combinations
**Enhanced**: 31 combinations (all possible from 5 safe attestors)

Safe attestors (no mocking needed):
- git, environment, material, product, file

All combinations:
- 5 singles
- 10 pairs
- 10 triples
- 5 quads
- 1 all-five

### Dimension 2: Step Names
**Current**: Always "build"
**Enhanced**: 10 step names

```
build, test, package, deploy, scan,
compile, lint, security-check, analyze, verify
```

### Dimension 3: User Question Phrasing
**Current**: 1 template
**Enhanced**: 7 templates

Examples:
- "How do I create..."
- "What's the setup for..."
- "Show me a working example..."
- "Walk me through..."
- etc.

### Dimension 4: Commands
**Current**: 1 pattern
**Enhanced**: 5 patterns

```bash
echo "Success" > output.txt
cat input.txt > output.txt
cp input.txt output.txt && echo "Done" >> output.txt
...
```

### Dimension 5: Rego Policies (NEW!)
**Current**: None
**Enhanced**: 4 policy types

Git policies:
- Branch enforcement
- Clean working directory

Environment policies:
- CI environment check

Product policies:
- Required output files

## Total Variations

**31 combinations × 10 steps × 7 questions × 5 commands = 10,850 variations**

Plus Rego policy variations = **20,000+ unique examples possible**

## Implementation Plan

### Phase 1: Generate Enhanced 20K Dataset
```bash
python3 scripts/generate_enhanced_verified.py --target 20000
```

Features:
- Random sampling from all dimensions
- Some examples with Rego, some without
- Different step names
- Varied question phrasings
- Different command patterns

### Phase 2: Retrain with Enhanced Dataset
```bash
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/verified-enhanced \
  --num-layers 32 \
  --batch-size 8 \
  --iters 1000 \
  --learning-rate 2e-5 \
  --adapter-path ./witness-expert-diverse
```

**Expected loss**: 0.25-0.30 (vs current 0.50)

## Why This Improves Loss

### 1. Reduces Overfitting
More diverse patterns prevent model from memorizing specific examples.

### 2. Better Generalization
Model learns the CONCEPT of witness, not specific commands.

### 3. Varied Context
Different step names, questions teach robustness.

### 4. Rego Policies
Adds another dimension of complexity and real-world usage.

### 5. Richer Training Signal
More variation = more for model to learn from each batch.

## Additional Future Enhancements

### Mock Servers for Complex Attestors
Create lightweight mocks for:
- **GitHub**: Mock GitHub API responses
- **GitLab**: Mock GitLab CI environment variables
- **AWS**: Mock EC2 metadata service
- **Docker**: Mock docker daemon socket

This would add:
- github, gitlab, jenkins (CI/CD)
- aws-iid, gcp-iit (cloud identity)
- docker, oci (containers)
- +15 more attestor types

**Potential**: 100+ attestor combinations, 50K+ examples

### Upstream Datatype Conformance
As you mentioned, use actual go-witness struct definitions:

```python
# Read from attestation/*.go files
def parse_attestor_schema(attestor_name):
    """Extract struct definition from go-witness source"""
    go_file = f"/Users/nkennedy/proj/go-witness/attestation/{attestor_name}/{attestor_name}.go"
    # Parse Go structs
    # Generate conformant JSON
    # Ensures 100% compatibility
```

## Next Steps

1. **Let current training finish** (~15-20 mins)
2. **Generate enhanced 20K dataset** (~1 hour)
3. **Retrain with improved hyperparameters** (~1 hour)
4. **Compare loss**: Should see 0.25-0.30 vs current 0.50

Want me to start generating the enhanced 20K dataset now (in parallel with current training)?
