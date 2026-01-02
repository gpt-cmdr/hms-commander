# Task 055: Frequency Storm Ground Truth Validation (TP-40/Hydro-35)

**Created**: 2025-12-26
**Template**: investigation.md
**Status**: Active
**Priority**: High
**Requester**: Cross-repo integration (HCFCD M3 model compatibility)

---

## Ultimate Goal

**Create `hms_commander.FrequencyStorm` module** that replicates HEC-HMS's "Frequency Based Hypothetical" storm generation (Hydro-35/TP-40/TP-49 method). This enables:

1. **HCFCD M3 model compatibility**: Generate design storms matching original M3 models
2. **RAS-Commander integration**: Provide TP-40 hyetographs for HEC-RAS precipitation BCs
3. **HMS-Commander completeness**: Support both Atlas 14 AND legacy TP-40 storm types

The end state is:
```python
# Generate TP-40 design storm identical to HEC-HMS output
from hms_commander import FrequencyStorm

hyetograph = FrequencyStorm.generate_hyetograph(
    depths=[1.2, 2.1, 4.3, 5.7, 6.7, 8.9, 10.8, 13.2],  # 8 cumulative depths
    total_duration_min=1440,   # 24 hours
    time_interval_min=5,       # 5-minute steps
    peak_position_pct=67,      # Peak at 67% of duration
    storm_type='TP40'          # or 'HYDRO35', 'TP49'
)

# Perfect match to HEC-HMS Frequency Based Hypothetical output
assert abs(hyetograph.sum() - 13.2) < 0.001  # Exact depth conservation
```

---

## Background: HCFCD M3 Model Configuration

### Sample .met File (Brays Bayou D100-00-00)

```
Meteorology: 1%_24HR
     Precipitation Method: Frequency Based Hypothetical
End:

Precip Method Parameters: Frequency Based Hypothetical
     Storm Type: Hydro-35/TP-40/TP-49
     Single Hypothetical Storm Size: Yes
     Convert From Annual Series: No
     Convert to Annual Series: Yes
     Uniform Depth Duration Curve: Yes
     User Specified Storm Area: Yes
     Storm Size: 0.01
     Total Duration: 1440
     Time Interval: 5
     Percent of Duration Before Peak Rainfall: 67
     Depth-Area Reduction Method: TP-40
     Depth: 1.2000
     Depth: 2.1000
     Depth: 4.3000
     Depth: 5.7000
     Depth: 6.7000
     Depth: 8.9000
     Depth: 10.800
     Depth: 13.200
End:
```

### Key Parameters Explained

| Parameter | Value | Meaning |
|-----------|-------|---------|
| **Storm Type** | Hydro-35/TP-40/TP-49 | Uses TP-40 temporal distribution algorithm |
| **Total Duration** | 1440 | 24 hours (in minutes) |
| **Time Interval** | 5 | Output at 5-minute timesteps (288 values + 1) |
| **Peak Position** | 67 | Peak intensity at 67% of duration (~hour 16) |
| **Storm Size** | 0.01 | Negligible area (point precipitation) |
| **Depth values** | 8 | Cumulative depths at standard durations |

### Depth Duration Table (HCFCD - Model D)

| Duration Index | Duration (assumed) | 10% Depth | 2% Depth | 1% Depth | 0.2% Depth |
|----------------|-------------------|-----------|----------|----------|------------|
| 1 | 5 min? | 0.9 | 1.1 | 1.2 | 1.4 |
| 2 | 15 min? | 1.5 | 1.9 | 2.1 | 2.6 |
| 3 | 30 min? | 2.9 | 3.8 | 4.3 | 5.5 |
| 4 | 1 hr? | 3.6 | 5.0 | 5.7 | 7.6 |
| 5 | 2 hr? | 4.1 | 5.8 | 6.7 | 9.2 |
| 6 | 3 hr? | 5.1 | 7.6 | 8.9 | 12.8 |
| 7 | 6 hr? | 6.2 | 9.2 | 10.8 | 15.5 |
| 8 | 24 hr | 7.6 | 11.3 | 13.2 | 18.9 |

**Research Required**: Confirm duration mapping for 8 depth values.

---

## Comparison with Atlas 14

| Aspect | Atlas 14 | FrequencyStorm (TP-40) |
|--------|----------|------------------------|
| **Met Method** | Hypothetical Storm | Frequency Based Hypothetical |
| **Storm Type** | Specified Pattern (from DSS) | Hydro-35/TP-40/TP-49 |
| **Depth Input** | Single 24-hr total depth | 8 cumulative depths |
| **Temporal Source** | NOAA temporal distribution | Built-in algorithm |
| **Peak Control** | Quartile selection | Fixed percentage (67%) |
| **Module** | Atlas14Storm (COMPLETE) | FrequencyStorm (TO BE CREATED) |

---

## Algorithm Research Required

### Questions to Answer

1. **What are the 8 standard durations?**
   - Need to verify from HEC-HMS documentation or source code
   - Likely: 5, 15, 30min, 1, 2, 3, 6, 24hr

2. **How does temporal disaggregation work?**
   - Depths are cumulative (increasing sequence)
   - Algorithm converts to incremental intensities
   - Then arranges around peak position (67%)

3. **What is the TP-40/Hydro-35 pattern?**
   - Different from Atlas 14 quartile patterns
   - Uses depth ratios between durations
   - Peak position explicitly specified

4. **How does Depth-Area Reduction work?**
   - TP-40 method reduces point rainfall for area
   - For point precip (Storm Size = 0.01), likely no reduction
   - Can potentially ignore for first implementation

### Reference Documents

1. **NOAA Technical Paper 40** (TP-40): "Rainfall Frequency Atlas of the United States"
2. **NOAA Technical Paper 49** (TP-49): "Probable Maximum Precipitation"
3. **Hydro-35**: "Five- to 60-Minute Precipitation Frequency"
4. **HEC-HMS Technical Reference Manual**: Chapter 4.2.1 (Frequency Storm)
5. **HEC-HMS User's Manual**: Frequency Storm section

---

## Validation Approach (6 Proofs)

Same as Atlas 14 validation:

| # | Proof | Description | Acceptance Criteria |
|---|-------|-------------|---------------------|
| 1 | Total Depth Conservation | Sum of hyetograph = 24-hr depth | < 0.001 in difference |
| 2 | Temporal Pattern Match | Intensity distribution matches HMS | < 0.001 in at each step |
| 3 | Peak Timing | Peak at 67% of duration | Correct timestep |
| 4 | Multi-AEP Consistency | All frequencies work | All 4 AEPs pass |
| 5 | Algorithm Equivalence | Code matches HMS docs | Code review |
| 6 | HMS Ground Truth | Compare vs PRECIP-INC | < 0.01 in max diff |

---

## Test Matrix

### Primary Test Cases (Model D - Brays Bayou)

| Storm | AEP | Met File | Expected 24-hr Depth |
|-------|-----|----------|---------------------|
| 10% | 10-year | 10__24HR.met | 7.6 in |
| 2% | 50-year | 2__24HR.met | 11.3 in |
| 1% | 100-year | 1__24HR.met | 13.2 in |
| 0.2% | 500-year | 0.2__24HR.met | 18.9 in |

### Secondary Test Cases (Other Models)

| Model | Unit | AEP | Purpose |
|-------|------|-----|---------|
| A | A100-00-00 | 1% | Clear Creek (different rainfall zone) |
| K | K100-L100 | 1% | Cypress Creek |
| G | G100-00-00 | 1% | San Jacinto |
| P | P100-00-00 | 1% | Greens Bayou |

---

## Implementation Plan

### Phase 1: Research & Analysis (Current)

**Notebook**: `01_M3_Analysis.ipynb`

1. Parse all M3 met files to extract TP-40 parameters
2. Build depth table for all M3 models/storms
3. Identify variations across rainfall zones
4. Document all parameter combinations found

### Phase 2: Algorithm Research

**Notebook**: `02_Algorithm_Research.ipynb`

1. Research TP-40 algorithm in HEC-HMS docs
2. Find duration mapping for 8 depth values
3. Document temporal disaggregation method
4. Create algorithm specification

### Phase 3: Ground Truth Collection

**Notebook**: `04_Extract_Ground_Truth.ipynb`

1. Run M3 HMS projects (or use existing DSS output)
2. Extract PRECIP-INC from DSS output
3. Store as validation dataset (CSV)

### Phase 4: Module Implementation

**File**: `hms_commander/FrequencyStorm.py`

1. Create FrequencyStorm class (static methods)
2. Implement `generate_hyetograph()` method
3. Match HEC-HMS algorithm exactly
4. Add parameter validation

### Phase 5: Validation

**Notebook**: `05_Validate.ipynb`

1. Compare generated hyetographs vs ground truth
2. Document all 6 proofs
3. Create validation summary table
4. Certify for production use

---

## Expected API

```python
from hms_commander import FrequencyStorm

# Generate from M3-style depths
hyetograph = FrequencyStorm.generate_hyetograph(
    depths=[1.2, 2.1, 4.3, 5.7, 6.7, 8.9, 10.8, 13.2],
    total_duration_min=1440,
    time_interval_min=5,
    peak_position_pct=67,
    storm_type='TP40'
)

# Generate from HCFCD rainfall zone
hyetograph = FrequencyStorm.generate_from_hcfcd(
    rainfall_zone=3,           # HCFCD rainfall zone (1-4)
    aep_percent=1.0,           # 1% AEP (100-year)
    duration_hours=24,
    time_interval_min=5
)

# Get depth-duration table
ddf = FrequencyStorm.get_hcfcd_depths(rainfall_zone=3, aep_percent=1.0)
# Returns: [1.2, 2.1, 4.3, 5.7, 6.7, 8.9, 10.8, 13.2]
```

---

## File Structure

```
examples/frequency_storm_validation/
├── 00_README.md                    # Overview
├── 01_M3_Analysis.ipynb           # M3 met file analysis
├── 02_Algorithm_Research.ipynb    # TP-40 algorithm research
├── 03_HCFCD_Data_Collection.ipynb # HCFCD rainfall data
├── 04_Extract_Ground_Truth.ipynb  # HMS ground truth
├── 05_Validate.ipynb              # Validation proofs
├── cache/                         # Extracted data
│   └── m3_met_parameters.csv      # Parsed met files
├── output/                        # Generated hyetographs
│   └── ground_truth/              # HMS PRECIP-INC
└── test_*.py                      # Test scripts
```

---

## Dependencies

- **M3 Models**: Extracted to `m3_hms_projects/`
- **HEC-HMS**: 4.11+ for running M3 models
- **HmsDss**: For DSS extraction (PRECIP-INC)
- **Atlas14Storm**: Reference implementation pattern

---

## Success Criteria

1. FrequencyStorm module generates hyetographs with < 0.001 in depth difference
2. All 6 validation proofs pass
3. 4 AEP events for Model D validated
4. At least 2 additional M3 models validated
5. API documented with examples
6. Integration with RAS-Commander demonstrated

---

## Related Tasks

- **Task 050**: Atlas 14 Hyetograph Ground Truth (COMPLETE - reference)
- **Cross-repo**: RAS-Commander precipitation BC generation

---

## References

### Existing Implementation (Pattern)

- `hms_commander/Atlas14Storm.py` - Reference for module structure
- `examples/atlas14_validation/` - Reference for validation approach
- `examples/08_atlas14_hyetograph_generation.ipynb` - Reference for notebook

### M3 Models

- `m3_hms_projects/D/D100-00-00/` - Brays Bayou (primary test)
- `hms_commander/HmsM3Model.py` - M3 project access
- `.claude/rules/integration/m3-model-integration.md` - M3 workflows

### HEC-HMS Documentation

- HEC-HMS Technical Reference Manual (Chapter 4: Meteorology)
- HEC-HMS User's Manual (Frequency Storm section)

---

**Document**: 055-frequency-storm-ground-truth.md
**Location**: agent_tasks/tasks/
**Created**: 2025-12-26
