# HmsCmdr.compute_run() - Complete API Reference

## Primary Source

**Authoritative documentation**: Read `hms_commander/HmsCmdr.py` docstrings for current API.

This file documents patterns and usage NOT captured in docstrings.

## Signature

```python
HmsCmdr.compute_run(
    run_name: str,
    hms_object=None,
    timeout: int = 3600
) -> bool
```

## Usage Patterns

### Pattern 1: Single Project (Global hms)

```python
from hms_commander import init_hms_project, hms, HmsCmdr

init_hms_project(r"C:\Projects\watershed")
success = HmsCmdr.compute_run("Run 1")
```

### Pattern 2: Multiple Projects

```python
from hms_commander import HmsPrj, init_hms_project, HmsCmdr

project1 = HmsPrj()
project2 = HmsPrj()

init_hms_project(r"C:\Projects\watershed1", hms_object=project1)
init_hms_project(r"C:\Projects\watershed2", hms_object=project2)

HmsCmdr.compute_run("Run 1", hms_object=project1)
HmsCmdr.compute_run("Run 1", hms_object=project2)
```

### Pattern 3: With Timeout

```python
# Large model, extend timeout to 2 hours
HmsCmdr.compute_run("Run 1", timeout=7200)
```

## Return Value

Returns `True` if simulation completed successfully, `False` otherwise.

**Check results**:
```python
if HmsCmdr.compute_run("Run 1"):
    # Extract results
    from hms_commander import HmsResults, hms
    dss_file = hms.run_df.loc["Run 1", "dss_file"]
    peaks = HmsResults.get_peak_flows(dss_file)
else:
    # Check log file for errors
    print("Simulation failed!")
```

## What Happens Behind the Scenes

1. **Generates Jython script** using HmsJython.generate_compute_script()
2. **Detects HMS version** from hms_object.hms_exe_path
3. **Executes script** via HmsJython.execute_script()
4. **Monitors progress** via subprocess
5. **Returns status** based on exit code

## Error Handling

```python
try:
    HmsCmdr.compute_run("Run 1")
except FileNotFoundError:
    print("HMS executable not found")
except TimeoutError:
    print("Simulation exceeded timeout")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Alternative Methods

- **HmsCmdr.compute_test_mode()** - Validate without running
- **HmsCmdr.compute_batch()** - Sequential execution
- **HmsCmdr.compute_parallel()** - Parallel execution

**See**: `../SKILL.md` for when to use each method.
