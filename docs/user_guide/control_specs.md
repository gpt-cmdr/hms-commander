# Control Specifications

Configuring simulation time windows and time intervals in HEC-HMS control specifications (.control).

## Overview

The `HmsControl` class provides methods for managing control specification files, which define simulation start/end dates and computational time intervals.

## Quick Examples

### Get Time Window

```python
from hms_commander import HmsControl

# Read time window
time_window = HmsControl.get_time_window("spec.control")
print(time_window)
# {'start_date': '01Jan2020', 'start_time': '00:00',
#  'end_date': '02Jan2020', 'end_time': '00:00'}
```

### Set Time Window

```python
# Update simulation period
HmsControl.set_time_window(
    "spec.control",
    start_date="15Jan2020",
    start_time="06:00",
    end_date="16Jan2020",
    end_time="18:00"
)
```

### Set Time Interval

```python
# Set computational time step
HmsControl.set_time_interval("spec.control", 15)  # 15 minutes
```

### Create New Control

```python
# Create control specification
HmsControl.create_control(
    path="new_spec.control",
    name="Storm_Event_2020",
    start_date="15Jan2020",
    start_time="00:00",
    end_date="17Jan2020",
    end_time="00:00",
    interval=15  # minutes
)
```

## Key Operations

- **Time windows** - `get_time_window()`, `set_time_window()`
- **Time intervals** - `get_time_interval()`, `set_time_interval()`
- **Create new** - `create_control()`
- **Clone workflow** - `clone_control()` for sensitivity analysis

## Time Interval Options

Supported intervals (in minutes):
- 1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30 minutes
- 60 (1 hour), 120 (2 hours), 180 (3 hours), 360 (6 hours), 720 (12 hours), 1440 (24 hours)

## Related Topics

- [API Reference: HmsControl](../api/hms_control.md) - Complete method documentation
- [Data Formats: Control File](../data_formats/control_file.md) - HMS .control file format
- [HmsUtils](../api/hms_utils.md) - Time interval conversion utilities

---

*For complete API documentation, see [HmsControl API Reference](../api/hms_control.md)*
