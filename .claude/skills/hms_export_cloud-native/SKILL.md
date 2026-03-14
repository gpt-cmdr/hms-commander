---
name: hms_export_cloud-native
description: |
  Exports HEC-HMS basin geometry and simulation results to cloud-native geospatial
  formats (GeoParquet, PMTiles) using the hms2cng package (HMS to Cloud Native GIS).
  Supports all HMS element types (subbasins, reaches, junctions, diversions, reservoirs,
  sources, sinks, watershed boundary) plus SQLite-based grid layers (subbasin polygons,
  flowpaths). Also exports results summary statistics (peak, min, mean) spatially joined
  with geometry. Use when generating GeoParquet for DuckDB/web analysis, PMTiles for
  map visualization, syncing to PostGIS, exporting basin elements for web GIS, building
  interactive map layers, or creating cloud-optimized archives of HMS project geometry.
  Trigger keywords: GeoParquet, PMTiles, cloud native, vector tiles, export geometry,
  export results, spatial export, parquet, tippecanoe, PostGIS sync, web map, DuckDB
  query, hms2cng.
---

# Exporting HMS to Cloud-Native Formats

## When This Skill Is Activated

You are the cloud-native export specialist. Route the user's request through the decision tree below.

## Decision Tree

1. **User wants geometry export** → "Export Geometry"
2. **User wants results export** → "Export Results"
3. **User wants PMTiles for web maps** → "Generate PMTiles"
4. **User wants to query exported data** → "Query with DuckDB"
5. **User wants PostGIS sync** → "Sync to PostGIS"

## Prerequisites

Ensure hms2cng is installed:
```bash
uv pip install -e "C:/GH/hms2cng[all]"
```

For PMTiles, also install:
```bash
conda install -c conda-forge tippecanoe pmtiles
```

## Export Geometry

1. Identify the basin file and desired layer:

   | Layer | Geometry | Source |
   |-------|----------|--------|
   | `subbasins` | Point | `.basin` canvas coords |
   | `junctions` | Point | `.basin` canvas coords |
   | `reaches` | LineString | `.basin` from/to coords |
   | `watershed` | Polygon | `.map` file boundary |
   | `subbasin_polygons` | Polygon | `.sqlite` grid database |
   | `longest_flowpaths` | LineString | `.sqlite` grid database |

2. Export via CLI:
   ```bash
   hms2cng geometry project.basin output.parquet --layer subbasins
   ```

   Or via Python API:
   ```python
   from hms2cng.geometry import export_basin_geometry, get_basin_layer_gdf
   gdf = get_basin_layer_gdf("project.basin", layer="subbasins")
   export_basin_geometry("project.basin", "output.parquet", layer="subbasins")
   ```

3. For all layers:
   ```python
   for layer in ["subbasins", "reaches", "junctions", "watershed"]:
       try:
           export_basin_geometry(basin, f"out/{layer}.parquet", layer=layer)
       except (FileNotFoundError, ValueError) as e:
           print(f"Skipping {layer}: {e}")
   ```

CRS is auto-detected from HMS project. If detection fails, specify `--crs EPSG:XXXX`.

## Export Results

Results come from `RUN_*.results` XML files (not DSS):
```bash
hms2cng results project/results output.parquet --type subbasin --var "Outflow"
```

This merges summary stats (max, min, mean, time_of_max) with geometry.

## Generate PMTiles

Convert GeoParquet to PMTiles for web visualization:
```bash
hms2cng pmtiles subbasins.parquet subbasins.pmtiles --layer subbasins
```

## Query with DuckDB

Query exported data directly:
```bash
hms2cng query results.parquet "SELECT name, max_value FROM _ ORDER BY max_value DESC"
```

Via Python:
```python
from hms2cng.duckdb_session import query_parquet
df = query_parquet("results.parquet", "SELECT * FROM _ WHERE max_value > 1000")
```

## Sync to PostGIS

```bash
hms2cng sync results.parquet postgresql://user:pass@host/db table_name
```

## If Something Goes Wrong

- **hms2cng not found**: Install with `uv pip install -e "C:/GH/hms2cng[all]"`
- **No .sqlite file**: SQLite layers (polygons, flowpaths) require an HMS SQLite grid database
- **CRS issues**: Pass `--crs` explicitly if auto-detection fails
- **tippecanoe not found**: Install via `conda install -c conda-forge tippecanoe`

## Primary Sources

- `C:/GH/hms2cng/` — CLI package (local dev install)
  - `hms2cng/cli.py` — Typer CLI (5 commands)
  - `hms2cng/geometry.py` — Basin layer extraction
  - `hms2cng/results.py` — Results XML parsing + spatial join

## Delegation Points

- **Need basin structure first** → `hms_parse_basin-models` skill
- **Need DSS time series (not XML summary)** → `hms_extract_dss-results` skill
- **Need to run simulations first** → `hms_execute_runs` skill
