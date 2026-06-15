# hms-commander

<p align="center">
  <img src="hms-commander_logo.svg" width=70%>
</p>

<p align="center">
  <strong>An open-source project of <a href="https://clbengineering.com/">CLB Engineering Corporation</a></strong><br>
  <em>LLM-Forward Engineering Solutions</em>
</p>

---

[![PyPI version](https://badge.fury.io/py/hms-commander.svg)](https://pypi.org/project/hms-commander/)
[![Documentation Status](https://img.shields.io/badge/docs-rascommander.info%2Fhms-1a365d)](https://rascommander.info/hms/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[📖 Full Documentation](https://rascommander.info/hms/)** | **[CLB Engineering](https://clbengineering.com/)**

> **Beta Software - Engineering Oversight Required**
>
> This library is in active development and should be used with caution. Many workflows have only been tested with HEC-HMS example projects, not production watersheds.
>
> **Real-world hydrologic modeling requires professional engineering judgment.** Every watershed has unique characteristics and nuances that automated workflows cannot fully capture. AI agent workflows are tools to assist engineers, not replace them.
>
> **Human-in-the-Loop is essential.** Licensed Professional Engineers must pilot these systems, guide their application, and verify all outputs before use in engineering decisions. Always validate results against established engineering practices and local knowledge.

## Why HMS Commander?

**HMS→RAS linked models are an industry standard** for watershed-to-river hydraulic analysis, yet there is no straightforward way to automate the linkage between HEC-HMS (hydrology) and HEC-RAS (hydraulics).

This library exists to **bridge that gap**—extending the [ras-commander](https://github.com/gpt-cmdr/ras-commander) effort for HEC-RAS automation to include HEC-HMS workflows. While HEC-HMS provides robust internal functionality for standalone hydrologic models, the real power emerges when HMS hydrographs flow into RAS hydraulic models for flood inundation mapping, bridge analysis, and infrastructure design.

**HMS Commander enables:**
- Automated HMS simulation execution and results extraction
- DSS file operations for seamless HMS→RAS boundary condition transfer
- Atlas 14, Frequency Storm, and SCS Type storm generation with DataFrame outputs
- AORC download, DSS grid conversion, grid-definition, and HRAP cell mapping helpers
- TauDEM-derived HMS basin/scaffold assembly and validation workflows
- Consistent API patterns across both HMS and RAS automation
- LLM-assisted workflows for complex multi-model scenarios

**LLM Forward Hydrologic Modeling Automation**

A Python library for automating HEC-HMS operations, built using [CLB Engineering's LLM Forward Approach](https://clbengineering.com/llm-forward). Within two years, CLB Engineering built the **most robust and feature-complete HEC-RAS and HEC-HMS automation solution on the open internet** using LLM Forward approaches -- proving that licensed professional engineers working alongside Large Language Models can create extraordinary value in compressed timeframes.

## LLM Forward Approach

<a href="https://clbengineering.com/">
  <img src="docs/assets/CLBEngineeringHzLogo.png" alt="CLB Engineering Corporation" width="280" align="right" style="margin-left: 16px; margin-bottom: 8px;">
</a>

This library was developed using the **[LLM Forward](https://clbengineering.com/llm-forward)** approach -- a framework pioneered by [CLB Engineering Corporation](https://clbengineering.com/) for responsible adoption of Large Language Models in professional engineering practice. LLM Forward places professional responsibility first while positioning LLMs forward to accelerate insight and automation.

**Core Tenets:**
- **Professional Responsibility First** -- Public safety, ethics, and licensure remain paramount
- **LLMs Forward (Not First)** -- Technology accelerates engineering insight without replacing professional judgment
- **Multi-Level Verifiability** -- HEC-HMS GUI review + visual outputs + code audit trails
- **Human-in-the-Loop** -- Licensed professionals in responsible charge at all times

See the [CLB Engineering LLM Forward Approach](docs/CLB_ENGINEERING_APPROACH.md) for full philosophy and best practices.

## ⚠️ Breaking Changes in v0.2.0

**Precipitation hyetograph methods now return DataFrame instead of ndarray**

If upgrading from v0.1.x, note that `Atlas14Storm`, `FrequencyStorm`, and `ScsTypeStorm` now return `pd.DataFrame` with columns `['hour', 'incremental_depth', 'cumulative_depth']` instead of `np.ndarray`.

**Quick Migration:**
```python
# OLD (v0.1.x)
hyeto = Atlas14Storm.generate_hyetograph(total_depth_inches=17.0, ...)
total = hyeto.sum()
peak = hyeto.max()

# NEW (v0.2.0+)
hyeto = Atlas14Storm.generate_hyetograph(total_depth_inches=17.0, ...)
total = hyeto['cumulative_depth'].iloc[-1]
peak = hyeto['incremental_depth'].max()
```

**Why this change?** Standardizes API for HMS→RAS integration and includes time axis.

See [CHANGELOG.md](CHANGELOG.md) for complete migration guide.

## Features

- **Project Management**: Initialize and manage HEC-HMS projects with DataFrames
- **File Operations**: Read and modify basin, met, control, and gage files
- **Simulation Execution**: Run HEC-HMS via Jython scripts (single, batch, parallel)
- **Results Analysis**: Extract peak flows, volumes, hydrograph statistics
- **DSS Integration**: Read/write DSS files (via ras-commander)
- **GIS Extraction**: Export model elements to GeoJSON
- **Clone Operations**: Non-destructive model cloning for QAQC workflows

## Current TauDEM/HMS Status

The repo now includes a full Spring Creek benchmark path for:

- gauge-first study packaging and report/data-gap regeneration
- direct TauDEM preprocessing and delineation manifests
- watershed verification and boundary handoff selection
- TauDEM-to-HMS basin/scaffold assembly with SQLite geometry
- clone-first HEC-HMS parser-of-record round-trip validation
- Atlas 14 storm bootstrap and a live compute demonstration

That workflow is now import-valid and compute-valid, but it is not yet production-ready. The first live HMS run still surfaces residual modeling warnings that must be handled deliberately: missing ET/canopy methods, Muskingum stability warnings, lag-vs-time-step warnings, and negative inflow clipping. The current roadmap therefore adds three gating items before generated HMS projects should be promoted as defensible engineering setups:

- a machine-readable pre-HMS readiness gate
- TauDEM parameter sensitivity / optimization support for delineation controls
- a human-review QAQC bundle and explicit signoff workflow

## Installation

### From PyPI (Recommended)

```bash
# Create conda environment (recommended)
conda create -n hms python=3.11
conda activate hms

# Install hms-commander
pip install hms-commander

# Verify installation
python -c "import hms_commander; print(hms_commander.__version__)"
```

### Optional Dependencies

```bash
# DSS file support (requires Java 8+)
pip install hms-commander[dss]

# GIS features (geopandas, shapely)
pip install hms-commander[gis]

# All optional features
pip install hms-commander[all]
```

### From Source (Development)

```bash
# Clone repository
git clone https://github.com/gpt-cmdr/hms-commander.git
cd hms-commander

# Create development environment
conda create -n hmscmdr_local python=3.11
conda activate hmscmdr_local

# Install in editable mode with all dependencies
pip install -e ".[all]"

# Verify using local copy
python -c "import hms_commander; print(hms_commander.__file__)"
# Should show: /path/to/hms-commander/hms_commander/__init__.py
```

## Quick Start

```python
from hms_commander import (
    init_hms_project, hms,
    HmsBasin, HmsControl, HmsCmdr, HmsResults
)

# Initialize project
init_hms_project(
    r"C:/HMS_Projects/MyProject",
    hms_exe_path=r"C:/HEC/HEC-HMS/4.9/hec-hms.cmd"
)

# View project data
print(hms.basin_df)
print(hms.run_df)

# Run simulation
success = HmsCmdr.compute_run("Run 1")

# Extract results
peaks = HmsResults.get_peak_flows("results.dss")
print(peaks)
```

## Example Notebooks

Comprehensive Jupyter notebooks demonstrating workflows:

| Notebook | Description |
|----------|-------------|
| [00_overview.ipynb](examples/00_overview.ipynb) | Environment verification, HMS glossary, and learning path |
| [01_basic_workflow.ipynb](examples/01_basic_workflow.ipynb) | Initialize a project, run HMS, and inspect results |
| [02_project_dataframes.ipynb](examples/02_project_dataframes.ipynb) | Explore project DataFrames and component structure |
| [05_clone_workflow.ipynb](examples/05_clone_workflow.ipynb) | Non-destructive QAQC with model cloning |
| [10_atlas14_hyetograph.ipynb](examples/10_atlas14_hyetograph.ipynb) | Generate NOAA Atlas 14 design storms |
| [11_frequency_storm.ipynb](examples/11_frequency_storm.ipynb) | Generate TP-40/Hydro-35 frequency storms |
| [14a_aorc_download.ipynb](examples/14a_aorc_download.ipynb) | Download AORC precipitation from NOAA AWS |
| [21_taudem_to_hms_atlas14.ipynb](examples/21_taudem_to_hms_atlas14.ipynb) | Build and validate a TauDEM-derived HMS bootstrap |

See [docs/examples/overview.md](docs/examples/overview.md) for the full notebook catalog.

**Run Configuration Management**:
```python
from hms_commander import HmsRun

# Modify run parameters with validation
HmsRun.set_description("Run 1", "Updated scenario", hms_object=hms)
HmsRun.set_basin("Run 1", "Basin_Model", hms_object=hms)  # Validates component exists!
HmsRun.set_dss_file("Run 1", "output.dss", hms_object=hms)

# Prevents HMS from auto-deleting runs with invalid component references
```

See [04_run_management.ipynb](examples/04_run_management.ipynb) for complete examples.

## Library Structure

| Class | Purpose |
|-------|---------|
| `HmsPrj` | Project manager (stateful singleton) |
| `HmsBasin` | Basin model operations (.basin) |
| `HmsControl` | Control specifications (.control) |
| `HmsMet` | Meteorologic models (.met) |
| `HmsGage` | Time-series gages (.gage) |
| `HmsRun` | Run configuration management (.run) |
| `HmsCmdr` | Simulation execution engine |
| `HmsJython` | Jython script generation |
| `HmsOutput` | Compute output and HMS log parsing |
| `DssCore`, `HmsDss`, `HmsDssGrid` | DSS time-series, paired-data, catalog, and grid operations |
| `HmsResults` | Results extraction & analysis |
| `HmsGeo`, `HmsHuc`, `HmsAorc`, `HmsGrid`, `HmsTauDEM` | GIS, HUC, AORC, grid, and TauDEM workflows |
| `Atlas14Storm`, `FrequencyStorm`, `ScsTypeStorm` | Design-storm hyetograph generation |
| `HmsExamples`, `HmsM3Model`, `HmsUtils` | Example project, M3 model, and utility functions |

## Key Methods

### Project Management
```python
init_hms_project(path, hms_exe_path)  # Initialize project
hms.basin_df                           # Basin models DataFrame
hms.run_df                             # Simulation runs DataFrame
```

### Basin Operations
```python
HmsBasin.get_subbasins(basin_path)                    # Get all subbasins
HmsBasin.get_loss_parameters(basin_path, subbasin)    # Get loss params
HmsBasin.set_loss_parameters(basin_path, subbasin, curve_number=80)
```

### Run Configuration
```python
HmsRun.set_description("Run 1", "Updated scenario", hms_object=hms)
HmsRun.set_basin("Run 1", "Basin_Model", hms_object=hms)  # Validates!
HmsRun.set_precip("Run 1", "Met_Model", hms_object=hms)   # Validates!
HmsRun.set_control("Run 1", "Control_Spec", hms_object=hms)  # Validates!
HmsRun.set_dss_file("Run 1", "output.dss", hms_object=hms)
```

### Simulation Execution
```python
HmsCmdr.compute_run("Run 1")                          # Single run
HmsCmdr.compute_parallel(["Run 1", "Run 2"], max_workers=2)  # Parallel
HmsCmdr.compute_batch(["Run 1", "Run 2", "Run 3"])    # Sequential
```

### Results Analysis
```python
HmsResults.get_peak_flows("results.dss")              # Peak flow summary
HmsResults.get_volume_summary("results.dss")          # Runoff volumes
HmsResults.get_hydrograph_statistics("results.dss", "Outlet")
HmsResults.compare_runs(["run1.dss", "run2.dss"], "Outlet")
```

### DSS Operations
```python
HmsDss.get_catalog("results.dss")                     # List all paths
HmsDss.read_timeseries("results.dss", pathname)       # Read time series
HmsDss.extract_hms_results("results.dss", result_type="flow")
```

## Requirements

- Python 3.10+
- pandas, numpy, tqdm, requests

### Optional
- **DSS**: ras-commander, pyjnius (Java 8+)
- **GIS**: geopandas, pyproj, shapely

## Related Projects

- [ras-commander](https://github.com/gpt-cmdr/ras-commander) - HEC-RAS automation
- [HEC-HMS](https://www.hec.usace.army.mil/software/hec-hms/) - USACE software

## Partner with CLB Engineering

**For Agencies & Government Organizations:** Looking to modernize your HEC-HMS workflows? CLB Engineering Corporation created hms-commander and pioneered LLM Forward engineering. As early LLM pioneers in civil engineering, CLB delivers extraordinary value in compressed timeframes. [Contact CLB](https://clbengineering.com/) to bring this expertise to your organization's toughest H&H challenges.

**For Engineering Firms:** Need a technology partner for your next H&H proposal or joint venture? CLB Engineering brings unmatched HEC-HMS automation expertise. With the hms-commander and ras-commander libraries, CLB can dramatically accelerate model development, calibration, and QA/QC workflows. Partner with the engineers who wrote the automation.

**Building on HMS Commander?** If you are building products or workflows on top of hms-commander, please cite the library and provide a link to the [GitHub repository](https://github.com/gpt-cmdr/hms-commander). Acknowledgment of CLB Engineering Corporation as the library's creator is appreciated.

## Author

**William Katzenmeyer, P.E., C.F.M.** - [CLB Engineering Corporation](https://clbengineering.com/)

## License

This software is released under the MIT license. HMS Commander is a free and open-source project of [CLB Engineering Corporation](https://clbengineering.com/).

## Contact

For questions, suggestions, or support, please contact:
William Katzenmeyer, P.E., C.F.M. - info@clbengineering.com
[CLB Engineering Corporation](https://clbengineering.com/) | [LLM Forward Engineering](https://clbengineering.com/llm-forward)
