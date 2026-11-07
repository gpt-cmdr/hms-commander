# DSS Native Backend: Example Notebook Qualification

**Date:** 2026-11-06
**Branch:** `feat/fast-dss-notebooks`, from `feat/fast-dss-native-engine` (draft PR #46) after the merge of `origin/main`
**Scope:** every example notebook that reads or writes DSS through hms-commander, run on the
`java`, `native` and `shadow` DSS backends (`HMS_COMMANDER_DSS_BACKEND`). This was the final round of
tests before the integration PR. No performance benchmarking was done. Run times are incidental wall
times from a shared workstation.

## Summary

- **Merge.** `origin/main` at `57fbd50` (#47, AORC grid period stamps) was merged into
  `feat/fast-dss-native-engine` as `e8d2d28`. Both #47's fix and #46's backends were kept. Full suite:
  **1054 passed, 14 skipped**.
- **Notebooks.** 11 current notebooks and 7 legacy notebooks were run on all three backends.
  Every notebook had the same outcome on `java`, `native` and `shadow`. No notebook failed on
  `native` or `shadow` that passed on `java`.
- **DSS contents and values.** Each backend's runs left 91 DSS files at matching paths: 270 file
  copies in all. They were compared across backends record by record: 90,412 record reads, about
  30,000 per backend. **No difference in values or metadata was found.** One native-written AORC grid file differs from the Java-written
  one only in the zlib-compressed size of 20 of its 124 grids. The cells and every header field are
  identical.
- **Shadow.** The notebook runs recorded no `unexpected` outcome. A separate full-file sweep read
  all 108 distinct DSS files on the shadow backend: 27,284 comparisons, **0 `unexpected`**. The only
  differences were the documented D1 (164) and D5 (160). One `unexpected` appeared in an earlier
  sweep while a second process read the same DSS6 file. It was traced to an intermittent Java
  (HEC Monolith) read under that contention; the native result was correct
  (see [open item 1](#open-items)).
- **Fixes.** No integration defect was found in the hms-commander code that the notebooks
  exercise, so no library change was made. The branch adds the qualification tooling
  (`scripts/dss_notebook_qualification/`) and this report.

## Environment

| Item | Value |
|---|---|
| Host | Windows 11 Pro for Workstations, CLB01 |
| Python | 3.12.11 (uv venv `D:\CLB-Dev\venvs\H-NB-3.12`, installed offline from the uv cache) |
| hms-commander | 0.4.0, editable from this branch (`e8d2d28` merge, then `a203e21` tooling) |
| Engine | `ras-commander-fast-dss` 0.0.1 built from dss-commander-rust `main` at `5af800d` (P46b); wheel `ras_commander_fast_dss-0.0.1-cp310-abi3-win_amd64.whl`, SHA-256 `eaf6b39e3554e4415abd8c9a101d3140ed56ad559482cc1bfebb03f9ac589e40` |
| Java backend | HEC Monolith 3.3.27 (`~/.ras-commander/dss/jar`), pyjnius 1.9.0, OpenJDK 17.0.20.1 (`D:\CLB-Dev\jdk\jdk-17.0.20.1+1`) |
| ras-commander | 0.113.0, for the one `RasDss.get_catalog` call in 14a (`RAS_COMMANDER_DSS_BACKEND` set to the same backend) |
| HEC-HMS | 4.13 (guides 101-106, 06, 14c), 4.10 (01, 05), 4.4.1, 4.8 and 4.13 (legacy 01). All runs went through `HmsCmdr`/`HmsJython`. |
| Notebook runner | nbclient 0.11.0, nbformat, ipykernel 7.4.0, matplotlib Agg backend |
| Other | numpy 2.5.4, pandas 3.1.1, xarray 2026.9.0, h5py 3.16.0, netCDF4 1.7.5.1.post1 |

The engine wheel is installed only in the qualification venv. It is not a dependency or extra of
hms-commander (D36).

## Method

1. **Inventory.** Each notebook's code was searched for calls into the DSS layer (`HmsDss`,
   `DssCore`, `HmsDssGrid`, `HmsResults`, `HmsAorc.convert_to_dss_grid`, `RasDss`). Notebooks
   that only read DSS file names from project text were also identified (see
   [Not run](#notebooks-not-run-on-the-three-backends)).
2. **Execution.** `run_nb.py` copies the notebook into
   `<scratch>/<backend>/<notebook>/` and runs it there with nbclient, with
   `HMS_COMMANDER_DSS_BACKEND` set. HEC-HMS example projects are extracted under that folder.
   An appended cell records `HmsDss.get_backend()`, the engine version and
   `HmsDss.get_shadow_summary()`. The `java` pass ran first as the baseline. It ran at the same
   time as the `native` pass; `shadow` ran alone.
3. **Comparison** (`compare.py`). Run status, failing cell and each cell's text output were compared
   with `java`, after paths, times and sizes were normalized. Every `*.dss` file left in each run
   folder was compared too: the catalog, then every record read through the Java backend.
   Time series were compared by value (exact, NaN-aware), units and type; paired data by curve
   values, units and labels; grids by cells and metadata. For the AORC grid file, `grid_deep.py`
   also compared every grid header field through the engine reader.
4. **Shadow sweep** (`sweep.py`). Every record of every distinct DSS file from the runs was read
   through `HmsDss` on the shadow backend: catalog, file version, time series and peak values,
   paired data, and grids.

## Results: current notebooks

Outcomes are listed as java / native / shadow. Times are wall seconds. All DSS reads run through
`HmsDss`/`HmsResults` on the selected backend.

| Notebook | Outcome (j / n / s) | DSS operations exercised | Shadow summary (all `identical` unless stated) | Differences across backends | Wall s (j / n / s) |
|---|---|---|---|---|---|
| 01_basic_workflow | pass / pass / pass | HMS 4.10 run (tifton); `get_peak_flows`, `get_catalog`, `read_timeseries` | catalog 2, peak 12, read_timeseries 1 | none: outputs equal; 3 DSS files, 529 records equal | 23 / 27 / 24 |
| 05_clone_workflow | pass / pass / pass | HMS 4.10 runs (castro baseline and clone); `get_peak_flows`, `get_catalog` | catalog 4, peak 9 | none; 5 files, 172 records | 32 / 36 / 33 |
| 06_results_dss | pass / pass / pass | HMS 4.13 run (tifton); `get_info`, `get_catalog`, `read_timeseries`, `get_peak_flows`, `get_outflow_timeseries` | catalog 6, peak 12, read_timeseries 4 | none; 2 files, 511 records | 17 / 24 / 17 |
| 101_guide_basic_model_setup | pass / pass / pass | HMS 4.13 run (castro); `get_catalog`, `read_timeseries` | catalog 1, read_timeseries 1 | none; 4 files, 174 records | 28 / 26 / 23 |
| 102_guide_meteorologic_methods | pass / pass / pass | `get_observed_dss_paths`, `read_timeseries` of a precipitation gage (no HMS run) | read_timeseries 1 | none; 6 files, 486 records (219 HRAP grids) | 21 / 17 / 17 |
| 104_guide_basin_methods_loss_transform | pass / pass / pass | HMS 4.13 run (castro); `get_catalog`, `read_timeseries` (inflow and outflow) | catalog 1, read_timeseries 2 | none; 4 files, 174 records | 27 / 23 / 22 |
| 105_guide_calibration_validation, as shipped | **fail / fail / fail** (cell 5) | HMS 4.13 runs (castro, River Bend); `get_catalog`, `read_timeseries` | none (failed before cell 5's reads) | same failure on all three; not DSS (open item 2) | 364 / 375 / 363 |
| 105, `timeout=180` raised to 900 in a scratch copy | pass / pass / pass | as above, including both River Bend roughness cases | catalog 3, read_timeseries 4 | none; 16 files, 3,972 records | 348 / 350 / 294 |
| 106_guide_advanced_analysis | pass / pass / pass | HMS 4.13 runs (castro baseline and 5 Snyder members); `get_catalog`, `read_timeseries` | catalog 5, read_timeseries 10 | none; 23 files, 1,034 records | 76 / 73 / 57 |
| 14a_aorc_download | pass / pass / pass | Network: AORC download from the NOAA S3 Zarr store; `HmsAorc.convert_to_dss_grid` writes 124 PER-CUM specified grids, DSS7, through `HmsDssGrid.write_grid_timeseries`; `RasDss.get_catalog` | write_grid_timeseries 1 | same 124 pathnames; cells and all header fields equal; native compressed size differs for 20 grids (see below) | 66 / 68 / 77 |
| 14b_aorc_grid_setup (runs in 14a's folder) | pass / pass / pass | No DSS-layer call: writes the grid definition and checks that 14a's DSS file exists | none | only the `Last Modified Time` line of the grid file differs (wall clock) | 48 / 36 / 32 |
| 14c_aorc_hms_execution | pass / pass / pass | HMS 4.13 run (tenk, HRAP gridded precipitation read by HEC-HMS); `get_catalog`, `get_peak_flows`, `read_timeseries` | catalog 4, peak 14, read_timeseries 15 | none; 3 files, 322 records (219 grids) | 40 / 26 / 26 |

**DSS files written by HEC-HMS.** HEC-HMS writes its own result DSS files; the backend does not.
Their bytes differ between runs because of write times, but every record's values and metadata
are equal. The HEC-HMS run logs report the same runs completed on all three backends.

**AORC grid file written by hms-commander (14a).** The Java and native writers produced the same
catalog, in the same order: 124 grids,
`/AORC/BALDEAGLE/PRECIP/29OCT2019:0000/29OCT2019:0100//` onward. Every grid has the same cells,
data type `PER-CUM`, units `MM`, WGS 84 CRS string, cell size, lower-left cell, start and end
seconds, statistics and range table. The only field that differs is
`sizeof_compressed_elements`, for 20 of the 124 grids (for example 115 against 107 bytes). The Java
and native zlib deflaters produced streams of different lengths for the same cells. This accounts
for the 8-byte difference in file size (384,424 against 384,416 bytes). The shadow run's file,
written by Java, matches the Java run's file in every field.

## Results: legacy notebooks (`examples/original_notebooks/`)

These are archived copies that the docs navigation does not include. They were run because they
call the DSS layer.

| Notebook | Outcome (j / n / s) | Shadow summary | Notes |
|---|---|---|---|
| 01_multi_version_execution | pass / pass / pass | catalog 12; read_timeseries `expected` D5 6 | Reads the shipped HEC-HMS 4.13, 4.8 and 4.4.1 tifton results. Cells 25 and 27 differ: see open item 3 (D5). Cell 18 differs only in run times. 7 files, 1,545 records equal. |
| 04_hms_workflow | pass / pass / pass | none | Computes no run, so its DSS cells take their "file not found" branch; the DSS layer is not exercised. |
| clone_workflow | pass / pass / pass | none | `HmsCmdr.compute_parallel` fails all three runs on every backend (open item 4); DSS cells not reached. |
| 07_m3_model_hms_projects | pass / pass / pass | none | DSS cells not reached. One 20,043-record M3 DSS file is equal across runs. |
| 05_version_3_to_4_conversion | fail / fail / fail (cell 7) | none | Needs `example_projects/Upgrade_M3_to_4.13`, which another workflow creates. Not DSS. |
| 08_atlas14_hyetograph_generation | fail / fail / fail (cell 27) | none | Same missing `Upgrade_M3_to_4.13` input. Not DSS. |
| 06_aorc_gridded_precipitation | fail / fail / fail (cell 59) | none | `import ras_commander` fails: `h5py` cannot load `_errors` after netCDF4 has loaded its HDF5 DLL in the same kernel. Environment problem, not a backend problem. The earlier AORC download, grid write (347 grids) and HEC-HMS run match across backends. |

## Shadow sweep of every DSS file

108 distinct DSS files: 12,856 RTD, 349 RTS, 160 RTP (patterns), 7 PD, 219 HRAP grids (GHT) and
372 specified grids (GST).

| Operation | identical | expected | unexpected |
|---|---|---|---|
| catalog | 108 | 0 | 0 |
| file_version | 108 | 0 | 0 |
| read_timeseries | 13,041 | 164 D1 (HEC missing markers returned as NaN), 160 D5 (patterns Java cannot read) | 0 |
| get_peak_value | 13,205 | 0 | 0 |
| read_paired_data | 7 | 0 | 0 |
| read_grid | 591 | 0 | 0 |

No call raised an exception to the caller.

## Fixes

None to library code. No defect was found in the hms-commander DSS integration that these notebooks
use, so this branch adds no library change and no new test. Committed on this branch:

- `e8d2d28` (on `feat/fast-dss-native-engine`): merge of `origin/main`. In
  `hms_commander/dss/hms_dss_grid.py`, the backend dispatch was kept. Main's copy of the
  period-window helpers was dropped, because the branch already had them; they differ only in a
  docstring word. In `CHANGELOG.md`, #47's Fixed entry was kept with a note that it applies on
  every backend, and the branch's duplicate Changed bullet was removed.
- `scripts/dss_notebook_qualification/`: `run_nb.py`, `run_backend.sh`, `compare.py`,
  `summarize.py`, `sweep.py`, `grid_deep.py` and `contention_repro.py`.

## Open items

1. **Intermittent truncated Java read of a DSS6 file under multi-process access (Java backend
   only).** While another process repeatedly called `HmsDss.get_catalog()` and
   `get_file_version()` on the same DSS6 file through Java, `HmsDss.read_timeseries()` on the
   Java backend sometimes returned one DSS block instead of the merged series. For
   `/ARS/000038/PRECIP-CUM/01OCT1972/15MIN/OBS/` in `tifton.dss`, it returned 2,976 values for
   October 1972 instead of 455,561. There was no exception and no WARNING. HEC Monolith printed
   `Cannot open data base file` and `Unable to access HEC-DSS file` to stdout, which bypasses
   hms-commander's message file. Observed rates: 1 in 464 and 3 in 1,625 reads, with 0 in 623 in a
   third run. `HecDss.isOpened()`, `checkForError()` and `HecDataManager.checkForSevereError()`
   did not distinguish the bad reads, so hms-commander has no status it can check. The native
   backend returned the full series in 1,588 of 1,588 and 2,520 of 2,520 reads under the same load,
   and printed nothing. The shadow backend reported the case correctly as `unexpected`. The
   notebooks do not share files between processes, and the sweep run alone found no unexpected.
   Reproducer: `python scripts/dss_notebook_qualification/contention_repro.py <copy of a DSS6 file>
   <multi-block pathname> [seconds]`. In Git Bash, set `MSYS_NO_PATHCONV=1` so the pathname is not
   rewritten. This behaviour predates #46.
2. **105_guide_calibration_validation fails as shipped on this host (not DSS).** The notebook calls
   `HmsCmdr.compute_run(..., timeout=180)` for each River Bend roughness case. The HEC-HMS 4.13
   "Minimum Facility" run took 161 s standalone and longer inside the notebook, so `HmsJython`
   timed out and `compute_run` returned False. The `assert ok` then fails on every backend, before
   any DSS read. With the timeout raised to 900 s in a scratch copy, the notebook passed on all
   three backends with identical results. Recommendation: raise the timeout in the notebook, then
   re-execute it to refresh its committed outputs. This was not done here, because it is outside
   the DSS scope and would rewrite committed outputs.
3. **D5 changes what a naive caller sees (legacy 01_multi_version_execution).** The notebook
   chooses the first pathname whose C part contains `FLOW`. That is HEC-HMS's unit-hydrograph
   pattern record, `//74006/FLOW-UNIT GRAPH/TS-PATTERN/1HOUR/...`. On `java` the read raises
   "No data found", and the notebook prints "Could not extract peak flow". On `native` the pattern
   is returned with stamps in year 3000, so the notebook prints a "peak flow" of 400.89 cfs at
   3000-01-01 19:00, which is a unit-hydrograph ordinate. D5 is documented in the
   [native backend guide](../user_guide/dss_native_backend.md), and `HmsResults.get_peak_flows()`
   excludes pattern records on every backend. The current notebooks select paths with
   `select_result_paths` and are not affected. Recommendation: in the legacy notebook, use
   `HmsResults`/`select_result_paths`, or retire it.
4. **Legacy notebook failures that are independent of the backend.** In `clone_workflow`,
   `HmsCmdr.compute_parallel` fails every run on all backends. The errors are
   `argument should be a str or an os.PathLike object ... not 'NoneType'`, and a worker-folder race
   (`WinError 145`, which left `worker_0` empty in one run). `05_version_3_to_4_conversion` and
   `08_atlas14_hyetograph_generation` need a prepared `Upgrade_M3_to_4.13` folder. In
   `06_aorc_gridded_precipitation`, an h5py/netCDF4 HDF5 DLL load order prevents
   `import ras_commander` late in the kernel.
5. **Committed notebook outputs were not refreshed.** The repository commits executed outputs,
   created on the Java backend. Re-running and committing all notebooks would rewrite unrelated
   outputs, so the outputs on the branch are unchanged. The evidence is in this report. The
   executed copies from the three backends are in the scratch folder
   (`D:\dss-commander-oracle\work\H-NB\runs`, `runs_orig`).
6. **Engine wheel build.** `build_wheel.sh` built the wheel, but it could not create its per-name
   test venvs, because TLS to PyPI failed (`invalid peer certificate: UnknownIssuer`). The engine's
   own `tests/python` suite was therefore not re-run by that script. The wheel was installed with
   `uv --offline`.

## Notebooks not run on the three backends

| Notebook | Reason |
|---|---|
| 02_project_dataframes, 03_file_ops_basin_met_control_gage, 04_run_management | Use DSS file names and pathnames from project text (`run_df`, `gage_df`, `HmsMet.get_dss_references`, `HmsRun.set_dss_file`/`get_dss_config`, `verify_dss_outputs`, which checks file existence). No DSS-layer call, so the backend setting has no effect. |
| 07_execution_jython, 21_taudem_to_hms_atlas14 | Run HEC-HMS and check that its DSS output file exists. No DSS-layer call. |
| 09_m3_conversion | Its DSS comparison is off by default (`ENABLE_DSS_COMPARISON = False`), so no DSS-layer call executes. It also needs HEC-HMS 3.3. |
| 00, 08, 10-13, 15-20, 22, 103 | No DSS use. |
| original_notebooks: 02, 03, 05_run_management, 09, 10, 11 | No DSS-layer call. |

A skipped notebook is not counted as a pass.

## Reproducing

```bash
export JAVA_HOME=<JDK 17>  PY=<venv python with hms-commander, the engine wheel, nbclient>
export RUN_ROOT=<scratch folder outside the repository>
for b in java native shadow; do bash scripts/dss_notebook_qualification/run_backend.sh $b; done
$PY scripts/dss_notebook_qualification/compare.py "$RUN_ROOT" compare.json
$PY scripts/dss_notebook_qualification/summarize.py compare.json
$PY scripts/dss_notebook_qualification/sweep.py "$RUN_ROOT" sweep.json
```

14a downloads AORC data from the public NOAA S3 store. The notebooks run HEC-HMS through
hms-commander, so HEC-HMS 4.10 and 4.13 must be installed.
