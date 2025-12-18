# Feature Implementation Template

**Task ID**: [NNN]
**Created**: [YYYY-MM-DD]
**Assigned to**: [Agent/Human]
**Status**: [Planning | Implementation | Testing | Documentation | Complete]

---

## Feature Description

### User Story
As a [user type], I want [functionality] so that [benefit].

### Motivation
<!-- Why is this feature needed? -->

### Scope
<!-- What's included and what's NOT included? -->

---

## Context Files

<!-- Reference relevant existing code -->
@[file_path]:[line_numbers]

**Related modules**:
- @hms_commander/[module].py
- @tests/test_[module].py
- @examples/[related_notebook].ipynb

---

## Constraints

### Safety Rules
- [ ] Must work with both HMS 3.x and 4.x
- [ ] Must use static class pattern
- [ ] Must follow file parsing patterns
- [ ] Must have complete docstrings

### Don't Do
- Don't instantiate static classes
- Don't use global state
- Don't hardcode file paths
- Don't skip error handling

### Dependencies
<!-- Are new dependencies needed? If so, justify. -->

---

## Requirements Gathering

### Functional Requirements
1. Requirement 1
2. Requirement 2
3. Requirement 3

### Non-Functional Requirements
- Performance: [metric and target]
- Compatibility: [HMS versions, Python versions]
- Maintainability: [code quality standards]

### Edge Cases
<!-- What unusual scenarios must be handled? -->

---

## Design Decisions

### Architecture
<!-- How does this fit into existing code? -->

### API Design
<!-- Method signatures, parameters, return types -->

```python
@staticmethod
def method_name(
    param1: Type1,
    param2: Type2,
    hms_object: Optional[HmsPrj] = None
) -> ReturnType:
    """
    One-line summary.

    Detailed description.

    Args:
        param1: Description
        param2: Description
        hms_object: HMS project object (uses global if None)

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this happens

    Example:
        >>> # Example usage
    """
```

### Alternative Approaches Considered
<!-- What other designs were rejected and why? -->

---

## Implementation Plan

### Phase 1: Core Functionality
- [ ] Create main implementation in `hms_commander/[Module].py`
- [ ] Add helper methods as needed
- [ ] Implement error handling

### Phase 2: Testing
- [ ] Unit tests in `tests/test_[module].py`
- [ ] Integration tests with HmsExamples
- [ ] Edge case tests

### Phase 3: Documentation
- [ ] Complete docstrings (Google style)
- [ ] Add to API docs in `docs/api/`
- [ ] Create example notebook in `examples/`
- [ ] Update GETTING_STARTED.md if needed

### Phase 4: Integration
- [ ] Update relevant skills if needed
- [ ] Update orchestrator routing if needed
- [ ] Update QUICK_REFERENCE.md

---

## Testing Strategy

### Test Coverage Requirements
- [ ] All public methods have unit tests
- [ ] Edge cases covered
- [ ] Error handling tested
- [ ] Example usage in docstrings

### Test Data
<!-- Which HmsExamples projects will be used? -->
- HmsExamples.extract_project("[project_name]")

### Test Cases
1. **Happy path**: [description]
2. **Edge case 1**: [description]
3. **Edge case 2**: [description]
4. **Error handling**: [description]

---

## Acceptance Criteria

### Feature Complete When
- [ ] All functional requirements met
- [ ] All tests pass
- [ ] Code coverage >80% for new code
- [ ] Docstrings complete and accurate
- [ ] Example notebook demonstrates usage
- [ ] API docs generated and reviewed
- [ ] Static class pattern followed
- [ ] File parsing pattern followed (if applicable)

### Code Quality
- [ ] Follows naming conventions
- [ ] No magic numbers (use _constants.py)
- [ ] Proper error handling
- [ ] Encoding fallback pattern (UTF-8 → Latin-1)

---

## Verification Steps

### Manual Testing
```python
from hms_commander import HmsExamples, [NewModule]

# Extract test project
HmsExamples.extract_project("[project_name]")

# Test basic functionality
result = [NewModule].method_name(...)
assert result is not None

# Test edge cases
...
```

### Automated Testing
```bash
# Run new tests
pytest tests/test_[module].py -v

# Run all tests
pytest

# Run example notebook
pytest --nbmake examples/[new_notebook].ipynb

# Generate coverage report
pytest --cov=hms_commander --cov-report=html
```

### Documentation Review
- [ ] Docstrings render correctly in mkdocs
- [ ] Example notebook executes without errors
- [ ] API docs show up in navigation

---

## Documentation Updates

### Files to Update
- [ ] `docs/api/[module].md` (auto-generated from docstrings)
- [ ] `examples/[new_notebook].ipynb` (working demonstration)
- [ ] `GETTING_STARTED.md` (if major feature)
- [ ] `QUICK_REFERENCE.md` (add to relevant section)
- [ ] `.claude/skills/` (if new workflow pattern)

### Example Notebook Checklist
- [ ] First cell is markdown with H1 title
- [ ] Uses HmsExamples for reproducibility
- [ ] Two-cell import pattern (pip + dev mode)
- [ ] All cells executed before committing
- [ ] Results validated

---

## Notes for Future

### Implementation Challenges
<!-- Document difficulties encountered -->

### Performance Considerations
<!-- Any performance gotchas? -->

### Future Enhancements
<!-- Ideas for later iterations -->

---

## Session Log

### [YYYY-MM-DD HH:MM] - Planning
- Requirements gathered:
- Design decisions:
- Questions resolved:

### [YYYY-MM-DD HH:MM] - Implementation
- Files created/modified:
- Tests added:
- Issues encountered:

### [YYYY-MM-DD HH:MM] - Documentation
- Docs updated:
- Example created:

### [YYYY-MM-DD HH:MM] - Completed
- Final status:
- Lessons learned:
