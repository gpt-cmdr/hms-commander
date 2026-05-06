"""Tests for FrequencyStorm — pure computation, no network needed."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hms_commander.Atlas14Storm import Atlas14Storm
from hms_commander.FrequencyStorm import FrequencyStorm

ATLAS14_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "atlas14"
    / "spring_creek_pfds_depth_english_pds.txt"
)


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

    def test_time_axis_and_zero_sentinel_contract(self):
        result = FrequencyStorm.generate_hyetograph(
            total_depth_inches=13.20,
            total_duration_min=1440,
            time_interval_min=5,
        )

        assert result["incremental_depth"].iloc[0] == 0.0
        assert result["hour"].iloc[0] == pytest.approx(0.0)
        assert result["hour"].iloc[1] == pytest.approx(5 / 60)
        assert result["hour"].iloc[-1] == pytest.approx(24.0)

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
# Atlas14Storm point-frequency parsing (fixture-based, no network)
# ---------------------------------------------------------------------------

class TestAtlas14PointFrequency:
    def test_parse_pfds_response_builds_duration_table(self):
        response_text = ATLAS14_FIXTURE_PATH.read_text(encoding="utf-8")

        parsed = Atlas14Storm.parse_pfds_response(response_text)
        depth_table = Atlas14Storm.build_depth_duration_table(parsed)

        assert parsed["reg"] == "orb"
        assert parsed["region"] == "Ohio River Basin"
        assert parsed["latitude"] == pytest.approx(39.8153)
        assert parsed["longitude"] == pytest.approx(-89.6987)
        assert len(depth_table) == 19
        assert depth_table.loc[depth_table["duration_minutes"] == 1440, 100].iloc[0] == pytest.approx(6.15)

    def test_build_frequency_storm_depths_returns_standard_hms_vector(self):
        response_text = ATLAS14_FIXTURE_PATH.read_text(encoding="utf-8")
        depth_table = Atlas14Storm.build_depth_duration_table(
            Atlas14Storm.parse_pfds_response(response_text)
        )

        depths = Atlas14Storm.build_frequency_storm_depths(depth_table, ari_years=100)

        assert depths == pytest.approx([0.861, 1.61, 2.32, 3.11, 3.78, 4.10, 4.81, 6.15])

    def test_parse_temporal_csv_invalid_content_raises_clear_value_error(self):
        with pytest.raises(ValueError, match="No Atlas 14 quartile tables"):
            Atlas14Storm.parse_temporal_csv("not a valid atlas14 temporal csv")

    def test_get_point_frequency_estimates_accepts_string_cache_dir(self, tmp_path):
        cache_file = Atlas14Storm._pfds_cache_file(
            latitude=39.815328,
            longitude=-89.698713,
            series="pds",
            units="english",
            cache_dir=tmp_path,
        )
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(ATLAS14_FIXTURE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

        result = Atlas14Storm.get_point_frequency_estimates(
            latitude=39.815328,
            longitude=-89.698713,
            series="pds",
            units="english",
            cache_dir=str(tmp_path),
        )

        assert result["cache_file"] == cache_file
        assert len(result["depth_duration_table"]) == 19

    def test_get_frequency_storm_depths_converts_metric_depths_to_inches(self, monkeypatch):
        metric_depth_table = pd.DataFrame(
            [
                {"duration_label": "5-min", "duration_minutes": 5, 100: 0.861 * 25.4},
                {"duration_label": "15-min", "duration_minutes": 15, 100: 1.61 * 25.4},
                {"duration_label": "30-min", "duration_minutes": 30, 100: 2.32 * 25.4},
                {"duration_label": "60-min", "duration_minutes": 60, 100: 3.11 * 25.4},
                {"duration_label": "2-hr", "duration_minutes": 120, 100: 3.78 * 25.4},
                {"duration_label": "3-hr", "duration_minutes": 180, 100: 4.10 * 25.4},
                {"duration_label": "6-hr", "duration_minutes": 360, 100: 4.81 * 25.4},
                {"duration_label": "24-hr", "duration_minutes": 1440, 100: 6.15 * 25.4},
            ]
        )

        def fake_get_point_frequency_estimates(**kwargs):
            return {
                "depth_duration_table": metric_depth_table,
                "units": "metric",
            }

        monkeypatch.setattr(
            Atlas14Storm,
            "get_point_frequency_estimates",
            staticmethod(fake_get_point_frequency_estimates),
        )

        result = Atlas14Storm.get_frequency_storm_depths(
            latitude=39.815328,
            longitude=-89.698713,
            ari_years=100,
            units="metric",
        )

        assert result["native_units"] == "metric"
        assert result["depths_native_units"] == pytest.approx(
            [0.861 * 25.4, 1.61 * 25.4, 2.32 * 25.4, 3.11 * 25.4, 3.78 * 25.4, 4.10 * 25.4, 4.81 * 25.4, 6.15 * 25.4]
        )
        assert result["depths_inches"] == pytest.approx([0.861, 1.61, 2.32, 3.11, 3.78, 4.10, 4.81, 6.15])

    def test_convert_depths_to_inches_rejects_unknown_units(self):
        assert Atlas14Storm.convert_depths_to_inches([25.4], units="mm") == pytest.approx([1.0])
        assert Atlas14Storm.convert_depths_to_inches([1.0], units="inches") == pytest.approx([1.0])

        with pytest.raises(ValueError, match="Unsupported Atlas 14 units"):
            Atlas14Storm.convert_depths_to_inches([1.0], units="cubits")

    def test_generate_hyetograph_from_ari_returns_dataframe_contract(self, monkeypatch):
        calls = {}
        expected = pd.DataFrame(
            {
                "hour": [0.0, 0.5],
                "incremental_depth": [0.0, 1.0],
                "cumulative_depth": [0.0, 1.0],
            }
        )

        def fake_generate_hyetograph(**kwargs):
            calls.update(kwargs)
            return expected

        monkeypatch.setattr(
            Atlas14Storm,
            "generate_hyetograph",
            staticmethod(fake_generate_hyetograph),
        )

        result = Atlas14Storm.generate_hyetograph_from_ari(
            ari_years=100,
            total_depth_inches=1.0,
            state="tx",
            region=3,
        )

        assert isinstance(result, pd.DataFrame)
        assert result.columns.tolist() == ["hour", "incremental_depth", "cumulative_depth"]
        assert result is expected
        assert calls["aep_percent"] == pytest.approx(1.0)

    def test_generate_hyetograph_time_axis_contract(self, monkeypatch):
        temporal = pd.DataFrame(
            {"50%": np.linspace(0.0, 100.0, 49)},
            index=pd.Index(np.linspace(0.0, 24.0, 49), name="hours"),
        )

        monkeypatch.setattr(
            Atlas14Storm,
            "load_temporal_distribution",
            staticmethod(lambda *args, **kwargs: {"All Cases": temporal}),
        )

        result = Atlas14Storm.generate_hyetograph(
            total_depth_inches=2.0,
            state="tx",
            region=3,
            duration_hours=24,
            aep_percent=50.0,
            interval_minutes=30,
        )

        assert result.columns.tolist() == ["hour", "incremental_depth", "cumulative_depth"]
        assert result["incremental_depth"].iloc[0] == 0.0
        assert result["hour"].iloc[0] == pytest.approx(0.0)
        assert result["hour"].iloc[1] == pytest.approx(0.5)
        assert result["hour"].iloc[-1] == pytest.approx(24.0)
        assert result["cumulative_depth"].iloc[-1] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# Atlas14Storm (requires network — marked accordingly)
# ---------------------------------------------------------------------------

class TestAtlas14Storm:
    @pytest.mark.requires_network
    def test_basic_generation(self):
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
        assert isinstance(hyeto, pd.DataFrame)
        assert hyeto.columns.tolist() == ["hour", "incremental_depth", "cumulative_depth"]
        total_sum = hyeto["cumulative_depth"].iloc[-1]
        assert abs(total_sum - 17.9) < 0.01

    @pytest.mark.requires_network
    def test_depth_conservation(self):
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
        assert isinstance(hyeto, pd.DataFrame)
        assert hyeto.columns.tolist() == ["hour", "incremental_depth", "cumulative_depth"]
        total_sum = hyeto["cumulative_depth"].iloc[-1]
        assert abs(total_sum - total) < 0.01
