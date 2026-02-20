---
paths: hms_commander/**/*.py
---

# Path Handling

## Primary Rule: Always Use `pathlib.Path`

Never use raw strings or `os.path` for file paths in hms-commander.

```python
from pathlib import Path

# ✅ Correct
file_path = Path(file_path)
project_dir = Path(project_dir)

# ❌ Wrong
import os
file_path = os.path.join(dir, "file.basin")
```

## Critical: HMS Requires Absolute Paths

**See also**: `.claude/rules/hec-hms/critical-bugs-workarounds.md` — Bug 1

HMS Jython API requires absolute paths. Always resolve at function entry:

```python
@staticmethod
@log_call
def get_subbasins(basin_path: Union[str, Path]) -> Dict[str, Any]:
    basin_path = Path(basin_path).resolve()  # ← resolve to absolute immediately
    # ...
```

## Standard Path Conversion Pattern

All public methods accept `Union[str, Path]` and convert at entry:

```python
def get_X(file_path: Union[str, Path], name: str) -> Dict[str, Any]:
    file_path = Path(file_path)  # Convert early
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    # ...
```

## HMS Project Path Conventions

```python
from pathlib import Path

project_dir = Path(r"C:\Projects\MyWatershed")

# HMS file paths
hms_file = project_dir / "MyWatershed.hms"
basin_file = project_dir / "Baseline.basin"
met_file = project_dir / "Storms.met"
control_file = project_dir / "Feb2014.control"
dss_file = project_dir / "MyWatershed.dss"

# Results
run_log = project_dir / "MyRun.log"
```

## Windows Path Handling

Use raw strings or forward slashes:
```python
# ✅ All of these work
Path(r"C:\Projects\watershed")
Path("C:/Projects/watershed")
Path("C:\\Projects\\watershed")

# Pass to HMS Jython as string with forward slashes
hms_path = str(project_dir).replace("\\", "/")
```

## Glob Patterns

```python
# Find all basin files in project
basin_files = list(project_dir.glob("*.basin"))

# Find all project files recursively
hms_files = list(base_dir.rglob("*.hms"))
```

## Related

- **Absolute path bug**: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
- **File parsing**: `.claude/rules/python/file-parsing.md`
- **Constants (extensions)**: `.claude/rules/python/constants.md`
