# HMS Version Upgrade Agent: 3.x to 4.x

This agent workflow guides the upgrade of HEC-HMS projects from version 3.x to version 4.x, including validation of computational results.

## Overview

When upgrading HMS projects from 3.x to 4.x, there are several important considerations:
- Project files are automatically upgraded when opened in HMS 4.x
- Computational results may differ slightly due to algorithm improvements
- New output types are available in HMS 4.x
- Some output types from 3.x are removed or renamed

## Prerequisites

- HMS 3.x installation (e.g., `C:\Program Files (x86)\HEC\HEC-HMS\3.3`)
- HMS 4.x installation (e.g., `C:\Program Files\HEC\HEC-HMS\4.11`)
- hms-commander library with DSS support
- Original HMS 3.x project files

## Workflow Steps

### Step 1: Backup Original Project

```bash
# Create a backup copy for upgrade testing
cp -r "/path/to/original_project" "/path/to/original_project_upgrade_4x"
```

### Step 2: Run Original Project in HMS 3.x

```python
from hms_commander import HmsJython, HmsOutput
from pathlib import Path

# Generate Python 2 compatible script for HMS 3.x
script = HmsJython.generate_compute_script(
    project_path="/path/to/original_project",
    run_name="Run 1",
    python2_compatible=True  # Required for HMS 3.x
)

# Execute in HMS 3.x
success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path=Path("C:/Program Files (x86)/HEC/HEC-HMS/3.3"),
    working_dir="/path/to/original_project"
)

# Parse and verify results
result = HmsOutput.parse_compute_output(stdout, stderr)
print(HmsOutput.format_summary(result))
```

### Step 3: Open Project in HMS 4.x (Auto-Upgrade)

**CRITICAL:** The project name in the script MUST match the `Project:` line in the .hms file, NOT the folder name.

```python
from hms_commander import HmsOutput

# Get the actual project name from the .hms file
project_name = HmsOutput.get_project_name_from_hms("/path/to/project_upgrade_4x/project.hms")

# Generate script with correct project name
script = HmsJython.generate_compute_script(
    project_path="/path/to/project_upgrade_4x",
    run_name="Run 1",
    python2_compatible=False,  # Use Python 3 syntax for HMS 4.x
    project_name=project_name  # Use actual project name from .hms file
)

# Execute in HMS 4.x
success, stdout, stderr = HmsJython.execute_script(
    script_content=script,
    hms_exe_path=Path("C:/Program Files/HEC/HEC-HMS/4.11"),
    working_dir="/path/to/project_upgrade_4x"
)
```

### Step 4: Verify Upgrade Messages

Check the log files for upgrade confirmation:

```python
# Parse project log for upgrade messages
result = HmsOutput.parse_project_log("/path/to/project_upgrade_4x")

# Check if version upgrade occurred
upgraded, from_ver, to_ver = HmsOutput.check_version_upgrade(result.stdout)
if upgraded:
    print(f"Project upgraded from {from_ver} to {to_ver}")
```

Expected messages:
- `WARNING 10020: Begin updating "project" from Version 3.3 to Version 4.11`
- `WARNING 10021: Project "project" was updated from Version 3.3 to Version 4.11`

### Step 5: Compare DSS Outputs

```python
from hms_commander import HmsDss
from pathlib import Path

# Run the comparison script
exec(open("agents/Update_3_to_4/compare_dss_outputs.py").read())

# Or use directly:
results = compare_hms_dss_outputs(
    dss_33_path="/path/to/original/results.dss",
    dss_411_path="/path/to/upgraded/results.dss"
)
```

## Expected Differences

### Computational Differences

Based on testing with the Tifton sample project:

| Metric | Typical Difference |
|--------|-------------------|
| Peak Flow | < 0.5% |
| Total Volume | < 0.1% |
| Peak Timing | Usually identical |
| Individual Values | Up to 4% mean difference |

These differences are due to:
1. Numerical solver improvements
2. Algorithm refinements (especially in SMA loss method)
3. Enhanced precision in newer versions

### Output Structure Changes

**Removed in HMS 4.x:**
- ET-SOIL
- PRECIP-CUM
- PRECIP-INC

**Added in HMS 4.x:**
- AQUIFER RECHARGE
- FLOW-BASE-1 (GW Layer 1 baseflow)
- FLOW-BASE-2 (GW Layer 2 baseflow)
- FLOW-CUMULATIVE
- FLOW-OBSERVED-CUMULATIVE
- FLOW-UNIT GRAPH
- PRECIP-LOSS-CUM

### File Format Changes

- HMS 3.x: DSS-6 format
- HMS 4.x: DSS-7 format
- Both formats can be read by HmsDss

## Common Issues

### Issue 1: NullPointerException on Compute

**Symptom:**
```
ERROR 10000: Unknown exception or error; restart HEC-HMS to continue working.
java.lang.NullPointerException
```

**Cause:** Project name passed to `OpenProject()` doesn't match the `Project:` line in .hms file.

**Solution:** Always read the .hms file to get the actual project name:
```python
project_name = HmsOutput.get_project_name_from_hms("project.hms")
```

### Issue 2: Empty Gage File Created

**Symptom:** HMS creates a new `.gage` file with the folder name but no gages imported.

**Cause:** Using folder name instead of project name in `OpenProject()`.

**Solution:** Same as Issue 1 - use correct project name.

### Issue 3: Empty Stdout from HMS 4.x

**Symptom:** `stdout` is empty after execution even though run succeeded.

**Cause:** HMS 4.x doesn't always write to stdout.

**Solution:** Read the log files instead:
```python
result = HmsOutput.parse_project_log(project_path)
run_result = HmsOutput.parse_run_log(project_path, run_name)
```

## Acceptance Criteria

For a successful upgrade, verify:

1. **No fatal errors** in compute logs
2. **Peak flow difference < 1%** from original
3. **Volume difference < 0.5%** from original
4. **Peak timing unchanged** (within 1 timestep)
5. **All expected output types present** in DSS file

## Files in This Agent

- `AGENT.md` - This documentation
- `compare_dss_outputs.py` - Script to compare DSS outputs between versions
- `upgrade_workflow.py` - Complete upgrade workflow script
- `RESULTS_TEMPLATE.md` - Template for documenting upgrade results
