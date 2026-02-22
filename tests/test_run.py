"""Tests for HmsRun — focus on *_direct methods (no project init needed)."""

import pytest

from hms_commander.HmsRun import HmsRun


# ---------------------------------------------------------------------------
# list_runs_direct
# ---------------------------------------------------------------------------

class TestListRunsDirect:
    def test_returns_list(self, run_path):
        runs = HmsRun.list_runs_direct(run_path)
        assert isinstance(runs, list)

    def test_count(self, run_path):
        runs = HmsRun.list_runs_direct(run_path)
        # File has 10 runs
        assert len(runs) == 10

    def test_known_run_names(self, run_path):
        runs = HmsRun.list_runs_direct(run_path)
        names = [r["name"] for r in runs]
        assert "1%(100YR)RUN" in names
        assert "10%(10YR)RUN" in names
        assert "Ph1_1PCT_Run" in names


# ---------------------------------------------------------------------------
# get_dss_file_direct
# ---------------------------------------------------------------------------

class TestGetDssFileDirect:
    def test_returns_string(self, run_path):
        dss = HmsRun.get_dss_file_direct(run_path, "1%(100YR)RUN")
        assert isinstance(dss, str)

    def test_known_dss_file(self, run_path):
        dss = HmsRun.get_dss_file_direct(run_path, "1%(100YR)RUN")
        assert dss == "A1000000.dss"


# ---------------------------------------------------------------------------
# set_dss_file_direct
# ---------------------------------------------------------------------------

class TestSetDssFileDirect:
    def test_modify_and_readback(self, tmp_run):
        HmsRun.set_dss_file_direct(tmp_run, "1%(100YR)RUN", "new_output.dss")
        dss = HmsRun.get_dss_file_direct(tmp_run, "1%(100YR)RUN")
        assert dss == "new_output.dss"

    def test_other_runs_unchanged(self, tmp_run):
        HmsRun.set_dss_file_direct(tmp_run, "1%(100YR)RUN", "new_output.dss")
        dss = HmsRun.get_dss_file_direct(tmp_run, "10%(10YR)RUN")
        assert dss == "A1000000.dss"


# ---------------------------------------------------------------------------
# set_description_direct
# ---------------------------------------------------------------------------

class TestSetDescriptionDirect:
    def test_modify_and_readback(self, tmp_run):
        HmsRun.set_description_direct(tmp_run, "1%(100YR)RUN", "Test Description")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_info = [r for r in runs if r["name"] == "1%(100YR)RUN"][0]
        assert run_info["description"] == "Test Description"

    def test_preserves_other_fields(self, tmp_run):
        HmsRun.set_description_direct(tmp_run, "1%(100YR)RUN", "New Desc")
        dss = HmsRun.get_dss_file_direct(tmp_run, "1%(100YR)RUN")
        assert dss == "A1000000.dss"


# ---------------------------------------------------------------------------
# set_basin_direct
# ---------------------------------------------------------------------------

class TestSetBasinDirect:
    def test_modify_and_readback(self, tmp_run):
        HmsRun.set_basin_direct(tmp_run, "1%(100YR)RUN", "NewBasin")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_info = [r for r in runs if r["name"] == "1%(100YR)RUN"][0]
        assert run_info["basin"] == "NewBasin"

    def test_other_runs_unchanged(self, tmp_run):
        """Runs without 'Basin:' in description should be unaffected."""
        HmsRun.set_basin_direct(tmp_run, "1%(100YR)RUN", "NewBasin")
        runs = HmsRun.list_runs_direct(tmp_run)
        # Use '1% A120D Split' which has Default Description: Yes (no 'Basin:' in desc)
        run_split = [r for r in runs if r["name"] == "1% A120D Split"][0]
        assert run_split["basin"] == "1PCT_A120D_Split"


# ---------------------------------------------------------------------------
# set_precip_direct
# ---------------------------------------------------------------------------

class TestSetPrecipDirect:
    def test_modify_and_readback(self, tmp_run):
        HmsRun.set_precip_direct(tmp_run, "1%(100YR)RUN", "NewMet")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_info = [r for r in runs if r["name"] == "1%(100YR)RUN"][0]
        assert run_info["precip"] == "NewMet"

    def test_other_runs_unchanged(self, tmp_run):
        HmsRun.set_precip_direct(tmp_run, "1%(100YR)RUN", "NewMet")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_10 = [r for r in runs if r["name"] == "10%(10YR)RUN"][0]
        assert run_10["precip"] == "10%_24HR"


# ---------------------------------------------------------------------------
# set_control_direct
# ---------------------------------------------------------------------------

class TestSetControlDirect:
    def test_modify_and_readback(self, tmp_run):
        HmsRun.set_control_direct(tmp_run, "1%(100YR)RUN", "NewControl")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_info = [r for r in runs if r["name"] == "1%(100YR)RUN"][0]
        assert run_info["control"] == "NewControl"

    def test_other_runs_unchanged(self, tmp_run):
        HmsRun.set_control_direct(tmp_run, "1%(100YR)RUN", "NewControl")
        runs = HmsRun.list_runs_direct(tmp_run)
        run_10 = [r for r in runs if r["name"] == "10%(10YR)RUN"][0]
        assert run_10["control"] == "Control 5"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            HmsRun.list_runs_direct(tmp_path / "nonexistent.run")

    def test_missing_run_name(self, run_path):
        with pytest.raises(ValueError):
            HmsRun.get_dss_file_direct(run_path, "NONEXISTENT_RUN")
