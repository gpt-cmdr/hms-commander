"""Tests for no-JAB HMS GUI workflow helpers."""

from __future__ import annotations

import pytest

from hms_commander.gui import (
    HmsGuiUnavailableError,
    StartupProjectSeed,
    WindowInfo,
    ensure_windows,
    infer_hms_version,
    project_state_file,
    restore_startup_project,
    seed_startup_project,
    startup_project_seed,
)
from hms_commander.gui import windows as windows_module


def test_window_info_serializes() -> None:
    window = WindowInfo(hwnd=123, title="HEC-HMS 4.13", process_id=456)

    assert window.to_dict() == {
        "hwnd": 123,
        "title": "HEC-HMS 4.13",
        "process_id": 456,
    }


def test_ensure_windows_raises_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(windows_module.os, "name", "posix", raising=False)

    with pytest.raises(HmsGuiUnavailableError):
        ensure_windows()


def test_infer_hms_version_from_install_dir_and_exe() -> None:
    assert infer_hms_version("C:/Program Files/HEC/HEC-HMS/4.13") == "4.13"
    assert infer_hms_version("C:/Program Files/HEC/HEC-HMS/4.13/HEC-HMS.exe") == "4.13"


def test_project_state_file_uses_appdata(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "AppData" / "Roaming"))

    assert project_state_file("4.13") == (
        tmp_path / "AppData" / "Roaming" / "HEC" / "HEC-HMS" / "projects413.hms"
    )


def test_seed_startup_project_writes_project_blocks(tmp_path) -> None:
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

    assert isinstance(result, StartupProjectSeed)
    assert result.backup_file is not None
    assert result.backup_file.exists()
    assert "Project: Truckee_River" in content
    assert "Recent Projects:" in content
    assert f"File Name: {project.resolve()}" in content
    assert "Open Last Project: Yes" in content


def test_restore_startup_project_restores_backup(tmp_path) -> None:
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


def test_startup_project_seed_context_removes_new_state_file(tmp_path) -> None:
    project = tmp_path / "Truckee_River.hms"
    project.write_text("Project file placeholder\n", encoding="utf-8")
    state = tmp_path / "projects412.hms"

    with startup_project_seed(project, state_file=state) as seed:
        assert seed.state_file == state
        assert state.exists()
        assert "Open Last Project: Yes" in state.read_text(encoding="utf-8")

    assert not state.exists()
