---
name: hms-cloud-native-gis
description: Coordinate HMS cloud-native export and map delivery through the installed hms2cng API or CLI, with source identity, CRS, units, and provenance. Use for GeoParquet, PMTiles, DuckDB, or database workflows.
shared_corpus: true
harness_scope: shared
source_owner: gpt-cmdr
security_review: internal
---

# HMS Cloud Native Export

Identify the HMS project, source component/results, requested format and consumer, output destination, and authorized operations. Read [HMS Commander](../hms-commander/SKILL.md) for current package discovery and MCP limits.

Discover the installed `hms2cng` version, public CLI help/signatures, release documentation, and available canonical package guidance before selecting commands. Use released packages for managed installations when authorized, preserve explicit pins, and report available updates. An editable checkout is appropriate only when the task calls for development; resolve its actual location rather than assuming a drive or repository path. Do not install all extras by default.

Use source-specific guidance to distinguish basin element geometry, model grid layers, ordinary series, DSS results, and statistics joined to geometry. Confirm the installed package supports the requested source/output combination. A missing command is a capability gap; do not invent a replacement flag from a historical example. Required native binaries and extras depend on the operation.

Record source identity, horizontal CRS, relevant datum, quantity/units, time basis, aggregation, layer names, and overwrite behavior. Preserve unknown metadata and original inputs. Do not relabel coordinates as a transformation. Use the full Python/CLI workflow for spatial/gridded data, binary results, exports, and database writes; these operations are excluded from MCP even if serialized as JSON or a table.

Local export, database synchronization, uploads, and publication have distinct side effects and task authorization. Delegate bounded domain work when useful and return compact artifact descriptions rather than large geometry arrays. Report generated paths, versions, transformations, checks actually performed, and blockers. External user maps and reports follow the user's requirements; repository writing standards apply to contributions.
