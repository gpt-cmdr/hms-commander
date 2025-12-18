# HMS Run Workflow

You are helping the user execute an HEC-HMS simulation run.

## Required Information

Before executing, gather:
1. **Project Path**: Full path to HMS project directory
2. **Run Name**: Name of the Run to execute (from project)
3. **Output Directory** (optional): Where to write outputs (defaults to project dir)

## Pre-Flight Checks

Before running, verify:

```python
from hms_commander import init_hms_project, hms, HmsUtils

# 1. Initialize project
init_hms_project(project_path)

# 2. List available runs
print(hms.run_df)  # Shows all configured runs

# 3. Validate project (optional but recommended)
validation = HmsUtils.validate_project(project_path)
print(validation)
```

## Execution Methods

### Method 1: Simple Execution (Most Common)

```python
from hms_commander import init_hms_project, HmsCmdr

init_hms_project(r"C:\Projects\watershed")

# Execute single run
result = HmsCmdr.compute_run("Run 1")
print(f"Status: {result['status']}")
print(f"DSS Output: {result['dss_file']}")
```

### Method 2: Batch Execution

```python
# Execute multiple runs
results = HmsCmdr.compute_batch(["Run 1", "Run 2", "Run 3"])

for run_name, result in results.items():
    print(f"{run_name}: {result['status']}")
```

### Method 3: Parallel Execution

```python
# Execute runs in parallel (for independent scenarios)
results = HmsCmdr.compute_parallel(
    ["Run 1", "Run 2", "Run 3"],
    max_workers=3
)
```

### Method 4: Direct Jython Script

```python
from hms_commander import HmsJython

# Generate Jython script (for custom workflows)
script = HmsJython.generate_script(
    project_path,
    run_name="Run 1",
    save_script=True
)

# Execute script
HmsJython.execute_script(script_path, project_path)
```

## Post-Execution

After successful execution:

```python
from hms_commander import HmsResults, HmsDss

# Get DSS output path
dss_file = result['dss_file']

# Extract results
flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
peaks = HmsResults.get_peak_flows(dss_file)

# Quick plot (see /hms-plot-dss for more)
flows.plot()
```

## Troubleshooting

**Run fails to start:**
- Check HMS installation path is correct
- Verify HMS version is installed (auto-detected)
- Check .hms file references correct basin/met/control

**Run completes with errors:**
- Check DSS file for partial results
- Look at HMS log file in project directory
- Validate met model has data for control spec time window

**DSS file not found:**
- Confirm run completed successfully
- Check output path configuration
- Look in project directory for .dss files

## Version Considerations

**HMS 3.x (32-bit):**
```python
HmsCmdr.compute_run("Run 1", python2_compatible=True)
```

**HMS 4.x (64-bit):**
```python
HmsCmdr.compute_run("Run 1")  # Default
```

## Your Response

1. Ask the user for project path if not provided
2. List available runs from the project
3. Confirm which run(s) to execute
4. Execute and report results
5. Offer to extract/plot results (suggest `/hms-plot-dss`)

**Primary Sources:**
- Code: `hms_commander/HmsCmdr.py`
- Skill: `.claude/skills/executing-hms-runs/`
- Examples: `examples/05_jython_execution.ipynb`
