"""Tests for private hyetograph generation primitives."""

import numpy as np

from hms_commander._hyetograph import (
    build_hyetograph_frame,
    incremental_depths_from_cumulative_pattern,
    incremental_depths_from_cumulative_values,
    resample_incremental_pattern,
)


def test_resample_incremental_pattern_preserves_unit_depth():
    pattern = np.array([0.25, 0.25, 0.25, 0.25])

    resampled = resample_incremental_pattern(pattern, target_intervals=8)

    assert len(resampled) == 8
    assert resampled.sum() == np.float64(1.0)


def test_cumulative_values_convert_to_incremental_depths():
    incremental = incremental_depths_from_cumulative_values(
        np.array([0, 25, 75, 100]),
        total_depth_inches=4.0,
        value_scale=100.0,
    )

    assert incremental.tolist() == [0.0, 1.0, 2.0, 1.0]


def test_cumulative_pattern_interpolation_preserves_total_depth():
    cumulative = np.linspace(0.0, 1.0, 11)

    incremental = incremental_depths_from_cumulative_pattern(
        cumulative,
        total_depth_inches=5.0,
        source_duration_min=10,
        time_interval_min=2,
    )

    assert len(incremental) == 6
    assert abs(incremental.sum() - 5.0) < 1e-12


def test_build_hyetograph_frame_contract():
    frame = build_hyetograph_frame(np.array([0.0, 1.0, 2.0]), time_interval_min=30)

    assert frame.columns.tolist() == ["hour", "incremental_depth", "cumulative_depth"]
    assert frame["hour"].tolist() == [0.5, 1.0, 1.5]
    assert frame["cumulative_depth"].tolist() == [0.0, 1.0, 3.0]
