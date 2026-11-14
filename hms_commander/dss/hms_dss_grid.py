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
    >>> times = [datetime(2020, 5, 1, i) for i in range(1, 4)]  # period ends
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
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
from datetime import datetime
import logging

from ..LoggingConfig import get_logger
from ..Decorators import log_call
from . import _backend
from .core import DssCore

logger = get_logger(__name__)

PathLike = Union[str, Path]


def _abs(value: PathLike) -> str:
    """Absolute path string for the engine."""
    return str(Path(value).resolve())


def _abs_many(value: Union[PathLike, Sequence[PathLike]]) -> Union[str, List[str]]:
    if isinstance(value, (str, Path)):
        return _abs(value)
    return [_abs(item) for item in value]


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

    Engine tools:
        ``import_gridded``, ``import_arrays``, ``import_zarr``, ``list_variables``,
        ``zarr_variables``, ``read_zarr``, ``calculate``, ``calculate_raster``,
        ``sanitize``, ``clip``, ``normalize``, ``shift_times``, ``resample_times``,
        ``time_steps``, ``series_info``, ``read_window``, ``read_nearest``,
        ``read_min_max``, ``grid_to_point``, ``zonal_statistics`` and ``zone_masks``
        are thin wrappers around the functions of the same names in
        ``ras_commander_fast_dss.gridded``. They run on the optional
        ras-commander-fast-dss engine whatever ``HmsDss.backend`` is (there is no
        Java route), pass their remaining arguments to the engine unchanged and
        return its result unchanged. They raise ``ImportError`` without the engine
        and ``DssCapabilityError`` when the installed version does not provide the
        operation; ``get_features()`` reports what it provides.
        ``help(ras_commander_fast_dss.gridded.<name>)`` documents every option.

    ``sync``:
        The engine's flush policy on the methods that write, passed through
        unchanged. ``None`` (default) states nothing, so the installed engine's own
        default applies; that default can change between engine releases. In
        ras-commander-fast-dss 0.1.2 the modes are ``"end"`` (default; ``True``),
        ``"step"`` and ``"none"`` (``False``); a call that stores several records
        flushes once, after its last record, under ``"end"``.

    Threads:
        In ras-commander-fast-dss 0.1.2, ``import_gridded``, ``import_arrays`` and
        ``import_zarr`` use every core by default (``threads=None``). The records
        (cell values, grid metadata and pathnames) do not depend on the count, but
        the file bytes can differ, because DSS stores each record's write time.
        Pass ``threads=1`` to limit it.

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
        data_type: str = "PER-CUM",
        interval_minutes: Optional[int] = None,
        *,
        target_crs: Optional[str] = None,
        cell_size: Optional[float] = None,
        resample_method: str = "bilinear",
        envelope: Optional[Sequence[float]] = None,
        sync: Optional[Any] = None,
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
            Times of the grids. For ``INST-VAL`` and ``INST-CUM``: one instant per grid.
            For ``PER-CUM`` and ``PER-AVER``: one period **end** per grid (the period is
            the ``interval_minutes`` before it), or one more time than there are grids,
            as period boundaries. AORC stamps are period ends, so they pass unchanged.
            Times must be whole minutes, and naive or UTC. A UTC time is stored at its
            UTC clock time; another time zone raises ``ValueError``, because DSS grid
            times hold no zone and the model clock is the caller's choice.
        units : str, default "MM"
            Data units string. Common values:
            - "MM" - millimeters
            - "IN" - inches
        data_type : str, default "PER-CUM"
            DSS data type. Options:
            - "PER-CUM" - Period cumulative (for precipitation)
            - "PER-AVER" - Period average (for temperature)
            - "INST-VAL" - Instantaneous value
            - "INST-CUM" - Instantaneous cumulative
        interval_minutes : int, optional
            Period length for ``PER-CUM`` and ``PER-AVER`` when ``timestamps`` holds
            period ends. ``None``: the spacing of the timestamps, which must be uniform.
            A single grid or stamps with gaps need this argument. Not used for
            instantaneous data.
        target_crs : str, optional
            ``None`` (default): write the WGS 84 grid as given, through the backend
            ``HmsDss.backend`` selects. ``"SHG"``: warp the grid to the Standard
            Hydrologic Grid (USGS CONUS Albers, NAD 83, metres) with the gridded
            importer of the native engine, ``ras_commander_fast_dss.gridded``, and
            store Albers grid records. This route needs the engine on every backend:
            HEC Monolith has no warp, so there is no Java route and no shadow
            comparison.
        cell_size : float, optional
            SHG cell size in metres; ``None`` means 2000 (the HEC-HMS SHG 2 km
            lattice). Only with ``target_crs``.
        resample_method : str, default "bilinear"
            ``"bilinear"``, ``"average"`` or ``"near"``. Only with ``target_crs``.
        envelope : sequence of float, optional
            ``(min_x, min_y, max_x, max_y)`` of the SHG grid in metres. ``None``:
            the extent of the WGS 84 cells, projected and snapped to whole cells by
            the engine. Only with ``target_crs``.
        sync : optional
            Flush policy of the native writer (and of the SHG warp route), passed to
            ras-commander-fast-dss unchanged. ``None`` (default) leaves the installed
            engine's own default. The ``java`` backend does not use it.

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
            If a time is not a whole minute or has a time zone other than UTC, array
            dimensions don't match, the data type is unknown, or a PER-CUM or
            PER-AVER grid has no period (start at or after end). Raised on every
            backend before anything is written: HEC-HMS treats the cells of a period
            grid with equal start and end times as missing.
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
        >>> times = [datetime(2020, 5, 1) + timedelta(hours=i) for i in range(1, 25)]  # period ends
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
        - Without ``target_crs``, data is written in the WGS84 (lat/lon) coordinate system
        - Cell size is calculated as average of lat/lon spacing
        - Grid origin is set to lower-left corner
        - Uses SpecifiedGridInfo (not AlbersInfo) for lat/lon grids
        - Implementation mirrors HEC-Vortex DssDataWriter.java
        - The D part is the period start and the E part the period end (midnight is
          ``0000`` in D and the previous day's ``2400`` in E), so the period ending
          2020-05-02 00:00 is ``/01MAY2020:2300/01MAY2020:2400/``. Instantaneous
          grids have the instant in both parts.
        - ``HmsDss.backend`` selects HEC Monolith (``java``, default), the
          ras_commander_fast_dss engine (``native``) or ``shadow``; the native
          writer stores the same specified-grid records as Monolith

        See Also
        --------
        HmsAorc.convert_to_dss_grid : Convenience method for AORC conversion
        """
        import numpy as np

        if sync is not None:
            with _backend.write_sync(sync, DssCore.get_backend()):
                return HmsDssGrid.write_grid_timeseries(
                    dss_file, pathname, grid_data, lat_coords, lon_coords, timestamps,
                    units, data_type, interval_minutes, target_crs=target_crs,
                    cell_size=cell_size, resample_method=resample_method,
                    envelope=envelope)
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

        windows = HmsDssGrid._grid_time_windows(timestamps, nt, data_type, interval_minutes)

        if target_crs is not None:
            return HmsDssGrid._write_grid_timeseries_warped(
                dss_file, pathname, grid_data, lat_coords, lon_coords, windows,
                units, data_type, target_crs=target_crs, cell_size=cell_size,
                resample_method=resample_method, envelope=envelope)
        if cell_size is not None or envelope is not None:
            raise ValueError("cell_size and envelope apply only with target_crs (for example 'SHG')")

        backend = DssCore.get_backend()
        if backend == "native":
            return HmsDssGrid._write_grid_timeseries_native(
                dss_file, pathname, grid_data, lat_coords, lon_coords, windows,
                units, data_type)
        if backend == "shadow":
            return HmsDssGrid._write_grid_timeseries_shadow(
                dss_file, pathname, grid_data, lat_coords, lon_coords, windows,
                units, data_type)
        return HmsDssGrid._write_grid_timeseries_java(
            dss_file, pathname, grid_data, lat_coords, lon_coords, windows,
            units, data_type)

    @staticmethod
    def _write_grid_timeseries_java(dss_file, pathname, grid_data, lat_coords,
                                    lon_coords, windows, units, data_type) -> Path:
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
        dss_data_type = data_type_map[data_type.upper()]

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
        for t_idx, (start, end) in enumerate(windows):
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

                # Period start and end (equal for instantaneous data)
                hec_start = HecTime(start.strftime('%Y-%m-%dT%H:%M:%S'))
                hec_end = HecTime(end.strftime('%Y-%m-%dT%H:%M:%S'))
                grid_info.setGridTimes(hec_start, hec_end)

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
                gridded_data.setGriddedTimeWindow(hec_start, hec_end)

                # WRITE TO DSS! (The critical call from Vortex)
                status = gridded_data.storeGriddedData(grid_info, grid_data_obj)
                if status != 0:
                    raise RuntimeError(
                        f"DSS grid write failed at {end}: status code {status}"
                    )

                # Cleanup (Vortex pattern: done() after each write)
                gridded_data.done()

                # Progress update
                if (t_idx + 1) % 10 == 0 or (t_idx + 1) == nt:
                    logger.info(f"  Wrote {t_idx + 1}/{nt} timesteps")

            except Exception as e:
                DssCore._release_dss_file(dss_path)
                raise RuntimeError(
                    f"DSS grid write failed at timestep {t_idx} ({end}): {e}"
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
    _INSTANT_TYPES = ("INST-VAL", "INST-CUM")
    _MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT",
               "NOV", "DEC")

    @staticmethod
    def _check_grid_time(t) -> None:
        if t.tzinfo is not None:
            raise ValueError(f"timestamp {t} is time-zone aware; DSS grid times are naive")
        if t.second or t.microsecond or t.nanosecond:
            raise ValueError(f"timestamp {t} is not a whole minute (grid pathnames store minutes)")

    @staticmethod
    def _naive_grid_time(timestamp):
        """``timestamp`` as a naive ``pd.Timestamp``. UTC keeps its clock time, as earlier
        versions stored it; another zone raises, rather than choosing a model clock."""
        import pandas as pd

        t = pd.Timestamp(timestamp)
        if t.tzinfo is not None:
            if t.utcoffset() != pd.Timedelta(0):
                raise ValueError(
                    f"timestamp {t} is time-zone aware and not UTC; DSS grid times hold no "
                    "zone, so convert it to the model's clock and pass it naive or as UTC"
                )
            t = t.tz_localize(None)
        HmsDssGrid._check_grid_time(t)
        return t

    @staticmethod
    def _grid_time_windows(timestamps, n_grids, data_type, interval_minutes=None):
        """``(start, end)`` for each grid, on every backend, before anything is written.

        Instantaneous types: start = end = the stamp. Period types: stamps are period
        ends (``interval_minutes``, or their uniform spacing, before each), or
        ``n_grids + 1`` boundaries, as ``RasDss._grid_time_windows``. Unlike RasDss, there
        is no median spacing or 60-minute default: a gap or a single grid would give a
        wrong period, so those need ``interval_minutes``. A period with start at or after end is
        refused: HEC-HMS 4.9 and 4.11 to 4.13 read the cells of such a record as missing.
        """
        import numpy as np
        import pandas as pd

        kind = str(data_type).upper()
        known = HmsDssGrid._PERIOD_TYPES + HmsDssGrid._INSTANT_TYPES
        if kind not in known:
            raise ValueError(f"Unknown grid data type {data_type!r}; expected one of {known}")
        stamps = [HmsDssGrid._naive_grid_time(t) for t in timestamps]
        is_period = kind in HmsDssGrid._PERIOD_TYPES
        if len(stamps) != n_grids and not (is_period and len(stamps) == n_grids + 1):
            raise ValueError(
                f"timestamps length ({len(stamps)}) must match grid_data time dimension "
                f"({n_grids})" + (" or be one longer (period boundaries)" if is_period else "")
            )
        if not is_period:
            return [(t, t) for t in stamps]

        if len(stamps) == n_grids + 1:
            windows = list(zip(stamps[:-1], stamps[1:]))
        else:
            if interval_minutes is None:
                steps = np.diff(np.array(stamps, dtype="datetime64[m]")).astype(int)
                if not len(steps) or steps.min() <= 0 or steps.min() != steps.max():
                    raise ValueError(
                        f"{data_type} grids are periods and these timestamps have no "
                        "uniform increasing spacing to take the period length from; "
                        "pass interval_minutes"
                    )
                interval_minutes = int(steps[0])
            if isinstance(interval_minutes, bool) or int(interval_minutes) != interval_minutes:
                raise ValueError(
                    f"interval_minutes must be a whole number, not {interval_minutes!r}")
            interval = pd.Timedelta(minutes=int(interval_minutes))
            windows = [(t - interval, t) for t in stamps]
        for start, end in windows:
            if start >= end:
                raise ValueError(
                    f"{data_type} grid period {start} to {end} has no length: the start "
                    "time must be before the end time. HEC-HMS reads the cells of a "
                    "record with equal start and end times as missing and sets the "
                    "precipitation to zero."
                )
        return windows

    @staticmethod
    def _grid_pathname(pathname: str, start, end=None) -> str:
        """The pathname HEC Monolith stores for one grid: D is the start
        (``DDMMMYYYY:HHMM``, midnight ``0000``), E the end (``end`` defaults to ``start``)
        with midnight as the previous day's ``2400``; A, B, C and F as given."""
        import pandas as pd

        parts = pathname.split("/")
        if len(parts) != 8 or parts[0] or parts[7]:
            raise ValueError(
                f"DSS pathname must have exactly six parts (/A/B/C/D/E/F/); got {pathname!r}")
        start = pd.Timestamp(start)
        end = start if end is None else pd.Timestamp(end)
        HmsDssGrid._check_grid_time(start)
        HmsDssGrid._check_grid_time(end)

        def fmt(day, hhmm):
            return f"{day.day:02d}{HmsDssGrid._MONTHS[day.month - 1]}{day.year:04d}:{hhmm}"

        d_part = fmt(start, f"{start.hour:02d}{start.minute:02d}")
        if end.hour == 0 and end.minute == 0:
            e_part = fmt(end - pd.Timedelta(days=1), "2400")
        else:
            e_part = fmt(end, f"{end.hour:02d}{end.minute:02d}")
        parts[4], parts[5] = d_part, e_part
        return "/".join(parts)

    @staticmethod
    def _native_grid_writes(pathname, grid_data, windows):
        """Per-grid ``(pathname, cells)`` for the native writer, checked before
        anything is written."""
        import numpy as np

        return [(HmsDssGrid._grid_pathname(pathname, start, end),
                 np.ascontiguousarray(grid_data[i], dtype=np.float32))
                for i, (start, end) in enumerate(windows)]

    @staticmethod
    def _write_grid_timeseries_native(dss_file, pathname, grid_data, lat_coords,
                                      lon_coords, windows, units, data_type) -> Path:
        """``write_grid_timeseries`` through ras_commander_fast_dss (no JVM).

        Mirrors the Java path's records: a specified (WGS 84 WKT) grid per timestep,
        cell size and lower-left cell from ``_grid_geometry``, cell zero (0, 0),
        rows as given (row 0 of each ``grid_data[t]`` is stored as the southern row),
        HEC Monolith's D/E parts and ``is_interval`` true.
        """
        writes = HmsDssGrid._native_grid_writes(pathname, grid_data, windows)
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
                    **_backend.native_sync_kwargs(),
                )
        logger.info(f"DSS grid write complete (native): {target} ({len(writes)} grids)")
        return Path(dss_file)

    @staticmethod
    def _write_grid_timeseries_shadow(dss_file, pathname, grid_data, lat_coords,
                                      lon_coords, windows, units, data_type) -> Path:
        """Java write (its result and errors are returned); the native writer repeats
        it on a temporary copy and the native read-backs of every grid are compared."""
        args = (pathname, grid_data, lat_coords, lon_coords, windows, units, data_type)

        def native_call(copy, existed):
            HmsDssGrid._write_grid_timeseries_native(copy, *args)

        def compare(copy):
            dc = _backend.import_native()
            diffs = []
            for start, end in windows:
                path_t = HmsDssGrid._grid_pathname(pathname, start, end)
                java = dc.read_grid(str(Path(dss_file).resolve()), path_t, missing="raw")
                native = dc.read_grid(str(copy), path_t, missing="raw")
                diffs += [f"{path_t}:{d}" for d in HmsDssGrid._compare_written(java, native)]
            return diffs

        return DssCore._shadow_write(
            "write_grid_timeseries", dss_file, pathname,
            lambda: HmsDssGrid._write_grid_timeseries_java(dss_file, *args),
            native_call, compare,
        )

    #: Target CRS names for the warped route, and the default SHG cell size (metres).
    WARP_TARGETS = ("SHG",)
    SHG_CELL_SIZE = 2000.0
    _RESAMPLE_METHODS = ("bilinear", "average", "near")

    @staticmethod
    def _lattice_transform(coords, name: str):
        """``(origin, spacing)`` of a uniform 1-D lattice of cell centres; the origin is
        the outer edge of the first cell. A lattice that is not uniform is refused."""
        import numpy as np

        c = np.asarray(coords, dtype=np.float64)
        if c.ndim != 1 or len(c) < 2:
            raise ValueError(f"{name} needs at least two cell centres to define a spacing")
        steps = np.diff(c)
        step = (c[-1] - c[0]) / (len(c) - 1)
        if step == 0 or not np.all(np.isfinite(steps)) or \
                np.max(np.abs(steps - step)) > 1e-3 * abs(step):
            raise ValueError(f"{name} must be evenly spaced and monotonic to be warped")
        return float(c[0] - step / 2.0), float(step)

    @staticmethod
    def _write_grid_timeseries_warped(dss_file, pathname, grid_data, lat_coords, lon_coords,
                                      windows, units, data_type, *, target_crs, cell_size,
                                      resample_method, envelope) -> Path:
        """``write_grid_timeseries`` warped to ``target_crs`` by the engine's gridded importer.

        The WGS 84 cells go to ``gridded.import_arrays`` with their cell-edge transform
        and the same period windows as the WGS 84 route. The A, B, C and F parts come
        from ``pathname``; D and E from each window. ``units`` labels the cells, as on the
        WGS 84 route. Everything is checked before the engine is called, and the engine
        plans the whole run before it writes, so a refusal leaves the output untouched.
        """
        import numpy as np

        crs = str(target_crs).strip().upper()
        if crs not in HmsDssGrid.WARP_TARGETS:
            raise ValueError(
                f"target_crs must be one of {HmsDssGrid.WARP_TARGETS} or None, not {target_crs!r}")
        method = str(resample_method).strip().lower()
        if method not in HmsDssGrid._RESAMPLE_METHODS:
            raise ValueError(
                f"resample_method must be one of {HmsDssGrid._RESAMPLE_METHODS}, not "
                f"{resample_method!r}")
        size = HmsDssGrid.SHG_CELL_SIZE if cell_size is None else float(cell_size)
        if not np.isfinite(size) or size <= 0:
            raise ValueError(f"cell_size must be a positive number of metres, not {cell_size!r}")
        parts = pathname.split("/")
        if len(parts) != 8 or parts[0] or parts[7]:
            raise ValueError(
                f"DSS pathname must have exactly six parts (/A/B/C/D/E/F/); got {pathname!r}")
        if not parts[3].strip():
            raise ValueError(f"pathname {pathname!r} needs a C part (for example PRECIP)")
        x0, dx = HmsDssGrid._lattice_transform(lon_coords, "lon_coords")
        y0, dy = HmsDssGrid._lattice_transform(lat_coords, "lat_coords")
        _, nlat, nlon = grid_data.shape
        if envelope is None:
            x1, y1 = x0 + nlon * dx, y0 + nlat * dy
            box = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
            box_crs = HmsDssGrid.WKT_WGS84
        else:
            box = tuple(float(v) for v in envelope)
            if len(box) != 4:
                raise ValueError("envelope must be (min_x, min_y, max_x, max_y) in metres")
            box_crs = crs

        gridded = _backend.require_native_gridded_import()
        backend = DssCore.get_backend()
        if backend != "native":
            logger.info("target_crs=%r: the grid is warped and written by the native engine "
                        "(there is no Java route); HmsDss.backend=%r does not apply", crs, backend)
        times = [(start.to_pydatetime(), end.to_pydatetime()) for start, end in windows]
        result = gridded.import_arrays(
            grid_data,
            str(Path(dss_file)),
            times=times,
            transform=(x0, dx, y0, dy),
            crs=HmsDssGrid.WKT_WGS84,
            variable=parts[3],
            source_units=units,
            envelope=box,
            envelope_crs=box_crs,
            target_crs=crs,
            cell_size=size,
            method=method,
            parts={"A": parts[1], "B": parts[2], "C": parts[3], "F": parts[6]},
            units=units,
            data_type=str(data_type).upper(),
            **_backend.native_sync_kwargs(),
        )
        first = result.records[0] if result.records else {}
        logger.info(
            "DSS grid write complete (native, %s %g m, %s): %s (%d grids, %s x %s cells, "
            "lower-left cell (%s, %s))", crs, size, method, dss_file, len(result.records),
            first.get("nx"), first.get("ny"), first.get("lower_left_cell_x"),
            first.get("lower_left_cell_y"))
        return Path(dss_file)

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

    # ------------------------------------------------------------------
    # Engine tools: gridded import and grid processing
    # (ras-commander-fast-dss on every backend)
    # ------------------------------------------------------------------

    @staticmethod
    def _engine_tool(tool: str, /, *args: Any, sync: Any = None, **kwargs: Any) -> Any:
        # ``tool`` is positional-only: the engine's own keywords, such as the resampling
        # ``method=`` of import_gridded, import_arrays and calculate_raster, must reach
        # the engine unchanged.
        function = _backend.require_gridded(tool)
        kwargs.update(_backend.engine_sync_kwargs(function, sync, f"gridded.{tool}"))
        return function(*args, **kwargs)

    @staticmethod
    @log_call
    def get_features() -> Dict[str, bool]:
        """Report which gridded feature groups the installed engine provides.

        Does not raise when ras-commander-fast-dss is missing (every value is False).

        Returns:
            ``dict`` of engine feature name to ``bool``: ``gridded_import``,
            ``gridded_netcdf``, ``gridded_zarr``, ``gridded_accumulation_window``,
            ``gridded_time_tools``, ``grid_tools`` and ``grid_to_point``.
        """
        names = sorted(set(_backend.GRIDDED_FEATURES.values())
                       | {"gridded_netcdf", "gridded_accumulation_window"})
        features = _backend.engine_features()
        return {name: name in features for name in names}

    # ------------------------------------------------------------------ import

    @staticmethod
    @log_call
    def import_gridded(
        inputs: Union[PathLike, Sequence[PathLike]],
        output: PathLike,
        *,
        sync: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Import grids from files into a DSS file, one frame at a time.

        Args:
            inputs: One path or a sequence, read in the order given: GRIB2, NetCDF
                (classic and NetCDF-4), HDF5, GeoTIFF, ASCII grid, or the folder of
                a local Zarr v2 store.
            output: DSS file to write. It is created when the first record is written.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: Options of ``ras_commander_fast_dss.gridded.import_gridded``,
                passed unchanged: ``variable``, ``product``, ``envelope``,
                ``envelope_crs``, ``shapefile``, ``target_crs`` (default ``"SHG"``),
                ``cell_size`` (metres, default 2000), ``method``, ``parts``,
                ``units`` (relabels; it does not convert), ``data_type``,
                ``version``, ``align``, ``window_rule``, ``duplicates``,
                ``threads``, ``progress``, ``bbox``, ``times`` and the reader limits.

        Returns:
            The engine's ``ImportResult`` (``output``, ``records``, ``pathnames``).

        Raises:
            ImportError: ras-commander-fast-dss is not installed.
            DssCapabilityError: The installed engine has no ``gridded_import``.
            ValueError: The engine refuses the run (nothing is written).
        """
        return HmsDssGrid._engine_tool("import_gridded", _abs_many(inputs), _abs(output),
                                sync=sync, **kwargs)

    @staticmethod
    @log_call
    def import_arrays(
        data: Any,
        output: PathLike,
        *,
        times: Sequence[Any],
        transform: Sequence[float],
        crs: str,
        variable: str,
        source_units: str,
        sync: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Import arrays through the same warp, unit, naming and writer steps as a file.

        Args:
            data: Shape ``(frames, rows, columns)``, or ``(rows, columns)``.
            output: DSS file to write.
            times: One per frame: ``None``, an instant, or ``(start, end)``.
            transform: ``(origin_x, dx, origin_y, dy)``; the origin is the outer
                corner of the first cell, and negative ``dy`` means row 0 is north.
            crs: ``"SHG"``, ``"HRAP"`` or WKT of the arrays.
            variable: Variable name; it sets the C part.
            source_units: Units the cells are in.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: Other ``ras_commander_fast_dss.gridded.import_arrays`` options.

        Returns:
            The engine's ``ImportResult``.

        Raises:
            ImportError: ras-commander-fast-dss is not installed.
            DssCapabilityError: The installed engine has no ``gridded_import``.
        """
        return HmsDssGrid._engine_tool(
            "import_arrays", data, _abs(output), times=times, transform=transform,
            crs=crs, variable=variable, source_units=source_units, sync=sync, **kwargs,
        )

    @staticmethod
    @log_call
    def import_zarr(
        inputs: Union[PathLike, Sequence[PathLike]],
        output: PathLike,
        *,
        variable: str,
        sync: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Import a variable of local Zarr v2 stores (for example AORC v1.1) into DSS.

        Args:
            inputs: One store folder or a sequence of them.
            output: DSS file to write.
            variable: Variable name (see ``zarr_variables``).
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: Other ``ras_commander_fast_dss.gridded.import_zarr`` options
                (``bbox``, ``times``, ``envelope``, ``target_crs``, ``cell_size``,
                ``parts``, ``window_rule``, ``limits``, ``stop``, ``strict``, ...).

        Returns:
            The engine's ``ImportResult``.

        Raises:
            ImportError: ras-commander-fast-dss is not installed.
            DssCapabilityError: The installed engine has no ``gridded_zarr``.
        """
        return HmsDssGrid._engine_tool("import_zarr", _abs_many(inputs), _abs(output),
                                variable=variable, sync=sync, **kwargs)

    @staticmethod
    @log_call
    def list_variables(path: PathLike) -> List[str]:
        """Variables a source file offers, by the names ``variable=`` takes.

        Args:
            path: A GRIB2, NetCDF, HDF5, GeoTIFF or ASCII grid file (not a DSS file).
                Only metadata is read.

        Returns:
            List of variable names.
        """
        return HmsDssGrid._engine_tool("list_variables", _abs(path))

    @staticmethod
    @log_call
    def zarr_variables(path: PathLike) -> List[Dict[str, Any]]:
        """Variables of a local Zarr v2 store, one ``dict`` each.

        Args:
            path: The store's folder. Only metadata and axes are read.

        Returns:
            The engine's list of dicts (``name``, ``error``, ``steps``, ``ny``,
            ``nx``, ``units``, ``crs``, ``first_time``, ``last_time``, ...).
        """
        return HmsDssGrid._engine_tool("zarr_variables", _abs(path))

    @staticmethod
    @log_call
    def read_zarr(path: PathLike, variable: str, *, steps: Tuple[int, int], **kwargs: Any) -> Any:
        """Read steps of a Zarr variable on a window, writing nothing.

        Args:
            path: The store's folder.
            variable: Variable name.
            steps: ``(first, end)`` step indexes.
            **kwargs: ``bbox``, ``rows``, ``cols``, ``limits``, ``stop``, ``strict``.

        Returns:
            The engine's ``ZarrWindow`` (``cells``, ``transform``, ``crs``, ``times``).
        """
        return HmsDssGrid._engine_tool("read_zarr", _abs(path), variable, steps=steps, **kwargs)

    # ------------------------------------------------------------- grid tools

    @staticmethod
    @log_call
    def calculate(input: PathLike, output: PathLike, *, sync: Optional[Any] = None,
                  **kwargs: Any) -> Any:
        """Apply one operation by one constant to every valid cell of each grid.

        Args:
            input: Source grids (a DSS file or a gridded source file).
            output: DSS file to write.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: Exactly one of ``multiply``, ``divide``, ``add``, ``subtract``;
                and ``variables``, ``parts``, ``units``, ``data_type``, ``version``,
                ``align``. A, B and F are empty unless ``parts`` states them.

        Returns:
            The engine's ``ImportResult``.
        """
        return HmsDssGrid._engine_tool("calculate", _abs(input), _abs(output), sync=sync, **kwargs)

    @staticmethod
    @log_call
    def calculate_raster(input: PathLike, raster: PathLike, output: PathLike, *,
                         operation: str, sync: Optional[Any] = None, **kwargs: Any) -> Any:
        """Combine each grid, on the left, with a raster resampled to it.

        Args:
            input: Source grids.
            raster: The raster operand (GeoTIFF, ASCII grid or a DSS grid).
            output: DSS file to write.
            operation: ``multiply``, ``divide``, ``add`` or ``subtract``.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``method``, ``raster_variable``, ``variables``, ``parts``,
                ``units``, ``data_type``, ``version``, ``align``, ``static_raster``.

        Returns:
            The engine's ``ImportResult``.
        """
        return HmsDssGrid._engine_tool("calculate_raster", _abs(input), _abs(raster),
                                _abs(output), operation=operation, sync=sync, **kwargs)

    @staticmethod
    @log_call
    def sanitize(input: PathLike, output: PathLike, *, sync: Optional[Any] = None,
                 **kwargs: Any) -> Any:
        """Replace valid cells at or beyond thresholds.

        Args:
            input: Source grids.
            output: DSS file to write.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``minimum``, ``maximum`` (inclusive), ``minimum_replacement``,
                ``maximum_replacement`` (NaN, the default, makes the cell missing),
                ``variables``, ``parts``, ``units``, ``data_type``, ``version``, ``align``.

        Returns:
            The engine's ``ImportResult``.
        """
        return HmsDssGrid._engine_tool("sanitize", _abs(input), _abs(output), sync=sync, **kwargs)

    @staticmethod
    @log_call
    def clip(input: PathLike, output: PathLike, *, sync: Optional[Any] = None,
             **kwargs: Any) -> Any:
        """Clip grids to an envelope, by nearest neighbour, in their own CRS.

        Args:
            input: Source grids.
            output: DSS file to write.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``envelope=(min_x, min_y, max_x, max_y)`` with
                ``envelope_crs``, or ``shapefile`` (its features' combined extent;
                not a polygon mask); ``variables``, ``parts``, ``units``,
                ``data_type``, ``version``, ``align``.

        Returns:
            The engine's ``ImportResult``.
        """
        if kwargs.get("shapefile") is not None:
            kwargs["shapefile"] = _abs(kwargs["shapefile"])
        return HmsDssGrid._engine_tool("clip", _abs(input), _abs(output), sync=sync, **kwargs)

    @staticmethod
    @log_call
    def normalize(input: PathLike, normals: PathLike, output: PathLike, *, start: Any,
                  end: Any, interval: Any, sync: Optional[Any] = None, **kwargs: Any) -> Any:
        """Scale each interval's source grids so their total matches its normals.

        Args:
            input: Source grids.
            normals: Grids holding the totals to match.
            output: DSS file to write.
            start: Start of the first interval.
            end: End of the last interval.
            interval: A ``datetime.timedelta`` or a number of seconds.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``source_variables``, ``normals_variables``, ``parts``,
                ``units``, ``data_type``, ``version``, ``align``.

        Returns:
            The engine's ``NormalizeResult``. Check ``sources_left_out``,
            ``normals_left_out`` and ``cells_made_missing_by_normal``.
        """
        return HmsDssGrid._engine_tool(
            "normalize", _abs(input), _abs(normals), _abs(output),
            start=start, end=end, interval=interval, sync=sync, **kwargs,
        )

    # -------------------------------------------------------------- time tools

    @staticmethod
    @log_call
    def shift_times(input: PathLike, output: PathLike, *, sync: Optional[Any] = None,
                    **kwargs: Any) -> Any:
        """Move grid records in time. Cell values are kept.

        Args:
            input: DSS file holding the grids.
            output: DSS file to write.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``shift`` (a ``datetime.timedelta``), or ``shift_start`` and
                ``shift_end``; ``select``, ``parts``, ``units``, ``data_type``,
                ``version``, ``progress``. A source's A and B parts are not kept
                unless ``parts`` states them.

        Returns:
            The engine's ``TimeToolResult``.
        """
        return HmsDssGrid._engine_tool("shift_times", _abs(input), _abs(output), sync=sync, **kwargs)

    @staticmethod
    @log_call
    def resample_times(input: PathLike, output: PathLike, step_minutes: int, *,
                       sync: Optional[Any] = None, **kwargs: Any) -> Any:
        """Resample each grid series to a fixed time step.

        Args:
            input: DSS file holding the grids.
            output: DSS file to write.
            step_minutes: One of ``time_steps()``.
            sync: Flush policy, passed to the engine unchanged (see the class notes on ``sync``).
            **kwargs: ``rule`` (``"strict"`` or ``"vortex"``), ``select``, ``parts``,
                ``units``, ``data_type``, ``version``, ``progress``.

        Returns:
            The engine's ``TimeToolResult``. ``dropped_tail_seconds`` is time after
            the last whole window, which is not in the output.
        """
        return HmsDssGrid._engine_tool("resample_times", _abs(input), _abs(output),
                                step_minutes, sync=sync, **kwargs)

    @staticmethod
    @log_call
    def time_steps() -> List[int]:
        """The steps ``resample_times`` takes, in minutes.

        Returns:
            List of ``int`` minutes.
        """
        return HmsDssGrid._engine_tool("time_steps")

    @staticmethod
    @log_call
    def series_info(input: PathLike, pathname: str) -> Dict[str, Any]:
        """What a grid series states: records, start, end, data type, units and grid.

        Args:
            input: DSS file.
            pathname: Any record of the series.

        Returns:
            The engine's ``dict``.
        """
        return HmsDssGrid._engine_tool("series_info", _abs(input), pathname)

    @staticmethod
    @log_call
    def read_window(input: PathLike, pathname: str, start: Any, end: Optional[Any] = None,
                    **kwargs: Any) -> Any:
        """One window of a grid series, computed as ``resample_times`` computes it.

        Args:
            input: DSS file.
            pathname: Any record of the series.
            start: Window start.
            end: Window end; ``None`` asks for an instant.
            **kwargs: ``rule`` and ``missing`` (``"nan"`` or ``"raw"``).

        Returns:
            The engine's ``WindowGrid`` (``data`` is ``(ny, nx)``, rows south to north).
        """
        return HmsDssGrid._engine_tool("read_window", _abs(input), pathname, start, end, **kwargs)

    @staticmethod
    @log_call
    def read_nearest(input: PathLike, pathname: str, time: Any, **kwargs: Any) -> Any:
        """The grid record of a series nearest a time.

        Args:
            input: DSS file.
            pathname: Any record of the series.
            time: The time to look near.
            **kwargs: ``missing`` (``"nan"`` or ``"raw"``).

        Returns:
            The engine's ``WindowGrid``.
        """
        return HmsDssGrid._engine_tool("read_nearest", _abs(input), pathname, time, **kwargs)

    @staticmethod
    @log_call
    def read_min_max(input: PathLike, pathname: str, start: Any, end: Any,
                     **kwargs: Any) -> Tuple[Any, Any]:
        """The minimum and maximum grids of a series over a window.

        Args:
            input: DSS file.
            pathname: Any record of the series.
            start: Window start.
            end: Window end.
            **kwargs: ``missing`` (``"nan"`` or ``"raw"``).

        Returns:
            ``(minimum, maximum)``, two engine ``WindowGrid`` objects.
        """
        return HmsDssGrid._engine_tool("read_min_max", _abs(input), pathname, start, end, **kwargs)

    # ------------------------------------------------------------------ zonal

    @staticmethod
    @log_call
    def grid_to_point(grids: PathLike, zones: PathLike, zone_field: str, output: PathLike, *,
                      sync: Optional[Any] = None, **kwargs: Any) -> Any:
        """Zonal statistics of each grid, written as one time series per zone and statistic.

        Args:
            grids: A DSS file, GRIB2 file, GeoTIFF or ASCII grid.
            zones: A shapefile or GeoJSON file of zones.
            zone_field: The field that names each zone; it becomes the B part.
            output: DSS file to write the time series to.
            sync: Flush policy, passed to the engine unchanged (see the class notes on
                ``sync``). ras-commander-fast-dss 0.1.1 has no such option on this
                function: stating it with 0.1.1 raises ``DssCapabilityError``.
            **kwargs: ``statistics`` (default ``("average",)``), ``accumulate``,
                ``parts`` (A and F), ``variables``, ``zones_crs``, ``area_weighted``,
                ``compatibility``, ``version``, ``assume_no_datum_shift``,
                ``allow_in_place``.

        Returns:
            The engine's ``GridToPointResult`` (``records``, ``zones``, ``pathnames``).
        """
        return HmsDssGrid._engine_tool("grid_to_point", _abs(grids), _abs(zones), zone_field,
                                _abs(output), sync=sync, **kwargs)

    @staticmethod
    @log_call
    def zonal_statistics(grids: PathLike, zones: PathLike, zone_field: str, **kwargs: Any) -> Any:
        """The statistics of ``grid_to_point`` as a table, writing nothing.

        Args:
            grids: A DSS file, GRIB2 file, GeoTIFF or ASCII grid.
            zones: A shapefile or GeoJSON file of zones.
            zone_field: The field that names each zone.
            **kwargs: ``variables``, ``zones_crs``, ``area_weighted``,
                ``compatibility``, ``assume_no_datum_shift``, ``raw``.

        Returns:
            The engine's ``pandas.DataFrame``, one row per frame and zone, unchanged.
            Missing statistics are NaN unless ``raw=True``.
        """
        return HmsDssGrid._engine_tool("zonal_statistics", _abs(grids), _abs(zones),
                                zone_field, **kwargs)

    @staticmethod
    @log_call
    def zone_masks(grids: PathLike, zones: PathLike, zone_field: str, **kwargs: Any) -> Dict[str, Any]:
        """Each zone's flat cell indices on the source's last grid.

        Args:
            grids: A DSS file, GRIB2 file, GeoTIFF or ASCII grid.
            zones: A shapefile or GeoJSON file of zones.
            zone_field: The field that names each zone.
            **kwargs: ``variables``, ``zones_crs``, ``assume_no_datum_shift``.

        Returns:
            ``dict`` of zone name to a NumPy index array.
        """
        return HmsDssGrid._engine_tool("zone_masks", _abs(grids), _abs(zones), zone_field, **kwargs)

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
