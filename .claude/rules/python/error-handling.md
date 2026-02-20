---
paths: hms_commander/**/*.py
---

# Error Handling

## Primary Pattern: Encoding Fallback

HMS files from Windows installations often use Latin-1 encoding. Always use the two-step fallback:

```python
from pathlib import Path

def read_hms_file(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        return file_path.read_text(encoding='latin-1')
```

**Why**: HMS was developed for Windows and older versions write files in system codepage (Latin-1 / Windows-1252). Never assume UTF-8.

**Preferred**: Use `HmsFileParser.read_file()` which handles encoding fallback automatically.

```python
from hms_commander._parsing import HmsFileParser

content = HmsFileParser.read_file(file_path)  # handles encoding internally
```

## Standard Exception Types

| Situation | Exception |
|-----------|-----------|
| File not found | `FileNotFoundError` |
| Element not found in file | `ValueError(f"Element '{name}' not found in {file_path}")` |
| Invalid parameter value | `ValueError(f"Invalid value: {value}")` |
| HMS execution failure | `RuntimeError(f"HMS execution failed: {detail}")` |

## LoggingConfig — Log Levels

**Source**: `hms_commander/_logging.py` (or `hms_commander/LoggingConfig.py`)

```python
from hms_commander import LoggingConfig

# Set log level for debugging
LoggingConfig.set_level("DEBUG")   # Verbose — show @log_call entries
LoggingConfig.set_level("INFO")    # Normal — show info messages (default)
LoggingConfig.set_level("WARNING") # Quiet — warnings and errors only
```

## Error Reporting in Agent Workflows

For long-running agents, use structured error reporting:

```python
try:
    result = HmsCmdr.compute_run(run_name)
except Exception as e:
    # Log with context
    logger.error(f"Failed to compute run '{run_name}': {e}")
    # Document in workflow
    workflow.log_change("Execution", "FAILED",
                        run=run_name, error=str(e),
                        justification="Execution error - see log")
    # Continue if pre-existing issue, raise if new issue
    if run_name in known_failing_runs:
        workflow.document_preexisting_issue(run_name, str(e))
    else:
        raise
```

## What NOT to Do

```python
# ❌ Bare except — hides all errors
try:
    content = file.read_text()
except:
    pass

# ❌ Silent fallback without logging
try:
    result = compute()
except Exception:
    result = default_value  # Silent failure

# ❌ Hardcoding encoding without fallback
content = file.read_text(encoding='utf-8')  # Fails on Latin-1 files
```

## Related

- **@log_call**: `.claude/rules/python/decorators.md`
- **File parsing**: `.claude/rules/python/file-parsing.md`
- **Critical bugs**: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
