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

**API**: `HmsControl.clone_control(template, new_name, hms_object=None)`

Control clones follow the same non-destructive contract as basin and
meteorologic clones. The destination `.control` file must not already exist;
an existing destination raises `FileExistsError` instead of being overwritten.

### Runs

**API**: `HmsRun.clone_run(source_run, new_run_name, new_basin=None, new_met=None, ...)`

**Critical for QAQC**: Separate DSS output file for comparison

## Implementation Pattern

All clone methods follow same pattern:

1. **Read template** file
2. **Modify content** (name, description)
3. **Write new file**
4. **Update .hms project file** (new component block added when a project is initialized)
5. **Return** (new component appears in GUI)

**Source**: `hms_commander/HmsUtils.py` - `clone_file()` and `update_project_file()`

## Project File Integration

Clone operations update the `.hms` project file when an initialized `HmsPrj`
object is supplied, or when the global `hms` object is initialized. After
registration, the project object is reinitialized so dataframes and GUI-visible
component lists include the clone immediately.

New Basin, Meteorology, and Control registrations are written as canonical HMS
component blocks:

```
Basin: Updated_Basin
     Filename: Updated_Basin.basin
     Description: Cloned from Baseline
     Last Modified Date: 15 January 2024
     Last Modified Time: 14:30:00
End:

Precipitation: Updated_Met
     Filename: Updated_Met.met
     Description: Cloned from Baseline
     Last Modified Date: 15 January 2024
     Last Modified Time: 14:30:00
End:

Control: Updated_Control
     FileName: Updated_Control.control
     Description:
End:
```

Legacy flat entries such as `Basin File:` and `Met File:` are still recognized
as already registered so compatibility projects are not duplicated during
idempotent updates.

**Why**: Ensures cloned components appear in HEC-HMS GUI without mutating the
original model component files.

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
