# Geospatial Files (.geo and .map)

## Overview

The `.geo` and `.map` files store geospatial coordinate information for HEC-HMS model elements. The `.geo` file contains coordinates for basin elements (subbasins, junctions, reaches), while the `.map` file stores background map features like watershed boundaries and river centerlines.

## File Purpose

Geospatial files serve several functions:

- **Spatial Layout**: Define geographic locations of model elements
- **Visualization**: Enable map-based display in HMS GUI
- **GIS Export**: Support export to GeoJSON for external GIS analysis
- **Coordinate System**: Store projection information (though often implicit)
- **Centroid Calculation**: Enable project center determination for web services

## .geo File (Basin Elements)

### File Structure

The `.geo` file stores coordinates for each basin element:

```
Subbasin: SubbasinName
     Canvas X: 1000.0
     Canvas Y: 2000.0
     Vertex: 945.5, 1850.2
     Vertex: 1055.3, 1850.2
     Vertex: 1055.3, 2150.8
     Vertex: 945.5, 2150.8
     Vertex: 945.5, 1850.2
End:

Junction: JunctionName
     Canvas X: 1500.0
     Canvas Y: 2500.0
     Point: 1500.0, 2500.0
End:

Reach: ReachName
     Canvas X: 2000.0
     Canvas Y: 3000.0
     Vertex: 1500.0, 2500.0
     Vertex: 1750.0, 2750.0
     Vertex: 2000.0, 3000.0
End:
```

### Coordinate Types

#### Canvas Coordinates
Display coordinates for GUI layout (may not be geographic):
```
Canvas X: 1000.0
Canvas Y: 2000.0
```

#### Vertices (Polygons)
Closed polygon for subbasin boundaries:
```
Vertex: 945.5, 1850.2
Vertex: 1055.3, 1850.2
Vertex: 1055.3, 2150.8
Vertex: 945.5, 2150.8
Vertex: 945.5, 1850.2  ← Closes polygon
```

#### Points
Single coordinate for junctions, sources, sinks:
```
Point: 1500.0, 2500.0
```

#### Line Segments
Multiple vertices for reaches:
```
Vertex: 1500.0, 2500.0
Vertex: 1750.0, 2750.0
Vertex: 2000.0, 3000.0
```

### Complete .geo Example

```
Subbasin: UpperWatershed
     Canvas X: 1200.0
     Canvas Y: 1800.0
     Vertex: 1100.0, 1600.0
     Vertex: 1300.0, 1600.0
     Vertex: 1300.0, 2000.0
     Vertex: 1100.0, 2000.0
     Vertex: 1100.0, 1600.0
End:

Subbasin: LowerWatershed
     Canvas X: 1200.0
     Canvas Y: 2400.0
     Vertex: 1100.0, 2200.0
     Vertex: 1300.0, 2200.0
     Vertex: 1300.0, 2600.0
     Vertex: 1100.0, 2600.0
     Vertex: 1100.0, 2200.0
End:

Junction: Confluence
     Canvas X: 1200.0
     Canvas Y: 2100.0
     Point: 1200.0, 2100.0
End:

Reach: MainChannel
     Canvas X: 1200.0
     Canvas Y: 2700.0
     Vertex: 1200.0, 2600.0
     Vertex: 1200.0, 2800.0
End:

Sink: Outlet
     Canvas X: 1200.0
     Canvas Y: 2900.0
     Point: 1200.0, 2900.0
End:
```

## .map File (Background Features)

### File Structure

The `.map` file stores background geographic features:

```
Background Shapefile: WatershedBoundary
     Filename: boundary.shp
End:

Background Shapefile: Rivers
     Filename: rivers.shp
End:

Map Layer: Boundaries
     Type: Polygon
     Vertex: 500.0, 1000.0
     Vertex: 2000.0, 1000.0
     Vertex: 2000.0, 3500.0
     Vertex: 500.0, 3500.0
     Vertex: 500.0, 1000.0
End:

Map Layer: StreamNetwork
     Type: Polyline
     Vertex: 1200.0, 1000.0
     Vertex: 1200.0, 2000.0
     Vertex: 1200.0, 3000.0
End:
```

### Background Shapefiles

References to external GIS data:

```
Background Shapefile: CountyBoundary
     Filename: data/county.shp
     Visible: True
End:

Background Shapefile: FEMA_Floodplains
     Filename: gis/fema_100yr.shp
     Visible: True
End:
```

### Map Layers

Manually drawn features:

**Polygon Features**:
```
Map Layer: WatershedBoundary
     Type: Polygon
     Vertex: 500.0, 1000.0
     Vertex: 2000.0, 1000.0
     Vertex: 2000.0, 3500.0
     Vertex: 500.0, 3500.0
     Vertex: 500.0, 1000.0
End:
```

**Polyline Features**:
```
Map Layer: MainRiver
     Type: Polyline
     Vertex: 1000.0, 500.0
     Vertex: 1200.0, 1500.0
     Vertex: 1400.0, 2500.0
     Vertex: 1200.0, 3000.0
End:
```

## Coordinate Reference Systems

HMS geo files typically use projected coordinate systems:

### Common US Systems

- **State Plane**: NAD83 State Plane (feet or meters)
- **UTM**: Universal Transverse Mercator zones
- **Custom**: Project-specific coordinate systems

### Example CRS (Texas)

```python
# Texas State Plane South Central (EPSG:2278)
# Units: US Survey Feet
# NAD83 datum

crs_epsg = "EPSG:2278"
```

**Note**: The coordinate system is often not explicitly stored in HMS files - it must be documented separately or inferred from project metadata.

## Working with Geo Files

### Parsing .geo File

```python
from hms_commander import HmsGeo

# Extract subbasin coordinates
subbasins = HmsGeo.parse_geo_file("MyProject.geo")

for name, coords in subbasins.items():
    print(f"{name}: {len(coords)} vertices")
    print(f"  First vertex: {coords[0]}")
```

### Parsing Basin File (Alternative)

```python
# Extract all basin element coordinates from .basin file
elements = HmsGeo.parse_basin_file("MyProject.basin")

print(f"Subbasins: {len(elements['subbasins'])}")
print(f"Junctions: {len(elements['junctions'])}")
print(f"Reaches: {len(elements['reaches'])}")
```

### Parsing Map File

```python
# Extract map features
map_features = HmsGeo.parse_map_file("MyProject.map")

boundaries = map_features.get('boundaries', [])
rivers = map_features.get('rivers', [])
```

### Project Bounds

Calculate project bounding box:

```python
# Get project extent in project CRS
bounds = HmsGeo.get_project_bounds(
    geo_path="MyProject.geo",
    crs_epsg="EPSG:2278"  # Texas State Plane South Central
)

minx, miny, maxx, maxy = bounds
print(f"Extent: {minx}, {miny} to {maxx}, {maxy}")
```

### Project Centroid

Calculate geographic center for web services:

```python
# Get project center in WGS84 lat/lon
lat, lon = HmsGeo.get_project_centroid_latlon(
    geo_path="MyProject.geo",
    crs_epsg="EPSG:2278"
)

print(f"Project center: {lat:.4f}°N, {abs(lon):.4f}°W")

# Use for NOAA Atlas 14 download
from noaa_atlas14 import Atlas14Downloader
downloader = Atlas14Downloader()
atlas14_data = downloader.download_from_coordinates(lat, lon)
```

**Requirements**: `pip install pyproj`

## GeoJSON Export

Export HMS spatial data to GeoJSON for use in QGIS, ArcGIS, or web mapping:

### Export Subbasins

```python
# Export subbasins to GeoJSON
HmsGeo.create_geojson_subbasins(
    subbasins=subbasin_coords,
    output_path="output/subbasins.geojson",
    crs_epsg="EPSG:2278"
)
```

### Export Boundaries

```python
# Export watershed boundary
HmsGeo.create_geojson_boundaries(
    boundaries=boundary_coords,
    output_path="output/boundary.geojson",
    crs_epsg="EPSG:2278"
)
```

### Export Rivers

```python
# Export river network
HmsGeo.create_geojson_rivers(
    rivers=river_coords,
    output_path="output/rivers.geojson",
    crs_epsg="EPSG:2278"
)
```

### Export All Features

```python
# Export everything at once
HmsGeo.export_all_geojson(
    basin_path="MyProject.basin",
    output_dir="output/geojson",
    geo_path="MyProject.geo",
    map_path="MyProject.map"
)
```

This creates:
- `subbasins.geojson`
- `junctions.geojson`
- `reaches.geojson`
- `boundaries.geojson` (if .map file provided)
- `rivers.geojson` (if .map file provided)

## Complete Workflow Example

### Extract and Export Spatial Data

```python
from hms_commander import HmsGeo, init_hms_project
from pathlib import Path

# Project setup
project_dir = Path(r"C:\Projects\UrbanWatershed")
init_hms_project(project_dir)

# Define coordinate system
crs = "EPSG:2278"  # Texas State Plane South Central

# Get project centroid for Atlas 14
lat, lon = HmsGeo.get_project_centroid_latlon(
    geo_path=project_dir / "UrbanWatershed.geo",
    crs_epsg=crs
)
print(f"Project center: {lat:.4f}°N, {abs(lon):.4f}°W")

# Export all spatial data to GeoJSON
output_dir = project_dir / "output" / "geojson"
output_dir.mkdir(parents=True, exist_ok=True)

HmsGeo.export_all_geojson(
    basin_path=project_dir / "UrbanWatershed.basin",
    output_dir=output_dir,
    geo_path=project_dir / "UrbanWatershed.geo",
    map_path=project_dir / "UrbanWatershed.map"
)

print(f"GeoJSON files exported to: {output_dir}")
```

### Use Centroid for Web Services

```python
# Get project center
lat, lon = HmsGeo.get_project_centroid_latlon("project.geo", "EPSG:2278")

# Download NOAA Atlas 14 precipitation
from some_atlas14_library import download_data
precip_data = download_data(latitude=lat, longitude=lon)

# Get elevation data
from some_dem_service import get_elevation
elevation = get_elevation(lat, lon)

# Get soil data
from some_soil_service import get_soil_data
soil_data = get_soil_data(lat, lon)
```

## Coordinate System Reference

### Texas (EPSG:2278)
```python
crs_epsg = "EPSG:2278"  # NAD83 / Texas South Central (ftUS)
```

### California (EPSG:2229)
```python
crs_epsg = "EPSG:2229"  # NAD83 / California zone 5 (ftUS)
```

### Florida (EPSG:2236)
```python
crs_epsg = "EPSG:2236"  # NAD83 / Florida East (ftUS)
```

### UTM Zone 15N (EPSG:26915)
```python
crs_epsg = "EPSG:26915"  # NAD83 / UTM zone 15N (meters)
```

Find your CRS at [epsg.io](https://epsg.io/)

## GeoJSON Output Format

Exported GeoJSON follows standard format:

```json
{
  "type": "FeatureCollection",
  "crs": {
    "type": "name",
    "properties": {
      "name": "EPSG:2278"
    }
  },
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "SubbasinName",
        "area": 145.8,
        "element_type": "Subbasin"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [1100.0, 1600.0],
            [1300.0, 1600.0],
            [1300.0, 2000.0],
            [1100.0, 2000.0],
            [1100.0, 1600.0]
          ]
        ]
      }
    }
  ]
}
```

## Best Practices

1. **Document CRS**: Always document the coordinate reference system used
2. **Consistent units**: Ensure coordinates match basin area units
3. **Close polygons**: First and last vertex must be identical for subbasins
4. **Export for QGIS**: Use GeoJSON export for external GIS analysis
5. **Validate topology**: Check that reaches connect properly to junctions
6. **Use centroid for web services**: Calculate lat/lon for Atlas 14, DEM services

## Common Pitfalls

- **Unknown CRS**: HMS doesn't store CRS explicitly - must document separately
- **Open polygons**: Subbasin polygons must close (first = last vertex)
- **Canvas vs. geographic**: Canvas coordinates may be schematic, not geographic
- **Mixed units**: Ensure coordinate units match area/length units in basin file
- **Missing .geo file**: Some older HMS projects lack .geo files

## GIS Integration Workflow

### HMS → QGIS/ArcGIS

```python
# 1. Export to GeoJSON
HmsGeo.export_all_geojson(
    basin_path="project.basin",
    output_dir="gis_export"
)

# 2. Open in QGIS/ArcGIS
# - Load subbasins.geojson
# - Load reaches.geojson
# - Symbolize by properties (area, CN, etc.)
# - Create maps for reports
```

### GIS → HMS

For creating HMS models from GIS:
1. Delineate subbasins in GIS
2. Extract coordinates
3. Create .geo file manually
4. Define basin model in HMS GUI
5. Verify alignment

## Validation

Check coordinate consistency:

```python
from hms_commander import HmsGeo, HmsBasin

# Parse coordinates
geo_coords = HmsGeo.parse_geo_file("project.geo")
basin_elements = HmsBasin.get_subbasins("project.basin")

# Check all basin elements have coordinates
for name in basin_elements.index:
    if name not in geo_coords:
        print(f"Warning: No coordinates for subbasin '{name}'")
```

## Related Documentation

- [Overview](overview.md) - HMS file format overview
- [Basin File Format](basin_file.md) - Basin model structure (includes some coordinate info)
- [Project File Format](project_file.md) - Project configuration

## API Reference

**Primary Class**: `HmsGeo`

**Parsing Methods**:
- `HmsGeo.parse_geo_file()` - Extract coordinates from .geo file
- `HmsGeo.parse_basin_file()` - Extract all basin element coordinates
- `HmsGeo.parse_map_file()` - Extract map features

**Spatial Analysis**:
- `HmsGeo.get_project_bounds()` - Calculate bounding box in project CRS
- `HmsGeo.get_project_centroid_latlon()` - Calculate center in WGS84 lat/lon

**GeoJSON Export**:
- `HmsGeo.create_geojson_subbasins()` - Export subbasins
- `HmsGeo.create_geojson_boundaries()` - Export boundaries
- `HmsGeo.create_geojson_rivers()` - Export rivers
- `HmsGeo.export_all_geojson()` - Export all features

**Requirements**:
- Coordinate transformations require: `pip install pyproj`
- GeoJSON creation may require: `pip install geopandas shapely`

See [API Reference](../api/hms_prj.md) for complete API documentation.
