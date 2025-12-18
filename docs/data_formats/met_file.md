# Meteorologic File Format (.met)

## Overview

The `.met` file defines meteorologic models that specify precipitation, evapotranspiration, and snowmelt inputs to the basin model. It controls how weather data is applied to subbasins and which gages provide the input data.

## File Purpose

The meteorologic file serves several functions:

- **Precipitation Methods**: Defines how rainfall is specified (gridded, gage weights, frequency storms)
- **Gage Assignments**: Maps subbasins to precipitation gages
- **Evapotranspiration**: Specifies ET methods and rates
- **Snowmelt**: Defines snowmelt parameters (if applicable)
- **DSS References**: Links to time-series data in DSS files

## Basic Structure

```
Meteorology: MetModelName
     Description: Optional description
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: Monthly Average
End:

Subbasin: SubbasinName
     Precipitation Gage: GageName
     Evapotranspiration: ETMethodName
End:
```

## Meteorologic Model Header

```
Meteorology: 100-Year 24-Hour
     Description: NOAA Atlas 14 100-year 24-hour storm
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: Monthly Average
End:
```

**Key Parameters**:
- **Precipitation Method**: How rainfall is specified (see Precipitation Methods)
- **Evapotranspiration Method**: How ET is calculated (see ET Methods)
- **Description**: Free-text description of meteorologic conditions

## Precipitation Methods

### Specified Hyetograph

Most common method for design storms:

```
Meteorology: DesignStorm
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: None
End:

Subbasin: Sub1
     Precipitation Gage: Gage1
End:

Subbasin: Sub2
     Precipitation Gage: Gage2
End:
```

Precipitation data comes from gages defined in the `.gage` file.

### Frequency Storm

Synthetic storm generation using TP40 or Atlas 14 data:

```
Meteorology: FrequencyBased
     Precipitation Method: Frequency Storm
     Storm Duration: 24.0
     Storm Depth: 8.5
     Return Period: 100
     Storm Area: 10.0
     Temporal Pattern: SCS Type II
     Evapotranspiration Method: None
End:

Subbasin: Sub1
     Precipitation Depth: 8.5
End:

Subbasin: Sub2
     Precipitation Depth: 8.2
End:
```

**Parameters**:
- **Storm Duration**: Duration in hours
- **Storm Depth**: Average depth over basin (inches or mm)
- **Return Period**: Statistical return period (years)
- **Storm Area**: Basin area in square miles
- **Temporal Pattern**: Rainfall distribution (SCS Type I, IA, II, III)

### Gage Weights

Spatial interpolation from multiple gages:

```
Meteorology: GageWeighted
     Precipitation Method: Gage Weights
     Evapotranspiration Method: Monthly Average
End:

Subbasin: Sub1
     Precipitation Gage: Gage1
     Precipitation Gage Weight: 0.6
     Precipitation Gage: Gage2
     Precipitation Gage Weight: 0.4
End:
```

### Gridded Precipitation

Uses gridded data (e.g., radar, HRRR):

```
Meteorology: GriddedData
     Precipitation Method: Gridded Precipitation
     Precipitation Grid: MyGrid
     Evapotranspiration Method: None
End:
```

### Inverse Distance

Spatial interpolation using inverse distance weighting:

```
Meteorology: InverseDistance
     Precipitation Method: Inverse Distance
     Power: 2.0
     Evapotranspiration Method: None
End:

Subbasin: Sub1
     Precipitation Gage: Gage1
     Precipitation Gage: Gage2
     Precipitation Gage: Gage3
End:
```

## Evapotranspiration Methods

### None

No evapotranspiration (common for design storms):

```
Evapotranspiration Method: None
```

### Monthly Average

Constant ET rate by month:

```
Meteorology: ContinuousModel
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: Monthly Average
End:

Basin Evapotranspiration:
     January: 0.05
     February: 0.08
     March: 0.15
     April: 0.22
     May: 0.28
     June: 0.32
     July: 0.30
     August: 0.26
     September: 0.20
     October: 0.12
     November: 0.07
     December: 0.05
End:
```

Values are in inches/day or mm/day.

### Priestley-Taylor

Physically-based ET estimation:

```
Evapotranspiration Method: Priestley-Taylor
```

### Hargreaves

Temperature-based ET method:

```
Evapotranspiration Method: Hargreaves
```

### Gridded Evapotranspiration

```
Evapotranspiration Method: Gridded Evapotranspiration
Evapotranspiration Grid: ETGrid
```

## Gage Assignments

Each subbasin must be assigned precipitation data:

```
Subbasin: ResidentialArea
     Precipitation Gage: RainGage1
     Evapotranspiration: Basin Average
End:

Subbasin: CommercialArea
     Precipitation Gage: RainGage2
     Evapotranspiration: Basin Average
End:
```

## Atlas 14 Frequency Storms

NOAA Atlas 14 provides updated precipitation frequency estimates:

```
Meteorology: Atlas14_100yr_24hr
     Description: NOAA Atlas 14 Volume 11, 100-year 24-hour
     Precipitation Method: Frequency Storm
     Storm Duration: 24.0
     Return Period: 100
     Storm Area: 10.0
     Temporal Pattern: SCS Type III
     Evapotranspiration Method: None
End:

Subbasin: Sub1
     Precipitation Depth: 9.2
End:

Subbasin: Sub2
     Precipitation Depth: 8.8
End:

Subbasin: Sub3
     Precipitation Depth: 9.5
End:
```

### Updating TP40 to Atlas 14

```python
from hms_commander import HmsMet

# Get current depths
current_depths = HmsMet.get_precipitation_depths("model.met")
print(f"Current (TP40): {current_depths}")

# Update to Atlas 14 values
atlas14_depths = [9.2, 8.8, 9.5]  # From NOAA Atlas 14
HmsMet.update_tp40_to_atlas14("model.met", atlas14_depths)

# Verify update
new_depths = HmsMet.get_precipitation_depths("model.met")
print(f"Updated (Atlas 14): {new_depths}")
```

## DSS File References

For observed or gridded data, met models reference DSS files:

```
Meteorology: ObservedEvent
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: None
End:

Subbasin: Sub1
     Precipitation Gage: ObservedGage1
End:
```

The gage data is defined in the `.gage` file with DSS path:

```
Gage: ObservedGage1
     Type: Precipitation
     DSS File: observed.dss
     DSS Pathname: /BASIN/SUB1/PRECIP-INC/01JAN2020/15MIN/OBS/
End:
```

## Complete Example

```
Meteorology: 100-Year Atlas14
     Description: NOAA Atlas 14 100-year 24-hour storm, SCS Type III
     Last Modified Date: 11 December 2024
     Last Modified Time: 09:15
     Precipitation Method: Frequency Storm
     Storm Duration: 24.0
     Return Period: 100
     Storm Area: 15.8
     Temporal Pattern: SCS Type III
     Evapotranspiration Method: None
End:

Subbasin: UpperBasin
     Precipitation Depth: 9.2
End:

Subbasin: MiddleBasin
     Precipitation Depth: 8.8
End:

Subbasin: LowerBasin
     Precipitation Depth: 9.0
End:

Meteorology: ContinuousSimulation
     Description: 2-year continuous simulation with monthly ET
     Last Modified Date: 05 December 2024
     Last Modified Time: 14:30
     Precipitation Method: Specified Hyetograph
     Evapotranspiration Method: Monthly Average
End:

Basin Evapotranspiration:
     January: 0.05
     February: 0.08
     March: 0.15
     April: 0.22
     May: 0.28
     June: 0.32
     July: 0.30
     August: 0.26
     September: 0.20
     October: 0.12
     November: 0.07
     December: 0.05
End:

Subbasin: UpperBasin
     Precipitation Gage: USGS_Gage_12345
     Evapotranspiration: Basin Average
End:

Subbasin: MiddleBasin
     Precipitation Gage: USGS_Gage_12345
     Evapotranspiration: Basin Average
End:

Subbasin: LowerBasin
     Precipitation Gage: CoCoRaHS_Station_A
     Evapotranspiration: Basin Average
End:
```

## Working with Met Files

### Reading Precipitation Method

```python
from hms_commander import HmsMet

# Get precipitation method
method = HmsMet.get_precipitation_method("model.met")
print(f"Precipitation method: {method}")

# Get evapotranspiration method
et_method = HmsMet.get_evapotranspiration_method("model.met")
print(f"ET method: {et_method}")
```

### Reading Gage Assignments

```python
# Get all gage assignments
assignments = HmsMet.get_gage_assignments("model.met")
print(assignments)
#    Subbasin          Gage
# 0  Sub1         RainGage1
# 1  Sub2         RainGage2
```

### Updating Gage Assignments

```python
# Assign gage to subbasin
HmsMet.set_gage_assignment("model.met", "Sub1", "NewGage")

# Assign same gage to multiple subbasins
subbasins = ["Sub1", "Sub2", "Sub3"]
for sub in subbasins:
    HmsMet.set_gage_assignment("model.met", sub, "RegionalGage")
```

### Reading Frequency Storm Parameters

```python
# Get frequency storm configuration
params = HmsMet.get_frequency_storm_params("model.met")
print(f"Duration: {params['Storm Duration']} hours")
print(f"Return Period: {params['Return Period']} years")
print(f"Temporal Pattern: {params['Temporal Pattern']}")
```

### Working with Precipitation Depths

```python
# Get precipitation depths for all subbasins
depths = HmsMet.get_precipitation_depths("model.met")
print(f"Depths: {depths}")

# Update depths (e.g., from Atlas 14)
new_depths = [9.2, 8.8, 9.5]
HmsMet.set_precipitation_depths("model.met", new_depths)
```

### Cloning Met Models

```python
# Clone met model (non-destructive)
HmsMet.clone_met(
    template="100yr.met",
    new_name="100yr_atlas14.met",
    description="Updated with NOAA Atlas 14 depths"
)
```

## Method Enumerations

Available methods from `_constants.py`:

```python
from hms_commander._constants import (
    PRECIP_METHODS,
    ET_METHODS
)

# Check if method is valid
if "Frequency Storm" in PRECIP_METHODS:
    print("Valid precipitation method")

if "Monthly Average" in ET_METHODS:
    print("Valid ET method")
```

## Best Practices

1. **Document data sources**: Note where precipitation data comes from (Atlas 14, gage, etc.)
2. **Match storm patterns to region**: Use appropriate SCS temporal patterns
3. **Verify gage assignments**: Ensure all subbasins have precipitation assigned
4. **Consider ET for continuous**: Include ET for long-term continuous simulations
5. **Use API for Atlas 14 updates**: Use `update_tp40_to_atlas14()` for systematic updates

## Common Pitfalls

- **Missing gage assignments**: All subbasins need precipitation assignments
- **Wrong temporal pattern**: Use region-appropriate SCS storm types
- **Inconsistent units**: Ensure depth units match project settings
- **DSS path errors**: Verify DSS pathnames are correct (case-sensitive)

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Gage File Format](gage_file.md) - Gage definitions and DSS references
- [Basin File Format](basin_file.md) - Basin model structure
- [Control File Format](control_file.md) - Simulation time control
- [DSS Integration](dss_integration.md) - Working with DSS data files

## API Reference

**Primary Class**: `HmsMet`

**Key Methods**:
- `HmsMet.get_precipitation_method()` - Get precipitation method
- `HmsMet.set_precipitation_method()` - Update precipitation method
- `HmsMet.get_evapotranspiration_method()` - Get ET method
- `HmsMet.get_gage_assignments()` - Get all gage assignments
- `HmsMet.set_gage_assignment()` - Assign gage to subbasin
- `HmsMet.get_frequency_storm_params()` - Get frequency storm parameters
- `HmsMet.get_precipitation_depths()` - Get depth values
- `HmsMet.set_precipitation_depths()` - Update depth values
- `HmsMet.update_tp40_to_atlas14()` - Update TP40 to Atlas 14
- `HmsMet.clone_met()` - Clone meteorologic model

See [API Reference](../api/hms_prj.md) for complete API documentation.
