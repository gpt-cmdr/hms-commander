# Bug Fix Template

**Task ID**: [NNN]
**Created**: [YYYY-MM-DD]
**Assigned to**: [Agent/Human]
**Status**: [Planning | In Progress | Verification | Complete]

---

## Bug Description

### Symptoms
<!-- What is the observable problem? -->

### Expected Behavior
<!-- What should happen instead? -->

### Actual Behavior
<!-- What actually happens? -->

### Impact
<!-- Who is affected? How severe? -->

---

## Context Files

<!-- Reference relevant files with @ syntax -->
@[file_path]:[line_numbers]

**Example**:
- @hms_commander/HmsBasin.py:145-160
- @tests/test_basin.py:45-60
- @examples/03_project_dataframes.ipynb

---

## Constraints

### Safety Rules
- [ ] Do not modify production HMS projects
- [ ] Work on HmsExamples projects only
- [ ] Maintain backwards compatibility
- [ ] All changes must have tests

### Don't Do
- Don't change API signatures without discussion
- Don't introduce new dependencies without approval
- Don't skip docstring updates
- Don't commit without running tests

---

## Investigation Plan

### Reproduction Steps
1. Step-by-step instructions to reproduce the bug
2. Include project setup (HmsExamples.extract_project("project_name"))
3. Include exact code/commands that trigger the bug

### Root Cause Analysis
<!-- Checklist for investigation -->
- [ ] Read relevant source code
- [ ] Check git history for related changes
- [ ] Search for similar issues in repo
- [ ] Test with different HMS versions
- [ ] Identify exact failure point

### Findings
<!-- Document what you discover -->

---

## Fix Implementation

### Approach
<!-- Describe the fix strategy -->

### Code Changes
<!-- List files to modify -->
- [ ] File 1: [description of change]
- [ ] File 2: [description of change]

### Tests Added
<!-- New tests to prevent regression -->
- [ ] Test case 1: [description]
- [ ] Test case 2: [description]

---

## Acceptance Criteria

### Fix Validates When
- [ ] Bug no longer reproduces with test case
- [ ] Existing tests still pass
- [ ] New tests pass
- [ ] Docstrings updated
- [ ] Example notebooks still run (if affected)

### Performance Requirements
- [ ] No performance regression
- [ ] Memory usage acceptable

---

## Verification Steps

### Manual Testing
1. Extract relevant HmsExamples project
2. Run reproduction steps
3. Verify bug no longer occurs
4. Test edge cases

### Automated Testing
```bash
# Run specific test
pytest tests/test_[module].py::[test_name] -v

# Run all related tests
pytest tests/test_[module].py -v

# Run example notebooks (if affected)
pytest --nbmake examples/[notebook].ipynb
```

### Regression Check
- [ ] Run full test suite
- [ ] Run all example notebooks
- [ ] Check documentation renders correctly

---

## Notes for Future

### Gotchas Discovered
<!-- Document any tricky aspects -->

### Related Issues
<!-- Link to related bugs or features -->

### Follow-up Tasks
<!-- Items to track separately -->

---

## Session Log

### [YYYY-MM-DD HH:MM] - Investigation Started
- Context:
- Actions:
- Findings:

### [YYYY-MM-DD HH:MM] - Fix Implemented
- Changes made:
- Tests added:
- Validation:

### [YYYY-MM-DD HH:MM] - Completed
- Final status:
- Lessons learned:
