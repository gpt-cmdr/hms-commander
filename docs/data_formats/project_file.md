# Project File Format (.hms)

## Overview

The `.hms` file is the root configuration file for an HEC-HMS project. It serves as a registry that references all other project files and defines project-level settings. This file is created automatically when you create a new project in the HEC-HMS GUI and must be present for the project to open.

## File Purpose

The project file serves several critical functions:

- **File Registry**: Lists all basin models, meteorologic models, control specifications, and simulation runs
- **Version Tracking**: Records the HMS version used to create/modify the project
- **Project Metadata**: Stores project name and basic configuration
- **File Paths**: References related files (.basin, .met, .control, .gage, .run)

## Basic Structure

```
Project: ProjectName
Version: 4.9
BasinFile: ProjectName.basin
MetFile: ProjectName.met
ControlFile: ProjectName.control
GageFile: ProjectName.gage
```

### Required Elements

- **Project**: Project name (must match)
- **Version**: HMS version number (e.g., "4.9", "4.13", "3.5")
- **BasinFile**: Path to basin model file (typically same as project name)
- **MetFile**: Path to meteorologic model file
- **ControlFile**: Path to control specifications file
- **GageFile**: Path to gage data file

## Complete Example

```
Project: MyWatershed
Version: 4.13
Description: Watershed hydrologic model for flood analysis
BasinFile: MyWatershed.basin
MetFile: MyWatershed.met
ControlFile: MyWatershed.control
GageFile: MyWatershed.gage
RunFile: MyWatershed.run

Basin Model: Existing Conditions
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
End:

Basin Model: Proposed Conditions
     Last Modified Date: 20 November 2024
     Last Modified Time: 09:15
     Description: Updated with new development
End:

Meteorologic Model: 100-Year Storm
     Last Modified Date: 10 November 2024
     Last Modified Time: 11:00
End:

Control Specifications: 24-Hour
     Last Modified Date: 05 November 2024
     Last Modified Time: 08:45
End:

Simulation Run: Baseline
     Basin Model: Existing Conditions
     Meteorologic Model: 100-Year Storm
     Control Specifications: 24-Hour
End:
```

## File Components

### Project Header

The header section defines basic project information:

```
Project: ProjectName
Version: 4.13
Description: Optional project description
```

- **Project**: Name must match directory name (best practice)
- **Version**: HMS version (affects file format compatibility)
- **Description**: Optional free-text description

### File References

File references point to associated model files:

```
BasinFile: MyWatershed.basin
MetFile: MyWatershed.met
ControlFile: MyWatershed.control
GageFile: MyWatershed.gage
RunFile: MyWatershed.run
```

These paths are typically relative to the project directory. Absolute paths are possible but not recommended.

### Component Registry

The project file maintains a registry of all models and configurations:

#### Basin Models

```
Basin Model: ModelName
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
     Description: Optional description
End:
```

Each basin model defined in the `.basin` file is registered here.

#### Meteorologic Models

```
Meteorologic Model: ModelName
     Last Modified Date: 10 November 2024
     Last Modified Time: 11:00
     Description: Optional description
End:
```

Each meteorologic model from the `.met` file is listed.

#### Control Specifications

```
Control Specifications: ControlName
     Last Modified Date: 05 November 2024
     Last Modified Time: 08:45
     Description: Optional description
End:
```

Each control specification from the `.control` file is registered.

#### Simulation Runs

```
Simulation Run: RunName
     Basin Model: ExistingConditions
     Meteorologic Model: 100-Year
     Control Specifications: 24-Hour
     Description: Optional run description
End:
```

Each simulation run connects a basin model, meteorologic model, and control specification.

## Working with Project Files

### Reading Project Information

Use the `HmsPrj` class to work with project files:

```python
from hms_commander import init_hms_project, hms

# Initialize project
init_hms_project(r"C:\Projects\MyWatershed")

# Access project data
print(f"Project: {hms.project_name}")
print(f"Basin models: {hms.basin_df}")
print(f"Met models: {hms.met_df}")
print(f"Runs: {hms.run_df}")
```

### Project Data Access

After initialization, the project data is available as DataFrames:

- `hms.basin_df` - All basin models
- `hms.met_df` - All meteorologic models
- `hms.control_df` - All control specifications
- `hms.run_df` - All simulation runs
- `hms.gage_df` - All gages

### Updating Project Registry

When cloning models or creating new components, the project file must be updated:

```python
from hms_commander import HmsBasin, HmsUtils

# Clone a basin model
HmsBasin.clone_basin(
    template="existing.basin",
    new_name="proposed.basin",
    description="New development scenario"
)

# The project file is automatically updated to register the new basin
```

The `HmsUtils.update_project_file()` method handles registry updates:

```python
from hms_commander import HmsUtils

# Manually update project registry
HmsUtils.update_project_file(
    hms_file="MyWatershed.hms",
    entry_type="Basin Model",
    entry_name="Proposed Conditions"
)
```

## Version Compatibility

### HMS 4.x Projects

Modern HMS 4.x projects (4.4.1+) use this format:

```
Project: ProjectName
Version: 4.13
BasinFile: ProjectName.basin
MetFile: ProjectName.met
ControlFile: ProjectName.control
GageFile: ProjectName.gage
```

### HMS 3.x Projects

Legacy HMS 3.x projects have a similar format but may use older version numbers:

```
Project: ProjectName
Version: 3.5
BasinFile: ProjectName.basin
MetFile: ProjectName.met
ControlFile: ProjectName.control
GageFile: ProjectName.gage
```

Version differences:
- HMS 3.x uses 32-bit architecture
- HMS 4.x uses 64-bit architecture
- File format is largely compatible between versions

## Common Patterns

### Multi-Scenario Projects

Complex projects often have multiple basin models and meteorologic conditions:

```
Project: UrbanWatershed
Version: 4.13

Basin Model: Existing Conditions
End:

Basin Model: 5-Year Development
End:

Basin Model: 10-Year Development
End:

Meteorologic Model: 10-Year Storm
End:

Meteorologic Model: 100-Year Storm
End:

Control Specifications: 24-Hour Event
End:

Simulation Run: Existing_100yr
     Basin Model: Existing Conditions
     Meteorologic Model: 100-Year Storm
     Control Specifications: 24-Hour Event
End:

Simulation Run: Future_100yr
     Basin Model: 10-Year Development
     Meteorologic Model: 100-Year Storm
     Control Specifications: 24-Hour Event
End:
```

This structure enables systematic comparison of different scenarios.

## Best Practices

1. **Keep project name consistent**: Project name should match directory name
2. **Use relative file paths**: Avoid absolute paths for portability
3. **Document modifications**: Use description fields to track changes
4. **Version appropriately**: Update version number when sharing across HMS versions
5. **Don't edit manually**: Use HMS GUI or hms-commander APIs to modify

## Project Validation

Validate project file integrity:

```python
from hms_commander import HmsUtils

# Validate project structure
validation = HmsUtils.validate_project(r"C:\Projects\MyWatershed")

if validation['valid']:
    print("Project structure is valid")
else:
    print(f"Validation errors: {validation['errors']}")
```

## File Location

The `.hms` file must be located in the project root directory:

```
MyWatershed/
├── MyWatershed.hms          ← Project file (required)
├── MyWatershed.basin        ← Basin model file
├── MyWatershed.met          ← Meteorologic model file
├── MyWatershed.control      ← Control specifications
├── MyWatershed.gage         ← Gage data
└── MyWatershed.run          ← Run configurations
```

## Related Documentation

- [Basin File Format](basin_file.md) - Basin model structure
- [Met File Format](met_file.md) - Meteorologic model structure
- [Control File Format](control_file.md) - Control specifications
- [Run File Format](run_file.md) - Simulation run configuration

## API Reference

**Primary Class**: `HmsPrj`

**Initialization**:
```python
from hms_commander import init_hms_project, HmsPrj, hms

# Single project
init_hms_project(r"C:\Projects\MyWatershed")

# Multiple projects
project1 = HmsPrj()
init_hms_project(r"C:\Projects\Project1", hms_object=project1)
```

**Utility Functions**:
- `HmsUtils.validate_project()` - Validate project structure
- `HmsUtils.update_project_file()` - Update project registry
- `HmsUtils.copy_project()` - Copy entire project
