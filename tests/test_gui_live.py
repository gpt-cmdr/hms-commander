r"""Opt-in live HMS GUI regression tests.

Run these only on Windows with HEC-HMS and Java Access Bridge available:

    $env:HMS_GUI_PROJECT = "C:\path\to\Project.hms"
    $env:HMS_GUI_PATH = "C:\Program Files\HEC\HEC-HMS\4.12"
    python -m pytest -m requires_hms_gui tests/test_gui_live.py

Set ``HMS_GUI_LAUNCH=1`` to let the fixture seed HMS startup state and launch
HMS before running the tests. Otherwise the tests attach to an already-open
project and verify the main-frame title.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pytest

from hms_commander import HmsGui


pytestmark = pytest.mark.requires_hms_gui


@dataclass(frozen=True)
class LiveGuiConfig:
    project: Path
    hms_path: Path
    jre_bin: Path
    basin: str
    run_name: str


def _live_config() -> LiveGuiConfig:
    project_text = os.environ.get("HMS_GUI_PROJECT")
    hms_path_text = os.environ.get("HMS_GUI_PATH")
    if not project_text or not hms_path_text:
        pytest.skip("Set HMS_GUI_PROJECT and HMS_GUI_PATH for live GUI tests.")

    project = Path(project_text)
    hms_path = Path(hms_path_text)
    if not project.exists():
        pytest.skip(f"HMS_GUI_PROJECT does not exist: {project}")
    if not (hms_path / "HEC-HMS.exe").exists():
        pytest.skip(f"HMS_GUI_PATH does not contain HEC-HMS.exe: {hms_path}")

    return LiveGuiConfig(
        project=project,
        hms_path=hms_path,
        jre_bin=hms_path / "jre" / "bin",
        basin=os.environ.get("HMS_GUI_BASIN", "Jan_1997"),
        run_name=os.environ.get("HMS_GUI_RUN", "RUN: Jan_1997"),
    )


@pytest.fixture(scope="module")
def live_gui():
    config = _live_config()
    version = os.environ.get("HMS_GUI_VERSION")
    if os.environ.get("HMS_GUI_LAUNCH") == "1":
        HmsGui.enable_access_bridge(hms_path=config.hms_path, version=version)
        with HmsGui.startup_project_seed(
            config.project,
            hms_path=config.hms_path,
            version=version,
        ):
            HmsGui.launch_project(
                config.project,
                hms_path=config.hms_path,
                version=version,
                seed_project_state=False,
                wait_seconds=10,
            )
            HmsGui.wait_for_project_open(
                config.project,
                hms_path=config.hms_path,
                timeout=60,
            )
            yield config
    else:
        HmsGui.wait_for_project_open(config.project, hms_path=config.hms_path, timeout=10)
        yield config


def test_live_project_title_verified(live_gui):
    window = HmsGui.wait_for_project_open(
        live_gui.project,
        hms_path=live_gui.hms_path,
        timeout=10,
    )

    assert str(live_gui.project) in window.title


def test_live_program_settings_modal_cleanup(live_gui):
    with HmsGui.attach(hms_path=live_gui.hms_path) as gui:
        result = gui.safe_invoke_action(
            "Program Settings...",
            role_filter="menu item",
            ancestor_name="Tools",
            timeout=12,
        )
        windows = gui.windows.windows_for_process(gui.process_id)

    assert result.completed
    assert all(window.title.startswith("HEC-HMS") for window in windows)


def test_live_standard_report_compute_combo(live_gui):
    with HmsGui.attach(hms_path=live_gui.hms_path) as gui:
        result = gui.safe_invoke_action(
            "Standard Report...",
            role_filter="menu item",
            ancestor_name="Reports",
            timeout=12,
            close_dialogs=False,
            keep_dialog_open=True,
        )
        assert result.completed
        assert result.dialogs

        with HmsGui.attach(hwnd=result.dialogs[0].hwnd, jre_bin=live_gui.jre_bin) as dialog:
            assert dialog.select_combo_by_label_ex("Compute", live_gui.run_name)

        assert gui.close_dialogs() >= 1


def test_live_subbasin_area_after_basin_activation(live_gui):
    with HmsGui.attach(hms_path=live_gui.hms_path) as gui:
        basin = gui.activate_basin_model(live_gui.basin)
        result = gui.safe_invoke_action(
            "Subbasin Area",
            role_filter="menu item",
            ancestor_name="Parameters",
            timeout=12,
            close_dialogs=False,
            keep_dialog_open=True,
        )
        titles = [dialog.title for dialog in result.dialogs]
        closed = gui.close_dialogs()

    assert basin.name == live_gui.basin
    assert result.completed
    assert any("Subbasin Area" in title for title in titles)
    assert closed >= 1
