# 100K Diverse Witness Training Examples Strategy

## Problem Analysis

**Current State (10K examples)**:
- Loss plateaued at **0.50**
- Only **15 attestor combinations** (cycling same patterns)
- **1 step name** (always "build")
- **1 question format**
- **1 command pattern**
- **No Rego policies**
- **No SBOM/real tool integration**

**Root Cause**: Model sees same patterns repeatedly → memorization instead of understanding

**Goal**: Generate 100K diverse examples to achieve loss of **0.25-0.30**

---

## Attestor Classification by Feasibility

### Tier 1: No Setup Required (DONE)
Already working in 10K dataset:
- ✅ `git` - Just needs git init
- ✅ `environment` - Just set env vars
- ✅ `material` - Just create input.txt
- ✅ `product` - Just creates output.txt
- ✅ `commandrun` - Always runs
- ✅ `link` - Always available

### Tier 2: Simple Setup (HIGH PRIORITY)
Can work locally with basic tools:
- `lockfiles` - Detect go.sum, package-lock.json, Cargo.lock, requirements.txt
- `sbom` - Use syft, cdx-gen, spdx-sbom-generator
- `maven` - Needs pom.xml file
- `secretscan` - Works on file content
- `sarif` - Provide SARIF JSON file

### Tier 3: Mock Environment Required (MEDIUM PRIORITY)
Need environment variable mocking:
- `github` - Mock GITHUB_* env vars
- `gitlab` - Mock CI_* env vars
- `jenkins` - Mock JENKINS_* env vars
- `aws-codebuild` - Mock CODEBUILD_* env vars

### Tier 4: Complex Setup (LOW PRIORITY)
Require infrastructure/services:
- `docker` - Needs docker daemon
- `oci` - Needs OCI registry
- `k8smanifest` - Needs kubectl/k8s
- `aws-iid` - Needs AWS metadata service
- `gcp-iit` - Needs GCP metadata
- `jwt` - Needs JWT token
- `omnitrail` - System-specific
- `system-packages` - System-specific

---

## Diversity Dimensions

### 1. Attestor Combinations (PRIMARY)

**Current**: 15 combinations from 5 attestors
**Target**: 1000+ combinations from 15+ attestors

#### Phase 1: Tier 1 + Tier 2 (11 attestors)
```
git, environment, material, product, commandrun, link,
lockfiles, sbom, maven, secretscan, sarif
```

**Combinations**:
- Singles: 11
- Pairs: 55 (C(11,2))
- Triples: 165 (C(11,3))
- Quads: 330 (C(11,4))
- 5-way: 462 (C(11,5))
- 6-way: 462 (C(11,6))
- Total: **1,485 combinations**

#### Phase 2: Add Tier 3 (15 attestors total)
```
+ github, gitlab, jenkins, aws-codebuild
```
**Total combinations**: 32,767 (2^15 - 1)

### 2. Step Names (10 variations)

**Current**: Always "build"
**Target**:
```
build, test, package, deploy, scan, compile, lint,
security-check, analyze, verify
```

### 3. Command Patterns (20 variations)

**Current**: `bash -c "echo 'Success' > output.txt"`

**Target - Real-world commands**:

#### Go/Generic
```bash
go build -o app ./cmd/main.go
go test ./...
make build
make test
```

#### Node
```bash
npm install
npm run build
npm test
npm run lint
```

#### Python
```bash
pip install -r requirements.txt
python -m pytest
python setup.py build
```

#### Java
```bash
mvn compile
mvn test
mvn package
gradle build
```

#### Rust
```bash
cargo build --release
cargo test
cargo clippy
```

#### Container
```bash
docker build -t app:latest .
tar czf app.tar.gz .
```

#### Security
```bash
trivy fs .
grype dir:.
gitleaks detect --no-git
```

#### Linting
```bash
golangci-lint run
eslint src/
pylint src/
```

### 4. User Question Phrasing (15 templates)

**Current**: 1 template

**Target**:
1. "How do I create a complete witness configuration for a {step} step with {attestors}?"
2. "What's the witness setup for {step} with {attestors} attestors?"
3. "Show me a working witness example for {step} using {attestors}"
4. "Walk me through setting up witness for {step} with {attestors}"
5. "I need to attest a {step} step with {attestors}. How do I do it?"
6. "Can you provide a verified witness config for {step} ({attestors})?"
7. "Help me set up witness attestation for {step} with {attestors}"
8. "What are the commands to attest {step} with {attestors}?"
9. "Create a witness workflow for {step} using {attestors} attestors"
10. "I want to use witness for {step} with {attestors}. What do I need?"
11. "Provide a complete example of {step} attestation with {attestors}"
12. "How would I configure witness to attest {step} with {attestors}?"
13. "Give me the witness commands for {step} attestation ({attestors})"
14. "What's the best way to attest {step} using {attestors}?"
15. "I'm trying to attest {step} with {attestors}. Show me how."

### 5. Rego Policies (NEW - HIGH VALUE)

**Current**: None

**Target**: 4 policy types

#### A. Git Policies
```rego
# Branch enforcement
deny[msg] {
  input.branch != "main"
  msg := "Must build from main branch"
}

# Clean working directory
deny[msg] {
  count(input.status.modified) > 0
  msg := "Working directory must be clean"
}

# Tag enforcement
deny[msg] {
  not startswith(input.tag, "v")
  msg := "Tags must start with 'v'"
}
```

#### B. Environment Policies
```rego
# CI enforcement
deny[msg] {
  input.variables.CI != "true"
  msg := "Must run in CI environment"
}

# Required variables
deny[msg] {
  required := ["CI", "BUILD_ID", "COMMIT_SHA"]
  missing := [v | v := required[_]; not input.variables[v]]
  count(missing) > 0
  msg := sprintf("Missing env vars: %v", [missing])
}
```

#### C. Product Policies
```rego
# Required output files
deny[msg] {
  required := ["app.tar.gz"]
  missing := [f | f := required[_]; not input[f]]
  count(missing) > 0
  msg := sprintf("Missing output files: %v", [missing])
}

# File hash validation
deny[msg] {
  expected := "sha256:abc123..."
  input["app.tar.gz"].digest.sha256 != expected
  msg := "Output file hash mismatch"
}
```

#### D. Command-Run Policies
```rego
# Exit code validation
deny[msg] {
  input.exitcode != 0
  msg := "Command must succeed (exit code 0)"
}

# Command allowlist
deny[msg] {
  allowed := ["go", "npm", "python", "make"]
  not startswith(input.cmd[0], allowed[_])
  msg := sprintf("Command not allowed: %s", [input.cmd[0]])
}
```

#### E. Lockfiles Policies
```rego
# Dependency hash validation
deny[msg] {
  lf := input.lockfiles[_]
  lf.type == "gomod"
  lf.digest.sha256 != "expected_hash"
  msg := "go.sum was modified"
}
```

#### F. SBOM Policies
```rego
# License compliance
deny[msg] {
  pkg := input.packages[_]
  pkg.licenseConcluded == "GPL-3.0"
  msg := sprintf("GPL license not allowed: %s", [pkg.name])
}

# Required dependencies
deny[msg] {
  required := ["github.com/spf13/cobra"]
  not has_package(required[_])
  msg := "Required dependency missing"
}
```

### 6. SBOM Tool Variations (NEW - HIGH VALUE)

**Target**: Real SBOM generation for different languages

#### Go Projects
```bash
# Setup
echo 'module example.com/app\ngo 1.21' > go.mod
echo 'require github.com/spf13/cobra v1.8.0' >> go.mod
go mod download

# Generate SBOM
witness run --step build \
  --attestations sbom \
  -- bash -c "syft . -o spdx-json > sbom.json"
```

#### Node Projects
```bash
# Setup
cat > package.json <<EOF
{
  "name": "app",
  "dependencies": {
    "express": "^4.18.0"
  }
}
EOF
npm install

# Generate SBOM
witness run --step build \
  --attestations sbom \
  -- bash -c "cdx-gen -o sbom.json ."
```

#### Python Projects
```bash
# Setup
cat > requirements.txt <<EOF
flask==3.0.0
requests==2.31.0
EOF
pip install -r requirements.txt

# Generate SBOM
witness run --step build \
  --attestations sbom \
  -- bash -c "cyclonedx-py -o sbom.json"
```

#### Java Projects
```bash
# Setup
cat > pom.xml <<EOF
<project>
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId>
  <artifactId>app</artifactId>
  <version>1.0</version>
  <dependencies>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-core</artifactId>
      <version>6.0.0</version>
    </dependency>
  </dependencies>
</project>
EOF

# Generate SBOM
witness run --step build \
  --attestations sbom,maven \
  -- bash -c "cyclonedx-maven:makeAggregateBom"
```

#### Rust Projects
```bash
# Setup
cat > Cargo.toml <<EOF
[package]
name = "app"
version = "0.1.0"

[dependencies]
serde = "1.0"
EOF

# Generate SBOM
witness run --step build \
  --attestations sbom,lockfiles \
  -- bash -c "syft . -o spdx-json > sbom.json"
```

### 7. Lockfiles Variations

**Target**: Real lockfile detection

```bash
# Go
echo "go.sum" > go.sum
# Attestor detects: type=gomod, hash=sha256:...

# Node
npm install  # Creates package-lock.json
# Attestor detects: type=npm, hash=sha256:...

# Python
pip freeze > requirements.txt
# Attestor detects: type=pip

# Rust
cargo build  # Creates Cargo.lock
# Attestor detects: type=cargo
```

### 8. CI Platform Mocking (Tier 3)

#### GitHub Actions Mock
```bash
export GITHUB_ACTIONS=true
export GITHUB_WORKFLOW="CI"
export GITHUB_RUN_ID="123456"
export GITHUB_REPOSITORY="testifysec/witness"
export GITHUB_SHA="abc123def456"
export GITHUB_REF="refs/heads/main"
export GITHUB_ACTOR="octocat"

witness run --step build --attestations github,git,environment ...
```

#### GitLab CI Mock
```bash
export CI=true
export GITLAB_CI=true
export CI_PIPELINE_ID="789"
export CI_PROJECT_NAME="witness"
export CI_COMMIT_SHA="abc123"
export CI_COMMIT_REF_NAME="main"
export CI_RUNNER_ID="1"

witness run --step build --attestations gitlab,git,environment ...
```

#### Jenkins Mock
```bash
export JENKINS_URL="http://jenkins.local"
export BUILD_NUMBER="42"
export JOB_NAME="witness-build"
export BUILD_ID="2025-01-08_12-00-00"
export WORKSPACE="/var/jenkins/workspace"

witness run --step build --attestations jenkins,git,environment ...
```

---

## Total Diversity Calculation

**Phase 1 (Tier 1 + Tier 2 attestors)**:
- 1,485 attestor combinations
- × 10 step names
- × 15 question phrasings
- × 20 command patterns
- × 5 policy variations (none, git, env, product, combined)
= **22,275,000 possible unique examples**

**Sampling for 100K**:
- Ensures wide coverage across all dimensions
- No duplicate examples
- Balanced across attestor types
- Mix of simple and complex scenarios

---

## Implementation Plan

### Phase 1: Setup Attestor Infrastructure (Week 1)

#### Task 1.1: Install SBOM Tools
```bash
# Syft (supports all languages)
brew install syft

# CycloneDX CLI
npm install -g @cyclonedx/cyclonedx-npm
pip install cyclonedx-bom

# SPDX Tools
wget https://github.com/spdx/tools-golang/releases/latest
```

#### Task 1.2: Create Language Project Templates
```python
# scripts/templates/go_project.py
def create_go_project(workdir: Path):
    (workdir / "go.mod").write_text(
        "module example.com/app\ngo 1.21\n"
        "require github.com/spf13/cobra v1.8.0\n"
    )
    subprocess.run(["go", "mod", "download"], cwd=workdir)
    return ["go.mod", "go.sum"]

# scripts/templates/node_project.py
# scripts/templates/python_project.py
# scripts/templates/java_project.py
# scripts/templates/rust_project.py
```

#### Task 1.3: Create Mock Environment Setups
```python
# scripts/mocks/github_env.py
def mock_github_env():
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_WORKFLOW": "CI",
        "GITHUB_RUN_ID": str(random.randint(100000, 999999)),
        "GITHUB_REPOSITORY": "testifysec/witness",
        "GITHUB_SHA": hashlib.sha1(os.urandom(20)).hexdigest(),
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_ACTOR": "github-bot",
    }

# scripts/mocks/gitlab_env.py
# scripts/mocks/jenkins_env.py
```

#### Task 1.4: Create Rego Policy Generator
```python
# scripts/policies/rego_generator.py
class RegoGenerator:
    def generate_git_policy(self, branch="main"):
        return f'''
package git
deny[msg] {{
  input.branch != "{branch}"
  msg := "Must build from {branch} branch"
}}
'''

    def generate_env_policy(self, required_vars):
        # ...

    def generate_product_policy(self, expected_files):
        # ...
```

### Phase 2: Enhanced Generator Script (Week 1)

Create `scripts/generate_100k_diverse.py`:

```python
#!/usr/bin/env python3
"""
Generate 100K diverse, formally verified witness training examples.

Features:
- 11 attestor types (Tier 1 + Tier 2)
- 10 step names
- 20 command patterns
- 15 question phrasings
- 6 Rego policy types
- Real SBOM generation
- Real lockfile detection
- CI platform mocking
"""

import random
import itertools
from dataclasses import dataclass
from typing import List, Set

@dataclass
class ExampleSpec:
    attestors: List[str]
    step_name: str
    command_pattern: str
    question_template: str
    policy_type: Optional[str]
    language: Optional[str]  # For SBOM/lockfiles

class DiverseExampleGenerator:
    def __init__(self):
        self.attestors_tier1 = ["git", "environment", "material", "product", "commandrun", "link"]
        self.attestors_tier2 = ["lockfiles", "sbom", "maven", "secretscan", "sarif"]
        self.step_names = ["build", "test", "package", "deploy", "scan",
                          "compile", "lint", "security-check", "analyze", "verify"]
        self.question_templates = [
            "How do I create a complete witness configuration for a {step} step with {attestors}?",
            "What's the witness setup for {step} with {attestors} attestors?",
            # ... 15 total
        ]
        self.command_patterns = self.load_command_patterns()
        self.policy_types = ["none", "git", "environment", "product", "commandrun", "combined"]

        self.generated_specs = set()  # Track uniqueness

    def generate_unique_spec(self) -> ExampleSpec:
        """Generate a unique example specification"""
        while True:
            # Randomly select dimensions
            num_attestors = random.randint(1, 7)
            all_attestors = self.attestors_tier1 + self.attestors_tier2
            attestors = sorted(random.sample(all_attestors, num_attestors))

            step_name = random.choice(self.step_names)
            question_template = random.choice(self.question_templates)
            policy_type = random.choice(self.policy_types)

            # Select command pattern based on attestors
            command_pattern = self.select_command_pattern(attestors)

            # Language if using sbom/lockfiles
            language = self.select_language(attestors)

            spec = ExampleSpec(
                attestors=attestors,
                step_name=step_name,
                command_pattern=command_pattern,
                question_template=question_template,
                policy_type=policy_type,
                language=language
            )

            # Check uniqueness
            spec_hash = hash((
                tuple(attestors),
                step_name,
                command_pattern,
                question_template,
                policy_type
            ))

            if spec_hash not in self.generated_specs:
                self.generated_specs.add(spec_hash)
                return spec

    def generate_and_verify_example(self, spec: ExampleSpec) -> Optional[dict]:
        """Generate example from spec and verify it works"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            # 1. Setup based on attestors
            self.setup_environment(workdir, spec)

            # 2. Generate keys
            key_pem, pub_pem = self.create_keys(workdir)

            # 3. Run witness
            attestation_file = workdir / f"{spec.step_name}.att"
            success, stdout, stderr = self.run_witness_attestation(
                workdir, spec, key_pem, attestation_file
            )

            if not success:
                return None

            # 4. Create policy (with Rego if specified)
            policy = self.create_policy(workdir, spec, pub_pem, attestation_file)

            # 5. Sign policy
            signed_policy = self.sign_policy(workdir, policy, key_pem)

            # 6. Verify
            artifact_file = self.get_artifact_file(workdir, spec)
            success, stdout, stderr = self.run_witness_verify(
                workdir, signed_policy, pub_pem, attestation_file, artifact_file
            )

            if not success:
                return None

            # 7. Create training example
            return self.create_training_example(spec, policy, signed_policy)

    def setup_environment(self, workdir: Path, spec: ExampleSpec):
        """Setup files/environment based on attestors"""
        # Git setup
        if "git" in spec.attestors:
            self.init_git_repo(workdir)

        # Material files
        if "material" in spec.attestors:
            (workdir / "input.txt").write_text("source data\n")

        # SBOM setup
        if "sbom" in spec.attestors:
            if spec.language == "go":
                create_go_project(workdir)
            elif spec.language == "node":
                create_node_project(workdir)
            # ...

        # Lockfiles setup
        if "lockfiles" in spec.attestors:
            if spec.language == "go":
                (workdir / "go.sum").write_text("example.com/pkg v1.0.0 h1:...\n")
            elif spec.language == "node":
                subprocess.run(["npm", "install"], cwd=workdir)

        # Maven setup
        if "maven" in spec.attestors:
            create_maven_pom(workdir)

        # Secretscan setup (create file with test secret)
        if "secretscan" in spec.attestors:
            (workdir / "config.yaml").write_text("api_key: fake_key_12345\n")

        # SARIF setup
        if "sarif" in spec.attestors:
            create_sarif_report(workdir)

    def create_policy(self, workdir: Path, spec: ExampleSpec, pub_pem: Path, att_file: Path):
        """Create policy document with optional Rego"""
        # Extract key ID
        keyid = self.extract_keyid(att_file)
        pubkey_b64 = self.encode_pubkey(pub_pem)

        policy = {
            "expires": "2026-12-31T23:59:59Z",
            "steps": {
                spec.step_name: {
                    "name": spec.step_name,
                    "attestations": [
                        {"type": f"https://witness.dev/attestations/{att}/v0.1"}
                        for att in spec.attestors
                    ],
                    "functionaries": [{
                        "type": "publickey",
                        "publickeyid": keyid
                    }]
                }
            },
            "publickeys": {
                keyid: {
                    "keyid": keyid,
                    "key": pubkey_b64
                }
            }
        }

        # Add Rego if specified
        if spec.policy_type != "none":
            policy["steps"][spec.step_name]["policyrules"] = [
                {
                    "module": f"policies/{spec.policy_type}.rego",
                    "attestor": spec.policy_type
                }
            ]

        return policy

def main():
    generator = DiverseExampleGenerator()
    output_file = Path("data/diverse-100k/diverse_train.jsonl")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    target = 100000
    generated = 0
    failed = 0

    print(f"🎯 Generating {target} diverse examples...")
    print(f"📊 Attestors: {len(generator.attestors_tier1 + generator.attestors_tier2)}")
    print(f"📊 Potential combinations: 22M+")
    print(f"📊 Target unique examples: {target}")
    print()

    with open(output_file, 'w') as f:
        while generated < target:
            # Generate unique spec
            spec = generator.generate_unique_spec()

            # Generate and verify example
            example = generator.generate_and_verify_example(spec)

            if example:
                f.write(json.dumps(example) + '\n')
                generated += 1

                if generated % 100 == 0:
                    print(f"✓ {generated}/{target} ({failed} failed)")
            else:
                failed += 1

    print(f"\n✅ Generated {generated} verified examples")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success rate: {generated/(generated+failed)*100:.1f}%")

if __name__ == "__main__":
    main()
```

### Phase 3: Parallel Generation (Week 2)

Use multiprocessing for speed:

```python
from multiprocessing import Pool, cpu_count

def generate_batch(batch_id: int, batch_size: int):
    """Generate a batch of examples in parallel"""
    generator = DiverseExampleGenerator()
    examples = []

    for i in range(batch_size):
        spec = generator.generate_unique_spec()
        example = generator.generate_and_verify_example(spec)
        if example:
            examples.append(example)

    return examples

def main():
    target = 100000
    num_processes = cpu_count()
    batch_size = 100
    num_batches = target // batch_size

    print(f"🚀 Using {num_processes} parallel processes")
    print(f"📦 Generating {num_batches} batches of {batch_size} examples")

    with Pool(num_processes) as pool:
        results = pool.starmap(
            generate_batch,
            [(i, batch_size) for i in range(num_batches)]
        )

    # Flatten and write
    all_examples = [ex for batch in results for ex in batch]

    with open("data/diverse-100k/train.jsonl", 'w') as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + '\n')
```

**Estimated time**: ~8-12 hours on M4 Max with 10-12 cores

### Phase 4: Training Configuration (Week 2)

```bash
mlx_lm.lora \
  --model mlx-community/Llama-3.2-3B-Instruct-4bit \
  --train \
  --data data/diverse-100k \
  --num-layers 32 \  # More layers for complex patterns
  --batch-size 8 \   # Larger batch
  --iters 2000 \     # More iterations for 100K dataset
  --learning-rate 1e-5 \
  --steps-per-eval 100 \
  --val-batches 50 \
  --adapter-path ./witness-expert-diverse-100k
```

**Expected results**:
- Initial val loss: ~2.0
- After 500 iters: ~0.50
- After 1000 iters: ~0.35
- After 1500 iters: ~0.28
- After 2000 iters: **~0.25** (target!)

---

## Validation & Testing

### Diversity Metrics
```python
# Measure actual diversity achieved
def analyze_diversity(dataset_path):
    stats = {
        "unique_attestor_combos": set(),
        "unique_step_names": set(),
        "unique_questions": set(),
        "policy_distribution": {},
        "language_distribution": {},
    }

    with open(dataset_path) as f:
        for line in f:
            ex = json.loads(line)
            # Extract and count
            ...

    return stats
```

### Quality Validation
```python
# Randomly sample 1000 examples and verify them
def validate_random_sample(dataset_path, sample_size=1000):
    examples = random.sample(load_all(dataset_path), sample_size)

    passed = 0
    for ex in examples:
        if verify_example_works(ex):
            passed += 1

    print(f"Validation: {passed}/{sample_size} passed")
```

---

## Success Criteria

✅ **100K unique examples generated** (no duplicates)
✅ **100% verification success** (all pass witness verify)
✅ **1000+ attestor combinations** covered
✅ **All 10 step names** represented
✅ **Rego policies** in 50%+ of examples
✅ **SBOM examples** for 5 languages
✅ **Training loss < 0.30** achieved
✅ **Model generates valid witness configs** on real prompts

---

## Timeline

- **Week 1**: Setup infrastructure, create templates, test generators
- **Week 2**: Generate 100K examples (8-12 hours parallel)
- **Week 2**: Train model (12-16 hours)
- **Week 3**: Evaluate, iterate if needed

---

## Next Steps

1. Review this plan - any changes needed?
2. Start with Phase 1 infrastructure setup?
3. Or start generating a smaller 20K diverse set first to validate approach?

**Recommendation**: Start with 20K diverse dataset to validate the approach, then scale to 100K.
