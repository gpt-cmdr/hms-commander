---
name: hms_link_to-ras
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
description: |
  Links HEC-HMS watershed models to HEC-RAS river models by extracting HMS DSS results
  and preparing them for RAS boundary condition import. Handles flow hydrograph export,
  spatial referencing (HMS outlets to RAS cross sections), DSS pathname formatting,
  quality validation, and time series alignment. Use when setting up HMS-to-RAS workflows,
  exporting HMS results for RAS, preparing upstream boundary conditions, coordinating
  watershed-to-river integrated modeling, or validating HMS results before handoff.
  Leverages shared RasDss infrastructure for consistent DSS operations across both tools.
  Trigger keywords: HMS to RAS, link HMS RAS, boundary condition, upstream BC, watershed
  to river, integrated model, export HMS, spatial matching, hydrograph import.
---

# Linking HMS to HEC-RAS

## When This Skill Is Activated

You are the HMS-to-RAS integration specialist. This is the HMS side of the handoff — you prepare and validate results for RAS import.

## Handoff Workflow

### 1. Ensure HMS Has Been Run

If not already run, delegate to `hms_execute_runs` skill first.

```python
from hms_commander import init_hms_project, hms, HmsResults, HmsGeo
init_hms_project("watershed")
dss_file = hms.run_df.loc["Design_Storm", "dss_file"]
```

### 2. Extract Flow Hydrographs

For each outlet/junction that feeds into RAS:
```python
flows = HmsResults.get_outflow_timeseries(dss_file, "Watershed_Outlet")
```

For multiple tributaries:
```python
for trib in ["Trib_A", "Trib_B"]:
    flows = HmsResults.get_outflow_timeseries(dss_file, trib)
```

### 3. Validate Quality

Before handing off to RAS, verify data quality:
```python
peaks = HmsResults.get_peak_flows(dss_file)
assert all(peaks["Peak Flow (cfs)"] > 0), "Negative or zero peaks detected"

flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
assert flows.notna().all().all(), "NaN values in hydrograph"
assert flows["Flow"].min() >= 0, "Negative flows detected"
```

### 4. Document Spatial Reference

Provide outlet locations so RAS engineer can match to cross sections:
```python
lat, lon = HmsGeo.get_project_centroid_latlon("project.geo", crs_epsg="EPSG:2278")
HmsGeo.export_all_geojson("project.basin", "geojson_output", "project.geo")
```

### 5. Prepare Handoff Package

Document for the RAS side:
- DSS file path (absolute)
- DSS pathname(s) for each element
- Peak flow(s) and timing
- Outlet coordinates
- Time step used (urban: 15-min, rural: 1-hour)
- CRS/projection

### 6. Delegate RAS Side

The RAS import is handled by ras-commander:
- **Cross-repo skill**: `ras-commander/.claude/skills/importing-hms-boundaries/`
- **Coordinator agent**: `.claude/agents/hms-ras-workflow-coordinator.md`

## Cross-Tool Compatibility

- **Units**: Both HMS and RAS use CFS — no conversion needed
- **DSS**: RAS can directly read HMS DSS files (shared RasDss infrastructure)
- **Time steps**: Match if possible; RAS can interpolate but matching is preferred
- **CRS**: Both must use same coordinate system — pass `crs_epsg` to HmsGeo

## If Something Goes Wrong

- **RAS can't find DSS**: Provide absolute path or copy DSS to RAS project folder
- **Spatial mismatch**: Export HMS boundaries to GeoJSON, overlay with RAS geometry in GIS
- **Time series gaps**: Check HMS log file, re-run with shorter interval
- **Peak mismatch after import**: Verify same DSS pathname, check unit consistency

## Primary Sources

- `hms_commander/HmsResults.py` — Flow extraction
- `hms_commander/HmsDss.py` — DSS operations (wraps RasDss)
- `hms_commander/HmsGeo.py` — Spatial reference
- `.claude/rules/integration/hms-ras-linking.md` — Complete workflow patterns

## Implementing Agent

For full cross-tool coordination, delegate to:
`.claude/agents/hms-ras-workflow-coordinator.md`

## Delegation Points

- **Need to run HMS first** → `hms_execute_runs` skill
- **Need to extract/validate results** → `hms_extract_dss-results` skill
- **Need watershed structure** → `hms_parse_basin-models` skill
- **RAS side import** → `ras-commander/.claude/skills/importing-hms-boundaries/`
