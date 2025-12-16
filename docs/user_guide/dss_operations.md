# DSS Operations

Read and write DSS files for time-series data and simulation results.

## Overview

The `HmsDss` class provides methods for working with HEC-DSS (Data Storage System) files, which HMS uses for time-series input data and simulation results.

!!! note "Requires RAS Commander"
    DSS operations require the `ras-commander` package, which provides the `RasDss` interface.
    ```bash
    pip install hms-commander[dss]
    ```

## Quick Examples

### Check DSS Availability

```python
from hms_commander import HmsDss

# Verify DSS support is available
if HmsDss.is_available():
    print("DSS operations available")
else:
    print("Install: pip install hms-commander[dss]")
```

### Read Time-Series Data

```python
# Read precipitation time series
data = HmsDss.read_timeseries(
    dss_file="input.dss",
    pathname="/BASIN/GAGE1/PRECIP/01JAN2020/15MIN/OBS/"
)
print(data)  # Returns pandas DataFrame
```

### Get Catalog

```python
# List all paths in DSS file
catalog = HmsDss.get_catalog("results.dss")
for path in catalog:
    print(path)
```

### Extract HMS Results

```python
# Extract all flow results
flows = HmsDss.extract_hms_results(
    dss_file="results.dss",
    result_type="flow"
)

# List available results
flow_paths = HmsDss.list_flow_results("results.dss")
precip_paths = HmsDss.list_precipitation_data("results.dss")
```

### Write Time-Series

```python
import pandas as pd

# Create time series
data = pd.DataFrame({
    'datetime': pd.date_range('2020-01-01', periods=24, freq='H'),
    'value': [1.0, 1.2, 0.8, ...]
})

# Write to DSS
HmsDss.write_timeseries(
    dss_file="output.dss",
    pathname="/BASIN/LOCATION/FLOW/01JAN2020/1HOUR/SIMULATED/",
    data=data,
    units="CFS"
)
```

## DSS Pathname Structure

DSS uses a 6-part pathname:
```
/A-Part/B-Part/C-Part/D-Part/E-Part/F-Part/
```

**Example:** `/BASIN/SUBBASIN1/PRECIP/01JAN2020/15MIN/OBS/`

- **A-Part:** Basin/watershed
- **B-Part:** Location (subbasin, junction, reach)
- **C-Part:** Parameter (PRECIP, FLOW, STAGE)
- **D-Part:** Start date
- **E-Part:** Time interval
- **F-Part:** Version (OBS, SIMULATED)

## Pathname Utilities

```python
# Parse pathname into components
parts = HmsDss.parse_dss_pathname(
    "/BASIN/SUB1/FLOW/01JAN2020/15MIN/SIM/"
)
print(parts)

# Create pathname from components
path = HmsDss.create_dss_pathname(
    basin="MYBASIN",
    element="OUTLET",
    param_type="FLOW",
    interval="1HOUR"
)
```

## Key Operations

- **Read/Write** - `read_timeseries()`, `write_timeseries()`
- **Catalog** - `get_catalog()`, `list_flow_results()`, `list_precipitation_data()`
- **Extract** - `extract_hms_results()`
- **Pathname** - `parse_dss_pathname()`, `create_dss_pathname()`

## Related Topics

- [API Reference: HmsDss](../api/hms_dss.md) - Complete method documentation
- [Results Analysis](results_analysis.md) - Processing HMS results
- [Time-Series Gages](gages.md) - Linking DSS data to models
- [Data Formats: DSS Integration](../data_formats/dss_integration.md) - DSS file format

---

*For complete API documentation, see [HmsDss API Reference](../api/hms_dss.md)*
