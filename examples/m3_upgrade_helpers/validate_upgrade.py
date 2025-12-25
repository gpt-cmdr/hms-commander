"""
Validate HMS 3.3 vs HMS 4.11 Upgrade

Compare DSS results between HMS versions to verify upgrade success.

Usage:
    python validate_upgrade.py <dss_33_path> <dss_411_path> <model_name>

Example:
    python validate_upgrade.py \
        D100-00-00/D1000000.dss \
        D100-00-00_HMS411/results.dss \
        "Brays Bayou"
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import json

def validate_upgrade(dss_33_path, dss_411_path, model_name, tolerance_pct=1.0):
    """
    Compare HMS 3.3 vs HMS 4.11 results.

    Args:
        dss_33_path: Path to HMS 3.3 DSS file
        dss_411_path: Path to HMS 4.11 DSS file
        model_name: Model name for reporting
        tolerance_pct: Acceptable difference percentage

    Returns:
        dict: Validation results
    """
    from hms_commander import HmsDss

    print(f"\n{'='*70}")
    print(f"VALIDATION: {model_name}")
    print(f"{'='*70}\n")

    dss_33 = Path(dss_33_path)
    dss_411 = Path(dss_411_path)

    # Verify files exist
    if not dss_33.exists():
        print(f"✗ HMS 3.3 DSS not found: {dss_33}")
        return {'status': 'FAIL', 'reason': 'HMS 3.3 DSS file not found'}

    if not dss_411.exists():
        print(f"✗ HMS 4.11 DSS not found: {dss_411}")
        return {'status': 'FAIL', 'reason': 'HMS 4.11 DSS file not found'}

    print(f"HMS 3.3:  {dss_33.name} ({dss_33.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"HMS 4.11: {dss_411.name} ({dss_411.stat().st_size / 1024 / 1024:.1f} MB)")
    print()

    # Extract peaks
    print("Extracting HMS 3.3 peaks...")
    peaks_33 = HmsDss.get_peak_flows_batched(dss_33, progress=False)
    print(f"  Extracted {len(peaks_33)} paths")

    print("Extracting HMS 4.11 peaks...")
    peaks_411 = HmsDss.get_peak_flows_batched(dss_411, progress=False)
    print(f"  Extracted {len(peaks_411)} paths")
    print()

    # Merge on DSS path (1:1 comparison)
    merged = peaks_33.merge(
        peaks_411[['dss_path', 'peak_flow']],
        on='dss_path',
        suffixes=('_33', '_411'),
        how='outer'
    )

    # Check for missing paths
    missing_33 = merged['peak_flow_33'].isna().sum()
    missing_411 = merged['peak_flow_411'].isna().sum()

    if missing_33 > 0:
        print(f"⚠️  WARNING: {missing_33} paths only in HMS 4.11 (new paths)")
    if missing_411 > 0:
        print(f"⚠️  WARNING: {missing_411} paths only in HMS 3.3 (missing in HMS 4.11)")
    if missing_33 == 0 and missing_411 == 0:
        print(f"✓ All paths matched (1:1 comparison)")
    print()

    # Calculate differences
    merged['diff_pct'] = np.where(
        merged['peak_flow_33'] != 0,
        (merged['peak_flow_411'] - merged['peak_flow_33']) / merged['peak_flow_33'] * 100,
        np.nan
    )
    merged['diff_abs'] = merged['peak_flow_411'] - merged['peak_flow_33']

    # Data quality flags
    extreme_33 = (merged['peak_flow_33'] > 1e100).sum()
    extreme_411 = (merged['peak_flow_411'] > 1e100).sum()
    zero_33 = (merged['peak_flow_33'] == 0).sum()
    zero_411 = (merged['peak_flow_411'] == 0).sum()
    negative_33 = (merged['peak_flow_33'] < 0).sum()
    negative_411 = (merged['peak_flow_411'] < 0).sum()

    # Valid comparisons (exclude extreme values, zeros, negatives)
    valid_mask = (
        (merged['peak_flow_33'] > 0) & (merged['peak_flow_33'] < 1e100) &
        (merged['peak_flow_411'] > 0) & (merged['peak_flow_411'] < 1e100)
    )
    valid = merged[valid_mask]

    # Statistics
    validation_result = {
        'model_name': model_name,
        'total_paths': len(merged),
        'valid_comparisons': len(valid),
        'invalid_comparisons': len(merged) - len(valid),
        'data_quality': {
            'hms_33_extreme': int(extreme_33),
            'hms_411_extreme': int(extreme_411),
            'extreme_fixed': int(extreme_33 - extreme_411),
            'hms_33_zeros': int(zero_33),
            'hms_411_zeros': int(zero_411),
            'hms_33_negative': int(negative_33),
            'hms_411_negative': int(negative_411)
        }
    }

    if len(valid) > 0:
        max_diff = float(valid['diff_pct'].abs().max())
        mean_diff = float(valid['diff_pct'].abs().mean())
        median_diff = float(valid['diff_pct'].abs().median())
        gt_tolerance = int((valid['diff_pct'].abs() > tolerance_pct).sum())

        validation_result['statistics'] = {
            'max_diff_pct': max_diff,
            'mean_diff_pct': mean_diff,
            'median_diff_pct': median_diff,
            'paths_gt_tolerance': gt_tolerance,
            'tolerance_pct': tolerance_pct
        }

        print(f"{'='*70}")
        print(f"RESULTS")
        print(f"{'='*70}\n")
        print(f"Total DSS Paths: {len(merged)}")
        print(f"Valid Comparisons: {len(valid)} ({len(valid)/len(merged)*100:.1f}%)")
        print(f"\nData Quality:")
        print(f"  HMS 3.3 extreme values: {extreme_33}")
        print(f"  HMS 4.11 extreme values: {extreme_411}")
        print(f"  Fixed: {extreme_33 - extreme_411}")
        print(f"  HMS 3.3 zeros: {zero_33}")
        print(f"  HMS 4.11 zeros: {zero_411}")
        print(f"\nComparison Statistics (Valid Data Only):")
        print(f"  Max difference: {max_diff:.3f}%")
        print(f"  Mean difference: {mean_diff:.3f}%")
        print(f"  Median difference: {median_diff:.3f}%")
        print(f"  Paths > {tolerance_pct}% diff: {gt_tolerance}")

        # Pass/Fail criteria
        if max_diff < 10 and gt_tolerance < len(valid) * 0.05:
            print(f"\n✓ VALIDATION PASSED")
            validation_result['status'] = "PASS"
        else:
            print(f"\n✗ VALIDATION FAILED")
            reason = []
            if max_diff >= 10:
                reason.append(f"Max diff {max_diff:.1f}% exceeds 10% threshold")
            if gt_tolerance >= len(valid) * 0.05:
                reason.append(f"{gt_tolerance} paths exceed {tolerance_pct}% ({gt_tolerance/len(valid)*100:.1f}%)")
            validation_result['status'] = "FAIL"
            validation_result['failure_reason'] = "; ".join(reason)
            print(f"   Reason: {validation_result['failure_reason']}")

        # Show largest differences
        if gt_tolerance > 0:
            print(f"\nLargest Differences (exceeding {tolerance_pct}%):")
            top_diff = valid[valid['diff_pct'].abs() > tolerance_pct].nlargest(5, lambda x: x['diff_pct'].abs())
            for idx, row in top_diff.iterrows():
                print(f"  {row['element']}: {row['peak_flow_33']:.1f} → {row['peak_flow_411']:.1f} ({row['diff_pct']:+.2f}%)")
                print(f"    Path: {row['dss_path']}")

        # Show sample of largest diffs even if within tolerance
        print(f"\nTop 5 Differences (all data):")
        top_5 = valid.assign(abs_diff=lambda x: x['diff_pct'].abs()).nlargest(5, 'abs_diff')
        for idx, row in top_5.iterrows():
            print(f"  {row['element']}: {row['peak_flow_33']:.1f} → {row['peak_flow_411']:.1f} ({row['diff_pct']:+.3f}%)")

    else:
        print("✗ No valid comparisons possible")
        validation_result['status'] = "FAIL"
        validation_result['failure_reason'] = "No valid data for comparison"

    return validation_result


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    dss_33_path = sys.argv[1]
    dss_411_path = sys.argv[2]
    model_name = sys.argv[3]
    tolerance = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0

    result = validate_upgrade(dss_33_path, dss_411_path, model_name, tolerance)

    # Save results
    output_file = Path("validation_results.json")
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    print(f"\nResults saved to: {output_file}")

    # Exit code based on status
    sys.exit(0 if result['status'] == 'PASS' else 1)
