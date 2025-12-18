# User Guide Overview

Welcome to the HMS Commander User Guide. This section provides comprehensive documentation for all features and workflows.

## Quick Navigation

### Project Management
Learn how to initialize and manage HEC-HMS projects using HMS Commander's DataFrame-based approach.

### Basin Models
Work with basin model files (.basin) - read subbasins, modify loss parameters, configure transform methods.

### Meteorologic Models
Manage precipitation, evapotranspiration, and gage assignments in meteorologic models (.met).

### Control Specifications
Configure simulation time windows and time intervals.

### Time-Series Gages
Create and manage precipitation and discharge gages.

### Run Configuration
Set up simulation runs with basin, met, and control combinations. Configure DSS output files.

### Execution
Execute HEC-HMS simulations - single runs, parallel execution, batch processing.

### Geospatial Operations
Extract model geometry and export to GeoJSON for visualization in GIS tools.

### DSS Operations
Read and write DSS files for time-series data and results.

### Results Analysis
Extract peak flows, volumes, hydrograph statistics, and compare multiple runs.

### Clone Workflows
Use non-destructive clone operations for QAQC and model comparison workflows.

### Atlas 14 Updates
Update precipitation from TP-40 to NOAA Atlas 14 frequency estimates.

## Getting Started

If you're new to HMS Commander, start with:

1. [Installation Guide](../getting_started/installation.md)
2. [Quick Start Guide](../getting_started/quick_start.md)
3. [Example Notebooks](../examples/overview.md)

## LLM Forward Approach

All HMS Commander workflows follow [CLB Engineering's LLM Forward Approach](../CLB_ENGINEERING_APPROACH.md):

- **GUI Verifiable** - Inspect changes in HEC-HMS GUI
- **Traceable** - Complete audit trail
- **QAQC-able** - Automated quality checks
- **Non-Destructive** - Original models preserved
- **Professional** - Client-ready documentation

## API Reference

For detailed API documentation, see the [API Reference](../api/hms_prj.md) section.

---

**Note:** This user guide is under active development. Detailed pages for each section are coming soon. In the meantime, refer to:

- [API Reference](../api/hms_prj.md) - Complete API documentation
- [Example Notebooks](../examples/overview.md) - Working examples
- [Getting Started](../getting_started/quick_start.md) - Quick start guide
