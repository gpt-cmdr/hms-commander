# Style Guide

HMS Commander follows consistent coding standards for maintainability and LLM-friendliness.

For the complete style guide, see: [STYLE_GUIDE.md](https://github.com/gpt-cmdr/hms-commander/blob/main/STYLE_GUIDE.md) in the repository root.

## Quick Reference

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Functions/Variables | snake_case | `get_subbasins()` |
| Classes | PascalCase | `HmsBasin` |
| Constants | UPPER_SNAKE | `INCHES_TO_MM` |
| Private | Leading _ | `_parse_block()` |

### Static Class Pattern

```python
# Good
HmsBasin.get_subbasins(basin_path)

# Bad
basin = HmsBasin()
basin.get_subbasins(basin_path)
```

### Docstring Template

```python
def function_name(param1: type1, param2: type2) -> return_type:
    """
    Brief description.

    Args:
        param1 (type1): Description
        param2 (type2): Description

    Returns:
        return_type: Description

    Example:
        >>> result = function_name(val1, val2)
    """
```

### When to Use Submodules

✅ **Use submodules when:**
- 5+ related classes
- Optional dependencies
- Experimental features
- Large utility collections (500+ lines)

❌ **Don't use submodules for:**
- Single purpose classes
- Few functions (<5 methods)
- Premature organization

See [full style guide](https://github.com/gpt-cmdr/hms-commander/blob/main/STYLE_GUIDE.md) for detailed patterns and examples.
