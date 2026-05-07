# Changelog

All notable changes to hms-commander will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
