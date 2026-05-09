"""Java Access Bridge bindings used by HMS GUI control."""

from __future__ import annotations

import ctypes
import os
import struct
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from .errors import HmsGuiAttachError, HmsGuiUnavailableError
from .nodes import AccessibleNode, Rect, parse_states

ACTIONS_COUNT = 256
ACTION_NAME_CHARS = 256
ACTION_NAME_BYTES = ACTION_NAME_CHARS * 2
ACTIONS_BUFFER_SIZE = 4 + ACTIONS_COUNT * ACTION_NAME_BYTES

ACTIONS_TO_DO_COUNT = 32
ACTIONS_TO_DO_BUFFER_SIZE = 4 + ACTIONS_TO_DO_COUNT * ACTION_NAME_BYTES
TEXT_CHUNK_CHARS = 16000


def build_action_todo_buffer(action_name: str) -> bytes:
    """Build an AccessibleActionsToDo buffer for doAccessibleActions."""
    payload = bytearray(ACTIONS_TO_DO_BUFFER_SIZE)
    payload[0:4] = struct.pack("<i", 1)
    action_bytes = action_name.encode("utf-16-le") + b"\x00\x00"
    max_bytes = ACTION_NAME_BYTES
    if len(action_bytes) > max_bytes:
        raise ValueError(f"Action name is too long: {action_name!r}")
    payload[4 : 4 + len(action_bytes)] = action_bytes
    return bytes(payload)


def parse_actions_buffer(buffer: Union[bytes, bytearray, memoryview]) -> List[str]:
    """Parse an AccessibleActions buffer returned by getAccessibleActions."""
    raw = bytes(buffer)
    if len(raw) < 4:
        return []
    count = max(0, min(struct.unpack("<i", raw[:4])[0], ACTIONS_COUNT))
    names: List[str] = []
    for index in range(count):
        offset = 4 + index * ACTION_NAME_BYTES
        chunk = raw[offset : offset + ACTION_NAME_BYTES]
        text = chunk.decode("utf-16-le", errors="ignore").split("\x00", 1)[0]
        if text:
            names.append(text)
    return names


def resolve_jre_bin(
    hms_path: Optional[Union[str, Path]] = None,
    version: Optional[str] = None,
) -> Optional[Path]:
    """Resolve the HMS-bundled JRE/JAB directory when possible."""
    if hms_path is None:
        try:
            from hms_commander.HmsJython import HmsJython

            found = HmsJython.find_hms_executable(version=version)
        except Exception:
            found = None
        hms_path = found

    if hms_path is None:
        return None

    path = Path(hms_path)
    candidates: Sequence[Path]
    if path.name.lower() == "bin" and (path / "windowsaccessbridge-64.dll").exists():
        return path
    if path.is_file():
        install_dir = path.parent
    else:
        install_dir = path
    candidates = (
        install_dir / "jre" / "bin",
        install_dir / "java" / "bin",
        install_dir,
    )
    for candidate in candidates:
        if (candidate / "windowsaccessbridge-64.dll").exists():
            return candidate
    return None


class MSG(ctypes.Structure):
    """Win32 MSG structure used to pump the Java Access Bridge handshake."""

    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_void_p),
        ("lParam", ctypes.c_void_p),
        ("time", ctypes.c_uint),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]


class AccessibleContextInfo(ctypes.Structure):
    """JAB AccessibleContextInfo structure."""

    _fields_ = [
        ("name", ctypes.c_wchar * 1024),
        ("description", ctypes.c_wchar * 1024),
        ("role", ctypes.c_wchar * 256),
        ("role_en_US", ctypes.c_wchar * 256),
        ("states", ctypes.c_wchar * 256),
        ("states_en_US", ctypes.c_wchar * 256),
        ("indexInParent", ctypes.c_int),
        ("childrenCount", ctypes.c_int),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("accessibleComponent", ctypes.c_int),
        ("accessibleAction", ctypes.c_int),
        ("accessibleSelection", ctypes.c_int),
        ("accessibleText", ctypes.c_int),
        ("accessibleInterfaces", ctypes.c_int),
    ]


class AccessibleTextInfo(ctypes.Structure):
    """JAB AccessibleTextInfo structure."""

    _fields_ = [
        ("charCount", ctypes.c_int),
        ("caretIndex", ctypes.c_int),
        ("indexAtPoint", ctypes.c_int),
    ]


class JavaAccessBridge:
    """Thin ctypes wrapper around windowsaccessbridge-64.dll."""

    def __init__(self, jre_bin: Optional[Union[str, Path]] = None):
        if os.name != "nt":
            raise HmsGuiUnavailableError("HMS GUI control requires Windows.")

        self.jre_bin = Path(jre_bin) if jre_bin else resolve_jre_bin()
        if self.jre_bin is None:
            raise HmsGuiUnavailableError(
                "Could not find HMS windowsaccessbridge-64.dll. "
                "Pass jre_bin or hms_path from the installed HEC-HMS version."
            )
        if not (self.jre_bin / "windowsaccessbridge-64.dll").exists():
            raise HmsGuiUnavailableError(
                f"windowsaccessbridge-64.dll not found in {self.jre_bin}"
            )

        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.kernel32.SetDllDirectoryW.argtypes = [ctypes.c_wchar_p]
        self.kernel32.SetDllDirectoryW.restype = ctypes.c_bool
        if not self.kernel32.SetDllDirectoryW(str(self.jre_bin)):
            raise HmsGuiUnavailableError(f"SetDllDirectory failed: {self.jre_bin}")

        self.dll = ctypes.CDLL("windowsaccessbridge-64.dll")
        self._bind_functions()

    def _bind_functions(self) -> None:
        self.user32.PeekMessageW.argtypes = [
            ctypes.POINTER(MSG),
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        self.user32.PeekMessageW.restype = ctypes.c_bool
        self.user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
        self.user32.TranslateMessage.restype = ctypes.c_bool
        self.user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
        self.user32.DispatchMessageW.restype = ctypes.c_void_p

        self.dll.Windows_run.argtypes = []
        self.dll.Windows_run.restype = None
        self.dll.isJavaWindow.argtypes = [ctypes.c_void_p]
        self.dll.isJavaWindow.restype = ctypes.c_bool
        self.dll.getAccessibleContextFromHWND.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_longlong),
        ]
        self.dll.getAccessibleContextFromHWND.restype = ctypes.c_bool
        self.dll.getAccessibleContextInfo.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.POINTER(AccessibleContextInfo),
        ]
        self.dll.getAccessibleContextInfo.restype = ctypes.c_bool
        self.dll.getAccessibleChildFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
        ]
        self.dll.getAccessibleChildFromContext.restype = ctypes.c_longlong
        self.dll.getAccessibleParentFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
        ]
        self.dll.getAccessibleParentFromContext.restype = ctypes.c_longlong
        self.dll.releaseJavaObject.argtypes = [ctypes.c_int, ctypes.c_longlong]
        self.dll.releaseJavaObject.restype = None
        self.dll.getAccessibleActions.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_void_p,
        ]
        self.dll.getAccessibleActions.restype = ctypes.c_bool
        self.dll.doAccessibleActions.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        self.dll.doAccessibleActions.restype = ctypes.c_bool
        self.dll.requestFocus.argtypes = [ctypes.c_int, ctypes.c_longlong]
        self.dll.requestFocus.restype = ctypes.c_bool
        self.dll.clearAccessibleSelectionFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
        ]
        self.dll.clearAccessibleSelectionFromContext.restype = None
        self.dll.addAccessibleSelectionFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
        ]
        self.dll.addAccessibleSelectionFromContext.restype = None
        self.dll.getAccessibleSelectionCountFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
        ]
        self.dll.getAccessibleSelectionCountFromContext.restype = ctypes.c_int
        self.dll.getAccessibleSelectionFromContext.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
        ]
        self.dll.getAccessibleSelectionFromContext.restype = ctypes.c_longlong
        self.dll.getAccessibleTextInfo.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.POINTER(AccessibleTextInfo),
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.dll.getAccessibleTextInfo.restype = ctypes.c_bool
        self.dll.getAccessibleTextRange.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_short,
        ]
        self.dll.getAccessibleTextRange.restype = ctypes.c_bool
        self.dll.setTextContents.argtypes = [
            ctypes.c_int,
            ctypes.c_longlong,
            ctypes.c_void_p,
        ]
        self.dll.setTextContents.restype = ctypes.c_bool

    def start(self, pump_seconds: float = 2.0) -> None:
        """Start the bridge and pump the message queue briefly."""
        self.dll.Windows_run()
        self.pump_messages(pump_seconds)

    def pump_messages(self, seconds: float = 0.0, max_messages: int = 50) -> None:
        """Pump the thread message queue for bridge IPC."""
        end = time.monotonic() + max(seconds, 0.0)
        processed = 0
        msg = MSG()
        while time.monotonic() <= end or (seconds == 0.0 and processed < max_messages):
            any_message = False
            while self.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                any_message = True
                processed += 1
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
                if seconds == 0.0 and processed >= max_messages:
                    return
            if seconds == 0.0:
                return
            if not any_message:
                time.sleep(0.05)

    def attach_window(self, hwnd: int) -> Tuple[int, int]:
        """Attach to a Java window and return ``(vm_id, root_context)``."""
        handle = ctypes.c_void_p(int(hwnd))
        if not self.dll.isJavaWindow(handle):
            raise HmsGuiAttachError(f"Window is not a Java window: {hwnd}")
        vm_id = ctypes.c_int()
        root = ctypes.c_longlong()
        ok = self.dll.getAccessibleContextFromHWND(
            handle, ctypes.byref(vm_id), ctypes.byref(root)
        )
        if not ok or root.value == 0:
            raise HmsGuiAttachError(f"Could not attach to Java window: {hwnd}")
        return vm_id.value, root.value

    def is_java_window(self, hwnd: int) -> bool:
        """Return True if the window is a JAB-enabled Java window."""
        return bool(self.dll.isJavaWindow(ctypes.c_void_p(int(hwnd))))

    def get_context_info(self, vm_id: int, context: int) -> AccessibleContextInfo:
        """Return raw JAB context info."""
        info = AccessibleContextInfo()
        ok = self.dll.getAccessibleContextInfo(vm_id, context, ctypes.byref(info))
        if not ok:
            raise HmsGuiAttachError(f"Could not read context info: {context}")
        return info

    def to_node(
        self,
        vm_id: int,
        context: int,
        info: Optional[AccessibleContextInfo] = None,
        hwnd: Optional[int] = None,
    ) -> AccessibleNode:
        """Convert raw context info to an immutable node snapshot."""
        info = info or self.get_context_info(vm_id, context)
        return AccessibleNode(
            name=(info.name or "").strip(),
            description=(info.description or "").strip(),
            role=(info.role_en_US or info.role or "").strip(),
            states=parse_states(info.states_en_US or info.states or ""),
            rect=Rect(info.x, info.y, info.width, info.height),
            index_in_parent=info.indexInParent,
            children_count=info.childrenCount,
            has_action=bool(info.accessibleAction),
            has_selection=bool(info.accessibleSelection),
            has_text=bool(info.accessibleText),
            vm_id=vm_id,
            context=context,
            hwnd=hwnd,
        )

    def get_child(self, vm_id: int, context: int, index: int) -> int:
        """Return a child context handle or 0."""
        self.pump_messages()
        return int(self.dll.getAccessibleChildFromContext(vm_id, context, index))

    def get_parent(self, vm_id: int, context: int) -> int:
        """Return a parent context handle or 0."""
        return int(self.dll.getAccessibleParentFromContext(vm_id, context))

    def release(self, vm_id: int, context: int) -> None:
        """Release a Java object handle."""
        if context:
            self.dll.releaseJavaObject(vm_id, context)

    def get_actions(self, vm_id: int, context: int) -> List[str]:
        """Return action names supported by the context."""
        buf = ctypes.create_string_buffer(ACTIONS_BUFFER_SIZE)
        ok = self.dll.getAccessibleActions(vm_id, context, ctypes.byref(buf))
        if not ok:
            return []
        return parse_actions_buffer(buf.raw)

    def do_action(self, vm_id: int, context: int, action_name: str) -> Tuple[bool, int]:
        """Invoke one JAB action and return ``(ok, first_failure)``."""
        payload = build_action_todo_buffer(action_name)
        buf = ctypes.create_string_buffer(payload, len(payload))
        first_failure = ctypes.c_int(-1)
        ok = self.dll.doAccessibleActions(
            vm_id, context, ctypes.byref(buf), ctypes.byref(first_failure)
        )
        return bool(ok), int(first_failure.value)

    def request_focus(self, vm_id: int, context: int) -> bool:
        """Request focus for a context."""
        return bool(self.dll.requestFocus(vm_id, context))

    def select_child_index(self, vm_id: int, parent_context: int, index: int) -> None:
        """Select a child by index on an AccessibleSelection parent."""
        self.dll.clearAccessibleSelectionFromContext(vm_id, parent_context)
        self.dll.addAccessibleSelectionFromContext(vm_id, parent_context, index)

    def get_selection_contexts(self, vm_id: int, context: int) -> List[int]:
        """Return selected child contexts for a selectable context."""
        count = max(0, self.dll.getAccessibleSelectionCountFromContext(vm_id, context))
        selected: List[int] = []
        for index in range(count):
            child = int(self.dll.getAccessibleSelectionFromContext(vm_id, context, index))
            if child:
                selected.append(child)
        return selected

    def read_text(self, vm_id: int, context: int, node: AccessibleNode) -> str:
        """Read text from a context with AccessibleText support."""
        text_info = AccessibleTextInfo()
        ok = self.dll.getAccessibleTextInfo(
            vm_id, context, ctypes.byref(text_info), node.rect.x, node.rect.y
        )
        if not ok or text_info.charCount <= 0:
            return ""

        chunks: List[str] = []
        start = 0
        while start < text_info.charCount:
            end = min(start + TEXT_CHUNK_CHARS, text_info.charCount) - 1
            chars = end - start + 1
            buf_len = chars + 1
            buf = ctypes.create_string_buffer(buf_len * 2)
            ok = self.dll.getAccessibleTextRange(
                vm_id, context, start, end, ctypes.byref(buf), ctypes.c_short(buf_len)
            )
            if not ok:
                break
            chunks.append(buf.raw[: chars * 2].decode("utf-16-le", errors="ignore"))
            start = end + 1
        return "".join(chunks)

    def set_text(self, vm_id: int, context: int, text: str) -> bool:
        """Set text contents for a context."""
        payload = text.encode("utf-16-le") + b"\x00\x00"
        buf = ctypes.create_string_buffer(payload, len(payload))
        return bool(self.dll.setTextContents(vm_id, context, ctypes.byref(buf)))
