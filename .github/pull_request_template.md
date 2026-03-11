## Summary

<!-- Brief description of what this PR does and why -->

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Refactoring (no functional changes)
- [ ] Example notebook

---

## LLM Self-Review

> **hms-commander encourages LLM-assisted contributions.** If your agent prepared this code, confirm it reviewed the style guide. See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.

### Style Compliance

- [ ] Static class pattern followed (`STYLE_GUIDE.md`, `.claude/rules/python/static-classes.md`)
- [ ] `@staticmethod` + `@log_call` on public methods (`.claude/rules/python/decorators.md`)
- [ ] Naming conventions followed (`STYLE_GUIDE.md`, `.claude/rules/python/naming-conventions.md`)
- [ ] `pathlib.Path` used, accepts both `str` and `Path` (`.claude/rules/python/path-handling.md`)
- [ ] Centralized `_parsing.py` patterns used (`.claude/rules/python/file-parsing.md`)

### Code Quality

- [ ] Google-style docstrings with Args, Returns, Raises
- [ ] Tested with real HEC-HMS project (`HmsExamples`)
- [ ] No hardcoded file paths
- [ ] Uses logging, not `print()`
- [ ] Proper error handling with informative messages

### API Changes (if applicable)

- [ ] `hms_object=None` parameter included for multi-project support
- [ ] Standard HMS parameter names used consistently
- [ ] Path parameters use `@standardize_path` or manual `Path()` conversion
- [ ] Return types consistent (DataFrames for tabular data, Path for file references)

### Notebooks (if applicable)

- [ ] First cell is markdown with H1 title
- [ ] Uses `HmsExamples` for reproducible data
- [ ] All cells execute without error

---

## Test Plan

<!-- How was this tested? Which example project? -->

## LLM Attribution

**Model/Tool used**: <!-- e.g., Claude Code (Opus 4.6), Codex CLI, Aider, Cursor, manual, etc. -->
