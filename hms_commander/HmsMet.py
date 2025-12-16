"""
HmsMet - Meteorologic Model File Operations

This module provides static methods for reading and modifying HEC-HMS meteorologic
model files (.met). It handles precipitation methods, evapotranspiration, and gage
assignments.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._parsing import HmsFileParser
from ._constants import PRECIP_METHODS, ET_METHODS, SNOWMELT_METHODS

logger = get_logger(__name__)


class HmsMet:
    """
    Meteorologic model file operations (.met files).

    Configure precipitation, evapotranspiration settings, and gage assignments.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsMet
        >>> precip_method = HmsMet.get_precipitation_method("model.met")
        >>> gage_assignments = HmsMet.get_gage_assignments("model.met")
    """

    # Meteorologic method enumerations (from _constants)

    @staticmethod
    @log_call
    def get_mets(
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all meteorologic models from the HMS project.

        Args:
            hms_object: HmsPrj instance (uses global hms if None)

        Returns:
            DataFrame with meteorologic model information
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized")

        return hms_obj.met_df.copy()

    @staticmethod
    @log_call
    def get_precipitation_method(
        met_path: Union[str, Path],
        hms_object=None
    ) -> str:
        """
        Get the precipitation method from a meteorologic model file.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            Precipitation method name string

        Example:
            >>> method = HmsMet.get_precipitation_method("model.met")
            >>> print(f"Method: {method}")
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)
        params = HmsMet._parse_meteorology_block(content)

        return params.get('Precip', 'None')

    @staticmethod
    @log_call
    def get_evapotranspiration_method(
        met_path: Union[str, Path],
        hms_object=None
    ) -> str:
        """
        Get the evapotranspiration method from a meteorologic model file.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            Evapotranspiration method name string
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)
        params = HmsMet._parse_meteorology_block(content)

        return params.get('Evapotranspiration', 'None')

    @staticmethod
    @log_call
    def get_gage_assignments(
        met_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get precipitation gage assignments for all subbasins.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: subbasin, precip_gage, weight

        Example:
            >>> assignments = HmsMet.get_gage_assignments("model.met")
            >>> print(assignments)
        """
        met_path = Path(met_path)
        logger.info(f"Reading gage assignments from: {met_path}")

        content = HmsMet._read_met_file(met_path)
        subbasin_blocks = HmsMet._parse_subbasin_blocks(content)

        records = []
        for subbasin_name, attrs in subbasin_blocks.items():
            record = {
                'subbasin': subbasin_name,
                'precip_gage': attrs.get('Precip Gage'),
                'weight': attrs.get('Weight', 1.0),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} gage assignments")
        return df

    @staticmethod
    @log_call
    def set_gage_assignment(
        met_path: Union[str, Path],
        subbasin_name: str,
        gage_name: str,
        weight: float = 1.0,
        hms_object=None
    ) -> bool:
        """
        Set the precipitation gage assignment for a subbasin.

        Args:
            met_path: Path to the .met file
            subbasin_name: Name of the subbasin
            gage_name: Name of the precipitation gage
            weight: Gage weight (default 1.0)
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Example:
            >>> HmsMet.set_gage_assignment("model.met", "Subbasin-1", "Gage-1")
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        # Find the subbasin block in the met file
        pattern = rf'(Subbasin:\s*{re.escape(subbasin_name)}\s*\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if match:
            # Update existing block
            block_content = match.group(2)
            block_content = HmsMet._update_param(block_content, 'Precip Gage', gage_name)

            new_block = match.group(1) + block_content + match.group(3)
            content = content[:match.start()] + new_block + content[match.end():]
        else:
            # Add new subbasin block before the final End: of the Meteorology block
            new_block = f"""
Subbasin: {subbasin_name}
     Precip Gage: {gage_name}
End:
"""
            # Find the Meteorology End: and insert before it
            met_end_pattern = r'(Meteorology:.*?)(End:\s*$)'
            content = re.sub(
                met_end_pattern,
                rf'\1{new_block}\2',
                content,
                flags=re.DOTALL | re.MULTILINE
            )

        with open(met_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Set gage '{gage_name}' for subbasin '{subbasin_name}'")
        return True

    @staticmethod
    @log_call
    def get_dss_references(
        met_path: Union[str, Path],
        hms_object=None
    ) -> List[Dict[str, str]]:
        """
        Get all DSS file references from a meteorologic model.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            List of dictionaries with DSS file information

        Example:
            >>> dss_refs = HmsMet.get_dss_references("model.met")
            >>> for ref in dss_refs:
            ...     print(f"File: {ref['dss_file']}, Path: {ref['dss_pathname']}")
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        dss_refs = []

        # Look for DSS File and DSS Pathname entries
        dss_file_pattern = r'DSS File Name:\s*(.+)'
        dss_path_pattern = r'DSS Pathname:\s*(.+)'

        dss_files = re.findall(dss_file_pattern, content)
        dss_paths = re.findall(dss_path_pattern, content)

        # Pair them up
        for i, dss_file in enumerate(dss_files):
            ref = {
                'dss_file': dss_file.strip(),
                'dss_pathname': dss_paths[i].strip() if i < len(dss_paths) else ''
            }
            dss_refs.append(ref)

        return dss_refs

    @staticmethod
    @log_call
    def get_met_info(
        met_path: Union[str, Path],
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get comprehensive information from a meteorologic model file.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with all meteorologic model parameters
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        met_params = HmsMet._parse_meteorology_block(content)
        subbasin_blocks = HmsMet._parse_subbasin_blocks(content)
        dss_refs = HmsMet.get_dss_references(met_path)

        return {
            'meteorology': met_params,
            'subbasin_assignments': subbasin_blocks,
            'dss_references': dss_refs,
            'num_subbasins': len(subbasin_blocks)
        }

    @staticmethod
    @log_call
    def clone_met(
        template_met: str,
        new_name: str,
        description: str = None,
        hms_object=None
    ) -> Path:
        """
        Clone a meteorologic model file with a new name.

        Follows the CLB Engineering LLM Forward Approach:
        - Non-destructive: Creates new file, preserves original
        - Traceable: Updates description with clone metadata
        - GUI-verifiable: New met model appears in HEC-HMS GUI
        - Project integration: Updates .hms project file

        Args:
            template_met: Name or path of the template met file
            new_name: Name for the new meteorologic model
            description: Optional description (defaults to "Cloned from {template}")
            hms_object: Optional HmsPrj instance

        Returns:
            Path to the new met file

        Raises:
            FileNotFoundError: If template met not found
            FileExistsError: If new met already exists

        Example:
            >>> # Clone for Atlas 14 update
            >>> new_path = HmsMet.clone_met(
            ...     "Design_Storms_TP40",
            ...     "Design_Storms_Atlas14",
            ...     description="Atlas 14 precipitation data",
            ...     hms_object=hms
            ... )
            >>> # New met model now visible in HEC-HMS GUI
        """
        from .HmsUtils import HmsUtils
        from .HmsPrj import hms

        hms_obj = hms_object or hms
        template_path = Path(template_met)

        # Try to resolve template path from project
        if not template_path.exists() and hms_obj is not None and hms_obj.initialized:
            matching = hms_obj.met_df[
                hms_obj.met_df['name'] == template_met
            ]
            if not matching.empty:
                template_path = Path(matching.iloc[0]['full_path'])
                template_name = matching.iloc[0]['name']
            else:
                # Try with .met extension
                potential = Path(template_met)
                if not potential.suffix:
                    template_path = potential.with_suffix('.met')
                    template_name = template_met
                else:
                    template_name = template_path.stem
        else:
            template_name = template_path.stem

        if not template_path.exists():
            raise FileNotFoundError(f"Template met not found: {template_met}")

        # Build new path
        new_path = template_path.parent / f"{new_name}.met"

        # Default description
        if description is None:
            description = f"Cloned from {template_name}"

        # Define modification callback
        def update_met_metadata(lines):
            """Update meteorology name and description in cloned file."""
            modified_lines = []
            in_met_block = False
            description_found = False

            for line in lines:
                # Update Meteorology: line
                if re.match(r'^Meteorology:\s*', line):
                    modified_lines.append(f"Meteorology: {new_name}\n")
                    in_met_block = True
                # Update Description: line if it exists
                elif in_met_block and re.match(r'^\s+Description:\s*', line):
                    modified_lines.append(f"     Description: {description}\n")
                    description_found = True
                # Add Description: if we hit Precip Method or End: without finding one
                elif in_met_block and (re.match(r'^\s+Precip Method:', line) or line.strip() == 'End:'):
                    if not description_found and re.match(r'^\s+Precip Method:', line):
                        # Insert before Precip Method
                        modified_lines.append(f"     Description: {description}\n")
                        description_found = True
                    modified_lines.append(line)
                    if line.strip() == 'End:':
                        in_met_block = False
                        description_found = False
                else:
                    modified_lines.append(line)

            return modified_lines

        # Clone file with modification
        HmsUtils.clone_file(template_path, new_path, update_met_metadata)

        # Update project file if we have an HMS object
        if hms_obj is not None and hms_obj.initialized:
            try:
                HmsUtils.update_project_file(
                    hms_obj.project_file,
                    'Met',
                    new_name
                )

                # Re-initialize to pick up new met
                hms_obj.initialize(hms_obj.project_folder, hms_obj.hms_exe_path)
                logger.info(f"Re-initialized project to register new met '{new_name}'")

            except Exception as e:
                logger.warning(f"Could not update project file: {e}")

        logger.info(f"Cloned met: {template_name} → {new_name}")
        return new_path

    @staticmethod
    @log_call
    def set_precipitation_method(
        met_path: Union[str, Path],
        method: str,
        hms_object=None
    ) -> bool:
        """
        Set the precipitation method in a meteorologic model file.

        Args:
            met_path: Path to the .met file
            method: Precipitation method name
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful
        """
        met_path = Path(met_path)

        if method not in HmsMet.PRECIP_METHODS:
            logger.warning(f"Non-standard precipitation method: {method}")

        content = HmsMet._read_met_file(met_path)
        content = HmsMet._update_param(content, 'Precip', method)

        with open(met_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Set precipitation method to: {method}")
        return True

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _read_met_file(met_path: Path) -> str:
        """Read met file content with encoding fallback."""
        return HmsFileParser.read_file(met_path)

    @staticmethod
    def _parse_meteorology_block(content: str) -> Dict[str, str]:
        """Parse the main Meteorology block parameters."""
        name, params = HmsFileParser.parse_named_section(content, "Meteorology")
        if name:
            params['name'] = name
        return params

    @staticmethod
    def _parse_subbasin_blocks(content: str) -> Dict[str, Dict[str, str]]:
        """Parse all Subbasin blocks from met file content."""
        return HmsFileParser.parse_blocks(content, "Subbasin")

    @staticmethod
    def _update_param(content: str, param_name: str, new_value: str) -> str:
        """Update a parameter value in met file content."""
        updated, _ = HmsFileParser.update_parameter(content, param_name, new_value)
        return updated

    # =========================================================================
    # Frequency Storm Precipitation Methods (TP40/Atlas 14)
    # =========================================================================

    @staticmethod
    @log_call
    def get_frequency_storm_params(
        met_path: Union[str, Path],
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get Frequency Based Hypothetical storm parameters from a met file.

        Used for TP40 and Atlas 14 precipitation updates.

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with frequency storm parameters including depth values

        Example:
            >>> params = HmsMet.get_frequency_storm_params("1PCT_24HR.met")
            >>> print(f"Duration: {params['total_duration']} min")
            >>> print(f"Depths (inches): {params['depths']}")
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        params = {
            'method': None,
            'exceedance_frequency': None,
            'storm_size': None,
            'total_duration': None,
            'time_interval': None,
            'peak_position': None,
            'depths': [],
            'convert_from_annual': False,
            'convert_to_annual': False,
        }

        # Find the Precip Method Parameters block
        pattern = r'Precip Method Parameters:\s*(.+?)\n(.*?)(?=Subbasin:|End:)'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            logger.warning(f"No Precip Method Parameters block found in {met_path}")
            return params

        params['method'] = match.group(1).strip()
        block = match.group(2)

        for line in block.splitlines():
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if key == 'Exceedence Frequency':
                    params['exceedance_frequency'] = float(value)
                elif key == 'Storm Size':
                    params['storm_size'] = float(value)
                elif key == 'Total Duration':
                    params['total_duration'] = int(value)
                elif key == 'Time Interval':
                    params['time_interval'] = int(value)
                elif key == 'Percent of Duration Before Peak Rainfall':
                    params['peak_position'] = int(value)
                elif key == 'Convert From Annual Series':
                    params['convert_from_annual'] = value.lower() == 'yes'
                elif key == 'Convert to Annual Series':
                    params['convert_to_annual'] = value.lower() == 'yes'
                elif key == 'Depth':
                    try:
                        params['depths'].append(float(value))
                    except ValueError:
                        pass

        logger.info(f"Found {len(params['depths'])} depth values in {met_path.name}")
        return params

    @staticmethod
    @log_call
    def get_precipitation_depths(
        met_path: Union[str, Path],
        hms_object=None
    ) -> List[float]:
        """
        Get precipitation depth values from a frequency storm met file.

        These are the cumulative depth values by duration (e.g., TP40 or Atlas 14).

        Args:
            met_path: Path to the .met file
            hms_object: Optional HmsPrj instance

        Returns:
            List of depth values in inches

        Example:
            >>> depths = HmsMet.get_precipitation_depths("1PCT_24HR.met")
            >>> print(f"24-hr depth: {depths[-1]} inches")
        """
        params = HmsMet.get_frequency_storm_params(met_path, hms_object)
        return params.get('depths', [])

    @staticmethod
    @log_call
    def set_precipitation_depths(
        met_path: Union[str, Path],
        new_depths: List[float],
        hms_object=None
    ) -> bool:
        """
        Set precipitation depth values in a frequency storm met file.

        Used for updating from TP40 to Atlas 14 precipitation values.

        Args:
            met_path: Path to the .met file
            new_depths: List of new depth values in inches
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Raises:
            ValueError: If number of depths doesn't match existing count

        Example:
            >>> # Atlas 14 depths for Houston, 1% AEP, 24-hr
            >>> atlas14_depths = [1.35, 2.4, 4.8, 6.3, 7.4, 9.8, 11.9, 14.5]
            >>> HmsMet.set_precipitation_depths("1PCT_24HR.met", atlas14_depths)
        """
        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        # Get existing depths to verify count
        existing_params = HmsMet.get_frequency_storm_params(met_path)
        existing_depths = existing_params.get('depths', [])

        if len(new_depths) != len(existing_depths):
            raise ValueError(
                f"New depths count ({len(new_depths)}) must match "
                f"existing count ({len(existing_depths)})"
            )

        # Find and replace depth lines
        depth_pattern = r'^(\s*Depth:\s*)[\d.]+\s*$'
        depth_lines = list(re.finditer(depth_pattern, content, re.MULTILINE))

        if len(depth_lines) != len(new_depths):
            raise ValueError(
                f"Found {len(depth_lines)} depth lines but "
                f"{len(new_depths)} new values provided"
            )

        # Replace in reverse order to preserve positions
        for i, match in enumerate(reversed(depth_lines)):
            idx = len(new_depths) - 1 - i
            new_line = f"     Depth: {new_depths[idx]:.4f}"
            content = content[:match.start()] + new_line + content[match.end():]

        with open(met_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Updated {len(new_depths)} depth values in {met_path.name}")
        return True

    @staticmethod
    @log_call
    def update_tp40_to_atlas14(
        met_path: Union[str, Path],
        atlas14_depths: List[float],
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Update a met file from TP40 to Atlas 14 precipitation depths.

        This is a convenience method that reads old values, updates to new,
        and returns a summary of changes.

        Args:
            met_path: Path to the .met file
            atlas14_depths: Atlas 14 depth values in inches
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary with old depths, new depths, and change percentages

        Example:
            >>> atlas14 = [1.35, 2.4, 4.8, 6.3, 7.4, 9.8, 11.9, 14.5]
            >>> result = HmsMet.update_tp40_to_atlas14("1PCT_24HR.met", atlas14)
            >>> print(f"24-hr depth changed by {result['changes'][-1]:.1f}%")
        """
        met_path = Path(met_path)

        # Get original values
        old_depths = HmsMet.get_precipitation_depths(met_path, hms_object)

        if not old_depths:
            raise ValueError(f"No precipitation depths found in {met_path}")

        # Update depths
        HmsMet.set_precipitation_depths(met_path, atlas14_depths, hms_object)

        # Calculate changes
        changes = []
        for old, new in zip(old_depths, atlas14_depths):
            if old > 0:
                pct_change = ((new - old) / old) * 100
            else:
                pct_change = 0 if new == 0 else float('inf')
            changes.append(pct_change)

        result = {
            'met_file': str(met_path),
            'old_depths': old_depths,
            'new_depths': atlas14_depths,
            'changes_percent': changes,
            'avg_change_percent': sum(changes) / len(changes) if changes else 0
        }

        logger.info(
            f"Updated {met_path.name}: avg change {result['avg_change_percent']:.1f}%"
        )
        return result
