"""
HmsAorc - AORC Precipitation Data Access for HMS Commander

Provides access to NOAA's Analysis of Record for Calibration (AORC) dataset
stored in Zarr format on AWS S3 for use in HEC-HMS gridded precipitation models.

The AORC dataset provides:
- Hourly precipitation data at ~800m resolution
- Coverage: CONUS (1979-present), Alaska (1981-present)
- Format: Cloud-optimized Zarr on AWS S3

Classes:
    HmsAorc: Static class for AORC data operations

Key Functions:
    download: Download AORC precipitation data for specified bounds and time range
    get_storm_catalog: Analyze AORC data and generate catalog of storm events
    check_availability: Check if AORC data is available for region and time period
    get_info: Get metadata about the AORC dataset
    convert_to_dss_grid: Convert AORC NetCDF to DSS grid format for HMS

Dependencies:
    Required:
        - xarray: NetCDF/Zarr handling
        - zarr: Cloud-optimized array storage
        - s3fs: AWS S3 filesystem access
        - netCDF4: NetCDF I/O
        - pandas: Time series handling
        - numpy: Numerical operations

    Optional:
        - ras-commander: For DSS grid conversion (RasDss)

    Install with:
        pip install hms-commander[aorc]
        # OR
        pip install xarray zarr s3fs netCDF4

Example:
    >>> from hms_commander import HmsAorc
    >>>
    >>> # Download AORC precipitation
    >>> output = HmsAorc.download(
    ...     bounds=(-77.71, 41.01, -77.25, 41.22),
    ...     start_time="2020-05-01",
    ...     end_time="2020-05-15",
    ...     output_path="precip/aorc_may2020.nc"
    ... )
    >>>
    >>> # Generate storm catalog
    >>> catalog = HmsAorc.get_storm_catalog(
    ...     bounds=(-77.71, 41.01, -77.25, 41.22),
    ...     year=2020
    ... )

Notes:
    - All methods are static (no instantiation required)
    - Data remains in WGS84 (lat/lon) for HMS compatibility
    - No reprojection (unlike ras-commander which uses SHG)
"""

from pathlib import Path
from typing import Tuple, Optional, Union, List
from datetime import datetime
import logging

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)


def _check_aorc_dependencies():
    """Check that AORC dependencies are installed."""
    missing = []
    try:
        import xarray
    except ImportError:
        missing.append("xarray")
    try:
        import zarr
    except ImportError:
        missing.append("zarr")
    try:
        import s3fs
    except ImportError:
        missing.append("s3fs")
    try:
        import netCDF4
    except ImportError:
        missing.append("netCDF4")

    if missing:
        raise ImportError(
            f"Missing AORC dependencies: {', '.join(missing)}. "
            "Install with: pip install hms-commander[aorc] "
            "or: pip install xarray zarr s3fs netCDF4"
        )


class HmsAorc:
    """
    Static class for AORC precipitation data access.

    Provides methods for downloading AORC data from AWS S3, generating storm
    catalogs, and converting to HMS-compatible formats.

    All methods are static - do not instantiate this class.

    Example:
        >>> from hms_commander import HmsAorc
        >>>
        >>> # Download AORC data
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> nc_file = HmsAorc.download(bounds, "2020-05-01", "2020-05-15", "aorc.nc")
        >>>
        >>> # Generate storm catalog
        >>> storms = HmsAorc.get_storm_catalog(bounds, year=2020)
    """

    # AWS S3 bucket configuration
    BUCKET = "noaa-nws-aorc-v1-1-1km"
    REGION = "us-east-1"

    # AORC variable names
    PRECIP_VAR = "APCP_surface"  # Hourly total precipitation (kg/m²)

    # CONUS bounding box (approximate)
    CONUS_BOUNDS = (-125.0, 25.0, -67.0, 53.0)  # west, south, east, north

    @staticmethod
    @log_call
    def download(
        bounds: Tuple[float, float, float, float],
        start_time: Union[str, datetime],
        end_time: Union[str, datetime],
        output_path: Union[str, Path],
        variable: str = "APCP_surface"
    ) -> Path:
        """
        Download AORC precipitation data for specified bounds and time range.

        Downloads data from AWS S3 Zarr store, subsets spatially and temporally,
        and exports to NetCDF format. Data remains in WGS84 (lat/lon) for HMS.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box in WGS84 as (west, south, east, north) in decimal degrees.
        start_time : str or datetime
            Start of time window. String format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM"
        end_time : str or datetime
            End of time window. Same format as start_time.
        output_path : str or Path
            Output NetCDF file path. Will be created if it doesn't exist.
        variable : str, default "APCP_surface"
            AORC variable name. Default is hourly precipitation (kg/m²).

        Returns
        -------
        Path
            Path to the output NetCDF file.

        Raises
        ------
        ImportError
            If required dependencies (xarray, zarr, s3fs) are not installed.
        ValueError
            If bounds are outside CONUS coverage or time range is invalid.

        Examples
        --------
        >>> from hms_commander import HmsAorc
        >>>
        >>> # Download AORC precipitation
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> output = HmsAorc.download(
        ...     bounds=bounds,
        ...     start_time="2020-05-01",
        ...     end_time="2020-05-15",
        ...     output_path="precip/aorc_may2020.nc"
        ... )

        Notes
        -----
        - Data is downloaded from AWS S3 (no authentication required)
        - Download time depends on spatial extent and time range
        - Data remains in WGS84 (lat/lon) - no reprojection
        - AORC resolution: ~800m, hourly timesteps
        - Units: kg/m² (equivalent to mm of precipitation)
        """
        _check_aorc_dependencies()

        import xarray as xr
        import s3fs
        import pandas as pd
        import numpy as np

        output_path = Path(output_path)

        # Parse time inputs
        if isinstance(start_time, str):
            start_dt = pd.to_datetime(start_time)
        else:
            start_dt = pd.Timestamp(start_time)

        if isinstance(end_time, str):
            end_dt = pd.to_datetime(end_time)
        else:
            end_dt = pd.Timestamp(end_time)

        # Extract bounds
        west, south, east, north = bounds

        # Validate bounds
        if west >= east or south >= north:
            raise ValueError(f"Invalid bounds: west must < east and south must < north. Got: {bounds}")

        # Check if within CONUS
        conus_west, conus_south, conus_east, conus_north = HmsAorc.CONUS_BOUNDS
        if west < conus_west or east > conus_east or south < conus_south or north > conus_north:
            logger.warning(f"Bounds {bounds} may extend outside CONUS coverage {HmsAorc.CONUS_BOUNDS}")

        logger.info(f"Downloading AORC data:")
        logger.info(f"  Bounds: W={west:.4f}, S={south:.4f}, E={east:.4f}, N={north:.4f}")
        logger.info(f"  Time range: {start_dt} to {end_dt}")
        logger.info(f"  Variable: {variable}")

        # Connect to S3 (anonymous access)
        logger.info("Connecting to AWS S3...")
        s3 = s3fs.S3FileSystem(anon=True)

        # Build Zarr store paths for each year in range
        years = range(start_dt.year, end_dt.year + 1)
        datasets = []

        for year in years:
            store_path = f"s3://{HmsAorc.BUCKET}/{year}.zarr"
            logger.info(f"  Loading year {year} from {store_path}")

            try:
                store = s3fs.S3Map(root=store_path, s3=s3)
                ds = xr.open_zarr(store)

                # AORC uses latitude/longitude naming
                lat_dim = 'latitude' if 'latitude' in ds.dims else 'lat'
                lon_dim = 'longitude' if 'longitude' in ds.dims else 'lon'

                # Get the actual dimension names from the variable
                if variable in ds:
                    var_dims = ds[variable].dims
                    lat_candidates = [d for d in var_dims if 'lat' in d.lower()]
                    lon_candidates = [d for d in var_dims if 'lon' in d.lower()]
                    if lat_candidates:
                        lat_dim = lat_candidates[0]
                    if lon_candidates:
                        lon_dim = lon_candidates[0]

                # Subset the variable
                ds_var = ds[variable]

                # Check coordinate ordering for latitude
                lat_coords = ds_var[lat_dim].values
                if lat_coords[0] > lat_coords[-1]:
                    # Latitude is descending (north to south)
                    ds_subset = ds_var.sel(
                        **{lat_dim: slice(north, south)},
                        **{lon_dim: slice(west, east)}
                    )
                else:
                    # Latitude is ascending (south to north)
                    ds_subset = ds_var.sel(
                        **{lat_dim: slice(south, north)},
                        **{lon_dim: slice(west, east)}
                    )

                # Subset temporally - use date-only strings for proper inclusive slicing
                year_start = max(start_dt, pd.Timestamp(f"{year}-01-01"))
                year_end = min(end_dt, pd.Timestamp(f"{year}-12-31 23:59:59"))
                # Use date format YYYY-MM-DD for proper inclusive time slicing
                start_str = year_start.strftime('%Y-%m-%d')
                end_str = year_end.strftime('%Y-%m-%d')
                ds_subset = ds_subset.sel(time=slice(start_str, end_str))

                if ds_subset.size > 0:
                    # Load data from S3 now (force lazy evaluation)
                    ds_subset = ds_subset.load()
                    datasets.append(ds_subset)
                    logger.info(f"    Loaded {ds_subset.sizes}")
                else:
                    logger.warning(f"    No data found for year {year}")

            except Exception as e:
                logger.error(f"Error loading year {year}: {e}")
                raise

        if not datasets:
            raise ValueError("No data found for the specified bounds and time range")

        # Combine all years
        logger.info("Combining datasets...")
        if len(datasets) == 1:
            combined = datasets[0]
        else:
            combined = xr.concat(datasets, dim='time')

        # Sort by time
        combined = combined.sortby('time')

        # Add metadata for HMS
        combined.attrs['title'] = 'AORC Precipitation Data'
        combined.attrs['source'] = f'NOAA NWS AORC v1.1 from s3://{HmsAorc.BUCKET}'
        combined.attrs['history'] = f'Downloaded by hms-commander on {datetime.now().isoformat()}'
        combined.attrs['units'] = 'kg/m^2'  # AORC precipitation units (equivalent to mm)
        combined.attrs['long_name'] = 'Hourly Total Precipitation'
        combined.attrs['crs'] = 'EPSG:4326'  # WGS84 lat/lon (no reprojection for HMS)

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to NetCDF
        logger.info(f"Writing to NetCDF: {output_path}")
        combined.to_netcdf(output_path)

        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Download complete: {output_path} ({file_size_mb:.1f} MB)")

        return output_path

    @staticmethod
    @log_call
    def get_storm_catalog(
        bounds: Tuple[float, float, float, float],
        year: int,
        inter_event_hours: float = 8.0,
        min_depth_inches: float = 0.5,
        min_wet_hours: int = 1,
        buffer_hours: int = 48,
        percentile_threshold: Optional[float] = None
    ) -> 'pd.DataFrame':
        """
        Analyze AORC data and generate catalog of storm events.

        Identifies discrete precipitation events using inter-event time analysis,
        ranks them by total depth, and returns timing information for HMS setup.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box in WGS84 as (west, south, east, north) in decimal degrees.
        year : int
            Year to analyze (1979+).
        inter_event_hours : float, default 8.0
            Minimum hours of no precipitation between storm events (USGS standard).
        min_depth_inches : float, default 0.5
            Minimum total precipitation depth (inches) to include event.
        min_wet_hours : int, default 1
            Minimum hours with measurable precipitation during event.
        buffer_hours : int, default 48
            Hours to add before and after event for simulation warm-up.
        percentile_threshold : float, optional
            If specified (0-100), only return storms above this percentile
            by total depth. E.g., 95 returns only top 5% storms.

        Returns
        -------
        pd.DataFrame
            Storm catalog with columns:
            - storm_id: Sequential storm identifier (1-based)
            - start_time: Event start (first hour with precipitation)
            - end_time: Event end (last hour with precipitation)
            - sim_start: Recommended simulation start (start - buffer)
            - sim_end: Recommended simulation end (end + buffer)
            - total_depth_in: Total event precipitation (inches, spatial mean)
            - peak_intensity_in_hr: Maximum hourly rate (inches/hour)
            - duration_hours: Event duration (hours)
            - wet_hours: Hours with measurable precipitation
            - rank: Rank by total depth (1 = largest)

        Examples
        --------
        >>> from hms_commander import HmsAorc
        >>>
        >>> # Get all significant storms from 2020
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> storms = HmsAorc.get_storm_catalog(bounds, 2020)
        >>> print(f"Found {len(storms)} storms")
        >>>
        >>> # Get only top 5% storms
        >>> major_storms = HmsAorc.get_storm_catalog(
        ...     bounds, 2020, percentile_threshold=95
        ... )

        Notes
        -----
        - Uses spatial mean precipitation over the bounding box
        - AORC precipitation units are kg/m² which equals mm depth
        - Conversion: 1 inch = 25.4 mm
        - Inter-event period of 8 hours is USGS standard for storm separation
        - Buffer hours allow model spin-up and recession
        """
        _check_aorc_dependencies()

        import xarray as xr
        import s3fs
        import pandas as pd
        import numpy as np

        logger.info(f"Generating storm catalog for {year}")
        logger.info(f"  Bounds: W={bounds[0]:.4f}, S={bounds[1]:.4f}, E={bounds[2]:.4f}, N={bounds[3]:.4f}")
        logger.info(f"  Parameters: inter_event={inter_event_hours}h, min_depth={min_depth_inches}in, buffer={buffer_hours}h")

        west, south, east, north = bounds

        # Connect to S3
        logger.info("Connecting to AWS S3...")
        s3 = s3fs.S3FileSystem(anon=True)

        # Load year's data
        store_path = f"s3://{HmsAorc.BUCKET}/{year}.zarr"
        logger.info(f"Loading {store_path}...")

        try:
            store = s3fs.S3Map(root=store_path, s3=s3)
            ds = xr.open_zarr(store)

            # Get precipitation variable
            ds_var = ds[HmsAorc.PRECIP_VAR]

            # Determine dimension names
            lat_dim = 'latitude' if 'latitude' in ds.dims else 'lat'
            lon_dim = 'longitude' if 'longitude' in ds.dims else 'lon'

            # Check coordinate ordering
            lat_coords = ds_var[lat_dim].values
            if lat_coords[0] > lat_coords[-1]:
                # Latitude is descending (north to south)
                ds_subset = ds_var.sel(
                    **{lat_dim: slice(north, south)},
                    **{lon_dim: slice(west, east)}
                )
            else:
                # Latitude is ascending
                ds_subset = ds_var.sel(
                    **{lat_dim: slice(south, north)},
                    **{lon_dim: slice(west, east)}
                )

            logger.info(f"Loading spatial subset...")
            # Compute spatial mean for each timestep (lazy then load)
            precip_mean = ds_subset.mean(dim=[lat_dim, lon_dim])
            precip_mean = precip_mean.load()

            logger.info(f"Loaded {len(precip_mean)} hourly timesteps")

        except Exception as e:
            logger.error(f"Error loading AORC data: {e}")
            raise

        # Convert to pandas Series for easier manipulation
        precip_series = precip_mean.to_series()
        precip_series.name = 'precip_mm'

        # Convert mm to inches (AORC kg/m² = mm)
        precip_inches = precip_series / 25.4

        # Define threshold for "wet" hour (0.01 inches = trace)
        wet_threshold = 0.01
        is_wet = precip_inches > wet_threshold

        # Identify event boundaries using inter-event gap
        events = []
        event_start = None
        dry_count = 0

        for i, (timestamp, wet) in enumerate(is_wet.items()):
            if wet:
                if event_start is None:
                    event_start = timestamp
                dry_count = 0
            else:
                if event_start is not None:
                    dry_count += 1
                    if dry_count >= inter_event_hours:
                        # Event ended - find actual end (last wet hour)
                        event_end_idx = i - int(dry_count)
                        if event_end_idx >= 0:
                            event_end = is_wet.index[event_end_idx]
                            events.append((event_start, event_end))
                        event_start = None
                        dry_count = 0

        # Handle event still in progress at end of year
        if event_start is not None:
            last_wet_idx = is_wet[is_wet].index[-1] if is_wet.any() else None
            if last_wet_idx is not None and last_wet_idx >= event_start:
                events.append((event_start, last_wet_idx))

        logger.info(f"Identified {len(events)} raw events")

        # Analyze each event
        storm_records = []
        for start, end in events:
            # Get precipitation for this event
            event_precip = precip_inches[start:end]

            if len(event_precip) == 0:
                continue

            # Calculate event statistics
            total_depth = event_precip.sum()
            peak_intensity = event_precip.max()
            duration = (end - start).total_seconds() / 3600 + 1  # hours (inclusive)
            wet_hours_count = (event_precip > wet_threshold).sum()

            # Apply filters
            if total_depth < min_depth_inches:
                continue
            if wet_hours_count < min_wet_hours:
                continue

            # Calculate simulation window with buffer
            sim_start = start - pd.Timedelta(hours=buffer_hours)
            sim_end = end + pd.Timedelta(hours=buffer_hours)

            storm_records.append({
                'start_time': start,
                'end_time': end,
                'sim_start': sim_start,
                'sim_end': sim_end,
                'total_depth_in': round(total_depth, 3),
                'peak_intensity_in_hr': round(peak_intensity, 3),
                'duration_hours': int(duration),
                'wet_hours': int(wet_hours_count),
            })

        if not storm_records:
            logger.warning("No storms found matching criteria")
            import pandas as pd
            return pd.DataFrame(columns=[
                'storm_id', 'start_time', 'end_time', 'sim_start', 'sim_end',
                'total_depth_in', 'peak_intensity_in_hr', 'duration_hours',
                'wet_hours', 'rank'
            ])

        # Create DataFrame
        import pandas as pd
        df = pd.DataFrame(storm_records)

        # Apply percentile filter if specified
        if percentile_threshold is not None:
            threshold_value = np.percentile(df['total_depth_in'], percentile_threshold)
            df = df[df['total_depth_in'] >= threshold_value]
            logger.info(f"Filtered to {len(df)} storms above {percentile_threshold}th percentile ({threshold_value:.2f} in)")

        # Rank by total depth (1 = largest)
        df['rank'] = df['total_depth_in'].rank(ascending=False, method='min').astype(int)

        # Add storm ID (sorted by date)
        df = df.sort_values('start_time').reset_index(drop=True)
        df['storm_id'] = range(1, len(df) + 1)

        # Reorder columns
        df = df[['storm_id', 'start_time', 'end_time', 'sim_start', 'sim_end',
                 'total_depth_in', 'peak_intensity_in_hr', 'duration_hours',
                 'wet_hours', 'rank']]

        logger.info(f"Storm catalog complete: {len(df)} storms")
        if len(df) > 0:
            logger.info(f"  Total depth range: {df['total_depth_in'].min():.2f} - {df['total_depth_in'].max():.2f} inches")
            logger.info(f"  Largest storm: {df[df['rank']==1]['start_time'].iloc[0]} ({df['total_depth_in'].max():.2f} in)")

        return df

    @staticmethod
    @log_call
    def convert_to_dss_grid(
        netcdf_file: Union[str, Path],
        output_dss_file: Union[str, Path],
        pathname: str,
        units: str = "MM"
    ) -> Path:
        """
        Convert AORC NetCDF to DSS grid format for HMS.

        Uses HmsDssGrid to write DSS grids using HEC Monolith libraries,
        following the pattern from HEC-Vortex.

        Parameters
        ----------
        netcdf_file : str or Path
            Input NetCDF file (from download())
        output_dss_file : str or Path
            Output DSS file path
        pathname : str
            DSS pathname (e.g., "/AORC/GRID/PRECIP////")
        units : str, default "MM"
            Output units. AORC data is in kg/m^2 which equals mm.

        Returns
        -------
        Path
            Path to output DSS file

        Raises
        ------
        ImportError
            If required dependencies (xarray, ras-commander) not installed.
        FileNotFoundError
            If input NetCDF file does not exist.
        RuntimeError
            If DSS conversion fails.

        Examples
        --------
        >>> from hms_commander import HmsAorc
        >>>
        >>> # Download AORC data
        >>> nc_file = HmsAorc.download(bounds, "2020-05-01", "2020-05-15", "aorc.nc")
        >>>
        >>> # Convert to DSS grid
        >>> dss_file = HmsAorc.convert_to_dss_grid(
        ...     netcdf_file="aorc.nc",
        ...     output_dss_file="aorc.dss",
        ...     pathname="/AORC/MAY2020/PRECIP////"
        ... )
        >>>
        >>> # Use in HMS met model
        >>> HmsMet.set_gridded_precipitation("model.met", dss_file, pathname)

        Notes
        -----
        - Requires ras-commander for HEC Monolith and DSS operations
        - AORC precipitation is in kg/m^2 which equals mm depth
        - Data is written in WGS84 (lat/lon) coordinate system
        - Each hourly timestep is written as a separate DSS grid record
        - Implementation uses HEC Monolith classes (same as HEC-Vortex)

        See Also
        --------
        HmsDssGrid.write_grid_timeseries : Lower-level DSS grid writing
        HmsAorc.download : Download AORC data to NetCDF
        """
        _check_aorc_dependencies()

        import xarray as xr
        import pandas as pd
        import numpy as np

        from .HmsDssGrid import HmsDssGrid

        netcdf_file = Path(netcdf_file)
        output_dss_file = Path(output_dss_file)

        if not netcdf_file.exists():
            raise FileNotFoundError(f"NetCDF file not found: {netcdf_file}")

        logger.info(f"Converting AORC NetCDF to DSS grid:")
        logger.info(f"  Input: {netcdf_file}")
        logger.info(f"  Output: {output_dss_file}")
        logger.info(f"  Pathname: {pathname}")

        # Open NetCDF
        ds = xr.open_dataarray(netcdf_file)

        # Get coordinates
        # AORC uses 'latitude' and 'longitude' naming
        lat_dim = 'latitude' if 'latitude' in ds.dims else 'lat'
        lon_dim = 'longitude' if 'longitude' in ds.dims else 'lon'

        lat_coords = ds[lat_dim].values
        lon_coords = ds[lon_dim].values
        time_coords = ds['time'].values

        # Get grid data (time, lat, lon)
        grid_data = ds.values

        # Handle case where lat might be first (time, lat, lon expected)
        if grid_data.ndim == 3:
            # Already in (time, lat, lon) shape
            pass
        elif grid_data.ndim == 2:
            # Single timestep - add time dimension
            grid_data = grid_data[np.newaxis, :, :]
            time_coords = np.array([time_coords]) if time_coords.ndim == 0 else time_coords

        # Convert time to datetime list
        timestamps = pd.to_datetime(time_coords).to_pydatetime().tolist()

        logger.info(f"  Grid shape: {grid_data.shape} (time, lat, lon)")
        logger.info(f"  Time range: {timestamps[0]} to {timestamps[-1]}")
        logger.info(f"  Lat range: {lat_coords.min():.4f} to {lat_coords.max():.4f}")
        logger.info(f"  Lon range: {lon_coords.min():.4f} to {lon_coords.max():.4f}")

        # Write to DSS using HmsDssGrid
        result = HmsDssGrid.write_grid_timeseries(
            dss_file=output_dss_file,
            pathname=pathname,
            grid_data=grid_data,
            lat_coords=lat_coords,
            lon_coords=lon_coords,
            timestamps=timestamps,
            units=units,
            data_type="PER-CUM"  # Precipitation is period cumulative
        )

        logger.info(f"DSS conversion complete: {result}")
        return result

    @staticmethod
    def check_availability(
        bounds: Tuple[float, float, float, float],
        start_time: Union[str, datetime],
        end_time: Union[str, datetime]
    ) -> dict:
        """
        Check if AORC data is available for specified region and time.

        Parameters
        ----------
        bounds : Tuple[float, float, float, float]
            Bounding box as (west, south, east, north)
        start_time : str or datetime
            Start of time window
        end_time : str or datetime
            End of time window

        Returns
        -------
        dict
            Availability information:
            - available: bool
            - in_conus: bool
            - years: list of available years
            - message: str with details

        Examples
        --------
        >>> from hms_commander import HmsAorc
        >>>
        >>> # Check data availability
        >>> bounds = (-77.71, 41.01, -77.25, 41.22)
        >>> avail = HmsAorc.check_availability(bounds, "2020-01-01", "2020-12-31")
        >>> print(avail['message'])
        """
        raise NotImplementedError(
            "HmsAorc.check_availability() not yet implemented.\n"
            "This will check AORC data coverage.\n"
            "Implementation coming in Phase 2 (Core Automation)."
        )

    @staticmethod
    def get_info() -> dict:
        """
        Get metadata about the AORC dataset.

        Returns
        -------
        dict
            Dataset information including:
            - name: Dataset name
            - source: AWS S3 bucket path
            - coverage: Spatial and temporal coverage
            - resolution: Spatial and temporal resolution
            - variables: Available variables

        Examples
        --------
        >>> from hms_commander import HmsAorc
        >>>
        >>> info = HmsAorc.get_info()
        >>> print(info['resolution']['spatial'])
        '30 arc-seconds (~800 meters)'
        """
        return {
            'name': 'Analysis of Record for Calibration (AORC)',
            'version': '1.1',
            'source': f's3://{HmsAorc.BUCKET}/',
            'coverage': {
                'spatial': 'Continental US (CONUS) and Alaska',
                'temporal': 'CONUS: 1979-present, Alaska: 1981-present',
                'bounds': HmsAorc.CONUS_BOUNDS,
            },
            'resolution': {
                'spatial': '30 arc-seconds (~800 meters)',
                'temporal': 'Hourly',
            },
            'variables': {
                'APCP_surface': 'Hourly total precipitation (kg/m²)',
                'TMP_2maboveground': 'Air temperature at 2m (K)',
                'SPFH_2maboveground': 'Specific humidity at 2m (g/g)',
                'DLWRF_surface': 'Downward longwave radiation (W/m²)',
                'DSWRF_surface': 'Downward shortwave radiation (W/m²)',
                'PRES_surface': 'Surface air pressure (Pa)',
                'UGRD_10maboveground': 'West-east wind at 10m (m/s)',
                'VGRD_10maboveground': 'South-north wind at 10m (m/s)',
            },
            'format': 'Zarr (cloud-optimized)',
            'access': 'Anonymous (no authentication required)',
        }
