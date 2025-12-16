# Atlas 14 Updates

Update precipitation frequency estimates from TP-40 to NOAA Atlas 14.

## Overview

HMS Commander includes specialized support for updating precipitation depth-area-duration (DAD) data from the legacy TP-40 Technical Paper to modern NOAA Atlas 14 estimates.

## Background

**TP-40 (1961):** Legacy rainfall frequency atlas
**NOAA Atlas 14 (2000s):** Modern precipitation frequency estimates with improved data and analysis methods

**Why Update?**
- More recent rainfall data (through ~2015)
- Improved statistical methods
- Higher spatial resolution
- Better captures extreme events

## Quick Examples

### Get Current Precipitation Depths

```python
from hms_commander import HmsMet

# Read current frequency storm depths
depths = HmsMet.get_precipitation_depths("model.met")
print(depths)  # Current values (likely TP-40)
```

### Update to Atlas 14

```python
# Atlas 14 depths from NOAA website or API
atlas14_depths = [2.5, 3.1, 3.8, 4.5, 5.2, 6.0]

# Update met model
HmsMet.update_tp40_to_atlas14(
    met_path="model.met",
    atlas14_depths=atlas14_depths
)
```

### Get Frequency Storm Parameters

```python
# Get all frequency storm configuration
params = HmsMet.get_frequency_storm_params("model.met")
print(params)
# Shows: storm durations, distributions, depths, etc.
```

## Complete Atlas 14 Workflow

### Step 1: Get Project Centroid

```python
from hms_commander import HmsGeo

# Calculate project center
lat, lon = HmsGeo.get_project_centroid_latlon(
    geo_path="project.geo",
    crs_epsg="EPSG:2278"  # Your project CRS
)
print(f"Project center: {lat:.4f}°N, {abs(lon):.4f}°W")
```

### Step 2: Download Atlas 14 Data

```python
# Option A: Use NOAA Atlas 14 API (requires external package)
from noaa_atlas14 import Downloader

downloader = Downloader()
data = downloader.download_from_coordinates(lat, lon)
atlas14_depths = data['precipitation_depths']  # Extract depths

# Option B: Manual entry from NOAA website
# Visit: https://hdsc.nws.noaa.gov/pfds/
# Enter coordinates, select durations, copy depths
atlas14_depths = [2.5, 3.1, 3.8, 4.5, 5.2, 6.0]  # inches
```

### Step 3: Clone Met Model for Comparison

```python
# Non-destructive update using clone workflow
HmsMet.clone_met(
    template="TP40_Met",
    new_name="Atlas14_Met",
    description="Updated with NOAA Atlas 14 precipitation"
)

# Update clone with new depths
HmsMet.update_tp40_to_atlas14(
    met_path="Atlas14_Met.met",
    atlas14_depths=atlas14_depths
)
```

### Step 4: Create Comparison Run

```python
from hms_commander import HmsRun

# Side-by-side comparison run
HmsRun.clone_run(
    source_run="TP40_Run",
    new_run_name="Atlas14_Run",
    new_met="Atlas14_Met",
    output_dss="atlas14_results.dss",
    description="NOAA Atlas 14 precipitation comparison"
)
```

### Step 5: Execute and Compare

```python
from hms_commander import HmsCmdr, HmsResults

# Run both simulations
HmsCmdr.compute_parallel(["TP40_Run", "Atlas14_Run"])

# Compare peak flows
comparison = HmsResults.compare_runs(
    dss_files=["tp40_results.dss", "atlas14_results.dss"],
    element="Outlet"
)
print(comparison)
```

## Depth Format

Atlas 14 depths should be provided as a list in inches, ordered by duration:

```python
# Example for 6 durations
atlas14_depths = [
    2.5,  # Duration 1 (e.g., 6-hour)
    3.1,  # Duration 2 (e.g., 12-hour)
    3.8,  # Duration 3 (e.g., 24-hour)
    4.5,  # Duration 4 (e.g., 2-day)
    5.2,  # Duration 5 (e.g., 3-day)
    6.0   # Duration 6 (e.g., 4-day)
]
```

**Important:** Number of depths must match number of durations in the frequency storm configuration.

## NOAA Atlas 14 Resources

- **NOAA Precipitation Frequency Data Server:** https://hdsc.nws.noaa.gov/pfds/
- **Documentation:** https://www.weather.gov/owp/hdsc_about
- **Coverage:** Varies by region (check NOAA website for your location)

## Regional Coverage

- **Semiarid Southwest:** Volume 1
- **Ohio River Basin:** Volume 2
- **Puerto Rico:** Volume 3
- **Hawaiian Islands:** Volume 4
- **Selected Pacific Islands:** Volume 5
- **California:** Volume 6
- **Alaska:** Volume 7
- **Midwestern States:** Volume 8
- **Southeastern States:** Volume 9
- **Northeastern States:** Volume 10
- **Texas:** Volume 11

## Comparison Analysis

After running both models:

```python
# Extract peak flows
tp40_peaks = HmsResults.get_peak_flows("tp40_results.dss")
atlas14_peaks = HmsResults.get_peak_flows("atlas14_results.dss")

# Calculate percent increase
for element in tp40_peaks['element']:
    tp40_peak = tp40_peaks.loc[tp40_peaks['element'] == element, 'peak_flow'].values[0]
    atlas14_peak = atlas14_peaks.loc[atlas14_peaks['element'] == element, 'peak_flow'].values[0]

    pct_increase = ((atlas14_peak - tp40_peak) / tp40_peak) * 100

    print(f"{element}:")
    print(f"  TP-40:     {tp40_peak:,.0f} CFS")
    print(f"  Atlas 14:  {atlas14_peak:,.0f} CFS")
    print(f"  Increase:  {pct_increase:.1f}%")
    print()
```

## Related Topics

- [API Reference: HmsMet](../api/hms_met.md) - Precipitation methods
- [API Reference: HmsGeo](../api/hms_geo.md) - Centroid calculation
- [Meteorologic Models](meteorologic_models.md) - Met file operations
- [Clone Workflows](clone_workflows.md) - Non-destructive comparison
- [Geospatial Operations](geospatial.md) - Project centroid

---

*For complete API documentation, see [HmsMet API Reference](../api/hms_met.md)*
