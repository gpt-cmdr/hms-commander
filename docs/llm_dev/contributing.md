# Contributing to HMS Commander

Thank you for your interest in contributing to HMS Commander! This project embraces **CLB Engineering's LLM Forward Approach** and welcomes contributions from both humans and AI-assisted workflows.

## Quick Start for Contributors

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/hms-commander.git
cd hms-commander
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install in editable mode with all dependencies
pip install -e ".[all]"
```

### 3. Read the Context Files

Before contributing, familiarize yourself with:

- **[CLAUDE.md](../../CLAUDE.md)** - Complete project context for LLMs
- **[STYLE_GUIDE.md](../../STYLE_GUIDE.md)** - Coding standards and patterns
- **[DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md)** - Future plans

## Development Workflow

### LLM Forward Development

HMS Commander is built using the LLM Forward approach. When using Claude or other LLMs:

1. **Provide CLAUDE.md**: Include the contents as context
2. **Reference style guide**: Mention specific patterns to follow
3. **Use examples**: Point to existing code as reference
4. **Iterate**: Review AI-generated code carefully

### Code Quality Standards

#### Static Type Hints (Optional but Encouraged)

```python
from pathlib import Path
import pandas as pd

def get_subbasins(basin_path: str) -> pd.DataFrame:
    """Type hints improve LLM understanding."""
    ...
```

#### Comprehensive Docstrings (Required)

Use Google-style docstrings with examples:

```python
def function_name(param1: type1, param2: type2) -> return_type:
    """
    Brief description.

    Detailed explanation of what the function does,
    why it exists, and how to use it.

    Args:
        param1 (type1): Description of param1
        param2 (type2): Description of param2

    Returns:
        return_type: Description of return value

    Raises:
        ErrorType: When this happens

    Example:
        >>> from hms_commander import Module
        >>> result = function_name("value1", 123)
        >>> print(result)
        expected_output

    Note:
        Additional considerations or warnings
    """
```

#### Logging (Required)

Use the `@log_call` decorator:

```python
from ._logging_config import log_call

@staticmethod
@log_call
def my_function(param: str) -> bool:
    """Function automatically logged."""
    ...
```

### Testing

HMS Commander uses **example-based testing** with real HEC-HMS projects:

```python
# tests/test_new_feature.py
from pathlib import Path
import sys
import pytest

# Flexible imports
try:
    from hms_commander import HmsExamples, NewFeature
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent))
    from hms_commander import HmsExamples, NewFeature


def test_new_feature():
    """Test with real HMS project."""
    # Extract example project
    project_path = HmsExamples.extract_project("castro")

    # Test your feature
    result = NewFeature.do_something(project_path)

    # Assertions
    assert result is not None
    assert len(result) > 0
```

Run tests:

```bash
pytest tests/
```

## Contribution Types

### Bug Fixes

1. Create an issue describing the bug
2. Reference the issue in your PR
3. Add a test that reproduces the bug
4. Fix the bug
5. Verify the test passes

### New Features

1. Check [DEVELOPMENT_ROADMAP.md](../../DEVELOPMENT_ROADMAP.md)
2. Open an issue for discussion
3. Follow the class design patterns (see [Style Guide](style_guide.md))
4. Add comprehensive documentation
5. Create example notebook demonstrating usage
6. Update CLAUDE.md with API documentation

### Documentation

- **Docstrings**: In-code documentation
- **User Guide**: `docs/user_guide/`
- **Examples**: Jupyter notebooks in `examples/`
- **API Reference**: Auto-generated from docstrings

### Example Notebooks

Notebooks should:

1. Use flexible import pattern
2. Use HMS example projects when possible
3. Include clear markdown explanations
4. Be tested before submission

```python
# Standard notebook import pattern
from pathlib import Path
import sys

try:
    from hms_commander import init_hms_project
except ImportError:
    sys.path.append(str(Path().resolve().parent))
    from hms_commander import init_hms_project
```

## Code Review Process

### What We Look For

✅ **Good practices:**
- Follows style guide
- Has comprehensive docstrings
- Includes working examples
- Uses `@log_call` decorator
- Handles errors appropriately
- Updates CLAUDE.md

❌ **Red flags:**
- No documentation
- Breaks existing tests
- Doesn't follow static class pattern
- Missing error handling
- No usage example

### Review Checklist

Before submitting a PR:

- [ ] Code follows [STYLE_GUIDE.md](style_guide.md)
- [ ] All functions have docstrings with examples
- [ ] Tests pass (`pytest tests/`)
- [ ] Example notebook created (if applicable)
- [ ] CLAUDE.md updated with new API
- [ ] No breaking changes (or clearly documented)
- [ ] Logging configured properly

## Documentation Builds

### Local Documentation

Build and serve docs locally:

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Serve docs locally
mkdocs serve
```

Open http://localhost:8000 in your browser.

### Documentation Structure

```
docs/
├── index.md                 # Home page
├── getting_started/         # Installation, quick start
├── user_guide/              # Comprehensive guides
├── examples/                # Notebook documentation
├── api/                     # API reference (auto-generated)
├── data_formats/            # HMS file format specs
└── llm_dev/                 # Development guides
```

## LLM-Driven Development Tips

### Using Claude Code

When working with Claude Code:

1. **Set context**: Paste CLAUDE.md content
2. **Specify patterns**: Reference style guide sections
3. **Provide examples**: Point to similar existing code
4. **Iterate**: Review and refine AI suggestions

### Effective Prompts

Good prompt:
> "Add a method to HmsBasin to extract reach parameters, following the same pattern as get_loss_parameters(). Use HmsFileParser for parsing, add @log_call decorator, include comprehensive docstring with example."

Poor prompt:
> "Add reach parameters"

### AI-Assisted Testing

Use LLMs to:
- Generate test cases
- Create example data
- Draft documentation
- Suggest edge cases

But always:
- Review generated code
- Test thoroughly
- Verify against style guide

## Release Process

HMS Commander follows semantic versioning:

- **Major** (X.0.0): Breaking changes
- **Minor** (0.X.0): New features, backward compatible
- **Patch** (0.0.X): Bug fixes

Releases are managed by maintainers.

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an Issue
- **Features**: Start with an Issue for discussion
- **LLM Help**: Reference CLAUDE.md for context

## Code of Conduct

Be respectful, inclusive, and constructive. We're building tools for the engineering community together.

## Attribution

Contributors are recognized in:
- Git commit history
- Release notes
- Project documentation

## Recognition

Significant contributions may be acknowledged in:
- CLAUDE.md acknowledgments section
- Release announcements
- Documentation

---

Thank you for contributing to HMS Commander! Your work helps the hydrologic engineering community automate and improve their workflows.
