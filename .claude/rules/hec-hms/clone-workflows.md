---
paths: hms_commander/**/*.py
---

# Clone Workflows (CLB Engineering LLM Forward)

## Philosophy

**CLB Engineering Approach**: Non-destructive, traceable, GUI-verifiable modifications

## Why Clone Instead of Modify?

### QAQC Requirement
Side-by-side comparison in HEC-HMS GUI is critical for validation:
- Open both baseline and updated models
- Compare parameter changes visually
- Verify results side-by-side
- Approve before committing final changes

### Traceability
Clone metadata captured in description:
```
Description: Cloned from 'Baseline' on 2024-01-15 14:30:00
```

### Safety
Original model preserved - can always revert if issues found.

## Clone Methods

### Basin Models

**API**: `HmsBasin.clone_basin(template, new_name, description=None, hms_object=None)`

**Example**: See `examples/clone_workflow.ipynb` cells 5-8

### Meteorologic Models

**API**: `HmsMet.clone_met(template, new_name, description=None, hms_object=None)`

### Control Specifications

**API**: `HmsControl.clone_control(template, new_name)`

### Runs

**API**: `HmsRun.clone_run(source_run, new_run_name, new_basin=None, new_met=None, ...)`

**Critical for QAQC**: Separate DSS output file for comparison

## Implementation Pattern

All clone methods follow same pattern:

1. **Read template** file
2. **Modify content** (name, description)
3. **Write new file**
4. **Update .hms project file** (new entry added)
5. **Return** (new component appears in GUI)

**Source**: `hms_commander/HmsUtils.py` - `clone_file()` and `update_project_file()`

## Project File Integration

Clone operations update `.hms` project file:

```
Basin File: Baseline.basin
Basin File: Updated_Basin.basin    # Added by clone
```

**Why**: Ensures cloned component appears in HEC-HMS GUI

## Typical Workflow

1. **Clone**: Create updated version
2. **Modify**: Change parameters in cloned version
3. **Run Both**: Execute baseline and updated
4. **Compare**: Side-by-side in GUI
5. **Validate**: Check differences meet acceptance criteria
6. **Decide**: Keep updated or revert to baseline
7. **Clean Up**: Remove unused versions

## GUI Verification

After cloning, verify in HEC-HMS:
1. Open project in HEC-HMS GUI
2. Navigate to Components > Basin Models (or Met Models, etc.)
3. Both original and clone should appear in list
4. Right-click > View to compare side-by-side

## Related

- **HmsBasin.clone_basin()**: hms_commander/HmsBasin.py
- **HmsMet.clone_met()**: hms_commander/HmsMet.py
- **HmsRun.clone_run()**: hms_commander/HmsRun.py
- **Example workflow**: examples/clone_workflow.ipynb
