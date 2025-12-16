"""
HmsBasin - Basin Model File Operations

This module provides static methods for reading and modifying HEC-HMS basin model
files (.basin). It handles subbasins, junctions, reaches, and their parameters.

All methods are static and designed to be used without instantiation.
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
import pandas as pd

from .LoggingConfig import get_logger
from .Decorators import log_call
from ._parsing import HmsFileParser
from ._constants import LOSS_METHODS, TRANSFORM_METHODS, BASEFLOW_METHODS, ROUTING_METHODS

logger = get_logger(__name__)


class HmsBasin:
    """
    Basin model file operations (.basin files).

    Parse and modify subbasin parameters including loss methods, transform methods,
    baseflow methods, and routing parameters.

    All methods are static - no instantiation required.

    Example:
        >>> from hms_commander import HmsBasin
        >>> subbasins = HmsBasin.get_subbasins("model.basin")
        >>> print(subbasins)
        >>> loss_params = HmsBasin.get_loss_parameters("model.basin", "Subbasin-1")
    """

    # HMS method enumerations (from _constants)

    @staticmethod
    @log_call
    def get_subbasins(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all subbasins from a basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, area, downstream, loss_method,
            transform_method, baseflow_method, percent_impervious, etc.

        Example:
            >>> subbasins = HmsBasin.get_subbasins("model.basin")
            >>> print(subbasins[['name', 'area', 'loss_method']])
        """
        basin_path = Path(basin_path)
        logger.info(f"Reading subbasins from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)
        subbasins = HmsBasin._parse_elements(content, "Subbasin")

        records = []
        for name, attrs in subbasins.items():
            record = {
                'name': name,
                'area': attrs.get('Area'),
                'downstream': attrs.get('Downstream'),
                'loss_method': attrs.get('Loss'),
                'transform_method': attrs.get('Transform'),
                'baseflow_method': attrs.get('Baseflow'),
                'percent_impervious': attrs.get('Percent Impervious Area'),
                'canvas_x': attrs.get('Canvas X'),
                'canvas_y': attrs.get('Canvas Y'),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} subbasins")
        return df

    @staticmethod
    @log_call
    def get_junctions(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all junctions from a basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, downstream, canvas_x, canvas_y

        Example:
            >>> junctions = HmsBasin.get_junctions("model.basin")
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        junctions = HmsBasin._parse_elements(content, "Junction")

        records = []
        for name, attrs in junctions.items():
            record = {
                'name': name,
                'downstream': attrs.get('Downstream'),
                'canvas_x': attrs.get('Canvas X'),
                'canvas_y': attrs.get('Canvas Y'),
            }
            records.append(record)

        return pd.DataFrame(records)

    @staticmethod
    @log_call
    def get_reaches(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get all reaches from a basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, downstream, route_method, etc.

        Example:
            >>> reaches = HmsBasin.get_reaches("model.basin")
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        reaches = HmsBasin._parse_elements(content, "Reach")

        records = []
        for name, attrs in reaches.items():
            record = {
                'name': name,
                'downstream': attrs.get('Downstream'),
                'route_method': attrs.get('Route'),
                'canvas_x': attrs.get('Canvas X'),
                'canvas_y': attrs.get('Canvas Y'),
                'from_canvas_x': attrs.get('From Canvas X'),
                'from_canvas_y': attrs.get('From Canvas Y'),
            }
            records.append(record)

        return pd.DataFrame(records)

    @staticmethod
    @log_call
    def get_loss_parameters(
        basin_path: Union[str, Path],
        subbasin_name: str,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get loss method parameters for a specific subbasin.

        Args:
            basin_path: Path to the .basin file
            subbasin_name: Name of the subbasin
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary of loss parameters (varies by method type)

        Example:
            >>> params = HmsBasin.get_loss_parameters("model.basin", "Subbasin-1")
            >>> print(params)
            {'method': 'Deficit and Constant', 'initial_deficit': 25.4, ...}
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        subbasins = HmsBasin._parse_elements(content, "Subbasin")

        if subbasin_name not in subbasins:
            raise ValueError(f"Subbasin '{subbasin_name}' not found in basin file")

        attrs = subbasins[subbasin_name]
        loss_method = attrs.get('Loss', 'None')

        params = {'method': loss_method}

        # Common loss parameters
        if 'Initial Deficit' in attrs:
            params['initial_deficit'] = float(attrs['Initial Deficit'])
        if 'Maximum Deficit' in attrs:
            params['maximum_deficit'] = float(attrs['Maximum Deficit'])
        if 'Constant Rate' in attrs:
            params['constant_rate'] = float(attrs['Constant Rate'])
        if 'Percolation Rate' in attrs:
            params['percolation_rate'] = float(attrs['Percolation Rate'])
        if 'Percent Impervious Area' in attrs:
            params['percent_impervious'] = float(attrs['Percent Impervious Area'])

        # SCS Curve Number parameters
        if 'Curve Number' in attrs:
            params['curve_number'] = float(attrs['Curve Number'])
        if 'Initial Abstraction' in attrs:
            params['initial_abstraction'] = float(attrs['Initial Abstraction'])

        # Green and Ampt parameters
        if 'Conductivity' in attrs:
            params['conductivity'] = float(attrs['Conductivity'])
        if 'Suction' in attrs:
            params['suction'] = float(attrs['Suction'])
        if 'Initial Content' in attrs:
            params['initial_content'] = float(attrs['Initial Content'])
        if 'Saturated Content' in attrs:
            params['saturated_content'] = float(attrs['Saturated Content'])

        return params

    @staticmethod
    @log_call
    def set_loss_parameters(
        basin_path: Union[str, Path],
        subbasin_name: str,
        initial_deficit: float = None,
        maximum_deficit: float = None,
        constant_rate: float = None,
        percolation_rate: float = None,
        percent_impervious: float = None,
        curve_number: float = None,
        hms_object=None
    ) -> bool:
        """
        Set loss method parameters for a specific subbasin.

        Args:
            basin_path: Path to the .basin file
            subbasin_name: Name of the subbasin
            initial_deficit: Initial deficit (inches or mm)
            maximum_deficit: Maximum deficit (inches or mm)
            constant_rate: Constant loss rate (in/hr or mm/hr)
            percolation_rate: Percolation rate (in/hr or mm/hr)
            percent_impervious: Percent impervious area (0-100)
            curve_number: SCS curve number (0-100)
            hms_object: Optional HmsPrj instance

        Returns:
            True if successful

        Example:
            >>> HmsBasin.set_loss_parameters(
            ...     "model.basin", "Subbasin-1",
            ...     initial_deficit=1.0, maximum_deficit=3.0
            ... )
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)

        # Find the subbasin block
        pattern = rf'(Subbasin:\s*{re.escape(subbasin_name)}\s*\n)(.*?)(End:)'
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)

        if not match:
            raise ValueError(f"Subbasin '{subbasin_name}' not found in basin file")

        block_content = match.group(2)
        modified = False

        # Update parameters
        if initial_deficit is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Initial Deficit', initial_deficit
            )
            modified = modified or changed

        if maximum_deficit is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Maximum Deficit', maximum_deficit
            )
            modified = modified or changed

        if constant_rate is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Constant Rate', constant_rate
            )
            modified = modified or changed

        if percolation_rate is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Percolation Rate', percolation_rate
            )
            modified = modified or changed

        if percent_impervious is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Percent Impervious Area', percent_impervious
            )
            modified = modified or changed

        if curve_number is not None:
            block_content, changed = HmsBasin._update_parameter(
                block_content, 'Curve Number', curve_number
            )
            modified = modified or changed

        if modified:
            new_block = match.group(1) + block_content + match.group(3)
            new_content = content[:match.start()] + new_block + content[match.end():]

            with open(basin_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info(f"Updated loss parameters for subbasin '{subbasin_name}'")

        return True

    @staticmethod
    @log_call
    def get_transform_parameters(
        basin_path: Union[str, Path],
        subbasin_name: str,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get transform method parameters for a specific subbasin.

        Args:
            basin_path: Path to the .basin file
            subbasin_name: Name of the subbasin
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary of transform parameters

        Example:
            >>> params = HmsBasin.get_transform_parameters("model.basin", "Subbasin-1")
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        subbasins = HmsBasin._parse_elements(content, "Subbasin")

        if subbasin_name not in subbasins:
            raise ValueError(f"Subbasin '{subbasin_name}' not found")

        attrs = subbasins[subbasin_name]
        transform_method = attrs.get('Transform', 'None')

        params = {'method': transform_method}

        # Clark Unit Hydrograph parameters
        if 'Time of Concentration' in attrs:
            params['time_of_concentration'] = float(attrs['Time of Concentration'])
        if 'Storage Coefficient' in attrs:
            params['storage_coefficient'] = float(attrs['Storage Coefficient'])

        # SCS Unit Hydrograph parameters
        if 'Lag Time' in attrs:
            params['lag_time'] = float(attrs['Lag Time'])
        if 'Graph Type' in attrs:
            params['graph_type'] = attrs['Graph Type']

        # Snyder parameters
        if 'Snyder Tp' in attrs:
            params['snyder_tp'] = float(attrs['Snyder Tp'])
        if 'Snyder Cp' in attrs:
            params['snyder_cp'] = float(attrs['Snyder Cp'])

        return params

    @staticmethod
    @log_call
    def get_baseflow_parameters(
        basin_path: Union[str, Path],
        subbasin_name: str,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get baseflow method parameters for a specific subbasin.

        Args:
            basin_path: Path to the .basin file
            subbasin_name: Name of the subbasin
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary of baseflow parameters
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        subbasins = HmsBasin._parse_elements(content, "Subbasin")

        if subbasin_name not in subbasins:
            raise ValueError(f"Subbasin '{subbasin_name}' not found")

        attrs = subbasins[subbasin_name]
        baseflow_method = attrs.get('Baseflow', 'None')

        params = {'method': baseflow_method}

        # Recession parameters
        if 'Recession Factor' in attrs:
            params['recession_factor'] = float(attrs['Recession Factor'])
        if 'Initial Discharge' in attrs:
            params['initial_discharge'] = float(attrs['Initial Discharge'])
        if 'Threshold Type' in attrs:
            params['threshold_type'] = attrs['Threshold Type']

        # Linear Reservoir parameters
        if 'GW 1 Initial' in attrs:
            params['gw1_initial'] = float(attrs['GW 1 Initial'])
        if 'GW 1 Coefficient' in attrs:
            params['gw1_coefficient'] = float(attrs['GW 1 Coefficient'])
        if 'GW 2 Initial' in attrs:
            params['gw2_initial'] = float(attrs['GW 2 Initial'])
        if 'GW 2 Coefficient' in attrs:
            params['gw2_coefficient'] = float(attrs['GW 2 Coefficient'])

        return params

    @staticmethod
    @log_call
    def get_routing_parameters(
        basin_path: Union[str, Path],
        reach_name: str,
        hms_object=None
    ) -> Dict[str, Any]:
        """
        Get routing method parameters for a specific reach.

        Args:
            basin_path: Path to the .basin file
            reach_name: Name of the reach
            hms_object: Optional HmsPrj instance

        Returns:
            Dictionary of routing parameters
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)
        reaches = HmsBasin._parse_elements(content, "Reach")

        if reach_name not in reaches:
            raise ValueError(f"Reach '{reach_name}' not found")

        attrs = reaches[reach_name]
        route_method = attrs.get('Route', 'None')

        params = {'method': route_method}

        # Muskingum parameters
        if 'Muskingum K' in attrs:
            params['muskingum_k'] = float(attrs['Muskingum K'])
        if 'Muskingum x' in attrs:
            params['muskingum_x'] = float(attrs['Muskingum x'])
        if 'Muskingum Steps' in attrs:
            params['muskingum_steps'] = int(attrs['Muskingum Steps'])

        # Lag parameters
        if 'Lag' in attrs:
            params['lag'] = float(attrs['Lag'])

        # Muskingum-Cunge parameters
        if 'Reach Length' in attrs:
            params['reach_length'] = float(attrs['Reach Length'])
        if 'Reach Slope' in attrs:
            params['reach_slope'] = float(attrs['Reach Slope'])
        if 'Manning n' in attrs:
            params['mannings_n'] = float(attrs['Manning n'])

        return params

    @staticmethod
    @log_call
    def clone_basin(
        template_basin: str,
        new_name: str,
        description: str = None,
        hms_object=None
    ) -> Path:
        """
        Clone a basin model file with a new name.

        Follows the CLB Engineering LLM Forward Approach:
        - Non-destructive: Creates new file, preserves original
        - Traceable: Updates description with clone metadata
        - GUI-verifiable: New basin appears in HEC-HMS GUI
        - Project integration: Updates .hms project file

        Args:
            template_basin: Name or path of the template basin file
            new_name: Name for the new basin model
            description: Optional description (defaults to "Cloned from {template}")
            hms_object: Optional HmsPrj instance

        Returns:
            Path to the new basin file

        Raises:
            FileNotFoundError: If template basin not found
            FileExistsError: If new basin already exists

        Example:
            >>> # Clone for Atlas 14 update
            >>> new_path = HmsBasin.clone_basin(
            ...     "Tifton_Original",
            ...     "Tifton_Atlas14",
            ...     description="Atlas 14 precipitation update",
            ...     hms_object=hms
            ... )
            >>> # New basin now visible in HEC-HMS GUI
        """
        from .HmsUtils import HmsUtils
        from .HmsPrj import hms

        hms_obj = hms_object or hms
        template_path = Path(template_basin)

        # Try to resolve template path from project
        if not template_path.exists() and hms_obj is not None and hms_obj.initialized:
            matching = hms_obj.basin_df[
                hms_obj.basin_df['name'] == template_basin
            ]
            if not matching.empty:
                template_path = Path(matching.iloc[0]['full_path'])
                template_name = matching.iloc[0]['name']
            else:
                # Try with .basin extension
                potential = Path(template_basin)
                if not potential.suffix:
                    template_path = potential.with_suffix('.basin')
                    template_name = template_basin
                else:
                    template_name = template_path.stem
        else:
            template_name = template_path.stem

        if not template_path.exists():
            raise FileNotFoundError(f"Template basin not found: {template_basin}")

        # Build new path
        new_path = template_path.parent / f"{new_name}.basin"

        # Default description
        if description is None:
            description = f"Cloned from {template_name}"

        # Define modification callback
        def update_basin_metadata(lines):
            """Update basin name and description in cloned file."""
            modified_lines = []
            in_basin_block = False
            description_found = False

            for line in lines:
                # Update Basin: line
                if re.match(r'^Basin:\s*', line):
                    modified_lines.append(f"Basin: {new_name}\n")
                    in_basin_block = True
                # Update Description: line if it exists
                elif in_basin_block and re.match(r'^\s+Description:\s*', line):
                    modified_lines.append(f"     Description: {description}\n")
                    description_found = True
                # Add Description: if we hit End: without finding one
                elif in_basin_block and line.strip() == 'End:':
                    if not description_found:
                        modified_lines.append(f"     Description: {description}\n")
                    modified_lines.append(line)
                    in_basin_block = False
                    description_found = False
                else:
                    modified_lines.append(line)

            return modified_lines

        # Clone file with modification
        HmsUtils.clone_file(template_path, new_path, update_basin_metadata)

        # Update project file if we have an HMS object
        if hms_obj is not None and hms_obj.initialized:
            try:
                HmsUtils.update_project_file(
                    hms_obj.project_file,
                    'Basin',
                    new_name
                )

                # Re-initialize to pick up new basin
                hms_obj.initialize(hms_obj.project_folder, hms_obj.hms_exe_path)
                logger.info(f"Re-initialized project to register new basin '{new_name}'")

            except Exception as e:
                logger.warning(f"Could not update project file: {e}")

        logger.info(f"Cloned basin: {template_name} → {new_name}")
        return new_path

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _read_basin_file(basin_path: Path) -> str:
        """Read basin file content with encoding fallback."""
        return HmsFileParser.read_file(basin_path)

    @staticmethod
    def _parse_elements(content: str, element_type: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse all elements of a given type from basin file content.

        Args:
            content: Basin file content
            element_type: Type of element (Subbasin, Junction, Reach, etc.)

        Returns:
            Dictionary mapping element names to their attributes
        """
        return HmsFileParser.parse_blocks(content, element_type)

    @staticmethod
    def _update_parameter(
        block_content: str,
        param_name: str,
        new_value: Union[float, int, str]
    ) -> Tuple[str, bool]:
        """
        Update a parameter value in a block of content.

        Returns:
            Tuple of (modified content, whether change was made)
        """
        return HmsFileParser.update_parameter(block_content, param_name, new_value)
