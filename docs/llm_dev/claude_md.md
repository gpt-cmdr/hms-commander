# CLAUDE.md Guide

Understanding and using the CLAUDE.md documentation file for AI-assisted development.

## What is CLAUDE.md?

`CLAUDE.md` is a comprehensive reference document written specifically for AI assistants (like Claude) working with the HMS Commander codebase. It provides complete API documentation, architectural patterns, and usage examples.

## Purpose

CLAUDE.md serves multiple audiences:

1. **AI Assistants** - Primary audience, provides complete context
2. **Developers** - Quick reference for all APIs
3. **New Contributors** - Architectural overview and patterns
4. **Documentation** - Source for auto-generating user docs

## Location

```
hms-commander/
├── CLAUDE.md          ← Main AI assistant documentation
├── STYLE_GUIDE.md     ← Coding standards
├── README.md          ← User-facing overview
└── docs/              ← Full documentation site
```

## Structure

### 1. Project Overview

```markdown
# CLAUDE.md

This file provides guidance to Claude Code...

## Project Overview
**hms-commander** is a Python library for automating HEC-HMS...
```

**Contains:**
- Project description
- Development environment setup
- Architecture overview

### 2. Development Environment

```markdown
## Development Environment

### Build Commands
- **Install locally**: `pip install -e .`
- **Install with optional dependencies**: `pip install -e ".[all]"`

### Dependencies
- **Python**: Requires 3.10+
- **Core packages**: pandas, numpy, pathlib, tqdm, requests
```

**Contains:**
- Installation methods
- Dependencies
- Environment management

### 3. Architecture Overview

```markdown
## Architecture Overview

### Core Classes and Execution Model

**Project Management**: `HmsPrj` class and global `hms` object
**File Operations Classes**: HmsBasin, HmsMet, HmsControl, HmsGage, HmsGeo
**Execution Classes**: HmsCmdr, HmsJython
```

**Contains:**
- Class organization
- Design patterns
- Execution model

### 4. Complete API Reference

```markdown
## Complete API Reference

### HmsBasin - Basin Model Operations
```python
HmsBasin.get_subbasins(basin_path)              # DataFrame of subbasins
HmsBasin.set_loss_parameters(basin_path, name, curve_number=80)
HmsBasin.clone_basin(template, new_name, description=None)
```
```

**Contains:**
- Every public method
- Parameter lists
- Return types
- Usage examples

### 5. File Formats

```markdown
## HEC-HMS File Formats

### Project File (.hms)
```
Project: ProjectName
Version: 4.9
BasinFile: ProjectName.basin
```
```

**Contains:**
- File format specifications
- Example sections
- Parsing notes

### 6. Development Patterns

```markdown
## Key Development Patterns

### Static Class Pattern
- Most classes use static methods with `@log_call` decorators
- No instantiation required
```

**Contains:**
- Architectural patterns
- Naming conventions
- Error handling

## Using CLAUDE.md

### For AI Assistants

When an AI assistant (like Claude Code) works with HMS Commander:

1. **Loads CLAUDE.md** - Automatically read by Claude Code
2. **Gets full context** - Complete API reference
3. **Follows patterns** - Architectural guidelines
4. **Uses examples** - Working code snippets

**Example AI workflow:**
```
User: "Clone the basin and update curve numbers"

AI: [Reads CLAUDE.md]
    - Finds HmsBasin.clone_basin() method
    - Sees example usage
    - Follows static class pattern
    - Generates code:

HmsBasin.clone_basin(
    template="Existing",
    new_name="Updated"
)
HmsBasin.set_loss_parameters(
    "Updated.basin",
    "Sub1",
    curve_number=85
)
```

### For Developers

Use CLAUDE.md as a quick reference:

```bash
# Search for specific API
grep -A 10 "HmsBasin.get_subbasins" CLAUDE.md

# Find file format info
grep -A 20 "Basin Model File" CLAUDE.md

# Check development patterns
grep -A 15 "Static Class Pattern" CLAUDE.md
```

### For Documentation Authors

Extract content from CLAUDE.md for user docs:

```python
# Data formats section → docs/data_formats/
# API reference section → Auto-generated with mkdocstrings
# Examples section → docs/user_guide/
```

## CLAUDE.md vs Other Docs

| Document | Audience | Purpose | Format |
|----------|----------|---------|--------|
| **CLAUDE.md** | AI Assistants | Complete API reference | Markdown |
| **README.md** | Users | Project overview | Markdown |
| **docs/** | Users | Full documentation site | MkDocs |
| **STYLE_GUIDE.md** | Contributors | Coding standards | Markdown |
| **API docs** | Developers | Auto-generated API | HTML |

## Keeping CLAUDE.md Updated

### When to Update

Update CLAUDE.md when:
- ✅ New classes added
- ✅ New public methods added
- ✅ File formats change
- ✅ Architectural patterns evolve
- ✅ Major functionality added

Don't update for:
- ❌ Internal implementation changes
- ❌ Private method changes
- ❌ Bug fixes (unless API changes)

### Update Process

1. **Modify code** - Implement new functionality
2. **Update CLAUDE.md** - Document new APIs
3. **Update docstrings** - Ensure API docs auto-generate
4. **Rebuild docs** - `mkdocs build`
5. **Commit together** - Code + docs in same commit

## Example: Adding New Method

```python
# 1. Add method to HmsBasin.py
class HmsBasin:
    @staticmethod
    @log_call
    def get_reach_parameters(basin_path: str, reach_name: str) -> Dict:
        """
        Get routing parameters for a reach.

        Args:
            basin_path (str): Path to .basin file
            reach_name (str): Name of reach

        Returns:
            Dict: Routing parameters

        Example:
            >>> params = HmsBasin.get_reach_parameters("model.basin", "Reach1")
        """
        # Implementation
```

```markdown
# 2. Add to CLAUDE.md

### HmsBasin - Basin Model Operations
```python
HmsBasin.get_subbasins(basin_path)              # DataFrame of subbasins
HmsBasin.get_junctions(basin_path)              # DataFrame of junctions
HmsBasin.get_reaches(basin_path)                # DataFrame of reaches
HmsBasin.get_reach_parameters(basin_path, name) # NEW: Reach routing params
```
```

## Best Practices

### ✅ Do

- Keep CLAUDE.md synchronized with code
- Use real working examples
- Document all public APIs
- Include file format specs
- Show architectural patterns

### ❌ Don't

- Don't include internal implementation details
- Don't let CLAUDE.md diverge from code
- Don't duplicate what's in docstrings
- Don't include outdated examples

## Related Topics

- [Contributing](contributing.md) - Development workflow
- [Style Guide](style_guide.md) - Coding standards
- [Architecture](architecture.md) - Technical details
- [LLM Forward Overview](overview.md) - Development philosophy

---

*CLAUDE.md is the single source of truth for AI assistants working with HMS Commander.*
