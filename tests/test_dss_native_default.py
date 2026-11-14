"""Parity fixes that came with the native default (see the parity audit in the PR).

- ``write_timeseries`` refuses stamps that are not regular for the E part on every
  backend. HEC Monolith stored such series by position and silently moved values; the
  native writer refused them.
- A native read of a record of another kind raises ``ValueError``, as the Java path does.

Java cases skip when Java/pyjnius or HEC Monolith is unavailable; native cases skip
without the engine.
"""

from __future__ import annotations

import logging
import tempfile

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


def _times(*stamps):
    return pd.DatetimeIndex(list(stamps))


def _java_ok():
    try:
        _java()
        return True
    except pytest.skip.Exception:
        return False


def _assert_kept(target, times, values, version, native_reader=True):
    """Every available reader returns each value at its given time."""
    readers = (["native"] if _backend.native_available() and native_reader else [])
    readers += ["java"] if _java_ok() else []
    weekly = "WEEK" in HmsDss.get_catalog(target)[0].upper()
    for reader in readers:
        if reader == "java" and version == 6 and weekly:
            continue  # the Java reader drops the first weekly value (shadow label D8)
        HmsDss.backend = reader
        back = HmsDss.read_timeseries(target, HmsDss.get_catalog(target)[0])
        assert list(back["datetime"]) == list(times), reader
        np.testing.assert_array_equal(back["value"].to_numpy(dtype=float), values, reader)


#: Inputs whose times HEC-DSS keeps (checked against HEC Monolith; see Review 1 in the PR).
#: Each is written on every backend, to DSS7 and DSS6, and read back exactly.
KEPT = {
    "hourly": ("1HOUR", HOURS),
    "hourly offset 00:15": ("1HOUR", pd.date_range("2020-01-01 00:15", periods=4, freq="h")),
    "15-minute across 29 February": (
        "15MIN", pd.date_range("2020-02-29 23:15", periods=6, freq="15min")),
    "daily across 29 February": ("1DAY", pd.date_range("2020-02-27", periods=5, freq="D")),
    "daily at 06:00": ("1DAY", pd.date_range("2019-12-30 06:00", periods=5, freq="D")),
    "single value": ("1HOUR", HOURS[:1]),
    "monthly, month ends (2400)": (
        "1MON", _times("2020-02-01", "2020-03-01", "2020-04-01", "2020-05-01")),
    "monthly, leap February end": (
        "1MON", _times("2020-01-01", "2020-02-01", "2020-03-01", "2020-04-01")),
    "monthly, mid-month across leap and common Februaries": (
        "1MON", pd.DatetimeIndex([pd.Timestamp("2019-11-15") + pd.DateOffset(months=i)
                                  for i in range(16)])),
    "monthly, 29 Feb 2020 12:00 offset": (
        "1MON", _times("2020-01-29 12:00", "2020-02-29 12:00", "2020-03-29 12:00",
                       "2020-04-29 12:00")),
    "yearly from 29 February (review)": ("1YEAR", _times("2020-02-29", "2021-03-01", "2022-03-01")),
    "yearly from 1 January": (
        "1YEAR", _times("2019-01-01", "2020-01-01", "2021-01-01", "2022-01-01")),
    "yearly, 15 June across a leap year": (
        "1YEAR", _times("2019-06-15", "2020-06-15", "2021-06-15")),
    "semi-month": ("SEMI-MONTH", _times("2020-01-16", "2020-02-01", "2020-02-16", "2020-03-01")),
    "tri-month across 29 February": (
        "TRI-MONTH", _times("2020-02-11", "2020-02-21", "2020-03-01", "2020-03-11")),
    "weekly": ("1WEEK", pd.date_range("2020-01-06", periods=5, freq="7D")),
}

#: Inputs HEC-DSS would store at other times (HEC Monolith moved these values before this
#: check). Each must be refused before anything is written, on every backend.
SHIFTED = {
    "a missing hour": ("1HOUR", HOURS.delete(3), "value 3 is at"),
    "hourly under 15MIN": ("15MIN", HOURS, "value 1 is at"),
    "a missing day": ("1DAY", _times("2020-01-01", "2020-01-02", "2020-01-04"), "value 2 is at"),
    "yearly 29 Feb then 28 Feb (review)": (
        "1YEAR", _times("2020-02-29", "2021-02-28", "2022-02-28"), "value 1"),
    "monthly month-end days (review)": (
        "1MON", _times("2020-02-29", "2020-03-31", "2020-04-30"), "value 0"),
    "monthly, a skipped month": ("1MON", _times("2020-02-01", "2020-03-01", "2020-04-02"), "value 2"),
    "monthly 30th across a 28-day February": (
        "1MON", _times("2019-01-30", "2019-03-02", "2019-03-30", "2019-04-30"), "value 1"),
    "monthly 30th, pandas month steps": (
        "1MON", _times("2019-01-30", "2019-02-28", "2019-03-30"), "value 1"),
    "semi-month off its half-month": (
        "SEMI-MONTH", _times("2020-01-16", "2020-02-01", "2020-02-29"), "value 2"),
    "semi-month 30th across February": (
        "SEMI-MONTH", _times("2019-01-30", "2019-02-15", "2019-03-02", "2019-03-15"), "value 2"),
    "tri-month 30th across February": (
        "TRI-MONTH", _times("2019-01-30", "2019-02-10", "2019-02-20", "2019-03-02"), "value 3"),
    "weekly from the first week of a DSS decade block": (
        "1WEEK", pd.date_range("2019-12-30", periods=4, freq="7D"), "value 0"),
}

#: DSS6 yearly times HEC keeps but engine 0.1.2's DSS6 writer refuses (engine gap for 0.1.3).
ENGINE_DSS6_YEARLY_GAP = {"yearly, 15 June across a leap year"}


@pytest.mark.parametrize("version", [7, 6])
@pytest.mark.parametrize("case", list(KEPT))
def test_times_hec_keeps_are_written_and_read_back_exactly(backend, tmp_path, case, version):
    e_part, times = KEPT[case]
    if backend == "native" and version == 6 and case in ENGINE_DSS6_YEARLY_GAP:
        with pytest.raises(ValueError, match="not regular"):
            HmsDss.write_timeseries(tmp_path / "gap.dss", f"//G/FLOW//{e_part}/OBS/", times,
                                    np.arange(len(times), dtype=float), dss_version=6)
        pytest.xfail("engine 0.1.2 refuses DSS6 yearly times HEC keeps (engine gap for 0.1.3)")
    target = tmp_path / "kept.dss"
    values = np.arange(len(times), dtype=float) + 0.5
    HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", times, values, dss_version=version)
    # Engine 0.1.2's DSS6 reader also places these yearly values a day early (engine gap);
    # HEC Monolith's reader is the reference for them.
    gap = version == 6 and case in ENGINE_DSS6_YEARLY_GAP
    _assert_kept(target, times, values, version, native_reader=not gap)


@pytest.mark.parametrize("version", [7, 6])
@pytest.mark.parametrize("case", list(SHIFTED))
def test_times_hec_would_move_are_refused_before_writing(backend, tmp_path, case, version):
    e_part, times, match = SHIFTED[case]
    target = tmp_path / "shifted.dss"
    with pytest.raises(ValueError, match=match):
        HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", times,
                                np.arange(len(times), dtype=float), dss_version=version)
    assert not target.exists()


@pytest.mark.parametrize("case", ["yearly 29 Feb then 28 Feb (review)",
                                  "monthly month-end days (review)",
                                  "monthly 30th across a 28-day February"])
def test_java_moves_the_refused_cases_without_the_check(tmp_path, monkeypatch, case):
    """Why the check exists: without it, HEC Monolith stores these values at other times."""
    _java()
    e_part, times, _ = SHIFTED[case]
    monkeypatch.setattr(DssCore, "_check_regular_stamps", staticmethod(lambda *a, **k: None))
    HmsDss.backend = "java"
    target = tmp_path / "moved.dss"
    HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", times,
                            np.arange(len(times), dtype=float))
    back = HmsDss.read_timeseries(target, HmsDss.get_catalog(target)[0])
    assert list(back["datetime"]) != list(times)


LEAP_YEARLY = {
    "leap year, 15 June": _times("2020-06-15", "2021-06-15", "2022-06-15"),
    "leap year, 3 March": _times("2020-03-03", "2021-03-03", "2022-03-03"),
    "leap year, 31 December": _times("2024-12-31", "2025-12-31", "2026-12-31"),
}


@pytest.mark.parametrize("case", list(LEAP_YEARLY))
def test_dss6_yearly_from_late_in_a_leap_year_is_refused(backend, tmp_path, case):
    times = LEAP_YEARLY[case]
    target = tmp_path / "leap6.dss"
    with pytest.raises(ValueError, match="DSS6 file"):
        HmsDss.write_timeseries(target, "//G/FLOW//1YEAR/OBS/", times,
                                np.arange(len(times), dtype=float), dss_version=6)
    assert not target.exists()


@pytest.mark.parametrize("case", list(LEAP_YEARLY))
def test_dss7_yearly_from_late_in_a_leap_year_is_kept(backend, tmp_path, case):
    times = LEAP_YEARLY[case]
    target = tmp_path / "leap7.dss"
    values = np.arange(len(times), dtype=float) + 0.5
    HmsDss.write_timeseries(target, "//G/FLOW//1YEAR/OBS/", times, values, dss_version=7)
    _assert_kept(target, times, values, 7)


@pytest.mark.parametrize("times", [
    _times("2020-02-28", "2021-02-28", "2022-02-28"),
    _times("2020-03-01", "2021-03-02", "2022-03-02"),   # 29 Feb 2400, HEC's leap placement
])
def test_dss6_yearly_up_to_the_leap_boundary_is_kept(backend, tmp_path, times):
    """The boundary of the DSS6 rule: HEC Monolith keeps these, so they are written."""
    target = tmp_path / "edge6.dss"
    values = np.arange(3, dtype=float) + 1
    HmsDss.write_timeseries(target, "//G/FLOW//1YEAR/OBS/", times, values, dss_version=6)
    _assert_kept(target, times, values, 6, native_reader=False)


def test_java_moves_dss6_yearly_from_late_in_a_leap_year_without_the_check(tmp_path, monkeypatch):
    _java()
    monkeypatch.setattr(DssCore, "_check_regular_stamps", staticmethod(lambda *a, **k: None))
    HmsDss.backend = "java"
    times = LEAP_YEARLY["leap year, 15 June"]
    target = tmp_path / "moved6.dss"
    HmsDss.write_timeseries(target, "//G/FLOW//1YEAR/OBS/", times,
                            np.arange(3, dtype=float), dss_version=6)
    back = HmsDss.read_timeseries(target, HmsDss.get_catalog(target)[0])
    assert list(back["datetime"]) != list(times)


#: Single values HEC-DSS stores at other times (review 2): (E part, version, time, where HEC
#: stores it). Each must be refused before anything is written, on every backend.
SINGLE_MOVED = {
    "DSS6 yearly, leap year after 2 March (review)": ("1YEAR", 6, "2020-06-15", "2020-06-16"),
    "DSS7 weekly, first week of a DSS decade block (review)": ("1WEEK", 7, "2019-12-30", "2020-01-06"),
    "DSS7 monthly, 29 February (review)": ("1MON", 7, "2020-02-29", "2020-03-01"),
    "DSS7 monthly, 31 January": ("1MON", 7, "2019-01-31", "2019-02-01"),
    "DSS7 semi-month, mid-month": ("SEMI-MONTH", 7, "2019-01-15", None),
    "DSS7 yearly, 31 December 12:00": ("1YEAR", 7, "2019-12-31 12:00", None),
}

#: Single values HEC-DSS keeps at their given time (checked with HEC Monolith, review 2),
#: including off-grid minutes on fixed intervals and single DSS6 offsets the check now
#: accepts through a DSS6 dry run.
SINGLE_KEPT = {
    "15MIN at 00:07": ("15MIN", (6, 7), "2019-12-31 23:07"),
    "1HOUR at 00:15": ("1HOUR", (6, 7), "2020-02-29 23:15"),
    "6HOUR at 03:17": ("6HOUR", (6, 7), "2020-01-01 03:17"),
    "1DAY at 06:00": ("1DAY", (6, 7), "2020-02-29 06:00"),
    "1MON at a month end": ("1MON", (6, 7), "2020-03-01"),
    "1YEAR from 29 February": ("1YEAR", (6, 7), "2020-02-29"),
    "1WEEK": ("1WEEK", (6, 7), "2020-01-06"),
    "DSS6 1MON on the 31st": ("1MON", (6,), "2019-01-31"),
    "DSS6 SEMI-MONTH on the 15th": ("SEMI-MONTH", (6,), "2019-01-15"),
    "DSS6 TRI-MONTH on the 20th": ("TRI-MONTH", (6,), "2019-01-20"),
}


@pytest.mark.parametrize("case", list(SINGLE_MOVED))
def test_a_single_value_hec_would_move_is_refused(backend, tmp_path, case):
    e_part, version, time, stored_at = SINGLE_MOVED[case]
    target = tmp_path / "one.dss"
    with pytest.raises(ValueError, match="Refused before writing") as caught:
        HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", _times(time), [42.0],
                                dss_version=version)
    assert not target.exists()
    if stored_at:
        assert stored_at in str(caught.value)
    assert "separately" not in str(caught.value)    # splitting writes is no remedy here


@pytest.mark.parametrize("case", ["DSS6 yearly, leap year after 2 March (review)",
                                  "DSS7 weekly, first week of a DSS decade block (review)",
                                  "DSS7 monthly, 29 February (review)"])
def test_java_moves_the_single_value_cases_without_the_check(tmp_path, monkeypatch, case):
    _java()
    e_part, version, time, stored_at = SINGLE_MOVED[case]
    monkeypatch.setattr(DssCore, "_check_regular_stamps", staticmethod(lambda *a, **k: None))
    HmsDss.backend = "java"
    target = tmp_path / "moved1.dss"
    HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", _times(time), [42.0],
                            dss_version=version)
    back = HmsDss.read_timeseries(target, HmsDss.get_catalog(target)[0])
    assert [str(t) for t in back["datetime"]] == [str(pd.Timestamp(stored_at))]


def test_one_and_two_dss6_yearly_values_from_the_same_leap_start_are_refused(backend, tmp_path):
    for times in (_times("2020-06-15"), _times("2020-06-15", "2021-06-15")):
        with pytest.raises(ValueError, match="DSS6 file"):
            HmsDss.write_timeseries(tmp_path / "leap.dss", "//G/FLOW//1YEAR/OBS/", times,
                                    np.arange(len(times), dtype=float), dss_version=6)
    assert not (tmp_path / "leap.dss").exists()


@pytest.mark.parametrize("case", list(SINGLE_KEPT))
def test_a_single_value_hec_keeps_is_written_at_its_time(backend, tmp_path, case):
    e_part, versions, time = SINGLE_KEPT[case]
    for version in versions:
        target = tmp_path / f"one{version}.dss"
        HmsDss.write_timeseries(target, f"//G/FLOW//{e_part}/OBS/", _times(time), [42.0],
                                dss_version=version)
        _assert_kept(target, _times(time), np.array([42.0]), version)


def test_dss6_only_single_offsets_are_still_refused_in_dss7(backend, tmp_path):
    """The DSS6 dry run qualifies single DSS6 values only; DSS7 keeps its own placement."""
    with pytest.raises(ValueError, match="2019-02-01"):
        HmsDss.write_timeseries(tmp_path / "x7.dss", "//G/FLOW//1MON/OBS/",
                                _times("2019-01-31"), [42.0], dss_version=7)


def test_the_dss6_leap_message_names_a_remedy_that_works(backend, tmp_path):
    times = _times("2020-06-15", "2021-06-15", "2022-06-15")
    with pytest.raises(ValueError, match="DSS7 file") as caught:
        HmsDss.write_timeseries(tmp_path / "a.dss", "//G/FLOW//1YEAR/OBS/", times,
                                np.arange(3.0), dss_version=6)
    assert "2020-06-16" in str(caught.value)
    target = tmp_path / "b.dss"            # the advice: the same times in a DSS7 file
    HmsDss.write_timeseries(target, "//G/FLOW//1YEAR/OBS/", times, np.arange(3.0), dss_version=7)
    _assert_kept(target, times, np.arange(3.0), 7)


def test_a_dss6_over_refusal_says_the_version_does_not_help(backend, tmp_path):
    """A multi-value DSS6 series HEC's DSS6 library keeps but the check refuses (review 2):
    the message says why, that DSS7 does not help, and that hms-commander cannot write it."""
    times = _times("2019-01-31", "2019-03-03", "2019-03-31")   # kept by HEC-DSS 6
    for version in (6, 7):
        with pytest.raises(ValueError) as caught:
            HmsDss.write_timeseries(tmp_path / f"o{version}.dss", "//G/FLOW//1MON/OBS/", times,
                                    np.arange(3.0), dss_version=version)
        text = str(caught.value)
        assert "Changing the DSS version does not help" in text
        assert ("cannot write those times" in text) is (version == 6)
        assert "Write it to a DSS7 file" not in text


def test_irregular_check_names_the_remedy():
    with pytest.raises(ValueError, match="fill the gaps with NaN"):
        DssCore._prepare_timeseries("//G/FLOW//1HOUR/OBS/", HOURS.delete(2), np.arange(5.0))


def test_irregular_e_parts_are_still_refused():
    with pytest.raises(ValueError, match="regular-interval data only"):
        DssCore._prepare_timeseries("//G/FLOW//IR-MONTH/OBS/", HOURS[:3], np.arange(3.0))


def test_calendar_check_without_the_engine_warns_once(monkeypatch, caplog):
    monkeypatch.setattr(_backend, "_maybe_native", lambda: None)
    monkeypatch.setattr(DssCore, "_calendar_check_warned", False)
    stamps = _times("2020-02-29", "2020-03-31").to_numpy(dtype="datetime64[s]")
    with caplog.at_level(logging.WARNING, logger="hms_commander.dss.core"):
        DssCore._check_regular_stamps("//G/FLOW//1MON/OBS/", "1MON", stamps)
        DssCore._check_regular_stamps("//G/FLOW//1MON/OBS/", "1MON", stamps)
    assert sum("not checked" in r.getMessage() for r in caplog.records) == 1
    # Fixed intervals are still checked without the engine.
    with pytest.raises(ValueError, match="value 3 is at"):
        DssCore._check_regular_stamps("//G/FLOW//1HOUR/OBS/", "1HOUR",
                                      HOURS.delete(3).to_numpy(dtype="datetime64[s]"))


def test_an_engine_failure_in_the_check_does_not_block_the_write(monkeypatch, caplog):
    class Broken:
        @staticmethod
        def create(*args, **kwargs):
            raise RuntimeError("disk full")

        write_timeseries = read_timeseries = staticmethod(lambda *a, **k: None)

    monkeypatch.setattr(_backend, "_maybe_native", lambda: Broken())
    stamps = _times("2020-03-01", "2020-04-01").to_numpy(dtype="datetime64[s]")
    with caplog.at_level(logging.WARNING, logger="hms_commander.dss.core"):
        DssCore._check_regular_stamps("//G/FLOW//1MON/OBS/", "1MON", stamps)
    assert any("unchecked" in r.getMessage() for r in caplog.records)


def test_the_check_leaves_no_file_behind(tmp_path, monkeypatch):
    _engine()
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    DssCore._check_regular_stamps("//G/FLOW//1YEAR/OBS/", "1YEAR",
                                  _times("2020-02-29", "2021-03-01").to_numpy(dtype="datetime64[s]"))
    assert list(tmp_path.iterdir()) == []


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
