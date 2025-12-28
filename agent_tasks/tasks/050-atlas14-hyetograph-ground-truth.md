# Task 050: Atlas 14 Hyetograph Ground Truth Validation

**Created**: 2025-12-25
**Template**: investigation.md
**Status**: Requested
**Priority**: High
**Requester**: Cross-repo validation (ras-commander)

---

## Ultimate Goal

**HMS-Commander will be used as a submodule by RAS-Commander** to duplicate HEC-HMS's internal hyetograph generation functionality. This validation suite will be used to:

1. **Build new logic** for HMS-Commander that replicates HEC-HMS's "Frequency Based Hypothetical" storm generation
2. **Validate the implementation** against actual HEC-HMS output (ground truth)
3. **Provide RAS-Commander** with a tested, validated precipitation module via submodule import

The end state is:
```python
# In ras-commander (future)
from hms_commander.precip import Atlas14Storm  # Submodule import

# Generate design storm identical to HEC-HMS output
storm = Atlas14Storm.from_coordinates(lat=38.9, lon=-77.0)
hyetograph = storm.generate(
    aep_percent=1.0,
    duration_hours=24,
    storm_type='SCS_Type_II',
    interval_minutes=60
)
```

---

## Goal

Create a comprehensive validation suite proving three-way algorithmic equivalence:

```
RAS-Commander StormGenerator = HMS-Commander Atlas14Converter = HEC-HMS Internal
```

This requires:
1. **Converting M3 model to Atlas 14** DDF values
2. **Testing all function parameters** available in both libraries
3. **Extracting HEC-HMS PRECIP-INC output** as ground truth
4. **Creating Jupyter notebooks** that iterate through all parameter combinations

---

## Comprehensive Parameter Validation Matrix

### Storm Type / Temporal Distribution

HEC-HMS "Frequency Based Hypothetical" supports these storm types:

| Storm Type | Description | Region | Priority |
|------------|-------------|--------|----------|
| **SCS Type II** | Standard 24-hour design storm | Most of CONUS | HIGH |
| **SCS Type I** | Pacific maritime (interior PNW) | Oregon, Washington | MEDIUM |
| **SCS Type IA** | Pacific maritime (coastal) | Pacific Coast | MEDIUM |
| **SCS Type III** | Gulf of Mexico/Atlantic coastal | Florida, Gulf States | MEDIUM |
| `Hydro-35/TP-40/TP-49` | Pre-Atlas 14 (current M3) | Legacy | LOW |
| `User-Specified` | Custom temporal pattern | Any | LOW |

**Validation Required**: Both ras-commander and hms-commander must support all SCS types.

### Annual Exceedance Probability (AEP)

| AEP | Return Period (ARI) | Test Priority |
|-----|---------------------|---------------|
| 50% | 2-year | HIGH |
| 20% | 5-year | MEDIUM |
| 10% | 10-year | HIGH |
| 4% | 25-year | MEDIUM |
| 2% | 50-year | HIGH |
| **1%** | **100-year** | **HIGH** |
| 0.5% | 200-year | MEDIUM |
| 0.2% | 500-year | HIGH |

### Storm Duration

| Duration | Use Case | Test Priority |
|----------|----------|---------------|
| 6-hour | Urban/Small watersheds | MEDIUM |
| 12-hour | Medium watersheds | MEDIUM |
| **24-hour** | **Standard design** | **HIGH** |
| 48-hour | Large watersheds | LOW |
| 72-hour | Very large watersheds | LOW |

### Time Interval

| Interval | Use Case | Test Priority |
|----------|----------|---------------|
| **5 min** | Urban, detailed | **HIGH** |
| 15 min | Standard detailed | HIGH |
| 30 min | Medium resolution | MEDIUM |
| **60 min** | Standard resolution | **HIGH** |

### Peak Position

| Position | Description | Test Priority |
|----------|-------------|---------------|
| 33% | Front-loaded | MEDIUM |
| 50% | Centered | HIGH |
| **67%** | **Standard (current M3)** | **HIGH** |
| 75% | Back-loaded | MEDIUM |

---

## Phase 1: M3 Model Conversion to Atlas 14

### Critical Discovery: Example Project Available

**User has created a working example**:
`examples/example_projects/A100-00-00_HMS411 - Atlas 14 Example/`

This example demonstrates:
- Converting from "Frequency Based Hypothetical" to "Hypothetical Storm" method
- Using Atlas 14 temporal distributions imported to DSS
- Both "Specified Pattern" and "SCS Type II" storm type options

### Key Method Difference

**Original M3 (Frequency Based Hypothetical)**:
```
Precipitation Method: Frequency Based Hypothetical
Storm Type: Hydro-35/TP-40/TP-49
Depth 5: 1.2000
Depth 10: 1.7310
...
Depth 1440: 13.500
```

**Atlas 14 Approach (Hypothetical Storm)**:
```
Precipitation Method: Hypothetical Storm
Precipitation Method: Point Depth
Storm Depth: 19.999    <- Single total depth from Atlas 14
Storm Type: Specified Pattern   <- OR "SCS Type II"
```

### Atlas 14 Temporal Distribution Format

**URL Pattern**: `https://hdsc.nws.noaa.gov/pub/hdsc/data/{state}/{state}_{region}_{duration}h_temporal.csv`

**Example (Houston, TX)**: `https://hdsc.nws.noaa.gov/pub/hdsc/data/tx/tx_3_24h_temporal.csv`

**CSV Structure** (5 tables per file):
1. `FIRST-QUARTILE CASES` - Peak in 0-6 hours
2. `SECOND-QUARTILE CASES` - Peak in 6-12 hours
3. `THIRD-QUARTILE CASES` - Peak in 12-18 hours
4. `FOURTH-QUARTILE CASES` - Peak in 18-24 hours
5. `ALL CASES` - Combined distribution

**Each table format**:
- Time column: 0 to 24 hours in 0.5-hour increments (49 rows)
- 9 probability columns: 90%, 80%, 70%, 60%, 50%, 40%, 30%, 20%, 10%
- Values: Cumulative percentages of total precipitation by given time

### Example Data (All Cases, 24hr, TX Region 3)
```csv
hours,90%,80%,70%,60%,50%,40%,30%,20%,10%
0,0,0,0,0,0,0,0,0,0
0.5, 0.11, 0.44, 0.75, 0.94, 1.30, 1.97, 2.79, 4.24, 7.71
...
12.0,19.48,32.00,41.07,51.30,61.51,71.47,82.57,93.13,99.33  <- ~50% point
...
24.0,100.00,100.00,100.00,100.00,100.00,100.00,100.00,100.00,100.00
```

### Atlas 14 DDF CSV Format

**Example** (`PF_Depth_English_PDS.csv`):
```csv
Location name: Houston, Texas, USA
Latitude: 29.6320 Degree
Longitude: -95.1352 Degree

PRECIPITATION FREQUENCY ESTIMATES
by duration for ARI (years):, 1,2,5,10,25,50,100,200,500,1000
5-min:, 0.502,0.600,0.756,0.888,1.07,1.22,1.37,1.53,1.76,1.94
...
24-hr:, 3.88,5.33,7.38,9.35,12.3,14.9,17.9,21.4,26.8,31.5
```

### Conversion Workflow

1. **Download Atlas 14 DDF Values**
   ```python
   # Download from NOAA PFDS for project location
   ddf_url = "https://hdsc.nws.noaa.gov/hdsc/pfds/..."
   # Save as: Atlas 14 CSV/PF_Depth_English_PDS.csv
   ```

2. **Download Atlas 14 Temporal Distributions**
   ```python
   # Determine region from NOAA Atlas 14 Volume/Region maps
   temporal_url = "https://hdsc.nws.noaa.gov/pub/hdsc/data/tx/tx_3_24h_temporal.csv"
   # Save as: Atlas 14 CSV/tx_3_24h_temporal.csv
   ```

3. **Import Temporal Distributions to DSS**
   ```python
   # Simulate the Atlas 14 Importer tool
   # Create paired data records in DSS for ALL quartiles
   # Output: data/TX_R3_24H.dss
   ```

4. **Create Met Files for Each Test Case**
   ```python
   # For each AEP/duration combination:
   # - Set Storm Depth from DDF table
   # - Set Storm Type to "Specified Pattern" or SCS type
   # - Reference imported temporal pattern
   ```

5. **Create Runs with Unique Output DSS Files**
   ```python
   # Each run outputs to uniquely named DSS:
   # - 0.2__500YR__RUN.dss
   # - 1__100YR_RUN.dss
   # - 2__50YR_RUN.dss
   # - 10__10YR_RUN.dss
   ```

---

## Phase 2: Validation Test Matrix

### Minimum Viable Test Suite (MVP)

| Test ID | Storm Type | AEP | Duration | Interval | Peak Pos |
|---------|------------|-----|----------|----------|----------|
| **T01** | SCS Type II | 1% | 24hr | 60min | 50% |
| **T02** | SCS Type II | 1% | 24hr | 60min | 67% |
| **T03** | SCS Type II | 10% | 24hr | 60min | 50% |
| **T04** | SCS Type II | 1% | 24hr | 5min | 50% |
| **T05** | SCS Type I | 1% | 24hr | 60min | 50% |
| **T06** | SCS Type III | 1% | 24hr | 60min | 50% |

### Extended Test Suite

| Test ID | Storm Type | AEP | Duration | Interval | Peak Pos |
|---------|------------|-----|----------|----------|----------|
| T07 | SCS Type II | 2% | 24hr | 60min | 50% |
| T08 | SCS Type II | 0.2% | 24hr | 60min | 50% |
| T09 | SCS Type II | 1% | 12hr | 60min | 50% |
| T10 | SCS Type II | 1% | 6hr | 15min | 50% |
| T11 | SCS Type IA | 1% | 24hr | 60min | 50% |
| T12 | SCS Type II | 1% | 24hr | 15min | 33% |
| T13 | SCS Type II | 1% | 24hr | 15min | 75% |

---

## Phase 3: Ground Truth Extraction

### For Each Test Case

```python
from hms_commander import init_hms_project, HmsCmdr
from hms_commander.dss import DssCore

# 1. Initialize project
project_path = "examples/atlas14_validation/"
hms = init_hms_project(project_path)

# 2. Execute run
run_name = "T01_SCS2_1pct_24hr_60min_50pct"
HmsCmdr.compute_run(run_name, hms_object=hms)

# 3. Extract PRECIP-INC from DSS
dss_file = hms.run_df.loc[run_name, 'dss_file']
catalog = DssCore.get_catalog(dss_file)

# Find PRECIP-INC pathnames
precip_paths = [p for p in catalog if 'PRECIP-INC' in p]

# Extract time series
for pathname in precip_paths:
    ts = DssCore.read_timeseries(dss_file, pathname)
    ts.to_csv(f"ground_truth/{run_name}_{pathname.split('/')[2]}.csv")
```

### Output Structure

```
examples/atlas14_validation/
├── ground_truth/
│   ├── T01_SCS2_1pct_24hr_60min_50pct_B100H.csv
│   ├── T01_SCS2_1pct_24hr_60min_50pct_B100G.csv
│   ├── ...
│   ├── T02_SCS2_1pct_24hr_60min_67pct_B100H.csv
│   └── ...
├── met/
│   ├── T01_Atlas14.met
│   ├── T02_Atlas14.met
│   └── ...
├── run/
│   ├── T01_SCS2_1pct_24hr_60min_50pct.run
│   └── ...
└── validation_summary.csv
```

---

## Phase 4: Cross-Validation with Python Libraries

### RAS-Commander Validation

```python
from ras_commander.precip import StormGenerator
import pandas as pd

# Load ground truth
hms_output = pd.read_csv("ground_truth/T01_SCS2_1pct_24hr_60min_50pct_B100H.csv")

# Generate with ras-commander (same parameters)
gen = StormGenerator.download_from_coordinates(lat=LAT, lon=LON)
ras_hyeto = gen.generate_hyetograph(
    ari=100,
    duration_hours=24,
    position_percent=50,
    method='alternating_block',  # or 'scs_type_ii'
    interval_minutes=60
)

# Compare
diff = abs(hms_output['value'] - ras_hyeto['incremental_depth']).max()
assert diff < 0.0001, f"RAS mismatch: {diff} inches"
```

### HMS-Commander Validation

```python
from hms_agents.hms_atlas14 import Atlas14Converter

converter = Atlas14Converter()
hms_depths = converter.generate_depth_values(
    atlas14_data=atlas14_data,
    aep='1%',
    total_duration=1440,
    time_interval=60,
    peak_position=50
)

# Compare
diff = abs(hms_output['value'].cumsum() - np.array(hms_depths)).max()
assert diff < 0.0001, f"HMS mismatch: {diff} inches"
```

---

## Deliverables

### Required Outputs

1. **Atlas 14 Validation Project**
   - `examples/atlas14_validation/` - Complete HMS project with all test cases

2. **Ground Truth Data**
   - CSV files with HEC-HMS PRECIP-INC output for each test case
   - `validation_summary.csv` - All test results in one table

3. **Validation Notebook**
   - `examples/XX_atlas14_ground_truth_validation.ipynb`
   - Demonstrates loading ground truth and comparing against HMS-Commander

4. **Cross-Repo Deliverable**
   - Copy ground truth CSVs to `ras-commander/examples/atlas14_ground_truth/`
   - Update `ras-commander/examples/723_atlas14_validation_vs_hms.ipynb`

### Documentation

1. **Parameter Support Matrix**
   - Document which parameters each library supports
   - Identify gaps requiring implementation

2. **SCS Storm Type Implementation Status**

   | Storm Type | HMS-Commander | RAS-Commander | HEC-HMS |
   |------------|---------------|---------------|---------|
   | SCS Type I | ? | ? | Yes |
   | SCS Type IA | ? | ? | Yes |
   | SCS Type II | ? | ? | Yes |
   | SCS Type III | ? | ? | Yes |
   | Alternating Block | Yes | Yes | Yes |

---

## Implementation Notes

### SCS Type Temporal Distributions

The SCS (NRCS) 24-hour storm types have defined cumulative distribution curves:

**SCS Type II** (most common, covers most of CONUS):
```
Hour  Cumulative %
0     0.0
2     1.1
4     2.2
6     4.8
8     9.8
10    18.1
11.5  66.3  <- peak region
12    74.7
14    83.5
16    89.2
18    93.5
20    96.7
22    98.9
24    100.0
```

**Implementation Required**: Both ras-commander and hms-commander need methods to:
1. Accept `storm_type` parameter (e.g., 'SCS_Type_II')
2. Apply the appropriate cumulative distribution curve
3. Scale to match Atlas 14 total depth for specified AEP/duration

### Alternating Block vs SCS Distribution

**Alternating Block Method** (current implementation):
- Arranges incremental depths with peak at specified position
- Simple, flexible, well-documented (Chow, Maidment, Mays 1988)
- Peak can be any position (0-100%)

**SCS Distribution Method**:
- Uses pre-defined cumulative curves from NRCS
- Peak is fixed at ~50% for Type II
- Standard for FEMA and regulatory submittals

**Recommendation**: Validate Alternating Block first (already implemented), then add SCS types as needed.

---

## Acceptance Criteria

### Phase 1 (M3 Conversion)
- [ ] M3 project location documented (lat/lon)
- [ ] Atlas 14 DDF values downloaded for location
- [ ] At least 6 test met models created
- [ ] At least 6 test runs configured

### Phase 2 (Ground Truth Extraction)
- [ ] All MVP test cases (T01-T06) executed successfully
- [ ] PRECIP-INC extracted for each test case
- [ ] Ground truth CSVs saved with documented format

### Phase 3 (Python Library Validation)
- [ ] HMS-Commander matches HEC-HMS within 0.0001 inches
- [ ] RAS-Commander matches HEC-HMS within 0.0001 inches
- [ ] Validation notebook created and executed

### Phase 4 (Documentation)
- [ ] Parameter support matrix documented
- [ ] SCS type implementation status documented
- [ ] Cross-repo deliverables provided to ras-commander

---

## Related Files

**hms-commander**:
- `hms_agents/hms_atlas14/atlas14_converter.py` - Alternating Block implementation
- `examples/m3_version_test/A/A100-00-00_HMS411/*.met` - Current frequency storm configs

**ras-commander**:
- `ras_commander/precip/StormGenerator.py` - Alternating Block implementation
- `ras_commander/precip/CLAUDE.md` - Documents SCS Types (implementation status unclear)
- `examples/723_atlas14_validation_vs_hms.ipynb` - Current validation notebook

---

## Cross-Repository Coordination

This task requires human-in-the-loop approval for:

1. M3 model modifications (update to Atlas 14)
2. Test case parameter selection
3. Ground truth data handoff to ras-commander
4. Final validation notebook review

See `agent_tasks/cross-repo/README.md` for coordination protocol.

---

## Technical References

1. **Chow, V.T., Maidment, D.R., Mays, L.W. (1988)**. Applied Hydrology, Section 14.4 - Alternating Block Method
2. **NRCS TR-55 (1986)**. Urban Hydrology for Small Watersheds - SCS Type Curves
3. **NOAA Atlas 14**. Precipitation-Frequency Atlas of the United States
4. **HEC-HMS Technical Reference Manual**. Chapter 7 - Meteorologic Models

---

## RAS-Commander Current Implementation (Reference)

The following documents what is **already implemented** in ras-commander's `StormGenerator` class. HMS-Commander's implementation should match this API and produce identical results.

### StormGenerator.py API (27 KB)

**Location**: `ras_commander/precip/StormGenerator.py`

**Design Storm Creation**:
- `generate_design_storm()` - Create Atlas 14 design storm hyetograph
- `get_precipitation_frequency()` - Query Atlas 14 point precipitation values
- `apply_temporal_distribution()` - Apply standard temporal patterns (SCS Type II, etc.)

**AEP Events Supported** (Annual Exceedance Probability):
- Standard AEPs: 50%, 20%, 10%, 4%, 2%, 1%, 0.5%, 0.2%
- Common durations: 6hr, 12hr, 24hr, 48hr
- Custom AEP and duration supported

**Temporal Distributions** (documented, implementation status needs verification):
- **SCS Type II** - Standard for most of US
- **SCS Type IA** - Pacific maritime climate
- **SCS Type III** - Gulf Coast and Florida
- **Custom distributions** - User-defined hyetograph patterns

**Spatial Processing**:
- `interpolate_point_values()` - Interpolate Atlas 14 values to grid
- `apply_areal_reduction()` - Apply ARF (Areal Reduction Factor) for large watersheds
- `generate_multi_point_storms()` - Spatially distributed design storms

**Output Formats**:
- HEC-HMS precipitation gage file
- HEC-RAS DSS precipitation
- Tabular hyetograph (CSV)

### RAS-Commander Atlas 14 Workflow

```python
from ras_commander.precip import StormGenerator

# 1. Specify Location
location = (38.9072, -77.0369)  # Lat/lon

# 2. Query Atlas 14 Values
precip_value = StormGenerator.get_precipitation_frequency(
    location=location,
    duration_hours=24,
    aep_percent=1.0  # 1% = 100-year event
)

# 3. Generate Design Storm
hyetograph = StormGenerator.generate_design_storm(
    total_precip=precip_value,
    duration_hours=24,
    distribution="SCS_Type_II",
    interval_minutes=15  # 15-minute increments
)

# 4. Export to HEC-RAS/HMS
StormGenerator.export_to_dss(
    hyetograph,
    dss_file="design_storm.dss",
    pathname="/PROJECT/PRECIP/DESIGN//15MIN/SYN/"
)
```

### Multi-Event Workflow (RAS-Commander)

```python
from ras_commander.precip import StormGenerator

# Define AEP suite (10%, 2%, 1%, 0.2%)
aep_events = [10, 2, 1, 0.2]

for aep in aep_events:
    # Query Atlas 14
    precip = StormGenerator.get_precipitation_frequency(
        location=(38.9, -77.0),
        duration_hours=24,
        aep_percent=aep
    )

    # Generate design storm
    hyetograph = StormGenerator.generate_design_storm(
        total_precip=precip,
        duration_hours=24,
        distribution="SCS_Type_II"
    )

    # Export to DSS
    dss_file = f"design_storm_{aep}pct.dss"
    StormGenerator.export_to_dss(hyetograph, dss_file)
```

### Areal Reduction Factors (ARF)

```python
# Point precipitation (from Atlas 14)
point_precip = StormGenerator.get_precipitation_frequency(
    location=(38.9, -77.0),
    duration_hours=24,
    aep_percent=1.0
)

# Apply ARF for 500 sq mi watershed
watershed_area_sqmi = 500
reduced_precip = StormGenerator.apply_areal_reduction(
    point_precip=point_precip,
    area_sqmi=watershed_area_sqmi,
    duration_hours=24
)

print(f"Point: {point_precip:.2f} in")
print(f"Areal (500 sq mi): {reduced_precip:.2f} in")
```

**ARF Guidance**:
- Small watersheds (< 10 sq mi): ARF ≈ 1.0 (use point values)
- Medium watersheds (10-100 sq mi): ARF = 0.95-0.98
- Large watersheds (> 100 sq mi): ARF < 0.95 (significant reduction)

### RAS-Commander Example Notebooks

These notebooks demonstrate current ras-commander precipitation workflows:

| Notebook | Purpose |
|----------|---------|
| `examples/24_aorc_precipitation.ipynb` | AORC retrieval and processing |
| `examples/103_Running_AEP_Events_from_Atlas_14.ipynb` | Single-project Atlas 14 workflow |
| `examples/104_Atlas14_AEP_Multi_Project.ipynb` | Batch processing multiple projects |
| `examples/723_atlas14_validation_vs_hms.ipynb` | **Current validation notebook** (needs ground truth) |

### Dependencies (RAS-Commander)

**Required**:
- pandas (time series handling)
- numpy (numerical operations)
- xarray (for AORC NetCDF data)
- requests (Atlas 14 API access)

**Optional**:
- geopandas (spatial operations on watersheds)
- rasterio (AORC grid processing)
- pydsstools (DSS export, lazy-loaded)

### NOAA Atlas 14 Data Source

- **Provider**: NOAA National Weather Service
- **Access**: NOAA HDSC Precipitation Frequency Data Server (PFDS)
- **Format**: JSON API response
- **Coverage**: CONUS, Hawaii, Puerto Rico
- **Documentation**: https://hdsc.nws.noaa.gov/pfds/

**Atlas 14 Regions** (auto-detected by lat/lon):
- CONUS coverage (volumes 1-11)
- Hawaii and Puerto Rico supported

---

## Notebook-Based Validation Approach

### Overview

The validation suite should be implemented as **Jupyter notebooks** that:
1. Take the M3 model and update met files for frequency storms
2. Iterate through all parameter combinations to create test cases
3. Execute HEC-HMS and extract PRECIP-INC output
4. Compare against Python library implementations

### Recommended Notebook Structure

```
examples/atlas14_validation/
├── 01_M3_to_Atlas14_Conversion.ipynb      # Convert M3 model to Atlas 14
├── 02_Create_Test_Suite.ipynb              # Generate all test cases (T01-T13)
├── 03_Execute_HEC_HMS.ipynb                # Run HEC-HMS for all test cases
├── 04_Extract_Ground_Truth.ipynb           # Extract PRECIP-INC from DSS
├── 05_Validate_HMS_Commander.ipynb         # Compare HMS-Commander vs ground truth
├── 06_Validate_RAS_Commander.ipynb         # Compare RAS-Commander vs ground truth
└── 07_Summary_Report.ipynb                 # Generate validation summary report
```

### Notebook 01: M3 to Atlas 14 Conversion

**Purpose**: Convert existing M3 model from TP-40 to Atlas 14 DDF values

**Steps**:
1. Read M3 project and determine location (lat/lon)
2. Query NOAA Atlas 14 API for location
3. Update .met file with Atlas 14 DDF values
4. Change storm type from "Hydro-35/TP-40/TP-49" to "SCS Type II" (or other)
5. Save modified met file

**Key Code**:
```python
# Determine project location
from hms_commander import init_hms_project
hms = init_hms_project("examples/m3_version_test/A/A100-00-00_HMS411/")
lat, lon = get_project_centroid(hms)  # From GIS files or manual input

# Download Atlas 14 data
from hms_agents.hms_atlas14 import Atlas14Downloader
atlas14 = Atlas14Downloader()
ddf_data = atlas14.download_from_coordinates(lat=lat, lon=lon)

# Update met file
update_met_file_ddf_values(met_file, ddf_data)
update_met_file_storm_type(met_file, "SCS Type II")
```

### Notebook 02: Create Test Suite

**Purpose**: Generate all test case configurations (T01-T13)

**Iteration Logic**:
```python
# Define parameter combinations
test_matrix = [
    # Test ID, Storm Type, AEP%, Duration_hr, Interval_min, Peak_Position%
    ("T01", "SCS Type II", 1.0, 24, 60, 50),
    ("T02", "SCS Type II", 1.0, 24, 60, 67),
    ("T03", "SCS Type II", 10.0, 24, 60, 50),
    ("T04", "SCS Type II", 1.0, 24, 5, 50),
    ("T05", "SCS Type I", 1.0, 24, 60, 50),
    ("T06", "SCS Type III", 1.0, 24, 60, 50),
    # ... extended tests T07-T13
]

# Generate met and run files for each test case
for test_id, storm_type, aep, duration, interval, peak_pos in test_matrix:
    create_test_met_file(test_id, storm_type, aep, duration, interval, peak_pos)
    create_test_run_file(test_id)
    print(f"Created test case: {test_id}")
```

### Notebook 03: Execute HEC-HMS

**Purpose**: Run HEC-HMS for all test cases

```python
from hms_commander import HmsCmdr

# Execute all test runs
for test_id in test_ids:
    run_name = f"{test_id}_SCS2_1pct_24hr_60min_50pct"
    print(f"Executing: {run_name}")
    HmsCmdr.compute_run(run_name, hms_object=hms)

# Verify all runs completed
for test_id in test_ids:
    dss_file = get_dss_file(test_id)
    assert dss_file.exists(), f"Run failed: {test_id}"
```

### Notebook 04: Extract Ground Truth

**Purpose**: Extract PRECIP-INC time series from DSS output

```python
from hms_commander.dss import DssCore
import pandas as pd

ground_truth = {}

for test_id in test_ids:
    dss_file = get_dss_file(test_id)
    catalog = DssCore.get_catalog(dss_file)

    # Find PRECIP-INC pathnames
    precip_paths = [p for p in catalog if 'PRECIP-INC' in p]

    for pathname in precip_paths:
        ts = DssCore.read_timeseries(dss_file, pathname)

        # Save to CSV
        csv_file = f"ground_truth/{test_id}_{pathname.split('/')[2]}.csv"
        ts.to_csv(csv_file)

        # Store in memory
        ground_truth[test_id] = ts

print(f"Extracted {len(ground_truth)} ground truth time series")
```

### Notebook 05-06: Validation

**Purpose**: Compare Python libraries against ground truth

```python
import pandas as pd
import numpy as np

validation_results = []

for test_id, params in test_cases.items():
    # Load ground truth
    gt = pd.read_csv(f"ground_truth/{test_id}_B100H.csv")

    # Generate with HMS-Commander
    hms_hyeto = generate_with_hms_commander(params)

    # Generate with RAS-Commander
    ras_hyeto = generate_with_ras_commander(params)

    # Calculate differences
    hms_diff = abs(gt['value'] - hms_hyeto['value']).max()
    ras_diff = abs(gt['value'] - ras_hyeto['value']).max()

    validation_results.append({
        'test_id': test_id,
        'hms_commander_diff': hms_diff,
        'ras_commander_diff': ras_diff,
        'hms_pass': hms_diff < 0.0001,
        'ras_pass': ras_diff < 0.0001
    })

results_df = pd.DataFrame(validation_results)
print(results_df)
```

---

## Implementation Checklist

### Phase 0: Notebook Setup
- [ ] Create `examples/atlas14_validation/` folder structure
- [ ] Create notebook 01 skeleton
- [ ] Verify M3 model can be loaded and modified

### Phase 1: M3 Conversion (Notebook 01)
- [ ] Determine M3 project lat/lon
- [ ] Query NOAA Atlas 14 API
- [ ] Update .met file with Atlas 14 DDF values
- [ ] Test modified model runs in HEC-HMS

### Phase 2: Test Suite Generation (Notebook 02)
- [ ] Implement parameter matrix iteration
- [ ] Generate T01-T06 (MVP) test cases
- [ ] Generate T07-T13 (extended) test cases
- [ ] Verify all met/run files created correctly

### Phase 3: Execution (Notebook 03)
- [ ] Execute all test cases in HEC-HMS
- [ ] Verify DSS output files created
- [ ] Document any execution failures

### Phase 4: Ground Truth Extraction (Notebook 04)
- [ ] Extract PRECIP-INC for all test cases
- [ ] Save to CSV format
- [ ] Create validation_summary.csv

### Phase 5: Validation (Notebooks 05-06)
- [ ] Validate HMS-Commander against ground truth
- [ ] Validate RAS-Commander against ground truth
- [ ] Document any discrepancies
- [ ] Identify implementation gaps

### Phase 6: Cross-Repo Handoff
- [ ] Copy ground truth CSVs to ras-commander
- [ ] Update ras-commander notebook 723
- [ ] Document API requirements for HMS-Commander submodule

---

## APPENDIX A: Complete Atlas 14 Test Matrix

### Location: Houston, Texas (Clear Creek M3 Model)
- **Latitude**: 29.6320
- **Longitude**: -95.1352
- **Atlas 14 Volume**: 11 (Texas)
- **Region**: 3

### Complete DDF Table (from PF_Depth_English_PDS.csv)

**Precipitation Depths (inches) by Duration and ARI**:

| Duration | 1-yr | 2-yr | 5-yr | 10-yr | 25-yr | 50-yr | 100-yr | 200-yr | 500-yr | 1000-yr |
|----------|------|------|------|-------|-------|-------|--------|--------|--------|---------|
| 5-min | 0.502 | 0.600 | 0.756 | 0.888 | 1.07 | 1.22 | 1.37 | 1.53 | 1.76 | 1.94 |
| 10-min | 0.794 | 0.950 | 1.20 | 1.41 | 1.71 | 1.94 | 2.19 | 2.43 | 2.76 | 3.02 |
| 15-min | 1.02 | 1.21 | 1.52 | 1.78 | 2.14 | 2.43 | 2.72 | 3.04 | 3.48 | 3.84 |
| 30-min | 1.47 | 1.73 | 2.16 | 2.53 | 3.03 | 3.42 | 3.83 | 4.29 | 4.96 | 5.51 |
| 60-min | 1.93 | 2.31 | 2.90 | 3.41 | 4.12 | 4.67 | 5.26 | 5.96 | 6.99 | 7.85 |
| 2-hr | 2.32 | 2.88 | 3.74 | 4.51 | 5.64 | 6.57 | 7.60 | 8.81 | 10.6 | 12.1 |
| 3-hr | 2.52 | 3.23 | 4.27 | 5.24 | 6.70 | 7.94 | 9.34 | 11.0 | 13.4 | 15.5 |
| 6-hr | 2.89 | 3.86 | 5.23 | 6.55 | 8.56 | 10.3 | 12.3 | 14.7 | 18.2 | 21.2 |
| 12-hr | 3.36 | 4.56 | 6.26 | 7.90 | 10.4 | 12.5 | 15.0 | 18.0 | 22.6 | 26.5 |
| **24-hr** | 3.88 | 5.33 | 7.38 | 9.35 | 12.3 | 14.9 | **17.9** | 21.4 | **26.8** | 31.5 |
| 2-day | 4.44 | 6.17 | 8.61 | 11.0 | 14.6 | 17.8 | 21.3 | 25.2 | 30.9 | 35.5 |
| 3-day | 4.84 | 6.72 | 9.36 | 11.9 | 15.9 | 19.4 | 23.3 | 27.3 | 33.0 | 37.5 |
| 4-day | 5.16 | 7.12 | 9.85 | 12.5 | 16.6 | 20.4 | 24.4 | 28.6 | 34.3 | 38.8 |
| 7-day | 5.89 | 7.97 | 10.8 | 13.7 | 18.1 | 22.1 | 26.5 | 30.8 | 36.6 | 41.0 |

### AEP to ARI Mapping

| AEP (%) | ARI (years) | Run Naming |
|---------|-------------|------------|
| 50% | 2-year | `50pct_2yr` |
| 20% | 5-year | `20pct_5yr` |
| 10% | 10-year | `10pct_10yr` |
| 4% | 25-year | `4pct_25yr` |
| 2% | 50-year | `2pct_50yr` |
| 1% | 100-year | `1pct_100yr` |
| 0.5% | 200-year | `0.5pct_200yr` |
| 0.2% | 500-year | `0.2pct_500yr` |

---

## APPENDIX B: DSS Temporal Distribution Import

### Temporal Distribution CSV Structure

**Source URL Pattern**: `https://hdsc.nws.noaa.gov/pub/hdsc/data/{state}/{state}_{region}_{duration}h_temporal.csv`

**Available Durations**: 6-hour, 12-hour, 24-hour, 96-hour

**Example (TX Region 3, 24-hour)**: `https://hdsc.nws.noaa.gov/pub/hdsc/data/tx/tx_3_24h_temporal.csv`

### CSV Table Structure (5 Tables per File)

```
Table 1: FIRST-QUARTILE CASES  (Peak in hours 0-6)
Table 2: SECOND-QUARTILE CASES (Peak in hours 6-12)
Table 3: THIRD-QUARTILE CASES  (Peak in hours 12-18)
Table 4: FOURTH-QUARTILE CASES (Peak in hours 18-24)
Table 5: ALL CASES             (Combined distribution)
```

**Each Table Format**:
- Column 1: Time (hours) - 0 to 24 in 0.5-hour increments (49 rows)
- Columns 2-10: Cumulative percentages at probability levels:
  - 90%, 80%, 70%, 60%, 50%, 40%, 30%, 20%, 10%

### DSS Pathname Format for Imported Temporal Patterns

**Pattern**: `//{REGION}/{QUARTILE}/{DURATION}///{PROBABILITY}/`

**Examples**:
```
//TX_R3/ALL_CASES/24HR///50PERCENT/
//TX_R3/FIRST_QUARTILE/24HR///50PERCENT/
//TX_R3/SECOND_QUARTILE/24HR///50PERCENT/
//TX_R3/THIRD_QUARTILE/24HR///50PERCENT/
//TX_R3/FOURTH_QUARTILE/24HR///50PERCENT/
```

### Python Implementation: Temporal Distribution Importer

```python
import pandas as pd
import requests
from io import StringIO

def download_temporal_distribution(state: str, region: int, duration_hours: int) -> dict:
    """
    Download Atlas 14 temporal distribution CSV and parse all 5 tables.

    Args:
        state: Two-letter state code (e.g., 'tx')
        region: Atlas 14 region number (e.g., 3)
        duration_hours: Duration in hours (6, 12, 24, or 96)

    Returns:
        dict: {quartile_name: pd.DataFrame} with cumulative percentages
    """
    url = f"https://hdsc.nws.noaa.gov/pub/hdsc/data/{state}/{state}_{region}_{duration_hours}h_temporal.csv"
    response = requests.get(url)
    response.raise_for_status()

    content = response.text
    tables = {}

    # Parse 5 tables from CSV content
    quartile_names = [
        'FIRST-QUARTILE',
        'SECOND-QUARTILE',
        'THIRD-QUARTILE',
        'FOURTH-QUARTILE',
        'ALL CASES'
    ]

    for quartile in quartile_names:
        # Find table start
        marker = f"CUMULATIVE PERCENTAGES OF TOTAL PRECIPITATION FOR {quartile}"
        if marker not in content:
            marker = f"CUMULATIVE PERCENTAGES OF TOTAL PRECIPITATION FOR {quartile} CASES"

        start_idx = content.find(marker)
        if start_idx == -1:
            continue

        # Find next table or end
        remaining = content[start_idx:]
        lines = remaining.split('\n')

        # Skip header lines, find data
        data_lines = []
        header_found = False
        for line in lines:
            if 'hours,90%' in line:
                header_found = True
                data_lines.append(line)
            elif header_found:
                if line.strip() and not line.startswith('CUMULATIVE'):
                    data_lines.append(line)
                elif not line.strip() and len(data_lines) > 1:
                    break

        # Parse to DataFrame
        csv_text = '\n'.join(data_lines)
        df = pd.read_csv(StringIO(csv_text))
        df.columns = ['hours', '90%', '80%', '70%', '60%', '50%', '40%', '30%', '20%', '10%']
        tables[quartile.replace(' ', '_').replace('-', '_')] = df

    return tables


def import_temporal_to_dss(dss_file: str, temporal_data: dict, region_name: str, duration_hours: int):
    """
    Import temporal distributions to DSS file.

    Args:
        dss_file: Path to output DSS file
        temporal_data: Dict from download_temporal_distribution()
        region_name: Name for DSS pathname (e.g., 'TX_R3')
        duration_hours: Duration in hours
    """
    from hms_commander.dss import DssCore

    for quartile_name, df in temporal_data.items():
        for prob_col in ['90%', '80%', '70%', '60%', '50%', '40%', '30%', '20%', '10%']:
            # Create paired data record
            times = df['hours'].values
            values = df[prob_col].values / 100.0  # Convert to fractions

            # Build DSS pathname
            prob_pct = prob_col.replace('%', 'PERCENT')
            pathname = f"//{region_name}/{quartile_name}/{duration_hours}HR///{prob_pct}/"

            # Write to DSS as paired data (curve)
            DssCore.write_paired_data(
                dss_file=dss_file,
                pathname=pathname,
                x_values=times,
                y_values=values,
                x_units='HR',
                y_units='FRACTION'
            )

    print(f"Imported {len(temporal_data) * 9} temporal patterns to {dss_file}")
```

---

## APPENDIX C: Run Configuration with Unique DSS Outputs

### Run Naming Convention

**Format**: `{AEP}_{DURATION}_{STORM_TYPE}.run`

**Examples**:
- `0.2pct_24hr_SCS2.run` - 500-year, 24-hour, SCS Type II
- `1pct_24hr_SCS2.run` - 100-year, 24-hour, SCS Type II
- `10pct_24hr_SCS2.run` - 10-year, 24-hour, SCS Type II

### Unique Output DSS File Configuration

**Key Configuration Lines in .run File**:
```
Run: 0.2%(500YR) RUN
     Log File: 0.2pct_24hr_SCS2.log
     DSS File: 0.2pct_24hr_SCS2_OUTPUT.dss    <- UNIQUE OUTPUT DSS
     Basin: A100_0.2PCT
     Precip: 0.2%_24HR
     Control: Control 5
     Time-Series Output: Save All
End:
```

### Python Implementation: Run File Generator

```python
def create_run_file(
    output_path: str,
    run_name: str,
    aep_percent: float,
    duration_hours: int,
    storm_type: str,
    basin_name: str,
    met_name: str,
    control_name: str = "Control 5"
) -> str:
    """
    Create HEC-HMS run file with unique output DSS.

    Args:
        output_path: Directory for run file
        run_name: Human-readable run name
        aep_percent: Annual exceedance probability (e.g., 1.0 for 1%)
        duration_hours: Storm duration
        storm_type: SCS type (e.g., 'SCS2')
        basin_name: Basin model name
        met_name: Meteorologic model name
        control_name: Control specifications name

    Returns:
        str: Path to created run file
    """
    from datetime import datetime

    # Generate unique identifiers
    aep_str = f"{aep_percent}pct".replace('.', '_')
    dur_str = f"{duration_hours}hr"
    unique_id = f"{aep_str}_{dur_str}_{storm_type}"

    # Create run content
    now = datetime.now()
    run_content = f"""Run: {run_name}
     Default Description: Yes
     Log File: {unique_id}.log
     DSS File: {unique_id}_OUTPUT.dss
     Is Save Spatial Results: No
     Last Modified Date: {now.strftime('%d %B %Y')}
     Last Modified Time: {now.strftime('%H:%M:%S')}
     Basin: {basin_name}
     Precip: {met_name}
     Control: {control_name}
     Time-Series Output: Save All
     Time Series Results Manager Start:
     Time Series Results Manager End:
End:

"""

    # Write to file
    run_file = Path(output_path) / f"{unique_id}.run"
    run_file.write_text(run_content)

    return str(run_file)


def create_met_file(
    output_path: str,
    met_name: str,
    storm_depth_inches: float,
    storm_type: str = "SCS Type II",
    version: str = "4.13"
) -> str:
    """
    Create HEC-HMS met file for Hypothetical Storm method.

    Args:
        output_path: Directory for met file
        met_name: Meteorologic model name
        storm_depth_inches: Total storm depth from Atlas 14 DDF
        storm_type: "SCS Type II", "SCS Type I", "SCS Type IA", "SCS Type III", or "Specified Pattern"
        version: HEC-HMS version

    Returns:
        str: Path to created met file
    """
    from datetime import datetime

    now = datetime.now()

    met_content = f"""Meteorology: {met_name}
     Last Modified Date: {now.strftime('%d %B %Y')}
     Last Modified Time: {now.strftime('%H:%M:%S')}
     Version: {version}
     Unit System: English
     Set Missing Data to Default: No
     Precipitation Method: Hypothetical Storm
     Air Temperature Method: None
     Atmospheric Pressure Method: None
     Dew Point Method: None
     Wind Speed Method: None
     Shortwave Radiation Method: None
     Longwave Radiation Method: None
     Snowmelt Method: None
     Evapotranspiration Method: No Evapotranspiration
End:

Precip Method Parameters: Hypothetical Storm
     Last Modified Date: {now.strftime('%d %B %Y')}
     Last Modified Time: {now.strftime('%H:%M:%S')}
     Precipitation Method: Point Depth
     Storm Depth: {storm_depth_inches:.3f}
     Storm Type: {storm_type}
     Depth-Area Reduction Method: No Reduction
     Uniform Depth: Yes
End:

"""

    # Sanitize met_name for filename
    safe_name = met_name.replace('%', '_').replace(' ', '_')
    met_file = Path(output_path) / f"{safe_name}.met"
    met_file.write_text(met_content)

    return str(met_file)
```

---

## APPENDIX D: Complete Test Suite Generation

### Python Implementation: Full Test Matrix Generator

```python
from pathlib import Path
import pandas as pd

# Atlas 14 DDF table for Houston, TX (29.6320, -95.1352)
DDF_TABLE = {
    # Duration (hours): {ARI (years): depth (inches)}
    24: {
        2: 5.33, 5: 7.38, 10: 9.35, 25: 12.3, 50: 14.9,
        100: 17.9, 200: 21.4, 500: 26.8, 1000: 31.5
    },
    12: {
        2: 4.56, 5: 6.26, 10: 7.90, 25: 10.4, 50: 12.5,
        100: 15.0, 200: 18.0, 500: 22.6, 1000: 26.5
    },
    6: {
        2: 3.86, 5: 5.23, 10: 6.55, 25: 8.56, 50: 10.3,
        100: 12.3, 200: 14.7, 500: 18.2, 1000: 21.2
    }
}

ARI_TO_AEP = {
    2: 50.0, 5: 20.0, 10: 10.0, 25: 4.0, 50: 2.0,
    100: 1.0, 200: 0.5, 500: 0.2, 1000: 0.1
}

def generate_test_matrix(
    project_path: str,
    durations: list = [24],
    aris: list = [10, 50, 100, 500],
    storm_types: list = ['SCS Type II'],
    control_name: str = "Control 5",
    basin_base_name: str = "A100"
) -> pd.DataFrame:
    """
    Generate complete test matrix with met files, run files, and unique DSS outputs.

    Args:
        project_path: Path to HEC-HMS project
        durations: List of storm durations (hours)
        aris: List of average recurrence intervals (years)
        storm_types: List of storm types to test
        control_name: Control specifications name
        basin_base_name: Base name for basin models

    Returns:
        pd.DataFrame: Test matrix with file paths
    """
    project_path = Path(project_path)
    tests = []

    for duration in durations:
        for ari in aris:
            aep = ARI_TO_AEP[ari]
            storm_depth = DDF_TABLE[duration][ari]

            for storm_type in storm_types:
                # Create unique identifiers
                aep_str = f"{aep}pct".replace('.', '_')
                ari_str = f"{ari}yr"
                dur_str = f"{duration}hr"
                type_str = storm_type.replace(' ', '').replace('Type', '')

                test_id = f"{aep_str}_{dur_str}_{type_str}"
                met_name = f"{aep}%_{duration}HR"
                run_name = f"{aep}%({ari}YR) RUN"
                basin_name = f"{basin_base_name}_{aep_str.upper()}"

                # Create met file
                met_file = create_met_file(
                    output_path=str(project_path),
                    met_name=met_name,
                    storm_depth_inches=storm_depth,
                    storm_type=storm_type
                )

                # Create run file
                run_file = create_run_file(
                    output_path=str(project_path),
                    run_name=run_name,
                    aep_percent=aep,
                    duration_hours=duration,
                    storm_type=type_str,
                    basin_name=basin_name,
                    met_name=met_name,
                    control_name=control_name
                )

                tests.append({
                    'test_id': test_id,
                    'aep_percent': aep,
                    'ari_years': ari,
                    'duration_hours': duration,
                    'storm_type': storm_type,
                    'storm_depth_inches': storm_depth,
                    'met_file': met_file,
                    'run_file': run_file,
                    'output_dss': f"{test_id}_OUTPUT.dss",
                    'basin_name': basin_name
                })

    return pd.DataFrame(tests)


# Example usage
if __name__ == "__main__":
    test_matrix = generate_test_matrix(
        project_path="examples/atlas14_validation",
        durations=[24],
        aris=[10, 50, 100, 500],
        storm_types=['SCS Type II']
    )

    print(f"Generated {len(test_matrix)} test cases")
    print(test_matrix[['test_id', 'storm_depth_inches', 'output_dss']])
```

### Expected Output DSS File Names

| AEP | ARI | Duration | Storm Type | Output DSS |
|-----|-----|----------|------------|------------|
| 10% | 10-yr | 24hr | SCS2 | `10pct_24hr_SCS2_OUTPUT.dss` |
| 2% | 50-yr | 24hr | SCS2 | `2pct_24hr_SCS2_OUTPUT.dss` |
| 1% | 100-yr | 24hr | SCS2 | `1pct_24hr_SCS2_OUTPUT.dss` |
| 0.2% | 500-yr | 24hr | SCS2 | `0_2pct_24hr_SCS2_OUTPUT.dss` |

---

## APPENDIX E: Ground Truth Extraction

### Extracting PRECIP-INC from Output DSS

```python
from hms_commander.dss import DssCore
import pandas as pd
from pathlib import Path

def extract_ground_truth(test_matrix: pd.DataFrame, project_path: str) -> dict:
    """
    Extract PRECIP-INC time series from all test case output DSS files.

    Args:
        test_matrix: DataFrame from generate_test_matrix()
        project_path: Path to HEC-HMS project

    Returns:
        dict: {test_id: pd.DataFrame with precipitation time series}
    """
    project_path = Path(project_path)
    ground_truth = {}

    for _, row in test_matrix.iterrows():
        test_id = row['test_id']
        dss_file = project_path / row['output_dss']

        if not dss_file.exists():
            print(f"WARNING: {dss_file} not found - run not executed?")
            continue

        # Get DSS catalog
        catalog = DssCore.get_catalog(str(dss_file))

        # Find PRECIP-INC pathnames
        precip_paths = [p for p in catalog if 'PRECIP-INC' in p]

        if not precip_paths:
            print(f"WARNING: No PRECIP-INC found in {dss_file}")
            continue

        # Extract first basin's precipitation (or iterate all)
        for pathname in precip_paths:
            ts = DssCore.read_timeseries(str(dss_file), pathname)

            # Extract location from pathname
            parts = pathname.split('/')
            location = parts[2] if len(parts) > 2 else 'UNKNOWN'

            # Store with test_id and location
            key = f"{test_id}_{location}"
            ground_truth[key] = ts

            # Save to CSV
            csv_file = project_path / 'ground_truth' / f"{key}.csv"
            csv_file.parent.mkdir(exist_ok=True)
            ts.to_csv(csv_file, index=True)

    print(f"Extracted {len(ground_truth)} ground truth time series")
    return ground_truth


def create_validation_summary(ground_truth: dict, output_file: str):
    """
    Create summary CSV of all ground truth extractions.
    """
    summary = []

    for key, ts in ground_truth.items():
        parts = key.rsplit('_', 1)
        test_id = parts[0] if len(parts) > 1 else key
        location = parts[1] if len(parts) > 1 else 'UNKNOWN'

        summary.append({
            'test_id': test_id,
            'location': location,
            'n_values': len(ts),
            'total_precip_inches': ts['value'].sum(),
            'max_incremental': ts['value'].max(),
            'time_of_peak': ts.loc[ts['value'].idxmax(), 'datetime'] if 'datetime' in ts.columns else None
        })

    df = pd.DataFrame(summary)
    df.to_csv(output_file, index=False)
    print(f"Validation summary saved to {output_file}")
    return df
```

---

## Summary: Complete Validation Workflow

### Step-by-Step Execution

1. **Download Atlas 14 Data**
   - DDF values: NOAA PFDS for project location
   - Temporal distributions: `tx_3_24h_temporal.csv`

2. **Import Temporal to DSS**
   - Use `download_temporal_distribution()` + `import_temporal_to_dss()`
   - Creates `TX_R3_24H.dss` with all 5 quartiles × 9 probabilities

3. **Generate Test Matrix**
   - Use `generate_test_matrix()` with desired AEPs and durations
   - Creates met files and run files with unique output DSS names

4. **Execute All Runs**
   ```python
   from hms_commander import HmsCmdr
   for _, row in test_matrix.iterrows():
       HmsCmdr.compute_run(row['test_id'], hms_object=hms)
   ```

5. **Extract Ground Truth**
   - Use `extract_ground_truth()` to get PRECIP-INC from all output DSS
   - Creates `ground_truth/` folder with CSVs

6. **Validate Python Libraries**
   - Compare HMS-Commander output vs ground truth
   - Compare RAS-Commander output vs ground truth
   - Document differences (should be < 0.0001 inches)
