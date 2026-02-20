Plot DSS results from HEC-HMS simulations using the `hms_extract_dss-results` skill.

## Workflow

1. **Identify the DSS file and paths**:
   ```python
   from hms_commander import HmsDss, HmsRun
   from pathlib import Path

   # Get DSS file location from run configuration
   run_config = HmsRun.get_run_config("project.run", "Run_1")
   dss_file = Path(run_config['dss_file'])
   ```

2. **Extract time series data**:
   ```python
   from hms_commander import HmsDss

   # List available paths in DSS file
   paths = HmsDss.list_paths(dss_file)

   # Extract hydrograph for specific element
   ts = HmsDss.get_time_series(dss_file, "/Basin/Junction1/FLOW//1Hour/Run_1/")
   # ts is a pandas DataFrame with DatetimeIndex and 'flow' column
   ```

3. **Plot hydrographs**:
   ```python
   import matplotlib.pyplot as plt

   fig, ax = plt.subplots(figsize=(12, 5))
   ax.plot(ts.index, ts['flow'], label='Run 1')
   ax.set_xlabel('Date/Time')
   ax.set_ylabel('Flow (cfs)')
   ax.set_title('Outlet Hydrograph')
   ax.legend()
   plt.tight_layout()
   plt.show()
   ```

4. **Compare baseline vs. updated**:
   ```python
   # Load two DSS files for comparison
   baseline = HmsDss.get_time_series(baseline_dss, pathway)
   updated = HmsDss.get_time_series(updated_dss, pathway)

   # Compute differences
   peak_diff_pct = (updated['flow'].max() - baseline['flow'].max()) / baseline['flow'].max() * 100
   vol_diff_pct = (updated['flow'].sum() - baseline['flow'].sum()) / baseline['flow'].sum() * 100

   print(f"Peak difference: {peak_diff_pct:.2f}%")  # Threshold: <1%
   print(f"Volume difference: {vol_diff_pct:.2f}%")  # Threshold: <0.5%
   ```

## DSS Comparison Acceptance Criteria

From `.claude/rules/hec-hms/critical-bugs-workarounds.md` Bug 5:
- Peak flow difference: **< 1.0%**
- Volume difference: **< 0.5%**
- Timing difference: **≤ 1 timestep**

## Reference

- Skill: `.claude/skills/hms_extract_dss-results/SKILL.md`
- DSS operations: `.claude/rules/hec-hms/dss-operations.md`
- Code: `hms_commander/HmsDss.py`, `hms_commander/HmsResults.py`
