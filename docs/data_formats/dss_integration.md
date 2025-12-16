# DSS Integration

## Overview

DSS (Data Storage System) is HEC's standard binary format for storing time-series hydrologic data. HEC-HMS uses DSS files for both input data (precipitation, flow) and output results (hydrographs, volumes). The `HmsDss` and `HmsResults` classes provide programmatic access to DSS data.

## DSS File Purpose

DSS files serve several critical functions in HMS workflows:

- **Input Data**: Store precipitation, discharge, stage, and meteorologic data
- **Simulation Results**: Store computed hydrographs, volumes, and statistics
- **Long-term Storage**: Efficient binary format for large time-series datasets
- **Cross-platform**: Consistent format across HEC software (HMS, RAS, ResSim)

## DSS Pathname Structure

DSS organizes data using 6-part pathnames:

```
/A-Part/B-Part/C-Part/D-Part/E-Part/F-Part/
```

### Pathname Parts

| Part | Purpose | HMS Examples |
|------|---------|--------------|
| **A** | Project/Basin | MYBASIN, WATERSHED, PROJECT |
| **B** | Location | SUB1, OUTLET, JUNCTION1, GAGE1 |
| **C** | Parameter | PRECIP-INC, FLOW, STAGE, VOLUME-INC |
| **D** | Start Date | 01JAN2020, 15AUG2023, blank |
| **E** | Interval | 15MIN, 1HOUR, 1DAY |
| **F** | Version | OBS, CALC, SIM, v1, v2 |

### Example Pathnames

**Precipitation Input**:
```
/URBAN_BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/
```

**Flow Output**:
```
/URBAN_BASIN/OUTLET/FLOW/01JAN2020/15MIN/RUN:BASELINE_100YR/
```

**Volume Output**:
```
/URBAN_BASIN/SUB1/VOLUME-INC/01JAN2020/15MIN/RUN:BASELINE_100YR/
```

## Input vs. Output DSS Files

### Input DSS Files (Gage Data)

Referenced in `.gage` file:

```
Gage: PrecipGage1
     Type: Precipitation
     DSS File: input/precipitation.dss
     DSS Pathname: /BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/
End:
```

**Common Input Parameters**:
- `PRECIP-INC` - Incremental precipitation (inches or mm)
- `PRECIP-CUM` - Cumulative precipitation
- `FLOW` - Discharge (cfs or cms)
- `STAGE` - Water surface elevation (ft or m)
- `TEMP` - Temperature (°F or °C)

### Output DSS Files (Results)

Specified in `.run` file:

```
Run: Baseline_100yr
     Basin: ExistingConditions
     Meteorology: 100-Year Storm
     Control: 24-Hour Event
     DSS File: output/baseline_100yr.dss
End:
```

**Common Output Parameters**:
- `FLOW` - Computed discharge
- `VOLUME-INC` - Incremental volume
- `VOLUME-CUM` - Cumulative volume
- `PRECIP-INC` - Applied precipitation
- `PRECIP-LOSS` - Infiltration losses

## Working with DSS Files

### Check DSS Availability

```python
from hms_commander import HmsDss

# Check if DSS functionality is available
if HmsDss.is_available():
    print("DSS support available via ras-commander")
else:
    print("DSS support not available - install ras-commander")
```

**Note**: DSS operations require `ras-commander` package, which provides `RasDss` functionality via `pyjnius`.

### Installation

```bash
# Install with DSS support
pip install hms-commander[dss]

# Or install dependencies separately
pip install ras-commander
```

### Reading DSS Catalog

```python
# List all pathnames in DSS file
catalog = HmsDss.get_catalog("results.dss")

for pathname in catalog:
    print(pathname)
# /BASIN/OUTLET/FLOW/01JAN2020/15MIN/RUN:BASELINE/
# /BASIN/SUB1/PRECIP-INC/01JAN2020/15MIN/RUN:BASELINE/
# ...
```

### Reading Time-Series Data

```python
# Read time-series as pandas DataFrame
df = HmsDss.read_timeseries(
    dss_file="results.dss",
    pathname="/BASIN/OUTLET/FLOW/01JAN2020/15MIN/RUN:BASELINE/"
)

print(df)
#                      Value
# DateTime
# 2020-01-01 00:00:00    5.2
# 2020-01-01 00:15:00    7.8
# 2020-01-01 00:30:00   12.4
# ...
```

### Writing Time-Series Data

```python
import pandas as pd

# Create time-series data
dates = pd.date_range(start='2020-01-01', periods=96, freq='15min')
values = [0.1, 0.2, 0.5, ...]  # 96 precipitation values
df = pd.DataFrame({'Value': values}, index=dates)

# Write to DSS
HmsDss.write_timeseries(
    dss_file="input/precip.dss",
    pathname="/BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/OBS/",
    data=df,
    units="IN"
)
```

### Parsing DSS Pathnames

```python
# Parse pathname into dictionary
pathname = "/BASIN/OUTLET/FLOW/01JAN2020/15MIN/RUN:BASELINE/"
parts = HmsDss.parse_dss_pathname(pathname)

print(parts)
# {
#     'A': 'BASIN',
#     'B': 'OUTLET',
#     'C': 'FLOW',
#     'D': '01JAN2020',
#     'E': '15MIN',
#     'F': 'RUN:BASELINE'
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

## Extracting Results

### Results Class Overview

`HmsResults` provides high-level access to simulation outputs:

```python
from hms_commander import HmsResults
```

### Peak Flows

```python
# Get peak flows for all elements
peaks = HmsResults.get_peak_flows("results.dss")

print(peaks)
#    Element    Peak Flow (cfs)  Time to Peak
# 0  Sub1              145.8     01Jan2020 14:30
# 1  Junction1         312.4     01Jan2020 15:00
# 2  Outlet            298.5     01Jan2020 15:45
```

### Volume Summary

```python
# Get volume summary
volumes = HmsResults.get_volume_summary("results.dss")

print(volumes)
#    Element  Precipitation (ac-ft)  Runoff (ac-ft)  Loss (ac-ft)
# 0  Sub1                 234.5           156.3         78.2
# 1  Sub2                 189.2           121.8         67.4
```

### Outflow Time-Series

```python
# Get hydrograph for specific element
hydrograph = HmsResults.get_outflow_timeseries("results.dss", "Outlet")

print(hydrograph)
#                      Flow (cfs)
# DateTime
# 2020-01-01 00:00:00         5.2
# 2020-01-01 00:15:00         7.8
# 2020-01-01 00:30:00        12.4
# ...
```

### Precipitation Time-Series

```python
# Get applied precipitation for element
precip = HmsResults.get_precipitation_timeseries("results.dss", "Sub1")

print(precip)
#                      Precip (in)
# DateTime
# 2020-01-01 00:00:00       0.00
# 2020-01-01 00:15:00       0.05
# 2020-01-01 00:30:00       0.12
# ...
```

### Hydrograph Statistics

```python
# Get statistical summary for element
stats = HmsResults.get_hydrograph_statistics("results.dss", "Outlet")

print(stats)
# {
#     'peak_flow': 298.5,
#     'time_to_peak': datetime(2020, 1, 1, 15, 45),
#     'total_volume': 156.3,
#     'mean_flow': 42.1,
#     'duration': 24.0
# }
```

### Comparing Multiple Runs

```python
# Compare results from multiple DSS files
comparison = HmsResults.compare_runs(
    dss_files=[
        "baseline.dss",
        "alternative_a.dss",
        "alternative_b.dss"
    ],
    element="Outlet"
)

print(comparison)
#    Run              Peak Flow  Volume  Time to Peak
# 0  baseline             298.5   156.3  15:45
# 1  alternative_a        245.2   156.3  16:15
# 2  alternative_b        212.8   156.3  16:45
```

### Export to CSV

```python
# Export all results to CSV files
HmsResults.export_results_to_csv(
    dss_file="results.dss",
    output_folder="csv_output"
)

# Creates:
# - csv_output/peak_flows.csv
# - csv_output/volumes.csv
# - csv_output/outlet_hydrograph.csv
# - csv_output/sub1_hydrograph.csv
# ...
```

## Complete Workflow Example

### Input Data Preparation

```python
from hms_commander import HmsDss
import pandas as pd

# Create 24-hour precipitation hyetograph
dates = pd.date_range(start='2020-01-01', periods=96, freq='15min')

# Example: SCS Type III distribution
precip_values = [...]  # 96 incremental values

precip_df = pd.DataFrame({'Value': precip_values}, index=dates)

# Write to DSS for input
HmsDss.write_timeseries(
    dss_file="input/design_storm.dss",
    pathname="/BASIN/GAGE1/PRECIP-INC/01JAN2020/15MIN/ATLAS14/",
    data=precip_df,
    units="IN"
)
```

### Run Simulation

```python
from hms_commander import init_hms_project, HmsCmdr

# Initialize and run
init_hms_project(r"C:\Projects\MyBasin")
HmsCmdr.compute_run("Baseline_100yr")
```

### Extract and Analyze Results

```python
from hms_commander import HmsResults

dss_file = "output/baseline_100yr.dss"

# Get peak flows
peaks = HmsResults.get_peak_flows(dss_file)
outlet_peak = peaks[peaks['Element'] == 'Outlet']['Peak Flow (cfs)'].values[0]
print(f"Outlet peak flow: {outlet_peak:.1f} cfs")

# Get full hydrograph
hydrograph = HmsResults.get_outflow_timeseries(dss_file, "Outlet")

# Plot results
import matplotlib.pyplot as plt
hydrograph.plot()
plt.title("Outlet Hydrograph - 100-Year Storm")
plt.xlabel("Time")
plt.ylabel("Flow (cfs)")
plt.savefig("hydrograph.png")
```

### Compare Scenarios

```python
# Compare baseline vs. alternative
baseline_peak = HmsResults.get_peak_flows("baseline.dss")
alternative_peak = HmsResults.get_peak_flows("alternative_a.dss")

# Calculate reduction
baseline_q = baseline_peak[baseline_peak['Element']=='Outlet']['Peak Flow (cfs)'].values[0]
alternative_q = alternative_peak[alternative_peak['Element']=='Outlet']['Peak Flow (cfs)'].values[0]
reduction = ((baseline_q - alternative_q) / baseline_q) * 100

print(f"Baseline: {baseline_q:.1f} cfs")
print(f"Alternative: {alternative_q:.1f} cfs")
print(f"Reduction: {reduction:.1f}%")
```

## DSS File Organization

### Simple Project

```
MyProject/
├── MyProject.hms
├── input/
│   └── precip.dss
└── output/
    ├── baseline_10yr.dss
    ├── baseline_100yr.dss
    └── baseline_500yr.dss
```

### Complex Project

```
MyProject/
├── MyProject.hms
├── data/
│   ├── observed/
│   │   ├── precipitation.dss
│   │   └── streamflow.dss
│   └── design/
│       └── atlas14_storms.dss
└── results/
    ├── calibration/
    │   ├── event1.dss
    │   └── event2.dss
    ├── existing/
    │   ├── existing_10yr.dss
    │   └── existing_100yr.dss
    └── alternatives/
        ├── alt_a_100yr.dss
        └── alt_b_100yr.dss
```

## Common DSS Parameters

### Precipitation Parameters

| Parameter | Description | Units |
|-----------|-------------|-------|
| PRECIP-INC | Incremental precipitation | IN, MM |
| PRECIP-CUM | Cumulative precipitation | IN, MM |
| PRECIP-LOSS | Infiltration loss | IN, MM |

### Flow Parameters

| Parameter | Description | Units |
|-----------|-------------|-------|
| FLOW | Discharge | CFS, CMS |
| VOLUME-INC | Incremental volume | AC-FT, M3 |
| VOLUME-CUM | Cumulative volume | AC-FT, M3 |

### Other Parameters

| Parameter | Description | Units |
|-----------|-------------|-------|
| STAGE | Water surface elevation | FT, M |
| STORAGE | Reservoir storage | AC-FT, M3 |
| ELEVATION | Pool elevation | FT, M |

## Time Intervals

Common DSS time intervals:

| Interval | E-Part | Description |
|----------|--------|-------------|
| 1 minute | 1MIN | High resolution |
| 5 minutes | 5MIN | Urban watersheds |
| 15 minutes | 15MIN | Standard design storms |
| 30 minutes | 30MIN | Medium watersheds |
| 1 hour | 1HOUR | Large watersheds |
| 1 day | 1DAY | Daily water balance |

## Best Practices

1. **Organize by scenario**: Use separate DSS files for each run
2. **Version F-part**: Use meaningful version strings (OBS, CALC, RUN:name)
3. **Consistent naming**: Use systematic pathname structure
4. **Document units**: Always specify units when writing data
5. **Backup results**: DSS files can be large; backup important results
6. **Check catalog**: Verify pathnames before reading data

## Common Pitfalls

- **Wrong parameter type**: Use PRECIP-INC (incremental) not PRECIP-CUM for HMS input
- **Case sensitivity**: DSS pathnames are case-sensitive
- **Missing units**: Always specify units when writing
- **Interval mismatch**: Ensure DSS interval matches HMS computational interval
- **Date format**: D-part uses format like "01JAN2020" (no spaces)
- **Trailing slashes**: Always include trailing slash in pathname
- **F-part conflicts**: Same A-F parts except F will overwrite

## Performance Considerations

### Large DSS Files

DSS files can become very large for:
- Long continuous simulations
- Many elements
- Small time intervals
- Multiple versions

**Tips**:
- Use appropriate time intervals
- Archive old versions
- Split by scenario
- Compress archived files

### Reading Speed

```python
# Fast: Read specific pathname
df = HmsDss.read_timeseries(dss_file, pathname)

# Slower: Get catalog then read many paths
catalog = HmsDss.get_catalog(dss_file)
for path in catalog:
    df = HmsDss.read_timeseries(dss_file, path)
```

## Troubleshooting

### DSS Not Available

```python
if not HmsDss.is_available():
    print("Install ras-commander for DSS support:")
    print("  pip install ras-commander")
```

### Java Errors

DSS operations use Java via `pyjnius`. If you encounter Java errors:

```bash
# Ensure Java is installed
java -version

# Reinstall ras-commander
pip uninstall ras-commander
pip install ras-commander
```

### Pathname Not Found

```python
# List all pathnames to verify
catalog = HmsDss.get_catalog("results.dss")
print("\n".join(catalog))

# Check exact spelling and case
```

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Gage File Format](gage_file.md) - DSS references for input data
- [Run File Format](run_file.md) - DSS file specification for output
- [Met File Format](met_file.md) - Meteorologic data and DSS integration

## API Reference

**Primary Classes**: `HmsDss`, `HmsResults`

**HmsDss Methods**:
- `HmsDss.is_available()` - Check if DSS support is available
- `HmsDss.get_catalog()` - List all DSS pathnames
- `HmsDss.read_timeseries()` - Read time-series data
- `HmsDss.write_timeseries()` - Write time-series data
- `HmsDss.parse_dss_pathname()` - Parse pathname components
- `HmsDss.create_dss_pathname()` - Build pathname from parts
- `HmsDss.list_flow_results()` - List flow output pathnames
- `HmsDss.list_precipitation_data()` - List precipitation pathnames

**HmsResults Methods**:
- `HmsResults.get_peak_flows()` - Extract peak flows
- `HmsResults.get_volume_summary()` - Extract volumes
- `HmsResults.get_outflow_timeseries()` - Get hydrograph
- `HmsResults.get_precipitation_timeseries()` - Get precipitation
- `HmsResults.get_hydrograph_statistics()` - Calculate statistics
- `HmsResults.compare_runs()` - Compare multiple scenarios
- `HmsResults.export_results_to_csv()` - Export to CSV

**Dependencies**:
- Requires: `pip install ras-commander` (includes `pyjnius` for Java/DSS access)
- Or install all: `pip install hms-commander[dss]`

See [CLAUDE.md](../../CLAUDE.md) for complete API documentation.
