---
name: hms_update_met-models
description: |
  Updates HEC-HMS meteorologic model files (.met) including precipitation methods,
  gage assignments, evapotranspiration, and Atlas 14 frequency storms. Use when
  configuring precipitation, assigning gages to subbasins, updating TP40 to Atlas 14,
  modifying ET methods, or cloning met models for scenario comparison.
  Trigger keywords: met model, precipitation, gage assignment, Atlas 14, TP40,
  frequency storm, evapotranspiration, ET, meteorologic model, update precip.
---

# Updating Meteorologic Models

## When This Skill Is Activated

You are the meteorologic model specialist. Route the user's request through the decision tree below.

## Decision Tree

1. **User wants to READ met configuration** → "Reading Met Configuration"
2. **User wants to MODIFY precipitation depths** → "Modifying Precipitation"
3. **User wants to ASSIGN gages** → "Gage Assignment"
4. **User wants Atlas 14 update** → "Atlas 14 Workflow"
5. **User wants to CLONE met for comparison** → Delegate to `hms_clone_components` skill
6. **Complex met automation** → Delegate to `met-model-specialist` agent

## Reading Met Configuration

1. Determine which `.met` file to work with
2. Read the precipitation method:
   ```python
   from hms_commander import HmsMet
   method = HmsMet.get_precipitation_method("project.met")
   ```
3. Read gage assignments:
   ```python
   assignments = HmsMet.get_gage_assignments("project.met")
   ```
4. Read current precipitation depths (for frequency storms):
   ```python
   depths = HmsMet.get_precipitation_depths("project.met")
   ```
5. Display results to the user

## Modifying Precipitation

1. Read current depths first — show the user what exists:
   ```python
   current = HmsMet.get_precipitation_depths("project.met")
   ```
2. Confirm the new values with the user
3. Apply the change:
   ```python
   HmsMet.set_precipitation_depths("project.met", [2.5, 3.1, 3.8, 4.5, 5.2, 6.0])
   ```
4. Re-read to verify: `HmsMet.get_precipitation_depths("project.met")`

## Gage Assignment

1. Read current assignments: `HmsMet.get_gage_assignments("project.met")`
2. Apply new assignment:
   ```python
   HmsMet.set_gage_assignment("project.met", "Subbasin1", "Gage1")
   ```
3. For bulk assignment:
   ```python
   for sub, gage in zip(subbasins, gages):
       HmsMet.set_gage_assignment("project.met", sub, gage)
   ```

## Atlas 14 Workflow

**Automated** (recommended): Delegate to the production agent at `.claude/agents/hms_atlas14/AGENT.md`

**Manual steps**:
1. Get project coordinates:
   ```python
   from hms_commander import HmsGeo
   lat, lon = HmsGeo.get_project_centroid_latlon("project.geo")
   ```
2. Download Atlas 14 depths from NOAA for those coordinates
3. Clone the met model first (preserve baseline):
   ```python
   HmsMet.clone_met("Baseline_Met", "Atlas14_Met", hms_object=hms)
   ```
4. Update the clone with Atlas 14 depths:
   ```python
   HmsMet.set_precipitation_depths("project/Atlas14_Met.met", atlas14_depths)
   ```
5. Clone the run to use the new met → delegate to `hms_clone_components` skill

## If Something Goes Wrong

- **Depths not updating**: Check that the met file uses a frequency storm method that stores depths
- **Gage not found**: Verify gage name matches exactly (case-sensitive)
- **Wrong met file**: If project has multiple met files, confirm which one the user intends

## Primary Sources

- `hms_commander/HmsMet.py` — Complete API
- `hms_agents/hms_atlas14/` — Automated Atlas 14 updates
- `.claude/rules/hec-hms/met-files.md` — Met file patterns

## Implementing Agent

For complex met model operations, delegate to:
`.claude/agents/met-model-specialist.md`

## Delegation Points

- **Run after updating** → `hms_execute_runs` skill
- **Clone for comparison** → `hms_clone_components` skill
- **Full Atlas 14 automation** → `.claude/agents/hms_atlas14/AGENT.md`
