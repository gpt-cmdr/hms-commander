---
paths: hms_commander/**/*.py
---

# HMS Version Support

## Primary Source

**Code**: `hms_commander/HmsJython.py` - Version detection and script generation

**Examples**: `examples/01_multi_version_execution.ipynb` - Multi-version workflow

## Supported Versions

| Version | Support | Architecture | Python | Notes |
|---------|---------|--------------|--------|-------|
| **HMS 4.4.1+** | ✅ Full | 64-bit | Python 3 | Recommended |
| **HMS 3.3-3.5** | ✅ Full | 32-bit | Python 2 | Requires `python2_compatible=True` |
| HMS 4.0-4.3 | ❌ | 64-bit | Python 3 | Legacy classpath not supported |
| HMS 3.0-3.2 | ❓ | 32-bit | Python 2 | Untested |

## Critical Differences

### HMS 3.x (32-bit, Python 2)

**Install Path**: `C:\Program Files (x86)\HEC\HEC-HMS\3.x\`
**Max Memory**: ~1.3 GB
**Java**: `java/bin/java.exe`
**Python**: Jython 2.5 (Python 2 syntax)

**Script Generation**:
```python
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name=run,
    python2_compatible=True  # MUST be True for 3.x!
)
```

**Python 2 Syntax**:
```python
print "Computing run"  # No parentheses
```

### HMS 4.x (64-bit, Python 3)

**Install Path**: `C:\Program Files\HEC\HEC-HMS\4.x\`
**Max Memory**: 32+ GB
**Java**: `jre/bin/java.exe`
**Python**: Jython 2.7 (Python 3 syntax)

**Script Generation**:
```python
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name=run
    # python2_compatible=False (default)
)
```

**Python 3 Syntax**:
```python
print(f"Computing {run_name}")  # Parentheses required
```

## Auto-Detection

### By Install Path

```python
from pathlib import Path

hms_path = Path(r"C:\Program Files (x86)\HEC\HEC-HMS\3.3")

# Detect from path
is_3x = "Program Files (x86)" in str(hms_path)
python2_compatible = is_3x
```

### Using HmsJython

```python
hms_exe = HmsJython.find_hms_executable()
# Searches common install locations

# Check version from path
if "3." in str(hms_exe):
    python2_compatible = True
```

**See**: `HmsJython.find_hms_executable()` docstring for search paths

## Testing Across Versions

**Example**: `examples/01_multi_version_execution.ipynb` cells 10-15

Multi-version test pattern:
```python
for version in HmsExamples.list_versions():
    HmsExamples.extract_project("tifton", version=version)
    # Generate version-appropriate script
    # Execute and validate
```

## Command-Line Execution

### HMS 3.x
```cmd
"C:\Program Files (x86)\HEC\HEC-HMS\3.3\HEC-HMS.cmd" -script script.py
```

### HMS 4.x
```cmd
"C:\Program Files\HEC\HEC-HMS\4.11\HEC-HMS.cmd" -script script.py
```

## Related

- **Execution**: .claude/rules/hec-hms/execution.md
- **HmsJython API**: hms_commander/HmsJython.py
- **Examples**: examples/01_multi_version_execution.ipynb
