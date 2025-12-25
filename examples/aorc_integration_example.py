"""
AORC Integration Example - HmsHuc, HmsAorc, HmsGrid Workflow

Demonstrates the complete workflow for integrating AORC precipitation data
with HMS using HUC watershed boundaries.

This example shows:
1. Downloading HUC12 watersheds for project area (HmsHuc)
2. Downloading AORC precipitation data (HmsAorc - coming in Phase 2)
3. Mapping AORC grid cells to HUC watersheds (HmsGrid - coming in Phase 3)
4. Generating HMS grid definition files (HmsGrid)
5. Configuring HMS met models for gridded precipitation

Status:
    Phase 1 (Current): HmsHuc is fully implemented and tested
    Phase 2 (Next): HmsAorc download and DSS conversion
    Phase 3 (Future): HmsGrid spatial operations
"""

from hms_commander import HmsHuc, HmsAorc, HmsGrid
from pathlib import Path


def example_huc_download():
    """Example 1: Download HUC watersheds for project area."""

    print("=" * 70)
    print("Example 1: Download HUC12 Watersheds")
    print("=" * 70)

    # Define project bounds (Bald Eagle Creek, PA)
    bounds = (-77.71, 41.01, -77.25, 41.22)  # west, south, east, north

    # Download HUC12 watersheds
    watersheds = HmsHuc.get_huc12_for_bounds(bounds)

    print(f"\nDownloaded {len(watersheds)} HUC12 watersheds")
    print("\nWatershed Summary:")
    print(watersheds[['huc12', 'name', 'areasqkm']].to_string(index=False))

    # Save for later use
    output_dir = Path("huc_watersheds")
    output_dir.mkdir(exist_ok=True)

    watersheds.to_file(output_dir / "huc12_watersheds.geojson", driver="GeoJSON")
    print(f"\nSaved to: {output_dir / 'huc12_watersheds.geojson'}")

    return watersheds


def example_aorc_workflow_planned():
    """Example 2: Complete AORC workflow (planned for Phase 2-3)."""

    print("\n" + "=" * 70)
    print("Example 2: Complete AORC Workflow (Planned)")
    print("=" * 70)

    # This shows the intended API - not yet implemented
    print("\nPlanned workflow (coming in Phase 2-3):")
    print("""
# 1. Download HUC12 watersheds (WORKING NOW!)
from hms_commander import HmsHuc
bounds = (-77.71, 41.01, -77.25, 41.22)
watersheds = HmsHuc.get_huc12_for_bounds(bounds)

# 2. Download AORC precipitation (Phase 2)
from hms_commander import HmsAorc
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
from hms_commander import HmsGrid
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
from hms_commander import HmsMet
HmsMet.set_gridded_precipitation("model.met", "AORC_May2020")

# 7. Run HMS simulation
from hms_commander import HmsCmdr
HmsCmdr.compute_run("AORC_May2020_Run")
    """)


def example_huc_info():
    """Example 3: Get HUC level information."""

    print("\n" + "=" * 70)
    print("Example 3: HUC Level Information")
    print("=" * 70)

    info = HmsHuc.get_huc_info()

    print("\nAvailable HUC Levels:")
    for level, data in info.items():
        print(f"\n{level.upper()}:")
        print(f"  Name: {data['name']}")
        print(f"  Description: {data['description']}")
        print(f"  Typical Size: {data['typical_size']}")
        print(f"  CONUS Count: {data['conus_count']}")
        print(f"  Example: {data['example']}")


def example_get_by_id():
    """Example 4: Download specific HUC by ID."""

    print("\n" + "=" * 70)
    print("Example 4: Download Specific HUC by ID")
    print("=" * 70)

    # Download specific HUC12
    huc_ids = ["020502030404"]  # Baker Run (from our test)

    watershed = HmsHuc.get_huc_by_ids("huc12", huc_ids)

    print(f"\nDownloaded {len(watershed)} watershed")
    print("\nWatershed Details:")
    print(f"  HUC12: {watershed.iloc[0]['huc12']}")
    print(f"  Name: {watershed.iloc[0]['name']}")
    print(f"  Area: {watershed.iloc[0]['areasqkm']:.2f} km²")
    print(f"  States: {watershed.iloc[0]['states']}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("HMS Commander AORC Integration Examples")
    print("=" * 70)
    print("\nPhase 1: HmsHuc (HUC Watershed Operations) - IMPLEMENTED")
    print("Phase 2: HmsAorc (AORC Download) - PLANNED")
    print("Phase 3: HmsGrid (Grid Cell Mapping) - PLANNED")
    print()

    # Run examples
    try:
        # Example 1: Download HUC12 watersheds (WORKING)
        watersheds = example_huc_download()

        # Example 2: Show planned AORC workflow
        example_aorc_workflow_planned()

        # Example 3: HUC level information
        example_huc_info()

        # Example 4: Download by ID
        example_get_by_id()

        print("\n" + "=" * 70)
        print("Examples Complete!")
        print("=" * 70)
        print("\nPhase 1 (HmsHuc) is working and ready to use.")
        print("Phase 2-3 (HmsAorc, HmsGrid) coming soon.")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
