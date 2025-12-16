# Getting Started with hms-commander

Welcome to **hms-commander**! This guide will help you extract GIS data from your HEC-HMS model files in just a few minutes.

## What is hms-commander?

hms-commander is a Python library that converts HEC-HMS hydrologic model files into standard GIS formats (GeoJSON). It extracts:

- 📍 **Subbasins** (points with area, imperviousness, time of concentration)
- 📍 **Junctions** (network connection points)
- 📏 **Reaches** (hydraulic routing connections)
- 🗺️ **Watershed Boundaries** (detailed polygons)
- 🌊 **Stream Networks** (detailed polylines)

## Installation

### Option 1: Using uv (Recommended)
```bash
cd C:\GH\hms-commander
uv pip install -e .
```

### Option 2: Using pip
```bash
cd C:\GH\hms-commander
pip install -e .
```

## Quick Start (30 seconds)

1. **Update file paths** in `test_extraction.py`:
   ```python
   basin_path = "C:/YOUR/PATH/model.basin"
   geo_path = "C:/YOUR/PATH/model.geo"
   map_path = "C:/YOUR/PATH/model.map"
   ```

2. **Run the test script**:
   ```bash
   cd C:\GH\hms-commander
   python test_extraction.py
   ```

3. **Check output**:
   - Look in `C:\GH\hms-commander\test_output\`
   - Open GeoJSON files in QGIS or ArcGIS

## Simple Example

```python
from HmsGeo import HmsGeo

# Extract all GIS data with one command
outputs = HmsGeo.extract_all_gis(
    basin_path="C:/Models/mymodel.basin",
    geo_path="C:/Models/mymodel.geo",
    map_path="C:/Models/mymodel.map",
    output_dir="C:/Models/gis_output"
)

# Output files are now in C:/Models/gis_output/
print("Created files:")
for key, path in outputs.items():
    print(f"  {key}: {path}")
```

## What You Get

After running extraction, you'll have these GeoJSON files:

| File | Type | Contents |
|------|------|----------|
| `hms_subbasins.geojson` | Points | Drainage areas with hydrologic properties |
| `hms_junctions.geojson` | Points | Network junctions |
| `hms_reaches.geojson` | Lines | Channel routing connections |
| `hms_boundaries.geojson` | Polygons | Detailed watershed boundaries (if .map file provided) |
| `hms_rivers.geojson` | Lines | Detailed stream network (if .map file provided) |

## Next Steps

### 1. View in QGIS (Free GIS Software)

1. Download QGIS: https://qgis.org/
2. Open QGIS
3. `Layer → Add Layer → Add Vector Layer`
4. Browse to your GeoJSON files
5. Click `Add`

### 2. Use in Python

```python
import geopandas as gpd

# Load GeoJSON
gdf = gpd.read_file("hms_subbasins.geojson")

# View data
print(gdf.head())

# Filter high imperviousness areas
urban = gdf[gdf['percent_impervious'] > 50]
print(f"Urban subbasins: {len(urban)}")
```

### 3. Convert to Other Formats

```bash
# Install GDAL (includes ogr2ogr)
# Then convert GeoJSON to other formats:

# To Shapefile
ogr2ogr -f "ESRI Shapefile" output.shp input.geojson

# To KML (Google Earth)
ogr2ogr -f "KML" output.kml input.geojson

# To GeoPackage
ogr2ogr -f "GPKG" output.gpkg input.geojson
```

## File Structure

```
C:\GH\hms-commander\
├── __init__.py              # Package initialization
├── HmsGeo.py                # Main class (all extraction methods)
├── README.md                # Project overview
├── AGENTS.md                # For AI coding assistants
├── QUICK_REFERENCE.md       # Quick API reference
├── GETTING_STARTED.md       # This file
├── pyproject.toml           # Package configuration
├── test_extraction.py       # Test script
└── examples/
    └── extract_example.py   # Detailed usage examples
```

## Common Workflows

### Workflow 1: Basic Extraction (Just Point Features)

```python
from HmsGeo import HmsGeo

# Parse basin file only
subs, juncs, reachs = HmsGeo.parse_basin_file("model.basin")

# Export to GeoJSON
HmsGeo.create_geojson_subbasins(subs, "subbasins.geojson")
HmsGeo.create_geojson_junctions(juncs, "junctions.geojson")
HmsGeo.create_geojson_reaches(reachs, "reaches.geojson")
```

**Time:** ~5 seconds
**Output:** 3 GeoJSON files with points and simple lines

### Workflow 2: Detailed Extraction (Polygons & Polylines)

```python
from HmsGeo import HmsGeo

# Parse MAP file
map_data = HmsGeo.parse_map_file("model.map")

# Export detailed geometry
HmsGeo.create_geojson_boundaries(
    map_data['boundaries'],
    "watershed_boundaries.geojson"
)

HmsGeo.create_geojson_rivers(
    map_data['rivers'],
    "stream_network.geojson"
)
```

**Time:** ~30 seconds (large files)
**Output:** High-resolution polygons and stream network

### Workflow 3: Everything (One Command)

```python
from HmsGeo import HmsGeo

# Extract everything
outputs = HmsGeo.extract_all_gis(
    basin_path="model.basin",
    geo_path="model.geo",
    map_path="model.map",
    output_dir="./gis"
)
```

**Time:** ~45 seconds
**Output:** Complete GIS representation of HMS model

## Troubleshooting

### Issue: "File not found"
- Check file paths use forward slashes: `C:/path/to/file`
- Or use raw strings: `r"C:\path\to\file"`
- Verify files exist: `Path("file.basin").exists()`

### Issue: Missing coordinates
- HMS models may store coords in .basin OR .geo file
- Solution: Parse both and merge (see examples/extract_example.py)

### Issue: Large file taking long time
- .map files with detailed geometry can be large
- Solution: Be patient, or extract basin file only first

### Issue: Wrong coordinate system
- Default is EPSG:2278 (Texas South Central)
- Solution: Specify custom CRS with `crs_epsg` parameter

## Learning Resources

1. **Quick Reference**: `QUICK_REFERENCE.md` - Common operations
2. **Examples**: `examples/extract_example.py` - 5 detailed examples
3. **API Docs**: `AGENTS.md` - Complete method documentation
4. **Test Script**: `test_extraction.py` - Verify everything works

## Getting Help

### Check Documentation
- `README.md` - Project overview
- `QUICK_REFERENCE.md` - Common operations
- `AGENTS.md` - Detailed API reference

### Common Questions

**Q: Do I need to install anything besides Python?**
A: No! hms-commander uses only Python standard library.

**Q: What Python version do I need?**
A: Python 3.8 or newer.

**Q: Can I use this with HEC-RAS models?**
A: No, use [ras-commander](https://github.com/[org]/ras-commander) for HEC-RAS.

**Q: What's the difference between .basin and .map files?**
A: .basin has basic points and attributes. .map has detailed polygons.

**Q: Can I convert GeoJSON to Shapefile?**
A: Yes! Use `ogr2ogr` or `geopandas` (see "Convert to Other Formats" above).

**Q: Does this work on Mac/Linux?**
A: Yes! Python is cross-platform.

## Example: Complete Workflow

Here's a complete example from start to finish:

```python
# 1. Import
from HmsGeo import HmsGeo
import logging

# 2. Enable logging (optional but recommended)
logging.basicConfig(level=logging.INFO)

# 3. Extract everything
outputs = HmsGeo.extract_all_gis(
    basin_path="C:/HCFCD/A100_B100/Ph1_1PCT.basin",
    geo_path="C:/HCFCD/A100_B100/A100-GEO.geo",
    map_path="C:/HCFCD/A100_B100/A100-MAP.map",
    output_dir="C:/HCFCD/A100_B100/gis_output"
)

# 4. Print results
print(f"\nGenerated {len(outputs)} GeoJSON files:")
for key, path in outputs.items():
    print(f"  {key}: {path}")

# 5. Load in geopandas (optional)
import geopandas as gpd
gdf = gpd.read_file(outputs['subbasins'])
print(f"\nLoaded {len(gdf)} subbasins")
print(f"Total drainage area: {gdf['area'].sum():.1f} sq mi")
```

## Success! What's Next?

Once you've extracted your HMS model to GIS:

1. ✅ **Visualize** - View in QGIS/ArcGIS
2. ✅ **Analyze** - Spatial analysis with your HMS results
3. ✅ **Share** - Include in reports and presentations
4. ✅ **Integrate** - Combine with other GIS data
5. ✅ **Automate** - Batch process multiple models

## Related Projects

- **ras-commander** - HEC-RAS automation (same author, same style)
- **HEC-HMS** - U.S. Army Corps hydrologic modeling software

---

**Ready to get started?** Run `python test_extraction.py` and open your first GeoJSON in QGIS!
