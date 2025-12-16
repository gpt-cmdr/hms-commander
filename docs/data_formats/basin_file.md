# Basin File Format (.basin)

## Overview

The `.basin` file defines the physical watershed model, including subbasins, stream reaches, junctions, reservoirs, and diversions. It contains the hydrologic parameters that govern how rainfall is converted to runoff and how water is routed through the stream network.

## File Purpose

The basin file serves as the core hydrologic model definition:

- **Physical Elements**: Defines subbasins, reaches, junctions, sources, sinks
- **Connectivity**: Specifies upstream-downstream relationships
- **Hydrologic Methods**: Defines loss methods, transform methods, routing methods
- **Parameters**: Stores calibration parameters for each method
- **Topology**: Establishes the basin network structure

## Basic Structure

```
Basin: BasinName
     Description: Optional basin description
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
End:

Subbasin: SubbasinName
     Area: 123.45
     Downstream: JunctionName
     Loss: SCS Curve Number
     Transform: SCS Unit Hydrograph
End:

Junction: JunctionName
     Downstream: OutletName
End:

Reach: ReachName
     Downstream: JunctionName
     Route: Muskingum
End:
```

## Element Types

### Basin Model Header

The header defines the basin model metadata:

```
Basin: ExistingConditions
     Description: Current watershed conditions
     Last Modified Date: 15 November 2024
     Last Modified Time: 14:30
     Canvas X: 12345
     Canvas Y: 67890
End:
```

### Subbasin

Subbasins represent drainage areas where rainfall-runoff transformation occurs:

```
Subbasin: Sub1
     Description: Upper watershed area
     Canvas X: 1000.0
     Canvas Y: 2000.0
     Area: 245.5
     Downstream: Junc1

     Loss: SCS Curve Number
          Curve Number: 75.0
          Percent Impervious: 5.0
          Initial Abstraction: 0.2
     End:

     Transform: SCS Unit Hydrograph
          Lag Time: 120.0
     End:

     Baseflow: Constant Monthly
          January: 10.0
          February: 12.0
          March: 15.0
          April: 18.0
          May: 20.0
          June: 22.0
          July: 18.0
          August: 15.0
          September: 12.0
          October: 10.0
          November: 10.0
          December: 10.0
     End:
End:
```

#### Key Subbasin Parameters

- **Area**: Drainage area in square miles (or km² depending on units)
- **Downstream**: Name of downstream element (junction, reach, or sink)
- **Canvas X/Y**: GUI display coordinates
- **Loss**: Infiltration/loss method (see Loss Methods section)
- **Transform**: Rainfall-runoff transformation (see Transform Methods)
- **Baseflow**: Base flow contribution (optional)

### Junction

Junctions combine flows from multiple upstream elements:

```
Junction: Junc1
     Description: Confluence of streams A and B
     Canvas X: 1500.0
     Canvas Y: 2500.0
     Downstream: Reach1
End:
```

Junctions do not transform flows; they simply sum upstream hydrographs.

### Reach

Reaches represent stream channel segments with routing:

```
Reach: Reach1
     Description: Main channel from junction to outlet
     Canvas X: 2000.0
     Canvas Y: 3000.0
     Downstream: Outlet

     Route: Muskingum
          Muskingum K: 1.5
          Muskingum X: 0.25
          Number of Subreaches: 3
     End:
End:
```

#### Common Routing Methods

**Muskingum Routing**:
```
Route: Muskingum
     Muskingum K: 1.5
     Muskingum X: 0.25
     Number of Subreaches: 3
End:
```

**Lag Routing**:
```
Route: Lag
     Lag Time: 60.0
End:
```

**Kinematic Wave**:
```
Route: Kinematic Wave
     Length: 5280.0
     Slope: 0.01
     Manning's N: 0.035
     Shape: Rectangular
     Width: 50.0
End:
```

### Source

Sources introduce external flow hydrographs:

```
Source: UpstreamInflow
     Canvas X: 500.0
     Canvas Y: 1000.0
     Downstream: Junc1
End:
```

### Sink

Sinks represent outlets or measurement points:

```
Sink: Outlet
     Canvas X: 3000.0
     Canvas Y: 4000.0
End:
```

### Reservoir

Reservoirs provide storage and routing:

```
Reservoir: Pond1
     Canvas X: 1800.0
     Canvas Y: 2800.0
     Downstream: Reach2

     Route: Storage Routing
          Storage Area Curve: PondCurve
          Outlet: Spillway
     End:
End:
```

### Diversion

Diversions split flows:

```
Diversion: Diversion1
     Canvas X: 2200.0
     Canvas Y: 3200.0
     Downstream: Junc2
     Diverted Downstream: Canal1
End:
```

## Loss Methods

Loss methods compute infiltration and surface retention.

### SCS Curve Number

Most common loss method in the United States:

```
Loss: SCS Curve Number
     Curve Number: 75.0
     Percent Impervious: 5.0
     Initial Abstraction: 0.2
End:
```

**Parameters**:
- **Curve Number**: 0-100, represents runoff potential (higher = more runoff)
- **Percent Impervious**: 0-100%, impervious area percentage
- **Initial Abstraction**: Ratio (typically 0.2) or absolute value

### Deficit and Constant

Alternative loss method:

```
Loss: Deficit and Constant
     Initial Deficit: 25.4
     Maximum Deficit: 76.2
     Constant Rate: 2.54
     Percent Impervious: 10.0
End:
```

### Green and Ampt

Physically-based infiltration:

```
Loss: Green and Ampt
     Initial Moisture Deficit: 0.25
     Hydraulic Conductivity: 0.5
     Wetting Front Suction: 3.5
     Percent Impervious: 5.0
End:
```

## Transform Methods

Transform methods convert excess precipitation to runoff hydrographs.

### SCS Unit Hydrograph

Synthetic unit hydrograph method:

```
Transform: SCS Unit Hydrograph
     Lag Time: 120.0
End:
```

**Lag Time**: Time in minutes from center of mass of rainfall to peak runoff

### Clark Unit Hydrograph

```
Transform: Clark Unit Hydrograph
     Time of Concentration: 180.0
     Storage Coefficient: 90.0
End:
```

### Snyder Unit Hydrograph

```
Transform: Snyder Unit Hydrograph
     Standard Lag: 3.5
     Peaking Coefficient: 0.6
End:
```

### User-Specified Unit Hydrograph

```
Transform: User-Specified Unit Hydrograph
     Unit Hydrograph: MyUnitHydrograph
End:
```

## Baseflow Methods

### Constant Monthly

```
Baseflow: Constant Monthly
     January: 10.0
     February: 12.0
     March: 15.0
     April: 18.0
     May: 20.0
     June: 22.0
     July: 18.0
     August: 15.0
     September: 12.0
     October: 10.0
     November: 10.0
     December: 10.0
End:
```

### Recession

```
Baseflow: Recession
     Initial Discharge: 100.0
     Recession Constant: 0.85
     Threshold Discharge: 500.0
End:
```

## Complete Example

```
Basin: UrbanWatershed
     Description: Mixed-use urban watershed with detention
     Last Modified Date: 20 December 2024
     Last Modified Time: 10:30
End:

Subbasin: ResidentialArea
     Description: Low-density residential
     Canvas X: 1000.0
     Canvas Y: 2000.0
     Area: 145.8
     Downstream: DowntownJunction

     Loss: SCS Curve Number
          Curve Number: 72.0
          Percent Impervious: 15.0
          Initial Abstraction: 0.2
     End:

     Transform: SCS Unit Hydrograph
          Lag Time: 95.0
     End:

     Baseflow: Constant Monthly
          January: 5.0
          February: 6.0
          March: 8.0
          April: 10.0
          May: 12.0
          June: 10.0
          July: 7.0
          August: 5.0
          September: 4.0
          October: 4.0
          November: 5.0
          December: 5.0
     End:
End:

Subbasin: CommercialArea
     Description: Commercial district with high impervious
     Canvas X: 1500.0
     Canvas Y: 2000.0
     Area: 78.3
     Downstream: DowntownJunction

     Loss: SCS Curve Number
          Curve Number: 88.0
          Percent Impervious: 65.0
          Initial Abstraction: 0.2
     End:

     Transform: SCS Unit Hydrograph
          Lag Time: 45.0
     End:
End:

Junction: DowntownJunction
     Description: Convergence before detention
     Canvas X: 2000.0
     Canvas Y: 2500.0
     Downstream: DetentionPond
End:

Reservoir: DetentionPond
     Description: Regional detention facility
     Canvas X: 2500.0
     Canvas Y: 2800.0
     Downstream: MainChannel

     Route: Storage Routing
          Storage Area Curve: DetentionCurve
          Outlet: OutletStructure
     End:
End:

Reach: MainChannel
     Description: Concrete-lined channel to outlet
     Canvas X: 3000.0
     Canvas Y: 3200.0
     Downstream: Outlet

     Route: Muskingum
          Muskingum K: 0.8
          Muskingum X: 0.20
          Number of Subreaches: 2
     End:
End:

Sink: Outlet
     Description: Watershed outlet at stream confluence
     Canvas X: 3500.0
     Canvas Y: 3600.0
End:
```

## Working with Basin Files

### Reading Basin Elements

```python
from hms_commander import HmsBasin

# Get all subbasins
subbasins_df = HmsBasin.get_subbasins("MyProject.basin")
print(subbasins_df)

# Get junctions
junctions_df = HmsBasin.get_junctions("MyProject.basin")

# Get reaches
reaches_df = HmsBasin.get_reaches("MyProject.basin")
```

### Reading Parameters

```python
# Get loss parameters for a subbasin
loss_params = HmsBasin.get_loss_parameters("MyProject.basin", "Sub1")
print(f"Curve Number: {loss_params['Curve Number']}")

# Get transform parameters
transform_params = HmsBasin.get_transform_parameters("MyProject.basin", "Sub1")
print(f"Lag Time: {transform_params['Lag Time']}")

# Get routing parameters for a reach
routing_params = HmsBasin.get_routing_parameters("MyProject.basin", "Reach1")
```

### Modifying Parameters

```python
# Update loss parameters
HmsBasin.set_loss_parameters(
    "MyProject.basin",
    "Sub1",
    curve_number=80,
    percent_impervious=20
)

# Update multiple subbasins
subbasins = ["Sub1", "Sub2", "Sub3"]
for sub in subbasins:
    HmsBasin.set_loss_parameters(
        "MyProject.basin",
        sub,
        curve_number=85
    )
```

### Cloning Basin Models

```python
# Clone basin model (non-destructive)
HmsBasin.clone_basin(
    template="existing.basin",
    new_name="proposed.basin",
    description="Future conditions with development"
)
```

## Method Enumerations

Available methods are defined in `_constants.py`:

```python
from hms_commander._constants import (
    LOSS_METHODS,
    TRANSFORM_METHODS,
    BASEFLOW_METHODS,
    ROUTING_METHODS
)

# Check if method is valid
if "SCS Curve Number" in LOSS_METHODS:
    print("Valid loss method")
```

## Best Practices

1. **Consistent naming**: Use clear, descriptive element names
2. **Document elements**: Use description fields for complex models
3. **Validate topology**: Ensure all elements have proper downstream connections
4. **Calibrate systematically**: Use observed data to calibrate parameters
5. **Use API for modifications**: Prefer `HmsBasin` methods over manual text editing

## Common Pitfalls

- **Missing downstream**: Every element (except sinks) must have a downstream connection
- **Invalid parameters**: Some parameters have valid ranges (e.g., CN: 0-100)
- **Method compatibility**: Not all methods work together (check HMS documentation)
- **Units consistency**: Ensure consistent units throughout the model

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Met File Format](met_file.md) - Meteorologic model configuration
- [Control File Format](control_file.md) - Simulation time control
- [Geo Files](geo_files.md) - Geospatial coordinates for basin elements

## API Reference

**Primary Class**: `HmsBasin`

**Key Methods**:
- `HmsBasin.get_subbasins()` - Extract all subbasins
- `HmsBasin.get_junctions()` - Extract all junctions
- `HmsBasin.get_reaches()` - Extract all reaches
- `HmsBasin.get_loss_parameters()` - Get loss method parameters
- `HmsBasin.set_loss_parameters()` - Update loss parameters
- `HmsBasin.get_transform_parameters()` - Get transform parameters
- `HmsBasin.get_routing_parameters()` - Get routing parameters
- `HmsBasin.clone_basin()` - Clone basin model

See [CLAUDE.md](../../CLAUDE.md) for complete API documentation.
