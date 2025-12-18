# CLAUDE.md

This file provides guidance to Claude Code when working with hms-commander.

---

## Project Overview

**hms-commander** is a Python library for automating HEC-HMS (Hydrologic Engineering Center's Hydrologic Modeling System) operations. It provides a comprehensive API for interacting with HEC-HMS project files, executing simulations, and processing results, following the architectural patterns established by ras-commander.

---

## Development Environment

### Package Management
- **Agent scripts and tools**: Use `uv` for installation, `python` for execution
- **User-facing docs**: Use `pip` for broader compatibility
- **Fast installation**: `uv pip install -e ".[all]"` (10-100x faster than pip)

### Build Commands
- **Install locally**: `pip install -e .` (for development)
- **Install from build**: `pip install hms-commander`
- **Install with optional dependencies**: `pip install -e ".[all]"` (includes dev, gis, dss)

### Dependencies
- **Python**: Requires 3.10+
- **Core packages**: pandas, numpy, pathlib, tqdm, requests
- **Optional GIS**: geopandas, pyproj, shapely
- **Optional DSS**: ras-commander, pyjnius

### Testing Environments (Conda)
- **hmscmdr_local**: Local development version (use when making code changes)
  - `conda create -n hmscmdr_local python=3.11`
  - `conda activate hmscmdr_local && pip install -e ".[all]"`
  - Editable install, changes immediately reflected in notebooks

- **hmscmdr_pip**: Published package version (use for release validation)
  - `conda create -n hmscmdr_pip python=3.11`
  - `conda activate hmscmdr_pip && pip install hms-commander`
  - Matches end-user experience

**See**: `.claude/rules/project/development-environment.md` for complete testing protocols

---

## Architecture Overview

### Core Classes

**File Operations**: HmsBasin, HmsMet, HmsControl, HmsGage, HmsRun, HmsGeo
**Execution**: HmsCmdr, HmsJython
**Data**: HmsDss, HmsResults
**Utilities**: HmsUtils, HmsExamples
**Project**: HmsPrj (initialization and multi-project support)

### Key Architectural Patterns

**Static Classes**: All core classes use static methods, no instantiation required.
See: `.claude/rules/python/static-classes.md`

**File Parsing**: Shared HmsFileParser eliminates duplication.
See: `.claude/rules/python/file-parsing.md`

**Clone Workflows**: Non-destructive, traceable, GUI-verifiable (CLB Engineering approach).
See: `.claude/rules/hec-hms/clone-workflows.md`

---

## Quick Start

### Initialize and Execute

```python
from hms_commander import init_hms_project, HmsCmdr

init_hms_project(r"C:\Projects\watershed")
HmsCmdr.compute_run("Run 1")
```

### Access Project Data

```python
from hms_commander import hms

# After initialization, access dataframes
subbasins = hms.basin_df
met_models = hms.met_df
runs = hms.run_df
```

### Direct File Operations (No Initialization)

```python
from hms_commander import HmsBasin, HmsMet

subbasins = HmsBasin.get_subbasins("project.basin")
HmsMet.set_gage_assignment("project.met", "Sub1", "Gage1")
```

---

## Detailed Documentation

### For Complete API

**Code**: `hms_commander/*.py` - All classes have comprehensive docstrings
**Examples**: `examples/*.ipynb` - Working demonstrations
**API Docs**: `docs/api/*.md` - Generated reference
**File Formats**: `tests/projects/2014.08_HMS/File Parsing Guide/` - HMS file structures

### For Patterns and Workflows

**See**: `.claude/rules/` for organized knowledge:

**Python Patterns** (`.claude/rules/python/`):
- static-classes.md - Core HMS pattern
- file-parsing.md - HmsFileParser utilities
- constants.md - Centralized magic numbers
- decorators.md, path-handling.md, error-handling.md, naming-conventions.md

**HMS Domain Knowledge** (`.claude/rules/hec-hms/`):
- execution.md - HmsCmdr, HmsJython, version detection
- basin-files.md - HmsBasin operations
- met-files.md - HmsMet operations
- control-files.md - HmsControl operations
- dss-operations.md - HmsDss, HmsResults
- clone-workflows.md - CLB Engineering LLM Forward approach
- version-support.md - HMS 3.x vs 4.x differences

**Testing** (`.claude/rules/testing/`):
- example-projects.md - HmsExamples usage
- tdd-approach.md - No mocks, use real HMS projects

---

## Key Principles

### 1. Static Classes, No Instantiation

```python
# ✅ Correct
HmsBasin.get_subbasins("project.basin")

# ❌ Wrong
basin = HmsBasin()  # Don't do this
```

### 2. Test with Real Projects, Not Mocks

```python
from hms_commander import HmsExamples, HmsBasin

HmsExamples.extract_project("tifton")  # Real HMS project
subbasins = HmsBasin.get_subbasins("tifton/tifton.basin")
```

### 3. HMS Version Awareness

**HMS 3.x (32-bit)**: Requires `python2_compatible=True`
**HMS 4.x (64-bit)**: Default Python 3 syntax

See: `.claude/rules/hec-hms/version-support.md`

### 4. Clone for QAQC

Non-destructive workflows enable side-by-side comparison in HEC-HMS GUI.

See: `.claude/rules/hec-hms/clone-workflows.md`

---

## Differences from ras-commander

| Aspect | ras-commander | hms-commander |
|--------|---------------|---------------|
| Primary Files | .prj, .p##, .g##, .hdf | .hms, .basin, .met, .control |
| Results Format | HDF5 | DSS (via RasDss) |
| Execution | Subprocess (Ras.exe) | Jython scripts (hec-hms.cmd) |
| Project Discovery | .prj file | .hms file |
| Data Storage | HDF groups/datasets | ASCII text sections |
| Parsing Approach | h5py library | Regex/text parsing |

**Integration**: hms-commander uses ras-commander's RasDss for DSS operations (no code duplication).

---

## Cross-Repository Integration: HMS→RAS Workflows

**hms-commander** and **ras-commander** work together for integrated watershed-to-river modeling.

### Workflow Pattern

```
HEC-HMS (Watershed)          HEC-RAS (River)
    ↓                            ↓
Precipitation                Geometry
    ↓                            ↓
Runoff Generation        ←─── Import HMS Flows
    ↓                            ↓
DSS Output               Hydraulic Analysis
```

### HMS Responsibilities (This Library)

1. **Generate Hydrographs**: Execute simulations, create DSS results
2. **Extract Flows**: Use HmsResults to get peak flows and time series
3. **Document Spatial Reference**: Use HmsGeo to provide outlet locations
4. **Validate Quality**: Check peaks, volumes, time series completeness

```python
from hms_commander import init_hms_project, HmsCmdr, HmsResults, HmsGeo

# Execute HMS
init_hms_project("watershed")
HmsCmdr.compute_run("Design_Storm")

# Extract for RAS
flows = HmsResults.get_outflow_timeseries(dss_file, "Outlet")
lat, lon = HmsGeo.get_project_centroid_latlon("project.geo")

# Handoff: DSS file, pathname, outlet location
```

### RAS Responsibilities (ras-commander)

1. **Import HMS DSS**: Use RasUnsteady to import boundary conditions
2. **Spatial Matching**: Match HMS outlets to RAS cross sections
3. **Hydraulic Analysis**: Run unsteady flow with HMS upstream BCs
4. **Validation**: Compare HMS peaks vs RAS peaks

### Shared Infrastructure

**RasDss**: Both libraries use the same DSS operations
- HMS: `HmsDss` (wraps RasDss)
- RAS: `RasDss` (direct)
- Result: No format conversion, consistent pathnames

### Skills and Subagents

- **Skill**: `.claude/skills/linking-hms-to-hecras/` - HMS side workflow
- **Skill** (ras-commander): `importing-hms-boundaries/` - RAS side workflow
- **Subagent**: `.claude/agents/hms-ras-workflow-coordinator.md` - Coordinates both sides
- **Rules**: `.claude/rules/integration/hms-ras-linking.md` - Integration patterns

See these files for complete HMS→RAS integration workflows.

---

## Common Pitfalls to Avoid

- ❌ Don't instantiate static classes like `HmsBasin()`
- ❌ Don't use mocks in tests - use `HmsExamples.extract_project()`
- ❌ Don't forget `python2_compatible=True` for HMS 3.x
- ✅ Always specify `hms_object` when working with multiple projects
- ✅ Use pathlib.Path for all path operations
- ✅ Handle file encodings (UTF-8 with Latin-1 fallback)

---

## Navigation

### Primary Sources (Authoritative)
- **Code**: `hms_commander/*.py` (docstrings)
- **Examples**: `examples/*.ipynb` (workflows)
- **File Formats**: `tests/projects/.../File Parsing Guide/`
- **API Docs**: `docs/api/*.md`

### Framework Documentation
- **Patterns**: `.claude/rules/python/`
- **HMS Knowledge**: `.claude/rules/hec-hms/`
- **Testing**: `.claude/rules/testing/`
- **Documentation**: `.claude/rules/documentation/`

### Task Coordination
- **Memory**: `.agent/` (multi-session state)
- **Agents**: `hms_agents/` (production workflows)
- **Research**: `feature_dev_notes/` (feature development)

### Complete Framework
See: `.claude/CLAUDE.md` for hierarchical knowledge organization
