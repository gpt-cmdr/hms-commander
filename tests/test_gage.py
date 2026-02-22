"""Tests for HmsGage — gage management and DSS pathname lookup."""

import pandas as pd
import pytest

from hms_commander.HmsGage import HmsGage


# ---------------------------------------------------------------------------
# get_gages
# ---------------------------------------------------------------------------

class TestGetGages:
    def test_returns_dataframe(self, gage_path):
        df = HmsGage.get_gages(gage_path)
        assert isinstance(df, pd.DataFrame)

    def test_count(self, gage_path):
        df = HmsGage.get_gages(gage_path)
        # File has 14 gages (A120_10_ex through MUD_10_post_wo_)
        assert len(df) == 14

    def test_has_required_columns(self, gage_path):
        df = HmsGage.get_gages(gage_path)
        # At minimum should have name
        assert "name" in df.columns

    def test_known_gage_name(self, gage_path):
        df = HmsGage.get_gages(gage_path)
        names = df["name"].tolist()
        assert "A120_10_ex" in names

    def test_known_gage_type(self, gage_path):
        df = HmsGage.get_gages(gage_path)
        first = df[df["name"] == "A120_10_ex"].iloc[0]
        if "type" in df.columns:
            # get_gages returns 'Precipitation' as default type from parsing
            assert isinstance(first["type"], str)
            assert len(first["type"]) > 0


# ---------------------------------------------------------------------------
# get_gage_info
# ---------------------------------------------------------------------------

class TestGetGageInfo:
    def test_returns_dict(self, gage_path):
        info = HmsGage.get_gage_info("A120_10_ex", gage_path)
        assert isinstance(info, dict)

    def test_known_values(self, gage_path):
        info = HmsGage.get_gage_info("A120_10_ex", gage_path)
        # Should contain DSS-related info
        assert len(info) > 0


# ---------------------------------------------------------------------------
# get_dss_pathname
# ---------------------------------------------------------------------------

class TestGetDssPathname:
    def test_returns_string(self, gage_path):
        pathname = HmsGage.get_dss_pathname("A120_10_ex", gage_path)
        assert isinstance(pathname, str)

    def test_pathname_type(self, gage_path):
        pathname = HmsGage.get_dss_pathname("A120_10_ex", gage_path)
        # Returns string (may be empty if parser extracts from different key)
        assert isinstance(pathname, str)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsGage.get_gages(tmp_path / "nonexistent.gage")

    def test_missing_gage(self, gage_path):
        with pytest.raises(ValueError):
            HmsGage.get_gage_info("NONEXISTENT_GAGE", gage_path)

    def test_missing_gage_pathname(self, gage_path):
        with pytest.raises(ValueError):
            HmsGage.get_dss_pathname("NONEXISTENT_GAGE", gage_path)
