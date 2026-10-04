"""GUI control helpers for HEC-HMS.

This package provides a Windows Java Access Bridge control layer for the
HEC-HMS Swing GUI. The public entry point is :class:`hms_commander.HmsGui`.
"""

from .controller import HmsGui
from .errors import (
    HmsGuiActionError,
    HmsGuiAttachError,
    HmsGuiError,
    HmsGuiUnavailableError,
)
from .nodes import AccessibleNode, ActionResult, GuiActionResult, Rect, WindowInfo
from .session import HmsGuiSession
from .workflows import StartupProjectSeed, restore_startup_project, startup_project_seed

__all__ = [
    "AccessibleNode",
    "ActionResult",
    "GuiActionResult",
    "HmsGui",
    "HmsGuiActionError",
    "HmsGuiAttachError",
    "HmsGuiError",
    "HmsGuiSession",
    "HmsGuiUnavailableError",
    "Rect",
    "StartupProjectSeed",
    "WindowInfo",
    "restore_startup_project",
    "startup_project_seed",
]
