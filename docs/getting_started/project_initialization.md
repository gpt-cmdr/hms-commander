# Project Initialization

How to initialize HEC-HMS projects with HMS Commander.

## Overview

Before using HMS Commander's functionality, you must initialize a project. This scans the project folder and creates DataFrames for all HMS components.

## Quick Start

```python
from hms_commander import init_hms_project, hms

# Initialize project
init_hms_project(r"C:\path\to\hms\project")

# Access project data
print(hms.basin_df)      # Basin models
print(hms.met_df)        # Meteorologic models
print(hms.control_df)    # Control specifications
print(hms.run_df)        # Simulation runs
print(hms.gage_df)       # Time-series gages
```

## Project Structure Requirements

HMS Commander expects a standard HEC-HMS project structure:

```
ProjectFolder/
├── ProjectName.hms          ← Project file (required)
├── ProjectName.basin        ← Basin models
├── ProjectName.met          ← Meteorologic models
├── ProjectName.control      ← Control specs
├── ProjectName.gage         ← Time-series gages
├── ProjectName.run          ← Simulation runs
├── ProjectName.geo          ← Geospatial data
├── ProjectName.map          ← Map data
└── results.dss             ← Results (created by HMS)
```

**Required:**
- `.hms` project file

**Optional:**
- All other files (created as needed)

## Initialization Methods

### Method 1: Global Project (Recommended)

For most users working with one project:

```python
from hms_commander import init_hms_project, hms

# Initialize global hms object
init_hms_project(r"C:\Projects\Watershed")

# Use global hms throughout session
print(hms.project_name)
print(hms.basin_df)
```

**Benefits:**
- Simple, intuitive
- No need to pass project object
- Most common use case

### Method 2: Multiple Projects

For advanced users managing multiple projects:

```python
from hms_commander import init_hms_project, HmsPrj

# Create separate project objects
project1 = HmsPrj()
project2 = HmsPrj()

# Initialize each
init_hms_project(r"C:\Projects\Watershed1", hms_object=project1)
init_hms_project(r"C:\Projects\Watershed2", hms_object=project2)

# Specify project in function calls
from hms_commander import HmsBasin
HmsBasin.get_subbasins("model.basin", hms_object=project1)
```

**When to use:**
- Comparing multiple projects
- Batch processing many projects
- Side-by-side analysis

## Specifying HEC-HMS Executable

### Auto-Detection (Recommended)

```python
# HMS Commander finds HMS installation automatically
init_hms_project(r"C:\Projects\Watershed")
```

Searches common locations:
- `C:\Program Files\HEC\HEC-HMS\4.13`
- `C:\Program Files (x86)\HEC\HEC-HMS\3.5`
- Custom installation paths

### Manual Path

```python
# Specify HMS installation
init_hms_project(
    project_path=r"C:\Projects\Watershed",
    hms_exe_path=r"C:\Program Files\HEC\HEC-HMS\4.13"
)
```

**When to specify:**
- Multiple HMS versions installed
- Non-standard installation location
- Explicit version control

## What Happens During Initialization

```python
init_hms_project(project_path)
```

**Steps:**

1. **Validate Path**
   - Check folder exists
   - Find `.hms` project file

2. **Parse Project File**
   - Extract project name
   - Find component file paths
   - Determine HMS version

3. **Create DataFrames**
   - Scan for basin models → `basin_df`
   - Scan for met models → `met_df`
   - Scan for control specs → `control_df`
   - Scan for runs → `run_df`
   - Scan for gages → `gage_df`

4. **Locate Executable**
   - Auto-detect or use provided path
   - Verify HEC-HMS installation

5. **Store in Project Object**
   - Global `hms` or provided object
   - Ready for operations

## Accessing Project Data

After initialization:

### Project Information

```python
print(hms.project_name)      # "Watershed"
print(hms.project_folder)    # Path to folder
print(hms.hms_file)          # Path to .hms file
print(hms.exe_path)          # Path to HEC-HMS
print(hms.version)           # HMS version
```

### Component DataFrames

```python
# Basin models
print(hms.basin_df)
#   name           path
# 0 Basin1        .../Basin1.basin
# 1 Basin2        .../Basin2.basin

# Meteorologic models
print(hms.met_df)
#   name           path
# 0 Met1          .../Met1.met
# 1 Met2          .../Met2.met

# Simulation runs
print(hms.run_df)
#   name    basin  met     control  dss_file
# 0 Run1    Basin1 Met1    Control1 results.dss
```

## Validation

Validate project structure:

```python
from hms_commander import HmsUtils

# Check project files
validation = HmsUtils.validate_project(r"C:\Projects\Watershed")

print(validation)
# {
#   'valid': True,
#   'hms_file': 'Found',
#   'basin_files': 2,
#   'met_files': 1,
#   'warnings': []
# }
```

## Common Issues

### Issue: Project file not found

```python
FileNotFoundError: No .hms file found in C:\Projects\Watershed
```

**Solution:** Ensure folder contains `.hms` project file

### Issue: HMS executable not found

```python
Warning: HEC-HMS executable not found. Execution features disabled.
```

**Solution:** Specify path manually:
```python
init_hms_project(
    r"C:\Projects\Watershed",
    hms_exe_path=r"C:\Program Files\HEC\HEC-HMS\4.13"
)
```

### Issue: Multiple .hms files

```python
ValueError: Multiple .hms files found. Please specify which to use.
```

**Solution:** Move extra .hms files or specify exact file

## Best Practices

1. **Initialize once per session**
   ```python
   # At top of script/notebook
   init_hms_project(r"C:\Projects\Watershed")

   # Use throughout script
   HmsBasin.get_subbasins(...)
   HmsCmdr.compute_run(...)
   ```

2. **Use absolute paths**
   ```python
   # ✅ Good
   init_hms_project(r"C:\Projects\Watershed")

   # ❌ Avoid
   init_hms_project("../Watershed")  # Relative path
   ```

3. **Verify initialization**
   ```python
   init_hms_project(project_path)

   # Check loaded correctly
   print(f"Project: {hms.project_name}")
   print(f"Basins: {len(hms.basin_df)}")
   print(f"Mets: {len(hms.met_df)}")
   ```

## Next Steps

After initialization:

1. [Quick Start Guide](quick_start.md) - Basic workflow
2. [Basin Models](../user_guide/basin_models.md) - Working with basins
3. [Execution](../user_guide/execution.md) - Running simulations
4. [Results Analysis](../user_guide/results_analysis.md) - Analyzing results

## Related Topics

- [API Reference: HmsPrj](../api/hms_prj.md) - Project class documentation
- [Project Management](../user_guide/project_management.md) - Advanced project operations
- [Data Formats: Project File](../data_formats/project_file.md) - .hms file format

---

*For complete API documentation, see [HmsPrj API Reference](../api/hms_prj.md)*
