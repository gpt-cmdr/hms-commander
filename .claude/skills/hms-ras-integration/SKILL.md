---
name: hms-ras-integration
description: Coordinate HMS hydrograph handoff to RAS with explicit source identity, outlet mapping, units, time basis, and evidence. Use for watershed-to-river integration and boundary-condition preparation.
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
---

# HMS–RAS Integration

Identify the HMS source run/outlet, RAS receiving plan/boundary, requested operation, and existing authorization. Read [HMS Commander](../hms-commander/SKILL.md) for package discovery and MCP limits. Load the installed RAS Commander workflow when available; identify the missing integration before dependent work if it is unavailable.

## Discover the actual contracts

Inspect installed public HMS/RAS exports, signatures, schemas, and matching release examples before selecting extraction or boundary-edit APIs. Do not use copied historical `RasGeom`, `RasUnsteady`, or result-method signatures as contracts. Domain libraries own parsing, execution, DSS access, and edits. Use Python with the required extras for binary DSS/HDF and GIS work; these operations do not belong in MCP.

Check existing results first. An inventory or handoff request does not authorize running HMS or RAS. Preserve source inputs and results; use authorized separate destinations for transformations or generated artifacts. Do not rerun a model or copy a DSS file into a project merely to resolve an information gap.

## Prepare a traceable handoff

Record the source project/run/element, exact DSS file and pathname (when applicable), quantity, units, time-zone or other time basis, series interval and period, missing values, and interval-value semantics. Preserve source profile/event names. Verify required conversions explicitly; HMS and RAS can use different unit systems. Rainfall frequency does not establish flood frequency.

Map each actual HMS outlet to its intended RAS receiving boundary. A project centroid is not an outlet. Use source-specific geometry and verified CRS transformations when spatial matching is requested; a shared CRS is convenient but not required if a valid transformation is applied. Record horizontal CRS, relevant vertical datum, transformation, and reviewed mapping. Proximity alone is not proof of hydraulic connectivity.

Check time-window coverage, sampling/interpolation behavior, units, signs, missing values, and conservation or summary comparisons relevant to the task. Explain the basis for any tolerance and account for routing/storage differences. Do not impose universal positive-flow, loss-ratio, peak-difference, or urban/rural timestep thresholds. A successful transfer establishes the checks performed, not model adequacy.

Separate read-only inspection, handoff preparation, authorized boundary edits, and model execution. Give each domain worker a focused scope and exclusive write destinations. Use native workers available in the harness, without provider model assumptions. Project MCP queries, if used for eligible text metadata, remain bounded subagent-only reads and cannot perform the transfer.

## Return evidence

Return source/target identities and versions; file/pathname mapping; units/time basis; CRS/outlet mapping where requested; transformations and checks actually performed; created/changed artifacts; and unresolved issues. HEC documentation is primary for its documented methods and controls; project capabilities and observations come from package contracts and evidence. Use passive official citations and distinguish project recommendations from documented HEC behavior. External reports follow the user's writing requirements.
