"""
hms-commander DSS subpackage: HEC-DSS file operations.

This subpackage provides DSS file reading and writing capabilities using HEC Monolith
Java libraries via pyjnius. All dependencies are lazy-loaded to minimize
import time and keep optional dependencies truly optional.

Classes:
    DssCore: Low-level DSS operations (read/write time series, paired data, catalog)
    HmsDss: HMS-specific DSS wrapper with convenience methods
    HmsDssGrid: DSS grid operations for gridded precipitation

Lazy Loading Behavior:
    - `import hms_commander` - DSS not loaded (fast startup)
    - `from hms_commander.dss import DssCore` - DSS subpackage loaded
    - `DssCore.get_catalog(...)` - pyjnius/Java loaded on first call
    - HEC Monolith libraries downloaded automatically on first use (~20 MB)

Dependencies:
    Required at runtime (lazy loaded):
        - pyjnius: pip install pyjnius
        - Java JRE/JDK 8+: Must be installed and JAVA_HOME set

    Auto-downloaded:
        - HEC Monolith libraries (~20 MB, cached in ~/.hms-commander/dss/)

Usage:
    # Low-level DSS operations
    from hms_commander.dss import DssCore
    paths = DssCore.get_catalog("file.dss")
    df = DssCore.read_timeseries("file.dss", paths[0])

    # HMS-specific convenience methods
    from hms_commander.dss import HmsDss
    peaks = HmsDss.get_peak_flows("results.dss")
    flows = HmsDss.list_flow_results("results.dss")

    # DSS grid operations
    from hms_commander.dss import HmsDssGrid
    HmsDssGrid.write_grid_timeseries("precip.dss", pathname, grid_data, lat, lon, times)

See Also:
    - examples/03_project_dataframes.ipynb for DSS integration with HMS projects
    - examples/08_atlas14_hyetograph_generation.ipynb for paired data operations
"""

from .core import DssCore
from .hms_dss import HmsDss
from .hms_dss_grid import HmsDssGrid

__all__ = ['DssCore', 'HmsDss', 'HmsDssGrid']
