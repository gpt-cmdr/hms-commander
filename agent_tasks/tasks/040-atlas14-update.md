# Task 040: Update Met Model from TP40 to Atlas 14

**Created**: 2025-12-17
**Template**: feature.md
**Status**: Reusable

---

## Goal

Update HMS meteorologic model precipitation depths from TP40 to Atlas 14 using NOAA data.

**Uses**: Clone workflow for non-destructive QAQC comparison

---

## Prerequisites

- hms-commander installed
- HMS project with TP40 precipitation
- Atlas 14 data for project location (lat/lon or station)

---

## Workflow Overview

```
1. Clone baseline met model
2. Update precipitation depths (Atlas 14)
3. Clone baseline run with new met
4. Execute both runs
5. Compare results
```

---

## Steps

### 1. Initialize Project and Clone Met Model

```python
from hms_commander import init_hms_project, HmsMet

# Initialize
hms = init_hms_project("path/to/project")

# Clone met model for QAQC
HmsMet.clone_met(
    met_file="project.met",
    source_name="BaseMet",
    new_name="BaseMet_Atlas14",
    hms_object=hms
)
```

### 2. Get Atlas 14 Precipitation Depths

**Option A: Use NOAA Atlas 14 website**
1. Visit: https://hdsc.nws.noaa.gov/pfds/
2. Enter project lat/lon
3. Select return periods (2-yr, 5-yr, 10-yr, 25-yr, 50-yr, 100-yr, 500-yr)
4. Select durations (6-hr, 12-hr, 24-hr)
5. Export data

**Option B: Use ras-commander Atlas14Downloader (if available)**
```python
from ras_commander import Atlas14Downloader

depths = Atlas14Downloader.get_depths(
    latitude=35.5,
    longitude=-85.2,
    return_periods=[2, 5, 10, 25, 50, 100, 500],
    durations=[6, 12, 24]
)
```

### 3. Update Precipitation Depths

```python
# Update each frequency storm
HmsMet.set_frequency_storm_depth(
    met_file="project.met",
    met_name="BaseMet_Atlas14",
    frequency="100-Year",
    duration="24-Hour",
    depth=8.5,  # Atlas 14 value in inches
    hms_object=hms
)

# Repeat for all frequencies and durations
```

### 4. Clone Run with New Met

```python
from hms_commander import HmsRun

HmsRun.clone_run(
    run_file="project.run",
    source_name="BaseRun",
    new_name="BaseRun_Atlas14",
    hms_object=hms
)

# Link new met to new run
HmsRun.set_met_model(
    run_file="project.run",
    run_name="BaseRun_Atlas14",
    met_name="BaseMet_Atlas14",
    hms_object=hms
)
```

### 5. Execute Both Runs

```python
from hms_commander import HmsCmdr

# Execute baseline
HmsCmdr.compute_run("BaseRun")

# Execute Atlas 14
HmsCmdr.compute_run("BaseRun_Atlas14")
```

### 6. Compare Results

```python
from hms_commander import HmsResults

# Extract peak flows
baseline_dss = hms.run_df.loc["BaseRun", "dss_file"]
atlas14_dss = hms.run_df.loc["BaseRun_Atlas14", "dss_file"]

baseline_peaks = HmsResults.get_peak_flows(baseline_dss)
atlas14_peaks = HmsResults.get_peak_flows(atlas14_dss)

# Compare
comparison = baseline_peaks.merge(
    atlas14_peaks,
    on="Element",
    suffixes=("_TP40", "_Atlas14")
)

comparison["Percent_Change"] = (
    (comparison["Peak Flow (cfs)_Atlas14"] - comparison["Peak Flow (cfs)_TP40"])
    / comparison["Peak Flow (cfs)_TP40"]
    * 100
)

print(comparison[["Element", "Peak Flow (cfs)_TP40", "Peak Flow (cfs)_Atlas14", "Percent_Change"]])
```

---

## Acceptance Criteria

- [x] Met model cloned successfully
- [x] All frequency storms updated with Atlas 14 depths
- [x] Run cloned and linked to new met
- [x] Both runs executed successfully
- [x] Results compared and documented
- [x] QAQC comparison available in HMS GUI

---

## Validation

### Check in HMS GUI

1. Open project in HMS GUI
2. Components > Meteorologic Models
3. Select `BaseMet_Atlas14`
4. View frequency storms
5. Verify depths match Atlas 14 data

### Side-by-Side Run Comparison

1. Components > Compute > Run Manager
2. Select both runs
3. View Results > Summary Table
4. Compare peak flows, volumes, timing

---

## Troubleshooting

### Depths not updating

**Check**: HMS version and parameter names

```python
# Verify parameter name
met_data = HmsMet.get_frequency_storm("project.met", "BaseMet_Atlas14", "100-Year", "24-Hour")
print(met_data)
```

### Run not using new met model

**Check**: Run configuration

```python
run_data = hms.run_df.loc["BaseRun_Atlas14"]
print(f"Met model: {run_data['met']}")
# Should show: BaseMet_Atlas14
```

---

## Related Tasks

- **020-run-simulation.md**: Execute HMS workflow
- **050-version-upgrade.md**: Upgrade to HMS 4.x (if on 3.x)

---

## Related Skills

**Skills activated**:
- `updating-met-models` - Meteorologic model operations
- `cloning-hms-components` - Non-destructive QAQC workflow
- `executing-hms-runs` - Run execution

**Subagents**:
- `met-model-specialist` - Met model expertise
- `run-manager-specialist` - Run configuration
- `dss-integration-specialist` - Results comparison

---

## Notes

**Atlas 14 vs TP40**:
- Atlas 14 generally shows 10-30% increase in depths
- Greatest increases in Southeast US
- Use appropriate Atlas 14 region (Volume 2, Volume 9, etc.)

**Documentation**:
Document Atlas 14 source:
- NOAA Atlas 14 Volume [X]
- Station ID or lat/lon
- Date retrieved
- Return periods and durations used
