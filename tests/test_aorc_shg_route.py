"""The optional SHG route of ``HmsAorc.convert_to_dss_grid`` (native gridded importer).

- The argument checks need neither the engine nor Java.
- The engine tests write through ``ras_commander_fast_dss.gridded`` and read the records
  back. They skip when the engine, or its ``gridded_import`` feature, is absent.
- The ``local_hms`` test converts an AORC-shaped WGS84 NetCDF to SHG grids and runs the
  tenk sample with ``HmsCmdr`` after moving its cells onto that SHG lattice. It builds its
  NetCDF in the test, with no network, and skips without the engine or an HEC-HMS
  ``samples.zip``.

The default (``target_crs=None``) WGS84 route is covered by ``test_aorc_period_stamps.py``.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hms_commander import HmsAorc, HmsDssGrid
from hms_commander.dss import HmsDss
from hms_commander.dss import _backend

CELL = 1.0 / 120.0  # AORC spacing, degrees


def _small(nt=3):
    lat = (4250 + np.arange(40)) * CELL  # about 35.4 N
    lon = (-11440 + np.arange(50)) * CELL  # about -95.3 E
    data = np.zeros((nt, 40, 50), dtype=np.float32)
    data[min(1, nt - 1), 20:, :] = 10.0  # northern half wet in the second hour
    stamps = [datetime(2020, 5, 1, h) for h in range(1, nt + 1)]  # period ends
    return data, lat, lon, stamps


# ---------------------------------------------------------------------------
# Argument checks (no engine, no Java): nothing is written
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kwargs,match", [
    ({"target_crs": "HRAP"}, "target_crs must be one of"),
    ({"target_crs": "EPSG:5070"}, "target_crs must be one of"),
    ({"target_crs": "SHG", "resample_method": "cubic"}, "resample_method"),
    ({"target_crs": "SHG", "cell_size": 0}, "cell_size"),
    ({"target_crs": "SHG", "cell_size": float("nan")}, "cell_size"),
    ({"target_crs": "SHG", "envelope": (0, 0, 1)}, "envelope"),
    ({"cell_size": 2000}, "only with target_crs"),
    ({"envelope": (0, 0, 1, 1)}, "only with target_crs"),
])
def test_bad_arguments_are_refused_before_writing(tmp_path, monkeypatch, kwargs, match):
    def no_engine():
        raise AssertionError("the engine must not be reached")

    monkeypatch.setattr(_backend, "require_native_gridded_import", no_engine)
    data, lat, lon, stamps = _small()
    target = tmp_path / "out.dss"
    with pytest.raises(ValueError, match=match):
        HmsDssGrid.write_grid_timeseries(target, "/A/B/PRECIP////", data, lat, lon, stamps,
                                         **kwargs)
    assert not target.exists()


@pytest.mark.parametrize("pathname,match", [
    ("/A/B//D/E/F/", "needs a C part"),
    ("/A/B/PRECIP/", "six parts"),
])
def test_bad_pathnames_are_refused(tmp_path, monkeypatch, pathname, match):
    monkeypatch.setattr(_backend, "require_native_gridded_import", lambda: pytest.fail("engine"))
    data, lat, lon, stamps = _small()
    with pytest.raises(ValueError, match=match):
        HmsDssGrid.write_grid_timeseries(tmp_path / "x.dss", pathname, data, lat, lon, stamps,
                                         target_crs="SHG")


def test_uneven_lattice_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(_backend, "require_native_gridded_import", lambda: pytest.fail("engine"))
    data, lat, lon, stamps = _small()
    lon = lon.copy()
    lon[10] += CELL / 2
    with pytest.raises(ValueError, match="evenly spaced"):
        HmsDssGrid.write_grid_timeseries(tmp_path / "x.dss", "/A/B/PRECIP////", data, lat, lon,
                                         stamps, target_crs="SHG")


def test_lattice_transform_is_the_outer_cell_edge():
    assert HmsDssGrid._lattice_transform([0.5, 1.5, 2.5], "x") == (0.0, 1.0)
    assert HmsDssGrid._lattice_transform([2.5, 1.5, 0.5], "y") == (3.0, -1.0)
    with pytest.raises(ValueError, match="at least two"):
        HmsDssGrid._lattice_transform([1.0], "x")


def test_missing_gridded_feature_is_a_capability_error(monkeypatch):
    monkeypatch.setattr(_backend, "import_native", lambda: object())
    monkeypatch.setattr(_backend, "engine_features", lambda: frozenset({"write_profile"}))
    with pytest.raises(_backend.DssCapabilityError, match="gridded_import"):
        _backend.require_native_gridded_import()


def test_capabilities_list_the_shg_route():
    caps = HmsDss.get_capabilities()
    row = caps[caps["operation"] == "write_grid_timeseries(target_crs='SHG')"]
    assert len(row) == 1 and set(row.iloc[0][["java", "native", "shadow"]]) == {"gated"}
    assert "native_gridded_import_available" in caps.attrs


# ---------------------------------------------------------------------------
# Engine: what the SHG route stores
# ---------------------------------------------------------------------------


def _paths(dc, dss_file):
    return sorted(dc.get_catalog(str(dss_file))["pathname"].tolist())


@pytest.fixture
def engine():
    pytest.importorskip("ras_commander_fast_dss")
    if not _backend.native_gridded_import_available():
        pytest.skip("the installed engine has no gridded importer")
    import ras_commander_fast_dss as dc

    return dc


@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
def test_shg_records_whatever_the_backend(engine, tmp_path, monkeypatch, backend):
    monkeypatch.setattr(HmsDss, "backend", backend)
    data, lat, lon, stamps = _small()
    target = tmp_path / "shg.dss"
    HmsDssGrid.write_grid_timeseries(target, "/AORC/TEST/PRECIP//x/F1/", data, lat, lon,
                                     stamps, target_crs="SHG")
    paths = _paths(engine, target)
    # The same D and E parts as the WGS84 route: stamps are period ends.
    assert paths == [
        "/AORC/TEST/PRECIP/01MAY2020:0000/01MAY2020:0100/F1/",
        "/AORC/TEST/PRECIP/01MAY2020:0100/01MAY2020:0200/F1/",
        "/AORC/TEST/PRECIP/01MAY2020:0200/01MAY2020:0300/F1/",
    ]
    g = engine.read_grid(str(target), paths[1])
    assert g.grid_type == "albers"
    assert g.cell_size == 2000.0
    assert g.data_units == "MM"
    assert g.data_type == 1  # PER-CUM
    albers = g.metadata["albers"]
    assert (albers["central_meridian"], albers["first_standard_parallel"],
            albers["second_standard_parallel"], albers["latitude_of_projection_origin"]) == (
        -96.0, 29.5, 45.5, 23.0)
    # Row 0 is the southern row: the wet half of the source is the north.
    column = g.data[:, g.nx // 2]
    valid = column[np.isfinite(column)]
    assert valid[0] == 0.0 and valid[-1] == pytest.approx(10.0)
    assert np.nanmax(engine.read_grid(str(target), paths[0]).data) == 0.0


def test_shg_envelope_and_cell_size_are_honoured(engine, tmp_path):
    data, lat, lon, stamps = _small(1)
    target = tmp_path / "shg.dss"
    box = (60_000.0, 1_376_000.0, 80_000.0, 1_392_000.0)  # whole 4 km cells inside the data
    HmsDssGrid.write_grid_timeseries(target, "/A/B/PRECIP////", data, lat, lon, stamps,
                                     interval_minutes=60, target_crs="shg", cell_size=4000,
                                     envelope=box, resample_method="near")
    g = engine.read_grid(str(target), _paths(engine, target)[0])
    assert (g.cell_size, g.nx, g.ny) == (4000.0, 5, 4)
    assert (g.lower_left_cell_x, g.lower_left_cell_y) == (15, 344)


def test_refused_warp_leaves_no_file(engine, tmp_path):
    data, lat, lon, stamps = _small(1)
    target = tmp_path / "shg.dss"
    dc_errors = pytest.importorskip("ras_commander_fast_dss.exceptions")
    with pytest.raises(dc_errors.DssUnsupportedRecordError, match="limit"):
        # An output grid over the engine's cell limit is refused while the run is planned.
        HmsDssGrid.write_grid_timeseries(target, "/A/B/PRECIP////", data, lat, lon, stamps,
                                         interval_minutes=60, target_crs="SHG",
                                         envelope=(-5e6, -5e6, 5e6, 5e6))
    assert not target.exists()


def test_convert_to_dss_grid_passes_the_shg_route(engine, tmp_path, monkeypatch):
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    data, lat, lon, _ = _small(3)
    times = pd.date_range("2020-05-01 01:00", periods=3, freq="h")
    nc = tmp_path / "aorc.nc"
    xr.DataArray(data, name="APCP_surface", dims=("time", "latitude", "longitude"),
                 coords={"time": times, "latitude": lat, "longitude": lon}).to_netcdf(nc)
    monkeypatch.setattr(sys.modules["hms_commander.HmsAorc"], "_check_aorc_dependencies",
                        lambda: None)
    out = HmsAorc.convert_to_dss_grid(nc, tmp_path / "shg.dss", "/AORC/TEST/PRECIP////",
                                      target_crs="SHG")
    paths = _paths(engine, out)
    assert len(paths) == 3
    assert engine.read_grid(str(out), paths[0]).grid_type == "albers"


# ---------------------------------------------------------------------------
# End to end: AORC-shaped NetCDF -> SHG DSS grids -> HEC-HMS
# ---------------------------------------------------------------------------

RUN = "Jan 96 storm"
BURST_END = pd.Timestamp("1996-01-17 12:00")
GRID_PATH = "/SHG/TENK/PRECIP////"
#: The SHG cell (2 km) given to tenk's south-west cell; about -95.2 E, 35.9 N.
SHG_ORIGIN = (34, 700)
#: The NetCDF extent, which covers that block of SHG cells with a margin.
LON_RANGE, LAT_RANGE = (-96.5, -93.5), (34.5, 37.5)
#: HEC-HMS 4.9 read no DSS7 grid (ERROR 12520 and no rain), so it gets an existing DSS6 file.
DSS7_FROM = (4, 10)


def _version_key(version):
    return tuple(int(p) for p in version.split("."))


def _installed_hms():
    """Installed versions HmsCmdr runs here: 4.4.1 and later (4.0 to 4.3 are not supported)."""
    from hms_commander import HmsExamples

    found = HmsExamples.detect_installed_versions()
    return sorted((v for v in found if _version_key(v) >= (4, 4, 1)), key=_version_key)


def _aorc_netcdf(path):
    """``APCP_surface`` on the AORC lattice over the extent: in the burst hour, a depth
    rising from 0 mm in the south to 100 mm in the north, so a row-order error or a stamp
    error changes every subbasin's result; no rain otherwise."""
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    times = pd.date_range("1996-01-17 01:00", "1996-01-21 23:00", freq="h")
    lat = np.arange(round(LAT_RANGE[0] / CELL), round(LAT_RANGE[1] / CELL)) * CELL + CELL / 2
    lon = np.arange(round(LON_RANGE[0] / CELL), round(LON_RANGE[1] / CELL)) * CELL + CELL / 2
    data = np.zeros((len(times), len(lat), len(lon)), dtype=np.float32)
    ramp = (100.0 * (lat - LAT_RANGE[0]) / (LAT_RANGE[1] - LAT_RANGE[0])).astype(np.float32)
    data[times.get_loc(BURST_END)] = ramp[:, np.newaxis]
    xr.DataArray(data, name="APCP_surface", dims=("time", "latitude", "longitude"),
                 coords={"time": times, "latitude": lat, "longitude": lon}).to_netcdf(path)


def _run_shg(tmp_path, version, monkeypatch, engine):
    """Move tenk's cells onto the SHG lattice, convert the NetCDF to SHG, compute the run.
    Returns the log, each subbasin's PRECIP-INC, and the burst depth each subbasin should
    get from the SHG grid as stored (area-weighted over its cells, in inches)."""
    from hms_commander import HmsCmdr, HmsExamples
    from hms_commander.HmsPrj import HmsPrj, init_hms_project

    project = Path(HmsExamples.extract_project("tenk", version=version, output_path=tmp_path))
    cells = project / "regions" / "hrapcells"  # the file Tenk_1.basin names
    text = cells.read_text()
    found = re.findall(r"GRIDCELL:\s+(\d+)\s+(\d+)", text)
    min_x = min(int(x) for x, _ in found)
    min_y = min(int(y) for _, y in found)
    x0, y0 = SHG_ORIGIN
    text = re.sub(r"GRIDCELL:\s+(\d+)\s+(\d+)",
                  lambda m: f"GRIDCELL: {x0 + int(m[1]) - min_x} {y0 + int(m[2]) - min_y}", text)
    cells.write_text(text)

    netcdf = project / "aorc.nc"
    _aorc_netcdf(netcdf)
    # The conversion needs xarray and netCDF4 only; the check also asks for zarr and s3fs.
    monkeypatch.setattr(sys.modules["hms_commander.HmsAorc"], "_check_aorc_dependencies",
                        lambda: None)
    # An existing file keeps its version. The sample's hrap.dss holds other pathnames.
    target = project / ("aorc_shg.dss" if _version_key(version) >= DSS7_FROM else "hrap.dss")
    HmsAorc.convert_to_dss_grid(netcdf, target, GRID_PATH, target_crs="SHG")
    monkeypatch.undo()

    burst = f"/SHG/TENK/PRECIP/17JAN1996:1100/17JAN1996:1200//"
    grid = engine.read_grid(str(target), burst)
    assert grid.grid_type == "albers" and grid.cell_size == 2000.0

    definition = project / "tenk.grid"
    definition.write_text(definition.read_text()
                          .replace("hrap.dss", target.name)
                          .replace("/HRAP/ABRFC/PRECIP////", GRID_PATH))
    results = project / "Jan_96_storm.dss"
    results.unlink(missing_ok=True)
    prj = init_hms_project(project, hms_exe_path=HmsExamples.get_hms_exe(version),
                           hms_object=HmsPrj())
    assert HmsCmdr.compute_run(RUN, hms_object=prj, timeout=900)
    log = (project / "Jan_96_storm.log").read_text(errors="replace")

    weighted, sub = {}, None
    for line in text.splitlines():
        parts = line.replace(":", " ").split()
        if parts[:1] == ["SUBBASIN"]:
            sub = parts[1]
            weighted[sub] = [0.0, 0.0]
        elif parts[:1] == ["GRIDCELL"]:
            col = int(parts[1]) - grid.lower_left_cell_x
            row = int(parts[2]) - grid.lower_left_cell_y  # row 0 is the southern row
            value = float(grid.data[row, col])
            assert np.isfinite(value), (parts[1], parts[2])
            weighted[sub][0] += float(parts[4])
            weighted[sub][1] += float(parts[4]) * value

    depth = {}
    for name in weighted:
        rain = HmsDss.read_timeseries(results,
                                      f"//{name}/PRECIP-INC/01Jan1996/1Hour/RUN:{RUN}/")
        depth[name] = rain.set_index("datetime")["value"].astype(float)
    return log, depth, {k: v[1] / v[0] / 25.4 for k, v in weighted.items()}


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
@pytest.mark.parametrize("version", _installed_hms())
def test_shg_grid_gives_rain_in_hms(engine, tmp_path, monkeypatch, version):
    log, depth, expected = _run_shg(tmp_path, version, monkeypatch, engine)
    assert "WARNING 40503" not in log
    # The ramp gives each subbasin a different depth, so a row or column error shows.
    assert len({round(v, 3) for v in expected.values()}) == len(expected)
    for name, series in depth.items():
        assert series.loc[BURST_END] == pytest.approx(expected[name], rel=1e-3, abs=1e-4), name
        assert series.drop(BURST_END).abs().max() == pytest.approx(0.0, abs=1e-6), name
