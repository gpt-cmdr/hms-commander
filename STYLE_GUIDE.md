# HMS Commander Style Guide

> Architecture and coding standards for hms-commander development, adapted from ras-commander patterns

## Table of Contents

- [Core Principles](#core-principles)
- [Code Organization](#code-organization)
- [Naming Conventions](#naming-conventions)
- [Class Design Patterns](#class-design-patterns)
- [Documentation Standards](#documentation-standards)
- [Import Patterns](#import-patterns)
- [Error Handling](#error-handling)
- [Testing Philosophy](#testing-philosophy)
- [File Structure](#file-structure)
- [When to Use Submodules](#when-to-use-submodules)

---

## Core Principles

### 1. LLM-First Development
HMS Commander is designed to be both human-readable and LLM-friendly:
- Clear, descriptive function names
- Comprehensive docstrings with examples
- Consistent patterns throughout the codebase
- CLAUDE.md provides complete context for AI-assisted development

### 2. Static Class Architecture
Most classes use static methods without requiring instantiation:

```python
# Good - Direct static method call
HmsBasin.get_subbasins(basin_path)

# Bad - Unnecessary instantiation
basin = HmsBasin()
basin.get_subbasins(basin_path)
```

**Why?** Static classes provide:
- Cleaner API for simple operations
- No state management overhead
- Direct function calls without setup
- Compatibility with both procedural and OOP styles

### 3. Technological Lineage Naming
Function names should reflect their data source and HMS heritage:

| Data Source | Naming Style | Example | Rationale |
|------------|--------------|---------|-----------|
| HMS Text Files | Descriptive snake_case | `get_loss_parameters()` | Modern Python convention |
| DSS Operations | Mirror ras-commander | `extract_hms_results()` | Consistency with ecosystem |
| Internal Utils | Unabbreviated names | `parse_time_interval()` | Self-documenting code |

**Common HMS abbreviations** (use sparingly):
- `hms`, `prj`, `met`, `bc` (boundary condition), `ic` (initial condition)
- Avoid: `geom` → use `geometry`, `num` → use `number`

---

## Code Organization

### Main Package Structure

```
hms_commander/
├── __init__.py              # Package exports
├── _parsing.py              # Internal parsing utilities
├── _constants.py            # Centralized constants
├── hms_prj.py              # Project management (HmsPrj class)
├── hms_basin.py            # Basin model operations
├── hms_met.py              # Meteorologic operations
├── hms_control.py          # Control specifications
├── hms_gage.py             # Gage data operations
├── hms_geo.py              # Geospatial operations
├── hms_run.py              # Run configuration
├── hms_cmdr.py             # Execution engine
├── hms_jython.py           # Jython script generation
├── hms_dss.py              # DSS file operations
├── hms_results.py          # Results analysis
├── hms_utils.py            # Utilities
├── hms_examples.py         # Example project management
└── _logging_config.py      # Centralized logging
```

### Module Organization Principles

1. **One class per file** - Each major HMS component gets its own module
2. **Flat hierarchy** - Avoid deep nesting; prefer single-level structure
3. **Internal modules** - Prefix with `_` for implementation details (e.g., `_parsing.py`)
4. **Logical grouping** - Related functionality stays together (e.g., all basin operations in `hms_basin.py`)

---

## When to Use Submodules

### Use Submodules When:

#### 1. **Multiple Related Classes** (5+ classes)
Create a submodule when functionality requires multiple coordinated classes:

```python
# Example: If DSS operations grow significantly
hms_commander/dss/
    __init__.py          # Expose main classes
    dss_operations.py    # Core DSS I/O
    dss_catalog.py       # Catalog management
    dss_timeseries.py    # Time-series specific
    dss_paired.py        # Paired data operations
```

#### 2. **Optional Dependencies**
Isolate features requiring optional packages:

```python
# Current example
hms_commander/
    hms_dss.py          # Requires ras-commander (optional)
    hms_geo.py          # Requires geopandas (optional)

# If it grows, convert to:
hms_commander/geo/
    __init__.py         # Lazy import with fallback
    parsers.py
    exporters.py
    transformations.py
```

#### 3. **Experimental Features**
Keep beta functionality separate:

```python
hms_commander/experimental/
    __init__.py
    gridded_precip.py   # Under development
    sediment_transport.py
```

#### 4. **Large Utility Collections**
When utilities grow beyond 500 lines:

```python
hms_commander/utils/
    __init__.py
    units.py            # Unit conversions
    time.py             # Date/time operations
    validation.py       # Input validation
    file_ops.py         # File operations
```

### Don't Use Submodules When:

❌ **Single purpose classes** - Keep `hms_basin.py`, `hms_met.py` as single files
❌ **Premature organization** - Wait until clear complexity threshold
❌ **Few functions** - A class with 3-5 methods doesn't need a submodule
❌ **No logical separation** - Don't create structure just for aesthetics

### Submodule Template

When creating a submodule, use this pattern:

```python
# hms_commander/submodule/__init__.py
"""
Submodule description.

Available classes:
    - MainClass: Primary functionality
    - HelperClass: Supporting operations
"""

from .main_module import MainClass
from .helper_module import HelperClass

__all__ = ['MainClass', 'HelperClass']
```

---

## Naming Conventions

### Python Standards

| Element | Convention | Example |
|---------|-----------|---------|
| Functions/Variables | snake_case | `get_subbasins()`, `basin_path` |
| Classes | PascalCase | `HmsCmdr`, `HmsBasin` |
| Constants | UPPER_SNAKE | `INCHES_TO_MM`, `DEFAULT_THRESHOLD` |
| Private/Internal | Leading underscore | `_parse_block()`, `_constants.py` |
| Module names | snake_case | `hms_basin.py`, `hms_cmdr.py` |

### HMS-Specific Patterns

**File path parameters:**
```python
# Good - Descriptive and clear
def get_subbasins(basin_path: str) -> pd.DataFrame:

# Bad - Ambiguous
def get_subbasins(path: str) -> pd.DataFrame:
```

**HMS object references:**
```python
# Good - Consistent naming
def compute_run(run_name: str, hms_object=None):

# Bad - Inconsistent
def compute_run(run_name: str, project=None):
```

**Return types:**
```python
# Good - Clear DataFrame content
subbasins_df = HmsBasin.get_subbasins(basin_path)

# Bad - Generic name
df = HmsBasin.get_subbasins(basin_path)
```

---

## Class Design Patterns

### Static Class Template

Most HMS Commander classes follow this pattern:

```python
from pathlib import Path
import pandas as pd
from ._logging_config import log_call

class HmsComponent:
    """
    Component operations for HEC-HMS.

    This class provides static methods for working with HMS component files.
    All methods can be called directly without instantiation.
    """

    @staticmethod
    @log_call
    def get_data(file_path: str) -> pd.DataFrame:
        """
        Retrieve data from HMS component file.

        Args:
            file_path (str): Path to component file (.component extension)

        Returns:
            pd.DataFrame: Component data with columns [name, property, value]

        Raises:
            FileNotFoundError: If file_path does not exist
            ValueError: If file format is invalid

        Example:
            >>> from hms_commander import HmsComponent
            >>> df = HmsComponent.get_data("model.component")
            >>> print(df.head())
        """
        file_path = Path(file_path)

        # Implementation
        ...

        return results_df
```

### Project-Aware Pattern

For methods that need project context:

```python
@staticmethod
@log_call
def modify_component(name: str, parameter: str, value: float,
                     hms_object=None) -> bool:
    """
    Modify component parameter.

    Args:
        name (str): Component name
        parameter (str): Parameter to modify
        value (float): New parameter value
        hms_object (HmsPrj, optional): Project instance.
            Uses global hms object if None.

    Returns:
        bool: True if modification successful

    Example:
        >>> # Single project (uses global hms)
        >>> HmsComponent.modify_component("Sub1", "Area", 150.0)

        >>> # Multiple projects
        >>> project1 = HmsPrj()
        >>> HmsComponent.modify_component("Sub1", "Area", 150.0,
        ...                               hms_object=project1)
    """
    # Get project instance
    if hms_object is None:
        from . import hms
        hms_object = hms

    # Implementation using hms_object
    ...
```

### Clone Operation Pattern

All clone operations follow the "CLB Engineering LLM Forward Approach":

```python
@staticmethod
@log_call
def clone_component(template_name: str, new_name: str,
                   description: str = None, hms_object=None) -> bool:
    """
    Clone HMS component (non-destructive).

    Creates a new component based on template. Follows CLB Engineering
    LLM Forward Approach:
    - Non-destructive: Preserves original
    - Traceable: Updates description with clone metadata
    - GUI-verifiable: New component appears in HEC-HMS GUI
    - Project integration: Updates .hms project file

    Args:
        template_name (str): Name of component to clone
        new_name (str): Name for new component
        description (str, optional): Description for new component.
            Auto-generated if None.
        hms_object (HmsPrj, optional): Project instance

    Returns:
        bool: True if clone successful

    Example:
        >>> HmsComponent.clone_component("Original", "Modified")
    """
    # Implementation
    ...
```

---

## Documentation Standards

### Docstring Template

Use Google-style docstrings consistently:

```python
def function_name(param1: type1, param2: type2) -> return_type:
    """
    Brief one-line description.

    More detailed explanation if needed. Explain the purpose,
    behavior, and any important considerations.

    Args:
        param1 (type1): Description of param1
        param2 (type2): Description of param2
            Can span multiple lines with indent

    Returns:
        return_type: Description of return value

    Raises:
        ErrorType1: When this error occurs
        ErrorType2: When that error occurs

    Example:
        >>> from hms_commander import Module
        >>> result = function_name(value1, value2)
        >>> print(result)
        expected_output

    Note:
        Additional notes, warnings, or considerations
    """
```

### Module-Level Documentation

Each module should have clear documentation:

```python
"""
HMS Basin Model Operations

This module provides functions for reading, modifying, and analyzing
HEC-HMS basin model files (.basin).

Available Functions:
    - get_subbasins(): Extract subbasin information
    - get_junctions(): Extract junction information
    - set_loss_parameters(): Modify loss method parameters
    - clone_basin(): Create basin model copy

Example:
    >>> from hms_commander import HmsBasin
    >>> subbasins = HmsBasin.get_subbasins("model.basin")
    >>> print(subbasins.head())
"""
```

### Comment Standards

```python
# Good - Explain WHY, not WHAT
# HMS 3.x uses Python 2 syntax for print statements
if python2_compatible:
    script += 'print "Running model"\n'

# Bad - Obvious comment
# Print a message
print("Running model")

# Good - Document complex logic
# Transform from project CRS to WGS84 for web service compatibility
# EPSG:2278 (Texas State Plane) → EPSG:4326 (lat/lon)
transformer = Transformer.from_crs(project_crs, "EPSG:4326")

# Bad - Redundant comment
# Create transformer
transformer = Transformer.from_crs(project_crs, "EPSG:4326")
```

---

## Import Patterns

### Development vs. Installed Package

Support both workflows with flexible imports:

```python
"""Example script or test file."""

from pathlib import Path
import sys

# Flexible import pattern for development
try:
    # Try installed package first
    from hms_commander import init_hms_project, HmsPrj, HmsBasin
except ImportError:
    # Fall back to local development
    current_file = Path(__file__).resolve()
    parent_directory = current_file.parent.parent
    sys.path.append(str(parent_directory))
    from hms_commander import init_hms_project, HmsPrj, HmsBasin
```

### Import Organization

Order imports following PEP 8:

```python
# Standard library
import sys
from pathlib import Path
from typing import Optional, List, Dict

# Third-party packages
import pandas as pd
import numpy as np
from tqdm import tqdm

# Local imports - absolute
from hms_commander._logging_config import log_call
from hms_commander._constants import INCHES_TO_MM
from hms_commander._parsing import HmsFileParser

# Local imports - relative (within submodule only)
from ._utils import helper_function
```

### Lazy Imports for Optional Dependencies

```python
class HmsDss:
    """DSS operations using ras-commander."""

    @staticmethod
    def is_available() -> bool:
        """Check if DSS functionality is available."""
        try:
            import ras_commander
            return True
        except ImportError:
            return False

    @staticmethod
    @log_call
    def read_timeseries(dss_file: str, pathname: str):
        """Read time-series from DSS file."""
        try:
            from ras_commander import RasDss
        except ImportError:
            raise ImportError(
                "DSS operations require ras-commander. "
                "Install with: pip install hms-commander[dss]"
            )

        # Use RasDss functionality
        ...
```

---

## Error Handling

### Exception Strategy

```python
from pathlib import Path

def read_file(file_path: str) -> str:
    """Read HMS file with proper error handling."""
    file_path = Path(file_path)

    # Validate input
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    if file_path.suffix != '.basin':
        raise ValueError(
            f"Invalid file type: {file_path.suffix}. "
            f"Expected .basin file."
        )

    # Attempt operation with fallback
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # HMS files sometimes use Latin-1 encoding
        content = file_path.read_text(encoding='latin-1')

    return content
```

### Logging Levels

Use appropriate logging levels:

```python
import logging
from ._logging_config import log_call

logger = logging.getLogger(__name__)

@log_call  # Logs function entry/exit at DEBUG level
def process_data(data):
    logger.debug(f"Processing {len(data)} records")  # Development info
    logger.info("Started data processing")           # User-facing progress
    logger.warning("Missing optional parameter X")   # Potential issues
    logger.error("Failed to parse record Y")         # Errors
    logger.critical("Database connection lost")      # Critical failures
```

---

## Testing Philosophy

### Example-Based Testing

HMS Commander uses real HMS example projects instead of traditional unit tests:

```python
# tests/test_basin.py
"""Test basin operations using HEC-HMS 4.13 example projects."""

from pathlib import Path
import sys
import pytest

# Flexible imports
try:
    from hms_commander import HmsExamples, HmsBasin
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent))
    from hms_commander import HmsExamples, HmsBasin


def test_get_subbasins_castro():
    """Test subbasin extraction from Castro example project."""
    # Extract example if not present
    if not HmsExamples.is_project_extracted("castro"):
        project_path = HmsExamples.extract_project("castro")
    else:
        project_info = HmsExamples.get_project_info("castro")
        project_path = project_info['extracted_path']

    basin_file = project_path / "castro.basin"

    # Test extraction
    df = HmsBasin.get_subbasins(basin_file)

    # Validate results
    assert len(df) > 0, "Should find subbasins"
    assert 'name' in df.columns, "Should have name column"
    assert 'area' in df.columns, "Should have area column"


def test_modify_parameters():
    """Test parameter modification workflow."""
    # Setup
    project_path = HmsExamples.extract_project("simple")
    basin_file = project_path / "simple.basin"

    # Get original value
    original = HmsBasin.get_loss_parameters(basin_file, "Sub1")

    # Modify
    HmsBasin.set_loss_parameters(
        basin_file, "Sub1",
        curve_number=85
    )

    # Verify
    modified = HmsBasin.get_loss_parameters(basin_file, "Sub1")
    assert modified['curve_number'] == 85
```

### Test Organization

```
tests/
├── conftest.py              # Pytest configuration & fixtures
├── test_basin.py            # Basin operations
├── test_met.py              # Meteorologic operations
├── test_control.py          # Control specifications
├── test_execution.py        # Simulation execution
├── test_results.py          # Results analysis
└── integration/             # End-to-end workflows
    ├── test_clone_workflow.py
    └── test_atlas14_update.py
```

---

## File Structure

### Repository Organization

```
hms-commander/
├── .agent/                  # Agent-specific instructions
│   ├── CONSTITUTION.md
│   ├── PRIORITIES.md
│   └── LEARNINGS.md
├── .github/
│   └── workflows/           # CI/CD pipelines
├── docs/                    # MkDocs documentation source
│   ├── index.md
│   ├── getting_started.md
│   ├── user_guide/
│   ├── examples/
│   └── api/
├── examples/                # Jupyter notebooks
│   ├── 01_basic_usage.ipynb
│   ├── 02_execution.ipynb
│   └── ...
├── hms_commander/           # Main package
│   ├── __init__.py
│   ├── _constants.py
│   ├── _parsing.py
│   └── ...
├── tests/                   # Test suite
├── CLAUDE.md               # LLM context file
├── STYLE_GUIDE.md          # This file
├── README.md
├── pyproject.toml
├── mkdocs.yml              # Documentation config
└── LICENSE
```

### Planning Documents

Major features get planning documents in repo root:

```
PLAN_feature_name.md        # Feature-specific planning
DEVELOPMENT_ROADMAP.md      # Long-term vision
```

---

## Version Support Strategy

### HMS Version Compatibility

```python
from ._constants import MIN_HMS_3X_VERSION, MIN_HMS_4X_VERSION

def validate_hms_version(version_string: str) -> dict:
    """
    Validate HMS version compatibility.

    Returns:
        dict: {
            'version': '4.13',
            'major': 4,
            'minor': 13,
            'supported': True,
            'python2_required': False
        }
    """
    major, minor = parse_version(version_string)

    python2_required = major < 4
    supported = (
        (major == 3 and version_string >= MIN_HMS_3X_VERSION) or
        (major == 4 and version_string >= MIN_HMS_4X_VERSION)
    )

    return {
        'version': version_string,
        'major': major,
        'minor': minor,
        'supported': supported,
        'python2_required': python2_required
    }
```

---

## Summary Checklist

When implementing new features:

- [ ] Use static methods with `@log_call` decorator
- [ ] Follow naming conventions (snake_case functions, PascalCase classes)
- [ ] Include comprehensive docstring with example
- [ ] Support both single and multi-project workflows (`hms_object` parameter)
- [ ] Handle file encoding with UTF-8 and Latin-1 fallback
- [ ] Add to `__init__.py` exports
- [ ] Create example notebook demonstrating usage
- [ ] Test with real HMS example projects
- [ ] Update CLAUDE.md with API documentation
- [ ] Consider if submodule is needed (>5 classes or optional dependency)

---

## References

- **ras-commander**: Sibling library for HEC-RAS automation
- **HEC-HMS Documentation**: [HEC HMS User's Manual](https://www.hec.usace.army.mil/software/hec-hms/documentation.aspx)
- **PEP 8**: Python style guide
- **Google Python Style Guide**: Docstring format reference

---

*This style guide evolves with the project. Suggestions welcome via issues or pull requests.*
