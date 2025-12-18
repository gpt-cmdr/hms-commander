# Task 020: Execute HMS Simulation Workflow

**Created**: 2025-12-17
**Template**: feature.md
**Status**: Reusable

---

## Goal

Run a complete HMS simulation workflow: initialize project, execute run, extract results.

**Uses**: HmsExamples for reproducibility

---

## Prerequisites

- hms-commander installed (editable or standard)
- HMS 4.x installed (required for execution)

---

## Steps

### 1. Extract Example Project

```python
from hms_commander import HmsExamples

# List available projects
HmsExamples.list_available()

# Extract project
HmsExamples.extract_project("tifton")
```

**Output location**: `hms_example_projects/tifton/`

### 2. Initialize Project

```python
from hms_commander import init_hms_project

# Initialize and load dataframes
hms = init_hms_project("hms_example_projects/tifton")

# Inspect configuration
print(f"Basin elements: {len(hms.basin_df)}")
print(f"Met models: {len(hms.met_df)}")
print(f"Runs: {len(hms.run_df)}")

# View run details
print(hms.run_df[["basin", "met", "control", "dss_file"]])
```

### 3. Execute Simulation

```python
from hms_commander import HmsCmdr

# Execute run
HmsCmdr.compute_run("Run 1")

# Or execute all runs
HmsCmdr.compute_all_runs()
```

**Note**: Requires HMS installed and accessible via PATH or `hms_commander._utils.HmsUtils.detect_hms_installation()`

### 4. Verify Execution

```python
from pathlib import Path

# Check DSS file created
dss_file = hms.run_df.loc["Run 1", "dss_file"]
dss_path = Path(dss_file)

assert dss_path.exists(), f"DSS file not found: {dss_file}"
print(f"✓ DSS file created: {dss_path}")
print(f"  Size: {dss_path.stat().st_size / 1024:.1f} KB")
```

### 5. Extract Results

```python
from hms_commander import HmsResults

# Extract peak flows
peaks = HmsResults.get_peak_flows(dss_file)
print(peaks)

# Extract hydrograph for specific element
flows = HmsResults.get_outflow_timeseries(dss_file, "Junction1")
print(f"Peak flow: {flows['Flow'].max():.1f} cfs")
print(f"Time to peak: {flows['Flow'].idxmax()}")
```

---

## Acceptance Criteria

- [x] Project extracted successfully
- [x] Project initialized, dataframes loaded
- [x] Simulation executed without errors
- [x] DSS file created
- [x] Results extracted and validated

---

## Troubleshooting

### "HMS not found" error

**Solution**: Verify HMS installation path

```python
from hms_commander import HmsUtils

hms_path = HmsUtils.detect_hms_installation()
print(f"HMS found: {hms_path}")
```

If not found, specify manually:
```python
HmsCmdr.compute_run("Run 1", hms_cmd=r"C:\Program Files\HEC\HEC-HMS\4.11\hec-hms.cmd")
```

### "DSS file not found" error

**Check**:
1. Did simulation complete without errors?
2. Is DSS path in run configuration correct?

```python
# Check run configuration
print(hms.run_df.loc["Run 1"])
```

### "RasDss import error"

**Solution**: Install DSS dependencies
```bash
pip install hms-commander[dss]
# or
pip install ras-commander
```

---

## Advanced Usage

### Parallel Execution

```python
HmsCmdr.compute_runs_parallel(
    run_names=["Run 1", "Run 2", "Run 3"],
    max_workers=3
)
```

### Version-Specific Execution

```python
# Generate Jython script with Python 2 compatibility
HmsJython.generate_compute_script(
    project_path="hms_example_projects/tifton/tifton.hms",
    run_name="Run 1",
    python2_compatible=True  # For HMS 3.x
)
```

---

## Related Tasks

- **040-atlas14-update.md**: Update precipitation before running
- **050-version-upgrade.md**: Upgrade HMS 3.x project to 4.x before running
- **070-dss-extraction.md**: Advanced DSS results extraction

---

## Related Skills

**Skills activated**:
- `executing-hms-runs` - Full execution workflow guidance
- `extracting-dss-results` - DSS operations patterns

**Subagents**:
- `run-manager-specialist` - Run configuration and execution
- `dss-integration-specialist` - Results extraction
