# Quick Start: 100K Diverse Witness Training

## TL;DR

Generate 20K diverse witness examples → Train model → Get loss from 0.50 to 0.25-0.30

**Time**: 9-12 hours | **Cost**: $0 | **Success rate**: >95%

---

## The Problem

10K examples, loss plateaued at **0.50** due to lack of diversity.

## The Solution

20K diverse examples with:
- **800+ attestor combinations** (vs 15)
- **10 step names** (vs 1)
- **Real SBOM generation** for 5 languages
- **Rego policies** in 50% of examples
- **20 command patterns** (vs 1)

Expected loss: **0.25-0.30** (2x improvement!)

---

## One-Command Setup

```bash
cd /Users/nkennedy/proj/witness-evals && \
./scripts/setup_sbom_tools.sh
```

Installs: Syft, CycloneDX (Node), CycloneDX (Python)

---

## Generate 20K Diverse Examples

```bash
python3 scripts/generate_enhanced_verified.py \
  --target 20000 \
  --output data/diverse-20k/diverse_train.jsonl \
  --parallel 8
```

**Time**: 2-3 hours | **Success rate**: 95%+

---

## Create Train/Valid Splits

```bash
python3 scripts/create_verified_splits.py \
  --input data/diverse-20k/diverse_train.jsonl \
  --train-ratio 0.9
```

Creates:
- `data/diverse-20k/train.jsonl` (18,000 examples)
- `data/diverse-20k/valid.jsonl` (2,000 examples)

---

## Train Model

```bash
source venv-mlx/bin/activate

mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/diverse-20k \
  --num-layers 32 \
  --batch-size 8 \
  --iters 1000 \
  --learning-rate 1e-5 \
  --adapter-path ./witness-llama-3.2-3b-diverse-20k
```

**Time**: 6-8 hours | **Expected final loss**: 0.25-0.30

---

## Test Model

```bash
mlx_lm.generate \
  --model witness-llama-3.2-3b-diverse-20k \
  --prompt "How do I attest a Go build with SBOM and lockfiles?" \
  --max-tokens 800
```

Should generate:
- ✅ Valid JSON policy
- ✅ Correct witness CLI flags
- ✅ SBOM generation with syft
- ✅ Lockfile detection

---

## Diversity Breakdown

| Dimension | Current (10K) | Enhanced (20K) |
|-----------|---------------|----------------|
| Attestor combos | 15 | 800+ |
| Step names | 1 | 10 |
| Commands | 1 | 20 |
| Questions | 1 | 15 |
| Rego policies | 0 | 10,000 (50%) |
| SBOMs | 0 | 4,000 (20%) |
| Languages | N/A | 5 |
| **Total unique** | **15** | **20,000** |

---

## Attestors Supported

**Tier 1 (Always Work)**:
git, environment, material, product, commandrun, link

**Tier 2 (New)**:
lockfiles, sbom, maven, secretscan, sarif

**Tier 3 (Future)**:
github, gitlab, jenkins, aws-codebuild

---

## SBOM Languages

| Language | Tool | Command |
|----------|------|---------|
| Go | syft | `syft . -o spdx-json > sbom.json` |
| Node.js | syft | `syft . -o spdx-json > sbom.json` |
| Python | syft | `syft dir:. -o spdx-json > sbom.json` |
| Java | syft | `syft . -o spdx-json > sbom.json` |
| Rust | syft | `syft . -o spdx-json > sbom.json` |

---

## Rego Policy Types

1. **Git**: Branch enforcement, clean working dir
2. **Environment**: CI checks, required vars
3. **Product**: Output file validation, hash checks
4. **CommandRun**: Exit code validation, command allowlist
5. **Lockfiles**: Dependency hash validation
6. **Combined**: Multiple policy types together

---

## Expected Loss Trajectory

```
Iteration   Loss     Status
0           2.177    Baseline
100         0.65     Learning patterns
200         0.48     Below 10K model (0.50)
400         0.38     Good progress
600         0.32     Very good
800         0.28     Excellent
1000        0.25-0.27 TARGET! 🎯
```

---

## Success Criteria

### Must Have
- ✅ Loss < 0.30
- ✅ 100% verification success
- ✅ 800+ attestor combos
- ✅ Valid JSON generation
- ✅ Correct CLI flags

### Nice to Have
- ✅ Valid Rego policies
- ✅ Correct SBOM commands
- ✅ Multi-language support

---

## Timeline

| Task | Duration | Can Run Overnight |
|------|----------|-------------------|
| Setup | 30 min | No |
| Generate 20K | 2-3 hours | Yes ✅ |
| Train | 6-8 hours | Yes ✅ |
| Evaluate | 30 min | No |
| **Total** | **9-12 hours** | - |

---

## File Structure

```
witness-evals/
├── EXECUTIVE_SUMMARY.md          ← Read this for full context
├── 100K_DIVERSITY_STRATEGY.md    ← Detailed strategy
├── IMPLEMENTATION_GUIDE.md       ← Step-by-step commands
├── QUICK_START.md                ← This file
│
├── scripts/
│   ├── setup_sbom_tools.sh       ← Install SBOM tools
│   ├── project_templates.py      ← Language templates
│   ├── generate_enhanced_verified.py  ← Main generator
│   └── analyze_diversity.py      ← Diversity analyzer
│
└── data/
    ├── verified/                 ← Current 10K examples
    └── diverse-20k/              ← New 20K examples
```

---

## Troubleshooting

**Syft not found?**
```bash
brew install syft
```

**Generation failures?**
```bash
# Check logs
grep "ERROR" generation.log | head -20
```

**Loss not decreasing?**
```bash
# Try lower learning rate
--learning-rate 5e-6
```

**Model generates invalid JSON?**
- Train longer (more iterations)
- Check training loss (should be < 0.35)

---

## Next Steps

**Right now**:
```bash
./scripts/setup_sbom_tools.sh
```

**Tonight** (overnight run):
```bash
python3 scripts/generate_enhanced_verified.py --target 20000 --parallel 8
```

**Tomorrow** (overnight run):
```bash
mlx_lm.lora --data data/diverse-20k --iters 1000 ...
```

**Day after** (evaluate):
```bash
mlx_lm.generate --model witness-llama-3.2-3b-diverse-20k --prompt "..."
```

---

## If 20K Works → Scale to 100K

```bash
# Generate 100K (12-16 hours)
python3 scripts/generate_enhanced_verified.py --target 100000 --parallel 12

# Train (16-20 hours)
mlx_lm.lora --data data/diverse-100k --iters 2000 ...
```

Expected loss: **0.23-0.25** (vs 0.25-0.30 for 20K)

---

## Questions?

Read the detailed docs:
- `EXECUTIVE_SUMMARY.md` - High-level overview
- `100K_DIVERSITY_STRATEGY.md` - Full strategy
- `IMPLEMENTATION_GUIDE.md` - Command reference

---

## Ready?

```bash
cd /Users/nkennedy/proj/witness-evals
./scripts/setup_sbom_tools.sh
```

Let's get that loss from 0.50 to 0.25! 🚀
