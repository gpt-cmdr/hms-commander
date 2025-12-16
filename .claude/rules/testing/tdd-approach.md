---
paths: tests/**/*.py
---

# TDD Approach: Real Projects, Not Mocks

## Philosophy

**Don't mock HEC-HMS files. Use real example projects.**

## Why No Mocks?

### HEC-HMS Files Are Complex

- Multiple file types (.hms, .basin, .met, .control, .gage, .run)
- Interdependencies between files
- Version-specific formats (HMS 3.x vs 4.x)
- Edge cases in parsing (encoding, whitespace, special characters)

**Mocks miss these realities.**

### Real Projects Test Actual Behavior

```python
# ❌ Mock approach - unrealistic
def test_parse_basin():
    mock_content = "Subbasin: Test\n    Area: 100.0\nEnd:"
    result = parse(mock_content)

# ✅ Real project approach - realistic
def test_parse_basin():
    HmsExamples.extract_project("tifton")  # Real HMS project
    result = HmsBasin.get_subbasins("tifton/tifton.basin")
```

**Real projects include**:
- Actual file formats from HEC
- Edge cases HEC engineers encountered
- Version-specific quirks
- Complete project structure

## Testing Pattern

### Setup

```python
import pytest
from hms_commander import HmsExamples

@pytest.fixture(scope="session")
def example_projects():
    """Extract example projects once per test session."""
    HmsExamples.extract_project("tifton")
    HmsExamples.extract_project("castro")
    return True
```

### Test

```python
def test_basin_operations(example_projects):
    from hms_commander import HmsBasin

    subbasins = HmsBasin.get_subbasins("tifton/tifton.basin")

    # Test with real data
    assert len(subbasins) > 0
    assert "Area" in subbasins.columns
    assert all(subbasins["Area"] > 0)  # Real validation
```

### Multi-Version Testing

```python
@pytest.mark.parametrize("version", ["4.13", "4.11", "4.6"])
def test_multi_version(version):
    HmsExamples.extract_project("tifton", version=version)
    # Test across HMS versions with real projects
```

## Available Example Projects

**Use HmsExamples to discover**:
```python
versions = HmsExamples.list_versions()
projects = HmsExamples.list_projects("4.13")
```

**Common test projects**:
- **tifton**: Time series, simple structure (good for basic tests)
- **castro**: 2 subbasins, simple watershed (good for connectivity tests)
- **river_bend**: Reservoir operations (good for advanced features)
- **tenk**: Gridded precipitation (good for HRAP/gridded tests)

## Validation With Actual Execution

**Not just parsing - actually run HMS**:

```python
def test_execution():
    from hms_commander import init_hms_project, HmsCmdr

    HmsExamples.extract_project("tifton")
    init_hms_project("tifton")

    HmsCmdr.compute_run("1970_simulation")  # Actually run HMS

    # Validate results
    assert dss_file.exists()
    peaks = HmsResults.get_peak_flows(str(dss_file))
    assert len(peaks) > 0
```

**This catches**:
- File format issues
- Execution errors
- Version compatibility
- Real-world edge cases

## Related

- **HmsExamples**: .claude/rules/testing/example-projects.md
- **Example projects API**: hms_commander/HmsExamples.py
- **Multi-version**: examples/01_multi_version_execution.ipynb
