"""Tests for high-level HMS result path selection behavior."""

import pandas as pd

from hms_commander.HmsResults import HmsResults
from hms_commander.dss import HmsDss


def test_get_peak_flows_passes_run_filter_to_batched_extractor(monkeypatch, tmp_path):
    calls = {}

    def fake_get_peak_flows_batched(
        dss_file,
        element_names=None,
        run_name=None,
        batch_size=50,
        progress=True,
    ):
        calls["dss_file"] = dss_file
        calls["element_names"] = element_names
        calls["run_name"] = run_name
        calls["batch_size"] = batch_size
        calls["progress"] = progress
        return pd.DataFrame(columns=["element", "peak_flow", "peak_time", "units", "dss_path"])

    monkeypatch.setattr(HmsDss, "get_peak_flows_batched", fake_get_peak_flows_batched)

    result = HmsResults.get_peak_flows(
        tmp_path / "results.dss",
        element_names=["J1"],
        run_name="RUN1",
        batch_size=10,
    )

    assert result.empty
    assert calls["element_names"] == ["J1"]
    assert calls["run_name"] == "RUN1"
    assert calls["batch_size"] == 10


def test_get_outflow_timeseries_uses_exact_run_match(monkeypatch, tmp_path):
    catalog = [
        "//J1/FLOW//15MIN/RUN:RUN10/",
        "//J1/FLOW//15MIN/RUN:RUN1/",
    ]
    selected = {}

    def fake_read_timeseries(dss_file, pathname):
        selected["pathname"] = pathname
        return pd.DataFrame({"value": [1.0, 2.0]})

    monkeypatch.setattr(HmsDss, "get_catalog", lambda dss_file: catalog)
    monkeypatch.setattr(HmsDss, "read_timeseries", fake_read_timeseries)

    result = HmsResults.get_outflow_timeseries(
        tmp_path / "results.dss",
        "J1",
        run_name="RUN1",
    )

    assert selected["pathname"] == "//J1/FLOW//15MIN/RUN:RUN1/"
    assert result.columns.tolist() == ["flow"]


def test_extract_hms_results_filters_exact_run_and_excludes_tables(monkeypatch, tmp_path):
    import hms_commander.dss.hms_dss as hms_dss_module

    catalog = [
        "//J1/FLOW//15MIN/RUN:RUN10/",
        "//J1/FLOW//15MIN/RUN:RUN1/",
        "//J2/FLOW/TABLE/15MIN/RUN:RUN1/",
        "//J3/FLOW-DIRECT//15MIN/RUN:RUN1/",
    ]
    read_paths = []

    def fake_read_timeseries(dss_file, pathname):
        read_paths.append(pathname)
        return pd.DataFrame({"value": [1.0]})

    monkeypatch.setattr(hms_dss_module, "DSS_AVAILABLE", True)
    monkeypatch.setattr(HmsDss, "get_catalog", lambda dss_file: catalog)
    monkeypatch.setattr(HmsDss, "read_timeseries", fake_read_timeseries)

    results = HmsDss.extract_hms_results(
        tmp_path / "results.dss",
        result_type="flow",
        run_name="RUN1",
    )

    assert read_paths == [
        "//J1/FLOW//15MIN/RUN:RUN1/",
        "//J3/FLOW-DIRECT//15MIN/RUN:RUN1/",
    ]
    assert sorted(results) == ["J1", "J3"]


def test_extract_hms_results_duplicate_element_keeps_last_catalog_match(monkeypatch, tmp_path):
    import hms_commander.dss.hms_dss as hms_dss_module

    catalog = [
        "//J1/FLOW//15MIN/RUN:RUN1/",
        "//J1/FLOW//15MIN/RUN:RUN2/",
    ]

    def fake_read_timeseries(dss_file, pathname):
        return pd.DataFrame({"source_path": [pathname]})

    monkeypatch.setattr(hms_dss_module, "DSS_AVAILABLE", True)
    monkeypatch.setattr(HmsDss, "get_catalog", lambda dss_file: catalog)
    monkeypatch.setattr(HmsDss, "read_timeseries", fake_read_timeseries)

    results = HmsDss.extract_hms_results(
        tmp_path / "results.dss",
        result_type="flow",
    )

    assert results["J1"]["source_path"].iloc[0] == "//J1/FLOW//15MIN/RUN:RUN2/"
