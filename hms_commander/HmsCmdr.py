"""
HmsCmdr - HEC-HMS Simulation Execution Engine

This module provides static methods for executing HEC-HMS simulations.
It mirrors the RasCmdr pattern from ras-commander.

Execution is performed via Jython scripts using the HmsJython class.

All methods are static and designed to be used without instantiation.
"""

import os
import re
import shutil
import tempfile
import time
import concurrent.futures
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

from .LoggingConfig import get_logger
from .Decorators import log_call
from .HmsJython import HmsJython
from ._constants import DEFAULT_EXECUTION_TIMEOUT

logger = get_logger(__name__)

# Run-log message codes. HEC-HMS writes one line per message, in the form
# "<NOTE|WARNING|ERROR> <code>:  <text>", to the file named by the run's
# "Log File:" entry in the .run file.
#   NOTE 15301    Began computing simulation run "<run>" ...
#   NOTE 15302    Finished computing simulation run "<run>" ...
#   WARNING 15303 Aborted run "<run>" ...
# 15301 and 15302 appear in every shipped sample run log of HEC-HMS 4.4.1
# through 4.13. 15303 and the ERROR lines before it were captured from a real
# HEC-HMS 4.10 compute of the HEC-HMS 4.13 "tenk" sample (see
# tests/fixtures/hms_run_logs/).
_RUN_BEGAN = re.compile(r"^NOTE 15301:", re.MULTILINE)
_RUN_FINISHED = re.compile(r"^NOTE 15302:", re.MULTILINE)
_RUN_ABORTED = re.compile(r"^WARNING 15303:.*$", re.MULTILINE)
_LOG_ERROR = re.compile(r"^ERROR \d+:.*$", re.MULTILINE)

# File-system timestamp tolerance when comparing modification times with the
# moment the run started (FAT and some network shares store 2-second times).
_MTIME_TOLERANCE_S = 2.0


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
            True only if HEC-HMS computed the run in this call: the script
            completed, the run log written by this call contains the
            "Finished computing" note (NOTE 15302) with no ERROR line and no
            "Aborted run" warning (WARNING 15303), and the run's results DSS
            file was written by this call. False otherwise; the reason and
            the relevant log lines are logged at ERROR level.

        Raises:
            RuntimeError: If the project is not initialized, or if no
                ``hms_exe_path`` was given and no installed HEC-HMS matches
                the project's ``Version:`` (exactly, by major.minor, or by a
                newer version). An older HEC-HMS is not chosen automatically.

        Note:
            Without ``hms_exe_path``, the HEC-HMS version is chosen from the
            project's ``.hms`` file ``Version:`` line; see
            :meth:`HmsJython.find_hms_executable`.

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

        HmsCmdr._ensure_hms_executable(hms_obj)

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
        started_at = time.time()
        success, stdout, stderr = HmsJython.execute_script(
            script_content=script,
            hms_exe_path=hms_obj.hms_exe_path,
            working_dir=working_project,
            timeout=timeout,
            max_memory=max_memory,
            initial_memory=initial_memory,
            additional_java_opts=additional_java_opts
        )

        success = HmsCmdr._verify_run(
            success, run_name, working_project, started_at, hms_obj, stdout
        )

        if success:
            logger.info(f"Run '{run_name}' completed successfully")
        else:
            logger.error(
                f"Run '{run_name}' failed. "
                f"See: https://hms-commander.readthedocs.io/user-guide/execution/"
            )
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

        HmsCmdr._ensure_hms_executable(hms_obj)

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

                started_at = time.time()
                success, stdout, stderr = HmsJython.execute_script(
                    script_content=script,
                    hms_exe_path=hms_obj.hms_exe_path,
                    working_dir=working_project,
                    timeout=timeout_per_run,
                    max_memory=max_memory,
                    initial_memory=initial_memory,
                    additional_java_opts=additional_java_opts
                )

                success = HmsCmdr._verify_run(
                    success, run_name, working_project, started_at, hms_obj, stdout
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

        HmsCmdr._ensure_hms_executable(hms_obj)

        logger.info(f"Starting batch execution of {len(run_names)} runs")

        # Generate batch script
        script = HmsJython.generate_batch_compute_script(
            project_path=hms_obj.project_folder,
            run_names=run_names,
            save_after_each=save_after_each
        )

        # Execute
        started_at = time.time()
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

            # Confirm each run from its own run log and results DSS
            results[run_name] = HmsCmdr._verify_run(
                results[run_name], run_name, hms_obj.project_folder,
                started_at, hms_obj
            )

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

        HmsCmdr._ensure_hms_executable(hms_obj)

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
        started_at = time.time()
        success, stdout, stderr = HmsJython.execute_script(
            script_content=script,
            hms_exe_path=hms_obj.hms_exe_path,
            working_dir=working_project,
            timeout=timeout,
            max_memory=max_memory,
            initial_memory=initial_memory,
            additional_java_opts=additional_java_opts
        )

        success = HmsCmdr._verify_run(
            success, run_name, working_project, started_at, hms_obj, stdout
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
    def _ensure_hms_executable(hms_obj, search_paths=None, include_defaults=True) -> Path:
        """
        Set ``hms_obj.hms_exe_path`` from the project's version when it is unset.

        The project's ``.hms`` ``Version:`` line selects the installation (see
        :meth:`HmsJython.find_hms_executable`). An explicitly given path is
        kept; a warning is logged when its version is older than the project's.

        Raises:
            RuntimeError: If no suitable installation is found.
        """
        project_version = getattr(hms_obj, "hms_version", None)
        if project_version in (None, "", "Unknown"):
            project_version = None

        if hms_obj.hms_exe_path is not None:
            exe = Path(hms_obj.hms_exe_path)
            # A folder name such as "4.13" has a suffix, so test for a file
            install = exe.parent if exe.is_file() else exe
            installed = HmsJython._parse_version_text(install.name)
            wanted = HmsJython._parse_version_text(project_version)
            if installed and wanted and installed[:2] < wanted[:2]:
                logger.warning(
                    f"hms_exe_path selects HEC-HMS {install.name}, older than the "
                    f"project's version {project_version}. HEC-HMS may abort the run."
                )
            return exe

        if project_version is None:
            logger.warning(
                "The project's .hms file declares no Version; using the newest "
                "installed HEC-HMS."
            )

        hms_exe = HmsJython.find_hms_executable(
            version=project_version,
            search_paths=search_paths,
            include_defaults=include_defaults,
        )
        if hms_exe is None:
            installed = ", ".join(
                HmsJython._installed_hms_versions(search_paths, include_defaults)
            ) or "none"
            raise RuntimeError(
                f"No installed HEC-HMS suits this project (project Version: "
                f"{project_version or 'not declared'}; installed: {installed}). "
                "Install that version, or pass hms_exe_path to init_hms_project() "
                "to choose one explicitly."
            )
        logger.info(
            f"Using HEC-HMS {hms_exe.name} for project version {project_version}"
        )
        hms_obj.hms_exe_path = hms_exe
        return hms_exe

    @staticmethod
    def _run_output_files(hms_obj, run_name: str, project_folder: Path) -> Tuple[Path, Optional[Path]]:
        """
        Return the run log and results DSS paths for ``run_name``.

        Names come from the run's ``Log File:`` and ``DSS File:`` entries.
        When the log name is not recorded, HEC-HMS's default (run name with
        spaces replaced by underscores, plus ``.log``) is used.
        """
        log_name, dss_name = "", ""
        run_df = getattr(hms_obj, "run_df", None)
        if run_df is not None and not run_df.empty and "name" in run_df.columns:
            rows = run_df[run_df["name"] == run_name]
            if not rows.empty:
                row = rows.iloc[0]
                log_name = str(row.get("log_file", "") or "").strip()
                dss_name = str(row.get("dss_file", "") or "").strip()
        if not log_name:
            log_name = run_name.replace(" ", "_") + ".log"
        log_path = Path(project_folder) / log_name
        dss_path = Path(project_folder) / dss_name if dss_name else None
        return log_path, dss_path

    @staticmethod
    def _check_run_log(log_text: str) -> Tuple[bool, str, List[str]]:
        """
        Judge a HEC-HMS run log.

        Only the part after the last "Began computing" note (NOTE 15301) is
        considered. The run succeeded when that part contains the "Finished
        computing" note (NOTE 15302), no "Aborted run" warning (WARNING 15303)
        and no ERROR line.

        Returns:
            Tuple of (succeeded, reason, relevant log lines)
        """
        starts = [m.start() for m in _RUN_BEGAN.finditer(log_text)]
        if not starts:
            return False, "the run log has no 'Began computing' note (NOTE 15301)", []
        section = log_text[starts[-1]:]

        errors = [m.group(0).strip() for m in _LOG_ERROR.finditer(section)]
        aborted = [m.group(0).strip() for m in _RUN_ABORTED.finditer(section)]
        if aborted:
            return False, "HEC-HMS aborted the run (WARNING 15303)", errors + aborted
        if errors:
            return False, "the run log contains ERROR messages", errors
        if not _RUN_FINISHED.search(section):
            return False, "the run log has no 'Finished computing' note (NOTE 15302)", []
        return True, "finished computing (NOTE 15302)", []

    @staticmethod
    def _verify_run(
        script_success: bool,
        run_name: str,
        project_folder: Union[str, Path],
        started_at: float,
        hms_obj,
        stdout: str = "",
    ) -> bool:
        """
        Confirm from the run's own outputs that HEC-HMS computed ``run_name``.

        Checks, in order: the script's own result, a run log written after
        ``started_at`` that :meth:`_check_run_log` accepts, and a results DSS
        file written after ``started_at``. Logs the reason for any failure
        with the relevant run-log lines.

        Returns:
            True only if every check passes.
        """
        project_folder = Path(project_folder)
        log_path, dss_path = HmsCmdr._run_output_files(hms_obj, run_name, project_folder)
        cutoff = started_at - _MTIME_TOLERANCE_S

        def fail(reason: str, lines: Optional[List[str]] = None) -> bool:
            logger.error(f"Run '{run_name}' failed: {reason}.")
            for line in (lines or [])[:20]:
                logger.error(f"  {line}")
            return False

        log_text = None
        if log_path.exists() and log_path.stat().st_mtime >= cutoff:
            log_text = log_path.read_text(encoding="utf-8", errors="replace")

        if not script_success:
            lines: List[str] = []
            if log_text is not None:
                _, _, lines = HmsCmdr._check_run_log(log_text)
            if not lines and stdout:
                lines = [
                    ln.strip() for ln in stdout.splitlines()
                    if ln.strip().startswith("ERROR") or ln.strip().startswith("Error")
                ]
            return fail("the HEC-HMS script did not complete", lines)

        if not log_path.exists():
            return fail(f"no run log was written ({log_path.name})")
        if log_text is None:
            return fail(
                f"the run log {log_path.name} was not updated by this run "
                f"(it predates the start of the run)"
            )

        ok, reason, lines = HmsCmdr._check_run_log(log_text)
        if not ok:
            return fail(f"{reason}; see {log_path.name}", lines)

        if dss_path is not None:
            if not dss_path.exists():
                return fail(f"the results DSS file {dss_path.name} was not written")
            if dss_path.stat().st_mtime < cutoff:
                return fail(
                    f"the results DSS file {dss_path.name} was not updated by this run"
                )

        logger.debug(f"Run '{run_name}' verified: {reason}; log {log_path.name}")
        return True

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
