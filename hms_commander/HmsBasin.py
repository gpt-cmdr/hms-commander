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
from ._constants import (
    LOSS_METHODS, TRANSFORM_METHODS, BASEFLOW_METHODS, ROUTING_METHODS,
    LOSS_PARAM_MAP, LOSS_PARAM_REVERSE_MAP,
    TRANSFORM_PARAM_MAP, TRANSFORM_PARAM_REVERSE_MAP,
    BASEFLOW_PARAM_MAP, BASEFLOW_PARAM_REVERSE_MAP,
    ROUTING_PARAM_MAP, ROUTING_PARAM_REVERSE_MAP,
)

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
                'area': HmsFileParser.to_numeric(attrs.get('Area')),
                'downstream': attrs.get('Downstream'),
                'loss_method': attrs.get('LossRate', attrs.get('Loss')),
                'transform_method': attrs.get('Transform'),
                'baseflow_method': attrs.get('Baseflow'),
                'percent_impervious': HmsFileParser.to_numeric(attrs.get('Percent Impervious Area')),
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
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
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
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
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
                'from_canvas_x': HmsFileParser.to_numeric(attrs.get('From Canvas X')),
                'from_canvas_y': HmsFileParser.to_numeric(attrs.get('From Canvas Y')),
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
        loss_method = attrs.get('LossRate', attrs.get('Loss', 'None'))

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

        # Modified Puls parameters
        if 'Number of Reaches' in attrs:
            params['number_of_reaches'] = int(attrs['Number of Reaches'])
        if 'Storage Outflow Table Name' in attrs:
            params['storage_outflow_table_name'] = attrs['Storage Outflow Table Name']

        return params

    @staticmethod
    @log_call
    def set_modified_puls_routing(
        basin_path: Union[str, Path],
        reach_name: str,
        sd_df,
        number_of_subreaches: int,
        table_name: Optional[str] = None,
        hms_object=None,
    ) -> str:
        """
        Set Modified Puls routing for an HMS reach.

        Convenience wrapper that calls ``import_modified_puls_table()`` to write
        the .tbl and .pdata files, then updates the .basin file routing method
        and number of subreaches.

        Args:
            basin_path: Path to the .basin file
            reach_name: Name of the reach to update
            sd_df: DataFrame with columns ``['storage_acft', 'outflow_cfs']``
                   (as returned by ``RasModPuls.extract_storage_outflow()``)
            number_of_subreaches: Number of Modified Puls subreaches
                                   (from ``RasModPuls.compute_subreach_count()``)
            table_name: Name for the paired data table. Auto-generated from reach
                        name if None (e.g., "ModPuls_{reach_name}").
            hms_object: Optional HmsPrj instance

        Returns:
            str: Name of the paired data table written

        Example:
            >>> sq_df = RasModPuls.extract_storage_outflow(plan_hdf, profile_line, "01")
            >>> n = RasModPuls.compute_subreach_count(travel_time_hours=6.0)
            >>> table = HmsBasin.set_modified_puls_routing(
            ...     "MyProject.basin", "Reach-1", sq_df, n
            ... )
            >>> print(f"Table written: {table}")
        """
        basin_path = Path(basin_path)

        # Generate table name if not provided
        if table_name is None:
            safe_name = reach_name.replace(" ", "_").replace("-", "_")
            table_name = f"ModPuls_{safe_name}"

        # Write S-Q table to .tbl and .pdata files, and update basin reference
        HmsBasin.import_modified_puls_table(
            basin_path=basin_path,
            reach_name=reach_name,
            storage_discharge_data=sd_df,
            table_name=table_name,
            hms_object=hms_object,
        )

        # Update routing method and subreaches in the basin file
        content = HmsBasin._read_basin_file(basin_path)
        from .HmsFileParser import HmsFileParser

        reach_blocks = HmsFileParser.find_all_blocks(content, "Reach")
        for match, name, attrs in reach_blocks:
            if name == reach_name:
                block_body = match.group(3)

                # Set routing method to Modified Puls
                new_block, _ = HmsFileParser.update_parameter(
                    block_body, "Route", "Modified Puls"
                )
                # Set number of subreaches
                new_block, _ = HmsFileParser.update_parameter(
                    new_block, "Number of Reaches", str(number_of_subreaches)
                )

                content = content[: match.start(3)] + new_block + content[match.end(3):]
                break

        HmsBasin._write_basin_file(basin_path, content)
        logger.info(
            f"Set Modified Puls routing on reach '{reach_name}': "
            f"table='{table_name}', subreaches={number_of_subreaches}"
        )
        return table_name

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
    # Diversion and Network Analysis Methods
    # =========================================================================

    @staticmethod
    @log_call
    def get_diversions(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Extract diversion elements from basin model file.

        CRITICAL: Diversions are NOT extracted by HmsGeo or other element methods.
        Without diversions, upstream drainage area calculations can be
        catastrophically wrong (e.g., 6 sq mi vs 52 sq mi for South Belt).

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, downstream, divert_to, canvas_x,
            canvas_y, from_canvas_x, from_canvas_y, description

        Example:
            >>> diversions = HmsBasin.get_diversions("model.basin")
            >>> print(diversions[['name', 'downstream', 'divert_to']])
        """
        basin_path = Path(basin_path)
        logger.info(f"Reading diversions from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)
        diversions = HmsBasin._parse_elements(content, "Diversion")

        records = []
        for name, attrs in diversions.items():
            record = {
                'name': name,
                'downstream': attrs.get('Downstream'),
                'divert_to': attrs.get('Divert To'),
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
                'from_canvas_x': HmsFileParser.to_numeric(attrs.get('From Canvas X')),
                'from_canvas_y': HmsFileParser.to_numeric(attrs.get('From Canvas Y')),
                'description': attrs.get('Description', ''),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} diversions")
        return df

    @staticmethod
    @log_call
    def get_reservoirs(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Extract reservoir elements from basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, downstream, canvas_x, canvas_y,
            from_canvas_x, from_canvas_y, description
        """
        basin_path = Path(basin_path)
        logger.info(f"Reading reservoirs from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)
        reservoirs = HmsBasin._parse_elements(content, "Reservoir")

        records = []
        for name, attrs in reservoirs.items():
            record = {
                'name': name,
                'downstream': attrs.get('Downstream'),
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
                'from_canvas_x': HmsFileParser.to_numeric(attrs.get('From Canvas X')),
                'from_canvas_y': HmsFileParser.to_numeric(attrs.get('From Canvas Y')),
                'description': attrs.get('Description', ''),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} reservoirs")
        return df

    @staticmethod
    @log_call
    def get_sources(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Extract source elements from basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, downstream, area, canvas_x, canvas_y,
            from_canvas_x, from_canvas_y, description
        """
        basin_path = Path(basin_path)
        logger.info(f"Reading sources from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)
        sources = HmsBasin._parse_elements(content, "Source")

        records = []
        for name, attrs in sources.items():
            record = {
                'name': name,
                'downstream': attrs.get('Downstream'),
                'area': HmsFileParser.to_numeric(attrs.get('Area')),
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
                'from_canvas_x': HmsFileParser.to_numeric(attrs.get('From Canvas X')),
                'from_canvas_y': HmsFileParser.to_numeric(attrs.get('From Canvas Y')),
                'description': attrs.get('Description', ''),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} sources")
        return df

    @staticmethod
    @log_call
    def get_sinks(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Extract sink elements from basin model file.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with columns: name, canvas_x, canvas_y, description
        """
        basin_path = Path(basin_path)
        logger.info(f"Reading sinks from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)
        sinks = HmsBasin._parse_elements(content, "Sink")

        records = []
        for name, attrs in sinks.items():
            record = {
                'name': name,
                'canvas_x': HmsFileParser.to_numeric(attrs.get('Canvas X')),
                'canvas_y': HmsFileParser.to_numeric(attrs.get('Canvas Y')),
                'description': attrs.get('Description', ''),
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info(f"Found {len(df)} sinks")
        return df

    @staticmethod
    @log_call
    def get_upstream_network(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Build reverse network lookup: for each element, list what flows into it.

        Includes subbasins, junctions, reaches, AND diversions. This is the
        inverse of the 'downstream' relationship used for upstream traversal.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            dict: {element_name: [{'name': str, 'type': str}, ...]}
                  Each entry lists all elements that flow INTO element_name.

        Example:
            >>> network = HmsBasin.get_upstream_network("model.basin")
            >>> print(network["Junction-1"])
            [{'name': 'Sub-A', 'type': 'subbasin'}, {'name': 'Reach-1', 'type': 'reach'}]
        """
        basin_path = Path(basin_path)
        logger.info(f"Building upstream network from: {basin_path}")

        content = HmsBasin._read_basin_file(basin_path)

        # Parse all element types
        element_types = {
            'subbasin': HmsBasin._parse_elements(content, "Subbasin"),
            'junction': HmsBasin._parse_elements(content, "Junction"),
            'reach': HmsBasin._parse_elements(content, "Reach"),
            'diversion': HmsBasin._parse_elements(content, "Diversion"),
        }

        from collections import defaultdict
        upstream_lookup = defaultdict(list)

        for elem_type, elements in element_types.items():
            for name, attrs in elements.items():
                downstream = attrs.get('Downstream', '')
                if downstream:
                    upstream_lookup[downstream].append({
                        'name': name,
                        'type': elem_type
                    })

                # Diversions also route flow via "Divert To"
                if elem_type == 'diversion':
                    divert_to = attrs.get('Divert To', '')
                    if divert_to:
                        upstream_lookup[divert_to].append({
                            'name': name,
                            'type': 'diversion'
                        })

        total_connections = sum(len(v) for v in upstream_lookup.values())
        logger.info(f"Built upstream network: {len(upstream_lookup)} targets, "
                     f"{total_connections} upstream connections")

        return dict(upstream_lookup)

    @staticmethod
    @log_call
    def get_upstream_elements(
        basin_path: Union[str, Path],
        target_element: str,
        hms_object=None
    ) -> Dict[str, List[str]]:
        """
        Find all elements upstream of target (recursive, cycle-safe).

        Traverses the network in reverse (upstream) direction, collecting
        all subbasins, junctions, reaches, and diversions that contribute
        flow to the target element.

        Args:
            basin_path: Path to the .basin file
            target_element: Name of element to find upstream of
            hms_object: Optional HmsPrj instance

        Returns:
            dict: {
                'subbasins': [name, ...],
                'junctions': [name, ...],
                'reaches': [name, ...],
                'diversions': [name, ...]
            }

        Example:
            >>> upstream = HmsBasin.get_upstream_elements("model.basin", "Outlet_J")
            >>> print(f"Upstream subbasins: {len(upstream['subbasins'])}")
        """
        basin_path = Path(basin_path)

        # Build upstream network
        network = HmsBasin.get_upstream_network(basin_path, hms_object=hms_object)

        # Recursive traversal with cycle detection
        result = {'subbasins': [], 'junctions': [], 'reaches': [], 'diversions': []}
        visited = set()

        def _traverse(element_name):
            if element_name in visited:
                return
            visited.add(element_name)

            upstream_elements = network.get(element_name, [])
            for upstream in upstream_elements:
                name = upstream['name']
                elem_type = upstream['type']

                # Add to appropriate list
                type_key = elem_type + 's'  # subbasin -> subbasins
                if type_key in result:
                    result[type_key].append(name)

                # Recurse upstream
                _traverse(name)

        _traverse(target_element)

        logger.info(f"Upstream of '{target_element}': "
                     f"{len(result['subbasins'])} subbasins, "
                     f"{len(result['junctions'])} junctions, "
                     f"{len(result['reaches'])} reaches, "
                     f"{len(result['diversions'])} diversions")

        return result

    @staticmethod
    @log_call
    def get_contributing_area(
        basin_path: Union[str, Path],
        target_element: str,
        hms_object=None
    ) -> float:
        """
        Calculate total contributing drainage area upstream of target element.

        Combines get_upstream_elements() + area summation from subbasin data.
        Includes areas routed through diversions.

        Args:
            basin_path: Path to the .basin file
            target_element: Name of element to calculate area for
            hms_object: Optional HmsPrj instance

        Returns:
            float: Total area in square miles (or model units)

        Example:
            >>> area = HmsBasin.get_contributing_area("model.basin", "Outlet_J")
            >>> print(f"Contributing area: {area:.2f} sq mi")
        """
        basin_path = Path(basin_path)

        # Get upstream subbasins
        upstream = HmsBasin.get_upstream_elements(
            basin_path, target_element, hms_object=hms_object
        )

        # Get subbasin areas
        subbasins_df = HmsBasin.get_subbasins(basin_path, hms_object=hms_object)

        # Sum areas of upstream subbasins
        upstream_names = set(upstream['subbasins'])
        total_area = 0.0

        for _, row in subbasins_df.iterrows():
            if row['name'] in upstream_names:
                area = row.get('area')
                if area is not None and not pd.isna(area):
                    total_area += float(area)

        logger.info(f"Contributing area for '{target_element}': {total_area:.2f} "
                     f"({len(upstream_names)} subbasins)")

        return total_area

    # =========================================================================
    # Batch Parameter Methods
    # =========================================================================

    @staticmethod
    @log_call
    def get_all_loss_parameters(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get loss parameters for ALL subbasins as a DataFrame.

        Each row is a subbasin. Columns are snake_case parameter names.
        Parameters not applicable to a subbasin's loss method are NaN.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with 'name' column identifying each subbasin and
            loss parameter columns. Parameters not applicable to a
            subbasin's method are NaN.

        Example:
            >>> df = HmsBasin.get_all_loss_parameters("model.basin")
            >>> print(df[['loss_method', 'hydraulic_conductivity']])
        """
        return HmsBasin._get_all_element_params(
            basin_path, "Subbasin", LOSS_PARAM_MAP
        )

    @staticmethod
    @log_call
    def get_all_transform_parameters(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get transform parameters for ALL subbasins as a DataFrame.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with 'name' column identifying each subbasin and
            transform parameter columns.

        Example:
            >>> df = HmsBasin.get_all_transform_parameters("model.basin")
            >>> print(df[['transform_method', 'time_of_concentration']])
        """
        return HmsBasin._get_all_element_params(
            basin_path, "Subbasin", TRANSFORM_PARAM_MAP
        )

    @staticmethod
    @log_call
    def get_all_baseflow_parameters(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get baseflow parameters for ALL subbasins as a DataFrame.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with 'name' column identifying each subbasin and
            baseflow parameter columns.

        Example:
            >>> df = HmsBasin.get_all_baseflow_parameters("model.basin")
        """
        return HmsBasin._get_all_element_params(
            basin_path, "Subbasin", BASEFLOW_PARAM_MAP
        )

    @staticmethod
    @log_call
    def get_all_routing_parameters(
        basin_path: Union[str, Path],
        hms_object=None
    ) -> pd.DataFrame:
        """
        Get routing parameters for ALL reaches as a DataFrame.

        Args:
            basin_path: Path to the .basin file
            hms_object: Optional HmsPrj instance

        Returns:
            DataFrame with 'name' column identifying each reach and
            routing parameter columns.

        Example:
            >>> df = HmsBasin.get_all_routing_parameters("model.basin")
            >>> print(df[['route_method', 'muskingum_k']])
        """
        return HmsBasin._get_all_element_params(
            basin_path, "Reach", ROUTING_PARAM_MAP
        )

    @staticmethod
    @log_call
    def set_all_loss_parameters(
        basin_path: Union[str, Path],
        params_df: pd.DataFrame,
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Set loss parameters for multiple subbasins from a DataFrame.

        Only non-NaN values in the DataFrame are written. NaN columns are
        skipped, making it safe to pass a DataFrame from get_all_loss_parameters()
        with selective edits.

        Args:
            basin_path: Path to the .basin file
            params_df: DataFrame with 'name' column and parameter columns
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Summary dict with keys: elements_modified, parameters_changed,
            elements_not_found, warnings, backup_path

        Example:
            >>> df = HmsBasin.get_all_loss_parameters("model.basin")
            >>> df['hydraulic_conductivity'] = 0.05  # Update all
            >>> result = HmsBasin.set_all_loss_parameters("model.basin", df)
        """
        return HmsBasin._set_all_element_params(
            basin_path, "Subbasin", params_df,
            LOSS_PARAM_REVERSE_MAP, create_backup
        )

    @staticmethod
    @log_call
    def set_all_transform_parameters(
        basin_path: Union[str, Path],
        params_df: pd.DataFrame,
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Set transform parameters for multiple subbasins from a DataFrame.

        Args:
            basin_path: Path to the .basin file
            params_df: DataFrame with 'name' column and parameter columns
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Summary dict

        Example:
            >>> df = HmsBasin.get_all_transform_parameters("model.basin")
            >>> df['time_of_concentration'] *= 1.1  # Increase Tc by 10%
            >>> result = HmsBasin.set_all_transform_parameters("model.basin", df)
        """
        return HmsBasin._set_all_element_params(
            basin_path, "Subbasin", params_df,
            TRANSFORM_PARAM_REVERSE_MAP, create_backup
        )

    @staticmethod
    @log_call
    def set_all_baseflow_parameters(
        basin_path: Union[str, Path],
        params_df: pd.DataFrame,
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Set baseflow parameters for multiple subbasins from a DataFrame.

        Args:
            basin_path: Path to the .basin file
            params_df: DataFrame with 'name' column and parameter columns
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Summary dict
        """
        return HmsBasin._set_all_element_params(
            basin_path, "Subbasin", params_df,
            BASEFLOW_PARAM_REVERSE_MAP, create_backup
        )

    @staticmethod
    @log_call
    def set_all_routing_parameters(
        basin_path: Union[str, Path],
        params_df: pd.DataFrame,
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Set routing parameters for multiple reaches from a DataFrame.

        Args:
            basin_path: Path to the .basin file
            params_df: DataFrame with 'name' column and parameter columns
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Summary dict
        """
        return HmsBasin._set_all_element_params(
            basin_path, "Reach", params_df,
            ROUTING_PARAM_REVERSE_MAP, create_backup
        )

    @staticmethod
    @log_call
    def export_parameters_csv(
        basin_path: Union[str, Path],
        output_csv: Union[str, Path],
        param_types: Optional[List[str]] = None,
        hms_object=None
    ) -> Path:
        """
        Export basin parameters to a CSV file for editing in Excel.

        Creates a CSV with comment header rows containing metadata, then
        standard CSV data. Edit in Excel, then import back with
        import_parameters_csv().

        Args:
            basin_path: Path to the .basin file
            output_csv: Path for the output CSV file
            param_types: List of parameter types to export. Options:
                'loss', 'transform', 'baseflow', 'routing'.
                Default None exports all types.
            hms_object: Optional HmsPrj instance

        Returns:
            Path to the created CSV file

        Example:
            >>> path = HmsBasin.export_parameters_csv("model.basin", "params.csv")
            >>> # Edit params.csv in Excel
            >>> HmsBasin.import_parameters_csv("model.basin", "params.csv")
        """
        from datetime import datetime

        basin_path = Path(basin_path)
        output_csv = Path(output_csv)

        if param_types is None:
            param_types = ['loss', 'transform', 'baseflow', 'routing']

        type_map = {
            'loss': ('Subbasin', LOSS_PARAM_MAP, 'get_all_loss_parameters'),
            'transform': ('Subbasin', TRANSFORM_PARAM_MAP, 'get_all_transform_parameters'),
            'baseflow': ('Subbasin', BASEFLOW_PARAM_MAP, 'get_all_baseflow_parameters'),
            'routing': ('Reach', ROUTING_PARAM_MAP, 'get_all_routing_parameters'),
        }

        # Collect DataFrames
        all_dfs = {}
        for ptype in param_types:
            if ptype not in type_map:
                logger.warning(f"Unknown param_type '{ptype}', skipping")
                continue
            getter = getattr(HmsBasin, type_map[ptype][2])
            df = getter(basin_path, hms_object=hms_object)
            if not df.empty:
                all_dfs[ptype] = df

        if not all_dfs:
            logger.warning("No parameters found to export")
            return output_csv

        # Write each param_type as its own CSV file (type suffix)
        # e.g., params_loss.csv, params_transform.csv, etc.
        written_files = []
        for ptype, df in all_dfs.items():
            if output_csv.suffix:
                type_csv = output_csv.with_name(
                    output_csv.stem + f'_{ptype}' + output_csv.suffix
                )
            else:
                type_csv = output_csv.with_name(output_csv.name + f'_{ptype}.csv')

            df = df.copy()
            df.insert(0, 'param_type', ptype)

            header_lines = [
                f"# HMS Basin Parameters - {ptype}",
                f"# Source: {basin_path.name}",
                f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Import with: HmsBasin.import_parameters_csv(\"{basin_path.name}\", \"{type_csv.name}\")",
            ]
            csv_text = df.to_csv(index=False)
            type_csv.write_text(
                '\n'.join(header_lines) + '\n' + csv_text,
                encoding='utf-8'
            )
            written_files.append(type_csv)
            logger.info(f"Exported {ptype} parameters to {type_csv}")

        # Also write a combined file if multiple types
        if len(all_dfs) > 1:
            header_lines = [
                f"# HMS Basin Parameters (combined)",
                f"# Source: {basin_path.name}",
                f"# Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Parameter types: {', '.join(all_dfs.keys())}",
            ]
            # Merge all into one wide DataFrame with param_type column
            combined_parts = []
            for ptype, df in all_dfs.items():
                df = df.copy()
                # Drop all-NA columns to avoid FutureWarning from pd.concat
                df = df.dropna(axis=1, how='all')
                df.insert(0, 'param_type', ptype)
                combined_parts.append(df)
            combined = pd.concat(combined_parts, ignore_index=True, sort=False)
            csv_text = combined.to_csv(index=False)
            output_csv.write_text(
                '\n'.join(header_lines) + '\n' + csv_text,
                encoding='utf-8'
            )
            written_files.insert(0, output_csv)

        elif len(all_dfs) == 1:
            # Single type — write directly to the requested path too
            import shutil
            shutil.copy2(written_files[0], output_csv)
            written_files.insert(0, output_csv)

        logger.info(f"Exported parameters to {output_csv}")
        return output_csv

    @staticmethod
    @log_call
    def import_parameters_csv(
        basin_path: Union[str, Path],
        input_csv: Union[str, Path],
        create_backup: bool = True,
        hms_object=None
    ) -> Dict:
        """
        Import basin parameters from a CSV file previously created by
        export_parameters_csv().

        The CSV should have a 'param_type' column ('loss', 'transform',
        'baseflow', 'routing') and a 'name' column. Comment rows starting
        with '#' are ignored.

        Args:
            basin_path: Path to the .basin file
            input_csv: Path to the input CSV file
            create_backup: Create .bak backup before writing (default True)
            hms_object: Optional HmsPrj instance

        Returns:
            Dict with results per param_type:
            {'loss': {summary}, 'transform': {summary}, ...}

        Example:
            >>> result = HmsBasin.import_parameters_csv("model.basin", "params.csv")
            >>> print(result['loss']['elements_modified'])
        """
        basin_path = Path(basin_path)
        input_csv = Path(input_csv)

        df = pd.read_csv(input_csv, comment='#')

        if 'param_type' not in df.columns:
            raise ValueError(
                "CSV must have 'param_type' column. "
                "Use export_parameters_csv() to generate the correct format."
            )

        if 'name' not in df.columns:
            raise ValueError("CSV must have 'name' column.")

        results = {}
        setter_map = {
            'loss': ('set_all_loss_parameters', LOSS_PARAM_REVERSE_MAP),
            'transform': ('set_all_transform_parameters', TRANSFORM_PARAM_REVERSE_MAP),
            'baseflow': ('set_all_baseflow_parameters', BASEFLOW_PARAM_REVERSE_MAP),
            'routing': ('set_all_routing_parameters', ROUTING_PARAM_REVERSE_MAP),
        }

        # Only create backup once
        backup_created = False

        for ptype, group_df in df.groupby('param_type'):
            if ptype not in setter_map:
                logger.warning(f"Unknown param_type '{ptype}' in CSV, skipping")
                continue

            setter_name, _ = setter_map[ptype]
            setter = getattr(HmsBasin, setter_name)

            # Drop the param_type column before passing to setter
            param_df = group_df.drop(columns=['param_type'])

            # Only create backup on first write
            should_backup = create_backup and not backup_created
            result = setter(basin_path, param_df, create_backup=should_backup, hms_object=hms_object)
            results[ptype] = result

            if should_backup and result.get('backup_path'):
                backup_created = True

        logger.info(f"Imported parameters from {input_csv}")
        return results

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _get_all_element_params(
        basin_path: Union[str, Path],
        element_type: str,
        param_map: Dict[str, str]
    ) -> pd.DataFrame:
        """
        Generic reader: get parameters for all elements of a type.

        Reads the file once, parses all blocks, maps HMS keys to snake_case
        columns using param_map.

        Args:
            basin_path: Path to the .basin file
            element_type: 'Subbasin' or 'Reach'
            param_map: Dict mapping HMS file keys to snake_case column names

        Returns:
            DataFrame with 'name' column plus parameter columns
        """
        basin_path = Path(basin_path)
        content = HmsFileParser.read_file(basin_path)
        elements = HmsFileParser.parse_blocks(content, element_type)

        records = []
        for name, attrs in elements.items():
            record = {'name': name}
            # Also include Area and Downstream for subbasins
            if element_type == "Subbasin":
                record['area'] = HmsFileParser.to_numeric(attrs.get('Area'))
            for hms_key, col_name in param_map.items():
                raw_val = attrs.get(hms_key)
                if raw_val is not None:
                    record[col_name] = HmsFileParser.to_numeric(raw_val)
                # Leave absent keys out — they become NaN in DataFrame
            records.append(record)

        df = pd.DataFrame(records)
        if not df.empty:
            # Ensure all param_map columns exist (NaN for missing)
            for col_name in param_map.values():
                if col_name not in df.columns:
                    df[col_name] = pd.NA
        logger.info(f"Read {len(df)} {element_type} parameter records from {basin_path.name}")
        return df

    @staticmethod
    def _set_all_element_params(
        basin_path: Union[str, Path],
        element_type: str,
        params_df: pd.DataFrame,
        reverse_map: Dict[str, str],
        create_backup: bool = True
    ) -> Dict:
        """
        Generic writer: set parameters for multiple elements from a DataFrame.

        Reads file once, finds all blocks with positions, iterates in reverse
        order (to preserve string offsets during replacement), updates non-NaN
        columns, writes file once.

        Args:
            basin_path: Path to the .basin file
            element_type: 'Subbasin' or 'Reach'
            params_df: DataFrame with 'name' column and parameter columns
            reverse_map: Dict mapping snake_case column names to HMS file keys
            create_backup: Create .bak backup before writing

        Returns:
            Summary dict with keys: elements_modified, parameters_changed,
            elements_not_found, warnings, backup_path
        """
        import shutil

        basin_path = Path(basin_path)
        content = HmsFileParser.read_file(basin_path)

        summary = {
            'elements_modified': 0,
            'parameters_changed': 0,
            'elements_not_found': [],
            'warnings': [],
            'backup_path': None,
        }

        if 'name' not in params_df.columns:
            raise ValueError("params_df must have a 'name' column")

        # Create backup
        if create_backup:
            backup_path = basin_path.with_suffix('.basin.bak')
            shutil.copy2(basin_path, backup_path)
            summary['backup_path'] = str(backup_path)
            logger.info(f"Created backup: {backup_path}")

        # Build lookup from DataFrame: name -> {col: value} (non-NaN only)
        df_lookup = {}
        for _, row in params_df.iterrows():
            name = row['name']
            updates = {}
            for col_name, hms_key in reverse_map.items():
                if col_name in row.index:
                    val = row[col_name]
                    if pd.notna(val):
                        updates[hms_key] = val
            if updates:
                df_lookup[name] = updates

        # Find all blocks with positions
        blocks = HmsFileParser.find_all_blocks(content, element_type)

        # Track which names from the DataFrame were found in the file
        found_names = set()

        # Iterate in reverse order to preserve offsets
        for match, name, attrs in reversed(blocks):
            if name not in df_lookup:
                continue

            found_names.add(name)
            updates = df_lookup[name]
            block_body = match.group(3)  # The content between header and End:
            element_modified = False

            for hms_key, new_value in updates.items():
                # Check if old value differs from new value
                old_raw = attrs.get(hms_key)
                if old_raw is not None:
                    old_numeric = HmsFileParser.to_numeric(old_raw)
                    try:
                        if float(old_numeric) == float(new_value):
                            continue  # Skip — value unchanged
                    except (ValueError, TypeError):
                        if str(new_value) == old_raw:
                            continue  # Skip — string value unchanged

                updated_body, changed = HmsFileParser.update_parameter(
                    block_body, hms_key, new_value
                )
                if changed:
                    block_body = updated_body
                    summary['parameters_changed'] += 1
                    element_modified = True
                elif old_raw is None:
                    # Parameter absent from file — warn caller
                    summary['warnings'].append(
                        f"Parameter '{hms_key}' not found in {element_type} '{name}', skipped"
                    )

            if element_modified:
                # Reconstruct the full block: header + body + End:
                header = match.group(1)
                footer = match.group(4)
                new_block = header + block_body + footer
                content = content[:match.start()] + new_block + content[match.end():]
                summary['elements_modified'] += 1

        # Check for names in DataFrame but not in file
        for name in df_lookup:
            if name not in found_names:
                summary['elements_not_found'].append(name)

        if summary['elements_not_found']:
            summary['warnings'].append(
                f"{len(summary['elements_not_found'])} elements not found in file: "
                f"{summary['elements_not_found'][:5]}"
            )

        # Write modified content
        HmsFileParser.write_file(basin_path, content)
        logger.info(
            f"Updated {summary['elements_modified']} {element_type}s, "
            f"{summary['parameters_changed']} parameters changed"
        )

        return summary

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

    @staticmethod
    @log_call
    def import_modified_puls_table(
        basin_path: Union[str, Path],
        reach_name: str,
        storage_discharge_data: pd.DataFrame,
        table_name: Optional[str] = None,
        hms_object=None
    ) -> Path:
        """
        Create an HMS storage-discharge table file and assign it to a reach.

        Creates an HMS-format .tbl file with storage-discharge pairs for
        Modified Puls routing, and updates the reach's routing parameters
        in the .basin file.

        Parameters
        ----------
        basin_path : str or Path
            Path to the .basin file
        reach_name : str
            Name of the reach to assign the table to
        storage_discharge_data : pd.DataFrame
            DataFrame with columns:
            - storage_acft: Storage values in acre-feet
            - outflow_cfs: Outflow/discharge values in cfs
        table_name : str, optional
            Name for the table. If None, auto-generated from reach name.
        hms_object : optional
            Optional HmsPrj instance

        Returns
        -------
        Path
            Path to the created .tbl file

        Raises
        ------
        ValueError
            If data has < 2 rows or values are not monotonically increasing

        Example
        -------
        >>> import pandas as pd
        >>> from hms_commander import HmsBasin
        >>> sd_data = pd.DataFrame({
        ...     'storage_acft': [0, 100, 500, 1000, 2000, 5000],
        ...     'outflow_cfs': [0, 50, 200, 500, 1200, 3500]
        ... })
        >>> tbl_path = HmsBasin.import_modified_puls_table(
        ...     "model.basin", "Reach-1", sd_data
        ... )
        >>> print(f"Table created: {tbl_path}")

        Notes
        -----
        The .tbl file is created in the same directory as the .basin file.
        The reach's 'Storage Outflow Table Name' parameter is updated in
        the .basin file to reference the new table.
        """
        basin_path = Path(basin_path)
        if not basin_path.exists():
            raise FileNotFoundError(f"Basin file not found: {basin_path}")

        # Validate input data
        if 'storage_acft' not in storage_discharge_data.columns:
            raise ValueError("DataFrame must have 'storage_acft' column")
        if 'outflow_cfs' not in storage_discharge_data.columns:
            raise ValueError("DataFrame must have 'outflow_cfs' column")

        if len(storage_discharge_data) < 2:
            raise ValueError("Storage-discharge table must have at least 2 rows")

        storage = storage_discharge_data['storage_acft'].values
        outflow = storage_discharge_data['outflow_cfs'].values

        # Validate monotonically increasing
        if not all(storage[i] <= storage[i + 1] for i in range(len(storage) - 1)):
            raise ValueError("Storage values must be monotonically increasing")
        if not all(outflow[i] <= outflow[i + 1] for i in range(len(outflow) - 1)):
            raise ValueError("Outflow values must be monotonically increasing")

        # Verify reach exists
        reaches = HmsBasin.get_reaches(basin_path, hms_object=hms_object)
        if reaches.empty or reach_name not in reaches['name'].values:
            raise ValueError(f"Reach '{reach_name}' not found in {basin_path.name}")

        # Generate table name
        if table_name is None:
            table_name = f"{reach_name} SD"

        # Create .tbl file in HMS format
        tbl_dir = basin_path.parent
        tbl_filename = f"{table_name}.tbl"
        tbl_path = tbl_dir / tbl_filename

        # Build HMS table content
        lines = []
        lines.append(f"Table: {table_name}")
        lines.append(f"  Number of Rows: {len(storage_discharge_data)}")
        for i in range(len(storage_discharge_data)):
            lines.append(f"  Storage-Outflow: {storage[i]:.2f}, {outflow[i]:.2f}")
        lines.append("End:")
        lines.append("")

        tbl_content = "\n".join(lines)
        HmsFileParser.write_file(tbl_path, tbl_content)
        logger.info(f"Created storage-discharge table: {tbl_path.name} ({len(storage_discharge_data)} rows)")

        # Update basin file to reference the table
        content = HmsBasin._read_basin_file(basin_path)

        # Find the reach block and update Storage Outflow Table Name
        reach_blocks = HmsFileParser.find_all_blocks(content, "Reach")
        updated = False

        for match, name, attrs in reach_blocks:
            if name == reach_name:
                block_body = match.group(3)
                # Check if parameter already exists
                param_line = f"     Storage Outflow Table Name: {table_name}"
                new_block, changed = HmsFileParser.update_parameter(
                    block_body, "Storage Outflow Table Name", table_name
                )

                if changed:
                    content = content[:match.start(3)] + new_block + content[match.end(3):]
                else:
                    # Insert parameter before End:
                    insert_content = block_body.rstrip() + f"\n{param_line}\n"
                    content = content[:match.start(3)] + insert_content + content[match.end(3):]

                updated = True
                break

        if updated:
            HmsFileParser.write_file(basin_path, content)
            logger.info(f"Updated reach '{reach_name}' with table reference: {table_name}")
        else:
            logger.warning(f"Could not update reach '{reach_name}' in basin file")

        return tbl_path

    @staticmethod
    @log_call
    def get_modified_puls_table(
        basin_path: Union[str, Path],
        reach_name: str,
        hms_object=None
    ) -> Optional[pd.DataFrame]:
        """
        Read a Modified Puls storage-discharge table for a reach.

        Looks up the table reference in the basin file, then reads and parses
        the .tbl file.

        Parameters
        ----------
        basin_path : str or Path
            Path to the .basin file
        reach_name : str
            Name of the reach to read table for
        hms_object : optional
            Optional HmsPrj instance

        Returns
        -------
        pd.DataFrame or None
            DataFrame with columns 'storage_acft' and 'outflow_cfs',
            or None if no table is assigned.

        Example
        -------
        >>> table = HmsBasin.get_modified_puls_table("model.basin", "Reach-1")
        >>> if table is not None:
        ...     print(table)
        """
        basin_path = Path(basin_path)
        content = HmsBasin._read_basin_file(basin_path)

        # Find reach block and get table name
        reach_blocks = HmsFileParser.find_all_blocks(content, "Reach")
        table_name = None

        for match, name, attrs in reach_blocks:
            if name == reach_name:
                table_name = attrs.get('Storage Outflow Table Name')
                break

        if table_name is None:
            logger.info(f"No storage outflow table assigned to reach '{reach_name}'")
            return None

        # Find and read the .tbl file
        tbl_path = basin_path.parent / f"{table_name}.tbl"
        if not tbl_path.exists():
            # Try without extension suffix variations
            possible_paths = list(basin_path.parent.glob(f"*{table_name}*.tbl"))
            if possible_paths:
                tbl_path = possible_paths[0]
            else:
                logger.warning(f"Table file not found: {tbl_path}")
                return None

        # Parse table file
        tbl_content = HmsFileParser.read_file(tbl_path)
        storage_values = []
        outflow_values = []

        for line in tbl_content.splitlines():
            line = line.strip()
            if line.startswith('Storage-Outflow:'):
                values_str = line.replace('Storage-Outflow:', '').strip()
                parts = [v.strip() for v in values_str.split(',')]
                if len(parts) >= 2:
                    try:
                        storage_values.append(float(parts[0]))
                        outflow_values.append(float(parts[1]))
                    except ValueError:
                        continue

        if not storage_values:
            logger.warning(f"No storage-outflow data found in {tbl_path.name}")
            return None

        df = pd.DataFrame({
            'storage_acft': storage_values,
            'outflow_cfs': outflow_values
        })
        logger.info(f"Read {len(df)} storage-outflow pairs from {tbl_path.name}")
        return df
