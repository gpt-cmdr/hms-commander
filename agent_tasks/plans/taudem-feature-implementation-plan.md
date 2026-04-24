# Plan: TauDEM Feature Implementation and `ras-agent` Enablement

## Status

- Created: 2026-04-21
- Last updated: 2026-04-24
- Status: Active
- Scope owner: `hms-commander`
- Primary consuming workflow: `G:\GH\ras-agent\workspace\Spring Creek Springfield IL`

## Implementation Progress

### Landed in this implementation slice

- restored `HmsGaugeStudy` as the gauge-first study/workspace builder
- restored `HmsHydrologyContext` primitive helpers for gauge metadata, basin, HUC context, flowlines, and TauDEM handoff assembly
- restored compatibility facades `HmsGaugeData` and `HmsTerrain`
- landed source tests for study packaging, structured data gaps, geometry/extent helpers, and TauDEM input-pack generation
- wired top-level package exports and API documentation entries for the restored modules
- landed `HmsTauDEM` with executable discovery, per-step wrappers, standard delineation orchestration, and machine-readable command manifests / run reports
- added focused fake-executable tests for TauDEM environment validation, successful run layout, and failure reporting
- landed `HmsWatershedVerification` for raster/vector basin comparison, CRS inheritance, outlet snap metrics, and stream-network summaries
- validated the verification workflow against the live Spring Creek workspace and generated `09_taudem_verification/boundary_verification.json`
- confirmed the Spring Creek consuming report package now recognizes the verification artifact and no longer reports `taudem-boundary-verification-pending`
- landed `HmsBasinBuilder` TauDEM-to-HMS writers for `.basin` scaffolds, HMS-style `.hms` registry blocks, `.run` bootstrap, and HMS SQLite geometry packages
- landed `HmsRoundTripValidator` for disposable clone validation with headless `OpenProject -> SaveAllProjectComponents -> Exit`, durable manifests, and normalized diff classification
- validated the parser-of-record loop against a cloned checked-in `river_bend` example project and confirmed normalized round-trip stability under local HMS 4.13
- validated Spring Creek TauDEM bootstrap variants for both terminal `Sink:` and terminal-junction control shapes under local HMS 4.13, with durable artifacts in `workspace/roundtrip_cases/`
- landed Atlas 14 PFDS point-frequency parsing and depth-duration helpers in `Atlas14Storm`, with committed Spring Creek NOAA fixture coverage
- promoted a compute-ready `bootstrap_taudem_atlas14_project` path that writes Atlas 14 meteorology, control specs, and run wiring on top of the TauDEM HMS scaffold
- corrected the HMS run-writer contract based on QAQC: new TauDEM runs must be upserted into the project aggregate `.run` file, not written as standalone `.run` files, for HEC-HMS to load them during compute
- added a reproducible end-to-end example notebook at `examples/21_taudem_to_hms_atlas14.ipynb`
- validated the full Spring Creek Atlas 14 bootstrap through both headless parser-of-record round-trip and a live HMS 4.13 compute run, with durable artifacts under `examples/output/21_taudem_to_hms_atlas14/`
- recorded the first live HMS residual warning set from that compute run so the remaining modeling work is explicit rather than implied: missing ET/canopy methods, Muskingum routing stability warnings, lag-vs-time-step warnings, and negative inflow clipping at multiple junctions and the sink

### Still open after this slice

- downstream handoff contract validation against live `ras-agent` workspace regeneration
- investigate the Spring Creek outlet-placement mismatch surfaced by the verification artifact before treating the benchmark as fully settled
- GUI smoke automation still needs to be promoted from workspace-script prototype to durable API-level validation
- hydrologic method population from TauDEM geometry remains provisional; the first compute-ready scaffold runs, but ET/canopy defaults and reach routing parameters still produce quality warnings that need a deliberate parameterization pass before treating the model as production-ready
- no durable pre-HMS readiness gate exists yet; the library can currently build an HMS scaffold before delineation, routing, or warning thresholds have been accepted
- no shared TauDEM parameter sensitivity / optimization layer exists yet for threshold, outlet, and related delineation controls
- no human-review QAQC checklist or signoff artifact exists yet for promoting a TauDEM-to-HMS case from “compute-valid” to “defensible engineering setup”
- API consistency QAQC still has cleanup items outside the core TauDEM workflow, including Atlas 14 manual-input unit normalization and final return-type/documentation alignment on convenience hyetograph helpers

---

## Objective

Convert the TauDEM-related work that already exists as research, prototype scripts, and cross-repo workspace artifacts into a durable `hms-commander` feature set that:

1. provides a reusable, region-agnostic preprocessing and delineation handoff,
2. closes the current feature gaps blocking Spring Creek boundary verification,
3. enables `ras-agent` to consume verified watershed artifacts without re-implementing hydrology-side logic locally.

This plan is intentionally narrower than full HMS model synthesis. The immediate target is a benchmarked preprocessing, delineation, verification, and handoff contract for downstream workflows.

---

## Current State Inventory

This inventory now separates durable current truth from remaining partial work after the first live Spring Creek HMS compute pass.

## What is already developed

| Area | Evidence | Status | Notes |
|------|----------|--------|-------|
| Durable ownership boundary | `agent_tasks/plans/taudem-preprocessing-ownership-boundary.md` | Done | Confirms `hms-commander` owns generic preprocessing handoff, not regional heuristics |
| Repo-wide priority tracking | `agent_tasks/plans/feature-dev-notes-roadmap-refresh.md` | Done | TauDEM remains the top active prototype track |
| Houston archive and research | `feature_dev_notes/completed/houston_hcfcd_taudem_prototype_2026_04/` | Done for learning | Good source of portable patterns and anti-patterns |
| TauDEM-aware HMS runtime environment | `hms_commander/HmsJython.py` | Done | HMS launch path already includes TauDEM/GDAL native paths |
| Illinois-first consuming benchmark | `G:\GH\ras-agent\workspace\Spring Creek Springfield IL` | Done | Provides gauge, basin, terrain, NLCD, soils, report, and validation context |
| Cross-repo roadmap and issue links | `G:\GH\ras-agent\agent_tasks\plans\illinois-taudem-primary.md` | Done | Explicit upstream dependency list already exists |
| Gauge-first study packaging | `HmsGaugeStudy`, `HmsGaugeData`, Spring Creek `00_metadata/` | Done | Study manifest and workspace-summary contract are upstreamed |
| Report and data-gap generation | `HmsGaugeStudy`, Spring Creek `08_report/` | Done | Spring Creek report package can now be regenerated from `hms-commander` |
| Shared analysis extent and TauDEM input-pack contract | `HmsTerrain`, Spring Creek `analysis_extent*` artifacts | Done | Shared buffered-extent and DEM handoff patterns are productized |
| Direct TauDEM execution | `HmsTauDEM` | Done | Core CLI wrappers, manifests, and run reports are landed |
| Boundary verification | `HmsWatershedVerification`, Spring Creek `09_taudem_verification/` | Done | Verification artifact, figures, and handoff outlet logic are landed |
| TauDEM-to-HMS assembly | `HmsBasinBuilder` | Done | TauDEM spec, export package, HMS scaffold writer, SQLite geometry, and Atlas 14 bootstrap are landed |
| Parser-of-record HMS validation | `HmsRoundTripValidator` | Done | Disposable clone validation, real normalized diffs, and change classification are landed |
| Compute-ready demonstration case | `examples/21_taudem_to_hms_atlas14.ipynb` and Spring Creek example outputs | Done with caveats | Import-valid and compute-valid, but not yet production-ready |

## What is partially developed but not productized

| Area | Evidence | Current gap |
|------|----------|-------------|
| TauDEM parameter sensitivity / optimization | first Spring Creek benchmark plus live compute warnings | No shared sweep / comparison surface exists yet for threshold, outlet, and related TauDEM controls |
| Pre-HMS readiness gate | Spring Creek compute logs and verification outputs | No durable pass/fail artifact yet blocks HMS project creation when delineation/modeling warnings exceed accepted thresholds |
| Production hydrologic parameter population | Spring Creek Atlas 14 bootstrap warnings | ET/canopy, routing stability, lag/time-step, and clipped-inflow issues still need a deliberate parameterization strategy |
| Human reviewer QAQC workflow | first live Spring Creek compute pass | No checklist, signoff artifact, or reviewer-ready comparison bundle exists yet |
| Downstream `ras-agent` regeneration proof | coupled Spring Creek workspace | Shared outputs exist, but the full downstream consume/regenerate loop has not been revalidated against live `ras-agent` orchestration |

## What is explicitly not ready for promotion

| Area | Evidence | Reason |
|------|----------|--------|
| `workspace/scripts/05_extract_characteristics.py` | Houston archive summary and script comments | Uses estimated longest flow path, calibration placeholders, and simplified topology |
| `workspace/scripts/06_generate_hms_basin.py` | Houston archive summary and script comments | Produces a scaffold, but still needs manual connectivity and calibration review |
| Whitebox-first or Whitebox-dependent mainline architecture | `ras-agent/AGENTS.md`, `illinois-taudem-primary.md` | Whitebox belongs in comparison work only, not the authoritative shared path |
| Houston/HCFCD defaults as shared runtime defaults | archive `NONPORTABLE_DEFAULTS.md` | Non-portable and out of scope for shared package defaults |

---

## Productization Target

The first durable TauDEM feature set in `hms-commander` should produce a verified watershed package with these layers:

- study metadata and manifest
- gauge and basin reference context
- shared analysis extent and DEM clip recommendation
- direct TauDEM command manifest and outputs
- watershed verification artifact against an official basin reference
- handoff metadata that `ras-agent` can consume without reconstructing hydrology-side provenance
- optional TauDEM-to-HMS assembly and compute scaffold artifacts for benchmark and review workflows

The package boundary stops before:

- regional calibration heuristics
- production hydrologic parameter estimation based on unbenchmarked shortcuts
- placeholder topology
- automatic promotion of a generated `.basin` / `.met` / `.control` package to production status without explicit quality gates and reviewer QAQC

---

## Proposed Package Surface

The exact module names can still change, but the feature split should follow the static-class pattern already used by the repo.

### Workstream A: Study and workspace primitives

Proposed module responsibility:

- `HmsGaugeStudy`

Primary responsibilities:

- gauge-first study initialization
- manifest creation
- gauge metadata normalization
- official basin / HUC context references
- report payload and data-gap payload generation

This workstream aligns with:

- `hms-commander` Issue #2: gauge-first watershed study builder
- `hms-commander` Issue #3: workspace organizer and manifest builder
- `hms-commander` Issue #4: hydrology-side report and data-gap generator

### Workstream B: Terrain and handoff inputs

Proposed module responsibility:

- `HmsTerrain`

Primary responsibilities:

- shared analysis extent builder
- DEM clip recommendation from basin geometry
- terrain source provenance capture
- basin / pour-point / context packaging for TauDEM runs

This workstream aligns with:

- `hms-commander` Issue #5: TauDEM example-workflow / input-pack support

### Workstream C: Direct TauDEM execution

Proposed module responsibility:

- `HmsTauDEM`

Primary responsibilities:

- direct TauDEM CLI discovery and execution
- step manifests for `pitremove`, `d8flowdir`, `aread8`, `threshold`, `moveoutletstostrm`, `streamnet`, and optional `gridnet`
- output-path contract and provenance
- failure reporting with structured status

### Workstream D: Verification and downstream handoff

Proposed module responsibility:

- `HmsWatershedVerification` or a verification namespace within `HmsTauDEM`

Primary responsibilities:

- compare TauDEM delineation against official basin reference
- compute drainage-area deltas, outlet-snap distance, overlap metrics, and stream-network summary metrics
- write a durable `boundary_verification.json`
- emit handoff metadata for `ras-agent`

This workstream is the bridge to:

- `ras-commander` Issue #36: drainage-area comparison utility
- `ras-commander` Issue #38: geometry-first 2D flow area writer

---

## Phase Plan

## Phase 0: Lock the contract

Goal:

- define the exact artifacts, filenames, and JSON payloads that the shared workflow will produce

Deliverables:

- shared file naming convention for study metadata, manifests, reports, and TauDEM outputs
- canonical location for `boundary_verification.json`
- canonical location for `analysis_extent_summary.json`
- canonical location for TauDEM command manifest and provenance
- explicit profile rules for regional defaults so processing CRS and source preferences are inputs, not hardcoded runtime assumptions

Acceptance criteria:

- Spring Creek workspace artifacts can be mapped one-to-one to the proposed shared contract
- no contract item depends on Houston-specific names, CRS, or heuristics

## Phase 1: Upstream the study-package primitives

Goal:

- make the Spring Creek-style study metadata, manifest, report, and data-gap outputs available from `hms-commander`

Deliverables:

- `HmsGaugeStudy` static methods for study manifest creation
- reusable report payload builder
- reusable data-gap payload builder
- structured workspace summary generation for gauge, basin, terrain, NLCD, and soils references

Required output parity with Spring Creek:

- `00_metadata/manifest.json`
- `00_metadata/gauge_data_summary.json`
- `08_report/report.json`
- `08_report/data_gap_analysis.json`

Acceptance criteria:

- Spring Creek report/data-gap artifacts can be regenerated by `hms-commander`
- output schemas are stable enough for `ras-agent` to treat them as a shared contract

## Phase 2: Upstream the TauDEM input-pack and analysis-extent layer

Goal:

- formalize the preprocessing inputs that precede a direct TauDEM run

Deliverables:

- shared analysis extent builder from official basin geometry
- DEM clip recommendation payload
- basin and pour-point context package
- optional HUC and upstream flowline references
- input-pack manifest and provenance report

Required output parity with Spring Creek:

- `00_metadata/analysis_extent.geojson`
- `00_metadata/analysis_extent_5070.geojson`
- `00_metadata/analysis_extent_summary.json`

Acceptance criteria:

- Spring Creek analysis extent can be regenerated from the shared builder
- profile-driven CRS selection works for Illinois without baking Illinois assumptions into generic runtime code

## Phase 3: Land the direct TauDEM CLI wrapper

Goal:

- make direct TauDEM execution the authoritative shared preprocessing path

Deliverables:

- executable discovery and PATH validation
- wrappers for core TauDEM stages:
  - `pitremove`
  - `d8flowdir`
  - `aread8`
  - `threshold`
  - `moveoutletstostrm`
  - `streamnet`
  - `gridnet` as needed for path-length metrics
- command manifest with exact args, inputs, outputs, timestamps, and exit status
- deterministic workspace output layout

Non-goals for this phase:

- Whitebox mainline conditioning path
- R-based reference-tool integration
- HMS model parameter estimation

Acceptance criteria:

- a direct TauDEM run can execute against the Spring Creek terrain and basin inputs
- each command produces a manifest entry and durable artifact path
- failures are reported in machine-readable form

## Phase 4: Ship boundary verification for Spring Creek

Goal:

- close the current `taudem-boundary-verification-pending` gap in the Spring Creek workspace

Deliverables:

- boundary verification workflow against official NLDI basin
- `boundary_verification.json`
- overlap and area-comparison metrics
- snapped outlet metrics
- summary report section that can flow into the study report or data-gap analysis

Minimum verification metrics:

- official basin area
- TauDEM basin area
- absolute and percent area difference
- outlet snap distance
- polygon overlap metrics
- stream network summary counts

Acceptance criteria:

- Spring Creek no longer reports `taudem-boundary-verification-pending`
- the verification artifact is sufficient for `ras-agent` to proceed to downstream modeling readiness checks

## Phase 4B: Add a pre-HMS quality gate

Goal:

- keep TauDEM-to-HMS assembly from skipping over unresolved delineation and model-readiness warnings

Deliverables:

- a machine-readable readiness artifact written before or alongside HMS bootstrap
- explicit pass/fail thresholds for:
  - delineation overlap and area checks
  - outlet placement status
  - stream-network sanity metrics
  - TauDEM run-parameter provenance
  - HMS warning classification for generated scaffolds
- shared support for TauDEM parameter sensitivity / comparison runs so threshold, outlet, and similar controls can be varied deliberately instead of by ad hoc reruns
- a reviewer-oriented comparison bundle and checklist for human QAQC

Minimum quality-gate checks:

- verification artifact present and within accepted tolerance
- outlet and handoff-point selection status recorded
- no unreviewed CRS/provenance ambiguity
- generated HMS scaffold warnings classified, including:
  - missing ET/canopy methods
  - Muskingum stability warnings
  - lag/time-step warnings
  - negative inflow clipping

Acceptance criteria:

- Spring Creek can emit a durable readiness artifact before HMS project promotion
- `ras-agent` can refuse downstream model creation when the gate is failing or reviewer signoff is missing
- TauDEM parameter changes needed to improve readiness can be traced through durable manifests and comparison outputs

## Phase 5: Finalize the `ras-agent` handoff

Goal:

- make the verified hydrology-side package directly consumable by `ras-agent`

Deliverables:

- documented handoff artifact list for `ras-agent`
- stable path and schema contract for verified basin package inputs
- clear ownership split:
  - `hms-commander`: hydrology-side preprocessing, delineation, verification
  - `ras-agent`: Illinois adaptation and orchestration
  - `ras-commander`: drainage-area comparison, geometry-first model build, land-cover/infiltration compilation

Required handoff outputs:

- official basin reference
- TauDEM basin output
- verification artifact
- stream network output
- terrain provenance
- analysis extent summary
- manifest / report / data-gap outputs

Acceptance criteria:

- Spring Creek workspace has everything needed for the `ras-agent` side to call the next workflow without local reconstruction of upstream context

## Phase 6: Expand beyond the first benchmark

Goal:

- avoid overfitting the shared workflow to Spring Creek

Deliverables:

- one second non-Houston benchmark basin
- comparison notes on what required profile inputs vs what stayed generic
- confirmation that the shared API still does not require Illinois-specific assumptions

Acceptance criteria:

- at least two benchmark basins pass the preprocessing and verification workflow
- runtime defaults remain profile-driven, not benchmark-driven

---

## Gap-Closing Matrix

| Gap | Current owner | Blocking effect | Resolution path |
|-----|---------------|----------------|-----------------|
| Study manifest/report/data-gap generation is not upstreamed | `hms-commander` | `ras-agent` must carry custom workspace logic | Phase 1 |
| Analysis extent and DEM clip contract is not upstreamed | `hms-commander` | inconsistent preprocessing envelope handling | Phase 2 |
| Direct TauDEM wrapper is not landed in shared package | `hms-commander` | `ras-agent` risks carrying reusable hydrology logic locally | Phase 3 |
| Spring Creek boundary verification artifact is missing | `hms-commander` | explicit blocker in Spring Creek data-gap report | Phase 4 |
| No pre-HMS readiness gate exists for TauDEM-to-HMS assembly | `hms-commander` | scaffolds can be created before delineation/modeling warnings are accepted | Phase 4B |
| No TauDEM parameter sensitivity / optimization surface exists | `hms-commander` | manual reruns are required to improve threshold/outlet settings | Phase 4B |
| No human reviewer QAQC bundle/signoff exists | shared `hms-commander` / `ras-agent` workflow | compute-valid scaffolds can be mistaken for production-ready models | Phase 4B plus downstream acceptance |
| Drainage-area comparison artifact is missing | `ras-commander` | model readiness remains incomplete | consume Issue #36 after Phase 4 |
| Geometry-first model handoff artifact is missing | `ras-commander` | geometry creation remains blocked downstream | consume Issue #38 after Phase 5 |
| StreamStats service integration is stale | `ras-agent` | automated peak-flow path remains incomplete | out of scope here; track separately |
| Whitebox comparison is not formalized | benchmark worktree only | no alternate-method comparison record | defer until direct TauDEM baseline is stable |
| HMS parameter estimation / topology remain heuristic | not ready for shared promotion | unsafe to ship as preprocessing API | defer until after verified delineation contract exists |

---

## `ras-agent` Enablement Sequence

`ras-agent` does not need all historical prototype features. It needs a narrow, durable sequence:

1. Study package and report contract from `hms-commander`
2. Shared analysis extent and terrain provenance
3. Direct TauDEM delineation outputs
4. Boundary verification artifact
5. Pre-HMS readiness gate and reviewer QAQC bundle
6. Stable handoff metadata for `ras-agent`
7. Downstream drainage-area comparison and geometry build from `ras-commander`

This ordering matters. It avoids spending time on premature HMS heuristics while the Spring Creek workflow still lacks the verification artifact that proves the hydrology-side package is trustworthy.

---

## Explicit Deferrals

These items should not be part of the first promoted TauDEM feature surface:

- Whitebox-first conditioning in mainline runtime
- Houston/HCFCD parameter defaults
- placeholder topology promotion
- estimated longest-flow-path promotion
- automatic HMS basin/met/control generation as a prerequisite for `ras-agent`
- GUI-driven HMS terrain wizard parity
- `rivnet` / `traudem` as required dependencies

They may be revisited later, but only after the direct TauDEM baseline and Spring Creek verification path are stable.

---

## Testing and Validation Strategy

## Unit tests

- schema and payload tests for manifest/report/data-gap outputs
- geometry and extent builder tests
- TauDEM command manifest tests
- profile selection tests that verify CRS and source rules are input-driven
- TauDEM-to-HMS spec, basin scaffold, SQLite geometry, and block-registry writer tests
- Atlas 14 point-frequency, duration-distribution, and bootstrap-wiring tests
- API-consistency regression tests for unit normalization and public return-type contracts

## Integration tests

- Spring Creek workspace regeneration smoke test
- direct TauDEM run smoke test against Spring Creek terrain inputs
- verification-artifact generation test
- cloned `river_bend` parser-of-record round-trip against TauDEM-derived HMS imports
- Spring Creek Atlas 14 bootstrap smoke test through `OpenProject -> SaveAllProjectComponents -> Exit`
- local HMS compute smoke test that captures and classifies residual warnings instead of treating compute success alone as a promotion signal

## Benchmark review outputs

- written comparison between official basin and TauDEM basin
- recorded data-gap resolution status for Spring Creek
- residual-warning summary for generated HMS scaffolds, including ET/canopy gaps, Muskingum stability warnings, lag-vs-time-step warnings, and negative inflow clipping
- reviewer-ready comparison bundle with the generated project, manifests, normalized round-trip diffs, compute log, and readiness classification
- second-basin comparison note before API promotion beyond Spring Creek

## Human Review Gate

The current Spring Creek path is benchmark-grade, not production-grade.

Promotion from "import-valid and compute-valid" to "defensible engineering setup" should require all of the following:

- a passing machine-readable pre-HMS readiness artifact
- explicit classification of any remaining HMS warnings
- reviewer-facing figures and comparison outputs for delineation, outlet, routing, and generated topology
- human QAQC signoff that the TauDEM configuration, HMS parameterization, and resulting warning set are acceptable for the intended engineering use

This gate is where future detailed human review belongs. The automated workflow can generate the comparison bundle, but it should not self-certify production readiness.

---

## Documentation Deliverables

- API docs for any new `Hms*` modules
- one reproducible workflow doc or notebook for the shared TauDEM study package
- explicit handoff documentation for `ras-agent`
- update to the repo-wide roadmap plan pointing to this implementation plan
- public documentation note that the TauDEM-to-HMS Spring Creek benchmark is import-valid and compute-valid, but still quality-gated from production use
- reviewer-oriented documentation for the readiness artifact, residual warning classes, and accepted-vs-blocking HMS compute warnings
- downstream documentation in `ras-agent` stating that only quality-gated and reviewer-cleared upstream artifacts should be treated as production handoffs

---

## Issue Mapping

Current linked upstream issues from the `ras-agent` plan:

- `hms-commander` Issue #2: gauge-first watershed study builder
- `hms-commander` Issue #3: workspace organizer and manifest builder
- `hms-commander` Issue #4: hydrology-side report and data-gap generator
- `hms-commander` Issue #5: TauDEM example-workflow / input-pack support
- `ras-commander` Issue #36: drainage-area comparison utility
- `ras-commander` Issue #38: geometry-first 2D flow area writer

If new feature gaps appear during Phase 3 or Phase 4, they should be recorded as GitHub issues in the owning repo rather than buried in local scratch notes.

---

## Immediate Next Step

Start with the quality-gate follow-through, not a new greenfield feature slice:

- define and write the machine-readable pre-HMS readiness artifact for Spring Creek
- add TauDEM parameter sensitivity / comparison support so threshold and related controls can be tuned deliberately
- produce the first reviewer-oriented QAQC bundle for the Spring Creek Atlas 14 benchmark
- revalidate the downstream `ras-agent` consume/regenerate story against that gated handoff package

That is the shortest path from "working benchmark" to a workflow that can be reviewed, tuned, and promoted responsibly.
