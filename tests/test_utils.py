"""Tests for HmsUtils — date parsing, unit conversion, project utilities."""

from datetime import datetime
from pathlib import Path

import pytest

from hms_commander.HmsUtils import HmsUtils


# ---------------------------------------------------------------------------
# parse_hms_date
# ---------------------------------------------------------------------------

class TestParseHmsDate:
    def test_full_month_name(self):
        dt = HmsUtils.parse_hms_date("1 June 2007", "00:00")
        assert dt == datetime(2007, 6, 1, 0, 0)

    def test_abbreviated_month(self):
        dt = HmsUtils.parse_hms_date("25 Aug 2014", "12:22")
        assert dt.year == 2014
        assert dt.month == 8
        assert dt.day == 25

    def test_compact_format(self):
        dt = HmsUtils.parse_hms_date("16Jan1973", "14:30")
        assert dt == datetime(1973, 1, 16, 14, 30)

    def test_with_time(self):
        dt = HmsUtils.parse_hms_date("4 June 2007", "02:45")
        assert dt.hour == 2
        assert dt.minute == 45

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            HmsUtils.parse_hms_date("not a date", "00:00")


# ---------------------------------------------------------------------------
# format_hms_date
# ---------------------------------------------------------------------------

class TestFormatHmsDate:
    def test_output_format(self):
        dt = datetime(2020, 3, 15, 12, 30)
        date_str, time_str = HmsUtils.format_hms_date(dt)
        assert "2020" in date_str
        assert time_str == "12:30"

    def test_roundtrip(self):
        original = datetime(2014, 8, 25, 12, 22)
        date_str, time_str = HmsUtils.format_hms_date(original)
        roundtrip = HmsUtils.parse_hms_date(date_str, time_str)
        assert roundtrip == original


# ---------------------------------------------------------------------------
# convert_units
# ---------------------------------------------------------------------------

class TestConvertUnits:
    def test_inches_to_mm(self):
        result = HmsUtils.convert_units(1.0, "in", "mm")
        assert abs(result - 25.4) < 0.01

    def test_cfs_to_cms(self):
        result = HmsUtils.convert_units(1000.0, "cfs", "cms")
        assert abs(result - 28.317) < 0.1

    def test_identity_conversion(self):
        result = HmsUtils.convert_units(42.0, "in", "in")
        assert result == 42.0

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            HmsUtils.convert_units(1.0, "unknown_unit", "mm")


# ---------------------------------------------------------------------------
# parse_time_interval
# ---------------------------------------------------------------------------

class TestParseTimeInterval:
    def test_five_minutes(self):
        assert HmsUtils.parse_time_interval("5 Minutes") == 5

    def test_fifteen_minutes(self):
        assert HmsUtils.parse_time_interval("15 Minutes") == 15

    def test_one_hour(self):
        assert HmsUtils.parse_time_interval("1 Hour") == 60

    def test_one_day(self):
        assert HmsUtils.parse_time_interval("1 Day") == 1440


# ---------------------------------------------------------------------------
# CN / IA calculations
# ---------------------------------------------------------------------------

class TestCnIaCalculations:
    def test_cn_75_to_ia(self):
        ia = HmsUtils.calculate_ia_from_cn(75.0)
        assert ia > 0
        # S = 1000/CN - 10 = 3.333, Ia = 0.2 * S = 0.667
        assert abs(ia - 0.667) < 0.01

    def test_ia_cn_roundtrip(self):
        cn = 80.0
        ia = HmsUtils.calculate_ia_from_cn(cn)
        cn_back = HmsUtils.calculate_cn_from_ia(ia)
        assert abs(cn_back - cn) < 0.01

    def test_cn_100_gives_zero_ia(self):
        ia = HmsUtils.calculate_ia_from_cn(100.0)
        assert ia == 0.0

    def test_cn_zero_raises(self):
        with pytest.raises(ValueError):
            HmsUtils.calculate_ia_from_cn(0.0)


# ---------------------------------------------------------------------------
# validate_project / list_project_files
# ---------------------------------------------------------------------------

class TestValidateProject:
    def test_valid_project(self, project_dir_33):
        result = HmsUtils.validate_project(project_dir_33)
        assert result["valid"] is True
        assert result["project_file"] is not None

    def test_nonexistent_dir(self, tmp_path):
        result = HmsUtils.validate_project(tmp_path / "nonexistent")
        assert result["valid"] is False

    def test_finds_basin_files(self, project_dir_33):
        result = HmsUtils.validate_project(project_dir_33)
        assert len(result.get("basin_files", [])) > 0


class TestListProjectFiles:
    def test_finds_all_types(self, project_dir_33):
        files = HmsUtils.list_project_files(project_dir_33)
        assert isinstance(files, dict)
        assert len(files.get("basin", [])) > 0
        assert len(files.get("met", [])) > 0
        assert len(files.get("control", [])) > 0

    def test_returns_paths(self, project_dir_33):
        files = HmsUtils.list_project_files(project_dir_33)
        for f in files.get("basin", []):
            assert isinstance(f, Path)

    def test_nonexistent_raises_or_empty(self, tmp_path):
        # Depending on implementation, may raise or return empty
        try:
            files = HmsUtils.list_project_files(tmp_path / "nonexistent")
            # If no error, all lists should be empty
            for key, flist in files.items():
                assert len(flist) == 0
        except (FileNotFoundError, OSError):
            pass  # Also acceptable
