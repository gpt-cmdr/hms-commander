"""Regression tests: DSS reads and writes release the native file on return.

Through pyjnius, HEC Monolith's ``HecDss.done()`` only lowers a file-cache
reference count. The native file, and its DSS lock words, stay open until a
background timer closes it about 6 seconds later. hms-commander therefore calls
``HecDSSFileAccess.close(path, True)`` with the path string it opened.

The Java tests check the release while the JVM is still running. On Windows a
file that Monolith holds open cannot be renamed (sharing violation), so each
test renames the file and back immediately after the hms-commander call. All
data is synthetic and created inside the test. Java tests skip when pyjnius,
Java or the HEC Monolith libraries are unavailable.
"""

from __future__ import annotations

import logging
import os
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from hms_commander.dss import DssCore, HmsDss, HmsDssGrid

SERIES_PATH = "/SYNTH/GAGE/FLOW/01JAN2020/1Hour/PUBLIC/"
CURVE_PATH = "//SYN_R1/CURVE/24HR//A/"


# ---------------------------------------------------------------------------
# Release helper contract (no Java)
# ---------------------------------------------------------------------------


def _fake_jnius(monkeypatch, close):
    """Install a stand-in ``jnius`` module whose HecDSSFileAccess.close is ``close``."""
    access = types.SimpleNamespace(close=close)
    module = types.SimpleNamespace(autoclass=lambda name: access)
    monkeypatch.setitem(sys.modules, "jnius", module)


def test_release_closes_the_exact_path_string(monkeypatch):
    calls = []
    _fake_jnius(monkeypatch, lambda path, force: calls.append((path, force)))
    DssCore._release_dss_file(r"C:\Data\Results Folder\run.dss")
    assert calls == [(r"C:\Data\Results Folder\run.dss", True)]


def test_release_failure_is_logged_at_debug_and_not_raised(monkeypatch, caplog):
    def close(path, force):
        raise RuntimeError("close failed")

    _fake_jnius(monkeypatch, close)
    with caplog.at_level(logging.DEBUG, logger="hms_commander.dss.core"):
        DssCore._release_dss_file("x.dss")
    assert any("close failed" in r.getMessage() and r.levelno == logging.DEBUG
               for r in caplog.records)


def test_done_error_propagates_and_file_is_still_released(monkeypatch):
    calls = []

    def close(path, force):
        calls.append(path)
        raise RuntimeError("release error must not replace the done() error")

    _fake_jnius(monkeypatch, close)

    class Handle:
        def done(self):
            raise ValueError("done failed")

    with pytest.raises(ValueError, match="done failed"):
        DssCore._done_and_release(Handle(), "x.dss")
    assert calls == ["x.dss"]


# ---------------------------------------------------------------------------
# HEC Monolith (Java required; rename check requires Windows)
# ---------------------------------------------------------------------------

windows_only = pytest.mark.skipif(
    os.name != "nt", reason="open-handle check relies on Windows sharing semantics"
)


@pytest.fixture(scope="module")
def java():
    if not DssCore.is_available():
        pytest.skip("pyjnius is not installed")
    try:
        DssCore._configure_jvm()
        from jnius import autoclass, cast

        autoclass("hec.heclib.dss.HecDSSFileAccess")
    except Exception as exc:  # Java, JVM or Monolith unavailable
        pytest.skip(f"HEC Monolith Java bridge unavailable: {type(exc).__name__}: {exc}")
    return autoclass, cast


def _assert_released(dss_file: Path) -> None:
    """Rename the file and back; Windows refuses while a handle is open."""
    moved = dss_file.with_name(dss_file.name + ".moved")
    try:
        os.rename(dss_file, moved)
    except PermissionError as exc:
        pytest.fail(f"{dss_file.name} is still held open after the call returned: {exc}")
    os.rename(moved, dss_file)


def _write_series_raw(java, dss_file: Path) -> None:
    """Write an hourly series with HecDss directly and close it (test setup)."""
    autoclass, cast = java
    path = str(dss_file.resolve())
    container = autoclass("hec.io.TimeSeriesContainer")()
    start = int((datetime(2020, 1, 1, 1) - datetime(1899, 12, 31)).total_seconds() // 60)
    container.fullName = SERIES_PATH
    container.units = "CFS"
    container.type = "INST-VAL"
    container.interval = 60
    container.setTimeGranularitySeconds(60)
    times = autoclass("hec.heclib.util.HecTimeArray")()
    assert times.set([start + 60 * i for i in range(5)], 60, 0) == 0
    assert container.setTimes(times) == 0
    assert container.setValues([1.0, 2.0, 3.0, 2.0, 1.0]) == 0
    container.numberValues = 5
    dss = autoclass("hec.heclib.dss.HecDss").open(path)
    try:
        dss.put(cast("hec.io.DataContainer", container))
    finally:
        dss.done()
        autoclass("hec.heclib.dss.HecDSSFileAccess").close(path, True)


@pytest.fixture
def series_file(java, tmp_path):
    dss_file = tmp_path / "series.dss"
    _write_series_raw(java, dss_file)
    _assert_released(dss_file)  # precondition: setup left no handle
    return dss_file


@windows_only
@pytest.mark.requires_java
def test_write_paired_data_releases_file(java, tmp_path):
    dss_file = tmp_path / "pd.dss"
    x = np.linspace(0.0, 24.0, 25)
    assert HmsDss.write_paired_data(dss_file, CURVE_PATH, x, x / 24.0) is True
    _assert_released(dss_file)

    records = [{"pathname": "//SYN_R1/CURVE/24HR//B/", "x_values": x, "y_values": x / 24.0}]
    assert DssCore.write_multiple_paired_data(dss_file, records) == {records[0]["pathname"]: True}
    _assert_released(dss_file)

    assert HmsDss.read_paired_data(dss_file, CURVE_PATH) is not None
    _assert_released(dss_file)


@windows_only
@pytest.mark.requires_java
def test_reads_release_file(series_file):
    assert SERIES_PATH.upper() in [p.upper() for p in HmsDss.get_catalog(series_file)]
    _assert_released(series_file)

    df = HmsDss.read_timeseries(series_file, SERIES_PATH)
    assert df["value"].tolist() == [1.0, 2.0, 3.0, 2.0, 1.0]
    _assert_released(series_file)

    assert DssCore.get_peak_value(series_file, SERIES_PATH)["peak_flow"] == 3.0
    _assert_released(series_file)


@windows_only
@pytest.mark.requires_java
def test_failed_read_raises_original_error_and_releases_file(series_file):
    with pytest.raises(ValueError, match="No data found"):
        DssCore.read_timeseries(series_file, "/SYNTH/NONE/FLOW/01JAN2020/1Hour/PUBLIC/")
    _assert_released(series_file)


@windows_only
@pytest.mark.requires_java
def test_grid_write_releases_file(java, tmp_path):
    dss_file = tmp_path / "grid.dss"
    start = datetime(2020, 1, 1, 1)
    HmsDssGrid.write_grid_timeseries(
        dss_file,
        "/SHG/SYNTH/PRECIP/01JAN2020:0000/01JAN2020:0100/AORC/",
        np.ones((2, 3, 4), dtype=np.float32),
        np.array([30.0, 30.1, 30.2]),
        np.array([-95.0, -94.9, -94.8, -94.7]),
        [start, start + timedelta(hours=1)],
    )
    _assert_released(dss_file)


@windows_only
@pytest.mark.requires_java
def test_short_8dot3_path_input_releases_file(series_file):
    import ctypes

    buffer = ctypes.create_unicode_buffer(1024)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(series_file.parent), buffer, 1024):
        pytest.skip("GetShortPathNameW failed")
    short_dir = Path(buffer.value)
    if str(short_dir) == str(series_file.parent):
        pytest.skip("no 8.3 short name for the temporary directory")

    HmsDss.read_timeseries(short_dir / series_file.name, SERIES_PATH)
    _assert_released(series_file)
