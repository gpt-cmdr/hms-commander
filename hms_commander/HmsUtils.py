"""
HmsUtils - Utility Functions for HEC-HMS Operations

This module provides utility functions for common HEC-HMS operations
including file management, unit conversions, and data validation.

All methods are static and designed to be used without instantiation.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._constants import (
    TIME_INTERVALS,
    INCHES_TO_MM, MM_TO_INCHES,
    FEET_TO_METERS, METERS_TO_FEET,
    SQMI_TO_SQKM, SQKM_TO_SQMI,
    ACRE_TO_SQKM, SQKM_TO_ACRE,
    CFS_TO_CMS, CMS_TO_CFS,
    ACFT_TO_M3, M3_TO_ACFT,
    MINUTES_PER_HOUR, MINUTES_PER_DAY,
    IA_RATIO, CN_FORMULA_BASE, CN_FORMULA_NUMERATOR, CN_MIN, CN_MAX,
)

logger = get_logger(__name__)


class HmsUtils:
    """
    Utility functions for HEC-HMS operations.

    Provides helper methods for file operations, unit conversions,
    time interval handling, and data validation.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsUtils
        >>> interval_min = HmsUtils.parse_time_interval("15 Minutes")
        >>> print(interval_min)  # 15
    """

    # Unit conversion factors - reference centralized constants
    CONVERSION_FACTORS = {
        # Length
        'in_to_mm': INCHES_TO_MM,
        'mm_to_in': MM_TO_INCHES,
        'ft_to_m': FEET_TO_METERS,
        'm_to_ft': METERS_TO_FEET,

        # Area
        'sqmi_to_sqkm': SQMI_TO_SQKM,
        'sqkm_to_sqmi': SQKM_TO_SQMI,
        'acre_to_sqkm': ACRE_TO_SQKM,
        'sqkm_to_acre': SQKM_TO_ACRE,

        # Flow
        'cfs_to_cms': CFS_TO_CMS,
        'cms_to_cfs': CMS_TO_CFS,

        # Volume
        'acft_to_m3': ACFT_TO_M3,
        'm3_to_acft': M3_TO_ACFT,
    }

    # Time interval mappings - reference centralized constants
    # Note: TIME_INTERVALS imported from _constants

    @staticmethod
    @log_call
    def parse_time_interval(interval_str: str) -> int:
        """
        Parse HMS time interval string to minutes.

        Args:
            interval_str: Time interval string (e.g., "15 Minutes", "1 Hour")

        Returns:
            Interval in minutes

        Example:
            >>> HmsUtils.parse_time_interval("15 Minutes")
            15
            >>> HmsUtils.parse_time_interval("1 Hour")
            60
        """
        if interval_str in TIME_INTERVALS:
            return TIME_INTERVALS[interval_str]

        # Try to parse custom format
        match = re.match(r'(\d+)\s*(\w+)', interval_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()

            if 'min' in unit:
                return value
            elif 'hour' in unit:
                return value * MINUTES_PER_HOUR
            elif 'day' in unit:
                return value * MINUTES_PER_DAY

        raise ValueError(f"Unknown time interval: {interval_str}")

    @staticmethod
    @log_call
    def minutes_to_interval_string(minutes: int) -> str:
        """
        Convert minutes to HMS interval string.

        Args:
            minutes: Number of minutes

        Returns:
            HMS interval string

        Example:
            >>> HmsUtils.minutes_to_interval_string(15)
            '15 Minutes'
            >>> HmsUtils.minutes_to_interval_string(60)
            '1 Hour'
        """
        # Find exact match
        for interval_str, mins in TIME_INTERVALS.items():
            if mins == minutes:
                return interval_str

        # Generate approximate string
        if minutes < MINUTES_PER_HOUR:
            return f"{minutes} Minutes" if minutes > 1 else "1 Minute"
        elif minutes < MINUTES_PER_DAY:
            hours = minutes // MINUTES_PER_HOUR
            return f"{hours} Hours" if hours > 1 else "1 Hour"
        else:
            days = minutes // MINUTES_PER_DAY
            return f"{days} Days" if days > 1 else "1 Day"

    @staticmethod
    @log_call
    def convert_units(
        value: float,
        from_unit: str,
        to_unit: str
    ) -> float:
        """
        Convert between common hydrologic units.

        Args:
            value: Value to convert
            from_unit: Source unit
            to_unit: Target unit

        Returns:
            Converted value

        Example:
            >>> HmsUtils.convert_units(1.0, "in", "mm")
            25.4
            >>> HmsUtils.convert_units(100, "cfs", "cms")
            2.83...
        """
        # Normalize unit names
        from_unit = from_unit.lower().replace(' ', '')
        to_unit = to_unit.lower().replace(' ', '')

        # Same units
        if from_unit == to_unit:
            return value

        # Build conversion key
        key = f"{from_unit}_to_{to_unit}"

        if key in HmsUtils.CONVERSION_FACTORS:
            return value * HmsUtils.CONVERSION_FACTORS[key]

        # Try reverse
        reverse_key = f"{to_unit}_to_{from_unit}"
        if reverse_key in HmsUtils.CONVERSION_FACTORS:
            return value / HmsUtils.CONVERSION_FACTORS[reverse_key]

        raise ValueError(f"Unknown unit conversion: {from_unit} to {to_unit}")

    @staticmethod
    @log_call
    def parse_hms_date(date_str: str, time_str: str = "00:00") -> datetime:
        """
        Parse HMS date/time strings to datetime.

        Args:
            date_str: Date string in HMS format (e.g., "01Jan2020")
            time_str: Time string (e.g., "00:00")

        Returns:
            datetime object

        Example:
            >>> dt = HmsUtils.parse_hms_date("15Mar2020", "12:30")
            >>> print(dt)
            2020-03-15 12:30:00
        """
        datetime_str = f"{date_str} {time_str}"
        return datetime.strptime(datetime_str, "%d%b%Y %H:%M")

    @staticmethod
    @log_call
    def format_hms_date(dt: datetime) -> Tuple[str, str]:
        """
        Format datetime to HMS date/time strings.

        Args:
            dt: datetime object

        Returns:
            Tuple of (date_str, time_str)

        Example:
            >>> dt = datetime(2020, 3, 15, 12, 30)
            >>> date_str, time_str = HmsUtils.format_hms_date(dt)
            >>> print(date_str, time_str)
            15Mar2020 12:30
        """
        date_str = dt.strftime("%d%b%Y")
        time_str = dt.strftime("%H:%M")
        return date_str, time_str

    @staticmethod
    @log_call
    def copy_project(
        source_folder: Union[str, Path],
        dest_folder: Union[str, Path],
        overwrite: bool = False
    ) -> Path:
        """
        Copy an HMS project to a new location.

        Args:
            source_folder: Source project folder
            dest_folder: Destination folder
            overwrite: Whether to overwrite existing destination

        Returns:
            Path to the copied project
        """
        source_folder = Path(source_folder)
        dest_folder = Path(dest_folder)

        if not source_folder.exists():
            raise FileNotFoundError(f"Source folder not found: {source_folder}")

        if dest_folder.exists():
            if overwrite:
                shutil.rmtree(dest_folder)
            else:
                raise FileExistsError(f"Destination exists: {dest_folder}")

        logger.info(f"Copying project from {source_folder} to {dest_folder}")
        shutil.copytree(source_folder, dest_folder)

        return dest_folder

    @staticmethod
    @log_call
    def list_project_files(
        project_folder: Union[str, Path]
    ) -> Dict[str, List[Path]]:
        """
        List all HMS files in a project folder by type.

        Args:
            project_folder: Path to the project folder

        Returns:
            Dictionary mapping file type to list of file paths

        Example:
            >>> files = HmsUtils.list_project_files("MyProject")
            >>> print(files['basin'])  # List of .basin files
        """
        project_folder = Path(project_folder)

        if not project_folder.exists():
            raise FileNotFoundError(f"Project folder not found: {project_folder}")

        file_types = {
            'hms': list(project_folder.glob("*.hms")),
            'basin': list(project_folder.glob("*.basin")),
            'met': list(project_folder.glob("*.met")),
            'control': list(project_folder.glob("*.control")),
            'gage': list(project_folder.glob("*.gage")),
            'run': list(project_folder.glob("*.run")),
            'dss': list(project_folder.glob("*.dss")),
            'log': list(project_folder.glob("*.log")),
            'geo': list(project_folder.glob("*.geo")),
            'map': list(project_folder.glob("*.map")),
            'grid': list(project_folder.glob("*.grid")),
            'sqlite': list(project_folder.glob("*.sqlite")),
        }

        return file_types

    @staticmethod
    @log_call
    def clean_project_outputs(
        project_folder: Union[str, Path],
        delete_dss: bool = True,
        delete_logs: bool = True
    ) -> int:
        """
        Clean output files from a project folder.

        Args:
            project_folder: Path to the project folder
            delete_dss: Whether to delete DSS files
            delete_logs: Whether to delete log files

        Returns:
            Number of files deleted
        """
        project_folder = Path(project_folder)
        deleted_count = 0

        patterns = []
        if delete_dss:
            patterns.extend(['*.dss'])
        if delete_logs:
            patterns.extend(['*.log', '*.out', '*.err'])

        for pattern in patterns:
            for file in project_folder.glob(pattern):
                try:
                    file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted: {file}")
                except Exception as e:
                    logger.warning(f"Could not delete {file}: {e}")

        logger.info(f"Deleted {deleted_count} output files")
        return deleted_count

    @staticmethod
    @log_call
    def validate_project(
        project_folder: Union[str, Path]
    ) -> Dict[str, Any]:
        """
        Validate an HMS project folder.

        Checks for required files and common issues.

        Args:
            project_folder: Path to the project folder

        Returns:
            Dictionary with validation results

        Example:
            >>> result = HmsUtils.validate_project("MyProject")
            >>> if result['valid']:
            ...     print("Project is valid")
        """
        project_folder = Path(project_folder)
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'project_file': None,
            'basin_files': [],
            'met_files': [],
            'control_files': [],
            'run_files': []
        }

        if not project_folder.exists():
            result['valid'] = False
            result['errors'].append(f"Project folder not found: {project_folder}")
            return result

        # Check for .hms project file
        hms_files = list(project_folder.glob("*.hms"))
        if not hms_files:
            result['valid'] = False
            result['errors'].append("No .hms project file found")
        else:
            result['project_file'] = str(hms_files[0])
            if len(hms_files) > 1:
                result['warnings'].append(f"Multiple .hms files found: {len(hms_files)}")

        # Check for basin files
        result['basin_files'] = [str(f) for f in project_folder.glob("*.basin")]
        if not result['basin_files']:
            result['warnings'].append("No .basin files found")

        # Check for met files
        result['met_files'] = [str(f) for f in project_folder.glob("*.met")]

        # Check for control files
        result['control_files'] = [str(f) for f in project_folder.glob("*.control")]

        # Check for run files
        result['run_files'] = [str(f) for f in project_folder.glob("*.run")]

        return result

    @staticmethod
    @log_call
    def get_project_summary(
        project_folder: Union[str, Path]
    ) -> str:
        """
        Get a text summary of a project.

        Args:
            project_folder: Path to the project folder

        Returns:
            Formatted summary string
        """
        files = HmsUtils.list_project_files(project_folder)

        summary = []
        summary.append(f"HMS Project: {Path(project_folder).name}")
        summary.append("=" * 50)

        for file_type, file_list in files.items():
            if file_list:
                summary.append(f"\n{file_type.upper()} files ({len(file_list)}):")
                for f in file_list[:5]:  # Limit to first 5
                    summary.append(f"  - {f.name}")
                if len(file_list) > 5:
                    summary.append(f"  ... and {len(file_list) - 5} more")

        return "\n".join(summary)

    @staticmethod
    def calculate_cn_from_ia(
        initial_abstraction: float,
        method: str = "standard"
    ) -> float:
        """
        Calculate SCS Curve Number from Initial Abstraction.

        Args:
            initial_abstraction: Initial abstraction in inches
            method: Calculation method ("standard" uses Ia = 0.2*S)

        Returns:
            Curve Number (0-100)

        Example:
            >>> cn = HmsUtils.calculate_cn_from_ia(1.0)
            >>> print(f"CN = {cn:.1f}")
        """
        # Standard method: Ia = IA_RATIO * S, where S = (1000/CN) - 10
        # Solving for CN: CN = 1000 / (S + 10) where S = Ia / IA_RATIO
        s = initial_abstraction / IA_RATIO
        cn = CN_FORMULA_NUMERATOR / (s + CN_FORMULA_BASE)
        return max(CN_MIN, min(CN_MAX, cn))

    @staticmethod
    def calculate_ia_from_cn(
        curve_number: float,
        method: str = "standard"
    ) -> float:
        """
        Calculate Initial Abstraction from SCS Curve Number.

        Args:
            curve_number: SCS Curve Number (0-100)
            method: Calculation method ("standard" uses Ia = 0.2*S)

        Returns:
            Initial Abstraction in inches

        Example:
            >>> ia = HmsUtils.calculate_ia_from_cn(75)
            >>> print(f"Ia = {ia:.2f} inches")
        """
        if curve_number <= CN_MIN or curve_number > CN_MAX:
            raise ValueError(f"Curve Number must be between {CN_MIN} and {CN_MAX}, got {curve_number}")

        # S = (CN_FORMULA_NUMERATOR/CN) - CN_FORMULA_BASE
        s = (CN_FORMULA_NUMERATOR / curve_number) - CN_FORMULA_BASE
        # Ia = IA_RATIO * S
        ia = IA_RATIO * s
        return ia

    @staticmethod
    @log_call
    def clone_file(
        template_path: Union[str, Path],
        new_path: Union[str, Path],
        modify_func: Optional[Any] = None
    ) -> Path:
        """
        Clone a file with optional modification via callback function.

        This is the core clone utility used by all HMS clone operations
        (clone_run, clone_basin, clone_met). It follows the ras-commander
        pattern of reading, modifying via callback, and writing.

        Args:
            template_path: Path to template file
            new_path: Path for new file
            modify_func: Optional callback function(lines: List[str]) -> List[str]
                        that modifies file content

        Returns:
            Path to the cloned file

        Raises:
            FileNotFoundError: If template doesn't exist
            FileExistsError: If new_path already exists

        Example:
            >>> def update_name(lines):
            ...     return [line.replace("Old", "New") for line in lines]
            >>> HmsUtils.clone_file("old.basin", "new.basin", update_name)

        Note:
            This implements the CLB Engineering LLM Forward Approach:
            - Non-destructive (creates new file, preserves original)
            - Traceable (clear source → destination relationship)
            - Modifiable (callback allows precise updates)
        """
        template_path = Path(template_path)
        new_path = Path(new_path)

        if not template_path.exists():
            raise FileNotFoundError(f"Template file not found: {template_path}")

        if new_path.exists():
            raise FileExistsError(f"Destination file already exists: {new_path}")

        # Read template with encoding fallback
        encodings = ['utf-8', 'latin-1', 'cp1252']
        content = None
        for encoding in encodings:
            try:
                content = template_path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise UnicodeDecodeError(
                f"Could not decode {template_path} with any supported encoding"
            )

        # Apply modification function if provided
        if modify_func is not None:
            lines = content.splitlines(keepends=True)
            modified_lines = modify_func(lines)
            content = ''.join(modified_lines)

        # Write new file
        new_path.write_text(content, encoding='utf-8')
        logger.info(f"Cloned file: {template_path.name} → {new_path.name}")

        return new_path

    @staticmethod
    @log_call
    def update_project_file(
        hms_file: Union[str, Path],
        entry_type: str,
        entry_name: str
    ) -> bool:
        """
        Update HMS project file to register a new component.

        When cloning basins, mets, controls, or runs, the .hms project
        file must be updated to register the new component. This follows
        the ras-commander pattern of updating the project file after
        creating new model components.

        Args:
            hms_file: Path to the .hms project file
            entry_type: Type of entry ('Basin', 'Met', 'Control', 'Run', etc.)
            entry_name: Name of the new component (filename without extension)

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If hms_file doesn't exist

        Example:
            >>> HmsUtils.update_project_file(
            ...     "MyProject.hms",
            ...     "Basin",
            ...     "Updated_Atlas14"
            ... )

        Note:
            The HMS project file format uses simple lines like:
            Basin File: BasinName.basin
            Met File: MetName.met
            This method appends new entries to ensure proper registration.
        """
        hms_file = Path(hms_file)

        if not hms_file.exists():
            raise FileNotFoundError(f"HMS project file not found: {hms_file}")

        content = hms_file.read_text(encoding='utf-8')

        # Determine the file pattern based on entry type
        file_extensions = {
            'Basin': 'basin',
            'Meteorology': 'met',
            'Met': 'met',
            'Control': 'control',
            'Run': 'run',
            'Gage': 'gage',
        }

        extension = file_extensions.get(entry_type)
        if extension is None:
            logger.warning(f"Unknown entry type '{entry_type}', using lowercase")
            extension = entry_type.lower()

        # Check if entry already exists
        entry_pattern = rf'^{entry_type}\s+File:\s*{re.escape(entry_name)}\.{extension}\s*$'
        if re.search(entry_pattern, content, re.MULTILINE | re.IGNORECASE):
            logger.info(f"{entry_type} '{entry_name}' already in project file")
            return True

        # Add new entry line
        new_entry = f"{entry_type} File: {entry_name}.{extension}\n"

        # Find insertion point (after last similar entry type, or before End: if exists)
        type_pattern = rf'^{entry_type}\s+File:.*$'
        matches = list(re.finditer(type_pattern, content, re.MULTILINE | re.IGNORECASE))

        if matches:
            # Insert after last matching entry
            last_match = matches[-1]
            insert_pos = last_match.end()
            content = content[:insert_pos] + '\n' + new_entry + content[insert_pos:]
        else:
            # Insert before 'End:' or at end of file
            end_match = re.search(r'^End:\s*$', content, re.MULTILINE)
            if end_match:
                content = content[:end_match.start()] + new_entry + content[end_match.start():]
            else:
                content = content.rstrip() + '\n' + new_entry

        # Write back
        hms_file.write_text(content, encoding='utf-8')
        logger.info(f"Added {entry_type} '{entry_name}' to project file")

        return True
