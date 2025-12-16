---
paths: hms_commander/**/*.py
---

# Basin Model Operations

## Primary Sources

**Code**: `hms_commander/HmsBasin.py`
- Complete API with docstrings for all methods
- get_subbasins(), get_junctions(), get_reaches()
- get_loss_parameters(), set_loss_parameters()
- get_transform_parameters(), get_baseflow_parameters()
- clone_basin()

**Examples**: `examples/03_project_dataframes.ipynb`
- Cells 5-10: Basin workflow demonstration
- Accessing basin_df, filtering, analysis

**File Format**: `tests/projects/2014.08_HMS/File Parsing Guide/02_Basin_File.md`
- Complete .basin file structure
- Section-by-section breakdown
- Subbasin:, Junction:, Reach: formats

## Common Patterns

### Pattern 1: Read Basin Elements

```python
from hms_commander import HmsBasin

subbasins = HmsBasin.get_subbasins("project.basin")
junctions = HmsBasin.get_junctions("project.basin")
reaches = HmsBasin.get_reaches("project.basin")
```

**See docstrings** in `HmsBasin.py` for parameters, returns, exceptions.

### Pattern 2: Clone Basin (CLB Engineering LLM Forward)

```python
from hms_commander import init_hms_project, hms, HmsBasin

init_hms_project(r"C:\Projects\watershed")
HmsBasin.clone_basin("Baseline", "Updated_Basin", hms_object=hms)
```

**Result**: New basin appears in HEC-HMS GUI, original preserved

**Why Clone?**
- **Non-destructive**: Original basin untouched
- **Traceable**: Description updated with clone metadata
- **GUI-verifiable**: Side-by-side comparison in HEC-HMS GUI for QAQC
- **Critical for validation**: Compare baseline vs updated before committing

**Complete workflow**: `examples/clone_workflow.ipynb`

### Pattern 3: Modify Parameters

**Read first**:
```python
loss_params = HmsBasin.get_loss_parameters("project.basin", "Subbasin1")
```

**Then modify**:
```python
HmsBasin.set_loss_parameters(
    "project.basin",
    "Subbasin1",
    curve_number=85  # Update CN
)
```

## Decision: Clone vs Modify In-Place

**Use Clone When**:
- Testing parameter changes
- QAQC comparison needed
- Want to preserve baseline
- Multiple scenarios to compare

**Use Modify When**:
- Final production update
- Single definitive version
- No comparison needed

## File Format Reference

**Subbasin Section**:
```
Subbasin: SubbasinName
     Area: 123.45
     Downstream: JunctionName
     Loss: Deficit and Constant
     Percent Impervious: 10.0
     Initial Deficit: 25.4
     Maximum Deficit: 76.2
     Constant Rate: 2.54
End:
```

**Complete format**: See File Parsing Guide referenced above

## Related

- **Clone workflow**: .claude/rules/hec-hms/clone-workflows.md
- **Static classes**: .claude/rules/python/static-classes.md
- **File parsing**: .claude/rules/python/file-parsing.md
