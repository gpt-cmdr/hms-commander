Calibrate an HEC-HMS basin model by adjusting parameters to match observed flow data.

## Calibration Workflow

### Phase 1: Set Up Calibration Baseline

1. **Clone the basin** (non-destructive pattern):
   ```python
   from hms_commander import HmsBasin, hms

   HmsBasin.clone_basin("Baseline", "Calibration_v1", hms_object=hms)
   ```

2. **Clone the run** (separate DSS output for comparison):
   ```python
   from hms_commander import HmsRun

   HmsRun.clone_run("Baseline_Run", "Calibration_Run_v1",
                    new_basin="Calibration_v1",
                    new_dss="calibration_v1.dss")
   ```

3. **Run baseline** and extract observed vs. simulated:
   ```python
   from hms_commander import HmsCmdr, HmsDss
   HmsCmdr.compute_run("Calibration_Run_v1")
   ```

### Phase 2: Adjust Parameters

**Common calibration parameters**:

| Loss Method | Parameters | Effect |
|-------------|-----------|--------|
| SCS Curve Number | `curve_number` (0-100) | Volume calibration |
| Deficit-Constant | `initial_deficit`, `maximum_deficit`, `constant_rate` | Volume + recession |
| Initial-Constant | `initial_rate`, `constant_rate` | Rate calibration |

| Transform Method | Parameters | Effect |
|-----------------|-----------|--------|
| SCS Unit Hydrograph | `lag` (minutes) | Timing calibration |
| Clark UH | `time_of_concentration`, `storage_coefficient` | Shape calibration |

```python
from hms_commander import HmsBasin

# Adjust curve number
HmsBasin.set_loss_parameters(
    "Calibration_v1.basin", "SubbasinA",
    curve_number=82  # Increase → less volume
)

# Adjust lag time
HmsBasin.set_transform_parameters(
    "Calibration_v1.basin", "SubbasinA",
    lag=90  # minutes — increase → delayed peak
)
```

### Phase 3: Validate Against Acceptance Criteria

Apply Green/Yellow/Red verdict from `.claude/rules/hec-hms/critical-bugs-workarounds.md` Bug 5:

| Metric | GREEN | YELLOW | RED |
|--------|-------|--------|-----|
| Peak flow diff | < 1% | 1-5% | > 5% |
| Volume diff | < 0.5% | 0.5-2% | > 2% |
| Timing diff | ≤ 1 timestep | 2-3 timesteps | > 3 timesteps |

### Phase 4: Document Changes

Log every parameter change using MODELING_LOG.md format:
```markdown
### [YYYY-MM-DD HH:MM] - Loss - Curve Number Adjustment
- **Subbasin:** SubbasinA
- **Parameter:** curve_number
- **Old Value:** 75
- **New Value:** 82
- **Justification:** Simulated volume 15% below observed — CN increase improves match
- **Impact:** Expected peak increase ~12%, volume increase ~18%
```

## Reference

- Observed data loading: `HmsGage.py` docstrings
- DSS extraction: `.claude/skills/hms_extract_dss-results/SKILL.md`
- Clone workflows: `.claude/rules/hec-hms/clone-workflows.md`
- Acceptance criteria: `.claude/rules/hec-hms/critical-bugs-workarounds.md`
