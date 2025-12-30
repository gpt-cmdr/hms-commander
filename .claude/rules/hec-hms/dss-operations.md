---
paths: hms_commander/**/*.py
---

# DSS File Operations

## Primary Sources

**Code** (consolidated under `hms_commander/dss/`):
- `hms_commander/dss/core.py` - DssCore: Low-level DSS operations via HEC Monolith
- `hms_commander/dss/hms_dss.py` - HmsDss: HMS-specific DSS convenience methods
- `hms_commander/dss/hms_dss_grid.py` - HmsDssGrid: DSS grid operations for gridded precipitation
- `hms_commander/dss/_hec_monolith.py` - HEC Monolith library downloader
- `hms_commander/HmsResults.py` - Results extraction and analysis

**Dependencies**:
- pyjnius: Python-Java bridge (pip install pyjnius)
- Java 8+ JRE/JDK
- HEC Monolith libraries: Auto-downloaded on first use (~20 MB)

## Architecture (Standalone DSS Implementation)

**Decision**: hms-commander has its own standalone DSS implementation using HEC Monolith libraries.

**Benefits**:
- No external dependency on ras-commander for DSS operations
- Full control over DSS functionality
- DSS V6/V7 support via HEC Monolith
- Auto-download of HEC libraries

**Implementation**:
```
hms_commander/dss/
├── __init__.py         # Exports DssCore, HmsDss, HmsDssGrid
├── core.py             # DssCore - Low-level DSS operations
├── hms_dss.py          # HmsDss - HMS-specific wrapper
├── hms_dss_grid.py     # HmsDssGrid - Grid operations
└── _hec_monolith.py    # Library downloader
```

**Lazy loading**: DSS dependencies (pyjnius, Java) are only loaded when actually needed.

## Common Patterns

### Pattern 1: Check DSS Availability

```python
from hms_commander import HmsDss

if HmsDss.is_available():
    catalog = HmsDss.get_catalog("results.dss")
```

**Note**: Requires pyjnius and Java 8+ installation

### Pattern 2: Extract HMS Results

```python
from hms_commander import HmsResults

# Peak flows
peaks = HmsResults.get_peak_flows("results.dss")

# Hydrographs
flows = HmsResults.get_outflow_timeseries("results.dss", "Outlet")

# Precipitation
precip = HmsResults.get_precipitation_timeseries("results.dss", "Sub1")
```

**See docstrings** in HmsResults.py for complete API

### Pattern 3: DSS Pathname Format

HMS uses standard DSS pathname: `/A/B/C/D/E/F/`

- **A**: Basin name
- **B**: Element name (subbasin/junction/reach)
- **C**: Parameter type (FLOW, PRECIP, etc.)
- **D**: Date/Time block (usually empty)
- **E**: Time interval (15MIN, 1HOUR, etc.)
- **F**: Run name/Version

**Example**: `/BASIN/OUTLET/FLOW//15MIN/RUN:RUN1/`

## Import Patterns

**All of these import patterns work:**

```python
# Top-level imports (recommended for most users)
from hms_commander import HmsDss, HmsDssGrid, DssCore

# Subpackage imports (also valid)
from hms_commander.dss import HmsDss, HmsDssGrid, DssCore
```

## HMS-Specific Methods

**HmsDss.extract_hms_results()**:
```python
results = HmsDss.extract_hms_results("results.dss", result_type="flow")
# Returns: {element_name: timeseries_dataframe}
```

Filters DSS catalog for HMS-specific pathnames.

## Results Analysis

**HmsResults provides**:
- get_peak_flows() - Summary DataFrame
- get_volume_summary() - Acre-feet volumes
- get_hydrograph_statistics() - Stats per element
- compare_runs() - Multi-run comparison
- export_results_to_csv() - Export workflows

**See**: `hms_commander/HmsResults.py` for complete API

## Paired Data (X-Y Curves)

**Write Atlas 14 temporal distributions and rating curves to DSS**

### Pattern 4: Write Paired Data

```python
import numpy as np
from hms_commander import HmsDss

# Write temporal distribution curve
x_hours = np.linspace(0, 24, 49)  # Time (hours)
y_cumulative = np.linspace(0, 1, 49)  # Cumulative fraction (0-1)

HmsDss.write_paired_data(
    dss_file="temporal.dss",
    pathname="//TX_R3/ALL-CASES/24HR///50%/",
    x_values=x_hours,
    y_values=y_cumulative,
    x_units="HOURS",
    y_units="FRACTION"
)
```

**Use cases**:
- Atlas 14 temporal distributions
- Rating curves
- Stage-discharge relationships
- Stage-area curves
- Any X-Y relationship

### Pattern 5: Write Multiple Paired Data

**More efficient** for batch writes:

```python
records = [
    {
        "pathname": "//TX_R3/FIRST-QUARTILE/24HR///50%/",
        "x_values": hours,
        "y_values": first_quartile_50,
    },
    {
        "pathname": "//TX_R3/FIRST-QUARTILE/24HR///90%/",
        "x_values": hours,
        "y_values": first_quartile_90,
    },
    # ... more records
]

results = HmsDss.write_multiple_paired_data("temporal.dss", records)
# Returns: {"//TX_R3/...": True, ...}
```

**See docstrings**: `HmsDss.write_paired_data()` and `HmsDss.write_multiple_paired_data()` for complete API

## Low-Level DSS Core

**Direct access to DSS Java bridge**: `hms_commander.dss.DssCore`

**When to use**:
- Custom DSS operations not in HmsDss
- Performance-critical operations (e.g., `get_peak_value()` for 350x memory efficiency)
- Advanced DSS features

**Example**:
```python
from hms_commander.dss import DssCore

# Low-level time series read
df = DssCore.read_timeseries("file.dss", pathname)

# Memory-efficient peak extraction
peak_info = DssCore.get_peak_value("file.dss", pathname)
# Returns: {'peak_flow': value, 'peak_time': datetime, 'units': str}

# Write paired data (low-level)
DssCore.write_paired_data(
    dss_file="file.dss",
    pathname="//A/B/C///D/",
    x_values=x_array,
    y_values=y_array
)
```

**Note**: Most users should use `HmsDss` wrapper instead

## DSS Grid Operations

**For gridded precipitation (AORC, HRAP, etc.)**:

```python
from hms_commander import HmsDssGrid
import numpy as np

# Write gridded precipitation to DSS
HmsDssGrid.write_grid_timeseries(
    dss_file="precip.dss",
    pathname="/AORC/WATERSHED/PRECIP////",
    grid_data=precip_array,  # shape: (time, lat, lon)
    lat_coords=lat_array,
    lon_coords=lon_array,
    timestamps=time_list,
    units="MM"
)
```

**See**: `hms_commander/dss/hms_dss_grid.py` for complete API

## File Structure

**After consolidation:**
```
hms_commander/
├── dss/                    # DSS subpackage
│   ├── __init__.py         # Exports: DssCore, HmsDss, HmsDssGrid
│   ├── core.py             # DssCore class
│   ├── hms_dss.py          # HmsDss class
│   ├── hms_dss_grid.py     # HmsDssGrid class
│   └── _hec_monolith.py    # Library downloader
├── HmsResults.py           # Results extraction (uses HmsDss)
├── HmsGrid.py              # HMS .grid files (NOT DSS, text files)
└── __init__.py             # Re-exports for backward compatibility
```

**Note**: `HmsGrid` is for HMS `.grid` text files, not DSS operations.

## Related

- **Execution**: .claude/rules/hec-hms/execution.md (generates DSS output)
- **Atlas14Storm**: .claude/rules/hec-hms/atlas14-storms.md (uses DSS for temporal distributions)
- **AORC Integration**: .claude/rules/hec-hms/aorc-integration.md (uses HmsDssGrid)
