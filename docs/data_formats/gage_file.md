# Gage File Format (.gage)

## Overview

The `.gage` file defines time-series gage data sources that provide precipitation, flow, or other time-varying inputs to the hydrologic model. Gages typically reference external data stored in DSS (Data Storage System) files, though manual entry is also possible.

## File Purpose

The gage file serves several functions:

- **Data Source Registry**: Lists all time-series gages available to the project
- **DSS File References**: Links to time-series data in DSS files via pathnames
- **Gage Metadata**: Stores gage type, location, and description
- **Data Type Specification**: Defines whether gage provides precipitation, flow, stage, etc.

## Basic Structure

```
Gage: GageName
     Type: Precipitation
     Description: Optional description
     DSS File: data.dss
     DSS Pathname: /BASIN/LOCATION/PARAMETER/DATE/INTERVAL/VERSION/
End:
```

## Gage Types

HMS supports several gage types:

- **Precipitation**: Rainfall or snowfall data
- **Discharge**: Stream flow data
- **Stage**: Water surface elevation
- **Temperature**: Air temperature (for snowmelt)
- **Shortwave**: Solar radiation (for snowmelt)

## DSS File Integration

Most gages reference data in DSS files using DSS pathnames.

### DSS Pathname Structure

DSS pathnames have 6 parts separated by slashes:

```
/A-PART/B-PART/C-PART/D-PART/E-PART/F-PART/
```

**Parts**:
1. **A-Part**: Project or basin name
2. **B-Part**: Location (subbasin, junction, gage)
3. **C-Part**: Parameter type (PRECIP-INC, FLOW, STAGE)
4. **D-Part**: Start date or blank
5. **E-Part**: Time interval (15MIN, 1HOUR, 1DAY)
6. **F-Part**: Version or source (OBS, CALC, SIM)

### Example Pathnames

**Precipitation (incremental)**:
```
/MYBASIN/SUB1/PRECIP-INC/01JAN2020/15MIN/OBS/
```

**Discharge (instantaneous)**:
```
/MYBASIN/OUTLET/FLOW/01JAN2020/15MIN/USGS/
```

**Stage**:
```
/MYBASIN/JUNCTION1/STAGE/15AUG2023/1HOUR/OBS/
```

## Precipitation Gages

### Specified Hyetograph from DSS

```
Gage: RainGage1
     Type: Precipitation
     Description: USGS precipitation gage 12345678
     DSS File: observed_precip.dss
     DSS Pathname: /WATERSHED/RAINGAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/
End:
```

**Key Fields**:
- **Type**: Must be "Precipitation"
- **DSS File**: Relative or absolute path to DSS file
- **DSS Pathname**: Full 6-part DSS pathname
- **Parameter**: Use "PRECIP-INC" for incremental precipitation

### Multiple Precipitation Gages

```
Gage: UpperBasinGage
     Type: Precipitation
     Description: Gage in upper watershed
     DSS File: precip_data.dss
     DSS Pathname: /BASIN/UPPER/PRECIP-INC/01JAN2020/15MIN/OBS/
End:

Gage: LowerBasinGage
     Type: Precipitation
     Description: Gage in lower watershed
     DSS File: precip_data.dss
     DSS Pathname: /BASIN/LOWER/PRECIP-INC/01JAN2020/15MIN/OBS/
End:

Gage: CentralGage
     Type: Precipitation
     Description: Central monitoring station
     DSS File: precip_data.dss
     DSS Pathname: /BASIN/CENTRAL/PRECIP-INC/01JAN2020/15MIN/OBS/
End:
```

### Manual Precipitation Entry

For design storms, gages can use manual hyetographs:

```
Gage: DesignStorm
     Type: Precipitation
     Description: 100-year 24-hour SCS Type III
     Manual Entry
     Time Series: DesignStormHyetograph
End:
```

The time series is defined separately in the project.

## Discharge Gages

Used for observed flow data or boundary conditions:

```
Gage: USGSGage12345
     Type: Discharge
     Description: USGS gage at watershed outlet
     DSS File: streamflow.dss
     DSS Pathname: /RIVER/OUTLET/FLOW/01JAN2020/15MIN/USGS/
End:
```

### Flow Boundary Conditions

```
Gage: UpstreamInflow
     Type: Discharge
     Description: Inflow from upstream ungaged area
     DSS File: boundary_conditions.dss
     DSS Pathname: /SYSTEM/UPSTREAM/FLOW/15AUG2023/1HOUR/COMPUTED/
End:
```

## Stage Gages

For reservoir or channel stage data:

```
Gage: ReservoirStage
     Type: Stage
     Description: Reservoir water surface elevation
     DSS File: reservoir_data.dss
     DSS Pathname: /RESERVOIR/POOL/STAGE/01JAN2020/1HOUR/OBS/
End:
```

## Temperature Gages (Snowmelt)

For temperature-based snowmelt calculations:

```
Gage: WeatherStation
     Type: Temperature
     Description: Air temperature for snowmelt
     DSS File: weather.dss
     DSS Pathname: /BASIN/STATION1/TEMP/01JAN2020/1HOUR/OBS/
End:
```

## Complete Example

```
Gage: MainPrecipGage
     Type: Precipitation
     Description: Primary precipitation gage for design storms
     Last Modified Date: 10 December 2024
     Last Modified Time: 14:30
     DSS File: precipitation.dss
     DSS Pathname: /URBAN_BASIN/MAIN_GAGE/PRECIP-INC/01JAN2020/15MIN/ATLAS14/
End:

Gage: BackupPrecipGage
     Type: Precipitation
     Description: Secondary gage for spatial coverage
     DSS File: precipitation.dss
     DSS Pathname: /URBAN_BASIN/BACKUP_GAGE/PRECIP-INC/01JAN2020/15MIN/ATLAS14/
End:

Gage: ObservedOutflow
     Type: Discharge
     Description: USGS gage 08012345 at basin outlet
     DSS File: observed_flow.dss
     DSS Pathname: /URBAN_BASIN/OUTLET/FLOW/01AUG2023/15MIN/USGS/
End:

Gage: UpstreamBoundary
     Type: Discharge
     Description: Inflow from ungaged upstream area
     DSS File: boundary.dss
     DSS Pathname: /URBAN_BASIN/UPSTREAM/FLOW/01JAN2020/1HOUR/ESTIMATED/
End:

Gage: DetentionStage
     Type: Stage
     Description: Water level in regional detention pond
     DSS File: detention.dss
     DSS Pathname: /URBAN_BASIN/DETENTION/STAGE/01JAN2020/15MIN/OBS/
End:
```

## Working with Gage Files

### Reading All Gages

```python
from hms_commander import HmsGage

# Get all gages as DataFrame
gages_df = HmsGage.get_gages("MyProject.gage")
print(gages_df)
#         Name              Type                    DSS File
# 0  RainGage1   Precipitation         observed_precip.dss
# 1  FlowGage1     Discharge          streamflow.dss
```

### Reading Gage Information

```python
# Get detailed info for specific gage
gage_info = HmsGage.get_gage_info("RainGage1", "MyProject.gage")
print(f"Type: {gage_info['Type']}")
print(f"DSS File: {gage_info['DSS File']}")
print(f"Pathname: {gage_info['DSS Pathname']}")
```

### Creating New Gage

```python
# Create new precipitation gage
HmsGage.create_gage(
    path="MyProject.gage",
    name="NewGage",
    dss_file="precip.dss",
    pathname="/BASIN/NEWGAGE/PRECIP-INC/01JAN2020/15MIN/OBS/"
)
```

### Updating Gage

```python
# Update DSS file reference
HmsGage.update_gage(
    path="MyProject.gage",
    name="RainGage1",
    dss_file="updated_precip.dss"
)
```

### Deleting Gage

```python
# Remove gage from file
HmsGage.delete_gage("MyProject.gage", "OldGage")
```

### Listing by Type

```python
# List only precipitation gages
precip_gages = HmsGage.list_precip_gages("MyProject.gage")
print(f"Precipitation gages: {precip_gages}")

# List only discharge gages
flow_gages = HmsGage.list_discharge_gages("MyProject.gage")
print(f"Discharge gages: {flow_gages}")
```

## DSS File Operations

### Reading DSS Data

```python
from hms_commander import HmsDss

# Read time-series from DSS file
df = HmsDss.read_timeseries(
    dss_file="precip.dss",
    pathname="/BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/"
)
print(df)
#                      Value
# DateTime
# 2020-01-01 00:00:00    0.0
# 2020-01-01 00:15:00    0.1
# 2020-01-01 00:30:00    0.2
```

### Writing DSS Data

```python
import pandas as pd
from datetime import datetime

# Create precipitation data
dates = pd.date_range(start='2020-01-01', periods=96, freq='15min')
values = [0.1, 0.2, 0.5, ...] # 96 values
df = pd.DataFrame({'Value': values}, index=dates)

# Write to DSS
HmsDss.write_timeseries(
    dss_file="new_precip.dss",
    pathname="/BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/SYNTHETIC/",
    data=df,
    units="IN"
)
```

### Parsing DSS Pathnames

```python
# Parse pathname into components
pathname = "/BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/"
parts = HmsDss.parse_dss_pathname(pathname)
print(parts)
# {
#     'A': 'BASIN',
#     'B': 'GAGE1',
#     'C': 'PRECIP-INC',
#     'D': '01JAN2020',
#     'E': '15MIN',
#     'F': 'OBS'
# }
```

### Creating DSS Pathnames

```python
# Build pathname from components
pathname = HmsDss.create_dss_pathname(
    basin="MYBASIN",
    element="SUB1",
    param_type="PRECIP-INC",
    interval="15MIN"
)
print(pathname)
# "/MYBASIN/SUB1/PRECIP-INC//15MIN//"
```

## Time Interval Considerations

DSS time intervals must match or be compatible with HMS control specifications:

| HMS Interval | DSS E-Part | Description |
|--------------|------------|-------------|
| 1 minute | 1MIN | Sub-minute data |
| 5 minutes | 5MIN | High-resolution |
| 15 minutes | 15MIN | Standard design storms |
| 30 minutes | 30MIN | Medium resolution |
| 1 hour | 1HOUR | Hourly data |
| 1 day | 1DAY | Daily data |

**Rule**: HMS computational interval should evenly divide DSS data interval.

## Common Gage Data Types

Defined in `_constants.py`:

```python
from hms_commander._constants import GAGE_DATA_TYPES

print(GAGE_DATA_TYPES)
# ['Precipitation', 'Discharge', 'Stage', 'Temperature', 'Shortwave']
```

## Best Practices

1. **Use descriptive names**: Name gages after location or source (e.g., "USGS_12345")
2. **Document data sources**: Use description field to note data origin
3. **Consistent DSS files**: Keep related data in same DSS file
4. **Version appropriately**: Use F-part to track data versions (OBS, CALC, v1, v2)
5. **Check intervals**: Ensure DSS interval matches or divides HMS interval
6. **Relative paths**: Use relative paths to DSS files for portability

## Common Pitfalls

- **Wrong parameter type**: Use PRECIP-INC (incremental) not PRECIP-CUM (cumulative)
- **Missing DSS files**: Verify DSS file exists before running simulation
- **Pathname typos**: DSS pathnames are case-sensitive
- **Interval mismatch**: HMS interval must align with DSS data interval
- **Date format**: D-part uses format like "01JAN2020" (no spaces)
- **Trailing slashes**: Always include trailing slash in pathname

## Validation

Check gage configuration:

```python
from hms_commander import HmsGage
import os

# Get all gages
gages = HmsGage.get_gages("MyProject.gage")

# Verify DSS files exist
for idx, row in gages.iterrows():
    dss_file = row['DSS File']
    if not os.path.exists(dss_file):
        print(f"Warning: DSS file not found for {row['Name']}: {dss_file}")
```

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Met File Format](met_file.md) - Meteorologic model and gage assignments
- [Control File Format](control_file.md) - Time interval specification
- [DSS Integration](dss_integration.md) - Working with DSS files
- [Run File Format](run_file.md) - Simulation configuration

## API Reference

**Primary Class**: `HmsGage`

**Key Methods**:
- `HmsGage.get_gages()` - Get all gages as DataFrame
- `HmsGage.get_gage_info()` - Get details for specific gage
- `HmsGage.create_gage()` - Create new gage
- `HmsGage.update_gage()` - Update existing gage
- `HmsGage.delete_gage()` - Remove gage
- `HmsGage.list_precip_gages()` - List precipitation gages only
- `HmsGage.list_discharge_gages()` - List discharge gages only

**DSS Operations**: `HmsDss`

**Key Methods**:
- `HmsDss.read_timeseries()` - Read DSS time-series data
- `HmsDss.write_timeseries()` - Write data to DSS
- `HmsDss.parse_dss_pathname()` - Parse pathname components
- `HmsDss.create_dss_pathname()` - Build pathname from parts
- `HmsDss.get_catalog()` - List all pathnames in DSS file

See [API Reference](../api/hms_prj.md) for complete API documentation.
