"""
HMS DSS Output Comparison Script

Compares DSS outputs between HMS 3.x and HMS 4.x runs to validate
version upgrade results.

Usage:
    python compare_dss_outputs.py <dss_3x_path> <dss_4x_path> [--element <name>]

Example:
    python compare_dss_outputs.py original/results.dss upgraded/results.dss
    python compare_dss_outputs.py original/results.dss upgraded/results.dss --element "74006"
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import sys

# Flexible import for development vs installed package
try:
    from hms_commander import HmsDss
except ImportError:
    current_file = Path(__file__).resolve()
    parent_directory = current_file.parent.parent.parent
    sys.path.insert(0, str(parent_directory))
    from hms_commander import HmsDss

import pandas as pd
import numpy as np


@dataclass
class ComparisonResult:
    """Results from comparing two DSS files."""

    # File info
    file_33_path: str
    file_411_path: str
    file_33_size_mb: float
    file_411_size_mb: float

    # Catalog info
    num_paths_33: int
    num_paths_411: int
    types_only_33: List[str]
    types_only_411: List[str]
    common_types: List[str]

    # Flow comparison (if available)
    flow_compared: bool = False
    element_name: Optional[str] = None
    peak_flow_33: Optional[float] = None
    peak_flow_411: Optional[float] = None
    peak_diff_pct: Optional[float] = None
    peak_time_33: Optional[str] = None
    peak_time_411: Optional[str] = None
    peak_timing_diff_hours: Optional[int] = None
    volume_33: Optional[float] = None
    volume_411: Optional[float] = None
    volume_diff_pct: Optional[float] = None
    max_abs_diff: Optional[float] = None
    mean_abs_diff: Optional[float] = None
    mean_pct_diff: Optional[float] = None
    num_differing_values: Optional[int] = None
    total_values: Optional[int] = None

    def is_acceptable(self,
                      peak_threshold_pct: float = 1.0,
                      volume_threshold_pct: float = 0.5,
                      timing_threshold_hours: int = 1) -> Tuple[bool, List[str]]:
        """
        Check if comparison results meet acceptance criteria.

        Args:
            peak_threshold_pct: Maximum acceptable peak flow difference (%)
            volume_threshold_pct: Maximum acceptable volume difference (%)
            timing_threshold_hours: Maximum acceptable peak timing difference (hours)

        Returns:
            Tuple of (acceptable: bool, issues: List[str])
        """
        issues = []

        if self.flow_compared:
            if self.peak_diff_pct is not None and abs(self.peak_diff_pct) > peak_threshold_pct:
                issues.append(f"Peak flow difference ({self.peak_diff_pct:.2f}%) exceeds threshold ({peak_threshold_pct}%)")

            if self.volume_diff_pct is not None and abs(self.volume_diff_pct) > volume_threshold_pct:
                issues.append(f"Volume difference ({self.volume_diff_pct:.2f}%) exceeds threshold ({volume_threshold_pct}%)")

            if self.peak_timing_diff_hours is not None and self.peak_timing_diff_hours > timing_threshold_hours:
                issues.append(f"Peak timing difference ({self.peak_timing_diff_hours} hours) exceeds threshold ({timing_threshold_hours} hours)")

        return len(issues) == 0, issues


def compare_hms_dss_outputs(
    dss_33_path: str,
    dss_411_path: str,
    element_name: Optional[str] = None,
    verbose: bool = True
) -> ComparisonResult:
    """
    Compare DSS outputs between HMS 3.x and HMS 4.x runs.

    Args:
        dss_33_path: Path to HMS 3.x DSS output file
        dss_411_path: Path to HMS 4.x DSS output file
        element_name: Specific element to compare (auto-detects if None)
        verbose: Print detailed output

    Returns:
        ComparisonResult with comparison metrics
    """
    dss_33 = Path(dss_33_path)
    dss_411 = Path(dss_411_path)

    if not dss_33.exists():
        raise FileNotFoundError(f"HMS 3.x DSS file not found: {dss_33}")
    if not dss_411.exists():
        raise FileNotFoundError(f"HMS 4.x DSS file not found: {dss_411}")

    # Get file info
    info_33 = HmsDss.get_info(dss_33)
    info_411 = HmsDss.get_info(dss_411)

    # Get catalogs
    cat_33 = HmsDss.get_catalog(dss_33)
    cat_411 = HmsDss.get_catalog(dss_411)

    # Extract data types (C-parts)
    types_33 = set(info_33['path_types'].keys())
    types_411 = set(info_411['path_types'].keys())

    only_33 = sorted(types_33 - types_411)
    only_411 = sorted(types_411 - types_33)
    common = sorted(types_33 & types_411)

    # Initialize result
    result = ComparisonResult(
        file_33_path=str(dss_33),
        file_411_path=str(dss_411),
        file_33_size_mb=info_33['file_size_mb'],
        file_411_size_mb=info_411['file_size_mb'],
        num_paths_33=info_33['num_paths'],
        num_paths_411=info_411['num_paths'],
        types_only_33=only_33,
        types_only_411=only_411,
        common_types=common
    )

    if verbose:
        print("=" * 80)
        print("HMS DSS OUTPUT COMPARISON")
        print("=" * 80)
        print(f"\nHMS 3.x file: {dss_33}")
        print(f"  Size: {info_33['file_size_mb']} MB, Paths: {info_33['num_paths']}")
        print(f"\nHMS 4.x file: {dss_411}")
        print(f"  Size: {info_411['file_size_mb']} MB, Paths: {info_411['num_paths']}")

        if only_33:
            print(f"\nData types in 3.x ONLY: {', '.join(only_33)}")
        if only_411:
            print(f"\nData types in 4.x ONLY (NEW): {', '.join(only_411)}")

    # Find flow paths for comparison
    flow_paths_33 = [p for p in cat_33 if '/FLOW/' in p.upper() and '-' not in p.split('/')[2]]
    flow_paths_411 = [p for p in cat_411 if '/FLOW/' in p.upper() and '-' not in p.split('/')[2]]

    if not flow_paths_33 or not flow_paths_411:
        if verbose:
            print("\nNo FLOW data found for comparison")
        return result

    # Auto-detect element if not specified
    if element_name is None:
        # Extract unique B-parts (element names) from flow paths
        elements_33 = set(p.split('/')[1] for p in flow_paths_33 if len(p.split('/')) > 1)
        elements_411 = set(p.split('/')[1] for p in flow_paths_411 if len(p.split('/')) > 1)
        common_elements = elements_33 & elements_411

        if common_elements:
            # Use first common element
            element_name = sorted(common_elements)[0]
        else:
            if verbose:
                print("\nNo common flow elements found for comparison")
            return result

    result.element_name = element_name

    # Filter paths for the target element
    elem_paths_33 = [p for p in flow_paths_33 if element_name.upper() in p.upper()]
    elem_paths_411 = [p for p in flow_paths_411 if element_name.upper() in p.upper()]

    if not elem_paths_33 or not elem_paths_411:
        if verbose:
            print(f"\nNo FLOW data found for element '{element_name}'")
        return result

    # Read and combine flow timeseries
    df_33_list = []
    for p in sorted(elem_paths_33):
        try:
            df = HmsDss.read_timeseries(dss_33, p)
            df_33_list.append(df)
        except Exception as e:
            if verbose:
                print(f"Warning: Could not read {p}: {e}")

    df_411_list = []
    for p in sorted(elem_paths_411):
        try:
            df = HmsDss.read_timeseries(dss_411, p)
            df_411_list.append(df)
        except Exception as e:
            if verbose:
                print(f"Warning: Could not read {p}: {e}")

    if not df_33_list or not df_411_list:
        return result

    # Combine and deduplicate
    df_33 = pd.concat(df_33_list).sort_index()
    df_411 = pd.concat(df_411_list).sort_index()
    df_33 = df_33[~df_33.index.duplicated(keep='first')]
    df_411 = df_411[~df_411.index.duplicated(keep='first')]

    # Find common timestamps
    common_idx = df_33.index.intersection(df_411.index)

    if len(common_idx) == 0:
        if verbose:
            print("\nNo overlapping timestamps for comparison")
        return result

    # Extract values
    vals_33 = df_33.loc[common_idx, 'value'].values
    vals_411 = df_411.loc[common_idx, 'value'].values

    # Calculate differences
    diff = vals_33 - vals_411
    abs_diff = np.abs(diff)
    pct_diff = np.where(vals_33 != 0, np.abs(diff / vals_33) * 100, 0)

    # Peak flow comparison
    peak_idx_33 = np.argmax(vals_33)
    peak_idx_411 = np.argmax(vals_411)

    result.flow_compared = True
    result.peak_flow_33 = float(vals_33.max())
    result.peak_flow_411 = float(vals_411.max())
    result.peak_diff_pct = float((vals_33.max() - vals_411.max()) / vals_33.max() * 100)
    result.peak_time_33 = str(common_idx[peak_idx_33])
    result.peak_time_411 = str(common_idx[peak_idx_411])
    result.peak_timing_diff_hours = abs(peak_idx_33 - peak_idx_411)
    result.volume_33 = float(vals_33.sum())
    result.volume_411 = float(vals_411.sum())
    result.volume_diff_pct = float((vals_33.sum() - vals_411.sum()) / vals_33.sum() * 100)
    result.max_abs_diff = float(abs_diff.max())
    result.mean_abs_diff = float(abs_diff.mean())
    result.mean_pct_diff = float(pct_diff.mean())
    result.num_differing_values = int(np.sum(abs_diff > 1e-6))
    result.total_values = len(vals_33)

    if verbose:
        print("\n" + "=" * 80)
        print(f"FLOW COMPARISON: {element_name}")
        print("=" * 80)

        print(f"\nPEAK FLOW:")
        print(f"  HMS 3.x: {result.peak_flow_33:.4f} CFS at {result.peak_time_33}")
        print(f"  HMS 4.x: {result.peak_flow_411:.4f} CFS at {result.peak_time_411}")
        print(f"  Difference: {result.peak_flow_33 - result.peak_flow_411:.4f} CFS ({result.peak_diff_pct:.2f}%)")
        print(f"  Timing difference: {result.peak_timing_diff_hours} hours")

        print(f"\nVOLUME:")
        print(f"  HMS 3.x: {result.volume_33:.2f} CFS-hours")
        print(f"  HMS 4.x: {result.volume_411:.2f} CFS-hours")
        print(f"  Difference: {result.volume_33 - result.volume_411:.2f} CFS-hours ({result.volume_diff_pct:.2f}%)")

        print(f"\nVALUE DIFFERENCES:")
        print(f"  Max absolute difference: {result.max_abs_diff:.4f} CFS")
        print(f"  Mean absolute difference: {result.mean_abs_diff:.4f} CFS")
        print(f"  Mean % difference: {result.mean_pct_diff:.2f}%")
        print(f"  Differing values: {result.num_differing_values} / {result.total_values} ({result.num_differing_values/result.total_values*100:.1f}%)")

        # Acceptance check
        acceptable, issues = result.is_acceptable()
        print("\n" + "=" * 80)
        print("ACCEPTANCE CHECK")
        print("=" * 80)
        if acceptable:
            print("\n[PASS] Results meet acceptance criteria")
        else:
            print("\n[FAIL] Results do not meet acceptance criteria:")
            for issue in issues:
                print(f"  - {issue}")

    return result


def format_comparison_report(result: ComparisonResult) -> str:
    """Format comparison result as a markdown report."""

    lines = [
        "# HMS Version Upgrade Comparison Report",
        "",
        "## File Information",
        "",
        "| Property | HMS 3.x | HMS 4.x |",
        "|----------|---------|---------|",
        f"| File Path | `{result.file_33_path}` | `{result.file_411_path}` |",
        f"| File Size | {result.file_33_size_mb} MB | {result.file_411_size_mb} MB |",
        f"| DSS Paths | {result.num_paths_33} | {result.num_paths_411} |",
        "",
    ]

    if result.types_only_33:
        lines.extend([
            "## Data Types Removed in 4.x",
            "",
            *[f"- {t}" for t in result.types_only_33],
            "",
        ])

    if result.types_only_411:
        lines.extend([
            "## Data Types Added in 4.x",
            "",
            *[f"- {t}" for t in result.types_only_411],
            "",
        ])

    if result.flow_compared:
        lines.extend([
            f"## Flow Comparison: {result.element_name}",
            "",
            "### Peak Flow",
            "",
            "| Metric | HMS 3.x | HMS 4.x | Difference |",
            "|--------|---------|---------|------------|",
            f"| Peak Flow | {result.peak_flow_33:.4f} CFS | {result.peak_flow_411:.4f} CFS | {result.peak_diff_pct:.2f}% |",
            f"| Peak Time | {result.peak_time_33} | {result.peak_time_411} | {result.peak_timing_diff_hours} hours |",
            "",
            "### Volume",
            "",
            "| Metric | HMS 3.x | HMS 4.x | Difference |",
            "|--------|---------|---------|------------|",
            f"| Total Volume | {result.volume_33:.2f} CFS-hr | {result.volume_411:.2f} CFS-hr | {result.volume_diff_pct:.2f}% |",
            "",
            "### Statistical Differences",
            "",
            f"- Max absolute difference: {result.max_abs_diff:.4f} CFS",
            f"- Mean absolute difference: {result.mean_abs_diff:.4f} CFS",
            f"- Mean % difference: {result.mean_pct_diff:.2f}%",
            f"- Values that differ: {result.num_differing_values} / {result.total_values} ({result.num_differing_values/result.total_values*100:.1f}%)",
            "",
        ])

        acceptable, issues = result.is_acceptable()
        lines.extend([
            "## Acceptance",
            "",
            f"**Status:** {'PASS' if acceptable else 'FAIL'}",
            "",
        ])
        if not acceptable:
            lines.extend([
                "**Issues:**",
                "",
                *[f"- {issue}" for issue in issues],
                "",
            ])

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare HMS DSS outputs between versions")
    parser.add_argument("dss_33", help="Path to HMS 3.x DSS file")
    parser.add_argument("dss_411", help="Path to HMS 4.x DSS file")
    parser.add_argument("--element", help="Element name to compare (auto-detects if not specified)")
    parser.add_argument("--output", help="Output markdown report path")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    result = compare_hms_dss_outputs(
        args.dss_33,
        args.dss_411,
        element_name=args.element,
        verbose=not args.quiet
    )

    if args.output:
        report = format_comparison_report(result)
        Path(args.output).write_text(report)
        print(f"\nReport saved to: {args.output}")
