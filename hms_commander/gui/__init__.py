"""Low-level GUI workflow helpers for HEC-HMS.

This package currently contains Windows startup/window utilities that do not
depend on Java Access Bridge. Higher-level GUI automation should live behind a
separate optional layer until it has broader HMS-version coverage.
"""

from .errors import (
    HmsGuiActionError,
    HmsGuiAttachError,
    HmsGuiError,
    HmsGuiUnavailableError,
)
from .windows import Win32Windows, WindowInfo, ensure_windows
from .workflows import (
    StartupProjectSeed,
    infer_hms_version,
    launch_hms,
    project_state_file,
    restore_startup_project,
    seed_startup_project,
    startup_project_seed,
)

__all__ = [
    "HmsGuiActionError",
    "HmsGuiAttachError",
    "HmsGuiError",
    "HmsGuiUnavailableError",
    "StartupProjectSeed",
    "Win32Windows",
    "WindowInfo",
    "ensure_windows",
    "infer_hms_version",
    "launch_hms",
    "project_state_file",
    "restore_startup_project",
    "seed_startup_project",
    "startup_project_seed",
]
