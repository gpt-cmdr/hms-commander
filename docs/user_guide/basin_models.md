# Basin Models

Working with HEC-HMS basin model files (.basin) - subbasins, junctions, reaches, and parameters.

## Overview

The `HmsBasin` class provides methods for reading and modifying basin model files. All operations work directly with HMS text files using static methods.

## Quick Examples

### Get Subbasins

```python
from hms_commander import HmsBasin

# Read all subbasins
subbasins_df = HmsBasin.get_subbasins("path/to/model.basin")
print(subbasins_df)
```

### Modify Loss Parameters

```python
# Update curve number
HmsBasin.set_loss_parameters(
    "model.basin",
    "Subbasin1",
    curve_number=85
)
```

### Clone Basin (Non-Destructive)

```python
# Create new basin from template
HmsBasin.clone_basin(
    template="ExistingBasin",
    new_name="UpdatedBasin",
    description="Modified parameters for sensitivity analysis"
)
```

## Key Operations

- **Read elements** - `get_subbasins()`, `get_junctions()`, `get_reaches()`
- **Get parameters** - `get_loss_parameters()`, `get_transform_parameters()`, `get_routing_parameters()`
- **Set parameters** - `set_loss_parameters()` and other setters
- **Clone workflow** - `clone_basin()` for non-destructive modifications

## LLM Forward Principles

Basin operations follow the LLM Forward approach:
- ✅ **GUI Verifiable** - Changes visible in HEC-HMS GUI
- ✅ **Non-Destructive** - Clone operations preserve originals
- ✅ **Traceable** - Parameter changes logged

## Related Topics

- [API Reference: HmsBasin](../api/hms_basin.md) - Complete method documentation
- [Clone Workflows](clone_workflows.md) - Non-destructive modification patterns
- [Data Formats: Basin File](../data_formats/basin_file.md) - HMS .basin file format

---

*For complete API documentation, see [HmsBasin API Reference](../api/hms_basin.md)*
