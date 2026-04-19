# Cloud-Native Export (hms2cng)

Convert HMS model geometry and results to cloud-native formats for analytics and web mapping.

## Overview

[hms2cng](https://github.com/gpt-cmdr/hms2cng) (HMS to Cloud-Native GIS) is a companion tool that exports HEC-HMS projects to modern geospatial and analytics formats:

- **GeoParquet** - Columnar, Arrow-native spatial data
- **PMTiles** - Serverless vector tiles for web maps
- **DuckDB** - Serverless SQL analytics
- **PostGIS** - Enterprise spatial database

hms2cng uses hms-commander internally to parse HMS files, then writes the results into formats optimized for cloud workflows, dashboards, and large-scale analysis.

## Installation

```bash
# Core (GeoParquet export)
pip install hms2cng

# All extras (DuckDB, PostGIS)
pip install "hms2cng[all]"
```

PMTiles generation requires tippecanoe:

```bash
conda install -c conda-forge tippecanoe pmtiles
```

## Quick Examples

### Export Geometry to GeoParquet

```python
from hms2cng import export_basin_geometry, get_basin_layer_gdf

# Get a single layer as a GeoDataFrame
gdf = get_basin_layer_gdf("project.basin", layer="subbasins")
print(gdf)

# Export to GeoParquet
export_basin_geometry("project.basin", "subbasins.parquet", layer="subbasins")
```

CLI equivalent:

```bash
hms2cng geometry project.basin output.parquet --layer subbasins
```

### Export Results with Spatial Join

```python
from hms2cng import export_hms_results

# Join results to geometry and export
export_hms_results("project/", "results.parquet", variable="Outflow")
```

CLI equivalent:

```bash
hms2cng results project/ results.parquet --var Outflow
```

### Full Project Export

```python
from hms2cng import export_full_project

# Export all geometry layers and results
export_full_project("MyProject.hms", "output/")
# Produces: output/myproject.parquet + manifest.json
```

### Generate PMTiles for Web Maps

```python
from hms2cng import generate_pmtiles_from_input

# Convert GeoParquet to serverless vector tiles
generate_pmtiles_from_input("subbasins.parquet", "subbasins.pmtiles")
```

CLI equivalent:

```bash
hms2cng pmtiles subbasins.parquet subbasins.pmtiles
```

### Query with DuckDB

```python
from hms2cng import query_parquet

# Run SQL directly on Parquet files (no database server needed)
df = query_parquet(
    "results.parquet",
    "SELECT name, max_value FROM _ WHERE max_value > 1000 ORDER BY max_value DESC"
)
print(df)
```

### Sync to PostGIS

```bash
hms2cng sync results.parquet postgresql://user:pass@host/db hms_results
```

## Available Geometry Layers

| Layer | Geometry | Source |
|-------|----------|--------|
| subbasins | Point | .basin canvas coordinates |
| reaches | LineString | .basin from/to coordinates |
| junctions | Point | .basin canvas coordinates |
| diversions | Point | .basin canvas coordinates |
| reservoirs | Point | .basin canvas coordinates |
| sources | Point | .basin canvas coordinates |
| sinks | Point | .basin canvas coordinates |
| watershed | Polygon | .map file boundary |
| subbasin_polygons | Polygon | .sqlite grid database |
| longest_flowpaths | LineString | .sqlite grid database |

## Data Pipeline

hms2cng supports a progressive pipeline from HMS files to enterprise databases:

```
HMS files (.basin, .results XML)
  -> hms2cng (parse via hms-commander)
  -> GeoParquet (columnar, compressed)
  -> PMTiles (serverless web tiles)
  -> DuckDB (SQL analytics)
  -> PostGIS (enterprise database)
```

Each stage is independent. You can stop at GeoParquet for local analysis, add PMTiles for web visualization, or push to PostGIS for multi-user access.

## Typical Export Workflow

```python
from hms2cng import export_basin_geometry, generate_pmtiles_from_input, query_parquet

# 1. Export subbasins to GeoParquet
export_basin_geometry("project.basin", "output/subbasins.parquet", layer="subbasins")

# 2. Generate web-ready tiles
generate_pmtiles_from_input(
    "output/subbasins.parquet",
    "output/subbasins.pmtiles"
)

# 3. Query with DuckDB
top_areas = query_parquet(
    "output/subbasins.parquet",
    "SELECT name, area FROM _ ORDER BY area DESC LIMIT 10"
)
print(top_areas)
```

## Key Operations

- **Geometry export** - `export_basin_geometry()`, `get_basin_layer_gdf()` - Extract HMS elements to GeoParquet
- **Results export** - `export_hms_results()` - Spatially-joined results
- **Full project** - `export_full_project()` - All layers and results with manifest
- **Web tiles** - `generate_pmtiles_from_input()` - Serverless vector tiles
- **SQL analytics** - `query_parquet()` - DuckDB queries on Parquet files
- **Database sync** - `hms2cng sync` - Push to PostGIS

## Related Topics

- [API Reference: HmsGeo](../api/hms_geo.md) - HMS geospatial parsing used by hms2cng
- [Geospatial Operations](geospatial.md) - Working with HMS geometry in hms-commander
- [Results Analysis](results_analysis.md) - HMS results extraction
- [hms2cng Documentation](https://hms2cng.readthedocs.io/) - Full hms2cng reference
- [hms2cng GitHub](https://github.com/gpt-cmdr/hms2cng) - Source code and issues

---

*For complete hms2cng documentation, see [hms2cng.readthedocs.io](https://hms2cng.readthedocs.io/)*
