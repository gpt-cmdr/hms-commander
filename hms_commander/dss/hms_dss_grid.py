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
from . import _backend
from .core import DssCore

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
            If pyjnius (Java backend) or ras_commander_fast_dss (native backend)
            is not installed.
        ValueError
            If array dimensions don't match. The native backend also refuses
            PER-CUM and PER-AVER grids (one time per grid gives equal start and
            end times) and unknown data types, before anything is written.
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
        - Each grid's D part is its timestamp and its E part the same time
          (midnight as the previous day's 2400), as HEC Monolith stores them
        - ``HmsDss.backend`` selects HEC Monolith (``java``, default), the
          ras_commander_fast_dss engine (``native``) or ``shadow``; the native
          writer stores the same specified-grid records as Monolith

        See Also
        --------
        HmsAorc.convert_to_dss_grid : Convenience method for AORC conversion
        """
        import numpy as np

        grid_data = np.asarray(grid_data)
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

        backend = DssCore.get_backend()
        if backend == "native":
            return HmsDssGrid._write_grid_timeseries_native(
                dss_file, pathname, grid_data, lat_coords, lon_coords, timestamps,
                units, data_type)
        if backend == "shadow":
            return HmsDssGrid._write_grid_timeseries_shadow(
                dss_file, pathname, grid_data, lat_coords, lon_coords, timestamps,
                units, data_type)
        return HmsDssGrid._write_grid_timeseries_java(
            dss_file, pathname, grid_data, lat_coords, lon_coords, timestamps,
            units, data_type)

    @staticmethod
    def _write_grid_timeseries_java(dss_file, pathname, grid_data, lat_coords,
                                    lon_coords, timestamps, units, data_type) -> Path:
        """``write_grid_timeseries`` through HEC Monolith (``GriddedData``)."""
        _check_dss_dependencies()
        import numpy as np

        dss_file = Path(dss_file)
        nt, nlat, nlon = grid_data.shape

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

        # Grid parameters (shared with the native writer)
        cell_size, min_x, min_y, lon_min, lat_min = HmsDssGrid._grid_geometry(
            lat_coords, lon_coords)

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

        # Full long absolute path. Monolith caches the native handle under this
        # exact string; the same string releases it after the writes.
        dss_path = str(dss_file.resolve())

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
                gridded_data.setDSSFileName(dss_path)
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
                DssCore._release_dss_file(dss_path)
                raise RuntimeError(
                    f"DSS grid write failed at timestep {t_idx} ({timestamp}): {e}"
                )

        # done() only lowers Monolith's file reference count. Close the native
        # file so its DSS lock is not held after this method returns.
        DssCore._release_dss_file(dss_path)

        # Final summary
        file_size_mb = dss_file.stat().st_size / (1024 * 1024) if dss_file.exists() else 0
        logger.info(f"DSS grid write complete: {dss_file}")
        logger.info(f"  File size: {file_size_mb:.2f} MB")
        logger.info(f"  Total cells: {nt * nlat * nlon:,}")

        return dss_file

    @staticmethod
    def _grid_geometry(lat_coords, lon_coords):
        """Cell size, lower-left cell indexes and origin, as the Java path computes them.

        The cell size is the average of the first latitude and longitude spacings and
        the lower-left cell is ``round(min / cell_size)`` from a (0, 0) cell zero.
        """
        import numpy as np

        lat_coords = np.asarray(lat_coords, dtype=np.float64)
        lon_coords = np.asarray(lon_coords, dtype=np.float64)
        dlat = abs(lat_coords[1] - lat_coords[0]) if len(lat_coords) > 1 else 0.01
        dlon = abs(lon_coords[1] - lon_coords[0]) if len(lon_coords) > 1 else 0.01
        cell_size = float((dlat + dlon) / 2.0)
        lat_min = float(lat_coords.min())
        lon_min = float(lon_coords.min())
        # Grid coordinates (origin / cellSize, per Vortex DssUtil.java line 156-157)
        return (cell_size, int(round(lon_min / cell_size)), int(round(lat_min / cell_size)),
                lon_min, lat_min)

    #: Period data types: HEC needs an end time after the start time for these.
    _PERIOD_TYPES = ("PER-CUM", "PER-AVER")
    _MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
               "NOV", "DEC")

    @staticmethod
    def _grid_pathname(pathname: str, timestamp) -> str:
        """The pathname HEC Monolith stores for one timestep: D is the time
        (``DDMMMYYYY:HHMM``, midnight ``0000``), E the same time with midnight as the
        previous day's ``2400``; A, B, C and F as given."""
        import pandas as pd

        parts = pathname.split("/")
        if len(parts) != 8 or parts[0] or parts[7]:
            raise ValueError(
                f"DSS pathname must have exactly six parts (/A/B/C/D/E/F/); got {pathname!r}")
        t = pd.Timestamp(timestamp)
        if t.tzinfo is not None:
            raise ValueError(f"timestamp {t} is time-zone aware; DSS grid times are naive")
        if t.second or t.microsecond or t.nanosecond:
            raise ValueError(f"timestamp {t} is not a whole minute (grid pathnames store minutes)")

        def fmt(day, hhmm):
            return f"{day.day:02d}{HmsDssGrid._MONTHS[day.month - 1]}{day.year:04d}:{hhmm}"

        d_part = fmt(t, f"{t.hour:02d}{t.minute:02d}")
        if t.hour == 0 and t.minute == 0:
            e_part = fmt(t - pd.Timedelta(days=1), "2400")
        else:
            e_part = d_part
        parts[4], parts[5] = d_part, e_part
        return "/".join(parts)

    @staticmethod
    def _native_grid_writes(pathname, grid_data, timestamps, data_type):
        """Per-timestep ``(pathname, cells)`` for the native writer, checked before
        anything is written."""
        import numpy as np

        if str(data_type).upper() in HmsDssGrid._PERIOD_TYPES:
            raise ValueError(
                f"The native DSS writer refuses {data_type} grids whose start and end "
                "times are equal (HEC period data needs an end time after the start "
                "time). write_grid_timeseries stores one time per grid, as the Java "
                "path does; use the Java backend for period grids, or INST-VAL / "
                "INST-CUM data."
            )
        return [(HmsDssGrid._grid_pathname(pathname, t),
                 np.ascontiguousarray(grid_data[i], dtype=np.float32))
                for i, t in enumerate(timestamps)]

    @staticmethod
    def _write_grid_timeseries_native(dss_file, pathname, grid_data, lat_coords,
                                      lon_coords, timestamps, units, data_type) -> Path:
        """``write_grid_timeseries`` through ras_commander_fast_dss (no JVM).

        Mirrors the Java path's records: a specified (WGS 84 WKT) grid per timestep,
        cell size and lower-left cell from ``_grid_geometry``, cell zero (0, 0),
        rows as given (row 0 of each ``grid_data[t]`` is stored as the southern row),
        HEC Monolith's D/E parts and ``is_interval`` true. Refuses PER-CUM and
        PER-AVER (equal start and end times) and unknown data types.
        """
        writes = HmsDssGrid._native_grid_writes(pathname, grid_data, timestamps, data_type)
        cell_size, min_x, min_y, _, _ = HmsDssGrid._grid_geometry(lat_coords, lon_coords)
        dc = _backend.require_native_writes()
        target, version, existed, created = DssCore._native_write_target(dss_file)
        with DssCore._native_new_file(dc, target, version, existed, created):
            for path_t, cells in writes:
                dc.write_grid(
                    str(target), path_t, cells, grid_type="specified",
                    cell_size=cell_size, lower_left_cell=(min_x, min_y),
                    cell_zero=(0.0, 0.0), units=units, data_type=str(data_type).upper(),
                    srs_definition=HmsDssGrid.WKT_WGS84, srs_name="WGS 84",
                    is_interval=True, version=version,
                )
        logger.info(f"DSS grid write complete (native): {target} ({len(writes)} grids)")
        return Path(dss_file)

    @staticmethod
    def _write_grid_timeseries_shadow(dss_file, pathname, grid_data, lat_coords,
                                      lon_coords, timestamps, units, data_type) -> Path:
        """Java write (its result and errors are returned); the native writer repeats
        it on a temporary copy and the native read-backs of every grid are compared."""
        args = (pathname, grid_data, lat_coords, lon_coords, timestamps, units, data_type)

        def native_call(copy, existed):
            HmsDssGrid._write_grid_timeseries_native(copy, *args)

        def compare(copy):
            dc = _backend.import_native()
            diffs = []
            for t in timestamps:
                path_t = HmsDssGrid._grid_pathname(pathname, t)
                java = dc.read_grid(str(Path(dss_file).resolve()), path_t, missing="raw")
                native = dc.read_grid(str(copy), path_t, missing="raw")
                diffs += [f"{path_t}:{d}" for d in HmsDssGrid._compare_written(java, native)]
            return diffs

        return DssCore._shadow_write(
            "write_grid_timeseries", dss_file, pathname,
            lambda: HmsDssGrid._write_grid_timeseries_java(dss_file, *args),
            native_call, compare,
        )

    #: Grid attributes compared after a shadow write (both files read natively).
    _WRITTEN_GRID_KEYS = (
        "pathname", "record_type", "grid_type", "nx", "ny", "cell_size",
        "lower_left_cell_x", "lower_left_cell_y", "x_coord_of_grid_cell_zero",
        "y_coord_of_grid_cell_zero", "srs_name", "srs_definition_type", "srs_definition",
        "data_units", "data_type", "start_time", "end_time", "min_value", "max_value",
        "mean_value", "null_value",
    )
    _WRITTEN_GRID_METADATA = ("compression_method", "time_zone_id", "time_zone_raw_offset",
                              "is_interval")

    @staticmethod
    def _compare_written(java, native) -> List[str]:
        """Differences between the native read-backs of a Java- and a native-written
        grid: stored cell bits, header fields and the range table. The compressed bytes
        and ZLIB's unused scale/base words are not compared."""
        import numpy as np

        diffs = []
        for key in HmsDssGrid._WRITTEN_GRID_KEYS:
            jv, nv = getattr(java, key), getattr(native, key)
            same = (jv is None and nv is None) or (
                jv is not None and nv is not None and np.array_equal(
                    np.asarray(jv), np.asarray(nv), equal_nan=isinstance(jv, float)))
            if not same:
                diffs.append(key)
        for key in HmsDssGrid._WRITTEN_GRID_METADATA:
            if java.metadata.get(key) != native.metadata.get(key):
                diffs.append(f"metadata.{key}")
        jd = np.ascontiguousarray(java.data, dtype=np.float32)
        nd = np.ascontiguousarray(native.data, dtype=np.float32)
        if jd.shape != nd.shape or not np.array_equal(jd.view(np.int32), nd.view(np.int32)):
            diffs.append("cells_bits")
        for key in ("range_limit_table", "range_counts"):
            if not np.array_equal(np.asarray(getattr(java, key)), np.asarray(getattr(native, key))):
                diffs.append(key)
        return diffs

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
