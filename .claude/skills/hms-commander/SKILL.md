---
name: hms-commander
description: Coordinate HEC-HMS tasks through HMS Commander, routing basin, meteorology, controls, runs, results, GIS, and HMS-to-RAS work. Use for requests to ask HMS Commander or handle a complete HMS workflow.
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
---

# HMS Commander

Serve as the shared entry point for HMS project workflows. Identify the project, requested result, installed library/engine versions, and authorized operations. Match the explanation to the user; repository editorial rules do not govern external user deliverables.

## Current package contracts

Inspect the installed `hms-commander` version and public signatures. Check the latest stable PyPI release at setup when network access is available. Prefer current compatible releases for authorized managed environments; preserve explicit user pins and do not silently upgrade a shared environment. Record unavailable checks, updates, and compatibility blockers. Repository main and web documentation may be ahead of the installed package.

Use the installed public APIs and canonical schemas rather than copied parser logic or a historical agent signature. No HEC executable is needed merely because an informational task mentions HMS; engine execution has separate prerequisites.

## Route the task

| Domain | Available route |
|---|---|
| Basin elements/parameters | Basin specialist; `hms_parse_basin-models`; current HmsBasin API |
| Meteorology/precipitation | Met specialist; `hms_update_met-models`; relevant storm/data APIs |
| Controls/run setup/execution | Run specialist and `hms_execute_runs`, with explicit execution scope |
| Results/DSS | Results/DSS specialist and public HmsResults/HmsDss APIs; optional dependencies only when needed |
| GIS/archive/export | `hms_export_cloud-native`; current hms2cng help/API and canonical guidance |
| HMS-to-RAS | Existing `hms-ras-workflow-coordinator` and `hms_link_to-ras`; load RAS guidance for RAS operations |

Use native specialists/workers available in the harness. Claude roles are thin adapters; Codex does not assume Claude Task syntax. Give workers a focused question, project root, versions, allowed actions, and bounded output. Assign exclusive files for concurrent edits and preserve other workers' changes. Delegate when useful; small Python tasks can be handled directly.

## MCP boundary

Any HMS/RAS project MCP calls must be made by a subagent, not the main coordinator. Limit its task to approved text data and non-spatial/non-gridded metadata, parameter tables, scalar summaries, or ordinary non-gridded time series. Set field, row/character, and time limits; require provenance, versions, units/time basis, and truncation status in the concise reply. Do not return full project dumps to the parent.

No MCP edits, model execution, preprocessing, exports, arbitrary code, spatial/gridded arrays, or binary DSS/HDF reads. A JSON/text rendering of such data does not change its scope. Use the heavier public Python tools for those tasks with their actual dependencies and authorization. If the harness cannot expose MCP tools to a subagent, use a scoped Python read or report the limitation; never fall back to a direct main-agent MCP call. Server enforcement of read-only operations and client enforcement of subagent-only exposure are separate requirements.

## Return useful evidence

Preserve source projects except for requested, authorized edits. Explain output paths, versions, checks actually performed, and unresolved issues. Separate a completed run from model suitability. GIS export must preserve quantity, CRS/datum, units, and time basis, following current hms2cng contracts. Downloads, publication, database writes, and deployment require their own task authorization. This entry point does not install a plugin or create an HMS MCP server.
