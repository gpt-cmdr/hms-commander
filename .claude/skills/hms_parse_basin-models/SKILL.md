---
name: hms_parse_basin-models
description: |
  Parses HEC-HMS basin model files (.basin) to extract and modify subbasins, junctions,
  reaches, loss parameters, transform parameters, baseflow, and routing. Use when reading
  basin files, modifying hydrologic parameters, analyzing basin structure, updating
  curve numbers or lag times, bulk parameter updates via CSV, or setting up clone workflows.
  Handles all loss methods (Deficit & Constant, SCS CN, Green & Ampt), transform methods
  (SCS UH, Clark, ModClark), and routing methods (Muskingum, Lag, ModPuls).
  Trigger keywords: basin file, subbasin, junction, reach, loss method, curve number,
  transform, lag time, baseflow, routing, Muskingum, parse basin, get parameters,
  batch parameters, CSV export.
---

# Parsing Basin Models

## When This Skill Is Activated

You are the basin model parsing specialist. Route the user's request through the decision tree below.

## Decision Tree

1. **User wants to READ basin data** → "Reading Basin Components"
2. **User wants to MODIFY a single element** → "Modifying Parameters"
3. **User wants BATCH operations across all elements** → "Batch Parameter Management"
4. **User wants to CLONE for QAQC** → Delegate to `hms_clone_components` skill
5. **Complex multi-step basin analysis** → Delegate to `basin-model-specialist` agent

## Reading Basin Components

1. Determine which `.basin` file to work with — check `hms.basin_df` if project is initialized, or ask the user for a path
2. Call `HmsBasin.get_subbasins(basin_file)` to extract all subbasins as a DataFrame
3. Display the DataFrame to the user
4. If junctions or reaches are also needed, call `HmsBasin.get_junctions(basin_file)` and/or `HmsBasin.get_reaches(basin_file)`
5. For parameter details on a specific element, call the appropriate getter:
   - `HmsBasin.get_loss_parameters(basin_file, element_name)`
   - `HmsBasin.get_transform_parameters(basin_file, element_name)`
   - `HmsBasin.get_baseflow_parameters(basin_file, element_name)`
   - `HmsBasin.get_routing_parameters(basin_file, element_name)` (for reaches)

## Modifying Parameters

1. Read current values first — always show the user what exists before changing anything:
   ```python
   current = HmsBasin.get_loss_parameters(basin_file, element_name)
   ```
2. Show current values to the user and confirm the change
3. Apply the change:
   ```python
   HmsBasin.set_loss_parameters(basin_file, element_name, curve_number=85)
   ```
4. Re-read the file to verify the change took effect:
   ```python
   updated = HmsBasin.get_loss_parameters(basin_file, element_name)
   ```
5. If the user wants to run the simulation after → delegate to `hms_execute_runs` skill

**Available setters**: `set_loss_parameters()`, `set_transform_parameters()`, `set_baseflow_parameters()`, `set_routing_parameters()`

## Batch Parameter Management

1. Export current parameters to a DataFrame:
   ```python
   loss_df = HmsBasin.get_all_loss_parameters(basin_file)
   ```
2. If user wants CSV: `loss_df.to_csv("loss_params.csv")`
3. After the user edits the CSV/DataFrame, apply changes:
   ```python
   edited_df = pd.read_csv("loss_params.csv")
   HmsBasin.set_all_loss_parameters(basin_file, edited_df)
   ```
4. Verify by re-reading: `HmsBasin.get_all_loss_parameters(basin_file)`

**Available batch getters/setters**: `get_all_loss_parameters()` / `set_all_loss_parameters()`, same pattern for transform, baseflow, routing.

## Bulk Loop (Alternative to Batch)

For applying the same change to all elements:
```python
subbasins = HmsBasin.get_subbasins(basin_file)
for name in subbasins.index:
    HmsBasin.set_loss_parameters(basin_file, name, curve_number=85)
```

## If Something Goes Wrong

- **"Element not found"**: Check element name spelling against `get_subbasins()` output
- **Parameter not changing**: The file key is `LossRate:` not `Loss:` — if `loss_method` returns None, the parser may not be finding the block
- **Integer vs float mismatch**: Values like `1` in the file become `1.0` in DataFrames — use numeric comparison, not string

## Primary Sources

- `hms_commander/HmsBasin.py` — Complete API with docstrings
- `examples/03_project_dataframes.ipynb` — Basin operations
- `.claude/rules/hec-hms/basin-files.md` — Basin file patterns

## Implementing Agent

For complex multi-step basin analysis, delegate to:
`.claude/agents/basin-model-specialist.md`

## Delegation Points

- **Clone for QAQC** → `hms_clone_components` skill
- **Run after modifying** → `hms_execute_runs` skill
- **Modify met model too** → `hms_update_met-models` skill
- **Extract results after run** → `hms_extract_dss-results` skill
