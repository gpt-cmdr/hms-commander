# HMS-Commander Project Constitution

## Identity
**Project**: hms-commander
**Purpose**: Python library for automating HEC-HMS (Hydrologic Modeling System) operations
**Stack**: Python 3.10+, pandas, pathlib, Jython (HMS automation), pyjnius (DSS files)

## Principles

### 1. **Mirror ras-commander Architecture**
HMS-Commander follows the patterns established by ras-commander:
- Static method classes (not instantiated)
- Global singleton pattern for project state
- File-based operations with pathlib.Path
- Comprehensive docstrings with examples
- @log_call decorators for function tracking

### 2. **Support Multiple HMS Versions**
Must handle both legacy (HMS 3.x, 32-bit, Python 2) and modern (HMS 4.x, 64-bit, Python 3):
- Auto-detect version from installation path
- Generate version-appropriate Jython scripts
- Handle encoding differences (UTF-8 vs Latin-1)

### 3. **Agent-Driven Workflows as First-Class Citizens**
Complex, multi-session tasks deserve structured workflows:
- Quality verdicts (GREEN/YELLOW/RED)
- Comprehensive change tracking (MODELING_LOG.md)
- Session save/resume capability
- Acceptance criteria validation

### 4. **Documentation is Critical**
HMS files are plain text with complex structure:
- Document every parameter change with justification
- Explain expected impact on results
- Track pre-existing issues separately
- Provide evidence for all decisions (decompilation, testing, references)

## Constraints

### MUST
- Use static methods with @log_call decorators
- Support both HMS 3.x and HMS 4.x
- Handle Windows paths correctly (pathlib.Path)
- Provide comprehensive docstrings with examples
- Maintain backward compatibility with ras-commander patterns
- Use lazy loading for optional dependencies (DSS, GIS)

### MUST NOT
- Break existing ras-commander integration points
- Require manual GUI interaction for automation tasks
- Assume HMS files are UTF-8 (must handle Latin-1 fallback)
- Make changes without documenting justification
- Mark pre-existing issues as failures

### PREFER
- Decompilation over guesswork (when HMS behavior unclear)
- File-based operations over database/JSON
- Markdown documentation over complex formats
- Simple patterns over elaborate architectures
- Evidence-based decisions (test results, code analysis)

## Quality Bar

### "Done" Means
1. **Tests Pass**: All existing tests continue to pass (no regression)
2. **Documentation Complete**: CLAUDE.md updated, examples provided
3. **Agent-Ready**: Workflow can be resumed across sessions
4. **Zero Deviation**: Results match baseline (for upgrade/migration tasks)
5. **Change Log**: Every modification documented with justification

### Acceptance Criteria for Agent Workflows
- ✅ Peak Flow Difference: <1.0%
- ✅ Volume Difference: <0.5%
- ✅ Timing Difference: ≤1 timestep
- ✅ Execution Success: 100% of valid runs complete
- ✅ Pre-existing Issues: Documented separately

## Project-Specific Patterns

### File Operations
```python
# Always use pathlib.Path
from pathlib import Path
file_path = Path(file_path)

# Encoding fallback pattern
try:
    content = file_path.read_text(encoding='utf-8')
except UnicodeDecodeError:
    content = file_path.read_text(encoding='latin-1')
```

### Static Method Pattern
```python
@staticmethod
@log_call
def get_X(file_path: Union[str, Path], name: str) -> Dict[str, Any]:
    """Get configuration for element."""
    # Implementation
```

### Agent Workflow Pattern
```python
from agents._shared import AgentWorkflow, QualityVerdict

class MyWorkflow(AgentWorkflow):
    def execute(self):
        self.log_change("Category", "Action", file="x.basin",
                       old_value="100", new_value="200",
                       justification="Reason", impact="Expected effect")
        return self.generate_verdict()
```

## Decision Framework

When facing implementation choices:

1. **Check ras-commander first** - Does it have a pattern we should follow?
2. **Check CLAUDE.md** - Is there existing guidance?
3. **Check HMS decompilation** - What does HMS actually do?
4. **Check test results** - Does it produce correct results?
5. **Document decision** - Add to LEARNINGS.md

## Version History
- **Session 1 (2025-12-10)**: Initial constitution based on A1000000 project lessons
