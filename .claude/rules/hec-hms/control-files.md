---
paths: hms_commander/**/*.py
---

# Control Specification Operations

## Primary Sources

**Code**: `hms_commander/HmsControl.py`
- `HmsControl.get_controls()` — list all control specs
- `HmsControl.get_time_window()` — read start/end times
- `HmsControl.set_time_window()` — write time window
- `HmsControl.clone_control()` — non-destructive copy

**File Format**: `tests/projects/2014.08_HMS/File Parsing Guide/04_Control_File.md`

## .control File Structure

```
Control: ControlName
     Start Date: 26 May 1992
     Start Time: 00:00
     End Date: 26 May 1992
     End Time: 06:00
     Time Interval: 5
End:
```

## Date/Time Format

**HMS uses this specific format** (not ISO 8601):

| Field | Format | Example |
|-------|--------|---------|
| Date | `DD Mmm YYYY` | `26 May 1992` |
| Time | `HH:MM` (24-hour) | `00:00`, `18:30` |
| Time Interval | integer minutes | `5`, `10`, `15`, `60` |

**Python conversion**:
```python
from datetime import datetime

# Parse HMS date/time
dt = datetime.strptime("26 May 1992 00:00", "%d %b %Y %H:%M")

# Format for HMS
hms_date = dt.strftime("%-d %b %Y")   # "26 May 1992" (Linux)
hms_date = dt.strftime("%#d %b %Y")   # "26 May 1992" (Windows)
hms_time = dt.strftime("%H:%M")        # "00:00"
```

## Common Patterns

### Read Time Window
```python
from hms_commander import HmsControl

window = HmsControl.get_time_window("project.control", "Feb2014_24hr")
# Returns: {
#   'start_date': '26 Feb 2014', 'start_time': '00:00',
#   'end_date': '27 Feb 2014',   'end_time': '00:00',
#   'time_interval': 15
# }
```

### Clone Control (for scenario comparison)
```python
from hms_commander import HmsControl, hms

HmsControl.clone_control("Baseline_Control", "Extended_Control")
# Creates copy in .control file, updates .hms project file
```

### List All Controls
```python
controls = HmsControl.get_controls("project.control")
# Returns: ['Feb2014_24hr', 'May1992_6hr', ...]
```

## Time Interval Considerations

- Time interval affects DSS output record length
- Must be consistent with precipitation time series resolution
- Common values: 5, 10, 15, 30, 60 minutes
- HMS will warn if time interval > precipitation data interval

## Related

- **Basin files**: `.claude/rules/hec-hms/basin-files.md`
- **Met files**: `.claude/rules/hec-hms/met-files.md`
- **File formats**: `.claude/rules/hec-hms/file-formats.md`
- **Execution**: `.claude/rules/hec-hms/execution.md`
