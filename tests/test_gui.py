"""Tests for the HMS GUI control package.

These tests avoid requiring a live HEC-HMS GUI. Live GUI tests should be marked
``requires_hms_gui`` and kept separate from default validation.
"""

import json
import struct
from inspect import signature

import pytest

from hms_commander import HmsGui
from hms_commander.gui.errors import HmsGuiUnavailableError
from hms_commander.gui.jab import (
    ACTIONS_BUFFER_SIZE,
    ACTION_NAME_BYTES,
    build_action_todo_buffer,
    parse_actions_buffer,
    resolve_jre_bin,
)
from hms_commander.gui.nodes import AccessibleNode, GuiActionResult, Rect, WindowInfo
from hms_commander.gui.session import HmsGuiSession
from hms_commander.gui.workflows import (
    restore_startup_project,
    seed_startup_project,
    startup_project_seed,
)


def test_public_import_exposes_hms_gui():
    assert HmsGui.__name__ == "HmsGui"
    assert callable(HmsGui.invoke_many)
    assert callable(HmsGui.select_combo_by_label)
    assert callable(HmsGui.wait_for_project_open)
    assert callable(HmsGui.restore_main_window)
    assert callable(HmsGui.restore_startup_project)
    assert callable(HmsGui.startup_project_seed)
    assert callable(HmsGui.write_text)


def test_invoke_accepts_scoped_selector_arguments():
    params = signature(HmsGui.invoke).parameters

    assert "role_filter" in params
    assert "require_enabled" in params
    assert "require_visible" in params
    assert "ancestor_name" in params
    assert "ancestor_role_filter" in params


def test_accessible_node_state_helpers():
    node = AccessibleNode(
        name="Map Layers...",
        role="menu item",
        states=("enabled", "visible", "selectable"),
        rect=Rect(10, 20, 30, 40),
    )

    assert node.enabled
    assert node.visible
    assert node.has_state("SELECTABLE")
    assert node.rect.center == (25, 40)
    assert node.to_dict()["rect"]["width"] == 30


def test_build_action_todo_buffer_uses_jab_layout():
    buf = build_action_todo_buffer("click")

    assert len(buf) == 4 + 32 * ACTION_NAME_BYTES
    assert struct.unpack("<i", buf[:4])[0] == 1
    assert buf[4 : 4 + 10].decode("utf-16-le").rstrip("\x00") == "click"


def test_parse_actions_buffer_reads_utf16_names():
    payload = bytearray(ACTIONS_BUFFER_SIZE)
    payload[:4] = struct.pack("<i", 2)
    payload[4 : 4 + len("click".encode("utf-16-le"))] = "click".encode(
        "utf-16-le"
    )
    offset = 4 + ACTION_NAME_BYTES
    payload[offset : offset + len("toggleexpand".encode("utf-16-le"))] = (
        "toggleexpand".encode("utf-16-le")
    )

    assert parse_actions_buffer(payload) == ["click", "toggleexpand"]


def test_gui_action_result_serializes_dialogs():
    result = GuiActionResult(
        target_name="Program Settings...",
        action_name="click",
        completed=True,
        dialogs=(WindowInfo(hwnd=123, title="Program Settings", process_id=456),),
        stdout=json.dumps({"ok": True}),
    )

    data = result.to_dict()

    assert data["completed"] is True
    assert data["dialogs"][0]["title"] == "Program Settings"


def test_parse_worker_json_uses_last_json_line():
    stdout = "diagnostic\n{\"ok\": false}\n{\"ok\": true, \"value\": 3}\n"

    assert HmsGuiSession.parse_worker_json(stdout) == {"ok": True, "value": 3}


def test_resolve_jre_bin_from_explicit_bin(tmp_path):
    bin_dir = tmp_path / "jre" / "bin"
    bin_dir.mkdir(parents=True)
    (bin_dir / "windowsaccessbridge-64.dll").write_bytes(b"")

    assert resolve_jre_bin(bin_dir) == bin_dir


def test_seed_startup_project_writes_project_blocks(tmp_path):
    project = tmp_path / "Truckee_River.hms"
    project.write_text("Project file placeholder\n", encoding="utf-8")
    state = tmp_path / "projects412.hms"
    state.write_text(
        "Screen Settings:\nEnd:\n\n"
        "ProgramSettings:\n"
        "     Open Last Project: No\n"
        "End:\n",
        encoding="utf-8",
    )

    result = seed_startup_project(project, state_file=state, backup=True)
    content = state.read_text(encoding="utf-8")

    assert result.backup_file is not None
    assert result.backup_file.exists()
    assert "Project: Truckee_River" in content
    assert "Recent Projects:" in content
    assert f"File Name: {project.resolve()}" in content
    assert "Open Last Project: Yes" in content


def test_restore_startup_project_restores_backup(tmp_path):
    project = tmp_path / "Truckee_River.hms"
    project.write_text("Project file placeholder\n", encoding="utf-8")
    state = tmp_path / "projects412.hms"
    original = (
        "Project: Original\n"
        "     File Name: C:\\original\\Original.hms\n"
        "End:\n"
        "ProgramSettings:\n"
        "     Open Last Project: No\n"
        "End:\n"
    )
    state.write_text(original, encoding="utf-8")

    seed = seed_startup_project(project, state_file=state, backup=True)
    assert "Truckee_River" in state.read_text(encoding="utf-8")

    assert restore_startup_project(seed) is True
    assert state.read_text(encoding="utf-8") == original


def test_startup_project_seed_context_removes_new_state_file(tmp_path):
    project = tmp_path / "Truckee_River.hms"
    project.write_text("Project file placeholder\n", encoding="utf-8")
    state = tmp_path / "projects412.hms"

    with startup_project_seed(project, state_file=state) as seed:
        assert seed.state_file == state
        assert state.exists()
        assert "Open Last Project: Yes" in state.read_text(encoding="utf-8")

    assert not state.exists()


def test_attach_fails_cleanly_without_windows(monkeypatch):
    if __import__("os").name == "nt":
        pytest.skip("non-Windows guard test")

    with pytest.raises(HmsGuiUnavailableError):
        HmsGui.attach()
