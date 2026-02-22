"""Tests for HmsBasin — the largest and most complex module."""

import shutil
from pathlib import Path

import pandas as pd
import pytest

from hms_commander.HmsBasin import HmsBasin


# ---------------------------------------------------------------------------
# get_subbasins
# ---------------------------------------------------------------------------

class TestGetSubbasins:
    def test_count_131(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        assert len(df) == 131

    def test_returns_dataframe(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        assert isinstance(df, pd.DataFrame)

    def test_has_required_columns(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        for col in ["name", "area", "downstream", "loss_method", "transform_method"]:
            assert col in df.columns

    def test_a100a_area(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        a100a = df[df["name"] == "A100A"]
        assert len(a100a) == 1
        assert abs(a100a.iloc[0]["area"] - 3.213) < 0.001

    def test_a100a_loss_method(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        a100a = df[df["name"] == "A100A"]
        assert a100a.iloc[0]["loss_method"] == "Green and Ampt"

    def test_a100a_downstream(self, basin_path_33):
        df = HmsBasin.get_subbasins(basin_path_33)
        a100a = df[df["name"] == "A100A"]
        assert a100a.iloc[0]["downstream"] == "A1000000_2494_J"


# ---------------------------------------------------------------------------
# get_junctions
# ---------------------------------------------------------------------------

class TestGetJunctions:
    def test_returns_dataframe(self, basin_path_33):
        df = HmsBasin.get_junctions(basin_path_33)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_has_downstream(self, basin_path_33):
        df = HmsBasin.get_junctions(basin_path_33)
        assert "downstream" in df.columns


# ---------------------------------------------------------------------------
# get_reaches
# ---------------------------------------------------------------------------

class TestGetReaches:
    def test_count_94(self, basin_path_33):
        df = HmsBasin.get_reaches(basin_path_33)
        assert len(df) == 94

    def test_has_route_method(self, basin_path_33):
        df = HmsBasin.get_reaches(basin_path_33)
        assert "route_method" in df.columns


# ---------------------------------------------------------------------------
# get_diversions
# ---------------------------------------------------------------------------

class TestGetDiversions:
    def test_returns_dataframe(self, basin_path_33):
        df = HmsBasin.get_diversions(basin_path_33)
        assert isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# get_loss_parameters
# ---------------------------------------------------------------------------

class TestGetLossParameters:
    def test_returns_dict(self, basin_path_33):
        params = HmsBasin.get_loss_parameters(basin_path_33, "A100A")
        assert isinstance(params, dict)

    def test_known_values(self, basin_path_33):
        params = HmsBasin.get_loss_parameters(basin_path_33, "A100A")
        assert params["method"] == "Green and Ampt"

    def test_nonexistent_raises(self, basin_path_33):
        with pytest.raises(ValueError):
            HmsBasin.get_loss_parameters(basin_path_33, "NONEXISTENT_SUB")


# ---------------------------------------------------------------------------
# get_transform_parameters
# ---------------------------------------------------------------------------

class TestGetTransformParameters:
    def test_clark_method(self, basin_path_33):
        params = HmsBasin.get_transform_parameters(basin_path_33, "A100A")
        assert params["method"] == "Clark"

    def test_tc_sc_values(self, basin_path_33):
        params = HmsBasin.get_transform_parameters(basin_path_33, "A100A")
        assert abs(params["time_of_concentration"] - 1.06) < 0.01
        assert abs(params["storage_coefficient"] - 14.86) < 0.01


# ---------------------------------------------------------------------------
# Batch getters (get_all_*)
# ---------------------------------------------------------------------------

class TestBatchGetters:
    def test_all_loss_shape(self, basin_path_33):
        df = HmsBasin.get_all_loss_parameters(basin_path_33)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 131
        assert "name" in df.columns

    def test_all_transform_shape(self, basin_path_33):
        df = HmsBasin.get_all_transform_parameters(basin_path_33)
        assert len(df) == 131
        assert "name" in df.columns

    def test_all_baseflow_shape(self, basin_path_33):
        df = HmsBasin.get_all_baseflow_parameters(basin_path_33)
        assert isinstance(df, pd.DataFrame)
        assert "name" in df.columns

    def test_all_routing_shape(self, basin_path_33):
        df = HmsBasin.get_all_routing_parameters(basin_path_33)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 94
        assert "name" in df.columns


# ---------------------------------------------------------------------------
# Batch setters (set_all_*)
# ---------------------------------------------------------------------------

class TestBatchSetters:
    def test_idempotent_write(self, tmp_basin):
        """Reading then writing the same data should not corrupt the file."""
        df = HmsBasin.get_all_loss_parameters(tmp_basin)
        result = HmsBasin.set_all_loss_parameters(tmp_basin, df, create_backup=False)
        assert result["elements_modified"] >= 0

        # Verify file still parses correctly
        df2 = HmsBasin.get_all_loss_parameters(tmp_basin)
        assert len(df2) == len(df)

    def test_modify_and_verify(self, tmp_basin):
        """Modify a parameter and read it back."""
        df = HmsBasin.get_all_transform_parameters(tmp_basin)
        # Find A100A and modify Tc
        idx = df[df["name"] == "A100A"].index[0]
        df.at[idx, "time_of_concentration"] = 99.99
        HmsBasin.set_all_transform_parameters(tmp_basin, df, create_backup=False)

        # Read back
        df2 = HmsBasin.get_all_transform_parameters(tmp_basin)
        a100a = df2[df2["name"] == "A100A"].iloc[0]
        assert abs(a100a["time_of_concentration"] - 99.99) < 0.01

    def test_nan_values_skipped(self, tmp_basin):
        """NaN values should be skipped, not written."""
        df = HmsBasin.get_all_loss_parameters(tmp_basin)
        # NaN values already exist in the df for non-applicable params
        result = HmsBasin.set_all_loss_parameters(tmp_basin, df, create_backup=False)
        # Should complete without error
        assert "elements_modified" in result


# ---------------------------------------------------------------------------
# CSV roundtrip
# ---------------------------------------------------------------------------

class TestCsvRoundtrip:
    def test_export_creates_file(self, tmp_basin, tmp_path):
        csv_path = tmp_path / "params.csv"
        result = HmsBasin.export_parameters_csv(tmp_basin, csv_path)
        assert result.exists()

    def test_import_roundtrip(self, tmp_basin, tmp_path):
        csv_path = tmp_path / "params.csv"
        HmsBasin.export_parameters_csv(tmp_basin, csv_path)
        # Import should succeed
        result = HmsBasin.import_parameters_csv(tmp_basin, csv_path, create_backup=False)
        assert isinstance(result, dict)

    def test_import_missing_file_raises(self, tmp_basin, tmp_path):
        with pytest.raises((FileNotFoundError, ValueError, OSError)):
            HmsBasin.import_parameters_csv(
                tmp_basin, tmp_path / "nonexistent.csv"
            )


# ---------------------------------------------------------------------------
# set_loss_parameters (single element)
# ---------------------------------------------------------------------------

class TestSetLossParameters:
    def test_modify_and_readback(self, tmp_basin):
        HmsBasin.set_loss_parameters(
            tmp_basin, "A100A", percent_impervious=50.0
        )
        params = HmsBasin.get_loss_parameters(tmp_basin, "A100A")
        assert "percent_impervious" in params
        assert abs(params["percent_impervious"] - 50.0) < 0.01

    def test_preserves_other_subbasins(self, tmp_basin):
        HmsBasin.set_loss_parameters(
            tmp_basin, "A100A", percent_impervious=50.0
        )
        # A100B should be unchanged
        params_b = HmsBasin.get_loss_parameters(tmp_basin, "A100B")
        assert params_b["method"] == "Green and Ampt"


# ---------------------------------------------------------------------------
# clone_basin
# ---------------------------------------------------------------------------

class TestCloneBasin:
    def test_clone_preserves_elements(self, tmp_project):
        """A file copy should have same subbasin count (clone_basin requires hms_object)."""
        original = tmp_project / "A100_1PCT.basin"
        clone_path = tmp_project / "A100_CLONE.basin"
        shutil.copy2(original, clone_path)
        df_orig = HmsBasin.get_subbasins(original)
        df_clone = HmsBasin.get_subbasins(clone_path)
        assert len(df_clone) == len(df_orig)

    def test_clone_independent_modification(self, tmp_project):
        """Modifying a clone should not affect the original."""
        original = tmp_project / "A100_1PCT.basin"
        clone_path = tmp_project / "A100_CLONE2.basin"
        shutil.copy2(original, clone_path)
        HmsBasin.set_loss_parameters(clone_path, "A100A", percent_impervious=99.0)
        orig_params = HmsBasin.get_loss_parameters(original, "A100A")
        # Original should be unchanged
        assert orig_params["method"] == "Green and Ampt"


# ---------------------------------------------------------------------------
# Cross-version comparison
# ---------------------------------------------------------------------------

class TestCrossVersion:
    def test_same_subbasin_count(self, basin_path_33, basin_path_411):
        df_33 = HmsBasin.get_subbasins(basin_path_33)
        df_411 = HmsBasin.get_subbasins(basin_path_411)
        assert len(df_33) == len(df_411)

    def test_same_reach_count(self, basin_path_33, basin_path_411):
        df_33 = HmsBasin.get_reaches(basin_path_33)
        df_411 = HmsBasin.get_reaches(basin_path_411)
        assert len(df_33) == len(df_411)

    def test_same_areas(self, basin_path_33, basin_path_411):
        df_33 = HmsBasin.get_subbasins(basin_path_33)
        df_411 = HmsBasin.get_subbasins(basin_path_411)
        # Merge on name and compare areas
        merged = df_33.merge(df_411, on="name", suffixes=("_33", "_411"))
        for _, row in merged.iterrows():
            assert abs(row["area_33"] - row["area_411"]) < 0.01, (
                f"Area mismatch for {row['name']}: {row['area_33']} vs {row['area_411']}"
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsBasin.get_subbasins(tmp_path / "nonexistent.basin")

    def test_missing_subbasin(self, basin_path_33):
        with pytest.raises(ValueError):
            HmsBasin.get_loss_parameters(basin_path_33, "DOES_NOT_EXIST")
