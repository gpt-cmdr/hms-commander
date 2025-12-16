---
paths: hms_commander/**/*.py, tests/**/*.py
---

# Testing with Example Projects

## Primary Source

**Code**: `hms_commander/HmsExamples.py`

Complete API for discovering and extracting HEC-HMS example projects from local installations.

## Philosophy: No Mocks, Use Real Projects

**Wrong approach**:
```python
def test_get_subbasins():
    mock_basin_file = create_mock_basin()  # ❌ Not realistic
    result = HmsBasin.get_subbasins(mock_basin_file)
```

**Right approach**:
```python
def test_get_subbasins():
    from hms_commander import HmsExamples, HmsBasin

    HmsExamples.extract_project("tifton")  # ✅ Real HMS project
    result = HmsBasin.get_subbasins("tifton/tifton.basin")
```

**Why**: HEC-HMS files are complex. Mocks miss edge cases. Real projects test actual behavior.

## HmsExamples Workflow

### Discovery

```python
from hms_commander import HmsExamples

# List installed HMS versions
versions = HmsExamples.list_versions()
# Returns: ["4.13", "4.11", "4.6", "3.5", ...]

# List projects for a version
projects = HmsExamples.list_projects("4.13")
# Returns: ["castro", "river_bend", "tenk", "tifton"]
```

### Extraction

```python
# Extract to default location (tests/projects/)
HmsExamples.extract_project("tifton")

# Extract to custom location
HmsExamples.extract_project("tifton", output_path="custom/path/")

# Extract specific version
HmsExamples.extract_project("tifton", version="4.11")
```

### Verification

```python
# Check if already extracted
if HmsExamples.is_project_extracted("tifton"):
    print("Already extracted, skip")
```

## Available Example Projects

**HMS 4.13 Examples** (most complete):
- **castro** - Simple watershed (2 subbasins)
- **river_bend** - Reservoir operations
- **tenk** - Gridded precipitation (HRAP cells)
- **tifton** - Time series demonstration

**Location**: `C:\Program Files\HEC\HEC-HMS\4.13\examples\`

## Testing Pattern

```python
import pytest
from pathlib import Path
from hms_commander import HmsExamples, HmsBasin

@pytest.fixture(scope="session")
def tifton_project():
    """Extract tifton project once per test session."""
    HmsExamples.extract_project("tifton")
    return Path("tests/projects/tifton")

def test_get_subbasins(tifton_project):
    basin_file = tifton_project / "tifton.basin"
    subbasins = HmsBasin.get_subbasins(str(basin_file))

    assert len(subbasins) > 0
    assert "Area" in subbasins.columns
```

## Multi-Version Testing

Test across HMS versions:

```python
@pytest.mark.parametrize("version", ["4.13", "4.11", "4.6"])
def test_execution_multi_version(version):
    HmsExamples.extract_project("tifton", version=version)
    # Test execution...
```

**See**: `examples/01_multi_version_execution.ipynb` for complete workflow

## Project Structure

After extraction:
```
tests/projects/tifton/
├── tifton.hms          # Project file
├── tifton.basin        # Basin model
├── tifton.met          # Met model
├── tifton.control      # Control specs
├── tifton.gage         # Gages
└── results/            # DSS results (if run)
```

## Related

- **TDD approach**: .claude/rules/testing/tdd-approach.md
- **HmsExamples API**: hms_commander/HmsExamples.py
- **Multi-version**: examples/01_multi_version_execution.ipynb
