# Run File Format (.run)

## Overview

The `.run` file defines simulation runs that combine basin models, meteorologic models, and control specifications into executable configurations. Each run specifies which models to use and where to store results.

## File Purpose

The run file serves several critical functions:

- **Model Integration**: Connects basin, meteorologic, and control specifications
- **Result Configuration**: Specifies output DSS file location
- **Run Metadata**: Stores run description and modification history
- **Execution Definition**: Provides complete configuration for HEC-HMS compute engine

## Basic Structure

```
Run: RunName
     Basin: BasinModelName
     Meteorology: MetModelName
     Control: ControlSpecName
     DSS File: results.dss
     Description: Optional description
End:
```

## Run Configuration Elements

### Complete Run Definition

```
Run: Baseline_100yr
     Description: Baseline conditions with 100-year storm
     Last Modified Date: 15 December 2024
     Last Modified Time: 09:30
     Basin: ExistingConditions
     Meteorology: 100-Year Atlas14
     Control: 24-Hour Event
     DSS File: results_baseline.dss
End:
```

**Required Fields**:
- **Run**: Unique run name
- **Basin**: Name of basin model (from .basin file)
- **Meteorology**: Name of meteorologic model (from .met file)
- **Control**: Name of control specification (from .control file)
- **DSS File**: Output file for results

**Optional Fields**:
- **Description**: Free-text description
- **Last Modified Date/Time**: Timestamp of last modification

### DSS File Output

The DSS File parameter specifies where simulation results are written:

```
DSS File: output/scenario1_results.dss
```

**Path Options**:
- **Relative path**: `results.dss` (relative to project directory)
- **Subdirectory**: `output/results.dss` (organized by folder)
- **Absolute path**: `C:/Projects/MyProject/results.dss` (full path)

**Best Practice**: Use relative paths for portability.

## Multiple Runs

Projects typically have multiple runs for scenario analysis:

```
Run: Existing_10yr
     Description: Existing conditions, 10-year storm
     Basin: ExistingConditions
     Meteorology: 10-Year Storm
     Control: 24-Hour Event
     DSS File: results_existing_10yr.dss
End:

Run: Existing_100yr
     Description: Existing conditions, 100-year storm
     Basin: ExistingConditions
     Meteorology: 100-Year Storm
     Control: 24-Hour Event
     DSS File: results_existing_100yr.dss
End:

Run: Future_10yr
     Description: Future development, 10-year storm
     Basin: FutureConditions
     Meteorology: 10-Year Storm
     Control: 24-Hour Event
     DSS File: results_future_10yr.dss
End:

Run: Future_100yr
     Description: Future development, 100-year storm
     Basin: FutureConditions
     Meteorology: 100-Year Storm
     Control: 24-Hour Event
     DSS File: results_future_100yr.dss
End:
```

## Scenario Analysis Patterns

### Baseline vs. Alternative Comparison

```
Run: Baseline
     Description: Current conditions baseline
     Basin: Current_Basin
     Meteorology: 100yr_24hr
     Control: Design_Event
     DSS File: baseline.dss
End:

Run: Alternative_A
     Description: Detention pond alternative
     Basin: Alternative_A_Basin
     Meteorology: 100yr_24hr
     Control: Design_Event
     DSS File: alternative_a.dss
End:

Run: Alternative_B
     Description: Channel improvements alternative
     Basin: Alternative_B_Basin
     Meteorology: 100yr_24hr
     Control: Design_Event
     DSS File: alternative_b.dss
End:
```

### Multi-Storm Analysis

```
Run: 2yr_Storm
     Description: 2-year frequency
     Basin: Current
     Meteorology: 2-Year Atlas14
     Control: 24-Hour
     DSS File: storm_2yr.dss
End:

Run: 10yr_Storm
     Description: 10-year frequency
     Basin: Current
     Meteorology: 10-Year Atlas14
     Control: 24-Hour
     DSS File: storm_10yr.dss
End:

Run: 100yr_Storm
     Description: 100-year frequency
     Basin: Current
     Meteorology: 100-Year Atlas14
     Control: 24-Hour
     DSS File: storm_100yr.dss
End:
```

### Calibration Runs

```
Run: Calibration_Event1
     Description: Hurricane Harvey calibration
     Basin: Uncalibrated
     Meteorology: Harvey_Observed
     Control: Harvey_Period
     DSS File: calib_harvey.dss
End:

Run: Calibration_Event2
     Description: Tax Day 2016 calibration
     Basin: Uncalibrated
     Meteorology: TaxDay_Observed
     Control: TaxDay_Period
     DSS File: calib_taxday.dss
End:

Run: Validation_Event
     Description: Memorial Day 2015 validation
     Basin: Calibrated
     Meteorology: Memorial_Observed
     Control: Memorial_Period
     DSS File: valid_memorial.dss
End:
```

## Working with Run Files

### Reading Run Configuration

```python
from hms_commander import HmsRun, init_hms_project, hms

# Initialize project
init_hms_project(r"C:\Projects\MyProject")

# Get all runs as DataFrame
runs_df = hms.run_df
print(runs_df)
#           Run              Basin        Meteorology         Control
# 0  Baseline    ExistingConditions  100-Year Storm    24-Hour Event
# 1  Future      FutureConditions    100-Year Storm    24-Hour Event
```

### Getting DSS Output Configuration

```python
# Get DSS file for specific run
dss_config = HmsRun.get_dss_config("Baseline_100yr")
print(f"DSS File: {dss_config['dss_file']}")
```

### Setting DSS Output File

```python
# Update DSS output location
HmsRun.set_output_dss(
    run_name="Baseline_100yr",
    dss_file="output/baseline_results.dss"
)
```

### Listing All Outputs

```python
# Get all run outputs
outputs = HmsRun.list_all_outputs()
for run, dss_file in outputs.items():
    print(f"{run}: {dss_file}")
```

### Verifying DSS Files Exist

```python
# Check if output DSS files exist
verification = HmsRun.verify_dss_outputs()
for run, exists in verification.items():
    status = "✓" if exists else "✗"
    print(f"{status} {run}")
```

### Cloning Runs

The clone operation is critical for QAQC workflows:

```python
# Clone run for comparison
HmsRun.clone_run(
    source_run="Baseline",
    new_run_name="Baseline_Atlas14",
    new_met="100yr_Atlas14",  # Updated meteorology
    output_dss="baseline_atlas14.dss",
    description="Baseline with updated Atlas 14 precipitation"
)
```

**Clone Benefits**:
- **Non-destructive**: Original run preserved
- **Traceable**: Description documents changes
- **GUI-verifiable**: Both runs appear in HMS for side-by-side comparison
- **QAQC-friendly**: Easy comparison of baseline vs. updated scenarios

## Direct File Operations

For advanced use cases without full project initialization:

### Reading DSS File Directly

```python
# Get DSS file from run file without project initialization
dss_file = HmsRun.get_dss_file_direct(
    run_file_path="MyProject.run",
    run_name="Baseline_100yr"
)
print(f"DSS File: {dss_file}")
```

### Setting DSS File Directly

```python
# Update DSS file without project initialization
HmsRun.set_dss_file_direct(
    run_file_path="MyProject.run",
    run_name="Baseline_100yr",
    dss_file="new_output/results.dss"
)
```

### Listing Runs Directly

```python
# List all runs without project initialization
runs = HmsRun.list_runs_direct("MyProject.run")
print(f"Available runs: {runs}")
```

## DSS Output Organization

### Flat Structure (Simple Projects)

```
MyProject/
├── MyProject.hms
├── MyProject.basin
├── results_10yr.dss
├── results_100yr.dss
└── results_500yr.dss
```

### Organized Structure (Complex Projects)

```
MyProject/
├── MyProject.hms
├── MyProject.basin
├── output/
│   ├── existing/
│   │   ├── existing_10yr.dss
│   │   ├── existing_100yr.dss
│   │   └── existing_500yr.dss
│   ├── future/
│   │   ├── future_10yr.dss
│   │   ├── future_100yr.dss
│   │   └── future_500yr.dss
│   └── alternatives/
│       ├── alt_a.dss
│       └── alt_b.dss
```

## Execution

### Computing Single Run

```python
from hms_commander import HmsCmdr, init_hms_project

# Initialize project
init_hms_project(r"C:\Projects\MyProject")

# Compute single run
success = HmsCmdr.compute_run("Baseline_100yr")
if success:
    print("Simulation completed successfully")
```

### Computing Multiple Runs (Sequential)

```python
# Compute runs in sequence
runs = ["Existing_10yr", "Existing_100yr", "Future_10yr", "Future_100yr"]
results = HmsCmdr.compute_batch(runs)

for run, success in results.items():
    print(f"{run}: {'✓' if success else '✗'}")
```

### Computing Multiple Runs (Parallel)

```python
# Compute runs in parallel (faster for independent runs)
runs = ["Baseline_10yr", "Baseline_100yr", "Baseline_500yr"]
results = HmsCmdr.compute_parallel(runs, max_workers=3)
```

## Run Naming Conventions

### Descriptive Pattern

Format: `{Scenario}_{Storm}_{Duration}`

Examples:
- `Existing_100yr_24hr`
- `Future_10yr_6hr`
- `Alternative_A_100yr_24hr`

### Systematic Pattern

Format: `{ID}_{Condition}_{Frequency}`

Examples:
- `R01_Existing_100yr`
- `R02_Future_100yr`
- `R03_Alternative_A_100yr`

## Complete Example

```
Run: Existing_100yr_Atlas14
     Description: Existing conditions, 100-year 24-hour Atlas 14 storm
     Last Modified Date: 11 December 2024
     Last Modified Time: 14:30
     Basin: Existing_Conditions_2024
     Meteorology: Atlas14_100yr_24hr_TypeIII
     Control: 24Hour_15min_Interval
     DSS File: output/existing/existing_100yr_atlas14.dss
End:

Run: Future_100yr_Atlas14
     Description: Future development (2040), 100-year 24-hour Atlas 14
     Last Modified Date: 11 December 2024
     Last Modified Time: 15:45
     Basin: Future_Buildout_2040
     Meteorology: Atlas14_100yr_24hr_TypeIII
     Control: 24Hour_15min_Interval
     DSS File: output/future/future_100yr_atlas14.dss
End:

Run: Alternative_Detention_100yr
     Description: Regional detention alternative, 100-year Atlas 14
     Last Modified Date: 12 December 2024
     Last Modified Time: 10:00
     Basin: Alternative_With_Detention
     Meteorology: Atlas14_100yr_24hr_TypeIII
     Control: 24Hour_15min_Interval
     DSS File: output/alternatives/detention_100yr_atlas14.dss
End:
```

## Best Practices

1. **Descriptive naming**: Use clear, systematic run names
2. **Separate DSS files**: Each run should have its own DSS output file
3. **Organize outputs**: Use subdirectories for complex projects
4. **Document scenarios**: Use description field to explain run purpose
5. **Version control**: Track run file changes in Git
6. **Clone for QAQC**: Use `clone_run()` for systematic comparisons

## Common Pitfalls

- **Same DSS file**: Multiple runs writing to same DSS file can cause conflicts
- **Missing models**: Referenced basin/met/control must exist in respective files
- **DSS path errors**: Ensure output directory exists before running
- **Name conflicts**: Run names must be unique within project
- **Absolute paths**: Avoid absolute paths for portability

## Validation

Validate run configuration:

```python
from hms_commander import init_hms_project, hms

# Initialize project
init_hms_project(r"C:\Projects\MyProject")

# Check if all referenced models exist
runs_df = hms.run_df
basins = set(hms.basin_df.index)
mets = set(hms.met_df.index)
controls = set(hms.control_df.index)

for idx, row in runs_df.iterrows():
    if row['Basin'] not in basins:
        print(f"Warning: Basin '{row['Basin']}' not found for run '{idx}'")
    if row['Meteorology'] not in mets:
        print(f"Warning: Met '{row['Meteorology']}' not found for run '{idx}'")
    if row['Control'] not in controls:
        print(f"Warning: Control '{row['Control']}' not found for run '{idx}'")
```

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Project File Format](project_file.md) - Project configuration
- [Basin File Format](basin_file.md) - Basin model structure
- [Met File Format](met_file.md) - Meteorologic model
- [Control File Format](control_file.md) - Control specifications
- [DSS Integration](dss_integration.md) - Working with results

## API Reference

**Primary Class**: `HmsRun`

**Key Methods**:
- `HmsRun.get_dss_config()` - Get DSS configuration for run
- `HmsRun.set_output_dss()` - Set DSS output file
- `HmsRun.list_all_outputs()` - List all run outputs
- `HmsRun.get_run_names()` - Get list of run names
- `HmsRun.verify_dss_outputs()` - Check if DSS files exist
- `HmsRun.clone_run()` - Clone run configuration

**Direct Operations** (no project initialization):
- `HmsRun.get_dss_file_direct()` - Get DSS file from .run file
- `HmsRun.set_dss_file_direct()` - Set DSS file in .run file
- `HmsRun.list_runs_direct()` - List runs from .run file

**Execution Class**: `HmsCmdr`
- `HmsCmdr.compute_run()` - Execute single run
- `HmsCmdr.compute_batch()` - Execute multiple runs sequentially
- `HmsCmdr.compute_parallel()` - Execute multiple runs in parallel

See [CLAUDE.md](../../CLAUDE.md) for complete API documentation.
