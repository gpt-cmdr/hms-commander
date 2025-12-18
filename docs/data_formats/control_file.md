# Control File Format (.control)

## Overview

The `.control` file defines control specifications that govern simulation timing and computational settings. It specifies the simulation start time, end time, and computational time interval - the fundamental parameters that control when and how frequently HMS performs calculations.

## File Purpose

The control file serves several critical functions:

- **Time Window**: Defines simulation start and end date/time
- **Time Interval**: Specifies computational timestep
- **Run Duration**: Implicitly determines simulation length
- **Temporal Discretization**: Controls calculation frequency and output resolution

## Basic Structure

```
Control: ControlName
     Description: Optional description
     Start Date: 01Jan2020
     Start Time: 00:00
     End Date: 02Jan2020
     End Time: 00:00
     Time Interval: 15
End:
```

## Control Specification Elements

### Header

```
Control: 24-Hour Event
     Description: Standard 24-hour design storm simulation
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
End:
```

**Key Fields**:
- **Control**: Name of control specification
- **Description**: Free-text description (optional)
- **Last Modified Date/Time**: Timestamp of last modification

### Time Window Parameters

```
Control: FloodEvent
     Start Date: 15Aug2023
     Start Time: 06:00
     End Date: 17Aug2023
     End Time: 18:00
     Time Interval: 15
End:
```

**Parameters**:
- **Start Date**: Simulation start date in `DDMmmYYYY` format
- **Start Time**: Simulation start time in `HH:MM` format (24-hour)
- **End Date**: Simulation end date in `DDMmmYYYY` format
- **End Time**: Simulation end time in `HH:MM` format (24-hour)
- **Time Interval**: Computational timestep in minutes

### Date Format

HMS uses a specific date format:
- **Format**: `DDMmmYYYY`
- **Examples**: `01Jan2020`, `15Aug2023`, `31Dec2024`
- **Month abbreviations**: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec

### Time Format

HMS uses 24-hour time format:
- **Format**: `HH:MM`
- **Examples**: `00:00` (midnight), `14:30` (2:30 PM), `23:45` (11:45 PM)
- **No seconds**: Only hours and minutes are specified

### Time Interval

The time interval determines computational timestep:
- **Units**: Minutes
- **Common values**: 5, 10, 15, 30, 60
- **Considerations**:
  - Smaller intervals = more accurate but slower
  - Larger intervals = faster but less accurate
  - Must be appropriate for basin time of concentration

## Complete Examples

### Design Storm (24-Hour)

```
Control: 24-Hour Design
     Description: Standard 24-hour design storm for flood analysis
     Last Modified Date: 10 December 2024
     Last Modified Time: 09:30
     Start Date: 01Jan2020
     Start Time: 00:00
     End Date: 02Jan2020
     End Time: 00:00
     Time Interval: 15
End:
```

This configuration:
- Simulates exactly 24 hours
- Uses 15-minute timestep
- Produces 96 computational intervals (24 hours × 60 min/hr ÷ 15 min)

### Multi-Day Event

```
Control: HurricaneEvent
     Description: 5-day hurricane simulation with hourly timestep
     Start Date: 25Aug2017
     Start Time: 00:00
     End Date: 30Aug2017
     End Time: 00:00
     Time Interval: 60
End:
```

This configuration:
- Simulates 5 days (120 hours)
- Uses 1-hour timestep
- Produces 120 computational intervals

### Short-Duration Event

```
Control: CloudburstEvent
     Description: 6-hour intense rainfall event
     Start Date: 15Jul2024
     Start Time: 14:00
     End Date: 15Jul2024
     End Time: 20:00
     Time Interval: 5
End:
```

This configuration:
- Simulates 6 hours
- Uses 5-minute timestep for high resolution
- Produces 72 computational intervals

### Continuous Simulation

```
Control: WaterYear2023
     Description: Complete water year continuous simulation
     Start Date: 01Oct2022
     Start Time: 00:00
     End Date: 30Sep2023
     End Time: 23:59
     Time Interval: 60
End:
```

This configuration:
- Simulates full water year (365 days)
- Uses 1-hour timestep
- Produces 8,760 computational intervals

### Multiple Control Specifications

A project can have multiple control specifications for different scenarios:

```
Control: 6-Hour Event
     Description: Short-duration intense storm
     Start Date: 01Jan2020
     Start Time: 00:00
     End Date: 01Jan2020
     End Time: 06:00
     Time Interval: 5
End:

Control: 24-Hour Event
     Description: Standard 24-hour design storm
     Start Date: 01Jan2020
     Start Time: 00:00
     End Date: 02Jan2020
     End Time: 00:00
     Time Interval: 15
End:

Control: 72-Hour Event
     Description: Extended multi-day event
     Start Date: 01Jan2020
     Start Time: 00:00
     End Date: 04Jan2020
     End Time: 00:00
     Time Interval: 30
End:
```

## Working with Control Files

### Reading Time Window

```python
from hms_commander import HmsControl

# Get simulation time window
time_window = HmsControl.get_time_window("MyProject.control")
print(f"Start: {time_window['start_date']} {time_window['start_time']}")
print(f"End: {time_window['end_date']} {time_window['end_time']}")
```

### Reading Time Interval

```python
# Get computational timestep
interval = HmsControl.get_time_interval("MyProject.control")
print(f"Time interval: {interval}")
# Output: "15 Minutes"
```

### Setting Time Window

```python
from datetime import datetime

# Update time window
HmsControl.set_time_window(
    "MyProject.control",
    start_datetime=datetime(2024, 1, 1, 0, 0),
    end_datetime=datetime(2024, 1, 2, 0, 0)
)
```

### Setting Time Interval

```python
# Set interval using minutes
HmsControl.set_time_interval("MyProject.control", 15)

# Or use string format
HmsControl.set_time_interval("MyProject.control", "15 Minutes")
```

### Creating New Control Specification

```python
from datetime import datetime

# Create new control specification
HmsControl.create_control(
    path="MyProject.control",
    name="6-Hour Storm",
    start_datetime=datetime(2024, 7, 15, 6, 0),
    end_datetime=datetime(2024, 7, 15, 12, 0),
    interval_minutes=5
)
```

### Cloning Control Specifications

```python
# Clone control specification (non-destructive)
HmsControl.clone_control(
    template="24hr.control",
    new_name="24hr_5min.control"
)

# Then modify the interval
HmsControl.set_time_interval("24hr_5min.control", 5)
```

## Time Interval Selection Guidelines

### Small Urban Watersheds
- **Time of Concentration**: < 1 hour
- **Recommended Interval**: 5-10 minutes
- **Reason**: Capture rapid response to rainfall

### Medium Watersheds
- **Time of Concentration**: 1-6 hours
- **Recommended Interval**: 10-15 minutes
- **Reason**: Balance accuracy and computation time

### Large Watersheds
- **Time of Concentration**: > 6 hours
- **Recommended Interval**: 15-60 minutes
- **Reason**: Slower response allows larger timestep

### Continuous Simulation
- **Duration**: Months to years
- **Recommended Interval**: 60 minutes (1 hour)
- **Reason**: Minimize computation time for long simulations

### General Rule of Thumb
Time interval should be **1/5 to 1/10** of the shortest time of concentration in the basin.

## Date/Time Utilities

### Parsing HMS Dates

```python
from hms_commander import HmsUtils
from datetime import datetime

# Parse HMS date and time strings
dt = HmsUtils.parse_hms_date("01Jan2020", "14:30")
print(dt)  # datetime(2020, 1, 1, 14, 30)
```

### Formatting Dates for HMS

```python
from datetime import datetime
from hms_commander import HmsUtils

# Format Python datetime for HMS
dt = datetime(2024, 12, 15, 9, 30)
date_str, time_str = HmsUtils.format_hms_date(dt)
print(f"{date_str} {time_str}")  # "15Dec2024 09:30"
```

### Time Interval Conversions

```python
from hms_commander import HmsUtils

# Parse interval string to minutes
minutes = HmsUtils.parse_time_interval("15 Minutes")
print(minutes)  # 15

# Convert minutes to interval string
interval_str = HmsUtils.minutes_to_interval_string(60)
print(interval_str)  # "1 Hour"
```

## Common Interval Values

| Minutes | String Format | Typical Use |
|---------|--------------|-------------|
| 1 | "1 Minute" | Research/special studies |
| 5 | "5 Minutes" | Small urban watersheds |
| 10 | "10 Minutes" | Urban watersheds |
| 15 | "15 Minutes" | Standard design storms |
| 30 | "30 Minutes" | Medium watersheds |
| 60 | "1 Hour" | Large watersheds, continuous |
| 1440 | "1 Day" | Daily water balance studies |

## Best Practices

1. **Match interval to basin**: Use appropriate timestep for time of concentration
2. **Consider output needs**: Smaller intervals = more detailed hydrographs
3. **Balance accuracy and speed**: Smaller isn't always better
4. **Use consistent dates**: Start at midnight (00:00) when possible
5. **Document rationale**: Use description field to explain choices

## Common Pitfalls

- **Interval too large**: May miss peak flows or produce numerical instability
- **Interval too small**: Unnecessarily long computation times
- **Wrong date format**: HMS requires `DDMmmYYYY` format exactly
- **Time beyond event**: Ensure simulation extends beyond rainfall end
- **Mismatched intervals**: Gage data interval should match or divide evenly into computational interval

## Validation

Check control specification validity:

```python
from hms_commander import HmsControl

# Get time window
window = HmsControl.get_time_window("MyProject.control")

# Verify duration is appropriate
start = datetime.strptime(f"{window['start_date']} {window['start_time']}",
                          "%d%b%Y %H:%M")
end = datetime.strptime(f"{window['end_date']} {window['end_time']}",
                        "%d%b%Y %H:%M")
duration_hours = (end - start).total_seconds() / 3600
print(f"Simulation duration: {duration_hours} hours")
```

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Basin File Format](basin_file.md) - Basin model structure
- [Met File Format](met_file.md) - Meteorologic model configuration
- [Run File Format](run_file.md) - Simulation run configuration
- [Gage File Format](gage_file.md) - Time-series gage data

## API Reference

**Primary Class**: `HmsControl`

**Key Methods**:
- `HmsControl.get_time_window()` - Extract start/end date/time
- `HmsControl.set_time_window()` - Update time window
- `HmsControl.get_time_interval()` - Get computational timestep
- `HmsControl.set_time_interval()` - Update timestep
- `HmsControl.create_control()` - Create new control specification
- `HmsControl.clone_control()` - Clone existing control specification

**Utility Functions**:
- `HmsUtils.parse_hms_date()` - Parse HMS date/time to Python datetime
- `HmsUtils.format_hms_date()` - Format datetime for HMS
- `HmsUtils.parse_time_interval()` - Convert interval string to minutes
- `HmsUtils.minutes_to_interval_string()` - Convert minutes to interval string

See [API Reference](../api/hms_prj.md) for complete API documentation.
