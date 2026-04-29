"""Tests for shared private GIS helpers."""

import pytest

pytest.importorskip("geopandas")
pytest.importorskip("pyproj")
pytest.importorskip("shapely")

import geopandas as gpd
from shapely.geometry import Polygon

from hms_commander._spatial import resolve_crs, single_geometry, write_json


def test_resolve_crs_uses_fallback_when_primary_missing():
    crs = resolve_crs(None, fallback_crs="EPSG:4326")

    assert crs.to_epsg() == 4326


def test_single_geometry_dissolves_non_empty_geometries():
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2]},
        geometry=[
            Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]),
            Polygon([(1, 0), (2, 0), (2, 1), (1, 1)]),
        ],
        crs="EPSG:4326",
    )

    geometry = single_geometry(gdf)

    assert geometry.area == pytest.approx(2.0)


def test_write_json_returns_artifact_metadata(tmp_path):
    path = tmp_path / "nested" / "artifact.json"

    result = write_json(path, {"path": path})

    assert result["status"] == "created"
    assert result["bytes"] > 0
    assert path.exists()
