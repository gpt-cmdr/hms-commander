"""
ScsTypeStorm - SCS Type I, IA, II, III Hyetograph Generation for HEC-HMS

Generates precipitation hyetographs using NRCS SCS temporal distributions,
matching the algorithm used by HEC-HMS "Hypothetical Storm -> SCS" exactly.

SCS Storm Types:
    - Type I: Pacific Coast (Alaska, California, Oregon, Washington)
    - Type IA: Pacific Northwest coastal regions
    - Type II: Most of the continental US (standard)
    - Type III: Gulf of Mexico and Atlantic coastal areas

Algorithm:
    1. Load built-in SCS cumulative distribution (1441 values for 24hr @ 1min)
    2. Interpolate to requested time interval
    3. Convert cumulative to incremental depths
    4. Scale to total storm depth

CRITICAL: Duration is ALWAYS 24 hours (1440 minutes).
This is a HEC-HMS constraint - SCS storms are hardcoded to 24hr duration.
Use FrequencyStorm for variable duration storms.

Pattern Data:
    Extracted from HEC-HMS 4.13 source code (aH.java)
    Arrays contain 1441 cumulative values (0 to 1) at 1-minute intervals
    Bundled as .npy files in hms_commander/data/

Reference:
    - NRCS TR-55 (Technical Release 55)
    - HEC-HMS Technical Reference Manual

Example:
    >>> from hms_commander import ScsTypeStorm
    >>>
    >>> # Generate 100-year, 24-hour Type II storm
    >>> hyeto = ScsTypeStorm.generate_hyetograph(
    ...     total_depth_inches=10.0,
    ...     scs_type='II'
    ... )
    >>> print(f"Generated {len(hyeto)} time steps")
    >>> print(f"Total depth: {hyeto.sum():.6f} inches")
"""

from pathlib import Path
from typing import Dict, Optional, Union, List
import numpy as np

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


class ScsTypeStorm:
    """
    Static class for generating SCS Type I, IA, II, III hyetographs.

    Implements the same algorithm as HEC-HMS "Hypothetical Storm" with
    SCS distribution type.

    All methods are static - no instantiation required.

    Attributes:
        SCS_TYPES: List of valid SCS type identifiers
        DURATION_MINUTES: Fixed duration (1440 = 24 hours, HMS constraint)

    Example:
        >>> from hms_commander import ScsTypeStorm
        >>>
        >>> # Generate Type II storm with 10 inches total depth
        >>> hyeto = ScsTypeStorm.generate_hyetograph(
        ...     total_depth_inches=10.0,
        ...     scs_type='II',
        ...     time_interval_min=60  # 1-hour intervals
        ... )
        >>> print(f"Total: {hyeto.sum():.6f} inches")
        >>> print(f"Peak: {hyeto.max():.3f} inches")
    """

    # Valid SCS storm types
    SCS_TYPES = ['I', 'IA', 'II', 'III']

    # Fixed 24-hour duration (HMS constraint)
    DURATION_MINUTES = 1440

    # Pattern file locations (relative to this module)
    _PATTERN_FILES = {
        'I': 'data/scs_type_i.npy',
        'IA': 'data/scs_type_ia.npy',
        'II': 'data/scs_type_ii.npy',
        'III': 'data/scs_type_iii.npy'
    }

    # Peak positions from TR-55 (approximate % of duration)
    # These are verified against HMS source code extraction
    PEAK_POSITIONS = {
        'I': 0.41,    # ~41% of duration (coastal Pacific)
        'IA': 0.32,   # ~32% of duration (Pacific Northwest)
        'II': 0.50,   # ~50% of duration (most of US)
        'III': 0.50   # ~50% of duration (Gulf/Atlantic coastal)
    }

    # Cached patterns
    _pattern_cache: Dict[str, np.ndarray] = {}

    @staticmethod
    def _load_pattern(scs_type: str) -> np.ndarray:
        """
        Load SCS cumulative distribution pattern from bundled data.

        Args:
            scs_type: SCS type ('I', 'IA', 'II', or 'III')

        Returns:
            numpy array of cumulative percentages (0 to 1, 1441 values)

        Raises:
            ValueError: If scs_type is not valid
            FileNotFoundError: If pattern file is missing
        """
        scs_type = scs_type.upper()

        if scs_type not in ScsTypeStorm.SCS_TYPES:
            raise ValueError(
                f"Invalid SCS type: '{scs_type}'. "
                f"Valid types: {ScsTypeStorm.SCS_TYPES}"
            )

        # Check cache
        if scs_type in ScsTypeStorm._pattern_cache:
            return ScsTypeStorm._pattern_cache[scs_type]

        # Load pattern file
        pattern_file = Path(__file__).parent / ScsTypeStorm._PATTERN_FILES[scs_type]

        if not pattern_file.exists():
            raise FileNotFoundError(
                f"SCS pattern file not found: {pattern_file}\n"
                "This file should be bundled with hms-commander.\n"
                "Try reinstalling: pip install --upgrade hms-commander"
            )

        pattern = np.load(pattern_file)
        logger.debug(f"Loaded SCS Type {scs_type} pattern: {len(pattern)} values")

        # Cache for future use
        ScsTypeStorm._pattern_cache[scs_type] = pattern

        return pattern

    @staticmethod
    @log_call
    def generate_hyetograph(
        total_depth_inches: float,
        scs_type: str = 'II',
        time_interval_min: int = 60
    ) -> np.ndarray:
        """
        Generate SCS Type hyetograph (incremental precipitation depths).

        This matches HEC-HMS "Hypothetical Storm -> SCS Type" exactly.
        Duration is ALWAYS 24 hours (HEC-HMS constraint).

        Args:
            total_depth_inches: Total storm precipitation depth (inches)
            scs_type: SCS distribution type ('I', 'IA', 'II', or 'III')
                - Type I: Pacific Coast (AK, CA, OR, WA) - peak at ~41%
                - Type IA: Pacific Northwest coastal - peak at ~32%
                - Type II: Most of continental US - peak at ~50%
                - Type III: Gulf/Atlantic coastal - peak at ~50%
            time_interval_min: Output time step in minutes (default: 60)
                Common values: 5, 10, 15, 30, 60 minutes
                Note: Storm is ALWAYS 24 hours (1440 min) regardless of interval

        Returns:
            numpy array of incremental precipitation depths (inches)
            Length = 1440 / time_interval_min + 1 (includes t=0)

        Raises:
            ValueError: If scs_type is not valid or interval invalid

        Example:
            >>> # Type II storm (most common)
            >>> hyeto = ScsTypeStorm.generate_hyetograph(
            ...     total_depth_inches=10.0,
            ...     scs_type='II',
            ...     time_interval_min=60
            ... )
            >>> print(f"Time steps: {len(hyeto)}")  # 25 (24 hours + t=0)
            >>> print(f"Total: {hyeto.sum():.6f} inches")  # 10.000000
            >>> print(f"Peak: {hyeto.max():.3f} inches")  # ~4.1 inches

        Note:
            Duration is ALWAYS 24 hours (hardcoded in HMS).
            Use FrequencyStorm.generate_hyetograph() for variable durations.
        """
        # Validate inputs
        scs_type = scs_type.upper()
        if scs_type not in ScsTypeStorm.SCS_TYPES:
            raise ValueError(
                f"Invalid SCS type: '{scs_type}'. "
                f"Valid types: {ScsTypeStorm.SCS_TYPES}"
            )

        if time_interval_min <= 0:
            raise ValueError(f"Time interval must be positive: {time_interval_min}")

        if ScsTypeStorm.DURATION_MINUTES % time_interval_min != 0:
            raise ValueError(
                f"Time interval {time_interval_min} min does not evenly divide "
                f"24-hour duration (1440 min). "
                f"Common intervals: 5, 10, 15, 30, 60 minutes."
            )

        # Load cumulative pattern (1441 values at 1-minute intervals)
        cumulative_1min = ScsTypeStorm._load_pattern(scs_type)

        # Resample to requested interval
        num_output_steps = ScsTypeStorm.DURATION_MINUTES // time_interval_min + 1
        output_times = np.linspace(0, 1440, num_output_steps)
        source_times = np.linspace(0, 1440, 1441)

        cumulative_resampled = np.interp(output_times, source_times, cumulative_1min)

        # Scale to total depth
        cumulative_depth = cumulative_resampled * total_depth_inches

        # Convert to incremental (prepend 0 at t=0)
        # HMS: dArray[0] = 0.0
        incremental = np.diff(cumulative_depth, prepend=0.0)

        # Verify depth conservation
        total_check = incremental.sum()
        depth_error = abs(total_check - total_depth_inches)

        if depth_error > 1e-6:
            logger.warning(
                f"Depth conservation warning: "
                f"Expected {total_depth_inches:.6f}, got {total_check:.6f} "
                f"(error: {depth_error:.6e} inches)"
            )

        logger.info(
            f"Generated SCS Type {scs_type} hyetograph: "
            f"{len(incremental)} intervals, {total_check:.6f} inches total, "
            f"peak {incremental.max():.3f} inches"
        )

        return incremental

    @staticmethod
    @log_call
    def generate_all_types(
        total_depth_inches: float,
        time_interval_min: int = 60
    ) -> Dict[str, np.ndarray]:
        """
        Generate hyetographs for all 4 SCS types.

        Useful for comparison and sensitivity analysis.

        Args:
            total_depth_inches: Total storm precipitation depth (inches)
            time_interval_min: Output time step in minutes (default: 60)

        Returns:
            Dictionary mapping SCS type to numpy array of incremental depths

        Example:
            >>> storms = ScsTypeStorm.generate_all_types(10.0)
            >>> for scs_type, hyeto in storms.items():
            ...     print(f"Type {scs_type}: peak={hyeto.max():.2f} inches")
        """
        results = {}
        for scs_type in ScsTypeStorm.SCS_TYPES:
            results[scs_type] = ScsTypeStorm.generate_hyetograph(
                total_depth_inches=total_depth_inches,
                scs_type=scs_type,
                time_interval_min=time_interval_min
            )
        return results

    @staticmethod
    def get_peak_position(scs_type: str) -> float:
        """
        Get expected peak position as fraction of storm duration.

        Args:
            scs_type: SCS type ('I', 'IA', 'II', or 'III')

        Returns:
            Peak position as fraction (0.0 to 1.0)
            e.g., 0.5 = 50% of duration = 12 hours into 24-hour storm

        Example:
            >>> pos = ScsTypeStorm.get_peak_position('II')
            >>> print(f"Type II peak at {pos*100:.0f}% = {pos*24:.1f} hours")
            Type II peak at 50% = 12.0 hours
        """
        scs_type = scs_type.upper()
        if scs_type not in ScsTypeStorm.SCS_TYPES:
            raise ValueError(
                f"Invalid SCS type: '{scs_type}'. "
                f"Valid types: {ScsTypeStorm.SCS_TYPES}"
            )
        return ScsTypeStorm.PEAK_POSITIONS[scs_type]

    @staticmethod
    def get_pattern_info(scs_type: str = 'II') -> dict:
        """
        Get information about SCS pattern.

        Args:
            scs_type: SCS type to query

        Returns:
            Dictionary with pattern metadata

        Example:
            >>> info = ScsTypeStorm.get_pattern_info('II')
            >>> print(f"Peak at {info['peak_position']*100:.0f}% of duration")
        """
        scs_type = scs_type.upper()
        pattern = ScsTypeStorm._load_pattern(scs_type)

        # Calculate incremental to find peak
        incremental = np.diff(pattern)
        peak_idx = np.argmax(incremental)
        peak_position = (peak_idx + 1) / len(incremental)

        return {
            'scs_type': scs_type,
            'num_values': len(pattern),
            'duration_minutes': ScsTypeStorm.DURATION_MINUTES,
            'duration_hours': ScsTypeStorm.DURATION_MINUTES / 60,
            'peak_index': peak_idx,
            'peak_position': peak_position,
            'peak_position_hours': peak_position * 24,
            'expected_peak_position': ScsTypeStorm.PEAK_POSITIONS[scs_type],
            'source': 'HEC-HMS 4.13 source code (aH.java)',
            'reference': 'NRCS TR-55'
        }

    @staticmethod
    def validate_against_reference(
        hyetograph: np.ndarray,
        reference: np.ndarray
    ) -> dict:
        """
        Compare generated hyetograph against reference (e.g., HMS output).

        Args:
            hyetograph: Generated hyetograph array
            reference: Reference array (e.g., from HMS DSS output)

        Returns:
            Dictionary with comparison metrics

        Example:
            >>> hyeto = ScsTypeStorm.generate_hyetograph(10.0, 'II')
            >>> hms_ref = np.load("hms_type_ii_reference.npy")
            >>> metrics = ScsTypeStorm.validate_against_reference(hyeto, hms_ref)
            >>> print(f"RMSE: {metrics['rmse']:.6f} inches")
        """
        if len(hyetograph) != len(reference):
            raise ValueError(
                f"Length mismatch: hyetograph={len(hyetograph)}, "
                f"reference={len(reference)}"
            )

        diff = hyetograph - reference

        return {
            'rmse': np.sqrt(np.mean(diff ** 2)),
            'max_abs_diff': np.max(np.abs(diff)),
            'mean_diff': np.mean(diff),
            'correlation': np.corrcoef(hyetograph, reference)[0, 1],
            'total_depth_diff': hyetograph.sum() - reference.sum(),
            'peak_diff': hyetograph.max() - reference.max(),
            'pass_threshold_001': np.sqrt(np.mean(diff ** 2)) < 0.001
        }

    @staticmethod
    def list_types() -> List[str]:
        """
        List all available SCS storm types.

        Returns:
            List of SCS type identifiers
        """
        return ScsTypeStorm.SCS_TYPES.copy()
