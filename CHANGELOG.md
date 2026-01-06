# Changelog

All notable changes to hms-commander will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
