# Plan: TauDEM Preprocessing Ownership Boundary

## Context

The active TauDEM evidence in this repo is split across:

- `workspace/scripts/01_download_watershed.py` through `06_generate_hms_basin.py`
- `workspace/research/01_taudem_overview.md` through `06_workflow_design.md`
- `feature_dev_notes/research/USGS_DEM_Houston_TauDEM_Research.md`
- `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/`

Those materials currently mix three different concerns:

- regional data acquisition and DEM-conditioning choices
- watershed delineation / TauDEM-adjacent hydro preprocessing
- downstream HMS parameter estimation and model-file generation

The roadmap item for April 2026 requires a clean ownership boundary so the repo stops carrying an ambiguous "maybe library, maybe app workflow, maybe archived prototype" story.

---

## Decision

`hms-commander` owns the **generic, HMS-facing TauDEM preprocessing handoff** up through validated delineation artifacts.

The ownership cutoff is:

- **inside scope**: reproducible hydro-preprocessing inputs, conditioning, TauDEM-stage orchestration, delineation outputs, and provenance that are generalizable across regions and directly useful to later HMS assembly
- **outside scope**: region-specific defaults, watershed-specific operating assumptions, and downstream HMS parameter heuristics that are not yet method-equivalent or benchmarked

In workflow terms, TauDEM preprocessing ends at a durable handoff package of delineation artifacts. It does **not** include the current prototype logic in scripts `05_extract_characteristics.py` and `06_generate_hms_basin.py`.

---

## Preferred Benchmark

Use the Spring Creek Illinois workspace in `ras-agent` as the primary cross-repo benchmark for this preprocessing boundary:

- workspace: `G:\GH\ras-agent\workspace\Spring Creek Springfield IL`
- gauge: `USGS 05577500` (`SPRING CREEK AT SPRINGFIELD, IL`)
- reference basin: `02_basin_outline/USGS_05577500_nldi_basin.geojson`

Why this is the preferred benchmark:

- it matches the Illinois-first direction in `ras-agent`
- it is already tightly coupled to active `ras-agent` development that depends on `hms-commander`
- it already contains the key comparison layers needed for preprocessing validation:
  - gauge metadata and observed flow records
  - official NLDI basin outline
  - NHDPlus context
  - terrain
  - NLCD
  - soils
  - model-validation outputs

This makes Spring Creek a better immediate validation target than the archived Houston prototype when testing whether `hms-commander` can provide a reusable preprocessing handoff to a consuming application repo.

---

## Owned In `hms-commander`

- a region-agnostic handoff contract for study geometry, pour points, basin boundaries, DEM clip recommendations, and provenance
- explicit conditioning and TauDEM command orchestration with inspectable intermediate artifacts
- delineation outputs that can be consumed by later HMS logic:
  - conditioned DEM
  - snapped outlet or pour-point artifacts
  - D8 pointer / slope / contributing-area rasters
  - stream raster
  - stream network vectors
  - watershed / subbasin polygons
  - command manifest, QA report, and provenance metadata
- HMS-facing geometry translation only after topology mapping is benchmarked and does not encode region-specific defaults

---

## Not Owned In `hms-commander`

- Houston/HCFCD defaults such as `EPSG:26914`, HCFCD channel priority, Hunting Bayou benchmark selection, Houston Green-Ampt values, Houston CN assumptions, or Houston Tc/R heuristics
- Illinois-first product orchestration or any other application-specific workflow owned by sibling repos such as `ras-agent`
- placeholder topology, estimated longest-flow-path logic, or "good enough to run" parameter guesses from the prototype scripts
- calibration policy, regulatory acceptance criteria, or regional benchmark selection that should live with the consuming application or benchmark repo

---

## Script Reclassification

- `workspace/scripts/01_...04_...` are **evidence for the preprocessing boundary**, not promotion-ready library code. They hardcode Hunting Bayou / Houston assumptions and mix py3dep, Whitebox, and pysheds choices that still need a generic contract.
- `workspace/scripts/05_...06_...` are **downstream HMS prototype work**, not TauDEM preprocessing. Keep them as reference until a benchmarked HMS-side assembly path exists.
- `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/` remains the frozen Houston snapshot. It is useful for portable patterns and anti-patterns, not as the live implementation target.

---

## Durable Next Steps

1. Define the minimal durable artifact contract for the preprocessing handoff.
   Outputs should be the smallest set needed for reviewable downstream HMS assembly.
2. Split regional defaults from the current scripts.
   Every CRS, stream-source priority, burn depth, threshold, and benchmark outlet must move to explicit inputs or named profiles outside the generic runtime.
3. Benchmark the generic preprocessing path first on Spring Creek Springfield, Illinois in `ras-agent`.
   Use the official NLDI basin as the comparison boundary and treat the existing terrain, NLCD, soils, and validation assets there as the acceptance-test workspace for the first cross-repo pass.
4. Execute the phased delivery plan in `agent_tasks/plans/taudem-feature-implementation-plan.md`.
   Use that plan as the detailed implementation roadmap for what lands first, what is deferred, and how Spring Creek closes the current verification gap.
5. After Spring Creek is working, add at least one second non-Houston basin before promoting code into the package API.
   Promotion should follow evidence, not prototype momentum.
6. Keep any active implementation notes for this work under `agent_tasks/plans/`.
   Do not restart the story in ad hoc scratch notes or one-off history-review files.

Until those steps are complete, the current workspace scripts remain exploratory evidence rather than shipped package surface.

---

## Evidence

- `agent_tasks/README.md`
- `agent_tasks/plans/feature-dev-notes-roadmap-refresh.md`
- `feature_dev_notes/DEVELOPMENT_ROADMAP.md`
- `workspace/scripts/01_download_watershed.py` through `06_generate_hms_basin.py`
- `feature_dev_notes/research/USGS_DEM_Houston_TauDEM_Research.md`
- `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/PORTABLE_PATTERNS.md`
- `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/NONPORTABLE_DEFAULTS.md`
- `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/SUCCESSOR_ROADMAP.md`
- `G:\GH\ras-agent\AGENTS.md`
- `G:\GH\ras-agent\agent_tasks\plans\illinois-taudem-primary.md`
- `G:\GH\ras-agent\workspace\Spring Creek Springfield IL\README.md`

---

**Created:** 2026-04-21
**Status:** Active
