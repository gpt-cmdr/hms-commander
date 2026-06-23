"""Small data models for HMS GUI control."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Rect:
    """Screen rectangle reported by Java Access Bridge."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        """Return the integer center point."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    def to_dict(self) -> Dict[str, int]:
        """Return a JSON-serializable rectangle."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class AccessibleNode:
    """A snapshot of one Java accessible node."""

    name: str
    role: str
    states: Tuple[str, ...] = field(default_factory=tuple)
    description: str = ""
    rect: Rect = field(default_factory=lambda: Rect(0, 0, 0, 0))
    index_in_parent: int = -1
    children_count: int = 0
    has_action: bool = False
    has_selection: bool = False
    has_text: bool = False
    vm_id: Optional[int] = None
    context: Optional[int] = None
    hwnd: Optional[int] = None

    @property
    def enabled(self) -> bool:
        """Return True if the node reports the enabled state."""
        return self.has_state("enabled")

    @property
    def visible(self) -> bool:
        """Return True if the node reports the visible state."""
        return self.has_state("visible")

    def has_state(self, state: str) -> bool:
        """Return True if a state is present, case-insensitively."""
        return state.lower() in {item.lower() for item in self.states}

    def to_dict(self, include_handles: bool = False) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        data: Dict[str, Any] = {
            "name": self.name,
            "role": self.role,
            "states": list(self.states),
            "description": self.description,
            "rect": self.rect.to_dict(),
            "index_in_parent": self.index_in_parent,
            "children_count": self.children_count,
            "has_action": self.has_action,
            "has_selection": self.has_selection,
            "has_text": self.has_text,
        }
        if include_handles:
            data.update({"vm_id": self.vm_id, "context": self.context, "hwnd": self.hwnd})
        return data


@dataclass(frozen=True)
class WindowInfo:
    """Visible top-level window owned by the HMS Java process."""

    hwnd: int
    title: str
    process_id: int

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "process_id": self.process_id,
        }


@dataclass(frozen=True)
class ActionResult:
    """Result from a direct JAB action invocation."""

    target_name: str
    action_name: str
    ok: bool
    first_failure: int
    node: AccessibleNode
    available_actions: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "target_name": self.target_name,
            "action_name": self.action_name,
            "ok": self.ok,
            "first_failure": self.first_failure,
            "node": self.node.to_dict(),
            "available_actions": list(self.available_actions),
        }


@dataclass(frozen=True)
class GuiActionResult:
    """Result from the safe public action wrapper."""

    target_name: str
    action_name: str
    completed: bool
    timed_out: bool = False
    returncode: Optional[int] = None
    dialogs: Tuple[WindowInfo, ...] = field(default_factory=tuple)
    stdout: str = ""
    stderr: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable representation."""
        return {
            "target_name": self.target_name,
            "action_name": self.action_name,
            "completed": self.completed,
            "timed_out": self.timed_out,
            "returncode": self.returncode,
            "dialogs": [dialog.to_dict() for dialog in self.dialogs],
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def parse_states(states: str) -> Tuple[str, ...]:
    """Parse a JAB state string into a normalized tuple."""
    return tuple(part.strip() for part in states.split(",") if part.strip())
