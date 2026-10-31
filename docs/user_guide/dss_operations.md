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

`write_timeseries` writes a regular-interval series, creating the file (DSS7, or DSS6
with `dss_version=6`) when it does not exist. Stamps are naive end-of-period times in
whole minutes; `NaN` is stored as HEC's missing value.

```python
import pandas as pd

times = pd.date_range("2020-01-01 01:00", periods=3, freq="h")

HmsDss.write_timeseries(
    dss_file="output.dss",
    pathname="/BASIN/LOCATION/FLOW//1HOUR/SIMULATED/",
    times=times,
    values=[10.0, 12.5, 11.0],
    units="CFS",
    data_type="INST-VAL",
)
```

### Choose a DSS backend

DSS calls use HEC Monolith (Java) by default. `HmsDss.backend = "native"` uses the
optional `ras_commander_fast_dss` engine without Java, and `"shadow"` compares both.
See [Native DSS Backend](dss_native_backend.md).

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

- **Read/Write** - `read_timeseries()`, `write_timeseries()`, `read_paired_data()`,
  `write_paired_data()`, `read_grid()`
- **File** - `get_file_version()`, `get_info()`
- **Backend** - `get_backend()`, `get_capabilities()`, `get_shadow_summary()`
- **Catalog** - `get_catalog()`, `list_flow_results()`, `list_precipitation_data()`
- **Extract** - `extract_hms_results()`
- **Pathname** - `parse_dss_pathname()`, `create_dss_pathname()`

## File Handles and Locks

Each `HmsDss`, `DssCore` and `HmsDssGrid` call closes the DSS file before it
returns, including when it raises. HEC-HMS or another program can write, rename
or delete the file as soon as the call returns, while the Python process and its
Java VM keep running.

HEC Monolith's `HecDss.done()` does not close the file by itself; it lowers a
shared reference count, and a background timer closes the file a few seconds
later. hms-commander therefore calls `HecDSSFileAccess.close(path, True)` with
the full absolute path it used to open the file. Code that calls the HEC
Monolith Java API directly through pyjnius needs the same call:

```python
from jnius import autoclass

HecDss = autoclass("hec.heclib.dss.HecDss")
HecDSSFileAccess = autoclass("hec.heclib.dss.HecDSSFileAccess")

path = r"C:\Projects\Basin\results.dss"  # full long path, not an 8.3 short name
dss = HecDss.open(path)
try:
    catalog = dss.getCatalogedPathnames()
finally:
    dss.done()
    HecDSSFileAccess.close(path, True)  # same string that was passed to open()
```

Other `HecDss` objects on the same file reopen it on their next access.

## Related Topics

- [API Reference: HmsDss](../api/hms_dss.md) - Complete method documentation
- [Native DSS Backend](dss_native_backend.md) - Java, native and shadow backends
- [Results Analysis](results_analysis.md) - Processing HMS results
- [Time-Series Gages](gages.md) - Linking DSS data to models
- [Data Formats: DSS Integration](../data_formats/dss_integration.md) - DSS file format

---

*For complete API documentation, see [HmsDss API Reference](../api/hms_dss.md)*
