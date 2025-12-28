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
from typing import List, Dict, Optional, Union, Any
import logging
import re

# Lazy imports - these are always needed for type hints and basic operations
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


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

        print("Configuring Java VM for DSS operations...")

        # Set JAVA_HOME if not already set
        if 'JAVA_HOME' not in os.environ:
            # Try to find Java
            java_candidates = [
                Path("C:/Program Files/Java/jre1.8.0_471"),
                Path("C:/Program Files/Java/jdk-11"),
                Path("C:/Program Files/Java/jdk-17"),
                Path("C:/Program Files/Java/jdk-21"),
                Path("C:/Program Files (x86)/Java/jre1.8.0_471"),
                Path("/usr/lib/jvm/java-11-openjdk"),
                Path("/usr/lib/jvm/java-17-openjdk"),
            ]
            for java_home in java_candidates:
                if java_home.exists():
                    os.environ['JAVA_HOME'] = str(java_home)
                    print(f"  Found Java: {java_home}")
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
        print("[OK] Java VM configured")

    @staticmethod
    def is_available() -> bool:
        """
        Check if DSS functionality is available.

        Returns:
            True if pyjnius can be imported
        """
        try:
            import jnius_config
            return True
        except ImportError:
            return False

    @staticmethod
    def get_catalog(dss_file: Union[str, Path]) -> List[str]:
        """
        Get list of all data paths in DSS file.

        Args:
            dss_file: Path to DSS file

        Returns:
            List of DSS path strings

        Example:
            paths = DssCore.get_catalog("sample.dss")
            for path in paths:
                print(path)
        """
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
            dss.done()

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
            pathname: DSS pathname (e.g., "/BASIN/LOC/FLOW//1HOUR/OBS/")
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            pandas DataFrame with:
            - DatetimeIndex for time series operations
            - 'datetime' column for plotting (same as index)
            - 'value' column with time series data
            - Metadata via df.attrs: pathname, units, type, interval, dss_file

        Example:
            df = DssCore.read_timeseries("file.dss", "/BASIN/LOC/FLOW//1HOUR/OBS/")
            print(df.head())
            print(f"Units: {df.attrs['units']}")

            # Plotting options:
            ax.plot(df.index, df['value'])          # Using DatetimeIndex
            ax.plot(df['datetime'], df['value'])    # Using datetime column
            df.plot(y='value')                      # Pandas automatic
        """
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
            values = np.array(tsc.values)  # Java double[] -> numpy array
            times = np.array(tsc.times)    # Java int[] -> numpy array (minutes since 1899-12-31)

            # Validate that we got data
            if len(values) == 0 or len(times) == 0:
                raise ValueError(f"No data found in time series for pathname: {pathname}")

            if len(values) != len(times):
                raise ValueError(
                    f"Mismatched array lengths: {len(values)} values, {len(times)} times"
                )

            # Convert HEC time to numpy datetime64
            # HEC epoch: December 31, 1899 00:00:00
            HEC_EPOCH = np.datetime64('1899-12-31T00:00:00')

            # Convert times (minutes since epoch) to timedelta
            # Handle potential invalid/missing times
            times_minutes = times.astype('int64')  # Ensure integer type
            time_deltas = pd.to_timedelta(times_minutes, unit='m')

            # Add to epoch to get actual datetimes
            datetimes = pd.DatetimeIndex(
                [HEC_EPOCH.astype('datetime64[ns]') + td for td in time_deltas]
            )

            # Create DataFrame with DatetimeIndex for time series operations
            df = pd.DataFrame({
                'value': values
            }, index=datetimes)

            # Also add datetime as a column for easier plotting
            # Users can do: ax.plot(df['datetime'], df['value'])
            # Or: df.plot(x='datetime', y='value')
            df.insert(0, 'datetime', df.index)

            # Add metadata as attributes
            df.attrs['pathname'] = pathname
            df.attrs['units'] = str(tsc.units) if tsc.units else ""
            df.attrs['type'] = str(tsc.type) if tsc.type else ""
            df.attrs['interval'] = (
                int(tsc.interval) if hasattr(tsc, 'interval') else None
            )
            df.attrs['dss_file'] = dss_file

            return df

        finally:
            dss.done()

    @staticmethod
    def _hec_time_to_datetime(hec_time_minutes: int) -> 'pd.Timestamp':
        """
        Convert HEC time (minutes since 1899-12-31) to Python datetime.

        Args:
            hec_time_minutes: Minutes since HEC epoch (1899-12-31 00:00:00)

        Returns:
            pandas Timestamp
        """
        HEC_EPOCH = pd.Timestamp('1899-12-31 00:00:00')
        return HEC_EPOCH + pd.Timedelta(minutes=int(hec_time_minutes))

    @staticmethod
    def get_peak_value(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract ONLY peak value from DSS without loading full time series.

        Uses HecDss API to read values array, calculates statistics immediately
        in NumPy, and returns only peak metadata. This avoids DataFrame overhead.

        Args:
            dss_file: Path to DSS file
            pathname: DSS pathname to read

        Returns:
            Dictionary with:
                - peak_flow: Maximum value (float)
                - peak_time: Time of maximum (datetime)
                - units: Engineering units (str)
                - count: Number of timesteps (int)
                - min_value: Minimum value (float)
                - mean_value: Mean value (float)
            Returns None if path doesn't exist or read fails

        Memory: ~200 bytes vs ~70 KB for full time series

        Example:
            >>> peak_info = DssCore.get_peak_value("results.dss", "//OUTLET/FLOW/.../")
            >>> print(f"Peak: {peak_info['peak_flow']} {peak_info['units']}")
        """
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

        # Open DSS file
        dss = HecDss.open(str(dss_file.resolve()))

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
            values = np.array(tsc.values)  # Java double[] -> numpy array
            times = np.array(tsc.times)    # Java int[] -> numpy array (minutes since 1899-12-31)

            # Validate that we got data
            if len(values) == 0 or len(times) == 0:
                logger.warning(f"No data found in time series for pathname: {pathname}")
                return None

            if len(values) != len(times):
                logger.warning(
                    f"Mismatched array lengths: {len(values)} values, {len(times)} times"
                )
                return None

            # Calculate statistics immediately in NumPy - no DataFrame overhead
            peak_idx = int(np.argmax(values))
            peak_value = float(values[peak_idx])
            peak_time_minutes = int(times[peak_idx])

            # Convert peak time to datetime
            peak_time = DssCore._hec_time_to_datetime(peak_time_minutes)

            # Calculate additional statistics
            min_value = float(np.min(values))
            mean_value = float(np.mean(values))
            count = len(values)

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
            dss.done()

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
        # Don't strip leading/trailing slashes - empty parts are significant!
        # DSS pathnames: /A/B/C/D/E/F/ or //B/C/D/E/F/ (empty A-part)
        parts = pathname.split('/')

        # Remove only the first and last empty strings from split (the slashes at start/end)
        # But keep internal empty strings (which represent empty pathname parts)
        if parts and parts[0] == '':
            parts = parts[1:]  # Remove leading empty string from first /
        if parts and parts[-1] == '':
            parts = parts[:-1]  # Remove trailing empty string from last /

        result = {
            'A': parts[0] if len(parts) > 0 else '',
            'B': parts[1] if len(parts) > 1 else '',
            'C': parts[2] if len(parts) > 2 else '',
            'D': parts[3] if len(parts) > 3 else '',
            'E': parts[4] if len(parts) > 4 else '',
            'F': parts[5] if len(parts) > 5 else '',
            'full_path': pathname
        }

        # Extract element name (B part)
        result['element_name'] = result['B']

        # Extract data type (C part)
        result['data_type'] = result['C']

        # Extract time interval (E part)
        result['time_interval'] = result['E']

        # Extract run name from F part if present
        if result['F'].startswith('RUN:'):
            result['run_name'] = result['F'][4:]
        else:
            result['run_name'] = result['F']

        return result

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
        f_part = f"RUN:{run_name}" if run_name else ""
        return f"/{basin}/{element}/{data_type}/{date_block}/{interval}/{f_part}/"

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
        filtered = catalog

        if pattern:
            regex = re.compile(pattern, re.IGNORECASE)
            filtered = [p for p in filtered if regex.search(p)]

        if data_type:
            filtered = [
                p for p in filtered
                if len(p.split('/')) >= 4 and data_type.upper() in p.split('/')[3].upper()
            ]

        if element:
            filtered = [
                p for p in filtered
                if len(p.split('/')) >= 3 and element.upper() in p.split('/')[2].upper()
            ]

        return filtered

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
        and other X-Y relationships.

        Args:
            dss_file: Path to DSS file (created if doesn't exist)
            pathname: DSS pathname (e.g., "//TX_R3/FIRST-QUARTILE/24HR///50%/")
            x_values: X coordinates (e.g., time in hours)
            y_values: Y coordinates (e.g., cumulative fraction 0-1)
            x_units: Units for X values (default: "HOURS")
            y_units: Units for Y values (default: "FRACTION")
            x_label: Label for X axis (default: "TIME")
            y_label: Label for Y axis (default: "CUMULATIVE")

        Returns:
            True if write succeeded, False otherwise

        Example:
            >>> x = np.linspace(0, 24, 49)  # 0 to 24 hours
            >>> y = np.linspace(0, 1, 49)   # 0 to 100% cumulative
            >>> DssCore.write_paired_data(
            ...     "temporal.dss",
            ...     "//TX_R3/ALL-CASES/24HR///50%/",
            ...     x, y
            ... )
        """
        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass

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

            # Write to DSS file
            dss.put(container)

            logger.info(f"Wrote paired data to {pathname}")
            return True

        except Exception as e:
            logger.error(f"Error writing paired data to {pathname}: {e}")
            return False

        finally:
            dss.done()

    @staticmethod
    def write_multiple_paired_data(
        dss_file: Union[str, Path],
        paired_data_records: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        Write multiple paired data records to DSS file.

        More efficient than calling write_paired_data repeatedly as it
        keeps the DSS file open for all writes.

        Args:
            dss_file: Path to DSS file
            paired_data_records: List of dicts with keys:
                - pathname: DSS pathname
                - x_values: numpy array of X values
                - y_values: numpy array of Y values
                - x_units: (optional) X units
                - y_units: (optional) Y units
                - x_label: (optional) X label
                - y_label: (optional) Y label

        Returns:
            Dict mapping pathname to success status (True/False)

        Example:
            >>> records = [
            ...     {"pathname": "//A/B/C///D/", "x_values": x1, "y_values": y1},
            ...     {"pathname": "//A/E/C///D/", "x_values": x2, "y_values": y2},
            ... ]
            >>> results = DssCore.write_multiple_paired_data("file.dss", records)
        """
        # Configure JVM (must be before first jnius import)
        DssCore._configure_jvm()

        # Import Java classes via pyjnius (lazy)
        from jnius import autoclass

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

                    # Write to DSS
                    dss.put(container)
                    results[pathname] = True

                except Exception as e:
                    logger.error(f"Error writing {pathname}: {e}")
                    results[pathname] = False

            logger.info(f"Wrote {sum(results.values())}/{len(results)} paired data records")

        finally:
            dss.done()

        return results

    @staticmethod
    def read_paired_data(
        dss_file: Union[str, Path],
        pathname: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read paired data (X-Y curve) from DSS file.

        Args:
            dss_file: Path to DSS file
            pathname: DSS pathname for paired data

        Returns:
            Dictionary with:
                - x_values: numpy array of X values
                - y_values: numpy array of Y values
                - x_units: X axis units
                - y_units: Y axis units
                - x_label: X axis label
                - y_label: Y axis label
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

        # Open DSS file
        dss = HecDss.open(str(dss_file.resolve()))

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
            dss.done()

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
