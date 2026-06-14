"""
HmsMet - Meteorologic Model File Operations

This module provides static methods for reading and modifying HEC-HMS meteorologic
model files (.met). It handles precipitation methods, evapotranspiration, and gage
assignments.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Mapping
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
    PRECIP_METHODS = PRECIP_METHODS
    ET_METHODS = ET_METHODS
    SNOWMELT_METHODS = SNOWMELT_METHODS

    _PRECIP_METHOD_KEY = 'Precipitation Method'
    _LEGACY_PRECIP_METHOD_KEY = 'Precip'
    _PRECIP_GAGE_KEY = 'Precip Gage'
    _ALT_PRECIP_GAGE_KEY = 'Precipitation Gage'
    _PRECIP_WEIGHT_KEY = 'Weight'
    _ALT_PRECIP_WEIGHT_KEY = 'Precipitation Gage Weight'
    _FREQUENCY_METHODS = {'Frequency Based Hypothetical', 'Frequency Storm'}
    _GAGE_METHODS = {'Gage Weights', 'Specified Hyetograph', 'Inverse Distance'}

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

        return params.get(
            HmsMet._PRECIP_METHOD_KEY,
            params.get(HmsMet._LEGACY_PRECIP_METHOD_KEY, 'None')
        )

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
            weight_value = HmsMet._get_precip_weight_value(attrs) or '1.0'
            record = {
                'subbasin': subbasin_name,
                'precip_gage': HmsMet._get_precip_gage_value(attrs),
                'weight': HmsFileParser.to_numeric(weight_value) if weight_value is not None else 1.0,
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

        match, header, block_content, footer = HmsFileParser.find_block(
            content, 'Subbasin', subbasin_name
        )

        if match:
            # Update existing block
            gage_key = HmsMet._select_existing_key(
                HmsFileParser._parse_attribute_block(block_content),
                HmsMet._PRECIP_GAGE_KEY,
                HmsMet._ALT_PRECIP_GAGE_KEY,
            )
            block_content, changed = HmsFileParser.update_parameter(
                block_content, gage_key, gage_name
            )
            if not changed:
                block_content = HmsMet._append_block_parameter(
                    block_content, gage_key, gage_name
                )

            weight_key = HmsMet._select_existing_key(
                HmsFileParser._parse_attribute_block(block_content),
                HmsMet._PRECIP_WEIGHT_KEY,
                HmsMet._ALT_PRECIP_WEIGHT_KEY,
            )
            block_content, changed = HmsFileParser.update_parameter(
                block_content, weight_key, weight
            )
            if not changed:
                block_content = HmsMet._append_block_parameter(
                    block_content, weight_key, weight
                )

            new_block = header + block_content + footer
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
    def set_all_gage_assignments(
        met_path: Union[str, Path],
        assignments_df: pd.DataFrame,
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Set precipitation gage assignments for multiple subbasins from a DataFrame.

        The DataFrame should have columns: subbasin, precip_gage, and optionally
        weight. Only rows where precip_gage is not NaN are updated.

        Args:
            met_path: Path to the .met file
            assignments_df: DataFrame with columns: subbasin, precip_gage, weight
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Summary dict with keys: subbasins_modified, subbasins_not_found,
            warnings, backup_path

        Example:
            >>> df = HmsMet.get_gage_assignments("model.met")
            >>> df['precip_gage'] = 'New_Gage'  # Reassign all
            >>> result = HmsMet.set_all_gage_assignments("model.met", df)
        """
        import shutil

        met_path = Path(met_path)
        content = HmsMet._read_met_file(met_path)

        summary = {
            'subbasins_modified': 0,
            'subbasins_not_found': [],
            'warnings': [],
            'backup_path': None,
        }

        if 'subbasin' not in assignments_df.columns:
            raise ValueError("assignments_df must have a 'subbasin' column")
        if 'precip_gage' not in assignments_df.columns:
            raise ValueError("assignments_df must have a 'precip_gage' column")

        # Create backup
        if create_backup:
            backup_path = met_path.with_suffix('.met.bak')
            shutil.copy2(met_path, backup_path)
            summary['backup_path'] = str(backup_path)
            logger.info(f"Created backup: {backup_path}")

        # Build lookup: subbasin_name -> {precip_gage, weight}
        update_lookup = {}
        for _, row in assignments_df.iterrows():
            name = row['subbasin']
            gage = row.get('precip_gage')
            if pd.notna(gage):
                update_lookup[name] = {
                    'Precip Gage': str(gage),
                }
                weight = row.get('weight')
                if pd.notna(weight):
                    update_lookup[name]['Weight'] = str(weight)

        # Find all Subbasin blocks with positions
        blocks = HmsFileParser.find_all_blocks(content, "Subbasin")

        found_names = set()

        # Iterate in reverse order to preserve offsets
        for match, name, attrs in reversed(blocks):
            if name not in update_lookup:
                continue

            found_names.add(name)
            updates = update_lookup[name]
            block_body = match.group(3)
            modified = False

            for param_key, new_value in updates.items():
                updated_body, changed = HmsFileParser.update_parameter(
                    block_body, param_key, new_value
                )
                if changed:
                    block_body = updated_body
                    modified = True
                elif param_key not in attrs:
                    # Parameter doesn't exist yet — insert it
                    block_body = block_body + f"     {param_key}: {new_value}\n"
                    modified = True

            if modified:
                header = match.group(1)
                footer = match.group(4)
                new_block = header + block_body + footer
                content = content[:match.start()] + new_block + content[match.end():]
                summary['subbasins_modified'] += 1

        # Check for names not found
        for name in update_lookup:
            if name not in found_names:
                summary['subbasins_not_found'].append(name)

        if summary['subbasins_not_found']:
            summary['warnings'].append(
                f"{len(summary['subbasins_not_found'])} subbasins not found: "
                f"{summary['subbasins_not_found'][:5]}"
            )

        HmsFileParser.write_file(met_path, content)
        logger.info(f"Updated {summary['subbasins_modified']} gage assignments in {met_path.name}")

        return summary

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

        hms_obj = hms_object if hms_object is not None else hms
        template_path = Path(template_met)
        template_name = template_path.stem

        # Try to resolve template path from project
        if not template_path.exists() and hms_obj is not None and hms_obj.initialized:
            matching = hms_obj.met_df[
                hms_obj.met_df['name'] == template_met
            ]
            if not matching.empty:
                template_path = Path(matching.iloc[0]['full_path'])
                template_name = matching.iloc[0]['name']

        # Try a same-folder file path with the expected extension when no
        # project object can resolve the logical component name.
        if not template_path.exists() and not template_path.suffix:
            potential = template_path.with_suffix('.met')
            if potential.exists():
                template_path = potential
                template_name = potential.stem

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
        content = HmsMet._set_meteorology_parameter(
            content,
            HmsMet._PRECIP_METHOD_KEY,
            method
        )

        HmsFileParser.write_file(met_path, content)

        logger.info(f"Set precipitation method to: {method}")
        return True

    @staticmethod
    @log_call
    def set_precipitation(
        met_path: Union[str, Path],
        method: str,
        data: Optional[Mapping[str, Any]] = None,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Set precipitation configuration in a meteorologic model file.

        Args:
            met_path: Path to the .met file.
            method: HMS precipitation method. Common values include
                ``Frequency Based Hypothetical``, ``Gage Weights``,
                ``Specified Hyetograph``, ``Gridded Precipitation``, and ``None``.
            data: Optional method-specific settings. Supported keys include
                ``depths`` for frequency storms, ``gage_assignments`` for gage
                methods, and ``grid_name``/``dss_file``/``dss_pathname`` for
                gridded precipitation.
            hms_object: Optional HmsPrj instance.

        Returns:
            Summary dictionary describing the precipitation update.

        Raises:
            ValueError: If required method-specific data is missing or invalid.

        Example:
            >>> HmsMet.set_precipitation(
            ...     "model.met",
            ...     "Gridded Precipitation",
            ...     {"grid_name": "AORC_Grid"}
            ... )
        """
        met_path = Path(met_path)
        method = str(method).strip()
        precip_data = dict(data or {})

        if not method:
            raise ValueError("method must be a non-empty precipitation method")
        if method not in HmsMet.PRECIP_METHODS:
            logger.warning(f"Non-standard precipitation method: {method}")

        content = HmsMet._read_met_file(met_path)
        original_content = content
        content = HmsMet._set_meteorology_parameter(
            content,
            HmsMet._PRECIP_METHOD_KEY,
            method
        )

        summary: Dict[str, Any] = {
            'met_file': str(met_path),
            'method': method,
            'depths_written': 0,
            'subbasins_modified': 0,
            'subbasins_not_found': [],
            'grid_name': None,
            'dss_references_written': 0,
        }

        has_depths = 'depths' in precip_data
        has_gages = (
            'gage_assignments' in precip_data
            or 'subbasin_assignments' in precip_data
        )
        has_grid = (
            'grid_name' in precip_data
            or 'precipitation_grid' in precip_data
        )

        if method in HmsMet._FREQUENCY_METHODS or has_depths:
            if not has_depths:
                raise ValueError("Frequency precipitation requires a non-empty 'depths' list")
            content, depths_written = HmsMet._set_frequency_storm_depths(
                content,
                precip_data['depths'],
                precip_data.get('frequency_parameters'),
                method
            )
            summary['depths_written'] = depths_written

        if method in HmsMet._GAGE_METHODS or has_gages:
            assignments = precip_data.get(
                'gage_assignments',
                precip_data.get('subbasin_assignments')
            )
            if assignments is None:
                raise ValueError(f"{method} precipitation requires gage assignments")

            assignments_df = HmsMet._normalize_gage_assignments(assignments)
            content, gage_summary = HmsMet._set_gage_assignments_in_content(
                content,
                assignments_df
            )
            if gage_summary['subbasins_not_found']:
                raise ValueError(
                    "Gage assignments reference missing subbasins: "
                    f"{gage_summary['subbasins_not_found']}"
                )
            summary.update(gage_summary)

        if method == 'Gridded Precipitation' or has_grid:
            content, grid_summary = HmsMet._set_gridded_precipitation(
                content,
                precip_data
            )
            summary.update(grid_summary)

        if method == 'None' and precip_data:
            raise ValueError("Precipitation method 'None' does not accept precipitation data")

        if content == original_content:
            logger.info(f"Precipitation configuration already matched {met_path.name}")
        else:
            HmsFileParser.write_file(met_path, content)
            logger.info(f"Updated precipitation configuration in {met_path.name}")

        return summary

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
        match = re.search(
            r'Meteorology:\s*(.+?)\n(.*?)(?=^End:)',
            content,
            re.DOTALL | re.IGNORECASE | re.MULTILINE,
        )
        if not match:
            return {}

        name = match.group(1).strip()
        params = HmsFileParser._parse_attribute_block(match.group(2))
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

    @staticmethod
    def _set_meteorology_parameter(content: str, param_name: str, new_value: Any) -> str:
        """Update or insert a parameter inside the main Meteorology block."""
        pattern = r'(Meteorology:\s*.+?\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            raise ValueError("Meteorology block not found in met file")

        header, body, footer = match.group(1), match.group(2), match.group(3)
        body, changed = HmsFileParser.update_parameter(body, param_name, new_value)
        if not changed and param_name == HmsMet._PRECIP_METHOD_KEY:
            body, changed = HmsFileParser.update_parameter(
                body,
                HmsMet._LEGACY_PRECIP_METHOD_KEY,
                new_value
            )

        if not changed:
            body = HmsMet._append_block_parameter(body, param_name, new_value)

        new_block = header + body + footer
        return content[:match.start()] + new_block + content[match.end():]

    @staticmethod
    def _append_block_parameter(block_body: str, param_name: str, value: Any) -> str:
        """Append an indented HMS key/value line to a block body."""
        if block_body and not block_body.endswith('\n'):
            block_body += '\n'
        return block_body + f"     {param_name}: {value}\n"

    @staticmethod
    def _select_existing_key(attrs: Dict[str, str], preferred: str, alternate: str) -> str:
        """Select the key already used in a block, falling back to preferred."""
        if preferred in attrs:
            return preferred
        if alternate in attrs:
            return alternate
        return preferred

    @staticmethod
    def _get_precip_gage_value(attrs: Dict[str, str]) -> Optional[str]:
        """Get a precipitation gage value from known HMS met key variants."""
        return attrs.get(HmsMet._PRECIP_GAGE_KEY) or attrs.get(HmsMet._ALT_PRECIP_GAGE_KEY)

    @staticmethod
    def _get_precip_weight_value(attrs: Dict[str, str]) -> Optional[str]:
        """Get a precipitation gage weight from known HMS met key variants."""
        return attrs.get(HmsMet._PRECIP_WEIGHT_KEY) or attrs.get(HmsMet._ALT_PRECIP_WEIGHT_KEY)

    @staticmethod
    def _format_depth(value: Any) -> str:
        """Format a precipitation depth using the existing HMS write convention."""
        return f"{float(value):.4f}"

    @staticmethod
    def _set_frequency_storm_depths(
        content: str,
        depths: List[float],
        frequency_parameters: Optional[Mapping[str, Any]] = None,
        method: str = 'Frequency Based Hypothetical'
    ) -> tuple[str, int]:
        """Update or create the Precip Method Parameters depth lines."""
        if depths is None or len(depths) == 0:
            raise ValueError("Frequency precipitation requires a non-empty 'depths' list")

        depth_values = [float(depth) for depth in depths]
        parameters = dict(frequency_parameters or {})

        pattern = r'(Precip Method Parameters:\s*(.+?)\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            block = HmsMet._build_frequency_storm_block(
                method,
                depth_values,
                parameters
            )
            meteorology_match = re.search(
                r'(Meteorology:\s*.+?\n.*?End:\s*\n)',
                content,
                re.DOTALL | re.IGNORECASE
            )
            if not meteorology_match:
                raise ValueError("Meteorology block not found in met file")
            insert_at = meteorology_match.end()
            separator = '' if content[insert_at:insert_at + 1] == '\n' else '\n'
            return (
                content[:insert_at] + separator + block + content[insert_at:],
                len(depth_values),
            )

        header, block_method, body, footer = (
            match.group(1),
            match.group(2).strip(),
            match.group(3),
            match.group(4),
        )
        if block_method != method:
            header = re.sub(
                r'Precip Method Parameters:\s*.+?\n',
                f"Precip Method Parameters: {method}\n",
                header,
                count=1,
            )

        for key, value in parameters.items():
            body = HmsMet._upsert_parameter_before_depths(body, str(key), value)

        lines = body.splitlines(keepends=True)
        depth_indices = [
            idx for idx, line in enumerate(lines)
            if re.match(r'^\s*Depth:\s*[-+]?\d*\.?\d+\s*$', line.strip('\r\n'))
        ]
        indent = '     '
        if depth_indices:
            indent_match = re.match(r'^(\s*)Depth:', lines[depth_indices[0]])
            if indent_match:
                indent = indent_match.group(1)

        new_depth_lines = [
            f"{indent}Depth: {HmsMet._format_depth(depth)}\n"
            for depth in depth_values
        ]

        if not depth_indices:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            lines.extend(new_depth_lines)
        elif len(depth_indices) == len(new_depth_lines):
            for idx, new_line in zip(depth_indices, new_depth_lines):
                lines[idx] = new_line
        else:
            first_depth_idx = depth_indices[0]
            depth_index_set = set(depth_indices)
            lines = [
                line for idx, line in enumerate(lines)
                if idx not in depth_index_set
            ]
            lines[first_depth_idx:first_depth_idx] = new_depth_lines

        body = ''.join(lines)
        new_block = header + body + footer
        return content[:match.start()] + new_block + content[match.end():], len(depth_values)

    @staticmethod
    def _build_frequency_storm_block(
        method: str,
        depths: List[float],
        parameters: Mapping[str, Any]
    ) -> str:
        """Build a minimal Precip Method Parameters block for frequency storms."""
        lines = [f"Precip Method Parameters: {method}"]
        for key, value in parameters.items():
            lines.append(f"     {key}: {value}")
        lines.extend(
            f"     Depth: {HmsMet._format_depth(depth)}"
            for depth in depths
        )
        lines.extend(["End:", ""])
        return "\n".join(lines)

    @staticmethod
    def _upsert_parameter_before_depths(block_body: str, param_name: str, value: Any) -> str:
        """Update a block parameter or insert it before the first depth line."""
        updated, changed = HmsFileParser.update_parameter(block_body, param_name, value)
        if changed:
            return updated

        lines = block_body.splitlines(keepends=True)
        insert_at = len(lines)
        for idx, line in enumerate(lines):
            if re.match(r'^\s*Depth:', line):
                insert_at = idx
                break
        lines.insert(insert_at, f"     {param_name}: {value}\n")
        return ''.join(lines)

    @staticmethod
    def _normalize_gage_assignments(assignments: Any) -> pd.DataFrame:
        """Normalize supported gage-assignment inputs to a DataFrame."""
        if isinstance(assignments, pd.DataFrame):
            df = assignments.copy()
        elif isinstance(assignments, Mapping):
            rows = []
            for subbasin, value in assignments.items():
                if isinstance(value, Mapping):
                    row = {'subbasin': subbasin}
                    row.update(value)
                else:
                    row = {'subbasin': subbasin, 'precip_gage': value}
                rows.append(row)
            df = pd.DataFrame(rows)
        else:
            df = pd.DataFrame(assignments)

        rename_map = {
            'Subbasin': 'subbasin',
            'subbasin_name': 'subbasin',
            'Precip Gage': 'precip_gage',
            'Precipitation Gage': 'precip_gage',
            'gage': 'precip_gage',
            'Gage': 'precip_gage',
            'Precipitation Gage Weight': 'weight',
            'Weight': 'weight',
        }
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        if 'subbasin' not in df.columns:
            raise ValueError("gage assignments must include a 'subbasin' column")
        if 'precip_gage' not in df.columns:
            raise ValueError("gage assignments must include a 'precip_gage' column")
        if df.empty:
            raise ValueError("gage assignments must include at least one row")

        missing_subbasin = df['subbasin'].isna() | (df['subbasin'].astype(str).str.strip() == '')
        missing_gage = df['precip_gage'].isna() | (df['precip_gage'].astype(str).str.strip() == '')
        if missing_subbasin.any():
            raise ValueError("gage assignments contain empty subbasin names")
        if missing_gage.any():
            raise ValueError("gage assignments contain empty precipitation gage names")

        return df

    @staticmethod
    def _set_gage_assignments_in_content(
        content: str,
        assignments_df: pd.DataFrame
    ) -> tuple[str, Dict[str, Any]]:
        """Apply gage assignments to existing Subbasin blocks."""
        update_lookup = {}
        for _, row in assignments_df.iterrows():
            update_lookup[str(row['subbasin'])] = {
                'precip_gage': str(row['precip_gage']),
                'weight': row.get('weight'),
            }

        summary = {
            'subbasins_modified': 0,
            'subbasins_not_found': [],
        }
        blocks = HmsFileParser.find_all_blocks(content, 'Subbasin')
        found_names = set()

        for match, name, attrs in reversed(blocks):
            if name not in update_lookup:
                continue

            found_names.add(name)
            updates = update_lookup[name]
            block_body = match.group(3)
            modified = False

            gage_key = HmsMet._select_existing_key(
                attrs,
                HmsMet._PRECIP_GAGE_KEY,
                HmsMet._ALT_PRECIP_GAGE_KEY,
            )
            block_body, changed = HmsFileParser.update_parameter(
                block_body,
                gage_key,
                updates['precip_gage']
            )
            if not changed:
                block_body = HmsMet._append_block_parameter(
                    block_body,
                    gage_key,
                    updates['precip_gage']
                )
            modified = True

            weight = updates.get('weight')
            if pd.notna(weight):
                weight_key = HmsMet._select_existing_key(
                    HmsFileParser._parse_attribute_block(block_body),
                    HmsMet._PRECIP_WEIGHT_KEY,
                    HmsMet._ALT_PRECIP_WEIGHT_KEY,
                )
                block_body, changed = HmsFileParser.update_parameter(
                    block_body,
                    weight_key,
                    weight
                )
                if not changed:
                    block_body = HmsMet._append_block_parameter(
                        block_body,
                        weight_key,
                        weight
                    )

            if modified:
                new_block = match.group(1) + block_body + match.group(4)
                content = content[:match.start()] + new_block + content[match.end():]
                summary['subbasins_modified'] += 1

        for name in update_lookup:
            if name not in found_names:
                summary['subbasins_not_found'].append(name)

        return content, summary

    @staticmethod
    def _set_gridded_precipitation(
        content: str,
        precip_data: Mapping[str, Any]
    ) -> tuple[str, Dict[str, Any]]:
        """Set gridded precipitation references in the Meteorology block."""
        grid_name = precip_data.get('grid_name', precip_data.get('precipitation_grid'))
        if grid_name is None or str(grid_name).strip() == '':
            raise ValueError("Gridded precipitation requires a non-empty 'grid_name'")

        content = HmsMet._set_meteorology_parameter(
            content,
            'Precipitation Grid',
            str(grid_name)
        )
        dss_refs = 0

        dss_file = precip_data.get('dss_file')
        if dss_file is not None:
            content = HmsMet._set_meteorology_parameter(
                content,
                'DSS File Name',
                str(dss_file)
            )
            dss_refs += 1

        dss_pathname = precip_data.get('dss_pathname')
        if dss_pathname is not None:
            HmsMet._validate_dss_pathname(str(dss_pathname))
            content = HmsMet._set_meteorology_parameter(
                content,
                'DSS Pathname',
                str(dss_pathname)
            )
            dss_refs += 1

        return content, {
            'grid_name': str(grid_name),
            'dss_references_written': dss_refs,
        }

    @staticmethod
    def _validate_dss_pathname(pathname: str) -> None:
        """Validate a DSS pathname-like reference before writing it."""
        if not pathname or not pathname.startswith('/') or not pathname.endswith('/'):
            raise ValueError(f"Invalid DSS pathname: {pathname!r}")
        if len(pathname.split('/')) < 8:
            raise ValueError(f"Invalid DSS pathname: {pathname!r}")

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
