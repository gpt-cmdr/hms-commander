# Changelog

All notable changes to hms-commander will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `HmsArfTexas`: Texas 1-day areal-reduction factors per Asquith (1999), USGS WRIR 99-4267 (Austin, Dallas, Houston; 1-day, T >= 2 yr, 0-50 mi radius).
  Reproduces WRIR Table 7 as printed by default; `dallas_intercept_correction=True` uses 0.6880 for the Dallas 24-27 mi ARF intercept (printed 0.6800). With `extrapolate=True`, an ARF or S2 outside (0, 1] raises `ValueError` from `circular_arf`, `noncircular_arf` and `depth_distance` (and so `scale_depth`/`scale_hyetograph`). Radius 0 or a tiny radius returns the r = 0 limit (1.0). The Dallas correction makes the ARF approximately continuous at r = 24 mi (residual about 0.0003) and applies over 24 <= r < 27 mi.
  Circular radius/area and scaling depth inputs must be finite and nonnegative; noncircular cell areas must also be positive and otherwise raise `ValueError`. Invalid numeric inputs, including bools, strings, and values outside the float64 range, raise `ValueError`.
- **TexasStorm** (`TexasStorm.generate_hyetograph`) for Texas dimensionless hyetographs: empirical curves (USGS SIR 2004-5075, Supplements 4-5), triangular and L-gamma models (TxDOT 0-4194-4; HDM 2019 Eq. 4-26 to 4-28).
  - `nonmonotone="raise"` (default) or `"running_max"` for the eight published empirical columns that decrease with time; `running_max` records the number of adjusted ordinates and the maximum adjustment (up to 1.09 percent points) in the provenance.
  - `total_depth_inches`, `duration_hours` and `drainage_area_sqmi` must be finite and positive.
  - The 160 mi2 warning applies to the empirical method only (SIR 2004-5075; HDM p. 4-77).
  - Docs state the HDM recommendation (`quartile="all"`, `duration_class="0-72"`), the HDM Table 4-16 8.70 vs SIR 6.37 value at 2.5 percent, the added (0, 0) and (100, 100) end points, and that `nws_hourly` durations of 12-13 hr, 24-25 hr and under 5 hr are unsupported.
- `BalancedFrequencyStorm` - HEC-HMS Frequency Storm (balanced/alternating-block) hyetograph generator validated against HEC-HMS 4.13 output. Existing `FrequencyStorm` is unchanged.
- `HmsDss.read_timeseries()` accepts optional `start_date` and `end_date`, passed to `DssCore.read_timeseries()`.

### Fixed

- **`HmsCmdr.compute_run()` returned `True` for runs that HEC-HMS aborted, and could choose an HEC-HMS version older than the project.** The HEC-HMS process exits normally after an abort, so the old check passed. Without `hms_exe_path`, the first installation found was used; folder names were compared as text, so 4.10 came before 4.13. On the HEC-HMS 4.13 `tenk` sample, 4.10 logged `ERROR 20137` and `WARNING 15303: Aborted run` but still created the results DSS. `compute_run()` returned `True`, and callers read the sample's shipped results or stale ones. Recheck results from runs that were reported as successful without an explicit `hms_exe_path`.
  - `compute_run()`, `compute_parallel()`, `compute_batch()` and `compute_with_parameters()` now return `True` only when the run's own outputs show that it computed.
    - Before HEC-HMS starts, the run's `Log File:` and `DSS File:` are read from the `.run` files, and each file's size, modification time and content (or SHA-256) are recorded.
    - After the run, the script must not have reported an error.
    - The log must have changed, and the text written since then must have a section for this run (`NOTE 15301 ... "<run>"`). That section must have `NOTE 15302`, no `ERROR` line and no `WARNING 15303`.
    - The results DSS file must be new or changed.
    - Files are compared with that record, not with the clock, so clock skew on a file server does not matter, and an unchanged file fails however recent its time.
    - Another run's result in a shared log is never credited to the target run. HEC-HMS 4.13 rewrites a shared log for each run of a batch, so an earlier run sharing it is reported as failed, and `compute_batch()` warns.
    - A run that is not in a `.run` file, or has no `Log File:` or `DSS File:`, cannot be verified and returns `False`.
    - On failure the reason and the log lines are logged at ERROR level. The return types are unchanged.
  - **New `RuntimeError`:** without `hms_exe_path`, all four methods now raise `RuntimeError` instead of running when no installation suits the project's `.hms` `Version:` line. That happens when only older versions (including an older patch) are installed, or when the `Version:` is not a comparable version and no installation has that exact name. The error names the project version and the installed versions. To run anyway, pass `hms_exe_path` explicitly; a warning is logged if it is older than the project.
  - **Version selection:**
    - The selection order is: the exact or an equal version (4.4.0 for 4.4); then a newer patch of the same major.minor; then the newest release of the nearest newer major.minor. Each fallback logs a warning.
    - Versions compare numerically, and a suffixed pre-release sorts before its release (4.13-beta < 4.13 < 4.13.1). The runtime version check reads a suffixed install folder such as `4.13-beta` as 4.13.
    - `HmsJython.find_hms_executable(version=...)` follows the same order and returns `None` instead of an older version. Without a version, it returns the newest installation in that order. It also has a new `include_defaults` argument.
  - **Evidence:**
    - Test fixtures: real run logs from HEC-HMS 4.10 (aborted) and 4.13 (finished) on `tenk`, and from 4.13 on `castro` (`Future` finished, and `Future` aborted with its gage data removed). The shipped sample `.run` files are fixtures too.
    - `local_hms` tests compute `tenk` with each version and over its shipped results, and run `castro` as a batch with separate and with shared logs.
    - `NOTE 15301` and `NOTE 15302` quote the run's name in every shipped sample run log in HEC-HMS 4.4.1 to 4.13.
    - The run-log check was not tested with HEC-HMS 3.x.

- **AORC DSS grids written by earlier versions give no rain in HEC-HMS; regenerate them.** `HmsDssGrid.write_grid_timeseries()` wrote PER-CUM grids with equal D and E parts, and HEC-HMS treats those cells as missing. Subbasin precipitation is 0, the log has `WARNING 40503` for every subbasin and hour, and the run still reports success. In a one-burst test on the tenk sample (HEC-HMS 4.9, 4.11, 4.12 and 4.13), the Tenkiller peak was 620 cfs, the initial baseflow, against 79,546 cfs with period stamps. It is not a timing shift. Regenerate any AORC DSS file from an earlier version, recheck calibrations and results built on it, and look for `WARNING 40503` in the run log. Do not merge old and new files, because the same hour has two pathnames.
  - PER-CUM and PER-AVER `timestamps` are now period end times, with a new `interval_minutes` argument (default: the stamps' uniform spacing; required for one grid or stamps with gaps), or one more time than there are grids, as boundaries. An AORC stamp T is the end of its hour, so `HmsAorc.convert_to_dss_grid()` writes D = T - 1h and E = T (T = 2020-05-02 00:00 gives `/01MAY2020:2300/01MAY2020:2400/`). A period with no length and an unknown data type now raise `ValueError`; an unknown type was previously stored as PER-CUM. So do a time that is not a whole minute and a time-zone-aware time other than UTC, which earlier versions stored at its local clock time. A UTC time is still stored at its UTC clock time.
  - Evidence and limits: the figures above come from a synthetic burst on an HRAP-index grid. A new `local_hms` test runs a generated AORC-shaped WGS84 grid through `convert_to_dss_grid()` and `HmsCmdr` on HEC-HMS 4.4.1 to 4.13, with the expected depth and timing; it is also synthetic. HEC-HMS 4.0 to 4.3 were not tested, because `HmsCmdr` does not support them. The runs use File-Specified discretization and check cell lookup and timing, not geographic placement; structured discretization was not run. Versions before 4.10 are tested with an existing DSS6 file: HEC-HMS 4.9 read no DSS7 grid, with either stamp form (`ERROR 12520`, no rain, success reported), and DSS7 was not tried on 4.4.1 to 4.8. The writer does not create a DSS6 file; it keeps the version of an existing one. A real AORC subset (January 1996; 4.11 to 4.13, and 4.9 with DSS6) matched the expected hourly subbasin depths in a one-off run.
  - Known gap: a cell file must use the writer's indexes, round(coordinate / cell size). `HmsGrid.map_aorc_to_subbasins()` and `map_grid_to_subbasins()` without `grid_origin` start at 600, 300, so those cells miss the grid and HEC-HMS 4.13 still gives `WARNING 40503` and no rain. Pass `grid_origin` to `map_grid_to_subbasins()`.
- DSS reads, writes and catalog calls (`DssCore`, the `HmsDss`/`HmsResults` methods built on it, and `HmsDssGrid.write_grid_timeseries()`) close the DSS file before returning, including when they raise. Through pyjnius, HEC Monolith's `HecDss.done()` only lowers a file-cache reference count, so the native file and its DSS locks stayed held for about 6 seconds, or longer if another object held the file. During that time HEC-HMS and other tools could not write the file, and on Windows it could not be renamed or deleted. hms-commander now calls `HecDSSFileAccess.close(path, True)` with the full long absolute path it opened (Windows 8.3 short names are expanded first). A failed close is logged at DEBUG and does not replace the original error.
- DSS time-series stamps (`DssCore.read_timeseries`, `DssCore.get_peak_value` and the `HmsDss`/`HmsResults` readers built on them) use the container's base date and time granularity. Second-granularity records, such as 15-second data, previously came back in January 1900. `attrs['interval']` is in minutes, with a float below one minute (0.25 for 15 seconds).
- `DssCore.get_peak_value()` excludes HEC missing values (-901, -902, -3.4028e38) and NaN from `peak_flow`, `min_value` and `mean_value`; ties return the first maximum.
- `DssCore.read_timeseries()` applies its documented `start_date`/`end_date` window (inclusive); the arguments were ignored.
- `write_paired_data()`, `write_multiple_paired_data()` and `import_atlas14_temporal()` write records again. With pyjnius 1.7.0 and 1.9.0 (both tested), `HecDss.put()` resolved to the wrong overload and nothing was written. Writes now confirm each record is in the file catalog and raise `RuntimeError` when it is not.
- Paired-data writers raise `ValueError` for pathnames without exactly six parts, and for duplicate pathnames in one batch. heclib silently dropped the extra part.
- `import_atlas14_temporal()` writes each probability to its own record, `//{region}/{QUARTILE}/{duration}HR//{probability}/`. The previous eight-slash pathname put every probability of a quartile on one record.
- `HmsResults.get_volume_summary()` and `get_hydrograph_statistics()` compute acre-feet as the trapezoidal integral of CFS over hours times 3600/43560. The previous formula multiplied by the time step twice, and it failed on NumPy 2 (`np.trapz` removed), where the summary was empty.
- `HmsResults.get_precipitation_summary()` and `HmsDss.get_total_precipitation()` total the interval depth (`PRECIP-INC`, legacy `PRECIP`) once per element and run. They previously summed every `PRECIP*` record, including cumulative `PRECIP-CUM`.
- `HmsDss.get_peak_flows()` reads total flow (`FLOW`) only; it could report `FLOW-CUMULATIVE` volumes as peak flows.

## [0.4.0] - 2026-10-04

### Added

- **Read-only text sections** (`HmsText.parse_sections`) parse named sections from caller-supplied `.hms`, `.basin`, `.met`, `.control`, `.run` and `.gage` text without opening files or initializing a project. The hms-commander-mcp server uses this API (#32).
- **DataFrame schemas** (`hms_commander.schemas`) declare the column contracts of the eight `HmsPrj` project DataFrames (#22).
- **ScienceBase example projects** (`HmsExamples.list_sciencebase_projects`, `extract_sciencebase_project`) with cached, SHA-256-verified downloads and provenance records (#16).
- Frequency-storm met reading reports `subbasin_depths`, an explicit keyword-only subbasin selector, storm type, unit system and depth-area reduction method (#31).
- Shared HMS Commander workflows and a generated skills-only plugin (#30, #32).

### Changed

- `clone_basin`, `clone_met` and `clone_control` return `Path` and use the same explicit project or global fallback. Project registry blocks use canonical `Filename:` casing (#18).

### Fixed

- HMS text block parsing is linear. USACE CWMS basins that end with `Zone Configuration` sections previously took over 60 seconds; an empty-header block no longer absorbs the next block (#34).
- `HmsResults.get_precipitation_timeseries()` prefers interval rainfall (`PRECIP-INC`) and rejects cumulative or diagnostic quantities instead of returning the first `PRECIP*` match (#33).
- Blank optional frequency-storm settings return `None` instead of raising `ValueError` (#31).
- Cloned meteorologic registrations use HMS `Precipitation:` blocks (#20).
- DSS time-series value handling used by notebooks 05 and 06; workstation-specific notebook paths removed (#21).

## [0.3.1] - 2026-05-07

### Added

- **DSS Time Series Writing** (`HmsDss.write_timeseries`) for writing HMS time series data to HEC-DSS files (CLB-507).
- **HMS Output Parsing** (`HmsOutput`, `HmsMessage`, `ComputeResult`) for structured parsing of HMS compute log output.
- **TauDEM Integration** (`HmsTauDEM`, `HmsTerrain`) for direct TauDEM execution wrappers with command manifests and run reports.
- **Watershed Verification** (`HmsWatershedVerification`) for boundary handoff outlet selection, figures, and CRS audit support.
- **Round-Trip Validation** (`HmsRoundTripValidator`) for TauDEM-to-HMS basin assembly and parser-of-record validation.
- **Gauge Study Packaging** (`HmsGaugeStudy`, `HmsGaugeData`) for gauge-first study packaging and workspace reports.
- **Areal Reduction Factors** (`HmsArf`) ARF computation pipeline with NOAA Atlas 14 point-to-area conversion.
- **Modified Puls Routing** (`HmsBasin.set_modified_puls_routing`) for configuring Modified Puls routing on reaches.
- **Batch Parameter Management** for `HmsBasin` and `HmsMet` -- bulk update loss, transform, and precipitation parameters across subbasins.
- **HmsSqlite Enhancements** -- flowpath extraction and statistics methods for grid database layers.
- **ScsTypeStorm** (`ScsTypeStorm.generate_hyetograph`) for SCS Type I, IA, II, III storm distributions with bundled `.npy` pattern data.
- Atlas 14 point-frequency storm bootstrap for TauDEM-derived HMS projects.
- Spring Creek TauDEM-to-HMS Atlas 14 example notebook and committed test fixtures.
- Comprehensive pytest suite with 265+ tests across 9 modules.
- CLB Engineering branding banner on project init with doc links in logs.
- LLM-forward contribution guidelines and GitHub issue/PR templates.
- Example notebooks 22-27: HMS guide series covering basic setup, met methods, GIS/terrain, basin methods, calibration, and advanced analysis.
- Cloud-native export integration guide and example notebooks for hms2cng.

### Fixed

- `HmsJython` `SaveProject` and `Compute` calls corrected to match HMS Jython API signatures.
- `HmsDss.write_timeseries` QAQC fixes for correct DSS pathname handling and documentation (CLB-507).
- `HmsArf.apply_arf` global depth bug fix.
- Phantom API references removed from docs and examples (CLB-340).
- Normalized Atlas 14 manual metric depth overrides before writing HMS frequency-storm depths.
- Aligned `Atlas14Storm.generate_hyetograph_from_ari()` with the DataFrame return contract.
- Tightened storm-generation tests so old ndarray-compatible behavior cannot silently return.

### ⚠️ BREAKING CHANGES

#### Precipitation Methods Return DataFrame

**BREAKING**: `Atlas14Storm.generate_hyetograph()`, `FrequencyStorm.generate_hyetograph()`, and `ScsTypeStorm.generate_hyetograph()` now return `pd.DataFrame` instead of `np.ndarray`.

**What Changed**:
- **Return Type**: `np.ndarray` → `pd.DataFrame`
- **New Columns**: `['hour', 'incremental_depth', 'cumulative_depth']`
- **FrequencyStorm Parameter**: `total_depth` → `total_depth_inches` (for API consistency)

**Why This Change**:
- Standardizes API across hms-commander and ras-commander
- Enables direct integration with HEC-RAS unsteady file writing
- Includes time axis (previously required manual calculation)
- More user-friendly for data analysis and visualization

**Migration Guide**:

| Old Code | New Code |
|----------|----------|
| `hyeto.sum()` | `hyeto['cumulative_depth'].iloc[-1]` |
| `hyeto.max()` | `hyeto['incremental_depth'].max()` |
| `len(hyeto)` | `len(hyeto)` (unchanged) |
| `plt.plot(range(len(hyeto)), hyeto)` | `plt.plot(hyeto['hour'], hyeto['incremental_depth'])` |
| `FrequencyStorm.generate_hyetograph(total_depth=13.2)` | `FrequencyStorm.generate_hyetograph(total_depth_inches=13.2)` |

**HMS Equivalence Preserved**:
Temporal distributions remain exactly HMS-compliant. Only the return wrapper changed. All validation tests continue to pass at 10^-6 precision.

**Files Modified**:
- `hms_commander/Atlas14Storm.py`
- `hms_commander/FrequencyStorm.py`
- `hms_commander/ScsTypeStorm.py`
- `tests/test_atlas14_multiduration.py`
- `tests/test_scs_type.py`

**Related**: Cross-repo API standardization with ras-commander for integrated HMS→RAS workflows.

---

## [0.2.1] - 2026-04-01

### Added

- HmsSqlite for SQLite grid database operations.
- Upstream network analysis primitives.
- Batch parameter management for HmsBasin and HmsMet.
- Quick Wins QW7-QW8: ARF application and Modified Puls import.
- Comprehensive pytest suite with 265 tests.

### Fixed

- Java detection and HMS date parsing in notebook execution.
- All example notebooks re-executed with current API.

---

## [0.1.0] - Initial Release

### Added
- Initial public release of hms-commander
- Static class API for HMS file operations
- Multi-version HMS execution support (3.x and 4.x)
- DSS operations via standalone HEC Monolith integration
- Atlas 14 storm generation
- SCS Type storm generation
- Frequency storm generation (TP-40/Hydro-35)
- HCFCD M3 model integration
- Example notebooks demonstrating all features
- Comprehensive test suite
