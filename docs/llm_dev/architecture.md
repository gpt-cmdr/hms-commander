# Architecture

Technical architecture and design decisions for HMS Commander.

## Overview

HMS Commander is designed around three core principles:
1. **Static class architecture** - No instantiation required for most operations
2. **DataFrame-based interfaces** - Pandas DataFrames for data manipulation
3. **File-based operations** - Direct manipulation of HMS text files

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     HMS Commander                            │
├─────────────────────────────────────────────────────────────┤
│  Project Layer                                              │
│  ┌────────────┐        ┌──────────────────────────┐        │
│  │  HmsPrj    │──────→ │ Project DataFrames       │        │
│  │  (global)  │        │ - basin_df, met_df, etc. │        │
│  └────────────┘        └──────────────────────────┘        │
├─────────────────────────────────────────────────────────────┤
│  File Operations Layer (Static Classes)                     │
│  ┌───────────┬───────────┬────────────┬──────────┐         │
│  │ HmsBasin  │ HmsMet    │ HmsControl │ HmsGage  │         │
│  └───────────┴───────────┴────────────┴──────────┘         │
│  ┌───────────┬───────────┬────────────┐                    │
│  │ HmsGeo    │ HmsRun    │ HmsUtils   │                    │
│  └───────────┴───────────┴────────────┘                    │
├─────────────────────────────────────────────────────────────┤
│  Execution Layer                                            │
│  ┌───────────┬───────────────────────────────────┐         │
│  │ HmsCmdr   │ HmsJython                         │         │
│  │ (compute) │ (script generation)               │         │
│  └───────────┴───────────────────────────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                 │
│  ┌───────────┬──────────────────────────────────┐          │
│  │ HmsDss    │ HmsResults                       │          │
│  │ (RasDss)  │ (analysis)                       │          │
│  └───────────┴──────────────────────────────────┘          │
├─────────────────────────────────────────────────────────────┤
│  Parsing Layer                                              │
│  ┌──────────────┬─────────────┐                            │
│  │ HmsFileParser│ _constants  │                            │
│  └──────────────┴─────────────┘                            │
└─────────────────────────────────────────────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌──────────────────────┐
│  HMS Text Files │    │  HEC-HMS Executable  │
│  (.basin, .met) │    │  (Jython interface)  │
└─────────────────┘    └──────────────────────┘
```

## Core Design Patterns

### 1. Static Class Pattern

**Why:** HMS operations are stateless - they work directly with files, no object state needed.

```python
# Static methods - no instantiation
HmsBasin.get_subbasins("model.basin")  # ✅ Correct

# NOT this:
basin = HmsBasin()  # ❌ Wrong - raises error
basin.get_subbasins("model.basin")
```

**Benefits:**
- Simple, intuitive API
- No state management
- Easy to test
- Clear functional boundaries

### 2. Global Project Object Pattern

**Why:** Most users work with one project at a time.

```python
from hms_commander import init_hms_project, hms

# Initialize global project
init_hms_project(r"C:\path\to\project")

# Use global object
print(hms.basin_df)
print(hms.met_df)

# Multi-project support still available
project1 = HmsPrj()
init_hms_project(r"C:\project1", hms_object=project1)
```

**Benefits:**
- Simple for common use case
- Optional multi-project support
- Backward compatible

### 3. DataFrame Interface Pattern

**Why:** Engineers are familiar with spreadsheet-like data.

```python
# All project data in DataFrames
basins_df = hms.basin_df
mets_df = hms.met_df

# Standard pandas operations
basins_df[basins_df['name'].str.contains('Sub')]
mets_df.sort_values('name')
```

**Benefits:**
- Familiar interface
- Powerful filtering/sorting
- Easy export to Excel/CSV
- Integration with data science tools

### 4. File Parser Pattern

**Why:** HMS files are ASCII text with consistent structure.

```python
# Shared parsing utilities
from hms_commander._parsing import HmsFileParser

# Read with encoding fallback
content = HmsFileParser.read_file("model.basin")

# Parse named blocks
blocks = HmsFileParser.parse_blocks(content, "Subbasin")

# Update parameters
updated = HmsFileParser.update_parameter(content, "Area", "100.0")
```

**Benefits:**
- DRY principle
- Consistent error handling
- Centralized encoding management
- Reusable across all file types

### 5. Clone Workflow Pattern

**Why:** Non-destructive operations critical for QAQC.

```python
# Template → Clone → Modify
HmsBasin.clone_basin("Original", "Modified")
HmsBasin.set_loss_parameters("Modified.basin", "Sub1", curve_number=85)

# Original untouched, modification in clone
```

**Implementation:**
```python
@staticmethod
def clone_basin(template, new_name, description=None, hms_object=None):
    # 1. Use HmsUtils.clone_file() for file copy
    # 2. Update internal references
    # 3. Add metadata (description)
    # 4. Register in project file
    # 5. Update hms_object DataFrames
```

**Benefits:**
- Preserves originals
- Side-by-side comparison
- Rollback capability
- Audit trail

## Module Organization

```
hms_commander/
├── __init__.py           # Package exports
├── HmsPrj.py            # Project management
├── HmsBasin.py          # Basin operations
├── HmsMet.py            # Met operations
├── HmsControl.py        # Control operations
├── HmsGage.py           # Gage operations
├── HmsRun.py            # Run configuration
├── HmsGeo.py            # Geospatial operations
├── HmsCmdr.py           # Execution engine
├── HmsJython.py         # Jython scripting
├── HmsDss.py            # DSS operations
├── HmsResults.py        # Results analysis
├── HmsUtils.py          # Utilities
├── HmsExamples.py       # Example management
├── _parsing.py          # Internal parsing
├── _constants.py        # Constants
├── Decorators.py        # @log_call etc.
└── LoggingConfig.py     # Logging setup
```

### Why No Submodules?

From STYLE_GUIDE.md:

**Use submodules when:**
- 5+ related classes
- Optional dependencies
- Experimental features
- Large utilities (500+ lines)

**Don't use submodules when:**
- Single purpose classes ✅ (HMS Commander case)
- Few functions
- Premature organization

**Decision:** HMS Commander has single-purpose classes that don't meet the threshold for submodule complexity.

## Execution Model

### Jython Script Generation

HMS Commander doesn't execute HEC-HMS directly. Instead:

```python
# 1. Generate Jython script
script = HmsJython.generate_compute_script("project", "Run 1")

# 2. Execute via HEC-HMS
HmsJython.execute_script(script, hms_exe_path)

# 3. HEC-HMS runs Jython in embedded interpreter
```

**Why Jython?**
- Official HEC-HMS automation interface
- Supports HMS 3.x and 4.x
- Version detection automatic

### Version Detection

```python
# Auto-detects HMS version from path
def execute_script(script, hms_exe_path, max_memory=None):
    if "3." in str(hms_exe_path):
        # HMS 3.x: hec-hms.cmd in root
        java_dir = "java/bin"
    else:
        # HMS 4.x: hec-hms.cmd in bin/
        java_dir = "../jre/bin"
```

## Data Flow

### 1. Project Initialization

```
User calls init_hms_project()
    ↓
Scan project folder for .hms file
    ↓
Parse .hms to find all component files
    ↓
Create DataFrames for each component type
    ↓
Store in HmsPrj object (global hms)
```

### 2. File Operations

```
User calls HmsBasin.get_subbasins(path)
    ↓
HmsFileParser.read_file() with encoding fallback
    ↓
HmsFileParser.parse_blocks("Subbasin")
    ↓
Extract parameters to dictionary
    ↓
Convert to pandas DataFrame
    ↓
Return to user
```

### 3. Execution

```
User calls HmsCmdr.compute_run("Run 1")
    ↓
HmsJython.generate_compute_script()
    ↓
Determine HMS version from hms.exe_path
    ↓
Generate Python 2 or 3 compatible script
    ↓
Write temporary script file
    ↓
Execute: hec-hms.cmd -script temp.py
    ↓
Monitor stdout/stderr
    ↓
Clean up temporary file
    ↓
Return success/failure status
```

## Error Handling Strategy

### Encoding Fallback

```python
# Primary: UTF-8
# Fallback: Latin-1 (CP1252)
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()
except UnicodeDecodeError:
    with open(file_path, 'r', encoding='latin-1') as f:
        return f.read()
```

### Logging Decorator

```python
@log_call
def some_function(param1, param2):
    # Automatically logs:
    # - Function name
    # - Parameters
    # - Return value
    # - Execution time
    # - Any exceptions
    pass
```

### Path Validation

```python
# Always use pathlib.Path
basin_path = Path(basin_path).resolve()

# Validate existence
if not basin_path.exists():
    raise FileNotFoundError(f"Basin file not found: {basin_path}")
```

## Testing Strategy

1. **Unit tests** - Test individual methods
2. **Integration tests** - Test workflows
3. **Example projects** - Real HMS models for testing
4. **HMS version matrix** - Test against 3.x and 4.x

## Related Topics

- [Style Guide](style_guide.md) - Coding standards
- [Contributing](contributing.md) - Development workflow
- [LLM Forward Overview](overview.md) - Design philosophy

---

*Architecture prioritizes simplicity, maintainability, and LLM Forward principles.*
