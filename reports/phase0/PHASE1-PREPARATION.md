# Phase 1: Shared Kernel Extraction - Preparation Checklist

**Phase**: 1 - Shared Kernel Extraction  
**Status**: 🔄 **PENDING**  
**Start Date**: TBD (awaiting Phase 0 completion)  
**Estimated Duration**: 3 days  
**Branch**: feat/modular-monolith-migration  
**Dependencies**: Phase 0 ✅ COMPLETE

---

## Phase 1 Objectives

Extract shared abstractions and base classes into `shared/kernel/` to establish the foundation for modular architecture.

### Primary Goals
1. Create `shared/kernel/interfaces/` with all ABC interfaces
2. Create `shared/kernel/di/` with dependency injection container
3. Create `shared/kernel/base/` with base use case and repository classes
4. Update all imports across codebase
5. Ensure zero breaking changes to external APIs

### Success Criteria
- ✅ All 9 files moved to `shared/kernel/`
- ✅ All imports updated to `src.shared.kernel.*`
- ✅ No circular dependencies introduced
- ✅ All 38 tests passing (100%)
- ✅ Architecture validation: PASS
- ✅ No breaking changes to FastAPI endpoints

---

## Pre-Requisites Checklist

### Phase 0 Completion Status
| Requirement | Status | Verification |
|-------------|--------|--------------|
| Migration branch created | ✅ COMPLETE | `feat/modular-monolith-migration` |
| Validation scripts | ✅ COMPLETE | 5 scripts functional |
| Dependency map | ✅ COMPLETE | 82 modules mapped |
| Baseline metrics | ✅ COMPLETE | Documented in JSON |
| CI/CD workflow | ✅ COMPLETE | Automated validation active |
| Backup strategy | ✅ COMPLETE | Rollback procedures tested |
| Tests passing | ✅ COMPLETE | 38/38 tests passing |

**Phase 0 Status**: ✅ **READY TO PROCEED**

### Tools & Scripts Available
```bash
# Validation scripts (all functional)
scripts/validate_architecture.py                    # Circular dep detection
scripts/analyze-dependencies-for-modular-monolith.py  # Dependency mapping
scripts/visualize-dependencies-with-mermaid.py       # Visualization
scripts/create-architecture-baseline.py              # Baseline metrics

# Run pre-flight check
python scripts/validate_architecture.py
python scripts/analyze-dependencies-for-modular-monolith.py
```

### Environment Setup
```bash
# Verify branch
git branch --show-current
# Expected: feat/modular-monolith-migration

# Verify baseline tag exists
git tag | grep pre-migration-phase0
# Expected: pre-migration-phase0

# Verify tests passing
pytest tests/ -v
# Expected: 38 passed
```

---

## Files to Move (Phase 1)

### Batch 1: ABC Interfaces (5 files)
```bash
# Source → Target
src/interfaces/__init__.py           → shared/kernel/interfaces/__init__.py
src/interfaces/handlers.py            → shared/kernel/interfaces/handlers.py
src/interfaces/classification.py      → shared/kernel/interfaces/classification.py
src/interfaces/retrieval.py           → shared/kernel/interfaces/retrieval.py
src/interfaces/container.py           → shared/kernel/interfaces/container.py
```

### Batch 2: DI Container (4 files)
```bash
# Source → Target
src/di/__init__.py                    → shared/kernel/di/__init__.py
src/di/container.py                   → shared/kernel/di/container.py
src/di/registry.py                    → shared/kernel/di/registry.py
src/di/feature_flags.py               → shared/kernel/di/feature_flags.py
```

### Batch 3: Base Classes (NEW - to be created)
```bash
# Create new files
shared/kernel/base/__init__.py        # Base package init
shared/kernel/base/use_case.py        # UseCase ABC
shared/kernel/base/repository.py      # Repository ABC
shared/kernel/base/entity.py          # Entity base class
```

**Total Files**: 9 files (5 move, 4 move, 3 create)

---

## Import Update Strategy

### Import Pattern Changes

#### Before Migration
```python
# Current imports (before Phase 1)
from src.interfaces.handlers import QueryHandlerBase
from src.interfaces.classification import ClassificationStrategyBase
from src.di.container import ServiceContainer
```

#### After Migration
```python
# New imports (after Phase 1)
from src.shared.kernel.interfaces.handlers import QueryHandlerBase
from src.shared.kernel.interfaces.classification import ClassificationStrategyBase
from src.shared.kernel.di.container import ServiceContainer
```

### Import Update Process

#### Step 1: Find All Imports
```bash
# Find all files importing from src.interfaces
grep -r "from src\.interfaces" src/ --include="*.py" | wc -l

# Find all files importing from src.di
grep -r "from src\.di" src/ --include="*.py" | wc -l
```

#### Step 2: Update Imports (Batch 1 - Interfaces)
```bash
# Update src.interfaces → src.shared.kernel.interfaces
find src/ -name "*.py" -type f -exec sed -i '' \
  's/from src\.interfaces/from src.shared.kernel.interfaces/g' {} +

# Verify changes
git diff --stat
```

#### Step 3: Update Imports (Batch 2 - DI)
```bash
# Update src.di → src.shared.kernel.di
find src/ -name "*.py" -type f -exec sed -i '' \
  's/from src\.di/from src.shared.kernel.di/g' {} +

# Verify changes
git diff --stat
```

#### Step 4: Validate No Breaking Changes
```bash
# Run tests to ensure no import errors
pytest tests/ -v

# Expected: All 38 tests passing
```

### Expected Import Count
| Module | Current Imports | After Migration | Change |
|--------|----------------|-----------------|--------|
| src.interfaces.* | ~25 files | 0 | -25 |
| src.di.* | ~15 files | 0 | -15 |
| src.shared.kernel.interfaces.* | 0 | ~25 | +25 |
| src.shared.kernel.di.* | 0 | ~15 | +15 |

---

## Validation Gates

### Gate 1: Pre-Migration Validation (Before Starting)
```bash
# Run baseline validation
python scripts/validate_architecture.py

# Expected output:
# ✅ Circular Dependencies: PASS (0 detected)
# ✅ Layer Boundaries: PASS
# ✅ Dependency Rules: PASS
# ✅ Import Patterns: PASS

# Document baseline
python scripts/create-architecture-baseline.py
```

**Gate Status**: ⏳ **PENDING** (run before Phase 1 start)

---

### Gate 2: Post-Batch Validation (After Each Batch)
```bash
# After Batch 1 (interfaces)
pytest tests/ -v
python scripts/validate_architecture.py

# After Batch 2 (di)
pytest tests/ -v
python scripts/validate_architecture.py

# After Batch 3 (base classes)
pytest tests/ -v
python scripts/validate_architecture.py
```

**Expected Result**: All gates PASS
**Stop Condition**: If any gate fails, stop and investigate before proceeding

---

### Gate 3: Post-Migration Validation (After Phase 1)
```bash
# Full test suite
pytest tests/ -v --cov=src

# Architecture validation
python scripts/validate_architecture.py

# Dependency analysis
python scripts/analyze-dependencies-for-modular-monolith.py

# Generate new baseline
python scripts/create-architecture-baseline.py

# Compare with Phase 0 baseline
diff reports/phase0/baselines/architecture-baseline.json \
     reports/phase1/baselines/architecture-baseline.json
```

**Expected Result**:
- ✅ Tests: 38/38 passing (100%)
- ✅ Circular dependencies: 0
- ✅ Layer boundaries: PASS
- ✅ Dependency rules: PASS

---

## Rollback Procedures

### Rollback Trigger Conditions
1. **Test Failures**: >0 tests failing after import updates
2. **Circular Dependencies**: New circular dependencies introduced
3. **Import Errors**: Python cannot resolve imports
4. **API Breaks**: FastAPI endpoints returning errors
5. **Performance Regression**: >20% performance degradation

### Rollback Steps
```bash
# Option 1: Git reset (recommended)
git checkout pre-migration-phase0 -- .
git clean -fd  # Remove untracked files

# Option 2: Restore from backup
tar -xzf backups/kira-pre-migration-20260611.tar.gz

# Option 3: Manual revert
git revert HEAD~3..HEAD  # Revert last 3 commits
```

### Rollback Validation
```bash
# Verify rollback successful
pytest tests/ -v
python scripts/validate_architecture.py

# Expected: All tests passing, validation PASS
```

---

## Day-by-Day Execution Plan

### Day 1: ABC Interfaces Migration
**Morning** (2-3 hours):
- [ ] Create `shared/kernel/interfaces/` directory
- [ ] Move 5 interface files from `src/interfaces/`
- [ ] Update imports (Batch 1)
- [ ] Run validation gate
- [ ] Run tests

**Afternoon** (2-3 hours):
- [ ] Fix any import errors
- [ ] Verify all 38 tests passing
- [ ] Create Git commit: "feat: move ABC interfaces to shared/kernel"

**Deliverables**:
- ✅ 5 files moved
- ✅ All imports updated
- ✅ Tests passing

---

### Day 2: DI Container Migration
**Morning** (2-3 hours):
- [ ] Create `shared/kernel/di/` directory
- [ ] Move 4 DI files from `src/di/`
- [ ] Update imports (Batch 2)
- [ ] Run validation gate
- [ ] Run tests

**Afternoon** (2-3 hours):
- [ ] Fix any import errors
- [ ] Verify all 38 tests passing
- [ ] Create Git commit: "feat: move DI container to shared/kernel"

**Deliverables**:
- ✅ 4 files moved
- ✅ All imports updated
- ✅ Tests passing

---

### Day 3: Base Classes & Validation
**Morning** (2-3 hours):
- [ ] Create `shared/kernel/base/` directory
- [ ] Create `use_case.py` (UseCase ABC)
- [ ] Create `repository.py` (Repository ABC)
- [ ] Create `entity.py` (Entity base class)
- [ ] Update imports (if needed)

**Afternoon** (2-3 hours):
- [ ] Run full validation (Gate 3)
- [ ] Run all tests with coverage
- [ ] Generate dependency map
- [ ] Create comparison report (Phase 0 vs Phase 1)
- [ ] Create PR for Phase 1

**Deliverables**:
- ✅ 3 base classes created
- ✅ All validations passing
- ✅ PR created and reviewed

---

## Success Metrics

### Quantitative Metrics
| Metric | Phase 0 Baseline | Phase 1 Target | Status |
|--------|------------------|----------------|--------|
| Tests Passing | 38/38 (100%) | 38/38 (100%) | ⏳ Pending |
| Circular Dependencies | 0 | 0 | ⏳ Pending |
| Layer Boundaries | PASS | PASS | ⏳ Pending |
| Dependency Rules | PASS | PASS | ⏳ Pending |
| Test Coverage | 65% | ≥65% | ⏳ Pending |
| Build Time | ~30s | <45s | ⏳ Pending |

### Qualitative Metrics
| Metric | Target | Status |
|--------|--------|--------|
| No breaking changes to APIs | ✅ | ⏳ Pending |
| All imports resolved | ✅ | ⏳ Pending |
| Code review approved | ✅ | ⏳ Pending |
| Documentation updated | ✅ | ⏳ Pending |

---

## Testing Strategy

### Pre-Migration Tests
```bash
# Run baseline tests
pytest tests/ -v --tb=short > reports/phase0/tests/baseline-results.txt

# Expected: 38 passed
```

### Post-Batch Tests
```bash
# After each batch
pytest tests/ -v --tb=short

# Stop if any tests fail
```

### Post-Migration Tests
```bash
# Full test suite with coverage
pytest tests/ -v --cov=src --cov-report=html

# Compare with baseline
diff reports/phase0/tests/baseline-results.txt \
     reports/phase1/tests/final-results.txt
```

### Integration Tests
```bash
# Test API endpoints still working
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test query"}'

# Expected: 200 OK with streaming response
```

---

## Risk Assessment

### Risks & Mitigations

#### Risk 1: Import Errors
**Probability**: MEDIUM  
**Impact**: HIGH  
**Mitigation**:
- Run tests after each batch
- Use automated import update scripts
- Have rollback plan ready

#### Risk 2: Circular Dependencies
**Probability**: LOW  
**Impact**: HIGH  
**Mitigation**:
- Baseline: 0 circular dependencies
- Run validation after each batch
- Stop immediately if circular deps detected

#### Risk 3: Test Failures
**Probability**: MEDIUM  
**Impact**: MEDIUM  
**Mitigation**:
- All tests passing in Phase 0
- Fix issues before proceeding
- Keep tests green throughout

#### Risk 4: Breaking Changes to APIs
**Probability**: LOW  
**Impact**: HIGH  
**Mitigation**:
- Internal refactoring only
- No changes to API contracts
- Test API endpoints after migration

### Risk Matrix
```
HIGH IMPACT    | Import Errors (M)   | Breaking Changes (L)
               | Circular Deps (L)   |
               |
MEDIUM IMPACT  | Test Failures (M)  |
               |
               |
LOW IMPACT     |                    |
               |                    |
               |____________________|
               LOW    MEDIUM    HIGH
               PROBABILITY
```

---

## Dependencies

### Internal Dependencies
- **Phase 0**: ✅ COMPLETE (must finish first)
- **Phase 2**: ⏳ PENDING (depends on Phase 1)

### External Dependencies
- **Python 3.11+**: Required (already installed)
- **pytest**: Required (already installed)
- **Git**: Required (already installed)

### Tool Dependencies
- **Validation scripts**: ✅ AVAILABLE (Phase 0 deliverables)
- **Backup archives**: ✅ AVAILABLE (Phase 0 deliverables)

---

## Communication Plan

### Stakeholder Notifications
- **Team**: Notify when Phase 1 starts
- **Management**: Weekly progress updates
- **Users**: No impact expected (internal refactoring)

### Progress Reporting
- **Daily**: Update task checklist
- **Weekly**: Generate progress report
- **End of Phase**: Create completion summary

---

## Documentation Requirements

### Phase 1 Deliverables
1. **Execution Summary**: `/reports/phase1/EXECUTION_SUMMARY.md`
2. **Import Changes**: `/reports/phase1/import-updates.md`
3. **Validation Report**: `/reports/phase1/validation-report.md`
4. **Test Results**: `/reports/phase1/test-results.txt`
5. **Dependency Map**: `/reports/phase1/dependencies/dependency_report.json`

### Documentation Updates
- Update `CLAUDE.md` with new import paths
- Update `docs/abc-migration-summary.md` (if applicable)
- Create Phase 1 completion report

---

## Next Actions

### Immediate (Before Starting)
1. ✅ Review this preparation checklist
2. ⏳ Run pre-migration validation (Gate 1)
3. ⏳ Verify all Phase 0 deliverables
4. ⏳ Notify team of Phase 1 start

### Day 1 (ABC Interfaces)
1. ⏳ Create `shared/kernel/interfaces/`
2. ⏳ Move 5 interface files
3. ⏳ Update imports (Batch 1)
4. ⏳ Run validation gate
5. ⏳ Create Git commit

### Day 2 (DI Container)
1. ⏳ Create `shared/kernel/di/`
2. ⏳ Move 4 DI files
3. ⏳ Update imports (Batch 2)
4. ⏳ Run validation gate
5. ⏳ Create Git commit

### Day 3 (Base Classes & Validation)
1. ⏳ Create `shared/kernel/base/`
2. ⏳ Create 3 base classes
3. ⏳ Run full validation (Gate 3)
4. ⏳ Create Phase 1 PR
5. ⏳ Generate completion summary

---

## Quick Reference Commands

### Pre-Flight Check
```bash
# Verify environment
git branch --show-current
pytest tests/ -v
python scripts/validate_architecture.py
```

### Import Updates
```bash
# Batch 1: Interfaces
find src/ -name "*.py" -type f -exec sed -i '' \
  's/from src\.interfaces/from src.shared.kernel.interfaces/g' {} +

# Batch 2: DI
find src/ -name "*.py" -type f -exec sed -i '' \
  's/from src\.di/from src.shared.kernel.di/g' {} +
```

### Validation
```bash
# Run tests
pytest tests/ -v

# Validate architecture
python scripts/validate_architecture.py

# Analyze dependencies
python scripts/analyze-dependencies-for-modular-monolith.py
```

### Rollback
```bash
# Git reset
git checkout pre-migration-phase0 -- .

# Restore backup
tar -xzf backups/kira-pre-migration-20260611.tar.gz
```

---

## Conclusion

**Phase 1 Readiness**: ✅ **READY**

Phase 0 has been successfully completed with all deliverables in place. The migration infrastructure is solid, tests are passing, and the team has clear visibility into the current architecture.

**Recommendation**: Proceed to Phase 1 immediately with confidence.

**Key Success Factors**:
- ✅ Comprehensive validation tools
- ✅ Clear execution plan
- ✅ Rollback procedures documented
- ✅ All tests passing (38/38)
- ✅ No circular dependencies

**Estimated Duration**: 3 days  
**Risk Level**: LOW-MEDIUM  
**Confidence Level**: HIGH

---

**Prepared By**: Phase 0 Manager  
**Date**: 2026-06-11 01:00:00  
**Status**: ✅ APPROVED FOR PHASE 1  
**Next Review**: End of Day 1 (Phase 1)

---

**End of Phase 1 Preparation Checklist**
