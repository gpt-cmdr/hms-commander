"""Stateful HMS GUI control session."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Union

from hms_commander.LoggingConfig import get_logger, log_call

from .errors import HmsGuiActionError, HmsGuiAttachError
from .jab import JavaAccessBridge, resolve_jre_bin
from .nodes import AccessibleNode, ActionResult, GuiActionResult, WindowInfo
from .windows import Win32Windows

logger = get_logger(__name__)


class HmsGuiSession:
    """A live Java Access Bridge session attached to one HEC-HMS GUI window."""

    def __init__(
        self,
        hwnd: Optional[int] = None,
        *,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        title_contains: str = "HEC-HMS",
    ):
        self.windows = Win32Windows()
        self.jre_bin = Path(jre_bin) if jre_bin else resolve_jre_bin(hms_path)
        self.bridge = JavaAccessBridge(self.jre_bin)
        self.bridge.start()
        self.window = self._resolve_window(hwnd, title_contains=title_contains)
        self.hwnd = self.window.hwnd
        self.process_id = self.window.process_id
        self.vm_id, self.root_context = self.bridge.attach_window(self.hwnd)
        self.closed = False

    def _resolve_window(
        self,
        hwnd: Optional[int],
        *,
        title_contains: str,
    ) -> WindowInfo:
        if hwnd is None:
            candidates = self.windows.find_hms_windows(title_contains=title_contains)
            candidates.extend(
                window
                for window in self.windows.visible_windows()
                if window not in candidates
            )
            for window in candidates:
                try:
                    vm_id, root = self.bridge.attach_window(window.hwnd)
                    info = self.bridge.get_context_info(vm_id, root)
                    node = self.bridge.to_node(vm_id, root, info, hwnd=window.hwnd)
                    self.bridge.release(vm_id, root)
                except Exception:
                    continue
                if node.role == "frame" and node.name.startswith("HEC-HMS"):
                    self.windows.restore_window(window.hwnd)
                    return WindowInfo(window.hwnd, node.name or window.title, window.process_id)
            raise HmsGuiAttachError("No JAB-enabled HEC-HMS main frame found.")
        for window in self.windows.visible_windows():
            if window.hwnd == int(hwnd):
                return window
        return WindowInfo(
            hwnd=int(hwnd),
            title="",
            process_id=self.windows.process_id_for_window(int(hwnd)),
        )

    def __enter__(self) -> "HmsGuiSession":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()

    def close(self) -> None:
        """Release the root Java object held by this session."""
        if not self.closed:
            self.bridge.release(self.vm_id, self.root_context)
            self.closed = True

    def _release_owned(self, context: int) -> None:
        """Release a context unless it is the session root."""
        if context and context != self.root_context:
            self.bridge.release(self.vm_id, context)

    @log_call
    def walk(self, max_depth: int = 8) -> List[AccessibleNode]:
        """Walk the current Java accessible tree and return node snapshots."""
        nodes: List[AccessibleNode] = []

        def visit(context: int, depth: int) -> None:
            info = self.bridge.get_context_info(self.vm_id, context)
            node = self.bridge.to_node(self.vm_id, context, info, hwnd=self.hwnd)
            nodes.append(node)
            if depth >= max_depth:
                return
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(self.vm_id, context, index)
                if child:
                    try:
                        visit(child, depth + 1)
                    finally:
                        self.bridge.release(self.vm_id, child)

        visit(self.root_context, 0)
        return nodes

    def dump_tree(self, max_depth: int = 8) -> str:
        """Return a readable text dump of the current accessible tree."""
        lines: List[str] = []

        def visit(context: int, depth: int) -> None:
            info = self.bridge.get_context_info(self.vm_id, context)
            node = self.bridge.to_node(self.vm_id, context, info, hwnd=self.hwnd)
            indent = "  " * depth
            states = ",".join(node.states)
            lines.append(
                f"{indent}[{node.role}] {node.name!r} states={states!r} "
                f"rect={node.rect.x},{node.rect.y} "
                f"{node.rect.width}x{node.rect.height} kids={node.children_count}"
            )
            if depth >= max_depth:
                return
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(self.vm_id, context, index)
                if child:
                    try:
                        visit(child, depth + 1)
                    finally:
                        self.bridge.release(self.vm_id, child)

        visit(self.root_context, 0)
        return "\n".join(lines)

    def find(
        self,
        name: str,
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = False,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
    ) -> AccessibleNode:
        """Find a node by exact accessible name."""
        context, node = self._find_scoped_context(
            name,
            role_filter=role_filter,
            require_enabled=require_enabled,
            require_visible=require_visible,
            ancestor_name=ancestor_name,
            ancestor_role_filter=ancestor_role_filter,
        )
        self._release_owned(context)
        return node

    def _find_context(
        self,
        predicate: Callable[[AccessibleNode], bool],
        *,
        start_context: Optional[int] = None,
    ) -> Tuple[int, AccessibleNode]:
        root = start_context or self.root_context
        found: Optional[Tuple[int, AccessibleNode]] = None

        def visit(context: int) -> bool:
            nonlocal found
            info = self.bridge.get_context_info(self.vm_id, context)
            node = self.bridge.to_node(self.vm_id, context, info, hwnd=self.hwnd)
            if predicate(node):
                found = (context, node)
                return True
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(self.vm_id, context, index)
                if not child:
                    continue
                child_has_match = visit(child)
                if child_has_match:
                    return True
                self.bridge.release(self.vm_id, child)
            return False

        visit(root)
        if found is None:
            raise HmsGuiAttachError("No matching accessible node found.")
        return found

    def _find_scoped_context(
        self,
        name: str,
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = False,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
        start_context: Optional[int] = None,
    ) -> Tuple[int, AccessibleNode]:
        root = start_context or self.root_context
        found: Optional[Tuple[int, AccessibleNode]] = None

        def visit(context: int) -> bool:
            nonlocal found
            info = self.bridge.get_context_info(self.vm_id, context)
            node = self.bridge.to_node(self.vm_id, context, info, hwnd=self.hwnd)
            matches = (
                node.name == name
                and (role_filter is None or node.role == role_filter)
                and (not require_enabled or node.enabled)
                and (not require_visible or node.visible)
                and self._context_has_ancestor(
                    context,
                    ancestor_name=ancestor_name,
                    ancestor_role_filter=ancestor_role_filter,
                )
            )
            if matches:
                found = (context, node)
                return True
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(self.vm_id, context, index)
                if not child:
                    continue
                child_has_match = visit(child)
                if child_has_match:
                    return True
                self.bridge.release(self.vm_id, child)
            return False

        visit(root)
        if found is None:
            pieces = [f"name={name!r}"]
            if role_filter:
                pieces.append(f"role={role_filter!r}")
            if ancestor_name:
                pieces.append(f"ancestor={ancestor_name!r}")
            raise HmsGuiAttachError("No matching accessible node found: " + ", ".join(pieces))
        return found

    def _context_has_ancestor(
        self,
        context: int,
        *,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
    ) -> bool:
        if ancestor_name is None:
            return True

        parent = self.bridge.get_parent(self.vm_id, context)
        while parent:
            try:
                info = self.bridge.get_context_info(self.vm_id, parent)
                node = self.bridge.to_node(self.vm_id, parent, info, hwnd=self.hwnd)
                if node.name == ancestor_name and (
                    ancestor_role_filter is None or node.role == ancestor_role_filter
                ):
                    return True
                next_parent = self.bridge.get_parent(self.vm_id, parent)
            finally:
                self._release_owned(parent)
            parent = next_parent
        return False

    def _collect_contexts(
        self,
        predicate: Callable[[AccessibleNode], bool],
        *,
        start_context: Optional[int] = None,
    ) -> List[Tuple[int, AccessibleNode]]:
        root = start_context or self.root_context
        matches: List[Tuple[int, AccessibleNode]] = []

        def visit(context: int) -> bool:
            info = self.bridge.get_context_info(self.vm_id, context)
            node = self.bridge.to_node(self.vm_id, context, info, hwnd=self.hwnd)
            keep = predicate(node)
            if keep:
                matches.append((context, node))
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(self.vm_id, context, index)
                if not child:
                    continue
                child_keep = visit(child)
                if not child_keep:
                    self.bridge.release(self.vm_id, child)
            return keep

        visit(root)
        return matches

    @log_call
    def invoke_action(
        self,
        target_name: str,
        action_name: str = "click",
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = True,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
    ) -> ActionResult:
        """Directly invoke a JAB action on a node.

        This low-level method can block if the action opens a modal dialog. Use
        :meth:`safe_invoke_action` for public workflows that may open dialogs.
        """
        context, node = self._find_scoped_context(
            target_name,
            role_filter=role_filter,
            require_enabled=require_enabled,
            require_visible=require_visible,
            ancestor_name=ancestor_name,
            ancestor_role_filter=ancestor_role_filter,
        )
        try:
            if require_enabled and not node.enabled:
                raise HmsGuiActionError(
                    f"Target is not enabled: {target_name!r} states={node.states!r}"
                )
            actions = tuple(self.bridge.get_actions(self.vm_id, context))
            if actions and action_name not in actions:
                raise HmsGuiActionError(
                    f"Action {action_name!r} not available for {target_name!r}; "
                    f"available actions: {actions}"
                )
            ok, first_failure = self.bridge.do_action(self.vm_id, context, action_name)
            return ActionResult(
                target_name=target_name,
                action_name=action_name,
                ok=ok,
                first_failure=first_failure,
                node=node,
                available_actions=actions,
            )
        finally:
            self._release_owned(context)

    @log_call
    def safe_invoke_action(
        self,
        target_name: str,
        action_name: str = "click",
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = True,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
        timeout: float = 10.0,
        close_dialogs: bool = True,
        keep_dialog_open: bool = False,
    ) -> GuiActionResult:
        """Invoke an action in a worker process with dialog cleanup.

        HMS modal dialogs can block ``doAccessibleActions``. This method mirrors
        the original controller's watchdog pattern: the blocking action runs in
        a child Python process while this process polls for new HMS windows,
        optionally closes dialogs, then terminates the worker if needed.
        """
        before = self.windows.windows_for_process(self.process_id)
        before_hwnds = {window.hwnd for window in before}
        cmd = [
            sys.executable,
            "-m",
            "hms_commander.gui._action_worker",
            "--hwnd",
            str(self.hwnd),
            "--target",
            target_name,
            "--action",
            action_name,
        ]
        if self.jre_bin:
            cmd.extend(["--jre-bin", str(self.jre_bin)])
        if role_filter:
            cmd.extend(["--role-filter", role_filter])
        if not require_enabled:
            cmd.append("--allow-disabled")
        if require_visible:
            cmd.append("--require-visible")
        if ancestor_name:
            cmd.extend(["--ancestor-name", ancestor_name])
        if ancestor_role_filter:
            cmd.extend(["--ancestor-role-filter", ancestor_role_filter])

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        dialogs: List[WindowInfo] = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            dialogs = self.windows.new_windows(self.process_id, before_hwnds)
            if dialogs:
                break
            if proc.poll() is not None:
                break
            time.sleep(0.3)

        if close_dialogs and not keep_dialog_open:
            self.close_dialogs()

        timed_out = proc.poll() is None and time.monotonic() >= deadline
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
            proc.terminate()
            try:
                stdout, stderr = proc.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()

        late_dialogs: List[WindowInfo] = []
        late_deadline = time.monotonic() + 2.0
        while time.monotonic() < late_deadline:
            late_dialogs = self.windows.new_windows(self.process_id, before_hwnds)
            if late_dialogs:
                break
            time.sleep(0.2)
        if late_dialogs:
            known = {dialog.hwnd for dialog in dialogs}
            dialogs.extend(dialog for dialog in late_dialogs if dialog.hwnd not in known)
        if close_dialogs and not keep_dialog_open:
            # Some HMS dialogs appear just after doAccessibleActions returns, so
            # run cleanup again after collecting the worker result.
            self.close_dialogs()
            time.sleep(0.5)
            self.close_dialogs()

        completed = proc.returncode == 0 and not timed_out
        if keep_dialog_open and dialogs:
            completed = True
        return GuiActionResult(
            target_name=target_name,
            action_name=action_name,
            completed=completed,
            timed_out=timed_out,
            returncode=proc.returncode,
            dialogs=tuple(dialogs),
            stdout=stdout,
            stderr=stderr,
        )

    @log_call
    def focus(self, target_name: str) -> bool:
        """Request focus on an accessible node by name."""
        context, _node = self._find_context(lambda item: item.name == target_name)
        try:
            return self.bridge.request_focus(self.vm_id, context)
        finally:
            self._release_owned(context)

    @log_call
    def select(
        self,
        target_name: str,
        *,
        role_filter: Optional[str] = "page tab",
    ) -> AccessibleNode:
        """Select a page tab or tree node by name."""
        context, node = self._find_context(
            lambda item: item.name == target_name
            and (role_filter is None or item.role == role_filter)
        )
        parent = 0
        try:
            parent = self.bridge.get_parent(self.vm_id, context)
            if not parent:
                raise HmsGuiActionError(f"No selectable parent for {target_name!r}")
            self.bridge.select_child_index(self.vm_id, parent, node.index_in_parent)
            return node
        finally:
            self._release_owned(context)
            self._release_owned(parent)

    def _read_context_value(self, context: int, node: AccessibleNode) -> str:
        if node.has_text:
            return self.bridge.read_text(self.vm_id, context, node)
        if node.role == "combo box":
            selected = self.bridge.get_selection_contexts(self.vm_id, context)
            try:
                if not selected:
                    return ""
                selected_info = self.bridge.get_context_info(self.vm_id, selected[0])
                selected_node = self.bridge.to_node(
                    self.vm_id, selected[0], selected_info, hwnd=self.hwnd
                )
                return selected_node.name or "--None--"
            finally:
                for selected_context in selected:
                    self._release_owned(selected_context)
        return node.name

    @log_call
    def read_text(self, target_name: str, *, role_filter: Optional[str] = None) -> str:
        """Read AccessibleText from a node by name."""
        context, node = self._find_context(
            lambda item: item.name == target_name
            and (role_filter is None or item.role == role_filter)
        )
        try:
            return self._read_context_value(context, node)
        finally:
            self._release_owned(context)

    @log_call
    def read_component_field(self, label_name: str) -> str:
        """Read a Component Editor value by visible label text."""
        label_context, label_node = self._find_scoped_context(
            label_name,
            role_filter="label",
            require_visible=True,
        )
        value_context = 0
        try:
            value_context = self._find_field_value_context(label_context, label_node)
            value_info = self.bridge.get_context_info(self.vm_id, value_context)
            value_node = self.bridge.to_node(
                self.vm_id, value_context, value_info, hwnd=self.hwnd
            )
            return self._read_context_value(value_context, value_node)
        finally:
            self._release_owned(label_context)
            self._release_owned(value_context)

    def _find_field_value_context(
        self,
        label_context: int,
        label_node: AccessibleNode,
    ) -> int:
        parent = self.bridge.get_parent(self.vm_id, label_context)
        try:
            if parent:
                sibling = self.bridge.get_child(
                    self.vm_id, parent, label_node.index_in_parent + 1
                )
                if sibling:
                    sibling_info = self.bridge.get_context_info(self.vm_id, sibling)
                    sibling_node = self.bridge.to_node(
                        self.vm_id, sibling, sibling_info, hwnd=self.hwnd
                    )
                    if self._is_field_value_node(sibling_node):
                        return sibling
                    self._release_owned(sibling)
            return self._find_field_value_by_geometry(label_node)
        finally:
            self._release_owned(parent)

    def _find_field_value_by_geometry(self, label_node: AccessibleNode) -> int:
        candidates = self._collect_contexts(
            lambda item: item.visible
            and item.name != label_node.name
            and self._is_field_value_node(item)
        )
        best: Optional[Tuple[int, AccessibleNode]] = None
        best_score = 10**9
        label_center_y = label_node.rect.y + label_node.rect.height // 2
        label_right = label_node.rect.x + label_node.rect.width
        for candidate in candidates:
            _context, node = candidate
            if node.rect.width < 0 or node.rect.height < 0:
                continue
            if node.rect.x < label_right - 4:
                continue
            center_y = node.rect.y + node.rect.height // 2
            y_delta = abs(center_y - label_center_y)
            if y_delta > 30:
                continue
            role_penalty = 100000 if node.role == "label" else 0
            x_delta = max(0, node.rect.x - label_right)
            score = role_penalty + y_delta * 1000 + x_delta
            if score < best_score:
                best = candidate
                best_score = score

        best_context = best[0] if best else 0
        for context, _node in candidates:
            if context != best_context:
                self._release_owned(context)
        if best_context:
            return best_context
        raise HmsGuiActionError(f"No value widget found for {label_node.name!r}")

    @staticmethod
    def _is_field_value_node(node: AccessibleNode) -> bool:
        return node.role in {"text", "combo box", "label"} and (
            node.has_text or node.role in {"combo box", "label"}
        )

    @log_call
    def write_text(
        self,
        target_name: str,
        text: str,
        *,
        label_sibling: bool = False,
    ) -> bool:
        """Write text to a text widget by name or label-sibling convention."""
        context, node = self._find_context(lambda item: item.name == target_name)
        parent = 0
        write_context = context
        try:
            if label_sibling:
                parent = self.bridge.get_parent(self.vm_id, context)
                if not parent:
                    raise HmsGuiActionError(f"No parent for {target_name!r}")
                write_context = self.bridge.get_child(
                    self.vm_id, parent, node.index_in_parent + 1
                )
                if not write_context:
                    raise HmsGuiActionError(f"No sibling text widget for {target_name!r}")
            return self.bridge.set_text(self.vm_id, write_context, text)
        finally:
            if write_context != context:
                self._release_owned(write_context)
            self._release_owned(parent)
            self._release_owned(context)

    @log_call
    def select_combo_by_label(self, label_name: str, option_name: str) -> bool:
        """Select a combo-box option using the visible label on the same row."""
        return self.select_combo_by_label_ex(
            label_name,
            option_name,
            force_keyboard_fallback=False,
        )

    @log_call
    def select_combo_by_label_ex(
        self,
        label_name: str,
        option_name: str,
        *,
        force_keyboard_fallback: bool = False,
    ) -> bool:
        """Select a combo-box option, optionally using keyboard fallback."""
        kept_contexts: List[int] = []
        try:
            matches = self._collect_contexts(
                lambda item: (
                    (item.role == "label" and item.name == label_name)
                    or (item.role == "combo box" and item.visible)
                )
            )
            kept_contexts = [context for context, _node in matches]
            labels = [(c, n) for c, n in matches if n.role == "label"]
            combos = [(c, n) for c, n in matches if n.role == "combo box"]
            if not labels:
                raise HmsGuiActionError(f"Label not found: {label_name!r}")
            label_node = labels[0][1]
            label_center_y = label_node.rect.y + label_node.rect.height // 2
            combo = self._nearest_combo_on_row(label_node, label_center_y, combos)
            option_context, option_node = self._find_context(
                lambda item: item.role == "label" and item.name == option_name,
                start_context=combo[0],
            )
            kept_contexts.append(option_context)
            parent = self.bridge.get_parent(self.vm_id, option_context)
            kept_contexts.append(parent)
            after = self._read_context_value(combo[0], combo[1])
            if not force_keyboard_fallback:
                self.bridge.select_child_index(
                    self.vm_id, combo[0], option_node.index_in_parent
                )
                time.sleep(0.3)
                after = self._read_context_value(combo[0], combo[1])
                if after != option_name and parent:
                    self.bridge.select_child_index(
                        self.vm_id, parent, option_node.index_in_parent
                    )
                    time.sleep(0.3)
                    after = self._read_context_value(combo[0], combo[1])
            if force_keyboard_fallback or after != option_name:
                self.bridge.request_focus(self.vm_id, combo[0])
                self.windows.post_key(self.hwnd, 0x24, delay_seconds=0.2)  # VK_HOME
                time.sleep(0.2)
                after = self._read_context_value(combo[0], combo[1])
                steps = max(0, option_node.index_in_parent)
                for _index in range(steps):
                    if after == option_name and not force_keyboard_fallback:
                        break
                    self.windows.post_key(self.hwnd, 0x28, delay_seconds=0.1)  # VK_DOWN
                    time.sleep(0.35)
                    after = self._read_context_value(combo[0], combo[1])
            return after == option_name
        finally:
            seen = set()
            for context in reversed([item for item in kept_contexts if item]):
                if context in seen:
                    continue
                seen.add(context)
                self._release_owned(context)

    def _nearest_combo_on_row(
        self,
        label_node: AccessibleNode,
        label_center_y: int,
        combos: Sequence[Tuple[int, AccessibleNode]],
    ) -> Tuple[int, AccessibleNode]:
        best: Optional[Tuple[int, AccessibleNode]] = None
        best_score = 10**9
        for combo in combos:
            _context, node = combo
            if node.rect.x < label_node.rect.x + label_node.rect.width:
                continue
            center_y = node.rect.y + node.rect.height // 2
            score = abs(center_y - label_center_y)
            if score < best_score:
                best = combo
                best_score = score
        if best is None or best_score > 30:
            raise HmsGuiActionError(f"No combo box found on row for {label_node.name!r}")
        return best

    @log_call
    def read_message_log(self) -> str:
        """Read the first visible multi-line text node, typically Message Log."""
        context, node = self._find_context(
            lambda item: item.has_text and item.has_state("multiple line")
        )
        try:
            return self.bridge.read_text(self.vm_id, context, node)
        finally:
            self._release_owned(context)

    @log_call
    def close_dialogs(
        self,
        preferred_buttons: Sequence[str] = ("Cancel", "Close", "Done", "OK"),
    ) -> int:
        """Close all visible Java windows except the main HMS frame."""
        dialogs = [
            window
            for window in self.windows.windows_for_process(self.process_id)
            if window.hwnd != self.hwnd
        ]
        closed = 0
        for dialog in dialogs:
            if self._click_dialog_button(dialog, preferred_buttons):
                closed += 1
                time.sleep(0.3)
                continue
            closed += self.windows.close_windows([dialog])
        self.windows.restore_window(self.hwnd)
        return closed

    @log_call
    def dismiss_update_prompt(self) -> bool:
        """Dismiss HMS 4.12/4.13 startup update prompt if present."""
        for window in self.windows.windows_for_process(self.process_id):
            if window.hwnd == self.hwnd or window.title != "New Version Available":
                continue
            try:
                with HmsGuiSession(hwnd=window.hwnd, jre_bin=self.jre_bin) as dialog:
                    result = dialog.invoke_action("Remind Me Later", require_enabled=True)
                    return result.ok
            except Exception:
                return False
        return False

    @log_call
    def activate_basin_model(self, basin_name: str) -> AccessibleNode:
        """Open/select a basin model in the Watershed Explorer tree."""
        try:
            self.select("Components", role_filter="page tab")
            time.sleep(0.3)
        except Exception:
            pass
        try:
            context, basin_root = self._find_context(
                lambda item: item.name == "Basin Models" and item.role == "label"
            )
            self._release_owned(context)
            if not basin_root.has_state("expanded"):
                self.invoke_action(
                    "Basin Models",
                    action_name="toggleexpand",
                    role_filter="label",
                    require_enabled=False,
                )
                time.sleep(0.3)
        except Exception:
            pass
        return self.select(basin_name, role_filter=None)

    def _click_dialog_button(
        self,
        dialog: WindowInfo,
        preferred_buttons: Sequence[str],
    ) -> bool:
        try:
            vm_id, root = self.bridge.attach_window(dialog.hwnd)
        except Exception:
            return False
        context = 0
        try:
            context, _node = self._find_dialog_button(vm_id, root, preferred_buttons)
            ok, _failure = self.bridge.do_action(vm_id, context, "click")
            return ok
        except Exception:
            return False
        finally:
            self.bridge.release(vm_id, context)
            self.bridge.release(vm_id, root)

    def _find_dialog_button(
        self,
        vm_id: int,
        root_context: int,
        preferred_buttons: Sequence[str],
    ) -> Tuple[int, AccessibleNode]:
        preferred = set(preferred_buttons)
        found: Optional[Tuple[int, AccessibleNode]] = None

        def visit(context: int) -> bool:
            nonlocal found
            info = self.bridge.get_context_info(vm_id, context)
            node = self.bridge.to_node(vm_id, context, info)
            if node.role == "push button" and node.name in preferred:
                found = (context, node)
                return True
            for index in range(max(0, info.childrenCount)):
                child = self.bridge.get_child(vm_id, context, index)
                if not child:
                    continue
                child_has_match = visit(child)
                if child_has_match:
                    return True
                self.bridge.release(vm_id, child)
            return False

        visit(root_context)
        if found is None:
            raise HmsGuiAttachError("No preferred dialog button found.")
        return found

    @staticmethod
    def parse_worker_json(stdout: str) -> Optional[dict]:
        """Parse the final JSON line from an action worker."""
        for line in reversed(stdout.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
        return None
