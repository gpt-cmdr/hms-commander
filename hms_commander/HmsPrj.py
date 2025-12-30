"""
HmsPrj - HEC-HMS Project Manager

This module provides the HmsPrj class for managing HEC-HMS projects.
It is the ONLY stateful class in hms-commander - all other classes use static methods.

A global singleton `hms` object is available after calling init_hms_project().

DataFrames:
    hms_df: Project-level key-value attributes from .hms file
    basin_df: Basin models with component counts and methods
    subbasin_df: Detailed subbasin parameters (loss, transform, baseflow)
    met_df: Meteorologic models with precipitation methods
    control_df: Control specifications with parsed time windows
    run_df: Simulation runs with cross-references
    gage_df: Time-series gages with DSS references
    pdata_df: Paired data tables (storage-outflow, etc.)
"""

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime
import pandas as pd

from .LoggingConfig import get_logger, log_call

logger = get_logger(__name__)

# Global HMS project object (singleton)
hms = None


class HmsPrj:
    """
    HEC-HMS project manager - the ONLY stateful class.

    This class handles project initialization, file discovery, and maintains
    DataFrames of project components (basin models, met models, control specs, etc.).

    Attributes:
        project_folder (Path): Path to the HEC-HMS project folder
        project_name (str): Name of the project (without extension)
        project_file (Path): Full path to the .hms project file
        hms_version (str): HEC-HMS version detected from project file
        hms_exe_path (Path): Path to HEC-HMS executable
        initialized (bool): Whether the project has been initialized

    DataFrames:
        hms_df (pd.DataFrame): Project-level attributes
        basin_df (pd.DataFrame): Basin model files with component info
        met_df (pd.DataFrame): Meteorologic model files with precip methods
        control_df (pd.DataFrame): Control specification files with time windows
        run_df (pd.DataFrame): Simulation runs with configurations
        gage_df (pd.DataFrame): Time-series gage files with DSS info
        pdata_df (pd.DataFrame): Paired data tables

    Example:
        >>> from hms_commander import init_hms_project, hms
        >>> init_hms_project(r"C:/HMS_Projects/MyProject")
        >>> print(hms.hms_df)
        >>> print(hms.basin_df)
        >>> print(hms.run_df)
    """

    def __init__(self):
        """Initialize an empty HmsPrj instance."""
        self.project_folder: Optional[Path] = None
        self.project_name: Optional[str] = None
        self.project_file: Optional[Path] = None
        self.hms_version: Optional[str] = None
        self.hms_exe_path: Optional[Path] = None
        self.initialized: bool = False

        # DataFrames for project components
        self.hms_df: pd.DataFrame = pd.DataFrame()      # Project attributes
        self.basin_df: pd.DataFrame = pd.DataFrame()    # Basin model summary
        self.subbasin_df: pd.DataFrame = pd.DataFrame() # Detailed subbasin parameters
        self.met_df: pd.DataFrame = pd.DataFrame()
        self.control_df: pd.DataFrame = pd.DataFrame()
        self.run_df: pd.DataFrame = pd.DataFrame()
        self.gage_df: pd.DataFrame = pd.DataFrame()
        self.pdata_df: pd.DataFrame = pd.DataFrame()    # Paired data

        # Raw parsed data from project files
        self._project_data: Dict[str, Any] = {}
        self._project_blocks: Dict[str, List[Dict[str, str]]] = {}

    def check_initialized(self) -> bool:
        """Check if the project has been initialized.

        Returns:
            bool: True if initialized

        Raises:
            RuntimeError: If project is not initialized
        """
        if not self.initialized:
            raise RuntimeError(
                "HMS project not initialized. Call init_hms_project() first."
            )
        return True

    @staticmethod
    def find_hms_project(folder_path: Union[str, Path]) -> Optional[Path]:
        """Find the .hms project file in a folder.

        Args:
            folder_path: Path to the folder to search

        Returns:
            Path to the .hms file, or None if not found

        Example:
            >>> hms_file = HmsPrj.find_hms_project(r"C:/HMS_Projects/MyProject")
            >>> print(hms_file)
            C:/HMS_Projects/MyProject/MyProject.hms
        """
        folder = Path(folder_path)
        if not folder.is_dir():
            logger.error(f"Folder does not exist: {folder}")
            return None

        # Look for .hms files
        hms_files = list(folder.glob("*.hms"))

        if not hms_files:
            logger.warning(f"No .hms file found in: {folder}")
            return None

        if len(hms_files) > 1:
            logger.warning(
                f"Multiple .hms files found in {folder}, using: {hms_files[0]}"
            )

        return hms_files[0]

    def initialize(
        self,
        project_folder: Union[str, Path],
        hms_exe_path: Optional[Union[str, Path]] = None,
        load_dss_metadata: bool = False
    ) -> 'HmsPrj':
        """Initialize the HMS project from a folder.

        Args:
            project_folder: Path to the HEC-HMS project folder
            hms_exe_path: Optional path to HEC-HMS executable
            load_dss_metadata: If True, read DSS files to populate time ranges

        Returns:
            Self for chaining

        Raises:
            FileNotFoundError: If project folder or .hms file not found
            ValueError: If project file cannot be parsed

        Example:
            >>> prj = HmsPrj()
            >>> prj.initialize(r"C:/HMS_Projects/MyProject")
        """
        self.project_folder = Path(project_folder)

        if not self.project_folder.is_dir():
            raise FileNotFoundError(
                f"Project folder does not exist: {self.project_folder}"
            )

        # Find the .hms project file
        self.project_file = self.find_hms_project(self.project_folder)

        if self.project_file is None:
            raise FileNotFoundError(
                f"No .hms file found in: {self.project_folder}"
            )

        self.project_name = self.project_file.stem

        # Set HMS executable path if provided
        if hms_exe_path:
            self.hms_exe_path = Path(hms_exe_path)

        # Parse the project file (block-based)
        self._parse_project_file()

        # Build all DataFrames
        self._build_hms_dataframe()
        self._build_basin_dataframe()
        self._build_subbasin_dataframe()  # Detailed subbasin parameters
        self._build_met_dataframe()
        self._build_control_dataframe()
        self._build_run_dataframe()
        self._build_gage_dataframe()
        self._build_pdata_dataframe()

        # Optionally load DSS metadata
        if load_dss_metadata:
            self._load_dss_metadata()

        self.initialized = True
        logger.info(f"HMS project initialized: {self.project_name}")
        logger.info(f"  Version: {self.hms_version}")
        logger.info(f"  Basin models: {len(self.basin_df)}")
        logger.info(f"  Met models: {len(self.met_df)}")
        logger.info(f"  Control specs: {len(self.control_df)}")
        logger.info(f"  Simulation runs: {len(self.run_df)}")
        logger.info(f"  Gages: {len(self.gage_df)}")
        logger.info(f"  Paired data tables: {len(self.pdata_df)}")

        return self

    def _read_file(self, file_path: Path) -> str:
        """Read file content with encoding fallback."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()

    def _parse_block(self, content: str) -> Tuple[str, str, Dict[str, str]]:
        """Parse a single HMS block.

        Returns:
            Tuple of (block_type, block_name, attributes_dict)
        """
        lines = content.strip().split('\n')
        if not lines:
            return '', '', {}

        # First line is "BlockType: BlockName"
        first_line = lines[0]
        if ':' not in first_line:
            return '', '', {}

        block_type, block_name = first_line.split(':', 1)
        block_type = block_type.strip()
        block_name = block_name.strip()

        # Parse remaining lines as key-value pairs
        attrs = {}
        for line in lines[1:]:
            line = line.strip()
            if line.startswith('End'):
                break
            if ':' in line:
                key, value = line.split(':', 1)
                attrs[key.strip()] = value.strip()

        return block_type, block_name, attrs

    def _parse_project_file(self) -> None:
        """Parse the .hms project file to extract all blocks.

        The .hms file format uses blocks like:
            Project: ProjectName
                 Description: ...
                 Version: 4.9
            End:

            Basin: BasinName
                 Filename: ...
            End:
        """
        logger.debug(f"Parsing project file: {self.project_file}")

        content = self._read_file(self.project_file)

        # Split into blocks (separated by "End:" followed by newlines)
        block_pattern = r'([A-Za-z][A-Za-z0-9 ]*:.*?End:)'
        blocks = re.findall(block_pattern, content, re.DOTALL)

        self._project_blocks = {}
        self._project_data = {}

        for block in blocks:
            block_type, block_name, attrs = self._parse_block(block)
            if not block_type:
                continue

            # Store in categorized dict
            if block_type not in self._project_blocks:
                self._project_blocks[block_type] = []

            self._project_blocks[block_type].append({
                'name': block_name,
                **attrs
            })

            # Extract project-level data
            if block_type == 'Project':
                self._project_data = {'name': block_name, **attrs}
                self.hms_version = attrs.get('Version', 'Unknown')

        logger.debug(f"Parsed {len(blocks)} blocks from project file")

    def _build_hms_dataframe(self) -> None:
        """Build the hms_df DataFrame with project-level attributes."""
        # Get project block attributes
        project_data = self._project_data

        records = []
        for key, value in project_data.items():
            records.append({
                'key': key,
                'value': value,
                'source': 'project'
            })

        # Add computed attributes
        records.append({
            'key': 'project_folder',
            'value': str(self.project_folder),
            'source': 'computed'
        })
        records.append({
            'key': 'project_file',
            'value': str(self.project_file),
            'source': 'computed'
        })
        records.append({
            'key': 'num_basins',
            'value': str(len(self._project_blocks.get('Basin', []))),
            'source': 'computed'
        })
        records.append({
            'key': 'num_met_models',
            'value': str(len(self._project_blocks.get('Precipitation', []))),
            'source': 'computed'
        })
        records.append({
            'key': 'num_controls',
            'value': str(len(self._project_blocks.get('Control', []))),
            'source': 'computed'
        })

        self.hms_df = pd.DataFrame(records)

    def _build_basin_dataframe(self) -> None:
        """Build the basin_df DataFrame with basin model information."""
        basin_blocks = self._project_blocks.get('Basin', [])

        records = []
        for block in basin_blocks:
            # Handle both HMS 3.x (FileName) and HMS 4.x (Filename) formats
            filename = block.get('Filename', block.get('FileName', ''))
            full_path = self.project_folder / filename if filename else None

            record = {
                'name': block.get('name', ''),
                'file_name': filename,
                'full_path': str(full_path) if full_path else '',
                'exists': full_path.exists() if full_path else False,
                'description': block.get('Description', ''),
                'last_modified_date': block.get('Last Modified Date', ''),
                'last_modified_time': block.get('Last Modified Time', ''),
            }

            # Parse basin file for additional details if it exists
            if full_path and full_path.exists():
                basin_info = self._parse_basin_summary(full_path)
                record.update(basin_info)
            else:
                record.update({
                    'num_subbasins': 0,
                    'num_reaches': 0,
                    'num_junctions': 0,
                    'num_reservoirs': 0,
                    'num_sources': 0,
                    'num_sinks': 0,
                    'total_area': 0.0,
                    'loss_methods': '',
                    'transform_methods': '',
                    'baseflow_methods': '',
                    'routing_methods': ''
                })

            records.append(record)

        self.basin_df = pd.DataFrame(records)

    def _parse_basin_summary(self, basin_path: Path) -> Dict[str, Any]:
        """Parse a basin file for summary information."""
        content = self._read_file(basin_path)

        # Count element types
        num_subbasins = len(re.findall(r'^Subbasin:', content, re.MULTILINE))
        num_reaches = len(re.findall(r'^Reach:', content, re.MULTILINE))
        num_junctions = len(re.findall(r'^Junction:', content, re.MULTILINE))
        num_reservoirs = len(re.findall(r'^Reservoir:', content, re.MULTILINE))
        num_sources = len(re.findall(r'^Source:', content, re.MULTILINE))
        num_sinks = len(re.findall(r'^Sink:', content, re.MULTILINE))

        # Extract areas and sum them
        areas = re.findall(r'Area:\s*([\d.]+)', content)
        total_area = sum(float(a) for a in areas) if areas else 0.0

        # Extract unique methods - HMS uses abbreviated field names:
        # LossRate:, Transform:, Baseflow:, Route: (not "Loss Method:", etc.)
        loss_methods = set(re.findall(r'^\s+LossRate:\s*(.+?)$', content, re.MULTILINE))
        transform_methods = set(re.findall(r'^\s+Transform:\s*(.+?)$', content, re.MULTILINE))
        baseflow_methods = set(re.findall(r'^\s+Baseflow:\s*(.+?)$', content, re.MULTILINE))
        routing_methods = set(re.findall(r'^\s+Route:\s*(.+?)$', content, re.MULTILINE))

        return {
            'num_subbasins': num_subbasins,
            'num_reaches': num_reaches,
            'num_junctions': num_junctions,
            'num_reservoirs': num_reservoirs,
            'num_sources': num_sources,
            'num_sinks': num_sinks,
            'total_area': round(total_area, 2),
            'loss_methods': ', '.join(sorted(loss_methods)),
            'transform_methods': ', '.join(sorted(transform_methods)),
            'baseflow_methods': ', '.join(sorted(baseflow_methods)),
            'routing_methods': ', '.join(sorted(routing_methods))
        }

    def _build_subbasin_dataframe(self) -> None:
        """Build the subbasin_df DataFrame with detailed subbasin parameters.

        Parses all basin files and extracts detailed parameters for each subbasin
        including loss, transform, and baseflow parameters.
        """
        records = []

        # Process each basin in basin_df
        for _, basin_row in self.basin_df.iterrows():
            basin_name = basin_row.get('name', '')
            basin_file = basin_row.get('full_path', '')

            if not basin_file or not Path(basin_file).exists():
                continue

            # Parse the basin file for subbasin details
            subbasins = self._parse_subbasin_details(Path(basin_file))

            for subbasin in subbasins:
                subbasin['basin_model'] = basin_name
                records.append(subbasin)

        self.subbasin_df = pd.DataFrame(records)
        logger.debug(f"Built subbasin_df with {len(records)} subbasins")

    def _parse_subbasin_details(self, basin_path: Path) -> List[Dict[str, Any]]:
        """Parse detailed subbasin information from a basin file.

        Args:
            basin_path: Path to the .basin file

        Returns:
            List of dictionaries with subbasin parameters
        """
        content = self._read_file(basin_path)
        subbasins = []

        # Find all Subbasin blocks
        pattern = r'Subbasin:\s*(.+?)\n(.*?)End:'
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            name = match[0].strip()
            block = match[1]

            # Parse all key-value pairs
            attrs = {}
            for line in block.splitlines():
                line = line.strip()
                if ':' in line and not line.startswith('End'):
                    key, value = line.split(':', 1)
                    attrs[key.strip()] = value.strip()

            record = {
                'name': name,
                'area': self._safe_float(attrs.get('Area')),
                'downstream': attrs.get('Downstream', ''),

                # Loss method and parameters
                'loss_method': attrs.get('LossRate', attrs.get('Loss', '')),
                'initial_deficit': self._safe_float(attrs.get('Initial Deficit')),
                'maximum_deficit': self._safe_float(attrs.get('Maximum Deficit')),
                'constant_rate': self._safe_float(attrs.get('Constant Rate')),
                'percolation_rate': self._safe_float(attrs.get('Percolation Rate')),
                'percent_impervious': self._safe_float(attrs.get('Percent Impervious Area')),
                'curve_number': self._safe_float(attrs.get('Curve Number')),
                'initial_abstraction': self._safe_float(attrs.get('Initial Abstraction')),

                # Transform method and parameters
                'transform_method': attrs.get('Transform', ''),
                'time_of_concentration': self._safe_float(attrs.get('Time of Concentration')),
                'storage_coefficient': self._safe_float(attrs.get('Storage Coefficient')),
                'lag_time': self._safe_float(attrs.get('Lag Time')),
                'snyder_tp': self._safe_float(attrs.get('Snyder Tp')),
                'snyder_cp': self._safe_float(attrs.get('Snyder Cp')),

                # Baseflow method and parameters
                'baseflow_method': attrs.get('Baseflow', ''),
                'recession_factor': self._safe_float(attrs.get('Recession Factor')),
                'initial_discharge': self._safe_float(attrs.get('Initial Discharge')),
                'gw1_initial': self._safe_float(attrs.get('GW 1 Initial')),
                'gw1_coefficient': self._safe_float(attrs.get('GW 1 Coefficient')),

                # Canvas position
                'canvas_x': self._safe_float(attrs.get('Canvas X')),
                'canvas_y': self._safe_float(attrs.get('Canvas Y')),

                # Source file
                'source_file': str(basin_path),
            }
            subbasins.append(record)

        return subbasins

    def _safe_float(self, value: Optional[str]) -> Optional[float]:
        """Safely convert a string to float, returning None on failure."""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _build_met_dataframe(self) -> None:
        """Build the met_df DataFrame with meteorologic model information."""
        met_blocks = self._project_blocks.get('Precipitation', [])

        records = []
        for block in met_blocks:
            # Handle both HMS 3.x (FileName) and HMS 4.x (Filename) formats
            filename = block.get('Filename', block.get('FileName', ''))
            full_path = self.project_folder / filename if filename else None

            record = {
                'name': block.get('name', ''),
                'file_name': filename,
                'full_path': str(full_path) if full_path else '',
                'exists': full_path.exists() if full_path else False,
                'description': block.get('Description', ''),
                'last_modified_date': block.get('Last Modified Date', ''),
                'last_modified_time': block.get('Last Modified Time', ''),
            }

            # Parse met file for additional details
            if full_path and full_path.exists():
                met_info = self._parse_met_summary(full_path)
                record.update(met_info)
            else:
                record.update({
                    'precip_method': '',
                    'et_method': '',
                    'snowmelt_method': '',
                    'num_subbasin_assignments': 0
                })

            records.append(record)

        self.met_df = pd.DataFrame(records)

    def _parse_met_summary(self, met_path: Path) -> Dict[str, Any]:
        """Parse a met file for summary information."""
        content = self._read_file(met_path)

        # Extract precipitation method from met model block
        precip_match = re.search(r'Precipitation Method:\s*(.+?)$', content, re.MULTILINE)
        precip_method = precip_match.group(1).strip() if precip_match else ''

        # ET method
        et_match = re.search(r'Evapotranspiration Method:\s*(.+?)$', content, re.MULTILINE)
        et_method = et_match.group(1).strip() if et_match else ''

        # Snowmelt method
        snow_match = re.search(r'Snowmelt Method:\s*(.+?)$', content, re.MULTILINE)
        snowmelt_method = snow_match.group(1).strip() if snow_match else ''

        # Count subbasin assignments
        num_assignments = len(re.findall(r'^Subbasin:', content, re.MULTILINE))

        return {
            'precip_method': precip_method,
            'et_method': et_method,
            'snowmelt_method': snowmelt_method,
            'num_subbasin_assignments': num_assignments
        }

    def _build_control_dataframe(self) -> None:
        """Build the control_df DataFrame with control specification information."""
        control_blocks = self._project_blocks.get('Control', [])

        records = []
        for block in control_blocks:
            filename = block.get('FileName', block.get('Filename', ''))
            full_path = self.project_folder / filename if filename else None

            record = {
                'name': block.get('name', ''),
                'file_name': filename,
                'full_path': str(full_path) if full_path else '',
                'exists': full_path.exists() if full_path else False,
                'description': block.get('Description', ''),
            }

            # Parse control file for time window
            if full_path and full_path.exists():
                control_info = self._parse_control_summary(full_path)
                record.update(control_info)
            else:
                record.update({
                    'start_date': None,
                    'end_date': None,
                    'time_interval': '',
                    'time_interval_minutes': 0,
                    'duration_hours': 0.0
                })

            records.append(record)

        self.control_df = pd.DataFrame(records)

    def _parse_control_summary(self, control_path: Path) -> Dict[str, Any]:
        """Parse a control file for time window information."""
        content = self._read_file(control_path)

        # Extract time window parameters
        start_date_match = re.search(r'Start Date:\s*(.+?)$', content, re.MULTILINE)
        start_time_match = re.search(r'Start Time:\s*(.+?)$', content, re.MULTILINE)
        end_date_match = re.search(r'End Date:\s*(.+?)$', content, re.MULTILINE)
        end_time_match = re.search(r'End Time:\s*(.+?)$', content, re.MULTILINE)
        interval_match = re.search(r'Time Interval:\s*(.+?)$', content, re.MULTILINE)

        start_date_str = start_date_match.group(1).strip() if start_date_match else ''
        start_time_str = start_time_match.group(1).strip() if start_time_match else '00:00'
        end_date_str = end_date_match.group(1).strip() if end_date_match else ''
        end_time_str = end_time_match.group(1).strip() if end_time_match else '00:00'
        time_interval = interval_match.group(1).strip() if interval_match else ''

        # Parse dates
        start_date = self._parse_hms_datetime(start_date_str, start_time_str)
        end_date = self._parse_hms_datetime(end_date_str, end_time_str)

        duration_hours = 0.0
        if start_date and end_date:
            duration_hours = (end_date - start_date).total_seconds() / 3600

        # Parse time interval to minutes
        interval_minutes = self._parse_interval_to_minutes(time_interval)

        return {
            'start_date': start_date,
            'end_date': end_date,
            'time_interval': time_interval,
            'time_interval_minutes': interval_minutes,
            'duration_hours': round(duration_hours, 2)
        }

    def _parse_hms_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse HMS date/time strings to datetime.

        HMS uses formats like:
        - Date: "16 January 1996" or "16January1996"
        - Time: "24:00" (midnight), "12:00", etc.
        """
        from datetime import timedelta

        if not date_str:
            return None

        # Handle 24:00 (midnight = start of next day)
        add_day = False
        if time_str == '24:00':
            time_str = '00:00'
            add_day = True

        # Try multiple date formats
        date_formats = [
            "%d %B %Y %H:%M",      # "16 January 1996 12:00"
            "%d%B%Y %H:%M",        # "16January1996 12:00"
            "%d %b %Y %H:%M",      # "16 Jan 1996 12:00"
            "%d%b%Y %H:%M",        # "16Jan1996 12:00"
        ]

        combined = f"{date_str} {time_str}"
        result = None

        for fmt in date_formats:
            try:
                result = datetime.strptime(combined, fmt)
                break
            except ValueError:
                continue

        if result and add_day:
            result = result + timedelta(days=1)

        return result

    def _parse_interval_to_minutes(self, interval_str: str) -> int:
        """Convert interval string to minutes.

        Handles:
        - Plain numbers (e.g., "60") -> assumes minutes
        - Strings like "15 Minutes", "1 Hour", "1 Day"
        """
        if not interval_str:
            return 0

        interval_str = interval_str.strip()

        # If it's just a number, assume minutes
        if interval_str.isdigit():
            return int(interval_str)

        # Match patterns like "15 Minutes", "1 Hour", "1 Day"
        match = re.match(r'(\d+)\s*(minute|hour|day)s?', interval_str, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            if unit == 'minute':
                return value
            elif unit == 'hour':
                return value * 60
            elif unit == 'day':
                return value * 1440

        return 0

    def _build_run_dataframe(self) -> None:
        """Build the run_df DataFrame from .run files."""
        run_records = []

        # Scan for .run files in the project folder
        run_files = list(self.project_folder.glob("*.run"))

        for run_file in run_files:
            runs = self._parse_run_file(run_file)
            run_records.extend(runs)

        self.run_df = pd.DataFrame(run_records)

    def _parse_run_file(self, run_path: Path) -> List[Dict[str, Any]]:
        """Parse a .run file to extract simulation run configurations."""
        content = self._read_file(run_path)

        # Find all Run: blocks
        block_pattern = r'(Run:.*?End:)'
        blocks = re.findall(block_pattern, content, re.DOTALL)

        runs = []
        for block in blocks:
            block_type, block_name, attrs = self._parse_block(block)
            if block_type != 'Run':
                continue

            runs.append({
                'name': block_name,
                'file_name': run_path.name,
                'full_path': str(run_path),
                'exists': True,
                'description': attrs.get('Description', ''),
                'basin_model': attrs.get('Basin', ''),
                'met_model': attrs.get('Precip', attrs.get('Precipitation', '')),
                'control_spec': attrs.get('Control', ''),
                'dss_file': attrs.get('DSS File', ''),
                'log_file': attrs.get('Log File', ''),
                'last_modified_date': attrs.get('Last Modified Date', ''),
                'last_modified_time': attrs.get('Last Modified Time', ''),
                'last_execution_date': attrs.get('Last Execution Date', ''),
                'last_execution_time': attrs.get('Last Execution Time', ''),
                'save_state_type': attrs.get('Save State Type', ''),
                'time_series_output': attrs.get('Time-Series Output', ''),
            })

        return runs

    def _build_gage_dataframe(self) -> None:
        """Build the gage_df DataFrame from .gage files."""
        gage_records = []

        # Scan for .gage files in the project folder
        gage_files = list(self.project_folder.glob("*.gage"))

        for gage_file in gage_files:
            gages = self._parse_gage_file(gage_file)
            gage_records.extend(gages)

        self.gage_df = pd.DataFrame(gage_records)

    def _parse_gage_file(self, gage_path: Path) -> List[Dict[str, Any]]:
        """Parse a .gage file to extract gage information."""
        content = self._read_file(gage_path)

        # Find all Gage: blocks
        block_pattern = r'(Gage:.*?End:)'
        blocks = re.findall(block_pattern, content, re.DOTALL)

        gages = []
        for block in blocks:
            # Skip the "Gage Manager:" header
            if 'Gage Manager:' in block and 'Gage Type:' not in block:
                continue

            block_type, block_name, attrs = self._parse_block(block)
            if block_type != 'Gage':
                continue

            # Parse DSS information
            dss_file = attrs.get('Filename', '')
            dss_pathname = attrs.get('Pathname', '')

            gages.append({
                'name': block_name,
                'gage_type': attrs.get('Gage Type', ''),
                'dss_file': dss_file,
                'dss_pathname': dss_pathname,
                'data_source_type': attrs.get('Data Source Type', ''),
                'last_modified_date': attrs.get('Last Modified Date', ''),
                'last_modified_time': attrs.get('Last Modified Time', ''),
                'reference_height': attrs.get('Reference Height', ''),
                'reference_height_units': attrs.get('Reference Height Units', ''),
                'source_file': str(gage_path),
                'has_dss_reference': bool(dss_file and dss_pathname),
            })

        return gages

    def _build_pdata_dataframe(self) -> None:
        """Build the pdata_df DataFrame from .pdata files."""
        pdata_records = []

        # Scan for .pdata files in the project folder
        pdata_files = list(self.project_folder.glob("*.pdata"))

        for pdata_file in pdata_files:
            tables = self._parse_pdata_file(pdata_file)
            pdata_records.extend(tables)

        self.pdata_df = pd.DataFrame(pdata_records)

    def _parse_pdata_file(self, pdata_path: Path) -> List[Dict[str, Any]]:
        """Parse a .pdata file to extract paired data tables."""
        content = self._read_file(pdata_path)

        # Find all Table: blocks
        block_pattern = r'(Table:.*?End:)'
        blocks = re.findall(block_pattern, content, re.DOTALL)

        tables = []
        for block in blocks:
            block_type, block_name, attrs = self._parse_block(block)
            if block_type != 'Table':
                continue

            tables.append({
                'name': block_name,
                'table_type': attrs.get('Table Type', ''),
                'description': attrs.get('Description', ''),
                'x_units': attrs.get('X-Units', ''),
                'y_units': attrs.get('Y-Units', ''),
                'dss_file': attrs.get('DSS File', ''),
                'dss_pathname': attrs.get('Pathname', ''),
                'use_external_dss': attrs.get('Use External DSS File', ''),
                'interpolation': attrs.get('Interpolation', ''),
                'last_modified_date': attrs.get('Last Modified Date', ''),
                'last_modified_time': attrs.get('Last Modified Time', ''),
                'source_file': str(pdata_path),
            })

        return tables

    def _load_dss_metadata(self) -> None:
        """Load DSS metadata to populate time ranges in gage_df.

        Only called if load_dss_metadata=True during initialization.
        """
        try:
            from .dss import HmsDss
            if not HmsDss.is_available():
                logger.warning("DSS functionality not available - skipping metadata")
                return
        except ImportError:
            logger.warning("HmsDss not available - skipping DSS metadata")
            return

        logger.info("Loading DSS metadata for gages...")

        for idx, row in self.gage_df.iterrows():
            if row['has_dss_reference']:
                dss_file = row['dss_file']
                dss_pathname = row['dss_pathname']

                # Resolve relative path
                dss_path = Path(dss_file)
                if not dss_path.is_absolute():
                    dss_path = self.project_folder / dss_file

                if dss_path.exists():
                    try:
                        df = HmsDss.read_timeseries(dss_path, dss_pathname)
                        self.gage_df.at[idx, 'dss_start_date'] = df.index.min()
                        self.gage_df.at[idx, 'dss_end_date'] = df.index.max()
                        self.gage_df.at[idx, 'dss_num_values'] = len(df)
                        self.gage_df.at[idx, 'dss_units'] = df.attrs.get('units', '')
                    except Exception as e:
                        logger.debug(f"Could not read DSS metadata for {row['name']}: {e}")

    # =========================================================================
    # Public accessor methods
    # =========================================================================

    def get_project_attribute(self, key: str) -> Optional[str]:
        """Get a project-level attribute by key.

        Args:
            key: Attribute key (e.g., 'Version', 'Description')

        Returns:
            Attribute value or None if not found
        """
        self.check_initialized()
        matches = self.hms_df[self.hms_df['key'] == key]
        if not matches.empty:
            return matches.iloc[0]['value']
        return None

    def get_basin_entries(self) -> pd.DataFrame:
        """Get DataFrame of basin model entries."""
        self.check_initialized()
        return self.basin_df.copy()

    def get_met_entries(self) -> pd.DataFrame:
        """Get DataFrame of meteorologic model entries."""
        self.check_initialized()
        return self.met_df.copy()

    def get_control_entries(self) -> pd.DataFrame:
        """Get DataFrame of control specification entries."""
        self.check_initialized()
        return self.control_df.copy()

    def get_run_entries(self) -> pd.DataFrame:
        """Get DataFrame of simulation run entries."""
        self.check_initialized()
        return self.run_df.copy()

    def get_gage_entries(self) -> pd.DataFrame:
        """Get DataFrame of time-series gage entries."""
        self.check_initialized()
        return self.gage_df.copy()

    def get_pdata_entries(self) -> pd.DataFrame:
        """Get DataFrame of paired data table entries."""
        self.check_initialized()
        return self.pdata_df.copy()

    def get_subbasin_entries(self, basin_name: Optional[str] = None) -> pd.DataFrame:
        """Get DataFrame of detailed subbasin parameters.

        Args:
            basin_name: Optional basin model name filter

        Returns:
            DataFrame with subbasin parameters
        """
        self.check_initialized()
        if basin_name and not self.subbasin_df.empty:
            return self.subbasin_df[self.subbasin_df['basin_model'] == basin_name].copy()
        return self.subbasin_df.copy()

    # =========================================================================
    # Computed properties
    # =========================================================================

    @property
    def total_area(self) -> float:
        """Total area of all basin models."""
        if self.basin_df.empty or 'total_area' not in self.basin_df.columns:
            return 0.0
        return self.basin_df['total_area'].sum()

    @property
    def dss_files(self) -> List[Path]:
        """List of all unique DSS files referenced in the project."""
        dss_set = set()

        # From gages
        if not self.gage_df.empty and 'dss_file' in self.gage_df.columns:
            for f in self.gage_df['dss_file'].dropna():
                if f:
                    dss_set.add(f)

        # From runs
        if not self.run_df.empty and 'dss_file' in self.run_df.columns:
            for f in self.run_df['dss_file'].dropna():
                if f:
                    dss_set.add(f)

        # From pdata
        if not self.pdata_df.empty and 'dss_file' in self.pdata_df.columns:
            for f in self.pdata_df['dss_file'].dropna():
                if f:
                    dss_set.add(f)

        # Resolve paths
        resolved = []
        for f in dss_set:
            p = Path(f)
            if not p.is_absolute():
                p = self.project_folder / f
            resolved.append(p)

        return sorted(resolved)

    @property
    def available_methods(self) -> Dict[str, List[str]]:
        """Dictionary of all hydrologic methods used by type."""
        methods = {
            'loss': [],
            'transform': [],
            'baseflow': [],
            'routing': [],
            'precipitation': [],
            'et': [],
            'snowmelt': []
        }

        if not self.basin_df.empty:
            for col, key in [('loss_methods', 'loss'),
                            ('transform_methods', 'transform'),
                            ('baseflow_methods', 'baseflow'),
                            ('routing_methods', 'routing')]:
                if col in self.basin_df.columns:
                    for val in self.basin_df[col].dropna():
                        if val:
                            methods[key].extend([m.strip() for m in val.split(',')])

        if not self.met_df.empty:
            for col, key in [('precip_method', 'precipitation'),
                            ('et_method', 'et'),
                            ('snowmelt_method', 'snowmelt')]:
                if col in self.met_df.columns:
                    for val in self.met_df[col].dropna():
                        if val:
                            methods[key].append(val)

        # Make unique
        return {k: sorted(set(v)) for k, v in methods.items()}

    def __repr__(self) -> str:
        """Return string representation of the project."""
        if not self.initialized:
            return "HmsPrj(not initialized)"
        return (
            f"HmsPrj(name='{self.project_name}', "
            f"version='{self.hms_version}', "
            f"basins={len(self.basin_df)}, "
            f"mets={len(self.met_df)}, "
            f"controls={len(self.control_df)}, "
            f"runs={len(self.run_df)}, "
            f"gages={len(self.gage_df)}, "
            f"pdata={len(self.pdata_df)})"
        )

    # =========================================================================
    # Run-based result retrieval methods
    # =========================================================================

    def get_run_dss_file(self, run_name: str) -> Optional[Path]:
        """Get the output DSS file path for a simulation run.

        Args:
            run_name: Name of the simulation run

        Returns:
            Path to the output DSS file, or None if not found

        Example:
            >>> dss_path = hms.get_run_dss_file("Run 1")
            >>> if dss_path.exists():
            ...     results = HmsResults.get_peak_flows(dss_path)
        """
        self.check_initialized()

        if self.run_df.empty:
            return None

        matches = self.run_df[self.run_df['name'] == run_name]
        if matches.empty:
            logger.warning(f"Run '{run_name}' not found in project")
            return None

        dss_file = matches.iloc[0].get('dss_file', '')
        if not dss_file:
            return None

        dss_path = Path(dss_file)
        if not dss_path.is_absolute():
            dss_path = self.project_folder / dss_file

        return dss_path

    def get_run_configuration(self, run_name: str) -> Dict[str, Any]:
        """Get full configuration for a simulation run.

        Returns the basin model, met model, and control spec details
        along with their associated file paths.

        Args:
            run_name: Name of the simulation run

        Returns:
            Dictionary with run configuration details

        Example:
            >>> config = hms.get_run_configuration("Run 1")
            >>> print(f"Basin: {config['basin_name']}")
            >>> print(f"Control: {config['control_start']} to {config['control_end']}")
        """
        self.check_initialized()

        if self.run_df.empty:
            raise ValueError("No runs found in project")

        matches = self.run_df[self.run_df['name'] == run_name]
        if matches.empty:
            raise ValueError(f"Run '{run_name}' not found in project")

        run = matches.iloc[0]
        config = {
            'run_name': run_name,
            'basin_name': run.get('basin_model', ''),
            'met_name': run.get('met_model', ''),
            'control_name': run.get('control_spec', ''),
            'dss_file': run.get('dss_file', ''),
        }

        # Get basin details
        if config['basin_name'] and not self.basin_df.empty:
            basin_matches = self.basin_df[self.basin_df['name'] == config['basin_name']]
            if not basin_matches.empty:
                basin = basin_matches.iloc[0]
                config['basin_area'] = basin.get('total_area', 0)
                config['basin_num_subbasins'] = basin.get('num_subbasins', 0)
                config['basin_file'] = basin.get('full_path', '')

        # Get met details
        if config['met_name'] and not self.met_df.empty:
            met_matches = self.met_df[self.met_df['name'] == config['met_name']]
            if not met_matches.empty:
                met = met_matches.iloc[0]
                config['met_precip_method'] = met.get('precip_method', '')
                config['met_file'] = met.get('full_path', '')

        # Get control details
        if config['control_name'] and not self.control_df.empty:
            ctrl_matches = self.control_df[self.control_df['name'] == config['control_name']]
            if not ctrl_matches.empty:
                ctrl = ctrl_matches.iloc[0]
                config['control_start'] = ctrl.get('start_date')
                config['control_end'] = ctrl.get('end_date')
                config['control_interval_minutes'] = ctrl.get('time_interval_minutes', 0)
                config['control_duration_hours'] = ctrl.get('duration_hours', 0)
                config['control_file'] = ctrl.get('full_path', '')

        return config

    def get_gage_by_name(self, gage_name: str) -> Optional[Dict[str, Any]]:
        """Get gage information by name.

        Args:
            gage_name: Name of the gage

        Returns:
            Dictionary with gage information, or None if not found
        """
        self.check_initialized()

        if self.gage_df.empty:
            return None

        matches = self.gage_df[self.gage_df['name'] == gage_name]
        if matches.empty:
            return None

        return matches.iloc[0].to_dict()

    def get_observed_dss_paths(self, gage_type: Optional[str] = None) -> List[Tuple[Path, str]]:
        """Get DSS file paths and pathnames for observed data gages.

        Args:
            gage_type: Optional filter by gage type ('Flow', 'Precipitation', etc.)

        Returns:
            List of (dss_file_path, dss_pathname) tuples

        Example:
            >>> flow_gages = hms.get_observed_dss_paths(gage_type='Flow')
            >>> for dss_path, pathname in flow_gages:
            ...     df = HmsDss.read_timeseries(dss_path, pathname)
        """
        self.check_initialized()
        results = []

        if self.gage_df.empty:
            return results

        df = self.gage_df
        if gage_type:
            df = df[df['gage_type'].str.upper() == gage_type.upper()]

        for _, row in df.iterrows():
            if row.get('has_dss_reference'):
                dss_file = row.get('dss_file', '')
                pathname = row.get('dss_pathname', '')

                if dss_file:
                    dss_path = Path(dss_file)
                    if not dss_path.is_absolute():
                        dss_path = self.project_folder / dss_file

                    results.append((dss_path, pathname))

        return results

    def list_run_names(self) -> List[str]:
        """Get list of all simulation run names.

        Returns:
            List of run names
        """
        self.check_initialized()
        if self.run_df.empty:
            return []
        return self.run_df['name'].tolist()

    def list_basin_names(self) -> List[str]:
        """Get list of all basin model names.

        Returns:
            List of basin names
        """
        self.check_initialized()
        if self.basin_df.empty:
            return []
        return self.basin_df['name'].tolist()

    def list_met_names(self) -> List[str]:
        """Get list of all meteorologic model names.

        Returns:
            List of met model names
        """
        self.check_initialized()
        if self.met_df.empty:
            return []
        return self.met_df['name'].tolist()

    def list_control_names(self) -> List[str]:
        """Get list of all control specification names.

        Returns:
            List of control spec names
        """
        self.check_initialized()
        if self.control_df.empty:
            return []
        return self.control_df['name'].tolist()

    def list_gage_names(self, gage_type: Optional[str] = None) -> List[str]:
        """Get list of all gage names, optionally filtered by type.

        Args:
            gage_type: Optional filter ('Flow', 'Precipitation', 'Stage', etc.)

        Returns:
            List of gage names
        """
        self.check_initialized()
        if self.gage_df.empty:
            return []

        df = self.gage_df
        if gage_type:
            df = df[df['gage_type'].str.upper() == gage_type.upper()]

        return df['name'].tolist()


def init_hms_project(
    project_folder: Union[str, Path],
    hms_exe_path: Optional[Union[str, Path]] = None,
    hms_object: Optional[HmsPrj] = None,
    load_dss_metadata: bool = False
) -> HmsPrj:
    """Initialize an HEC-HMS project.

    This is the primary entry point for working with HMS projects.
    It initializes either the global `hms` singleton or a provided HmsPrj instance.

    Args:
        project_folder: Path to the HEC-HMS project folder containing the .hms file
        hms_exe_path: Optional path to HEC-HMS executable (hec-hms.cmd or HEC-HMS.exe)
        hms_object: Optional HmsPrj instance to initialize (uses global `hms` if None)
        load_dss_metadata: If True, read DSS files to populate time ranges in gage_df

    Returns:
        HmsPrj: The initialized project object

    Example:
        # Single project workflow (uses global hms object)
        >>> from hms_commander import init_hms_project, hms
        >>> init_hms_project(r"C:/HMS_Projects/MyProject")
        >>> print(hms.hms_df)
        >>> print(hms.basin_df)
        >>> print(hms.run_df)

        # Multi-project workflow (uses separate instances)
        >>> project1 = HmsPrj()
        >>> init_hms_project(r"C:/Project1", hms_object=project1)
        >>> project2 = HmsPrj()
        >>> init_hms_project(r"C:/Project2", hms_object=project2)
    """
    global hms

    if hms_object is not None:
        # Initialize the provided object
        hms_object.initialize(project_folder, hms_exe_path, load_dss_metadata)
        return hms_object
    else:
        # Initialize the global singleton
        hms = HmsPrj()
        hms.initialize(project_folder, hms_exe_path, load_dss_metadata)
        return hms
