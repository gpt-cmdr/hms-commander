"""Tests for _constants.py — unit conversions, method lists, parameter maps."""

import pytest

from hms_commander._constants import (
    INCHES_TO_MM,
    MM_TO_INCHES,
    CFS_TO_CMS,
    CMS_TO_CFS,
    FEET_TO_METERS,
    METERS_TO_FEET,
    SQMI_TO_SQKM,
    SQKM_TO_SQMI,
    LOSS_METHODS,
    TRANSFORM_METHODS,
    BASEFLOW_METHODS,
    ROUTING_METHODS,
    PRECIP_METHODS,
    LOSS_PARAM_MAP,
    LOSS_PARAM_REVERSE_MAP,
    TRANSFORM_PARAM_MAP,
    TRANSFORM_PARAM_REVERSE_MAP,
    BASEFLOW_PARAM_MAP,
    BASEFLOW_PARAM_REVERSE_MAP,
    ROUTING_PARAM_MAP,
    ROUTING_PARAM_REVERSE_MAP,
    TIME_INTERVALS,
    IA_RATIO,
    CN_MIN,
    CN_MAX,
)


# ---------------------------------------------------------------------------
# Unit conversion roundtrips
# ---------------------------------------------------------------------------

class TestUnitConversions:
    def test_inches_mm_roundtrip(self):
        original = 10.0
        result = original * INCHES_TO_MM * MM_TO_INCHES
        assert abs(result - original) < 1e-10

    def test_cfs_cms_roundtrip(self):
        original = 1000.0
        result = original * CFS_TO_CMS * CMS_TO_CFS
        assert abs(result - original) < 1e-6

    def test_feet_meters_roundtrip(self):
        original = 100.0
        result = original * FEET_TO_METERS * METERS_TO_FEET
        assert abs(result - original) < 1e-10

    def test_sqmi_sqkm_roundtrip(self):
        original = 50.0
        result = original * SQMI_TO_SQKM * SQKM_TO_SQMI
        assert abs(result - original) < 1e-6


# ---------------------------------------------------------------------------
# Method enumerations
# ---------------------------------------------------------------------------

class TestMethodEnumerations:
    def test_loss_methods_has_known(self):
        assert "Green and Ampt" in LOSS_METHODS
        assert "SCS Curve Number" in LOSS_METHODS
        assert "Deficit and Constant" in LOSS_METHODS
        assert "None" in LOSS_METHODS

    def test_transform_methods_has_known(self):
        assert "Clark Unit Hydrograph" in TRANSFORM_METHODS
        assert "SCS Unit Hydrograph" in TRANSFORM_METHODS
        assert "None" in TRANSFORM_METHODS

    def test_routing_methods_has_known(self):
        assert "Muskingum" in ROUTING_METHODS
        assert "Modified Puls" in ROUTING_METHODS
        assert "Lag" in ROUTING_METHODS

    def test_precip_methods_has_known(self):
        assert "Frequency Storm" in PRECIP_METHODS
        assert "Gage Weights" in PRECIP_METHODS


# ---------------------------------------------------------------------------
# Parameter maps
# ---------------------------------------------------------------------------

class TestParameterMaps:
    def test_loss_map_reverse_is_bijective(self):
        for k, v in LOSS_PARAM_MAP.items():
            assert LOSS_PARAM_REVERSE_MAP[v] == k

    def test_transform_map_reverse_is_bijective(self):
        for k, v in TRANSFORM_PARAM_MAP.items():
            assert TRANSFORM_PARAM_REVERSE_MAP[v] == k

    def test_baseflow_map_reverse_is_bijective(self):
        for k, v in BASEFLOW_PARAM_MAP.items():
            assert BASEFLOW_PARAM_REVERSE_MAP[v] == k

    def test_routing_map_reverse_is_bijective(self):
        for k, v in ROUTING_PARAM_MAP.items():
            assert ROUTING_PARAM_REVERSE_MAP[v] == k


# ---------------------------------------------------------------------------
# Time intervals
# ---------------------------------------------------------------------------

class TestTimeIntervals:
    def test_known_intervals(self):
        assert TIME_INTERVALS["1 Minute"] == 1
        assert TIME_INTERVALS["1 Hour"] == 60
        assert TIME_INTERVALS["1 Day"] == 1440

    def test_has_multiple_entries(self):
        assert len(TIME_INTERVALS) >= 10


# ---------------------------------------------------------------------------
# CN constants
# ---------------------------------------------------------------------------

class TestCnConstants:
    def test_ia_ratio(self):
        assert IA_RATIO == 0.2

    def test_cn_bounds(self):
        assert CN_MIN == 0
        assert CN_MAX == 100
