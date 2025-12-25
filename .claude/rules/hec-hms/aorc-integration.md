# AORC Precipitation Integration

**Purpose**: Document AORC precipitation integration for HMS gridded precipitation workflows.

**Primary sources**:
- `hms_commander/HmsHuc.py` - HUC watershed operations (IMPLEMENTED)
- `hms_commander/HmsAorc.py` - AORC data download (SKELETON)
- `hms_commander/HmsGrid.py` - Grid cell mapping (SKELETON)
- `examples/aorc_integration_example.py` - Complete workflow example
- `feature_dev_notes/AORC_Precip_Research/` - Research documentation

---

## Overview

HMS Commander provides automated AORC precipitation integration using:
1. **HmsHuc**: Download HUC watersheds as subbasin templates (via PyNHD)
2. **HmsAorc**: Download AORC data from AWS S3, convert to DSS grid
3. **HmsGrid**: Map AORC grid cells to subbasins, generate HMS grid files

**Status**: Phase 1 complete (HmsHuc), Phase 2-3 in development

---

## Quick Start (Phase 1 - Available Now)

### Download HUC Watersheds

```python
from hms_commander import HmsHuc

# Download HUC12 watersheds for project area
bounds = (-77.71, 41.01, -77.25, 41.22)  # west, south, east, north
watersheds = HmsHuc.get_huc12_for_bounds(bounds)

print(f"Downloaded {len(watersheds)} HUC12 watersheds")
for idx, ws in watersheds.iterrows():
    print(f"  {ws['huc12']}: {ws['name']} ({ws['areasqkm']:.1f} km²)")
```

**See**: `hms_commander/HmsHuc.py` for complete API

---

## Complete Workflow (Planned for Phase 2-3)

```python
from hms_commander import HmsHuc, HmsAorc, HmsGrid, HmsMet

# 1. Download HUC12 watersheds (WORKING)
bounds = (-77.71, 41.01, -77.25, 41.22)
watersheds = HmsHuc.get_huc12_for_bounds(bounds)

# 2. Download AORC precipitation (Phase 2)
aorc_nc = HmsAorc.download(
    bounds=bounds,
    start_time="2020-05-01",
    end_time="2020-05-15",
    output_path="precip/aorc_may2020.nc"
)

# 3. Convert to DSS grid (Phase 2)
aorc_dss = HmsAorc.convert_to_dss_grid(
    netcdf_file=aorc_nc,
    output_dss_file="precip/aorc_may2020.dss",
    pathname="/AORC/MAY2020/PRECIP////"
)

# 4. Create grid definition (Phase 3)
HmsGrid.create_grid_definition(
    grid_name="AORC_May2020",
    dss_file=aorc_dss,
    pathname="/AORC/MAY2020/PRECIP////",
    output_file="grids/aorc.grid"
)

# 5. Map AORC grid to each HUC12 (Phase 3)
for idx, watershed in watersheds.iterrows():
    HmsGrid.map_aorc_to_subbasins(
        basin_geometry=watershed['geometry'],
        aorc_grid=aorc_nc,
        output_hrapcells=f"regions/huc12_{watershed['huc12']}"
    )

# 6. Configure HMS met model (Phase 4)
HmsMet.set_gridded_precipitation("model.met", "AORC_May2020")

# 7. Run simulation
from hms_commander import HmsCmdr
HmsCmdr.compute_run("AORC_May2020_Run")
```

---

## Implementation Status

### Phase 1: HUC Watersheds ✅ COMPLETE

**Class**: `HmsHuc` (IMPLEMENTED)

**Methods Available**:
- `get_huc12_for_bounds(bounds)` - Download HUC12 watersheds
- `get_huc8_for_bounds(bounds)` - Download HUC8 watersheds
- `get_huc_by_ids(level, ids)` - Download specific HUCs
- `get_available_levels()` - List HUC levels
- `get_huc_info()` - Get HUC level information

**Dependencies**:
```bash
pip install hms-commander[gis]
# Includes: pygeohydro, pynhd, geopandas, shapely
```

**Example**:
```python
from hms_commander import HmsHuc

watersheds = HmsHuc.get_huc12_for_bounds((-77.71, 41.01, -77.25, 41.22))
# Returns: GeoDataFrame with 23 HUC12 watersheds
```

**Test Results**: 100% success rate (23 HUC12s, 4 HUC8s downloaded and validated)

---

### Phase 2: AORC Download and DSS Conversion (PLANNED)

**Class**: `HmsAorc` (SKELETON)

**Methods Planned**:
- `download(bounds, start_time, end_time, output_path)` - AWS S3 download
- `get_storm_catalog(bounds, year)` - Storm event identification
- `convert_to_dss_grid(netcdf, dss, pathname)` - NetCDF → DSS
- `check_availability(bounds, start, end)` - Data validation
- `get_info()` - Dataset metadata (IMPLEMENTED)

**Source Reference**: `ras_commander/precip/PrecipAorc.py` (954 lines to adapt)

**Dependencies**:
```bash
pip install hms-commander[aorc]
# Includes: xarray, zarr, s3fs, netCDF4, rioxarray
```

**Modifications from ras-commander**:
- Keep WGS84 (no SHG reprojection)
- Keep native ~800m resolution
- Add DSS grid export (use RasDss)

---

### Phase 3: Grid Cell Mapping (PLANNED)

**Class**: `HmsGrid` (SKELETON)

**Methods Planned**:
- `create_grid_definition(name, dss_file, pathname, output)` - Generate .grid files
- `map_aorc_to_subbasins(geometry, aorc_grid, output)` - Create hrapcells files
- `calculate_travel_lengths(grid_cells, outlet)` - Flow distance calculation
- `get_grid_info(grid_file)` - Read .grid metadata

**Template**: `tenk` example project (only HMS example with gridded precip)

**Dependencies**:
```bash
pip install hms-commander[gis]
# Already includes: geopandas, shapely (for spatial operations)
```

**Key Operation**: Spatial intersection of AORC grid cells × HUC polygons

---

## HUC Levels for HMS

| Level | Typical Size | CONUS Count | HMS Use Case |
|-------|--------------|-------------|--------------|
| HUC8 | 10-100 sq mi | 2,264 | Regional models (multiple subbasins) |
| HUC12 | 0.1-1 sq mi | 100,000+ | Detailed models (individual subbasins) |

**Recommendation**:
- **HUC8**: For watershed-scale models (5-20 subbasins)
- **HUC12**: For catchment-scale models (50-200 subbasins)

---

## Data Sources

### AORC Dataset (NOAA)
- **Coverage**: CONUS (1979-present), Alaska (1981-present)
- **Resolution**: ~800m, hourly timesteps
- **Format**: Cloud-optimized Zarr on AWS S3
- **Access**: Anonymous (no authentication required)
- **Source**: `s3://noaa-nws-aorc-v1-1-1km/`

### Watershed Boundary Dataset (USGS)
- **Coverage**: All of CONUS, HUC2-HUC12
- **Resolution**: Variable by HUC level
- **Format**: Vector polygons (via PyNHD web services)
- **Access**: Free USGS web services
- **Status**: Final static version published January 2025

---

## Tenk Project Geographic Coordinates

**Important**: The tenk project shapefiles use HMS schematic coordinates, NOT WGS84.

### Actual Geographic Bounds

The Tenkiller Lake / Illinois River watershed is in eastern Oklahoma:
```python
# Use these bounds for AORC downloads, NOT shapefile bounds
bounds = (-95.2, 35.4, -94.4, 36.2)  # (west, south, east, north)
```

### Key Locations
| Location | Longitude | Latitude |
|----------|-----------|----------|
| Tahlequah, OK | -94.97 | 35.92 |
| Watts, OK | -94.57 | 36.12 |
| Tenkiller Lake | -94.95 | 35.60 |

### Shapefile Coordinate Issue

```python
# The shapefiles use schematic coordinates, not WGS84!
import geopandas as gpd
gdf = gpd.read_file('tenk/maps/subbasins.shp')
print(gdf.total_bounds)  # Returns: [0.0, 57.469, 460.634, 500.0] - NOT lat/lon!
print(gdf.crs)  # Returns: None
```

**Solution**: Use known geographic coordinates (above) or HmsHuc to download actual HUC boundaries.

---

## Reference: tenk Example Project

**Only HMS example with gridded precipitation**

**File Structure**:
```
tenk/
├── tenk.grid              # Grid definition (18 lines)
├── Stage3_HRAP.met        # Met model referencing grid
├── hrap.dss               # DSS grid data (1.2 MB)
└── regions/
    └── hrapcells          # Grid cell mapping (87 cells for subbasin 85)
```

**Grid Definition Format** (`tenk.grid`):
```
Grid: Grid 1
Grid Type: Precipitation
Description: Stage3-HRAP
Data Source Type: External DSS
Filename: hrap.dss
Pathname: /HRAP/ABRFC/PRECIP////
```

**Grid Cell Mapping Format** (`hrapcells`):
```
Parameter Order: xCoord yCoord TravelLength Area
SUBBASIN: 85
GRIDCELL: 633 359 88.38 3.76
GRIDCELL: 634 359 84.51 0.18
...
```

**See**: `feature_dev_notes/AORC_Precip_Research/TENK_PROJECT_ANALYSIS.md`

---

## PyNHD API

### Correct API (v0.19.4)

**Download by bounding box**:
```python
from pygeohydro import WBD
from shapely.geometry import box

wbd = WBD("huc12")
bbox_geom = box(west, south, east, north)
watersheds = wbd.bygeom(bbox_geom, geo_crs="EPSG:4326")
```

**Download by HUC IDs**:
```python
wbd = WBD("huc12")
watersheds = wbd.byids("huc12", ["020502030404", "020502030405"])
```

**Note**: Documentation shows `bybox()` method, but actual API is `bygeom()`.

---

## Dependencies

### Installation Options

**Full AORC support** (all features):
```bash
pip install hms-commander[all]
# Includes: gis, aorc, dss, dev, docs
```

**AORC only**:
```bash
pip install hms-commander[gis,aorc,dss]
```

**Individual packages**:
```bash
pip install pygeohydro pynhd geopandas shapely xarray zarr s3fs netCDF4 ras-commander
```

### Dependency Groups

**[gis]**: HUC watershed operations (HmsHuc)
- pygeohydro>=0.19.0
- pynhd>=0.19.0
- geopandas>=0.12.0
- shapely>=2.0.0
- pyproj>=3.3.0

**[aorc]**: AORC data access (HmsAorc)
- xarray>=2023.1.0
- zarr>=2.13.0
- s3fs>=2023.1.0
- netCDF4>=1.6.0
- rioxarray>=0.13.0

**[dss]**: DSS operations (HmsGrid → DSS conversion)
- ras-commander>=0.83.0
- pyjnius

---

## Research Documentation

**Complete research available in**: `feature_dev_notes/AORC_Precip_Research/`

**Key Documents**:
- `EXECUTIVE_SUMMARY.md` - Strategic overview
- `RECOMMENDATIONS.md` - Implementation plan (8-12 weeks)
- `RAS_COMMANDER_AORC_ANALYSIS.md` - ras-commander code analysis
- `TENK_PROJECT_ANALYSIS.md` - HMS template analysis
- `HUC_WATERSHED_DOWNLOAD.md` - PyNHD documentation
- `PYNHD_TEST_SUCCESS.md` - Validation test results
- `SESSION_SUMMARY.md` - Session accomplishments

---

## Related Documentation

**HMS Gridded Precipitation**:
- `.claude/rules/hec-hms/met-files.md` - Met model operations
- `.claude/rules/hec-hms/basin-files.md` - Basin discretization
- `tests/projects/tenk/` - Example gridded precip project

**Integration**:
- `.claude/rules/integration/hms-ras-linking.md` - HMS→RAS workflows
- `.claude/skills/linking-hms-to-hecras/` - HMS side workflow

**Testing**:
- `.claude/rules/testing/example-projects.md` - HmsExamples usage
- `.claude/rules/testing/tdd-approach.md` - No mocks, use real projects

---

## Quick Reference

**Available now** (Phase 1):
```python
from hms_commander import HmsHuc

# Download HUC12 watersheds
watersheds = HmsHuc.get_huc12_for_bounds(bounds)
```

**Coming soon** (Phase 2-3):
```python
from hms_commander import HmsAorc, HmsGrid

# Download AORC
aorc_nc = HmsAorc.download(bounds, start, end, output)

# Map to subbasins
HmsGrid.map_aorc_to_subbasins(geometry, aorc_grid, output)
```

**Example**: `examples/aorc_integration_example.py`

---

**Status**: Phase 1 complete, Phase 2-3 in development
**Created**: 2025-12-21
