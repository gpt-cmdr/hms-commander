"""Tests for headless HMS round-trip validation."""

from __future__ import annotations

from pathlib import Path
import json
import re

import pytest

from hms_commander import HmsBasinBuilder, HmsJython, HmsRoundTripValidator


def test_normalize_project_diff_strips_volatile_hms_lines(tmp_path):
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()

    (before_dir / "example.hms").write_text(
        "Project: demo\n"
        "     Last Modified Date: 1 January 2024\n"
        "     Last Modified Time: 12:00:00\n"
        "     Version: 4.13\n"
        "End:\n",
        encoding="utf-8",
    )
    (after_dir / "example.hms").write_text(
        "Project: demo\n"
        "     Last Modified Date: 23 April 2026\n"
        "     Last Modified Time: 09:00:00\n"
        "     Version: 4.13\n"
        "End:\n",
        encoding="utf-8",
    )

    diff_report = HmsRoundTripValidator.normalize_project_diff(before_dir, after_dir)
    classification = HmsRoundTripValidator.classify_roundtrip_changes(diff_report)
    report = diff_report["files"]["example.hms"]

    assert report["raw_equal"] is False
    assert report["normalized_equal"] is True
    assert classification["passed"] is True
    assert len(classification["accepted_changes"]) == 1


def test_classify_roundtrip_changes_flags_unclassified_differences(tmp_path):
    before_dir = tmp_path / "before"
    after_dir = tmp_path / "after"
    before_dir.mkdir()
    after_dir.mkdir()

    (before_dir / "example.run").write_text(
        "Run: demo\n"
        "     Basin: Basin A\n"
        "     Precip: Met A\n"
        "End:\n",
        encoding="utf-8",
    )
    (after_dir / "example.run").write_text(
        "Run: demo\n"
        "     Basin: Basin B\n"
        "     Precip: Met A\n"
        "End:\n",
        encoding="utf-8",
    )

    diff_report = HmsRoundTripValidator.normalize_project_diff(before_dir, after_dir)
    classification = HmsRoundTripValidator.classify_roundtrip_changes(diff_report)

    assert diff_report["files"]["example.run"]["normalized_equal"] is False
    assert classification["passed"] is False
    assert len(classification["unclassified_changes"]) == 1


def test_roundtrip_open_save_close_uses_disposable_clone(monkeypatch, tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    hms_path = project_dir / "demo.hms"
    hms_path.write_text(
        "Project: demo\n"
        "     Description: demo project\n"
        "     Version: 4.13\n"
        "     Filepath Separator: \\\n"
        "     DSS File Name: demo.dss\n"
        "     Time Zone ID: America/Chicago\n"
        "End:\n",
        encoding="utf-8",
    )
    fake_hms_exe = tmp_path / "fake_hms.exe"
    fake_hms_exe.write_text("fake", encoding="utf-8")

    def fake_execute_script(script_content, hms_exe_path, working_dir, **kwargs):
        match = re.search(r"OpenProject\('demo', '(.+?)'\)", script_content)
        assert match is not None
        validation_project_dir = Path(match.group(1))
        validation_hms_path = validation_project_dir / "demo.hms"
        validation_hms_path.write_text(
            "Project: demo\n"
            "     Description: demo project\n"
            "     Last Modified Date: 23 April 2026\n"
            "     Last Modified Time: 09:00:00\n"
            "     Version: 4.13\n"
            "     Filepath Separator: \\\n"
            "     DSS File Name: demo.dss\n"
            "     Time Zone ID: America/Chicago\n"
            "End:\n",
            encoding="utf-8",
        )
        return True, "ok", ""

    monkeypatch.setattr(HmsJython, "execute_script", staticmethod(fake_execute_script))
    result = HmsRoundTripValidator.roundtrip_open_save_close(project_dir, hms_exe_path=fake_hms_exe)
    diff_report = json.loads(Path(result["diff_path"]).read_text(encoding="utf-8"))

    assert "Last Modified Date" not in hms_path.read_text(encoding="utf-8")
    assert Path(result["validation_project_dir"]).exists()
    assert Path(result["script_path"]).name == "requested_hms_script.py"
    assert "demo.hms" in diff_report["files"]
    assert result["passed"] is True


def test_roundtrip_open_save_close_rejects_gui_smoke(tmp_path):
    project_dir = tmp_path / "demo_project"
    project_dir.mkdir()
    (project_dir / "demo.hms").write_text(
        "Project: demo\n"
        "     Version: 4.13\n"
        "End:\n",
        encoding="utf-8",
    )

    with pytest.raises(NotImplementedError):
        HmsRoundTripValidator.roundtrip_open_save_close(project_dir, gui_smoke=True)


@pytest.mark.local_hms
def test_roundtrip_open_save_close_passes_on_cloned_river_bend_example(tmp_river_bend_example):
    if HmsJython.find_hms_executable(version="4.13") is None:
        pytest.skip("Local HMS 4.13 installation not available")

    result = HmsRoundTripValidator.roundtrip_open_save_close(tmp_river_bend_example)

    assert result["headless_success"] is True
    assert result["normalized_passed"] is True
    assert result["passed"] is True
    assert Path(result["artifact_dir"]).exists()
    assert Path(result["diff_path"]).exists()
    assert Path(result["validation_project_dir"]).exists()


@pytest.mark.requires_gis
@pytest.mark.local_hms
def test_bootstrapped_taudem_import_roundtrips_headlessly(
    spring_creek_taudem_fixture_root,
    river_bend_example_dir,
    tmp_path,
):
    if HmsJython.find_hms_executable(version="4.13") is None:
        pytest.skip("Local HMS 4.13 installation not available")

    spec = HmsBasinBuilder.build_taudem_hms_spec(spring_creek_taudem_fixture_root)
    project_dir = tmp_path / "spring_creek_sink"
    HmsBasinBuilder.bootstrap_taudem_project(
        spec=spec,
        template_project_dir=river_bend_example_dir,
        output_dir=project_dir,
        basin_name="Spring Creek TauDEM Sink",
        met_name="Spring Creek TauDEM Sink Met",
        control_name="Spring Creek TauDEM Sink Control",
        run_name="Spring Creek TauDEM Sink Run",
        terminal_node_mode="sink",
    )

    result = HmsRoundTripValidator.roundtrip_open_save_close(project_dir)

    assert result["headless_success"] is True
    assert result["normalized_passed"] is True
    assert result["passed"] is True
