"""Native (ras-commander-fast-dss) DSS backend: selection, gates, and parity with Java.

Reads compare the Java (HEC Monolith) and native backends on every record of real
HEC-HMS example projects (``HmsExamples``: castro, tenk, river_bend). Writes take real
data (a castro hydrograph, HMS storage-outflow tables, the NOAA Atlas 14 Texas region 3
temporal distributions, HRAP precipitation cells from tenk), write them natively and
with Java, read both files back with Java and compare. Shadow mode must return the Java
result and record no unexpected difference.

Tests skip when the engine (``ras_commander_fast_dss``), Java/pyjnius or an installed
HEC-HMS with ``samples.zip`` is unavailable. The selection and gate tests need neither.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hms_commander.dss import DssCapabilityError, DssCore, HmsDss, HmsDssGrid
from hms_commander.dss import _backend

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PROJECTS = ("castro", "tenk", "river_bend")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _restore_backend(monkeypatch):
    """Every test starts on the default backend with clean shadow counters."""
    monkeypatch.delenv(_backend.ENV_VAR, raising=False)
    monkeypatch.delenv(_backend.SHADOW_COPY_LIMIT_ENV, raising=False)
    saved = HmsDss.backend
    HmsDss.backend = None
    _backend.reset_shadow_stats()
    _backend.reset_fallback_warning()
    yield
    HmsDss.backend = saved


@pytest.fixture(scope="module")
def engine():
    try:
        import ras_commander_fast_dss as dc
    except Exception as exc:  # missing or broken wheel
        pytest.skip(f"ras_commander_fast_dss unavailable: {type(exc).__name__}: {exc}")
    return dc


@pytest.fixture(scope="module")
def java():
    if not DssCore.java_available():
        pytest.skip("pyjnius is not installed")
    try:
        DssCore._configure_jvm()
        from jnius import autoclass

        autoclass("hec.heclib.dss.HecDss")
    except Exception as exc:  # Java, JVM or Monolith unavailable
        pytest.skip(f"HEC Monolith Java bridge unavailable: {type(exc).__name__}: {exc}")
    return True


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    """Real HEC-HMS example projects extracted from the newest installed samples.zip."""
    from hms_commander import HmsExamples

    try:
        versions = HmsExamples.list_versions()
    except Exception as exc:
        pytest.skip(f"HEC-HMS examples unavailable: {exc}")
    if not versions:
        pytest.skip("no HEC-HMS installation with samples.zip")
    root = tmp_path_factory.mktemp("hms_examples")
    return {name: HmsExamples.extract_project(name, output_path=root)
            for name in SAMPLE_PROJECTS}


@pytest.fixture(scope="module")
def sample_files(samples):
    return sorted(p for project in samples.values() for p in project.rglob("*.dss"))


def _use(backend):
    HmsDss.backend = backend


def _java_then_native(call):
    """``call()`` on the Java backend, then on the native backend."""
    _use("java")
    java_result = call()
    _use("native")
    native_result = call()
    _use(None)
    return java_result, native_result


def _assert_no_unexpected():
    bad = [r for r in _backend.SHADOW_RECORDS if r["outcome"] == "unexpected"]
    assert not bad, bad[:5]


def _catalog_frame(engine, dss_file):
    return engine.get_catalog(dss_file)


# ---------------------------------------------------------------------------
# Backend selection and gates (no engine or Java needed)
# ---------------------------------------------------------------------------


def test_default_backend_is_java():
    assert HmsDss.get_backend() == "java"
    assert DssCore.get_backend() == "java"


def test_environment_overrides_attribute(monkeypatch, engine):
    HmsDss.backend = "java"
    monkeypatch.setenv(_backend.ENV_VAR, "Native")
    assert HmsDss.get_backend() == "native"


def test_invalid_backend_raises():
    HmsDss.backend = "rust"
    with pytest.raises(ValueError, match="Invalid DSS backend"):
        HmsDss.get_backend()
    assert HmsDss.is_available() is False


def _without_engine(monkeypatch):
    real = _backend.importlib.import_module

    def fake(name, *args, **kwargs):
        if name == _backend.ENGINE_MODULE:
            raise ImportError("No module named 'ras_commander_fast_dss'")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(_backend.importlib, "import_module", fake)


def test_native_without_engine_raises_import_error(monkeypatch):
    _without_engine(monkeypatch)
    HmsDss.backend = "native"
    with pytest.raises(ImportError, match="ras-commander-fast-dss"):
        HmsDss.get_backend()
    assert HmsDss.is_available() is False


def test_broken_engine_counts_as_missing(monkeypatch):
    real = _backend.importlib.import_module

    def broken(name, *args, **kwargs):
        if name == _backend.ENGINE_MODULE:
            raise OSError("DLL load failed")
        return real(name, *args, **kwargs)

    monkeypatch.setattr(_backend.importlib, "import_module", broken)
    assert _backend.native_available() is False
    HmsDss.backend = "native"
    with pytest.raises(ImportError, match="failed to load"):
        HmsDss.get_backend()


def test_shadow_without_engine_falls_back_to_java_once(monkeypatch, caplog):
    _without_engine(monkeypatch)
    HmsDss.backend = "shadow"
    with caplog.at_level(logging.WARNING, logger="hms_commander.dss"):
        assert HmsDss.get_backend() == "java"
        assert HmsDss.get_backend() == "java"
    assert sum("shadow" in r.getMessage() for r in caplog.records) == 1


def test_java_import_never_loads_engine():
    code = ("import sys, hms_commander; from hms_commander.dss import HmsDss, DssCore; "
            "HmsDss.get_backend(); HmsDss.is_available(); "
            "print('ras_commander_fast_dss' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, env={**__import__("os").environ,
                                          _backend.ENV_VAR: "java"})
    assert out.stdout.strip().splitlines()[-1] == "False"


@pytest.mark.parametrize("features, qualified", [
    (frozenset({"grid_srs_monolith_parity"}), True),
    ({"grid_srs_monolith_parity": True}, True),
    ({"grid_srs_monolith_parity": False}, False),
    (frozenset(), False),
    (None, False),
    ("grid_srs_monolith_parity", False),  # a bare string is not a feature set
])
def test_grid_gate_reads_engine_features(monkeypatch, features, qualified):
    fake = types.SimpleNamespace(FEATURES=features)
    monkeypatch.setattr(_backend, "_maybe_native", lambda: fake)
    assert _backend.native_grid_qualified() is qualified


def test_writer_gate_needs_the_whole_writer_api(monkeypatch):
    full = types.SimpleNamespace(create=print, write_timeseries=print, write_paired_data=print,
                                 write_grid=print, HEC_MISSING_DSS6=-901.0, GRID_NODATA=-1.0)
    monkeypatch.setattr(_backend, "_maybe_native", lambda: full)
    assert _backend.native_writes_available() is True
    partial = types.SimpleNamespace(**{k: v for k, v in vars(full).items()
                                       if k != "write_paired_data"})
    monkeypatch.setattr(_backend, "_maybe_native", lambda: partial)
    assert _backend.native_writes_available() is False
    monkeypatch.setattr(_backend, "import_native", lambda: partial)
    with pytest.raises(DssCapabilityError, match="native DSS writers"):
        _backend.require_native_writes()


def test_unqualified_grid_reads_raise_capability_error(monkeypatch, tmp_path):
    fake = types.SimpleNamespace(FEATURES=frozenset())
    monkeypatch.setattr(_backend, "_maybe_native", lambda: fake)
    monkeypatch.setattr(_backend, "import_native", lambda: fake)
    target = tmp_path / "grid.dss"
    target.write_bytes(b"\0" * 64)
    HmsDss.backend = "native"
    with pytest.raises(DssCapabilityError, match="grid_srs_monolith_parity"):
        HmsDss.read_grid(target, "/A/B/PRECIP/01JAN2020:0000/01JAN2020:0100//")


def test_capabilities_table():
    caps = HmsDss.get_capabilities()
    assert list(caps.columns) == ["operation", "java", "native", "shadow", "note"]
    assert {"read_grid", "write_timeseries", "import_atlas14_temporal"} <= set(caps.operation)
    assert caps.attrs["requested_backend"] == "java"


def test_grid_pathname_matches_monolith_d_and_e_parts():
    # Probed against HEC Monolith 3.3.27: midnight is 0000 in D and the previous
    # day's 2400 in E; A, B, C and F are kept.
    assert (HmsDssGrid._grid_pathname("/AORC/TEST/TEMP/XX/YY/F/", "2020-05-01 23:00")
            == "/AORC/TEST/TEMP/01MAY2020:2300/01MAY2020:2300/F/")
    assert (HmsDssGrid._grid_pathname("/AORC/TEST/TEMP////", "2020-05-02 00:00")
            == "/AORC/TEST/TEMP/02MAY2020:0000/01MAY2020:2400//")
    with pytest.raises(ValueError, match="whole minute"):
        HmsDssGrid._grid_pathname("/A/B/C////", "2020-05-02 00:00:30")


def test_dss6_paired_data_types_over_eight_characters_are_refused():
    records = [{"pathname": "//R/Q/24HR//50%/", "x_values": [0, 1], "y_values": [0, 1]}]
    with pytest.raises(ValueError, match="'CUMULATI'"):
        DssCore._paired_data_specs(records, 6)
    assert DssCore._paired_data_specs(records, 7)[0]["y_type"] == "CUMULATIVE"


@pytest.mark.parametrize("kwargs, match", [
    ({"pathname": "//G/FLOW//IR-MONTH/OBS/"}, "regular-interval"),
    ({"times": ["2020-01-01 01:00:30", "2020-01-01 02:00:30"]}, "whole minutes"),
    ({"values": [1.0, np.inf]}, "infinite"),
    ({"times": ["2020-01-01 02:00", "2020-01-01 01:00"]}, "increasing"),
])
def test_timeseries_write_argument_checks(kwargs, match):
    args = {"pathname": "//G/FLOW//1HOUR/OBS/",
            "times": ["2020-01-01 01:00", "2020-01-01 02:00"], "values": [1.0, 2.0]}
    args.update(kwargs)
    with pytest.raises(ValueError, match=match):
        DssCore._prepare_timeseries(args["pathname"], args["times"], args["values"])


# ---------------------------------------------------------------------------
# Reads: Java against native on the HMS example corpus
# ---------------------------------------------------------------------------


@pytest.mark.requires_java
def test_catalog_and_version_match(engine, java, sample_files):
    for dss_file in sample_files:
        java_cat, native_cat = _java_then_native(lambda: HmsDss.get_catalog(dss_file))
        assert java_cat == native_cat, dss_file
        assert _java_then_native(lambda: HmsDss.get_file_version(dss_file)) == (6, 6)


def _timeseries_paths(engine, dss_file):
    cat = _catalog_frame(engine, dss_file)
    return [p for p, rt in zip(cat.pathname, cat.record_type) if rt < 200]


def _same_frame_with_nan(java_df, native_df):
    diffs = _backend.compare_frames(java_df, native_df)
    assert not diffs, diffs


@pytest.mark.requires_java
@pytest.mark.slow
def test_every_time_series_matches(engine, java, sample_files):
    """Every time-series record of castro, tenk and river_bend: identical except
    HEC missing markers (NaN natively) and patterns Java cannot read."""
    checked = 0
    for dss_file in sample_files:
        for path in _timeseries_paths(engine, dss_file):
            _use("java")
            try:
                java_df = HmsDss.read_timeseries(dss_file, path)
            except ValueError:
                java_df = None
            _use("native")
            native_df = HmsDss.read_timeseries(dss_file, path)
            if java_df is None:
                assert native_df.index[0].year == 3000, path  # D5: pattern record
                continue
            _same_frame_with_nan(java_df, native_df)
            _use("java")
            java_peak = DssCore.get_peak_value(dss_file, path)
            _use("native")
            assert _backend.compare_peak(java_peak, DssCore.get_peak_value(dss_file, path)) == []
            checked += 1
    assert checked > 1000


@pytest.mark.requires_java
@pytest.mark.parametrize("start, end", [
    ("2000-01-01", None),
    (None, "1990-01-01"),
    ("windowed", "windowed"),
])
def test_windows_are_the_same_inclusive_filter(engine, java, samples, start, end):
    dss_file = samples["castro"] / "Current.dss"
    path = _timeseries_paths(engine, dss_file)[0]
    _use("java")
    whole = HmsDss.read_timeseries(dss_file, path)
    if start == "windowed":
        start, end = whole.index[3], whole.index[-4]
    java_df, native_df = _java_then_native(
        lambda: HmsDss.read_timeseries(dss_file, path, start, end))
    _same_frame_with_nan(java_df, native_df)
    if start is not None and end is not None:
        assert java_df.index[0] == start and java_df.index[-1] == end
        assert len(java_df) == len(whole) - 6


@pytest.mark.requires_java
def test_paired_data_and_grids_match(engine, java, sample_files):
    grids = 0
    for dss_file in sample_files:
        cat = _catalog_frame(engine, dss_file)
        for path, rt in zip(cat.pathname, cat.record_type):
            if rt in (200, 205):
                java_pd, native_pd = _java_then_native(
                    lambda: HmsDss.read_paired_data(dss_file, path))
                assert _backend.compare_paired_data(java_pd, native_pd) == [], path
            elif 400 <= rt < 450 and grids < 25:
                java_g, native_g = _java_then_native(lambda: HmsDss.read_grid(dss_file, path))
                diffs, _ = _backend.compare_grids(java_g, native_g)
                assert diffs == [], (path, diffs)
                assert java_g["grid_type"] == "hrap" and java_g["start_time"] is not None
                grids += 1
    assert grids == 25


@pytest.mark.requires_java
@pytest.mark.slow
def test_shadow_reads_return_native_and_log_no_unexpected_difference(engine, java, samples):
    """As ras-commander: shadow reads return the native result (grids: Java's grid),
    run Java for comparison and record every outcome."""
    dss_file = samples["castro"] / "Current.dss"
    paths = _timeseries_paths(engine, dss_file)[:20]  # includes TS-PATTERN records
    _use("native")
    expected = [HmsDss.read_timeseries(dss_file, p) for p in paths]
    _use("shadow")
    got = [HmsDss.read_timeseries(dss_file, p) for p in paths]
    for e, g in zip(expected, got):
        pd.testing.assert_frame_equal(e, g, check_exact=True)
    assert HmsDss.get_catalog(dss_file) == _java_then_native(
        lambda: HmsDss.get_catalog(dss_file))[1]
    _use("shadow")
    assert HmsDss.get_file_version(dss_file) == 6
    HmsDss.get_peak_flows_batched(dss_file, progress=False)
    HmsDss.read_paired_data(samples["tenk"] / "tenk.dss", "//TABLE 1/STORAGE-FLOW///TABLE/")
    hrap = samples["tenk"] / "hrap.dss"
    grid_path = HmsDss.get_catalog(hrap)[0]
    grid = HmsDss.read_grid(hrap, grid_path)
    _use("java")
    java_grid = HmsDss.read_grid(hrap, grid_path)
    assert np.array_equal(grid["data"], java_grid["data"], equal_nan=True)
    assert grid["crs"] == java_grid["crs"]
    _assert_no_unexpected()
    summary = HmsDss.get_shadow_summary()
    for op in ("read_timeseries", "catalog", "file_version", "get_peak_value",
               "read_paired_data", "read_grid"):
        assert any(key.startswith(op + "|") for key in summary), op
    assert summary["read_timeseries|expected|D5 pattern record (Java cannot read)"] >= 1
    returned = {r["operation"]: r["returned"] for r in _backend.SHADOW_RECORDS
                if "returned" in r}
    assert returned["read_grid"] == "java" and returned["read_timeseries"] == "native"


@pytest.mark.requires_java
def test_shadow_raises_native_not_found_after_comparing(engine, java, samples):
    _use("shadow")
    with pytest.raises(engine.DssPathnameNotFoundError, match="No data found"):
        HmsDss.read_timeseries(samples["castro"] / "castro.dss", "//NOWHERE/FLOW//1HOUR//")
    _assert_no_unexpected()
    rec = list(_backend.SHADOW_RECORDS)[-1]
    assert rec["label"] == "D4/D6 no data: typed native error" and rec["java_error"]


@pytest.mark.requires_java
def test_shadow_does_not_run_java_after_other_native_errors(engine, java, tmp_path):
    """Java creates a missing DSS file on open; shadow never runs it after a native
    failure other than not-found."""
    missing = tmp_path / "missing.dss"
    _use("shadow")
    with pytest.raises(Exception):
        DssCore.get_catalog(missing)
    assert not missing.exists()
    rec = list(_backend.SHADOW_RECORDS)[-1]
    assert rec["outcome"] == "skipped" and rec["label"].startswith("java skipped: native ")


@pytest.mark.requires_java
def test_shadow_without_java_returns_native_and_records_skip(engine, java, samples,
                                                              monkeypatch):
    def no_java(*args, **kwargs):
        raise ImportError("pyjnius is required for DSS file operations.")

    monkeypatch.setattr(DssCore, "_read_timeseries_java", staticmethod(no_java))
    dss_file = samples["castro"] / "Current.dss"
    path = _timeseries_paths(engine, dss_file)[1]
    _use("shadow")
    df = HmsDss.read_timeseries(dss_file, path)
    _use("native")
    pd.testing.assert_frame_equal(df, HmsDss.read_timeseries(dss_file, path))
    rec = list(_backend.SHADOW_RECORDS)[0]
    assert (rec["outcome"], rec["label"]) == ("skipped", "java unavailable")


@pytest.mark.requires_java
def test_shadow_does_not_run_java_on_a_record_of_the_wrong_type(engine, java, tmp_path):
    """Java crashes the JVM reading paired data as a time series and the reverse, so
    shadow skips it after the native type error. The HMS contract is then None."""
    target = tmp_path / "mixed.dss"
    engine.create(target, 7)
    _use("native")
    times = pd.date_range("2020-01-01 01:00", periods=4, freq="h")
    HmsDss.write_timeseries(target, "//G/FLOW//1HOUR/R/", times, np.arange(4.0))
    HmsDss.write_paired_data(target, "//G/SF///T/", np.arange(3.0), np.arange(3.0))
    _use("shadow")
    assert DssCore.get_peak_value(target, "//G/SF///T/") is None
    assert DssCore.read_paired_data(target, "//G/FLOW//1HOUR/R/") is None
    for rec in list(_backend.SHADOW_RECORDS)[-2:]:
        assert rec["outcome"] == "skipped" and rec["label"].startswith("java skipped: native ")


def test_timeseries_labels_match_ras_commander():
    index = pd.date_range("2020-01-05", periods=3, freq="7D")
    frame = pd.DataFrame({"value": [1.0, 2.0, 3.0]}, index=index)
    frame.attrs["interval"] = 10080
    assert _backend.classify_timeseries("//A/B//1WEEK/F/", _backend._with_attrs(frame.iloc[1:], frame),
                                        None, frame, None)[1] == \
        "D8 weekly data: Java drops first value"
    index = pd.date_range("2020-01-01 00:00:15", periods=5, freq="15s")
    frame = pd.DataFrame({"value": np.arange(5.0)}, index=index)
    frame.attrs["interval"] = 0.25
    assert _backend.classify_timeseries("//A/B//15S/F/", _backend._with_attrs(frame.iloc[:-1], frame),
                                        None, frame, None)[1] == \
        "J2b Java sub-minute tail cut to whole minute"
    no_data = ValueError("No data found for pathname: //A/\xc9/C//1HOUR/F/")
    assert _backend.classify_timeseries("//A/\xc9/C//1HOUR/F/", None, no_data, frame,
                                        None)[1] == "D7 Latin-1 pathname (Java cannot address)"
    # A native answer for a Java "no data" outside those rules stays visible.
    assert _backend.classify_timeseries("//A/B/C//1HOUR/F/", None, no_data, frame,
                                        None)[0] == "unexpected"


def test_file_version_errors_are_expected_only_when_both_say_invalid():
    invalid = ValueError("File is not a DSS6 or DSS7 file")
    assert _backend.classify_file_version(None, invalid, None, invalid)[0] == "expected"
    assert _backend.classify_file_version(None, RuntimeError("jvm"), None, invalid)[0] == \
        "unexpected"


def test_paired_data_and_catalog_labels_match_ras_commander():
    assert _backend.classify_catalog(["/A/", "/B/"], None, ["/B/", "/A/"])[1] == \
        "D15 catalog order"
    assert _backend.classify_paired_data(None, None, None, None)[1] == \
        "not found on both backends"
    assert _backend.classify_paired_data({"x_values": [1.0]}, None, None, None)[1] == \
        "Java data, native error"


# ---------------------------------------------------------------------------
# Writes: native write, Java read-back, compared with a Java write
# ---------------------------------------------------------------------------


def _java_reads(call):
    _use("java")
    try:
        return call()
    finally:
        _use(None)


@pytest.fixture(scope="module")
def castro_flow(engine, java, samples):
    """A real hydrograph: the first FLOW record of castro's Current.dss."""
    dss_file = samples["castro"] / "Current.dss"
    cat = _catalog_frame(engine, dss_file)
    path = next(p for p in cat.pathname if p.split("/")[3] == "FLOW")
    df = _java_reads(lambda: HmsDss.read_timeseries(dss_file, path))
    parts = path.split("/")
    return df, parts[5], df.attrs["units"], df.attrs["type"]


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_native_timeseries_write_reads_back_like_java_write(engine, java, castro_flow,
                                                            tmp_path, version):
    df, e_part, units, data_type = castro_flow
    values = df["value"].to_numpy().copy()
    values[3] = np.nan  # stored as HEC's missing value on both backends
    path = f"//CASTRO COPY/FLOW//{e_part}/H1 TEST/"
    files = {}
    for backend in ("java", "native"):
        _use(backend)
        files[backend] = tmp_path / f"{backend}{version}.dss"
        HmsDss.write_timeseries(files[backend], path, df.index, values, units, data_type,
                                dss_version=version)
    _use(None)
    assert _java_reads(lambda: HmsDss.get_file_version(files["native"])) == version
    readback = DssCore._readback_pathname(path, version)
    java_df = _java_reads(lambda: HmsDss.read_timeseries(files["java"], readback))
    native_df = _java_reads(lambda: HmsDss.read_timeseries(files["native"], readback))
    pd.testing.assert_frame_equal(java_df, native_df, check_exact=True)
    assert {k: v for k, v in java_df.attrs.items() if k != "dss_file"} == \
           {k: v for k, v in native_df.attrs.items() if k != "dss_file"}
    assert len(native_df) == len(df)
    np.testing.assert_array_equal(native_df["value"].to_numpy()[4:], df["value"].to_numpy()[4:])
    # Stored marker: -901 on DSS6, -FLT_MAX on DSS7 (both writers); HEC Monolith
    # reads either as -FLT_MAX.
    undefined = float(-np.finfo(np.float32).max)
    assert native_df["value"].iloc[3] == undefined
    marker = -901.0 if version == 6 else undefined
    for f in files.values():
        assert engine.read_timeseries(f, readback, raw=True)["value"].iloc[3] == marker


@pytest.mark.requires_java
def test_native_timeseries_write_refuses_version_mismatch(engine, java, castro_flow, tmp_path):
    df, e_part, units, data_type = castro_flow
    target = tmp_path / "v6.dss"
    _use("native")
    HmsDss.write_timeseries(target, f"//A/FLOW//{e_part}/F/", df.index, df["value"], units,
                            data_type, dss_version=6)
    with pytest.raises(ValueError, match="version 6"):
        HmsDss.write_timeseries(target, f"//B/FLOW//{e_part}/F/", df.index, df["value"],
                                units, data_type, dss_version=7)


@pytest.fixture(scope="module")
def storage_tables(engine, java, samples):
    """Real HMS storage-outflow and elevation-storage paired data."""
    tables = []
    for dss_file in (samples["tenk"] / "tenk.dss", samples["river_bend"] / "river_bend.dss"):
        cat = _catalog_frame(engine, dss_file)
        for path in cat.pathname[cat.record_type == 200]:
            data = _java_reads(lambda: HmsDss.read_paired_data(dss_file, path))
            tables.append((path, data))
    assert len(tables) == 6
    return tables


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_native_paired_data_write_reads_back_like_java_write(engine, java, storage_tables,
                                                             tmp_path, version):
    records = [{"pathname": path, "x_values": d["x_values"], "y_values": d["y_values"],
                "x_units": d["x_units"], "y_units": d["y_units"], "x_label": d["x_label"],
                "y_label": d["y_label"]} for path, d in storage_tables]
    files = {}
    for backend in ("java", "native"):
        files[backend] = tmp_path / f"{backend}{version}.dss"
        engine.create(files[backend], version)
        _use(backend)
        assert all(HmsDss.write_multiple_paired_data(files[backend], records).values())
    for path, original in storage_tables:
        java_pd = _java_reads(lambda: HmsDss.read_paired_data(files["java"], path))
        native_pd = _java_reads(lambda: HmsDss.read_paired_data(files["native"], path))
        assert _backend.compare_paired_data(java_pd, native_pd) == []
        assert _backend.compare_paired_data(original, native_pd) == []
    # Float32 (PD) records without curve labels from both writers. Precision: on DSS6
    # Monolith stores KIPREC 0, which Monolith itself reads as unset (-1, -1) and the
    # engine decodes with heclib's C rule as (0, 0); the native writer stores -1
    # (unset for both readers). The HMS read_paired_data dict carries no precision.
    unset = (-1, -1)
    java_precision = (0, 0) if version == 6 else unset
    for path, _ in storage_tables:
        j = engine.read_paired_data(files["java"], path)
        n = engine.read_paired_data(files["native"], path)
        assert (j.record_type, j.labels) == (n.record_type, n.labels) == (200, [])
        assert (j.x_precision, j.y_precision) == java_precision
        assert (n.x_precision, n.y_precision) == unset
        assert np.array_equal(j.ordinates.view(np.int32), n.ordinates.view(np.int32))
        assert np.array_equal(j.values.view(np.int32), n.values.view(np.int32))


@pytest.fixture(scope="module")
def atlas14_tx3_24h():
    from hms_commander import Atlas14Storm

    text = (FIXTURES / "atlas14" / "temporal" / "tx_3_24h_temporal.csv").read_text()
    return Atlas14Storm.parse_temporal_csv(text)


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_atlas14_import_writes_distinct_pathnames_on_both_backends(engine, java,
                                                                   atlas14_tx3_24h, tmp_path,
                                                                   version):
    """P17 Issue B2 regression: one record per quartile and probability."""
    expected = {f"//TX_R3/{q}/24HR//{p}/"
                for q in ("FIRST-QUARTILE", "SECOND-QUARTILE", "THIRD-QUARTILE",
                          "FOURTH-QUARTILE", "ALL-CASES")
                for p in atlas14_tx3_24h["First Quartile"].columns}
    assert len(expected) == 45
    files = {}
    for backend in ("java", "native"):
        files[backend] = tmp_path / f"a14_{backend}{version}.dss"
        engine.create(files[backend], version)
        _use(backend)
        results = HmsDss.import_atlas14_temporal(files[backend], atlas14_tx3_24h, "TX_R3", 24)
        assert set(results) == expected and all(results.values())
        catalog = {p.upper() for p in _java_reads(lambda: HmsDss.get_catalog(files[backend]))}
        assert catalog == {p.upper() for p in expected}
    y_type = "CUMULATI" if version == 6 else "CUMULATIVE"
    for path in sorted(expected):
        java_pd = _java_reads(lambda: HmsDss.read_paired_data(files["java"], path))
        native_pd = _java_reads(lambda: HmsDss.read_paired_data(files["native"], path))
        assert _backend.compare_paired_data(java_pd, native_pd) == []
        assert native_pd["y_label"] == y_type and native_pd["x_units"] == "HOURS"
    fifty = _java_reads(lambda: HmsDss.read_paired_data(files["native"],
                                                        "//TX_R3/FIRST-QUARTILE/24HR//50%/"))
    ninety = _java_reads(lambda: HmsDss.read_paired_data(files["native"],
                                                         "//TX_R3/FIRST-QUARTILE/24HR//90%/"))
    assert not np.array_equal(fifty["y_values"], ninety["y_values"])
    np.testing.assert_allclose(
        fifty["y_values"], atlas14_tx3_24h["First Quartile"]["50%"].to_numpy() / 100.0,
        rtol=1e-6)


@pytest.mark.requires_java
def test_native_paired_data_refuses_long_dss6_type_before_writing(engine, java, tmp_path):
    target = tmp_path / "pd6.dss"
    engine.create(target, 6)
    before = target.read_bytes()
    _use("native")
    with pytest.raises(ValueError, match="DSS6 file stores at most 8"):
        HmsDss.write_paired_data(target, "//R/Q/24HR//50%/", [0.0, 24.0], [0.0, 1.0])
    assert target.read_bytes() == before


def test_write_paired_data_has_the_rasdss_arguments():
    # ras_commander.RasDss.write_paired_data, plus the earlier HMS names at the end.
    import inspect

    canonical = ["dss_file", "pathname", "x_values", "y_values", "x_units", "y_units", "x_type",
                 "y_type", "labels", "create_if_missing", "x_precision", "y_precision",
                 "value_type", "dss_version", "x_label", "y_label"]
    for method in (DssCore.write_paired_data, HmsDss.write_paired_data):
        parameters = inspect.signature(method).parameters
        assert list(parameters) == canonical
        assert parameters["value_type"].default == "auto"
        assert parameters["y_values"].default is None and parameters["x_units"].default is None


@pytest.mark.parametrize("kwargs, error, match", [
    ({"x_values": [1.0], "y_values": None}, ValueError, "y_values is required"),
    ({"x_values": [1.0, 2.0], "y_values": [1.0]}, ValueError, "rows"),
    ({"x_values": [], "y_values": []}, ValueError, "empty"),
    ({"x_values": ["a"], "y_values": [1.0]}, ValueError, "numeric"),
    ({"labels": ["a", "b"]}, ValueError, "labels"),
    ({"labels": "a"}, ValueError, "sequence"),
    ({"labels": [1]}, TypeError, "string"),
    ({"x_units": 3}, TypeError, "string"),
    ({"x_precision": 1}, ValueError, "both"),
    ({"x_precision": -1, "y_precision": 2}, ValueError, "both -1"),
    ({"x_precision": 10, "y_precision": 2}, ValueError, "-1 to 9"),
    ({"value_type": "half"}, ValueError, "value_type"),
    ({"dss_version": 5}, ValueError, "dss_version"),
    ({"x_type": "A", "x_label": "B"}, ValueError, "not both"),
    ({"y_type": "A", "y_label": "B"}, ValueError, "not both"),
])
@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
def test_paired_data_arguments_fail_the_same_on_every_backend(backend, kwargs, error, match,
                                                              tmp_path):
    args = {"x_values": [1.0, 2.0], "y_values": [1.0, 2.0], "x_units": "FT"}
    args.update(kwargs)
    target = tmp_path / "bad.dss"
    _use(backend)
    with pytest.raises(error, match=match):
        HmsDss.write_paired_data(target, "//G/SF///T/", **args)
    assert not target.exists()


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_paired_data_nan_is_stored_as_nan_on_both_backends(engine, java, tmp_path, version):
    """Settles R3's inference: Monolith stores NaN bits; the engine default stored -901 or
    -FLT_MAX. HMS now passes raw=True, for one record and for the batch writer."""
    x, y = np.array([1.0, 2.0, 3.0]), np.array([10.0, np.nan, 30.0])
    path = "//NAN/SF///T/"
    stored = {}
    for backend in ("java", "native"):
        for how in ("single", "batch"):
            target = tmp_path / f"nan_{backend}_{how}{version}.dss"
            engine.create(target, version)
            _use(backend)
            if how == "single":
                HmsDss.write_paired_data(target, path, x, y, "FT", "CFS", "LIN", "LIN",
                                         value_type="float")
            else:
                assert HmsDss.write_multiple_paired_data(target, [{
                    "pathname": path, "x_values": x, "y_values": y, "x_units": "FT",
                    "y_units": "CFS", "x_label": "LIN", "y_label": "LIN"}])[path]
            stored[backend, how] = engine.read_paired_data(str(target), path, dtype="stored").values
            for reader in ("java", "native"):
                _use(reader)
                back = HmsDss.read_paired_data(target, path)["y_values"]
                assert np.isnan(back[1]) and back[0] == 10.0, (backend, how, reader)
    for key, values in stored.items():
        assert np.asarray(values).tobytes() == np.asarray(stored["java", "single"]).tobytes(), key
        assert np.isnan(np.asarray(values).ravel()[1])


def test_native_paired_data_refuses_infinity_before_writing(engine, tmp_path):
    target = tmp_path / "sub" / "inf.dss"
    _use("native")
    with pytest.raises(ValueError, match="infinity"):
        HmsDss.write_paired_data(target, "//I/SF///T/", [1.0, np.inf], [1.0, 2.0], "FT", "CFS")
    with pytest.raises(ValueError, match="infinity"):
        HmsDss.write_multiple_paired_data(target, [{
            "pathname": "//I/SF///T/", "x_values": np.array([1.0]), "y_values": np.array([np.inf])}])
    assert not target.parent.exists()


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_multi_curve_paired_data_matches_java(engine, java, tmp_path, version):
    x = np.array([1.0, 2.0, 3.0])
    y = np.array([[10.0, 100.0], [20.0, 200.0], [30.0, np.nan]])
    kwargs = dict(x_units="FT", y_units="CFS", x_type="LIN", y_type="LIN", labels=["LOW", "HIGH"],
                  x_precision=2, y_precision=1, dss_version=version)
    path = "//M/STAGE-FLOW///RATING/"
    files = {}
    for backend in ("java", "native"):
        files[backend] = tmp_path / f"curves_{backend}{version}.dss"
        _use(backend)
        assert HmsDss.write_paired_data(files[backend], path, x, y, **kwargs) is True
    assert DssCore._compare_written_paired_data(files["java"], files["native"], path) == []
    for dss_file in files.values():
        record = engine.read_paired_data(str(dss_file), path, dtype="stored")
        assert record.record_type == 205 and record.dss_version == version
        assert list(record.labels) == ["LOW", "HIGH"]
        assert record.y_precision == 1
        np.testing.assert_array_equal(np.asarray(record.values), y.T)  # curve-major
        first = _java_reads(lambda: HmsDss.read_paired_data(dss_file, path))
        np.testing.assert_array_equal(first["y_values"], y[:, 0])


@pytest.mark.requires_java
@pytest.mark.parametrize("backend", ["java", "native"])
def test_paired_data_value_type_frame_and_create_flag(engine, java, tmp_path, backend):
    path = "//V/SF///T/"
    _use(backend)
    x64, y64 = np.array([1.0, 2.0]), np.array([3.0, 4.0])
    width = {}
    for name, x, y, value_type in [("auto64", x64, y64, "auto"),
                                   ("auto32", x64.astype("f4"), y64.astype("f4"), "auto"),
                                   ("float", x64, y64, "float"),
                                   ("double", x64.astype("f4"), y64.astype("f4"), "double")]:
        target = tmp_path / f"{name}.dss"
        HmsDss.write_paired_data(target, path, x, y, "FT", "CFS", "LIN", "LIN",
                                 value_type=value_type)
        width[name] = engine.read_paired_data(str(target), path, dtype="stored").record_type
    assert width == {"auto64": 205, "auto32": 200, "float": 200, "double": 205}

    frame = pd.DataFrame({"LOW": y64, "HIGH": y64 * 2}, index=x64)
    frame.attrs.update(x_units="FT", y_units="CFS", x_type="LIN", y_type="LOG")
    target = tmp_path / "frame.dss"
    HmsDss.write_paired_data(target, path, frame)
    record = engine.read_paired_data(str(target), path, dtype="stored")
    assert list(record.labels) == ["LOW", "HIGH"]
    assert (record.units_independent, record.units_dependent) == ("FT", "CFS")
    assert (record.type_independent, record.type_dependent) == ("LIN", "LOG")

    missing = tmp_path / "missing" / "new.dss"
    with pytest.raises(FileNotFoundError):
        HmsDss.write_paired_data(missing, path, x64, y64, "FT", "CFS", "L", "L",
                                 create_if_missing=False)
    assert not missing.parent.exists()
    with pytest.raises(ValueError, match="version"):
        HmsDss.write_paired_data(target, path, x64, y64, "FT", "CFS", "L", "L", dss_version=6)


@pytest.mark.requires_java
@pytest.mark.parametrize("backend", ["java", "native"])
def test_existing_paired_data_callers_keep_working(engine, java, tmp_path, backend):
    path, x, y = "//R/Q/24HR//50%/", np.array([0.0, 24.0]), np.array([0.0, 1.0])
    _use(backend)
    # The earlier defaults, with a warning: same record type and metadata as before.
    target = tmp_path / "defaults.dss"
    with pytest.warns(DeprecationWarning, match="earlier Atlas 14 default"):
        assert HmsDss.write_paired_data(target, path, x, y) is True
    record = engine.read_paired_data(str(target), path, dtype="stored")
    assert record.record_type == 200
    assert (record.units_independent, record.units_dependent) == ("HOURS", "FRACTION")
    assert (record.type_independent, record.type_dependent) == ("TIME", "CUMULATIVE")
    # The earlier keyword names and positions.
    for name, call in (("keywords", dict(x_units="H", y_units="F", x_label="XT", y_label="YT")),
                       ("positions", None)):
        target = tmp_path / f"{name}.dss"
        if call:
            HmsDss.write_paired_data(target, path, x, y, **call)
        else:
            HmsDss.write_paired_data(target, path, x, y, "H", "F", "XT", "YT")
        back = _java_reads(lambda: HmsDss.read_paired_data(target, path))
        assert (back["x_label"], back["y_label"]) == ("XT", "YT")
        _use(backend)
    # Some metadata: each omitted field keeps main's Java default, and the record stays
    # float32 (PD), as main's signature (x_units="HOURS", y_units="FRACTION",
    # x_label="TIME", y_label="CUMULATIVE", float32) stored it. See
    # test_partial_paired_data_metadata_matches_main_java below for every combination.
    target = tmp_path / "partial.dss"
    with pytest.warns(DeprecationWarning, match="earlier Atlas 14 default"):
        HmsDss.write_paired_data(target, path, x, y, x_units="FT", y_units="CFS")
    record = engine.read_paired_data(str(target), path, dtype="stored")
    assert record.record_type == 200
    assert (record.units_independent, record.units_dependent) == ("FT", "CFS")
    assert (record.type_independent, record.type_dependent) == ("TIME", "CUMULATIVE")


#: main's ``DssCore.write_paired_data`` (before #46): keyword defaults per field, and a
#: float32 (PD, record type 200) record from HEC Monolith for every array call.
_MAIN_JAVA_DEFAULTS = {"x_units": "HOURS", "y_units": "FRACTION",
                       "x_label": "TIME", "y_label": "CUMULATIVE"}


@pytest.mark.requires_java
@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
@pytest.mark.parametrize("given", [
    {"x_units": "FT"},
    {"y_units": "CFS"},
    {"x_label": "STAGE"},
    {"y_label": "FLOW"},
    {"x_units": "FT", "y_units": "CFS"},
    {"x_units": "FT", "y_units": "CFS", "x_label": "STAGE"},
    {"x_type": "STAGE", "y_type": "FLOW"},
])
def test_partial_paired_data_metadata_matches_main_java(engine, java, tmp_path, backend, given):
    """Regression (PR #46 review): an array call that gives only some units or types
    stores what main's Java writer stored: each omitted field keeps its default and the
    record is float32. Read back through Java, on every backend."""
    path, x, y = "//TEST/CURVE/TABLE///", np.array([0.0, 1.0]), np.array([0.0, 1.0])
    expected = dict(_MAIN_JAVA_DEFAULTS)
    for key, value in given.items():
        expected[{"x_type": "x_label", "y_type": "y_label"}.get(key, key)] = value
    _use(backend)
    target = tmp_path / "partial.dss"
    with pytest.warns(DeprecationWarning, match="earlier Atlas 14 default"):
        assert HmsDss.write_paired_data(target, path, x, y, **given) is True
    back = _java_reads(lambda: HmsDss.read_paired_data(target, path))
    assert {key: back[key] for key in expected} == expected
    assert engine.read_paired_data(str(target), path, dtype="stored").record_type == 200


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_paired_data_library_failure_raises_on_java(java, tmp_path, monkeypatch, version):
    """A library error used to come back as False; it now raises, as RasDss does."""
    target = tmp_path / f"fail{version}.dss"
    _use("java")
    HmsDss.write_paired_data(target, "//F/SF///T/", [1.0], [1.0], "FT", "CFS", "L", "L",
                             dss_version=version)
    monkeypatch.setattr(DssCore, "_cataloged_pathnames",
                        staticmethod(lambda dss: (_ for _ in ()).throw(OSError("boom"))))
    with pytest.raises(RuntimeError, match="boom"):
        HmsDss.write_paired_data(target, "//F/SF///U/", [1.0], [1.0], "FT", "CFS", "L", "L")


@pytest.mark.requires_java
def test_shadow_multi_curve_paired_data_is_identical(engine, java, tmp_path):
    _use("shadow")
    for version in (6, 7):
        target = tmp_path / f"shadowpd{version}.dss"
        engine.create(target, version)
        HmsDss.write_paired_data(target, "//S/SF///T/", [1.0, 2.0], [[1.0, 2.0], [3.0, 4.0]],
                                 "FT", "CFS", "LIN", "LIN", labels=["A", "B"])
    _assert_no_unexpected()
    assert HmsDss.get_shadow_summary()["write_paired_data|identical|identical"] == 2


@pytest.fixture(scope="module")
def hrap_cells(engine, java, samples):
    """Real HRAP precipitation cells (tenk/hrap.dss), three consecutive hours."""
    dss_file = samples["tenk"] / "hrap.dss"
    paths = _java_reads(lambda: HmsDss.get_catalog(dss_file))[:3]
    cells = [np.nan_to_num(_java_reads(lambda: HmsDss.read_grid(dss_file, p))["data"])
             for p in paths]
    return np.stack(cells).astype(np.float64)


def _lat_lon(shape):
    ny, nx = shape
    return np.linspace(35.0, 35.0 + 0.04 * (ny - 1), ny), np.linspace(-97.0, -97.0 + 0.04 * (nx - 1), nx)


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_native_grid_write_reads_back_like_java_write(engine, java, hrap_cells, tmp_path,
                                                      version):
    lat, lon = _lat_lon(hrap_cells.shape[1:])
    times = list(pd.date_range("2020-05-01 23:00", periods=3, freq="h"))  # crosses midnight
    files = {}
    for backend in ("java", "native"):
        files[backend] = tmp_path / f"grid_{backend}{version}.dss"
        engine.create(files[backend], version)
        _use(backend)
        HmsDssGrid.write_grid_timeseries(files[backend], "/AORC/TENK HRAP COPY/PRECIP////",
                                         hrap_cells, lat, lon, times, units="MM",
                                         data_type="INST-VAL")
    java_cat = _java_reads(lambda: HmsDss.get_catalog(files["java"]))
    assert _java_reads(lambda: HmsDss.get_catalog(files["native"])) == java_cat
    assert java_cat[1] == "/AORC/TENK HRAP COPY/PRECIP/02MAY2020:0000/01MAY2020:2400//"
    for path in java_cat:
        java_g = _java_reads(lambda: HmsDss.read_grid(files["java"], path))
        native_g = _java_reads(lambda: HmsDss.read_grid(files["native"], path))
        diffs, _ = _backend.compare_grids(java_g, native_g)
        assert diffs == [], diffs
        assert HmsDssGrid._compare_written(
            engine.read_grid(files["java"], path, missing="raw"),
            engine.read_grid(files["native"], path, missing="raw")) == []


def _skip_aorc_dependency_check(monkeypatch):
    """convert_to_dss_grid reads a local NetCDF; its dependency check also asks for the
    download-only packages, which it does not use here."""
    import sys

    monkeypatch.setattr(sys.modules["hms_commander.HmsAorc"], "_check_aorc_dependencies",
                        lambda: None)


def test_aorc_stamp_is_the_end_of_its_hour():
    # Maintainer decision on AORC_TIMESTAMP_RESEARCH: D = T - 1h, E = T.
    expected = {
        "2020-05-01 12:00": "/A/B/PRECIP/01MAY2020:1100/01MAY2020:1200//",
        "2020-05-02 00:00": "/A/B/PRECIP/01MAY2020:2300/01MAY2020:2400//",
        "2020-05-02 01:00": "/A/B/PRECIP/02MAY2020:0000/02MAY2020:0100//",
        "2021-01-01 00:00": "/A/B/PRECIP/31DEC2020:2300/31DEC2020:2400//",
    }
    for stamp, path in expected.items():
        (start, end), = HmsDssGrid._grid_time_windows([stamp], 1, "PER-CUM", 60)
        assert HmsDssGrid._grid_pathname("/A/B/PRECIP////", start, end) == path


def test_grid_time_windows_rules():
    stamps = list(pd.date_range("2020-05-01 01:00", periods=3, freq="h"))
    windows = HmsDssGrid._grid_time_windows(stamps, 3, "per-aver")  # uniform spacing
    assert windows[0] == (pd.Timestamp("2020-05-01 00:00"), pd.Timestamp("2020-05-01 01:00"))
    boundaries = HmsDssGrid._grid_time_windows(stamps, 2, "PER-CUM")
    assert boundaries == [(stamps[0], stamps[1]), (stamps[1], stamps[2])]
    assert HmsDssGrid._grid_time_windows(stamps, 3, "INST-VAL")[1] == (stamps[1], stamps[1])
    # A gap must not stretch a period: refused without an interval, exact with one.
    gappy = [stamps[0], stamps[1], pd.Timestamp("2020-05-01 09:00")]
    with pytest.raises(ValueError, match="interval_minutes"):
        HmsDssGrid._grid_time_windows(gappy, 3, "PER-CUM")
    assert HmsDssGrid._grid_time_windows(gappy, 3, "PER-CUM", 60)[2][0] == pd.Timestamp("2020-05-01 08:00")
    with pytest.raises(ValueError, match="interval_minutes"):
        HmsDssGrid._grid_time_windows(stamps[:1], 1, "PER-CUM")
    with pytest.raises(ValueError, match="Unknown grid data type"):
        HmsDssGrid._grid_time_windows(stamps, 3, "PER-MAX")
    with pytest.raises(ValueError, match="must match"):
        HmsDssGrid._grid_time_windows(stamps, 2, "INST-VAL")
    with pytest.raises(ValueError, match="whole minute"):
        HmsDssGrid._grid_time_windows(["2020-05-01 00:00:30"], 1, "PER-CUM", 60)


@pytest.mark.parametrize("backend", ["java", "native", "shadow"])
@pytest.mark.parametrize("kwargs", [
    {"timestamps": ["2020-05-01 01:00", "2020-05-01 01:00", "2020-05-01 02:00"], "n": 2},
    {"timestamps": ["2020-05-01 01:00"], "n": 1, "interval_minutes": 0},
    {"timestamps": ["2020-05-01 01:00"], "n": 1, "interval_minutes": -60},
])
def test_period_grid_with_no_length_is_refused_before_writing(backend, kwargs, tmp_path):
    # start = end stays refused for a caller who still asks for it, on every backend:
    # HEC-HMS reads such a record as missing precipitation.
    kwargs = dict(kwargs)
    n = kwargs.pop("n")
    target = tmp_path / "sub" / "percum.dss"
    _use(backend)
    with pytest.raises(ValueError, match="no length"):
        HmsDssGrid.write_grid_timeseries(target, "/AORC/T/PRECIP////", np.ones((n, 2, 2)),
                                         [35.0, 35.04], [-97.0, -96.96], **kwargs)
    assert not target.parent.exists()


@pytest.mark.requires_java
@pytest.mark.parametrize("version", [6, 7])
def test_period_grid_write_matches_java_and_reads_back_both_ways(engine, java, hrap_cells,
                                                                 tmp_path, version):
    lat, lon = _lat_lon(hrap_cells.shape[1:])
    times = list(pd.date_range("2020-05-01 23:00", periods=3, freq="h"))  # period ends
    expected = ["/AORC/T/PRECIP/01MAY2020:2200/01MAY2020:2300//",
                "/AORC/T/PRECIP/01MAY2020:2300/01MAY2020:2400//",
                "/AORC/T/PRECIP/02MAY2020:0000/02MAY2020:0100//"]
    files = {}
    for backend in ("java", "native"):
        files[backend] = tmp_path / f"period_{backend}{version}.dss"
        engine.create(files[backend], version)
        _use(backend)
        HmsDssGrid.write_grid_timeseries(files[backend], "/AORC/T/PRECIP////", hrap_cells,
                                         lat, lon, times)
    for backend, dss_file in files.items():
        assert sorted(_java_reads(lambda: HmsDss.get_catalog(dss_file))) == sorted(expected)
        assert sorted(engine.get_catalog(str(dss_file))["pathname"]) == sorted(expected)
    for i, path in enumerate(expected):
        java_g = _java_reads(lambda: HmsDss.read_grid(files["java"], path))
        native_g = _java_reads(lambda: HmsDss.read_grid(files["native"], path))
        assert _backend.compare_grids(java_g, native_g)[0] == []
        for dss_file in files.values():
            stored = engine.read_grid(str(dss_file), path, missing="raw")
            assert stored.data_type == 1  # HEC's code for PER-CUM
            np.testing.assert_array_equal(np.asarray(stored.data, dtype=np.float32),
                                          hrap_cells[i].astype(np.float32))
        assert HmsDssGrid._compare_written(
            engine.read_grid(str(files["java"]), path, missing="raw"),
            engine.read_grid(str(files["native"]), path, missing="raw")) == []


@pytest.mark.requires_java
@pytest.mark.parametrize("backend", ["java", "native"])
def test_convert_to_dss_grid_uses_end_of_hour_periods(engine, java, tmp_path, monkeypatch, backend):
    xr = pytest.importorskip("xarray")
    pytest.importorskip("netCDF4")
    from hms_commander import HmsAorc

    _skip_aorc_dependency_check(monkeypatch)
    # Whole-burst AORC layout: the stamp 2020-05-02 00:00 crosses midnight.
    times = pd.date_range("2020-05-01 23:00", periods=3, freq="h")
    data = np.arange(3 * 4 * 5, dtype=np.float32).reshape(3, 4, 5)
    nc = tmp_path / "aorc.nc"
    xr.DataArray(data, dims=("time", "latitude", "longitude"), name="APCP_surface",
                 coords={"time": times, "latitude": 35.0 + 0.01 * np.arange(4),
                         "longitude": -97.0 + 0.01 * np.arange(5)}).to_netcdf(nc)
    target = tmp_path / f"aorc_{backend}.dss"
    _use(backend)
    HmsAorc.convert_to_dss_grid(nc, target, "/AORC/TEST/PRECIP////")
    path = "/AORC/TEST/PRECIP/01MAY2020:2300/01MAY2020:2400//"
    assert path in list(engine.get_catalog(str(target))["pathname"])
    np.testing.assert_array_equal(engine.read_grid(str(target), path, missing="raw").data, data[1])
    assert path in _java_reads(lambda: HmsDss.get_catalog(target))
    np.testing.assert_allclose(_java_reads(lambda: HmsDss.read_grid(target, path))["data"], data[1])


@pytest.mark.requires_java
def test_shadow_writes_return_java_and_compare_natively(engine, java, castro_flow,
                                                        storage_tables, atlas14_tx3_24h,
                                                        hrap_cells, tmp_path):
    df, e_part, units, data_type = castro_flow
    lat, lon = _lat_lon(hrap_cells.shape[1:])
    times = list(pd.date_range("2020-05-01 23:00", periods=3, freq="h"))
    _use("shadow")
    for version in (6, 7):
        target = tmp_path / f"shadow{version}.dss"
        engine.create(target, version)
        HmsDss.write_timeseries(target, f"//CASTRO/FLOW//{e_part}/SHADOW/", df.index,
                                df["value"], units, data_type)
        path, data = storage_tables[0]
        HmsDss.write_paired_data(target, path, data["x_values"], data["y_values"],
                                 data["x_units"], data["y_units"], data["x_label"],
                                 data["y_label"])
        HmsDss.import_atlas14_temporal(target, atlas14_tx3_24h, "TX_R3", 24)
        HmsDssGrid.write_grid_timeseries(target, "/AORC/T/TEMP////", hrap_cells, lat, lon,
                                         times, units="DEG C", data_type="INST-VAL")
        HmsDssGrid.write_grid_timeseries(target, "/AORC/T/PRECIP////", hrap_cells, lat, lon,
                                         times)
    # A new file through shadow: Java creates it, the native copy is a new DSS7 file.
    HmsDss.write_timeseries(tmp_path / "new" / "created.dss", f"//C/FLOW//{e_part}/N/",
                            df.index, df["value"], units, data_type)
    _assert_no_unexpected()
    summary = HmsDss.get_shadow_summary()
    assert summary["write_timeseries|identical|identical"] == 3
    assert summary["write_paired_data|identical|identical"] == 2
    assert summary["write_multiple_paired_data|identical|identical"] == 2  # Atlas 14
    assert summary["write_grid_timeseries|identical|identical"] == 4
    # The caller's files hold the Java writes.
    assert _java_reads(lambda: HmsDss.get_file_version(tmp_path / "new" / "created.dss")) == 7


@pytest.mark.requires_java
def test_shadow_write_skips_files_above_the_copy_limit(engine, java, castro_flow, tmp_path,
                                                       monkeypatch):
    df, e_part, units, data_type = castro_flow
    target = tmp_path / "big.dss"
    engine.create(target, 7)
    monkeypatch.setenv(_backend.SHADOW_COPY_LIMIT_ENV, "0")
    _use("shadow")
    HmsDss.write_timeseries(target, f"//C/FLOW//{e_part}/F/", df.index, df["value"], units,
                            data_type)
    rec = list(_backend.SHADOW_RECORDS)[-1]
    assert rec["outcome"] == "skipped" and "copy limit" in rec["label"]


@pytest.mark.requires_java
def test_shadow_write_skips_when_the_engine_has_no_writers(engine, java, castro_flow,
                                                           tmp_path, monkeypatch):
    df, e_part, units, data_type = castro_flow
    target = tmp_path / "nowriters.dss"
    engine.create(target, 7)
    monkeypatch.setattr(_backend, "native_writes_available", lambda: False)
    _use("shadow")
    HmsDss.write_timeseries(target, f"//C/FLOW//{e_part}/F/", df.index, df["value"], units,
                            data_type)
    rec = list(_backend.SHADOW_RECORDS)[-1]
    assert (rec["outcome"], rec["label"]) == ("skipped", _backend.NATIVE_WRITERS_MISSING_LABEL)
    # The caller's file holds the Java write.
    assert len(_java_reads(lambda: HmsDss.read_timeseries(
        target, f"//C/FLOW//{e_part}/F/"))) == len(df)
