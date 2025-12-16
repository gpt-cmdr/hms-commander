# Meteorologic Models

Managing precipitation, evapotranspiration, and gage assignments in HEC-HMS meteorologic models (.met).

## Overview

The `HmsMet` class provides methods for working with meteorologic model files, including precipitation methods, gage assignments, and frequency storm parameters.

## Quick Examples

### Get Gage Assignments

```python
from hms_commander import HmsMet

# Read gage assignments
gages_df = HmsMet.get_gage_assignments("model.met")
print(gages_df)
```

### Update Gage Assignment

```python
# Assign gage to subbasin
HmsMet.set_gage_assignment(
    "model.met",
    subbasin="Sub1",
    gage="Precip_Gage_1"
)
```

### Update Precipitation Depths (Atlas 14)

```python
# Update TP-40 to Atlas 14 depths
atlas14_depths = [2.5, 3.1, 3.8, 4.5, 5.2, 6.0]
HmsMet.update_tp40_to_atlas14(
    "model.met",
    atlas14_depths=atlas14_depths
)
```

## Key Operations

- **Precipitation methods** - `get_precipitation_method()`, `set_precipitation_method()`
- **Gage assignments** - `get_gage_assignments()`, `set_gage_assignment()`
- **Frequency storms** - `get_frequency_storm_params()`, `set_precipitation_depths()`
- **Clone workflow** - `clone_met()` for QAQC comparisons

## Atlas 14 Updates

HMS Commander includes specialized support for updating precipitation from TP-40 to NOAA Atlas 14:

```python
# Get current depths
depths = HmsMet.get_precipitation_depths("model.met")

# Update to Atlas 14 (from API or manual entry)
HmsMet.update_tp40_to_atlas14("model.met", new_depths)
```

## Related Topics

- [API Reference: HmsMet](../api/hms_met.md) - Complete method documentation
- [Atlas 14 Updates](atlas14_updates.md) - Precipitation frequency updates
- [Time-Series Gages](gages.md) - Gage file management
- [Data Formats: Met File](../data_formats/met_file.md) - HMS .met file format

---

*For complete API documentation, see [HmsMet API Reference](../api/hms_met.md)*
