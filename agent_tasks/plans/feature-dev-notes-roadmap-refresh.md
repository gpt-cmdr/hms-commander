# Plan: Feature Notes and Roadmap Refresh (April 2026)

## Context

`feature_dev_notes/` has grown into a mixed archive:
- active notes,
- large research dumps,
- completed validation artifacts,
- and frozen prototype snapshots.

Before this refresh, the local index and roadmap were behind the actual repo state. The package now ships more than those docs acknowledged, while the most recent April 2026 work lives mostly in `workspace/scripts/` and recent history-review notes instead of the durable planning structure.

This plan is the shared cross-session source of truth for repo-wide prioritization.

---

## Source of Truth Verified

### Shipped in the repo

- `HmsSqlite` is in the package and exported publicly
- `HmsBasin` includes diversions, upstream network lookup, upstream element discovery, contributing-area methods, and batch parameter workflows
- `HmsGeo` includes `detect_model_type()` and diversion-aware extraction
- `HmsArf` is present and tested
- pytest is configured and `tests/` contains 12 test modules
- `examples/` now includes the TauDEM-to-HMS Atlas 14 bootstrap notebook `21_taudem_to_hms_atlas14.ipynb`
- TauDEM study packaging, direct TauDEM execution, watershed verification, TauDEM-to-HMS assembly, parser-of-record round-trip validation, and a live Spring Creek Atlas 14 compute benchmark are all now shipped in the repo

### Not yet productized

- promotion of the Spring Creek TauDEM-to-HMS benchmark from "import-valid and compute-valid" to "production-ready"
- pre-HMS readiness gating, TauDEM parameter sensitivity / optimization, and human reviewer QAQC artifacts for generated HMS scaffolds

### Deprioritized / likely dead ends

- GUI automation work described in `feature_dev_notes/historyreview_2026_04-12.md`
- JAB version-sweep scripts and output logs in `workspace/scripts/`
- HMS RMI / direct Java access work in `feature_dev_notes/research/`

### Still missing at repo level

- `.github/workflows/` does not exist yet
- later notebooks are not fully represented in `docs/notebooks/`
- `HmsAorc` and `HmsGrid` still contain unimplemented paths

---

## Priority Order

### 1. Promote or archive the TauDEM prototype work

**Why first**:
- This is the only prototype track in this group that is still under active development.
- It is also the least durable because it currently lives in local scripts and note fragments.

**Immediate actions**:
- ownership boundary decided: `hms-commander` owns the generic TauDEM preprocessing handoff up through validated delineation artifacts; regional defaults and downstream HMS parameter heuristics stay outside that scope
- durable next-step plan lives in `agent_tasks/plans/taudem-preprocessing-ownership-boundary.md`, not in ad hoc scratch notes
- first coupled validation target is `G:\GH\ras-agent\workspace\Spring Creek Springfield IL`, which already carries the Illinois-first gauge, basin, terrain, landcover, soils, and model-validation context that `ras-agent` needs from `hms-commander`
- detailed delivery roadmap lives in `agent_tasks/plans/taudem-feature-implementation-plan.md`
- current benchmark status is stronger than the older notes implied: Spring Creek now has verified delineation artifacts, a TauDEM-to-HMS assembly/export path, headless HMS parser-of-record validation, and a live Atlas 14 compute demonstration
- the next active gap is not "can this run at all"; it is whether the workflow can emit a readiness gate, support TauDEM parameter tuning, and survive human QAQC before downstream promotion

### 2. Normalize docs and notebooks around shipped features

**Why second**:
- The package surface area is ahead of the docs story.
- Several features that are already real in code still look "pending" if someone reads the older notes first.

**Immediate actions**:
- finish the notebook reorganization carryover
- sync or intentionally exclude later notebooks from `docs/notebooks/`
- update feature notes that are now validation/reference rather than backlog
- make the public docs explicit that the TauDEM/HMS Spring Creek path is import-valid and compute-valid, but still quality-gated from production use

### 3. Add CI for the already-testable subset

**Why third**:
- The repo already has a meaningful pytest baseline.
- Automation should follow the existing testable surface area instead of waiting for a perfect future state.

**Immediate actions**:
- add GitHub Actions
- run non-HMS-dependent tests in CI
- preserve markers for environment-specific tests

### 4. Finish the gridded precipitation path

**Why fourth**:
- `HmsSqlite` closed one major gridded-model gap.
- `HmsAorc` and `HmsGrid` are still not fully closed-loop.

**Immediate actions**:
- remove the remaining unimplemented paths
- validate the AORC notebook chain end-to-end

### 5. Revisit only if reopened by real need

**Candidates**:
- parameter calculators
- calibration framework

Explicitly deprioritized unless reopened:

- GUI automation
- HMS RMI / direct Java access

These should not outrank durable documentation, CI, and TauDEM prototype triage.

---

## Reclassified Work

These topics should generally be treated as shipped-or-reference, not greenfield backlog:

- DSS ReLink core primitives
- SQLite grid database support
- batch parameter management
- ARF support
- major portions of the notebook catalog

The notes for those areas still matter, but mostly for validation, cleanup, and historical traceability.

---

## Update Triggers

Update this plan when any of the following happen:

- GUI automation is explicitly reopened or formally archived as dead-end research
- TauDEM preprocessing is promoted into a durable repo asset or explicitly archived
- the TauDEM/HMS readiness gate, TauDEM parameter-comparison support, or reviewer QAQC bundle lands
- CI lands in `.github/workflows/`
- later notebooks are brought into or intentionally left out of `docs/notebooks/`
- `HmsAorc` / `HmsGrid` move from partial to complete
- a new repo-wide initiative displaces the current priority order

---

## Evidence Pointers

- `feature_dev_notes/INDEX.md`
- `feature_dev_notes/DEVELOPMENT_ROADMAP.md`
- `feature_dev_notes/historyreview_2026_04-12.md`
- `feature_dev_notes/reference/legacy_hms_commander_2025_07/`
- `feature_dev_notes/completed/scs_type_storm_validation_2026_01/`
- `workspace/scripts/`
- `tests/`
- `examples/`

User clarification recorded on 2026-04-21:

- TauDEM is still active
- GUI / JAB work is currently a dead end
- HMS RMI / direct Java access work is currently a dead end

TauDEM boundary decision recorded on 2026-04-21:

- `hms-commander` owns the generic preprocessing handoff, not the Houston-specific workflow as-is
- preprocessing stops at validated delineation artifacts; scripts `05_...06_...` are downstream HMS prototype work
- region-specific orchestration belongs outside the shared package surface
- Spring Creek Springfield, Illinois is the preferred first non-Houston benchmark because it is already the active `ras-agent` example area

---

## Migration Notes (2026-04-21)

Imported from `H:\Backups\CLB01 GH` during roadmap reorganization:

- `HEC-Commander\HMS-Commander\*` ->
  `feature_dev_notes/reference/legacy_hms_commander_2025_07/`
- `hms-commander\.claude\outputs\scs-implementation\*.md` ->
  `feature_dev_notes/completed/scs_type_storm_validation_2026_01/`

The imported material was intentionally classified as:

- historical reference for notebook-era origins
- completed validation evidence for `ScsTypeStorm`

It was **not** merged into active backlog folders.

---

**Created:** 2026-04-21
**Status:** Active
