"""
Atlas14Converter - Convert Atlas 14 data to HMS format

Generates cumulative depth arrays for HMS frequency-based hypothetical storms
using the Alternating Block Method for hyetograph generation.

Based on ras-commander hyetograph generation logic.
"""

import logging
from typing import Dict, List, Optional
import numpy as np

logger = logging.getLogger(__name__)


class Atlas14Converter:
    """
    Convert Atlas 14 precipitation data to HMS frequency storm format.

    HMS frequency-based hypothetical storms require cumulative precipitation
    depths at specific time intervals. This class generates those depth arrays
    from Atlas 14 point estimates.

    Example:
        >>> converter = Atlas14Converter()
        >>> depths = converter.generate_depth_values(
        ...     atlas14_data=data,
        ...     aep='1%',
        ...     total_duration=1440,  # 24 hours
        ...     time_interval=60,     # 1-hour intervals
        ...     peak_position=50      # Peak at 50% (centered)
        ... )
        >>> print(f"Generated {len(depths)} cumulative depth values")
    """

    def __init__(self):
        """Initialize Atlas 14 converter."""
        pass

    def generate_depth_values(
        self,
        atlas14_data: Dict,
        aep: str,
        total_duration: int,
        time_interval: int,
        peak_position: int = 50,
        method: str = 'alternating_block'
    ) -> List[float]:
        """
        Generate cumulative depth values for HMS frequency storm.

        Args:
            atlas14_data: Atlas 14 data dictionary from downloader
            aep: Annual exceedance probability (e.g., '1%', '2%', '10%')
            total_duration: Total storm duration in minutes
            time_interval: Time interval in minutes
            peak_position: Percent of duration before peak (0-100)
            method: Hyetograph generation method ('alternating_block')

        Returns:
            List of cumulative precipitation depths

        Raises:
            ValueError: If AEP not found or duration parameters invalid

        Example:
            >>> # Generate 24-hour storm at 1-hour intervals
            >>> depths = converter.generate_depth_values(
            ...     atlas14_data,
            ...     aep='1%',
            ...     total_duration=1440,  # 24 hours
            ...     time_interval=60,     # 1-hour intervals
            ...     peak_position=50      # Peak in middle
            ... )
            >>> # Result: [0.45, 0.92, 1.45, ..., 14.5] (24 values)
        """
        # Validate inputs
        if aep not in atlas14_data['depths']:
            available = list(atlas14_data['depths'].keys())
            raise ValueError(f"AEP '{aep}' not found. Available: {available}")

        if total_duration % time_interval != 0:
            raise ValueError(
                f"Total duration ({total_duration}) must be divisible by "
                f"time interval ({time_interval})"
            )

        if not (0 <= peak_position <= 100):
            raise ValueError(f"Peak position must be 0-100, got {peak_position}")

        num_intervals = total_duration // time_interval

        logger.info(f"Generating depths for {aep} AEP, {total_duration}-min storm")
        logger.debug(f"Intervals: {num_intervals}, Time step: {time_interval} min")

        # Get Atlas 14 depths for this AEP
        aep_depths = atlas14_data['depths'][aep]

        # Generate incremental depths using alternating block method
        if method == 'alternating_block':
            cumulative_depths = self._alternating_block_method(
                aep_depths=aep_depths,
                total_duration=total_duration,
                time_interval=time_interval,
                peak_position=peak_position
            )
        else:
            raise ValueError(f"Unknown method: {method}")

        logger.info(f"Generated {len(cumulative_depths)} cumulative depth values")
        logger.debug(f"Total depth: {cumulative_depths[-1]:.2f} {atlas14_data['units']}")

        return cumulative_depths

    def _alternating_block_method(
        self,
        aep_depths: Dict[str, float],
        total_duration: int,
        time_interval: int,
        peak_position: int
    ) -> List[float]:
        """
        Generate cumulative depths using Alternating Block Method.

        The Alternating Block Method is the standard approach for
        creating design storm hyetographs from intensity-duration-frequency
        (IDF) data. It produces realistic storm patterns with the peak
        intensity near the center of the storm.

        Process:
        1. Extract intensity values for durations from time_interval to total_duration
        2. Calculate incremental depths for each duration
        3. Rank incremental depths from highest to lowest
        4. Place highest depth at peak_position
        5. Alternate remaining depths left/right of peak

        Args:
            aep_depths: Dictionary of Atlas 14 depths by duration
            total_duration: Total storm duration in minutes
            time_interval: Time interval in minutes
            peak_position: Percent of duration before peak (0-100)

        Returns:
            List of cumulative precipitation depths

        Reference:
            Chow, V.T., Maidment, D.R., Mays, L.W. (1988). Applied Hydrology.
            McGraw-Hill. Section 14.4 "Design Storms".
        """
        num_intervals = total_duration // time_interval

        # Step 1: Get cumulative depths for each duration from Atlas 14
        durations = []
        cumulative_depths_atlas14 = []

        for i in range(1, num_intervals + 1):
            duration_min = i * time_interval

            # Try to find Atlas 14 depth for this duration
            depth = None

            # First try exact match by minutes
            if duration_min in aep_depths:
                depth = aep_depths[duration_min]

            # Try labeled durations (e.g., "24-hr")
            else:
                if duration_min < 60:
                    label = f"{duration_min}-min"
                elif duration_min == 60:
                    label = "1-hr"
                elif duration_min < 1440:
                    hours = duration_min // 60
                    label = f"{hours}-hr"
                elif duration_min == 1440:
                    label = "24-hr"
                else:
                    days = duration_min // 1440
                    label = f"{days}-day"

                depth = aep_depths.get(label)

            # If still not found, try interpolation
            if depth is None:
                depth = self._interpolate_depth(
                    aep_depths,
                    duration_min
                )

            if depth is None:
                logger.warning(f"No data for {duration_min}-min duration, using extrapolation")
                # Simple linear extrapolation from longest available
                max_duration = max([d for d in aep_depths.keys() if isinstance(d, int)])
                max_depth = aep_depths[max_duration]
                depth = max_depth * (duration_min / max_duration)

            durations.append(duration_min)
            cumulative_depths_atlas14.append(depth)

        # Step 2: Calculate incremental depths
        incremental_depths = [cumulative_depths_atlas14[0]]
        for i in range(1, len(cumulative_depths_atlas14)):
            incremental = cumulative_depths_atlas14[i] - cumulative_depths_atlas14[i-1]
            incremental_depths.append(incremental)

        # Step 3: Rank incremental depths (highest to lowest)
        ranked_depths = sorted(enumerate(incremental_depths), key=lambda x: x[1], reverse=True)

        # Step 4: Place depths using alternating block pattern
        # Peak position determines where highest intensity goes
        peak_index = int((peak_position / 100.0) * num_intervals)

        # Initialize pattern array
        pattern = [0.0] * num_intervals

        # Place highest depth at peak
        pattern[peak_index] = ranked_depths[0][1]

        # Alternate remaining depths left and right of peak
        left_index = peak_index - 1
        right_index = peak_index + 1

        for i in range(1, len(ranked_depths)):
            depth_value = ranked_depths[i][1]

            # Alternate left and right
            if i % 2 == 1:  # Odd - go left
                if left_index >= 0:
                    pattern[left_index] = depth_value
                    left_index -= 1
                elif right_index < num_intervals:
                    pattern[right_index] = depth_value
                    right_index += 1
            else:  # Even - go right
                if right_index < num_intervals:
                    pattern[right_index] = depth_value
                    right_index += 1
                elif left_index >= 0:
                    pattern[left_index] = depth_value
                    left_index -= 1

        # Step 5: Convert incremental to cumulative
        cumulative_pattern = []
        cumulative = 0.0
        for depth in pattern:
            cumulative += depth
            cumulative_pattern.append(cumulative)

        return cumulative_pattern

    def _interpolate_depth(
        self,
        aep_depths: Dict,
        target_duration: int
    ) -> Optional[float]:
        """
        Interpolate depth for a duration not directly available.

        Uses linear interpolation in log-log space (standard for IDF curves).

        Args:
            aep_depths: Dictionary of depths by duration
            target_duration: Target duration in minutes

        Returns:
            Interpolated depth or None if can't interpolate
        """
        # Get numeric durations
        numeric_durations = [d for d in aep_depths.keys() if isinstance(d, int)]

        if not numeric_durations:
            return None

        numeric_durations = sorted(numeric_durations)

        # Find bracketing durations
        lower_dur = None
        upper_dur = None

        for dur in numeric_durations:
            if dur < target_duration:
                lower_dur = dur
            elif dur > target_duration:
                upper_dur = dur
                break

        # Can't interpolate if we don't have brackets
        if lower_dur is None or upper_dur is None:
            return None

        # Linear interpolation in log-log space
        lower_depth = aep_depths[lower_dur]
        upper_depth = aep_depths[upper_dur]

        # log(depth) = log(lower_depth) + slope * (log(duration) - log(lower_dur))
        slope = (np.log(upper_depth) - np.log(lower_depth)) / (np.log(upper_dur) - np.log(lower_dur))
        log_depth = np.log(lower_depth) + slope * (np.log(target_duration) - np.log(lower_dur))
        depth = np.exp(log_depth)

        logger.debug(f"Interpolated {target_duration} min: {depth:.3f} "
                     f"(between {lower_dur} min: {lower_depth:.3f} and {upper_dur} min: {upper_depth:.3f})")

        return float(depth)

    def validate_depths(
        self,
        depths: List[float],
        atlas14_data: Dict,
        aep: str,
        total_duration: int,
        tolerance: float = 0.01
    ) -> bool:
        """
        Validate generated depths against Atlas 14 total.

        The final cumulative depth should match the Atlas 14 total depth
        for the storm duration.

        Args:
            depths: Generated cumulative depth list
            atlas14_data: Original Atlas 14 data
            aep: AEP label
            total_duration: Total duration in minutes
            tolerance: Allowable relative error (default 1%)

        Returns:
            True if validation passes

        Raises:
            ValueError: If validation fails
        """
        if not depths:
            raise ValueError("Empty depths list")

        # Get final cumulative depth
        final_depth = depths[-1]

        # Get expected Atlas 14 depth for total duration
        aep_depths = atlas14_data['depths'][aep]
        expected_depth = None

        # Try to find expected depth
        if total_duration in aep_depths:
            expected_depth = aep_depths[total_duration]
        else:
            # Try labeled duration
            if total_duration == 1440:
                expected_depth = aep_depths.get('24-hr')
            elif total_duration == 720:
                expected_depth = aep_depths.get('12-hr')
            # Add more as needed

        if expected_depth is None:
            logger.warning(f"Could not find Atlas 14 depth for {total_duration} min")
            return True  # Can't validate, assume OK

        # Check relative error
        relative_error = abs(final_depth - expected_depth) / expected_depth

        if relative_error > tolerance:
            raise ValueError(
                f"Generated depth {final_depth:.2f} differs from "
                f"Atlas 14 total {expected_depth:.2f} by {relative_error*100:.1f}% "
                f"(tolerance: {tolerance*100:.1f}%)"
            )

        logger.info(f"Validation passed: {final_depth:.2f} vs {expected_depth:.2f} "
                    f"({relative_error*100:.2f}% error)")

        return True
