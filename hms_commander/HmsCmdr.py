"""
HmsCmdr - HEC-HMS Simulation Execution Engine

This module provides static methods for executing HEC-HMS simulations.
It mirrors the RasCmdr pattern from ras-commander.

Execution is performed via Jython scripts using the HmsJython class.

All methods are static and designed to be used without instantiation.
"""

import os
import shutil
import tempfile
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

from .LoggingConfig import get_logger
from .Decorators import log_call
from .HmsJython import HmsJython
from ._constants import DEFAULT_EXECUTION_TIMEOUT

logger = get_logger(__name__)


class HmsCmdr:
    """
    HEC-HMS simulation execution - mirrors RasCmdr pattern.

    All static methods, no instantiation required.

    Example:
        >>> from hms_commander import HmsCmdr, init_hms_project
        >>> init_hms_project(r"C:/HMS_Projects/MyProject", hms_exe_path=r"C:/HEC/HEC-HMS/4.9/hec-hms.cmd")
        >>> success = HmsCmdr.compute_run("Run 1")
        >>> results = HmsCmdr.compute_parallel(["Run 1", "Run 2", "Run 3"])
    """

    @staticmethod
    @log_call
    def compute_run(
        run_name: str,
        hms_object=None,
        dest_folder: Optional[Union[str, Path]] = None,
        overwrite_dest: bool = False,
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
        save_project: bool = True,
        max_memory: str = None,
        initial_memory: str = None,
        additional_java_opts: Optional[List[str]] = None
    ) -> bool:
        """
        Execute a single HEC-HMS simulation run.

        Args:
            run_name: Name of the simulation run to execute
            hms_object: Optional HmsPrj instance (uses global hms if None)
            dest_folder: Optional destination folder for execution
                        (copies project there first)
            overwrite_dest: Whether to overwrite existing destination
            timeout: Maximum execution time in seconds
            save_project: Whether to save project after computation
            max_memory: Maximum JVM heap size (default: "4G")
                       Examples: "4G", "8G", "16G" for large models
            initial_memory: Initial JVM heap size (default: "128M")
            additional_java_opts: Extra JVM options
                       Examples: ["-XX:+UseG1GC", "-XX:MaxGCPauseMillis=200"]

        Returns:
            True if computation succeeded, False otherwise

        Example:
            >>> from hms_commander import HmsCmdr, init_hms_project
            >>> init_hms_project(r"C:/Projects/MyProject", hms_exe_path=r"C:/HEC/HEC-HMS/4.9/hec-hms.cmd")
            >>> success = HmsCmdr.compute_run("Run 1")
            >>> # For large models:
            >>> success = HmsCmdr.compute_run("Run 1", max_memory="16G")
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized. Call init_hms_project() first.")

        if hms_obj.hms_exe_path is None:
            # Try to find HEC-HMS
            hms_exe = HmsJython.find_hms_executable()
            if hms_exe is None:
                raise RuntimeError(
                    "HEC-HMS executable not found. "
                    "Provide hms_exe_path in init_hms_project() or set HEC_HMS_HOME environment variable."
                )
            hms_obj.hms_exe_path = hms_exe

        # Determine working directory
        if dest_folder:
            dest_folder = Path(dest_folder)
            working_project = HmsCmdr._copy_project(
                hms_obj.project_folder,
                dest_folder,
                overwrite_dest
            )
        else:
            working_project = hms_obj.project_folder

        logger.info(f"Computing run '{run_name}' in {working_project}")

        # Generate script
        script = HmsJython.generate_compute_script(
            project_path=working_project,
            run_name=run_name,
            save_project=save_project
        )

        # Execute
        success, stdout, stderr = HmsJython.execute_script(
            script_content=script,
            hms_exe_path=hms_obj.hms_exe_path,
            working_dir=working_project,
            timeout=timeout,
            max_memory=max_memory,
            initial_memory=initial_memory,
            additional_java_opts=additional_java_opts
        )

        if success:
            logger.info(f"Run '{run_name}' completed successfully")
        else:
            logger.error(f"Run '{run_name}' failed")
            if stderr:
                logger.error(f"Error output: {stderr}")

        return success

    @staticmethod
    @log_call
    def compute_parallel(
        run_names: Optional[List[str]] = None,
        max_workers: int = 2,
        hms_object=None,
        dest_folder: Optional[Union[str, Path]] = None,
        timeout_per_run: int = DEFAULT_EXECUTION_TIMEOUT,
        max_memory: str = None,
        initial_memory: str = None,
        additional_java_opts: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Execute multiple HEC-HMS runs in parallel using worker folders.

        Each run is executed in a separate copy of the project to avoid
        conflicts. This is the recommended method for batch processing.

        Args:
            run_names: List of run names to execute (all runs if None)
            max_workers: Maximum number of parallel workers
            hms_object: Optional HmsPrj instance
            dest_folder: Base folder for worker copies
            timeout_per_run: Timeout per individual run in seconds
            max_memory: Maximum JVM heap size (default: "4G")
            initial_memory: Initial JVM heap size (default: "128M")
            additional_java_opts: Extra JVM options

        Returns:
            Dictionary mapping run names to success status

        Example:
            >>> results = HmsCmdr.compute_parallel(
            ...     ["Run 1", "Run 2", "Run 3"],
            ...     max_workers=3
            ... )
            >>> for run, success in results.items():
            ...     print(f"{run}: {'OK' if success else 'FAILED'}")
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized")

        # Get run names if not specified
        if run_names is None:
            if hms_obj.run_df.empty:
                raise ValueError("No runs found in project")
            run_names = hms_obj.run_df['name'].tolist()

        if not run_names:
            logger.warning("No runs to execute")
            return {}

        # Set up destination folder
        if dest_folder:
            base_dest = Path(dest_folder)
        else:
            base_dest = hms_obj.project_folder.parent / f"{hms_obj.project_name}_workers"

        base_dest.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting parallel execution of {len(run_names)} runs with {max_workers} workers")
        results = {}

        def execute_worker(run_name: str, worker_id: int) -> Tuple[str, bool]:
            """Execute a single run in a worker folder."""
            worker_folder = base_dest / f"worker_{worker_id}"

            try:
                # Copy project to worker folder
                working_project = HmsCmdr._copy_project(
                    hms_obj.project_folder,
                    worker_folder,
                    overwrite=True
                )

                # Generate and execute script
                script = HmsJython.generate_compute_script(
                    project_path=working_project,
                    run_name=run_name,
                    save_project=True
                )

                success, stdout, stderr = HmsJython.execute_script(
                    script_content=script,
                    hms_exe_path=hms_obj.hms_exe_path,
                    working_dir=working_project,
                    timeout=timeout_per_run,
                    max_memory=max_memory,
                    initial_memory=initial_memory,
                    additional_java_opts=additional_java_opts
                )

                return run_name, success

            except Exception as e:
                logger.error(f"Worker {worker_id} failed for '{run_name}': {e}")
                return run_name, False

        # Execute in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, run_name in enumerate(run_names):
                worker_id = i % max_workers
                future = executor.submit(execute_worker, run_name, worker_id)
                futures[future] = run_name

            for future in concurrent.futures.as_completed(futures):
                run_name, success = future.result()
                results[run_name] = success
                status = "completed" if success else "FAILED"
                logger.info(f"Run '{run_name}' {status}")

        # Summary
        successful = sum(1 for s in results.values() if s)
        failed = len(results) - successful
        logger.info(f"Parallel execution complete: {successful} succeeded, {failed} failed")

        return results

    @staticmethod
    @log_call
    def compute_batch(
        run_names: List[str],
        hms_object=None,
        save_after_each: bool = False,
        timeout: int = 7200,
        max_memory: str = None,
        initial_memory: str = None,
        additional_java_opts: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Execute multiple runs sequentially in a single HMS session.

        This is more efficient than compute_parallel when runs don't conflict
        and don't need separate output files.

        Args:
            run_names: List of run names to execute
            hms_object: Optional HmsPrj instance
            save_after_each: Whether to save project after each run
            timeout: Total timeout for all runs in seconds
            max_memory: Maximum JVM heap size (default: "4G")
            initial_memory: Initial JVM heap size (default: "128M")
            additional_java_opts: Extra JVM options

        Returns:
            Dictionary mapping run names to success status

        Example:
            >>> results = HmsCmdr.compute_batch(["Run 1", "Run 2", "Run 3"])
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized")

        if not run_names:
            logger.warning("No runs to execute")
            return {}

        logger.info(f"Starting batch execution of {len(run_names)} runs")

        # Generate batch script
        script = HmsJython.generate_batch_compute_script(
            project_path=hms_obj.project_folder,
            run_names=run_names,
            save_after_each=save_after_each
        )

        # Execute
        success, stdout, stderr = HmsJython.execute_script(
            script_content=script,
            hms_exe_path=hms_obj.hms_exe_path,
            working_dir=hms_obj.project_folder,
            timeout=timeout,
            max_memory=max_memory,
            initial_memory=initial_memory,
            additional_java_opts=additional_java_opts
        )

        # Parse results from stdout
        results = {}
        for run_name in run_names:
            # Default to overall success status
            results[run_name] = success

            # Try to parse individual status from output
            if stdout:
                if f"Completed: {run_name}" in stdout:
                    results[run_name] = True
                elif f"Error computing {run_name}" in stdout:
                    results[run_name] = False

        # Summary
        successful = sum(1 for s in results.values() if s)
        failed = len(results) - successful
        logger.info(f"Batch execution complete: {successful} succeeded, {failed} failed")

        return results

    @staticmethod
    @log_call
    def compute_with_parameters(
        run_name: str,
        basin_name: str,
        parameter_modifications: Dict[str, Dict[str, Any]],
        hms_object=None,
        dest_folder: Optional[Union[str, Path]] = None,
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
        max_memory: str = None,
        initial_memory: str = None,
        additional_java_opts: Optional[List[str]] = None
    ) -> Tuple[bool, Path]:
        """
        Execute a run with modified parameters.

        Useful for sensitivity analysis and calibration workflows.

        Args:
            run_name: Name of the simulation run
            basin_name: Name of the basin model to modify
            parameter_modifications: Dictionary of element -> parameter changes
            hms_object: Optional HmsPrj instance
            dest_folder: Destination for modified project
            timeout: Execution timeout in seconds
            max_memory: Maximum JVM heap size (default: "4G")
            initial_memory: Initial JVM heap size (default: "128M")
            additional_java_opts: Extra JVM options

        Returns:
            Tuple of (success, path to output folder)

        Example:
            >>> mods = {
            ...     "Subbasin-1": {"CurveNumber": 80, "InitialAbstraction": 0.5},
            ...     "Subbasin-2": {"CurveNumber": 75}
            ... }
            >>> success, output_path = HmsCmdr.compute_with_parameters(
            ...     "Run 1", "Basin 1", mods
            ... )
        """
        from .HmsPrj import hms
        hms_obj = hms_object or hms

        if hms_obj is None or not hms_obj.initialized:
            raise RuntimeError("HMS project not initialized")

        # Set up destination folder
        if dest_folder:
            dest_folder = Path(dest_folder)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_folder = hms_obj.project_folder.parent / f"{hms_obj.project_name}_modified_{timestamp}"

        # Copy project
        working_project = HmsCmdr._copy_project(
            hms_obj.project_folder,
            dest_folder,
            overwrite=True
        )

        logger.info(f"Computing '{run_name}' with modified parameters in {working_project}")

        # Generate script with modifications
        script = HmsJython.generate_parameter_modification_script(
            project_path=working_project,
            basin_name=basin_name,
            modifications=parameter_modifications,
            run_name=run_name
        )

        # Execute
        success, stdout, stderr = HmsJython.execute_script(
            script_content=script,
            hms_exe_path=hms_obj.hms_exe_path,
            working_dir=working_project,
            timeout=timeout,
            max_memory=max_memory,
            initial_memory=initial_memory,
            additional_java_opts=additional_java_opts
        )

        if success:
            logger.info(f"Modified run '{run_name}' completed successfully")
        else:
            logger.error(f"Modified run '{run_name}' failed")

        return success, working_project

    @staticmethod
    @log_call
    def verify_hms_installation(
        hms_exe_path: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        Verify HEC-HMS installation and return information.

        Args:
            hms_exe_path: Path to HEC-HMS executable (auto-detect if None)

        Returns:
            Dictionary with installation information
        """
        result = {
            'found': False,
            'executable': None,
            'version': None,
            'java_home': os.environ.get('JAVA_HOME'),
            'hec_hms_home': os.environ.get('HEC_HMS_HOME')
        }

        if hms_exe_path:
            exe_path = Path(hms_exe_path)
        else:
            exe_path = HmsJython.find_hms_executable()

        if exe_path and exe_path.exists():
            result['found'] = True
            result['executable'] = str(exe_path)

            # Try to extract version from path
            path_parts = exe_path.parts
            for part in path_parts:
                if part.replace('.', '').isdigit() or (
                    len(part) > 2 and part[0].isdigit() and '.' in part
                ):
                    result['version'] = part
                    break

        return result

    # =========================================================================
    # Private helper methods
    # =========================================================================

    @staticmethod
    def _copy_project(
        source_folder: Path,
        dest_folder: Path,
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
        if dest_folder.exists():
            if overwrite:
                shutil.rmtree(dest_folder)
            else:
                raise FileExistsError(f"Destination exists: {dest_folder}")

        logger.debug(f"Copying project from {source_folder} to {dest_folder}")
        shutil.copytree(source_folder, dest_folder)

        return dest_folder

    @staticmethod
    def _cleanup_worker_folders(base_folder: Path) -> None:
        """Remove worker folders after parallel execution."""
        if base_folder.exists():
            for item in base_folder.iterdir():
                if item.is_dir() and item.name.startswith("worker_"):
                    try:
                        shutil.rmtree(item)
                    except Exception as e:
                        logger.warning(f"Could not remove {item}: {e}")
