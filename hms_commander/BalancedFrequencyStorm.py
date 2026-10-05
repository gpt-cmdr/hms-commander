"""
BalancedFrequencyStorm - HEC-HMS "Frequency Storm" (balanced / nested) hyetographs.

This module reproduces the HEC-HMS *Frequency Storm* meteorologic method
(``Precipitation Method: Frequency Based Hypothetical`` in the ``.met`` file) so
that a hyetograph can be built from a depth-duration-frequency (DDF) table
outside of HMS and compared to HMS output.

It is distinct from :class:`hms_commander.FrequencyStorm`, which scales a fixed
HCFCD/Houston temporal pattern to a single total depth. The two classes are
kept separate so that existing ``FrequencyStorm`` behavior is unchanged.

Algorithm (HEC-HMS Technical Reference Manual, section 5.2.6, verified against
HEC-HMS 4.13 output; see ``tests/fixtures/hms_frequency_storm``):

1. Depths for the standard durations (5 min ... 10 days) are supplied for one
   exceedance probability.  Per the TRM, 10-min and 30-min depths are estimated
   with the HYDRO-35 relationships ``P10 = 0.59*P15 + 0.41*P5`` and
   ``P30 = 0.49*P60 + 0.51*P15``.  In HMS 4.13 this only happens for legacy
   (3.x-format) met files without 10/30-min entries; a native 4.13 file uses the
   supplied durations as given and does NOT augment blanks, so
   ``augment=False`` is the default here (``augment=True`` reproduces legacy).
2. Depths are reduced for storm area (``storm_area_sqmi``) with the HMS
   TP-40/TP-49 depth-area curves (see :meth:`areal_reduction_factor`).
3. Optional partial-duration to annual-duration conversion with the Table 11
   factors (0.88 / 0.96 / 0.99 for 50 / 20 / 10 percent exceedance).
4. Cumulative depth is interpolated at every multiple of the time interval,
   linearly in log(duration)-log(depth) space; successive differences give the
   incremental blocks.
5. Blocks are arranged with the alternating block method: the first nested
   block is placed at the peak-intensity position and the remaining blocks
   alternate before/after it in duration order.  This follows observed HMS
   4.13 behavior for non-monotone increments; it differs from the TRM wording
   that describes descending order.

Time Axis:
    Output DataFrames follow the repository convention (a t=0 zero-sentinel row
    followed by interval-end rows), see ``_hyetograph.build_hyetograph_frame``.

Example:
    >>> from hms_commander import BalancedFrequencyStorm
    >>> depths = {5: 1.17, 10: 1.88, 15: 2.32, 30: 3.20, 60: 4.27, 120: 5.77,
    ...           180: 6.82, 360: 8.63, 720: 10.3, 1440: 12.1}
    >>> hyeto = BalancedFrequencyStorm.generate_hyetograph(
    ...     depths, total_duration_min=1440, time_interval_min=15,
    ...     peak_position_pct=50)
    >>> round(hyeto["incremental_depth"].sum(), 6)
    12.1
"""

from __future__ import annotations

import math
from typing import Dict, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd

from .Decorators import log_call
from .LoggingConfig import get_logger
from ._hyetograph import build_hyetograph_frame

logger = get_logger(__name__)


class BalancedFrequencyStorm:
    """HEC-HMS Frequency Storm (balanced hyetograph) generator.

    All methods are static.
    """

    #: Standard HMS 4.13 Frequency Storm durations (minutes).
    STANDARD_DURATIONS_MIN = [
        5,
        10,
        15,
        30,
        60,
        120,
        180,
        360,
        720,
        1440,
        2880,
        4320,
        5760,
        10080,
        14400,
    ]

    #: Intensity (peak) positions offered by HMS, percent of storm duration.
    PEAK_POSITIONS_PCT = (25, 33, 50, 67, 75)

    #: HMS Table 11: partial-duration -> annual-duration reduction factors,
    #: keyed by exceedance probability in percent.
    PARTIAL_TO_ANNUAL_FACTORS = {50: 0.88, 20: 0.96, 10: 0.99}

    #: Depth-area reduction curve (TP-40/TP-49 option) as implemented by HMS 4.13:
    #: ``RF(d, A) = RF_inf(d) + (1 - RF_inf(d)) * exp(-AREA_DECAY * A)`` with A in
    #: square miles.  ``RF_inf`` is tabulated below at table durations (minutes)
    #: and interpolated linearly in ln(duration) vs ln(1 - RF_inf) between them.
    #: Values were derived empirically from HEC-HMS 4.13 output (the formula is
    #: not published).  HMS 4.13 applies the 30-min value below 30 min, despite
    #: the TRM wording that says no adjustment is made below 30 min.
    AREA_DECAY = 0.015
    _RF_INF_TABLE_MIN = (30, 60, 180, 360, 1440, 2880, 5760, 10080, 14400)
    _RF_INF_TABLE = (0.52, 0.65, 0.78, 0.83, 0.91, 0.932, 0.945, 0.951, 0.956)

    # ------------------------------------------------------------------
    # Pieces of the algorithm (public so they can be tested individually)
    # ------------------------------------------------------------------

    @staticmethod
    def areal_reduction_factor(duration_min: float, storm_area_sqmi: float) -> float:
        """HMS TP-40/TP-49 depth-area reduction factor (1.0 for a point storm).

        HMS 4.13 uses the 30-minute factor for shorter durations; this differs
        from the Technical Reference Manual wording.  The TP-40/TP-49
        depth-area curves are documented through 400 square miles.
        """
        if storm_area_sqmi <= 0:
            return 1.0
        durs = BalancedFrequencyStorm._RF_INF_TABLE_MIN
        loss = [1.0 - v for v in BalancedFrequencyStorm._RF_INF_TABLE]
        d = min(max(float(duration_min), durs[0]), durs[-1])
        log_loss = float(np.interp(math.log(d), np.log(durs), np.log(loss)))
        l_inf = math.exp(log_loss)
        return 1.0 - l_inf * (
            1.0 - math.exp(-BalancedFrequencyStorm.AREA_DECAY * storm_area_sqmi)
        )

    @staticmethod
    def augment_depths(depths: Mapping[int, float]) -> Dict[int, float]:
        """Add HYDRO-35 estimated 10-min and 30-min depths when they are absent."""
        out = _validate_depth_table(depths)
        if 10 not in out and 5 in out and 15 in out:
            out[10] = 0.59 * out[15] + 0.41 * out[5]
        if 30 not in out and 15 in out and 60 in out:
            out[30] = 0.49 * out[60] + 0.51 * out[15]
        return dict(sorted(out.items()))

    @staticmethod
    def cumulative_depths(
        depths: Mapping[int, float],
        total_duration_min: int,
        time_interval_min: int,
    ) -> np.ndarray:
        """Log-log interpolated cumulative depth at each interval end time."""
        durs = np.array(sorted(depths), dtype=float)
        vals = np.array([depths[int(d)] for d in durs], dtype=float)
        if total_duration_min > durs[-1] or total_duration_min < durs[0]:
            raise ValueError(
                f"total_duration_min={total_duration_min} is outside the supplied "
                f"depth durations ({int(durs[0])}-{int(durs[-1])} min)"
            )
        t = np.arange(
            time_interval_min, total_duration_min + 1e-9, time_interval_min, dtype=float
        )
        # log-log linear interpolation inside the table
        return np.exp(np.interp(np.log(t), np.log(durs), np.log(vals)))

    @staticmethod
    def alternating_blocks(
        increments: np.ndarray, peak_position_pct: float = 50.0
    ) -> np.ndarray:
        """Arrange incremental blocks with the HMS alternating block method.

        ``increments`` must be in *time order of the nested storm*, i.e. block k
        is ``depth(k*dt) - depth((k-1)*dt)``. HMS places them in that order
        (it does not re-sort by value), which matters only where the
        interpolated increments are not monotone (at changes of slope between
        depth-duration table knots).  The non-monotone HMS 4.13 fixtures support
        this behavior; it differs from the Technical Reference Manual's
        descending-order wording.
        """
        order = np.asarray(increments, dtype=float)
        n = len(order)
        peak = BalancedFrequencyStorm._peak_index(n, peak_position_pct)
        out = np.zeros(n)
        out[peak] = order[0]
        lo, hi = peak - 1, peak + 1
        place_before = True
        for value in order[1:]:
            if place_before:
                if lo >= 0:
                    out[lo] = value
                    lo -= 1
                else:
                    out[hi] = value
                    hi += 1
            else:
                if hi < n:
                    out[hi] = value
                    hi += 1
                else:
                    out[lo] = value
                    lo -= 1
            place_before = not place_before
        return out

    @staticmethod
    def _peak_index(n: int, peak_position_pct: float) -> int:
        """0-based index of the peak block among ``n`` blocks."""
        return min(max(int(math.floor(peak_position_pct / 100.0 * n + 1e-9)), 0), n - 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    @log_call
    def generate_hyetograph(
        depths: Union[Mapping[int, float], Sequence[float]],
        total_duration_min: int = 1440,
        time_interval_min: int = 15,
        peak_position_pct: float = 50.0,
        storm_area_sqmi: float = 0.0,
        exceedance_pct: Optional[float] = None,
        convert_partial_to_annual: bool = False,
        durations_min: Optional[Sequence[int]] = None,
        augment: bool = False,
        area_reduction: str = "tp40_tp49",
    ) -> pd.DataFrame:
        """
        Generate an HMS Frequency Storm hyetograph.

        Args:
            depths: Point depths (inches) by duration. Either a mapping
                ``{duration_min: depth}`` or a sequence aligned with
                ``durations_min`` (default: the 15 standard HMS durations).
                Every supplied depth must be finite and positive; omit an
                unavailable duration rather than supplying ``None`` or NaN.
            total_duration_min: Storm duration (minutes); must have a depth.
            time_interval_min: Computation/intensity interval (minutes); must
                have a depth.
            peak_position_pct: Percent of the storm before the peak block
                (25, 33, 50, 67 or 75 in HMS).
            storm_area_sqmi: Storm area for depth-area reduction (0 = point).
                A warning is logged above 400 sq mi, the documented extent of
                the TP-40/TP-49 depth-area curves.
            exceedance_pct: Exceedance probability in percent (50, 20, 10 are
                the only values for which HMS applies a conversion factor).
            convert_partial_to_annual: Apply the HMS partial -> annual factor
                (HMS "Convert to Annual Series: Yes", input assumed partial).
            durations_min: Durations for a sequence ``depths``.
            area_reduction: ``"tp40_tp49"`` (HMS TP-40/TP-49 curves, default) or
                ``"none"`` (HMS "Depth-Area Reduction Method: None"). HMS user-specified
                area-reduction functions are not implemented.
            augment: Estimate missing 10-min/30-min depths with HYDRO-35 (TRM
                5.2.6.1). Default False: HEC-HMS 4.13 does not augment when it reads
                a native 4.13 ``.met`` file with blank 10-min/30-min rows; it does
                augment when it reads a legacy (3.x) file that has no 10/30-min
                entries. Use ``augment=True`` to reproduce the latter.

        Returns:
            DataFrame with ``hour``, ``incremental_depth`` and
            ``cumulative_depth`` (t=0 sentinel row first).

        Notes:
            Cumulative depths are interpolated linearly in log(duration)-
            log(depth) space between supplied durations.  Omitting intermediate
            durations is therefore supported by the implementation, but is only
            partly validated against HMS 4.13; the selected interval and total
            duration must still be supplied explicitly.

            Blocks follow the observed HMS 4.13 duration order.  This differs
            from the Technical Reference Manual's descending-order wording; the
            HMS re-sort setting is not exposed by this API.
        """
        if peak_position_pct not in BalancedFrequencyStorm.PEAK_POSITIONS_PCT:
            logger.warning(
                f"peak_position_pct={peak_position_pct} is not one of the HMS options "
                f"{BalancedFrequencyStorm.PEAK_POSITIONS_PCT}"
            )
        if not isinstance(depths, Mapping):
            durs = list(
                BalancedFrequencyStorm.STANDARD_DURATIONS_MIN
                if durations_min is None
                else durations_min
            )
            values = list(depths)
            if len(values) != len(durs):
                raise ValueError(
                    "Sequence depths and durations_min must have equal lengths"
                )
            if len(set(durs)) != len(durs):
                raise ValueError("durations_min must not contain duplicates")
            depths = dict(zip(durs, values))
        table = (
            BalancedFrequencyStorm.augment_depths(depths)
            if augment
            else _validate_depth_table(depths)
        )
        for needed, label in (
            (total_duration_min, "storm duration"),
            (time_interval_min, "time interval"),
        ):
            if int(needed) not in table:
                raise ValueError(f"No depth supplied for the {label} ({needed} min)")
        if total_duration_min <= time_interval_min:
            raise ValueError("Storm duration must be longer than the time interval")
        if total_duration_min % time_interval_min:
            raise ValueError("Storm duration must be a multiple of the time interval")

        # Only durations from the intensity duration to the storm duration are
        # used by HMS;
        # shorter knots are irrelevant, longer knots are not reached.
        method = str(area_reduction).lower().replace("-", "_").replace("/", "_")
        if method not in ("tp40_tp49", "none"):
            raise ValueError("area_reduction must be 'tp40_tp49' or 'none'")
        area = float(storm_area_sqmi) if method == "tp40_tp49" else 0.0
        if area > 400:
            logger.warning(
                "storm_area_sqmi=%s exceeds 400 sq mi, the documented extent of "
                "the TP-40/TP-49 depth-area curves",
                area,
            )
        reduced = {
            d: v * BalancedFrequencyStorm.areal_reduction_factor(d, area)
            for d, v in table.items()
        }
        if convert_partial_to_annual and exceedance_pct is None:
            raise ValueError(
                "exceedance_pct is required when convert_partial_to_annual=True"
            )
        if convert_partial_to_annual:
            factor = (
                BalancedFrequencyStorm.PARTIAL_TO_ANNUAL_FACTORS.get(
                    int(exceedance_pct)
                )
                if float(exceedance_pct).is_integer()
                else None
            )
            if factor is not None:
                reduced = {d: v * factor for d, v in reduced.items()}

        cumulative = BalancedFrequencyStorm.cumulative_depths(
            reduced, int(total_duration_min), int(time_interval_min)
        )
        increments = np.diff(np.concatenate([[0.0], cumulative]))
        blocks = BalancedFrequencyStorm.alternating_blocks(
            increments, peak_position_pct
        )
        return build_hyetograph_frame(np.insert(blocks, 0, 0.0), int(time_interval_min))


def _validate_depth_table(depths: Mapping[int, float]) -> Dict[int, float]:
    """Return a finite, positive, nondecreasing duration/depth table."""
    table = {}
    for duration, depth in depths.items():
        if isinstance(duration, (bool, np.bool_)):
            raise ValueError("DDF durations must not be boolean values")
        if isinstance(depth, (bool, np.bool_)):
            raise ValueError("DDF depths must not be boolean values")
        try:
            duration_value = float(duration)
            depth_value = float(depth)
        except (TypeError, ValueError) as exc:
            raise ValueError("DDF durations and depths must be numeric") from exc
        if not math.isfinite(duration_value) or duration_value <= 0:
            raise ValueError("DDF durations must be finite and positive")
        if not duration_value.is_integer():
            raise ValueError("DDF durations must be whole minutes")
        if not math.isfinite(depth_value) or depth_value <= 0:
            raise ValueError("DDF depths must be finite and positive")
        duration_int = int(duration_value)
        if duration_int in table:
            raise ValueError(f"Duplicate DDF duration: {duration_int} min")
        table[duration_int] = depth_value

    if not table:
        raise ValueError("At least one DDF duration/depth pair is required")
    ordered = dict(sorted(table.items()))
    previous = None
    for duration, depth in ordered.items():
        if previous is not None and depth < previous:
            raise ValueError(
                "DDF depths must be nondecreasing with duration; HEC-HMS 4.13 "
                "rejects decreasing tables with ERROR 20025"
            )
        previous = depth
    return ordered
