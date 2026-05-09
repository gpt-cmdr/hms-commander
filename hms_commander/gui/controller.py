"""Public static facade for HMS GUI control."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import List, Optional, Sequence, Union

from hms_commander.LoggingConfig import log_call

from .errors import HmsGuiActionError, HmsGuiUnavailableError
from .jab import resolve_jre_bin
from .nodes import AccessibleNode, GuiActionResult, WindowInfo
from .session import HmsGuiSession
from .windows import Win32Windows
from .workflows import (
    StartupProjectSeed,
    launch_hms,
    restore_startup_project,
    seed_startup_project,
    startup_project_seed,
)


class HmsGui:
    """Static namespace for controlling the HEC-HMS GUI.

    The GUI layer is Windows-only and uses Java Access Bridge. Prefer
    ``HmsCmdr``/``HmsJython``/file APIs for computation and durable project
    edits; use this class for GUI-only workflows and GUI verification.
    """

    @staticmethod
    @log_call
    def attach(
        hwnd: Optional[int] = None,
        *,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        title_contains: str = "HEC-HMS",
    ) -> HmsGuiSession:
        """Attach to a running HEC-HMS GUI window."""
        return HmsGuiSession(
            hwnd=hwnd,
            hms_path=hms_path,
            jre_bin=jre_bin,
            title_contains=title_contains,
        )

    @staticmethod
    @log_call
    def walk(
        max_depth: int = 8,
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> List[AccessibleNode]:
        """Walk the current HEC-HMS GUI accessible tree."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.walk(max_depth=max_depth)

    @staticmethod
    @log_call
    def find_windows(title_contains: str = "HEC-HMS") -> List[WindowInfo]:
        """Find visible HEC-HMS windows."""
        return Win32Windows().find_hms_windows(title_contains=title_contains)

    @staticmethod
    @log_call
    def enable_access_bridge(
        *,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        version: Optional[str] = None,
    ) -> bool:
        """Enable Java Access Bridge for future HEC-HMS GUI launches.

        HEC-HMS must be restarted after enabling JAB. Enabling the bridge does
        not attach it to an already-running JVM.
        """
        bin_path = Path(jre_bin) if jre_bin else resolve_jre_bin(hms_path, version)
        if bin_path is None:
            raise HmsGuiUnavailableError("Could not resolve an HMS JRE bin folder.")
        jabswitch = bin_path / "jabswitch.exe"
        if not jabswitch.exists():
            raise HmsGuiUnavailableError(f"jabswitch.exe not found: {jabswitch}")
        result = subprocess.run(
            [str(jabswitch), "/enable"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0

    @staticmethod
    @log_call
    def seed_startup_project(
        project_file: Union[str, Path],
        *,
        hms_path: Optional[Union[str, Path]] = None,
        version: Optional[str] = None,
        state_file: Optional[Union[str, Path]] = None,
        backup: bool = True,
    ) -> StartupProjectSeed:
        """Seed HMS project state so the GUI opens a project on startup."""
        return seed_startup_project(
            project_file,
            hms_path=hms_path,
            version=version,
            state_file=state_file,
            backup=backup,
        )

    @staticmethod
    @log_call
    def restore_startup_project(seed: StartupProjectSeed) -> bool:
        """Restore HMS startup project state from a seed backup."""
        return restore_startup_project(seed)

    @staticmethod
    @log_call
    def startup_project_seed(
        project_file: Union[str, Path],
        *,
        hms_path: Optional[Union[str, Path]] = None,
        version: Optional[str] = None,
        state_file: Optional[Union[str, Path]] = None,
    ):
        """Temporarily seed HMS startup state and restore it on context exit."""
        return startup_project_seed(
            project_file,
            hms_path=hms_path,
            version=version,
            state_file=state_file,
        )

    @staticmethod
    @log_call
    def launch_project(
        project_file: Union[str, Path],
        *,
        hms_path: Union[str, Path],
        version: Optional[str] = None,
        seed_project_state: bool = True,
        wait_seconds: float = 30.0,
    ):
        """Launch HMS with deterministic startup-open state seeded first."""
        return launch_hms(
            hms_path=hms_path,
            project_file=project_file,
            version=version,
            seed_project_state=seed_project_state,
            wait_seconds=wait_seconds,
        )

    @staticmethod
    @log_call
    def wait_for_project_open(
        project_file: Union[str, Path],
        *,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        timeout: float = 60.0,
        poll_interval: float = 1.0,
    ) -> WindowInfo:
        """Wait until the HMS main-frame title confirms the project is open."""
        project = str(Path(project_file).resolve()).lower()
        deadline = time.monotonic() + timeout
        last_status = "no HMS window found"

        while time.monotonic() < deadline:
            try:
                with HmsGui.attach(hms_path=hms_path, jre_bin=jre_bin) as session:
                    session.dismiss_update_prompt()
                    if project in session.window.title.lower():
                        return session.window
                    last_status = session.window.title
            except Exception as exc:
                last_status = str(exc)
            time.sleep(poll_interval)

        raise HmsGuiActionError(
            f"Timed out waiting for HMS to open {project_file!s}; last status: {last_status}"
        )

    @staticmethod
    @log_call
    def restore_main_window(
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Restore the HEC-HMS main frame if a dialog moved it off-screen."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.windows.restore_window(session.hwnd)

    @staticmethod
    @log_call
    def dump_tree(
        max_depth: int = 8,
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> str:
        """Return a text dump of the current HEC-HMS GUI accessible tree."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.dump_tree(max_depth=max_depth)

    @staticmethod
    @log_call
    def invoke(
        target_name: str,
        action_name: str = "click",
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = True,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        timeout: float = 10.0,
        close_dialogs: bool = True,
        keep_dialog_open: bool = False,
    ) -> GuiActionResult:
        """Safely invoke a GUI action by accessible name."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.safe_invoke_action(
                target_name,
                action_name=action_name,
                role_filter=role_filter,
                require_enabled=require_enabled,
                require_visible=require_visible,
                ancestor_name=ancestor_name,
                ancestor_role_filter=ancestor_role_filter,
                timeout=timeout,
                close_dialogs=close_dialogs,
                keep_dialog_open=keep_dialog_open,
            )

    @staticmethod
    @log_call
    def invoke_many(
        target_names: Sequence[str],
        action_name: str = "click",
        *,
        role_filter: Optional[str] = None,
        require_enabled: bool = True,
        require_visible: bool = False,
        ancestor_name: Optional[str] = None,
        ancestor_role_filter: Optional[str] = None,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        timeout: float = 10.0,
        close_dialogs: bool = True,
    ) -> List[GuiActionResult]:
        """Safely invoke the same GUI action for multiple accessible names."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return [
                session.safe_invoke_action(
                    target_name,
                    action_name=action_name,
                    role_filter=role_filter,
                    require_enabled=require_enabled,
                    require_visible=require_visible,
                    ancestor_name=ancestor_name,
                    ancestor_role_filter=ancestor_role_filter,
                    timeout=timeout,
                    close_dialogs=close_dialogs,
                )
                for target_name in target_names
            ]

    @staticmethod
    @log_call
    def focus(
        target_name: str,
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Request focus on a GUI node."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.focus(target_name)

    @staticmethod
    @log_call
    def select(
        target_name: str,
        *,
        role_filter: Optional[str] = "page tab",
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> AccessibleNode:
        """Select a tab or tree node by accessible name."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.select(target_name, role_filter=role_filter)

    @staticmethod
    @log_call
    def read_component_field(
        label_name: str,
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> str:
        """Read a Component Editor value by visible label text."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.read_component_field(label_name)

    @staticmethod
    @log_call
    def read_text(
        target_name: str,
        *,
        role_filter: Optional[str] = None,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> str:
        """Read text from a named accessible text widget."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.read_text(target_name, role_filter=role_filter)

    @staticmethod
    @log_call
    def write_text(
        target_name: str,
        text: str,
        *,
        label_sibling: bool = False,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Write text to a named text widget or label-sibling value widget."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.write_text(
                target_name,
                text,
                label_sibling=label_sibling,
            )

    @staticmethod
    @log_call
    def select_combo_by_label(
        label_name: str,
        option_name: str,
        *,
        force_keyboard_fallback: bool = False,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Select a combo-box option using a visible field label."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.select_combo_by_label_ex(
                label_name,
                option_name,
                force_keyboard_fallback=force_keyboard_fallback,
            )

    @staticmethod
    @log_call
    def read_message_log(
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> str:
        """Read the HMS Message Log text."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.read_message_log()

    @staticmethod
    @log_call
    def close_dialogs(
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
        preferred_buttons: Sequence[str] = ("Cancel", "Close", "Done", "OK"),
    ) -> int:
        """Close all HMS Java dialogs except the main frame."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.close_dialogs(preferred_buttons=preferred_buttons)

    @staticmethod
    @log_call
    def dismiss_update_prompt(
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> bool:
        """Dismiss the HMS startup update prompt if it is open."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.dismiss_update_prompt()

    @staticmethod
    @log_call
    def activate_basin_model(
        basin_name: str,
        *,
        hwnd: Optional[int] = None,
        hms_path: Optional[Union[str, Path]] = None,
        jre_bin: Optional[Union[str, Path]] = None,
    ) -> AccessibleNode:
        """Select/open a basin model from Watershed Explorer."""
        with HmsGui.attach(hwnd=hwnd, hms_path=hms_path, jre_bin=jre_bin) as session:
            return session.activate_basin_model(basin_name)
