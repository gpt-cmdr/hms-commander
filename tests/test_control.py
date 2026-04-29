"""Tests for HmsControl — time window, intervals, control info."""

from datetime import datetime
import importlib
from pathlib import Path

import pytest

from hms_commander.HmsControl import HmsControl
from hms_commander.HmsPrj import HmsPrj


# ---------------------------------------------------------------------------
# get_time_window
# ---------------------------------------------------------------------------

class TestGetTimeWindow:
    def test_returns_dict(self, control_path):
        tw = HmsControl.get_time_window(control_path)
        assert isinstance(tw, dict)

    def test_has_start_end(self, control_path):
        tw = HmsControl.get_time_window(control_path)
        assert "start_date" in tw
        assert "end_date" in tw

    def test_datetime_objects(self, control_path):
        tw = HmsControl.get_time_window(control_path)
        assert isinstance(tw["start_date"], datetime)
        assert isinstance(tw["end_date"], datetime)

    def test_known_values(self, control_path):
        tw = HmsControl.get_time_window(control_path)
        # From file: Start Date: 1 June 2007, End Date: 4 June 2007
        assert tw["start_date"].year == 2007
        assert tw["start_date"].month == 6
        assert tw["start_date"].day == 1
        assert tw["end_date"].day == 4


# ---------------------------------------------------------------------------
# set_time_window
# ---------------------------------------------------------------------------

class TestSetTimeWindow:
    def test_modify_and_readback(self, tmp_control):
        new_start = datetime(2024, 1, 1, 0, 0)
        new_end = datetime(2024, 1, 5, 12, 0)
        HmsControl.set_time_window(tmp_control, new_start, new_end)
        tw = HmsControl.get_time_window(tmp_control)
        assert tw["start_date"].year == 2024
        assert tw["end_date"].day == 5

    def test_roundtrip(self, tmp_control):
        original = HmsControl.get_time_window(tmp_control)
        HmsControl.set_time_window(
            tmp_control, original["start_date"], original["end_date"]
        )
        readback = HmsControl.get_time_window(tmp_control)
        assert readback["start_date"] == original["start_date"]
        assert readback["end_date"] == original["end_date"]


# ---------------------------------------------------------------------------
# get_time_interval / set_time_interval
# ---------------------------------------------------------------------------

class TestGetTimeInterval:
    def test_returns_string(self, control_path):
        interval = HmsControl.get_time_interval(control_path)
        assert isinstance(interval, str)

    def test_known_value(self, control_path):
        interval = HmsControl.get_time_interval(control_path)
        # File has "Time Interval: 5" — may return "5" or "5 Minutes"
        assert "5" in interval


class TestSetTimeInterval:
    def test_modify_and_readback(self, tmp_control):
        HmsControl.set_time_interval(tmp_control, "15 Minutes")
        interval = HmsControl.get_time_interval(tmp_control)
        assert "15" in interval

    def test_integer_input(self, tmp_control):
        HmsControl.set_time_interval(tmp_control, 30)
        interval = HmsControl.get_time_interval(tmp_control)
        assert "30" in interval


# ---------------------------------------------------------------------------
# get_control_info
# ---------------------------------------------------------------------------

class TestGetControlInfo:
    def test_returns_dict(self, control_path):
        info = HmsControl.get_control_info(control_path)
        assert isinstance(info, dict)
        assert len(info) > 0


# ---------------------------------------------------------------------------
# clone_control
# ---------------------------------------------------------------------------

class TestCloneControl:
    def test_clone_preserves_time_window(self, tmp_path, control_path):
        import shutil
        dest = tmp_path / "Control_Clone.control"
        shutil.copy2(control_path, dest)
        tw_orig = HmsControl.get_time_window(control_path)
        tw_clone = HmsControl.get_time_window(dest)
        assert tw_orig["start_date"] == tw_clone["start_date"]
        assert tw_orig["end_date"] == tw_clone["end_date"]

    def test_clone_registers_control_in_initialized_project(self, tmp_project):
        hms_project = HmsPrj().initialize(tmp_project)

        clone_path = HmsControl.clone_control(
            "Control 5",
            "Control_CLONE_REGISTERED",
            hms_object=hms_project,
        )

        assert clone_path.exists()
        assert "Control_CLONE_REGISTERED" in hms_project.control_df["name"].tolist()
        project_text = (tmp_project / "A1000000.hms").read_text(encoding="utf-8")
        assert "Control: Control_CLONE_REGISTERED" in project_text
        assert "FileName: Control_CLONE_REGISTERED.control" in project_text

    def test_clone_without_project_context_is_file_only(self, tmp_control, monkeypatch):
        prj_module = importlib.import_module("hms_commander.HmsPrj")
        monkeypatch.setattr(prj_module, "hms", None)

        clone_path = HmsControl.clone_control(
            str(tmp_control),
            "Control_STANDALONE",
        )

        assert clone_path.exists()
        assert clone_path.parent == tmp_control.parent
        assert not (clone_path.parent / "A1000000.hms").exists()

    def test_clone_raises_when_destination_exists(self, tmp_control, monkeypatch):
        prj_module = importlib.import_module("hms_commander.HmsPrj")
        monkeypatch.setattr(prj_module, "hms", None)
        existing_clone = tmp_control.parent / "Control_EXISTS.control"
        existing_clone.write_text("already here", encoding="utf-8")

        with pytest.raises(FileExistsError):
            HmsControl.clone_control(
                str(tmp_control),
                "Control_EXISTS",
            )

    def test_clone_uses_initialized_global_project_when_no_object_supplied(self, tmp_project, monkeypatch):
        prj_module = importlib.import_module("hms_commander.HmsPrj")
        global_project = HmsPrj().initialize(tmp_project)
        monkeypatch.setattr(prj_module, "hms", global_project)

        clone_path = HmsControl.clone_control(
            "Control 5",
            "Control_GLOBAL_REGISTERED",
        )

        assert clone_path.exists()
        assert "Control_GLOBAL_REGISTERED" in global_project.control_df["name"].tolist()
        project_text = (tmp_project / "A1000000.hms").read_text(encoding="utf-8")
        assert "Control: Control_GLOBAL_REGISTERED" in project_text


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsControl.get_time_window(tmp_path / "nonexistent.control")

    def test_missing_control_get_info(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsControl.get_control_info(tmp_path / "nonexistent.control")
