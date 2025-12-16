"""
HmsGage - Time-Series Gage File Operations

This module provides static methods for reading and modifying HEC-HMS time-series
gage files (.gage). It handles precipitation gages, discharge gages, and their
DSS data references.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._parsing import HmsFileParser
from ._constants import GAGE_DATA_TYPES, PRECIP_UNITS, DISCHARGE_UNITS, STAGE_UNITS, TEMP_UNITS

logger = get_logger(__name__)


class HmsGage:
    """
    Time-series gage file operations (.gage files).

    Manage gage data and DSS references for precipitation, discharge, and other
    time-series data.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsGage
        >>> gages = HmsGage.get_gages("model.gage")
        >>> print(gages)
    """

    # Gage data types and units (from _constants)
    GAGE_TYPES = GAGE_DATA_TYPES

    @staticmethod
    @log_call
    def get_gages(
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all gages from a gage file or HMS project.

        Args:
            gage_path: Path to the .gage file (optional if hms_object provided)
            hms_object: HmsPrj instance (uses global hms if None)

        Returns:
            DataFrame with columns: name, type, units, dss_file, dss_pathname

        Example:
            >>> gages = HmsGage.get_gages("model.gage")
            >>> print(gages[['name', 'type', 'units']])
        """
        from .HmsPrj import hms

        # If no gage_path provided, get from project
        if gage_path is None:
            hms_obj = hms_object or hms
            if hms_obj is None or not hms_obj.initialized:
                raise RuntimeError("HMS project not initialized and no gage_path provided")
            return hms_obj.gage_df.copy()

        gage_path = Path(gage_path)
        logger.info(f"Reading gages from: {gage_path}")

        content = HmsGage._read_gage_file(gage_path)
        gage_blocks = HmsGage._parse_gage_blocks(content)

        records = []
        for name, attrs in gage_blocks.items():
            record = {
                'name': name,
                'type': attrs.get('Type', 'Precipitation'),
                'units': attrs.get('Units', ''),
                'data_type': attrs.get('Data Type', ''),
                'dss_file': attrs.get('DSS File Name', ''),
                'dss_pathname': attrs.get('DSS Pathname', ''),
                'description': attrs.get('Description', ''),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} gages")
        return df

    @staticmethod
    @log_call
    def get_gage_info(
        gage_name: str,
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get detailed information for a specific gage.

        Args:
            gage_name: Name of the gage
            gage_path: Path to the .gage file
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with all gage parameters

        Example:
            >>> info = HmsGage.get_gage_info("Precip-Gage-1", "model.gage")
            >>> print(f"DSS File: {info['dss_file']}")
        """
        from .HmsPrj import hms

        if gage_path is None:
            hms_obj = hms_object or hms
            if hms_obj is None or not hms_obj.initialized:
                raise RuntimeError("HMS project not initialized and no gage_path provided")

            # Find gage file from project
            if hms_obj.gage_df.empty:
                raise ValueError("No gage files in project")

            gage_path = Path(hms_obj.gage_df.iloc[0]['full_path'])

        gage_path = Path(gage_path)
        content = HmsGage._read_gage_file(gage_path)
        gage_blocks = HmsGage._parse_gage_blocks(content)

        if gage_name not in gage_blocks:
            raise ValueError(f"Gage '{gage_name}' not found")

        return gage_blocks[gage_name]

    @staticmethod
    @log_call
    def get_dss_pathname(
        gage_name: str,
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> str:
        """
        Get the DSS pathname for a specific gage.

        Args:
            gage_name: Name of the gage
            gage_path: Path to the .gage file
            hms_object: Optional HmsPrj instance

        Returns:
            DSS pathname string

        Example:
            >>> pathname = HmsGage.get_dss_pathname("Precip-Gage-1", "model.gage")
        """
        info = HmsGage.get_gage_info(gage_name, gage_path, hms_object)
        return info.get('DSS Pathname', '')

    @staticmethod
    @log_call
    def create_gage(
        gage_path: Union[str, Path],
        name: str,
        dss_file: Union[str, Path],
        pathname: str,
        gage_type: str = "Precipitation",
        units: str = "IN",
        data_type: str = "PER-CUM",
        description: str = "",
        hms_object=None
    ) -> bool:
        """
        Create a new gage entry in a gage file.

        Args:
            gage_path: Path to the .gage file
            name: Name for the new gage
            dss_file: Path to the DSS file
            pathname: DSS pathname for the data
            gage_type: Type of gage (Precipitation, Discharge, etc.)
            units: Data units (IN, MM, CFS, etc.)
            data_type: DSS data type (PER-CUM, INST-VAL, etc.)
            description: Optional description
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Example:
            >>> HmsGage.create_gage(
            ...     "model.gage",
            ...     name="New-Gage",
            ...     dss_file="precip.dss",
            ...     pathname="/BASIN/GAGE1/PRECIP-INC//15MIN/OBS/",
            ...     gage_type="Precipitation",
            ...     units="IN"
            ... )
        """
        gage_path = Path(gage_path)

        # Read existing content or create new
        if gage_path.exists():
            content = HmsGage._read_gage_file(gage_path)
        else:
            content = ""

        # Create new gage block
        new_gage_block = f"""
Gage: {name}
     Type: {gage_type}
     Units: {units}
     Data Type: {data_type}
     DSS File Name: {dss_file}
     DSS Pathname: {pathname}
"""
        if description:
            new_gage_block += f"     Description: {description}\n"
        new_gage_block += "End:\n"

        # Append to content
        content += new_gage_block

        with open(gage_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Created gage '{name}' in {gage_path}")
        return True

    @staticmethod
    @log_call
    def update_gage(
        gage_path: Union[str, Path],
        gage_name: str,
        dss_file: str = None,
        pathname: str = None,
        units: str = None,
        hms_object=None
    ) -> bool:
        """
        Update an existing gage entry.

        Args:
            gage_path: Path to the .gage file
            gage_name: Name of the gage to update
            dss_file: New DSS file path (optional)
            pathname: New DSS pathname (optional)
            units: New units (optional)
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful
        """
        gage_path = Path(gage_path)
        content = HmsGage._read_gage_file(gage_path)

        # Find the gage block
        pattern = rf'(Gage:\s*{re.escape(gage_name)}\s*\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            raise ValueError(f"Gage '{gage_name}' not found")

        block_content = match.group(2)
        modified = False

        if dss_file is not None:
            block_content = HmsGage._update_param(block_content, 'DSS File Name', dss_file)
            modified = True

        if pathname is not None:
            block_content = HmsGage._update_param(block_content, 'DSS Pathname', pathname)
            modified = True

        if units is not None:
            block_content = HmsGage._update_param(block_content, 'Units', units)
            modified = True

        if modified:
            new_block = match.group(1) + block_content + match.group(3)
            content = content[:match.start()] + new_block + content[match.end():]

            with open(gage_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Updated gage '{gage_name}'")

        return True

    @staticmethod
    @log_call
    def delete_gage(
        gage_path: Union[str, Path],
        gage_name: str,
        hms_object=None
    ) -> bool:
        """
        Delete a gage entry from a gage file.

        Args:
            gage_path: Path to the .gage file
            gage_name: Name of the gage to delete
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful
        """
        gage_path = Path(gage_path)
        content = HmsGage._read_gage_file(gage_path)

        # Find and remove the gage block
        pattern = rf'Gage:\s*{re.escape(gage_name)}\s*\n.*?End:\s*\n?'
        new_content, count = re.subn(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)

        if count == 0:
            raise ValueError(f"Gage '{gage_name}' not found")

        with open(gage_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        logger.info(f"Deleted gage '{gage_name}'")
        return True

    @staticmethod
    @log_call
    def list_precip_gages(
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> List[str]:
        """
        Get a list of precipitation gage names.

        Args:
            gage_path: Path to the .gage file
            hms_object: Optional HmsPrj instance

        Returns:
            List of precipitation gage names
        """
        gages = HmsGage.get_gages(gage_path, hms_object)
        precip_gages = gages[gages['type'] == 'Precipitation']
        return precip_gages['name'].tolist()

    @staticmethod
    @log_call
    def list_discharge_gages(
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> List[str]:
        """
        Get a list of discharge gage names.

        Args:
            gage_path: Path to the .gage file
            hms_object: Optional HmsPrj instance

        Returns:
            List of discharge gage names
        """
        gages = HmsGage.get_gages(gage_path, hms_object)
        discharge_gages = gages[gages['type'] == 'Discharge']
        return discharge_gages['name'].tolist()

    @staticmethod
    @log_call
    def get_dss_files(
        gage_path: Union[str, Path] = None,
        hms_object=None
    ) -> List[str]:
        """
        Get a list of unique DSS files referenced by gages.

        Args:
            gage_path: Path to the .gage file
            hms_object: Optional HmsPrj instance

        Returns:
            List of unique DSS file paths
        """
        gages = HmsGage.get_gages(gage_path, hms_object)
        dss_files = gages['dss_file'].dropna().unique().tolist()
        return [f for f in dss_files if f]  # Filter out empty strings

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _read_gage_file(gage_path: Path) -> str:
        """Read gage file content with encoding fallback."""
        return HmsFileParser.read_file(gage_path)

    @staticmethod
    def _parse_gage_blocks(content: str) -> Dict[str, Dict[str, str]]:
        """Parse all Gage blocks from gage file content."""
        return HmsFileParser.parse_blocks(content, "Gage")

    @staticmethod
    def _update_param(content: str, param_name: str, new_value: str) -> str:
        """Update a parameter value in gage block content."""
        updated, _ = HmsFileParser.update_parameter(content, param_name, new_value)
        return updated
