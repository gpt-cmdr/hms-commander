---
paths: hms_commander/**/*.py
---

# Naming Conventions

## Standard Python Conventions

| Construct | Convention | Example |
|-----------|-----------|---------|
| Classes | `PascalCase` | `HmsBasin`, `HmsMet`, `HmsControl` |
| Functions/methods | `snake_case` | `get_subbasins`, `clone_basin` |
| Variables | `snake_case` | `basin_path`, `run_name` |
| Constants | `UPPER_SNAKE_CASE` | `PRIMARY_ENCODING`, `FILE_EXTENSIONS` |
| Private helpers | `_snake_case` | `_get_hms_object`, `_parse_block` |
| Module files | `PascalCase.py` | `HmsBasin.py`, `HmsMet.py` |

## HMS Class Naming

All file-operation classes follow `Hms<Component>` pattern:

```
HmsBasin    → .basin file operations
HmsMet      → .met file operations
HmsControl  → .control file operations
HmsGage     → .gage file operations
HmsRun      → .run file operations
HmsGeo      → .geo / geographic files
HmsDss      → DSS data read/write
HmsResults  → Post-run results analysis
HmsCmdr     → High-level execution API
HmsJython   → Jython script generation
HmsUtils    → Utility functions
HmsExamples → Example project management
HmsPrj      → Project state (the one instantiated class)
```

## Method Naming Patterns

```python
# Read operations
get_subbasins(basin_path)         # Returns dict of all subbasins
get_loss_parameters(basin_path, name)  # Returns dict for one element
get_project_name(hms_path)        # Returns string

# Write operations
set_loss_parameters(basin_path, name, **kwargs)
update_parameter(basin_path, name, param, value)

# Creation operations
clone_basin(template, new_name, ...)
clone_met(template, new_name, ...)
clone_run(source_run, new_name, ...)

# Execution operations
compute_run(run_name, hms_object=None)
execute_all_runs(hms_object=None)
```

## Approved Abbreviations

These abbreviations are used consistently throughout hms-commander:

| Abbreviation | Meaning |
|-------------|---------|
| `hms` | HEC-HMS project object / global singleton |
| `prj` | Project |
| `cntr` | Control (specification) |
| `met` | Meteorologic model |
| `dss` | Data Storage System (HEC-DSS file) |
| `cmdr` | Commander |
| `exec` | Execution |
| `cfg` | Configuration |
| `df` | DataFrame (pandas) |
| `clb` | CLB Engineering (company) |

## File/Directory Naming

```
# Python modules: PascalCase
hms_commander/HmsBasin.py
hms_commander/HmsMet.py

# Production agent directories: python_case (PEP 8), inside .claude/agents/
.claude/agents/update_3_to_4/
.claude/agents/hms_doc_query/
.claude/agents/hms_atlas14/

# Agent spec files: kebab-case
.claude/agents/basin-model-specialist.md
.claude/agents/met-model-specialist.md

# Example notebooks: NN_description_snake_case.ipynb
examples/01_multi_version_execution.ipynb
examples/03_project_dataframes.ipynb
```

## Related

- **Static classes**: `.claude/rules/python/static-classes.md`
- **Agent naming**: CLAUDE.md "Agent Naming Conventions" section
