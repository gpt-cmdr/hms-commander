# Docs Drift Audit - CLB-130

**Date:** 2026-05-01
**Scope:** public docs, README, notebook catalog, API nav, feature notes, and agent task notes named in CLB-130.
**Status:** First-pass reconciliation complete.

## Priority Findings

1. Public notebook documentation was contradictory.
   - `mkdocs.yml` pointed at many `docs/notebooks/*.ipynb` files that are not present in this checkout.
   - `docs/examples/overview.md` linked to those missing rendered notebooks.
   - Action: MkDocs now renders the notebook catalog page and the selected TauDEM benchmark notebook. The catalog links to canonical source notebooks in `examples/`.

2. Public API documentation lagged exported classes.
   - Current package exports or documents import paths for `HmsAorc`, `HmsGrid`, `HmsDssGrid`, `HmsHuc`, `HmsSqlite`, `HmsArf`, `DssCore`, `HmsOutput`, `HmsM3Model`, `Atlas14Config`, `FrequencyStorm`, and `ScsTypeStorm`, but the API nav did not expose them all.
   - Action: added API stub pages/nav entries for the missing public helpers and added `Atlas14Config` to the Atlas 14 API page.

3. Several user-facing docs still treated `CLAUDE.md` as an API reference.
   - `docs/user_guide/project_management.md`, `docs/index.md`, and release notes had stale wording.
   - Action: user docs now point to generated API pages and describe `AGENTS.md` as the shared agent contract with harness adapters.

4. Release notes were behind current package behavior.
   - `docs/llm_dev/release_notes.md` called v0.1.0 current and listed gridded precipitation as planned, while `pyproject.toml` declares v0.3.0 and AORC/grid helpers exist.
   - Action: rewrote release notes around v0.3.0, v0.2.0 DataFrame API, current limitations, and planned work.

5. AORC guidance mixed implemented helpers with non-existent met-model API.
   - `examples/aorc_integration_example.py` still said `HmsAorc` and `HmsGrid` were planned.
   - `HmsAorc.convert_to_dss_grid()` referenced `HmsMet.set_gridded_precipitation()`, which is not present.
   - Action: updated the example and docstring to show the implemented helper chain and mark HMS met-model gridded-precipitation wiring as manual/review-required for now.

6. Agent task notes could steer future agents into stale release steps.
   - The January 2026 precipitation DataFrame handoff still said "ready for commit", referenced `setup.py`, and described v0.2.0 release steps as active.
   - Action: added archival notices across the cross-repo handoff files and feature note; current package metadata is now called out as `pyproject.toml`.

7. Early Phase 1/1.5 agent infrastructure plans looked active.
   - They predate the current multi-harness contract and Codex bridge.
   - Action: marked them historical/superseded and pointed agents back to current repo contracts and manifests.

## Remaining Recommendations

- Do not move large task-note trees in this issue. The safer next step is a dedicated archival pass that moves historical release handoffs under an `archive/` folder and updates any inbound links.
- Decide whether docs should render more notebooks under `docs/notebooks/` or keep the docs site as a catalog linking to source notebooks in `examples/`.
- Add a real `HmsMet` helper for gridded-precipitation met-model wiring before documenting that workflow as end-to-end automated.
- Add CI for the non-HMS-dependent pytest subset once docs drift is reviewed.

