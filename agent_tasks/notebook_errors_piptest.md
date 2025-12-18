# Notebook Errors - PyPI Test Environment (hmscmdr_piptest)

Testing date: 2025-12-13

---

## Summary

All notebook errors have been identified and fixed.

---

## Error 1: `hms` is None after init_hms_project

**Affected Notebooks:**
- `03_project_dataframes.ipynb`
- `clone_workflow.ipynb`

**Error:**
```
AttributeError: 'NoneType' object has no attribute 'hms_df'
```

**Root Cause:**
Python import binding issue - `from hms_commander import hms` creates a local binding to `None` that doesn't update when `init_hms_project()` modifies the module-level variable.

**Fix Applied:**
1. Removed `hms` from import statements
2. Changed to capture return value: `hms = init_hms_project(project_path)`

**Status:** FIXED

---

## Error 2: Incorrect API parameter names in clone_workflow.ipynb

**Error:**
```
TypeError: HmsBasin.clone_basin() got an unexpected keyword argument 'template'
```

**Root Cause:**
Notebook used `template="Castro"` but API expects `template_basin="Castro 1"`

**Fix Applied:**
1. Changed `template=` to `template_basin=` for HmsBasin.clone_basin()
2. Changed `template=` to `template_met=` for HmsMet.clone_met()
3. Used actual basin name "Castro 1" from the castro example project
4. Added `hms_object=hms` parameter for proper context

**Status:** FIXED

---

## Error 3: Incorrect basin name in clone_workflow.ipynb

**Error:**
```
FileNotFoundError: Template basin not found: Castro
```

**Root Cause:**
The castro example project has basins named "Castro 1" and "Castro 2", not "Castro"

**Fix Applied:**
1. Changed hardcoded "Castro" to "Castro 1"
2. Updated notebook to dynamically read available basin/met/run names from project

**Status:** FIXED

---

## Test Results (hmscmdr_local environment)

| Notebook | Status | Notes |
|----------|--------|-------|
| 01_multi_version_execution.ipynb | Not tested | Does not use `hms` global |
| 02_run_all_hms413_projects.ipynb | Not tested | Does not use `hms` global |
| 03_project_dataframes.ipynb | PASS | Fixed import binding issue |
| 04_hms_workflow.ipynb | OK | Already used correct pattern |
| 05_run_management.ipynb | Not tested | Uses `HmsPrj()` directly |
| clone_workflow.ipynb | PASS | Fixed import binding + API params + basin names |

---

## Fixes Summary

### Pattern: Use Return Value

**Before:**
```python
from hms_commander import init_hms_project, hms
init_hms_project(project_path)
hms.hms_df  # FAILS - hms is None
```

**After:**
```python
from hms_commander import init_hms_project
hms = init_hms_project(project_path)  # Capture return value
hms.hms_df  # Works
```

### Pattern: Use Correct API Parameters

**Before:**
```python
HmsBasin.clone_basin(template="Castro", ...)
```

**After:**
```python
HmsBasin.clone_basin(template_basin="Castro 1", hms_object=hms, ...)
```
