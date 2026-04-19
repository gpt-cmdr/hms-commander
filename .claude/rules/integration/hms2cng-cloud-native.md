# HMS to Cloud-Native GIS (hms2cng)

**Purpose**: Document integration between hms-commander and the hms2cng companion package for cloud-native geospatial export.

**Primary sources**:
- `G:\GH\hms2cng\hms2cng\` - Package source (geometry.py, results.py, project.py, pmtiles.py, duckdb_session.py, postgis_sync.py)
- `G:\GH\hms2cng\docs\` - MkDocs documentation
- `G:\GH\hms2cng\examples\` - Marimo interactive examples
- `.claude/skills/hms_export_cloud-native/SKILL.md` - Agent skill definition

---

## Overview

**hms2cng** (HMS to Cloud Native GIS) exports HEC-HMS model geometry and simulation results to modern cloud-native geospatial formats. It depends on hms-commander for all HMS file parsing and provides the output layer for GeoParquet, PMTiles, DuckDB, and PostGIS workflows.

**Repository**: https://github.com/gpt-cmdr/hms2cng
**Documentation**: https://hms2cng.readthedocs.io/
**PyPI**: `pip install hms2cng`

---

## Package Relationship

| Package | Role | Depends On |
|---------|------|------------|
| **hms-commander** | Parse HMS files, static class APIs | Core Python (pandas, numpy) |
| **hms2cng** | Cloud-native export layer | hms-commander >= 0.2.0 |

hms2cng imports and uses:
- `HmsBasin.get_subbasins()`, `get_junctions()`, `get_reaches()`, etc. for geometry
- `HmsGeo.parse_map_file()` for watershed boundary polygons
- `init_hms_project()` / `HmsPrj` for CRS auto-detection and project metadata
- `HmsSqlite` for grid database layers (subbasin polygons, flowpaths)

---

## Data Flow

```
HMS Project Files (.hms, .basin, .met, .control)
  |  [hms-commander: HmsBasin, HmsGeo, HmsPrj]
  v
DataFrames + GeoDataFrames
  |  [hms2cng: geometry.py, results.py, project.py]
  v
GeoParquet (ZSTD compressed, bbox columns, Hilbert-sorted)
  |  [hms2cng: pmtiles.py, duckdb_session.py, postgis_sync.py]
  v
PMTiles | DuckDB | PostGIS
```

**Results parsing**: hms2cng parses `RUN_*.results` XML files for summary statistics (peak, min, mean, time_of_max, volume, depth). It does NOT read DSS files directly -- for DSS time series, use HmsDss/HmsResults from hms-commander.

---

## Installation

```bash
# Both packages
pip install hms-commander hms2cng

# hms2cng with all extras (DuckDB, PostGIS)
pip install "hms2cng[all]"

# For PMTiles generation (external CLI tools)
conda install -c conda-forge tippecanoe pmtiles
```

**Development mode** (local editable installs):
```bash
cd G:\GH\hms-commander && pip install -e ".[all]"
cd G:\GH\hms2cng && pip install -e ".[all]"
```

---

## CLI Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `hms2cng geometry` | Export basin geometry layers | `hms2cng geometry project.basin out.parquet --layer subbasins` |
| `hms2cng results` | Export results with spatial join | `hms2cng results project/ out.parquet --var Outflow` |
| `hms2cng project` | Full project export | `hms2cng project project.hms out_dir/` |
| `hms2cng pmtiles` | Generate vector tiles | `hms2cng pmtiles data.parquet out.pmtiles` |
| `hms2cng query` | DuckDB SQL on GeoParquet | `hms2cng query data.parquet "SELECT * FROM _"` |
| `hms2cng sync` | Upload to PostGIS | `hms2cng sync data.parquet connstr table_name` |
| `hms2cng manifest` | Show project metadata | `hms2cng manifest project.hms` |

---

## Python API

```python
from hms2cng import (
    # Geometry
    export_basin_geometry, get_basin_layer_gdf, export_all_basin_geometry,
    merge_all_layers,
    # Results
    export_hms_results, export_all_results, merge_all_variables,
    # Project
    get_project_manifest, export_project_manifest, export_full_project,
    # Analytics
    DuckSession, query_parquet, spatial_join,
    # Tiles
    generate_pmtiles_from_input,
    # PostGIS
    sync_to_postgres, read_from_postgres,
)
```

---

## Workflow Patterns

### Pattern 1: Geometry Export

```python
from hms2cng import get_basin_layer_gdf, export_basin_geometry

# Extract as GeoDataFrame
gdf = get_basin_layer_gdf("project.basin", layer="subbasins")

# Write to GeoParquet
export_basin_geometry("project.basin", "subbasins.parquet", layer="subbasins")
```

### Pattern 2: Results with Spatial Join

```python
from hms2cng import export_hms_results

# Parses RUN_*.results XML, merges with geometry, writes GeoParquet
export_hms_results("project/", "results.parquet", variable="Outflow")
```

### Pattern 3: Full Project Archive

```python
from hms2cng import export_full_project

# Single consolidated parquet + manifest.json
export_full_project("MyProject.hms", "output/")
# Produces: output/myproject.parquet + manifest.json
```

### Pattern 4: PMTiles for Web Maps

```python
from hms2cng import generate_pmtiles_from_input

# GeoParquet -> GeoJSON -> tippecanoe -> PMTiles
generate_pmtiles_from_input("subbasins.parquet", "subbasins.pmtiles")
```

### Pattern 5: Web Visualization in Jupyter

```python
import leafmap, geopandas as gpd

gdf = gpd.read_parquet("subbasins.parquet")
m = leafmap.Map(center=(31.5, -83.5), zoom=10)
m.add_gdf(gdf, layer_name="Subbasins")
m
```

---

## Available Geometry Layers

| Layer | Geometry | Source File |
|-------|----------|------------|
| subbasins | Point | .basin (canvas coords) |
| reaches | LineString | .basin (from/to coords) |
| junctions | Point | .basin (canvas coords) |
| diversions | Point | .basin (canvas coords) |
| reservoirs | Point | .basin (canvas coords) |
| sources | Point | .basin (canvas coords) |
| sinks | Point | .basin (canvas coords) |
| watershed | Polygon | .map file |
| subbasin_polygons | Polygon | .sqlite grid database |
| longest_flowpaths | LineString | .sqlite grid database |
| centroidal_flowpaths | LineString | .sqlite grid database |
| teneightyfive_flowpaths | LineString | .sqlite grid database |
| subbasin_statistics | Point | .sqlite (joined with subbasins) |

---

## CRS Handling

- hms2cng auto-detects CRS from the HMS project via `init_hms_project()`
- If detection fails, geometry keeps native coordinates (`crs=None`) unless the caller supplies `--crs` / `crs_epsg`
- Canvas coordinates (schematic, not geographic) are preserved in `canvas_x`, `canvas_y` columns
- Override with `--crs EPSG:XXXX` CLI flag or `crs_epsg` Python parameter

---

## Common Issues

### tippecanoe/pmtiles not found
PMTiles generation requires external CLI tools. Install via conda-forge:
```bash
conda install -c conda-forge tippecanoe pmtiles
```

### No CRS detected
Some HMS projects (especially example projects) lack CRS metadata. Pass `--crs` explicitly or use `out_crs=None` to keep schematic coordinates.

### No .sqlite for polygon layers
Polygon-based layers (subbasin_polygons, flowpaths) require an HMS SQLite grid database from terrain preprocessing (GeoHMS). Point-based layers work from .basin files alone.

### Results XML not found
hms2cng reads `RUN_*.results` XML files, not DSS. Ensure the HMS simulation has been run and results XML exists.

---

## Cross-References

**hms-commander Documentation**:
- `docs/user_guide/cloud_native_export.md` - User guide page
- `docs/user_guide/geospatial.md` - Geospatial operations (GeoJSON export)
- `examples/19_cloud_native_export.ipynb` - Export workflow notebook
- `examples/20_pmtiles_web_map.ipynb` - Web map visualization notebook
- `.claude/skills/hms_export_cloud-native/SKILL.md` - Agent skill

**hms2cng Repository**:
- `hms2cng/geometry.py` - Geometry extraction and export
- `hms2cng/results.py` - Results XML parsing and spatial join
- `hms2cng/project.py` - Full project export and manifest
- `hms2cng/pmtiles.py` - Vector tiles pipeline
- `hms2cng/duckdb_session.py` - DuckDB wrapper
- `hms2cng/postgis_sync.py` - PostGIS upload

---

**Status**: Stable (v0.1.1)
**Created**: 2025-06-01
