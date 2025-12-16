---
paths: hms_commander/**/*.py
---

# DSS File Operations

## Primary Sources

**Code**:
- `hms_commander/HmsDss.py` - DSS operations (wraps RasDss)
- `hms_commander/HmsResults.py` - Results extraction and analysis

**Integration**: `ras-commander` package
- HmsDss wraps RasDss from ras-commander
- Provides DSS V6/V7 support via shared infrastructure

## Why HmsDss Wraps RasDss

**Decision**: Don't duplicate DSS code. Leverage ras-commander's mature DSS infrastructure.

**Benefits**:
- No code duplication
- Consistent DSS operations across HMS and RAS
- Automatic V6/V7 support
- Shared Java bridge maintenance

**Implementation**:
```python
# In hms_commander/HmsDss.py
from ras_commander import RasDss

class HmsDss:
    @staticmethod
    def read_timeseries(dss_file, pathname):
        return RasDss.read_timeseries(dss_file, pathname)
```

**Installation**: `pip install hms-commander` auto-installs ras-commander

## Common Patterns

### Pattern 1: Check DSS Availability

```python
from hms_commander import HmsDss

if HmsDss.is_available():
    catalog = HmsDss.get_catalog("results.dss")
```

**Note**: Requires Java and ras-commander installation

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
- **D**: Time interval (15MIN, 1HOUR, etc.)
- **E**: Run name
- **F**: Version (usually blank)

**Example**: `/BASIN/OUTLET/FLOW/15MIN/RUN1/`

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

## Related

- **RasDss**: ras-commander package (authoritative DSS implementation)
- **Execution**: .claude/rules/hec-hms/execution.md (generates DSS output)
