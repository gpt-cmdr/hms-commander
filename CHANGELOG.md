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
- **Native DSS backend (pre-release).** `HmsDss.backend` (or the environment variable `HMS_COMMANDER_DSS_BACKEND`) selects `"java"` (HEC Monolith, the default), `"native"` (the optional `ras_commander_fast_dss` engine, no Java) or `"shadow"` (returns the Java result and logs every difference against a native repeat; never raises). It applies to `DssCore`, `HmsDss`, `HmsDssGrid` and the readers built on them. The engine is not on PyPI and is not a dependency or extra; every engine import is guarded, so a missing or broken wheel does not affect the Java backend.
  - Native reads: catalog, time series (same inclusive window filter as Java; HEC missing values as NaN), peak values, paired data, grids (gated on the engine's `grid_srs_monolith_parity` feature) and file version.
  - Native writes (gated on the engine's writer API): time series, paired data, Atlas 14 temporal curves and `HmsDssGrid` specified grids. A closed gate raises `hms_commander.dss.DssCapabilityError`; there is no Java fallback.
  - New methods: `DssCore`/`HmsDss.read_grid()`, `get_file_version()` and `write_timeseries()` (regular intervals, both backends); `HmsDss.get_backend()`, `get_capabilities()` and `get_shadow_summary()`.
  - On DSS6, the native paired-data writer refuses unit or type strings longer than 8 characters (HEC Monolith truncates them silently), and `import_atlas14_temporal()` stores the Y type `CUMULATI`, the value Monolith stores there for `CUMULATIVE`, on both backends. The native grid writer refuses PER-CUM and PER-AVER grids, which `write_grid_timeseries()` writes with equal start and end times. See `docs/user_guide/dss_native_backend.md`.

### Fixed

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
