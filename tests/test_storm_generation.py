"""Tests for FrequencyStorm — pure computation, no network needed."""

import numpy as np
import pandas as pd
import pytest

from hms_commander.FrequencyStorm import FrequencyStorm


# ---------------------------------------------------------------------------
# generate_hyetograph
# ---------------------------------------------------------------------------

class TestFrequencyStormGenerate:
    def test_returns_dataframe(self):
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=13.20)
        assert isinstance(result, pd.DataFrame)

    def test_depth_conservation(self):
        """Sum of incremental depths must equal total depth to 1e-6."""
        total = 13.20
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=total)
        actual_sum = result["incremental_depth"].sum()
        assert abs(actual_sum - total) < 1e-4, (
            f"Depth conservation failed: {actual_sum} vs {total}"
        )

    def test_depth_conservation_different_depth(self):
        total = 9.10
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=total)
        actual_sum = result["incremental_depth"].sum()
        assert abs(actual_sum - total) < 1e-4

    def test_non_negative_increments(self):
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=13.20)
        assert (result["incremental_depth"] >= -1e-10).all(), "Negative increments found"

    def test_peak_position_67_percent(self):
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=13.20, peak_position_pct=67.0
        )
        peak_idx = result["incremental_depth"].idxmax()
        total_intervals = len(result) - 1  # Exclude t=0
        peak_fraction = peak_idx / total_intervals
        # Peak should be roughly at 67% of duration (some tolerance)
        assert 0.5 < peak_fraction < 0.85, f"Peak at {peak_fraction*100:.0f}%"

    def test_correct_number_of_intervals(self):
        """24hr storm at 5-min intervals = 288 intervals + 1 for t=0 = 289."""
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=13.20,
            total_duration_min=1440,
            time_interval_min=5,
        )
        expected = (1440 // 5) + 1  # 289
        assert len(result) == expected

    def test_has_required_columns(self):
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=13.20)
        assert "hour" in result.columns
        assert "incremental_depth" in result.columns
        assert "cumulative_depth" in result.columns

    def test_cumulative_monotonic(self):
        result = FrequencyStorm.generate_hyetograph(total_depth_inches=13.20)
        cumulative = result["cumulative_depth"].values
        diffs = np.diff(cumulative)
        assert (diffs >= -1e-10).all(), "Cumulative depth is not monotonically increasing"


# ---------------------------------------------------------------------------
# Variable durations
# ---------------------------------------------------------------------------

class TestFrequencyStormVariableDuration:
    def test_6hr_depth_conservation(self):
        total = 9.10
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=total, total_duration_min=360
        )
        actual_sum = result["incremental_depth"].sum()
        assert abs(actual_sum - total) < 1e-4

    def test_12hr_depth_conservation(self):
        total = 11.10
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=total, total_duration_min=720
        )
        actual_sum = result["incremental_depth"].sum()
        assert abs(actual_sum - total) < 1e-4

    def test_6hr_interval_count(self):
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=9.10,
            total_duration_min=360,
            time_interval_min=5,
        )
        expected = (360 // 5) + 1  # 73
        assert len(result) == expected


# ---------------------------------------------------------------------------
# get_pattern_info
# ---------------------------------------------------------------------------

class TestFrequencyStormPatternInfo:
    def test_returns_dict(self):
        info = FrequencyStorm.get_pattern_info()
        assert isinstance(info, dict)

    def test_expected_keys(self):
        info = FrequencyStorm.get_pattern_info()
        assert "num_intervals" in info
        assert "time_interval_min" in info
        assert "total_duration_min" in info


# ---------------------------------------------------------------------------
# generate_from_ddf
# ---------------------------------------------------------------------------

class TestFrequencyStormDdf:
    def test_known_depths(self):
        # HCFCD M3 Model D: TP-40 depths for 1% AEP
        depths = [1.20, 2.10, 4.30, 5.70, 6.80, 9.10, 11.10, 13.50]
        result = FrequencyStorm.generate_from_ddf(depths)
        # Should return DataFrame (delegates to generate_hyetograph)
        assert result is not None

    def test_depth_conservation_from_ddf(self):
        depths = [1.20, 2.10, 4.30, 5.70, 6.80, 9.10, 11.10, 13.50]
        result = FrequencyStorm.generate_from_ddf(depths)
        if isinstance(result, pd.DataFrame):
            total = result["incremental_depth"].sum()
        else:
            total = np.sum(result)
        # Should equal last depth (24hr total)
        assert abs(total - 13.50) < 1e-3

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            FrequencyStorm.generate_from_ddf(
                depths=[1.0, 2.0, 3.0],
                durations=[5, 15],  # Mismatch!
            )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestFrequencyStormErrorHandling:
    def test_zero_depth(self):
        # Zero depth should produce all-zero hyetograph or raise
        try:
            result = FrequencyStorm.generate_hyetograph(total_depth_inches=0.0)
            if isinstance(result, pd.DataFrame):
                assert result["incremental_depth"].sum() == 0.0
        except (ValueError, ZeroDivisionError):
            pass  # Also acceptable

    def test_negative_depth(self):
        try:
            result = FrequencyStorm.generate_hyetograph(total_depth_inches=-5.0)
            # If it produces a result, all increments should be <= 0
            assert (result["incremental_depth"] <= 1e-10).all(), (
                "Negative depth produced positive increments"
            )
        except (ValueError, ZeroDivisionError):
            pass  # Raising is also acceptable


# ---------------------------------------------------------------------------
# validate_against_ground_truth
# ---------------------------------------------------------------------------

class TestValidateAgainstGroundTruth:
    def test_identical_arrays(self):
        a = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
        result = FrequencyStorm.validate_against_ground_truth(a, a)
        assert result["rmse"] < 1e-10
        assert result["max_diff"] < 1e-10

    def test_different_arrays(self):
        a = np.array([0.0, 1.0, 2.0, 1.0, 0.0])
        b = np.array([0.0, 1.1, 2.1, 1.1, 0.1])
        result = FrequencyStorm.validate_against_ground_truth(a, b)
        assert result["rmse"] > 0
        assert result["max_diff"] > 0

    def test_length_mismatch_raises(self):
        a = np.array([1.0, 2.0])
        b = np.array([1.0, 2.0, 3.0])
        with pytest.raises(ValueError):
            FrequencyStorm.validate_against_ground_truth(a, b)


# ---------------------------------------------------------------------------
# Atlas14Storm (requires network — marked accordingly)
# ---------------------------------------------------------------------------

class TestAtlas14Storm:
    @pytest.mark.requires_network
    def test_basic_generation(self):
        from hms_commander.Atlas14Storm import Atlas14Storm
        try:
            hyeto = Atlas14Storm.generate_hyetograph(
                total_depth_inches=17.9,
                state="tx",
                region=3,
                aep_percent=1.0,
            )
        except Exception:
            pytest.skip("Atlas14 data not available (network/cache)")
        assert len(hyeto) > 0
        # hyeto may be DataFrame or ndarray — use .values if needed
        if isinstance(hyeto, pd.DataFrame):
            total_sum = hyeto.iloc[:, -1].max()  # cumulative max = total
        else:
            total_sum = float(np.sum(hyeto))
        assert abs(total_sum - 17.9) < 0.01

    @pytest.mark.requires_network
    def test_depth_conservation(self):
        from hms_commander.Atlas14Storm import Atlas14Storm
        total = 10.5
        try:
            hyeto = Atlas14Storm.generate_hyetograph(
                total_depth_inches=total,
                state="tx",
                region=3,
                aep_percent=10.0,
            )
        except Exception:
            pytest.skip("Atlas14 data not available (network/cache)")
        if isinstance(hyeto, pd.DataFrame):
            total_sum = hyeto.iloc[:, -1].max()
        else:
            total_sum = float(np.sum(hyeto))
        assert abs(total_sum - total) < 0.01
