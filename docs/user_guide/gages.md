# Time-Series Gages

Creating and managing precipitation and discharge gages in HEC-HMS (.gage files).

## Overview

The `HmsGage` class provides methods for working with time-series gage files, which link HMS models to DSS time-series data.

## Quick Examples

### List Gages

```python
from hms_commander import HmsGage

# Get all gages
gages_df = HmsGage.get_gages("gages.gage")
print(gages_df)

# List by type
precip_gages = HmsGage.list_precip_gages("gages.gage")
discharge_gages = HmsGage.list_discharge_gages("gages.gage")
```

### Get Gage Information

```python
# Get specific gage details
gage_info = HmsGage.get_gage_info("Gage1", "gages.gage")
print(gage_info)
```

### Create New Gage

```python
# Create precipitation gage
HmsGage.create_gage(
    path="gages.gage",
    name="Precip_Gage_1",
    dss_file="timeseries.dss",
    pathname="/BASIN/LOCATION/PRECIP/01JAN2020/1HOUR/OBS/"
)
```

### Update Gage DSS Reference

```python
# Update DSS file reference
HmsGage.update_gage(
    "gages.gage",
    name="Precip_Gage_1",
    dss_file="updated_data.dss"
)
```

## DSS Pathname Format

HMS gages reference DSS data using standard pathnames:
```
/A-Part/B-Part/C-Part/D-Part/E-Part/F-Part/
```

Example:
```
/BASIN/SUBBASIN1/PRECIP/01JAN2020/15MIN/OBS/
```

## Key Operations

- **List gages** - `get_gages()`, `list_precip_gages()`, `list_discharge_gages()`
- **Get details** - `get_gage_info()`
- **Create/modify** - `create_gage()`, `update_gage()`
- **Delete** - `delete_gage()`

## Related Topics

- [API Reference: HmsGage](../api/hms_gage.md) - Complete method documentation
- [DSS Operations](dss_operations.md) - Working with DSS files
- [Meteorologic Models](meteorologic_models.md) - Gage assignments
- [Data Formats: Gage File](../data_formats/gage_file.md) - HMS .gage file format

---

*For complete API documentation, see [HmsGage API Reference](../api/hms_gage.md)*
