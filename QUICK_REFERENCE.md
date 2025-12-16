# hms-commander Quick Reference

Quick reference for common operations with hms-commander classes.

---

# HmsPrj - Project Management

## Import and Initialize

```python
from hms_commander import init_hms_project, hms

# Initialize project (uses global hms object)
init_hms_project(r"C:\HMS_Projects\MyProject")

# Access dataframes
print(hms.hms_df)
print(hms.basin_df)
print(hms.run_df)
```

## Available DataFrames

| DataFrame | Description |
|-----------|-------------|
| `hms_df` | Project-level attributes from .hms file |
| `basin_df` | Basin models with element counts and methods |
| `subbasin_df` | Detailed subbasin parameters (loss, transform, baseflow) |
| `met_df` | Meteorologic models with precipitation methods |
| `control_df` | Control specifications with parsed time windows |
| `run_df` | Simulation runs with cross-references |
| `gage_df` | Time-series gages with DSS references |
| `pdata_df` | Paired data tables (storage-outflow, etc.) |

## DataFrame Columns

### basin_df
```python
# Columns: name, file_name, full_path, exists, num_subbasins, num_reaches,
#          num_junctions, num_reservoirs, total_area, loss_methods,
#          transform_methods, baseflow_methods, routing_methods
print(hms.basin_df[['name', 'num_subbasins', 'total_area', 'loss_methods']])
```

### subbasin_df
```python
# Detailed subbasin parameters from basin files
# Columns: name, basin_model, area, downstream, loss_method, transform_method,
#          baseflow_method, initial_deficit, curve_number, time_of_concentration, etc.
print(hms.subbasin_df[['name', 'basin_model', 'area', 'loss_method', 'curve_number']])

# Filter by basin model
castro1_subs = hms.get_subbasin_entries(basin_name='Castro 1')
```

### met_df
```python
# Columns: name, file_name, full_path, exists, precip_method,
#          et_method, snowmelt_method, num_subbasin_assignments
print(hms.met_df[['name', 'precip_method', 'et_method']])
```

### control_df
```python
# Columns: name, file_name, full_path, exists, start_date, end_date,
#          time_interval, time_interval_minutes, duration_hours
print(hms.control_df[['name', 'start_date', 'end_date', 'duration_hours']])
```

### run_df
```python
# Columns: name, file_name, full_path, basin_model, met_model,
#          control_spec, dss_file, description, last_execution_date
print(hms.run_df[['name', 'basin_model', 'met_model', 'dss_file']])
```

### gage_df
```python
# Columns: name, gage_type, dss_file, dss_pathname,
#          has_dss_reference, source_file
print(hms.gage_df[['name', 'gage_type', 'dss_file']])
```

### pdata_df
```python
# Columns: name, table_type, x_units, y_units, dss_file, source_file
print(hms.pdata_df[['name', 'table_type', 'x_units', 'y_units']])
```

## Computed Properties

```python
# Total area across all basin models (sq mi or km2)
print(f"Total area: {hms.total_area:.2f}")

# All DSS files referenced in the project
for dss_file in hms.dss_files:
    print(dss_file)

# All hydrologic methods used
methods = hms.available_methods
print(methods['loss'])        # e.g., ['Initial+Constant', 'SCS']
print(methods['transform'])   # e.g., ['Snyder', 'Clark']
print(methods['routing'])     # e.g., ['Muskingum', 'Modified Puls']
```

## Multiple Projects

```python
from hms_commander import HmsPrj, init_hms_project

# Create separate instances
project1 = HmsPrj()
project2 = HmsPrj()

init_hms_project(r"C:\Project1", hms_object=project1)
init_hms_project(r"C:\Project2", hms_object=project2)

# Compare projects
print(f"P1: {project1.total_area:.2f} sq mi")
print(f"P2: {project2.total_area:.2f} sq mi")
```

## Access Individual Attributes

```python
# Get project-level attribute
name = hms.get_project_attribute('name')
version = hms.hms_version
desc = hms.get_project_attribute('Description')

# Get copies of dataframes
basins = hms.get_basin_entries()
runs = hms.get_run_entries()
```

## Run-Based Queries

```python
# Get run configuration with all cross-referenced details
config = hms.get_run_configuration('Run 1')
print(f"Basin: {config['basin_name']}, Area: {config['basin_area']}")
print(f"Start: {config['control_start']}, End: {config['control_end']}")

# Get result DSS file path for a run
dss_path = hms.get_run_dss_file('Run 1')

# List names
print(hms.list_run_names())
print(hms.list_basin_names())
print(hms.list_gage_names(gage_type='Flow'))

# Get observed data DSS paths
observed = hms.get_observed_dss_paths(gage_type='Flow')
for dss_file, pathname in observed:
    print(f"{dss_file}: {pathname}")
```

---

# DssCore - DSS File Operations

Standalone DSS file reading (no ras-commander dependency).

## Import

```python
from hms_commander.dss import DssCore
```

## Reading DSS Files

```python
# Check if DSS is available (requires pyjnius + Java)
if DssCore.is_available():
    # Get catalog
    paths = DssCore.get_catalog("results.dss")

    # Read time series
    df = DssCore.read_timeseries("results.dss", paths[0])
    print(df.attrs['units'])  # Access metadata

    # Filter catalog by data type
    flow_paths = DssCore.filter_catalog(paths, data_type='FLOW')
    precip_paths = DssCore.filter_catalog(paths, data_type='PRECIP')
```

## DSS Pathname Parsing

```python
# Parse a pathname into components
parts = DssCore.parse_pathname("/BASIN/LOC/FLOW//1HOUR/RUN:SIM1/")
print(parts['element_name'])  # 'LOC'
print(parts['data_type'])     # 'FLOW'
print(parts['run_name'])      # 'SIM1'

# Create a pathname
path = DssCore.create_pathname("BASIN", "LOC", "FLOW", "1HOUR", "RUN1")
```

---

# HmsRun - DSS Output Manager

Manage run configurations and DSS outputs for HMS-to-RAS workflows.

## Import

```python
from hms_commander import HmsRun
```

## Get DSS Configuration

```python
# Get DSS output configuration for a run
config = HmsRun.get_dss_config("Current", hms_object=hms)
print(f"DSS file: {config['dss_file']}")
print(f"DSS path: {config['dss_path']}")
print(f"Basin: {config['basin_model']}")
print(f"Met: {config['met_model']}")
print(f"Control: {config['control_spec']}")
```

## Set DSS Output

```python
# Set output DSS file for RAS boundary conditions
HmsRun.set_output_dss(
    run_name="Current",
    dss_file="HMS_Output.dss",
    hms_object=hms
)
```

## List All Outputs

```python
# List all DSS outputs for all runs
outputs = HmsRun.list_all_outputs(hms_object=hms)
for run_name, config in outputs.items():
    print(f"{run_name}: {config['dss_file']}")
```

## Verify DSS Files Exist

```python
# Check which DSS output files exist
results = HmsRun.verify_dss_outputs(hms_object=hms)
for run_name, info in results.items():
    status = "[EXISTS]" if info['exists'] else "[MISSING]"
    print(f"{status} {run_name}: {info['dss_file']}")
```

## Clone Run for Sensitivity Analysis

```python
# Clone a run with new DSS output
HmsRun.clone_run(
    source_run="Current",
    new_run_name="CN_Sensitivity_70",
    output_dss="CN_70.dss",
    hms_object=hms
)

# Verify clone was created
print(HmsRun.get_run_names(hms_object=hms))
```

## HMS-to-RAS Workflow Example

```python
from hms_commander import init_hms_project, hms, HmsRun, HmsCmdr

# Initialize HMS project
init_hms_project(r"C:\HMS_Projects\MyProject")

# Verify DSS outputs are configured
outputs = HmsRun.list_all_outputs(hms_object=hms)
print("DSS outputs for RAS boundary conditions:")
for run, config in outputs.items():
    print(f"  {run}: {config['dss_file']}")

# Set specific DSS file for RAS
HmsRun.set_output_dss("Current", "HMS_BC_Output.dss", hms_object=hms)

# Run simulation
result = HmsCmdr.compute_run("Current", hms_object=hms)

# DSS file ready for RAS: HMS_BC_Output.dss
```

---

# HmsGeo Quick Reference

Quick reference for common operations with the HmsGeo class.

## Import

```python
from HmsGeo import HmsGeo
```

## Extract Everything (One Command)

```python
outputs = HmsGeo.extract_all_gis(
    basin_path="model.basin",
    geo_path="model.geo",      # Optional
    map_path="model.map",       # Optional
    output_dir="./output",      # Optional (defaults to basin file dir)
    crs_epsg=None               # Optional (defaults to EPSG:2278)
)
# Returns: Dict[str, Path] with keys: 'subbasins', 'junctions', 'reaches',
#          'boundaries' (if map_path), 'rivers' (if map_path)
```

## Parse Files

### Basin File (Subbasins, Junctions, Reaches)
```python
subbasins, junctions, reaches = HmsGeo.parse_basin_file("model.basin")
# Returns: Tuple[Dict, Dict, Dict]
```

### Geo File (Coordinates)
```python
coords = HmsGeo.parse_geo_file("model.geo")
# Returns: Dict[str, Dict[str, float]] - {subbasin_name: {x, y}}
```

### Map File (Detailed Polygons & Polylines)
```python
map_data = HmsGeo.parse_map_file("model.map")
boundaries = map_data['boundaries']  # List of polygon features
rivers = map_data['rivers']          # List of polyline features
# Returns: Dict[str, List[Dict]]
```

## Export to GeoJSON

### Subbasins (Points)
```python
HmsGeo.create_geojson_subbasins(
    subbasins,                  # From parse_basin_file
    "subbasins.geojson",        # Output path
    crs_epsg=None               # Optional CRS
)
```

### Junctions (Points)
```python
HmsGeo.create_geojson_junctions(
    junctions,                  # From parse_basin_file
    "junctions.geojson",
    crs_epsg=None
)
```

### Reaches (Lines)
```python
HmsGeo.create_geojson_reaches(
    reaches,                    # From parse_basin_file
    "reaches.geojson",
    crs_epsg=None
)
```

### Boundaries (Polygons)
```python
HmsGeo.create_geojson_boundaries(
    boundaries,                 # From parse_map_file
    "boundaries.geojson",
    crs_epsg=None
)
```

### Rivers (Polylines)
```python
HmsGeo.create_geojson_rivers(
    rivers,                     # From parse_map_file
    "rivers.geojson",
    crs_epsg=None
)
```

## Common Patterns

### Pattern 1: Just Basin Data
```python
# Parse
subs, juncs, reachs = HmsGeo.parse_basin_file("model.basin")

# Export
HmsGeo.create_geojson_subbasins(subs, "subs.geojson")
HmsGeo.create_geojson_junctions(juncs, "juncs.geojson")
HmsGeo.create_geojson_reaches(reachs, "reachs.geojson")
```

### Pattern 2: Detailed Geometry
```python
# Parse
map_data = HmsGeo.parse_map_file("model.map")

# Export
HmsGeo.create_geojson_boundaries(map_data['boundaries'], "bounds.geojson")
HmsGeo.create_geojson_rivers(map_data['rivers'], "rivers.geojson")
```

### Pattern 3: Everything
```python
# One command does it all
outputs = HmsGeo.extract_all_gis(
    "model.basin",
    geo_path="model.geo",
    map_path="model.map",
    output_dir="./gis"
)
```

### Pattern 4: Merge GEO coordinates with Basin data
```python
# Parse both files
geo_coords = HmsGeo.parse_geo_file("model.geo")
subs, juncs, reachs = HmsGeo.parse_basin_file("model.basin")

# Merge coordinates
for name, coords in geo_coords.items():
    if name in subs and 'x' not in subs[name]:
        subs[name]['x'] = coords['x']
        subs[name]['y'] = coords['y']

# Export
HmsGeo.create_geojson_subbasins(subs, "subs.geojson")
```

## Data Structures

### Subbasin Dictionary
```python
{
    'type': 'Subbasin',
    'x': 3084918.3,
    'y': 13771479.6,
    'area': 3.213,
    'percent_impervious': 0.9,
    'time_of_concentration': 1.06,
    'downstream': 'A1000000_2494_J'
}
```

### Junction Dictionary
```python
{
    'type': 'Junction',
    'x': 3092226.137,
    'y': 13774267.764,
    'downstream': 'A1000000_2385_R'
}
```

### Reach Dictionary
```python
{
    'type': 'Reach',
    'from_x': 3092226.137,
    'from_y': 13774267.764,
    'x': 3102109.795,
    'y': 13775418.773,
    'downstream': 'A1000000_2385_J',
    'description': 'updated-4th round (01-15-04)'
}
```

### Boundary/River Feature
```python
{
    'coordinates': [[x1, y1], [x2, y2], ...],  # List of [x, y] pairs
    'segment_type': 'closed',                   # or 'open'
    'map_type': 'BoundaryMap'                   # or 'RiverMap'
}
```

## Coordinate Systems

Default CRS (Harris County, Texas):
```python
"urn:ogc:def:crs:EPSG::2278"  # NAD83 / Texas South Central (ftUS)
```

Custom CRS examples:
```python
# UTM Zone 15N
"urn:ogc:def:crs:EPSG::32615"

# WGS84 Geographic
"urn:ogc:def:crs:EPSG::4326"

# Texas State Plane (meters)
"urn:ogc:def:crs:EPSG::3664"
```

## File Paths

Both string and Path objects are supported:
```python
from pathlib import Path

# String paths
HmsGeo.parse_basin_file("C:/Models/model.basin")

# Path objects
basin_path = Path("C:/Models/model.basin")
HmsGeo.parse_basin_file(basin_path)
```

## Logging

Configure logging to see progress:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

Log levels:
- `DEBUG`: Detailed parsing info
- `INFO`: Major operations (parsing, exporting)
- `WARNING`: Missing data, skipped elements
- `ERROR`: File errors, parsing failures

## Common Issues

### Missing Coordinates
Some subbasins may not have coordinates in .basin file.
Solution: Also parse .geo file and merge coordinates.

### Closed Polygon Requirement
GeoJSON polygons need first/last vertex to match.
Solution: HmsGeo automatically closes polygons.

### Large Files
.map files can be very large (MB+ size).
Solution: HmsGeo handles large files efficiently, processes line-by-line.

### File Not Found
Always check paths exist before processing.
```python
from pathlib import Path

basin_path = Path("model.basin")
if not basin_path.exists():
    print(f"File not found: {basin_path}")
```

## Tips

1. **Start simple**: Try `extract_all_gis()` first
2. **Check outputs**: Open GeoJSON in QGIS to verify
3. **Use logging**: Enable INFO level to see progress
4. **Batch process**: Loop over multiple models easily
5. **Coordinate check**: Verify CRS matches your data

## Next Steps

- Load GeoJSON in QGIS: `Layer → Add Layer → Add Vector Layer`
- Load in Python: `import geopandas; gdf = geopandas.read_file("file.geojson")`
- Load in JavaScript: `fetch("file.geojson").then(r => r.json())`
- Convert formats: Use `ogr2ogr` to convert to Shapefile, KML, etc.
