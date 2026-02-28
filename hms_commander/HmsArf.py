"""
HmsArf - Areal Reduction Factor (ARF) Operations

This module provides static methods for applying Areal Reduction Factors to
HEC-HMS meteorologic model files. ARFs adjust precipitation depths to account
for the spatial variability of rainfall over large drainage areas.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
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

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsArf
        >>> arf_table = {'Subbasin-1': 0.92, 'Subbasin-2': 0.88}
        >>> result = HmsArf.apply_arf("model.met", arf_table)
        >>> print(f"Updated {result['subbasins_updated']} subbasins")
    """

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
        arf_table: Union[Dict[str, float], pd.DataFrame],
        preserve_original: bool = True,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Apply Areal Reduction Factors to precipitation depths in a met file.

        For each subbasin, looks up the gage assignment, reads the precipitation
        depths, multiplies by the ARF scalar, and writes back the adjusted values.

        Parameters
        ----------
        met_path : str or Path
            Path to the .met file
        arf_table : dict or pd.DataFrame
            If dict: {subbasin_name: arf_scalar}.
            If DataFrame: must have columns 'subbasin' and 'arf'.
        preserve_original : bool, default True
            If True, creates a backup copy (.met.bak) before modifying
        hms_object : optional
            Optional HmsPrj instance

        Returns
        -------
        dict
            Summary with keys:
            - subbasins_updated: int — number of subbasins with ARF applied
            - subbasins_skipped: int — subbasins not found in ARF table
            - changes: list of dict — per-subbasin change details
            - backup_path: str or None — path to backup file

        Example
        -------
        >>> from hms_commander import HmsArf
        >>> arf_table = {
        ...     'Subbasin-1': 0.92,
        ...     'Subbasin-2': 0.88,
        ...     'Subbasin-3': 0.95,
        ... }
        >>> # Validate first
        >>> validation = HmsArf.validate_arf_table("model.met", arf_table)
        >>> if validation['valid']:
        ...     result = HmsArf.apply_arf("model.met", arf_table)
        ...     print(f"Updated {result['subbasins_updated']} subbasins")

        Notes
        -----
        ARF scalars are typically between 0.0 and 1.0, where 1.0 means no
        reduction. Values > 1.0 are allowed but will produce a warning.
        The method modifies precipitation depth values directly in the .met file.
        """
        from .HmsMet import HmsMet

        met_path = Path(met_path)
        arf_dict = HmsArf._normalize_arf_table(arf_table)

        # Validate ARF values
        for subbasin, arf in arf_dict.items():
            if arf < 0:
                raise ValueError(f"Negative ARF value for '{subbasin}': {arf}")
            if arf > 1.0:
                logger.warning(f"ARF > 1.0 for '{subbasin}': {arf} (amplification)")

        # Create backup
        backup_path = None
        if preserve_original:
            backup_path = Path(str(met_path) + '.bak')
            import shutil
            shutil.copy2(met_path, backup_path)
            logger.info(f"Created backup: {backup_path}")

        # Read current content
        content = HmsFileParser.read_file(met_path)

        # Get gage assignments to map subbasins → gages
        assignments = HmsMet.get_gage_assignments(met_path, hms_object=hms_object)

        changes = []
        subbasins_updated = 0
        subbasins_skipped = 0

        # Get current depths
        try:
            current_depths = HmsMet.get_precipitation_depths(met_path, hms_object=hms_object)
        except Exception:
            current_depths = []

        if not current_depths:
            logger.warning("No precipitation depths found in met file — applying ARF to depth lines directly")

        # Apply ARF by modifying depth values
        # For frequency storm met files, depths are shared across all subbasins
        # The ARF approach: apply a single representative ARF or per-subbasin adjustment

        # Find all Depth: lines and apply ARF
        depth_pattern = r'^(\s*Depth:\s*)([\d.]+)\s*$'
        depth_matches = list(re.finditer(depth_pattern, content, re.MULTILINE))

        if depth_matches and arf_dict:
            # Use the mean ARF as the representative value for shared depths
            # (per-subbasin ARFs are applied when subbasins have individual depth records)
            mean_arf = sum(arf_dict.values()) / len(arf_dict)

            # Check if subbasins have individual depth blocks
            # Parse subbasin blocks to find per-subbasin depths
            subbasin_pattern = r'Subbasin:\s*(.+?)\n(.*?)End:'
            subbasin_matches = list(re.finditer(subbasin_pattern, content, re.DOTALL))

            if subbasin_matches:
                # Per-subbasin depth modification
                # Process in reverse order to preserve positions
                for match in reversed(subbasin_matches):
                    subbasin_name = match.group(1).strip()
                    if subbasin_name not in arf_dict:
                        subbasins_skipped += 1
                        continue

                    arf = arf_dict[subbasin_name]
                    block = match.group(2)
                    block_start = match.start(2)

                    # Find depth lines within this subbasin block
                    block_depths = list(re.finditer(depth_pattern, block, re.MULTILINE))
                    if not block_depths:
                        subbasins_skipped += 1
                        continue

                    # Apply ARF to depths in this block (reverse order)
                    for dm in reversed(block_depths):
                        old_val = float(dm.group(2))
                        new_val = old_val * arf
                        abs_start = block_start + dm.start()
                        abs_end = block_start + dm.end()
                        new_line = f"{dm.group(1)}{new_val:.4f}"
                        content = content[:abs_start] + new_line + content[abs_end:]

                    changes.append({
                        'subbasin': subbasin_name,
                        'arf': arf,
                        'depths_modified': len(block_depths),
                    })
                    subbasins_updated += 1
            else:
                # Global depth modification (single set of depths for all subbasins)
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

        # Write modified content
        HmsFileParser.write_file(met_path, content)

        logger.info(
            f"ARF applied: {subbasins_updated} subbasins updated, "
            f"{subbasins_skipped} skipped in {met_path.name}"
        )

        return {
            'subbasins_updated': subbasins_updated,
            'subbasins_skipped': subbasins_skipped,
            'changes': changes,
            'backup_path': str(backup_path) if backup_path else None,
        }

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
