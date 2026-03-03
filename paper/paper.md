---
title: 'HMS-Commander: A Python Library for Automating HEC-HMS Hydrologic Modeling Workflows'
tags:
  - Python
  - hydrology
  - hydrologic modeling
  - HEC-HMS
  - water resources
  - flood analysis
  - automation
  - DSS
authors:
  - name: William Mark Katzenmeyer
    orcid: 0009-0003-2907-1906
    affiliation: 1
    corresponding: true
affiliations:
  - name: CLB Engineering, Inc., Bethany, Connecticut, United States
    index: 1
date: 3 March 2026
bibliography: paper.bib
---

# Summary

HMS-Commander is an open-source Python library that provides a programmatic interface for
automating the U.S. Army Corps of Engineers' Hydrologic Modeling System (HEC-HMS). HEC-HMS
is the standard-of-practice software for watershed hydrology in the United States, used by
federal agencies, state departments of transportation, and private engineering firms to
simulate precipitation-runoff processes for flood forecasting, infrastructure design, and
floodplain management [@Scharffenberg2024; @Feldman2000]. Despite its widespread adoption,
HEC-HMS lacks a native Python API, requiring engineers to interact with the software
exclusively through its graphical user interface (GUI) or through Jython scripts executed
within the HMS Java runtime.

HMS-Commander addresses this gap by providing static-method classes that parse and modify
HMS project files (`.basin`, `.met`, `.control`, `.gage`, `.run`), execute simulations via
generated Jython scripts, extract results from HEC-DSS output files, and export model
geometry to GIS formats. The library supports both HMS 3.x (32-bit, Jython 2.5) and
HMS 4.x (64-bit, Jython 2.7/Python 3) versions, enabling workflows across legacy and
current model archives. HMS-Commander integrates with its companion library ras-commander
[@Katzenmeyer2024] to support end-to-end watershed-to-river modeling pipelines where HMS
hydrographs serve as upstream boundary conditions for HEC-RAS hydraulic simulations.

# Statement of Need

Hydrologic engineers routinely manage HEC-HMS projects containing dozens of subbasins,
multiple meteorologic scenarios, and numerous simulation runs. Common tasks---updating curve
numbers across all subbasins, comparing results between storm frequencies, or preparing
boundary conditions for downstream hydraulic models---require repetitive manual interaction
with the HMS GUI. This manual workflow is error-prone, difficult to reproduce, and does not
scale to the batch processing, sensitivity analysis, or uncertainty quantification demands of
modern water resources practice.

The need for HMS automation is well documented. The U.S. Army Engineer Research and
Development Center (ERDC) developed a Python wrapper for HEC-HMS to support gridded model
initialization and calibration [@Nwachukwu2022], demonstrating the demand for programmatic
access. The HEC-HMS development team added Jython scripting support in version 4.4.1,
acknowledging the need for automation [@USACE_Jython]. However, Jython scripts operate within
the HMS Java Virtual Machine, lack access to the Python scientific computing ecosystem
(NumPy, pandas, SciPy), and require manual construction of script files with version-specific
syntax.

HMS-Commander provides a pure Python interface that operates externally to HEC-HMS, parsing
ASCII project files directly and generating Jython scripts only for simulation execution. This
design gives engineers access to the full Python ecosystem for pre-processing, post-processing,
and analysis while maintaining compatibility with the official HEC-HMS execution engine. Target
users include:

- **Practicing engineers** performing flood studies, bridge scour analyses, and stormwater
  management who need to run multiple scenarios efficiently.
- **Researchers** conducting sensitivity analyses, calibration studies, or uncertainty
  quantification on watershed models.
- **Agencies** managing archives of HEC-HMS models (e.g., FEMA effective models) that require
  systematic review, update, or comparison.

# State of the Field

No comprehensive open-source Python library for HEC-HMS automation existed prior to
HMS-Commander. Existing tools address fragments of the workflow:

- **HEC-HMS Jython scripting** [@USACE_Jython] provides execution control within the HMS
  runtime but cannot parse or modify project files, access external Python packages, or
  operate across HMS versions without syntax changes.
- **ERDC's Python wrapper** [@Nwachukwu2022] focused on gridded model initialization and
  initial condition testing but was not released as a general-purpose library.
- **pyhms** (gnodnooh/pyhms on GitHub) reimplements HMS hydrologic methods in Python for
  academic research but does not interface with actual HMS project files or the HMS
  execution engine.
- **HMS-PrePro** [@Castro2020] automates GIS preprocessing for HMS basin delineation using
  ArcGIS but does not address model execution, results extraction, or file modification.
- **raspy** [@raspy] provides a Python interface for HEC-RAS via the Windows COM controller
  but has no HMS counterpart.
- **PyRAS** [@Dysarz2018] demonstrated Python-HEC-RAS integration through COM automation
  but is limited to HEC-RAS and Windows platforms.

HMS-Commander fills this gap by providing a unified library spanning project initialization,
file operations, simulation execution, results analysis, and GIS export---analogous to what
ras-commander [@Katzenmeyer2024] provides for HEC-RAS.

# Software Design

## Architecture

HMS-Commander uses a static-method class architecture where each class corresponds to an HMS
file type or functional domain (\autoref{fig:architecture}). All file-operation classes
(`HmsBasin`, `HmsMet`, `HmsControl`, `HmsGage`, `HmsRun`) expose only static methods,
reflecting the stateless nature of HMS file operations. A single stateful class (`HmsPrj`)
manages project state through pandas DataFrames that index all project components:

```python
from hms_commander import init_hms_project, hms, HmsCmdr

init_hms_project("/path/to/project")
print(hms.basin_df)   # DataFrame of all basin models
print(hms.run_df)     # DataFrame of all run configurations
HmsCmdr.compute_run("Design Storm 100yr")
```

![HMS-Commander architecture. Static classes parse HMS file types, HmsPrj manages project
state via DataFrames, and HmsCmdr orchestrates execution through generated Jython
scripts.\label{fig:architecture}](architecture.png){ width=85% }

## Key Components

**File parsing.** A shared `HmsFileParser` utility handles the block-structured ASCII format
used by all HMS files, with UTF-8 and Latin-1 encoding fallback for compatibility with legacy
models. Classes provide methods to read parameters (`get_loss_parameters`,
`get_transform_parameters`) and write them back atomically (`set_loss_parameters`,
`set_curve_number`).

**Simulation execution.** `HmsCmdr` generates version-appropriate Jython scripts and invokes
`hec-hms.cmd -script` for execution. The library detects installed HMS versions, selects
Python 2 or Python 3 syntax as needed, and supports single, batch, and parallel execution
with configurable worker pools.

**DSS integration.** `HmsDss` provides read and write access to HEC-DSS files---the binary
time series database used by both HEC-HMS and HEC-RAS---through the HEC Monolith Java
library with automatic dependency management. This shared infrastructure enables direct
transfer of HMS simulation results to HEC-RAS boundary conditions without intermediate
format conversion.

**Storm generation.** Three validated storm generation modules produce design hyetographs:
`Atlas14Storm` generates storms from NOAA Atlas 14 temporal distributions
[@Perica2013], `FrequencyStorm` implements TP-40/Hydro-35 patterns for legacy
compatibility, and `ScsTypeStorm` provides SCS Type I/IA/II/III distributions [@NRCS2004].
All three are validated against HEC-HMS ground truth to $10^{-6}$ inch precision.

**Clone workflows.** Non-destructive model cloning enables side-by-side comparison of
baseline and modified scenarios within the HMS GUI, supporting quality assurance and quality
control (QAQC) workflows where all changes remain traceable and GUI-verifiable.

## HMS Version Support

HMS-Commander supports both major HMS version families. HMS 3.x models (32-bit, Jython 2.5)
remain in active use through FEMA effective model archives such as the Harris County Flood
Control District M3 Models [@HCFCD_M3], which contain 42 HMS projects across 21 watersheds
in the Houston metropolitan area. HMS 4.x models (64-bit, Jython 2.7) represent current
practice. The library handles syntax differences transparently through a
`python2_compatible` flag on script generation.

## Integration with ras-commander

HMS-Commander and ras-commander share DSS infrastructure and follow identical architectural
conventions (static classes, DataFrame-based discovery, non-destructive cloning). This
enables integrated watershed-to-river workflows:

```python
from hms_commander import init_hms_project, HmsCmdr, HmsResults

init_hms_project("/path/to/watershed")
HmsCmdr.compute_run("100yr_24hr")
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
# Transfer flows to HEC-RAS as upstream boundary condition
```

# Research Impact

HMS-Commander enables research workflows that are impractical with manual HMS operation:

- **Batch scenario analysis**: Systematic execution of dozens of storm frequencies, durations,
  and temporal patterns across the same watershed model.
- **Sensitivity analysis**: Programmatic variation of curve numbers, lag times, or routing
  parameters with automated result extraction and comparison.
- **Model archive management**: Automated review and update of legacy FEMA effective models,
  including the 42 HMS projects in the HCFCD M3 Model archive that HMS-Commander can
  extract and execute directly.
- **Reproducible hydrology**: Version-controlled Python scripts replace undocumented GUI
  interactions, enabling peer review of modeling decisions.

The library has been applied to HCFCD M3 Model validation, Atlas 14 precipitation update
workflows, and HMS 3.x to 4.x model conversion testing. Twenty Jupyter notebooks
distributed with the library demonstrate complete workflows from project initialization
through results visualization.

# AI Usage Disclosure

HMS-Commander was developed using an AI-assisted workflow termed the "LLM Forward Approach,"
where large language models (Claude by Anthropic) served as coding assistants throughout
development. Critically, the library is not simply a programmatic interface retrofitted with
AI tooling---it was designed from the ground up with LLM-agentic engineering workflows in
mind. The repository's hierarchical memory system (`.claude/rules/`, skill definitions, and
specialist subagent configurations) enables AI agents to navigate HMS domain knowledge,
execute multi-step hydrologic workflows, and maintain context across sessions.

The library's twenty Jupyter notebooks serve a dual purpose: they are both human-readable
documentation and the primary vehicle for test-driven development. Rather than relying on
atomized unit tests with mocked dependencies, HMS-Commander validates functionality through
whole-project workflow notebooks that initialize real HMS projects, execute simulations,
and verify results end-to-end. This approach ensures that tests capture critical
application-specific and project-level context that isolated unit tests would miss, while
simultaneously producing examples that both human engineers and AI agents can interpret to
learn correct usage patterns.

AI tools were used for code generation, documentation writing, test development,
and iterative refinement of library architecture. All AI-generated code was reviewed,
tested against real HEC-HMS projects, and validated by the author, a licensed Professional
Engineer. This paper was drafted with AI assistance and reviewed and edited by the author.

# Acknowledgements

The author acknowledges the U.S. Army Corps of Engineers Hydrologic Engineering Center for
developing and maintaining HEC-HMS and HEC-DSS as freely available software. The Harris
County Flood Control District is acknowledged for making M3 Model archives publicly available
for engineering practice and research. The author thanks the contributors to the Python
scientific computing ecosystem, particularly the pandas and NumPy projects, upon which
HMS-Commander depends.

# References
