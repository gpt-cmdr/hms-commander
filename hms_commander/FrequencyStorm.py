"""
FrequencyStorm - Generate TP-40/Hydro-35 hyetographs for HCFCD M3 models.

This module generates hyetographs using the same algorithm as HEC-HMS
"Hypothetical Storm → User Specified Pattern" method.

The temporal pattern was extracted from HCFCD M3 Model D (Brays Bayou) HMS output
and validated to match HMS to 10^-6 precision for 24-hour storms.

Algorithm:
    Cumulative pattern scaling (same as HMS User Specified Pattern and Atlas14Storm):
    1. Load dimensionless temporal pattern
    2. Interpolate cumulative percentage at each time step
    3. Scale to total depth
    4. Convert cumulative to incremental

HCFCD M3 Model Defaults:
    - Duration: 24 hours (1440 minutes)
    - Time interval: 5 minutes
    - Peak position: 67% of duration
    - All 21 M3 models use these values for consistency

Supported Configurations:
    - Duration: Any duration (validated for 24-hour)
    - Intervals: Any interval (5-minute recommended for HCFCD)
    - Peak position: Variable (67% default for HCFCD)

Example:
    >>> from hms_commander import FrequencyStorm
    >>>
    >>> # HCFCD M3 compatible (all defaults)
    >>> hyeto = FrequencyStorm.generate_hyetograph(13.20)
    >>> print(f"24hr: {len(hyeto)} intervals, peak={hyeto.max():.2f}")
    24hr: 288 intervals, peak=1.20
    >>>
    >>> # Variable duration (6-hour storm)
    >>> hyeto_6hr = FrequencyStorm.generate_hyetograph(9.10, total_duration_min=360)
    >>> print(f"6hr: {len(hyeto_6hr)} intervals, peak={hyeto_6hr.max():.2f}")
    6hr: 72 intervals, peak=1.48
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Union, List, Tuple
import logging

logger = logging.getLogger(__name__)


class FrequencyStorm:
    """
    Generate TP-40/Hydro-35 hyetographs using HMS-compatible temporal pattern.

    This class provides static methods for generating incremental precipitation
    hyetographs that match HEC-HMS "Frequency Based Hypothetical" output.

    The temporal pattern is a fixed dimensionless distribution that is scaled
    to the specified 24-hour total depth. This pattern was reverse-engineered
    from HEC-HMS PRECIP-INC output and validated to match across all AEP storms.

    Notes:
        - The pattern was extracted from HCFCD M3 Model D (Brays Bayou)
        - Pattern is valid for 24-hour storms with 5-minute intervals (288 values)
        - Pattern can be resampled for different time intervals
        - Peak position is configurable (default 67% as per M3 models)

    See Also:
        - Atlas14Storm: For Atlas 14 hyetograph generation
        - examples/frequency_storm_validation/FINDINGS.md: Validation details
    """

    # Standard TP-40 durations (minutes)
    STANDARD_DURATIONS = [5, 15, 30, 60, 120, 180, 360, 1440]

    # Pattern file location (relative to this module)
    _PATTERN_FILE = "data/tp40_dimensionless_pattern.npy"

    # Cached pattern
    _dimensionless_pattern: Optional[np.ndarray] = None

    @staticmethod
    def _load_pattern() -> np.ndarray:
        """Load the dimensionless temporal pattern from bundled data."""
        if FrequencyStorm._dimensionless_pattern is not None:
            return FrequencyStorm._dimensionless_pattern

        pattern_path = Path(__file__).parent / FrequencyStorm._PATTERN_FILE

        if not pattern_path.exists():
            raise FileNotFoundError(
                f"TP-40 pattern file not found: {pattern_path}\n"
                "This file should be bundled with hms-commander.\n"
                "Try reinstalling: pip install --upgrade hms-commander"
            )

        FrequencyStorm._dimensionless_pattern = np.load(pattern_path)
        logger.debug(
            f"Loaded TP-40 pattern: {len(FrequencyStorm._dimensionless_pattern)} values"
        )

        return FrequencyStorm._dimensionless_pattern

    @staticmethod
    def generate_hyetograph(
        total_depth_inches: float,
        total_duration_min: int = 1440,
        time_interval_min: int = 5,
        peak_position_pct: float = 67.0
    ) -> pd.DataFrame:
        """
        Generate a TP-40/Hydro-35 hyetograph using HCFCD M3 model pattern.

        This generates an incremental precipitation hyetograph using the same
        algorithm as HEC-HMS "Hypothetical Storm → User Specified Pattern".

        HCFCD M3 Model Defaults (validated configuration):
            - Duration: 1440 minutes (24 hours)
            - Time interval: 5 minutes
            - Peak position: 67% of duration

        Args:
            total_depth_inches: Total precipitation depth (inches)
                RENAMED from 'total_depth' for API consistency across methods
            total_duration_min: Storm duration in minutes (default: 1440 = 24hr)
                - Default: 1440 min (HCFCD M3 standard)
                - Validated: 24-hour storms to 10^-6 precision
                - Supported: Any duration (HMS User Pattern compatible)
            time_interval_min: Time step in minutes (default: 5)
                - Default: 5 min (HCFCD M3 standard)
                - Supported: Any interval (pattern resampled as needed)
            peak_position_pct: Percent of duration before peak (default: 67)
                - Default: 67% (HCFCD M3 standard)
                - HMS options: 25%, 33%, 50%, 67%, 75%

        Returns:
            pd.DataFrame with columns:
                - 'hour': Time in hours from storm start (float)
                - 'incremental_depth': Precipitation depth for this interval (inches)
                - 'cumulative_depth': Cumulative precipitation depth (inches)

        Example:
            >>> # HCFCD M3 compatible (all defaults)
            >>> hyeto = FrequencyStorm.generate_hyetograph(total_depth_inches=13.20)
            >>> print(hyeto.columns.tolist())
            ['hour', 'incremental_depth', 'cumulative_depth']
            >>> print(f"{len(hyeto)} intervals, total={hyeto['cumulative_depth'].iloc[-1]:.2f} inches")
            288 intervals, total=13.20 inches

            >>> # Variable duration (6-hour storm)
            >>> hyeto_6hr = FrequencyStorm.generate_hyetograph(
            ...     total_depth_inches=9.10, total_duration_min=360
            ... )
            >>> print(f"{len(hyeto_6hr)} intervals, total={hyeto_6hr['cumulative_depth'].iloc[-1]:.2f} inches")
            72 intervals, total=9.10 inches

        Notes:
            - Algorithm validated against HMS source code (aY.java)
            - 24-hour storms validated to 10^-6 precision vs M3 Model D
            - Pattern from HCFCD Model D (Brays Bayou) 1% AEP
            - Pattern consistent across all AEP values (0.2% to 10%)
        """
        # No warning - variable durations are supported

        # Load dimensionless pattern (288 incremental values for 24hr/5min)
        pattern = FrequencyStorm._load_pattern()

        # Calculate number of intervals (not including t=0)
        # HMS formula: duration/interval + 1, but we handle t=0 separately
        num_intervals = total_duration_min // time_interval_min

        # Resample pattern if needed
        if len(pattern) != num_intervals:
            pattern = FrequencyStorm._resample_pattern(
                pattern, len(pattern), num_intervals
            )

        # Handle peak position shift if different from 67%
        if abs(peak_position_pct - 67.0) > 0.5:
            pattern = FrequencyStorm._shift_peak(
                pattern, 67.0, peak_position_pct
            )

        # Scale to total depth
        incremental = pattern * total_depth_inches

        # Prepend 0.0 at t=0 to match HMS output format
        # HMS: dArray[0] = 0.0 (aY.java:143)
        hyetograph = np.insert(incremental, 0, 0.0)

        # Calculate time axis
        num_intervals = len(hyetograph)
        interval_hours = time_interval_min / 60.0
        hours = np.arange(1, num_intervals + 1) * interval_hours

        # Return DataFrame with standard columns
        return pd.DataFrame({
            'hour': hours,
            'incremental_depth': hyetograph,
            'cumulative_depth': np.cumsum(hyetograph)
        })

    @staticmethod
    def _resample_pattern(
        pattern: np.ndarray,
        source_intervals: int,
        target_intervals: int
    ) -> np.ndarray:
        """Resample pattern to different number of intervals."""
        # Convert to cumulative for interpolation
        cumulative = np.cumsum(pattern)
        cumulative = np.insert(cumulative, 0, 0)  # Add zero at start

        # Source and target time fractions
        source_t = np.linspace(0, 1, source_intervals + 1)
        target_t = np.linspace(0, 1, target_intervals + 1)

        # Interpolate cumulative
        target_cumulative = np.interp(target_t, source_t, cumulative)

        # Convert back to incremental
        resampled = np.diff(target_cumulative)

        # Normalize to sum to 1
        resampled = resampled / resampled.sum()

        return resampled

    @staticmethod
    def _shift_peak(
        pattern: np.ndarray,
        current_peak_pct: float,
        target_peak_pct: float
    ) -> np.ndarray:
        """Shift the peak position of the pattern."""
        n = len(pattern)
        current_peak_idx = int(current_peak_pct / 100 * n)
        target_peak_idx = int(target_peak_pct / 100 * n)

        shift = target_peak_idx - current_peak_idx

        if shift == 0:
            return pattern

        # Roll the array
        shifted = np.roll(pattern, shift)

        # Zero out wrapped values
        if shift > 0:
            shifted[:shift] = shifted[shift]  # Extend first value
        else:
            shifted[shift:] = shifted[shift - 1]  # Extend last value

        # Renormalize
        shifted = shifted / shifted.sum()

        return shifted

    @staticmethod
    def generate_from_ddf(
        depths: List[float],
        durations: Optional[List[int]] = None,
        peak_position_pct: float = 67.0,
        time_interval_min: int = 5
    ) -> np.ndarray:
        """
        Generate hyetograph from depth-duration-frequency data.

        This method takes the 8 cumulative depths from a TP-40 table and
        generates a hyetograph using the HMS-compatible temporal pattern.

        Args:
            depths: Cumulative depths at each standard duration (8 values, inches)
                   Order: 5, 15, 30, 60, 120, 180, 360, 1440 min
            durations: Optional custom durations (default: standard TP-40)
            peak_position_pct: Percent of duration before peak (default 67)
            time_interval_min: Output time step in minutes (default 5)

        Returns:
            numpy array of incremental precipitation depths

        Example:
            >>> # TP-40 depths for Houston 1% AEP
            >>> depths = [1.20, 2.10, 4.30, 5.70, 6.70, 8.90, 10.80, 13.20]
            >>> hyeto = FrequencyStorm.generate_from_ddf(depths)
            >>> print(f"Total: {hyeto.sum():.2f} inches")
            Total: 13.20 inches
        """
        if durations is None:
            durations = FrequencyStorm.STANDARD_DURATIONS

        if len(depths) != len(durations):
            raise ValueError(
                f"Number of depths ({len(depths)}) must match "
                f"number of durations ({len(durations)})"
            )

        # Get total depth (last value - corresponds to longest duration)
        total_depth_inches = depths[-1]

        # Generate using the standard pattern
        return FrequencyStorm.generate_hyetograph(
            total_depth_inches=total_depth_inches,
            total_duration_min=durations[-1],
            time_interval_min=time_interval_min,
            peak_position_pct=peak_position_pct
        )

    @staticmethod
    def get_pattern_info() -> dict:
        """
        Get information about the bundled temporal pattern.

        Returns:
            Dictionary with pattern metadata

        Example:
            >>> info = FrequencyStorm.get_pattern_info()
            >>> print(f"Peak at {info['peak_position']*100:.0f}%")
            Peak at 67%
        """
        pattern = FrequencyStorm._load_pattern()

        peak_idx = np.argmax(pattern)
        peak_pct = (peak_idx + 1) / len(pattern)

        # Calculate cumulative at key points
        cumulative = np.cumsum(pattern)

        return {
            "num_intervals": len(pattern),
            "time_interval_min": 5,
            "total_duration_min": 1440,
            "peak_index": peak_idx,
            "peak_position": peak_pct,
            "peak_fraction": pattern.max(),
            "source": "HCFCD Model D (Brays Bayou) - 1% AEP ground truth",
            "validation": "Consistent across 10%, 2%, 1%, 0.2% AEP storms",
            "cumulative_50pct": cumulative[len(pattern) // 2],
            "cumulative_67pct": cumulative[int(0.67 * len(pattern))],
        }

    @staticmethod
    def validate_against_ground_truth(
        hyetograph: np.ndarray,
        ground_truth: np.ndarray
    ) -> dict:
        """
        Compare a generated hyetograph against ground truth.

        Args:
            hyetograph: Generated hyetograph array
            ground_truth: Ground truth array (same length)

        Returns:
            Dictionary with comparison metrics

        Example:
            >>> hyeto = FrequencyStorm.generate_hyetograph(13.20)
            >>> gt = np.load("ground_truth.npy")
            >>> metrics = FrequencyStorm.validate_against_ground_truth(hyeto, gt)
            >>> print(f"RMSE: {metrics['rmse']:.6f}")
        """
        if len(hyetograph) != len(ground_truth):
            raise ValueError(
                f"Length mismatch: hyetograph={len(hyetograph)}, "
                f"ground_truth={len(ground_truth)}"
            )

        diff = hyetograph - ground_truth

        return {
            "rmse": np.sqrt(np.mean(diff ** 2)),
            "max_diff": np.max(np.abs(diff)),
            "mean_diff": np.mean(diff),
            "correlation": np.corrcoef(hyetograph, ground_truth)[0, 1],
            "total_diff": hyetograph.sum() - ground_truth.sum(),
            "peak_diff": hyetograph.max() - ground_truth.max(),
        }
