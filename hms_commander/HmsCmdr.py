"""
HmsCmdr - HEC-HMS Simulation Execution Engine

This module provides static methods for executing HEC-HMS simulations.
It mirrors the RasCmdr pattern from ras-commander.

Execution is performed via Jython scripts using the HmsJython class.

All methods are static and designed to be used without instantiation.
"""

import hashlib
import os
import re
import shutil
import tempfile
import time
import uuid
import concurrent.futures
import contextlib
import queue
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime

from .LoggingConfig import get_logger
from .Decorators import log_call
from .HmsJython import HmsJython
from ._constants import DEFAULT_EXECUTION_TIMEOUT
from ._run_lock import OutputLock

logger = get_logger(__name__)

# Run-log message codes. HEC-HMS writes one line per message, in the form
# "<NOTE|WARNING|ERROR> <code>:  <text>", to the file named by the run's
# "Log File:" entry in the .run file.
#   NOTE 15301    Began computing simulation run "<run>" ...
#   NOTE 15302    Finished computing simulation run "<run>" ...
#   WARNING 15303 Aborted run "<run>" ...
# 15301 and 15302, with the run name in quotes, appear in every shipped sample
# run log of HEC-HMS 4.4.1 through 4.13 (70 logs). 15303 and the ERROR lines
# before it were captured from a real HEC-HMS 4.10 compute of the HEC-HMS 4.13
# "tenk" sample (see tests/fixtures/hms_run_logs/).
_RUN_BEGAN_ANY = re.compile(r"^NOTE 15301:", re.MULTILINE)
_LOG_ERROR = re.compile(r"^ERROR \d+:.*$", re.MULTILINE)


def _run_markers(run_name: str) -> Tuple["re.Pattern", "re.Pattern", "re.Pattern"]:
    """Begin, finish and abort patterns for one run, matched by its quoted name."""
    quoted = re.escape(f'"{run_name}"')
    return (
        re.compile(rf"^NOTE 15301:\s+Began computing simulation run {quoted}", re.MULTILINE),
        re.compile(rf"^NOTE 15302:\s+Finished computing simulation run {quoted}", re.MULTILINE),
        re.compile(rf"^WARNING 15303:\s+Aborted run {quoted}.*$", re.MULTILINE),
    )


# Results DSS files up to this size are hashed before and after a run, so a
# rewrite is detected even when size and modification time do not change
# (coarse FAT or network-share timestamps). Larger files are compared by
# size and modification time only.
_DSS_HASH_LIMIT_BYTES = 512 * 1024 * 1024

# While a run executes, the prior run log is moved to
# "<log name>.hms-commander-prev-<32 hex digits>", a name unique to that call
# (see HmsCmdr._snapshot_run). Only names of exactly this form are ever
# treated as HMS Commander backups; any other file is left alone.
_LOG_BACKUP_INFIX = ".hms-commander-prev-"


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
            True only if HEC-HMS computed the run in this call. The log file
            and results DSS file are those the run's ``.run`` entry names
            (``Log File:``, ``DSS File:``). Both files (and ``dest_folder``,
            if given) are locked across threads and processes from before
            launch until verification ends, so another compute cannot write
            them meanwhile; computes on other files are not held up. Before
            launch, an existing log is moved to a backup name unique to this
            call, ``<log name>.hms-commander-prev-<32 hex>`` (deleted
            afterwards if the run wrote a new log, moved back if not), and
            the DSS file's size, modification time and hash (up to 512 MB)
            are recorded. Then:

            - the generated script reported no error;
            - a run log exists (written while this call held the lock) and
              has a section for this run (``NOTE 15301 ... "<run_name>"``)
              with the "Finished computing" note for it (NOTE 15302), no
              ERROR line and no "Aborted run" warning (WARNING 15303);
            - the results DSS file is new, or its size, modification time or
              content hash changed.

            Nothing is compared with the clock. If the run, its ``Log File:``
            or its ``DSS File:`` entry cannot be found, the run cannot be
            verified and False is returned. False otherwise as well; the
            reason and the relevant log lines are logged at ERROR level.

        Raises:
            RuntimeError: If the project is not initialized, or if no
                ``hms_exe_path`` was given and no installed HEC-HMS suits the
                project's ``Version:`` (equal, a newer patch of the same
                major.minor, or a newer major.minor), or if that ``Version:``
                is not a comparable version. An older HEC-HMS is never chosen
                automatically. Also if this thread is already computing with
                the same output files (a nested call).
            TimeoutError: If another compute holds the run's output files
                (or ``dest_folder``) for longer than ``timeout`` seconds.

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

        # A copied destination folder is locked while it is filled and
        # computed, so a concurrent call cannot replace it meanwhile.
        dest_lock = (
            OutputLock([Path(dest_folder)], timeout, purpose=f"copy for run '{run_name}'")
            if dest_folder else contextlib.nullcontext()
        )
        with dest_lock:
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
            success, stdout, stderr = HmsCmdr._execute_and_verify(
                run_name, working_project, script,
                hms_exe_path=hms_obj.hms_exe_path,
                timeout=timeout,
                max_memory=max_memory,
                initial_memory=initial_memory,
                additional_java_opts=additional_java_opts
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
            Dictionary mapping run names to success status.
            Each run is verified as in :meth:`compute_run` (run log section
            for that run, changed results DSS, compared with a pre-launch
            record). If no ``hms_exe_path`` is set, the HEC-HMS version is
            chosen as in :meth:`compute_run`; RuntimeError is raised when no
            installation suits the project's ``Version:``.

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

        # Each running task takes a free worker folder and returns it when
        # done, so no two runs ever use the same folder at once.
        free_workers: "queue.Queue[int]" = queue.Queue()
        for worker_id in range(max_workers):
            free_workers.put(worker_id)

        def execute_worker(run_name: str) -> Tuple[str, bool]:
            """Execute a single run in a free worker folder."""
            worker_id = free_workers.get()
            worker_folder = base_dest / f"worker_{worker_id}"

            try:
                # The worker folder is also locked across processes, in case
                # another call uses the same dest_folder.
                with OutputLock([worker_folder], timeout_per_run,
                                purpose=f"worker for run '{run_name}'"):
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

                    success, stdout, stderr = HmsCmdr._execute_and_verify(
                        run_name, working_project, script,
                        hms_exe_path=hms_obj.hms_exe_path,
                        timeout=timeout_per_run,
                        max_memory=max_memory,
                        initial_memory=initial_memory,
                        additional_java_opts=additional_java_opts
                    )
                return run_name, success

            except Exception as e:
                logger.error(f"Worker {worker_id} failed for '{run_name}': {e}")
                return run_name, False
            finally:
                free_workers.put(worker_id)

        # Execute in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for run_name in run_names:
                future = executor.submit(execute_worker, run_name)
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
        and don't need separate output files. Runs that share a run log are
        computed one HMS session per run instead (see Returns).

        Args:
            run_names: List of run names to execute
            hms_object: Optional HmsPrj instance
            save_after_each: Whether to save project after each run
            timeout: Total timeout for all runs in seconds
            max_memory: Maximum JVM heap size (default: "4G")
            initial_memory: Initial JVM heap size (default: "128M")
            additional_java_opts: Extra JVM options

        Returns:
            Dictionary mapping run names to success status.
            Each run is verified as in :meth:`compute_run` (run log section
            for that run, changed results DSS, compared with a pre-launch
            record). If no ``hms_exe_path`` is set, the HEC-HMS version is
            chosen as in :meth:`compute_run`; RuntimeError is raised when no
            installation suits the project's ``Version:``.
            When runs share a ``Log File:``, HEC-HMS would keep only the last
            run's section in one session, so each run is computed in its own
            HEC-HMS session, in the given order, and verified before the next
            starts. ``timeout`` then covers all of these sessions together.
            Runs that share a ``DSS File:`` cannot tell from the DSS file
            which of them wrote it, so the log decides.

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

        project_folder = hms_obj.project_folder
        shared = HmsCmdr._shared_log_runs(project_folder, run_names)
        results: Dict[str, bool] = {}

        if shared:
            # HEC-HMS rewrites a run log for every run it computes, so in one
            # session a shared log keeps only the last run's section. Compute
            # each run in its own session, in the given order, and verify it
            # before the next run can overwrite its log.
            for names in shared.values():
                logger.info(
                    f"Runs {', '.join(repr(n) for n in names)} write the same run log; "
                    "computing each run in its own HEC-HMS session so that each "
                    "can be verified before the next."
                )
            deadline = time.monotonic() + timeout
            for run_name in run_names:
                remaining = int(deadline - time.monotonic())
                if remaining <= 0:
                    logger.error(
                        f"Run '{run_name}' not computed: the batch timeout of "
                        f"{timeout} s was used up by earlier runs."
                    )
                    results[run_name] = False
                    continue
                script = HmsJython.generate_batch_compute_script(
                    project_path=project_folder,
                    run_names=[run_name],
                    save_after_each=save_after_each
                )
                verified, stdout, _ = HmsCmdr._execute_and_verify(
                    run_name, project_folder, script,
                    hms_exe_path=hms_obj.hms_exe_path,
                    timeout=remaining,
                    max_memory=max_memory,
                    initial_memory=initial_memory,
                    additional_java_opts=additional_java_opts,
                )
                results[run_name] = verified
        else:
            # Generate batch script
            script = HmsJython.generate_batch_compute_script(
                project_path=project_folder,
                run_names=run_names,
                save_after_each=save_after_each
            )
            # Lock every run's outputs for the whole session, so no other
            # compute can write them between snapshot and verification.
            outputs = []
            for name in run_names:
                outputs.extend(HmsCmdr._run_output_files(project_folder, name)[:2])
            with OutputLock(outputs, timeout, purpose=f"batch in {Path(project_folder).name}"):
                snapshots = {
                    name: HmsCmdr._snapshot_run(project_folder, name)
                    for name in run_names
                }

                # Execute
                try:
                    success, stdout, stderr = HmsJython.execute_script(
                        script_content=script,
                        hms_exe_path=hms_obj.hms_exe_path,
                        working_dir=project_folder,
                        timeout=timeout,
                        max_memory=max_memory,
                        initial_memory=initial_memory,
                        additional_java_opts=additional_java_opts
                    )
                except BaseException:
                    for snapshot in snapshots.values():
                        HmsCmdr._release_snapshot(snapshot)
                    raise

                for run_name in run_names:
                    # Default to overall success status
                    status = success

                    # Try to parse individual status from output
                    if stdout:
                        if f"Completed: {run_name}" in stdout:
                            status = True
                        elif f"Error computing {run_name}" in stdout:
                            status = False

                    # Confirm each run from its own run log and results DSS
                    results[run_name] = HmsCmdr._verify_run(status, snapshots[run_name])

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
            Tuple of (success, path to output folder).
            Each run is verified as in :meth:`compute_run` (run log section
            for that run, changed results DSS, compared with a pre-launch
            record). If no ``hms_exe_path`` is set, the HEC-HMS version is
            chosen as in :meth:`compute_run`; RuntimeError is raised when no
            installation suits the project's ``Version:``.

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
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            dest_folder = hms_obj.project_folder.parent / f"{hms_obj.project_name}_modified_{timestamp}"

        # The destination is locked while it is filled and computed, so a
        # concurrent call with the same dest_folder waits instead of
        # replacing it.
        with OutputLock([dest_folder], timeout, purpose=f"copy for run '{run_name}'"):
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
            success, stdout, stderr = HmsCmdr._execute_and_verify(
                run_name, working_project, script,
                hms_exe_path=hms_obj.hms_exe_path,
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
            if installed and wanted and installed < wanted:
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
        if hms_exe is None and project_version is not None and (
            HmsJython._parse_version_text(project_version) is None
        ):
            raise RuntimeError(
                f"The project's Version '{project_version}' is not a version "
                "format hms-commander can compare (expected numbers such as 4.13 "
                "or 4.7.1, optionally with an alpha, beta or rc suffix such as "
                "4.13-beta2 or 4.13-rc10), and no "
                "installation has that exact name. Pass hms_exe_path to "
                "init_hms_project() to choose one explicitly."
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
    def _run_output_files(project_folder: Union[str, Path], run_name: str) -> Tuple[Optional[Path], Optional[Path], str]:
        """
        Read the run log and results DSS paths of ``run_name`` from the project's .run files.

        The .run files in ``project_folder`` are read when called, so a
        working copy or an edited run is described as it is now. No default
        name is guessed: every run in the HEC-HMS 4.4.1 to 4.13 sample
        projects declares both ``Log File:`` and ``DSS File:``.

        Returns:
            Tuple of (log path or None, DSS path or None, problem). ``problem``
            is an empty string when both paths were found, otherwise the reason.
        """
        from ._parsing import HmsFileParser

        project_folder = Path(project_folder)
        entry = None
        for run_file in sorted(project_folder.glob("*.run")):
            try:
                blocks = HmsFileParser.parse_blocks(
                    HmsFileParser.read_file(run_file), "Run"
                )
            except Exception as e:  # unreadable .run file
                logger.debug(f"Could not read {run_file.name}: {e}")
                continue
            if run_name in blocks:
                entry = blocks[run_name]
                break
        if entry is None:
            return None, None, f"run '{run_name}' is not defined in a .run file in the project"

        log_name = str(entry.get("Log File", "") or "").strip()
        dss_name = str(entry.get("DSS File", "") or "").strip()
        log_path = project_folder / log_name if log_name else None
        dss_path = project_folder / dss_name if dss_name else None
        missing = [label for label, value in (("Log File", log_name), ("DSS File", dss_name)) if not value]
        problem = (
            f"run '{run_name}' declares no {' or '.join(missing)} entry, so its "
            "output cannot be verified" if missing else ""
        )
        return log_path, dss_path, problem

    @staticmethod
    def _execute_and_verify(
        run_name: str,
        project_folder: Union[str, Path],
        script: str,
        hms_exe_path: Union[str, Path],
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
        max_memory: str = None,
        initial_memory: str = None,
        additional_java_opts: Optional[List[str]] = None,
    ) -> Tuple[bool, str, str]:
        """
        Lock one run's outputs, snapshot them, execute ``script`` in
        ``project_folder``, verify the run, and release.

        The run's log and results DSS file are locked (:class:`OutputLock`)
        across threads and processes from before the snapshot until
        verification and clean-up are done, so another compute cannot write
        them in between and have its outputs credited to this run. Computes
        on other output files are not blocked. The lock wait counts against
        ``timeout``.

        Returns:
            Tuple of (verified success, stdout, stderr). If execution raises,
            the prior run log is put back before the exception propagates.

        Raises:
            TimeoutError: If another compute holds the outputs for longer
                than ``timeout`` seconds.
        """
        log_path, dss_path, _ = HmsCmdr._run_output_files(project_folder, run_name)
        with OutputLock([log_path, dss_path], timeout,
                        purpose=f"run '{run_name}' in {Path(project_folder).name}"):
            snapshot = HmsCmdr._snapshot_run(project_folder, run_name)
            try:
                success, stdout, stderr = HmsJython.execute_script(
                    script_content=script,
                    hms_exe_path=hms_exe_path,
                    working_dir=project_folder,
                    timeout=timeout,
                    max_memory=max_memory,
                    initial_memory=initial_memory,
                    additional_java_opts=additional_java_opts,
                )
            except BaseException:
                HmsCmdr._release_snapshot(snapshot)
                raise
            return HmsCmdr._verify_run(success, snapshot, stdout), stdout, stderr

    @staticmethod
    def _file_state(path: Optional[Path], hash_limit: int) -> Dict[str, Any]:
        """Size, mtime_ns and SHA-256 (up to ``hash_limit`` bytes) of a file; ``exists`` False if absent."""
        state: Dict[str, Any] = {"path": path, "exists": False}
        if path is None or not path.exists():
            return state
        stat = path.stat()
        state.update(exists=True, size=stat.st_size, mtime_ns=stat.st_mtime_ns)
        if stat.st_size <= hash_limit:
            digest = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    digest.update(chunk)
            state["sha256"] = digest.hexdigest()
        return state

    @staticmethod
    def _log_backups(log_path: Path) -> List[Path]:
        """HMS Commander backups of ``log_path`` (``<log>.hms-commander-prev-<32 hex>``), oldest name first."""
        pattern = re.compile(re.escape(log_path.name + _LOG_BACKUP_INFIX) + r"[0-9a-f]{32}$")
        try:
            return sorted(p for p in log_path.parent.iterdir() if pattern.match(p.name))
        except OSError:
            return []

    @staticmethod
    def _move_no_clobber(src: Path, dst: Path) -> None:
        """Move ``src`` to ``dst``; raise FileExistsError rather than replace an existing ``dst``."""
        try:
            os.link(src, dst)        # fails with FileExistsError if dst exists
        except FileExistsError:
            raise
        except OSError:
            # No hard links here (for example FAT): check, then rename.
            if dst.exists():
                raise FileExistsError(f"{dst} already exists")
            os.rename(src, dst)
            return
        os.unlink(src)

    @staticmethod
    def _recover_orphan_backups(log_path: Path) -> List[Path]:
        """
        Deal with backups that an interrupted compute left beside ``log_path``.

        Called with the run's outputs locked, so any backup found belongs to
        a compute that ended without cleaning up (for example, a killed
        Python process). A backup is never read as evidence of a run.

        - If the run log is missing and there is exactly one backup, the
          interrupted compute wrote no new log, so the backup is the user's
          earlier log: it is moved back to the log name.
        - Otherwise (a current log exists, which may be the interrupted run's
          own log, or several backups exist) nothing is moved or deleted.
          The backups are kept and listed in a warning for the user to
          review or delete.

        Returns:
            The backups that remain.
        """
        orphans = HmsCmdr._log_backups(log_path)
        if not orphans:
            return []
        if not log_path.exists() and len(orphans) == 1:
            try:
                HmsCmdr._move_no_clobber(orphans[0], log_path)
                logger.warning(
                    f"Restored {log_path.name} from {orphans[0].name}, left by an "
                    "interrupted compute that wrote no new log."
                )
                return []
            except OSError as e:
                logger.warning(f"Could not restore {log_path.name} from {orphans[0].name}: {e}")
                return orphans
        logger.warning(
            f"Kept {len(orphans)} backup(s) of {log_path.name} left by interrupted "
            f"computes: {', '.join(p.name for p in orphans)}. They are not used as "
            "evidence; review or delete them."
        )
        return orphans

    @staticmethod
    def _snapshot_run(project_folder: Union[str, Path], run_name: str) -> Dict[str, Any]:
        """
        Prepare the run's outputs for verification, just before HEC-HMS starts.

        Call with the run's outputs locked (see :meth:`_execute_and_verify`).

        - Backups left by an interrupted compute are recovered or kept, as
          described in :meth:`_recover_orphan_backups`.
        - The prior run log, if any, is moved to
          ``<log name>.hms-commander-prev-<32 hex>``, a new name unique to
          this call; an existing file is never replaced. Any run log present
          after the run was therefore written while this call held the lock,
          even if its bytes equal the prior log's. :meth:`_release_snapshot`
          later deletes that backup if a new log was written, or moves it
          back if not.
        - The results DSS file's size, mtime_ns and SHA-256 (files up to
          512 MB) are recorded.

        :meth:`_verify_run` compares the files after the run with this
        record; no wall-clock time is compared with file times.
        """
        log_path, dss_path, problem = HmsCmdr._run_output_files(project_folder, run_name)
        snapshot: Dict[str, Any] = {
            "run_name": run_name, "problem": problem,
            "log_path": log_path, "log_backup": None,
            "dss": {"path": dss_path, "exists": False},
        }
        if problem:
            return snapshot
        try:
            HmsCmdr._recover_orphan_backups(log_path)
            snapshot["dss"] = HmsCmdr._file_state(dss_path, _DSS_HASH_LIMIT_BYTES)
            if log_path.exists():
                backup = log_path.with_name(log_path.name + _LOG_BACKUP_INFIX + uuid.uuid4().hex)
                HmsCmdr._move_no_clobber(log_path, backup)
                snapshot["log_backup"] = backup
        except OSError as e:
            snapshot["problem"] = f"could not prepare the run outputs before the run: {e}"
        return snapshot

    @staticmethod
    def _release_snapshot(snapshot: Dict[str, Any]) -> None:
        """
        Deal with the prior run log that this call's :meth:`_snapshot_run` moved aside.

        Only the backup this call created is touched. If the run wrote a new
        log, the backup is deleted, as HEC-HMS replaces a run log when it
        computes the run. Otherwise the prior log is moved back. Safe to call
        more than once.
        """
        backup = snapshot.get("log_backup")
        if backup is None:
            return
        snapshot["log_backup"] = None
        log_path = snapshot["log_path"]
        try:
            if log_path.exists():
                backup.unlink(missing_ok=True)
            elif backup.exists():
                HmsCmdr._move_no_clobber(backup, log_path)
        except OSError as e:
            logger.warning(f"Could not tidy the prior run log {backup.name}: {e}")

    @staticmethod
    def _shared_log_runs(project_folder: Union[str, Path], run_names: List[str]) -> Dict[str, List[str]]:
        """Group ``run_names`` that write the same run log file (two or more per group)."""
        groups: Dict[str, List[str]] = {}
        for name in run_names:
            log_path, _, _ = HmsCmdr._run_output_files(project_folder, name)
            if log_path is not None:
                groups.setdefault(str(log_path).lower(), []).append(name)
        return {key: names for key, names in groups.items() if len(names) > 1}

    @staticmethod
    def _read_log_text(path: Path) -> str:
        data = path.read_bytes()
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")

    @staticmethod
    def _check_run_log(log_text: str, run_name: str) -> Tuple[bool, str, List[str]]:
        """
        Judge the section of a HEC-HMS run log that belongs to ``run_name``.

        The section starts at the last "Began computing simulation run
        "<run_name>"" note (NOTE 15301) and ends at the next NOTE 15301 of any
        run, so another run's result in the same log is never credited to
        ``run_name``. The run succeeded when that section has the "Finished
        computing" note for ``run_name`` (NOTE 15302), no "Aborted run"
        warning (WARNING 15303) and no ERROR line.

        Returns:
            Tuple of (succeeded, reason, relevant log lines)
        """
        began, finished, aborted_re = _run_markers(run_name)
        starts = [m.start() for m in began.finditer(log_text)]
        if not starts:
            return False, f"the run log has no 'Began computing' note (NOTE 15301) for run '{run_name}'", []
        start = starts[-1]
        following = _RUN_BEGAN_ANY.search(log_text, start + 1)
        section = log_text[start:following.start() if following else len(log_text)]

        errors = [m.group(0).strip() for m in _LOG_ERROR.finditer(section)]
        aborted = [m.group(0).strip() for m in aborted_re.finditer(section)]
        if aborted:
            return False, "HEC-HMS aborted the run (WARNING 15303)", errors + aborted
        if errors:
            return False, "the run log contains ERROR messages", errors
        if not finished.search(section):
            return False, f"the run log has no 'Finished computing' note (NOTE 15302) for run '{run_name}'", []
        return True, "finished computing (NOTE 15302)", []

    @staticmethod
    def _verify_run(script_success: bool, snapshot: Dict[str, Any], stdout: str = "") -> bool:
        """
        Confirm from the run's own outputs that HEC-HMS computed the run.

        ``snapshot`` comes from :meth:`_snapshot_run`, taken just before
        launch; this call also releases it (:meth:`_release_snapshot`).
        Checks, in order:

        1. the run declares a ``Log File`` and a ``DSS File`` (otherwise the
           run cannot be verified and False is returned);
        2. the script's own result;
        3. a run log exists. The prior log was moved aside before launch, so
           it was written by this run. It must have a section for this run
           that :meth:`_check_run_log` accepts;
        4. the results DSS file exists and changed since the snapshot (it is
           new, or its size, modification time or SHA-256 differs).

        Nothing is compared with the clock, so clock skew between this
        computer and a file server does not matter. A changed DSS file does
        not show which run wrote it; the run identity comes from the log.

        Returns:
            True only if every check passes. The reason for a failure and the
            relevant log lines are logged at ERROR level.
        """
        try:
            return HmsCmdr._verify_outputs(script_success, snapshot, stdout)
        finally:
            HmsCmdr._release_snapshot(snapshot)

    @staticmethod
    def _verify_outputs(script_success: bool, snapshot: Dict[str, Any], stdout: str) -> bool:
        run_name = snapshot["run_name"]

        def fail(reason: str, lines: Optional[List[str]] = None) -> bool:
            logger.error(f"Run '{run_name}' failed: {reason}.")
            for line in (lines or [])[:20]:
                logger.error(f"  {line}")
            return False

        if snapshot.get("problem"):
            return fail(snapshot["problem"])

        log_path, dss_before = snapshot["log_path"], snapshot["dss"]
        dss_path = dss_before["path"]
        try:
            log_text = HmsCmdr._read_log_text(log_path) if log_path.exists() else None
            dss_after = HmsCmdr._file_state(dss_path, _DSS_HASH_LIMIT_BYTES)
        except OSError as e:
            return fail(f"could not read the run outputs after the run: {e}")

        if not script_success:
            lines: List[str] = []
            if log_text is not None:
                _, _, lines = HmsCmdr._check_run_log(log_text, run_name)
            if not lines and stdout:
                lines = [
                    ln.strip() for ln in stdout.splitlines()
                    if ln.strip().startswith(("ERROR", "Error"))
                ]
            return fail("the HEC-HMS script did not complete", lines)

        if log_text is None:
            return fail(f"no run log was written ({log_path.name})")

        ok, reason, lines = HmsCmdr._check_run_log(log_text, run_name)
        if not ok:
            return fail(f"{reason}; see {log_path.name}", lines)

        if not dss_after["exists"]:
            return fail(f"the results DSS file {dss_path.name} was not written")
        dss_changed = not dss_before["exists"] or any(
            dss_after.get(key) != dss_before.get(key) for key in ("size", "mtime_ns", "sha256")
        )
        if not dss_changed:
            return fail(f"the results DSS file {dss_path.name} was not changed by this run")

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
