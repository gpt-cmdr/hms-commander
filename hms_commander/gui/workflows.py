"""Deterministic HMS GUI startup helpers."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional, Union

from .errors import HmsGuiUnavailableError


@dataclass(frozen=True)
class StartupProjectSeed:
    """Result from seeding an HMS startup project state file."""

    state_file: Path
    project_file: Path
    backup_file: Optional[Path]
    original_state_existed: bool = True


def infer_hms_version(hms_path: Union[str, Path]) -> str:
    """Infer HMS version text from an installation path."""
    path = Path(hms_path)
    if path.is_file():
        return path.parent.name
    return path.name


def project_state_file(version: str) -> Path:
    """Return the HMS project-state file for a version such as ``4.13``."""
    digits = "".join(part for part in str(version) if part.isdigit())
    if not digits:
        raise ValueError(f"Cannot derive projects*.hms file from version: {version!r}")
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise HmsGuiUnavailableError("APPDATA is not set; cannot find HMS state file.")
    return Path(appdata) / "HEC" / "HEC-HMS" / f"projects{digits}.hms"


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _replace_or_insert_block(content: str, block_name: str, block: str) -> str:
    pattern = rf"(?ms)^{re.escape(block_name)}:\s.*?^End:\s*\n?"
    if re.search(pattern, content):
        return re.sub(pattern, lambda _match: block, content, count=1)

    insert_match = re.search(r"(?m)^Screen Settings:|^ProgramSettings:", content)
    if insert_match:
        return content[: insert_match.start()] + block + "\n" + content[insert_match.start() :]
    return block + "\n" + content


def _set_open_last_project(content: str) -> str:
    if re.search(r"(?m)^(\s*Open Last Project:\s*).*$", content):
        return re.sub(
            r"(?m)^(\s*Open Last Project:\s*).*$",
            r"\1Yes",
            content,
            count=1,
        )
    pattern = r"(?ms)^(ProgramSettings:\s*\n)(.*?)(^End:\s*)"
    match = re.search(pattern, content)
    if match:
        return (
            content[: match.start()]
            + match.group(1)
            + match.group(2)
            + "     Open Last Project: Yes\n"
            + match.group(3)
            + content[match.end() :]
        )
    return content + "\nProgramSettings:\n     Open Last Project: Yes\nEnd:\n"


def seed_startup_project(
    project_file: Union[str, Path],
    *,
    hms_path: Optional[Union[str, Path]] = None,
    version: Optional[str] = None,
    state_file: Optional[Union[str, Path]] = None,
    backup: bool = True,
) -> StartupProjectSeed:
    """Seed HMS ``projects*.hms`` so startup opens a project deterministically."""
    project = Path(project_file).resolve()
    if not project.exists() or project.suffix.lower() != ".hms":
        raise FileNotFoundError(f"HMS project file not found: {project}")

    if state_file is None:
        if version is None:
            if hms_path is None:
                raise ValueError("Provide hms_path or version when state_file is omitted.")
            version = infer_hms_version(hms_path)
        state = project_state_file(version)
    else:
        state = Path(state_file)

    state.parent.mkdir(parents=True, exist_ok=True)
    original_state_existed = state.exists()
    content = _read_text(state) if original_state_existed else ""
    backup_file: Optional[Path] = None
    if backup and original_state_existed:
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        backup_file = state.with_name(f"{state.name}.hmscmdr-backup-{stamp}")
        shutil.copy2(state, backup_file)

    project_block = (
        f"Project: {project.stem}\n"
        "     Description: \n"
        f"     File Name: {project}\n"
        "End:\n"
    )
    recent_block = (
        "Recent Projects:\n"
        f"     Project: {project.stem}\n"
        "     Description: \n"
        f"     File Name: {project}\n"
        "End:\n"
    )
    content = _replace_or_insert_block(content, "Project", project_block)
    content = _replace_or_insert_block(content, "Recent Projects", recent_block)
    content = _set_open_last_project(content)
    state.write_text(content, encoding="utf-8")

    return StartupProjectSeed(
        state_file=state,
        project_file=project,
        backup_file=backup_file,
        original_state_existed=original_state_existed,
    )


def restore_startup_project(seed: StartupProjectSeed) -> bool:
    """Restore an HMS ``projects*.hms`` file from a startup seed backup."""
    if seed.backup_file is None:
        if not seed.original_state_existed and seed.state_file.exists():
            seed.state_file.unlink()
            return True
        return False
    if not seed.backup_file.exists():
        raise FileNotFoundError(f"HMS startup seed backup not found: {seed.backup_file}")
    seed.state_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(seed.backup_file, seed.state_file)
    return True


@contextmanager
def startup_project_seed(
    project_file: Union[str, Path],
    *,
    hms_path: Optional[Union[str, Path]] = None,
    version: Optional[str] = None,
    state_file: Optional[Union[str, Path]] = None,
) -> Iterator[StartupProjectSeed]:
    """Temporarily seed HMS startup state and restore it on context exit."""
    seed = seed_startup_project(
        project_file,
        hms_path=hms_path,
        version=version,
        state_file=state_file,
        backup=True,
    )
    try:
        yield seed
    finally:
        restore_startup_project(seed)


def _resolve_jre_bin(hms_path: Union[str, Path]) -> Optional[Path]:
    install = Path(hms_path)
    if install.is_file():
        install = install.parent
    candidates = (
        install / "jre" / "bin",
        install / "java" / "bin",
        install,
    )
    for candidate in candidates:
        if (candidate / "jabswitch.exe").exists():
            return candidate
    return None


def launch_hms(
    *,
    hms_path: Union[str, Path],
    project_file: Optional[Union[str, Path]] = None,
    version: Optional[str] = None,
    seed_project_state: bool = True,
    wait_seconds: float = 30.0,
) -> tuple[subprocess.Popen, Optional[StartupProjectSeed]]:
    """Launch HMS, optionally seeding startup project state first."""
    install = Path(hms_path)
    exe = install if install.is_file() else install / "HEC-HMS.exe"
    if not exe.exists():
        raise FileNotFoundError(f"HEC-HMS.exe not found: {exe}")
    version = version or infer_hms_version(exe.parent)
    seed = None
    if project_file and seed_project_state:
        seed = seed_startup_project(project_file, hms_path=exe.parent, version=version)

    jre_bin = _resolve_jre_bin(exe.parent)
    if jre_bin is not None:
        subprocess.run(
            [str(jre_bin / "jabswitch.exe"), "/enable"],
            check=False,
            capture_output=True,
        )

    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    if wait_seconds:
        time.sleep(wait_seconds)
    return proc, seed
