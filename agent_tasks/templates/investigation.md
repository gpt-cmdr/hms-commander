# Investigation Template

**Task ID**: [NNN]
**Created**: [YYYY-MM-DD]
**Assigned to**: [Agent/Human]
**Status**: [Research | Analysis | Documentation | Complete]

---

## Research Question

### What We Need to Know
<!-- Clear statement of the investigation goal -->

### Why This Matters
<!-- How will this knowledge be used? -->

### Success Criteria
<!-- How will we know when investigation is complete? -->

---

## Context Files

<!-- Reference relevant existing files -->
@[file_path]:[line_numbers]

**Relevant documentation**:
- @docs/[relevant_doc].md
- @.claude/rules/[relevant_rule].md
- @tests/projects/[HMS_project]/File Parsing Guide/

---

## Constraints

### Scope Limits
<!-- What's in scope and what's NOT -->
- **In scope**: [list]
- **Out of scope**: [list]

### Time Box
<!-- How long to spend before reporting findings? -->
- Maximum time: [N hours/days]
- Check-in points: [timestamps]

---

## Information Sources

### Primary Sources
<!-- Authoritative information -->
1. **HMS Source Code** (decompiled if needed)
   - Location: [path to JAR or decompiled source]
   - Methods to investigate: [list]

2. **Official Documentation**
   - HMS User's Manual
   - Technical Reference Manual
   - Release notes

3. **Code Implementation**
   - hms_commander/[module].py
   - Related test files

### Secondary Sources
<!-- Supporting information -->
- HEC forums
- Academic papers
- Stack Overflow threads
- GitHub issues

### Experiments
<!-- Code to write and run -->
- Test cases to create
- HMS projects to examine
- Parameter combinations to test

---

## Investigation Plan

### Phase 1: Background Research
- [ ] Read relevant documentation
- [ ] Search existing codebase
- [ ] Review related issues/PRs
- [ ] Check HMS decompiled source

### Phase 2: Experimentation
- [ ] Create test project (HmsExamples or new)
- [ ] Run controlled experiments
- [ ] Document parameter behavior
- [ ] Capture output/results

### Phase 3: Analysis
- [ ] Synthesize findings
- [ ] Identify patterns
- [ ] Document edge cases
- [ ] Formulate recommendations

---

## Findings

### Key Discoveries
<!-- Document what you learned -->

#### Discovery 1: [Title]
**Evidence**:
- [Source or experiment that revealed this]

**Details**:
- [Detailed explanation]

**Implications**:
- [How this affects our code/decisions]

#### Discovery 2: [Title]
...

### HMS Behavior Analysis
<!-- If investigating HMS internals -->

**Parameter**: [name]
**File format**: [.basin, .met, .control, etc.]
**HMS versions tested**: [3.x, 4.x]

**Behavior**:
- HMS 3.x: [description]
- HMS 4.x: [description]

**Parsing pattern**:
```java
// Decompiled HMS code (if relevant)
```

**hms-commander implementation**:
```python
# Our current or proposed code
```

### Edge Cases Discovered
<!-- Unusual scenarios that need special handling -->

---

## Experiments Conducted

### Experiment 1: [Description]

**Hypothesis**: [What we expected to find]

**Method**:
```python
# Test code
from hms_commander import HmsExamples, [Module]

HmsExamples.extract_project("[project]")
# ... test steps ...
```

**Results**:
- [Observations]

**Conclusion**:
- [What this tells us]

### Experiment 2: [Description]
...

---

## Recommendations

### Immediate Actions
1. [ ] Action 1: [description and rationale]
2. [ ] Action 2: [description and rationale]

### Future Considerations
- [ ] Item 1
- [ ] Item 2

### Documentation Needs
<!-- What should be documented based on findings? -->
- [ ] Update `.claude/rules/hec-hms/[topic].md`
- [ ] Add to docstrings
- [ ] Create example notebook
- [ ] Update LEARNINGS.md

---

## Questions Answered

### Question 1: [Original question]
**Answer**: [Clear answer with evidence]

### Question 2: [Original question]
**Answer**: [Clear answer with evidence]

---

## Questions Raised

### New Questions Discovered
<!-- What new questions arose during investigation? -->

1. Question 1 → [Should we investigate further? Create new task?]
2. Question 2 → [Follow-up needed or document as limitation?]

---

## Acceptance Criteria

### Investigation Complete When
- [ ] All primary research questions answered
- [ ] Experiments conducted and documented
- [ ] Findings synthesized
- [ ] Recommendations formulated
- [ ] Documentation updated
- [ ] Knowledge transferred (LEARNINGS.md, rules, docstrings)

---

## Knowledge Transfer

### Files to Update

**LEARNINGS.md**:
```markdown
### [Topic] - [Date]

**What worked**:
- [Finding]

**What doesn't work**:
- [Finding]

**Pattern discovered**:
- [Finding]
```

**Rules to Update**:
- [ ] `.claude/rules/hec-hms/[topic].md`
- [ ] `.claude/rules/python/[topic].md`

**Code to Update**:
- [ ] `hms_commander/[module].py` (docstrings)
- [ ] `tests/test_[module].py` (new test cases)

---

## References

### Sources Consulted
1. [Citation]
2. [Citation]
3. [Citation]

### Related Tasks
- [Link to related bug fix task]
- [Link to related feature task]
- [Link to follow-up investigation]

---

## Session Log

### [YYYY-MM-DD HH:MM] - Research Started
- Sources identified:
- Initial findings:

### [YYYY-MM-DD HH:MM] - Experiments
- Tests conducted:
- Results:
- Surprises:

### [YYYY-MM-DD HH:MM] - Analysis
- Patterns identified:
- Conclusions reached:

### [YYYY-MM-DD HH:MM] - Completed
- Final recommendations:
- Documentation updated:
- Follow-up tasks created:

---

## Appendix: Raw Data

### Experiment Outputs
<!-- Paste raw data, logs, screenshots -->

### HMS Decompilation Snippets
<!-- Relevant decompiled code -->

### File Format Examples
<!-- Example .basin, .met file snippets -->
