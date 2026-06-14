"""Private helpers for HMS project-file component registration.

The public API stays on the existing static classes. This module centralizes
the real ``.hms`` registry block behavior so clone workflows and builders do
not each maintain their own project-file writer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional, Union

from .LoggingConfig import get_logger
from ._parsing import HmsFileParser

logger = get_logger(__name__)


@dataclass(frozen=True)
class ProjectComponentSpec:
    """Canonical HMS project component metadata."""

    block_type: str
    extension: str
    filename_key: str
    legacy_line_types: tuple[str, ...]


_COMPONENT_SPECS: Mapping[str, ProjectComponentSpec] = {
    "basin": ProjectComponentSpec("Basin", "basin", "Filename", ("Basin",)),
    "meteorology": ProjectComponentSpec(
        "Met",
        "met",
        "Filename",
        ("Met", "Meteorology", "Precipitation"),
    ),
    "met": ProjectComponentSpec(
        "Met",
        "met",
        "Filename",
        ("Met", "Meteorology", "Precipitation"),
    ),
    "precipitation": ProjectComponentSpec(
        "Met",
        "met",
        "Filename",
        ("Met", "Meteorology", "Precipitation"),
    ),
    "control": ProjectComponentSpec("Control", "control", "Filename", ("Control",)),
}

_PROJECT_BLOCK_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9 ]*:\s*.*?\n.*?^End:\s*$)",
    flags=re.MULTILINE | re.DOTALL,
)


def normalize_component_type(entry_type: str) -> ProjectComponentSpec:
    """Return the canonical registry spec for a public entry-type alias."""

    normalized = re.sub(r"[\s_\-]+", " ", str(entry_type).strip().lower())
    normalized = normalized.replace(" ", "")
    if normalized not in _COMPONENT_SPECS:
        raise ValueError(f"Unsupported project registry entry type: {entry_type!r}")
    return _COMPONENT_SPECS[normalized]


def read_project_text(hms_path: Union[str, Path]) -> str:
    """Read an HMS project file using the shared encoding fallback."""

    return HmsFileParser.read_file(hms_path)


def write_project_text(hms_path: Union[str, Path], content: str) -> Path:
    """Write HMS project text as UTF-8 and return the path."""

    hms_path = Path(hms_path)
    HmsFileParser.write_file(hms_path, content)
    return hms_path


def _local_hms_timestamp() -> Dict[str, str]:
    """Return HMS-style local date/time strings."""

    now = datetime.now()
    return {
        "date": f"{now.day} {now.strftime('%B %Y')}",
        "time": now.strftime("%H:%M:%S"),
    }


def _filename_for(logical_name: str, extension: str, filename: Optional[str] = None) -> str:
    """Return an HMS component filename, adding the extension when omitted."""

    if filename:
        return filename
    return f"{logical_name}.{extension}"


def build_project_registry_block(
    block_type: str,
    logical_name: str,
    filename: str,
    description: str = "",
) -> str:
    """Build a canonical HMS ``.hms`` registry block."""

    try:
        spec = normalize_component_type(block_type)
        block_type = spec.block_type
        filename_key = spec.filename_key
    except ValueError:
        block_type = str(block_type).strip()
        filename_key = "Filename"

    timestamp = _local_hms_timestamp()

    lines = [
        f"{block_type}: {logical_name}",
        f"     {filename_key}: {filename}",
        f"     Description: {description}",
    ]
    if block_type != "Control":
        lines.extend(
            [
                f"     Last Modified Date: {timestamp['date']}",
                f"     Last Modified Time: {timestamp['time']}",
            ]
        )
    lines.extend(["End:", ""])
    return "\n".join(lines)


def build_project_registry_block_for_entry(
    entry_type: str,
    logical_name: str,
    filename: Optional[str] = None,
    description: str = "",
) -> str:
    """Build a registry block from a public entry-type alias."""

    spec = normalize_component_type(entry_type)
    return build_project_registry_block(
        block_type=spec.block_type,
        logical_name=logical_name,
        filename=_filename_for(logical_name, spec.extension, filename),
        description=description,
    )


def iter_project_blocks(content: str) -> Iterator[tuple[re.Match[str], str, str, Dict[str, str]]]:
    """Yield HMS project blocks as match, block type, name, and attributes."""

    for match in _PROJECT_BLOCK_PATTERN.finditer(content):
        block_text = match.group(1)
        lines = block_text.splitlines()
        if not lines or ":" not in lines[0]:
            continue
        block_type, block_name = lines[0].split(":", 1)
        attrs: Dict[str, str] = {}
        for line in lines[1:]:
            stripped = line.strip()
            if stripped == "End:":
                break
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            attrs[key.strip()] = value.strip()
        yield match, block_type.strip(), block_name.strip(), attrs


def _block_type_aliases(spec: ProjectComponentSpec) -> set[str]:
    """Return lower-case block headers that are equivalent for a component."""

    return {
        spec.block_type.lower(),
        *(alias.lower() for alias in spec.legacy_line_types),
    }


def component_is_registered(
    content: str,
    spec: ProjectComponentSpec,
    logical_name: str,
) -> bool:
    """Return True when the project already has the requested component block."""

    block_type_aliases = _block_type_aliases(spec)
    for _, candidate_type, candidate_name, _ in iter_project_blocks(content):
        if (
            candidate_type.lower() in block_type_aliases
            and candidate_name.lower() == str(logical_name).strip().lower()
        ):
            return True
    return False


def legacy_component_is_registered(
    content: str,
    spec: ProjectComponentSpec,
    filename: str,
) -> bool:
    """Return True when a legacy flat ``* File:`` entry already registers a file."""

    for line_type in spec.legacy_line_types:
        pattern = rf"^\s*{re.escape(line_type)}\s+File:\s*{re.escape(filename)}\s*$"
        if re.search(pattern, content, flags=re.MULTILINE | re.IGNORECASE):
            return True
    return False


def _find_insert_position(content: str, spec: ProjectComponentSpec) -> int:
    """Find a stable insertion point outside the ``Project`` block."""

    matches = list(iter_project_blocks(content))
    block_type_aliases = _block_type_aliases(spec)
    same_type_matches = [
        match for match, candidate_type, _, _ in matches
        if candidate_type.lower() in block_type_aliases
    ]
    if same_type_matches:
        return same_type_matches[-1].end()

    project_matches = [
        match for match, candidate_type, _, _ in matches
        if candidate_type.lower() == "project"
    ]
    if project_matches:
        return project_matches[-1].end()

    return len(content)


def _insert_block(content: str, insert_pos: int, block_text: str) -> str:
    """Insert a registry block while preserving surrounding file text."""

    prefix = content[:insert_pos].rstrip()
    suffix = content[insert_pos:].lstrip("\n")
    new_content = f"{prefix}\n\n{block_text}"
    if suffix:
        new_content += f"\n{suffix}"
    else:
        new_content += "\n"
    return new_content


def register_project_block(
    hms_path: Union[str, Path],
    entry_type: str,
    logical_name: str,
    filename: Optional[str] = None,
    description: str = "",
    allow_existing: bool = False,
) -> Path:
    """Register a Basin/Met/Control block in a project file."""

    hms_path = Path(hms_path)
    if not hms_path.exists():
        raise FileNotFoundError(f"HMS project file not found: {hms_path}")

    spec = normalize_component_type(entry_type)
    content = read_project_text(hms_path)
    resolved_filename = _filename_for(logical_name, spec.extension, filename)
    if component_is_registered(
        content,
        spec,
        logical_name,
    ) or legacy_component_is_registered(content, spec, resolved_filename):
        if allow_existing:
            logger.info("%s '%s' already registered in %s", spec.block_type, logical_name, hms_path.name)
            return hms_path
        raise ValueError(f"{spec.block_type} '{logical_name}' is already registered in {hms_path.name}")

    block_text = build_project_registry_block(
        block_type=spec.block_type,
        logical_name=logical_name,
        filename=resolved_filename,
        description=description,
    )
    insert_pos = _find_insert_position(content, spec)
    write_project_text(hms_path, _insert_block(content, insert_pos, block_text))
    return hms_path


def rewrite_project_block(
    hms_path: Union[str, Path],
    entry_type: str,
    logical_name: str,
    filename: Optional[str] = None,
    description: str = "",
) -> Path:
    """Rewrite an existing Basin/Met/Control block in a project file."""

    hms_path = Path(hms_path)
    if not hms_path.exists():
        raise FileNotFoundError(f"HMS project file not found: {hms_path}")

    spec = normalize_component_type(entry_type)
    resolved_filename = _filename_for(logical_name, spec.extension, filename)
    replacement = build_project_registry_block(
        block_type=spec.block_type,
        logical_name=logical_name,
        filename=resolved_filename,
        description=description,
    ).rstrip()

    content = read_project_text(hms_path)
    block_type_aliases = _block_type_aliases(spec)
    for match, candidate_type, candidate_name, _ in iter_project_blocks(content):
        if (
            candidate_type.lower() in block_type_aliases
            and candidate_name.lower() == str(logical_name).strip().lower()
        ):
            new_content = content[:match.start()] + replacement + content[match.end():]
            if not new_content.endswith("\n"):
                new_content += "\n"
            write_project_text(hms_path, new_content)
            return hms_path

    raise ValueError(f"{spec.block_type} '{logical_name}' is not registered in {hms_path.name}")


def parse_project_components(content: str) -> Dict[str, list[Dict[str, Any]]]:
    """Parse project blocks into the structure used by ``HmsPrj``."""

    blocks: Dict[str, list[Dict[str, Any]]] = {}
    for _, block_type, block_name, attrs in iter_project_blocks(content):
        blocks.setdefault(block_type, []).append({"name": block_name, **attrs})
    return blocks
