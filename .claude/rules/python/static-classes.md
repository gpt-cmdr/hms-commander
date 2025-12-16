---
paths: hms_commander/**/*.py
---

# Static Class Pattern

## Overview

All core HMS classes use static methods. No instantiation required.

## Pattern

```python
# ✅ Correct
from hms_commander import HmsBasin
subbasins = HmsBasin.get_subbasins("project.basin")

# ❌ Wrong - will fail
basin = HmsBasin()
subbasins = basin.get_subbasins("project.basin")
```

## Why Static?

1. **Cleaner API** - No confusion about instance vs class methods
2. **Consistent with HEC-HMS** - HMS files are stateless, operations are file-based
3. **Easier testing** - No setup/teardown of object instances
4. **Clear scoping** - Operations are file-based, not object-based

## Classes Using This Pattern

**File Operations**:
- HmsBasin, HmsMet, HmsControl, HmsGage, HmsRun, HmsGeo

**Execution**:
- HmsCmdr, HmsJython

**Data**:
- HmsDss, HmsResults

**Utilities**:
- HmsUtils, HmsExamples

**Source**: See hms_commander/ for complete class definitions

## The Exception: HmsPrj

**Only HmsPrj is instantiated** (for multiple project support):

```python
from hms_commander import HmsPrj, init_hms_project

# Single project - uses global hms object
init_hms_project(r"C:\Projects\project1")

# Multiple projects - create separate instances
project1 = HmsPrj()
project2 = HmsPrj()
init_hms_project(r"C:\Projects\project1", hms_object=project1)
init_hms_project(r"C:\Projects\project2", hms_object=project2)
```

## hms_object Parameter

When working with multiple projects, pass `hms_object` parameter:

```python
HmsBasin.get_subbasins("project.basin", hms_object=project1)
```

If `hms_object=None` (default), uses global `hms` object.

## Implementation Detail

All static methods use `@log_call` decorator for automatic logging:

```python
from hms_commander._logging import log_call

class HmsBasin:
    @staticmethod
    @log_call
    def get_subbasins(basin_path):
        """Get subbasins from basin file."""
        pass
```

See .claude/rules/python/decorators.md for @log_call details.

## Testing Pattern

Test static methods directly without instantiation:

```python
def test_get_subbasins():
    from hms_commander import HmsBasin, HmsExamples

    HmsExamples.extract_project("tifton")
    subbasins = HmsBasin.get_subbasins("tifton/tifton.basin")

    assert len(subbasins) > 0
```

## Related Patterns

- **@log_call**: .claude/rules/python/decorators.md
- **Path handling**: .claude/rules/python/path-handling.md
- **Testing**: .claude/rules/testing/example-projects.md
