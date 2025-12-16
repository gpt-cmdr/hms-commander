# Project Management

Working with HEC-HMS projects using HMS Commander's DataFrame-based approach.

## Overview

HMS Commander provides the `HmsPrj` class for managing HEC-HMS projects. The project object maintains DataFrames for all project components (basins, meteorologic models, controls, runs, gages) and provides methods for project-wide operations.

## Quick Start

```python
from hms_commander import init_hms_project, hms

# Initialize project
init_hms_project(r"C:\path\to\project")

# Access project DataFrames
print(hms.basin_df)      # Basin models
print(hms.met_df)        # Meteorologic models
print(hms.control_df)    # Control specifications
print(hms.run_df)        # Simulation runs
print(hms.gage_df)       # Time-series gages
```

## Key Features

- **DataFrame-based interface** - All project data in pandas DataFrames
- **Multi-project support** - Manage multiple projects simultaneously
- **Automatic discovery** - Scans project folder for all HMS files
- **Path management** - Maintains absolute paths to all project files

## Related Topics

- [Project Initialization](../getting_started/project_initialization.md) - How to initialize projects
- [API Reference: HmsPrj](../api/hms_prj.md) - Complete API documentation
- [Quick Start Guide](../getting_started/quick_start.md) - Basic workflow

## Detailed Documentation

For complete API documentation and examples, see:
- [CLAUDE.md](https://github.com/gpt-cmdr/hms-commander/blob/main/CLAUDE.md) - Complete API reference

---

*This page is being developed. Check back for more examples and workflows.*
