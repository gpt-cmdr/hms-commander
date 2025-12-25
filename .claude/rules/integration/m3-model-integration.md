# M3 Model HMS↔RAS Integration

**Purpose**: Document integrated workflows using HCFCD M3 Models for both HMS (hydrology) and RAS (hydraulics).

**Primary sources**:
- `hms_commander/HmsM3Model.py` - HMS project access
- `ras_commander/M3Model.py` - RAS project access
- `hms_commander/data/m3_hms_catalog.csv` - HMS project catalog

**M3 Model Upgrade & Testing**:
- `feature_dev_notes/HCFCD_M3_HMS411_UPGRADE_WORKFLOW.md` - Step-by-step upgrade guide
- `feature_dev_notes/HCFCD_M3_Clear_Creek_*` - Clear Creek pilot results (reference)
- `examples/m3_upgrade_helpers/` - Validation scripts

---

## Overview

HCFCD M3 Models are complete H&H (Hydrology & Hydraulics) model packages containing:
- **HEC-HMS projects**: Hydrologic models for runoff generation
- **HEC-RAS projects**: Hydraulic models for river routing

This enables integrated watershed-to-river modeling using a consistent, FEMA-effective dataset.

---

## M3 Model Structure

Each M3 model zip file contains:

```
{Model}_{ShortName}_FEMA_Effective.zip
├── HEC-HMS/                    # Hydrologic models
│   ├── {Unit_ID}/              # e.g., D_D100-00-00
│   │   ├── {Unit_ID}/
│   │   │   ├── *.hms           # HMS project file
│   │   │   ├── *.basin         # Basin models (by storm frequency)
│   │   │   ├── *.met           # Met models (by storm frequency)
│   │   │   ├── *.control       # Control specifications
│   │   │   ├── *.dss           # DSS output file
│   │   │   └── Support_Data/   # Supporting data
│   │   └── ...
│   └── ...
└── HEC-RAS/                    # Hydraulic models
    ├── {Reach_ID}/             # e.g., D100-00-00, D109-00-00
    │   ├── *.prj               # RAS project file
    │   ├── *.g##               # Geometry files
    │   ├── *.p##               # Plan files
    │   ├── *.f##               # Steady flow files
    │   ├── *.u##               # Unsteady flow files
    │   └── ...
    └── ...
```

**Key Insight**: Each M3 model typically has:
- 1-16 HMS projects (one per unit/watershed)
- 1-32 RAS reaches (individual river segments)

---

## Two-Library Integration

### Library Responsibilities

| Library | Class | Purpose | Projects |
|---------|-------|---------|----------|
| **hms-commander** | `HmsM3Model` | HMS project access | 42 HMS projects |
| **ras-commander** | `M3Model` | RAS project access | 235 RAS reaches |

### Installation

```bash
# For HMS-only workflows
pip install hms-commander

# For RAS-only workflows
pip install ras-commander

# For integrated HMS→RAS workflows
pip install hms-commander ras-commander
```

---

## Workflow Patterns

### Pattern 1: HMS-Only (Hydrology)

Extract and run HMS model independently:

```python
from hms_commander import HmsM3Model, init_hms_project, HmsCmdr, HmsJython

# List available HMS projects
projects = HmsM3Model.list_projects()
print(projects[['model_id', 'model_name', 'unit_id']])

# Extract Brays Bayou HMS model
path = HmsM3Model.extract_project('D', 'D100-00-00')

# Initialize project
init_hms_project(path)

# Generate Jython script (HMS 3.x requires python2_compatible=True)
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name="1PCT",
    python2_compatible=True  # M3 uses HMS 3.3
)

# Execute
HmsCmdr.compute_run("1PCT")
```

### Pattern 2: RAS-Only (Hydraulics)

Extract and use RAS model independently:

```python
from ras_commander import M3Model, init_ras_project, RasCmdr

# List RAS reaches
reaches = M3Model.list_models()

# Extract Brays Bayou RAS reaches
model_path = M3Model.extract_model('D')

# Initialize specific reach
reach_path = model_path / "HEC-RAS" / "D100-00-00"
init_ras_project(reach_path)

# Run hydraulic simulation
RasCmdr.compute_plan("Plan 01")
```

### Pattern 3: Integrated HMS→RAS Workflow

Use HMS results as RAS boundary conditions:

```python
from hms_commander import HmsM3Model, init_hms_project, HmsCmdr, HmsResults
from ras_commander import M3Model, init_ras_project, RasUnsteady

# === Step 1: Run HMS to generate hydrographs ===
model_id = 'D'  # Brays Bayou

# Extract and run HMS
hms_path = HmsM3Model.extract_project(model_id, 'D100-00-00')
init_hms_project(hms_path)
HmsCmdr.compute_run("1PCT", python2_compatible=True)

# Get DSS output
dss_file = hms_path / "D100_00_00.dss"
peaks = HmsResults.get_peak_flows(dss_file)
print(f"HMS Peak Flow: {peaks.iloc[0]['Peak Flow (cfs)']}")

# === Step 2: Import to RAS ===
# Extract RAS reach
ras_model_path = M3Model.extract_model(model_id)
ras_reach_path = ras_model_path / "HEC-RAS" / "D100-00-00"
init_ras_project(ras_reach_path)

# Import HMS hydrograph as upstream boundary condition
# (See ras-commander documentation for RasUnsteady.import_hms_bc())
```

### Pattern 4: Cross-Reference Same Watershed

Work with HMS and RAS for the same HCFCD unit:

```python
from hms_commander import HmsM3Model
from ras_commander import M3Model

# Find HMS and RAS projects for Brays Bayou
model_id = 'D'

# HMS side
hms_info = HmsM3Model.get_model_info(model_id)
print(f"HMS Projects: {hms_info['hms_projects']}")  # ['D100-00-00']

# RAS side (more reaches for detailed hydraulics)
ras_info = M3Model.get_model_info(model_id)
# RAS has: D100-00-00, D109-00-00, D111-00-00, ... (16 reaches)

# Typically:
# - HMS D100-00-00 covers entire watershed hydrology
# - RAS D100-00-00, D109-00-00, etc. are individual channel segments
```

---

## Model-by-Model Reference

| Model | Watershed | HMS Projects | RAS Reaches | Integration Notes |
|-------|-----------|--------------|-------------|-------------------|
| A | Clear Creek | 1 | 14 | HMS outlet → RAS upstream |
| B | Armand Bayou | 1 | 17 | Single watershed |
| C | Sims Bayou | 1 | 13 | HMS outlet → RAS upstream |
| D | Brays Bayou | 1 | 16 | Well-documented watershed |
| E | White Oak Bayou | 1 | 14 | Urban watershed |
| F | San Jacinto/Galveston Bay | 2 | 2 | Coastal area |
| G | San Jacinto River | 16 | 24 | Most HMS projects |
| H | Hunting Bayou | 1 | 5 | Small urban |
| I | Vince Bayou | 1 | 2 | Small watershed |
| J | Spring Creek | 1 | 6 | Suburban area |
| K | Cypress Creek | 2 | 32 | Most RAS reaches |
| L | Little Cypress Creek | 2 | 5 | Shares HMS with K |
| M | Willow Creek | 1 | 10 | TSARP study area |
| N | Carpenters Bayou | 1 | 3 | Small watershed |
| O | Spring Gully/Goose Creek | 2 | 4 | Multiple creeks |
| P | Greens Bayou | 1 | 27 | Large watershed |
| Q | Cedar Bayou | 1 | 9 | Eastern Harris County |
| R | Jackson Bayou | 1 | 4 | Small watershed |
| S | Luce Bayou | 2 | 3 | Northern area |
| T | Barker | 1 | 5 | Reservoir area |
| U | Addicks | 1 | 10 | Reservoir restudy |
| W | Buffalo Bayou | 1 | 10 | Downtown Houston |

---

## HMS Project Details

### All Projects Use HMS 3.x Format

**Critical**: M3 HMS projects use HMS 3.3 or 3.4, which requires:

```python
# Always use python2_compatible=True for M3 HMS projects
script = HmsJython.generate_compute_script(
    project_path=path,
    run_name="1PCT",
    python2_compatible=True  # Required for HMS 3.x
)
```

### Design Storm Frequencies

Standard M3 design storms (most projects):
- **0.2%** (500-year) - Extreme event
- **1%** (100-year) - Base flood
- **2%** (50-year) - Major event
- **10%** (10-year) - Moderate event

Model U (Addicks) has extended frequencies:
- 0.2%, 0.4%, 1%, 2%, 4%, 10%, 20%, 50%

### Hydrologic Methods

Typical M3 HMS configuration:

| Method | Most Common | Alternative |
|--------|-------------|-------------|
| Loss | Initial+Constant | Green and Ampt |
| Transform | Clark | Modified Clark |
| Baseflow | Recession | None |
| Routing | Modified Puls | Muskingum, Lag |

### Rainfall Regions

M3 uses HCFCD rainfall regions (NOT Atlas 14):
- **Region 1**: Western Harris County (Addicks, Barker)
- **Region 2**: Northern Harris County (Greens Bayou)
- **Region 3**: Central/Eastern Harris County (most models)

---

## DSS Data Flow

### HMS to RAS via DSS

```
HMS Execution → DSS Output → RAS Import
                   ↓
         /BASIN/OUTLET/FLOW/1HOUR/1PCT/
                   ↓
         RAS Boundary Condition
```

### DSS Pathname Format

HMS M3 projects use standard DSS pathname format:
```
/A/B/C/D/E/F/
/BASIN_NAME/ELEMENT_NAME/PARAMETER/INTERVAL/RUN_NAME/
```

Example:
```
/D100_00_00/OUTLET/FLOW/15MIN/1PCT/
```

### Extracting HMS Results

```python
from hms_commander import HmsResults

dss_file = "D100_00_00.dss"

# Get peak flows
peaks = HmsResults.get_peak_flows(dss_file)

# Get hydrograph for RAS import
flows = HmsResults.get_outflow_timeseries(dss_file, "OUTLET")
```

---

## Channel Name Lookup

Find M3 models by channel name (uses HCFCD ArcGIS API):

```python
from hms_commander import HmsM3Model

# Find by channel name
result = HmsM3Model.get_project_by_channel('BRAYS BAYOU')
if result:
    model_id, unit_id = result
    print(f"Model: {model_id}, Unit: {unit_id}")
    # Model: D, Unit: D100-00-00
```

Available channel lookups:
- CLEAR CREEK → Model A
- BRAYS BAYOU → Model D
- WHITE OAK BAYOU → Model E
- BUFFALO BAYOU → Model W
- (See HmsM3Model.MODELS for complete list)

---

## Common Integration Scenarios

### Scenario 1: FEMA Map Revision

1. Extract HMS project for design storm analysis
2. Run HMS to get peak flows and hydrographs
3. Extract corresponding RAS reaches
4. Import HMS results as RAS boundary conditions
5. Run RAS for water surface profiles
6. Generate FEMA mapping outputs

### Scenario 2: Development Impact Analysis

1. Extract baseline HMS project (M3 = existing conditions)
2. Clone and modify for proposed conditions
3. Compare peak flows
4. Run RAS with both conditions
5. Compare flood extents

### Scenario 3: Real-Time Flood Forecasting

1. Use M3 HMS models as calibrated baseline
2. Update with real-time rainfall data
3. Run HMS for forecast hydrographs
4. Feed to RAS for water level predictions

---

## File Locations After Extraction

### Default Locations

```
./m3_hms_projects/          # HmsM3Model default
└── {model_id}/
    └── {unit_id}/
        ├── *.hms
        ├── *.basin
        └── ...

./m3_models/                # M3Model (ras-commander) default
└── {Model Name}/
    ├── HEC-HMS/
    └── HEC-RAS/
```

### Custom Locations

```python
# Specify custom output paths
hms_path = HmsM3Model.extract_project('D', 'D100-00-00',
                                       output_path='my_hms_models/')

ras_path = M3Model.extract_model('D',
                                  output_path='my_ras_models/')
```

---

## Best Practices

### 1. Version Compatibility

Always remember M3 HMS projects are HMS 3.x:
```python
# WRONG - will fail with syntax errors
script = HmsJython.generate_compute_script(path, run_name="1PCT")

# CORRECT
script = HmsJython.generate_compute_script(
    path, run_name="1PCT",
    python2_compatible=True
)
```

### 2. Unit System Awareness

Most M3 projects use Metric units:
- Flow: cms (cubic meters per second)
- Area: km² (square kilometers)
- Depth: mm (millimeters)

Some older projects use English:
- Flow: cfs (cubic feet per second)
- Area: mi² or acres
- Depth: inches

Check `unit_system` in catalog before unit conversions.

### 3. Consistent Model Selection

When doing HMS→RAS integration, ensure you're using the same watershed:
```python
# Good: Same model_id for both
model_id = 'D'
hms_path = HmsM3Model.extract_project(model_id, 'D100-00-00')
ras_path = M3Model.extract_model(model_id)  # Gets all D reaches

# Bad: Mixing different watersheds
hms_path = HmsM3Model.extract_project('D', 'D100-00-00')  # Brays
ras_path = M3Model.extract_model('E')  # White Oak - wrong!
```

### 4. Validate Peak Flows

After HMS→RAS import, validate:
```python
# Compare HMS peak with RAS upstream BC peak
hms_peak = HmsResults.get_peak_flows(hms_dss)['Peak Flow (cfs)'].iloc[0]
ras_bc_peak = RasUnsteady.get_bc_peak(ras_project, "Upstream")

tolerance = 0.01  # 1% difference acceptable
assert abs(hms_peak - ras_bc_peak) / hms_peak < tolerance
```

---

## Troubleshooting

### Issue: HMS script fails with syntax error

**Cause**: Using Python 3 syntax with HMS 3.x project

**Solution**: Add `python2_compatible=True`:
```python
script = HmsJython.generate_compute_script(
    path, run_name="1PCT",
    python2_compatible=True
)
```

### Issue: Extracted folder is empty

**Cause**: Relative path mismatch in zip extraction

**Solution**: Check `relative_path` in catalog matches actual zip structure

### Issue: DSS file not found

**Cause**: HMS project not run, or DSS file in different location

**Solution**:
1. Run HMS first: `HmsCmdr.compute_run("1PCT")`
2. Check catalog for correct DSS filename

### Issue: Peak flows don't match between HMS and RAS

**Cause**: Different storm events or unit mismatch

**Solution**:
1. Verify same storm frequency (1PCT, 2PCT, etc.)
2. Check unit system (Metric vs English)
3. Verify correct DSS pathname

---

## Related Documentation

**HMS-Commander**:
- `.claude/rules/hec-hms/execution.md` - HMS execution
- `.claude/rules/hec-hms/version-support.md` - HMS 3.x vs 4.x
- `.claude/rules/integration/hms-ras-linking.md` - General HMS→RAS workflow

**RAS-Commander**:
- `ras_commander/M3Model.py` - RAS M3 access
- `.claude/rules/integration/hms-ras-linking.md` - RAS side workflow

**HCFCD Resources**:
- Website: https://www.m3models.org/
- Model Library: https://www.m3models.org/Downloads/ModelLibrary
- ArcGIS Channels: https://www.gis.hctx.net/arcgishcpid/rest/services/HCFCD/Channels/MapServer

---

## Quick Reference

```python
from hms_commander import HmsM3Model

# List all HMS projects
HmsM3Model.list_projects()

# List projects for specific model
HmsM3Model.list_projects(model_id='D')

# Get model info
HmsM3Model.get_model_info('D')

# Get project info
HmsM3Model.get_project_info('D', 'D100-00-00')

# Find by channel
HmsM3Model.get_project_by_channel('BRAYS BAYOU')

# Extract single project
HmsM3Model.extract_project('D', 'D100-00-00')

# Extract all HMS projects from a model
HmsM3Model.extract_model('G')

# Check if extracted
HmsM3Model.is_project_extracted('D', 'D100-00-00')

# Clean up
HmsM3Model.clean_projects_directory()

# Statistics
HmsM3Model.get_statistics()
```
