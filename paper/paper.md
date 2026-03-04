---
title: 'hms-commander: A Python Library for LLM-Accelerated HEC-HMS Hydrologic Modeling Automation'
tags:
  - Python
  - hydrology
  - hydrologic modeling
  - HEC-HMS
  - water resources
  - flood analysis
  - automation
  - DSS
  - LLM-assisted engineering
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

hms-commander is an open-source Python library that automates the U.S. Army Corps of
Engineers' Hydrologic Modeling System (HEC-HMS) and serves as a first-class substrate for
AI-agent-driven engineering workflows. HEC-HMS is the standard-of-practice software for
watershed hydrology in the United States, used by federal agencies, state departments of
transportation, and private engineering firms to simulate precipitation-runoff processes for
flood forecasting, infrastructure design, and floodplain management [@Scharffenberg2024;
@Feldman2000]. Despite its widespread adoption, HEC-HMS lacks a native Python API, requiring
engineers to interact with the software exclusively through its graphical user interface (GUI)
or through Jython scripts executed within the HMS Java runtime.

hms-commander addresses this gap by providing static-method classes that parse and modify HMS
project files (`.basin`, `.met`, `.control`, `.gage`, `.run`), execute simulations via
generated Jython scripts, extract results from HEC-DSS output files, and export model geometry
to GIS formats. The library supports both HMS 3.x (32-bit, Jython 2.5) and HMS 4.x (64-bit,
Jython 2.7) versions, enabling workflows across legacy and current model archives.
hms-commander integrates with its companion library ras-commander [@Katzenmeyer2024] to
support end-to-end watershed-to-river modeling pipelines where HMS hydrographs serve as
upstream boundary conditions for HEC-RAS hydraulic simulations.

Critically, hms-commander was engineered from the ground up using the "LLM Forward" approach
[@llmforward2024]---a methodology where domain experts design software as a first-class
substrate for AI-agent collaboration. The repository's hierarchical knowledge architecture,
validated notebook corpus, and specialized agent infrastructure collectively constitute a new
paradigm for LLM-accelerated engineering in the water resources domain.

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
access. The HEC-HMS development team added Jython scripting support in version 4.4.1
[@USACE_Jython]. However, Jython scripts operate within the HMS Java Virtual Machine (JVM),
lack access to the Python scientific computing ecosystem (NumPy, pandas, SciPy), and require
manual construction of script files with version-specific syntax.

hms-commander provides a pure Python interface that operates externally to HEC-HMS, parsing
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
- **AI-agent developers** building domain-specific engineering agents that need verified,
  machine-readable workflows as training and execution contexts.

# State of the Field

No comprehensive open-source Python library for HEC-HMS automation existed prior to
hms-commander. Existing tools address fragments of the workflow:

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

hms-commander fills this gap by providing a unified library spanning project initialization,
file operations, simulation execution, results analysis, and GIS export---analogous to what
ras-commander [@Katzenmeyer2024] provides for HEC-RAS. Both libraries share architectural
conventions, DSS infrastructure, and the LLM Forward development methodology, forming a
complete watershed-to-river automation stack.

# Software Design

## Architecture

hms-commander uses a static-method class architecture where each class corresponds to an HMS
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

**JVM-based simulation execution.** `HmsCmdr` generates version-appropriate Jython scripts
and invokes the HMS execution engine directly via Java Virtual Machine instantiation---not
batch file wrapping. This approach eliminates batch file bugs present in legacy automation
approaches. The library constructs explicit classpaths for HMS 3.x compatibility (32-bit Java
does not support wildcard classpath expansion), allocates 4 GB JVM heap by default (64-bit)
with automatic reduction to 1,280 MB for 32-bit installations, and detects installed HMS
versions from the installation path to select appropriate Python 2 or Python 3 Jython syntax.
Single, batch, and parallel execution modes are supported with configurable worker pools.

**DSS integration.** `HmsDss` provides read and write access to HEC-DSS files---the binary
time series database used by both HEC-HMS and HEC-RAS---through the HEC Monolith Java library
with automatic dependency management. This shared infrastructure enables direct transfer of
HMS simulation results to HEC-RAS boundary conditions without intermediate format conversion,
and is the same DSS implementation used by ras-commander.

**Storm generation.** Three validated storm generation modules produce design hyetographs
that all return a standardized `pd.DataFrame(['hour', 'incremental_depth', 'cumulative_depth'])`
for direct use in both HMS and RAS workflows:

- `Atlas14Storm` generates storms from NOAA Atlas 14 temporal distributions [@Perica2013],
  validated against HEC-HMS ground truth across 8 AEP events with 100% success
- `FrequencyStorm` implements TP-40/Hydro-35 patterns for HCFCD M3 model compatibility,
  validated against HMS source code (decompiled via CFR Java decompiler) to $10^{-6}$
  inch precision
- `ScsTypeStorm` provides SCS Type I/IA/II/III distributions [@NRCS2004] with validated
  peak positions: Type I at 41.1%, Type IA at 32.4%, Type II at 49.4%, Type III at 50.1%

Collectively, 77 tests covering 100+ parameter combinations verify depth conservation
at $10^{-6}$ inch precision across all storm generators.

**Clone workflows.** Non-destructive model cloning enables side-by-side comparison of
baseline and modified scenarios within the HMS GUI, supporting quality assurance and quality
control (QAQC) workflows where all changes remain traceable and GUI-verifiable. This pattern,
applied consistently throughout hms-commander and ras-commander, ensures that automated
changes can always be reviewed in the native HEC software interface.

## HMS Version Support

hms-commander supports both major HMS version families. HMS 3.x models (32-bit, Jython 2.5)
remain in active use through FEMA effective model archives such as the Harris County Flood
Control District M3 Models [@HCFCD_M3], which contain 42 HMS projects across 22 watersheds
in the Houston metropolitan area (models A through W, excluding V). These 22 model letter
codes correspond to 235 companion HEC-RAS reaches, covering the complete FEMA-effective flood
insurance maps for America's fourth-largest city. The HMS-only archive can be extracted,
executed, and analyzed programmatically using a single `HmsM3Model` class:

```python
from hms_commander import HmsM3Model

# Extract Brays Bayou HMS model directly from the online archive
path = HmsM3Model.extract_project('D', 'D100-00-00')

# Or find models by channel name via HCFCD ArcGIS API
model_id, unit_id = HmsM3Model.get_project_by_channel('BRAYS BAYOU')
```

HMS 4.x models (64-bit, Jython 2.7) represent current practice. The library handles syntax
differences transparently through a `python2_compatible` flag on Jython script generation,
with automatic version detection from the HMS installation path.

## Integration with ras-commander

hms-commander and ras-commander share DSS infrastructure and follow identical architectural
conventions (static classes, DataFrame-based discovery, non-destructive cloning). This
enables integrated watershed-to-river workflows:

```python
from hms_commander import init_hms_project, HmsCmdr, HmsResults
from ras_commander import init_ras_project, RasUnsteady

# Run HMS to generate hydrographs
init_hms_project("/path/to/watershed")
HmsCmdr.compute_run("100yr_24hr")
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")

# Transfer flows to HEC-RAS as upstream boundary condition
init_ras_project("/path/to/hydraulic_model")
RasUnsteady.set_flow_hydrograph("Plan01", "Upstream BC", flows)
```

The two libraries are designed to interoperate at the data level (shared DSS format and
pathname conventions) and at the agent level (a `hms-ras-workflow-coordinator` specialist
agent spans both repositories to guide multi-step coupled modeling workflows).

# LLM Forward Methodology

hms-commander was developed using the "LLM Forward" methodology [@llmforward2024], a framework
for domain experts who leverage AI agents as primary collaborators while maintaining full
professional responsibility for engineering decisions. The six tenets that governed development
are:

1. **Professional Responsibility First**: All AI-generated code is reviewed and validated by
   a licensed Professional Engineer. AI is a tool, not a decision-maker.
2. **LLMs Forward, Not First**: Domain experts define requirements, architecture, and
   acceptance criteria; LLMs implement and iterate.
3. **Multi-Level Verifiability**: Every claim is verifiable at multiple levels---source code,
   notebook outputs, and ground-truth comparisons against HEC software.
4. **Human-in-the-Loop**: Agent autonomy is bounded by explicit checkpoints and the
   non-destructive clone workflow pattern.
5. **Domain Expertise Accelerated**: The library encodes decades of HEC-HMS engineering
   knowledge (file formats, version quirks, JVM behavior, M3 model catalog) that guides AI
   agents toward correct domain-specific implementations.
6. **Focus on LLMs Specifically**: The repository is optimized for the current generation of
   large language model agents, not generic automation.

## Cognitive Infrastructure

The repository contains a hierarchical knowledge architecture that enables AI agents to
navigate HMS domain knowledge, execute multi-step workflows, and maintain context across
sessions:

- **28 rule files** organized in 7 domain categories (Python patterns, HMS domain knowledge,
  testing, integration, project organization, documentation, workflow)
- **13 workflow skills** with structured `SKILL.md`, examples, and reference data for
  repeatable task execution
- **30+ specialist agents** organized in a three-tier architecture: domain-expert Sonnet
  agents for HMS operations, fast Haiku review agents for validation, and Opus orchestration
  agents for multi-step coordination

The knowledge architecture uses four-level progressive disclosure: root `CLAUDE.md` provides
entry-point navigation, subpackage `CLAUDE.md` aggregates domain rules via `@import`
statements, `rules/` files contain authoritative patterns, and `agents/` files contain
specialist agent definitions. A Phase 4 refactoring reduced the framework from 30,201 lines
across 60 files to 4,937 lines---an 83.6% content reduction with zero duplication---by
replacing repeated content with lightweight navigators pointing to authoritative sources.

A key capability is the `hms_doc_query` production agent, which combines retrieval from USACE
Confluence documentation pages with a browser integration plugin that renders full HTML
content (including screenshots, parameter tables, and embedded equations) directly to the
agent context. This solves the core challenge of navigating visual engineering documentation
that resists plain-text extraction.

# Whole-Project Test-Driven Development

hms-commander deliberately rejects mocked unit tests in favor of whole-project workflow
notebooks that execute real HEC-HMS operations end-to-end. `HmsExamples` extracts authentic
HMS example projects distributed with HMS installations---Tifton, GA watershed, Castro
Valley, CA basin, and the Tenkiller Lake gridded precipitation project---providing verified
test data without synthetic fixtures.

The 33 Jupyter notebooks distributed with the library serve a dual purpose: they are both
human-readable documentation and the primary validation vehicle. Notebooks verify that file
parsing, simulation execution, DSS extraction, storm generation, and M3 model access all
function correctly against real HMS data. This approach ensures that tests capture
application-specific and project-level context that isolated unit tests would miss, while
simultaneously producing examples that both human engineers and AI agents can interpret to
learn correct usage patterns.

All storm generator validations compare programmatic output against HEC-HMS DSS ground truth
files, achieving $10^{-6}$ inch precision. The `FrequencyStorm` algorithm was verified by
decompiling HMS 4.13 Java source code (via CFR decompiler) to confirm exact algorithmic
equivalence.

# Research Impact

hms-commander enables research workflows that are impractical with manual HMS operation:

- **Batch scenario analysis**: Systematic execution of dozens of storm frequencies, durations,
  and temporal patterns across watershed models, with results aggregated into pandas DataFrames
  for statistical analysis.
- **Sensitivity analysis**: Programmatic variation of curve numbers, lag times, or routing
  parameters with automated result extraction and comparison across parameter spaces.
- **Model archive management**: Automated review and update of legacy FEMA effective models,
  including the 42 HMS projects across 22 HCFCD M3 watersheds that hms-commander can
  extract and execute directly from the public online archive.
- **Reproducible hydrology**: Version-controlled Python scripts replace undocumented GUI
  interactions, enabling peer review and reproduction of modeling decisions.
- **HMS-to-RAS hydrologic handoff**: Automated extraction of HMS outlet hydrographs and
  transfer to HEC-RAS as boundary conditions, completing the watershed-to-river simulation
  pipeline with ras-commander.

The library has been applied to HCFCD M3 Model validation, Atlas 14 precipitation update
workflows, and HMS 3.x to 4.x model conversion testing. A cross-repository multi-agent
coordination workflow demonstrated the ecosystem's AI-agent capabilities: an orchestrating
Sonnet 4.5 agent coordinated four parallel Opus agents to implement a shared precipitation
DataFrame API standardization across both hms-commander and ras-commander, achieving 77/77
tests passing in a single session. The coordination protocol---`START_HERE.md` → `PLAN.md` →
`IMPLEMENTATION.md` → `FINAL_SUMMARY.md`---is documented in `agent_tasks/cross-repo/` as a
replicable multi-agent engineering pattern.

# AI Usage Disclosure and Whole-Project Testing

HMS-Commander was developed using the LLM Forward Approach [@llmforward2024], where large
language models (Claude by Anthropic) served as primary coding collaborators throughout
development. Critically, the library is not simply a programmatic interface retrofitted with
AI tooling---it was designed from the ground up with LLM-agentic engineering workflows in
mind.

The repository's cognitive infrastructure (hierarchical `rules/` knowledge, skill
definitions, and specialist agent configurations) enables AI agents to navigate HMS domain
knowledge, execute multi-step hydrologic workflows, and maintain context across sessions.
Workflow skills include `hms_parse_basin-models`, `hms_execute_runs`, `hms_extract_dss-results`,
`hms_update_met-models`, `hms_clone_components`, `hms_manage_versions`, `hms_link_to-ras`,
`hms_query_docs`, and `hms_investigate_internals`---each backed by structured documentation
and real-project test cases.

The library's 33 Jupyter notebooks serve dual purpose: they are both human-readable
documentation and the primary vehicle for test-driven development. Rather than relying on
atomized unit tests with mocked dependencies, hms-commander validates functionality through
whole-project workflow notebooks that initialize real HMS projects, execute simulations, and
verify results end-to-end. This approach ensures that tests capture critical
application-specific and project-level context that isolated unit tests would miss, while
simultaneously producing examples that both human engineers and AI agents can interpret to
learn correct usage patterns.

AI tools were used for code generation, documentation writing, test development, and
iterative refinement of library architecture. All AI-generated code was reviewed, tested
against real HEC-HMS projects, and validated by the author, a licensed Professional Engineer.
This paper was drafted with AI assistance and reviewed and edited by the author.

# Acknowledgements

The author acknowledges the U.S. Army Corps of Engineers Hydrologic Engineering Center for
developing and maintaining HEC-HMS and HEC-DSS as freely available software. The Harris
County Flood Control District is acknowledged for making M3 Model archives publicly available
for engineering practice and research. The author thanks the contributors to the Python
scientific computing ecosystem, particularly the pandas [@McKinney2010] and NumPy [@Harris2020]
projects, upon which hms-commander depends.

# References
