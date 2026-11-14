"""Parity fixes that came with the native default (see the parity audit in the PR).

- ``write_timeseries`` refuses stamps that are not regular for the E part on every
  backend. HEC Monolith stored such series by position and silently moved values; the
  native writer refused them.
- A native read of a record of another kind raises ``ValueError``, as the Java path does.

Java cases skip when Java/pyjnius or HEC Monolith is unavailable; native cases skip
without the engine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from hms_commander.dss import DssCore, HmsDss
from hms_commander.dss import _backend

HOURS = pd.date_range("2020-01-01 01:00", periods=6, freq="h")


@pytest.fixture(autouse=True)
def _restore_backend(monkeypatch):
    monkeypatch.delenv(_backend.ENV_VAR, raising=False)
    saved = HmsDss.backend
    HmsDss.backend = None
    _backend.reset_fallback_warning()
    yield
    HmsDss.backend = saved


def _engine():
    try:
        import ras_commander_fast_dss  # noqa: F401
    except Exception as exc:
        pytest.skip(f"ras_commander_fast_dss unavailable: {exc}")


def _java():
    if not DssCore.java_available():
        pytest.skip("pyjnius is not installed")
    try:
        DssCore._configure_jvm()
        from jnius import autoclass

        autoclass("hec.heclib.dss.HecDss")
    except Exception as exc:
        pytest.skip(f"HEC Monolith Java bridge unavailable: {type(exc).__name__}: {exc}")


@pytest.fixture(params=["java", "native"])
def backend(request):
    (_java if request.param == "java" else _engine)()
    HmsDss.backend = request.param
    return request.param


@pytest.mark.parametrize("pathname, times, match", [
    ("//G/FLOW//1HOUR/OBS/", HOURS.delete(3), "value 3 is at"),          # a missing hour
    ("//G/FLOW//15MIN/OBS/", HOURS, "value 1 is at"),                    # hourly under 15MIN
    ("//G/FLOW//1DAY/OBS/", pd.DatetimeIndex(["2020-01-01", "2020-01-02", "2020-01-04"]),
     "value 2 is at"),
    ("//G/FLOW//1MON/OBS/", pd.DatetimeIndex(["2020-02-01", "2020-03-01", "2020-04-02"]),
     "value 2 is at"),
])
def test_irregular_stamps_are_refused_on_every_backend(backend, tmp_path, pathname, times, match):
    target = tmp_path / "irregular.dss"
    with pytest.raises(ValueError, match=match):
        HmsDss.write_timeseries(target, pathname, times, np.arange(len(times), dtype=float))
    assert not target.exists()


@pytest.mark.parametrize("pathname, times", [
    ("//G/FLOW//1HOUR/OBS/", HOURS),
    ("//G/FLOW//15MIN/OBS/", pd.date_range("2020-01-01 00:15", periods=9, freq="15min")),
    ("//G/FLOW//1DAY/OBS/", pd.date_range("2020-01-01", periods=40, freq="D")),
    ("//G/FLOW//1MON/OBS/", pd.DatetimeIndex(["2020-02-01", "2020-03-01", "2020-04-01",
                                              "2020-05-01"])),
    ("//G/FLOW//1HOUR/OBS/", HOURS[:1]),
])
def test_regular_stamps_are_written_on_every_backend(backend, tmp_path, pathname, times):
    target = tmp_path / "regular.dss"
    values = np.arange(len(times), dtype=float) + 0.5
    HmsDss.write_timeseries(target, pathname, times, values)
    HmsDss.backend = "native" if _backend.native_available() else "java"
    path = HmsDss.get_catalog(target)[0]
    back = HmsDss.read_timeseries(target, path)
    assert list(back["datetime"]) == list(times)
    np.testing.assert_array_equal(back["value"].to_numpy(dtype=float), values)


def test_irregular_check_names_the_remedy():
    with pytest.raises(ValueError, match="fill the gaps with NaN"):
        DssCore._prepare_timeseries("//G/FLOW//1HOUR/OBS/", HOURS.delete(2), np.arange(5.0))


def test_unchecked_e_parts_are_left_to_the_writer():
    # SEMI-MONTH and TRI-MONTH have no fixed or monthly step; the writer decides.
    DssCore._check_regular_stamps("//G/FLOW//SEMI-MONTH/OBS/", "SEMI-MONTH",
                                  pd.DatetimeIndex(["2020-01-16", "2020-02-01", "2020-02-29"])
                                  .to_numpy(dtype="datetime64[s]"))


def test_native_wrong_record_kind_is_a_value_error(tmp_path):
    _engine()
    HmsDss.backend = "native"
    pd_file, ts_file = tmp_path / "pd.dss", tmp_path / "ts.dss"
    HmsDss.write_paired_data(pd_file, "//G/SF///T/", np.arange(3.0), np.arange(3.0),
                             "FT", "CFS", "L", "L")
    HmsDss.write_timeseries(ts_file, "//G/FLOW//1HOUR/R/", HOURS[:3], np.arange(3.0))
    with pytest.raises(ValueError, match="not a time-series record"):
        HmsDss.read_timeseries(pd_file, "//G/SF///T/")
    with pytest.raises(ValueError, match="not a grid record"):
        HmsDss.read_grid(ts_file, "//G/FLOW/01JAN2020/1HOUR/R/")
    # Unchanged contracts: None for the HMS dict readers.
    assert HmsDss.read_paired_data(ts_file, "//G/FLOW//1HOUR/R/") is None
    assert DssCore.get_peak_value(pd_file, "//G/SF///T/") is None
