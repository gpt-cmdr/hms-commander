"""Tests for TauDEM watershed verification."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, box

from hms_commander import HmsTerrain, HmsWatershedVerification


@pytest.mark.requires_gis
def test_verify_taudem_run_writes_expected_metrics_with_crs_fallback(tmp_path):
    reference_path = tmp_path / "reference.geojson"
    run_root = tmp_path / "taudem_run"
    run_root.mkdir(parents=True, exist_ok=True)

    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 100, 100)], crs="EPSG:5070")
    reference.to_file(reference_path, driver="GeoJSON")

    watershed_path = run_root / "w.tif"
    watershed_array = np.zeros((10, 10), dtype="int32")
    watershed_array[2:, 2:] = 1
    with rasterio.open(
        watershed_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs="EPSG:5070",
        transform=from_origin(0, 100, 10, 10),
        nodata=-9999,
    ) as dst:
        dst.write(watershed_array, 1)

    outlet = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(90, 90)], crs="EPSG:5070")
    outlet.to_file(run_root / "outlet.shp")
    (run_root / "outlet.prj").unlink()

    outlet_snapped = gpd.GeoDataFrame({"id": [1], "Dist_moved": [22.361]}, geometry=[Point(80, 70)], crs="EPSG:5070")
    outlet_snapped.to_file(run_root / "outlet_snapped.shp")
    (run_root / "outlet_snapped.prj").unlink()

    streams = gpd.GeoDataFrame(
        {"strmOrder": [1, 2]},
        geometry=[LineString([(20, 20), (20, 80)]), LineString([(20, 80), (80, 80)])],
        crs="EPSG:5070",
    )
    streams.to_file(run_root / "net.shp")
    (run_root / "net.prj").unlink()

    result = HmsWatershedVerification.verify_taudem_run(
        run_root=run_root,
        reference_boundary_path=reference_path,
        study_name="Synthetic Verification",
        site_id="05555500",
    )

    artifact_path = run_root / "boundary_verification.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert artifact_path.exists()
    assert artifact["study_name"] == "Synthetic Verification"
    assert artifact["site_id"] == "05555500"
    assert artifact["metrics"]["reference_basin_area_m2"] == 10000.0
    assert artifact["metrics"]["taudem_basin_area_m2"] == 6400.0
    assert artifact["metrics"]["absolute_area_difference_m2"] == 3600.0
    assert artifact["metrics"]["percent_area_difference"] == -36.0
    assert artifact["metrics"]["polygon_overlap"]["intersection_over_union"] == 0.64
    assert artifact["metrics"]["polygon_overlap"]["reference_coverage_ratio"] == 0.64
    assert artifact["metrics"]["polygon_overlap"]["taudem_coverage_ratio"] == 1.0
    assert artifact["metrics"]["outlet"]["snap_distance_m"] == 22.361
    assert artifact["metrics"]["outlet"]["original_outlet"]["inside_reference_boundary"] is True
    assert artifact["metrics"]["outlet"]["snapped_outlet"]["inside_taudem_boundary"] is True
    assert artifact["metrics"]["stream_network"]["feature_count"] == 2
    assert artifact["metrics"]["stream_network"]["total_length_m"] == 120.0
    assert artifact["metrics"]["stream_network"]["max_stream_order"] == 2
    assert artifact["metrics"]["stream_network"]["stream_order_counts"] == {"1": 1, "2": 1}


@pytest.mark.requires_gis
def test_create_taudem_run_figures_writes_pngs_and_manifest(tmp_path):
    reference_path = tmp_path / "reference.geojson"
    run_root = tmp_path / "taudem_run"
    output_dir = tmp_path / "verification_figures"
    run_root.mkdir(parents=True, exist_ok=True)

    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 100, 100)], crs="EPSG:5070")
    reference.to_file(reference_path, driver="GeoJSON")

    transform = from_origin(0, 100, 10, 10)

    watershed_path = run_root / "w.tif"
    watershed_array = np.zeros((10, 10), dtype="int32")
    watershed_array[1:9, 1:9] = 1
    with rasterio.open(
        watershed_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs="EPSG:5070",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(watershed_array, 1)

    fel_path = run_root / "fel.tif"
    fel_array = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(
        fel_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:5070",
        transform=transform,
        nodata=-9999.0,
    ) as dst:
        dst.write(fel_array, 1)

    ad8_path = run_root / "ad8.tif"
    ad8_array = np.ones((10, 10), dtype="float32")
    ad8_array[2:8, 2:8] = np.arange(1, 37, dtype="float32").reshape(6, 6)
    with rasterio.open(
        ad8_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:5070",
        transform=transform,
        nodata=0.0,
    ) as dst:
        dst.write(ad8_array, 1)

    src_path = run_root / "src.tif"
    src_array = np.zeros((10, 10), dtype="int32")
    src_array[2:8, 4] = 1
    src_array[6, 4:8] = 1
    with rasterio.open(
        src_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs="EPSG:5070",
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(src_array, 1)

    outlet = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 80)], crs="EPSG:5070")
    outlet.to_file(run_root / "outlet.shp")
    (run_root / "outlet.prj").unlink()

    outlet_snapped = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 80)], crs="EPSG:5070")
    outlet_snapped.to_file(run_root / "outlet_snapped.shp")
    (run_root / "outlet_snapped.prj").unlink()

    streams = gpd.GeoDataFrame(
        {"strmOrder": [1, 2]},
        geometry=[LineString([(20, 20), (20, 80)]), LineString([(20, 80), (80, 80)])],
        crs="EPSG:5070",
    )
    streams.to_file(run_root / "net.shp")
    (run_root / "net.prj").unlink()

    result = HmsWatershedVerification.create_taudem_run_figures(
        run_root=run_root,
        reference_boundary_path=reference_path,
        output_dir=output_dir,
        study_name="Synthetic Figures",
        site_id="05555500",
    )

    outlet_figure = output_dir / "outlet_boundary_mismatch.png"
    overview_figure = output_dir / "taudem_outputs_overview.png"
    manifest_path = output_dir / "figure_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert outlet_figure.exists()
    assert overview_figure.exists()
    assert manifest_path.exists()
    assert outlet_figure.stat().st_size > 0
    assert overview_figure.stat().st_size > 0
    assert manifest["study_name"] == "Synthetic Figures"
    assert manifest["site_id"] == "05555500"
    assert manifest["figures"]["outlet_boundary_mismatch"]["path"] == str(outlet_figure)
    assert manifest["figures"]["taudem_outputs_overview"]["path"] == str(overview_figure)
    assert manifest["metrics_summary"]["absolute_percent_area_difference"] == 36.0


@pytest.mark.requires_gis
def test_audit_crs_alignment_reports_declared_and_resolved_crs(tmp_path):
    reference_path = tmp_path / "reference.geojson"
    run_root = tmp_path / "taudem_run"
    run_root.mkdir(parents=True, exist_ok=True)

    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 100, 100)], crs="EPSG:5070")
    reference.to_file(reference_path, driver="GeoJSON")

    watershed_path = run_root / "w.tif"
    watershed_array = np.zeros((10, 10), dtype="int32")
    watershed_array[1:9, 1:9] = 1
    with rasterio.open(
        watershed_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs="EPSG:5070",
        transform=from_origin(0, 100, 10, 10),
        nodata=0,
    ) as dst:
        dst.write(watershed_array, 1)

    dem_path = run_root / "dem.tif"
    dem_array = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:5070",
        transform=from_origin(0, 100, 10, 10),
        nodata=-9999.0,
    ) as dst:
        dst.write(dem_array, 1)

    outlet = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 50)], crs="EPSG:5070")
    outlet.to_file(run_root / "outlet.shp")

    outlet_snapped = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 50)], crs="EPSG:5070")
    outlet_snapped.to_file(run_root / "outlet_snapped.shp")
    (run_root / "outlet_snapped.prj").unlink()

    streams = gpd.GeoDataFrame(
        {"strmOrder": [2]},
        geometry=[LineString([(50, 20), (50, 80)])],
        crs="EPSG:5070",
    )
    streams.to_file(run_root / "net.shp")
    (run_root / "net.prj").unlink()

    gauge = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(80, 50)], crs="EPSG:5070")
    gauge_path = tmp_path / "gauge.geojson"
    gauge.to_file(gauge_path, driver="GeoJSON")

    output_path = tmp_path / "crs_alignment_audit.json"
    result = HmsWatershedVerification.audit_crs_alignment(
        reference_boundary_path=reference_path,
        output_path=output_path,
        dem_path=dem_path,
        taudem_watershed_raster_path=watershed_path,
        original_outlet_path=run_root / "outlet.shp",
        snapped_outlet_path=run_root / "outlet_snapped.shp",
        stream_network_path=run_root / "net.shp",
        gauge_point_path=gauge_path,
        study_name="Synthetic CRS audit",
        site_id="05555500",
    )

    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert output_path.exists()
    assert artifact["study_name"] == "Synthetic CRS audit"
    assert artifact["datasets"]["reference_boundary"]["declared_crs"] == "EPSG:5070"
    assert artifact["datasets"]["dem"]["declared_crs"] == "EPSG:5070"
    assert artifact["datasets"]["snapped_outlet"]["declared_crs"] is None
    assert artifact["datasets"]["snapped_outlet"]["resolved_crs"] == "EPSG:5070"
    assert artifact["datasets"]["stream_network"]["declared_crs"] is None
    assert artifact["datasets"]["stream_network"]["resolved_crs"] == "EPSG:5070"
    assert artifact["datasets"]["original_outlet"]["first_point_in_verification_crs"] == {"x": 120.0, "y": 50.0}
    assert "lon" in artifact["datasets"]["original_outlet"]["first_point_in_wgs84"]
    assert artifact["comparisons"]["original_outlet_vs_reference_boundary"] == {
        "inside_reference_boundary_verification_crs": False,
        "inside_reference_boundary_wgs84": False,
        "distance_to_reference_boundary_m": 20.0,
    }
    assert artifact["comparisons"]["original_outlet_vs_dem_bounds"] == {
        "inside_dem_bounds_verification_crs": False,
        "inside_dem_bounds_wgs84": False,
        "distance_to_dem_bounds_m": 20.0,
    }
    assert artifact["comparisons"]["original_vs_snapped_outlet"]["distance_m"] == 0.0
    assert artifact["comparisons"]["original_outlet_vs_gauge_point"]["distance_m"] == 40.0


@pytest.mark.requires_gis
def test_create_crs_alignment_figure_writes_png_and_manifest(tmp_path):
    reference_path = tmp_path / "reference.geojson"
    run_root = tmp_path / "taudem_run"
    run_root.mkdir(parents=True, exist_ok=True)

    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 100, 100)], crs="EPSG:5070")
    reference.to_file(reference_path, driver="GeoJSON")

    watershed_path = run_root / "w.tif"
    watershed_array = np.zeros((10, 10), dtype="int32")
    watershed_array[1:9, 1:9] = 1
    with rasterio.open(
        watershed_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs="EPSG:5070",
        transform=from_origin(0, 100, 10, 10),
        nodata=0,
    ) as dst:
        dst.write(watershed_array, 1)

    dem_path = run_root / "dem.tif"
    dem_array = np.arange(100, dtype="float32").reshape(10, 10)
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:5070",
        transform=from_origin(0, 100, 10, 10),
        nodata=-9999.0,
    ) as dst:
        dst.write(dem_array, 1)

    outlet = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 50)], crs="EPSG:5070")
    outlet.to_file(run_root / "outlet.shp")

    outlet_snapped = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(120, 50)], crs="EPSG:5070")
    outlet_snapped.to_file(run_root / "outlet_snapped.shp")
    (run_root / "outlet_snapped.prj").unlink()

    streams = gpd.GeoDataFrame(
        {"strmOrder": [2]},
        geometry=[LineString([(50, 20), (50, 80)])],
        crs="EPSG:5070",
    )
    streams.to_file(run_root / "net.shp")
    (run_root / "net.prj").unlink()

    gauge = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(80, 50)], crs="EPSG:5070")
    gauge_path = tmp_path / "gauge.geojson"
    gauge.to_file(gauge_path, driver="GeoJSON")

    figure_path = tmp_path / "gauge_outlet_dem_context.png"
    manifest_path = tmp_path / "gauge_outlet_dem_context_manifest.json"
    result = HmsWatershedVerification.create_crs_alignment_figure(
        reference_boundary_path=reference_path,
        output_path=figure_path,
        manifest_path=manifest_path,
        dem_path=dem_path,
        taudem_watershed_raster_path=watershed_path,
        original_outlet_path=run_root / "outlet.shp",
        snapped_outlet_path=run_root / "outlet_snapped.shp",
        stream_network_path=run_root / "net.shp",
        gauge_point_path=gauge_path,
        study_name="Synthetic CRS context figure",
        site_id="05555500",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert figure_path.exists()
    assert manifest_path.exists()
    assert figure_path.stat().st_size > 0
    assert manifest["study_name"] == "Synthetic CRS context figure"
    assert manifest["site_id"] == "05555500"
    assert manifest["figure"]["path"] == str(figure_path)
    assert manifest["summary"]["original_outlet_vs_gauge_point"]["distance_m"] == 40.0


@pytest.mark.requires_gis
def test_derive_taudem_boundary_outlet_selects_mainstem_crossing_nearest_seed(tmp_path):
    run_root = tmp_path / "taudem_run"
    streams_path = run_root / "net.shp"
    seed_path = tmp_path / "seed.geojson"
    output_path = tmp_path / "derived_taudem_boundary_outlet.geojson"
    run_root.mkdir(parents=True, exist_ok=True)

    watershed_path = run_root / "w.tif"
    watershed_array = np.zeros((10, 10), dtype="int32")
    watershed_array[1:9, 1:9] = 1
    local_conus_albers = (
        'LOCAL_CS["NAD83 / Conus Albers",UNIT["metre",1],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'
    )
    with rasterio.open(
        watershed_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="int32",
        crs=local_conus_albers,
        transform=from_origin(0, 100, 10, 10),
        nodata=0,
    ) as dst:
        dst.write(watershed_array, 1)

    streams = gpd.GeoDataFrame(
        {"strmOrder": [4, 2]},
        geometry=[
            LineString([(50, 140), (50, 60), (50, -20)]),
            LineString([(20, 80), (20, 30)]),
        ],
        crs="EPSG:5070",
    )
    streams.to_file(streams_path)
    (run_root / "net.prj").unlink()

    seed = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(50, -25)], crs="EPSG:5070")
    seed.to_file(seed_path, driver="GeoJSON")

    result = HmsTerrain.derive_taudem_boundary_outlet(
        stream_network_path=streams_path,
        taudem_watershed_raster_path=watershed_path,
        output_path=output_path,
        seed_outlet_path=seed_path,
        study_name="Synthetic TauDEM boundary outlet",
        site_id="05555500",
    )

    derived = gpd.read_file(output_path).to_crs("EPSG:5070")
    point = derived.geometry.iloc[0]

    assert result["status"] == "completed"
    assert result["selection"]["selection_method"] == "nearest_seed_outlet"
    assert result["selection"]["selected_stream_order"] == 4
    assert result["selection"]["boundary_crossing_count"] == 2
    assert result["selection"]["selected_outlet"]["distance_to_seed_m"] == 35.0
    assert round(float(point.x), 3) == 50.0
    assert round(float(point.y), 3) == 10.0


@pytest.mark.requires_gis
def test_derive_boundary_outlet_selects_mainstem_crossing_nearest_seed(tmp_path):
    reference_path = tmp_path / "reference.geojson"
    streams_path = tmp_path / "net.shp"
    seed_path = tmp_path / "seed.geojson"
    output_path = tmp_path / "derived_boundary_outlet.geojson"

    reference = gpd.GeoDataFrame({"id": [1]}, geometry=[box(0, 0, 100, 100)], crs="EPSG:5070")
    reference.to_file(reference_path, driver="GeoJSON")

    streams = gpd.GeoDataFrame(
        {"strmOrder": [4, 2]},
        geometry=[
            LineString([(50, 140), (50, 60), (50, -20)]),
            LineString([(20, 80), (20, 30)]),
        ],
        crs="EPSG:5070",
    )
    streams.to_file(streams_path)
    (tmp_path / "net.prj").unlink()

    seed = gpd.GeoDataFrame({"id": [1]}, geometry=[Point(50, -25)], crs="EPSG:5070")
    seed.to_file(seed_path, driver="GeoJSON")

    result = HmsTerrain.derive_boundary_outlet(
        reference_boundary_path=reference_path,
        stream_network_path=streams_path,
        output_path=output_path,
        seed_outlet_path=seed_path,
        study_name="Synthetic boundary outlet",
        site_id="05555500",
    )

    derived = gpd.read_file(output_path).to_crs("EPSG:5070")
    point = derived.geometry.iloc[0]

    assert result["status"] == "completed"
    assert result["selection"]["selection_method"] == "nearest_seed_outlet"
    assert result["selection"]["selected_stream_order"] == 4
    assert result["selection"]["boundary_crossing_count"] == 2
    assert result["selection"]["selected_outlet"]["distance_to_seed_m"] == 25.0
    assert round(float(point.x), 3) == 50.0
    assert round(float(point.y), 3) == 0.0
