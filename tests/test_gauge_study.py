"""Tests for the restored gauge-study and TauDEM preprocessing helpers."""

from __future__ import annotations

import json
from pathlib import Path

from hms_commander import HmsGaugeData, HmsGaugeStudy, HmsHydrologyContext, HmsTerrain
from hms_commander.HmsHuc import HmsHuc


class FakeResponse:
    """Simple requests-like response object for mock HTTP sessions."""

    def __init__(self, *, text=None, json_data=None, status_code=200):
        self.text = text or ""
        self._json = json_data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300

    def raise_for_status(self):
        """Raise on non-2xx responses."""
        if not self.ok:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        """Return the seeded JSON payload."""
        return self._json


class MockSession:
    """Mock session that returns canned payloads keyed by request url."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        for matcher, response in self.routes:
            if matcher(url, params):
                return response
        raise RuntimeError(f"Unhandled url: {url}")


def _sample_feature_payload():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-88.25, 40.12]},
                "properties": {
                    "identifier": "USGS-05555500",
                    "navigation": (
                        "https://api.water.usgs.gov/nldi/linked-data/"
                        "nwissite/USGS-05555500/navigation"
                    ),
                    "measure": 12.3,
                    "reachcode": "07130005000000",
                    "name": "Sample River At Test",
                    "source": "nwissite",
                    "sourceName": "NWIS Surface Water Sites",
                    "comid": "12345678",
                    "type": "nwissite",
                    "uri": "https://waterdata.usgs.gov/monitoring-location/05555500",
                    "mainstem": "main",
                },
            }
        ],
    }


def _sample_basin_payload():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-88.3, 40.1],
                        [-88.1, 40.1],
                        [-88.1, 40.2],
                        [-88.3, 40.2],
                        [-88.3, 40.1],
                    ]],
                },
                "properties": {"identifier": "USGS-05555500"},
            }
        ],
    }


def _sample_flowlines_payload():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-88.3, 40.1], [-88.25, 40.12], [-88.2, 40.15]],
                },
                "properties": {"nhdplus_comid": "123"},
            }
        ],
    }


def _sample_huc_payload(level, identifier):
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-88.3, 40.0],
                        [-88.0, 40.0],
                        [-88.0, 40.3],
                        [-88.3, 40.3],
                        [-88.3, 40.0],
                    ]],
                },
                "properties": {f"huc_{level}": identifier, "name": f"Sample HUC {level}"},
            }
        ],
    }


def _sample_nwis_rdb():
    return (
        "# comment\n"
        "agency_cd\tsite_no\tstation_nm\tdec_lat_va\tdec_long_va\n"
        "5s\t15s\t50s\t16n\t16n\n"
        "USGS\t05555500\tSample River At Test\t40.12\t-88.25\n"
    )


def _build_happy_path_session():
    feature_payload = _sample_feature_payload()
    basin_payload = _sample_basin_payload()
    flowlines_payload = _sample_flowlines_payload()
    huc8_payload = _sample_huc_payload("8", "07130005")
    huc12_payload = _sample_huc_payload("12", "071300050101")
    nwis_rdb = _sample_nwis_rdb()

    routes = [
        (
            lambda url, params: url.endswith("/linked-data/nwissite/USGS-05555500"),
            FakeResponse(json_data=feature_payload),
        ),
        (
            lambda url, params: "waterservices.usgs.gov/nwis/site/" in url,
            FakeResponse(text=nwis_rdb),
        ),
        (
            lambda url, params: url.endswith("/linked-data/nwissite/USGS-05555500/basin"),
            FakeResponse(json_data=basin_payload),
        ),
        (
            lambda url, params: "collections/nhdplusv2-huc08/items" in url,
            FakeResponse(json_data=huc8_payload),
        ),
        (
            lambda url, params: "collections/nhdplusv2-huc12/items" in url,
            FakeResponse(json_data=huc12_payload),
        ),
        (
            lambda url, params: "/navigation/UT/flowlines" in url,
            FakeResponse(json_data=flowlines_payload),
        ),
    ]
    return MockSession(routes)


def _seed_study_workspace(tmp_path):
    workspace_root = tmp_path / "study"
    workspace = HmsGaugeStudy.create_workspace(workspace_root)
    gauge_metadata = {
        "site_id": "05555500",
        "nldi_feature_id": "USGS-05555500",
        "retrieved_at": "2026-04-21T00:00:00Z",
        "name": "Sample River At Test",
        "coordinates": {"longitude": -88.25, "latitude": 40.12},
        "nldi": {
            "source": "nwissite",
            "source_name": "NWIS Surface Water Sites",
            "comid": "12345678",
            "reachcode": "07130005000000",
            "measure": 12.3,
            "navigation_url": (
                "https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-05555500/navigation"
            ),
            "uri": "https://waterdata.usgs.gov/monitoring-location/05555500",
            "mainstem": "main",
            "type": "nwissite",
        },
        "nwis_site": {
            "agency_cd": "USGS",
            "site_no": "05555500",
            "station_nm": "Sample River At Test",
            "dec_lat_va": "40.12",
            "dec_long_va": "-88.25",
        },
    }
    (workspace["metadata"] / "gauge_metadata.json").write_text(
        json.dumps(gauge_metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    (workspace["context"] / "nldi_basin.geojson").write_text(
        json.dumps(_sample_basin_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    return workspace["root"]


def test_gauge_primitives_support_site_to_pour_point():
    session = _build_happy_path_session()

    assert HmsGaugeData.normalize_site_id(" USGS-05555500 ") == "05555500"
    assert HmsGaugeData.get_nldi_feature_id("05555500") == "USGS-05555500"

    metadata = HmsGaugeData.get_usgs_gauge_metadata("05555500", session=session)
    point_feature = HmsGaugeData.get_usgs_gauge_point_feature(gauge_metadata=metadata)
    pour_point = HmsGaugeData.build_pour_point_feature(gauge_metadata=metadata)

    assert metadata["site_id"] == "05555500"
    assert metadata["coordinates"] == {"longitude": -88.25, "latitude": 40.12}
    assert metadata["nwis_site"]["station_nm"] == "Sample River At Test"
    assert point_feature["features"][0]["geometry"]["coordinates"] == [-88.25, 40.12]
    assert pour_point["features"][0]["properties"]["nldi_feature_id"] == "USGS-05555500"


def test_source_specific_boundary_helpers_compose_from_gauge():
    session = _build_happy_path_session()

    basin = HmsGaugeData.get_nldi_basin_from_gauge("05555500", session=session)
    upstream = HmsGaugeData.get_nhdplus_upstream_flowlines_from_gauge("05555500", session=session)
    huc8 = HmsGaugeData.get_nhd_huc8_boundary_from_gauge("05555500", session=session)
    huc12 = HmsGaugeData.get_nhd_huc12_boundary_from_gauge("05555500", session=session)

    assert basin["features"][0]["properties"]["identifier"] == "USGS-05555500"
    assert upstream["features"][0]["properties"]["nhdplus_comid"] == "123"
    assert huc8["features"][0]["properties"]["huc_8"] == "07130005"
    assert huc12["features"][0]["properties"]["huc_12"] == "071300050101"


def test_primitive_geometry_and_dem_extent_helpers_are_chainable():
    basin_payload = _sample_basin_payload()
    gauge_metadata = {
        "site_id": "05555500",
        "nldi_feature_id": "USGS-05555500",
        "name": "Sample River At Test",
        "coordinates": {"longitude": -88.25, "latitude": 40.12},
    }
    huc_context = {"huc8_context": _sample_huc_payload("8", "07130005")}

    bounds = HmsTerrain.geometry_bounds(basin_payload)
    dem_extent = HmsTerrain.recommend_dem_clip_extent(basin_payload)
    handoff = HmsTerrain.build_taudem_handoff(gauge_metadata, basin_payload, huc_context)

    assert bounds == (-88.3, 40.1, -88.1, 40.2)
    assert dem_extent["recommended_bounds"] == [-88.31, 40.09, -88.09, 40.21]
    assert dem_extent["minimum_buffer_degrees"] == 0.01
    assert handoff["pour_point"]["features"][0]["geometry"]["coordinates"] == [-88.25, 40.12]
    assert handoff["recommended_dem_clip_extent"]["recommended_bounds"] == [-88.31, 40.09, -88.09, 40.21]


def test_build_from_usgs_site_creates_workspace_and_artifacts(tmp_path):
    session = _build_happy_path_session()
    workspace_root = tmp_path / "study"

    result = HmsGaugeStudy.build_from_usgs_site("05555500", workspace_root, session=session)

    expected_files = [
        workspace_root / "metadata" / "gauge_metadata.json",
        workspace_root / "metadata" / "provenance.json",
        workspace_root / "metadata" / "study_manifest.json",
        workspace_root / "context" / "nldi_basin.geojson",
        workspace_root / "context" / "upstream_hydrography.geojson",
        workspace_root / "context" / "huc8_context.geojson",
        workspace_root / "context" / "huc12_context.geojson",
        workspace_root / "reports" / "study_report.json",
        workspace_root / "reports" / "data_gap_analysis.json",
    ]

    assert result["workspace_root"] == workspace_root
    assert all(path.exists() for path in expected_files)
    assert result["study_report"]["available_context"] == [
        "huc12_context",
        "huc8_context",
        "nldi_basin",
        "upstream_hydrography",
    ]
    assert result["data_gap_analysis"]["gap_count"] == 0


def test_build_from_usgs_site_records_structured_data_gaps(tmp_path, monkeypatch):
    def unavailable_huc_context(*args, **kwargs):
        raise RuntimeError("HUC context intentionally unavailable for this test")

    monkeypatch.setattr(HmsHuc, "get_huc8_for_bounds", unavailable_huc_context)
    monkeypatch.setattr(HmsHuc, "get_huc12_for_bounds", unavailable_huc_context)

    session = MockSession(
        [
            (
                lambda url, params: url.endswith("/linked-data/nwissite/USGS-05555500"),
                FakeResponse(json_data=_sample_feature_payload()),
            ),
            (
                lambda url, params: "waterservices.usgs.gov/nwis/site/" in url,
                FakeResponse(text=_sample_nwis_rdb()),
            ),
            (
                lambda url, params: url.endswith("/linked-data/nwissite/USGS-05555500/basin"),
                FakeResponse(json_data=_sample_basin_payload()),
            ),
        ]
    )

    result = HmsGaugeStudy.build_from_usgs_site("05555500", tmp_path / "study", session=session)
    gap_ids = [gap["id"] for gap in result["data_gap_analysis"]["gaps"]]

    assert gap_ids == [
        "missing_huc8_context",
        "missing_huc12_context",
        "missing_upstream_hydrography",
    ]
    assert result["study_report"]["blocking_gap_count"] == 1
    assert sorted(result["study_report"]["gap_affected_artifacts"]) == [
        "huc12_context",
        "huc8_context",
        "upstream_hydrography",
    ]


def test_build_taudem_input_pack_creates_expected_artifacts(tmp_path):
    workspace_root = tmp_path / "study"
    HmsGaugeStudy.build_from_usgs_site("05555500", workspace_root, session=_build_happy_path_session())

    result = HmsGaugeStudy.build_taudem_input_pack(workspace_root)
    pack_root = workspace_root / "raw" / "taudem_input_pack"

    expected_files = [
        pack_root / "pour_point.geojson",
        pack_root / "basin_boundary.geojson",
        pack_root / "huc_context_reference.json",
        pack_root / "recommended_dem_clip_extent.json",
        pack_root / "provenance.json",
        pack_root / "taudem_input_pack_manifest.json",
        pack_root / "report.json",
        pack_root / "data_gap_analysis.json",
    ]

    dem_extent = json.loads((pack_root / "recommended_dem_clip_extent.json").read_text(encoding="utf-8"))
    huc_reference = json.loads((pack_root / "huc_context_reference.json").read_text(encoding="utf-8"))

    assert result["pack_root"] == pack_root
    assert all(path.exists() for path in expected_files)
    assert huc_reference["primary_reference"] == "huc8_context"
    assert dem_extent["recommended_bounds"] == [-88.31, 40.09, -88.09, 40.21]
    assert result["data_gap_analysis"]["gap_count"] == 0


def test_build_taudem_input_pack_records_structured_data_gaps(tmp_path):
    workspace_root = _seed_study_workspace(tmp_path)

    result = HmsGaugeStudy.build_taudem_input_pack(workspace_root)
    gap_ids = [gap["id"] for gap in result["data_gap_analysis"]["gaps"]]

    assert gap_ids == ["missing_huc_context_for_taudem_pack"]
    assert result["study_report"]["available_components"] == [
        "taudem_basin_boundary",
        "taudem_dem_clip_extent",
        "taudem_pour_point",
    ]
    assert result["study_report"]["missing_components"] == ["taudem_huc_context_reference"]
