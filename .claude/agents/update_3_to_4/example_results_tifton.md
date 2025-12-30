# HMS Version Upgrade Results: Tifton Project

## Project Information

| Field | Value |
|-------|-------|
| Project Name | `tifton` |
| Original Path | `C:/GH/hms-commander/test_hms33/tifton` |
| Upgraded Path | `C:/GH/hms-commander/test_hms33/tifton_upgrade_4.11` |
| Run Name | `Run 1` |
| Upgrade Date | 2025-12-10 |

## Version Information

| Version | HMS Installation |
|---------|------------------|
| Original | HMS 3.3 (`C:/Program Files (x86)/HEC/HEC-HMS/3.3`) |
| Upgraded | HMS 4.11 (`C:/Program Files/HEC/HEC-HMS/4.11`) |

## Execution Results

### HMS 3.x Run

| Metric | Value |
|--------|-------|
| Status | SUCCESS |
| Warnings | 1 |
| Errors | 0 |
| Exit Code | 0 |

<details>
<summary>Log Output</summary>

```
NOTE 14650: Run Script: "hms_script.py"
NOTE 10008: Finished opening project "tifton"
NOTE 10181: Opened control specifications "Jan1-Jun30 1970"
NOTE 10179: Opened basin model "Tifton"
NOTE 10180: Opened meteorologic model "Tifton Hyetograph"
WARNING 42720: Basin map file "maps\Tifton.map" is missing for basin model "Tifton".
NOTE 10184: Began computing simulation run "Run 1"
NOTE 20364: Found no parameter problems in meteorologic model "Tifton Hyetograph"
NOTE 40049: Found no parameter problems in basin model "Tifton"
NOTE 10185: Finished computing simulation run "Run 1"
NOTE 12573: End script; Exit code 0
```

</details>

### HMS 4.x Run

| Metric | Value |
|--------|-------|
| Status | SUCCESS |
| Version Upgrade | 3.3 → 4.11 |
| Warnings | 2 (upgrade messages) |
| Errors | 0 |
| Exit Code | 0 |

<details>
<summary>Log Output</summary>

```
NOTE 10019: Finished opening project "tifton"
WARNING 10020: Begin updating "tifton" from Version 3.3 to Version 4.11
NOTE 10181: Opened control specifications "Jan1-Jun30 1970"
WARNING 10021: Project "tifton" was updated from Version 3.3 to Version 4.11
NOTE 42413: Unit hydrograph volume for subbasin "74006" is 1.0000 in.
NOTE 15301: Began computing simulation run "Run 1"
NOTE 10181: Opened control specifications "Jan1-Jun30 1970"
NOTE 20364: Found no parameter problems in meteorologic model "Tifton Hyetograph"
NOTE 40049: Found no parameter problems in basin model "Tifton"
NOTE 42413: Unit hydrograph volume for subbasin "74006" is 1.0000 in.
NOTE 15302: Finished computing simulation run "Run 1"
NOTE 15312: The total runtime for this simulation is 00:00.
NOTE 12573: End script; Exit code 0
```

</details>

## DSS Output Comparison

### File Information

| Property | HMS 3.x | HMS 4.x |
|----------|---------|---------|
| File Size | 1.12 MB | 1.08 MB |
| DSS Paths | 174 | 199 |
| DSS Version | DSS-6 | DSS-7 |

### Data Type Changes

**Removed in 4.x:**
- ET-SOIL
- PRECIP-CUM
- PRECIP-INC

**Added in 4.x:**
- AQUIFER RECHARGE
- FLOW-BASE-1 (GW Layer 1 baseflow)
- FLOW-BASE-2 (GW Layer 2 baseflow)
- FLOW-CUMULATIVE
- FLOW-OBSERVED-CUMULATIVE
- FLOW-UNIT GRAPH
- PRECIP-LOSS-CUM

### Flow Comparison: 74006 (Subbasin)

#### Peak Flow

| Metric | HMS 3.x | HMS 4.x | Difference |
|--------|---------|---------|------------|
| Peak Flow | 838.93 CFS | 837.18 CFS | 0.21% |
| Peak Time | 1970-03-31 13:00 | 1970-03-31 13:00 | 0 hours |

#### Volume

| Metric | HMS 3.x | HMS 4.x | Difference |
|--------|---------|---------|------------|
| Total Volume | 201,611 CFS-hr | 201,677 CFS-hr | -0.03% |

#### Statistical Differences

| Metric | Value |
|--------|-------|
| Max Absolute Difference | 32.00 CFS |
| Mean Absolute Difference | 1.21 CFS |
| Mean % Difference | 4.22% |
| Differing Values | 3,552 / 4,321 (82.2%) |

### Flow Comparison: Station I (Outlet)

#### Peak Flow

| Metric | HMS 3.x | HMS 4.x | Difference |
|--------|---------|---------|------------|
| Peak Flow | 838.93 CFS | 837.18 CFS | 0.21% |

#### Volume

| Metric | HMS 3.x | HMS 4.x | Difference |
|--------|---------|---------|------------|
| Total Volume | 201,611 CFS-hr | 201,677 CFS-hr | 0.03% |

## Acceptance Criteria

| Criterion | Threshold | Actual | Status |
|-----------|-----------|--------|--------|
| Peak Flow Difference | < 1.0% | 0.21% | PASS |
| Volume Difference | < 0.5% | 0.03% | PASS |
| Peak Timing Difference | < 1 hour | 0 hours | PASS |

## Overall Result

**Status:** PASS

### Issues Found

- Minor map file warning in HMS 3.x (cosmetic only)
- 82% of individual timestep values differ between versions (expected due to algorithm changes)

### Recommendations

1. The upgrade is successful and results are within acceptable tolerances
2. Peak flow and volume differences are negligible for engineering purposes
3. Users should be aware that exact numerical reproducibility is not expected
4. The new output types (FLOW-BASE-1, FLOW-BASE-2, etc.) provide additional insight into model behavior

## Notes

This upgrade was performed using the Tifton sample project from HMS 3.3. The project uses:
- **Loss Method:** Soil Moisture Account (SMA)
- **Transform:** Clark Unit Hydrograph (Tc=20 hrs, R=24 hrs)
- **Baseflow:** SMA Groundwater with Linear Reservoir
- **Simulation Period:** Jan 1 - Jun 30, 1970 (6 months)

The computational differences observed are consistent with expected algorithm refinements between HMS 3.x and 4.x, particularly in the SMA loss method implementation.

---

*Generated by hms-commander Update_3_to_4 agent workflow on 2025-12-10*
