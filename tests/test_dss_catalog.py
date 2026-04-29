"""Pure DSS catalog/query tests."""

from hms_commander.dss.catalog import (
    create_pathname,
    filter_catalog,
    parse_pathname,
    select_result_paths,
    unique_elements,
)
from hms_commander.dss import DssCore, HmsDss


CATALOG = [
    "//J1/FLOW//15MIN/RUN:RUN1/",
    "//J1/FLOW//15MIN/RUN:RUN2/",
    "//J2/FLOW-DIRECT//15MIN/RUN:RUN1/",
    "//J3/FLOW//15MIN/RUN:RUN10/",
    "//J4/TABLE//IR-CENTURY/RUN:RUN1/",
    "//SUB1/PRECIP-INC//15MIN/RUN:RUN1/",
    "/BASIN/STAGE_NODE/STAGE//15MIN/RUN:RUN1/",
]


def test_parse_pathname_preserves_empty_a_part_and_d_part():
    parts = parse_pathname("//J1/FLOW//15MIN/RUN:RUN1/")

    assert parts["A"] == ""
    assert parts["B"] == "J1"
    assert parts["C"] == "FLOW"
    assert parts["D"] == ""
    assert parts["E"] == "15MIN"
    assert parts["F"] == "RUN:RUN1"
    assert parts["run_name"] == "RUN1"


def test_create_pathname_roundtrip():
    path = create_pathname("BASIN", "OUTLET", "FLOW", "1HOUR", "RUN1")
    parts = parse_pathname(path)

    assert path == "/BASIN/OUTLET/FLOW//1HOUR/RUN:RUN1/"
    assert parts["element_name"] == "OUTLET"
    assert parts["run_name"] == "RUN1"


def test_filter_catalog_matches_components_case_insensitively():
    filtered = filter_catalog(CATALOG, data_type="flow", element="j1")

    assert filtered == [
        "//J1/FLOW//15MIN/RUN:RUN1/",
        "//J1/FLOW//15MIN/RUN:RUN2/",
    ]


def test_select_flow_total_excludes_derived_flow_table_and_other_runs():
    selected = select_result_paths(CATALOG, result_type="flow-total", run_name="RUN1")

    assert selected == ["//J1/FLOW//15MIN/RUN:RUN1/"]


def test_run_filter_is_exact_not_substring():
    selected = select_result_paths(CATALOG, result_type="flow-total", run_name="RUN1")

    assert "//J3/FLOW//15MIN/RUN:RUN10/" not in selected


def test_unique_elements_preserves_catalog_order():
    assert unique_elements(CATALOG[:3]) == ["J1", "J2"]


def test_dss_wrappers_use_same_pure_parse_and_create_behavior():
    path = HmsDss.create_dss_pathname("BASIN", "J1", "FLOW", "15MIN", "RUN1")

    assert DssCore.parse_pathname(path) == HmsDss.parse_dss_pathname(path)
    assert HmsDss.filter_catalog(CATALOG, data_type="PRECIP") == [
        "//SUB1/PRECIP-INC//15MIN/RUN:RUN1/"
    ]
