"""
Core DSS File Operations for hms-commander

Provides static methods for interacting with HEC-DSS files (versions 6 and 7),
enabling reading of time series, extracting catalogs, and fetching file metadata.
Uses HEC Monolith libraries accessed via pyjnius.

JVM setup and dependency downloads are handled automatically at runtime.

Lazy Loading:
    This module implements lazy loading for all heavy dependencies:
    - pyjnius: Only imported when DSS methods are actually called
    - jnius_config: Only imported during JVM configuration
    - HecMonolithDownloader: Only imported when ensuring monolith installation
    - Java classes: Only loaded after JVM is configured

    This ensures that importing HmsDss has minimal overhead and users who don't
    use DSS functionality don't pay the cost of loading Java/pyjnius.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union, Any
import logging
import re
import time
from contextlib import contextmanager

# Lazy imports - these are always needed for type hints and basic operations
import pandas as pd
import numpy as np

from . import _backend
from .catalog import create_pathname, filter_catalog, parse_pathname

logger = logging.getLogger(__name__)

# HEC time epoch: TimeSeriesContainer times count from December 31, 1899 00:00.
_HEC_EPOCH = pd.Timestamp('1899-12-31 00:00:00')

# HEC missing-value markers. -901 and -902 are the classic heclib markers;
# HEC Monolith reports undefined values as -Float.MAX_VALUE (about -3.4028e38).
_HEC_MISSING_MARKERS = (-901.0, -902.0)
_HEC_UNDEFINED_THRESHOLD = -3.4e38
# HEC's DSS7 missing value as a double (-Float.MAX_VALUE widened).
_HEC_UNDEFINED_DOUBLE = float(-np.finfo(np.float32).max)
# Last stamp a datetime64[ns] index can hold (pattern records sit in year 3000).
_NS_MAX = np.datetime64(pd.Timestamp.max.floor('s').to_datetime64(), 's')
# HEC Monolith grid-info classes and the grid_type names read_grid reports.
_GRID_TYPE_NAMES = {'AlbersInfo': 'albers', 'SpecifiedGridInfo': 'specified', 'HrapInfo': 'hrap'}


class DssCore:
    """
    Core static class for DSS file operations.

    Uses HEC Monolith libraries (auto-downloaded on first use).
    Supports both DSS V6 and V7 formats.

    All heavy dependencies (pyjnius, Java) are lazy-loaded on first use.

    Usage:
        from hms_commander.dss import DssCore

        # Read time series
        df = DssCore.read_timeseries("file.dss", "/BASIN/LOC/FLOW//1HOUR/OBS/")

        # Get catalog
        paths = DssCore.get_catalog("file.dss")
    """

    _jvm_configured = False
    _monolith = None

    @staticmethod
    def _to_1d_array(values) -> np.ndarray:
        """Convert Java arrays or scalar values returned by pyjnius to 1-D arrays."""
        if values is None:
            return np.asarray([])

        try:
            array = np.asarray(list(values))
        except TypeError:
            array = np.asarray(values)

        if array.ndim == 0:
            array = array.reshape(1)

        return array.ravel()

    @staticmethod
    def _tsc_granularity_seconds(tsc) -> int:
        """Seconds per unit of ``TimeSeriesContainer.times`` (60 when not reported)."""
        getter = getattr(tsc, 'getTimeGranularitySeconds', None)
        try:
            value = int(getter()) if getter is not None else 60
        except Exception:
            value = 60
        return value if value > 0 else 60

    @staticmethod
    def _tsc_julian_base_date(tsc) -> int:
        """Days from the HEC epoch to the container's time base (0 when absent)."""
        try:
            return int(getattr(tsc, 'julianBaseDate', 0) or 0)
        except Exception:
            return 0

    @staticmethod
    def _tsc_interval_minutes(tsc, granularity: int) -> Optional[Union[int, float]]:
        """Regular interval in minutes; 0 for irregular data; float below one minute.

        ``TimeSeriesContainer.interval`` is counted in the container's time
        granularity, so a 15-second series reports 15 with granularity 1.
        """
        if not hasattr(tsc, 'interval'):
            return None
        seconds = int(tsc.interval) * int(granularity)
        if seconds % 60 == 0:
            return seconds // 60
        return seconds / 60

    @staticmethod
    def _hec_times_to_datetimes(
        times,
        granularity_seconds: int = 60,
        julian_base_date: int = 0,
    ) -> pd.DatetimeIndex:
        """Convert ``TimeSeriesContainer.times`` to a DatetimeIndex.

        HEC stores each time as a count of ``granularity_seconds`` (60 for
        minutes, 1 for seconds) after ``julian_base_date`` days past the HEC
        epoch (December 31, 1899 00:00). Containers that report minutes from the
        epoch use granularity 60 and base 0.
        """
        counts = np.asarray(times, dtype=np.int64)
        seconds = (counts * np.int64(granularity_seconds)).astype('timedelta64[s]')
        base = np.datetime64('1899-12-31T00:00:00', 'ns') + np.timedelta64(
            int(julian_base_date), 'D'
        )
        return pd.DatetimeIndex(base + seconds.astype('timedelta64[ns]'))

    @staticmethod
    def _valid_value_mask(values) -> np.ndarray:
        """True where a value is finite and not an HEC missing marker."""
        values = np.asarray(values, dtype=np.float64)
        return (
            np.isfinite(values)
            & ~np.isin(values, _HEC_MISSING_MARKERS)
            & (values > _HEC_UNDEFINED_THRESHOLD)
        )

    @staticmethod
    def _check_pathname_format(pathname: str) -> None:
        """Raise ValueError unless ``pathname`` has exactly six parts (/A/B/C/D/E/F/).

        heclib does not reject a pathname with extra slashes. It stores the
        record under the first six parts and drops the rest without a warning.
        """
        if not isinstance(pathname, str):
            raise ValueError(f"DSS pathname must be a string, got {type(pathname).__name__}")
        if not (pathname.startswith('/') and pathname.endswith('/')) or pathname.count('/') != 7:
            raise ValueError(
                "DSS pathname must have exactly six parts (/A/B/C/D/E/F/, seven slashes); "
                f"got {pathname!r} with {pathname.count('/')} slashes"
            )

    @staticmethod
    def _missing_pathnames(catalog: List[str], pathnames: List[str]) -> List[str]:
        """Return the pathnames that do not appear in ``catalog`` (case-insensitive)."""
        stored = {str(path).upper() for path in catalog}
        return [path for path in pathnames if path.upper() not in stored]

    @staticmethod
    def _cataloged_pathnames(dss) -> List[str]:
        """List the pathnames of an open HecDss handle."""
        vector = dss.getCatalogedPathnames()
        return [str(vector.get(i)) for i in range(vector.size())]

    @staticmethod
    def _release_dss_file(dss_path: str) -> None:
        """Close HEC Monolith's shared native handle for ``dss_path``.

        ``HecDss.done()`` only lowers Monolith's file-cache reference count.
        The native file stays open, with its DSS lock words held, until a
        background timer closes it (or never, if the timer is disabled).
        ``HecDSSFileAccess.close(path, True)`` closes it now. ``dss_path``
        must be the exact string that was passed to open the file; callers
        open with ``str(Path(...).resolve())``, which on Windows also expands
        8.3 short names (a short name would leave a second handle open). Other
        ``HecDss`` objects on the same file reopen it on their next access.

        Failures are logged at DEBUG and never raised, so the release cannot
        mask an exception from the read or write it follows.
        """
        try:
            from jnius import autoclass

            autoclass('hec.heclib.dss.HecDSSFileAccess').close(dss_path, True)
        except Exception as exc:
            logger.debug("Could not release DSS file %s: %s", dss_path, exc)

    @staticmethod
    def _done_and_release(dss, dss_path: str) -> None:
        """Call ``dss.done()``, then release the native file in all cases."""
        try:
            dss.done()
        finally:
            DssCore._release_dss_file(dss_path)

    @staticmethod
    def _ensure_monolith():
        """Ensure HEC Monolith is downloaded and available."""
        if DssCore._monolith is not None:
            return DssCore._monolith

        # Lazy import from same subpackage
        from ._hec_monolith import HecMonolithDownloader

        DssCore._monolith = HecMonolithDownloader()

        if not DssCore._monolith.is_installed():
            print("\n" + "=" * 80)
            print("HEC Monolith libraries not found")
            print("Installing automatically (one-time download, ~20 MB)...")
            print("=" * 80)
            DssCore._monolith.install()

        return DssCore._monolith

    @staticmethod
    def _configure_jvm(max_memory: str = "4G"):
        """
        Configure Java VM for DSS operations with memory settings.

        Sets up JVM with HEC Monolith libraries and configures heap size
        for large DSS file operations.

        Args:
            max_memory: Maximum heap size (default: "4G")
                       Examples: "512M", "2G", "4G", "8G", "16G"

        Memory recommendations:
            - < 1,000 DSS paths: "2G"
            - 1,000-10,000 paths: "4G" (default)
            - 10,000-50,000 paths: "8G"
            - > 50,000 paths: "16G"

        Note: JVM options must be set BEFORE first jnius import.
              If JVM already running, max_memory parameter is ignored.
        """
        if DssCore._jvm_configured:
            return

        # Ensure monolith is installed
        monolith = DssCore._ensure_monolith()

        # Lazy import pyjnius config
        try:
            import jnius_config
        except ImportError:
            raise ImportError(
                "pyjnius is required for DSS file operations.\n"
                "Install with: pip install pyjnius"
            )

        # Check if JVM already started - if so, we can't set memory options
        if jnius_config.vm_running:
            logger.warning(f"JVM already running, cannot set max_memory={max_memory}")
            DssCore._jvm_configured = True
            return

        # Configure JVM memory options BEFORE first jnius import
        # These must be set before the JVM starts
        jvm_args = [
            '-Xms512M',              # Initial heap: 512 MB
            f'-Xmx{max_memory}',     # Max heap: configurable
            '-XX:+UseG1GC',          # G1 garbage collector
            '-XX:MaxGCPauseMillis=200',  # Limit GC pause time
        ]
        jnius_config.add_options(*jvm_args)
        logger.info(f"Configured JVM with max memory: {max_memory}")

        # Get classpath and library path
        classpath = monolith.get_classpath()
        library_path = monolith.get_library_path()

        logger.info("Configuring Java VM for DSS operations")

        # Set JAVA_HOME if not already set
        if 'JAVA_HOME' not in os.environ:
            java_candidates = []

            # Check HMS-bundled JREs first (most reliable on Windows)
            if os.name == 'nt':
                for hms_dir in [Path("C:/Program Files/HEC/HEC-HMS"),
                                Path("C:/Program Files (x86)/HEC/HEC-HMS")]:
                    if hms_dir.exists():
                        # Sort versions descending to prefer newest
                        versions = sorted(hms_dir.iterdir(), reverse=True)
                        for v in versions:
                            jre = v / "jre"
                            if jre.exists() and (jre / "bin").exists():
                                java_candidates.append(jre)

            # Standard Java installations
            java_candidates.extend([
                Path("C:/Program Files/Java/jdk-21"),
                Path("C:/Program Files/Java/jdk-17"),
                Path("C:/Program Files/Java/jdk-11"),
                Path("/usr/lib/jvm/java-17-openjdk"),
                Path("/usr/lib/jvm/java-11-openjdk"),
            ])

            # Also scan C:/Program Files/Java/ for any JRE/JDK
            java_base = Path("C:/Program Files/Java")
            if java_base.exists():
                for d in sorted(java_base.iterdir(), reverse=True):
                    if d.is_dir() and (d / "bin").exists():
                        java_candidates.append(d)

            for java_home in java_candidates:
                if java_home.exists():
                    os.environ['JAVA_HOME'] = str(java_home)
                    logger.info("Using Java runtime at %s", java_home)
                    break
            else:
                raise RuntimeError(
                    "Java not found. Please set JAVA_HOME environment variable "
                    "or install Java JDK/JRE.\n"
                    "Download from: https://www.oracle.com/java/technologies/downloads/"
                )

        # Set classpath (must be done before first import from jnius)
        jnius_config.add_classpath(*classpath)

        # Set library path for native libraries
        if 'LD_LIBRARY_PATH' in os.environ:
            os.environ['LD_LIBRARY_PATH'] = (
                library_path + ':' + os.environ['LD_LIBRARY_PATH']
            )
        else:
            os.environ['LD_LIBRARY_PATH'] = library_path

        # Windows: Add to PATH for native DLLs
        if os.name == 'nt':
            os.environ['PATH'] = (
                library_path + os.pathsep + os.environ.get('PATH', '')
            )

        DssCore._jvm_configured = True
        logger.info("Java VM configured for DSS operations")

    @staticmethod
    def is_available() -> bool:
        """
        Check if DSS functionality is available for the selected backend.

        The ``native`` backend needs the ``ras_commander_fast_dss`` engine and no
        Java; ``java`` and ``shadow`` need pyjnius (``shadow`` returns the Java
        result). An invalid backend name counts as unavailable.

        Returns:
            True if the selected backend can run
        """
        try:
            backend = _backend.requested_backend(DssCore._backend_attribute())
        except ValueError:
            return False
        if backend == "native":
            return _backend.native_available()
        return DssCore.java_available()

    @staticmethod
    def java_available() -> bool:
        """True if pyjnius can be imported (the Java backend's Python dependency)."""
        try:
            import jnius_config  # noqa: F401
            return True
        except ImportError:
            return False

    @staticmethod
    def _backend_attribute() -> Any:
        """``HmsDss.backend`` (the single class attribute that selects the backend)."""
        from .hms_dss import HmsDss

        return getattr(HmsDss, "backend", None)

    @staticmethod
    def get_backend() -> str:
        """
        DSS backend for the next call: ``"java"``, ``"native"`` or ``"shadow"``.

        The environment variable ``HMS_COMMANDER_DSS_BACKEND``, when set, overrides
        ``HmsDss.backend``. ``native`` without the ``ras_commander_fast_dss`` engine
        raises ``ImportError``; ``shadow`` without it runs Java only (one warning).

        Raises:
            ValueError: If the backend name is not one of the three
            ImportError: If ``native`` is requested and the engine is missing
        """
        return _backend.effective_backend(DssCore._backend_attribute())

    @staticmethod
    def _get_catalog_java(dss_file: Union[str, Path]) -> List[str]:
        """Catalog pathnames through HEC Monolith (Java backend)."""
        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass

        HecDss = autoclass('hec.heclib.dss.HecDss')

        dss_file = str(Path(dss_file).resolve())

        # Open DSS file
        dss = HecDss.open(dss_file)

        # Suppress DSS library verbose output (ZREAD/ZOPEN messages)
        # Note: DSS Fortran library writes directly to stdout and cannot be suppressed
        try:
            dss.setMessageLevel(0)  # 0 = quiet, 1 = errors only, 2 = warnings, 3 = verbose
        except Exception:
            pass  # Older DSS versions may not have this method

        try:
            # Get catalog (returns Java Vector of pathname strings)
            catalog_vector = dss.getCatalogedPathnames()

            # Convert Java Vector to Python list
            paths = []
            for i in range(catalog_vector.size()):
                paths.append(str(catalog_vector.get(i)))

            return paths

        finally:
            DssCore._done_and_release(dss, dss_file)

    @staticmethod
    def _read_timeseries_java(
        dss_file: Union[str, Path],
        pathname: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """``read_timeseries`` through HEC Monolith (Java backend)."""
        window_start = pd.Timestamp(start_date) if start_date is not None else None
        window_end = pd.Timestamp(end_date) if end_date is not None else None
        if window_start is not None and window_end is not None and window_start > window_end:
            raise ValueError(
                f"start_date ({window_start}) is after end_date ({window_end})"
            )

        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        TimeSeriesContainer = autoclass('hec.io.TimeSeriesContainer')

        dss_file = str(Path(dss_file).resolve())

        # Open DSS file
        dss = HecDss.open(dss_file)

        # Suppress DSS library verbose output (ZREAD/ZOPEN messages)
        # Note: DSS Fortran library writes directly to stdout and cannot be suppressed
        try:
            dss.setMessageLevel(0)  # 0 = quiet, 1 = errors only, 2 = warnings, 3 = verbose
        except Exception:
            pass  # Older DSS versions may not have this method

        try:
            # Read time series
            # True = ignore D-part (date) for wildcards
            container = dss.get(pathname, True)

            if container is None:
                raise ValueError(f"No data found for pathname: {pathname}")

            # Cast to TimeSeriesContainer to access fields
            tsc = cast('hec.io.TimeSeriesContainer', container)

            # Extract values and times from Java container
            # pyjnius automatically converts Java arrays to Python lists
            values = DssCore._to_1d_array(tsc.values)
            times = DssCore._to_1d_array(tsc.times)

            # Validate that we got data
            if values.size == 0 or times.size == 0:
                raise ValueError(f"No data found in time series for pathname: {pathname}")

            if values.size != times.size:
                raise ValueError(
                    f"Mismatched array lengths: {values.size} values, {times.size} times"
                )

            # Times are counts of the container's granularity after its base
            # date, not always minutes from the HEC epoch.
            granularity = DssCore._tsc_granularity_seconds(tsc)
            datetimes = DssCore._hec_times_to_datetimes(
                times, granularity, DssCore._tsc_julian_base_date(tsc)
            )

            # Create DataFrame with DatetimeIndex for time series operations
            df = pd.DataFrame({
                'value': values
            }, index=datetimes)

            if window_start is not None:
                df = df[df.index >= window_start]
            if window_end is not None:
                df = df[df.index <= window_end]

            # Also add datetime as a column for easier plotting
            # Users can do: ax.plot(df['datetime'], df['value'])
            # Or: df.plot(x='datetime', y='value')
            df.insert(0, 'datetime', df.index)

            # Add metadata as attributes
            df.attrs['pathname'] = pathname
            df.attrs['units'] = str(tsc.units) if tsc.units else ""
            df.attrs['type'] = str(tsc.type) if tsc.type else ""
            df.attrs['interval'] = DssCore._tsc_interval_minutes(tsc, granularity)
            df.attrs['dss_file'] = dss_file

            return df

        finally:
            DssCore._done_and_release(dss, dss_file)

    @staticmethod
    def _hec_time_to_datetime(
        hec_time: int,
        granularity_seconds: int = 60,
        julian_base_date: int = 0,
    ) -> 'pd.Timestamp':
        """
        Convert one HEC container time to a pandas Timestamp.

        Args:
            hec_time: Count of ``granularity_seconds`` after the base date
            granularity_seconds: Seconds per count (default 60, minutes)
            julian_base_date: Days from the HEC epoch (1899-12-31 00:00) to the
                base date (default 0)

        Returns:
            pandas Timestamp
        """
        return (
            _HEC_EPOCH
            + pd.Timedelta(days=int(julian_base_date))
            + pd.Timedelta(seconds=int(hec_time) * int(granularity_seconds))
        )

    @staticmethod
    def _get_peak_value_java(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """``get_peak_value`` through HEC Monolith (Java backend)."""
        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        TimeSeriesContainer = autoclass('hec.io.TimeSeriesContainer')

        dss_file = Path(dss_file)

        if not dss_file.exists():
            logger.warning(f"DSS file not found: {dss_file}")
            return None

        dss_file = str(dss_file.resolve())

        # Open DSS file
        dss = HecDss.open(dss_file)

        # Suppress DSS library verbose output (ZREAD messages)
        # Note: DSS Fortran library writes directly to stdout and cannot be suppressed
        try:
            dss.setMessageLevel(0)  # 0 = quiet, 1 = errors only, 2 = warnings, 3 = verbose
        except Exception:
            pass  # Older DSS versions may not have this method

        try:
            # Read time series
            # True = ignore D-part (date) for wildcards
            container = dss.get(pathname, True)

            if container is None:
                logger.warning(f"No data found for pathname: {pathname}")
                return None

            # Cast to TimeSeriesContainer to access fields
            tsc = cast('hec.io.TimeSeriesContainer', container)

            # Extract values and times from Java container directly to NumPy
            # pyjnius automatically converts Java arrays to Python lists
            values = DssCore._to_1d_array(tsc.values)
            times = DssCore._to_1d_array(tsc.times)

            # Validate that we got data
            if values.size == 0 or times.size == 0:
                logger.warning(f"No data found in time series for pathname: {pathname}")
                return None

            if values.size != times.size:
                logger.warning(
                    f"Mismatched array lengths: {values.size} values, {times.size} times"
                )
                return None

            # Exclude HEC missing markers (-901, -902, -Float.MAX) and NaN
            # before computing statistics.
            values = values.astype(np.float64)
            valid = DssCore._valid_value_mask(values)
            if not valid.any():
                logger.warning(f"Only missing values in time series for pathname: {pathname}")
                return None
            valid_values = values[valid]
            valid_times = times[valid]

            # Calculate statistics immediately in NumPy - no DataFrame overhead.
            # np.argmax returns the first maximum when values tie.
            peak_idx = int(np.argmax(valid_values))
            peak_value = float(valid_values[peak_idx])

            # Convert peak time with the container's base date and granularity
            peak_time = DssCore._hec_time_to_datetime(
                int(valid_times[peak_idx]),
                DssCore._tsc_granularity_seconds(tsc),
                DssCore._tsc_julian_base_date(tsc),
            )

            # Calculate additional statistics
            min_value = float(np.min(valid_values))
            mean_value = float(np.mean(valid_values))
            count = int(values.size)

            # Extract units from container
            units = str(tsc.units) if tsc.units else ""

            return {
                'peak_flow': peak_value,
                'peak_time': peak_time,
                'units': units,
                'count': count,
                'min_value': min_value,
                'mean_value': mean_value
            }

        except Exception as e:
            logger.error(f"Error reading DSS pathname {pathname}: {e}")
            return None

        finally:
            DssCore._done_and_release(dss, dss_file)

    @staticmethod
    def read_multiple_timeseries(
        dss_file: Union[str, Path],
        pathnames: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        Read multiple time series from DSS file.

        Args:
            dss_file: Path to DSS file
            pathnames: List of DSS pathnames

        Returns:
            Dictionary mapping pathnames to DataFrames (None on failure)

        Example:
            paths = ["/BASIN/LOC1/FLOW//1HOUR/OBS/", "/BASIN/LOC2/FLOW//1HOUR/OBS/"]
            data = DssCore.read_multiple_timeseries("file.dss", paths)
            for path, df in data.items():
                if df is not None:
                    print(f"{path}: {len(df)} points")
        """
        results = {}
        for pathname in pathnames:
            try:
                results[pathname] = DssCore.read_timeseries(dss_file, pathname)
            except Exception as e:
                logger.warning(f"Could not read {pathname}: {e}")
                results[pathname] = None

        return results

    @staticmethod
    def get_info(dss_file: Union[str, Path]) -> Dict[str, Any]:
        """
        Get summary information about DSS file.

        Args:
            dss_file: Path to DSS file

        Returns:
            Dictionary with file information

        Example:
            info = DssCore.get_info("sample.dss")
            print(f"Total paths: {info['total_paths']}")
            print(f"File size: {info['file_size_mb']:.2f} MB")
        """
        dss_path = Path(dss_file)

        if not dss_path.exists():
            return {
                'filepath': str(dss_path),
                'exists': False,
                'error': 'File not found'
            }

        catalog = DssCore.get_catalog(dss_file)

        # Categorize paths by C-part (data type)
        path_types = {}
        for path in catalog:
            parts = path.split('/')
            if len(parts) >= 4:
                data_type = parts[3]  # C part
                path_types[data_type] = path_types.get(data_type, 0) + 1

        return {
            'filepath': str(dss_path.resolve()),
            'filename': dss_path.name,
            'exists': True,
            'file_size_mb': dss_path.stat().st_size / (1024 * 1024),
            'total_paths': len(catalog),
            'path_types': path_types,
            'first_5_paths': catalog[:5] if len(catalog) > 5 else catalog,
        }

    @staticmethod
    def parse_pathname(pathname: str) -> Dict[str, str]:
        """
        Parse a DSS pathname into its component parts.

        DSS pathnames have format: /A/B/C/D/E/F/
        - A: Basin/Project identifier
        - B: Location/Element name
        - C: Data type (FLOW, PRECIP, etc.)
        - D: Date/Time block
        - E: Time interval
        - F: Version/Run identifier

        Args:
            pathname: DSS pathname string

        Returns:
            Dictionary with pathname components

        Example:
            parts = DssCore.parse_pathname("/BASIN/OUTLET/FLOW//15MIN/RUN:RUN1/")
            print(parts['B'])  # 'OUTLET'
            print(parts['C'])  # 'FLOW'
        """
        return parse_pathname(pathname)

    @staticmethod
    def create_pathname(
        basin: str,
        element: str,
        data_type: str,
        interval: str,
        run_name: str = "",
        date_block: str = ""
    ) -> str:
        """
        Create a DSS pathname from components.

        Args:
            basin: Basin/Project name (A part)
            element: Element name (B part)
            data_type: Data type like FLOW, PRECIP (C part)
            interval: Time interval like 15MIN, 1HOUR (E part)
            run_name: Run identifier (F part)
            date_block: Date block (D part, usually empty)

        Returns:
            Formatted DSS pathname

        Example:
            path = DssCore.create_pathname(
                "MYBASIN", "OUTLET", "FLOW", "15MIN", "RUN1"
            )
            print(path)  # '/MYBASIN/OUTLET/FLOW//15MIN/RUN:RUN1/'
        """
        return create_pathname(basin, element, data_type, interval, run_name, date_block)

    @staticmethod
    def filter_catalog(
        catalog: List[str],
        pattern: Optional[str] = None,
        data_type: Optional[str] = None,
        element: Optional[str] = None
    ) -> List[str]:
        """
        Filter DSS catalog by pattern or components.

        Args:
            catalog: List of DSS pathnames
            pattern: Regex pattern to match against full pathname
            data_type: Filter by C-part (e.g., "FLOW", "PRECIP")
            element: Filter by B-part (element/location name)

        Returns:
            Filtered list of pathnames

        Example:
            paths = DssCore.get_catalog("file.dss")
            flow_paths = DssCore.filter_catalog(paths, data_type="FLOW")
        """
        return filter_catalog(catalog, pattern, data_type, element)

    @staticmethod
    def _write_paired_data_java(
        dss_file: Union[str, Path],
        pathname: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        x_units: str = "HOURS",
        y_units: str = "FRACTION",
        x_label: str = "TIME",
        y_label: str = "CUMULATIVE"
    ) -> bool:
        """``write_paired_data`` through HEC Monolith (Java backend)."""
        DssCore._check_pathname_format(pathname)

        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        PairedDataContainer = autoclass('hec.io.PairedDataContainer')

        dss_file = str(Path(dss_file).resolve())

        # Open DSS file (creates if doesn't exist)
        dss = HecDss.open(dss_file)

        # Suppress DSS library verbose output
        try:
            dss.setMessageLevel(0)
        except Exception:
            pass

        try:
            # Create PairedDataContainer
            container = PairedDataContainer()

            # Use setter methods (pyjnius requires explicit setters, not property assignment)
            container.setFullName(pathname)
            container.setXUnits(x_units)
            container.setYUnits(y_units)
            container.setXType(x_label)
            container.setYType(y_label)

            # Convert numpy arrays to Java arrays
            # X ordinates: 1D array (double[])
            x_list = x_values.astype(np.float64).tolist()

            # Y ordinates: 2D array (double[numberCurves][numberOrdinates])
            # For single curve, wrap in outer list: [[y1, y2, ...]]
            # See: https://www.hec.usace.army.mil/confluence/dssdocs/dssjavaprogrammer/paired-data
            y_list = y_values.astype(np.float64).tolist()
            y_2d = [y_list]  # Single curve: yOrdinates[1][n]

            container.setXOrdinates(x_list)
            container.setYOrdinates(y_2d)
            container.setNumberOrdinates(len(x_values))
            container.setNumberCurves(1)

            # Write to DSS file. HecDss.put has DataContainer and
            # DataContainerTransformer overloads; without the cast pyjnius
            # can select the wrong one and nothing is written.
            dss.put(cast('hec.io.DataContainer', container))

        except Exception as e:
            logger.error(f"Error writing paired data to {pathname}: {e}")
            DssCore._done_and_release(dss, dss_file)
            return False

        try:
            missing = DssCore._missing_pathnames(
                DssCore._cataloged_pathnames(dss), [pathname]
            )
        finally:
            DssCore._done_and_release(dss, dss_file)

        if missing:
            raise RuntimeError(
                f"Paired data write reported no error, but {pathname} is not in "
                f"the catalog of {dss_file}"
            )

        logger.info(f"Wrote paired data to {pathname}")
        return True

    @staticmethod
    def _write_multiple_paired_data_java(
        dss_file: Union[str, Path],
        paired_data_records: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """``write_multiple_paired_data`` through HEC Monolith (Java backend)."""
        seen = {}
        for record in paired_data_records:
            pathname = record['pathname']
            DssCore._check_pathname_format(pathname)
            key = pathname.upper()
            if key in seen:
                raise ValueError(
                    f"Duplicate paired-data pathname {pathname!r} (also {seen[key]!r}); "
                    "the later record would overwrite the earlier one"
                )
            seen[key] = pathname

        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        PairedDataContainer = autoclass('hec.io.PairedDataContainer')

        dss_file = str(Path(dss_file).resolve())
        results = {}

        # Open DSS file once for all writes
        dss = HecDss.open(dss_file)

        try:
            dss.setMessageLevel(0)
        except Exception:
            pass

        try:
            for record in paired_data_records:
                pathname = record['pathname']
                try:
                    # Create container with setter methods
                    container = PairedDataContainer()
                    container.setFullName(pathname)
                    container.setXUnits(record.get('x_units', 'HOURS'))
                    container.setYUnits(record.get('y_units', 'FRACTION'))
                    container.setXType(record.get('x_label', 'TIME'))
                    container.setYType(record.get('y_label', 'CUMULATIVE'))

                    x_values = record['x_values']
                    y_values = record['y_values']

                    # X ordinates: 1D array (double[])
                    x_list = x_values.astype(np.float64).tolist()

                    # Y ordinates: 2D array (double[numberCurves][numberOrdinates])
                    y_list = y_values.astype(np.float64).tolist()
                    y_2d = [y_list]  # Single curve: yOrdinates[1][n]

                    container.setXOrdinates(x_list)
                    container.setYOrdinates(y_2d)
                    container.setNumberOrdinates(len(x_values))
                    container.setNumberCurves(1)

                    # Write to DSS. The cast selects the DataContainer
                    # overload of HecDss.put (see write_paired_data).
                    dss.put(cast('hec.io.DataContainer', container))
                    results[pathname] = True

                except Exception as e:
                    logger.error(f"Error writing {pathname}: {e}")
                    results[pathname] = False

            written = [path for path, ok in results.items() if ok]
            missing = (
                DssCore._missing_pathnames(DssCore._cataloged_pathnames(dss), written)
                if written else []
            )

        finally:
            DssCore._done_and_release(dss, dss_file)

        if missing:
            raise RuntimeError(
                f"{len(missing)} paired data write(s) reported no error but are not in "
                f"the catalog of {dss_file}: {missing}"
            )

        logger.info(f"Wrote {sum(results.values())}/{len(results)} paired data records")
        return results

    @staticmethod
    def _read_paired_data_java(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """``read_paired_data`` through HEC Monolith (Java backend)."""
        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        PairedDataContainer = autoclass('hec.io.PairedDataContainer')

        dss_file = Path(dss_file)

        if not dss_file.exists():
            logger.warning(f"DSS file not found: {dss_file}")
            return None

        dss_file = str(dss_file.resolve())

        # Open DSS file
        dss = HecDss.open(dss_file)

        # Suppress DSS library verbose output
        try:
            dss.setMessageLevel(0)
        except Exception:
            pass

        try:
            # Read paired data
            # True = ignore D-part for wildcard matching
            container = dss.get(pathname, True)

            if container is None:
                logger.warning(f"No data found for pathname: {pathname}")
                return None

            # Cast to PairedDataContainer to access fields
            pdc = cast('hec.io.PairedDataContainer', container)

            # Extract X ordinates (1D array)
            x_values = np.array(pdc.xOrdinates)

            # Extract Y ordinates (2D array - [curves][ordinates])
            # Most paired data has single curve, so take first curve
            y_ordinates = pdc.yOrdinates
            if y_ordinates is not None:
                # Convert Java 2D array to numpy
                # y_ordinates[0] is the first (usually only) curve
                y_values = np.array(y_ordinates[0])
            else:
                logger.warning(f"No Y ordinates found for pathname: {pathname}")
                return None

            # Extract metadata
            x_units = str(pdc.xUnits) if pdc.xUnits else ""
            y_units = str(pdc.yUnits) if pdc.yUnits else ""
            x_label = str(pdc.xType) if pdc.xType else ""
            y_label = str(pdc.yType) if pdc.yType else ""

            return {
                'x_values': x_values,
                'y_values': y_values,
                'x_units': x_units,
                'y_units': y_units,
                'x_label': x_label,
                'y_label': y_label,
                'pathname': pathname
            }

        except Exception as e:
            logger.error(f"Error reading paired data from {pathname}: {e}")
            return None

        finally:
            DssCore._done_and_release(dss, dss_file)

    # ------------------------------------------------------------------
    # Public dispatch (java / native / shadow)
    # ------------------------------------------------------------------

    @staticmethod
    def _shadow_read(operation: str, dss_file: Any, pathname: Optional[str],
                     java_call, native_call, classify):
        """Run ``java_call`` (its result or error is what the caller gets), then
        ``native_call``, classify the pair and record it. The comparison never raises."""
        java_result, java_exc = None, None
        t0 = time.perf_counter()
        try:
            java_result = java_call()
        except Exception as exc:
            java_exc = exc
        java_s = time.perf_counter() - t0
        try:
            native_result, native_exc = None, None
            t1 = time.perf_counter()
            try:
                native_result = native_call()
            except Exception as exc:
                native_exc = exc
            native_s = time.perf_counter() - t1
            outcome, label, diffs = classify(java_result, java_exc, native_result, native_exc)
            _backend.record(
                operation, outcome, label, dss_file=dss_file, pathname=pathname, diffs=diffs,
                java_seconds=java_s, native_seconds=native_s, java_error=java_exc,
                native_error=native_exc,
            )
        except Exception as exc:  # the comparison must never break the read
            logger.debug("DSS shadow %s comparison failed: %s", operation, exc)
        if java_exc is not None:
            raise java_exc
        return java_result

    @staticmethod
    def get_catalog(dss_file: Union[str, Path]) -> List[str]:
        """
        Get list of all data paths in DSS file.

        Args:
            dss_file: Path to DSS file

        Returns:
            List of DSS pathnames in HEC catalog order

        Example:
            paths = DssCore.get_catalog("sample.dss")
            for path in paths:
                print(path)
        """
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._get_catalog_native(dss_file)
        if backend == "shadow":
            def classify(j, je, n, ne):
                if ne is not None and je is None:
                    return "unexpected", "native catalog error", []
                if ne is not None:
                    return "expected", "error on both backends", []
                return _backend.classify_catalog(j, je, n)

            return DssCore._shadow_read(
                "get_catalog", dss_file, None,
                lambda: DssCore._get_catalog_java(dss_file),
                lambda: DssCore._get_catalog_native(dss_file),
                classify,
            )
        return DssCore._get_catalog_java(dss_file)

    @staticmethod
    def _get_catalog_native(dss_file: Union[str, Path]) -> List[str]:
        """Catalog pathnames through ras_commander_fast_dss (no JVM)."""
        dc = _backend.import_native()
        catalog = dc.get_catalog(str(Path(dss_file).resolve()))
        return [str(path) for path in catalog["pathname"].tolist()]

    @staticmethod
    def _check_window(start_date, end_date):
        window_start = pd.Timestamp(start_date) if start_date is not None else None
        window_end = pd.Timestamp(end_date) if end_date is not None else None
        if window_start is not None and window_end is not None and window_start > window_end:
            raise ValueError(f"start_date ({window_start}) is after end_date ({window_end})")
        return window_start, window_end

    @staticmethod
    def read_timeseries(
        dss_file: Union[str, Path],
        pathname: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Read time series from DSS file.

        Args:
            dss_file: Path to DSS file
            pathname: DSS pathname (e.g., "/BASIN/LOC/FLOW//1HOUR/OBS/"). The D part
                is ignored; the whole dataset is read.
            start_date: Optional inclusive lower bound on the returned stamps
                (any value ``pandas.Timestamp`` accepts)
            end_date: Optional inclusive upper bound on the returned stamps

        Returns:
            pandas DataFrame with:
            - DatetimeIndex for time series operations
            - 'datetime' column for plotting (same as index)
            - 'value' column with time series data
            - Metadata via df.attrs: pathname, units, type, interval, dss_file

            Stamps come from the record's base date and time granularity, so
            second-granularity records (for example 15-second data) get their
            stored dates. ``attrs['interval']`` is in minutes: an int for whole
            minutes, a float below one minute, and 0 for irregular data. A
            window that matches no stamps returns an empty DataFrame. The window
            is the same inclusive stamp filter on every backend.

            Missing values: the Java backend returns HEC's missing markers as
            stored (-901, -902, -3.4028e38); the native backend returns NaN.

        Raises:
            ValueError: If the pathname has no data, or ``start_date`` is
                after ``end_date``.

        Example:
            df = DssCore.read_timeseries("file.dss", "/BASIN/LOC/FLOW//1HOUR/OBS/")
            print(df.head())
            print(f"Units: {df.attrs['units']}")
        """
        DssCore._check_window(start_date, end_date)
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._read_timeseries_native(dss_file, pathname, start_date, end_date)
        if backend == "shadow":
            return DssCore._shadow_read(
                "read_timeseries", dss_file, pathname,
                lambda: DssCore._read_timeseries_java(dss_file, pathname, start_date, end_date),
                lambda: DssCore._read_timeseries_native(dss_file, pathname, start_date, end_date),
                lambda j, je, n, ne: _backend.classify_timeseries(pathname, j, je, n, ne),
            )
        return DssCore._read_timeseries_java(dss_file, pathname, start_date, end_date)

    @staticmethod
    def _read_timeseries_native(
        dss_file: Union[str, Path],
        pathname: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """``read_timeseries`` through ras_commander_fast_dss (no JVM).

        Reads the whole dataset (HEC's ``get(path, True)`` semantics, leading and
        trailing missing values trimmed) and then applies the same inclusive stamp
        window as the Java path, so both backends return the same rows.
        """
        window_start, window_end = DssCore._check_window(start_date, end_date)
        dc = _backend.import_native()
        resolved = str(Path(dss_file).resolve())
        native = dc.read_timeseries(resolved, pathname)
        stamps = native.index.to_numpy(dtype="datetime64[s]")
        if len(stamps) == 0 or stamps.max() <= _NS_MAX:
            index = pd.DatetimeIndex(stamps.astype("datetime64[ns]"))
        else:  # pattern records (year 3000) do not fit nanoseconds
            index = pd.DatetimeIndex(stamps)
        df = pd.DataFrame({'value': native['value'].to_numpy(dtype=np.float64)}, index=index)
        if window_start is not None:
            df = df[df.index >= window_start]
        if window_end is not None:
            df = df[df.index <= window_end]
        df.insert(0, 'datetime', df.index)
        df.attrs['pathname'] = pathname
        df.attrs['units'] = native.attrs.get('units', "")
        df.attrs['type'] = native.attrs.get('type', "")
        df.attrs['interval'] = native.attrs.get('interval')
        df.attrs['dss_file'] = resolved
        return df

    @staticmethod
    def get_peak_value(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract ONLY peak value from DSS without loading full time series.

        Args:
            dss_file: Path to DSS file
            pathname: DSS pathname to read

        Returns:
            Dictionary with:
                - peak_flow: Maximum value (float)
                - peak_time: Time of maximum (datetime); the first maximum
                  when values tie
                - units: Engineering units (str)
                - count: Number of timesteps, including missing values (int)
                - min_value: Minimum value (float)
                - mean_value: Mean value (float)
            peak_flow, min_value and mean_value exclude HEC missing values
            (-901, -902 and -3.4028e38) and NaN.
            Returns None if path doesn't exist, read fails, or every value is
            missing

        Example:
            >>> peak_info = DssCore.get_peak_value("results.dss", "//OUTLET/FLOW/.../")
            >>> print(f"Peak: {peak_info['peak_flow']} {peak_info['units']}")
        """
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._get_peak_value_native(dss_file, pathname)
        if backend == "shadow":
            def classify(j, je, n, ne):
                if _backend.java_unavailable(je):
                    return "skipped", "java unavailable", []
                diffs = _backend.compare_peak(j, n)
                if diffs:
                    return "unexpected", "peak difference", diffs
                return "identical", "identical", []

            return DssCore._shadow_read(
                "get_peak_value", dss_file, pathname,
                lambda: DssCore._get_peak_value_java(dss_file, pathname),
                lambda: DssCore._get_peak_value_native(dss_file, pathname),
                classify,
            )
        return DssCore._get_peak_value_java(dss_file, pathname)

    @staticmethod
    def _get_peak_value_native(
        dss_file: Union[str, Path], pathname: str
    ) -> Optional[Dict[str, Any]]:
        """``get_peak_value`` through ras_commander_fast_dss (no JVM)."""
        dss_path = Path(dss_file)
        if not dss_path.exists():
            logger.warning(f"DSS file not found: {dss_path}")
            return None
        dc = _backend.import_native()
        not_found = getattr(dc, "DssPathnameNotFoundError", None) or ()
        try:
            # raw=True keeps the stored markers so ``count`` matches the Java path.
            df = dc.read_timeseries(str(dss_path.resolve()), pathname, raw=True)
        except not_found:
            logger.warning(f"No data found for pathname: {pathname}")
            return None
        except Exception as e:
            logger.error(f"Error reading DSS pathname {pathname}: {e}")
            return None
        values = df['value'].to_numpy(dtype=np.float64)
        valid = DssCore._valid_value_mask(values)
        if not valid.any():
            logger.warning(f"Only missing values in time series for pathname: {pathname}")
            return None
        valid_values = values[valid]
        valid_stamps = df.index.to_numpy(dtype="datetime64[s]")[valid]
        peak_idx = int(np.argmax(valid_values))  # first maximum when values tie
        return {
            'peak_flow': float(valid_values[peak_idx]),
            'peak_time': pd.Timestamp(valid_stamps[peak_idx]),
            'units': str(df.attrs.get('units', "") or ""),
            'count': int(values.size),
            'min_value': float(np.min(valid_values)),
            'mean_value': float(np.mean(valid_values)),
        }

    @staticmethod
    def read_paired_data(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read paired data (X-Y curve) from DSS file.

        Args:
            dss_file: Path to DSS file
            pathname: DSS pathname for paired data. The D part is ignored when the
                exact pathname is not found.

        Returns:
            Dictionary with:
                - x_values: numpy array of X values (float64)
                - y_values: numpy array of Y values, first curve only (float64)
                - x_units: X axis units
                - y_units: Y axis units
                - x_label: X axis type as stored (for example ``UNT``)
                - y_label: Y axis type as stored
                - pathname: Original pathname
            Returns None if read fails

        Example:
            >>> data = DssCore.read_paired_data(
            ...     "file.dss",
            ...     "//ELEMENT/FLOW-DIVERSION///TABLE/"
            ... )
            >>> print(f"X: {data['x_values']}")
            >>> print(f"Y: {data['y_values']}")
        """
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._read_paired_data_native(dss_file, pathname)
        if backend == "shadow":
            return DssCore._shadow_read(
                "read_paired_data", dss_file, pathname,
                lambda: DssCore._read_paired_data_java(dss_file, pathname),
                lambda: DssCore._read_paired_data_native(dss_file, pathname),
                _backend.classify_paired_data,
            )
        return DssCore._read_paired_data_java(dss_file, pathname)

    @staticmethod
    def _read_paired_data_native(
        dss_file: Union[str, Path], pathname: str
    ) -> Optional[Dict[str, Any]]:
        """``read_paired_data`` through ras_commander_fast_dss (no JVM).

        The engine's ``read_paired_data_compat`` returns exactly the Java dict:
        curve 0 only, axis types under the ``*_label`` keys, None on any failure.
        """
        dc = _backend.import_native()
        dss_path = Path(dss_file)
        if not dss_path.exists():
            logger.warning(f"DSS file not found: {dss_path}")
            return None
        return dc.read_paired_data_compat(str(dss_path.resolve()), pathname)

    @staticmethod
    def get_file_version(dss_file: Union[str, Path]) -> int:
        """
        HEC-DSS version of an existing file: 6 or 7.

        Args:
            dss_file: Path to an existing DSS file

        Returns:
            6 or 7

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the file is not a DSS6 or DSS7 file
        """
        dss_path = Path(dss_file)
        if not dss_path.is_file():
            raise FileNotFoundError(f"DSS file not found: {dss_path}")
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._get_file_version_native(dss_path)
        if backend == "shadow":
            return DssCore._shadow_read(
                "get_file_version", dss_path, None,
                lambda: DssCore._get_file_version_java(dss_path),
                lambda: DssCore._get_file_version_native(dss_path),
                _backend.classify_file_version,
            )
        return DssCore._get_file_version_java(dss_path)

    @staticmethod
    def _get_file_version_java(dss_file: Union[str, Path]) -> int:
        """File version through HEC Monolith (``HecDataManager.getDssFileVersion``)."""
        DssCore._configure_jvm()
        from jnius import autoclass

        resolved = str(Path(dss_file).resolve())
        try:
            version = int(autoclass('hec.heclib.dss.HecDataManager').getDssFileVersion(
                resolved))
        finally:
            DssCore._release_dss_file(resolved)
        if version not in (6, 7):
            raise ValueError(f"File is not a DSS6 or DSS7 file: {dss_file}")
        return version

    @staticmethod
    def _get_file_version_native(dss_file: Union[str, Path]) -> int:
        """File version through ras_commander_fast_dss (no JVM)."""
        dc = _backend.import_native()
        try:
            version = int(dc.file_signature(str(Path(dss_file).resolve()))["version"])
        except Exception as exc:
            raise ValueError(f"File is not a DSS6 or DSS7 file: {dss_file} ({exc})") from exc
        if version not in (6, 7):
            raise ValueError(f"File is not a DSS6 or DSS7 file: {dss_file}")
        return version

    # -- grids -----------------------------------------------------------------

    @staticmethod
    def _parse_grid_time(part: str) -> Optional[pd.Timestamp]:
        """``DDMMMYYYY:HHMM`` (``2400`` is the next day's 00:00) or None."""
        match = re.fullmatch(r"(\d{2}[A-Za-z]{3}\d{4}):?(\d{2})(\d{2})", (part or "").strip())
        if not match:
            return None
        day = pd.Timestamp(pd.to_datetime(match.group(1), format="%d%b%Y"))
        return day + pd.Timedelta(hours=int(match.group(2)), minutes=int(match.group(3)))

    @staticmethod
    def read_grid(dss_file: Union[str, Path], pathname: str) -> Dict[str, Any]:
        """
        Read one grid record (HRAP, Albers/SHG or specified) by its full pathname.

        Args:
            dss_file: Path to an existing DSS file
            pathname: Full grid pathname, including its D and E parts

        Returns:
            Dictionary with:
                - data: float32 array shaped ``(ny, nx)``; row 0 is the southern row
                  (HEC order); missing cells are NaN
                - pathname, dss_file
                - shape: ``(ny, nx)``
                - units, data_type (``PER-CUM``, ``PER-AVER``, ``INST-VAL``, ``INST-CUM``)
                - grid_type: ``hrap``, ``albers`` or ``specified``
                - cell_size: cell size in CRS units
                - lower_left_cell: ``(x, y)`` cell indexes of the lower-left cell
                - cell_zero: CRS coordinates of the lower-left corner of cell (0, 0)
                - origin: CRS coordinates of the grid's lower-left corner
                - crs: spatial reference (WKT) as HEC Monolith reports it
                - start_time, end_time: from the D and E parts (``pandas.Timestamp``)
                  or None

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If the pathname is malformed, or the record does not exist
                or is not a grid
            hms_commander.dss.DssCapabilityError: With the native backend, when the
                engine does not advertise qualified grid CRS strings

        Example:
            >>> grid = DssCore.read_grid("hrap.dss",
            ...     "/HRAP/ABRFC/PRECIP/18JAN1996:0600/18JAN1996:0700//")
            >>> grid["data"].shape
        """
        dss_path = Path(dss_file)
        if not dss_path.is_file():
            raise FileNotFoundError(f"DSS file not found: {dss_path}")
        DssCore._check_pathname_format(pathname)
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._read_grid_native(dss_path, pathname)
        if backend == "shadow":
            return DssCore._shadow_read(
                "read_grid", dss_path, pathname,
                lambda: DssCore._read_grid_java(dss_path, pathname),
                lambda: DssCore._read_grid_native(dss_path, pathname),
                _backend.classify_grid,
            )
        return DssCore._read_grid_java(dss_path, pathname)

    @staticmethod
    def _read_grid_java(dss_file: Union[str, Path], pathname: str) -> Dict[str, Any]:
        """``read_grid`` through HEC Monolith (``HecDss.get`` -> ``GridContainer``)."""
        DssCore._configure_jvm()
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        GridInfo = autoclass('hec.heclib.grid.GridInfo')
        resolved = str(Path(dss_file).resolve())
        dss = HecDss.open(resolved)
        try:
            dss.setMessageLevel(0)
        except Exception:
            pass
        try:
            if not dss.recordExists(pathname):
                raise ValueError(f"No data found for pathname: {pathname}")
            container = dss.get(pathname)
            if container is None:
                raise ValueError(f"No data found for pathname: {pathname}")
            class_name = str(container.getClass().getName())
            if class_name != "hec.io.GridContainer":
                raise ValueError(f"Not a grid record: {pathname} ({class_name})")
            grid_data = cast('hec.io.GridContainer', container).getGridData()
            info_base = grid_data.getGridInfo()
            info_class = str(info_base.getClass().getName())
            info = cast(info_class, info_base)
            nx, ny = int(info.getNumberOfCellsX()), int(info.getNumberOfCellsY())
            values = np.asarray(grid_data.getData(), dtype=np.float32)
            if values.size != nx * ny:
                raise RuntimeError(
                    f"Grid {pathname} returned {values.size} cells for {ny}x{nx}")
            values = values.reshape((ny, nx)).copy()
            values[values == np.float32(GridInfo.getGridNodataValue())] = np.nan
            short = info_class.rsplit('.', 1)[-1]
            cell_size = float(info.getCellSize())
            lower_left = (int(info.getLowerLeftCellX()), int(info.getLowerLeftCellY()))
            if short in ("AlbersInfo", "SpecifiedGridInfo"):
                cell_zero = (float(info.getXCoordOfGridCellZero()),
                             float(info.getYCoordOfGridCellZero()))
            else:
                cell_zero = (0.0, 0.0)
            parts = pathname.split('/')
            return {
                'dss_file': resolved,
                'pathname': pathname,
                'data': values,
                'shape': (ny, nx),
                'units': str(info.getDataUnits()),
                'data_type': str(info.getDataTypeName()),
                'grid_type': _GRID_TYPE_NAMES.get(short, short),
                'cell_size': cell_size,
                'lower_left_cell': lower_left,
                'cell_zero': cell_zero,
                'origin': (cell_zero[0] + lower_left[0] * cell_size,
                           cell_zero[1] + lower_left[1] * cell_size),
                'crs': str(info.getSpatialReferenceSystem()),
                'start_time': DssCore._parse_grid_time(parts[4]),
                'end_time': DssCore._parse_grid_time(parts[5]),
            }
        finally:
            DssCore._done_and_release(dss, resolved)

    @staticmethod
    def _read_grid_native(dss_file: Union[str, Path], pathname: str) -> Dict[str, Any]:
        """``read_grid`` through ras_commander_fast_dss (no JVM). Gated on the engine's
        ``grid_srs_monolith_parity`` feature."""
        dc = _backend.require_native_grid_reads()
        resolved = str(Path(dss_file).resolve())
        grid = dc.read_grid(resolved, pathname)
        cell_size = float(grid.cell_size)
        lower_left = (int(grid.lower_left_cell_x), int(grid.lower_left_cell_y))
        cell_zero = (float(grid.x_coord_of_grid_cell_zero),
                     float(grid.y_coord_of_grid_cell_zero))
        parts = pathname.split('/')
        return {
            'dss_file': resolved,
            'pathname': pathname,
            'data': np.asarray(grid.data, dtype=np.float32),
            'shape': (int(grid.ny), int(grid.nx)),
            'units': str(grid.data_units),
            'data_type': grid.data_type_name,
            'grid_type': str(grid.grid_type),
            'cell_size': cell_size,
            'lower_left_cell': lower_left,
            'cell_zero': cell_zero,
            'origin': (cell_zero[0] + lower_left[0] * cell_size,
                       cell_zero[1] + lower_left[1] * cell_size),
            'crs': str(grid.srs_definition),
            'start_time': DssCore._parse_grid_time(parts[4]),
            'end_time': DssCore._parse_grid_time(parts[5]),
        }

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    #: DSS version a new file gets when no version is requested. It is the Java
    #: path's default: HEC Monolith 3.3.27 creates DSS7 files.
    NEW_FILE_VERSION = 7

    #: Longest unit or type string a DSS6 paired-data record stores.
    DSS6_TEXT_LIMIT = 8

    @staticmethod
    def _validate_dss_version(dss_version: Optional[int]) -> Optional[int]:
        if dss_version is None:
            return None
        if isinstance(dss_version, bool) or dss_version not in (6, 7):
            raise ValueError(f"dss_version must be 6, 7 or None, not {dss_version!r}")
        return int(dss_version)

    @staticmethod
    def _target_version(dss_file: Union[str, Path], dss_version: Optional[int] = None) -> int:
        """Version a write will use: the existing file's (it must match an explicit
        ``dss_version``), else ``dss_version`` or ``NEW_FILE_VERSION``."""
        dss_version = DssCore._validate_dss_version(dss_version)
        dss_path = Path(dss_file)
        if dss_path.exists():
            if not dss_path.is_file():
                raise IsADirectoryError(f"DSS path is not a file: {dss_path}")
            version = DssCore.get_file_version(dss_path)
            if dss_version is not None and version != dss_version:
                raise ValueError(
                    f"Existing DSS file is version {version}, not requested version "
                    f"{dss_version}: {dss_path}"
                )
            return version
        return dss_version if dss_version is not None else DssCore.NEW_FILE_VERSION

    @staticmethod
    def _native_write_target(
        dss_file: Union[str, Path], dss_version: Optional[int] = None
    ) -> Tuple[Path, int, bool, List[Path]]:
        """Resolved target, its DSS version, whether it existed, and the parent
        directories created for it (deepest first), for a native write."""
        dss_version = DssCore._validate_dss_version(dss_version)
        dss_path = Path(dss_file)
        existed = dss_path.exists()
        created: List[Path] = []
        if existed:
            if not dss_path.is_file():
                raise IsADirectoryError(f"DSS path is not a file: {dss_path}")
            version = DssCore._get_file_version_native(dss_path)
            if dss_version is not None and version != dss_version:
                raise ValueError(
                    f"Existing DSS file is version {version}, not requested version "
                    f"{dss_version}: {dss_path}"
                )
        else:
            created = _backend.make_parents(dss_path)
            version = dss_version if dss_version is not None else DssCore.NEW_FILE_VERSION
        return dss_path.resolve(), int(version), existed, created

    @staticmethod
    @contextmanager
    def _native_new_file(dc: Any, target: Path, version: int, existed: bool,
                         created_dirs: Optional[List[Path]] = None):
        """Create ``target`` when it did not exist, and remove it (and the empty parent
        directories made for it) if the write inside the block raises, so a refused
        native write leaves no new file or directory."""
        try:
            if not existed:
                dc.create(str(target), version)
            yield
        except BaseException:
            if not existed and target.exists():
                try:
                    target.unlink()
                except OSError as exc:
                    logger.warning("Could not remove %s after a failed native write: %s",
                                   target, exc)
            _backend.remove_created_dirs(created_dirs or [])
            raise

    @staticmethod
    def _readback_pathname(pathname: str, version: int) -> str:
        """Dataset pathname for a read-back: D part blank; on DSS6 upper case with the
        DSS6 interval names (``1Minute`` -> ``1MIN``, ``1Month`` -> ``1MON``)."""
        parts = pathname.split("/")
        if len(parts) == 8:
            parts[4] = ""
        if version != 6:
            return "/".join(parts)
        parts = [part.upper() for part in parts]
        if len(parts) == 8:
            parts[5] = re.sub(r"^(\d+)MINUTES?$", r"\1MIN", parts[5])
            parts[5] = re.sub(r"^(\d+)MONTHS?$", r"\1MON", parts[5])
        return "/".join(parts)

    @staticmethod
    def _shadow_write(operation: str, dss_file: Any, pathname: Optional[str],
                      java_call, native_call, compare):
        """Shadow write: snapshot the target, run ``java_call`` (its result or error is
        what the caller gets), repeat the write natively with ``native_call(copy,
        existed)`` on the snapshot, then ``compare(copy)`` the native read-backs.
        The comparison never raises."""
        from .hms_dss import HmsDss

        limit = getattr(HmsDss, "shadow_copy_limit_mb", _backend.SHADOW_COPY_LIMIT_MB_DEFAULT)
        ctx = _backend.shadow_snapshot(dss_file, limit)
        try:
            t0 = time.perf_counter()
            result = java_call()
            java_s = time.perf_counter() - t0
            try:
                if ctx.get("skip"):
                    _backend.record(operation, "skipped", ctx["skip"], dss_file=dss_file,
                                    pathname=pathname, java_seconds=java_s)
                else:
                    native_exc, diffs = None, []
                    t1 = time.perf_counter()
                    try:
                        native_call(ctx["copy"], ctx["existed"])
                    except Exception as exc:
                        native_exc = exc
                    native_s = time.perf_counter() - t1
                    if native_exc is None:
                        diffs = compare(ctx["copy"])
                    outcome, label, diffs = _backend.classify_write(native_exc, diffs)
                    _backend.record(operation, outcome, label, dss_file=dss_file,
                                    pathname=pathname, diffs=diffs, java_seconds=java_s,
                                    native_seconds=native_s, native_error=native_exc)
            except Exception as exc:  # the comparison must never break the write
                logger.warning("DSS shadow %s comparison failed for %s: %s",
                               operation, dss_file, exc)
            return result
        finally:
            _backend.shadow_cleanup(ctx)

    # -- time series ---------------------------------------------------------

    @staticmethod
    def _prepare_timeseries(pathname, times, values):
        """Shared argument checks for ``write_timeseries``; returns ``(stamps, values)``
        with stamps as ``datetime64[s]`` and values as float64."""
        DssCore._check_pathname_format(pathname)
        e_part = pathname.split('/')[5]
        if e_part.upper().startswith('IR-'):
            raise ValueError(
                "write_timeseries writes regular-interval data only; the E part "
                f"{e_part!r} names an irregular series")
        values = np.asarray(values, dtype=np.float64)
        if values.ndim != 1:
            raise ValueError("values must be one-dimensional")
        try:
            index = pd.DatetimeIndex(times)
        except Exception as exc:
            raise ValueError(f"times must be dates or times: {exc}") from exc
        if index.tz is not None:
            raise ValueError("times are time-zone aware; DSS stamps are naive")
        if len(index) != len(values):
            raise ValueError(
                f"times ({len(index)}) and values ({len(values)}) must have same length")
        if len(values) == 0:
            raise ValueError("times and values must not be empty")
        if index.hasnans:
            raise ValueError("times contain NaT")
        stamps = index.to_numpy(dtype="datetime64[ns]")
        if np.any(stamps.astype(np.int64) % 60_000_000_000):
            raise ValueError("times must be whole minutes (HEC time-series stamps)")
        if len(stamps) > 1 and np.any(np.diff(stamps.astype(np.int64)) <= 0):
            raise ValueError("times must be strictly increasing")
        if np.isinf(values).any():
            first = int(np.flatnonzero(np.isinf(values))[0])
            raise ValueError(f"value {first} is infinite; HEC-DSS has no infinity convention")
        return stamps.astype("datetime64[s]"), values

    @staticmethod
    def write_timeseries(
        dss_file: Union[str, Path],
        pathname: str,
        times,
        values,
        units: str = "CFS",
        data_type: str = "INST-VAL",
        dss_version: Optional[int] = None,
    ) -> Path:
        """
        Write a regular-interval time series to a DSS file (created if missing).

        Args:
            dss_file: Path to the DSS file. A missing file is created as DSS7
                unless ``dss_version`` is 6.
            pathname: ``/A/B/C/D/E/F/`` with a regular E part (``15MIN``, ``1HOUR``,
                ``1Hour``, ``1DAY``, ...). D may be empty; HEC sets it per block.
            times: One naive stamp per value (end-of-period stamps), whole minutes,
                strictly increasing and regular for the E part
            values: Numeric values, stored as doubles. ``NaN`` is stored as HEC's
                missing value (-3.4028e38 on DSS7, -901 on DSS6); infinity is refused.
            units: HEC units (default ``CFS``)
            data_type: HEC type: ``INST-VAL``, ``PER-AVER``, ``PER-CUM`` or ``INST-CUM``
            dss_version: 6 or 7 for a new file; for an existing file it must match

        Returns:
            Path to the DSS file

        Raises:
            ValueError: Invalid pathname, times or values, or a version mismatch.
                The native backend also refuses stamps that are not regular for the
                E part.
            RuntimeError: If HEC Monolith reports a failed write

        Example:
            >>> times = pd.date_range("2020-01-01 01:00", periods=24, freq="h")
            >>> DssCore.write_timeseries("obs.dss", "//GAGE 1/FLOW//1HOUR/OBS/",
            ...                          times, flows)
        """
        DssCore._prepare_timeseries(pathname, times, values)
        DssCore._validate_dss_version(dss_version)
        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._write_timeseries_native(
                dss_file, pathname, times, values, units, data_type, dss_version)
        if backend == "shadow":
            def native_call(copy, existed):
                version = DssCore._get_file_version_native(dss_file)
                DssCore._write_timeseries_native(copy, pathname, times, values, units,
                                                 data_type, None if existed else version)

            def compare(copy):
                version = DssCore._get_file_version_native(dss_file)
                readback = DssCore._readback_pathname(pathname, version)
                java_df = DssCore._read_timeseries_native(dss_file, readback)
                native_df = DssCore._read_timeseries_native(copy, readback)
                return _backend.compare_frames(java_df, native_df, skip_attrs=("dss_file",))

            return DssCore._shadow_write(
                "write_timeseries", dss_file, pathname,
                lambda: DssCore._write_timeseries_java(
                    dss_file, pathname, times, values, units, data_type, dss_version),
                native_call, compare,
            )
        return DssCore._write_timeseries_java(
            dss_file, pathname, times, values, units, data_type, dss_version)

    @staticmethod
    def _write_timeseries_java(dss_file, pathname, times, values, units, data_type,
                               dss_version) -> Path:
        """``write_timeseries`` through HEC Monolith (``TimeSeriesContainer``)."""
        stamps, values = DssCore._prepare_timeseries(pathname, times, values)
        dss_path = Path(dss_file)
        existed = dss_path.exists()
        version = DssCore._target_version(dss_path, dss_version)
        values = values.copy()
        values[np.isnan(values)] = -901.0 if version == 6 else _HEC_UNDEFINED_DOUBLE
        minutes = ((stamps - np.datetime64('1899-12-31T00:00:00', 's'))
                   .astype('timedelta64[m]').astype(np.int64))
        interval = int(np.median(np.diff(minutes))) if len(minutes) > 1 else 0

        DssCore._configure_jvm()
        from jnius import autoclass, cast

        HecDss = autoclass('hec.heclib.dss.HecDss')
        tsc = autoclass('hec.io.TimeSeriesContainer')()
        tsc.fullName = pathname
        tsc.units = units
        tsc.type = data_type
        tsc.interval = interval
        tsc.setStoreAsDoubles(True)
        status_t = tsc.setTimes(autoclass('hec.heclib.util.HecTimeArray')(
            [int(m) for m in minutes]))
        status_v = tsc.setValues(values.tolist())
        if status_t != 0 or status_v != 0:
            raise RuntimeError(
                f"HEC time-series container rejected input: times={status_t}, "
                f"values={status_v}")
        tsc.numberValues = len(values)

        if not existed:
            dss_path.parent.mkdir(parents=True, exist_ok=True)
        resolved = str(dss_path.resolve())
        dss = HecDss.open(resolved, version) if not existed else HecDss.open(resolved)
        try:
            try:
                dss.setMessageLevel(0)
            except Exception:
                pass
            dss.put(cast('hec.io.DataContainer', tsc))
        except Exception as exc:
            raise RuntimeError(
                f"Failed to write time series {pathname} to {resolved}: {exc}") from exc
        finally:
            DssCore._done_and_release(dss, resolved)
        logger.info(f"Wrote {len(values)} values to {pathname}")
        return Path(resolved)

    @staticmethod
    def _write_timeseries_native(dss_file, pathname, times, values, units, data_type,
                                 dss_version) -> Path:
        """``write_timeseries`` through ras_commander_fast_dss (no JVM). Values are
        stored as doubles, as the Java path stores them."""
        stamps, values = DssCore._prepare_timeseries(pathname, times, values)
        dc = _backend.require_native_writes()
        target, version, existed, created = DssCore._native_write_target(dss_file, dss_version)
        with DssCore._native_new_file(dc, target, version, existed, created):
            dc.write_timeseries(str(target), pathname, values, times=stamps, units=units,
                                data_type=data_type, version=version, value_type="double")
        logger.info(f"Wrote {len(values)} values to {pathname}")
        return target

    # -- paired data -----------------------------------------------------------

    @staticmethod
    def _check_paired_data_records(paired_data_records: List[Dict[str, Any]]) -> None:
        seen = {}
        for record in paired_data_records:
            pathname = record['pathname']
            DssCore._check_pathname_format(pathname)
            key = pathname.upper()
            if key in seen:
                raise ValueError(
                    f"Duplicate paired-data pathname {pathname!r} (also {seen[key]!r}); "
                    "the later record would overwrite the earlier one"
                )
            seen[key] = pathname

    @staticmethod
    def write_paired_data(
        dss_file: Union[str, Path],
        pathname: str,
        x_values: np.ndarray,
        y_values: np.ndarray,
        x_units: str = "HOURS",
        y_units: str = "FRACTION",
        x_label: str = "TIME",
        y_label: str = "CUMULATIVE"
    ) -> bool:
        """
        Write paired data (X-Y curve) to DSS file.

        This is used for Atlas 14 temporal distributions, rating curves,
        and other X-Y relationships. The record is stored as float32 paired
        data (HEC record type PD), as HEC Monolith stores it.

        Args:
            dss_file: Path to DSS file (created as DSS7 if it doesn't exist)
            pathname: DSS pathname with exactly six parts
                (e.g., "//TX_R3/FIRST-QUARTILE/24HR//50%/")
            x_values: X coordinates (e.g., time in hours)
            y_values: Y coordinates (e.g., cumulative fraction 0-1)
            x_units: Units for X values (default: "HOURS")
            y_units: Units for Y values (default: "FRACTION")
            x_label: Stored as the X axis type (default: "TIME")
            y_label: Stored as the Y axis type (default: "CUMULATIVE")

        Returns:
            True if the record was written and found in the file catalog,
            False if the DSS library raised an error during the write

        Raises:
            ValueError: If ``pathname`` does not have exactly six parts
                (seven slashes). With the native backend, also if a unit or type
                string is longer than 8 characters for a DSS6 file (HEC Monolith
                silently truncates it there). Nothing is written in either case.
            RuntimeError: If the write returned without error but the record
                is not in the file catalog afterwards

        Example:
            >>> x = np.linspace(0, 24, 49)  # 0 to 24 hours
            >>> y = np.linspace(0, 1, 49)   # 0 to 100% cumulative
            >>> DssCore.write_paired_data(
            ...     "temporal.dss",
            ...     "//TX_R3/ALL-CASES/24HR//50%/",
            ...     x, y
            ... )
        """
        DssCore._check_pathname_format(pathname)
        record = {'pathname': pathname, 'x_values': x_values, 'y_values': y_values,
                  'x_units': x_units, 'y_units': y_units, 'x_label': x_label,
                  'y_label': y_label}

        def java_call():
            return DssCore._write_paired_data_java(
                dss_file, pathname, x_values, y_values, x_units, y_units, x_label, y_label)

        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._write_paired_data_native(dss_file, [record])[pathname]
        if backend == "shadow":
            return DssCore._shadow_write_paired_data(
                "write_paired_data", dss_file, [record], java_call)
        return java_call()

    @staticmethod
    def write_multiple_paired_data(
        dss_file: Union[str, Path],
        paired_data_records: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Write multiple paired data records to DSS file.

        Args:
            dss_file: Path to DSS file (created as DSS7 if it doesn't exist)
            paired_data_records: List of dicts with keys:
                - pathname: DSS pathname
                - x_values: numpy array of X values
                - y_values: numpy array of Y values
                - x_units: (optional) X units
                - y_units: (optional) Y units
                - x_label: (optional) X axis type
                - y_label: (optional) Y axis type

        Returns:
            Dict mapping pathname to success status. True means the record was
            written and found in the file catalog; False means the DSS library
            raised an error for that record.

        Raises:
            ValueError: If any pathname does not have exactly six parts, or two
                records share a pathname (the later record would overwrite the
                earlier one). With the native backend, also if a unit or type
                string is longer than 8 characters for a DSS6 file. Nothing is
                written in these cases.
            RuntimeError: If a write reported no error but its record is not
                in the file catalog afterwards

        Example:
            >>> records = [
            ...     {"pathname": "//A/B/C//D/", "x_values": x1, "y_values": y1},
            ...     {"pathname": "//A/E/C//D/", "x_values": x2, "y_values": y2},
            ... ]
            >>> results = DssCore.write_multiple_paired_data("file.dss", records)
        """
        DssCore._check_paired_data_records(paired_data_records)

        def java_call():
            return DssCore._write_multiple_paired_data_java(dss_file, paired_data_records)

        backend = DssCore.get_backend()
        if backend == "native":
            return DssCore._write_paired_data_native(dss_file, paired_data_records)
        if backend == "shadow":
            return DssCore._shadow_write_paired_data(
                "write_multiple_paired_data", dss_file, paired_data_records, java_call)
        return java_call()

    @staticmethod
    def _paired_data_specs(paired_data_records: List[Dict[str, Any]], version: int):
        """Normalized records; refuses DSS6 unit/type strings over 8 characters."""
        specs = []
        for record in paired_data_records:
            spec = {
                'pathname': record['pathname'],
                'x': np.asarray(record['x_values'], dtype=np.float64),
                'y': np.asarray(record['y_values'], dtype=np.float64),
                'x_units': record.get('x_units', 'HOURS'),
                'y_units': record.get('y_units', 'FRACTION'),
                'x_type': record.get('x_label', 'TIME'),
                'y_type': record.get('y_label', 'CUMULATIVE'),
            }
            if version == 6:
                for key in ('x_units', 'x_type', 'y_units', 'y_type'):
                    text = str(spec[key])
                    if len(text) > DssCore.DSS6_TEXT_LIMIT:
                        raise ValueError(
                            f"{record['pathname']}: {key} {text!r} is {len(text)} "
                            f"characters; a DSS6 file stores at most "
                            f"{DssCore.DSS6_TEXT_LIMIT} (HEC Monolith would silently store "
                            f"{text[:DssCore.DSS6_TEXT_LIMIT]!r}). Pass a string of "
                            f"{DssCore.DSS6_TEXT_LIMIT} characters or fewer, or write to a "
                            "DSS7 file."
                        )
            specs.append(spec)
        return specs

    @staticmethod
    def _write_paired_data_native(
        dss_file: Union[str, Path], paired_data_records: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Paired-data writes through ras_commander_fast_dss (no JVM).

        Mirrors the Java path: float32 (PD) records, the ``*_label`` arguments stored
        as axis types, no curve labels, one result per record (False when the engine
        raised for that record), then a catalog check. DSS6 unit/type strings over 8
        characters are refused before anything is written.
        """
        DssCore._check_paired_data_records(paired_data_records)
        dc = _backend.require_native_writes()
        target, version, existed, created = DssCore._native_write_target(dss_file)
        try:
            specs = DssCore._paired_data_specs(paired_data_records, version)
        except Exception:
            _backend.remove_created_dirs(created)
            raise
        results: Dict[str, bool] = {}
        with DssCore._native_new_file(dc, target, version, existed, created):
            for spec in specs:
                pathname = spec['pathname']
                try:
                    dc.write_paired_data(
                        str(target), pathname, spec['x'], spec['y'],
                        x_units=spec['x_units'], x_type=spec['x_type'],
                        y_units=spec['y_units'], y_type=spec['y_type'],
                        value_type="float", version=version,
                    )
                    results[pathname] = True
                except Exception as e:
                    logger.error(f"Error writing paired data to {pathname}: {e}")
                    results[pathname] = False
        written = [path for path, ok in results.items() if ok]
        missing = (DssCore._missing_pathnames(DssCore._get_catalog_native(target), written)
                   if written else [])
        if missing:
            raise RuntimeError(
                f"{len(missing)} paired data write(s) reported no error but are not in "
                f"the catalog of {target}: {missing}"
            )
        logger.info(f"Wrote {sum(results.values())}/{len(results)} paired data records")
        return results

    @staticmethod
    def _shadow_write_paired_data(operation, dss_file, records, java_call):
        def native_call(copy, existed):
            DssCore._write_paired_data_native(copy, records)

        def compare(copy):
            diffs = []
            for record in records:
                pathname = record['pathname']
                java = DssCore._read_paired_data_native(dss_file, pathname)
                native = DssCore._read_paired_data_native(copy, pathname)
                diffs += [f"{pathname}:{d}"
                          for d in _backend.compare_paired_data(java, native)]
            return diffs

        pathname = records[0]['pathname'] if len(records) == 1 else None
        return DssCore._shadow_write(operation, dss_file, pathname, java_call,
                                     native_call, compare)

    @staticmethod
    def shutdown_jvm():
        """
        Shutdown Java Virtual Machine.

        Note: With pyjnius, JVM shutdown is typically not needed.
        This is a placeholder for API compatibility.
        """
        logger.info("pyjnius handles JVM lifecycle automatically")
        pass


if __name__ == "__main__":
    """Test DssCore class"""
    import sys

    print("=" * 80)
    print("DssCore Test (hms-commander)")
    print("=" * 80)

    # Check if available
    print(f"\nDSS available: {DssCore.is_available()}")

    # Test pathname parsing
    print("\nTesting pathname parsing:")
    test_path = "/BASIN/OUTLET/FLOW//15MIN/RUN:SIMULATION1/"
    parts = DssCore.parse_pathname(test_path)
    for key, value in parts.items():
        print(f"  {key}: {value}")

    # Test pathname creation
    print("\nTesting pathname creation:")
    created = DssCore.create_pathname("MYBASIN", "OUTLET", "FLOW", "1HOUR", "TEST")
    print(f"  Created: {created}")

    print("\n" + "=" * 80)
    print("Basic tests complete!")
    print("=" * 80)
