# Refactoring Template

**Task ID**: [NNN]
**Created**: [YYYY-MM-DD]
**Assigned to**: [Agent/Human]
**Status**: [Planning | Implementation | Testing | Complete]

---

## Refactoring Goal

### What Needs Improvement
<!-- Describe current state and why it needs refactoring -->

### Desired End State
<!-- Describe target state after refactoring -->

### Benefits
<!-- Why is this refactoring worth doing? -->
- Improved maintainability
- Better performance
- Clearer code structure
- Reduced duplication
- Easier testing

---

## Context Files

<!-- Reference code to be refactored -->
@[file_path]:[line_numbers]

**Files involved**:
- @hms_commander/[module].py
- @tests/test_[module].py

---

## Constraints

### Safety Rules
- [ ] No behavior changes (only structure)
- [ ] All existing tests must still pass
- [ ] API compatibility maintained (or clearly deprecated)
- [ ] No performance regression

### Don't Do
- Don't change functionality
- Don't skip regression testing
- Don't introduce new dependencies
- Don't break backwards compatibility without migration path

---

## Current State Analysis

### Code Smells Identified
<!-- What makes current code suboptimal? -->
- Duplication
- Long methods
- Complex conditionals
- Unclear naming
- Missing abstraction

### Dependencies
<!-- What other code depends on this? -->

### Test Coverage
<!-- What's currently tested? -->
```bash
pytest --cov=hms_commander.[module] --cov-report=term
```

---

## Refactoring Strategy

### Approach
<!-- Which refactoring pattern(s) will be used? -->
- Extract method
- Extract class
- Rename for clarity
- Consolidate conditional
- Replace magic numbers with constants

### Step-by-Step Plan
1. [ ] Write characterization tests (if coverage incomplete)
2. [ ] Refactor incrementally
3. [ ] Run tests after each step
4. [ ] Commit after each successful refactor

### Incremental Steps
<!-- Break into small, safe refactorings -->

#### Step 1: [Description]
- Before:
  ```python
  # Current code
  ```
- After:
  ```python
  # Refactored code
  ```
- Tests: Run `pytest tests/test_[module].py::[test_name]`

#### Step 2: [Description]
...

---

## Testing Strategy

### Regression Testing
- [ ] All existing tests pass
- [ ] No new failures in CI
- [ ] Example notebooks still execute

### Performance Validation
```python
# Before refactoring
import time
start = time.time()
# ... operation ...
print(f"Before: {time.time() - start:.3f}s")

# After refactoring
start = time.time()
# ... operation ...
print(f"After: {time.time() - start:.3f}s")
```

### Memory Profiling (if relevant)
```bash
python -m memory_profiler script.py
```

---

## Acceptance Criteria

### Refactoring Complete When
- [ ] All planned refactorings applied
- [ ] All existing tests pass
- [ ] New tests added (if gaps found)
- [ ] Code coverage maintained or improved
- [ ] Documentation updated
- [ ] Performance not degraded

### Code Quality Improvements
- [ ] Reduced duplication
- [ ] Clearer naming
- [ ] Shorter methods (<50 lines)
- [ ] Reduced cyclomatic complexity
- [ ] Better separation of concerns

---

## Verification Steps

### Automated Testing
```bash
# Run full test suite
pytest

# Run specific module tests
pytest tests/test_[module].py -v

# Check coverage
pytest --cov=hms_commander.[module] --cov-report=html

# Run example notebooks
pytest --nbmake examples/*.ipynb
```

### Manual Verification
1. Extract HmsExamples project
2. Run common workflows
3. Verify behavior unchanged
4. Check performance (if applicable)

### Code Review Checklist
- [ ] Naming clear and consistent
- [ ] No magic numbers
- [ ] Proper error handling
- [ ] Docstrings updated
- [ ] Type hints present
- [ ] Follows static class pattern

---

## Documentation Updates

### Files to Update
- [ ] Docstrings (if signatures changed)
- [ ] API docs (if public API changed)
- [ ] Examples (if usage patterns changed)
- [ ] CHANGELOG.md (note refactoring)

### Migration Guide (if breaking changes)
<!-- If API changed, document migration -->

**Before**:
```python
# Old way
```

**After**:
```python
# New way
```

---

## Rollback Plan

### If Refactoring Fails
- Git commit before each step allows rollback
- Incremental approach minimizes risk

### Rollback Commands
```bash
# View recent commits
git log --oneline -5

# Rollback to previous commit
git reset --hard <commit-hash>
```

---

## Notes for Future

### Lessons Learned
<!-- What went well? What was harder than expected? -->

### Further Refactoring Opportunities
<!-- What else could be improved later? -->

### Performance Insights
<!-- Any surprising performance findings? -->

---

## Session Log

### [YYYY-MM-DD HH:MM] - Analysis
- Current state analyzed:
- Refactoring strategy decided:
- Risks identified:

### [YYYY-MM-DD HH:MM] - Implementation
- Refactorings applied:
- Tests run:
- Issues encountered:

### [YYYY-MM-DD HH:MM] - Completed
- Final status:
- Improvements achieved:
- Follow-up items:
