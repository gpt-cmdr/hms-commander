# HMS Commander API rules

These rules describe the conventions that `hms_commander` code follows today. Each rule was checked against the package source on October 6, 2026 (`origin/main` at `4907409`, 46 non-`__init__` modules, 398 public methods on classes). The evidence column records that survey so a reviewer can tell an established convention from an aspiration. Rules were adapted from the ras-commander API Consistency Auditor; RAS-only rules were not adopted (see the end of this file).

`CONTRIBUTING.md` lists five critical rules. They map to these IDs: static class pattern → HMS-API-01; `@log_call` required → HMS-API-04; `@staticmethod` required → HMS-API-02 and HMS-API-03; parameter naming → HMS-API-05 and HMS-API-06; path handling → HMS-API-07.

Exceptions live in the repository [`.auditor.yaml`](../../../../.auditor.yaml). Each one records a design decision with a reason.

## Rule catalog

| ID | Rule | Severity | Automated | Evidence in current code |
|---|---|---|---|---|
| HMS-API-01 | Library classes are static namespaces: no `__init__`, no instance state. Exceptions are listed in `.auditor.yaml` `exception_classes`. Dataclasses, exceptions, and enums are exempt. | major | yes | 37 of 39 plain classes have no `__init__`. The two with `__init__` are `HmsPrj` (project state) and `HecMonolithDownloader` (private DSS helper); both are listed exceptions |
| HMS-API-02 | Public methods of a static class use `@staticmethod`. `@classmethod` is allowed only for classes listed in `classmethod_classes` (class-level caches). | major | yes | 0 public instance methods in static classes. `HmsExamples` (16 methods) and `HmsM3Model` (10 methods) use `@classmethod` for class-attribute caches |
| HMS-API-03 | Decorator order is `@staticmethod` (or `@classmethod`) above `@log_call`. Use the bare `@log_call` form. | major | yes | 228 of 228 methods with both decorators use this order; all 251 `@log_call` uses are bare |
| HMS-API-04 | Public methods of public static classes use `@log_call` (from `hms_commander.LoggingConfig`, re-exported by `hms_commander.Decorators`). Private methods, properties, private modules, and `log_call_exempt` entries are exempt. | minor | yes | Mixed: 251 of 398 public methods. New and changed public methods must comply; existing gaps are baseline findings |
| HMS-API-05 | Methods that resolve project state accept `hms_object=None` (keyword with a `None` default meaning the global `hms`). Never `ras_object`, `project`, `prj`, or `hms_prj`. | major | yes | 85 `hms_object` parameters, all defaulting to `None`; no alternative spellings |
| HMS-API-06 | Parameter names follow the established vocabulary (below); avoid `num` and `geom` abbreviations (`STYLE_GUIDE.md`). | minor | partly (abbreviations only) | No `num`/`geom` parameters. Drift exists for project folders (see baseline) |
| HMS-API-07 | Filesystem path parameters accept `Union[str, Path]` and convert with `Path(...)` at entry. `@standardize_path` exists in `Decorators.py` but is not used and is not required. A parameter holding a file *name* written into an HMS file may be `str` when listed in `path_str_exempt`. | minor | yes (name heuristic) | 294 path parameters use `Union[str, Path]`; 0 `@standardize_path` uses |
| HMS-API-08 | Public methods have return annotations. Tabular results are `pd.DataFrame` (or `gpd.GeoDataFrame`), created or located files are `Path`, single-element parameter reads are `Dict[str, Any]`, and DSS pathnames are `str`. | suggestion | annotation presence only | 389 of 398 public methods are annotated; `Dict[str, Any]` (72), `pd.DataFrame` (43), `bool` (32), `str` (31), `Path` (22) dominate |
| HMS-API-09 | Public methods have Google-style docstrings (`Args:`, `Returns:`, `Raises:`, `Example:`) per `STYLE_GUIDE.md`. Prose content is reviewed with `technical-writing-auditor` rule `TW-API-01`. | minor (missing), suggestion (NumPy style) | yes | 248 Google-style `Args:` sections versus 27 NumPy-style `Parameters` sections |
| HMS-API-10 | Public classes in public modules are exported in the package `__all__` (`hms_commander/__init__.py` or the `dss` subpackage). When a public DataFrame's columns change, update `hms_commander/schemas.py` in the same change (`AGENTS.md`, Documentation Site). | minor | export only | Every public static class is exported today |
| HMS-API-11 | Renames and moves keep the old public name working through a delegating alias whose docstring says "Compatibility alias for ..." until a release note announces removal. | review | no | `HmsGaugeData` is a compatibility facade over `HmsHydrologyContext`; `HmsGaugeStudy` and `HmsExamples` contain documented compatibility aliases |

Severity meanings: **major** breaks the public calling pattern or multi-project behavior; **minor** is a convention gap that a new or changed public method must not introduce; **suggestion** is consistency polish; **review** requires a reviewer decision.

## Parameter vocabulary (HMS-API-06)

Use the dominant existing spelling for a new parameter of the same meaning.

| Meaning | Name | Evidence (public method parameters) |
|---|---|---|
| Project context | `hms_object=None` | 85 |
| HMS component file | `<component>_path`: `basin_path`, `met_path`, `control_path`, `gage_path`, `run_file_path`, `geo_path`, `map_path`, `sqlite_path` | 33, 16, 6, 9, 8, 4, 5, 14 |
| Named component | `<component>_name`: `run_name`, `basin_name`, `subbasin_name`, `gage_name`, `reach_name`, `element_name` | 38, 8, 6, 6, 4, 4 |
| DSS file and record | `dss_file`, `pathname` | 38, 14 |
| Output location | `output_path` (file), `output_dir` (folder) | 26, 6 |
| Units in numeric names | suffix the unit: `duration_hours`, `total_depth_inches`, `time_interval_min`, `area_mi2` | Mixed; see baseline |

## Applying the rules

1. Run the checker from the repository root. It parses source only; it does not import `hms_commander` or execute HEC-HMS.

   ```bash
   python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py               # whole package
   python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py hms_commander/HmsBasin.py --format json
   python .claude/skills/api-consistency-auditor/scripts/check_api_consistency.py --fail-on major  # exit 1 on major findings
   ```

2. For a PR, restrict attention to findings on new or changed public methods. Do not ask a contributor to fix unrelated baseline gaps.
3. Review the non-automated parts by reading the diff: vocabulary choices (HMS-API-06), return-type meaning (HMS-API-08), `schemas.py` updates (HMS-API-10), and compatibility aliases (HMS-API-11).
4. Treat a checker hit as a finding to evaluate, not an automatic defect. The HMS-API-07 heuristic matches parameter names ending in `path`, `file`, `dir`, `directory`, or `folder`; confirm that the value is a filesystem path.
5. Propose an `.auditor.yaml` exception only with a specific architectural reason, and leave acceptance to a maintainer.

## Rules not adopted from ras-commander

These ras-commander rules depend on HEC-RAS structures and do not apply here: `@standardize_input` with HDF file types (`plan_hdf`, `geom_hdf`); `plan_number`, `geom_file`, and `ras_object` naming; the `RasPrj`, remote worker, and execution-callback exception classes; module-level execution-contract function exceptions; and the prohibition on invoking `Ras.exe` directly. HEC-HMS execution goes through `HmsCmdr` and `HmsJython`; `AGENTS.md` and `.claude/rules/hec-hms/execution.md` govern it.

## Baseline findings (October 6, 2026)

The checker reported these findings on the full package with the committed `.auditor.yaml`. They are recorded for planning and were not changed by the PR that added this auditor.

- HMS-API-04 (105): largest groups are `HmsHydrologyContext` (21), `DssCore` (13), `HmsGaugeData` (10, a delegating facade), `HmsGeo` (9), `HmsTauDEM` (8), `HmsGaugeStudy` (7), and `HmsTerrain` (5). `HmsPrj` (instance methods) and private modules are outside this rule.
- HMS-API-07 (8): `Atlas14Storm.generate_hyetograph` and `generate_hyetograph_from_ari` take `cache_dir: Optional[Path]`. `HmsRun.set_dss_file`, `set_output_dss`, `set_dss_file_direct`, `set_log_file`, `set_log_file_direct`, and `HmsGage.update_gage` take `dss_file`/`log_file: str`; their docstrings describe file names written into HMS files, so these are probable `path_str_exempt` candidates pending maintainer decision.
- HMS-API-08 (6): `HmsArfTexas.scale_depth`, `HmsArfTexas.scale_hyetograph`, `HmsTerrain.geometry_bounds`, `TexasStorm.triangular_cumulative`, `TexasStorm.lgamma_cumulative`, `DssCore.shutdown_jvm`.
- HMS-API-09 (27, NumPy style): `HmsSqlite` (15), `HmsAorc` (4), `HmsHuc` (3), `HmsArf` (2), `HmsBasin` (2), `HmsDssGrid` (1).
- HMS-API-06 (manual): project folder parameters use three spellings, `project_path` (6), `project_folder` (5), and `project_dir` (3); duration uses `duration_hours` (7) and `duration_hr` (4, `HmsArfTexas`).
- Guidance drift (manual): `.claude/rules/python/decorators.md` and `error-handling.md` cite `hms_commander/_logging.py`, which does not exist. `@log_call` is defined in `hms_commander/LoggingConfig.py` and re-exported by `hms_commander/Decorators.py`.
