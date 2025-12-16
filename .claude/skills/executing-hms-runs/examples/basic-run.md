# Basic HMS Run Execution - Complete Example

## Scenario

Execute a single HMS simulation from start to finish.

## Prerequisites

- HMS project folder with .hms, .basin, .met, .control files
- HMS installed (3.x or 4.x)
- hms-commander installed

## Complete Workflow

```python
from hms_commander import init_hms_project, HmsCmdr, HmsResults
from pathlib import Path

# 1. Initialize project
project_path = Path(r"C:\Projects\watershed")
init_hms_project(project_path)

# 2. Verify project loaded correctly
from hms_commander import hms
print(f"Basin models: {len(hms.basin_df)}")
print(f"Runs: {len(hms.run_df)}")

# 3. Execute run
print("Executing simulation...")
success = HmsCmdr.compute_run("Run 1")

# 4. Check results
if success:
    print("Simulation completed successfully!")

    # Get DSS file path
    dss_file = hms.run_df.loc["Run 1", "dss_file"]
    print(f"Results written to: {dss_file}")

    # Extract peak flows
    peaks = HmsResults.get_peak_flows(dss_file)
    print(f"\nPeak Flows:\n{peaks}")
else:
    print("Simulation failed!")
    # Check log file
    log_file = project_path / "RUN_Run 1.log"
    if log_file.exists():
        print(f"\nError log:\n{log_file.read_text()}")
```

## Expected Output

```
Executing simulation...
INFO: HmsCmdr.compute_run called with run_name='Run 1'
INFO: Generating Jython script...
INFO: Executing HMS simulation...
Simulation completed successfully!
Results written to: C:\Projects\watershed\results\watershed.dss

Peak Flows:
          Element  Peak Flow (cfs)  Time to Peak
0      Subbasin1           542.3    01Jan2020 12:00
1      Subbasin2           324.1    01Jan2020 12:15
2         Outlet           866.4    01Jan2020 13:00
```

## Troubleshooting

**Issue**: "HMS executable not found"
```python
# Specify HMS path explicitly
from hms_commander import HmsJython
hms_exe = HmsJython.find_hms_executable()
print(f"Found HMS at: {hms_exe}")

# Or set manually
init_hms_project(project_path, hms_exe_path=r"C:\Program Files\HEC\HEC-HMS\4.11")
```

**Issue**: Simulation times out
```python
# Extend timeout to 2 hours
HmsCmdr.compute_run("Run 1", timeout=7200)
```

## Next Steps

- **Extract results**: See `extracting-dss-results` skill
- **Batch execution**: See `batch-runs.md`
- **Parallel execution**: See `parallel-runs.md`
