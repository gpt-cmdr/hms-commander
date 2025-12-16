# Run Configuration

Setting up HEC-HMS simulation runs with basin, meteorologic, and control combinations.

## Overview

The `HmsRun` class manages simulation run configurations, including basin/met/control assignments and DSS output file settings.

## Quick Examples

### Get DSS Output Configuration

```python
from hms_commander import HmsRun

# Check DSS output for a run
dss_config = HmsRun.get_dss_config("Run 1")
print(dss_config)
```

### Set Output DSS File

```python
# Configure DSS output location
HmsRun.set_output_dss(
    run_name="Run 1",
    dss_file="results.dss"
)
```

### Clone Run for QAQC

```python
# Create comparison run with updated met model
HmsRun.clone_run(
    source_run="Baseline_Run",
    new_run_name="Atlas14_Run",
    new_met="Atlas14_Met",
    output_dss="atlas14_results.dss",
    description="Updated with Atlas 14 precipitation"
)
```

## Key Operations

- **DSS configuration** - `get_dss_config()`, `set_output_dss()`
- **List runs** - `get_run_names()`, `list_all_outputs()`
- **Verify outputs** - `verify_dss_outputs()`
- **Clone workflow** - `clone_run()` for side-by-side comparison

## Clone Workflow for QAQC

The clone operation is critical for the LLM Forward approach:

```python
# Non-destructive comparison workflow
HmsRun.clone_run(
    source_run="Existing_Model",
    new_run_name="Calibrated_Model",
    new_basin="Calibrated_Basin",  # Updated parameters
    output_dss="calibrated.dss"    # Separate output
)

# Both runs now visible in HEC-HMS GUI for comparison
```

**Benefits:**
- ✅ Preserves original run
- ✅ Separate DSS output files
- ✅ Side-by-side GUI comparison
- ✅ Traceable modifications

## Direct File Operations

For advanced use cases without project initialization:

```python
# Work directly with .run files
HmsRun.set_dss_file_direct(
    run_file_path="project.run",
    run_name="Run 1",
    dss_file="output.dss"
)
```

## Related Topics

- [API Reference: HmsRun](../api/hms_run.md) - Complete method documentation
- [Clone Workflows](clone_workflows.md) - Non-destructive QAQC patterns
- [Execution](execution.md) - Running simulations
- [Results Analysis](results_analysis.md) - Processing DSS results

---

*For complete API documentation, see [HmsRun API Reference](../api/hms_run.md)*
