"""
HmsDss - DSS File Operations for HEC-HMS

This module provides static methods for reading and writing HEC-DSS files
commonly used with HEC-HMS for time-series input/output.

hms-commander includes its own standalone DSS implementation using HEC Monolith
libraries via pyjnius. No external dependencies like ras-commander are required.

Dependencies:
    Required at runtime (lazy loaded):
        - pyjnius: pip install pyjnius
        - Java JRE/JDK 8+: Must be installed and JAVA_HOME set

    Auto-downloaded on first use:
        - HEC Monolith libraries (~20 MB, cached in ~/.hms-commander/dss/)

All methods are static and designed to be used without instantiation.
"""

import gc
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call

logger = get_logger(__name__)

# Import standalone DSS core - this is now the primary implementation
try:
    from .dss import DssCore
    DSS_AVAILABLE = True
    logger.debug("Standalone DssCore available")
except ImportError as e:
    DSS_AVAILABLE = False
    logger.warning(f"DssCore import failed: {e}")


class HmsDss:
    """
    DSS file operations for HMS input/output.

    Uses hms-commander's standalone DSS implementation powered by HEC Monolith
    libraries. Provides HMS-specific convenience methods for working with
    precipitation, discharge, and other hydrologic time series.

    All methods are static - no instantiation required.

    Dependencies:
        - pyjnius (pip install pyjnius)
        - Java 8+ (JRE or JDK)
        - HEC Monolith libraries (auto-downloaded on first use)

    Example:
        >>> from hms_commander import HmsDss
        >>> catalog = HmsDss.get_catalog("results.dss")
        >>> ts = HmsDss.read_timeseries("results.dss", "/BASIN/OUTLET/FLOW//15MIN/RUN:RUN1/")
        >>> print(f"Units: {ts.attrs['units']}")
    """

    # Common HMS DSS path patterns (C-part matching)
    # HMS uses formats like FLOW, FLOW-OBSERVED, FLOW-DIRECT, FLOW-BASE, etc.
    HMS_RESULT_PATTERNS = {
        'flow': r'/FLOW[^/]*/|/FLOW/',             # Matches FLOW, FLOW-DIRECT, FLOW-COMBINE, etc.
        'flow-total': r'/FLOW/',                    # Only total FLOW
        'flow-observed': r'/FLOW-OBSERVED/',
        'flow-direct': r'/FLOW-DIRECT/',
        'flow-base': r'/FLOW-BASE/',
        'flow-combine': r'/FLOW-COMBINE/',
        'precipitation': r'/PRECIP[^/]*/|/PRECIP/', # Matches PRECIP, PRECIP-INC, PRECIP-CUM
        'precip-inc': r'/PRECIP-INC/',
        'precip-cum': r'/PRECIP-CUM/',
        'precip-excess': r'/PRECIP-EXCESS/',
        'precip-loss': r'/PRECIP-LOSS/',
        'stage': r'/STAGE/',
        'storage': r'/STORAGE[^/]*/|/STORAGE/',
        'storage-gw': r'/STORAGE-GW/',
        'storage-soil': r'/STORAGE-SOIL/',
        'elevation': r'/ELEV/',
        'outflow': r'/OUTFLOW[^/]*/|/OUTFLOW/',
        'inflow': r'/INFLOW[^/]*/|/INFLOW/',
        'excess': r'/EXCESS[^/]*/|/EXCESS/',
        'baseflow': r'/BASEFLOW/',
        'infiltration': r'/INFILTRATION/',
        'et': r'/ET[^/]*/|/ET/',
    }

    @staticmethod
    def is_available() -> bool:
        """
        Check if full DSS functionality is available.

        Returns:
            True if pyjnius can be imported and DSS operations will work

        Example:
            >>> if HmsDss.is_available():
            ...     catalog = HmsDss.get_catalog("file.dss")
            ... else:
            ...     print("Install pyjnius: pip install pyjnius")
        """
        if not DSS_AVAILABLE:
            return False
        return DssCore.is_available()

    @staticmethod
    @log_call
    def get_catalog(
        dss_file: Union[str, Path]
    ) -> List[str]:
        """
        Get catalog of all paths in a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            List of DSS pathnames

        Example:
            >>> paths = HmsDss.get_catalog("results.dss")
            >>> for path in paths:
            ...     print(path)
        """
        dss_file = Path(dss_file)

        if not dss_file.exists():
            raise FileNotFoundError(f"DSS file not found: {dss_file}")

        if not DSS_AVAILABLE:
            raise ImportError(
                "DSS functionality requires pyjnius.\n"
                "Install with: pip install pyjnius\n"
                "Also requires Java 8+ (JRE or JDK)"
            )

        return DssCore.get_catalog(dss_file)

    @staticmethod
    @log_call
    def read_timeseries(
        dss_file: Union[str, Path],
        pathname: str
    ) -> pd.DataFrame:
        """
        Read a time series from a DSS file.

        Args:
            dss_file: Path to the DSS file
            pathname: DSS pathname to read

        Returns:
            DataFrame with:
            - DatetimeIndex for time series operations
            - 'datetime' column for plotting (same as index)
            - 'value' column with time series data
            - Metadata via df.attrs: pathname, units, type, interval

        Example:
            >>> ts = HmsDss.read_timeseries(
            ...     "results.dss",
            ...     "/BASIN/OUTLET/FLOW//15MIN/RUN:RUN1/"
            ... )
            >>> print(ts.head())
            >>> print(f"Units: {ts.attrs['units']}")
            >>>
            >>> # Plotting options:
            >>> ax.plot(ts['datetime'], ts['value'])    # Using datetime column
            >>> ax.plot(ts.index, ts['value'])          # Using DatetimeIndex
            >>> ts.plot(y='value')                      # Pandas automatic
        """
        dss_file = Path(dss_file)

        if not dss_file.exists():
            raise FileNotFoundError(f"DSS file not found: {dss_file}")

        if not DSS_AVAILABLE:
            raise ImportError(
                "DSS functionality requires pyjnius.\n"
                "Install with: pip install pyjnius"
            )

        return DssCore.read_timeseries(dss_file, pathname)

    @staticmethod
    @log_call
    def read_multiple_timeseries(
        dss_file: Union[str, Path],
        pathnames: List[str]
    ) -> Dict[str, pd.DataFrame]:
        """
        Read multiple time series from a DSS file.

        Args:
            dss_file: Path to the DSS file
            pathnames: List of DSS pathnames to read

        Returns:
            Dictionary mapping pathnames to DataFrames (None on failure)

        Example:
            >>> paths = ["/BASIN/SUB1/FLOW//15MIN/RUN1/", "/BASIN/SUB2/FLOW//15MIN/RUN1/"]
            >>> data = HmsDss.read_multiple_timeseries("results.dss", paths)
            >>> for path, df in data.items():
            ...     if df is not None:
            ...         print(f"{path}: {len(df)} points")
        """
        dss_file = Path(dss_file)

        if not DSS_AVAILABLE:
            raise ImportError("DSS functionality requires pyjnius.")

        return DssCore.read_multiple_timeseries(dss_file, pathnames)

    @staticmethod
    @log_call
    def extract_hms_results(
        dss_file: Union[str, Path],
        element_names: Optional[List[str]] = None,
        result_type: str = "flow"
    ) -> Dict[str, pd.DataFrame]:
        """
        Extract HMS simulation results from a DSS file.

        This is a convenience method that filters results by element name
        and result type.

        Args:
            dss_file: Path to the DSS file
            element_names: List of element names to extract (all if None)
            result_type: Type of result ("flow", "precipitation", "stage", etc.)

        Returns:
            Dictionary mapping element names to result DataFrames

        Example:
            >>> results = HmsDss.extract_hms_results(
            ...     "results.dss",
            ...     element_names=["Outlet", "Junction-1"],
            ...     result_type="flow"
            ... )
            >>> for name, df in results.items():
            ...     print(f"{name}: peak = {df['value'].max():.2f}")
        """
        dss_file = Path(dss_file)

        if not DSS_AVAILABLE:
            raise ImportError("DSS functionality requires pyjnius.")

        # Get catalog
        catalog = HmsDss.get_catalog(dss_file)

        # Filter by result type
        pattern = HmsDss.HMS_RESULT_PATTERNS.get(result_type.lower())
        if pattern:
            matching_paths = [p for p in catalog if re.search(pattern, p, re.IGNORECASE)]
        else:
            matching_paths = catalog

        # Filter by element names if specified
        if element_names:
            filtered_paths = []
            for path in matching_paths:
                parts = path.split('/')
                if len(parts) >= 3:
                    element = parts[2]  # B part is typically the element name
                    if element in element_names:
                        filtered_paths.append(path)
            matching_paths = filtered_paths

        # Read matching time series
        results = {}
        for path in matching_paths:
            parts = path.split('/')
            if len(parts) >= 3:
                element_name = parts[2]
                try:
                    df = HmsDss.read_timeseries(dss_file, path)
                    results[element_name] = df
                except Exception as e:
                    logger.warning(f"Could not read {path}: {e}")

        logger.info(f"Extracted {len(results)} result time series")
        return results

    @staticmethod
    @log_call
    def get_info(
        dss_file: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Get summary information about a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            Dictionary with file information including path count and data types

        Example:
            >>> info = HmsDss.get_info("results.dss")
            >>> print(f"Total paths: {info['num_paths']}")
            >>> print(f"Data types: {info['path_types']}")
        """
        dss_file = Path(dss_file)

        info = {
            'file_path': str(dss_file),
            'file_exists': dss_file.exists(),
            'file_size_mb': None,
            'num_paths': None,
            'path_types': {},
            'dss_available': DSS_AVAILABLE
        }

        if dss_file.exists():
            info['file_size_mb'] = round(dss_file.stat().st_size / (1024 * 1024), 2)

            if DSS_AVAILABLE:
                try:
                    catalog = HmsDss.get_catalog(dss_file)
                    info['num_paths'] = len(catalog)

                    # Categorize paths by C-part
                    for path in catalog:
                        parts = path.split('/')
                        if len(parts) >= 4:
                            data_type = parts[3]  # C part
                            info['path_types'][data_type] = info['path_types'].get(data_type, 0) + 1

                except Exception as e:
                    logger.warning(f"Could not read DSS catalog: {e}")

        return info

    @staticmethod
    @log_call
    def list_flow_results(
        dss_file: Union[str, Path]
    ) -> List[str]:
        """
        List all flow result pathnames in a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            List of flow result pathnames

        Example:
            >>> flows = HmsDss.list_flow_results("results.dss")
            >>> for path in flows:
            ...     parts = HmsDss.parse_dss_pathname(path)
            ...     print(f"{parts['element_name']}: {path}")
        """
        catalog = HmsDss.get_catalog(dss_file)
        pattern = HmsDss.HMS_RESULT_PATTERNS['flow']
        return [p for p in catalog if re.search(pattern, p, re.IGNORECASE)]

    @staticmethod
    @log_call
    def list_precipitation_data(
        dss_file: Union[str, Path]
    ) -> List[str]:
        """
        List all precipitation data pathnames in a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            List of precipitation pathnames
        """
        catalog = HmsDss.get_catalog(dss_file)
        # Match both PRECIP and PRECIP-INC/PRECIP-CUM
        results = []
        for p in catalog:
            if re.search(r'/[^/]+/[^/]+/PRECIP', p, re.IGNORECASE):
                results.append(p)
        return results

    @staticmethod
    @log_call
    def list_stage_results(
        dss_file: Union[str, Path]
    ) -> List[str]:
        """
        List all stage result pathnames in a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            List of stage result pathnames
        """
        catalog = HmsDss.get_catalog(dss_file)
        pattern = HmsDss.HMS_RESULT_PATTERNS['stage']
        return [p for p in catalog if re.search(pattern, p, re.IGNORECASE)]

    @staticmethod
    @log_call
    def list_storage_results(
        dss_file: Union[str, Path]
    ) -> List[str]:
        """
        List all storage result pathnames in a DSS file.

        Args:
            dss_file: Path to the DSS file

        Returns:
            List of storage result pathnames
        """
        catalog = HmsDss.get_catalog(dss_file)
        pattern = HmsDss.HMS_RESULT_PATTERNS['storage']
        return [p for p in catalog if re.search(pattern, p, re.IGNORECASE)]

    @staticmethod
    @log_call
    def parse_dss_pathname(pathname: str) -> Dict[str, str]:
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
            Dictionary with pathname components including convenience fields

        Example:
            >>> parts = HmsDss.parse_dss_pathname("/BASIN/OUTLET/FLOW//15MIN/RUN:RUN1/")
            >>> print(parts['element_name'])  # 'OUTLET'
            >>> print(parts['data_type'])     # 'FLOW'
            >>> print(parts['run_name'])      # 'RUN1'
        """
        if DSS_AVAILABLE:
            return DssCore.parse_pathname(pathname)

        # Fallback implementation if DSS core not available
        # Don't strip - empty parts are significant (e.g., //B/C/D/E/F/ has empty A-part)
        parts = pathname.split('/')

        # Remove only the first and last empty strings (from leading/trailing slashes)
        if parts and parts[0] == '':
            parts = parts[1:]
        if parts and parts[-1] == '':
            parts = parts[:-1]

        result = {
            'A': parts[0] if len(parts) > 0 else '',
            'B': parts[1] if len(parts) > 1 else '',
            'C': parts[2] if len(parts) > 2 else '',
            'D': parts[3] if len(parts) > 3 else '',
            'E': parts[4] if len(parts) > 4 else '',
            'F': parts[5] if len(parts) > 5 else '',
            'full_path': pathname
        }

        result['element_name'] = result['B']
        result['data_type'] = result['C']
        result['time_interval'] = result['E']

        if result['F'].startswith('RUN:'):
            result['run_name'] = result['F'][4:]
        else:
            result['run_name'] = result['F']

        return result

    @staticmethod
    @log_call
    def create_dss_pathname(
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
            >>> path = HmsDss.create_dss_pathname(
            ...     "MYBASIN", "OUTLET", "FLOW", "15MIN", "RUN1"
            ... )
            >>> print(path)  # '/MYBASIN/OUTLET/FLOW//15MIN/RUN:RUN1/'
        """
        if DSS_AVAILABLE:
            return DssCore.create_pathname(basin, element, data_type, interval, run_name, date_block)

        # Fallback
        f_part = f"RUN:{run_name}" if run_name else ""
        return f"/{basin}/{element}/{data_type}/{date_block}/{interval}/{f_part}/"

    @staticmethod
    @log_call
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
            >>> paths = HmsDss.get_catalog("file.dss")
            >>> flow_paths = HmsDss.filter_catalog(paths, data_type="FLOW")
            >>> outlet_flows = HmsDss.filter_catalog(flow_paths, element="OUTLET")
        """
        if DSS_AVAILABLE:
            return DssCore.filter_catalog(catalog, pattern, data_type, element)

        # Fallback implementation
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
    @log_call
    def get_peak_flows(
        dss_file: Union[str, Path],
        element_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Extract peak flow values for all elements.

        Note:
            For large DSS files with many elements (100+), consider using
            get_peak_flows_batched() instead to avoid memory issues. That method
            processes elements in batches with garbage collection between batches.

        Args:
            dss_file: Path to the DSS file
            element_names: Optional list of element names to filter

        Returns:
            DataFrame with columns: element, peak_flow, peak_time, units

        Example:
            >>> peaks = HmsDss.get_peak_flows("results.dss")
            >>> print(peaks.sort_values('peak_flow', ascending=False))

        See Also:
            get_peak_flows_batched: Memory-efficient version for large files
        """
        results = HmsDss.extract_hms_results(dss_file, element_names, result_type="flow")

        records = []
        for element_name, df in results.items():
            if df is not None and not df.empty:
                peak_idx = df['value'].idxmax()
                records.append({
                    'element': element_name,
                    'peak_flow': df.loc[peak_idx, 'value'],
                    'peak_time': peak_idx,
                    'units': df.attrs.get('units', '')
                })

        return pd.DataFrame(records)

    @staticmethod
    @log_call
    def get_peak_flows_batched(
        dss_file: Union[str, Path],
        element_names: Optional[List[str]] = None,
        run_name: Optional[str] = None,
        batch_size: int = 50,
        progress: bool = True
    ) -> pd.DataFrame:
        """
        Extract peak flows in batches to avoid memory issues.

        Processes N elements at a time, garbage collects between batches,
        preventing memory exhaustion for large DSS files.

        Args:
            dss_file: Path to DSS file
            element_names: Optional filter for specific elements
            run_name: Optional filter for specific run (e.g., "1%(100YR)RUN")
            batch_size: Elements to process per batch (default: 50)
            progress: Show progress logging (default: True)

        Returns:
            DataFrame with columns:
                - element: Element name
                - peak_flow: Peak flow value (cfs)
                - peak_time: Time of peak (datetime)
                - units: Engineering units
                - dss_path: Full DSS pathname

        Memory: O(batch_size) instead of O(total_elements)

        Example:
            >>> # Safe for 1000+ elements
            >>> peaks = HmsDss.get_peak_flows_batched(
            ...     "results.dss",
            ...     run_name="1%(100YR)RUN",
            ...     batch_size=100  # Adjust for available memory
            ... )
        """
        dss_file = Path(dss_file)

        if not dss_file.exists():
            raise FileNotFoundError(f"DSS file not found: {dss_file}")

        if not DSS_AVAILABLE:
            raise ImportError(
                "DSS functionality requires pyjnius.\n"
                "Install with: pip install pyjnius\n"
                "Also requires Java 8+ (JRE or JDK)"
            )

        # Get all flow paths - use 'flow-total' pattern for /FLOW/ only (not FLOW-DIRECT, etc.)
        catalog = HmsDss.get_catalog(dss_file)
        flow_total_pattern = HmsDss.HMS_RESULT_PATTERNS['flow-total']
        flow_paths = [p for p in catalog if re.search(flow_total_pattern, p, re.IGNORECASE)]

        # Exclude TABLE data (paired data, not time series)
        flow_paths = [p for p in flow_paths if '/TABLE/' not in p.upper()]

        # Filter by run_name if provided (F-part)
        if run_name:
            flow_paths = [p for p in flow_paths if run_name.upper() in p.upper()]

        # Filter by element_names if provided
        if element_names:
            filtered_paths = []
            for path in flow_paths:
                parts = HmsDss.parse_dss_pathname(path)
                if parts['element_name'] in element_names:
                    filtered_paths.append(path)
            flow_paths = filtered_paths

        total_paths = len(flow_paths)
        if total_paths == 0:
            logger.info("No flow paths found in DSS file")
            return pd.DataFrame(columns=['element', 'peak_flow', 'peak_time', 'units', 'dss_path'])

        if progress:
            logger.info(f"Extracting peaks from {total_paths} paths...")

        records = []
        total_batches = (total_paths + batch_size - 1) // batch_size  # Ceiling division

        for i in range(0, total_paths, batch_size):
            batch_num = i // batch_size + 1
            batch_paths = flow_paths[i:i + batch_size]

            if progress:
                logger.info(f"Batch {batch_num}/{total_batches}: processing {len(batch_paths)} paths...")

            # Process each path in the batch
            for path in batch_paths:
                try:
                    parts = HmsDss.parse_dss_pathname(path)

                    # Use peak-only extraction (350x more memory efficient)
                    peak_info = DssCore.get_peak_value(dss_file, path)

                    if peak_info is not None:
                        records.append({
                            'element': parts['element_name'],
                            'peak_flow': peak_info['peak_flow'],
                            'peak_time': peak_info['peak_time'],
                            'units': peak_info['units'],
                            'dss_path': path
                        })

                except Exception as e:
                    logger.warning(f"Could not read {path}: {e}")

            # Garbage collect after each batch to free memory
            gc.collect()

        # Create DataFrame from records
        result_df = pd.DataFrame(records)

        # Sort by peak_flow descending
        if not result_df.empty:
            result_df = result_df.sort_values('peak_flow', ascending=False).reset_index(drop=True)

        if progress:
            logger.info(f"Extracted peak flows for {len(result_df)} elements")
        return result_df

    @staticmethod
    @log_call
    def get_total_precipitation(
        dss_file: Union[str, Path],
        element_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Calculate total precipitation for all elements.

        Args:
            dss_file: Path to the DSS file
            element_names: Optional list of element names to filter

        Returns:
            DataFrame with columns: element, total_precip, units, num_intervals

        Example:
            >>> precip = HmsDss.get_total_precipitation("results.dss")
            >>> print(precip)
        """
        results = HmsDss.extract_hms_results(
            dss_file, element_names, result_type="precipitation"
        )

        records = []
        for element_name, df in results.items():
            if df is not None and not df.empty:
                records.append({
                    'element': element_name,
                    'total_precip': df['value'].sum(),
                    'units': df.attrs.get('units', ''),
                    'num_intervals': len(df)
                })

        return pd.DataFrame(records)
