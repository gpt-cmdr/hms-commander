"""
hms-commander DSS subpackage: HEC-DSS file operations.

This subpackage provides DSS file reading capabilities using HEC Monolith
Java libraries via pyjnius. All dependencies are lazy-loaded to minimize
import time and keep optional dependencies truly optional.

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
    from hms_commander.dss import DssCore

    # Get catalog of all paths in DSS file
    paths = DssCore.get_catalog("file.dss")

    # Read time series
    df = DssCore.read_timeseries("file.dss", paths[0])
    print(df.attrs['units'])  # Access metadata

See Also:
    - examples/03_project_dataframes.ipynb for DSS integration with HMS projects
"""

from .core import DssCore

__all__ = ['DssCore']
