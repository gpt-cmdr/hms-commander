"""
HmsDssGrid - DSS Grid Operations for HMS Commander

Provides methods for writing gridded precipitation data to DSS format
using HEC Monolith libraries, following the pattern discovered in HEC-Vortex.

This module enables conversion of AORC NetCDF data to HMS-compatible DSS grids.

Classes:
    HmsDssGrid: Static class for DSS grid writing operations

Key Functions:
    write_grid_timeseries: Write gridded precipitation time series to DSS
    get_info: Get information about DSS grid format

Dependencies:
    Required:
        - pyjnius: pip install pyjnius
        - Java 8+ JRE/JDK
        - numpy: Numerical array operations
        - pandas: Time series handling

    Install with:
        pip install hms-commander[dss]
        # OR
        pip install pyjnius numpy pandas

Technical Notes:
    The implementation mirrors HEC-Vortex's DssDataWriter.java (lines 276-317)
    and DssUtil.java (lines 99-187), using the same HEC Monolith classes:
    - hec.heclib.grid.SpecifiedGridInfo: For WGS84 lat/lon grids
    - hec.heclib.grid.GridData: Grid values container
    - hec.heclib.grid.GriddedData: DSS writer (key class)
    - hec.heclib.dss.DssDataType: Data type enum (PER_CUM for precip)
    - hec.heclib.util.HecTime: Time handling

Example:
    >>> from hms_commander import HmsDssGrid
    >>> import numpy as np
    >>> from datetime import datetime
    >>>
    >>> # Create sample grid (5x5, 3 timesteps)
    >>> grid_data = np.random.rand(3, 5, 5) * 10  # mm
    >>> lat = np.linspace(41.0, 41.1, 5)
    >>> lon = np.linspace(-77.5, -77.4, 5)
    >>> times = [datetime(2020, 5, 1, i) for i in range(3)]
    >>>
    >>> # Write to DSS
    >>> HmsDssGrid.write_grid_timeseries(
    ...     dss_file="precip.dss",
    ...     pathname="/AORC/TEST/PRECIP////",
    ...     grid_data=grid_data,
    ...     lat_coords=lat,
    ...     lon_coords=lon,
    ...     timestamps=times
    ... )

References:
    - HEC-Vortex source: https://github.com/HydrologicEngineeringCenter/Vortex
    - DssDataWriter.java: vortex-api/src/main/java/.../io/DssDataWriter.java
    - DssUtil.java: vortex-api/src/main/java/.../util/DssUtil.java
"""

from pathlib import Path
from typing import Union, List, Optional
from datetime import datetime
import logging

from ..LoggingConfig import get_logger
from ..Decorators import log_call

logger = get_logger(__name__)


def _check_dss_dependencies():
    """Check that DSS dependencies are installed."""
    missing = []

    try:
        import numpy
    except ImportError:
        missing.append("numpy")

    try:
        import jnius_config
    except ImportError:
        missing.append("pyjnius")

    if missing:
        raise ImportError(
            f"Missing DSS dependencies: {', '.join(missing)}. "
            "Install with: pip install hms-commander[dss] "
            "or: pip install pyjnius numpy"
        )


class HmsDssGrid:
    """
    Static class for DSS grid operations using HEC Monolith.

    Provides methods for writing gridded precipitation data to DSS format,
    mirroring the implementation pattern found in HEC-Vortex.

    All methods are static - do not instantiate this class.

    Technical Background:
        HMS requires gridded precipitation data in DSS format with specific
        grid metadata (SpecifiedGridInfo for WGS84). This class uses the same
        HEC Monolith Java classes as HEC-Vortex, accessed via pyjnius.

    Example:
        >>> from hms_commander import HmsDssGrid
        >>> import numpy as np
        >>>
        >>> # Write AORC data to DSS
        >>> HmsDssGrid.write_grid_timeseries(
        ...     dss_file="aorc.dss",
        ...     pathname="/AORC/STORM/PRECIP////",
        ...     grid_data=precip_array,
        ...     lat_coords=lat_array,
        ...     lon_coords=lon_array,
        ...     timestamps=time_list
        ... )
    """

    _jvm_configured = False

    # WKT for WGS84 (standard for AORC and most gridded precip data)
    WKT_WGS84 = (
        'GEOGCS["WGS 84",'
        'DATUM["WGS_1984",'
        'SPHEROID["WGS 84",6378137,298.257223563]],'
        'PRIMEM["Greenwich",0],'
        'UNIT["degree",0.0174532925199433]]'
    )

    @staticmethod
    def _ensure_monolith():
        """
        Ensure HEC Monolith libraries are loaded.

        Uses hms-commander's local DssCore infrastructure for HEC Monolith
        download and JVM configuration.
        """
        from .core import DssCore
        DssCore._ensure_monolith()

        if not HmsDssGrid._jvm_configured:
            DssCore._configure_jvm()
            HmsDssGrid._jvm_configured = True

    @staticmethod
    @log_call
    def write_grid_timeseries(
        dss_file: Union[str, Path],
        pathname: str,
        grid_data: 'np.ndarray',
        lat_coords: 'np.ndarray',
        lon_coords: 'np.ndarray',
        timestamps: List[datetime],
        units: str = "MM",
        data_type: str = "PER-CUM"
    ) -> Path:
        """
        Write gridded precipitation time series to DSS file.

        Converts NumPy grid arrays to DSS grid format using HEC Monolith,
        following the pattern from HEC-Vortex's DssDataWriter.

        Parameters
        ----------
        dss_file : str or Path
            Output DSS file path. Created if it doesn't exist.
        pathname : str
            DSS pathname for the grid data.
            Format: /A/B/C/D/E/F/ where typically:
            - A: Source identifier (e.g., "AORC")
            - B: Location/grid name
            - C: Parameter (e.g., "PRECIP")
            - D-F: Time/version (handled internally)
        grid_data : np.ndarray
            Precipitation data as 3D array with shape (time, lat, lon).
            Values should be in units specified by `units` parameter.
        lat_coords : np.ndarray
            1D array of latitude values in decimal degrees (WGS84).
            Must match grid_data.shape[1].
        lon_coords : np.ndarray
            1D array of longitude values in decimal degrees (WGS84).
            Must match grid_data.shape[2].
        timestamps : List[datetime]
            List of datetime objects for each timestep.
            Must match grid_data.shape[0].
        units : str, default "MM"
            Data units string. Common values:
            - "MM" - millimeters
            - "IN" - inches
        data_type : str, default "PER-CUM"
            DSS data type. Options:
            - "PER-CUM" - Period cumulative (for precipitation)
            - "PER-AVER" - Period average (for temperature)
            - "INST-VAL" - Instantaneous value

        Returns
        -------
        Path
            Path to the output DSS file.

        Raises
        ------
        ImportError
            If pyjnius not installed.
        ValueError
            If array dimensions don't match.
        RuntimeError
            If DSS write operation fails.

        Examples
        --------
        >>> from hms_commander import HmsDssGrid
        >>> import numpy as np
        >>> from datetime import datetime, timedelta
        >>>
        >>> # Create synthetic grid (hourly data for 24 hours)
        >>> grid = np.random.rand(24, 10, 10) * 5.0  # 0-5 mm per hour
        >>> lat = np.linspace(40.0, 41.0, 10)
        >>> lon = np.linspace(-78.0, -77.0, 10)
        >>> times = [datetime(2020, 5, 1) + timedelta(hours=i) for i in range(24)]
        >>>
        >>> # Write to DSS
        >>> HmsDssGrid.write_grid_timeseries(
        ...     dss_file="precip.dss",
        ...     pathname="/AORC/WATERSHED/PRECIP////",
        ...     grid_data=grid,
        ...     lat_coords=lat,
        ...     lon_coords=lon,
        ...     timestamps=times,
        ...     units="MM"
        ... )

        Notes
        -----
        - Data is written in WGS84 (lat/lon) coordinate system
        - Cell size is calculated as average of lat/lon spacing
        - Grid origin is set to lower-left corner
        - Uses SpecifiedGridInfo (not AlbersInfo) for lat/lon grids
        - Implementation mirrors HEC-Vortex DssDataWriter.java

        See Also
        --------
        HmsAorc.convert_to_dss_grid : Convenience method for AORC conversion
        """
        _check_dss_dependencies()

        import numpy as np
        import pandas as pd

        dss_file = Path(dss_file)

        # Validate array dimensions
        if grid_data.ndim != 3:
            raise ValueError(
                f"grid_data must be 3D (time, lat, lon), got shape {grid_data.shape}"
            )

        nt, nlat, nlon = grid_data.shape

        if len(lat_coords) != nlat:
            raise ValueError(
                f"lat_coords length ({len(lat_coords)}) must match "
                f"grid_data lat dimension ({nlat})"
            )

        if len(lon_coords) != nlon:
            raise ValueError(
                f"lon_coords length ({len(lon_coords)}) must match "
                f"grid_data lon dimension ({nlon})"
            )

        if len(timestamps) != nt:
            raise ValueError(
                f"timestamps length ({len(timestamps)}) must match "
                f"grid_data time dimension ({nt})"
            )

        # Ensure HEC Monolith is ready
        logger.info("Configuring HEC Monolith for DSS grid writing...")
        HmsDssGrid._ensure_monolith()

        # Import HEC classes (exact classes from Vortex analysis)
        from jnius import autoclass

        try:
            SpecifiedGridInfo = autoclass('hec.heclib.grid.SpecifiedGridInfo')
            GridData = autoclass('hec.heclib.grid.GridData')
            GriddedData = autoclass('hec.heclib.grid.GriddedData')
            DssDataType = autoclass('hec.heclib.dss.DssDataType')
            HecTime = autoclass('hec.heclib.util.HecTime')
        except Exception as e:
            raise RuntimeError(
                f"Failed to load HEC Monolith grid classes: {e}\n"
                "Ensure pyjnius is properly installed with Java 8+."
            )

        # Calculate grid parameters
        lat_coords = np.asarray(lat_coords, dtype=np.float64)
        lon_coords = np.asarray(lon_coords, dtype=np.float64)

        # Cell size (average of lat and lon spacing)
        dlat = abs(lat_coords[1] - lat_coords[0]) if nlat > 1 else 0.01
        dlon = abs(lon_coords[1] - lon_coords[0]) if nlon > 1 else 0.01
        cell_size = float((dlat + dlon) / 2.0)

        # Grid origin (lower-left corner)
        lat_min = float(lat_coords.min())
        lon_min = float(lon_coords.min())

        # Grid coordinates (origin / cellSize, per Vortex DssUtil.java line 156-157)
        min_x = int(round(lon_min / cell_size))
        min_y = int(round(lat_min / cell_size))

        # Map data_type string to DssDataType enum
        data_type_map = {
            "PER-CUM": DssDataType.PER_CUM,
            "PER-AVER": DssDataType.PER_AVER,
            "INST-VAL": DssDataType.INST_VAL,
            "INST-CUM": DssDataType.INST_CUM,
        }
        dss_data_type = data_type_map.get(data_type.upper(), DssDataType.PER_CUM)

        # Create output directory if needed
        dss_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing DSS grid to: {dss_file}")
        logger.info(f"  Pathname: {pathname}")
        logger.info(f"  Grid: {nlat} lat x {nlon} lon = {nlat * nlon} cells")
        logger.info(f"  Timesteps: {nt}")
        logger.info(f"  Cell size: {cell_size:.6f} degrees")
        logger.info(f"  Origin: ({lon_min:.4f}, {lat_min:.4f})")
        logger.info(f"  Units: {units}, Type: {data_type}")

        # Write each timestep (Vortex pattern: one write per timestep)
        for t_idx, timestamp in enumerate(timestamps):
            try:
                # Create SpecifiedGridInfo for this timestep (Vortex DssUtil.java lines 141-159)
                grid_info = SpecifiedGridInfo()

                # Set spatial reference (WGS84)
                grid_info.setSpatialReference("WGS 84", HmsDssGrid.WKT_WGS84, 0, 0)

                # Set cell info (minX, minY, nx, ny, cellSize)
                grid_info.setCellInfo(min_x, min_y, nlon, nlat, float(cell_size))

                # Set units and data type
                grid_info.setDataUnits(units)
                grid_info.setDataType(dss_data_type.value())

                # Set times (Vortex pattern: same start and end for single timestep)
                time_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
                hec_time = HecTime(time_str)
                grid_info.setGridTimes(hec_time, hec_time)

                # Extract and flatten grid for this timestep
                # Grid is (lat, lon), flatten in C order (row-major)
                precip_2d = grid_data[t_idx, :, :]
                precip_flat = precip_2d.flatten(order='C').astype(np.float32)

                # Convert numpy array to Java float array
                # pyjnius handles Python list to Java array conversion
                precip_list = precip_flat.tolist()

                # Create GridData (Vortex pattern: GridData constructor takes float[] and GridInfo)
                grid_data_obj = GridData(precip_list, grid_info)

                # Create GriddedData writer (Vortex DssDataWriter.java lines 294-316)
                gridded_data = GriddedData()
                gridded_data.setDSSFileName(str(dss_file))
                gridded_data.setPathname(pathname)

                # Set time window
                gridded_data.setGriddedTimeWindow(hec_time, hec_time)

                # WRITE TO DSS! (The critical call from Vortex)
                status = gridded_data.storeGriddedData(grid_info, grid_data_obj)
                if status != 0:
                    raise RuntimeError(
                        f"DSS grid write failed at {timestamp}: status code {status}"
                    )

                # Cleanup (Vortex pattern: done() after each write)
                gridded_data.done()

                # Progress update
                if (t_idx + 1) % 10 == 0 or (t_idx + 1) == nt:
                    logger.info(f"  Wrote {t_idx + 1}/{nt} timesteps")

            except Exception as e:
                raise RuntimeError(
                    f"DSS grid write failed at timestep {t_idx} ({timestamp}): {e}"
                )

        # Final summary
        file_size_mb = dss_file.stat().st_size / (1024 * 1024) if dss_file.exists() else 0
        logger.info(f"DSS grid write complete: {dss_file}")
        logger.info(f"  File size: {file_size_mb:.2f} MB")
        logger.info(f"  Total cells: {nt * nlat * nlon:,}")

        return dss_file

    @staticmethod
    def get_info() -> dict:
        """
        Get information about DSS grid format and requirements.

        Returns
        -------
        dict
            Information about DSS grid format including:
            - format: Description of DSS grid format
            - requirements: HMS requirements for gridded precip
            - classes: HEC Monolith classes used
            - references: Links to documentation

        Examples
        --------
        >>> from hms_commander import HmsDssGrid
        >>> info = HmsDssGrid.get_info()
        >>> print(info['format'])
        'HEC-DSS grid format with SpecifiedGridInfo for WGS84 lat/lon grids'
        """
        return {
            'format': 'HEC-DSS grid format with SpecifiedGridInfo for WGS84 lat/lon grids',
            'hms_requirement': 'HMS requires gridded precipitation in DSS format (External DSS source)',
            'supported_crs': {
                'WGS84': 'SpecifiedGridInfo with WKT spatial reference',
                'Albers': 'AlbersInfo for HRAP/SHG projections',
            },
            'data_types': {
                'PER-CUM': 'Period cumulative (precipitation)',
                'PER-AVER': 'Period average (temperature)',
                'INST-VAL': 'Instantaneous value',
                'INST-CUM': 'Instantaneous cumulative',
            },
            'hec_classes': {
                'SpecifiedGridInfo': 'hec.heclib.grid.SpecifiedGridInfo - Grid definition for lat/lon',
                'GridData': 'hec.heclib.grid.GridData - Grid values container',
                'GriddedData': 'hec.heclib.grid.GriddedData - DSS writer',
                'DssDataType': 'hec.heclib.dss.DssDataType - Data type enum',
                'HecTime': 'hec.heclib.util.HecTime - Time handling',
            },
            'references': {
                'HEC-Vortex': 'https://github.com/HydrologicEngineeringCenter/Vortex',
                'DssDataWriter': 'vortex-api/src/main/java/.../io/DssDataWriter.java',
                'DssUtil': 'vortex-api/src/main/java/.../util/DssUtil.java',
                'HMS Gridded Precip': 'https://www.hec.usace.army.mil/confluence/hmsdocs/hmsguides/gridded-boundary-condition-data/',
            },
        }
