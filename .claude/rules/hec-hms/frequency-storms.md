# Frequency Storm Generation (TP-40/Hydro-35)

**Purpose**: Document FrequencyStorm module for HEC-HMS "Hypothetical Storm" compatibility.

**Primary sources**:
- `hms_commander/FrequencyStorm.py` - Static class implementation
- `hms_commander/data/tp40_dimensionless_pattern.npy` - Bundled temporal pattern
- `feature_dev_notes/hms_frequency_storm_extraction/` - HMS 4.13 source code extraction
- `FREQUENCY_STORM_VALIDATION_RESULTS.md` - Validation findings

---

## Overview

**FrequencyStorm** generates hyetographs using the same algorithm as HEC-HMS "Hypothetical Storm → User Specified Pattern" method.

**Status**: ✅ **VALIDATED** (2025-12-28)
- Algorithm matches HMS source code exactly
- 24-hour storms validated to 10^-6 precision against HCFCD M3 Model D
- Variable durations supported (HMS User Specified Pattern compatible)

**Algorithm**: Cumulative pattern scaling (same as Atlas14Storm)
- NOT alternating block method
- Confirmed via HMS 4.13 decompiled source code

---

## Quick Start

```python
from hms_commander import FrequencyStorm

# Generate 24-hour frequency storm (5-minute intervals)
# HCFCD M3 model compatible
hyeto = FrequencyStorm.generate_hyetograph(
    total_depth=13.20,      # 24-hour total depth (inches)
    total_duration_min=1440,  # 24 hours (default)
    time_interval_min=5,      # 5-minute intervals (default)
    peak_position_pct=67.0    # Peak at 67% (default)
)

print(f"Generated {len(hyeto)} intervals")
print(f"Total: {hyeto.sum():.2f} inches")
print(f"Peak: {hyeto.max():.3f} inches")
```

---

## Algorithm

### HMS Equivalence (Validated)

FrequencyStorm implements the **EXACT algorithm** HMS uses for "Hypothetical Storm → User Specified Pattern":

```python
# From HMS aY.java:148-156 (extracted code)
for each time interval:
    time_pct = 100.0 * time_min / duration_min
    cumulative_pct = interpolate(pattern, time_pct)
    cumulative_depth = total_depth * cumulative_pct / 100.0
    incremental[i] = cumulative_depth - prev_cumulative
```

**Steps**:
1. Load dimensionless temporal pattern
2. Interpolate cumulative percentage at each time step
3. Scale to total depth
4. Convert cumulative to incremental

**Validation**: RMSE < 10^-6 inches vs HMS ground truth (M3 Model D)

---

## HMS Storm Types (Important Distinction)

HEC-HMS has **TWO** types of Hypothetical Storms:

### 1. SCS Distributions (Type I, IA, II, III)

**Characteristics**:
- **Duration**: Fixed at 24 hours (hardcoded in HMS source)
- **Pattern**: Built-in 1441-value arrays
- **Peak**: Built into distribution (Type II ~50%, Type IA ~30%)
- **Use case**: Standard NRCS storm distributions

**HMS Code** (`aH.java:39`):
```java
protected int c() {
    return 1440;  // ALWAYS 24 hours
}
```

### 2. User Specified Pattern

**Characteristics**:
- **Duration**: Variable (1-300 hours in HMS)
- **Pattern**: External PERCENT_TABLE paired data
- **Peak**: Defined by pattern data
- **Use case**: Custom temporal distributions, TP-40 storms

**HMS Code** (`aY.java:72`):
```java
protected int c() {
    return this.d().k() * 60;  // User duration * 60
}
```

**FrequencyStorm matches Type 2** (User Specified Pattern)

---

## Variable Duration Support

### HMS Reality

**CORRECTION**: Previous documentation incorrectly stated "HMS only supports 24-hour storms."

**Truth**:
- HMS **SCS storms** are 24-hour only (hardcoded)
- HMS **User Specified Pattern** supports 1-300 hours
- HCFCD M3 models **chose** 24-hour as their standard (not an HMS limitation)

### FrequencyStorm Support

**Current**: Validated for 24-hour storms
**Capable**: Can generate any duration (uses same algorithm as HMS User Pattern)
**HCFCD Default**: 24 hours (for M3 model compatibility)

**Example**:
```python
# 6-hour storm (HMS User Pattern compatible)
hyeto_6hr = FrequencyStorm.generate_hyetograph(
    total_depth=9.10,
    total_duration_min=360,  # 6 hours
    time_interval_min=5
)

# 12-hour storm
hyeto_12hr = FrequencyStorm.generate_hyetograph(
    total_depth=11.10,
    total_duration_min=720,  # 12 hours
    time_interval_min=5
)

# 48-hour storm
hyeto_48hr = FrequencyStorm.generate_hyetograph(
    total_depth=16.20,
    total_duration_min=2880,  # 48 hours
    time_interval_min=15
)
```

**Note**: Only 24-hour has been validated against HMS ground truth. Other durations use scaled pattern approach.

---

## API Reference

### Main Method

```python
FrequencyStorm.generate_hyetograph(
    total_depth: float,
    total_duration_min: int = 1440,
    time_interval_min: int = 5,
    peak_position_pct: float = 67.0
) -> np.ndarray
```

**Parameters**:
- `total_depth`: Total precipitation depth (inches)
- `total_duration_min`: Storm duration in minutes (default: 1440 = 24 hours)
  - Validated: 24 hours (1440 min)
  - Supported: Any duration (HMS User Pattern compatible)
  - HCFCD Default: 1440 min (24 hours)
- `time_interval_min`: Output time step in minutes (default: 5)
  - Common values: 5, 10, 15, 30, 60
  - HCFCD Default: 5 minutes
- `peak_position_pct`: Percent of duration before peak (default: 67)
  - HCFCD Default: 67%
  - HMS SCS Type II: ~50%
  - HMS SCS Type IA: ~30%

**Returns**: numpy array of incremental precipitation depths (inches)

**HCFCD Defaults** (for validation):
```python
# M3 Model D compatible
hyeto = FrequencyStorm.generate_hyetograph(
    total_depth=13.20,
    # All other parameters use HCFCD defaults
)
```

### From DDF Table Method

```python
FrequencyStorm.generate_from_ddf(
    depths: List[float],
    durations: Optional[List[int]] = None,
    peak_position_pct: float = 67.0,
    time_interval_min: int = 5
) -> np.ndarray
```

**Usage**:
```python
# TP-40 depths for Houston 1% AEP
depths = [1.20, 2.10, 4.30, 5.70, 6.70, 8.90, 10.80, 13.20]
durations = [5, 15, 30, 60, 120, 180, 360, 1440]

hyeto = FrequencyStorm.generate_from_ddf(depths, durations)
```

---

## Pattern Information

### Bundled Pattern

**Source**: HCFCD M3 Model D (Brays Bayou) - 1% AEP
**Format**: Dimensionless incremental pattern (288 values, 5-min intervals)
**Peak Position**: 67% of duration
**Validation**: Consistent across 0.2%, 1%, 2%, 10% AEP storms

**Get pattern info**:
```python
info = FrequencyStorm.get_pattern_info()
print(f"Intervals: {info['num_intervals']}")      # 288
print(f"Time step: {info['time_interval_min']}")  # 5 minutes
print(f"Peak position: {info['peak_position']*100:.0f}%")  # 67%
```

---

## HCFCD M3 Model Compatibility

### M3 Model Configuration

**All 21 HCFCD M3 models use**:
- Duration: 24 hours (1440 minutes)
- Time interval: 5 minutes
- Peak position: 67%
- Method: TP-40/Hydro-35 temporal distribution

**FrequencyStorm generates identical output**:
```python
# Generate 1% AEP storm for Model D
hyeto = FrequencyStorm.generate_hyetograph(total_depth=13.20)

# Matches HMS PRECIP-INC output to 10^-6 precision
```

**Validation**:
- ✅ 24-hour storms: RMSE < 10^-6 inches
- ✅ Pattern consistent across all AEP values
- ✅ Total depth conserved
- ✅ Peak position accurate

---

## Validation Summary

### Algorithm Validation

**Source**: HMS 4.13 decompiled source code
**Method**: Direct algorithm comparison
**Result**: **EXACT MATCH**

From extracted HMS code (`feature_dev_notes/hms_frequency_storm_extraction/`):
- FrequencyStorm uses identical cumulative scaling algorithm
- Matches HMS User Specified Pattern implementation
- NOT alternating block method

### Ground Truth Validation

**Source**: HCFCD M3 Model D, 1% AEP, 24-hour storm
**Metric**: RMSE < 0.000001 inches
**Status**: ✅ **VALIDATED**

**Test Results**:
```
FrequencyStorm vs HMS:
  RMSE: 0.000001 inches
  Max diff: 0.000016 inches
  Correlation: 1.000000
  Result: MATCHES HMS (RMSE < 0.001)
```

**See**: `FREQUENCY_STORM_VALIDATION_RESULTS.md` for complete findings

---

## Comparison with Atlas14Storm

### When to Use FrequencyStorm

**Use FrequencyStorm when**:
- Working with HCFCD M3 models (exact compatibility)
- Need TP-40/Hydro-35 temporal patterns
- Validating against HCFCD models
- Using HCFCD rainfall regions

### When to Use Atlas14Storm

**Use Atlas14Storm when**:
- Need modern NOAA Atlas 14 data
- Multiple quartile options required
- Any Atlas 14 region/state
- HEC-RAS boundary conditions
- Non-HCFCD applications

### Key Differences

| Aspect | FrequencyStorm | Atlas14Storm |
|--------|----------------|--------------|
| Algorithm | Cumulative scaling | Cumulative scaling (same!) |
| Data Source | TP-40/Hydro-35 pattern | NOAA Atlas 14 PFDS |
| Validated Durations | 24-hour | 6hr, 12hr, 24hr, 48hr |
| Regions | HCFCD (Houston area) | All Atlas 14 states |
| Quartiles | Fixed (67% peak) | 5 quartiles available |
| Use Case | M3 model validation | Modern design storms |

**Note**: Both use the same underlying algorithm (confirmed via HMS source code)

---

## Parameter Variation for Validation

### Storm Duration

```python
# Test various durations (HMS User Pattern compatible)
for duration_hr in [6, 12, 24, 48]:
    hyeto = FrequencyStorm.generate_hyetograph(
        total_depth=depth_for_duration[duration_hr],
        total_duration_min=duration_hr * 60
    )
```

### Intensity Duration (Time Interval)

```python
# Test various intervals
for interval_min in [5, 10, 15, 30, 60]:
    hyeto = FrequencyStorm.generate_hyetograph(
        total_depth=13.20,
        time_interval_min=interval_min
    )
```

### Intensity Position (Peak Position)

```python
# Test various peak positions
for peak_pct in [25, 33, 50, 67, 75]:
    hyeto = FrequencyStorm.generate_hyetograph(
        total_depth=13.20,
        peak_position_pct=peak_pct
    )
```

---

## Related Documentation

**HMS Source Code**:
- `feature_dev_notes/hms_frequency_storm_extraction/README.md` - Algorithm details
- `feature_dev_notes/hms_frequency_storm_extraction/ALGORITHM.md` - Complete algorithm
- `feature_dev_notes/hms_frequency_storm_extraction/VALIDATION_TEST_PLAN.md` - Test procedures

**Validation**:
- `FREQUENCY_STORM_VALIDATION_RESULTS.md` - Complete validation findings
- `examples/frequency_storm_validation/FINDINGS.md` - Pattern extraction details

**Related Modules**:
- `.claude/rules/hec-hms/atlas14-storms.md` - Atlas14Storm (similar algorithm)
- `.claude/rules/hec-hms/met-files.md` - HmsMet operations
- `.claude/rules/integration/m3-model-integration.md` - M3 model workflows

---

**Status**: Production-ready for HCFCD M3 model validation
**Validation**: 24-hour storms to 10^-6 precision
**Algorithm**: HMS source code verified (cumulative pattern scaling)
**Created**: 2025-12-26 | **Updated**: 2025-12-28
