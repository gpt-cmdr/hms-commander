# Example: Query JythonHms API

**Scenario**: You want to know if HMS supports a specific JythonHms method and how to use it.

---

## Question

Does HMS 4.13 support `SetTimeWindow()` in the JythonHms API? If so, what are the parameters?

---

## Investigation Steps

### Step 1: Check API Reference

Open `knowledge/JYTHON_HMS_API.md` and search for "SetTimeWindow".

### Step 2: Review Method Signature

Found in JYTHON_HMS_API.md:

```java
public static void SetTimeWindow(String startDate, String startTime, String endDate, String endTime)
    throws Exception
```

### Step 3: Understand Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `startDate` | String | Start date | "01Jan2020" |
| `startTime` | String | Start time (24-hour) | "00:00" |
| `endDate` | String | End date | "02Jan2020" |
| `endTime` | String | End time (24-hour) | "00:00" |

**Date format**: `DDMmmYYYY` (e.g., "01Jan2020", "15Mar2021")
**Time format**: `HH:MM` (24-hour, e.g., "00:00", "14:30")

### Step 4: Check for Notes

From JYTHON_HMS_API.md:

- Throws `Exception` if invalid date/time format
- Sets simulation time window for current control specification
- Must be called before `ComputeRun()`

---

## Result

✅ **YES** - HMS 4.13 supports `SetTimeWindow()`

---

## hms-commander Integration

### Current Status

**Not yet implemented** in hms-commander.

HmsControl currently manages time window via file parsing:
- `HmsControl.set_start_date()`
- `HmsControl.set_start_time()`
- `HmsControl.set_end_date()`
- `HmsControl.set_end_time()`

### Potential Implementation

Could add HmsJython method wrapper:

```python
# hms_commander/HmsJython.py

@staticmethod
def set_time_window(start_date, start_time, end_date, end_time, python2_compatible=False):
    """
    Generate Jython script to set time window.

    Args:
        start_date (str): Start date (e.g., "01Jan2020")
        start_time (str): Start time (e.g., "00:00")
        end_date (str): End date (e.g., "02Jan2020")
        end_time (str): End time (e.g., "00:00")
        python2_compatible (bool): Use Python 2 syntax for HMS 3.x

    Returns:
        str: Jython script lines
    """
    lines = []

    # Validate date format
    # (implementation here)

    # Generate script
    lines.append(f'JythonHms.SetTimeWindow("{start_date}", "{start_time}", "{end_date}", "{end_time}")')

    return lines
```

**Usage**:
```python
from hms_commander import HmsJython

script_lines = HmsJython.set_time_window(
    start_date="01Jan2020",
    start_time="00:00",
    end_date="02Jan2020",
    end_time="00:00"
)
```

---

## Validation

### Test in HMS

Create test script:

```python
# test_time_window.py
from hec.script import *
JythonHms = HmsScriptAPI()

JythonHms.OpenProject("Test Project", "C:/Projects/test")
JythonHms.SetTimeWindow("01Jan2020", "00:00", "02Jan2020", "00:00")
JythonHms.ComputeRun("Run 1")
JythonHms.Exit(0)
```

Run in HMS:
```batch
HEC-HMS.cmd -script test_time_window.py
```

**Expected**: Simulation runs with specified time window

---

## Alternative: File-Based Approach

**Current hms-commander approach** (via HmsControl):

```python
from hms_commander import HmsControl

HmsControl.set_start_date("project.control", "01Jan2020")
HmsControl.set_start_time("project.control", "00:00")
HmsControl.set_end_date("project.control", "02Jan2020")
HmsControl.set_end_time("project.control", "00:00")
```

**Advantages**:
- Works without executing HMS
- Direct file modification
- GUI-verifiable

**Jython approach advantages**:
- Runtime modification
- Programmatic control
- Can set during script execution

---

## Related Questions

**Q: Does HMS 3.x support SetTimeWindow()?**
A: Check `knowledge/HMS_3x_SUPPORT.md` for version differences - likely YES, same API

**Q: What happens if I provide invalid date format?**
A: JythonHms throws `Exception`. HMS execution fails with error code.

**Q: Can I set time window mid-script?**
A: Unknown - test required. Likely must be before ComputeRun().

---

## Next Steps

1. Test `SetTimeWindow()` in HMS 4.13
2. Test in HMS 3.3 (confirm 3.x support)
3. Implement in hms-commander if valuable
4. Document any discovered limitations

---

**Example completed**: 2025-12-12
**HMS version tested**: 4.13 (via decompilation)
**hms-commander version**: Not yet implemented
