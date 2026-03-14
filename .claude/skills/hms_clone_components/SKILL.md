---
name: hms_clone_components
description: |
  Clones HEC-HMS components (basins, met models, control specs, runs) using the
  CLB Engineering LLM Forward approach. Creates non-destructive, traceable, GUI-verifiable
  copies for QAQC comparison, scenario analysis, and parameter sensitivity testing.
  Use when creating alternative scenarios, setting up QAQC workflows, comparing baseline
  vs updated models, preserving originals while testing modifications, Atlas 14
  precipitation updates (keep TP40 baseline), or model calibration with different
  parameter sets. All clones appear in HEC-HMS GUI with separate DSS outputs for
  side-by-side comparison.
  Trigger keywords: clone, duplicate, copy, QAQC, scenario, alternative, baseline,
  comparison, side-by-side, non-destructive, traceable.
---

# Cloning HMS Components

## When This Skill Is Activated

You are the HMS cloning specialist. Follow the CLB Engineering LLM Forward approach: Non-Destructive, Traceable, GUI-Verifiable.

## Decision Tree

1. **User wants a simple component clone** → "Clone a Component"
2. **User wants a full QAQC workflow** → "QAQC Clone Workflow"
3. **User wants parameter sensitivity analysis** → "Sensitivity Analysis"
4. **Complex multi-component scenario** → Delegate to `basin-model-specialist` agent

## Clone a Component

The project MUST be initialized first:
```python
from hms_commander import init_hms_project, hms
init_hms_project("project")
```

Then clone the component the user needs:

**Basin**:
```python
HmsBasin.clone_basin("Baseline", "Updated_Basin",
    description="Updated with Atlas 14 precip", hms_object=hms)
```

**Met model**:
```python
HmsMet.clone_met("Baseline_Met", "Atlas14_Met",
    description="Updated to Atlas 14 depths", hms_object=hms)
```

**Control spec**:
```python
HmsControl.clone_control("Jan2020", "Jun2020",
    description="Extended to June 2020", hms_object=hms)
```

**Run** (most important — always specify separate DSS):
```python
HmsRun.clone_run("Baseline", "Updated",
    new_basin="Updated_Basin", new_met="Atlas14_Met",
    output_dss="results_updated.dss",
    description="Atlas 14 update QAQC", hms_object=hms)
```

**Critical**: Always specify `output_dss` for cloned runs — separate DSS files enable side-by-side comparison.

## QAQC Clone Workflow

Follow these steps in order:

1. **Initialize project**: `init_hms_project("project")`
2. **Clone the component being modified** (basin or met):
   ```python
   HmsMet.clone_met("Baseline_Met", "Atlas14_Met", hms_object=hms)
   ```
3. **Modify the clone** (not the original):
   ```python
   HmsMet.set_precipitation_depths("project/Atlas14_Met.met", new_depths)
   ```
4. **Clone the run** with new component + separate DSS:
   ```python
   HmsRun.clone_run("Baseline", "Atlas14_Update",
       new_met="Atlas14_Met", output_dss="results_atlas14.dss", hms_object=hms)
   ```
5. **Execute both runs**:
   ```python
   HmsCmdr.compute_parallel(["Baseline", "Atlas14_Update"])
   ```
6. **Compare results** → delegate to `hms_extract_dss-results` skill

## Sensitivity Analysis

For parameter sweeps:
```python
for cn in [70, 75, 80, 85, 90]:
    HmsBasin.clone_basin("Baseline", f"CN{cn}", hms_object=hms)
    HmsBasin.set_loss_parameters(f"project/CN{cn}.basin", "Sub1", curve_number=cn)
    HmsRun.clone_run("Baseline_Run", f"Run_CN{cn}",
        new_basin=f"CN{cn}", output_dss=f"results_cn{cn}.dss", hms_object=hms)

HmsCmdr.compute_parallel([f"Run_CN{cn}" for cn in [70, 75, 80, 85, 90]])
```

## CLB Engineering Principles

- **Non-Destructive**: Never modify the original — always clone first
- **Traceable**: Use `description` parameter to document why the clone was made
- **GUI-Verifiable**: All clones appear in HMS GUI immediately for visual review

## If Something Goes Wrong

- **Clone not appearing in HMS GUI**: Re-initialize the project or restart HMS
- **Run disappears after opening in HMS**: Components referenced in the run must exist — validate before cloning the run
- **DSS collision**: Two runs writing to the same DSS file corrupt results — always use separate DSS files

## Primary Sources

- `hms_commander/HmsBasin.py#clone_basin()`, `HmsMet.py#clone_met()`
- `hms_commander/HmsControl.py#clone_control()`, `HmsRun.py#clone_run()`
- `.claude/rules/hec-hms/clone-workflows.md` — CLB Engineering approach

## Implementing Agent

For complex multi-step scenarios, delegate to:
`.claude/agents/basin-model-specialist.md`

## Delegation Points

- **Modify cloned basins** → `hms_parse_basin-models` skill
- **Modify cloned met models** → `hms_update_met-models` skill
- **Run cloned scenarios** → `hms_execute_runs` skill
- **Compare cloned results** → `hms_extract_dss-results` skill
