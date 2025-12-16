"""
Example: Extract GIS data from HEC-HMS model files

This example demonstrates how to extract geospatial data from HEC-HMS
model files and export to GeoJSON format.
"""

import sys
from pathlib import Path
import logging

# Add parent directory to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent))

from HmsGeo import HmsGeo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def example_extract_all():
    """
    Example 1: Extract all GIS data with one method call.

    This is the simplest approach - provide paths to your HMS files
    and let HmsGeo extract everything.
    """
    print("\n" + "="*70)
    print("Example 1: Extract All GIS Data")
    print("="*70)

    # File paths (update these to your actual model files)
    basin_path = "C:/HCFCD/Models/A100_B100/Ph1_1PCT.basin"
    geo_path = "C:/HCFCD/Models/A100_B100/A100-GEO.geo"
    map_path = "C:/HCFCD/Models/A100_B100/A100-MAP.map"
    output_dir = "C:/HCFCD/Models/A100_B100/gis_output"

    # Extract all GIS data
    outputs = HmsGeo.extract_all_gis(
        basin_path=basin_path,
        geo_path=geo_path,
        map_path=map_path,
        output_dir=output_dir
    )

    # Print output file locations
    print("\nGenerated GeoJSON files:")
    for key, path in outputs.items():
        print(f"  {key}: {path}")


def example_extract_basin_only():
    """
    Example 2: Extract only basin file data (subbasins, junctions, reaches).

    Use this when you only need basic point and line features without
    detailed polygons and river networks.
    """
    print("\n" + "="*70)
    print("Example 2: Extract Basin File Only")
    print("="*70)

    basin_path = "C:/HCFCD/Models/A100_B100/Ph1_1PCT.basin"
    output_dir = Path("C:/HCFCD/Models/A100_B100/gis_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse basin file
    subbasins, junctions, reaches = HmsGeo.parse_basin_file(basin_path)

    print(f"\nFound:")
    print(f"  Subbasins: {len(subbasins)}")
    print(f"  Junctions: {len(junctions)}")
    print(f"  Reaches: {len(reaches)}")

    # Export each type
    HmsGeo.create_geojson_subbasins(
        subbasins,
        output_dir / "subbasins.geojson"
    )

    HmsGeo.create_geojson_junctions(
        junctions,
        output_dir / "junctions.geojson"
    )

    HmsGeo.create_geojson_reaches(
        reaches,
        output_dir / "reaches.geojson"
    )

    print("\nExported 3 GeoJSON files")


def example_extract_detailed_geometry():
    """
    Example 3: Extract detailed polygons and stream networks from .map file.

    The .map file contains much more detailed geometry than .basin or .geo files.
    Use this when you need high-resolution watershed boundaries and stream networks.
    """
    print("\n" + "="*70)
    print("Example 3: Extract Detailed Geometry from MAP File")
    print("="*70)

    map_path = "C:/HCFCD/Models/A100_B100/A100-MAP.map"
    output_dir = Path("C:/HCFCD/Models/A100_B100/gis_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse MAP file
    map_data = HmsGeo.parse_map_file(map_path)

    boundaries = map_data['boundaries']
    rivers = map_data['rivers']

    print(f"\nFound:")
    print(f"  Boundary polygons: {len(boundaries)}")
    print(f"  River polylines: {len(rivers)}")

    # Calculate statistics
    total_boundary_vertices = sum(len(b['coordinates']) for b in boundaries)
    total_river_vertices = sum(len(r['coordinates']) for r in rivers)

    print(f"\nDetail level:")
    print(f"  Boundary vertices: {total_boundary_vertices:,}")
    print(f"  Avg vertices per boundary: {total_boundary_vertices / len(boundaries):.1f}")
    print(f"  River vertices: {total_river_vertices:,}")
    print(f"  Avg vertices per river segment: {total_river_vertices / len(rivers):.1f}")

    # Export detailed geometry
    HmsGeo.create_geojson_boundaries(
        boundaries,
        output_dir / "watershed_boundaries.geojson"
    )

    HmsGeo.create_geojson_rivers(
        rivers,
        output_dir / "stream_network.geojson"
    )

    print("\nExported detailed geometry GeoJSON files")


def example_inspect_data():
    """
    Example 4: Parse and inspect data without exporting.

    Useful for quality control, debugging, or custom processing.
    """
    print("\n" + "="*70)
    print("Example 4: Inspect Parsed Data")
    print("="*70)

    basin_path = "C:/HCFCD/Models/A100_B100/Ph1_1PCT.basin"

    # Parse basin file
    subbasins, junctions, reaches = HmsGeo.parse_basin_file(basin_path)

    # Inspect first subbasin
    first_subbasin_name = list(subbasins.keys())[0]
    first_subbasin = subbasins[first_subbasin_name]

    print(f"\nFirst subbasin: {first_subbasin_name}")
    print(f"  Coordinates: ({first_subbasin.get('x')}, {first_subbasin.get('y')})")
    print(f"  Area: {first_subbasin.get('area')} sq mi")
    print(f"  Imperviousness: {first_subbasin.get('percent_impervious')}%")
    print(f"  Time of Concentration: {first_subbasin.get('time_of_concentration')} hr")
    print(f"  Downstream: {first_subbasin.get('downstream')}")

    # Find subbasins with high imperviousness
    high_imperv = {
        name: data['percent_impervious']
        for name, data in subbasins.items()
        if data.get('percent_impervious', 0) > 50
    }

    print(f"\nSubbasins with >50% imperviousness: {len(high_imperv)}")
    for name, imperv in sorted(high_imperv.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {name}: {imperv}%")


def example_custom_crs():
    """
    Example 5: Use a custom coordinate reference system.

    Default is EPSG:2278 (Texas South Central), but you can specify any CRS.
    """
    print("\n" + "="*70)
    print("Example 5: Custom Coordinate System")
    print("="*70)

    basin_path = "C:/HCFCD/Models/A100_B100/Ph1_1PCT.basin"
    output_dir = Path("C:/HCFCD/Models/A100_B100/gis_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse data
    subbasins, _, _ = HmsGeo.parse_basin_file(basin_path)

    # Export with custom CRS (example: UTM Zone 15N)
    custom_crs = "urn:ogc:def:crs:EPSG::32615"  # UTM Zone 15N

    HmsGeo.create_geojson_subbasins(
        subbasins,
        output_dir / "subbasins_utm15n.geojson",
        crs_epsg=custom_crs
    )

    print(f"\nExported with CRS: {custom_crs}")
    print("Note: Coordinate values are still in original units.")
    print("For coordinate transformation, use a tool like ogr2ogr or geopandas.")


def main():
    """
    Run all examples.

    Uncomment the examples you want to run.
    """
    print("\n" + "="*70)
    print("HEC-HMS GIS Extraction Examples")
    print("="*70)
    print("\nNote: Update file paths in each example before running!")

    # Run examples (uncomment as needed)
    try:
        # example_extract_all()
        # example_extract_basin_only()
        # example_extract_detailed_geometry()
        # example_inspect_data()
        # example_custom_crs()

        print("\n" + "="*70)
        print("Examples Complete!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Update file paths in examples")
        print("  2. Uncomment examples you want to run")
        print("  3. Open output GeoJSON files in QGIS or ArcGIS")

    except FileNotFoundError as e:
        print(f"\n❌ Error: File not found - {e}")
        print("Please update the file paths in the example code.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
