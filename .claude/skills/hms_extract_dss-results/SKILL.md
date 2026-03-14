---
name: hms_extract_dss-results
description: |
  Extracts and analyzes HEC-HMS simulation results from DSS files using HmsDss and
  HmsResults classes. Handles peak flows, hydrographs, volume summaries, and time series
  data. Leverages ras-commander's RasDss for DSS V6/V7 support. Use when processing
  HMS results, extracting peak flows, analyzing hydrographs, computing volumes, exporting
  time series, comparing multiple runs, or linking HMS results to HEC-RAS boundary
  conditions.
  Trigger keywords: DSS file, results, peak flow, hydrograph, time series, volume,
  extract results, HMS output, analyze results, compare runs.
---

# Extracting DSS Results

## When This Skill Is Activated

You are the HMS results extraction specialist. Follow this post-simulation workflow.

## Decision Tree

1. **User wants peak flows** → "Extract Peak Flows"
2. **User wants hydrograph time series** → "Extract Hydrographs"
3. **User wants to compare multiple runs** → "Compare Runs"
4. **User wants to hand off results to RAS** → Delegate to `hms_link_to-ras` skill
5. **DSS operations beyond results** → Delegate to `dss-integration-specialist` agent

## Step 1: Locate the DSS File

If the project is initialized:
```python
dss_file = hms.run_df.loc["Run 1", "dss_file"]
```

If not, ask the user for the DSS file path. Verify it exists:
```python
from pathlib import Path
assert Path(dss_file).exists(), f"DSS file not found: {dss_file}"
```

## Extract Peak Flows

```python
from hms_commander import HmsResults

peaks = HmsResults.get_peak_flows(dss_file)
# Columns: Element, Peak Flow (cfs), Time to Peak
```

Display the DataFrame to the user. Validate:
- All peak flows > 0 (negative flows indicate a problem)
- Time to peak is within the simulation window

## Extract Hydrographs

```python
flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
# Returns: pandas DataFrame with datetime index
```

For precipitation:
```python
precip = HmsResults.get_precipitation_timeseries(dss_file, "Subbasin1")
```

Validate:
- No NaN values: `assert flows.notna().all().all()`
- No negative flows: `assert flows["Flow"].min() >= 0`

## Volume Analysis

```python
volumes = HmsResults.get_volume_summary(dss_file)
```

## Compare Runs

```python
comparison = HmsResults.compare_runs(
    ["baseline.dss", "alternative.dss"],
    element="Outlet"
)
```

Display side-by-side peak flows and timing differences.

## DSS Catalog (Advanced)

If the user needs to see all available pathnames:
```python
if HmsDss.is_available():
    catalog = HmsDss.get_catalog(dss_file)
    print(catalog)
```

Note: HmsDss wraps ras-commander's RasDss — requires `ras-commander` and `pyjnius` installed.

## If Something Goes Wrong

- **DSS file not found**: Run hasn't been executed yet — delegate to `hms_execute_runs` skill
- **Empty results**: Check that the run completed successfully (check log file)
- **HmsDss not available**: RasDss/pyjnius not installed — use HmsResults (text-based) instead
- **Element not found**: Check element name against `hms.basin_df` or `get_subbasins()`

## Primary Sources

- `hms_commander/HmsDss.py` — DSS operations (wraps RasDss)
- `hms_commander/HmsResults.py` — Results extraction and analysis
- `.claude/rules/hec-hms/dss-operations.md` — DSS patterns and pathname format

## Implementing Agent

For advanced DSS operations, delegate to:
`.claude/agents/dss-integration-specialist.md`

## Delegation Points

- **Need to run simulation first** → `hms_execute_runs` skill
- **Hand off results to RAS** → `hms_link_to-ras` skill
- **Modify model and re-run** → `hms_parse_basin-models` skill
