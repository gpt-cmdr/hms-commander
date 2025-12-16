# HMS Atlas 14 Precipitation Update Agent

This agent automates the update of HEC-HMS projects from deprecated TP-40 precipitation frequency estimates to current NOAA Atlas 14 data.

## Overview

**Purpose:** Upgrade HEC-HMS models from TP-40 to Atlas 14 precipitation data while maintaining GUI-verifiable QAQC workflows for H&H engineer review.

**CLB Engineering LLM Forward Approach:**
- Non-destructive: Clones original models, preserves baseline
- Traceable: Comprehensive change logging (MODELING_LOG.md)
- GUI-verifiable: Side-by-side comparison in HEC-HMS GUI
- QAQC-able: Automated acceptance criteria validation
- Professional documentation: Client-deliverable quality reports

## Background

### Why Update to Atlas 14?

**TP-40 (Technical Paper 40)** - Published 1961, officially deprecated
- Last updated with data through the 1950s
- Does not reflect recent extreme precipitation events
- No longer supported by NOAA

**NOAA Atlas 14** - Current standard (2004-present)
- Based on modern statistical methods and recent data
- Includes confidence intervals (upper/lower bounds)
- Regional volumes available for most of the United States
- Required by many regulatory agencies (FEMA, state DOTs)

### Typical Magnitude Changes

Atlas 14 precipitation depths are typically **10-20% higher** than TP-40 for the same return period, though this varies by location:

| Region | Typical Change |
|--------|----------------|
| Gulf Coast (TX, LA, MS) | +15% to +25% |
| Southeast (GA, FL, SC) | +10% to +20% |
| Midwest (OH, IN, IL) | +5% to +15% |
| Northeast (NY, PA, NJ) | +10% to +20% |

**Example: Houston, TX (1% AEP, 24-hr)**
- TP-40: 13.0 inches
- Atlas 14: 14.5 inches (+11.5%)

## Prerequisites

### Software Requirements
- HEC-HMS 4.4.1+ (64-bit recommended)
- hms-commander v0.4.1+
- Python 3.10+
- Optional: ras-commander (for DSS comparison)

### Project Requirements
- Existing HMS project with TP-40 precipitation data
- Frequency-based hypothetical storm precipitation method
- Known project location (latitude/longitude)

### Knowledge Requirements
- Project location coordinates (for Atlas 14 API query)
- Desired AEP intervals (e.g., 10%, 4%, 2%, 1%, 0.5%, 0.2%)
- Storm durations (e.g., 6-hr, 12-hr, 24-hr)
- Whether to use upper/lower confidence intervals

## Workflow Steps

### Step 1: Backup and Initialize

```python
from hms_commander import init_hms_project, hms, HmsUtils
from pathlib import Path

# Backup original project
project_path = Path("C:/HMS_Projects/Tifton")
backup_path = HmsUtils.copy_project(project_path, project_path.parent / "Tifton_Backup")

# Initialize project
init_hms_project(project_path)

# Verify project structure
validation = HmsUtils.validate_project(project_path)
if not validation['valid']:
    print(f"Errors: {validation['errors']}")
```

### Step 2: Query Atlas 14 Data

```python
from hms_agents.HmsAtlas14 import Atlas14Downloader

# Project location (Tifton, GA)
lat = 31.4504
lon = -83.5285

# Download Atlas 14 data
downloader = Atlas14Downloader()
atlas14_data = downloader.download_from_coordinates(
    lat=lat,
    lon=lon,
    data='depth',      # Precipitation depth
    units='english',   # Inches
    series='pds'       # Partial duration series
)

# View available data
print(f"Return periods: {atlas14_data['return_periods']}")
print(f"Durations: {atlas14_data['durations']}")
print(f"1% AEP, 24-hr: {atlas14_data['depths']['1%']['24-hr']} inches")
```

**Atlas 14 API Response:**
- 10 return periods: 1, 2, 5, 10, 25, 50, 100, 200, 500, 1000 years
- Converted to AEP: 50%, 20%, 10%, 4%, 2%, 1%, 0.5%, 0.2%, 0.1%
- 19 standard durations: 5-min, 10-min, 15-min, 30-min, 60-min, 2-hr, 3-hr, 6-hr, 12-hr, 24-hr, etc.
- Upper/lower confidence intervals (90% confidence)

### Step 3: Clone Models for Comparison

Following the CLB Engineering LLM Forward Approach, we clone the original models to enable side-by-side GUI comparison:

```python
from hms_commander import HmsBasin, HmsMet, HmsRun

# Clone basin model (if needed for parameter updates)
HmsBasin.clone_basin(
    template_basin="Tifton",
    new_name="Tifton_Atlas14",
    description="Basin model for Atlas 14 precipitation update",
    hms_object=hms
)

# Clone meteorologic model
HmsMet.clone_met(
    template_met="Design_Storms_TP40",
    new_name="Design_Storms_Atlas14",
    description="Atlas 14 precipitation frequency estimates (NOAA 2023)",
    hms_object=hms
)

# Clone runs for each storm event
HmsRun.clone_run(
    source_run="100yr Storm - TP40",
    new_run_name="100yr Storm - Atlas14",
    new_basin="Tifton",  # Or "Tifton_Atlas14" if basin was modified
    new_met="Design_Storms_Atlas14",
    output_dss="results_100yr_atlas14.dss",
    description="1% AEP storm with Atlas 14 precipitation",
    hms_object=hms
)
```

**Result:**
- Engineer opens HEC-HMS GUI
- Sees both met models: "Design_Storms_TP40" and "Design_Storms_Atlas14"
- Sees both runs: "100yr Storm - TP40" and "100yr Storm - Atlas14"
- Can click between them to verify changes visually

### Step 4: Update Precipitation Depths

```python
from hms_commander import HmsMet
from hms_agents.HmsAtlas14 import Atlas14Converter

# Get existing TP-40 configuration
tp40_params = HmsMet.get_frequency_storm_params(
    met_path=hms.project_folder / "Design_Storms_TP40.met"
)

print(f"Total duration: {tp40_params['total_duration']} minutes")
print(f"Time interval: {tp40_params['time_interval']} minutes")
print(f"Number of depths: {len(tp40_params['depths'])}")

# Convert Atlas 14 data to HMS depth format
converter = Atlas14Converter()
atlas14_depths = converter.generate_depth_values(
    atlas14_data=atlas14_data,
    aep='1%',              # 100-year storm
    total_duration=1440,   # 24 hours in minutes
    time_interval=60,      # 1-hour intervals
    peak_position=50       # Peak at 50% (centered)
)

# Update cloned met model with Atlas 14 depths
result = HmsMet.update_tp40_to_atlas14(
    met_path=hms.project_folder / "Design_Storms_Atlas14.met",
    atlas14_depths=atlas14_depths
)

print(f"Average change: {result['avg_change_percent']:.1f}%")
print(f"24-hr depth: TP-40={result['old_depths'][-1]:.2f} in, "
      f"Atlas14={result['new_depths'][-1]:.2f} in")
```

### Step 5: Execute Baseline and Updated Runs

```python
from hms_commander import HmsCmdr

# Run baseline (TP-40)
print("Running baseline (TP-40)...")
HmsCmdr.compute_run("100yr Storm - TP40")

# Run updated (Atlas 14)
print("Running updated (Atlas 14)...")
HmsCmdr.compute_run("100yr Storm - Atlas14")

# Verify DSS outputs exist
outputs = HmsRun.verify_dss_outputs(hms_object=hms)
for run, info in outputs.items():
    status = "✓" if info['exists'] else "✗"
    print(f"{status} {run}: {info['dss_file']}")
```

### Step 6: Compare Results and Generate QAQC Report

```python
from hms_agents.HmsAtlas14 import ResultsComparator

# Compare DSS outputs
comparator = ResultsComparator()
comparison = comparator.compare_runs(
    baseline_dss=hms.project_folder / "results_100yr_tp40.dss",
    updated_dss=hms.project_folder / "results_100yr_atlas14.dss",
    acceptance_criteria={
        'peak_deviation_pct': 15.0,     # Max 15% peak flow increase
        'volume_deviation_pct': 15.0,   # Max 15% volume increase
        'timing_deviation_hrs': 0.5     # Max 30 min timing difference
    }
)

# Generate quality verdict
if comparison['verdict'] == 'GREEN':
    print("✓ Results within expected range for Atlas 14 update")
elif comparison['verdict'] == 'YELLOW':
    print("⚠ Results require engineer review")
else:
    print("✗ Results outside acceptable range - investigate")

# Export comparison report
comparator.export_report(
    comparison,
    output_path=hms.project_folder / "ATLAS14_COMPARISON_REPORT.md"
)
```

**Example Comparison Report:**

```markdown
## Results Comparison: TP-40 vs. Atlas 14

### Peak Flow Analysis
| Location | TP-40 Peak (cfs) | Atlas 14 Peak (cfs) | Difference | % Change |
|----------|------------------|---------------------|------------|----------|
| Outlet   | 2,450            | 2,680               | +230       | +9.4%    |
| Junc-1   | 1,820            | 1,950               | +130       | +7.1%    |

### Volume Analysis
| Location | TP-40 Volume (ac-ft) | Atlas 14 Volume (ac-ft) | Difference | % Change |
|----------|----------------------|-------------------------|------------|----------|
| Outlet   | 145                  | 158                     | +13        | +9.0%    |

### Quality Verdict: 🟢 GREEN
- Peak flow increase < 15% (acceptable for precip update)
- Volume increase consistent with precipitation change (+11.5%)
- Timing differences < 30 minutes (negligible)
- No errors or warnings in model execution

**Reviewer Notes:**
_Increases are within expected range for Atlas 14 update.
Recommend proceeding with updated model for design calculations._
```

### Step 7: Generate MODELING_LOG.md

```python
from hms_agents.HmsAtlas14 import ModelingLogger

# Document all changes
logger = ModelingLogger(project_path=hms.project_folder)

logger.log_change(
    category="Data Source Change",
    action="Replace TP-40 with NOAA Atlas 14 precipitation frequency estimates",
    file="Design_Storms_Atlas14.met",
    element="Precipitation Depths",
    old_value="TP-40: 13.0 inches (24-hr)",
    new_value="Atlas 14: 14.5 inches (24-hr)",
    justification="TP-40 deprecated; Atlas 14 is current NOAA standard",
    impact="+11.5% precipitation → higher runoff volumes expected",
    source="NOAA Atlas 14 Point Precipitation Frequency Estimates",
    location=f"{lat}°N, {lon}°W"
)

# Export comprehensive log
logger.export_modeling_log()
```

**Example MODELING_LOG.md:**

```markdown
# Modeling Change Log: TP-40 to Atlas 14 Update

## Project Information
- **Project:** Tifton Watershed Model
- **Location:** Tifton, GA (31.4504°N, 83.5285°W)
- **Date:** 2025-12-11
- **Engineer:** [Name]
- **Software:** HEC-HMS 4.11, hms-commander 0.4.1

## Change Summary

This log documents the update of precipitation frequency estimates from
TP-40 (1961) to NOAA Atlas 14 (2023) for design storm analysis.

---

## Change Log

### 2025-12-11 14:30 - Precipitation Data Source Update

**Category:** Data Source Change
**Action:** Replace TP-40 with NOAA Atlas 14 precipitation frequency estimates
**File:** Design_Storms_Atlas14.met
**Element:** Precipitation Depths (1% AEP, 24-hr)

**Old Value:** 13.0 inches (TP-40)
**New Value:** 14.5 inches (Atlas 14)
**Change:** +1.5 inches (+11.5%)

**Justification:**
- TP-40 (1961) officially deprecated by NOAA
- Atlas 14 (2023) is current standard for southeastern United States
- Required for FEMA compliance and regulatory submittals

**Impact:**
- +11.5% precipitation depth
- Expected +9-10% increase in peak flows
- Expected +9-10% increase in runoff volumes
- Timing changes expected to be negligible

**Data Source:**
- NOAA Atlas 14 Point Precipitation Frequency Estimates
- Volume 9: Southeastern States (Alabama, Arkansas, Florida, Georgia, Louisiana, Mississippi)
- Location: 31.4504°N, 83.5285°W (Tifton, GA)
- Download Date: 2025-12-11
- API: https://hdsc.nws.noaa.gov/cgi-bin/hdsc/new/cgi_readH5.py

**Verification:**
- Results comparison: See ATLAS14_COMPARISON_REPORT.md
- Quality Verdict: GREEN (within acceptable range)
- GUI Verification: Both models available for side-by-side inspection

---

## Files Modified

1. **Design_Storms_Atlas14.met** (new, cloned from Design_Storms_TP40.met)
   - Updated precipitation depths for all durations
   - Updated description with Atlas 14 metadata

2. **100yr Storm - Atlas14.run** (new, cloned from 100yr Storm - TP40.run)
   - Updated met model reference: Design_Storms_Atlas14
   - Updated DSS output: results_100yr_atlas14.dss
   - Updated description: "1% AEP storm with Atlas 14 precipitation"

## Files Preserved (Baseline)

1. **Design_Storms_TP40.met** (unchanged)
2. **100yr Storm - TP40.run** (unchanged)
3. **results_100yr_tp40.dss** (baseline results)

## Quality Assurance

- [x] Baseline model executed successfully
- [x] Updated model executed successfully
- [x] Results compared and documented
- [x] Changes verifiable in HEC-HMS GUI
- [x] Acceptance criteria met (GREEN verdict)
- [x] MODELING_LOG.md generated
- [x] COMPARISON_REPORT.md generated

## Reviewer Sign-Off

**Reviewed By:** _________________________
**Date:** _________________________
**Comments:** _________________________

---

*This log was generated using hms-commander Atlas 14 agent following the CLB Engineering LLM Forward Approach.*
```

## Acceptance Criteria

The agent validates results against these criteria:

| Criterion | Threshold | Justification |
|-----------|-----------|---------------|
| Peak Flow Deviation | < 15% | Typical for precip data source change |
| Volume Deviation | < 15% | Should match precipitation % change |
| Timing Deviation | < 30 minutes | Should be negligible for same storm pattern |
| Model Execution | No errors | Both baseline and updated must run successfully |

**Verdict Scale:**
- 🟢 **GREEN** - All criteria met, recommend proceeding
- 🟡 **YELLOW** - Some criteria exceeded, requires engineer review
- 🔴 **RED** - Major deviations, investigate before proceeding

## Batch Processing Multiple AEPs

For projects requiring multiple storm events:

```python
from hms_agents.HmsAtlas14 import BatchProcessor

# Define storms to update
storms = [
    {'aep': '10%', 'duration': '24-hr', 'name': '10yr Storm'},
    {'aep': '4%', 'duration': '24-hr', 'name': '25yr Storm'},
    {'aep': '2%', 'duration': '24-hr', 'name': '50yr Storm'},
    {'aep': '1%', 'duration': '24-hr', 'name': '100yr Storm'},
    {'aep': '0.5%', 'duration': '24-hr', 'name': '200yr Storm'},
]

# Batch process
processor = BatchProcessor(
    project_path=hms.project_folder,
    atlas14_data=atlas14_data
)

results = processor.process_batch(
    storms=storms,
    template_met="Design_Storms_TP40",
    new_met_prefix="Design_Storms_Atlas14"
)

# Generate summary report
processor.export_batch_summary(results, "BATCH_SUMMARY.md")
```

## Confidence Intervals (Upper/Lower Bounds)

For sensitivity analysis, Atlas 14 provides 90% confidence intervals:

```python
# Download upper confidence interval data
atlas14_upper = downloader.download_from_coordinates(
    lat=lat, lon=lon,
    data='upper',  # Upper 90% CI
    units='english'
)

# Clone run for upper bound scenario
HmsRun.clone_run(
    source_run="100yr Storm - Atlas14",
    new_run_name="100yr Storm - Atlas14 Upper CI",
    new_met="Design_Storms_Atlas14_Upper",
    output_dss="results_100yr_atlas14_upper.dss",
    description="1% AEP storm with Atlas 14 upper 90% CI",
    hms_object=hms
)

# Similar process for lower bound
```

**Use Cases for Confidence Intervals:**
- Sensitivity analysis for critical infrastructure
- Risk assessment for dam safety studies
- Regulatory compliance where conservative estimates required

## Limitations and Assumptions

1. **Temporal Distribution:** Agent uses same temporal pattern (Alternating Block Method) as original TP-40 model. If project used custom temporal patterns, manual review required.

2. **Spatial Distribution:** For watersheds with multiple gages, agent updates each gage independently. Spatial correlation not automatically adjusted.

3. **Atlas 14 Coverage:** Atlas 14 not available for all U.S. regions. Check coverage at: https://hdsc.nws.noaa.gov/pfds/

4. **Model Calibration:** Updating precipitation data may invalidate calibrated parameters. Recommend recalibration if model was calibrated to observed events.

5. **Frequency Conversion:** Atlas 14 uses partial duration series (PDS). If original model used annual maximum series (AMS), frequency conversion may be needed.

## Troubleshooting

### Issue: "Could not find run block"
**Cause:** Run name doesn't match exactly
**Solution:** Use `HmsRun.get_run_names()` to verify exact run names

### Issue: "Depth count mismatch"
**Cause:** Number of Atlas 14 depths doesn't match TP-40 configuration
**Solution:** Verify `time_interval` and `total_duration` match original configuration

### Issue: "Results differ by >25%"
**Cause:** Possible data download error or wrong location
**Solution:** Verify lat/lon coordinates, check Atlas 14 data visually

### Issue: "DSS file not found"
**Cause:** Model execution failed
**Solution:** Check HMS log files in project folder for errors

## References

- NOAA Atlas 14: https://hdsc.nws.noaa.gov/pfds/
- TP-40 Technical Paper: https://www.weather.gov/media/owp/oh/hdsc/docs/TechnicalPaper_No40.pdf
- CLB Engineering LLM Forward Approach: `docs/CLB_ENGINEERING_APPROACH.md`
- hms-commander Documentation: `CLAUDE.md`

## Example Projects

Sample projects demonstrating the Atlas 14 workflow:

- **Tifton, GA** - Small agricultural watershed (Southeast)
- **Houston, TX** - Urban watershed (Gulf Coast)
- **Pittsburgh, PA** - Snowmelt-influenced watershed (Northeast)

Access via:
```python
from hms_commander import HmsExamples
HmsExamples.extract_project("tifton_atlas14_demo")
```

## Agent Implementation

**File:** `hms_agents/HmsAtlas14/atlas14_agent.py`
**Usage:** See `EXAMPLE.py` for complete workflow demonstration

---

**Version:** 1.0.0
**Last Updated:** 2025-12-11
**Author:** CLB Engineering
**License:** MIT
