"""Quiet batched DSS extraction test - writes results to file."""
from hms_commander import HmsDss
from pathlib import Path
import time
import json

dss_33 = Path(r'C:\GH\hms-commander\examples\m3_version_test\A\A100-00-00\A1000000.dss')
dss_411 = Path(r'C:\GH\hms-commander\examples\m3_version_test\A\A100-00-00_HMS411\A1000000.dss')

output_file = Path('examples/batched_test_results.json')

print('Testing batched extraction (quiet mode)...')
print(f'DSS 3.3: {dss_33.stat().st_size / 1024 / 1024:.1f} MB')
print(f'DSS 4.11: {dss_411.stat().st_size / 1024 / 1024:.1f} MB')
print()

results = {}

# Extract peaks from HMS 3.3 (NO PROGRESS LOGGING)
print('Extracting HMS 3.3 peaks...')
start = time.time()
peaks_33 = HmsDss.get_peak_flows_batched(dss_33, batch_size=100, progress=False)
elapsed_33 = time.time() - start
print(f'  OK: {len(peaks_33)} elements in {elapsed_33:.1f}s')

results['hms_33'] = {
    'count': len(peaks_33),
    'elapsed': elapsed_33,
    'top_3_peaks': peaks_33.nlargest(3, 'peak_flow')[['element', 'peak_flow']].to_dict('records')
}

# Extract peaks from HMS 4.11 (NO PROGRESS LOGGING)
print('Extracting HMS 4.11 peaks...')
start = time.time()
peaks_411 = HmsDss.get_peak_flows_batched(dss_411, batch_size=100, progress=False)
elapsed_411 = time.time() - start
print(f'  OK: {len(peaks_411)} elements in {elapsed_411:.1f}s')

results['hms_411'] = {
    'count': len(peaks_411),
    'elapsed': elapsed_411,
    'top_3_peaks': peaks_411.nlargest(3, 'peak_flow')[['element', 'peak_flow']].to_dict('records')
}

# Compare results (match on full DSS path for 1:1 comparison)
print('Comparing...')
merged = peaks_33.merge(
    peaks_411[['dss_path', 'peak_flow', 'peak_time']],
    on='dss_path',
    suffixes=('_33', '_411')
)

# Calculate differences (handle zeros to avoid inf)
import numpy as np
merged['diff_abs'] = merged['peak_flow_411'] - merged['peak_flow_33']
merged['diff_pct'] = np.where(
    merged['peak_flow_33'] != 0,
    (merged['diff_abs'] / merged['peak_flow_33'] * 100),
    np.nan  # Use NaN instead of inf when dividing by zero
)

# Data quality checks
print('Data Quality Analysis...')
zero_33 = (merged['peak_flow_33'] == 0).sum()
zero_411 = (merged['peak_flow_411'] == 0).sum()
both_zero = ((merged['peak_flow_33'] == 0) & (merged['peak_flow_411'] == 0)).sum()
extreme_33 = (merged['peak_flow_33'] > 1e100).sum()
extreme_411 = (merged['peak_flow_411'] > 1e100).sum()
negative_33 = (merged['peak_flow_33'] < 0).sum()
negative_411 = (merged['peak_flow_411'] < 0).sum()

print(f'  HMS 3.3: {zero_33} zeros, {extreme_33} extreme values (>1e100), {negative_33} negative')
print(f'  HMS 4.11: {zero_411} zeros, {extreme_411} extreme values (>1e100), {negative_411} negative')
print(f'  Both zero: {both_zero}')

# Filter out invalid comparisons for statistics
valid_mask = (merged['peak_flow_33'] > 0) & (merged['peak_flow_33'] < 1e100) & \
             (merged['peak_flow_411'] > 0) & (merged['peak_flow_411'] < 1e100)
valid_merged = merged[valid_mask]

results['comparison'] = {
    'total_paths': len(merged),
    'valid_comparisons': len(valid_merged),
    'invalid_comparisons': len(merged) - len(valid_merged),
    'data_quality': {
        'hms_33_zeros': int(zero_33),
        'hms_411_zeros': int(zero_411),
        'both_zero': int(both_zero),
        'hms_33_extreme': int(extreme_33),
        'hms_411_extreme': int(extreme_411),
        'hms_33_negative': int(negative_33),
        'hms_411_negative': int(negative_411)
    },
    'statistics': {
        'max_diff_pct': float(valid_merged['diff_pct'].abs().max()) if len(valid_merged) > 0 else None,
        'mean_diff_pct': float(valid_merged['diff_pct'].abs().mean()) if len(valid_merged) > 0 else None,
        'median_diff_pct': float(valid_merged['diff_pct'].abs().median()) if len(valid_merged) > 0 else None,
        'paths_gt_1pct': int((valid_merged['diff_pct'].abs() > 1).sum()),
        'paths_gt_10pct': int((valid_merged['diff_pct'].abs() > 10).sum())
    },
    'largest_differences': valid_merged.assign(abs_diff_pct=lambda x: x['diff_pct'].abs()).nlargest(5, 'abs_diff_pct')[
        ['element', 'peak_flow_33', 'peak_flow_411', 'diff_pct', 'dss_path']
    ].to_dict('records') if len(valid_merged) > 0 else [],
    'sample_invalid': merged[~valid_mask].head(5)[
        ['element', 'peak_flow_33', 'peak_flow_411', 'dss_path']
    ].to_dict('records')
}

# Write detailed results to file
with open(output_file, 'w') as f:
    json.dump(results, f, indent=2, default=str)

print(f'  OK: {len(merged)} paths matched (1:1 comparison)')
print(f'  Valid comparisons: {results["comparison"]["valid_comparisons"]}')
print(f'  Invalid comparisons: {results["comparison"]["invalid_comparisons"]}')
print()
print('Data Quality:')
print(f'  HMS 3.3: {results["comparison"]["data_quality"]["hms_33_zeros"]} zeros, '
      f'{results["comparison"]["data_quality"]["hms_33_extreme"]} extreme values')
print(f'  HMS 4.11: {results["comparison"]["data_quality"]["hms_411_zeros"]} zeros, '
      f'{results["comparison"]["data_quality"]["hms_411_extreme"]} extreme values')
print()
if results["comparison"]["statistics"]["max_diff_pct"] is not None:
    print('Valid Comparison Statistics:')
    print(f'  Max diff: {results["comparison"]["statistics"]["max_diff_pct"]:.2f}%')
    print(f'  Mean diff: {results["comparison"]["statistics"]["mean_diff_pct"]:.2f}%')
    print(f'  Median diff: {results["comparison"]["statistics"]["median_diff_pct"]:.2f}%')
    print(f'  Paths >1% diff: {results["comparison"]["statistics"]["paths_gt_1pct"]}')
    print(f'  Paths >10% diff: {results["comparison"]["statistics"]["paths_gt_10pct"]}')
print()
print(f'Full results -> {output_file}')
print()
print('SUCCESS: Batched extraction completed!')
