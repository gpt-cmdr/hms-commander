"""AORC and other period grids: stamps are period ends, with a real D-to-E period.

- ``_grid_time_windows`` needs no Java, HEC-HMS or network.
- The Java tests write through HEC Monolith and read the catalog back.
- The ``local_hms`` test runs an AORC-shaped WGS84 grid through
  ``HmsAorc.convert_to_dss_grid`` and ``HmsCmdr`` on the tenk sample. It builds its NetCDF
  in the test, with no network, and skips without Java or an HEC-HMS ``samples.zip``.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hms_commander import HmsAorc, HmsDssGrid
from hms_commander.dss import DssCore, HmsDss

T = pd.Timestamp


def windows(*args):
    return HmsDssGrid._grid_time_windows(*args)


# ---------------------------------------------------------------------------
# Period rules (no Java)
# ---------------------------------------------------------------------------


def test_stamps_are_period_ends():
    stamps = [datetime(2020, 5, 1, 23), datetime(2020, 5, 2, 0)]
    assert windows(stamps, 2, "PER-CUM", 60) == [
        (T("2020-05-01 22:00"), T("2020-05-01 23:00")),
        (T("2020-05-01 23:00"), T("2020-05-02 00:00")),
    ]


def test_interval_defaults_to_uniform_spacing():
    stamps = [datetime(2020, 5, 1, h) for h in (6, 12, 18)]
    assert windows(stamps, 3, "PER-AVER")[0] == (T("2020-05-01 00:00"), T("2020-05-01 06:00"))


def test_boundaries_give_one_period_per_grid():
    stamps = [datetime(2020, 5, 1, h) for h in (0, 1, 3)]
    assert windows(stamps, 2, "PER-CUM") == [
        (T("2020-05-01 00:00"), T("2020-05-01 01:00")),
        (T("2020-05-01 01:00"), T("2020-05-01 03:00")),
    ]


@pytest.mark.parametrize("stamps", [
    [datetime(2020, 5, 1, 1)],  # one grid has no spacing
    [datetime(2020, 5, 1, h) for h in (1, 2, 5)],  # a gap would give a wrong period
    [datetime(2020, 5, 1, h) for h in (3, 2, 1)],  # decreasing
])
def test_period_length_is_never_guessed(stamps):
    with pytest.raises(ValueError, match="interval_minutes"):
        windows(stamps, len(stamps), "PER-CUM")


def test_a_gap_is_kept_when_the_interval_is_given():
    stamps = [datetime(2020, 5, 1, h) for h in (1, 2, 5)]
    assert windows(stamps, 3, "PER-CUM", 60)[2] == (T("2020-05-01 04:00"), T("2020-05-01 05:00"))


@pytest.mark.parametrize("stamps,n,interval", [
    ([datetime(2020, 5, 1, 1)], 1, 0),
    ([datetime(2020, 5, 1, 1)], 1, -60),
    ([datetime(2020, 5, 1, 1), datetime(2020, 5, 1, 1)], 1, None),  # equal boundaries
    ([datetime(2020, 5, 1, 2), datetime(2020, 5, 1, 1)], 1, None),  # reversed boundaries
])
def test_zero_length_periods_are_refused(stamps, n, interval):
    with pytest.raises(ValueError, match="no length"):
        windows(stamps, n, "PER-CUM", interval)


@pytest.mark.parametrize("kind", ["INST-VAL", "inst-cum"])
def test_instantaneous_types_keep_the_instant(kind):
    t = datetime(2020, 5, 1, 1)
    assert windows([t], 1, kind) == [(T(t), T(t))]
    with pytest.raises(ValueError, match="must match"):  # no boundaries form
        windows([t, t], 1, kind)


@pytest.mark.parametrize("kind", ["PER-CUMM", "", None])
def test_unknown_data_types_are_refused(kind):
    with pytest.raises(ValueError, match="Unknown grid data type"):
        windows([datetime(2020, 5, 1, 1)], 1, kind, 60)


@pytest.mark.parametrize("stamp,match", [
    (datetime(2020, 5, 1, 1, tzinfo=timezone(timedelta(hours=-6))), "not UTC"),
    (datetime(2020, 5, 1, 1, 0, 30), "whole minute"),
])
def test_stamps_a_pathname_cannot_hold_are_refused(stamp, match):
    with pytest.raises(ValueError, match=match):
        windows([stamp], 1, "PER-CUM", 60)


@pytest.mark.parametrize("kind,expected", [
    ("INST-VAL", (T("2020-01-01 12:00"), T("2020-01-01 12:00"))),
    ("INST-CUM", (T("2020-01-01 12:00"), T("2020-01-01 12:00"))),
    ("PER-CUM", (T("2020-01-01 11:00"), T("2020-01-01 12:00"))),
    ("PER-AVER", (T("2020-01-01 11:00"), T("2020-01-01 12:00"))),
])
def test_utc_stamps_keep_their_clock_time(kind, expected):
    stamp = datetime(2020, 1, 1, 12, tzinfo=timezone.utc)
    assert windows([stamp], 1, kind, 60) == [expected]


def test_interval_must_be_whole_minutes():
    with pytest.raises(ValueError, match="whole number"):
        windows([datetime(2020, 5, 1, 1)], 1, "PER-CUM", 0.5)


def test_wrong_stamp_count_is_refused():
    with pytest.raises(ValueError, match="one longer"):
        windows([datetime(2020, 5, 1, 1)] * 3, 1, "PER-CUM", 60)


def test_aorc_interval_is_one_hour():
    assert HmsAorc.PRECIP_INTERVAL_MINUTES == 60


# ---------------------------------------------------------------------------
# Refusals reach the caller before any file exists (pyjnius import check only)
# ---------------------------------------------------------------------------


def _small_grid(nt=1):
    lat = np.array([41.0, 41.01])
    lon = np.array([-77.5, -77.49, -77.48])
    return np.ones((nt, 2, 3), dtype=np.float32), lat, lon


@pytest.mark.parametrize("kwargs,match", [
    ({"data_type": "PER-CUM"}, "interval_minutes"),
    ({"data_type": "PER-CUM", "interval_minutes": 0}, "no length"),
    ({"data_type": "BOGUS"}, "Unknown grid data type"),
])
def test_write_refuses_before_writing(tmp_path, kwargs, match):
    pytest.importorskip("jnius_config")
    grid, lat, lon = _small_grid()
    target = tmp_path / "out.dss"
    with pytest.raises(ValueError, match=match):
        HmsDssGrid.write_grid_timeseries(target, "/A/B/PRECIP////", grid, lat, lon,
                                         [datetime(2020, 5, 2)], **kwargs)
    assert not target.exists()


# ---------------------------------------------------------------------------
# Stored D and E parts (HEC Monolith)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def java():
    pytest.importorskip("jnius_config")
    # _ensure_monolith() downloads a missing Monolith; these tests stay offline.
    from hms_commander.dss._hec_monolith import HecMonolithDownloader

    if not HecMonolithDownloader().is_installed():
        pytest.skip("HEC Monolith is not installed; these tests do not download it")
    try:
        DssCore._ensure_monolith()
        DssCore._configure_jvm()
        from jnius import autoclass

        autoclass("hec.heclib.grid.GriddedData")
    except Exception as exc:  # no Java or no Monolith on this host
        pytest.skip(f"HEC Monolith unavailable: {exc}")


def _grid_parts(dss_file):
    paths = HmsDss.get_catalog(dss_file)
    paths = paths["pathname"].tolist() if hasattr(paths, "columns") else list(paths)
    return sorted((p.split("/")[4].upper(), p.split("/")[5].upper()) for p in paths)


@pytest.mark.requires_java
def test_java_writes_period_d_and_e_parts(java, tmp_path):
    grid, lat, lon = _small_grid(2)
    target = tmp_path / "period.dss"
    HmsDssGrid.write_grid_timeseries(
        target, "/A/B/PRECIP////", grid, lat, lon,
        [datetime(2020, 5, 2, 0), datetime(2020, 5, 2, 1)], interval_minutes=60)
    assert _grid_parts(target) == [
        ("01MAY2020:2300", "01MAY2020:2400"),
        ("02MAY2020:0000", "02MAY2020:0100"),
    ]


@pytest.mark.requires_java
def test_java_writes_per_aver_and_boundaries(java, tmp_path):
    grid, lat, lon = _small_grid(1)
    target = tmp_path / "aver.dss"
    HmsDssGrid.write_grid_timeseries(
        target, "/A/B/TEMPERATURE////", grid, lat, lon,
        [datetime(2020, 5, 1, 6), datetime(2020, 5, 1, 12)], units="DEG C", data_type="PER-AVER")
    assert _grid_parts(target) == [("01MAY2020:0600", "01MAY2020:1200")]


@pytest.mark.requires_java
def test_java_keeps_instantaneous_grids_as_instants(java, tmp_path):
    grid, lat, lon = _small_grid(1)
    target = tmp_path / "inst.dss"
    HmsDssGrid.write_grid_timeseries(
        target, "/A/B/SWE////", grid, lat, lon, [datetime(2020, 5, 1, 6)], data_type="INST-VAL")
    assert _grid_parts(target) == [("01MAY2020:0600", "01MAY2020:0600")]


@pytest.mark.requires_java
def test_java_writes_a_utc_instant_at_its_clock_time(java, tmp_path):
    grid, lat, lon = _small_grid(1)
    target = tmp_path / "utc.dss"
    HmsDssGrid.write_grid_timeseries(
        target, "/A/B/SWE////", grid, lat, lon,
        [datetime(2020, 1, 1, 12, tzinfo=timezone.utc)], data_type="INST-VAL")
    assert _grid_parts(target) == [("01JAN2020:1200", "01JAN2020:1200")]


# ---------------------------------------------------------------------------
# End to end: AORC-shaped NetCDF -> DSS -> HEC-HMS
# ---------------------------------------------------------------------------

CELL = 1.0 / 120.0  # AORC spacing, degrees
RUN = "Jan 96 storm"
BURST_END = pd.Timestamp("1996-01-17 12:00")
GRID_PATH = "/AORC/TENK/PRECIP////"
#: HEC-HMS 4.9 read no DSS7 grid (ERROR 12520 and no rain), so it gets an existing DSS6 file.
DSS7_FROM = (4, 10)


def _version_key(version):
    return tuple(int(p) for p in version.split("."))


def _installed_hms():
    """Installed versions HmsCmdr runs here: 4.4.1 and later (4.0 to 4.3 are not supported)."""
    from hms_commander import HmsExamples

    found = HmsExamples.detect_installed_versions()
    return sorted((v for v in found if _version_key(v) >= (4, 4, 1)), key=_version_key)


def _backends():
    """Java everywhere; native too where this version of the library has that backend."""
    return ["java", "native"] if hasattr(HmsDss, "get_backend") else ["java"]


def _aorc_netcdf(path, x0, y0, nx, ny, split_row):
    """An ``APCP_surface`` array on a WGS84 lattice at the Illinois River basin: 100 mm in
    one hour, on rows from ``split_row`` north only, so a wrong row order or a stamp error
    changes the result."""
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    times = pd.date_range("1996-01-17 01:00", "1996-01-21 23:00", freq="h")
    data = np.zeros((len(times), ny, nx), dtype=np.float32)
    data[times.get_loc(BURST_END), split_row:, :] = 100.0
    xr.DataArray(
        data, name="APCP_surface", dims=("time", "latitude", "longitude"),
        coords={"time": times, "latitude": (y0 + np.arange(ny)) * CELL,
                "longitude": (x0 + np.arange(nx)) * CELL},
    ).to_netcdf(path)


def _run_aorc(tmp_path, version, monkeypatch, backend="java", stamps_as_before=False):
    """Move tenk's cells to the WGS84 index lattice, convert the NetCDF, compute the run.
    Returns the log, each subbasin's PRECIP-INC, and each subbasin's expected burst depth."""
    from hms_commander import HmsCmdr, HmsExamples
    from hms_commander.HmsPrj import HmsPrj, init_hms_project

    project = Path(HmsExamples.extract_project("tenk", version=version, output_path=tmp_path))
    cells = project / "regions" / "hrapcells"  # the file Tenk_1.basin names
    text = cells.read_text()
    found = re.findall(r"GRIDCELL:\s+(\d+)\s+(\d+)", text)
    xs, ys = [int(x) for x, _ in found], [int(y) for _, y in found]
    nx, ny = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
    # write_grid_timeseries stores the lower-left cell as round(coordinate / cell size).
    x0, y0 = round(-95.3 / CELL), round(35.4 / CELL)
    cells.write_text(re.sub(
        r"GRIDCELL:\s+(\d+)\s+(\d+)",
        lambda m: f"GRIDCELL: {x0 + int(m[1]) - min(xs)} {y0 + int(m[2]) - min(ys)}", text))

    split_row = ny // 2
    netcdf = project / "aorc.nc"
    _aorc_netcdf(netcdf, x0, y0, nx, ny, split_row)
    # The conversion needs xarray and netCDF4 only; the check also asks for zarr and s3fs.
    monkeypatch.setattr(sys.modules["hms_commander.HmsAorc"], "_check_aorc_dependencies", lambda: None)
    if stamps_as_before:
        monkeypatch.setattr(HmsDssGrid, "_grid_time_windows", staticmethod(
            lambda ts, n, d, i=None: [(pd.Timestamp(t), pd.Timestamp(t)) for t in ts]))
    if backend == "native":
        pytest.importorskip("ras_commander_fast_dss")
        monkeypatch.setattr(HmsDss, "backend", backend)
    # An existing file keeps its version. The sample's hrap.dss holds other pathnames.
    target = project / ("aorc.dss" if _version_key(version) >= DSS7_FROM else "hrap.dss")
    HmsAorc.convert_to_dss_grid(netcdf, target, GRID_PATH)
    monkeypatch.undo()

    grid = project / "tenk.grid"
    grid.write_text(grid.read_text()
                    .replace("hrap.dss", target.name)
                    .replace("/HRAP/ABRFC/PRECIP////", GRID_PATH))
    results = project / "Jan_96_storm.dss"
    results.unlink(missing_ok=True)
    prj = init_hms_project(project, hms_exe_path=HmsExamples.get_hms_exe(version), hms_object=HmsPrj())
    assert HmsCmdr.compute_run(RUN, hms_object=prj, timeout=900)
    log = (project / "Jan_96_storm.log").read_text(errors="replace")

    # Area-weighted share of each subbasin's cells that the burst covers.
    areas, sub = {}, None
    for line in text.splitlines():
        parts = line.replace(":", " ").split()
        if parts[:1] == ["SUBBASIN"]:
            sub = parts[1]
            areas[sub] = [0.0, 0.0]
        elif parts[:1] == ["GRIDCELL"]:
            areas[sub][0] += float(parts[4])
            if int(parts[2]) - min(ys) >= split_row:
                areas[sub][1] += float(parts[4])

    depth = {}
    for name in areas:
        rain = HmsDss.read_timeseries(results, f"//{name}/PRECIP-INC/01Jan1996/1Hour/RUN:{RUN}/")
        depth[name] = rain.set_index("datetime")["value"].astype(float)
    return log, depth, {k: v[1] / v[0] * 100.0 / 25.4 for k, v in areas.items()}


@pytest.mark.requires_hms
@pytest.mark.requires_java
@pytest.mark.local_hms
@pytest.mark.slow
@pytest.mark.parametrize("backend", _backends())
@pytest.mark.parametrize("version", _installed_hms())
def test_wgs84_grid_gives_rain_in_hms(java, tmp_path, monkeypatch, version, backend):
    log, depth, expected = _run_aorc(tmp_path, version, monkeypatch, backend)
    assert "WARNING 40503" not in log
    assert max(expected.values()) > 1.0 and min(expected.values()) < max(expected.values())
    for name, series in depth.items():
        # All of the burst lands in the step ending at the stamp, at the share of the
        # subbasin's area under it. Row order and timing errors both change this.
        assert series.loc[BURST_END] == pytest.approx(expected[name], rel=1e-3, abs=1e-4), name
        assert series.drop(BURST_END).abs().max() == pytest.approx(0.0, abs=1e-6), name


@pytest.mark.requires_hms
@pytest.mark.requires_java
@pytest.mark.local_hms
@pytest.mark.slow
@pytest.mark.parametrize("version", _installed_hms()[-1:])
def test_equal_d_and_e_parts_give_no_rain_in_hms(java, tmp_path, monkeypatch, version):
    """Why zero-length periods are refused: the earlier stamp form, otherwise the same run."""
    log, depth, _ = _run_aorc(tmp_path, version, monkeypatch, stamps_as_before=True)
    assert "WARNING 40503" in log
    assert all(series.abs().max() == 0.0 for series in depth.values())
