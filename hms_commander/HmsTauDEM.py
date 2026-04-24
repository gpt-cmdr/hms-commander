"""
Direct TauDEM CLI execution helpers.

This module provides a narrow, reusable wrapper around the core TauDEM tools
needed by the shared watershed delineation workflow. The emphasis is on
durable orchestration artifacts:

- deterministic run layout under `raw/taudem_runs/<run_name>/`
- machine-readable command manifest and run report
- per-step logs and output-path contracts

The implementation intentionally avoids GIS-heavy preprocessing or verification
logic. It focuses on executing TauDEM steps against prepared inputs.
"""

from __future__ import annotations

import os
import json
import shutil
import subprocess
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .Decorators import log_call
from .LoggingConfig import get_logger
from ._constants import DEFAULT_EXECUTION_TIMEOUT

logger = get_logger(__name__)

try:
    PACKAGE_VERSION = version("hms-commander")
except PackageNotFoundError:  # pragma: no cover - fallback for source-only runs
    PACKAGE_VERSION = "0.2.1"


class HmsTauDEM:
    """Static helpers for direct TauDEM CLI execution and manifesting."""

    TOOL_CANDIDATES: Mapping[str, Sequence[str]] = {
        "pitremove": ("pitremove", "PitRemove"),
        "d8flowdir": ("d8flowdir", "D8FlowDir"),
        "aread8": ("aread8", "AreaD8"),
        "threshold": ("threshold", "Threshold"),
        "moveoutletstostrm": ("MoveOutletsToStreams", "moveoutletstostrm"),
        "streamnet": ("streamnet", "StreamNet"),
        "gridnet": ("gridnet", "GridNet"),
        "mpiexec": ("mpiexec",),
    }
    STANDARD_STEP_ORDER: Tuple[str, ...] = (
        "pitremove",
        "d8flowdir",
        "aread8",
        "threshold",
        "moveoutletstostrm",
        "streamnet",
    )

    @staticmethod
    def _utc_now() -> str:
        """Return a compact UTC timestamp."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @staticmethod
    def _json_default(value: Any) -> Any:
        """Serialize pathlib objects inside JSON payloads."""
        if isinstance(value, Path):
            return str(value)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """Write JSON with stable formatting."""
        existed = path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, default=HmsTauDEM._json_default) + "\n",
            encoding="utf-8",
        )
        return {"status": "updated" if existed else "created", "bytes": path.stat().st_size}

    @staticmethod
    def _tool_names(tool_name: str) -> Sequence[str]:
        """Return executable name candidates for a TauDEM tool."""
        normalized = str(tool_name).lower()
        return HmsTauDEM.TOOL_CANDIDATES.get(normalized, (tool_name,))

    @staticmethod
    def _candidate_search_paths(search_paths: Optional[Sequence[Union[str, Path]]] = None) -> List[Path]:
        """Collect plausible TauDEM search directories."""
        explicit_candidates: List[Path] = []
        fallback_candidates: List[Path] = []

        def add_path(path_value: Optional[Union[str, Path]], bucket: List[Path]) -> None:
            if not path_value:
                return
            path = Path(path_value)
            if path.is_file():
                bucket.append(path.parent)
            else:
                bucket.append(path)

        for item in search_paths or ():
            add_path(item, explicit_candidates)

        for well_known_path in (
            Path(r"C:\Program Files\Microsoft MPI\Bin"),
            Path(r"C:\Program Files\TauDEM\TauDEM5Exe"),
            Path(r"C:\Program Files\TauDEM"),
        ):
            add_path(well_known_path, fallback_candidates)

        for env_name in ("TAUDEM_HOME", "HEC_HMS_HOME"):
            env_value = os.environ.get(env_name)
            if env_value:
                env_path = Path(env_value)
                add_path(env_path, fallback_candidates)
                add_path(env_path / "bin", fallback_candidates)
                add_path(env_path / "bin" / "taudem", fallback_candidates)

        try:
            from .HmsJython import HmsJython

            hms_install = HmsJython.find_hms_executable()
            if hms_install:
                add_path(hms_install, fallback_candidates)
                add_path(hms_install / "bin", fallback_candidates)
                add_path(hms_install / "bin" / "taudem", fallback_candidates)
        except Exception:  # pragma: no cover - defensive only
            pass

        path_env = os.environ.get("PATH", "")
        for item in path_env.split(os.pathsep):
            if item:
                add_path(item, fallback_candidates)

        candidates = explicit_candidates + fallback_candidates

        unique_candidates: List[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            candidate_str = str(candidate)
            if candidate_str not in seen:
                seen.add(candidate_str)
                unique_candidates.append(candidate)
        return unique_candidates

    @staticmethod
    @log_call
    def find_executable(
        tool_name: str,
        search_paths: Optional[Sequence[Union[str, Path]]] = None,
    ) -> Optional[Path]:
        """Find a TauDEM executable by name."""
        direct_path = Path(str(tool_name))
        if direct_path.exists():
            return direct_path.resolve()

        explicit_dirs: List[Path] = []
        for item in search_paths or ():
            path = Path(item)
            explicit_dirs.append(path.parent if path.is_file() else path)

        fallback_dirs = HmsTauDEM._candidate_search_paths(None)
        name_candidates: List[str] = []
        for base_name in HmsTauDEM._tool_names(tool_name):
            if Path(base_name).suffix:
                name_candidates.append(base_name)
            else:
                name_candidates.extend(
                    [base_name, f"{base_name}.exe", f"{base_name}.cmd", f"{base_name}.bat"]
                )

        for name in name_candidates:
            for directory in explicit_dirs:
                candidate = directory / name
                if candidate.exists():
                    return candidate.resolve()
        for name in name_candidates:
            for directory in fallback_dirs:
                candidate = directory / name
                if candidate.exists():
                    return candidate.resolve()
        for name in name_candidates:
            which_match = shutil.which(name)
            if which_match:
                return Path(which_match).resolve()
        return None

    @staticmethod
    @log_call
    def validate_environment(
        required_tools: Optional[Sequence[str]] = None,
        search_paths: Optional[Sequence[Union[str, Path]]] = None,
        mpi_processes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Validate TauDEM tool discovery for the requested workflow."""
        tools = list(required_tools or HmsTauDEM.STANDARD_STEP_ORDER)
        if mpi_processes is not None and mpi_processes >= 1:
            tools.append("mpiexec")

        resolved_tools: Dict[str, Optional[Path]] = {}
        missing_tools: List[str] = []
        for tool in tools:
            executable = HmsTauDEM.find_executable(tool, search_paths=search_paths)
            resolved_tools[tool] = executable
            if executable is None:
                missing_tools.append(tool)

        return {
            "available": not missing_tools,
            "required_tools": tools,
            "search_paths": [str(path) for path in HmsTauDEM._candidate_search_paths(search_paths)],
            "tools": {tool: str(path) if path else None for tool, path in resolved_tools.items()},
            "missing_tools": missing_tools,
        }

    @staticmethod
    def create_workspace(workspace_root: Union[str, Path], run_name: str = "standard") -> Dict[str, Path]:
        """Create the standard TauDEM run layout under a study workspace."""
        workspace_root = Path(workspace_root)
        run_root = workspace_root / "raw" / "taudem_runs" / run_name
        logs_dir = run_root / "logs"
        run_root.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        return {
            "workspace_root": workspace_root,
            "run_root": run_root,
            "logs": logs_dir,
        }

    @staticmethod
    def _runtime_env(
        search_paths: Optional[Sequence[Union[str, Path]]] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, str]:
        """Build the runtime environment for TauDEM subprocesses."""
        runtime_env = os.environ.copy()
        if env:
            runtime_env.update({key: str(value) for key, value in env.items()})
        candidate_paths = [str(path) for path in HmsTauDEM._candidate_search_paths(search_paths)]
        if candidate_paths:
            runtime_env["PATH"] = os.pathsep.join(candidate_paths + [runtime_env.get("PATH", "")])
        return runtime_env

    @staticmethod
    def _standard_output_paths(run_root: Path, outlet_path: Union[str, Path]) -> Dict[str, Path]:
        """Return the deterministic output layout for a standard TauDEM run."""
        outlet_suffix = Path(outlet_path).suffix or ".shp"
        return {
            "fel": run_root / "fel.tif",
            "p": run_root / "p.tif",
            "sd8": run_root / "sd8.tif",
            "ad8": run_root / "ad8.tif",
            "src": run_root / "src.tif",
            "outlet_snapped": run_root / f"outlet_snapped{outlet_suffix}",
            "ord": run_root / "ord.tif",
            "tree": run_root / "tree.dat",
            "coord": run_root / "coord.dat",
            "net": run_root / "net.shp",
            "w": run_root / "w.tif",
            "plen": run_root / "plen.tif",
            "tlen": run_root / "tlen.tif",
            "gord": run_root / "gord.tif",
            "command_manifest": run_root / "taudem_command_manifest.json",
            "run_report": run_root / "taudem_run_report.json",
        }

    @staticmethod
    def _artifact_catalog(
        output_paths: Mapping[str, Path],
        *,
        include_gridnet: bool = False,
    ) -> List[Dict[str, Any]]:
        """Build the artifact list for the standard TauDEM run."""
        specs = [
            ("fel", "raster", "tif", "Pit-removed DEM."),
            ("p", "raster", "tif", "D8 flow direction grid."),
            ("sd8", "raster", "tif", "D8 slope grid."),
            ("ad8", "raster", "tif", "D8 contributing area grid."),
            ("src", "raster", "tif", "Stream raster after thresholding."),
            ("outlet_snapped", "vector", output_paths["outlet_snapped"].suffix.lstrip("."), "Outlet snapped to the stream network."),
            ("ord", "raster", "tif", "Grid of stream order values."),
            ("tree", "table", "dat", "Stream topology tree output."),
            ("coord", "table", "dat", "Stream network coordinates table."),
            ("net", "vector", "shp", "Stream network vector output."),
            ("w", "raster", "tif", "Watershed grid output."),
        ]
        if include_gridnet:
            specs.extend(
                [
                    ("plen", "raster", "tif", "Longest path length grid."),
                    ("tlen", "raster", "tif", "Total path length grid."),
                    ("gord", "raster", "tif", "Grid network order output."),
                ]
            )
        specs.extend(
            [
                ("command_manifest", "report", "json", "Machine-readable TauDEM command manifest."),
                ("run_report", "report", "json", "High-level TauDEM run summary."),
            ]
        )

        artifacts: List[Dict[str, Any]] = []
        for artifact_id, artifact_type, fmt, description in specs:
            path = output_paths[artifact_id]
            entry = {
                "id": artifact_id,
                "artifact_type": artifact_type,
                "format": fmt,
                "description": description,
                "path": str(path),
                "status": "created" if path.exists() else "planned",
            }
            if path.exists():
                entry["bytes"] = path.stat().st_size
            artifacts.append(entry)
        return artifacts

    @staticmethod
    def _artifact_rows(artifacts: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Build compact report rows from artifact entries."""
        return [{"id": artifact["id"], "path": artifact["path"], "status": artifact["status"]} for artifact in artifacts]

    @staticmethod
    def _run_step(
        step_name: str,
        args: Sequence[Union[str, Path, int, float]],
        *,
        run_root: Union[str, Path],
        search_paths: Optional[Sequence[Union[str, Path]]] = None,
        executable_path: Optional[Union[str, Path]] = None,
        expected_outputs: Optional[Mapping[str, Union[str, Path]]] = None,
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
        mpi_processes: Optional[int] = None,
        mpiexec_path: Optional[Union[str, Path]] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Execute one TauDEM step and capture logs plus machine-readable status."""
        run_root = Path(run_root)
        logs_dir = run_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        stdout_path = logs_dir / f"{step_name}.stdout.log"
        stderr_path = logs_dir / f"{step_name}.stderr.log"

        executable = Path(executable_path).resolve() if executable_path else HmsTauDEM.find_executable(step_name, search_paths=search_paths)
        if executable is None:
            step_result = {
                "step": step_name,
                "tool": step_name,
                "status": "failed",
                "started_at": HmsTauDEM._utc_now(),
                "finished_at": HmsTauDEM._utc_now(),
                "duration_seconds": 0.0,
                "exit_code": None,
                "command": [],
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "outputs": {name: str(Path(path)) for name, path in (expected_outputs or {}).items()},
                "missing_outputs": list((expected_outputs or {}).keys()),
                "error": f"Executable not found for step '{step_name}'.",
            }
            stdout_path.write_text("", encoding="utf-8")
            stderr_path.write_text(step_result["error"] + "\n", encoding="utf-8")
            return step_result

        command: List[str] = []
        if mpi_processes is not None and mpi_processes >= 1:
            mpi_executable = (
                Path(mpiexec_path).resolve()
                if mpiexec_path
                else HmsTauDEM.find_executable("mpiexec", search_paths=search_paths)
            )
            if mpi_executable is None:
                error_message = "MPI execution requested but mpiexec could not be found."
                stdout_path.write_text("", encoding="utf-8")
                stderr_path.write_text(error_message + "\n", encoding="utf-8")
                return {
                    "step": step_name,
                    "tool": step_name,
                    "status": "failed",
                    "started_at": HmsTauDEM._utc_now(),
                    "finished_at": HmsTauDEM._utc_now(),
                    "duration_seconds": 0.0,
                    "exit_code": None,
                    "command": [],
                    "stdout_log": str(stdout_path),
                    "stderr_log": str(stderr_path),
                    "outputs": {name: str(Path(path)) for name, path in (expected_outputs or {}).items()},
                    "missing_outputs": list((expected_outputs or {}).keys()),
                    "error": error_message,
                }
            command.extend([str(mpi_executable), "-n", str(max(int(mpi_processes), 1))])

        command.append(str(executable))
        command.extend(str(arg) for arg in args)

        started_at = datetime.now(timezone.utc)
        runtime_env = HmsTauDEM._runtime_env(search_paths=search_paths, env=env)

        try:
            process = subprocess.run(
                command,
                cwd=str(run_root),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=runtime_env,
            )
            stdout_text = process.stdout or ""
            stderr_text = process.stderr or ""
            stdout_path.write_text(stdout_text, encoding="utf-8")
            stderr_path.write_text(stderr_text, encoding="utf-8")
            exit_code = process.returncode
        except subprocess.TimeoutExpired as exc:
            stdout_text = exc.stdout or ""
            stderr_text = (exc.stderr or "") + f"\nTimed out after {timeout} seconds."
            stdout_path.write_text(stdout_text, encoding="utf-8")
            stderr_path.write_text(stderr_text, encoding="utf-8")
            finished_at = datetime.now(timezone.utc)
            return {
                "step": step_name,
                "tool": step_name,
                "status": "failed",
                "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "finished_at": finished_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
                "exit_code": None,
                "command": command,
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "outputs": {name: str(Path(path)) for name, path in (expected_outputs or {}).items()},
                "missing_outputs": list((expected_outputs or {}).keys()),
                "error": f"Timed out after {timeout} seconds.",
            }
        except Exception as exc:  # pragma: no cover - defensive only
            stderr_path.write_text(str(exc) + "\n", encoding="utf-8")
            stdout_path.write_text("", encoding="utf-8")
            finished_at = datetime.now(timezone.utc)
            return {
                "step": step_name,
                "tool": step_name,
                "status": "failed",
                "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "finished_at": finished_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
                "exit_code": None,
                "command": command,
                "stdout_log": str(stdout_path),
                "stderr_log": str(stderr_path),
                "outputs": {name: str(Path(path)) for name, path in (expected_outputs or {}).items()},
                "missing_outputs": list((expected_outputs or {}).keys()),
                "error": str(exc),
            }

        finished_at = datetime.now(timezone.utc)
        output_paths = {name: Path(path) for name, path in (expected_outputs or {}).items()}
        missing_outputs = [name for name, path in output_paths.items() if not path.exists()]
        status = "completed" if exit_code == 0 and not missing_outputs else "failed"
        error = None
        if exit_code != 0:
            error = f"Step '{step_name}' exited with code {exit_code}."
        elif missing_outputs:
            error = f"Step '{step_name}' completed without creating expected outputs: {', '.join(missing_outputs)}."

        return {
            "step": step_name,
            "tool": step_name,
            "status": status,
            "started_at": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "finished_at": finished_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "exit_code": exit_code,
            "command": command,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
            "outputs": {name: str(path) for name, path in output_paths.items()},
            "missing_outputs": missing_outputs,
            "error": error,
        }

    @staticmethod
    def pitremove(
        dem_path: Union[str, Path],
        fel_path: Union[str, Path],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `pitremove`."""
        return HmsTauDEM._run_step(
            "pitremove",
            ["-z", dem_path, "-fel", fel_path],
            expected_outputs={"fel": fel_path},
            **kwargs,
        )

    @staticmethod
    def d8flowdir(
        fel_path: Union[str, Path],
        p_path: Union[str, Path],
        sd8_path: Union[str, Path],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `d8flowdir`."""
        return HmsTauDEM._run_step(
            "d8flowdir",
            ["-fel", fel_path, "-p", p_path, "-sd8", sd8_path],
            expected_outputs={"p": p_path, "sd8": sd8_path},
            **kwargs,
        )

    @staticmethod
    def aread8(
        p_path: Union[str, Path],
        ad8_path: Union[str, Path],
        *,
        outlet_path: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `aread8`."""
        args: List[Union[str, Path]] = ["-p", p_path, "-ad8", ad8_path]
        if outlet_path is not None:
            args.extend(["-o", outlet_path])
        return HmsTauDEM._run_step(
            "aread8",
            args,
            expected_outputs={"ad8": ad8_path},
            **kwargs,
        )

    @staticmethod
    def threshold(
        ad8_path: Union[str, Path],
        src_path: Union[str, Path],
        threshold_value: Union[int, float],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `threshold`."""
        return HmsTauDEM._run_step(
            "threshold",
            ["-ssa", ad8_path, "-src", src_path, "-thresh", threshold_value],
            expected_outputs={"src": src_path},
            **kwargs,
        )

    @staticmethod
    def moveoutletstostrm(
        p_path: Union[str, Path],
        src_path: Union[str, Path],
        outlet_path: Union[str, Path],
        snapped_outlet_path: Union[str, Path],
        *,
        max_distance: Optional[Union[int, float]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `moveoutletstostrm`."""
        args: List[Union[str, Path, int, float]] = [
            "-p", p_path,
            "-src", src_path,
            "-o", outlet_path,
            "-om", snapped_outlet_path,
        ]
        if max_distance is not None:
            args.extend(["-md", max_distance])
        return HmsTauDEM._run_step(
            "moveoutletstostrm",
            args,
            expected_outputs={"outlet_snapped": snapped_outlet_path},
            **kwargs,
        )

    @staticmethod
    def streamnet(
        fel_path: Union[str, Path],
        p_path: Union[str, Path],
        ad8_path: Union[str, Path],
        src_path: Union[str, Path],
        outlet_path: Union[str, Path],
        ord_path: Union[str, Path],
        tree_path: Union[str, Path],
        coord_path: Union[str, Path],
        net_path: Union[str, Path],
        watershed_path: Union[str, Path],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `streamnet`."""
        return HmsTauDEM._run_step(
            "streamnet",
            [
                "-fel", fel_path,
                "-p", p_path,
                "-ad8", ad8_path,
                "-src", src_path,
                "-o", outlet_path,
                "-ord", ord_path,
                "-tree", tree_path,
                "-coord", coord_path,
                "-net", net_path,
                "-w", watershed_path,
            ],
            expected_outputs={
                "ord": ord_path,
                "tree": tree_path,
                "coord": coord_path,
                "net": net_path,
                "w": watershed_path,
            },
            **kwargs,
        )

    @staticmethod
    def gridnet(
        p_path: Union[str, Path],
        plen_path: Union[str, Path],
        tlen_path: Union[str, Path],
        gord_path: Union[str, Path],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run TauDEM `gridnet`."""
        return HmsTauDEM._run_step(
            "gridnet",
            ["-p", p_path, "-plen", plen_path, "-tlen", tlen_path, "-gord", gord_path],
            expected_outputs={"plen": plen_path, "tlen": tlen_path, "gord": gord_path},
            **kwargs,
        )

    @staticmethod
    def _build_run_report(
        run_name: str,
        run_root: Path,
        manifest_path: Path,
        step_results: Sequence[Mapping[str, Any]],
        artifacts: Sequence[Mapping[str, Any]],
        status: str,
    ) -> Dict[str, Any]:
        """Build a compact TauDEM run report."""
        failed_steps = [step["step"] for step in step_results if step.get("status") != "completed"]
        completed_steps = [step["step"] for step in step_results if step.get("status") == "completed"]
        return {
            "study_type": "taudem_run",
            "run_name": run_name,
            "generated_at": HmsTauDEM._utc_now(),
            "run_root": str(run_root),
            "status": status,
            "step_count": len(step_results),
            "completed_step_count": len(completed_steps),
            "failed_step_count": len(failed_steps),
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "last_completed_step": completed_steps[-1] if completed_steps else None,
            "artifacts": HmsTauDEM._artifact_rows(artifacts),
            "manifest_path": str(manifest_path),
        }

    @staticmethod
    @log_call
    def run_standard_delineation(
        workspace_root: Union[str, Path],
        dem_path: Union[str, Path],
        outlet_path: Union[str, Path],
        threshold_value: Union[int, float],
        *,
        run_name: str = "standard",
        include_gridnet: bool = False,
        max_move_distance: Optional[Union[int, float]] = None,
        search_paths: Optional[Sequence[Union[str, Path]]] = None,
        timeout: int = DEFAULT_EXECUTION_TIMEOUT,
        mpi_processes: Optional[int] = None,
        mpiexec_path: Optional[Union[str, Path]] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> Dict[str, Any]:
        """Run the standard TauDEM delineation sequence against prepared inputs."""
        dem_path = Path(dem_path)
        outlet_path = Path(outlet_path)
        workspace = HmsTauDEM.create_workspace(workspace_root, run_name=run_name)
        run_root = workspace["run_root"]
        output_paths = HmsTauDEM._standard_output_paths(run_root, outlet_path)
        manifest_path = output_paths["command_manifest"]
        report_path = output_paths["run_report"]

        required_tools = list(HmsTauDEM.STANDARD_STEP_ORDER)
        if include_gridnet:
            required_tools.append("gridnet")
        environment = HmsTauDEM.validate_environment(
            required_tools=required_tools,
            search_paths=search_paths,
            mpi_processes=mpi_processes,
        )

        step_results: List[Dict[str, Any]] = []
        status = "running"

        def persist() -> Tuple[Dict[str, Any], Dict[str, Any]]:
            artifacts = HmsTauDEM._artifact_catalog(output_paths, include_gridnet=include_gridnet)
            manifest = {
                "schema_version": "1.0",
                "study_type": "taudem_run",
                "run_name": run_name,
                "generated_at": HmsTauDEM._utc_now(),
                "builder": {
                    "package": "hms-commander",
                    "class": "HmsTauDEM",
                    "method": "run_standard_delineation",
                    "version": PACKAGE_VERSION,
                },
                "workspace_root": str(Path(workspace_root)),
                "run_root": str(run_root),
                "inputs": {
                    "dem_path": str(dem_path),
                    "outlet_path": str(outlet_path),
                    "threshold": threshold_value,
                    "include_gridnet": include_gridnet,
                    "max_move_distance": max_move_distance,
                },
                "environment": environment,
                "status": status,
                "steps": step_results,
                "artifacts": artifacts,
            }
            HmsTauDEM._write_json(manifest_path, manifest)
            report = HmsTauDEM._build_run_report(
                run_name=run_name,
                run_root=run_root,
                manifest_path=manifest_path,
                step_results=step_results,
                artifacts=artifacts,
                status=status,
            )
            HmsTauDEM._write_json(report_path, report)
            return manifest, report

        manifest, report = persist()
        if not environment["available"]:
            status = "failed"
            failure_step = {
                "step": "environment_validation",
                "tool": "environment_validation",
                "status": "failed",
                "started_at": HmsTauDEM._utc_now(),
                "finished_at": HmsTauDEM._utc_now(),
                "duration_seconds": 0.0,
                "exit_code": None,
                "command": [],
                "stdout_log": None,
                "stderr_log": None,
                "outputs": {},
                "missing_outputs": list(environment["missing_tools"]),
                "error": "Missing required TauDEM tools.",
            }
            step_results.append(failure_step)
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        common_kwargs = {
            "run_root": run_root,
            "search_paths": search_paths,
            "timeout": timeout,
            "mpi_processes": mpi_processes,
            "mpiexec_path": mpiexec_path,
            "env": env,
        }

        step_results.append(HmsTauDEM.pitremove(dem_path, output_paths["fel"], **common_kwargs))
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        step_results.append(
            HmsTauDEM.d8flowdir(output_paths["fel"], output_paths["p"], output_paths["sd8"], **common_kwargs)
        )
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        step_results.append(HmsTauDEM.aread8(output_paths["p"], output_paths["ad8"], **common_kwargs))
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        step_results.append(
            HmsTauDEM.threshold(output_paths["ad8"], output_paths["src"], threshold_value, **common_kwargs)
        )
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        step_results.append(
            HmsTauDEM.moveoutletstostrm(
                output_paths["p"],
                output_paths["src"],
                outlet_path,
                output_paths["outlet_snapped"],
                max_distance=max_move_distance,
                **common_kwargs,
            )
        )
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        step_results.append(
            HmsTauDEM.streamnet(
                output_paths["fel"],
                output_paths["p"],
                output_paths["ad8"],
                output_paths["src"],
                output_paths["outlet_snapped"],
                output_paths["ord"],
                output_paths["tree"],
                output_paths["coord"],
                output_paths["net"],
                output_paths["w"],
                **common_kwargs,
            )
        )
        manifest, report = persist()
        if step_results[-1]["status"] != "completed":
            status = "failed"
            manifest, report = persist()
            return {
                "status": status,
                "workspace": workspace,
                "run_root": run_root,
                "output_paths": output_paths,
                "environment": environment,
                "steps": step_results,
                "manifest": manifest,
                "report": report,
                "artifacts": manifest["artifacts"],
            }

        if include_gridnet:
            step_results.append(
                HmsTauDEM.gridnet(
                    output_paths["p"],
                    output_paths["plen"],
                    output_paths["tlen"],
                    output_paths["gord"],
                    **common_kwargs,
                )
            )
            manifest, report = persist()
            if step_results[-1]["status"] != "completed":
                status = "failed"
                manifest, report = persist()
                return {
                    "status": status,
                    "workspace": workspace,
                    "run_root": run_root,
                    "output_paths": output_paths,
                    "environment": environment,
                    "steps": step_results,
                    "manifest": manifest,
                    "report": report,
                    "artifacts": manifest["artifacts"],
                }

        status = "completed"
        manifest, report = persist()
        return {
            "status": status,
            "workspace": workspace,
            "run_root": run_root,
            "output_paths": output_paths,
            "environment": environment,
            "steps": step_results,
            "manifest": manifest,
            "report": report,
            "artifacts": manifest["artifacts"],
        }
