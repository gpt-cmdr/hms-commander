"""Wrappers over ras-commander-fast-dss (0.1.1 and 0.1.2): ``HmsDss.repair``, the all-curve
paired-data read, profile and location methods, the ``HmsDssGrid`` engine tools, and
``sync=`` on the writers.

Every wrapper passes its arguments to the engine and returns the engine's result
unchanged. The tests write small synthetic DSS files under ``tmp_path`` and check the
stored data, the pass-through and the gates. No JVM is started and HEC-HMS is not run.
The module skips when the engine or its writers are unavailable.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import logging

import numpy as np
import pandas as pd
import pytest

dc = pytest.importorskip("ras_commander_fast_dss")

from hms_commander.dss import DssCapabilityError, DssCore, HmsDss, HmsDssGrid  # noqa: E402
from hms_commander.dss import _backend  # noqa: E402

if not _backend.native_writes_available():  # pragma: no cover - depends on the wheel
    pytest.skip("installed ras-commander-fast-dss has no writers", allow_module_level=True)

TIMES = pd.date_range("2020-01-01 01:00", periods=24, freq="h")
TS_PATH = "/A/B/FLOW//1HOUR/F/"
PD_PATH = "//DAM/ELEV-STOR-AREA///TABLE/"
PROFILE_PATH = "/LAKE/DAM/TEMP-WATER//1Day/OBS/"
DEPTHS = np.array([0.0, 5.0, 10.0])
PROFILE_VALUES = np.arange(12.0).reshape(4, 3)

# A 5 x 4 SHG grid of 2000 m cells, three hourly frames. Row 0 of FRAMES is north.
FRAMES = np.arange(3 * 4 * 5, dtype=np.float32).reshape(3, 4, 5)
T0 = dt.datetime(2020, 1, 1)
WINDOWS = [(T0 + dt.timedelta(hours=i), T0 + dt.timedelta(hours=i + 1)) for i in range(3)]
TRANSFORM = (100000.0, 2000.0, 208000.0, -2000.0)
GRID_PARTS = {"A": "SHG", "B": "TEST", "F": "SYN"}

# Two zones in longitude and latitude (NAD83) that split the grid between its second and
# third column, with a 1000 m margin outside it, so no cell centre is near an edge.
ZONE_WEST = [[-95.033091, 24.820631], [-94.984261, 24.820154], [-94.983216, 24.911567],
             [-95.032096, 24.912044], [-95.033091, 24.820631]]
ZONE_EAST = [[-94.984261, 24.820154], [-94.9159, 24.819447], [-94.914784, 24.910859],
             [-94.983216, 24.911567], [-94.984261, 24.820154]]


@pytest.fixture(autouse=True)
def native_backend(monkeypatch):
    monkeypatch.delenv(_backend.ENV_VAR, raising=False)
    monkeypatch.setattr(HmsDss, "backend", "native")


def _spy(monkeypatch, module, name):
    """Record the keyword arguments of every call to ``module.name``; still call it."""
    real = getattr(module, name)
    calls = []

    def wrapper(*args, **kwargs):
        calls.append(kwargs)
        return real(*args, **kwargs)

    monkeypatch.setattr(module, name, wrapper)
    return calls


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cells(dss_file, pathname):
    return np.asarray(dc.read_grid(dss_file, pathname).data)


# ---------------------------------------------------------------------------
# sync= on the writers
# ---------------------------------------------------------------------------


def test_unstated_sync_is_not_passed_so_the_engine_default_applies(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "write_timeseries")
    HmsDss.write_timeseries(tmp_path / "a.dss", TS_PATH, TIMES, np.arange(24.0))
    assert len(calls) == 1 and "sync" not in calls[0]
    assert _backend.native_sync_kwargs() == {}


@pytest.mark.parametrize("writer", [HmsDss.write_timeseries, DssCore.write_timeseries])
@pytest.mark.parametrize("sync", [False, True, "end", "step", "none"])
def test_write_timeseries_passes_sync_unchanged_and_stores_the_data(
    tmp_path, monkeypatch, writer, sync
):
    calls = _spy(monkeypatch, dc, "write_timeseries")
    target = tmp_path / "a.dss"
    writer(target, TS_PATH, TIMES, np.arange(24.0), sync=sync)
    assert len(calls) == 1 and calls[0]["sync"] is sync
    assert _backend.native_sync_kwargs() == {}  # the stated value does not outlive the call
    df = HmsDss.read_timeseries(target, TS_PATH)
    np.testing.assert_array_equal(df["value"].to_numpy(), np.arange(24.0))


def test_sync_is_the_engines_value_not_a_bool_this_wrapper_checks(tmp_path, monkeypatch):
    """A value the wrapper does not know reaches the engine as given; the engine
    refuses it (0.1.1 with TypeError, 0.1.2 with ValueError naming the modes)."""
    target = tmp_path / "a.dss"
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0))
    seen = []
    monkeypatch.setattr(dc, "write_timeseries",
                        lambda *args, **kwargs: seen.append(kwargs.get("sync")) or {})
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0), sync="per_step")
    assert seen == ["per_step"]
    monkeypatch.undo()
    monkeypatch.setattr(HmsDss, "backend", "native")
    with pytest.raises((TypeError, ValueError), match="sync"):  # the engine's refusal
        HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0), sync="per_step")


def test_paired_data_writers_pass_sync(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "write_paired_data")
    target = tmp_path / "pd.dss"
    x = np.array([1.0, 2.0, 3.0])
    assert HmsDss.write_paired_data(target, "//A/STAGE-FLOW///F/", x, 10 * x, x_units="FT",
                                    y_units="CFS", x_type="UNT", y_type="UNT", sync=False)
    assert calls[-1]["sync"] is False
    assert HmsDss.write_paired_data(target, "//A/STAGE-FLOW///G/", x, 10 * x, x_units="FT",
                                    y_units="CFS", x_type="UNT", y_type="UNT")
    assert "sync" not in calls[-1]
    records = [{"pathname": f"//B{i}/STAGE-FLOW///F/", "x_values": x, "y_values": x * i,
                "x_units": "FT", "y_units": "CFS"} for i in (1, 2)]
    before = len(calls)
    assert all(HmsDss.write_multiple_paired_data(target, records, sync=False).values())
    assert [call["sync"] for call in calls[before:]] == [False, False]
    np.testing.assert_array_equal(
        HmsDss.read_paired_data(target, "//B2/STAGE-FLOW///F/")["y_values"], 2 * x)


def test_import_atlas14_temporal_passes_sync(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "write_paired_data")
    hours = np.arange(0.0, 24.5, 0.5)
    frame = pd.DataFrame({"50%": np.linspace(0.0, 100.0, len(hours))}, index=hours)
    results = HmsDss.import_atlas14_temporal(tmp_path / "t.dss", {"First Quartile": frame},
                                             "TX_R3", sync=False)
    assert results and all(results.values())
    assert calls and all(call["sync"] is False for call in calls)


def test_grid_writer_passes_sync_on_both_routes(tmp_path, monkeypatch):
    lat = np.array([30.0, 30.1, 30.2, 30.3])
    lon = np.array([-95.4, -95.3, -95.2, -95.1, -95.0])
    stamps = [T0 + dt.timedelta(hours=i) for i in (1, 2, 3)]
    grid_calls = _spy(monkeypatch, dc, "write_grid")
    target = tmp_path / "wgs.dss"
    HmsDssGrid.write_grid_timeseries(target, "/AORC/TEST/PRECIP////", FRAMES, lat, lon,
                                     stamps, sync=False)
    assert len(grid_calls) == 3 and all(call["sync"] is False for call in grid_calls)
    HmsDssGrid.write_grid_timeseries(tmp_path / "wgs2.dss", "/AORC/TEST/PRECIP////", FRAMES,
                                     lat, lon, stamps)
    assert "sync" not in grid_calls[-1]
    import_calls = _spy(monkeypatch, dc.gridded, "import_arrays")
    HmsDssGrid.write_grid_timeseries(tmp_path / "shg.dss", "/SHG/TEST/PRECIP////", FRAMES,
                                     lat, lon, stamps, target_crs="SHG", sync=False)
    assert len(import_calls) == 1 and import_calls[0]["sync"] is False
    assert len(HmsDss.get_catalog(tmp_path / "shg.dss")) == 3


def test_stated_sync_needs_the_engine_feature_and_touches_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dc, "FEATURES", frozenset(dc.FEATURES) - {"write_sync_policy"})
    assert HmsDss.get_capabilities().attrs["native_write_sync_available"] is False
    target = tmp_path / "gated.dss"
    with pytest.raises(DssCapabilityError, match="write_sync_policy"):
        HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0), sync=False)
    assert not target.exists()
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0))  # unstated still writes
    assert target.exists()
    monkeypatch.undo()
    assert _backend.native_sync_available() is True


def test_named_sync_mode_needs_the_modes_feature_and_touches_no_file(tmp_path, monkeypatch):
    """A named mode ("end", "step", "none") needs an engine with write_sync_modes;
    booleans need only write_sync_policy."""
    monkeypatch.setattr(dc, "FEATURES", frozenset(dc.FEATURES) - {"write_sync_modes"})
    target = tmp_path / "gated.dss"
    with pytest.raises(DssCapabilityError, match="write_sync_modes"):
        HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0), sync="step")
    assert not target.exists()
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0), sync=False)
    assert target.exists()


@pytest.mark.skipif(not _backend.takes_keyword(dc.create, "sync"),
                    reason="the installed engine's create() takes no sync=")
def test_stated_sync_reaches_create_for_a_new_file(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "create")
    HmsDss.write_timeseries(tmp_path / "a.dss", TS_PATH, TIMES, np.arange(24.0), sync="none")
    HmsDss.write_timeseries(tmp_path / "b.dss", TS_PATH, TIMES, np.arange(24.0))
    assert calls[0]["sync"] == "none" and "sync" not in calls[1]


def test_java_backend_does_not_use_sync_and_a_nested_unstated_call_keeps_it():
    with _backend.write_sync(False, "java"):
        assert _backend.native_sync_kwargs() == {"sync": False}
        with _backend.write_sync(None, "native"):
            assert _backend.native_sync_kwargs() == {"sync": False}
        with _backend.write_sync(True, "native"):
            assert _backend.native_sync_kwargs() == {"sync": True}
        assert _backend.native_sync_kwargs() == {"sync": False}
    assert _backend.native_sync_kwargs() == {}
    assert _backend.native_sync_kwargs(True) == {"sync": True}


# ---------------------------------------------------------------------------
# repair
# ---------------------------------------------------------------------------


@pytest.fixture
def dss7(tmp_path):
    src = tmp_path / "source.dss"
    for i in range(5):
        HmsDss.write_timeseries(src, f"/A/B{i}/FLOW//1HOUR/F/", TIMES, np.arange(24.0) * (i + 1))
    assert HmsDss.get_file_version(src) == 7
    return src


@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
def test_repair_copies_a_clean_file_on_every_backend(dss7, tmp_path, monkeypatch, backend):
    monkeypatch.setattr(HmsDss, "backend", backend)
    before = _digest(dss7)
    dest = tmp_path / f"recovered_{backend}.dss"
    result = HmsDss.repair(dss7, dest)
    assert result["complete"] is True and result["not_copied"] == []
    assert result["records_copied"] == result["src_listed_records"] > 0
    assert _digest(dss7) == before  # src is opened read-only
    monkeypatch.setattr(HmsDss, "backend", "native")
    for i in range(5):
        df = HmsDss.read_timeseries(dest, f"/A/B{i}/FLOW/01JAN2020/1HOUR/F/")
        np.testing.assert_array_equal(df["value"].to_numpy(), np.arange(24.0) * (i + 1))


def test_repair_publishes_a_partial_recovery_and_warns(dss7, tmp_path, caplog):
    raw = bytearray(dss7.read_bytes())
    for j in range(int(len(raw) * 0.55), int(len(raw) * 0.65)):
        raw[j] ^= 0xFF
    damaged = tmp_path / "damaged.dss"
    damaged.write_bytes(raw)
    before = _digest(damaged)
    dest = tmp_path / "partial.dss"
    with caplog.at_level(logging.WARNING):
        result = HmsDss.repair(damaged, dest)
    assert result["complete"] is False and result["not_copied"]
    assert dest.exists() and _digest(damaged) == before
    assert "incomplete" in caplog.text


@pytest.mark.skipif(not _backend.takes_keyword(dc.repair, "sync"),
                    reason="the installed engine's repair() takes no sync=")
@pytest.mark.parametrize("sync", [None, "end", "step", "none"])
def test_repair_passes_sync(dss7, tmp_path, monkeypatch, sync):
    calls = _spy(monkeypatch, dc, "repair")
    result = HmsDss.repair(dss7, tmp_path / "out.dss", sync=sync)
    assert result["complete"] is True
    assert calls[0].get("sync") == sync if sync is not None else "sync" not in calls[0]


def test_repair_file_rules_and_gate(dss7, tmp_path, monkeypatch):
    dest = tmp_path / "exists.dss"
    dest.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        HmsDss.repair(dss7, dest)
    assert dest.read_bytes() == b"keep"
    with pytest.raises(FileNotFoundError):
        HmsDss.repair(tmp_path / "missing.dss", tmp_path / "out.dss")
    assert not (tmp_path / "out.dss").exists()
    monkeypatch.setattr(dc, "FEATURES", frozenset(dc.FEATURES) - {"repair_copy_out"})
    with pytest.raises(DssCapabilityError, match="repair_copy_out"):
        HmsDss.repair(dss7, tmp_path / "gated.dss")
    assert not (tmp_path / "gated.dss").exists()


# ---------------------------------------------------------------------------
# All curves of a paired-data record
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
@pytest.mark.parametrize("version", [6, 7])
def test_read_paired_data_all_returns_every_curve(tmp_path, monkeypatch, backend, version):
    target = tmp_path / "tables.dss"
    elevation = np.array([100.0, 110.0, 120.0, 130.0])
    curves = np.column_stack([elevation * 10, elevation * 2])  # storage, area
    assert HmsDss.write_paired_data(
        target, PD_PATH, elevation, curves, x_units="FT", y_units="AC-FT", x_type="UNT",
        y_type="UNT", labels=["STORAGE", "AREA"], dss_version=version,
    )
    first = HmsDss.read_paired_data(target, PD_PATH)  # the HMS dict: curve 0 only
    np.testing.assert_array_equal(first["y_values"], curves[:, 0])
    monkeypatch.setattr(HmsDss, "backend", backend)
    record = HmsDss.read_paired_data_all(target, PD_PATH)
    assert isinstance(record, dc.PairedData)
    assert record.n_curves == 2 and record.labels == ["STORAGE", "AREA"]
    np.testing.assert_array_equal(record.ordinates, elevation)
    np.testing.assert_array_equal(record.values, curves.T)  # one row per curve
    np.testing.assert_array_equal(record.curve(1), curves[:, 1])
    assert (record.units_independent, record.units_dependent) == ("FT", "AC-FT")
    frame = record.to_dataframe()
    assert frame.shape == (4, 2)
    assert HmsDss.read_paired_data_all(target, PD_PATH, dtype="float64").values.dtype == np.float64


def test_read_paired_data_all_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        HmsDss.read_paired_data_all(tmp_path / "missing.dss", PD_PATH)
    target = tmp_path / "ts.dss"
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0))
    with pytest.raises(dc.DssPathnameNotFoundError):
        HmsDss.read_paired_data_all(target, PD_PATH)
    with pytest.raises(dc.DssUnsupportedRecordError):
        HmsDss.read_paired_data_all(target, TS_PATH)


# ---------------------------------------------------------------------------
# Profiles and locations
# ---------------------------------------------------------------------------


def _write_profile(target, **kwargs):
    return HmsDss.write_profile(
        target, PROFILE_PATH, DEPTHS, PROFILE_VALUES, start="01JAN2024 2400",
        depth_units="ft", value_units="DEG F", data_type="INST-VAL", **kwargs,
    )


@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
def test_profile_round_trip_runs_on_the_engine_on_every_backend(tmp_path, monkeypatch, backend):
    monkeypatch.setattr(HmsDss, "backend", backend)
    target = tmp_path / "profile.dss"
    report = _write_profile(target)
    assert report["blocks"][0]["record_type"] == 107
    assert dc.file_signature(target)["version"] == 7
    profile = HmsDss.read_profile(target, PROFILE_PATH)
    assert isinstance(profile, dc.Profile)
    np.testing.assert_array_equal(profile.depths, DEPTHS)
    np.testing.assert_array_equal(profile.values, PROFILE_VALUES)
    assert (profile.depth_units, profile.value_units) == ("ft", "DEG F")
    frame = profile.to_dataframe()
    assert frame.shape == (4, 3) and frame.index[0] == pd.Timestamp("2024-01-02")
    window = HmsDss.read_profile(target, PROFILE_PATH, "03JAN2024 0000", "04JAN2024 0000")
    np.testing.assert_array_equal(window.values, PROFILE_VALUES[1:3])


def test_write_profile_options_and_file_rules(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "write_profile")
    target = tmp_path / "profile.dss"
    _write_profile(target)
    _write_profile(target, sync=False, value_type="double", quality=[0, 0, 0, 0])
    assert "sync" not in calls[0]
    assert calls[1]["sync"] is False and calls[1]["value_type"] == "double"
    missing = tmp_path / "missing.dss"
    with pytest.raises(ValueError):  # the engine refuses a 1-D values array
        HmsDss.write_profile(missing, PROFILE_PATH, DEPTHS, np.arange(3.0),
                             start="01JAN2024 2400", depth_units="ft",
                             value_units="DEG F", data_type="INST-VAL")
    assert not missing.exists()  # the file this call created is removed again
    dss6 = tmp_path / "six.dss"
    HmsDss.write_timeseries(dss6, TS_PATH, TIMES, np.arange(24.0), dss_version=6)
    with pytest.raises(ValueError, match="version 6"):
        _write_profile(dss6)
    with pytest.raises(dc.DssUnsupportedRecordError):
        HmsDss.read_profile(dss6, TS_PATH)


def test_location_round_trip(tmp_path, monkeypatch):
    calls = _spy(monkeypatch, dc, "write_location")
    target = tmp_path / "loc.dss"
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0))
    assert HmsDss.read_associated_location(target, TS_PATH) is None
    report = HmsDss.write_location(target, TS_PATH, x=-90.07, y=29.95, z=3.2,
                                   supplemental="note:test", sync=False)
    assert calls[0]["sync"] is False
    assert report["blocks"][0]["pathname"] == "/A/B/Location Info////"
    location = HmsDss.read_associated_location(target, TS_PATH)
    assert isinstance(location, dc.Location)
    assert location.coordinates == (-90.07, 29.95, 3.2) and location.supplemental == "note:test"
    assert HmsDss.read_location(target, "/A/B/Location Info////").coordinates == (-90.07, 29.95, 3.2)
    HmsDss.write_location(target, TS_PATH, z=4.0)  # a partial update keeps the other fields
    assert "sync" not in calls[1]
    assert HmsDss.read_associated_location(target, TS_PATH).coordinates == (-90.07, 29.95, 4.0)
    dss6 = tmp_path / "six.dss"
    HmsDss.write_timeseries(dss6, TS_PATH, TIMES, np.arange(24.0), dss_version=6)
    HmsDss.write_location(dss6, TS_PATH, x=1.5, y=2.5, z=3.5)
    assert HmsDss.read_associated_location(dss6, TS_PATH).coordinates == (1.5, 2.5, 3.5)
    missing = tmp_path / "missing.dss"
    for call in (lambda: HmsDss.write_location(missing, TS_PATH, x=1.0),
                 lambda: HmsDss.read_location(missing, TS_PATH),
                 lambda: HmsDss.read_associated_location(missing, TS_PATH)):
        with pytest.raises(FileNotFoundError):
            call()
    assert not missing.exists()


@pytest.mark.parametrize("feature, call", [
    ("write_profile", lambda target: _write_profile(target)),
    ("write_location", lambda target: HmsDss.write_location(target, TS_PATH, x=1.0)),
])
def test_profile_and_location_writers_are_gated(tmp_path, monkeypatch, feature, call):
    target = tmp_path / "gated.dss"
    HmsDss.write_timeseries(target, TS_PATH, TIMES, np.arange(24.0))
    before = _digest(target)
    monkeypatch.setattr(dc, "FEATURES", frozenset(dc.FEATURES) - {feature})
    with pytest.raises(DssCapabilityError, match=feature):
        call(target)
    assert _digest(target) == before


def test_capabilities_list_the_engine_only_operations():
    caps = HmsDss.get_capabilities().set_index("operation")
    for operation in ("repair", "read_paired_data_all", "read_profile", "write_profile",
                      "read_location", "read_associated_location", "write_location"):
        assert list(caps.loc[operation, ["java", "native", "shadow"]]) == ["gated"] * 3
        assert callable(getattr(HmsDss, operation))
    assert "HmsDssGrid engine tools" in caps.index
    assert HmsDss.get_capabilities().attrs["native_write_sync_available"] is True


# ---------------------------------------------------------------------------
# HmsDssGrid engine tools
# ---------------------------------------------------------------------------


@pytest.fixture
def grids(tmp_path):
    """Three hourly SHG precipitation grids imported from arrays."""
    target = tmp_path / "grids.dss"
    result = HmsDssGrid.import_arrays(
        FRAMES, target, times=WINDOWS, transform=TRANSFORM, crs="SHG",
        variable="precipitation", source_units="mm", parts=GRID_PARTS,
    )
    assert [record["outcome"] for record in result.records] == ["added"] * 3
    return target, result.pathnames


@pytest.fixture
def zones(tmp_path):
    path = tmp_path / "zones.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"NAME": "WEST"},
         "geometry": {"type": "Polygon", "coordinates": [ZONE_WEST]}},
        {"type": "Feature", "properties": {"NAME": "EAST"},
         "geometry": {"type": "Polygon", "coordinates": [ZONE_EAST]}},
    ]}))
    return path


def test_every_engine_tool_has_a_wrapper():
    assert set(_backend.GRIDDED_FEATURES) <= set(vars(HmsDssGrid))
    for name in _backend.GRIDDED_FEATURES:
        assert callable(getattr(dc.gridded, name)), name
    assert all(HmsDssGrid.get_features().values())
    assert callable(HmsDssGrid.write_grid_timeseries) and callable(HmsDssGrid.get_info)


def test_import_arrays_writes_the_frames(grids):
    target, pathnames = grids
    assert pathnames[0] == "/SHG/TEST/PRECIPITATION/01JAN2020:0000/01JAN2020:0100/SYN/"
    info = HmsDssGrid.series_info(target, pathnames[0])
    assert (info["records"], info["nx"], info["ny"], info["units"]) == (3, 5, 4, "MM")
    assert (info["start"], info["end"]) == ("01JAN2020:0000", "01JAN2020:0300")
    np.testing.assert_array_equal(_cells(target, pathnames[1]), FRAMES[1][::-1])


def test_import_gridded_reads_an_ascii_grid(tmp_path):
    source = tmp_path / "depth.asc"
    source.write_text(
        "ncols 3\nnrows 2\nxllcorner 100000\nyllcorner 200000\ncellsize 2000\n"
        "NODATA_value -9999\n1 2 3\n4 5 6\n"
    )
    (tmp_path / "depth.prj").write_text(dc.SHG_WKT)
    target = tmp_path / "out.dss"
    result = HmsDssGrid.import_gridded(
        source, target, variable=HmsDssGrid.list_variables(source)[0], target_crs=None,
        cell_size=None, parts={"A": "SHG", "B": "ASC", "C": "DEPTH", "F": "T"},
        units="MM", data_type="INST-VAL", sync=False,
    )
    assert len(result.pathnames) == 1
    np.testing.assert_array_equal(_cells(target, result.pathnames[0]),
                                  [[4.0, 5.0, 6.0], [1.0, 2.0, 3.0]])


def test_calculate_sanitize_and_raster(grids, tmp_path):
    target, pathnames = grids
    source = _cells(target, pathnames[0])
    doubled = HmsDssGrid.calculate(target, tmp_path / "x2.dss", multiply=2.0,
                                   parts={**GRID_PARTS, "F": "X2"})
    assert len(doubled.pathnames) == 3 and doubled.pathnames[0].endswith("/X2/")
    np.testing.assert_array_equal(_cells(tmp_path / "x2.dss", doubled.pathnames[0]), 2 * source)
    floored = HmsDssGrid.sanitize(target, tmp_path / "floor.dss", minimum=5.0,
                                  minimum_replacement=0.0, parts=GRID_PARTS)
    np.testing.assert_array_equal(_cells(tmp_path / "floor.dss", floored.pathnames[0]),
                                  np.where(source <= 5.0, 0.0, source))
    squared = HmsDssGrid.calculate_raster(
        target, target, tmp_path / "sq.dss", operation="multiply",
        raster_variable=pathnames[0], variables=[pathnames[0]], parts=GRID_PARTS,
    )
    np.testing.assert_array_equal(_cells(tmp_path / "sq.dss", squared.pathnames[0]),
                                  source * source)


def test_clip_and_normalize(grids, tmp_path):
    target, pathnames = grids
    clipped = HmsDssGrid.clip(target, tmp_path / "clip.dss", parts=GRID_PARTS,
                              envelope=(102000.0, 202000.0, 108000.0, 206000.0),
                              envelope_crs="SHG")
    assert {(r["nx"], r["ny"]) for r in clipped.records} == {(3, 2)}
    assert {(r["lower_left_cell_x"], r["lower_left_cell_y"]) for r in clipped.records} == {(51, 101)}
    normals = tmp_path / "normals.dss"
    HmsDssGrid.calculate(target, normals, multiply=3.0, parts={**GRID_PARTS, "F": "NORMAL"})
    result = HmsDssGrid.normalize(
        target, normals, tmp_path / "norm.dss", start=T0, end=T0 + dt.timedelta(hours=3),
        interval=dt.timedelta(hours=3), parts=GRID_PARTS,
    )
    assert result.sources_left_out == [] and result.normals_left_out == []
    np.testing.assert_allclose(_cells(tmp_path / "norm.dss", pathnames[2]),
                               3.0 * _cells(target, pathnames[2]), rtol=1e-6)


def test_time_tools(grids, tmp_path):
    target, pathnames = grids
    shifted = HmsDssGrid.shift_times(target, tmp_path / "shift.dss",
                                     shift=dt.timedelta(hours=6), parts=GRID_PARTS)
    assert shifted.pathnames[0] == "/SHG/TEST/PRECIPITATION/01JAN2020:0600/01JAN2020:0700/SYN/"
    np.testing.assert_array_equal(_cells(tmp_path / "shift.dss", shifted.pathnames[0]),
                                  _cells(target, pathnames[0]))
    assert 180 in HmsDssGrid.time_steps()
    resampled = HmsDssGrid.resample_times(target, tmp_path / "3h.dss", 180, parts=GRID_PARTS)
    assert resampled.pathnames == ["/SHG/TEST/PRECIPITATION/01JAN2020:0000/01JAN2020:0300/SYN/"]
    assert resampled.dropped_tail_seconds == 0
    np.testing.assert_array_equal(_cells(tmp_path / "3h.dss", resampled.pathnames[0]),
                                  FRAMES.sum(axis=0)[::-1])  # PER-CUM keeps the volume
    window = HmsDssGrid.read_window(target, pathnames[0], "01JAN2020:0000", "01JAN2020:0300")
    np.testing.assert_array_equal(window.data, FRAMES.sum(axis=0)[::-1])
    nearest = HmsDssGrid.read_nearest(target, pathnames[0], "01JAN2020:0100")
    np.testing.assert_array_equal(nearest.data, FRAMES[1][::-1])
    low, high = HmsDssGrid.read_min_max(target, pathnames[0], "01JAN2020:0000", "01JAN2020:0300")
    np.testing.assert_array_equal(low.data, FRAMES[0][::-1])
    np.testing.assert_array_equal(high.data, FRAMES[2][::-1])


def test_zonal_statistics_and_grid_to_point(grids, zones, tmp_path):
    target, _ = grids
    masks = HmsDssGrid.zone_masks(target, zones, "NAME", assume_no_datum_shift=True)
    assert {name: len(cells) for name, cells in masks.items()} == {"WEST": 8, "EAST": 12}
    table = HmsDssGrid.zonal_statistics(target, zones, "NAME", assume_no_datum_shift=True)
    assert isinstance(table, pd.DataFrame) and len(table) == 6
    west = np.array([FRAMES[i][:, :2].mean() for i in range(3)])
    east = np.array([FRAMES[i][:, 2:].mean() for i in range(3)])
    out = tmp_path / "points.dss"
    result = HmsDssGrid.grid_to_point(target, zones, "NAME", out, assume_no_datum_shift=True,
                                      parts={"A": "SHG", "F": "SYN"})
    assert result.pathnames == ["/SHG/WEST/PRECIP-INC//1Hour/SYN/",
                                "/SHG/EAST/PRECIP-INC//1Hour/SYN/"]
    for pathname, expected in zip(result.pathnames, (west, east)):
        df = HmsDss.read_timeseries(out, pathname)
        np.testing.assert_allclose(df["value"].to_numpy(), expected, rtol=1e-6)


@pytest.mark.parametrize("method", ["near", "bilinear", "average"])
def test_resampling_method_reaches_the_engine(grids, tmp_path, monkeypatch, method):
    """The engine's ``method=`` keyword is passed through, not taken by the wrapper."""
    target, _ = grids
    calls = _spy(monkeypatch, dc.gridded, "import_arrays")
    out = tmp_path / f"{method}.dss"
    HmsDssGrid.import_arrays(FRAMES, out, times=WINDOWS, transform=TRANSFORM, crs="SHG",
                             variable="precipitation", source_units="mm",
                             target_crs="SHG", cell_size=2000.0, method=method,
                             parts=GRID_PARTS)
    assert calls[-1]["method"] == method
    assert len(HmsDss.get_catalog(out)) == 3
    raster_calls = _spy(monkeypatch, dc.gridded, "calculate_raster")
    HmsDssGrid.calculate_raster(target, out, tmp_path / "r.dss", operation="add",
                                method=method, parts=GRID_PARTS,
                                raster_variable=HmsDss.get_catalog(out)[0],
                                static_raster=True)
    assert raster_calls[-1]["method"] == method
    assert len(HmsDss.get_catalog(tmp_path / "r.dss")) == 3


def test_tools_sync_gates_and_refusals(grids, zones, tmp_path, monkeypatch):
    target, _ = grids
    calls = _spy(monkeypatch, dc.gridded, "calculate")
    HmsDssGrid.calculate(target, tmp_path / "a.dss", add=1.0, parts=GRID_PARTS)
    HmsDssGrid.calculate(target, tmp_path / "b.dss", add=1.0, parts=GRID_PARTS, sync=False)
    assert "sync" not in calls[0] and calls[1]["sync"] is False
    refused = tmp_path / "refused.dss"
    with pytest.raises(ValueError):
        HmsDssGrid.calculate(target, refused, add=1.0, multiply=2.0)
    assert not refused.exists()
    if not _backend.takes_keyword(dc.gridded.grid_to_point, "sync"):
        out = tmp_path / "points.dss"
        with pytest.raises(DssCapabilityError, match="sync"):
            HmsDssGrid.grid_to_point(target, zones, "NAME", out, assume_no_datum_shift=True,
                                     sync=False)
        assert not out.exists()
    monkeypatch.setattr(dc, "FEATURES", frozenset(dc.FEATURES) - {"grid_tools"})
    assert HmsDssGrid.get_features()["grid_tools"] is False
    with pytest.raises(DssCapabilityError, match="grid_tools"):
        HmsDssGrid.calculate(target, tmp_path / "gated.dss", add=1.0)
    assert not (tmp_path / "gated.dss").exists()
    assert HmsDssGrid.time_steps()  # another feature group is unaffected
