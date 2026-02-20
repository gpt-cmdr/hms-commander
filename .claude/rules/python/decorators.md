---
paths: hms_commander/**/*.py
---

# Python Decorators

## Overview

Two decorators are used consistently across all HMS classes: `@staticmethod` and `@log_call`.

## `@log_call` — Automatic Function Logging

**Source**: `hms_commander/_logging.py`

**Purpose**: Automatically logs function entry with arguments and exit with return values. Provides debugging visibility without manual print statements.

**Usage — always stack below `@staticmethod`**:
```python
from hms_commander._logging import log_call

class HmsBasin:
    @staticmethod
    @log_call
    def get_subbasins(basin_path: Union[str, Path]) -> Dict[str, Any]:
        """Get subbasins from basin file."""
        # implementation
```

**Decorator Order Matters**:
```python
# ✅ CORRECT order (log_call closer to function)
@staticmethod
@log_call
def my_method(...):

# ❌ WRONG order
@log_call
@staticmethod
def my_method(...):
```

**Why this order**: `@log_call` wraps the raw function; `@staticmethod` then makes the wrapped result a static method. Reversing the order wraps the staticmethod descriptor, which breaks.

## `@staticmethod` — No Instance Required

All HMS file operation methods are static. See `.claude/rules/python/static-classes.md` for complete rationale.

```python
# Call directly on class — no instantiation
subbasins = HmsBasin.get_subbasins("project.basin")

# ❌ Never instantiate
basin = HmsBasin()  # wrong
```

## When to Add `@log_call`

Add to **all public methods** in HMS classes:
- `get_*` methods (read operations)
- `set_*` methods (write operations)
- `clone_*` methods
- `compute_*` methods

Skip for:
- Private helper methods (`_my_helper`)
- Properties
- `__init__` (HMS classes don't have these)

## Related

- **Static classes**: `.claude/rules/python/static-classes.md`
- **Logging config**: `.claude/rules/python/error-handling.md`
- **Implementation**: `hms_commander/_logging.py`
