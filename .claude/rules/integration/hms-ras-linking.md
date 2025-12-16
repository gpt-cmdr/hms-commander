---
paths: hms_commander/**/*.py
---

# HMS-RAS Workflow Integration

## Overview

HMS generates runoff hydrographs → RAS consumes as boundary conditions

**Workflow Pattern**:
```
HEC-HMS (Watershed)          HEC-RAS (River)
    ↓                            ↓
Precipitation                Geometry
    ↓                            ↓
Runoff Generation            ←─── Import HMS Flows
    ↓                            ↓
DSS Output              Hydraulic Analysis
    ↓                            ↓
Flow Hydrographs         Flood Inundation
```

## HMS Side Responsibilities

### 1. Generate Results in DSS Format

```python
from hms_commander import init_hms_project, HmsCmdr, hms

# Execute HMS simulation
init_hms_project("watershed")
HmsCmdr.compute_run("Design_Storm")

# Results written to DSS
dss_file = hms.run_df.loc["Design_Storm", "dss_file"]
# Example: watershed/results.dss
```

**DSS Pathname Format** (HMS standard):
```
/A/B/C/D/E/F/
/BASIN/ELEMENT/FLOW/15MIN/RUN_NAME/
```

Example: `/WATERSHED/OUTLET/FLOW/15MIN/DESIGN_STORM/`

### 2. Export Hydrographs for RAS

```python
from hms_commander import HmsResults

# Extract flow hydrograph
flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
# Returns: pandas DataFrame with datetime index, flow values in cfs

# Identify peak flow and timing
peaks = HmsResults.get_peak_flows(dss_file)
print(f"Peak: {peaks.loc['Outlet', 'Peak Flow (cfs)']} cfs")
print(f"Time: {peaks.loc['Outlet', 'Time to Peak']}")
```

### 3. Document Spatial Reference

**Critical for RAS matching**: Document where HMS subbasin outlets are located

```python
from hms_commander import HmsGeo

# Get project centroid (for general reference)
lat, lon = HmsGeo.get_project_centroid_latlon("watershed.geo", crs_epsg="EPSG:2278")

# Export subbasin boundaries to GeoJSON
HmsGeo.export_all_geojson(
    basin_path="watershed.basin",
    output_dir="geojson",
    geo_path="watershed.geo"
)
# Creates: geojson/subbasins.geojson (with outlet point coordinates)
```

**Result**: RAS engineer can spatially match HMS outlets → RAS cross sections

### 4. Validate Time Series Quality

Before handing off to RAS:

```python
# Check hydrograph statistics
stats = HmsResults.get_hydrograph_statistics(dss_file, "Outlet")

# Validate:
# - No negative flows
# - Peak is reasonable
# - Volume conservation (precip in ≈ flow out + losses)
# - Time series complete (no gaps)
```

## Integration Points

### HMS Provides to RAS

1. **Flow Hydrographs**: Time series in DSS format
2. **Spatial Reference**: Outlet locations (lat/lon or project coordinates)
3. **Time Window**: Start/end dates, time interval
4. **Units**: CFS (cubic feet per second) - standard for both tools
5. **Metadata**: Basin name, run name, storm event description

### RAS Receives from HMS

RAS imports HMS DSS files as upstream boundary conditions:

**See**: `ras-commander/.claude/rules/integration/hms-ras-linking.md` for RAS side

**RAS Operations** (informational, not in hms-commander scope):
- Import DSS using RasDss (ras-commander)
- Match HMS subbasin outlets → RAS cross sections (spatial matching)
- Align time series (HMS interval → RAS computation interval)
- Validate boundary condition (peak, volume, timing)

## Common Workflow Patterns

### Pattern 1: Single Outlet → Single Upstream BC

**HMS Side**:
```python
# 1. Execute HMS
HmsCmdr.compute_run("100yr_Storm")

# 2. Extract outlet hydrograph
dss_file = hms.run_df.loc["100yr_Storm", "dss_file"]
outlet_flows = HmsResults.get_outflow_timeseries(dss_file, "Watershed_Outlet")

# 3. Document outlet location
lat, lon = HmsGeo.get_project_centroid_latlon("project.geo")
print(f"Outlet location: {lat:.4f}°N, {lon:.4f}°W")
```

**Handoff to RAS**:
- DSS file: `watershed/results.dss`
- Pathname: `/WATERSHED/WATERSHED_OUTLET/FLOW/15MIN/100YR_STORM/`
- Location: (lat, lon) or project coordinates
- RAS engineer matches to upstream cross section

### Pattern 2: Multiple Tributaries → Multiple Upstream BCs

**HMS Side**:
```python
# Extract multiple outlets
tributaries = ["Tributary_A", "Tributary_B", "Tributary_C"]

for trib in tributaries:
    flows = HmsResults.get_outflow_timeseries(dss_file, trib)
    print(f"{trib}: Peak = {flows['Flow'].max()} cfs")
    # Document each tributary outlet location
```

**Handoff to RAS**: Multiple DSS pathnames, each matched to RAS cross section

### Pattern 3: Internal Junctions → Lateral Inflows

**HMS Side**:
```python
# Extract flows at junctions (lateral inflows to RAS)
junctions = HmsBasin.get_junctions("watershed.basin")

for junction in junctions.index:
    flows = HmsResults.get_outflow_timeseries(dss_file, junction)
    # Each junction becomes lateral inflow in RAS
```

## DSS Operations (Shared Infrastructure)

**Both HMS and RAS use RasDss**:

```python
from hms_commander import HmsDss

# HmsDss wraps ras_commander.RasDss
if HmsDss.is_available():
    # Read DSS catalog
    catalog = HmsDss.get_catalog(dss_file)

    # Read time series
    flows = HmsDss.read_timeseries(dss_file, pathname)
```

**Why This Matters**:
- Consistent DSS operations across HMS and RAS
- No code duplication
- Automatic V6/V7 support
- RAS can directly read HMS DSS files (same Java bridge)

## Quality Checks Before Handoff

**Validate HMS results before giving to RAS**:

```python
from hms_commander import HmsResults

# 1. Check peak flows are reasonable
peaks = HmsResults.get_peak_flows(dss_file)
assert all(peaks["Peak Flow (cfs)"] > 0), "Negative peaks detected!"

# 2. Check volume conservation
volumes = HmsResults.get_volume_summary(dss_file)
precip_vol = volumes["Precipitation Volume (ac-ft)"].sum()
runoff_vol = volumes["Runoff Volume (ac-ft)"].sum()
loss_ratio = 1 - (runoff_vol / precip_vol)
print(f"Loss ratio: {loss_ratio:.1%}")  # Should be reasonable (20-70%)

# 3. Check time series completeness
flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
assert flows.notna().all().all(), "Missing data in time series!"
```

## Cross-Tool Considerations

### Time Step Compatibility

**HMS**: Typically 15-minute or 1-hour intervals
**RAS**: Computation interval set in unsteady flow plan

**Recommendation**:
- Use 15-minute HMS interval for urban watersheds
- Use 1-hour HMS interval for large rural watersheds
- RAS can interpolate if needed, but matching intervals is preferred

### Units Consistency

**HMS**: CFS (cubic feet per second) - standard
**RAS**: CFS (cubic feet per second) - standard

✅ **Units match** - no conversion needed for flow

### Coordinate Systems

**HMS**: Project coordinate system (e.g., State Plane)
**RAS**: Same project coordinate system required for spatial matching

**Recommendation**: Ensure both HMS and RAS use same CRS

### Time Zone

**HMS**: Local time (no time zone in DSS pathname)
**RAS**: Local time (no time zone in HDF)

✅ **Assumption**: Both use same local time zone

## Automation Opportunities

**Future**: Production task agent for HMS→RAS linking

**Would automate**:
1. Extract HMS hydrographs from DSS
2. Match HMS outlets → RAS cross sections (spatial)
3. Import to RAS boundary conditions
4. Validate peak/volume/timing alignment
5. Generate QAQC report

**Status**: Documented in planning, not yet implemented

**See**: `hms_agents/HMS_to_RAS_Linker/` (placeholder for future development)

## Related Documentation

**HMS-Commander**:
- `.claude/skills/linking-hms-to-hecras/` - HMS side workflow
- `.claude/skills/extracting-dss-results/` - DSS operations
- `.claude/rules/hec-hms/dss-operations.md` - DSS integration

**RAS-Commander** (cross-reference):
- `ras-commander/.claude/rules/integration/hms-ras-linking.md` - RAS side workflow
- `ras-commander/.claude/skills/importing-hms-boundaries/` - RAS import workflow

## Key Decisions

### Decision 1: DSS as Exchange Format

**Why DSS?**
- Native format for both HMS and RAS
- Efficient time series storage
- Shared RasDss infrastructure (no conversion needed)

**Alternative considered**: CSV export/import (rejected - more error-prone)

### Decision 2: Manual Spatial Matching

**Why manual?**
- HMS outlets and RAS cross sections may not align exactly
- Engineering judgment required for best match
- Automation risk: incorrect matching → bad results

**Future**: Could provide matching suggestions based on proximity

### Decision 3: HmsDss Wraps RasDss

**Why?**
- Avoids code duplication
- Leverages ras-commander's mature DSS infrastructure
- Ensures consistency across tools
- Single Java bridge maintenance

**See**: `.claude/rules/hec-hms/dss-operations.md` for complete rationale

---

**Summary**: HMS generates hydrographs in DSS format. RAS imports as boundary conditions. Spatial matching is manual (engineering judgment). Both use shared RasDss infrastructure for consistent DSS operations.
