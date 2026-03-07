"""
HmsArf - Areal Reduction Factor (ARF) Operations

This module provides static methods for applying Areal Reduction Factors to
HEC-HMS meteorologic model files. ARFs adjust precipitation depths to account
for the spatial variability of rainfall over large drainage areas.

All methods are static and designed to be used without instantiation.
"""

import re
import shutil
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._parsing import HmsFileParser

logger = get_logger(__name__)


class HmsArf:
    """
    Areal Reduction Factor (ARF) application for HEC-HMS met files.

    Applies ARF scalars to precipitation depths in .met files, scaling
    point precipitation to areal averages based on subbasin-specific
    reduction factors.

    Supports two workflows:
    - **Compute**: Per-junction ARF values from DAR curves and CDA
      (``compute_kcda_cdas``, ``lookup_arf_from_dar``, ``build_kcda_arf_table``)
    - **Apply**: ARF scalar to global depths in a met file (``apply_arf``)

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsArf
        >>> dar_curve = [(10, 1.0), (100, 0.97), (1000, 0.92), (10000, 0.85)]
        >>> table = HmsArf.build_kcda_arf_table(
        ...     "watershed.basin", ["J-Outlet"], dar_curve
        ... )
        >>> result = HmsArf.apply_arf("model.met", arf=table.loc[0, 'arf'])
        >>> print(f"Updated {result['depths_modified']} depths")
    """

    # Compiled regex patterns for Precip Method Parameters block
    _PARAMS_BLOCK = re.compile(
        r'(Precip Method Parameters:.*?^End:)',
        re.DOTALL | re.MULTILINE,
    )
    _DEPTH_LINE = re.compile(r'^(\s*Depth:\s*)([\d.]+)\s*$', re.MULTILINE)

    @staticmethod
    @log_call
    def validate_arf_table(
        met_path: Union[str, Path],
        arf_table: Union[Dict[str, float], pd.DataFrame],
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Verify all subbasins in met file have ARF values in the table.

        Parameters
        ----------
        met_path : str or Path
            Path to the .met file
        arf_table : dict or pd.DataFrame
            If dict: {subbasin_name: arf_scalar}.
            If DataFrame: must have columns 'subbasin' and 'arf'.
        hms_object : optional
            Optional HmsPrj instance

        Returns
        -------
        dict
            Validation result with keys:
            - valid: bool — True if all subbasins have ARF values
            - met_subbasins: list — subbasins found in met file
            - arf_subbasins: list — subbasins in ARF table
            - missing: list — subbasins in met file but not in ARF table
            - extra: list — subbasins in ARF table but not in met file

        Example
        -------
        >>> result = HmsArf.validate_arf_table("model.met", arf_table)
        >>> if not result['valid']:
        ...     print(f"Missing ARFs for: {result['missing']}")
        """
        from .HmsMet import HmsMet

        met_path = Path(met_path)
        arf_dict = HmsArf._normalize_arf_table(arf_table)

        # Get subbasins from met file
        assignments = HmsMet.get_gage_assignments(met_path, hms_object=hms_object)
        met_subbasins = set(assignments['subbasin'].tolist()) if not assignments.empty else set()
        arf_subbasins = set(arf_dict.keys())

        missing = met_subbasins - arf_subbasins
        extra = arf_subbasins - met_subbasins

        if missing:
            logger.warning(f"Subbasins missing ARF values: {sorted(missing)}")
        if extra:
            logger.info(f"Extra ARF entries not in met file: {sorted(extra)}")

        return {
            'valid': len(missing) == 0,
            'met_subbasins': sorted(met_subbasins),
            'arf_subbasins': sorted(arf_subbasins),
            'missing': sorted(missing),
            'extra': sorted(extra),
        }

    @staticmethod
    @log_call
    def apply_arf(
        met_path: Union[str, Path],
        arf_table: Union[Dict[str, float], pd.DataFrame, None] = None,
        arf: Optional[float] = None,
        preserve_original: bool = True,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Apply Areal Reduction Factors to precipitation depths in a met file.

        Two usage modes:

        **Mode 1 – Direct scalar** (A03 workflow, "Frequency Based Hypothetical"):
        Pass ``arf`` as a float.  All ``Depth:`` lines inside the
        ``Precip Method Parameters:`` block are multiplied by the scalar.
        This correctly handles met files where subbasin blocks are empty
        and depths live only in the global parameters block.

        **Mode 2 – Per-subbasin table** (met files with per-subbasin depth lines):
        Pass ``arf_table`` as a dict or DataFrame.  Each subbasin block that
        contains ``Depth:`` lines is updated with its own ARF scalar.  Falls
        back to mean-ARF global modification when no subbasin blocks have depths.

        Parameters
        ----------
        met_path : str or Path
            Path to the .met file
        arf_table : dict or pd.DataFrame, optional
            If dict: {subbasin_name: arf_scalar}.
            If DataFrame: must have columns 'subbasin' and 'arf'.
            Ignored when ``arf`` is provided.
        arf : float, optional
            Single scalar ARF applied to ALL ``Depth:`` lines in the
            ``Precip Method Parameters:`` block.  Takes precedence over
            ``arf_table`` when provided.
        preserve_original : bool, default True
            If True, creates a backup copy (.met.bak) before modifying.
        hms_object : optional
            Optional HmsPrj instance

        Returns
        -------
        dict
            Summary with keys:
            - subbasins_updated: int
            - subbasins_skipped: int
            - depths_modified: int — number of Depth: lines changed
            - changes: list of dict — per-subbasin/global change details
            - backup_path: str or None

        Example
        -------
        >>> # A03: Apply 0.92 ARF to all global depths
        >>> result = HmsArf.apply_arf("model.met", arf=0.92)
        >>> print(f"Modified {result['depths_modified']} depth values")

        >>> # Per-subbasin ARF table
        >>> arf_table = {'Subbasin-1': 0.92, 'Subbasin-2': 0.88}
        >>> result = HmsArf.apply_arf("model.met", arf_table=arf_table)

        Notes
        -----
        ARF scalars are typically between 0.0 and 1.0, where 1.0 means no
        reduction. Values > 1.0 are allowed but will produce a warning.
        """
        met_path = Path(met_path)

        if arf is None and arf_table is None:
            raise ValueError("Must provide either 'arf' (float) or 'arf_table' (dict/DataFrame)")

        # Create backup
        backup_path = None
        if preserve_original:
            backup_path = Path(str(met_path) + '.bak')
            shutil.copy2(met_path, backup_path)
            logger.info(f"Created backup: {backup_path}")

        content = HmsFileParser.read_file(met_path)

        # ------------------------------------------------------------------ #
        # Mode 1: direct scalar ARF → Precip Method Parameters block
        # ------------------------------------------------------------------ #
        if arf is not None:
            if arf < 0:
                raise ValueError(f"Negative ARF: {arf}")
            if arf > 1.0:
                logger.warning(f"ARF > 1.0: {arf} (amplification)")

            block_match = HmsArf._PARAMS_BLOCK.search(content)
            if block_match is None:
                logger.warning("No 'Precip Method Parameters:' block found in met file")
                return {
                    'subbasins_updated': 0,
                    'subbasins_skipped': 0,
                    'depths_modified': 0,
                    'changes': [],
                    'backup_path': str(backup_path) if backup_path else None,
                }

            block_start = block_match.start()
            block_content = block_match.group(1)
            depth_matches = list(HmsArf._DEPTH_LINE.finditer(block_content))

            if not depth_matches:
                logger.warning("No 'Depth:' lines found in Precip Method Parameters block")
                return {
                    'subbasins_updated': 0,
                    'subbasins_skipped': 0,
                    'depths_modified': 0,
                    'changes': [],
                    'backup_path': str(backup_path) if backup_path else None,
                }

            # Apply ARF in reverse order to preserve string offsets
            for dm in reversed(depth_matches):
                old_val = float(dm.group(2))
                new_val = old_val * arf
                abs_start = block_start + dm.start()
                abs_end = block_start + dm.end()
                new_line = f"{dm.group(1)}{new_val:.4f}"
                content = content[:abs_start] + new_line + content[abs_end:]

            HmsFileParser.write_file(met_path, content)
            logger.info(
                f"ARF {arf:.4f} applied: {len(depth_matches)} Depth: lines "
                f"updated in {met_path.name}"
            )

            return {
                'subbasins_updated': 1,
                'subbasins_skipped': 0,
                'depths_modified': len(depth_matches),
                'changes': [{
                    'subbasin': 'all (global)',
                    'arf': arf,
                    'depths_modified': len(depth_matches),
                }],
                'backup_path': str(backup_path) if backup_path else None,
            }

        # ------------------------------------------------------------------ #
        # Mode 2: per-subbasin arf_table
        # ------------------------------------------------------------------ #
        from .HmsMet import HmsMet

        arf_dict = HmsArf._normalize_arf_table(arf_table)

        for subbasin, arf_val in arf_dict.items():
            if arf_val < 0:
                raise ValueError(f"Negative ARF value for '{subbasin}': {arf_val}")
            if arf_val > 1.0:
                logger.warning(f"ARF > 1.0 for '{subbasin}': {arf_val} (amplification)")

        # Get gage assignments (informational / legacy)
        assignments = HmsMet.get_gage_assignments(met_path, hms_object=hms_object)

        changes = []
        subbasins_updated = 0
        subbasins_skipped = 0

        try:
            current_depths = HmsMet.get_precipitation_depths(met_path, hms_object=hms_object)
        except Exception:
            current_depths = []

        if not current_depths:
            logger.warning("No precipitation depths found in met file — applying ARF to depth lines directly")

        depth_pattern = r'^(\s*Depth:\s*)([\d.]+)\s*$'
        depth_matches = list(re.finditer(depth_pattern, content, re.MULTILINE))

        if depth_matches and arf_dict:
            mean_arf = sum(arf_dict.values()) / len(arf_dict)

            subbasin_pattern = r'Subbasin:\s*(.+?)\n(.*?)End:'
            subbasin_matches = list(re.finditer(subbasin_pattern, content, re.DOTALL))

            if subbasin_matches:
                for match in reversed(subbasin_matches):
                    subbasin_name = match.group(1).strip()
                    if subbasin_name not in arf_dict:
                        subbasins_skipped += 1
                        continue

                    arf_val = arf_dict[subbasin_name]
                    block = match.group(2)
                    block_start = match.start(2)

                    block_depths = list(re.finditer(depth_pattern, block, re.MULTILINE))
                    if not block_depths:
                        subbasins_skipped += 1
                        continue

                    for dm in reversed(block_depths):
                        old_val = float(dm.group(2))
                        new_val = old_val * arf_val
                        abs_start = block_start + dm.start()
                        abs_end = block_start + dm.end()
                        new_line = f"{dm.group(1)}{new_val:.4f}"
                        content = content[:abs_start] + new_line + content[abs_end:]

                    changes.append({
                        'subbasin': subbasin_name,
                        'arf': arf_val,
                        'depths_modified': len(block_depths),
                    })
                    subbasins_updated += 1
            else:
                # Global fallback: no per-subbasin blocks with depths
                for dm in reversed(depth_matches):
                    old_val = float(dm.group(2))
                    new_val = old_val * mean_arf
                    new_line = f"{dm.group(1)}{new_val:.4f}"
                    content = content[:dm.start()] + new_line + content[dm.end():]

                changes.append({
                    'subbasin': 'all (global)',
                    'arf': mean_arf,
                    'depths_modified': len(depth_matches),
                })
                subbasins_updated = len(arf_dict)

        HmsFileParser.write_file(met_path, content)
        logger.info(
            f"ARF applied: {subbasins_updated} subbasins updated, "
            f"{subbasins_skipped} skipped in {met_path.name}"
        )

        return {
            'subbasins_updated': subbasins_updated,
            'subbasins_skipped': subbasins_skipped,
            'depths_modified': sum(c.get('depths_modified', 0) for c in changes),
            'changes': changes,
            'backup_path': str(backup_path) if backup_path else None,
        }

    # ---------------------------------------------------------------------- #
    # ---------------------------------------------------------------------- #
    # ARF computation methods (DAR curve + CDA pipeline)
    # ---------------------------------------------------------------------- #

    @staticmethod
    @log_call
    def compute_kcda_cdas(
        basin_path: Union[str, Path],
        kcda_junctions: List[str],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Compute Contributing Drainage Area (CDA) at each KCDA junction.

        Traverses the basin network upstream from each KCDA junction and sums
        the subbasin areas to obtain the Contributing Drainage Area.

        Args:
            basin_path: Path to the .basin file
            kcda_junctions: List of KCDA junction names (analysis points)
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns:
            - junction: KCDA junction name
            - cda_acres: contributing drainage area (in model area units)
            - subbasin_count: number of upstream subbasins
            - upstream_subbasins: list of upstream subbasin names

        Example:
            >>> cdas = HmsArf.compute_kcda_cdas(
            ...     "watershed.basin", ["J-Outlet", "J-Fork-A"]
            ... )
            >>> print(cdas[['junction', 'cda_acres', 'subbasin_count']])
        """
        from .HmsBasin import HmsBasin

        basin_path = Path(basin_path)
        subbasins_df = HmsBasin.get_subbasins(basin_path, hms_object=hms_object)
        area_lookup = dict(zip(subbasins_df['name'], subbasins_df['area']))

        rows = []
        for junction in kcda_junctions:
            upstream = HmsBasin.get_upstream_elements(
                basin_path, junction, hms_object=hms_object
            )
            upstream_subs = upstream['subbasins']
            cda = sum(
                float(area_lookup.get(s) or 0)
                for s in upstream_subs
                if area_lookup.get(s) is not None and not pd.isna(area_lookup.get(s))
            )
            rows.append({
                'junction': junction,
                'cda_acres': cda,
                'subbasin_count': len(upstream_subs),
                'upstream_subbasins': upstream_subs,
            })

        return pd.DataFrame(rows)

    @staticmethod
    def lookup_arf_from_dar(
        cda: float,
        dar_curve: Union[pd.DataFrame, List[Tuple[float, float]], Dict],
        duration_hours: float = 24.0
    ) -> float:
        """
        Interpolate ARF from a DAR (Depth-Area Reduction) curve at a given CDA.

        Args:
            cda: Contributing drainage area (same units as dar_curve 'area' column
                 or first element of each tuple)
            dar_curve: One of:
                - DataFrame with columns ['area', 'arf']
                - List of (area, arf) tuples, sorted or unsorted
                - Dict keyed by duration_hours → list of (area, arf) tuples,
                  e.g. {6.0: [(10, 1.0), ...], 24.0: [(10, 1.0), ...]}
            duration_hours: Used only when dar_curve is a duration-keyed dict.
                Selects the nearest available duration key.

        Returns:
            float: ARF value in [min_curve_arf, 1.0].
            Returns 1.0 if CDA is at or below the minimum curve area
            (no reduction for very small areas).  Extrapolation beyond the
            maximum curve area returns the last (smallest) ARF value.

        Example:
            >>> dar = [(10, 1.0), (100, 0.97), (1000, 0.92), (10000, 0.85)]
            >>> HmsArf.lookup_arf_from_dar(500, dar)   # between 100 and 1000
            0.945  # approx
        """
        # Resolve duration-keyed dict
        if isinstance(dar_curve, dict):
            if duration_hours in dar_curve:
                raw = dar_curve[duration_hours]
            else:
                nearest_key = min(dar_curve.keys(), key=lambda k: abs(k - duration_hours))
                raw = dar_curve[nearest_key]
            areas = [x[0] for x in raw]
            arfs = [x[1] for x in raw]
        elif isinstance(dar_curve, pd.DataFrame):
            areas = dar_curve['area'].tolist()
            arfs = dar_curve['arf'].tolist()
        else:
            # List of (area, arf) tuples
            areas = [x[0] for x in dar_curve]
            arfs = [x[1] for x in dar_curve]

        if not areas:
            return 1.0

        # Sort by area ascending
        sorted_pairs = sorted(zip(areas, arfs), key=lambda p: p[0])
        areas_sorted = [p[0] for p in sorted_pairs]
        arfs_sorted = [p[1] for p in sorted_pairs]

        # Below minimum curve area → no reduction
        if cda <= areas_sorted[0]:
            return 1.0

        # Linear interpolation (extrapolation beyond max uses last ARF value)
        arf = float(np.interp(cda, areas_sorted, arfs_sorted))

        # Clamp to [minimum ARF in curve, 1.0]
        return float(np.clip(arf, min(arfs_sorted), 1.0))

    @staticmethod
    @log_call
    def build_kcda_arf_table(
        basin_path: Union[str, Path],
        kcda_junctions: List[str],
        dar_curve: Union[pd.DataFrame, List[Tuple[float, float]], Dict],
        duration_hours: float = 24.0,
        hms_object=None
    ) -> pd.DataFrame:
        """
        Compute ARF for each KCDA junction from DAR curves and drainage area.

        Combines ``compute_kcda_cdas()`` and ``lookup_arf_from_dar()`` into a
        single call.  Specify outlet junctions → traverse upstream → sum subbasin
        areas → CDA → look up ARF from DAR curve.

        Args:
            basin_path: Path to the .basin file
            kcda_junctions: KCDA junction names (analysis points)
            dar_curve: DAR curve (see ``lookup_arf_from_dar`` for accepted formats)
            duration_hours: Storm duration for DAR curve lookup (default: 24)
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame sorted ascending by CDA with columns:
            - junction: KCDA junction name
            - cda_acres: contributing drainage area (model area units)
            - subbasin_count: number of upstream subbasins
            - upstream_subbasins: list of upstream subbasin names
            - arf: ARF from DAR curve at this CDA
            - a14_dar_multiplier: alias for arf (for use in reports)

        Example:
            >>> dar_curve = [(10, 1.0), (100, 0.97), (1000, 0.92), (10000, 0.85)]
            >>> table = HmsArf.build_kcda_arf_table(
            ...     "watershed.basin",
            ...     ["J-Outlet", "J-Mid", "J-Headwater"],
            ...     dar_curve,
            ...     duration_hours=24,
            ... )
            >>> print(table[['junction', 'cda_acres', 'arf']])
        """
        basin_path = Path(basin_path)

        cda_df = HmsArf.compute_kcda_cdas(
            basin_path, kcda_junctions, hms_object=hms_object
        )

        arfs = [
            HmsArf.lookup_arf_from_dar(row['cda_acres'], dar_curve, duration_hours)
            for _, row in cda_df.iterrows()
        ]

        cda_df['arf'] = arfs
        cda_df['a14_dar_multiplier'] = arfs

        return cda_df.sort_values('cda_acres').reset_index(drop=True)

    # ---------------------------------------------------------------------- #
    # Internal helpers
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _normalize_arf_table(
        arf_table: Union[Dict[str, float], pd.DataFrame]
    ) -> Dict[str, float]:
        """Normalize ARF table input to dict format."""
        if isinstance(arf_table, pd.DataFrame):
            if 'subbasin' not in arf_table.columns or 'arf' not in arf_table.columns:
                raise ValueError("DataFrame must have 'subbasin' and 'arf' columns")
            return dict(zip(arf_table['subbasin'], arf_table['arf']))
        return dict(arf_table)
