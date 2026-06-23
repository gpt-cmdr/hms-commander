"""Win32 helpers for finding and closing HMS windows."""

from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from .errors import HmsGuiUnavailableError

WM_CLOSE = 0x0010
WM_SYSCOMMAND = 0x0112
SC_CLOSE = 0xF060
SW_RESTORE = 9


@dataclass(frozen=True)
class WindowInfo:
    """Visible top-level window metadata."""

    hwnd: int
    title: str
    process_id: int

    def to_dict(self) -> dict[str, int | str]:
        """Return a JSON-serializable representation."""
        return {
            "hwnd": self.hwnd,
            "title": self.title,
            "process_id": self.process_id,
        }


class RECT(ctypes.Structure):
    """Win32 RECT."""

    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def ensure_windows() -> None:
    """Raise when Win32 GUI APIs are unavailable."""
    if os.name != "nt":
        raise HmsGuiUnavailableError("HMS GUI window helpers require Windows.")


class Win32Windows:
    """Small wrapper for the Win32 window APIs used by HMS helpers."""

    def __init__(self) -> None:
        ensure_windows()
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._bind()

    def _bind(self) -> None:
        self._enum_proc = ctypes.WINFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self.user32.EnumWindows.argtypes = [self._enum_proc, ctypes.c_void_p]
        self.user32.EnumWindows.restype = ctypes.c_bool
        self.user32.GetWindowThreadProcessId.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint),
        ]
        self.user32.GetWindowThreadProcessId.restype = ctypes.c_uint
        self.user32.GetWindowTextW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_wchar_p,
            ctypes.c_int,
        ]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.IsWindowVisible.argtypes = [ctypes.c_void_p]
        self.user32.IsWindowVisible.restype = ctypes.c_bool
        self.user32.PostMessageW.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.user32.PostMessageW.restype = ctypes.c_bool
        self.user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
        self.user32.GetWindowRect.restype = ctypes.c_bool
        self.user32.ShowWindowAsync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.user32.ShowWindowAsync.restype = ctypes.c_bool

    def visible_windows(self, process_id: Optional[int] = None) -> List[WindowInfo]:
        """Return visible top-level windows, optionally filtered by PID."""
        windows: List[WindowInfo] = []

        def callback(hwnd, _lparam):
            pid = ctypes.c_uint()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if process_id is not None and int(pid.value) != int(process_id):
                return True
            if not self.user32.IsWindowVisible(hwnd):
                return True
            title_buf = ctypes.create_unicode_buffer(512)
            self.user32.GetWindowTextW(hwnd, title_buf, 512)
            title = title_buf.value
            if title:
                windows.append(WindowInfo(int(hwnd), title, int(pid.value)))
            return True

        self.user32.EnumWindows(self._enum_proc(callback), None)
        return windows

    def find_hms_windows(self, title_contains: str = "HEC-HMS") -> List[WindowInfo]:
        """Find visible HMS top-level windows by title text."""
        needle = title_contains.lower()
        return [
            window
            for window in self.visible_windows()
            if needle in window.title.lower()
        ]

    def find_main_hms_window(self, title_contains: str = "HEC-HMS") -> WindowInfo:
        """Return the first visible HMS main window."""
        windows = self.find_hms_windows(title_contains=title_contains)
        if not windows:
            raise HmsGuiUnavailableError("No visible HEC-HMS window found.")
        preferred = [window for window in windows if window.title.startswith("HEC-HMS")]
        return (preferred or windows)[0]

    def windows_for_process(self, process_id: int) -> List[WindowInfo]:
        """Return visible top-level windows for a process."""
        return self.visible_windows(process_id=process_id)

    def process_id_for_window(self, hwnd: int) -> int:
        """Return the owning process id for a window."""
        pid = ctypes.c_uint()
        self.user32.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
        return int(pid.value)

    def new_windows(
        self,
        process_id: int,
        existing_hwnds: Iterable[int],
    ) -> List[WindowInfo]:
        """Return process windows not present in an existing HWND collection."""
        existing = {int(hwnd) for hwnd in existing_hwnds}
        return [
            window
            for window in self.windows_for_process(process_id)
            if window.hwnd not in existing
        ]

    def post_close(self, hwnd: int, system_close: bool = True) -> bool:
        """Post a close message to a window."""
        if system_close:
            return bool(
                self.user32.PostMessageW(
                    ctypes.c_void_p(hwnd),
                    WM_SYSCOMMAND,
                    ctypes.c_void_p(SC_CLOSE),
                    None,
                )
            )
        return bool(self.user32.PostMessageW(ctypes.c_void_p(hwnd), WM_CLOSE, None, None))

    def restore_window(self, hwnd: int) -> bool:
        """Restore a minimized top-level window."""
        return bool(self.user32.ShowWindowAsync(ctypes.c_void_p(hwnd), SW_RESTORE))

    def close_windows(
        self,
        windows: Sequence[WindowInfo],
        wait_seconds: float = 0.35,
    ) -> int:
        """Close windows with SC_CLOSE and then WM_CLOSE fallback."""
        closed = 0
        for window in windows:
            self.post_close(window.hwnd, system_close=True)
            time.sleep(wait_seconds)
            still_open = {
                item.hwnd for item in self.windows_for_process(window.process_id)
            }
            if window.hwnd not in still_open:
                closed += 1
                continue
            self.post_close(window.hwnd, system_close=False)
            time.sleep(wait_seconds)
            still_open = {
                item.hwnd for item in self.windows_for_process(window.process_id)
            }
            if window.hwnd not in still_open:
                closed += 1
        return closed

    def window_rect(self, hwnd: int) -> RECT:
        """Return a Win32 RECT for a window."""
        rect = RECT()
        if not self.user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect)):
            raise HmsGuiUnavailableError(f"Could not read window rect: {hwnd}")
        return rect
