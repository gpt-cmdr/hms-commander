"""
HmsResults - HEC-HMS Results Extraction and Analysis

This module provides static methods for extracting and analyzing HEC-HMS
simulation results from DSS files.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from .LoggingConfig import get_logger
from .Decorators import log_call
from .dss import HmsDss

logger = get_logger(__name__)


class HmsResults:
    """
    Extract and analyze HMS simulation results from DSS files.

    Provides high-level methods for accessing flow, precipitation, and
    other hydrologic results with statistical analysis.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsResults
        >>> flow = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
        >>> peaks = HmsResults.get_peak_flows("results.dss")
        >>> print(peaks)
    """

    @staticmethod
    @log_call
    def get_outflow_timeseries(
        dss_file: Union[str, Path],
        element_name: str,
        run_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get outflow time series for a specific element.

        Args:
            dss_file: Path to the DSS file
            element_name: Name of the element (junction, outlet, etc.)
            run_name: Optional run name filter

        Returns:
            DataFrame with datetime index and flow values

        Example:
            >>> flow = HmsResults.get_outflow_timeseries("results.dss", "Outlet")
            >>> print(flow.head())
        """
        dss_file = Path(dss_file)

        # Get catalog and find matching flow path
        catalog = HmsDss.get_catalog(dss_file)

        matching_paths = []
        for path in catalog:
            parts = HmsDss.parse_dss_pathname(path)
            if parts['element_name'].upper() == element_name.upper():
                if 'FLOW' in parts['data_type'].upper():
                    if run_name is None or parts['run_name'].upper() == run_name.upper():
                        matching_paths.append(path)

        if not matching_paths:
            raise ValueError(f"No flow data found for element '{element_name}'")

        # Read the first matching path (or most recent if multiple)
        path = matching_paths[0]
        logger.info(f"Reading flow data from: {path}")

        df = HmsDss.read_timeseries(dss_file, path)
        df.columns = ['flow']
        return df

    @staticmethod
    @log_call
    def get_precipitation_timeseries(
        dss_file: Union[str, Path],
        element_name: str,
        run_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get precipitation time series for a specific element.

        Args:
            dss_file: Path to the DSS file
            element_name: Name of the subbasin or gage
            run_name: Optional run name filter

        Returns:
            DataFrame with datetime index and precipitation values
        """
        dss_file = Path(dss_file)
        catalog = HmsDss.get_catalog(dss_file)

        matching_paths = []
        for path in catalog:
            parts = HmsDss.parse_dss_pathname(path)
            if parts['element_name'].upper() == element_name.upper():
                if 'PRECIP' in parts['data_type'].upper():
                    if run_name is None or parts['run_name'].upper() == run_name.upper():
                        matching_paths.append(path)

        if not matching_paths:
            raise ValueError(f"No precipitation data found for element '{element_name}'")

        path = matching_paths[0]
        df = HmsDss.read_timeseries(dss_file, path)
        df.columns = ['precipitation']
        return df

    @staticmethod
    @log_call
    def get_peak_flows(
        dss_file: Union[str, Path],
        element_names: Optional[List[str]] = None,
        run_name: Optional[str] = None,
        batch_size: int = 50
    ) -> pd.DataFrame:
        """
        Get peak flow summary for all elements in a DSS file.

        Uses batched extraction for memory efficiency with large DSS files.
        Processing is done in batches to prevent memory exhaustion when
        extracting peaks from files with hundreds of elements.

        Args:
            dss_file: Path to the DSS file
            element_names: Optional list of element names to include
            run_name: Optional run name filter
            batch_size: Elements per batch (default: 50, increase for more RAM)

        Returns:
            DataFrame with columns:
                - element: Element name
                - peak_flow: Peak flow value (cfs)
                - peak_time: Time of peak (datetime)
                - units: Engineering units
                - dss_path: Full DSS pathname

        Example:
            >>> from hms_commander import HmsResults
            >>> peaks = HmsResults.get_peak_flows("results.dss")
            >>> print(peaks.nlargest(10, 'peak_flow'))

        Note:
            For very large DSS files (1000+ elements), you can adjust
            batch_size based on available memory. Lower values use less
            memory but take longer to process.
        """
        dss_file = Path(dss_file)

        # If run_name filter specified, get paths and filter element names
        if run_name:
            flow_paths = HmsDss.list_flow_results(dss_file)
            matching_elements = set()
            for path in flow_paths:
                parts = HmsDss.parse_dss_pathname(path)
                if parts['run_name'].upper() == run_name.upper():
                    matching_elements.add(parts['element_name'])

            # Combine with any user-specified element_names filter
            if element_names:
                element_names = [e for e in element_names if e in matching_elements]
            else:
                element_names = list(matching_elements)

            if not element_names:
                logger.info(f"No elements found for run_name '{run_name}'")
                return pd.DataFrame(columns=['element', 'peak_flow', 'peak_time', 'units', 'dss_path'])

        # Delegate to batched implementation
        return HmsDss.get_peak_flows_batched(
            dss_file,
            element_names=element_names,
            batch_size=batch_size,
            progress=True
        )

    @staticmethod
    @log_call
    def get_volume_summary(
        dss_file: Union[str, Path],
        run_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get runoff volume summary for all elements.

        Args:
            dss_file: Path to the DSS file
            run_name: Optional run name filter
            start_time: Optional start time for volume calculation
            end_time: Optional end time for volume calculation

        Returns:
            DataFrame with element names and total volumes

        Example:
            >>> volumes = HmsResults.get_volume_summary("results.dss")
            >>> print(volumes)
        """
        dss_file = Path(dss_file)
        flow_paths = HmsDss.list_flow_results(dss_file)

        if run_name:
            flow_paths = [
                p for p in flow_paths
                if HmsDss.parse_dss_pathname(p)['run_name'].upper() == run_name.upper()
            ]

        records = []
        for path in flow_paths:
            try:
                parts = HmsDss.parse_dss_pathname(path)
                df = HmsDss.read_timeseries(dss_file, path)

                if df.empty:
                    continue

                # Filter by time window if specified
                if start_time:
                    df = df[df.index >= start_time]
                if end_time:
                    df = df[df.index <= end_time]

                if df.empty:
                    continue

                # Calculate volume (trapezoidal integration)
                # Assuming flow in CFS and time in hours
                time_diff = df.index.to_series().diff().dt.total_seconds() / 3600  # hours
                flow_values = df.iloc[:, 0].values

                # Volume in acre-feet (CFS * hours * 0.0413)
                volume_af = np.trapz(flow_values, dx=time_diff.mean()) * time_diff.mean() * 0.0413

                records.append({
                    'element': parts['element_name'],
                    'total_volume_af': round(volume_af, 2),
                    'mean_flow': round(df.iloc[:, 0].mean(), 2),
                    'duration_hours': round((df.index[-1] - df.index[0]).total_seconds() / 3600, 2),
                    'run_name': parts['run_name']
                })

            except Exception as e:
                logger.warning(f"Could not process {path}: {e}")

        df = pd.DataFrame(records)
        if not df.empty:
            df = df.sort_values('total_volume_af', ascending=False)

        return df

    @staticmethod
    @log_call
    def get_hydrograph_statistics(
        dss_file: Union[str, Path],
        element_name: str,
        run_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive statistics for a flow hydrograph.

        Args:
            dss_file: Path to the DSS file
            element_name: Name of the element
            run_name: Optional run name filter

        Returns:
            Dictionary with hydrograph statistics

        Example:
            >>> stats = HmsResults.get_hydrograph_statistics("results.dss", "Outlet")
            >>> print(f"Peak: {stats['peak_flow']} cfs at {stats['peak_time']}")
        """
        df = HmsResults.get_outflow_timeseries(dss_file, element_name, run_name)

        if df.empty:
            return {}

        flow = df['flow']

        stats = {
            'element': element_name,
            'start_time': df.index[0],
            'end_time': df.index[-1],
            'duration_hours': (df.index[-1] - df.index[0]).total_seconds() / 3600,

            # Flow statistics
            'peak_flow': flow.max(),
            'peak_time': flow.idxmax(),
            'min_flow': flow.min(),
            'mean_flow': flow.mean(),
            'median_flow': flow.median(),
            'std_flow': flow.std(),

            # Volume
            'total_volume_af': None,

            # Timing
            'time_to_peak_hours': None,
            'centroid_time': None,
        }

        # Calculate volume (acre-feet)
        time_diff_hours = df.index.to_series().diff().dt.total_seconds() / 3600
        stats['total_volume_af'] = round(
            np.trapz(flow.values, dx=time_diff_hours.mean()) * time_diff_hours.mean() * 0.0413,
            2
        )

        # Time to peak from start
        stats['time_to_peak_hours'] = round(
            (stats['peak_time'] - stats['start_time']).total_seconds() / 3600,
            2
        )

        # Centroid time (flow-weighted average time)
        try:
            time_numeric = (df.index - df.index[0]).total_seconds() / 3600
            stats['centroid_time'] = round(
                np.average(time_numeric, weights=flow.values),
                2
            )
        except Exception:
            pass

        return stats

    @staticmethod
    @log_call
    def compare_runs(
        dss_files: Union[List[Union[str, Path]], Union[str, Path]],
        element_name: str,
        run_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Compare flow results from multiple runs.

        Args:
            dss_files: List of DSS files or single file with multiple runs
            element_name: Name of the element to compare
            run_names: Optional list of run names to compare

        Returns:
            DataFrame with time series from all runs for comparison

        Example:
            >>> comparison = HmsResults.compare_runs(
            ...     ["run1.dss", "run2.dss", "run3.dss"],
            ...     "Outlet"
            ... )
            >>> comparison.plot()
        """
        if isinstance(dss_files, (str, Path)):
            dss_files = [dss_files]

        all_series = {}

        for dss_file in dss_files:
            dss_file = Path(dss_file)

            try:
                # Get flow paths for this file
                flow_paths = HmsDss.list_flow_results(dss_file)

                for path in flow_paths:
                    parts = HmsDss.parse_dss_pathname(path)

                    if parts['element_name'].upper() != element_name.upper():
                        continue

                    if run_names and parts['run_name'] not in run_names:
                        continue

                    # Create unique key
                    key = f"{dss_file.stem}_{parts['run_name']}" if parts['run_name'] else dss_file.stem

                    df = HmsDss.read_timeseries(dss_file, path)
                    if not df.empty:
                        all_series[key] = df.iloc[:, 0]

            except Exception as e:
                logger.warning(f"Could not process {dss_file}: {e}")

        if not all_series:
            return pd.DataFrame()

        # Combine all series into a single DataFrame
        result = pd.DataFrame(all_series)
        logger.info(f"Compared {len(all_series)} runs for element '{element_name}'")

        return result

    @staticmethod
    @log_call
    def get_precipitation_summary(
        dss_file: Union[str, Path],
        run_name: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get precipitation summary for all subbasins.

        Args:
            dss_file: Path to the DSS file
            run_name: Optional run name filter

        Returns:
            DataFrame with precipitation statistics by subbasin
        """
        dss_file = Path(dss_file)
        precip_paths = HmsDss.list_precipitation_data(dss_file)

        if run_name:
            precip_paths = [
                p for p in precip_paths
                if HmsDss.parse_dss_pathname(p)['run_name'].upper() == run_name.upper()
            ]

        records = []
        for path in precip_paths:
            try:
                parts = HmsDss.parse_dss_pathname(path)
                df = HmsDss.read_timeseries(dss_file, path)

                if df.empty:
                    continue

                precip = df.iloc[:, 0]

                records.append({
                    'element': parts['element_name'],
                    'total_depth': round(precip.sum(), 2),
                    'max_intensity': round(precip.max(), 2),
                    'duration_hours': round((df.index[-1] - df.index[0]).total_seconds() / 3600, 2),
                    'run_name': parts['run_name']
                })

            except Exception as e:
                logger.warning(f"Could not process {path}: {e}")

        return pd.DataFrame(records)

    @staticmethod
    @log_call
    def export_results_to_csv(
        dss_file: Union[str, Path],
        output_folder: Union[str, Path],
        element_names: Optional[List[str]] = None,
        run_name: Optional[str] = None
    ) -> List[str]:
        """
        Export results to CSV files for external analysis.

        Args:
            dss_file: Path to the DSS file
            output_folder: Folder for output CSV files
            element_names: Optional list of elements to export
            run_name: Optional run name filter

        Returns:
            List of created CSV file paths

        Example:
            >>> files = HmsResults.export_results_to_csv(
            ...     "results.dss",
            ...     "csv_output",
            ...     element_names=["Outlet", "Junction-1"]
            ... )
        """
        dss_file = Path(dss_file)
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)

        created_files = []

        # Export flow results
        try:
            results = HmsDss.extract_hms_results(
                dss_file,
                element_names=element_names,
                result_type="flow"
            )

            for element, df in results.items():
                filename = f"flow_{element}.csv"
                filepath = output_folder / filename
                df.to_csv(filepath)
                created_files.append(str(filepath))
                logger.info(f"Exported: {filepath}")

        except Exception as e:
            logger.warning(f"Could not export flow results: {e}")

        # Export peak summary
        try:
            peaks = HmsResults.get_peak_flows(dss_file, run_name=run_name)
            if not peaks.empty:
                filepath = output_folder / "peak_flows_summary.csv"
                peaks.to_csv(filepath, index=False)
                created_files.append(str(filepath))

        except Exception as e:
            logger.warning(f"Could not export peak summary: {e}")

        # Export volume summary
        try:
            volumes = HmsResults.get_volume_summary(dss_file, run_name)
            if not volumes.empty:
                filepath = output_folder / "volume_summary.csv"
                volumes.to_csv(filepath, index=False)
                created_files.append(str(filepath))

        except Exception as e:
            logger.warning(f"Could not export volume summary: {e}")

        logger.info(f"Exported {len(created_files)} files to {output_folder}")
        return created_files
