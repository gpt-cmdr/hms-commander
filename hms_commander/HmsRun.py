"""
HmsRun - HMS Run File Operations

This module provides static methods for working with HMS run files (.run),
with a focus on DSS output management for HEC-RAS integration workflows.

The primary use case is enabling HEC-RAS modelers to:
1. Configure HMS output DSS files that RAS will consume as boundary conditions
2. Query run configurations and DSS output paths
3. Clone and modify runs for sensitivity analysis

Classes:
    HmsRun: Static methods for run file operations and DSS output management

Example:
    >>> from hms_commander import init_hms_project, hms
    >>> from hms_commander import HmsRun
    >>>
    >>> init_hms_project(r"C:\\HMS_Projects\\MyProject")
    >>>
    >>> # Get DSS output configuration for a run
    >>> config = HmsRun.get_dss_config("Current", hms_object=hms)
    >>> print(f"Output DSS: {config['dss_file']}")
    >>>
    >>> # Set a new output DSS file
    >>> HmsRun.set_output_dss("Current", "HMS_Output.dss", hms_object=hms)
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from .LoggingConfig import log_call, get_logger

logger = get_logger(__name__)


class HmsRun:
    """
    Static class for HMS run file operations.

    Provides methods to read, modify, and manage HMS run configurations,
    with a focus on DSS output file management for RAS integration.

    All methods are static and operate on run files directly or via
    an HmsPrj object for path resolution.
    """

    @staticmethod
    @log_call
    def get_dss_config(
        run_name: str,
        hms_object: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Get DSS output configuration for a specific run.

        Retrieves the DSS file configuration and related output settings
        for a named run. This is essential for setting up RAS boundary
        conditions that reference HMS output DSS files.

        Args:
            run_name: Name of the run (e.g., "Current", "Future")
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            Dictionary containing DSS configuration:
            - dss_file: Name of output DSS file
            - dss_path: Full path to DSS file (if resolvable)
            - log_file: Name of log file
            - time_series_output: Output saving mode
            - basin_model: Associated basin model name
            - met_model: Associated meteorologic model name
            - control_spec: Associated control specification name
            - run_file: Path to the .run file containing this run

        Raises:
            ValueError: If run_name is not found
            RuntimeError: If HMS project not initialized

        Example:
            >>> config = HmsRun.get_dss_config("Current", hms_object=hms)
            >>> print(f"DSS file: {config['dss_file']}")
            >>> print(f"Full path: {config['dss_path']}")
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # Look up run in run_df
        if hms_obj.run_df.empty:
            raise RuntimeError("No runs found in HMS project")

        matches = hms_obj.run_df[hms_obj.run_df['name'] == run_name]
        if matches.empty:
            available = hms_obj.run_df['name'].tolist()
            raise ValueError(
                f"Run '{run_name}' not found. Available runs: {available}"
            )

        run_info = matches.iloc[0].to_dict()

        # Build DSS configuration dictionary
        dss_file = run_info.get('dss_file', '')

        # Resolve full DSS path if possible
        dss_path = None
        if dss_file and hms_obj.project_folder:
            potential_path = hms_obj.project_folder / dss_file
            if potential_path.exists():
                dss_path = potential_path
            else:
                # DSS might not exist yet (before first run)
                dss_path = potential_path

        config = {
            'dss_file': dss_file,
            'dss_path': dss_path,
            'log_file': run_info.get('log_file', ''),
            'time_series_output': run_info.get('time_series_output', ''),
            'basin_model': run_info.get('basin_model', ''),
            'met_model': run_info.get('met_model', ''),
            'control_spec': run_info.get('control_spec', ''),
            'run_file': run_info.get('full_path', ''),
            'description': run_info.get('description', ''),
        }

        logger.info(f"Retrieved DSS config for run '{run_name}': {dss_file}")
        return config

    @staticmethod
    @log_call
    def set_dss_file(
        run_name: str,
        dss_file: str,
        hms_object: Optional[Any] = None,
        update_log_file: bool = True
    ) -> bool:
        """
        Set the DSS output file for a run.

        Modifies the run file to specify a new DSS output file. This is
        critical for RAS workflows where specific DSS file names are
        expected as boundary condition sources.

        Args:
            run_name: Name of the run to modify (e.g., "Current")
            dss_file: New DSS file name (e.g., "HMS_Output.dss")
            hms_object: Optional HmsPrj instance. If None, uses global hms.
            update_log_file: If True, also updates log file name to match

        Returns:
            True if successful

        Raises:
            ValueError: If run_name is not found
            FileNotFoundError: If run file doesn't exist
            PermissionError: If run file cannot be written

        Example:
            >>> # Set output DSS for RAS consumption
            >>> HmsRun.set_dss_file(
            ...     run_name="Current",
            ...     dss_file="HMS_Output.dss",
            ...     hms_object=hms
            ... )
            >>>
            >>> # Verify the change
            >>> config = HmsRun.get_dss_config("Current", hms_object=hms)
            >>> print(f"New DSS: {config['dss_file']}")  # HMS_Output.dss
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # Get run info to find file
        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        # Pattern matches from "Run: {run_name}" to "End:"
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_dss_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace DSS File line
            dss_pattern = r'(\s+DSS File:\s*)([^\n]*)'
            if re.search(dss_pattern, body):
                body = re.sub(dss_pattern, rf'\g<1>{dss_file}', body)
            else:
                # Add DSS File line if not present
                body = body.rstrip() + f'\n     DSS File: {dss_file}\n'

            # Optionally update log file to match
            if update_log_file:
                log_name = Path(dss_file).stem + '.log'
                log_pattern = r'(\s+Log File:\s*)([^\n]*)'
                if re.search(log_pattern, body):
                    body = re.sub(log_pattern, rf'\g<1>{log_name}', body)

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_dss_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run block for '{run_name}'")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated DSS output for run '{run_name}' to '{dss_file}'")

            # Refresh the project to update run_df
            if hasattr(hms_obj, '_build_run_dataframe'):
                hms_obj._build_run_dataframe()

            return True
        else:
            logger.info(f"DSS file already set to '{dss_file}' for run '{run_name}'")
            return True

    @staticmethod
    @log_call
    def set_output_dss(
        run_name: str,
        dss_file: str,
        hms_object: Optional[Any] = None,
        update_log_file: bool = True
    ) -> bool:
        """
        DEPRECATED: Use set_dss_file() instead.

        Set the output DSS file for a run.

        This method is deprecated and maintained for backwards compatibility.
        Use HmsRun.set_dss_file() for new code.

        Args:
            run_name: Name of the run to modify (e.g., "Current")
            dss_file: New DSS file name (e.g., "HMS_Output.dss")
            hms_object: Optional HmsPrj instance. If None, uses global hms.
            update_log_file: If True, also updates log file name to match

        Returns:
            True if successful

        Example:
            >>> # DEPRECATED - use set_dss_file() instead
            >>> HmsRun.set_output_dss("Current", "HMS_Output.dss", hms_object=hms)
        """
        import warnings
        warnings.warn(
            "set_output_dss() is deprecated, use set_dss_file() instead",
            DeprecationWarning,
            stacklevel=2
        )
        return HmsRun.set_dss_file(run_name, dss_file, hms_object, update_log_file)

    @staticmethod
    @log_call
    def list_all_outputs(
        hms_object: Optional[Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        List all DSS outputs for all runs in the project.

        Returns a dictionary mapping run names to their DSS output
        configurations. Useful for verifying all outputs are properly
        configured before batch execution for RAS.

        Args:
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            Dictionary mapping run names to output configurations:
            {
                "Run1": {"dss_file": "Run1.dss", "dss_path": Path(...), ...},
                "Run2": {"dss_file": "Run2.dss", "dss_path": Path(...), ...},
            }

        Example:
            >>> outputs = HmsRun.list_all_outputs(hms_object=hms)
            >>> for run_name, config in outputs.items():
            ...     print(f"{run_name}: {config['dss_file']}")
            Current: Current.dss
            Future: Future.dss
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        outputs = {}
        run_names = hms_obj.list_run_names()

        for run_name in run_names:
            try:
                config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
                outputs[run_name] = config
            except Exception as e:
                logger.warning(f"Could not get config for run '{run_name}': {e}")
                outputs[run_name] = {'error': str(e)}

        logger.info(f"Listed outputs for {len(outputs)} runs")
        return outputs

    @staticmethod
    @log_call
    def get_run_names(hms_object: Optional[Any] = None) -> List[str]:
        """
        Get list of all run names in the project.

        Args:
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            List of run names

        Example:
            >>> runs = HmsRun.get_run_names(hms_object=hms)
            >>> print(runs)  # ['Current', 'Future']
        """
        hms_obj = HmsRun._get_hms_object(hms_object)
        return hms_obj.list_run_names()

    @staticmethod
    @log_call
    def verify_dss_outputs(
        hms_object: Optional[Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verify DSS output files exist for all runs.

        Checks each run's DSS output configuration and verifies the
        DSS file exists. Useful before setting up RAS boundary conditions.

        Args:
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            Dictionary with verification results:
            {
                "Run1": {"dss_file": "Run1.dss", "exists": True, "path": Path(...)},
                "Run2": {"dss_file": "Run2.dss", "exists": False, "path": None},
            }

        Example:
            >>> results = HmsRun.verify_dss_outputs(hms_object=hms)
            >>> for run, info in results.items():
            ...     status = "✓" if info['exists'] else "✗"
            ...     print(f"{status} {run}: {info['dss_file']}")
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        results = {}
        outputs = HmsRun.list_all_outputs(hms_object=hms_obj)

        for run_name, config in outputs.items():
            if 'error' in config:
                results[run_name] = {
                    'dss_file': None,
                    'exists': False,
                    'path': None,
                    'error': config['error']
                }
                continue

            dss_path = config.get('dss_path')
            exists = dss_path is not None and dss_path.exists()

            results[run_name] = {
                'dss_file': config.get('dss_file', ''),
                'exists': exists,
                'path': dss_path if exists else None
            }

        # Log summary
        existing = sum(1 for r in results.values() if r['exists'])
        total = len(results)
        logger.info(f"DSS output verification: {existing}/{total} files exist")

        return results

    @staticmethod
    @log_call
    def clone_run(
        source_run: str,
        new_run_name: str,
        new_basin: str = None,
        new_met: str = None,
        new_control: str = None,
        output_dss: str = None,
        description: str = None,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Clone an existing run with a new name and optional configuration changes.

        Follows the CLB Engineering LLM Forward Approach:
        - Non-destructive: Creates new run, preserves original
        - Traceable: Updates description with clone metadata
        - GUI-verifiable: New run appears in HEC-HMS GUI
        - Separate outputs: Uses new DSS file for comparison

        This is critical for QAQC workflows where engineers need to compare
        baseline vs. updated runs side-by-side in the GUI.

        Args:
            source_run: Name of run to clone (e.g., "100yr Storm - TP40")
            new_run_name: Name for the new run (e.g., "100yr Storm - Atlas14")
            new_basin: Optional basin model name (if None, uses same as source)
            new_met: Optional met model name (if None, uses same as source)
            new_control: Optional control spec name (if None, uses same as source)
            output_dss: Optional DSS output file name (defaults to "{new_run_name}.dss")
            description: Optional description (defaults to "Cloned from {source}")
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If source_run not found or new_run_name already exists

        Example:
            >>> # Clone run for Atlas 14 comparison
            >>> HmsRun.clone_run(
            ...     source_run="100yr Storm - TP40",
            ...     new_run_name="100yr Storm - Atlas14",
            ...     new_basin="Tifton_Atlas14",
            ...     new_met="Design_Storms_Atlas14",
            ...     output_dss="results_atlas14.dss",
            ...     description="Atlas 14 precipitation update",
            ...     hms_object=hms
            ... )
            >>> # Engineer can now compare both runs in GUI
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # Validate source exists
        config = HmsRun.get_dss_config(source_run, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])

        # Check new name doesn't exist
        existing_runs = HmsRun.get_run_names(hms_object=hms_obj)
        if new_run_name in existing_runs:
            raise ValueError(f"Run '{new_run_name}' already exists")

        # Defaults
        if output_dss is None:
            output_dss = f"{new_run_name}.dss"
        if description is None:
            description = f"Cloned from {source_run}"
        if new_basin is None:
            new_basin = config.get('basin_model', '')
        if new_met is None:
            new_met = config.get('met_model', '')
        if new_control is None:
            new_control = config.get('control_spec', '')

        # Read run file
        content = HmsRun._read_file(run_file_path)

        # Extract the source run block
        escaped_name = re.escape(source_run)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n.*?End:)'
        match = re.search(block_pattern, content, re.DOTALL)

        if not match:
            raise ValueError(f"Could not find run block for '{source_run}'")

        source_block = match.group(1)

        # Create new block with modifications
        new_block = source_block

        # Update run name
        new_block = re.sub(
            rf'Run:\s*{escaped_name}',
            f'Run: {new_run_name}',
            new_block
        )

        # Update basin
        new_block = re.sub(
            r'(\s+Basin:\s*)([^\n]*)',
            rf'\g<1>{new_basin}',
            new_block
        )

        # Update met (handles both "Precip:" and "Meteorology:" variants)
        new_block = re.sub(
            r'(\s+(?:Precip|Meteorology):\s*)([^\n]*)',
            rf'\g<1>{new_met}',
            new_block
        )

        # Update control
        new_block = re.sub(
            r'(\s+Control:\s*)([^\n]*)',
            rf'\g<1>{new_control}',
            new_block
        )

        # Update DSS file
        if re.search(r'\s+DSS File:', new_block):
            new_block = re.sub(
                r'(\s+DSS File:\s*)([^\n]*)',
                rf'\g<1>{output_dss}',
                new_block
            )
        else:
            # Add DSS File line before End:
            new_block = re.sub(
                r'(End:)',
                rf'     DSS File: {output_dss}\n\1',
                new_block
            )

        # Update log file
        log_name = Path(output_dss).stem + '.log'
        if re.search(r'\s+Log File:', new_block):
            new_block = re.sub(
                r'(\s+Log File:\s*)([^\n]*)',
                rf'\g<1>{log_name}',
                new_block
            )
        else:
            # Add Log File line before End:
            new_block = re.sub(
                r'(End:)',
                rf'     Log File: {log_name}\n\1',
                new_block
            )

        # Update description
        if re.search(r'\s+Description:', new_block):
            new_block = re.sub(
                r'(\s+Description:\s*)([^\n]*)',
                rf'\g<1>{description}',
                new_block
            )
        else:
            # Add Description line after Run: name
            new_block = re.sub(
                rf'(Run:\s*{re.escape(new_run_name)}\s*\n)',
                rf'\1     Description: {description}\n',
                new_block
            )

        # Append new block to file
        new_content = content.rstrip() + '\n\n' + new_block + '\n'

        HmsRun._write_file(run_file_path, new_content)
        logger.info(f"Cloned run: {source_run} → {new_run_name}")
        logger.info(f"  Basin: {new_basin}, Met: {new_met}, DSS: {output_dss}")

        # Refresh project
        if hasattr(hms_obj, '_build_run_dataframe'):
            hms_obj._build_run_dataframe()
            logger.info(f"Re-initialized project to register new run '{new_run_name}'")

        return True

    @staticmethod
    @log_call
    def set_dss_file_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        dss_file: str,
        update_log_file: bool = True
    ) -> bool:
        """
        Set the DSS output file for a run directly in the run file.

        This is a standalone method that doesn't require project initialization.
        It directly modifies the run file to set a new DSS output path.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run to modify (e.g., "Run 1")
            dss_file: New DSS file name (e.g., "output.dss")
            update_log_file: If True, also updates log file name to match

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> # Direct file modification without project init
            >>> HmsRun.set_dss_file_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "custom_output.dss"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_dss_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace DSS File line
            dss_pattern = r'(\s+DSS File:\s*)([^\n]*)'
            if re.search(dss_pattern, body):
                body = re.sub(dss_pattern, rf'\g<1>{dss_file}', body)
            else:
                # Add DSS File line if not present (after Log File if exists)
                log_match = re.search(r'(\s+Log File:[^\n]*\n)', body)
                if log_match:
                    insert_pos = log_match.end()
                    body = body[:insert_pos] + f'     DSS File: {dss_file}\n' + body[insert_pos:]
                else:
                    # Add after header
                    body = f'     DSS File: {dss_file}\n' + body

            # Optionally update log file to match
            if update_log_file:
                log_name = Path(dss_file).stem + '.log'
                log_pattern = r'(\s+Log File:\s*)([^\n]*)'
                if re.search(log_pattern, body):
                    body = re.sub(log_pattern, rf'\g<1>{log_name}', body)

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_dss_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated DSS output for run '{run_name}' to '{dss_file}' in {run_file_path}")
        else:
            logger.info(f"DSS file already set to '{dss_file}' for run '{run_name}'")

        return True

    @staticmethod
    @log_call
    def get_dss_file_direct(
        run_file_path: Union[str, Path],
        run_name: str
    ) -> Optional[str]:
        """
        Get the DSS output file for a run directly from the run file.

        This is a standalone method that doesn't require project initialization.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")

        Returns:
            DSS file name or None if not found

        Example:
            >>> dss = HmsRun.get_dss_file_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1"
            ... )
            >>> print(dss)  # "output.dss"
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        content = HmsRun._read_file(run_file_path)

        # Find the run block
        escaped_name = re.escape(run_name)
        block_pattern = rf'Run:\s*{escaped_name}\s*\n(.*?)End:'
        match = re.search(block_pattern, content, re.DOTALL)

        if not match:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        body = match.group(1)

        # Extract DSS File line
        dss_match = re.search(r'DSS File:\s*([^\n]+)', body)
        if dss_match:
            return dss_match.group(1).strip()

        return None

    @staticmethod
    @log_call
    def list_runs_direct(
        run_file_path: Union[str, Path]
    ) -> List[Dict[str, str]]:
        """
        List all runs in a run file directly without project initialization.

        Args:
            run_file_path: Path to the .run file

        Returns:
            List of dictionaries with run info:
            [
                {"name": "Run 1", "dss_file": "output.dss", "basin": "Basin1", ...},
                ...
            ]

        Example:
            >>> runs = HmsRun.list_runs_direct("C:/Projects/MyProject/project.run")
            >>> for run in runs:
            ...     print(f"{run['name']}: {run['dss_file']}")
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        content = HmsRun._read_file(run_file_path)

        # Find all run blocks
        runs = []
        block_pattern = r'Run:\s*([^\n]+)\n(.*?)End:'

        for match in re.finditer(block_pattern, content, re.DOTALL):
            run_name = match.group(1).strip()
            body = match.group(2)

            run_info = {'name': run_name}

            # Extract common fields
            field_patterns = {
                'description': r'Description:\s*([^\n]*)',
                'log_file': r'Log File:\s*([^\n]+)',
                'dss_file': r'DSS File:\s*([^\n]+)',
                'basin': r'Basin:\s*([^\n]+)',
                'precip': r'Precip:\s*([^\n]+)',
                'control': r'Control:\s*([^\n]+)',
            }

            for field, pattern in field_patterns.items():
                field_match = re.search(pattern, body)
                if field_match:
                    run_info[field] = field_match.group(1).strip()

            runs.append(run_info)

        logger.info(f"Found {len(runs)} runs in {run_file_path}")
        return runs

    @staticmethod
    @log_call
    def set_description(
        run_name: str,
        description: str,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Set the description for a run.

        Args:
            run_name: Name of the run (e.g., "Current")
            description: New description text
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If run_name is not found
            FileNotFoundError: If run file doesn't exist

        Example:
            >>> HmsRun.set_description(
            ...     run_name="Current",
            ...     description="Updated baseline scenario",
            ...     hms_object=hms
            ... )
            True
        """
        hms_obj = HmsRun._get_hms_object(hms_object)
        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])
        return HmsRun.set_description_direct(run_file_path, run_name, description)

    @staticmethod
    @log_call
    def set_description_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        description: str
    ) -> bool:
        """
        Set the description for a run directly in the run file.

        This is a standalone method that doesn't require project initialization.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")
            description: New description text

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> HmsRun.set_description_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "Updated description"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_description_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace Description line
            desc_pattern = r'(\s+Description:\s*)([^\n]*)'
            if re.search(desc_pattern, body):
                body = re.sub(desc_pattern, rf'\g<1>{description}', body)
            else:
                # Add Description line after run name (at beginning of body)
                body = f'     Description: {description}\n' + body

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_description_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated description for run '{run_name}' in {run_file_path}")
        else:
            logger.info(f"Description already set to '{description}' for run '{run_name}'")

        return True

    @staticmethod
    @log_call
    def set_log_file(
        run_name: str,
        log_file: str,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Set the log file for a run.

        Args:
            run_name: Name of the run (e.g., "Current")
            log_file: New log file name (e.g., "run1.log")
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If run_name is not found
            FileNotFoundError: If run file doesn't exist

        Example:
            >>> HmsRun.set_log_file(
            ...     run_name="Current",
            ...     log_file="current_run.log",
            ...     hms_object=hms
            ... )
            True
        """
        hms_obj = HmsRun._get_hms_object(hms_object)
        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])
        return HmsRun.set_log_file_direct(run_file_path, run_name, log_file)

    @staticmethod
    @log_call
    def set_log_file_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        log_file: str
    ) -> bool:
        """
        Set the log file for a run directly in the run file.

        This is a standalone method that doesn't require project initialization.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")
            log_file: New log file name (e.g., "run1.log")

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> HmsRun.set_log_file_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "custom.log"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_log_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace Log File line
            log_pattern = r'(\s+Log File:\s*)([^\n]*)'
            if re.search(log_pattern, body):
                body = re.sub(log_pattern, rf'\g<1>{log_file}', body)
            else:
                # Add Log File line (after Description if exists, otherwise at beginning)
                desc_match = re.search(r'(\s+Description:[^\n]*\n)', body)
                if desc_match:
                    insert_pos = desc_match.end()
                    body = body[:insert_pos] + f'     Log File: {log_file}\n' + body[insert_pos:]
                else:
                    body = f'     Log File: {log_file}\n' + body

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_log_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated log file for run '{run_name}' to '{log_file}' in {run_file_path}")
        else:
            logger.info(f"Log file already set to '{log_file}' for run '{run_name}'")

        return True

    @staticmethod
    @log_call
    def set_basin(
        run_name: str,
        basin_model: str,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Set the basin model for a run.

        ⚠️ CRITICAL: HMS will delete runs with invalid basin references on project open.
        This method validates that the basin model exists before setting it.

        Args:
            run_name: Name of the run (e.g., "Current")
            basin_model: Name of basin model (must exist in project)
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If basin model doesn't exist in project or run not found
            FileNotFoundError: If run file doesn't exist

        Example:
            >>> # Validate before setting
            >>> HmsRun.set_basin(
            ...     run_name="Current",
            ...     basin_model="Updated_Basin",
            ...     hms_object=hms
            ... )
            True
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # CRITICAL: Validate basin exists
        basin_names = hms_obj.list_basin_names()
        if basin_model not in basin_names:
            raise ValueError(
                f"Basin '{basin_model}' not found in project. "
                f"Available basins: {basin_names}. "
                f"HMS will delete runs with invalid basin references on project open!"
            )

        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])

        success = HmsRun.set_basin_direct(run_file_path, run_name, basin_model)

        # Refresh project to update run_df
        if success and hasattr(hms_obj, '_build_run_dataframe'):
            hms_obj._build_run_dataframe()

        return success

    @staticmethod
    @log_call
    def set_basin_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        basin_model: str
    ) -> bool:
        """
        Set the basin model for a run directly in the run file.

        ⚠️ WARNING: This method does NOT validate basin existence.
        Use set_basin() with hms_object for validation to prevent HMS from
        deleting the run on project open.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")
            basin_model: Name of basin model

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> HmsRun.set_basin_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "Basin_Model_Name"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_basin_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace Basin line
            basin_pattern = r'(\s+Basin:\s*)([^\n]*)'
            if re.search(basin_pattern, body):
                body = re.sub(basin_pattern, rf'\g<1>{basin_model}', body)
            else:
                # Add Basin line (after Log File if exists, otherwise after Description)
                log_match = re.search(r'(\s+Log File:[^\n]*\n)', body)
                if log_match:
                    insert_pos = log_match.end()
                    body = body[:insert_pos] + f'     Basin: {basin_model}\n' + body[insert_pos:]
                else:
                    desc_match = re.search(r'(\s+Description:[^\n]*\n)', body)
                    if desc_match:
                        insert_pos = desc_match.end()
                        body = body[:insert_pos] + f'     Basin: {basin_model}\n' + body[insert_pos:]
                    else:
                        body = f'     Basin: {basin_model}\n' + body

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_basin_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated basin for run '{run_name}' to '{basin_model}' in {run_file_path}")
        else:
            logger.info(f"Basin already set to '{basin_model}' for run '{run_name}'")

        return True

    @staticmethod
    @log_call
    def set_precip(
        run_name: str,
        met_model: str,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Set the meteorologic model for a run.

        ⚠️ CRITICAL: HMS will delete runs with invalid met references on project open.
        This method validates that the met model exists before setting it.

        Args:
            run_name: Name of the run (e.g., "Current")
            met_model: Name of meteorologic model (must exist in project)
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If met model doesn't exist in project or run not found
            FileNotFoundError: If run file doesn't exist

        Example:
            >>> # Validate before setting
            >>> HmsRun.set_precip(
            ...     run_name="Current",
            ...     met_model="Atlas14_Met",
            ...     hms_object=hms
            ... )
            True
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # CRITICAL: Validate met exists
        met_names = hms_obj.list_met_names()
        if met_model not in met_names:
            raise ValueError(
                f"Met model '{met_model}' not found in project. "
                f"Available met models: {met_names}. "
                f"HMS will delete runs with invalid met references on project open!"
            )

        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])

        success = HmsRun.set_precip_direct(run_file_path, run_name, met_model)

        # Refresh project to update run_df
        if success and hasattr(hms_obj, '_build_run_dataframe'):
            hms_obj._build_run_dataframe()

        return success

    @staticmethod
    @log_call
    def set_precip_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        met_model: str
    ) -> bool:
        """
        Set the meteorologic model for a run directly in the run file.

        ⚠️ WARNING: This method does NOT validate met model existence.
        Use set_precip() with hms_object for validation to prevent HMS from
        deleting the run on project open.

        Note: Handles both "Precip:" (HMS 3.x) and "Meteorology:" (HMS 4.x) variants.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")
            met_model: Name of meteorologic model

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> HmsRun.set_precip_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "Met_Model_Name"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_precip_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace Precip or Meteorology line (handle both variants)
            precip_pattern = r'(\s+(?:Precip|Meteorology):\s*)([^\n]*)'
            if re.search(precip_pattern, body):
                body = re.sub(precip_pattern, rf'\g<1>{met_model}', body)
            else:
                # Add Precip line (after Basin if exists)
                basin_match = re.search(r'(\s+Basin:[^\n]*\n)', body)
                if basin_match:
                    insert_pos = basin_match.end()
                    body = body[:insert_pos] + f'     Precip: {met_model}\n' + body[insert_pos:]
                else:
                    # After Log File
                    log_match = re.search(r'(\s+Log File:[^\n]*\n)', body)
                    if log_match:
                        insert_pos = log_match.end()
                        body = body[:insert_pos] + f'     Precip: {met_model}\n' + body[insert_pos:]
                    else:
                        body = f'     Precip: {met_model}\n' + body

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_precip_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated met model for run '{run_name}' to '{met_model}' in {run_file_path}")
        else:
            logger.info(f"Met model already set to '{met_model}' for run '{run_name}'")

        return True

    @staticmethod
    @log_call
    def set_control(
        run_name: str,
        control_spec: str,
        hms_object: Optional[Any] = None
    ) -> bool:
        """
        Set the control specification for a run.

        ⚠️ CRITICAL: HMS will delete runs with invalid control references on project open.
        This method validates that the control spec exists before setting it.

        Args:
            run_name: Name of the run (e.g., "Current")
            control_spec: Name of control specification (must exist in project)
            hms_object: Optional HmsPrj instance. If None, uses global hms.

        Returns:
            True if successful

        Raises:
            ValueError: If control spec doesn't exist in project or run not found
            FileNotFoundError: If run file doesn't exist

        Example:
            >>> # Validate before setting
            >>> HmsRun.set_control(
            ...     run_name="Current",
            ...     control_spec="24hr_Storm",
            ...     hms_object=hms
            ... )
            True
        """
        hms_obj = HmsRun._get_hms_object(hms_object)

        # CRITICAL: Validate control exists
        control_names = hms_obj.list_control_names()
        if control_spec not in control_names:
            raise ValueError(
                f"Control spec '{control_spec}' not found in project. "
                f"Available control specs: {control_names}. "
                f"HMS will delete runs with invalid control references on project open!"
            )

        config = HmsRun.get_dss_config(run_name, hms_object=hms_obj)
        run_file_path = Path(config['run_file'])

        success = HmsRun.set_control_direct(run_file_path, run_name, control_spec)

        # Refresh project to update run_df
        if success and hasattr(hms_obj, '_build_run_dataframe'):
            hms_obj._build_run_dataframe()

        return success

    @staticmethod
    @log_call
    def set_control_direct(
        run_file_path: Union[str, Path],
        run_name: str,
        control_spec: str
    ) -> bool:
        """
        Set the control specification for a run directly in the run file.

        ⚠️ WARNING: This method does NOT validate control spec existence.
        Use set_control() with hms_object for validation to prevent HMS from
        deleting the run on project open.

        Args:
            run_file_path: Path to the .run file
            run_name: Name of the run (e.g., "Run 1")
            control_spec: Name of control specification

        Returns:
            True if successful

        Raises:
            FileNotFoundError: If run file doesn't exist
            ValueError: If run_name not found in the file

        Example:
            >>> HmsRun.set_control_direct(
            ...     "C:/Projects/MyProject/project.run",
            ...     "Run 1",
            ...     "Control_Spec_Name"
            ... )
            True
        """
        run_file_path = Path(run_file_path)

        if not run_file_path.exists():
            raise FileNotFoundError(f"Run file not found: {run_file_path}")

        # Read the run file
        content = HmsRun._read_file(run_file_path)
        original_content = content

        # Build the block pattern to find this specific run
        escaped_name = re.escape(run_name)
        block_pattern = rf'(Run:\s*{escaped_name}\s*\n)(.*?)(End:)'

        def replace_control_in_block(match):
            header = match.group(1)
            body = match.group(2)
            footer = match.group(3)

            # Replace Control line
            control_pattern = r'(\s+Control:\s*)([^\n]*)'
            if re.search(control_pattern, body):
                body = re.sub(control_pattern, rf'\g<1>{control_spec}', body)
            else:
                # Add Control line (after Precip if exists)
                precip_match = re.search(r'(\s+(?:Precip|Meteorology):[^\n]*\n)', body)
                if precip_match:
                    insert_pos = precip_match.end()
                    body = body[:insert_pos] + f'     Control: {control_spec}\n' + body[insert_pos:]
                else:
                    # After Basin
                    basin_match = re.search(r'(\s+Basin:[^\n]*\n)', body)
                    if basin_match:
                        insert_pos = basin_match.end()
                        body = body[:insert_pos] + f'     Control: {control_spec}\n' + body[insert_pos:]
                    else:
                        body = f'     Control: {control_spec}\n' + body

            return header + body + footer

        # Apply replacement
        new_content, count = re.subn(
            block_pattern,
            replace_control_in_block,
            content,
            flags=re.DOTALL
        )

        if count == 0:
            raise ValueError(f"Could not find run '{run_name}' in {run_file_path}")

        # Write back if changed
        if new_content != original_content:
            HmsRun._write_file(run_file_path, new_content)
            logger.info(f"Updated control spec for run '{run_name}' to '{control_spec}' in {run_file_path}")
        else:
            logger.info(f"Control spec already set to '{control_spec}' for run '{run_name}'")

        return True

    @staticmethod
    def _get_hms_object(hms_object: Optional[Any] = None) -> Any:
        """Get HMS object, falling back to global if not provided."""
        if hms_object is not None:
            return hms_object

        try:
            from .HmsPrj import hms
            if hms is None or not hms._initialized:
                raise RuntimeError("HMS project not initialized")
            return hms
        except ImportError:
            raise RuntimeError("Could not import HMS project module")

    @staticmethod
    def _read_file(file_path: Path) -> str:
        """Read file with encoding fallback."""
        encodings = ['utf-8', 'latin-1', 'cp1252']
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(
            f"Could not decode {file_path} with any supported encoding"
        )

    @staticmethod
    def _write_file(file_path: Path, content: str) -> None:
        """Write file with UTF-8 encoding."""
        file_path.write_text(content, encoding='utf-8')
