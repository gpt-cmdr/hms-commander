# Results Analysis

Extract peak flows, volumes, hydrograph statistics, and compare multiple runs.

## Overview

The `HmsResults` class provides methods for analyzing HEC-HMS simulation results stored in DSS files.

## Quick Examples

### Get Peak Flows

```python
from hms_commander import HmsResults

# Extract peak flow summary
peaks = HmsResults.get_peak_flows("results.dss")
print(peaks)
```

### Get Volume Summary

```python
# Get volumes in acre-feet
volumes = HmsResults.get_volume_summary("results.dss")
print(volumes)
```

### Get Hydrograph Time Series

```python
# Extract outflow hydrograph
hydrograph = HmsResults.get_outflow_timeseries(
    dss_file="results.dss",
    element="Outlet"
)
print(hydrograph)  # pandas DataFrame
```

### Compare Multiple Runs

```python
# Side-by-side comparison
comparison = HmsResults.compare_runs(
    dss_files=["baseline.dss", "calibrated.dss"],
    element="Outlet"
)
print(comparison)
```

### Hydrograph Statistics

```python
# Get detailed statistics
stats = HmsResults.get_hydrograph_statistics(
    dss_file="results.dss",
    element="Outlet"
)
print(f"Peak: {stats['peak_flow']} CFS")
print(f"Time to peak: {stats['time_to_peak']}")
print(f"Total volume: {stats['volume']} ac-ft")
```

## Precipitation Analysis

```python
# Get precipitation summary
precip = HmsResults.get_precipitation_summary("results.dss")
print(precip)

# Extract precipitation time series
precip_ts = HmsResults.get_precipitation_timeseries(
    dss_file="results.dss",
    element="Subbasin1"
)
```

## Export Results

```python
# Export all results to CSV files
HmsResults.export_results_to_csv(
    dss_file="results.dss",
    output_folder="results_csv"
)
# Creates: peaks.csv, volumes.csv, hydrographs/*.csv
```

## Multi-Run Comparison Workflow

```python
# Compare baseline vs. calibrated
runs = {
    "Baseline": "baseline.dss",
    "Calibrated": "calibrated.dss",
    "Atlas14": "atlas14.dss"
}

for name, dss_file in runs.items():
    peaks = HmsResults.get_peak_flows(dss_file)
    print(f"\n{name}:")
    print(peaks)
```

## Typical Analysis Workflow

```python
# 1. Check simulation completed
peaks = HmsResults.get_peak_flows("results.dss")
if peaks.empty:
    print("No results found - check simulation")
else:
    # 2. Extract key metrics
    outlet_peak = peaks.loc[peaks['element'] == 'Outlet', 'peak_flow'].values[0]

    # 3. Get detailed hydrograph
    hydrograph = HmsResults.get_outflow_timeseries("results.dss", "Outlet")

    # 4. Plot (using matplotlib)
    import matplotlib.pyplot as plt
    hydrograph.plot(x='datetime', y='flow')
    plt.title(f'Outlet Hydrograph - Peak: {outlet_peak:.1f} CFS')
    plt.show()
```

## Key Operations

- **Peak flows** - `get_peak_flows()` - Summary table
- **Volumes** - `get_volume_summary()` - Total volumes
- **Time series** - `get_outflow_timeseries()`, `get_precipitation_timeseries()`
- **Statistics** - `get_hydrograph_statistics()` - Comprehensive metrics
- **Comparison** - `compare_runs()` - Multi-run analysis
- **Export** - `export_results_to_csv()` - CSV output

## Related Topics

- [API Reference: HmsResults](../api/hms_results.md) - Complete method documentation
- [DSS Operations](dss_operations.md) - Working with DSS files
- [Clone Workflows](clone_workflows.md) - QAQC comparison patterns
- [Execution](execution.md) - Running simulations

---

*For complete API documentation, see [HmsResults API Reference](../api/hms_results.md)*
