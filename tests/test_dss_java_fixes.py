"""Regression tests for the Java (HEC Monolith) DSS read and paired-data write paths.

- Times honour ``TimeSeriesContainer.julianBaseDate`` and the time granularity,
  so second-granularity records get their stored dates and interval.
- ``get_peak_value`` statistics exclude HEC missing values.
- ``read_timeseries`` applies its ``start_date``/``end_date`` window.
- Paired-data writes select the ``HecDss.put(DataContainer)`` overload, verify
  the record exists, and reject pathnames that heclib would silently truncate.
- Atlas 14 temporal curves get one six-part pathname per probability.
- Volume and precipitation summaries use the right quantity and arithmetic.

All data is synthetic and created inside the test. Tests that need Java skip
when pyjnius, Java or the HEC Monolith libraries are unavailable.
"""

from __future__ import annotations

import types
from datetime import date

import numpy as np
import pandas as pd
import pytest

from hms_commander import HmsResults
from hms_commander.dss import DssCore, HmsDss

UNDEFINED = -3.4028234663852886e38  # HEC Monolith undefined value (-Float.MAX)


# ---------------------------------------------------------------------------
# Pure helpers (no Java)
# ---------------------------------------------------------------------------


def _tsc(interval, granularity=None):
    fake = types.SimpleNamespace(interval=interval)
    if granularity is not None:
        fake.getTimeGranularitySeconds = lambda: granularity
    return fake


def test_interval_minutes_honours_granularity():
    assert DssCore._tsc_interval_minutes(_tsc(60, 60), 60) == 60
    assert DssCore._tsc_interval_minutes(_tsc(15, 1), 1) == 0.25
    assert DssCore._tsc_interval_minutes(_tsc(3600, 1), 1) == 60
    assert DssCore._tsc_interval_minutes(_tsc(0, 1), 1) == 0


def test_granularity_defaults_to_minutes():
    assert DssCore._tsc_granularity_seconds(types.SimpleNamespace()) == 60
    assert DssCore._tsc_granularity_seconds(_tsc(1, 0)) == 60
    assert DssCore._tsc_granularity_seconds(_tsc(1, 1)) == 1


def test_second_granularity_times_use_base_date():
    # 09:00:00 as seconds after the base date 2024-11-11 (45606 days after the epoch).
    base = (date(2024, 11, 11) - date(1899, 12, 31)).days
    stamps = DssCore._hec_times_to_datetimes([32400, 32415], 1, base)
    assert list(stamps) == [pd.Timestamp("2024-11-11 09:00:00"),
                            pd.Timestamp("2024-11-11 09:00:15")]
    assert DssCore._hec_time_to_datetime(32400, 1, base) == pd.Timestamp("2024-11-11 09:00:00")


def test_minute_times_from_epoch_are_unchanged():
    minutes = int((pd.Timestamp("2020-01-01 01:00") - pd.Timestamp("1899-12-31")).total_seconds() // 60)
    assert DssCore._hec_times_to_datetimes([minutes])[0] == pd.Timestamp("2020-01-01 01:00")
    assert DssCore._hec_time_to_datetime(minutes) == pd.Timestamp("2020-01-01 01:00")


def test_valid_value_mask_excludes_hec_missing_markers():
    values = np.array([1.0, -901.0, -902.0, UNDEFINED, np.nan, -5.0])
    assert DssCore._valid_value_mask(values).tolist() == [True, False, False, False, False, True]


@pytest.mark.parametrize("pathname", [
    "//TX_R3/FIRST-QUARTILE/24HR///50%/",  # eight slashes: heclib drops "50%"
    "/A/B/C/D/E/",
    "A/B/C/D/E/F/",
    "/A/B/C/D/E/F",
])
def test_pathname_format_rejects_wrong_part_count(pathname):
    with pytest.raises(ValueError, match="six parts"):
        DssCore._check_pathname_format(pathname)


def test_pathname_format_accepts_six_parts():
    DssCore._check_pathname_format("//TX_R3/FIRST-QUARTILE/24HR//50%/")


def test_missing_pathnames_is_case_insensitive():
    catalog = ["//R/Q/24HR//50%/"]
    assert DssCore._missing_pathnames(catalog, ["//r/q/24hr//50%/", "//R/Q/24HR//90%/"]) == [
        "//R/Q/24HR//90%/"
    ]


def test_atlas14_import_builds_one_six_part_pathname_per_probability(monkeypatch, tmp_path):
    captured = {}

    def fake_write(dss_file, records):
        captured["records"] = records
        return {record["pathname"]: True for record in records}

    monkeypatch.setattr(DssCore, "write_multiple_paired_data", staticmethod(fake_write))
    hours = np.linspace(0.0, 24.0, 5)
    temporal = {
        "First Quartile": pd.DataFrame({"50%": [0, 25, 50, 75, 100],
                                        "90%": [0, 40, 70, 90, 100]}, index=hours),
    }
    HmsDss.import_atlas14_temporal(tmp_path / "a14.dss", temporal, region_code="SYN_R1")

    paths = [record["pathname"] for record in captured["records"]]
    assert paths == ["//SYN_R1/FIRST-QUARTILE/24HR//50%/", "//SYN_R1/FIRST-QUARTILE/24HR//90%/"]
    for path in paths:
        DssCore._check_pathname_format(path)


def test_paired_data_writers_reject_bad_pathnames_before_writing(tmp_path):
    target = tmp_path / "pd.dss"
    with pytest.raises(ValueError, match="six parts"):
        DssCore.write_paired_data(target, "//R/Q/24HR///50%/", np.array([0.0, 1.0]),
                                  np.array([0.0, 1.0]))
    records = [
        {"pathname": "//R/Q/24HR//50%/", "x_values": np.array([0.0]), "y_values": np.array([0.0])},
        {"pathname": "//r/q/24hr//50%/", "x_values": np.array([0.0]), "y_values": np.array([0.0])},
    ]
    with pytest.raises(ValueError, match="Duplicate"):
        DssCore.write_multiple_paired_data(target, records)
    assert not target.exists()


def test_volume_is_trapezoid_in_acre_feet():
    # 100 CFS for 24 hours = 2400 CFS-hours = 198.347 acre-feet,
    # at both 30-minute and 2-hour spacing.
    for step in ("30min", "2h"):
        index = pd.date_range("2020-01-01", "2020-01-02", freq=step)
        volume = HmsResults._volume_acre_feet(index, np.full(len(index), 100.0))
        assert volume == pytest.approx(2400 * 3600 / 43560)


def _flow_frame():
    index = pd.date_range("2020-01-01", periods=49, freq="30min")
    df = pd.DataFrame({"datetime": index, "value": np.full(49, 100.0)}, index=index)
    df.attrs["units"] = "CFS"
    return df


def test_volume_summary_and_hydrograph_statistics_use_acre_feet(monkeypatch, tmp_path):
    path = "//OUTLET/FLOW/01JAN2020/30MIN/RUN:R1/"
    monkeypatch.setattr(HmsDss, "list_flow_results", lambda _: [path])
    monkeypatch.setattr(HmsDss, "get_catalog", lambda _: [path])
    monkeypatch.setattr(HmsDss, "read_timeseries", lambda _f, _p: _flow_frame())

    expected = round(2400 * 3600 / 43560, 2)  # 198.35
    summary = HmsResults.get_volume_summary(tmp_path / "results.dss")
    assert summary["total_volume_af"].tolist() == [expected]
    stats = HmsResults.get_hydrograph_statistics(tmp_path / "results.dss", "OUTLET")
    assert stats["total_volume_af"] == expected


# Pathnames in the form HEC-HMS writes for one subbasin: interval depth
# (PER-CUM), cumulative depth (INST-CUM), losses, excess and spatial spread.
_PRECIP_CATALOG = [
    "//SUB1/PRECIP-EXCESS/01JAN2020/1HOUR/RUN:R1/",
    "//SUB1/PRECIP-LOSS/01JAN2020/1HOUR/RUN:R1/",
    "//SUB1/PRECIP-INC/01JAN2020/1HOUR/RUN:R1/",
    "//SUB1/PRECIP-STAND DEV/01JAN2020/1HOUR/RUN:R1/",
    "//SUB1/PRECIP-CUM/01JAN2020/1HOUR/RUN:R1/",
]


def _precip_reader(_file, path):
    index = pd.date_range("2020-01-01 01:00", periods=4, freq="1h")
    incremental = np.array([0.1, 0.5, 0.3, 0.1])
    values = np.cumsum(incremental) if "/PRECIP-CUM/" in path else incremental
    df = pd.DataFrame({"datetime": index, "value": values}, index=index)
    df.attrs["units"] = "IN"
    return df


def test_select_interval_precip_paths_prefers_incremental_depth():
    from hms_commander.dss.catalog import select_interval_precip_paths

    assert select_interval_precip_paths(_PRECIP_CATALOG) == [
        "//SUB1/PRECIP-INC/01JAN2020/1HOUR/RUN:R1/"
    ]
    legacy = ["//SUB1/PRECIP-CUM/01JAN2020/1HOUR/RUN:R1/", "//SUB1/PRECIP/01JAN2020/1HOUR/RUN:R1/"]
    assert select_interval_precip_paths(legacy) == [legacy[1]]


@pytest.mark.parametrize("catalog", [_PRECIP_CATALOG, list(reversed(_PRECIP_CATALOG))])
def test_precipitation_totals_use_interval_depth(monkeypatch, tmp_path, catalog):
    monkeypatch.setattr(HmsDss, "get_catalog", lambda _: catalog)
    monkeypatch.setattr(HmsDss, "read_timeseries", _precip_reader)

    summary = HmsResults.get_precipitation_summary(tmp_path / "results.dss")
    assert summary["element"].tolist() == ["SUB1"]
    assert summary["total_depth"].tolist() == [1.0]
    assert summary["max_intensity"].tolist() == [0.5]

    totals = HmsDss.get_total_precipitation(tmp_path / "results.dss")
    assert totals["element"].tolist() == ["SUB1"]
    assert totals["total_precip"].tolist() == [pytest.approx(1.0)]


def test_get_peak_flows_uses_total_flow_only(monkeypatch, tmp_path):
    catalog = [
        "//SUB1/FLOW/01JAN2020/1HOUR/RUN:R1/",
        "//SUB1/FLOW-CUMULATIVE/01JAN2020/1HOUR/RUN:R1/",
    ]

    def reader(_file, path):
        index = pd.date_range("2020-01-01", periods=3, freq="1h")
        values = [5000.0, 6000.0, 7000.0] if "CUMULATIVE" in path else [10.0, 30.0, 20.0]
        df = pd.DataFrame({"datetime": index, "value": values}, index=index)
        df.attrs["units"] = "AC-FT" if "CUMULATIVE" in path else "CFS"
        return df

    monkeypatch.setattr(HmsDss, "get_catalog", lambda _: catalog)
    monkeypatch.setattr(HmsDss, "read_timeseries", reader)
    peaks = HmsDss.get_peak_flows(tmp_path / "results.dss")
    assert peaks["peak_flow"].tolist() == [30.0]
    assert peaks["units"].tolist() == ["CFS"]


# ---------------------------------------------------------------------------
# HEC Monolith round trips (Java required)
# ---------------------------------------------------------------------------

SECONDS_PATH = "/SYNTH/GAGE/FLOW/11NOV2024/15Second/PUBLIC/"
HOURLY_PATH = "/SYNTH/GAGE/FLOW/01JAN2020/1Hour/PUBLIC/"


@pytest.fixture(scope="module")
def java():
    if not DssCore.is_available():
        pytest.skip("pyjnius is not installed")
    try:
        DssCore._configure_jvm()
        from jnius import autoclass, cast

        autoclass("hec.heclib.dss.HecDss")
    except Exception as exc:  # Java, JVM or Monolith unavailable
        pytest.skip(f"HEC Monolith Java bridge unavailable: {type(exc).__name__}: {exc}")
    return autoclass, cast


def _write_series(java, dss_file, pathname, counts, granularity, julian_base, interval, values):
    autoclass, cast = java
    container = autoclass("hec.io.TimeSeriesContainer")()
    times = autoclass("hec.heclib.util.HecTimeArray")()
    assert times.set([int(c) for c in counts], int(granularity), int(julian_base)) == 0
    container.fullName = pathname
    container.units = "CFS"
    container.type = "INST-VAL"
    container.interval = int(interval)
    container.setTimeGranularitySeconds(int(granularity))
    assert container.setTimes(times) == 0
    assert container.setValues([float(v) for v in values]) == 0
    container.numberValues = len(values)
    dss = autoclass("hec.heclib.dss.HecDss").open(str(dss_file))
    try:
        dss.put(cast("hec.io.DataContainer", container))
    finally:
        dss.done()


@pytest.fixture(scope="module")
def series_file(java, tmp_path_factory):
    """A 15-second series (second granularity, nonzero base date) and an hourly series."""
    dss_file = tmp_path_factory.mktemp("dss") / "synthetic.dss"

    # 241 values at 15 s from 2024-11-11 09:00:00; triangular hydrograph
    # peaking at 100.0 at 09:30:00; two values replaced by missing markers.
    base = (date(2024, 11, 11) - date(1899, 12, 31)).days
    values = np.concatenate([np.linspace(0.0, 100.0, 121), np.linspace(100.0, 0.0, 121)[1:]])
    values[5] = UNDEFINED
    values[6] = -901.0
    _write_series(java, dss_file, SECONDS_PATH, [32400 + 15 * i for i in range(241)],
                  1, base, 15, values)

    # Five hourly values from 2020-01-01 01:00, written in minutes from the epoch.
    start = int((pd.Timestamp("2020-01-01 01:00") - pd.Timestamp("1899-12-31")).total_seconds() // 60)
    _write_series(java, dss_file, HOURLY_PATH, [start + 60 * i for i in range(5)],
                  60, 0, 60, [1.0, 2.0, 3.0, 2.0, 1.0])
    return dss_file


@pytest.mark.requires_java
def test_second_granularity_series_gets_stored_dates(series_file):
    df = HmsDss.read_timeseries(series_file, SECONDS_PATH)
    assert len(df) == 241
    assert df.index[0] == pd.Timestamp("2024-11-11 09:00:00")
    assert df.index[-1] == pd.Timestamp("2024-11-11 10:00:00")
    assert set(df.index.to_series().diff().dropna().dt.total_seconds()) == {15.0}
    assert df.attrs["interval"] == 0.25


@pytest.mark.requires_java
def test_minute_series_is_unchanged(series_file):
    df = HmsDss.read_timeseries(series_file, HOURLY_PATH)
    assert list(df.index) == list(pd.date_range("2020-01-01 01:00", periods=5, freq="1h"))
    assert df.attrs["interval"] == 60
    assert df["value"].tolist() == [1.0, 2.0, 3.0, 2.0, 1.0]


@pytest.mark.requires_java
def test_peak_value_time_and_statistics_exclude_missing(series_file):
    peak = DssCore.get_peak_value(series_file, SECONDS_PATH)
    assert peak["peak_flow"] == 100.0
    assert peak["peak_time"] == pd.Timestamp("2024-11-11 09:30:00")
    assert peak["count"] == 241
    assert peak["min_value"] == 0.0
    valid = np.concatenate([np.linspace(0.0, 100.0, 121), np.linspace(100.0, 0.0, 121)[1:]])
    valid = np.delete(valid, [5, 6])
    assert peak["mean_value"] == pytest.approx(valid.mean())


@pytest.mark.requires_java
def test_read_timeseries_applies_inclusive_window(series_file):
    df = DssCore.read_timeseries(series_file, SECONDS_PATH,
                                 start_date="2024-11-11 09:10:00",
                                 end_date=pd.Timestamp("2024-11-11 09:20:00"))
    assert df.index[0] == pd.Timestamp("2024-11-11 09:10:00")
    assert df.index[-1] == pd.Timestamp("2024-11-11 09:20:00")
    assert len(df) == 41
    hourly = HmsDss.read_timeseries(series_file, HOURLY_PATH, start_date="2020-01-01 03:00")
    assert hourly["value"].tolist() == [3.0, 2.0, 1.0]
    with pytest.raises(ValueError, match="after end_date"):
        DssCore.read_timeseries(series_file, HOURLY_PATH, start_date="2020-01-02",
                                end_date="2020-01-01")


@pytest.mark.requires_java
def test_write_paired_data_round_trips(java, tmp_path):
    dss_file = tmp_path / "pd.dss"
    path = "//SYN_R1/CURVE/24HR//A/"
    x = np.linspace(0.0, 24.0, 49)
    y = np.linspace(0.0, 1.0, 49)
    assert HmsDss.write_paired_data(dss_file, path, x, y) is True
    assert path in HmsDss.get_catalog(dss_file)
    back = HmsDss.read_paired_data(dss_file, path)
    np.testing.assert_allclose(back["x_values"], x)
    np.testing.assert_allclose(back["y_values"], y)
    assert back["x_units"] == "HOURS"
    assert back["y_units"] == "FRACTION"


@pytest.mark.requires_java
def test_atlas14_probabilities_land_on_distinct_records(java, tmp_path):
    dss_file = tmp_path / "a14.dss"
    hours = np.linspace(0.0, 24.0, 49)
    median = np.linspace(0.0, 100.0, 49)
    upper = 100.0 * (hours / 24.0) ** 0.5
    temporal = {"First Quartile": pd.DataFrame({"50%": median, "90%": upper}, index=hours)}

    result = HmsDss.import_atlas14_temporal(dss_file, temporal, region_code="SYN_R1")

    expected = ["//SYN_R1/FIRST-QUARTILE/24HR//50%/", "//SYN_R1/FIRST-QUARTILE/24HR//90%/"]
    assert result == {path: True for path in expected}
    assert sorted(HmsDss.get_catalog(dss_file)) == expected
    np.testing.assert_allclose(HmsDss.read_paired_data(dss_file, expected[0])["y_values"],
                               median / 100.0)
    np.testing.assert_allclose(HmsDss.read_paired_data(dss_file, expected[1])["y_values"],
                               upper / 100.0)
