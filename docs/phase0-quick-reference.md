# Phase 0 Quick Reference Guide

**Migration**: Modular Monolith  
**Phase**: 0 (Pre-Migration Preparation)  
**Status**: ✅ Complete  
**Date**: 2026-06-11  
**Branch**: `feat/modular-monolith-migration`

---

## Purpose

This guide provides quick reference commands, procedures, and troubleshooting steps for Phase 0 of the modular monolith migration. Use this for validation, analysis, and rollback operations.

---

## Validation Commands

### Run All Validations

```bash
# Execute all validation scripts in sequence
python scripts/validate_architecture.py && \
python scripts/analyze-dependencies-for-modular-monolith.py && \
python scripts/visualize-dependencies-with-mermaid.py && \
python scripts/create-architecture-baseline.py
```

### Individual Validation Scripts

#### 1. Architecture Validation

**Purpose**: Validate layer boundaries and detect circular dependencies

```bash
# Run validation
python scripts/validate_architecture.py

# Expected output:
# ✅ No circular dependencies found
# ✅ Layer boundaries validated
# ✅ No forbidden imports detected
```

**Output Files**:
- Console: Validation results
- JSON: `architecture_validation_report.json` (if enabled)

**Common Issues**:

| Issue | Cause | Solution |
|-------|-------|----------|
| Syntax errors in parsed files | Invalid Python syntax | Fix syntax errors in source files |
| Missing dependencies | Import failures | Install missing packages |
| False circular deps | Import edge cases | Review dependency graph manually |

---

#### 2. Dependency Analysis

**Purpose**: Generate dependency graph for modularization planning

```bash
# Run analysis
python scripts/analyze-dependencies-for-modular-monolith.py

# Output: dependency_report.json
```

**Report Structure**:
```json
{
  "total_modules": 82,
  "python_files": 96,
  "graph": {
    "nodes": [...],    // Module list with metadata
    "edges": [...]     // Dependency edges
  },
  "circular_dependencies": [],
  "layer_violations": []
}
```

**Usage Examples**:
```bash
# View module count
cat dependency_report.json | grep "total_modules"

# Find modules with most dependencies
cat dependency_report.json | jq '.graph.nodes | sort_by(.out_degree) | reverse | .[0:5]'

# Check for circular dependencies
cat dependency_report.json | jq '.circular_dependencies | length'
```

---

#### 3. Dependency Visualization

**Purpose**: Create Mermaid diagrams for dependency visualization

```bash
# Generate visualization
python scripts/visualize-dependencies-with-mermaid.py

# Output: dependency_visualization.html
```

**View Visualization**:
```bash
# Open in browser
open dependency_visualization.html  # macOS
xdg-open dependency_visualization.html  # Linux
start dependency_visualization.html  # Windows
```

**Diagram Features**:
- Layer-based module grouping
- Edge direction indicators
- Interactive hover information
- Color-coded by layer

**Customization**:
```python
# Edit these parameters in the script:
MAX_MODULES_PER_LAYER = 5  # Adjust for diagram size
MAX_EDGES = 50              # Limit edges for readability
```

---

#### 4. Architecture Baseline

**Purpose**: Create baseline snapshot for progress tracking

```bash
# Create baseline
python scripts/create-architecture-baseline.py

# Output: architecture_baseline.json
```

**Baseline Structure**:
```json
{
  "timestamp": "2026-06-11T00:00:00Z",
  "total_modules": 82,
  "python_files": 96,
  "modules_by_layer": {
    "serving": 8,
    "agents": 12,
    "retrieval": 15,
    "ingestion": 10
  },
  "metrics": {
    "circular_dependencies": 0,
    "layer_violations": 0
  }
}
```

**Comparison Usage**:
```bash
# Compare baselines
diff <git show HEAD:architecture_baseline.json> architecture_baseline.json

# Check module count changes
cat architecture_baseline.json | jq '.total_modules'
```

---

## CI Workflow Commands

### GitHub Actions Workflow

**Workflow File**: `.github/workflows/validate-modular-monolith-architecture.yml`

### Trigger Workflow Manually

```bash
# Using GitHub CLI
gh workflow run validate-modular-monolith-architecture.yml

# With specific branch
gh workflow run validate-modular-monolith-architecture.yml --ref feat/modular-monolith-migration
```

### Monitor Workflow Status

```bash
# List workflow runs
gh run list --workflow=validate-modular-monolith-architecture.yml

# View specific run
gh run view <run-id>

# Watch run in real-time
gh run watch <run-id>
```

### Download Workflow Artifacts

```bash
# Download all artifacts from a run
gh run download <run-id>

# Download specific artifact
gh run download <run-id> -n dependency-report

# Artifact extraction location: ./<run-id>/
```

### Workflow Configuration

**Edit Workflow**:
```bash
# Open workflow file in editor
code .github/workflows/validate-modular-monolith-architecture.yml

# Key settings:
trigger:
  push:
    branches: [feat/modular-monolith-migration]
  pull_request:
    branches: [feat/modular-monolith-migration]
```

---

## Re-running Dependency Analysis

### Full Re-analysis

```bash
# Clean previous reports
rm -f dependency_report.json architecture_baseline.json dependency_visualization.html

# Re-run all analyses
python scripts/validate_architecture.py
python scripts/analyze-dependencies-for-modular-monolith.py
python scripts/visualize-dependencies-with-mermaid.py
python scripts/create-architecture-baseline.py

# Verify outputs
ls -la dependency_report.json architecture_baseline.json dependency_visualization.html
```

### Targeted Analysis

```bash
# Analyze specific module only
python scripts/analyze-dependencies-for-modular-monolith.py --module retrieval

# Analyze specific layer only
python scripts/analyze-dependencies-for-modular-monolith.py --layer serving

# Validate specific files only
python scripts/validate_architecture.py --path src/retrieval/
```

---

## Viewing Architecture Reports

### Dependency Report

```bash
# View full report
cat dependency_report.json | jq '.'

# View module list
cat dependency_report.json | jq '.graph.nodes'

# View dependency edges
cat dependency_report.json | jq '.graph.edges'

# Find circular dependencies
cat dependency_report.json | jq '.circular_dependencies'

# Check layer violations
cat dependency_report.json | jq '.layer_violations'
```

### Architecture Baseline

```bash
# View baseline
cat architecture_baseline.json | jq '.'

# Compare with git history
git log --oneline architecture_baseline.json

# View changes over time
git diff HEAD~1 architecture_baseline.json
```

### Visualization

```bash
# Open HTML visualization
open dependency_visualization.html

# Or serve locally
python -m http.server 8000
# Then visit: http://localhost:8000/dependency_visualization.html
```

---

## Rollback Procedures

### Git Rollback

```bash
# View recent commits
git log --oneline -10

# Reset to specific commit
git reset --hard <commit-hash>

# Reset while preserving changes
git reset --soft <commit-hash>

# Revert specific commit
git revert <commit-hash>
```

### Restore from Baseline

```bash
# Check available baselines
git log --oneline architecture_baseline.json

# Restore specific baseline
git checkout <commit-hash> -- architecture_baseline.json

# Re-generate from baseline
python scripts/create-architecture-baseline.py --restore
```

### Disable CI Workflow

```bash
# Edit workflow file
code .github/workflows/validate-modular-monolith-architecture.yml

# Disable workflow (add at top):
# if: false

# Commit change
git add .github/workflows/
git commit -m "chore: disable modular monolith validation workflow"
git push
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: Validation Script Fails

**Symptoms**:
```
❌ Validation failed
❌ Circular dependencies detected
```

**Solutions**:
```bash
# Check which modules are involved
cat dependency_report.json | jq '.circular_dependencies'

# Manually review imports
python scripts/analyze_imports.py src/problematic/module.py

# Fix circular dependencies:
# Option 1: Extract shared code to separate module
# Option 2: Use dependency injection to break cycle
# Option 3: Merge modules if they're tightly coupled
```

---

#### Issue: Empty Module Names in Report

**Symptoms**:
```json
{
  "id": "",
  "files": 0,
  "in_degree": 7,
  "out_degree": 0
}
```

**Cause**: Module name extraction logic produces empty strings

**Solution**:
```bash
# Filter out empty modules
cat dependency_report.json | jq '.graph.nodes | map(select(.id != ""))'

# Update script to filter empty modules
# Edit: scripts/analyze-dependencies-for-modular-monolith.py
# Add filtering in generate_graph() function
```

---

#### Issue: Visualization Too Large

**Symptoms**: Mermaid diagram fails to render or is unreadable

**Solution**:
```bash
# Adjust visualization limits
# Edit: scripts/visualize-dependencies-with-mermaid.py

# Reduce module limit
MAX_MODULES_PER_LAYER = 3  # Instead of 5

# Reduce edge limit
MAX_EDGES = 30  # Instead of 50

# Re-generate visualization
python scripts/visualize-dependencies-with-mermaid.py
```

---

#### Issue: CI Workflow Not Triggering

**Symptoms**: Workflow doesn't run on push

**Solutions**:
```bash
# Check workflow status
gh workflow list

# Verify branch name matches trigger
git branch --show-current

# Check workflow file syntax
gh workflow view validate-modular-monolith-architecture.yml

# Re-trigger manually
gh workflow run validate-modular-monolith-architecture.yml
```

---

#### Issue: File Encoding Errors

**Symptoms**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte...
```

**Solution**:
```bash
# Check file encoding
file -I src/problematic/file.py

# Convert to UTF-8 if needed
iconv -f ISO-8859-1 -t UTF-8 src/problematic/file.py -o src/problematic/file.py

# Update scripts to handle encoding
# Edit: scripts/analyze-dependencies-for-modular-monolith.py
# Change: with open(file_path, encoding="utf-8")
```

---

## Phase 1 Preparation Steps

### Before Starting Phase 1

#### 1. Review Phase 0 Outputs

```bash
# Review dependency report
cat dependency_report.json | jq '.' > phase0-dependency-review.txt

# Check baseline metrics
cat architecture_baseline.json | jq '.metrics' > phase0-baseline-metrics.txt

# Review visualization
open dependency_visualization.html
```

#### 2. Identify High-Priority Modules

```bash
# Find modules with most dependencies (high coupling)
cat dependency_report.json | jq '.graph.nodes | sort_by(.out_degree + .in_degree) | reverse | .[0:10]'

# Find leaf modules (low coupling, good candidates for extraction)
cat dependency_report.json | jq '.graph.nodes | map(select(.out_degree == 0)) | sort_by(.in_degree)'

# Find core modules (high dependency, extract last)
cat dependency_report.json | jq '.graph.nodes | sort_by(.in_degree) | reverse | .[0:5]'
```

#### 3. Document Current Architecture

```bash
# Generate architecture documentation
python scripts/visualize-dependencies-with-mermaid.py > docs/current-dependencies.html

# Create module inventory
cat dependency_report.json | jq '.graph.nodes | sort_by(.id)' > docs/module-inventory.json
```

#### 4. Set Up Phase 1 Tracking

```bash
# Create Phase 1 branch (when ready)
git checkout -b phase1-module-identification

# Set up project board (GitHub Projects)
gh project create --title "Modular Monolith Migration - Phase 1"

# Add milestones
gh api repos/:owner/:repo/milestones -f title="Phase 1: Module Identification" -f state="open"
```

---

## Performance Benchmarks

### Validation Script Performance

| Script | Execution Time | Memory Usage | Output Size |
|--------|----------------|---------------|-------------|
| `validate_architecture.py` | ~2.5s | ~50MB | Console + JSON |
| `analyze-dependencies-for-modular-monolith.py` | ~1.8s | ~80MB | ~500KB JSON |
| `visualize-dependencies-with-mermaid.py` | ~0.5s | ~30MB | ~200KB HTML |
| `create-architecture-baseline.py` | ~0.8s | ~40MB | ~5KB JSON |
| **Total** | **~5.6s** | **~200MB** | **~705KB** |

**Benchmark Command**:
```bash
# Measure execution time
time python scripts/validate_architecture.py

# Measure memory usage
/usr/bin/time -v python scripts/analyze-dependencies-for-modular-monolith.py

# Profile with Python
python -m cProfile -o profile.stats scripts/validate_architecture.py
python -m pstats profile.stats
```

---

## Maintenance and Updates

### Update Validation Scripts

```bash
# Edit script
code scripts/validate_architecture.py

# Test changes
python scripts/validate_architecture.py

# Run full suite
python scripts/validate_architecture.py && \
python scripts/analyze-dependencies-for-modular-monolith.py && \
python scripts/visualize-dependencies-with-mermaid.py

# Commit changes
git add scripts/
git commit -m "docs: update validation scripts for Phase 0"
git push
```

### Update Documentation

```bash
# Edit this file
code docs/phase0-quick-reference.md

# Update migration progress
code docs/modular-monolith-migration-progress.md

# Commit documentation
git add docs/
git commit -m "docs: update Phase 0 documentation"
git push
```

---

## Contact and Support

### Team Communication

- **Migration Lead**: [To be assigned]
- **Architecture Questions**: [To be assigned]
- **CI/CD Issues**: [To be assigned]

### Issue Tracking

```bash
# Create issue for problems
gh issue create --title "Phase 0 validation issue" --body "Description of problem"

# Link issue to migration project
gh issue create --title "Phase 0 validation issue" --project "Modular Monolith Migration"
```

---

## Appendix

### A. File Locations

```
kira-simple/
├── docs/
│   ├── modular-monolith-migration-progress.md
│   ├── phase0-quick-reference.md
│   └── system-architecture.md
├── scripts/
│   ├── validate_architecture.py
│   ├── analyze-dependencies-for-modular-monolith.py
│   ├── visualize-dependencies-with-mermaid.py
│   ├── create-architecture-baseline.py
│   ├── analyze_imports.py
│   └── categorize_problematic_imports.py
├── .github/workflows/
│   └── validate-modular-monolith-architecture.yml
├── dependency_report.json
├── architecture_baseline.json
└── dependency_visualization.html
```

### B. Environment Variables

```bash
# Optional: Custom visualization limits
export MAX_MODULES_PER_LAYER=5
export MAX_EDGES=50

# Optional: Validation output directory
export VALIDATION_OUTPUT_DIR=validation_reports/

# Optional: Enable debug logging
export DEBUG_VALIDATION=true
```

### C. Git Aliases (Optional)

```bash
# Add to ~/.gitconfig
[alias]
    phase0-validate = "!f() { python scripts/validate_architecture.py && python scripts/analyze-dependencies-for-modular-monolith.py; }; f"
    phase0-visualize = "!python scripts/visualize-dependencies-with-mermaid.py"
    phase0-baseline = "!python scripts/create-architecture-baseline.py"
    phase0-all = "!f() { git phase0-validate && git phase0-visualize && git phase0-baseline; }; f"
```

**Usage**:
```bash
git phase0-all  # Run all Phase 0 validations
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-06-11  
**Maintained By**: Migration Team

---

*This guide is updated as Phase 0 evolves. For the latest information, check the migration progress tracker.*
