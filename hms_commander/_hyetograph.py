"""Private hyetograph generation primitives.

Public storm classes keep their domain-specific API and validation. These
helpers centralize the repeated numerical operations used to assemble the
standard HMS-style hyetograph DataFrame.

Storm generators use a sentinel-inclusive time axis: row 0 is the zero-depth
t=0 value, later rows are interval end times, and the last row is the storm
duration when the input covers the full storm.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def build_hyetograph_frame(
    incremental_depth: np.ndarray,
    time_interval_min: int,
) -> pd.DataFrame:
    """Build the standard HMS hyetograph DataFrame from incremental depths."""

    incremental = np.asarray(incremental_depth, dtype=float)
    interval_hours = time_interval_min / 60.0
    hours = np.arange(0, len(incremental)) * interval_hours
    return pd.DataFrame(
        {
            "hour": hours,
            "incremental_depth": incremental,
            "cumulative_depth": np.cumsum(incremental),
        }
    )


def resample_incremental_pattern(
    pattern: np.ndarray,
    target_intervals: int,
    source_intervals: Optional[int] = None,
) -> np.ndarray:
    """Resample an incremental dimensionless pattern by cumulative interpolation."""

    source_pattern = np.asarray(pattern, dtype=float)
    if source_intervals is None:
        source_intervals = len(source_pattern)
    if target_intervals <= 0:
        raise ValueError(f"Target intervals must be positive: {target_intervals}")

    cumulative = np.insert(np.cumsum(source_pattern), 0, 0.0)
    source_t = np.linspace(0.0, 1.0, source_intervals + 1)
    target_t = np.linspace(0.0, 1.0, target_intervals + 1)
    target_cumulative = np.interp(target_t, source_t, cumulative)
    resampled = np.diff(target_cumulative)

    total = resampled.sum()
    if total != 0:
        resampled = resampled / total
    return resampled


def shift_incremental_peak(
    pattern: np.ndarray,
    current_peak_pct: float,
    target_peak_pct: float,
) -> np.ndarray:
    """Shift an incremental pattern to a target peak position and renormalize."""

    shifted = np.asarray(pattern, dtype=float).copy()
    n = len(shifted)
    current_peak_idx = int(current_peak_pct / 100 * n)
    target_peak_idx = int(target_peak_pct / 100 * n)
    shift = target_peak_idx - current_peak_idx

    if shift == 0:
        return shifted

    shifted = np.roll(shifted, shift)
    if shift > 0:
        shifted[:shift] = shifted[shift]
    else:
        shifted[shift:] = shifted[shift - 1]

    total = shifted.sum()
    if total != 0:
        shifted = shifted / total
    return shifted


def incremental_depths_from_cumulative_values(
    cumulative_values: np.ndarray,
    total_depth_inches: float,
    value_scale: float = 1.0,
) -> np.ndarray:
    """Scale cumulative fractions/percentages and convert to incremental depths."""

    cumulative = np.asarray(cumulative_values, dtype=float)
    cumulative_depth = cumulative / value_scale * total_depth_inches
    return np.diff(cumulative_depth, prepend=0.0)


def incremental_depths_from_cumulative_pattern(
    cumulative_pattern: np.ndarray,
    total_depth_inches: float,
    source_duration_min: int,
    time_interval_min: int,
    value_scale: float = 1.0,
) -> np.ndarray:
    """Interpolate a cumulative pattern to an interval and return increments."""

    num_output_steps = source_duration_min // time_interval_min + 1
    output_times = np.linspace(0, source_duration_min, num_output_steps)
    source_times = np.linspace(0, source_duration_min, len(cumulative_pattern))
    cumulative_resampled = np.interp(output_times, source_times, cumulative_pattern)
    return incremental_depths_from_cumulative_values(
        cumulative_resampled,
        total_depth_inches=total_depth_inches,
        value_scale=value_scale,
    )
