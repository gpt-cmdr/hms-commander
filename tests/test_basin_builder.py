"""Tests for TauDEM-to-HMS basin assembly."""

from __future__ import annotations

import json
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

from hms_commander import HmsBasinBuilder, HmsPrj, HmsSqlite


@pytest.mark.requires_gis
def test_build_taudem_hms_spec_from_fixture_returns_deterministic_counts(
    spring_creek_taudem_fixture_root,
):
    fixture_root = Path(spring_creek_taudem_fixture_root)
    spec = HmsBasinBuilder.build_taudem_hms_spec(fixture_root)

    assert not (fixture_root / "04_terrain" / "taudem_work" / "net.prj").exists()
    assert spec["counts"] == {"subbasins": 60, "reaches": 60, "junctions": 29, "sinks": 1}
    assert spec["crs"]["epsg"] == "EPSG:5070"
    assert spec["outlet"]["source"] == "artifact"
    assert spec["outlet"]["name"] == "Sink_001"
    assert [item["name"] for item in spec["subbasins"][:5]] == [
        "SB_0",
        "SB_1",
        "SB_2",
        "SB_4",
        "SB_5",
    ]
    assert [item["name"] for item in spec["junctions"][:5]] == [
        "J_20",
        "J_24",
        "J_28",
        "J_32",
        "J_36",
    ]
    assert spec["network_checks"]["terminal_link_names"] == ["R_22", "R_56"]
    assert spec["network_checks"]["junction_fallback_count"] == 29


@pytest.mark.requires_gis
def test_build_taudem_hms_spec_closes_subbasin_areas_and_assigns_sink(
    spring_creek_taudem_fixture_root,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)

    subbasin_area_sum = sum(item["area_m2"] for item in spec["subbasins"])

    assert subbasin_area_sum == pytest.approx(spec["network_checks"]["taudem_basin_area_m2"])
    assert spec["network_checks"]["area_closure_error_m2"] == pytest.approx(0.0)
    assert spec["network_checks"]["area_closure_error_pct"] == pytest.approx(0.0)
    assert spec["sink"]["name"] == "Sink_001"
    assert spec["sink"]["upstream_reaches"] == ["R_22", "R_56"]
    assert spec["sink"]["source"] == "artifact"


@pytest.mark.requires_gis
def test_build_taudem_hms_spec_canonicalizes_unit_system(
    spring_creek_taudem_fixture_root,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(
        spring_creek_taudem_fixture_root,
        unit_system="imperial",
    )

    assert spec["unit_system"] == "English"


@pytest.mark.requires_gis
def test_build_taudem_hms_spec_derives_boundary_handoff_outlet_when_artifact_is_missing(
    tmp_spring_creek_taudem_fixture,
):
    fixture_root = Path(tmp_spring_creek_taudem_fixture)
    outlet_artifact = (
        fixture_root
        / "09_taudem_verification"
        / "taudem_boundary_handoff_outlet.geojson"
    )
    outlet_artifact.unlink()

    spec = HmsBasinBuilder.build_taudem_hms_spec(fixture_root)

    assert spec["outlet"]["source"] == "derived"
    assert spec["outlet"]["x"] == pytest.approx(531443.987, abs=1.0)
    assert spec["outlet"]["y"] == pytest.approx(1883487.629, abs=1.0)


@pytest.mark.requires_gis
def test_export_taudem_hms_spec_writes_expected_artifacts(
    spring_creek_taudem_fixture_root,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    output_dir = tmp_path / "10_hms_handoff"

    paths = HmsBasinBuilder.export_taudem_hms_spec(spec, output_dir)

    expected_paths = {
        "spec": output_dir / "taudem_hms_spec.json",
        "subbasins_geojson": output_dir / "subbasins.geojson",
        "subbasins_csv": output_dir / "subbasins.csv",
        "reaches_geojson": output_dir / "reaches.geojson",
        "reaches_csv": output_dir / "reaches.csv",
        "junctions_geojson": output_dir / "junctions.geojson",
        "sink_geojson": output_dir / "sink.geojson",
        "assembly_report": output_dir / "assembly_report.json",
    }

    assert paths == expected_paths
    assert all(path.exists() for path in expected_paths.values())

    exported_spec = json.loads(expected_paths["spec"].read_text(encoding="utf-8"))
    assembly_report = json.loads(expected_paths["assembly_report"].read_text(encoding="utf-8"))
    subbasins_gdf = gpd.read_file(expected_paths["subbasins_geojson"])
    reaches_gdf = gpd.read_file(expected_paths["reaches_geojson"])
    junctions_gdf = gpd.read_file(expected_paths["junctions_geojson"])
    sink_gdf = gpd.read_file(expected_paths["sink_geojson"])
    subbasins_csv = pd.read_csv(expected_paths["subbasins_csv"])
    reaches_csv = pd.read_csv(expected_paths["reaches_csv"])

    assert exported_spec["counts"] == spec["counts"]
    assert assembly_report["counts"] == spec["counts"]
    assert len(subbasins_gdf) == 60
    assert len(reaches_gdf) == 60
    assert len(junctions_gdf) == 29
    assert len(sink_gdf) == 1
    assert len(subbasins_csv) == 60
    assert len(reaches_csv) == 60


@pytest.mark.requires_gis
def test_write_basin_scaffold_writes_sink_and_terminal_junction_variants(
    spring_creek_taudem_fixture_root,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)

    sink_path = tmp_path / "Spring_Creek_TauDEM_Sink.basin"
    junction_path = tmp_path / "Spring_Creek_TauDEM_Junction.basin"

    HmsBasinBuilder.write_basin_scaffold(
        spec=spec,
        basin_path=sink_path,
        basin_name="Spring Creek TauDEM Sink",
        terminal_node_mode="sink",
    )
    HmsBasinBuilder.write_basin_scaffold(
        spec=spec,
        basin_path=junction_path,
        basin_name="Spring Creek TauDEM Junction",
        terminal_node_mode="junction",
    )

    sink_content = sink_path.read_text(encoding="utf-8")
    junction_content = junction_path.read_text(encoding="utf-8")

    assert len(re.findall(r"^Subbasin:", sink_content, flags=re.MULTILINE)) == 60
    assert len(re.findall(r"^Reach:", sink_content, flags=re.MULTILINE)) == 60
    assert len(re.findall(r"^Junction:", sink_content, flags=re.MULTILINE)) == 29
    assert len(re.findall(r"^Sink:", sink_content, flags=re.MULTILINE)) == 1
    assert "Sink: Sink_001" in sink_content

    assert len(re.findall(r"^Subbasin:", junction_content, flags=re.MULTILINE)) == 60
    assert len(re.findall(r"^Reach:", junction_content, flags=re.MULTILINE)) == 60
    assert len(re.findall(r"^Junction:", junction_content, flags=re.MULTILINE)) == 30
    assert len(re.findall(r"^Sink:", junction_content, flags=re.MULTILINE)) == 0
    assert "Junction: Sink_001" in junction_content


@pytest.mark.requires_gis
def test_write_sqlite_geometry_roundtrips_through_hms_sqlite(
    spring_creek_taudem_fixture_root,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    sqlite_path = tmp_path / "Spring_Creek_TauDEM_Sink.sqlite"

    written_path = HmsBasinBuilder.write_sqlite_geometry(spec, sqlite_path)
    assert written_path == sqlite_path
    assert sqlite_path.exists()

    layer_info = HmsSqlite.list_layers(sqlite_path)
    layers = {
        row.table_name: (int(row.row_count), row.geometry_type)
        for row in layer_info.itertuples(index=False)
    }

    assert layers["subbasin2d"][0] == 60
    assert layers["reach2d"][0] == 60
    assert layers["subbasin"][0] == 60
    assert layers["reach"][0] == 60
    assert layers["junction"][0] == 29
    assert layers["sink"][0] == 1
    assert HmsSqlite.get_crs(sqlite_path)

    subbasins = HmsSqlite.get_subbasins(sqlite_path)
    reaches = HmsSqlite.get_reaches(sqlite_path)
    junctions = HmsSqlite.get_junctions(sqlite_path)
    all_layers = HmsSqlite.read_grid_database(sqlite_path, skip_empty=False)

    assert len(subbasins) == 60
    assert len(reaches) == 60
    assert len(junctions) == 29
    assert "sink" in all_layers
    assert len(all_layers["sink"]) == 1


@pytest.mark.requires_gis
def test_write_sqlite_geometry_honors_terminal_junction_mode(
    spring_creek_taudem_fixture_root,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    sqlite_path = tmp_path / "Spring_Creek_TauDEM_Junction.sqlite"

    HmsBasinBuilder.write_sqlite_geometry(
        spec,
        sqlite_path,
        terminal_node_mode="junction",
    )

    all_layers = HmsSqlite.read_grid_database(sqlite_path, skip_empty=False)
    assert len(all_layers["junction"]) == 30
    assert len(all_layers["sink"]) == 0
    assert "Sink_001" in all_layers["junction"]["name"].tolist()


@pytest.mark.requires_gis
def test_bootstrap_taudem_project_registers_real_hms_blocks(
    spring_creek_taudem_fixture_root,
    river_bend_example_dir,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    output_dir = tmp_path / "river_bend_bootstrap"

    paths = HmsBasinBuilder.bootstrap_taudem_project(
        spec=spec,
        template_project_dir=river_bend_example_dir,
        output_dir=output_dir,
        basin_name="Spring Creek TauDEM Sink",
        met_name="Spring Creek TauDEM Met",
        control_name="Spring Creek TauDEM Control",
        run_name="Spring Creek TauDEM Run",
    )

    assert output_dir.exists()
    assert all(path.exists() for path in paths.values() if path != output_dir)

    project = HmsPrj().initialize(output_dir)
    hms_content = paths["project_file"].read_text(encoding="utf-8")
    run_content = paths["run"].read_text(encoding="utf-8")

    assert "Basin: Spring Creek TauDEM Sink" in hms_content
    assert "Precipitation: Spring Creek TauDEM Met" in hms_content
    assert "Control: Spring Creek TauDEM Control" in hms_content
    assert paths["run"].name == "river_bend.run"
    assert "Run: Spring Creek TauDEM Run" in run_content
    assert "Basin: Spring Creek TauDEM Sink" in run_content
    assert "Precip: Spring Creek TauDEM Met" in run_content
    assert "Control: Spring Creek TauDEM Control" in run_content

    assert "Spring Creek TauDEM Sink" in project.basin_df["name"].tolist()
    assert "Spring Creek TauDEM Met" in project.met_df["name"].tolist()
    assert "Spring Creek TauDEM Control" in project.control_df["name"].tolist()
    assert "Spring Creek TauDEM Run" in project.run_df["name"].tolist()


@pytest.mark.requires_gis
def test_bootstrap_taudem_atlas14_project_writes_compute_ready_met_and_control(
    spring_creek_taudem_fixture_root,
    river_bend_example_dir,
    tmp_path,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    output_dir = tmp_path / "river_bend_atlas14_bootstrap"
    depth_table = pd.DataFrame(
        [
            {"duration_label": "5-min", "duration_minutes": 5, 100: 0.861},
            {"duration_label": "15-min", "duration_minutes": 15, 100: 1.61},
            {"duration_label": "30-min", "duration_minutes": 30, 100: 2.32},
            {"duration_label": "60-min", "duration_minutes": 60, 100: 3.11},
            {"duration_label": "2-hr", "duration_minutes": 120, 100: 3.78},
            {"duration_label": "3-hr", "duration_minutes": 180, 100: 4.10},
            {"duration_label": "6-hr", "duration_minutes": 360, 100: 4.81},
            {"duration_label": "24-hr", "duration_minutes": 1440, 100: 6.15},
        ]
    )

    paths = HmsBasinBuilder.bootstrap_taudem_atlas14_project(
        spec=spec,
        template_project_dir=river_bend_example_dir,
        output_dir=output_dir,
        basin_name="Spring Creek TauDEM Sink",
        met_name="Spring Creek Atlas14 100YR",
        control_name="Spring Creek Atlas14 Control",
        run_name="Spring Creek Atlas14 Run",
        atlas14_depth_table=depth_table,
        atlas14_latitude=39.815328,
        atlas14_longitude=-89.698713,
    )

    met_content = paths["met"].read_text(encoding="utf-8")
    control_content = paths["control"].read_text(encoding="utf-8")
    hms_content = paths["project_file"].read_text(encoding="utf-8")
    atlas14_report = json.loads(paths["atlas14_report"].read_text(encoding="utf-8"))
    project = HmsPrj().initialize(output_dir)

    assert "Meteorology: Spring Creek Atlas14 100YR" in met_content
    assert "Version: 3.3" in met_content
    assert "Precipitation Method: Frequency Based Hypothetical" in met_content
    assert "Exceedence Frequency: 1" in met_content
    assert len(re.findall(r"^\s+Depth:", met_content, flags=re.MULTILINE)) == 8
    assert paths["run"].name == "river_bend.run"
    assert "Time Interval: 5" in control_content
    assert "Version: 4.13" in control_content
    assert "Atlas 14 frequency storm meteorology scaffold" in hms_content
    assert atlas14_report["atlas14"]["depths_inches"] == pytest.approx([0.861, 1.61, 2.32, 3.11, 3.78, 4.10, 4.81, 6.15])
    assert atlas14_report["query_point"]["source"] == "user_supplied"
    assert "Spring Creek Atlas14 100YR" in project.met_df["name"].tolist()
    assert "Spring Creek Atlas14 Control" in project.control_df["name"].tolist()
    assert "Spring Creek Atlas14 Run" in project.run_df["name"].tolist()


@pytest.mark.requires_gis
@pytest.mark.parametrize("manual_source", ["depths", "depth_table"])
def test_bootstrap_taudem_atlas14_project_converts_manual_metric_depths_to_inches(
    spring_creek_taudem_fixture_root,
    river_bend_example_dir,
    tmp_path,
    manual_source,
):
    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    output_dir = tmp_path / f"river_bend_atlas14_bootstrap_metric_{manual_source}"
    depths_inches = [0.861, 1.61, 2.32, 3.11, 3.78, 4.10, 4.81, 6.15]
    depths_mm = [depth * 25.4 for depth in depths_inches]
    kwargs = {
        "atlas14_depths": depths_mm,
    }
    if manual_source == "depth_table":
        kwargs = {
            "atlas14_depth_table": pd.DataFrame(
                [
                    {"duration_label": "5-min", "duration_minutes": 5, 100: depths_mm[0]},
                    {"duration_label": "15-min", "duration_minutes": 15, 100: depths_mm[1]},
                    {"duration_label": "30-min", "duration_minutes": 30, 100: depths_mm[2]},
                    {"duration_label": "60-min", "duration_minutes": 60, 100: depths_mm[3]},
                    {"duration_label": "2-hr", "duration_minutes": 120, 100: depths_mm[4]},
                    {"duration_label": "3-hr", "duration_minutes": 180, 100: depths_mm[5]},
                    {"duration_label": "6-hr", "duration_minutes": 360, 100: depths_mm[6]},
                    {"duration_label": "24-hr", "duration_minutes": 1440, 100: depths_mm[7]},
                ]
            ),
        }

    paths = HmsBasinBuilder.bootstrap_taudem_atlas14_project(
        spec=spec,
        template_project_dir=river_bend_example_dir,
        output_dir=output_dir,
        basin_name="Spring Creek TauDEM Sink",
        met_name="Spring Creek Atlas14 100YR",
        control_name="Spring Creek Atlas14 Control",
        run_name="Spring Creek Atlas14 Run",
        atlas14_units="metric",
        atlas14_latitude=39.815328,
        atlas14_longitude=-89.698713,
        **kwargs,
    )

    met_content = paths["met"].read_text(encoding="utf-8")
    atlas14_report = json.loads(paths["atlas14_report"].read_text(encoding="utf-8"))

    assert atlas14_report["atlas14"]["units"] == "metric"
    assert atlas14_report["atlas14"]["requested_units"] == "metric"
    assert atlas14_report["atlas14"]["native_units"] == "metric"
    assert atlas14_report["atlas14"]["depths_native_units"] == pytest.approx(depths_mm)
    assert atlas14_report["atlas14"]["depths_inches"] == pytest.approx(depths_inches)
    assert "     Depth: 0.861" in met_content
    assert "     Depth: 21.8694" not in met_content
