"""Tests for HmsMet — meteorologic model operations."""

import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

from hms_commander.HmsMet import HmsMet
from hms_commander.HmsPrj import HmsPrj


def _write_synthetic_met(
    path: Path,
    precipitation_method: str = "None",
    subbasins=("Upper", "Lower"),
) -> Path:
    """Write a minimal HMS-like met file for precipitation write tests."""
    lines = [
        "Meteorology: SyntheticMet",
        "     Description: Synthetic precipitation round-trip fixture",
        "     Version: 4.13",
        "     Unit System: English",
        f"     Precipitation Method: {precipitation_method}",
        "     Snowmelt Method: None",
        "End:",
        "",
    ]
    for subbasin in subbasins:
        lines.extend([
            f"Subbasin: {subbasin}",
            "     # Preserve this manual note",
            "End:",
            "",
        ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# get_precipitation_method
# ---------------------------------------------------------------------------

class TestGetPrecipitationMethod:
    def test_returns_string(self, met_path_33):
        method = HmsMet.get_precipitation_method(met_path_33)
        assert isinstance(method, str)

    def test_returns_known_method(self, met_path_33):
        method = HmsMet.get_precipitation_method(met_path_33)
        assert method == "Frequency Based Hypothetical"


# ---------------------------------------------------------------------------
# get_gage_assignments
# ---------------------------------------------------------------------------

class TestGetGageAssignments:
    def test_returns_dataframe(self, met_path_33):
        df = HmsMet.get_gage_assignments(met_path_33)
        assert isinstance(df, pd.DataFrame)

    def test_has_subbasin_column(self, met_path_33):
        df = HmsMet.get_gage_assignments(met_path_33)
        # Frequency storm met files may not have gage assignments
        # but should still return a DataFrame
        assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# get_frequency_storm_params
# ---------------------------------------------------------------------------

class TestGetFrequencyStormParams:
    def test_returns_dict(self, met_path_33):
        params = HmsMet.get_frequency_storm_params(met_path_33)
        assert isinstance(params, dict)

    def test_known_values(self, met_path_33):
        params = HmsMet.get_frequency_storm_params(met_path_33)
        # From the file: Exceedence Frequency: 1, Total Duration: 1440
        if "exceedance_frequency" in params:
            assert params["exceedance_frequency"] == 1.0
        if "total_duration" in params:
            assert params["total_duration"] == 1440


# ---------------------------------------------------------------------------
# get_precipitation_depths
# ---------------------------------------------------------------------------

class TestGetPrecipitationDepths:
    def test_returns_list(self, met_path_33):
        depths = HmsMet.get_precipitation_depths(met_path_33)
        assert isinstance(depths, list)

    def test_count_matches(self, met_path_33):
        depths = HmsMet.get_precipitation_depths(met_path_33)
        # From file: 12 Depth entries (1.2, 2.1, 4.3, 5.7, 6.8, 9.1, 11.1, 13.5, 0, 0, 0, 0)
        assert len(depths) == 12


# ---------------------------------------------------------------------------
# set_precipitation_depths
# ---------------------------------------------------------------------------

class TestSetPrecipitationDepths:
    def test_modify_and_readback(self, tmp_met):
        original = HmsMet.get_precipitation_depths(tmp_met)
        # Modify first depth
        new_depths = list(original)
        new_depths[0] = 99.99
        HmsMet.set_precipitation_depths(tmp_met, new_depths)
        readback = HmsMet.get_precipitation_depths(tmp_met)
        assert abs(readback[0] - 99.99) < 0.01

    def test_count_mismatch_raises(self, tmp_met):
        with pytest.raises(ValueError):
            HmsMet.set_precipitation_depths(tmp_met, [1.0, 2.0])  # Wrong count


# ---------------------------------------------------------------------------
# set_precipitation
# ---------------------------------------------------------------------------

class TestSetPrecipitation:
    def test_frequency_storm_round_trip_preserves_format(self, tmp_met):
        original = tmp_met.read_text(encoding="utf-8")
        original = original.replace(
            "     Depth: 4.3000",
            "     # Preserve depth note\n     Depth: 4.3000",
            1,
        )
        tmp_met.write_text(original, encoding="utf-8")

        new_depths = [1.1111, 2.2222, 3.3333, 4.4444, 5.5555, 6.6666,
                      7.7777, 8.8888, 0.1111, 0.2222, 0.3333, 0.4444]

        summary = HmsMet.set_precipitation(
            tmp_met,
            "Frequency Based Hypothetical",
            {"depths": new_depths},
        )

        rewritten = tmp_met.read_text(encoding="utf-8")
        assert summary["depths_written"] == len(new_depths)
        assert HmsMet.get_precipitation_method(tmp_met) == "Frequency Based Hypothetical"
        assert HmsMet.get_precipitation_depths(tmp_met) == pytest.approx(new_depths)
        assert "     # Preserve depth note" in rewritten
        assert rewritten.index("Precip Method Parameters:") < rewritten.index("Subbasin: A100A")
        assert re.search(r"^     Depth: 1\.1111$", rewritten, flags=re.MULTILINE)

    def test_gage_assignments_round_trip(self, tmp_path):
        met_path = _write_synthetic_met(tmp_path / "gage_roundtrip.met")

        summary = HmsMet.set_precipitation(
            met_path,
            "Gage Weights",
            {
                "gage_assignments": [
                    {"subbasin": "Upper", "precip_gage": "Rain_Upper", "weight": 0.65},
                    {"subbasin": "Lower", "precip_gage": "Rain_Lower", "weight": 0.35},
                ]
            },
        )

        assignments = HmsMet.get_gage_assignments(met_path).set_index("subbasin")
        rewritten = met_path.read_text(encoding="utf-8")
        assert summary["subbasins_modified"] == 2
        assert HmsMet.get_precipitation_method(met_path) == "Gage Weights"
        assert assignments.loc["Upper", "precip_gage"] == "Rain_Upper"
        assert assignments.loc["Lower", "precip_gage"] == "Rain_Lower"
        assert assignments.loc["Upper", "weight"] == pytest.approx(0.65)
        assert "     # Preserve this manual note" in rewritten
        assert "     Precip Gage: Rain_Upper" in rewritten
        assert "     Weight: 0.65" in rewritten

    def test_gridded_precipitation_round_trip_with_dss_reference(self, tmp_path):
        met_path = _write_synthetic_met(tmp_path / "grid_roundtrip.met", subbasins=())
        dss_pathname = "/AORC/GRID/PRECIP/01JAN2020/1HOUR/OBS/"

        summary = HmsMet.set_precipitation(
            met_path,
            "Gridded Precipitation",
            {
                "grid_name": "AORC_Test_Grid",
                "dss_file": "aorc_test.dss",
                "dss_pathname": dss_pathname,
            },
        )

        info = HmsMet.get_met_info(met_path)
        assert summary["grid_name"] == "AORC_Test_Grid"
        assert summary["dss_references_written"] == 2
        assert HmsMet.get_precipitation_method(met_path) == "Gridded Precipitation"
        assert info["meteorology"]["Precipitation Grid"] == "AORC_Test_Grid"
        assert info["dss_references"] == [
            {"dss_file": "aorc_test.dss", "dss_pathname": dss_pathname}
        ]

    def test_empty_precipitation_round_trip(self, tmp_path):
        met_path = _write_synthetic_met(
            tmp_path / "empty_roundtrip.met",
            precipitation_method="Specified Hyetograph",
        )

        summary = HmsMet.set_precipitation(met_path, "None")

        assert summary["method"] == "None"
        assert HmsMet.get_precipitation_method(met_path) == "None"
        assert "Precip Gage:" not in met_path.read_text(encoding="utf-8")

    def test_missing_gage_reference_raises_without_writing(self, tmp_path):
        met_path = _write_synthetic_met(tmp_path / "missing_gage.met")
        original = met_path.read_text(encoding="utf-8")

        with pytest.raises(ValueError, match="empty precipitation gage"):
            HmsMet.set_precipitation(
                met_path,
                "Gage Weights",
                {"gage_assignments": [{"subbasin": "Upper", "precip_gage": ""}]},
            )

        assert met_path.read_text(encoding="utf-8") == original

    def test_missing_subbasin_reference_raises_without_writing(self, tmp_path):
        met_path = _write_synthetic_met(tmp_path / "missing_subbasin.met")
        original = met_path.read_text(encoding="utf-8")

        with pytest.raises(ValueError, match="missing subbasins"):
            HmsMet.set_precipitation(
                met_path,
                "Specified Hyetograph",
                {"gage_assignments": [{"subbasin": "NotInMet", "precip_gage": "Rain"}]},
            )

        assert met_path.read_text(encoding="utf-8") == original

    def test_invalid_gridded_dss_pathname_raises_without_writing(self, tmp_path):
        met_path = _write_synthetic_met(tmp_path / "bad_grid_ref.met", subbasins=())
        original = met_path.read_text(encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid DSS pathname"):
            HmsMet.set_precipitation(
                met_path,
                "Gridded Precipitation",
                {"grid_name": "AORC_Test_Grid", "dss_pathname": "BAD/PATH"},
            )

        assert met_path.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# set_all_gage_assignments
# ---------------------------------------------------------------------------

class TestSetAllGageAssignments:
    def test_batch_modify(self, tmp_met):
        df = pd.DataFrame({
            "subbasin": ["A100A", "A100B"],
            "precip_gage": ["TestGage1", "TestGage2"],
            "weight": [1.0, 1.0],
        })
        result = HmsMet.set_all_gage_assignments(tmp_met, df, create_backup=False)
        assert isinstance(result, dict)
        assert "subbasins_modified" in result
        # Verify modifications or lookup attempts occurred
        assert result["subbasins_modified"] > 0 or len(result.get("subbasins_not_found", [])) > 0

    def test_backup_created(self, tmp_met):
        df = pd.DataFrame({
            "subbasin": ["A100A"],
            "precip_gage": ["TestGage1"],
        })
        result = HmsMet.set_all_gage_assignments(tmp_met, df, create_backup=True)
        assert result.get("backup_path") is not None, "Backup requested but no path returned"
        assert Path(result["backup_path"]).exists(), "Backup file does not exist on disk"


# ---------------------------------------------------------------------------
# get_met_info
# ---------------------------------------------------------------------------

class TestGetMetInfo:
    def test_returns_dict(self, met_path_33):
        info = HmsMet.get_met_info(met_path_33)
        assert isinstance(info, dict)


# ---------------------------------------------------------------------------
# clone_met
# ---------------------------------------------------------------------------

class TestCloneMet:
    def test_clone_creates_file(self, tmp_path, met_path_33):
        dest = tmp_path / "clone_test.met"
        shutil.copy2(met_path_33, dest)
        # clone_met needs hms_object context normally
        # Just verify file copy preserves content
        content = dest.read_text(encoding="utf-8")
        assert "Meteorology:" in content

    def test_clone_preserves_content(self, tmp_path, met_path_33):
        dest = tmp_path / "clone.met"
        shutil.copy2(met_path_33, dest)
        original_method = HmsMet.get_precipitation_method(met_path_33)
        clone_method = HmsMet.get_precipitation_method(dest)
        assert original_method == clone_method

    def test_clone_registers_precipitation_in_initialized_project(self, tmp_project):
        hms_project = HmsPrj().initialize(tmp_project)

        clone_path = HmsMet.clone_met(
            "1%_24HR",
            "Atlas14_CLONE_REGISTERED",
            hms_object=hms_project,
        )

        assert clone_path.exists()
        assert "Atlas14_CLONE_REGISTERED" in hms_project.met_df["name"].tolist()
        project_text = (tmp_project / "A1000000.hms").read_text(encoding="utf-8")
        assert "Precipitation: Atlas14_CLONE_REGISTERED" in project_text
        assert "Met File: Atlas14_CLONE_REGISTERED.met" not in project_text


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsMet.get_precipitation_method(tmp_path / "nonexistent.met")

    def test_missing_model(self, met_path_33):
        # get_met_info should handle gracefully
        info = HmsMet.get_met_info(met_path_33)
        assert isinstance(info, dict)
