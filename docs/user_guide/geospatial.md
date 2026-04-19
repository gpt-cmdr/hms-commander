# Geospatial Operations

Extract model geometry and export to GeoJSON for visualization in GIS tools.

## Overview

The `HmsGeo` class provides methods for working with HMS geospatial files (.geo, .map) and exporting model geometry to GeoJSON format for use in QGIS, ArcGIS, or web mapping applications.

## Quick Examples

### Parse Geospatial Files

```python
from hms_commander import HmsGeo

# Extract subbasin coordinates from .geo file
subbasins = HmsGeo.parse_geo_file("model.geo")
print(subbasins)

# Extract all basin elements
elements = HmsGeo.parse_basin_file("model.basin")

# Extract boundary and river features
features = HmsGeo.parse_map_file("model.map")
```

### Export to GeoJSON

```python
# Export subbasins to GeoJSON
HmsGeo.create_geojson_subbasins(
    subbasins=subbasins,
    output_path="subbasins.geojson",
    crs_epsg="EPSG:2278"  # Texas State Plane Central
)

# Export all features
HmsGeo.export_all_geojson(
    basin_path="model.basin",
    output_dir="geojson_output",
    geo_path="model.geo",
    map_path="model.map"
)
```

### Get Project Centroid

```python
# Calculate project center for web services (e.g., Atlas 14 API)
lat, lon = HmsGeo.get_project_centroid_latlon(
    "model.geo",
    crs_epsg="EPSG:2278"
)
print(f"Project center: {lat:.4f}°N, {abs(lon):.4f}°W")

# Use with NOAA Atlas 14
from noaa_atlas14 import Downloader
downloader = Downloader()
data = downloader.download_from_coordinates(lat, lon)
```

### Get Project Bounds

```python
# Get bounding box in project CRS
minx, miny, maxx, maxy = HmsGeo.get_project_bounds(
    "model.geo",
    crs_epsg="EPSG:2278"
)
```

## Coordinate Reference Systems

HMS Commander uses pyproj for coordinate transformations:

```python
# Common CRS examples
crs_examples = {
    "EPSG:2278": "Texas State Plane Central (US Feet)",
    "EPSG:2277": "Texas State Plane North (US Feet)",
    "EPSG:26914": "UTM Zone 14N (NAD83)",
    "EPSG:4326": "WGS84 (Lat/Lon)"
}

# Transform to WGS84 for web mapping
HmsGeo.create_geojson_subbasins(
    subbasins=subbasins,
    output_path="web_map.geojson",
    crs_epsg="EPSG:4326"  # Web standard
)
```

## GeoJSON Output

Exported GeoJSON files are compatible with:
- **QGIS** - Load directly as vector layers
- **ArcGIS Pro** - Import as features
- **Leaflet/Mapbox** - Web mapping
- **Python** - GeoPandas, Folium

## Key Operations

- **Parse files** - `parse_geo_file()`, `parse_basin_file()`, `parse_map_file()`
- **Export GeoJSON** - `create_geojson_subbasins()`, `export_all_geojson()`
- **Project info** - `get_project_centroid_latlon()`, `get_project_bounds()`

## Cloud-Native Export

For exporting HMS geometry to modern cloud-native formats (GeoParquet, PMTiles, DuckDB), see the companion tool **hms2cng**:

```python
from hms2cng import get_basin_layer_gdf, export_basin_geometry

# Export subbasins to GeoParquet
gdf = get_basin_layer_gdf("project.basin", layer="subbasins")
export_basin_geometry("project.basin", "subbasins.parquet", layer="subbasins")
```

Install with: `pip install "hms2cng[all]"`

See [Cloud-Native Export Guide](cloud_native_export.md) for full documentation.

## Related Topics

- [API Reference: HmsGeo](../api/hms_geo.md) - Complete method documentation
- [Atlas 14 Updates](atlas14_updates.md) - Using centroid for precipitation data
- [Data Formats: Geo Files](../data_formats/geo_files.md) - HMS .geo and .map formats
- [Cloud-Native Export](cloud_native_export.md) - GeoParquet, PMTiles, DuckDB via hms2cng
- [hms2cng Documentation](https://hms2cng.readthedocs.io/) - Full hms2cng reference

---

*For complete API documentation, see [HmsGeo API Reference](../api/hms_geo.md)*
