---
paths: hms_commander/**/*.py
---

# File Parsing Utilities

## Primary Source

**Authoritative**: `hms_commander/_parsing.py`

Complete API with docstrings for:
- `HmsFileParser.read_file()`
- `HmsFileParser.parse_blocks()`
- `HmsFileParser.parse_named_section()`
- `HmsFileParser.update_parameter()`
- `HmsFileParser.find_block()`
- `HmsFileParser.replace_block()`

## Why HmsFileParser Exists

Eliminates ~243 lines of duplicated parsing code across HmsBasin, HmsMet, HmsControl, HmsGage.

**Before consolidation**: Each class had its own file reading, block parsing, parameter updating
**After consolidation**: All use shared HmsFileParser utilities

## Common Patterns

### Pattern 1: Read HMS File (Encoding Fallback)

```python
from hms_commander._parsing import HmsFileParser

content = HmsFileParser.read_file("model.basin")
```

**Why**: Handles UTF-8 with Latin-1 fallback for older HMS files

### Pattern 2: Parse Named Blocks

```python
blocks = HmsFileParser.parse_blocks(content, "Subbasin")
# Returns: {'Sub1': {'Area': '100.0', ...}, 'Sub2': {...}}
```

**Use for**: Subbasin:, Junction:, Reach:, Gage:, etc.

### Pattern 3: Update Parameters

```python
updated_content, changed = HmsFileParser.update_parameter(
    content, "Area", "150.0"
)
```

**Returns**: (new content, bool indicating if changed)

## Usage Examples

See implementation in:
- `hms_commander/HmsBasin.py` lines 50-100
- `hms_commander/HmsMet.py` lines 40-80
- `hms_commander/HmsControl.py` lines 30-60

## File Format Support

Handles HMS ASCII text file format:
```
Block: Name
     Parameter1: Value1
     Parameter2: Value2
End:
```

## Related

- **Constants**: .claude/rules/python/constants.md (FILE_EXTENSIONS, PRIMARY_ENCODING)
- **Error handling**: .claude/rules/python/error-handling.md
