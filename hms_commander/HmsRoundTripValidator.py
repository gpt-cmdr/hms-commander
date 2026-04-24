"""Round-trip validation helpers for TauDEM-to-HMS imports."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

import pandas as pd

from .Decorators import log_call
from .HmsJython import HmsJython
from .HmsSqlite import HmsSqlite
from .LoggingConfig import get_logger

logger = get_logger(__name__)


class HmsRoundTripValidator:
    """Static helpers for headless HMS open-save-close validation."""

    CORE_SUFFIXES = {".hms", ".basin", ".met", ".control", ".gage", ".run", ".sqlite"}
    VOLATILE_LINE_PATTERNS = [
        r"^\s*Last Modified Date:.*$",
        r"^\s*Last Modified Time:.*$",
        r"^\s*Last Execution Date:.*$",
        r"^\s*Last Execution Time:.*$",
        r"^\s*Version:.*$",
        r"^\s*Filepath Separator:.*$",
        r"^\s*Time Zone ID:.*$",
        r"^\s*Default Description:.*$",
        r"^\s*Is Save Spatial Results:.*$",
        r"^\s*Save State Type:.*$",
    ]

    @staticmethod
    def _utc_now() -> str:
        """Return a compact UTC timestamp."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")

    @staticmethod
    def _json_default(value: Any) -> Any:
        """Serialize pathlib and pandas-like values in JSON payloads."""
        if isinstance(value, Path):
            return str(value)
        return str(value)

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
        """Write JSON with stable formatting."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, default=HmsRoundTripValidator._json_default) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _read_text_with_fallback(path: Path) -> str:
        """Read an HMS text file using common encodings."""
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Could not decode {path}")

    @staticmethod
    def _hash_bytes(data: bytes) -> str:
        """Return a SHA-256 hash."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def _iter_core_files(project_dir: Path):
        """Yield core project files, excluding validation artifacts."""
        for path in project_dir.rglob("*"):
            if not path.is_file():
                continue
            relative_parts = path.relative_to(project_dir).parts
            if relative_parts and relative_parts[0] == "_roundtrip_validation":
                continue
            if path.suffix.lower() not in HmsRoundTripValidator.CORE_SUFFIXES:
                continue
            yield path

    @staticmethod
    def _capture_project_manifest(project_dir: Union[str, Path]) -> Dict[str, Any]:
        """Capture hashes and sizes for the core project files."""
        project_dir = Path(project_dir)
        files: Dict[str, Dict[str, Any]] = {}
        for path in sorted(HmsRoundTripValidator._iter_core_files(project_dir)):
            rel = str(path.relative_to(project_dir))
            raw = path.read_bytes()
            files[rel] = {
                "size_bytes": len(raw),
                "sha256": HmsRoundTripValidator._hash_bytes(raw),
                "suffix": path.suffix.lower(),
            }
        return {
            "project_dir": str(project_dir.resolve()),
            "captured_at": HmsRoundTripValidator._utc_now(),
            "files": files,
        }

    @staticmethod
    def _copy_core_snapshot(project_dir: Union[str, Path], snapshot_dir: Union[str, Path]) -> Path:
        """Copy core project files into a snapshot directory."""
        project_dir = Path(project_dir)
        snapshot_dir = Path(snapshot_dir)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        for path in HmsRoundTripValidator._iter_core_files(project_dir):
            rel = path.relative_to(project_dir)
            dest = snapshot_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
        return snapshot_dir

    @staticmethod
    def _clone_project_tree(source_dir: Union[str, Path], clone_dir: Union[str, Path]) -> Path:
        """Clone a project into a disposable validation workspace."""
        source_dir = Path(source_dir)
        clone_dir = Path(clone_dir)
        if clone_dir.exists():
            shutil.rmtree(clone_dir)
        shutil.copytree(
            source_dir,
            clone_dir,
            ignore=shutil.ignore_patterns("_roundtrip_validation"),
        )
        return clone_dir

    @staticmethod
    def _read_project_name(project_dir: Path) -> str:
        """Read the exact Project: line value required by OpenProject()."""
        hms_files = sorted(project_dir.glob("*.hms"))
        if not hms_files:
            raise FileNotFoundError(f"No .hms file found in {project_dir}")
        content = HmsRoundTripValidator._read_text_with_fallback(hms_files[0])
        match = re.search(r"^Project:\s*(.+?)\s*$", content, flags=re.MULTILINE)
        if not match:
            raise ValueError(f"Could not find Project: line in {hms_files[0].name}")
        return match.group(1).strip()

    @staticmethod
    def _read_project_version(project_dir: Path) -> Optional[str]:
        """Read the project version from the .hms header."""
        hms_files = sorted(project_dir.glob("*.hms"))
        if not hms_files:
            return None
        content = HmsRoundTripValidator._read_text_with_fallback(hms_files[0])
        project_block_match = re.search(r"Project:.*?^End:\s*$", content, flags=re.MULTILINE | re.DOTALL)
        if not project_block_match:
            return None
        match = re.search(r"^\s*Version:\s*(.+?)\s*$", project_block_match.group(0), flags=re.MULTILINE)
        if not match:
            return None
        return match.group(1).strip()

    @staticmethod
    def _resolve_hms_executable(project_dir: Path, hms_exe_path: Optional[Union[str, Path]] = None) -> Path:
        """Resolve the HEC-HMS installation directory for validation."""
        if hms_exe_path is not None:
            resolved = Path(hms_exe_path)
            if not resolved.exists():
                raise FileNotFoundError(f"HMS executable path not found: {resolved}")
            return resolved

        version = HmsRoundTripValidator._read_project_version(project_dir)
        discovered = HmsJython.find_hms_executable(version=version)
        if discovered is None:
            raise FileNotFoundError(
                f"Could not find a local HEC-HMS installation for version {version or 'unknown'}"
            )
        return discovered

    @staticmethod
    def _build_open_save_close_script(project_name: str, project_dir: Path) -> str:
        """Generate a minimal headless Jython script that only opens and saves."""
        project_dir_text = str(project_dir.resolve())
        lines = [
            HmsJython.SCRIPT_HEADER.format(timestamp=HmsRoundTripValidator._utc_now()),
            f"project = JythonHms.OpenProject({project_name!r}, {project_dir_text!r})",
            "JythonHms.SaveAllProjectComponents()",
            HmsJython.SCRIPT_FOOTER,
        ]
        return "\n".join(lines)

    @staticmethod
    def _normalize_text_content(content: str, suffix: Optional[str] = None) -> str:
        """Strip volatile HMS-owned lines and normalize whitespace."""
        if suffix == ".gage":
            manager_match = re.search(r"(Gage Manager:.*?End:\s*)", content, flags=re.MULTILINE | re.DOTALL)
            gage_blocks = re.findall(r"(Gage:.*?End:\s*)", content, flags=re.MULTILINE | re.DOTALL)
            if manager_match and gage_blocks:
                gage_blocks = sorted(
                    gage_blocks,
                    key=lambda block: re.search(r"^Gage:\s*(.+?)\s*$", block, flags=re.MULTILINE).group(1).strip(),
                )
                content = manager_match.group(1).rstrip() + "\n\n" + "\n\n".join(
                    block.rstrip() for block in gage_blocks
                )

        normalized_lines = []
        for raw_line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw_line.rstrip()
            if any(re.match(pattern, line) for pattern in HmsRoundTripValidator.VOLATILE_LINE_PATTERNS):
                continue
            normalized_lines.append(line)

        collapsed_lines = []
        previous_blank = False
        for line in normalized_lines:
            is_blank = line == ""
            if is_blank and previous_blank:
                continue
            collapsed_lines.append(line)
            previous_blank = is_blank

        return "\n".join(collapsed_lines).strip() + "\n"

    @staticmethod
    def _summarize_sqlite(sqlite_path: Path) -> Dict[str, Any]:
        """Create a semantic summary of an HMS SQLite geometry package."""
        layer_info = HmsSqlite.list_layers(sqlite_path)
        layer_info = layer_info.sort_values("table_name").reset_index(drop=True)

        summary: Dict[str, Any] = {
            "crs_wkt": HmsSqlite.get_crs(sqlite_path),
            "layers": [],
        }
        for row in layer_info.itertuples(index=False):
            layer_summary: Dict[str, Any] = {
                "table_name": row.table_name,
                "row_count": int(row.row_count),
                "geometry_type": row.geometry_type,
                "srid": int(row.srid) if row.srid is not None else None,
            }
            if row.row_count > 0:
                gdf = HmsSqlite._read_layer(sqlite_path, row.table_name)
                sort_columns = [column for column in ("name", "ogc_fid") if column in gdf.columns]
                if sort_columns:
                    gdf = gdf.sort_values(sort_columns).reset_index(drop=True)
                features = []
                for _, feature_row in gdf.iterrows():
                    attrs: Dict[str, Any] = {}
                    for column in gdf.columns:
                        if column == "geometry":
                            continue
                        value = feature_row[column]
                        if pd.isna(value):
                            attrs[column] = None
                        elif hasattr(value, "item"):
                            attrs[column] = value.item()
                        else:
                            attrs[column] = value
                    features.append(
                        {
                            "attrs": attrs,
                            "geometry_wkb_hex": feature_row.geometry.wkb_hex,
                        }
                    )
                layer_summary["columns"] = [column for column in gdf.columns if column != "geometry"]
                layer_summary["feature_hash"] = HmsRoundTripValidator._hash_bytes(
                    json.dumps(features, sort_keys=True, default=str).encode("utf-8")
                )
            summary["layers"].append(layer_summary)
        summary["semantic_hash"] = HmsRoundTripValidator._hash_bytes(
            json.dumps(summary["layers"], sort_keys=True, default=str).encode("utf-8")
        )
        return summary

    @staticmethod
    @log_call
    def normalize_project_diff(
        before_dir: Union[str, Path],
        after_dir: Union[str, Path],
    ) -> Dict[str, Any]:
        """Compare two project snapshots while stripping volatile HMS rewrite noise."""
        before_dir = Path(before_dir)
        after_dir = Path(after_dir)

        before_files = {
            str(path.relative_to(before_dir)): path
            for path in before_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in HmsRoundTripValidator.CORE_SUFFIXES
        }
        after_files = {
            str(path.relative_to(after_dir)): path
            for path in after_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in HmsRoundTripValidator.CORE_SUFFIXES
        }

        relative_paths = sorted(set(before_files) | set(after_files))
        file_reports: Dict[str, Dict[str, Any]] = {}
        for relative_path in relative_paths:
            before_path = before_files.get(relative_path)
            after_path = after_files.get(relative_path)

            if before_path is None:
                file_reports[relative_path] = {"status": "added", "suffix": after_path.suffix.lower()}
                continue
            if after_path is None:
                file_reports[relative_path] = {"status": "removed", "suffix": before_path.suffix.lower()}
                continue

            raw_before = before_path.read_bytes()
            raw_after = after_path.read_bytes()
            raw_equal = raw_before == raw_after
            suffix = before_path.suffix.lower()

            report: Dict[str, Any] = {
                "status": "unchanged" if raw_equal else "changed",
                "suffix": suffix,
                "raw_equal": raw_equal,
                "before_size_bytes": len(raw_before),
                "after_size_bytes": len(raw_after),
                "before_sha256": HmsRoundTripValidator._hash_bytes(raw_before),
                "after_sha256": HmsRoundTripValidator._hash_bytes(raw_after),
            }

            if suffix == ".sqlite":
                before_summary = HmsRoundTripValidator._summarize_sqlite(before_path)
                after_summary = HmsRoundTripValidator._summarize_sqlite(after_path)
                semantic_equal = before_summary["semantic_hash"] == after_summary["semantic_hash"]
                report.update(
                    {
                        "normalized_equal": semantic_equal,
                        "before_semantic_hash": before_summary["semantic_hash"],
                        "after_semantic_hash": after_summary["semantic_hash"],
                        "before_summary": before_summary,
                        "after_summary": after_summary,
                    }
                )
            else:
                normalized_before = HmsRoundTripValidator._normalize_text_content(
                    HmsRoundTripValidator._read_text_with_fallback(before_path),
                    suffix=suffix,
                )
                normalized_after = HmsRoundTripValidator._normalize_text_content(
                    HmsRoundTripValidator._read_text_with_fallback(after_path),
                    suffix=suffix,
                )
                normalized_equal = normalized_before == normalized_after
                report.update(
                    {
                        "normalized_equal": normalized_equal,
                        "before_normalized_hash": HmsRoundTripValidator._hash_bytes(
                            normalized_before.encode("utf-8")
                        ),
                        "after_normalized_hash": HmsRoundTripValidator._hash_bytes(
                            normalized_after.encode("utf-8")
                        ),
                    }
                )

            file_reports[relative_path] = report

        return {
            "before_dir": str(before_dir.resolve()),
            "after_dir": str(after_dir.resolve()),
            "generated_at": HmsRoundTripValidator._utc_now(),
            "files": file_reports,
        }

    @staticmethod
    @log_call
    def classify_roundtrip_changes(diff_report: Mapping[str, Any]) -> Dict[str, Any]:
        """Classify normalized project diffs into accepted vs unclassified changes."""
        accepted_changes = []
        unclassified_changes = []

        for relative_path, report in diff_report.get("files", {}).items():
            status = report.get("status")
            if status in {"added", "removed"}:
                unclassified_changes.append(
                    {"path": relative_path, "reason": f"File was {status}", "report": report}
                )
                continue

            if report.get("raw_equal"):
                continue

            if report.get("normalized_equal"):
                accepted_changes.append(
                    {"path": relative_path, "reason": "Raw rewrite normalized away", "report": report}
                )
            else:
                unclassified_changes.append(
                    {
                        "path": relative_path,
                        "reason": "Normalized content changed",
                        "report": report,
                    }
                )

        return {
            "generated_at": HmsRoundTripValidator._utc_now(),
            "accepted_changes": accepted_changes,
            "unclassified_changes": unclassified_changes,
            "passed": len(unclassified_changes) == 0,
        }

    @staticmethod
    @log_call
    def roundtrip_open_save_close(
        project_dir: Union[str, Path],
        hms_exe_path: Optional[Union[str, Path]] = None,
        gui_smoke: bool = False,
    ) -> Dict[str, Any]:
        """Run a headless HMS open-save-close loop and capture durable artifacts."""
        source_project_dir = Path(project_dir).resolve()
        if not source_project_dir.is_dir():
            raise FileNotFoundError(f"Project directory not found: {source_project_dir}")
        if gui_smoke:
            raise NotImplementedError("gui_smoke validation is not implemented yet")

        hms_install_path = HmsRoundTripValidator._resolve_hms_executable(source_project_dir, hms_exe_path)
        artifact_dir = source_project_dir / "_roundtrip_validation" / HmsRoundTripValidator._utc_now()
        before_snapshot = artifact_dir / "before_snapshot"
        after_snapshot = artifact_dir / "after_snapshot"
        validation_project_dir = artifact_dir / "validation_project"
        artifact_dir.mkdir(parents=True, exist_ok=True)
        HmsRoundTripValidator._clone_project_tree(source_project_dir, validation_project_dir)

        project_name = HmsRoundTripValidator._read_project_name(validation_project_dir)
        before_manifest = HmsRoundTripValidator._capture_project_manifest(validation_project_dir)
        HmsRoundTripValidator._write_json(artifact_dir / "before_manifest.json", before_manifest)
        HmsRoundTripValidator._copy_core_snapshot(validation_project_dir, before_snapshot)

        requested_script_path = artifact_dir / "requested_hms_script.py"
        script_content = HmsRoundTripValidator._build_open_save_close_script(project_name, validation_project_dir)
        requested_script_path.write_text(script_content, encoding="utf-8")

        execution_error = None
        try:
            success, stdout, stderr = HmsJython.execute_script(
                script_content=script_content,
                hms_exe_path=hms_install_path,
                working_dir=artifact_dir,
            )
        except Exception as exc:  # pragma: no cover - exercised only with live HMS failures
            success = False
            stdout = ""
            stderr = str(exc)
            execution_error = {
                "type": type(exc).__name__,
                "message": str(exc),
            }

        (artifact_dir / "stdout.txt").write_text(stdout, encoding="utf-8", errors="replace")
        (artifact_dir / "stderr.txt").write_text(stderr, encoding="utf-8", errors="replace")

        after_manifest = HmsRoundTripValidator._capture_project_manifest(validation_project_dir)
        HmsRoundTripValidator._write_json(artifact_dir / "after_manifest.json", after_manifest)
        HmsRoundTripValidator._copy_core_snapshot(validation_project_dir, after_snapshot)

        diff_report = HmsRoundTripValidator.normalize_project_diff(before_snapshot, after_snapshot)
        classification = HmsRoundTripValidator.classify_roundtrip_changes(diff_report)
        HmsRoundTripValidator._write_json(artifact_dir / "normalized_diff.json", diff_report)
        HmsRoundTripValidator._write_json(artifact_dir / "change_classification.json", classification)

        result = {
            "project_dir": str(source_project_dir),
            "project_name": project_name,
            "validation_project_dir": str(validation_project_dir.resolve()),
            "hms_install_path": str(Path(hms_install_path).resolve()),
            "artifact_dir": str(artifact_dir.resolve()),
            "before_snapshot": str(before_snapshot.resolve()),
            "after_snapshot": str(after_snapshot.resolve()),
            "headless_success": success,
            "normalized_passed": classification["passed"],
            "passed": bool(success and classification["passed"]),
            "execution_error": execution_error,
            "gui_smoke": {
                "requested": False,
                "status": "not_requested",
            },
            "stdout_path": str((artifact_dir / "stdout.txt").resolve()),
            "stderr_path": str((artifact_dir / "stderr.txt").resolve()),
            "script_path": str(requested_script_path.resolve()),
            "diff_path": str((artifact_dir / "normalized_diff.json").resolve()),
            "classification_path": str((artifact_dir / "change_classification.json").resolve()),
        }
        HmsRoundTripValidator._write_json(artifact_dir / "roundtrip_result.json", result)
        return result
