# Installation

HMS Commander can be installed via pip or from source for development.

## Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows (required for HEC-HMS integration)
- **HEC-HMS**: Version 3.3+ or 4.4.1+ installed on your system

## Installation Options

### Basic Installation

For basic HMS file operations and project management:

```bash
pip install hms-commander
```

This includes:
- Basin, met, control, gage file operations
- Project management and initialization
- HmsPrj DataFrame access
- Execution engine (requires HMS installed)

### With DSS Support

For DSS file operations and results analysis:

```bash
pip install hms-commander[dss]
```

Additional packages:
- ras-commander (provides DSS functionality)
- pyjnius (Java bridge for DSS)

## Installing from Source

For the latest development version:

### Clone Repository

```bash
git clone https://github.com/gpt-cmdr/hms-commander.git
cd hms-commander
```

### Development Install

```bash
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate

# Install in editable mode with all extras
pip install -e ".[all]"
```

### Quick Development Pattern

For rapid development without installation:

```python
from pathlib import Path
import sys

# Add to path
current_file = Path(__file__).resolve()
parent_directory = current_file.parent.parent
sys.path.append(str(parent_directory))

# Now import
from hms_commander import init_hms_project, HmsPrj
```

## Verify Installation

Test your installation:

```python
import hms_commander
print(hms_commander.__version__)

# Check available classes
from hms_commander import (
    HmsPrj,
    HmsBasin,
    HmsMet,
    HmsControl,
    HmsCmdr,
)

print("HMS Commander installed successfully!")
```

## Next Steps

- [Quick Start Guide](quick_start.md) - Get started with basic usage
- [Project Initialization](project_initialization.md) - Learn how to initialize HMS projects
- [User Guide](../user_guide/overview.md) - Comprehensive feature documentation

## Troubleshooting

### Import Errors

If you encounter import errors:

```python
# Check if optional dependencies are installed
from hms_commander import HmsDss
if HmsDss.is_available():
    print("DSS support available")
else:
    print("Install DSS support: pip install hms-commander[dss]")
```

### HEC-HMS Not Found

HMS Commander requires HEC-HMS to be installed for execution:

```python
from hms_commander import HmsJython

# Find installed HMS versions
exe_path = HmsJython.find_hms_executable()
print(f"HMS found at: {exe_path}")
```

### Java/DSS Issues

If DSS operations fail, ensure Java is properly configured:

```python
# Check Java environment
import os
java_home = os.environ.get('JAVA_HOME')
print(f"JAVA_HOME: {java_home}")
```

See [DSS Operations Guide](../user_guide/dss_operations.md) for detailed setup.
