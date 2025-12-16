---
paths: hms_commander/**/*.py
---

# HEC-HMS Execution

## Primary Sources

**Code**:
- `hms_commander/HmsCmdr.py` - High-level execution API
- `hms_commander/HmsJython.py` - Jython script generation

**Examples**:
- `examples/01_multi_version_execution.ipynb` - Version detection workflow
- `examples/02_run_all_hms413_projects.ipynb` - Parallel execution

## Decision: When to Use What

### Use HmsCmdr (High-Level)

**For most use cases**:
```python
from hms_commander import init_hms_project, HmsCmdr

init_hms_project(r"C:\Projects\watershed")
HmsCmdr.compute_run("Run 1")
```

**Methods**: See `HmsCmdr.py` docstrings for complete API

### Use HmsJython (Low-Level)

**When you need**:
- Custom script generation
- Version-specific syntax control
- Advanced workflows

**Example**: See `examples/01_multi_version_execution.ipynb` cells 8-12

## Critical: HMS 3.x vs 4.x

### HMS 3.x (32-bit, Python 2)

**MUST use** `python2_compatible=True`:

```python
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name=run,
    python2_compatible=True  # CRITICAL!
)
```

**Why**: HMS 3.x uses Jython 2.5 (Python 2 syntax)

### HMS 4.x (64-bit, Python 3)

**Default** (Python 3 syntax):

```python
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name=run
)
```

### Version Detection

**Automatic detection**:
```python
hms_exe = HmsJython.find_hms_executable()
# Auto-detects from path (Program Files vs Program Files (x86))
```

**See**: `examples/01_multi_version_execution.ipynb` cell 6 for detection workflow

## Key Differences

| Aspect | HMS 3.x | HMS 4.x |
|--------|---------|---------|
| Architecture | 32-bit | 64-bit |
| Install Path | Program Files (x86) | Program Files |
| Python Syntax | Python 2 | Python 3 |
| Max Memory | ~1.3 GB | 32+ GB |
| Java Location | java/bin/ | jre/bin/ |

**Complete table**: See .claude/rules/hec-hms/version-support.md

## Workflows

### Single Run
**Example**: `examples/02_run_all_hms413_projects.ipynb` cell 5

### Parallel Execution
**Example**: `examples/02_run_all_hms413_projects.ipynb` cells 10-15

### Custom Memory Allocation
**API**: `HmsJython.execute_script(script, hms_exe_path, max_memory="8G")`

## Common Issues

**Issue**: "HMS executable not found"
**Solution**: Read `HmsJython.find_hms_executable()` docstring for search paths

**Issue**: "OutOfMemoryError"
**Solution**: Increase max_memory parameter (see docstring)

**Issue**: "SyntaxError" (HMS 3.x)
**Solution**: Use `python2_compatible=True` (see above)

## Related

- **Version support**: .claude/rules/hec-hms/version-support.md
- **Testing**: .claude/rules/testing/example-projects.md
- **HmsExamples**: For multi-version testing
