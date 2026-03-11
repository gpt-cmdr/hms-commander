# Contributing to hms-commander

## Our Philosophy: Don't Ask Me, Ask a GPT!

hms-commander was **built by LLMs**, is **designed for LLM workflows**, and **welcomes contributions prepared with LLM agent assistance**.

We encourage ALL contributors to use an LLM coding agent when preparing pull requests. The repository contains comprehensive, machine-readable style rules in `STYLE_GUIDE.md` and `.claude/rules/` that any LLM can read and follow. When your agent reads these rules before writing code, your PR becomes trivially easy to review.

**Why this works**: An LLM-reviewed PR that follows the style guide takes 5 minutes to review. A PR that ignores the style guide takes 50 minutes. Help us merge your code fast -- load the rules.

**Any agent works**: [Claude Code](https://claude.ai/code), [Codex CLI](https://github.com/openai/codex), [Aider](https://aider.chat), [Cursor](https://cursor.sh), [Gemini CLI](https://github.com/google-gemini/gemini-cli), or any other LLM coding tool. The rules are plain markdown -- every LLM can read them.

---

## Quick Start

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/hms-commander.git
cd hms-commander

# 2. Set up environment
pip install -e ".[all]"

# 3. Launch your preferred coding agent
claude          # Claude Code
codex           # OpenAI Codex CLI
aider           # Aider
cursor .        # Cursor IDE
```

Your agent will find `AGENTS.md`, `CLAUDE.md`, and `STYLE_GUIDE.md` files that provide codebase context. Have it read the style rules before writing code.

---

## The Self-Review Contract

This is what makes LLM contributions welcome rather than burdensome:

1. **Before writing code**: Your agent reads `STYLE_GUIDE.md` and the relevant `.claude/rules/` files
2. **Before submitting**: You run through the Self-Review Checklist below
3. **When opening the PR**: The PR template includes the checklist

If your agent followed the rules, your PR is easy to review and fast to merge. If it didn't, we'll ask you to re-run with the rules loaded. This isn't gatekeeping -- it's how we keep velocity high for everyone.

---

## LLM Self-Review Checklist

Have your agent confirm each item before opening a PR.

### Style Compliance

| Rule | Where to Read | What It Means |
|------|--------------|---------------|
| Static class pattern | `STYLE_GUIDE.md`, `.claude/rules/python/static-classes.md` | No `__init__` unless legitimately stateful. Call methods directly: `HmsBasin.get_subbasins(basin_file)` |
| Decorator stacking | `STYLE_GUIDE.md`, `.claude/rules/python/decorators.md` | `@staticmethod` then `@log_call` on all public methods |
| Naming conventions | `STYLE_GUIDE.md`, `.claude/rules/python/naming-conventions.md` | `snake_case` functions, `PascalCase` classes, HMS abbreviations |
| Path handling | `.claude/rules/python/path-handling.md` | `pathlib.Path` internally, accept both `str` and `Path` in parameters |
| File parsing | `.claude/rules/python/file-parsing.md` | Use centralized `_parsing.py` patterns |

### Code Quality

- [ ] All public functions have Google-style docstrings (Args, Returns, Raises)
- [ ] Tested with a real HEC-HMS project via `HmsExamples` -- no mocks or synthetic data
- [ ] No hardcoded file paths -- parameters accept both `str` and `Path`
- [ ] Uses `logging` (via `@log_call` or `logger`), not `print()`
- [ ] Error handling with appropriate exceptions and informative messages

### For API Changes

- [ ] `hms_object=None` parameter included for multi-project support
- [ ] Standard HMS parameter names used consistently
- [ ] Path parameters use `@standardize_path` or manual `Path()` conversion
- [ ] Return types are consistent (DataFrames for tabular data, Path for file references)

### For Example Notebooks

- [ ] First cell is markdown with H1 title (`# Descriptive Title`)
- [ ] Uses `HmsExamples` for reproducible data
- [ ] All cells execute without error

---

## API Consistency: The 5 Critical Rules

Any PR that adds or modifies public API methods must follow these rules:

| # | Rule | Violation Example | Correct Pattern |
|---|------|-------------------|-----------------|
| 1 | **Static class pattern** | `class Foo:` with `__init__` | Static methods, no instantiation |
| 2 | **@log_call required** | Public method without decorator | `@log_call` on every public method |
| 3 | **@staticmethod required** | Method in static class without it | `@staticmethod` above `@log_call` |
| 4 | **Parameter naming** | Inconsistent HMS parameter names | Follow `STYLE_GUIDE.md` conventions |
| 5 | **Path handling** | `filepath: Path` (rigid) | Accept both `str` and `Path` |

### Gold Standard Template

Copy this pattern for new classes:

```python
from hms_commander.Decorators import log_call, standardize_path
from pathlib import Path
from typing import Union

class MyNewAnalyzer:
    """Analyzer for [domain] data. Static class -- do not instantiate."""

    @staticmethod
    @log_call
    def analyze_data(
        file_path: Union[Path, str],
        hms_object=None
    ):
        """Analyze data from HEC-HMS output.

        Args:
            file_path: Path to input file (str or Path)
            hms_object: Optional HmsPrj context for multi-project support

        Returns:
            pd.DataFrame: Analysis results with columns [col1, col2, ...]

        Raises:
            FileNotFoundError: If file_path does not exist
            ValueError: If invalid parameters provided
        """
        file_path = Path(file_path)
        _hms = hms_object if hms_object is not None else hms
        # Implementation...
```

---

## What We Accept

- Bug fixes with test validation
- New HMS file parsing capabilities (`hms_commander/`)
- Basin model operations (`HmsBasin`)
- Meteorologic model operations (`HmsMet`)
- Control specification operations (`HmsControl`)
- Storm generation methods (`Atlas14Storm`, `FrequencyStorm`, `ScsTypeStorm`)
- AORC precipitation integration (`HmsAorc`)
- DSS file operations (`HmsDss`)
- Example notebooks (`examples/`)
- Documentation improvements
- Performance optimizations

## What We Don't Accept

- Changes that break the static class pattern without prior discussion
- Mock-based tests (use real HEC-HMS projects via `HmsExamples`)
- New dependencies without clear justification
- Changes that bypass professional review pathways (this is safety-critical flood modeling software)

---

## Development Setup

### Environment Setup

```bash
# Clone and install with all dependencies
git clone https://github.com/YOUR_USERNAME/hms-commander.git
cd hms-commander
pip install -e ".[all]"

# Or with specific dependency groups
pip install -e ".[gis]"   # GIS features only
pip install -e ".[dss]"   # DSS features only
```

### Testing

```python
from hms_commander import HmsExamples, init_hms_project

# Extract example project
project_path = HmsExamples.extract_project("ProjectName")
init_hms_project(project_path)

# Test your functionality
```

See `GETTING_STARTED.md` for complete setup instructions and `STYLE_GUIDE.md` for the full code standards reference.

---

## Commit Messages

Use conventional commit format with scope:

```
feat(HmsBasin): Add subbasin area extraction method
fix(HmsMet): Handle missing gage assignments correctly
docs(examples): Add Atlas 14 storm generation notebook
refactor(HmsCmdr): Simplify Jython script generation
```

When your contribution was prepared with LLM assistance, include attribution:

```
feat(HmsBasin): Add subbasin area extraction method

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

---

## Style Guide Reference for LLM Agents

These files contain the complete style rules. Have your agent read the ones relevant to your contribution:

### Primary Style Guide

| File | What It Covers |
|------|---------------|
| `STYLE_GUIDE.md` | Complete code standards, architecture, naming, patterns (21 KB) |

### Python Patterns (`.claude/rules/python/`)

| Rule File | What It Covers |
|-----------|---------------|
| `static-classes.md` | No instantiation pattern -- call methods directly on class |
| `decorators.md` | `@staticmethod` then `@log_call` stacking order |
| `naming-conventions.md` | `snake_case` functions, `PascalCase` classes, HMS abbreviations |
| `path-handling.md` | `pathlib.Path` internally, accept both `str` and `Path` |
| `file-parsing.md` | Centralized `_parsing.py` patterns |
| `error-handling.md` | Logging, exceptions, `LoggingConfig` |
| `constants.md` | Centralized constants in `_constants.py` |

### HEC-HMS Domain (`.claude/rules/hec-hms/`)

| Rule File | What It Covers |
|-----------|---------------|
| `execution.md` | `HmsCmdr` execution engine, Jython scripts |
| `basin-files.md` | Basin model parsing and modification |
| `met-files.md` | Meteorologic model operations |
| `control-files.md` | Control specification operations |
| `clone-workflows.md` | Cloning basin/met/control files |
| `dss-operations.md` | DSS file reading and writing |
| `atlas14-storms.md` | Atlas 14 hyetograph generation |
| `frequency-storms.md` | TP-40 Frequency storm generation |
| `critical-bugs-workarounds.md` | Known HMS bugs and workarounds |

### Testing & Documentation

| Rule File | What It Covers |
|-----------|---------------|
| `.claude/rules/testing/tdd-approach.md` | Test with real HMS projects, not mocks |
| `.claude/rules/testing/example-projects.md` | Example project management |
| `.claude/rules/documentation/notebook-standards.md` | H1 title required, execution policy |

---

## Community Standards

### Respect for Maintainer Time

The entire point of LLM self-review is to reduce review burden. A well-prepared PR is a gift to the maintainer. A poorly prepared PR -- regardless of whether a human or LLM wrote it -- wastes everyone's time.

### Professional Context

hms-commander is used for **hydrologic modeling and flood prediction**. Professional engineers use this library to make decisions that affect public safety. All contributions are reviewed with this context in mind.

### LLM Forward Philosophy

This project follows the [LLM Forward](https://clbengineering.com/llm-forward) philosophy: professional responsibility first, LLMs positioned forward to accelerate engineering insight. See `docs/CLB_ENGINEERING_APPROACH.md` for the complete framework.

### Conduct

- Be respectful and professional in all interactions
- Focus on engineering quality and code correctness
- Welcome contributors of all experience levels
- Judge contributions on merit, not on what tool was used to write them

---

## Getting Help

- **Open an issue** for questions, bug reports, or feature requests
- **Read `AGENTS.md` files** throughout the repo for codebase context
- **Read `STYLE_GUIDE.md`** for the complete code standards reference
- **Check `examples/`** for working patterns and usage demonstrations
- **Your LLM agent can explore the codebase** -- that's exactly what it's designed for

---

*hms-commander is maintained by [CLB Engineering Corporation](https://clbengineering.com/). Licensed under MIT.*
