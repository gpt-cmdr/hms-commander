"""Regression tests: HmsCmdr must not report an aborted HEC-HMS run as a success.

The run logs under ``tests/fixtures/hms_run_logs`` were captured from real
computes of the HEC-HMS 4.13 ``tenk`` sample (see the README there). HEC-HMS
4.10 aborts that project, yet the process exits normally and, before this
fix, ``HmsCmdr.compute_run`` returned True. Without ``hms_exe_path`` the old
discovery also picked 4.10 first, because folder names sorted as text.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest

from hms_commander import HmsCmdr, HmsExamples, HmsJython, HmsPrj

TESTS_DIR = Path(__file__).parent
LOGS = TESTS_DIR / "fixtures" / "hms_run_logs"
ABORTED_LOG = LOGS / "tenk_hms410_aborted_run_log.txt"
FINISHED_LOG = LOGS / "tenk_hms413_finished_run_log.txt"
ABORTED_STDOUT = LOGS / "tenk_hms410_aborted_stdout.txt"
PROJECT_411 = TESTS_DIR / "projects" / "2014.08_HMS" / "A1000000_upgrade_411"
PROJECT_33 = TESTS_DIR / "projects" / "2014.08_HMS" / "A1000000_baseline_33"
RUN = "1%(100YR)RUN"  # Log File: A100B100_1_.log, DSS File: A1000000.dss


# ---------------------------------------------------------------------------
# Run-log judgement on real logs
# ---------------------------------------------------------------------------

def test_aborted_log_is_a_failure():
    ok, reason, lines = HmsCmdr._check_run_log(ABORTED_LOG.read_text())
    assert ok is False
    assert "15303" in reason
    assert any(line.startswith("ERROR 20137:") for line in lines)
    assert any(line.startswith("WARNING 15303:") for line in lines)


def test_finished_log_with_warnings_is_a_success():
    text = FINISHED_LOG.read_text()
    assert "WARNING 40503" in text  # warnings alone do not fail a run
    ok, reason, lines = HmsCmdr._check_run_log(text)
    assert ok is True, reason
    assert lines == []


def test_only_the_last_run_in_a_log_counts():
    # An earlier aborted attempt followed by a finished run in the same file
    text = ABORTED_LOG.read_text() + FINISHED_LOG.read_text()
    assert HmsCmdr._check_run_log(text)[0] is True
    text = FINISHED_LOG.read_text() + ABORTED_LOG.read_text()
    assert HmsCmdr._check_run_log(text)[0] is False


def test_log_without_finish_note_is_a_failure():
    began_only = FINISHED_LOG.read_text().split("NOTE 15302")[0]
    ok, reason, _ = HmsCmdr._check_run_log(began_only)
    assert ok is False and "15302" in reason
    assert HmsCmdr._check_run_log("")[0] is False


def test_generated_script_failure_line_is_recognised():
    stdout = ABORTED_STDOUT.read_text()
    assert any(m in stdout for m in HmsJython.SCRIPT_FAILURE_MARKERS)
    # The successful run prints no failure marker
    assert not any(
        m in "Project opened successfully: tenk\nComputation completed for: Jan 96 storm\n"
        for m in HmsJython.SCRIPT_FAILURE_MARKERS
    )


# ---------------------------------------------------------------------------
# _verify_run on a real project folder
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    dest = tmp_path / "A1000000"
    shutil.copytree(PROJECT_411, dest)
    prj = HmsPrj().initialize(dest)
    return prj


def _outputs(prj):
    return HmsCmdr._run_output_files(prj, RUN, prj.project_folder)


def _write_outputs(prj, log_fixture: Path, age_s: float = 0.0):
    log_path, dss_path = _outputs(prj)
    log_path.write_text(log_fixture.read_text())
    dss_path.write_bytes(b"results")
    if age_s:
        old = time.time() - age_s
        os.utime(log_path, (old, old))
        os.utime(dss_path, (old, old))
    return log_path, dss_path


def test_output_names_come_from_the_run_file(project):
    log_path, dss_path = _outputs(project)
    assert log_path.name == "A100B100_1_.log"
    assert dss_path.name == "A1000000.dss"


def test_fresh_finished_run_is_verified(project):
    start = time.time()
    _write_outputs(project, FINISHED_LOG)
    assert HmsCmdr._verify_run(True, RUN, project.project_folder, start, project) is True


def test_fresh_aborted_run_fails_even_with_a_new_dss(project):
    # HEC-HMS 4.10 created the results DSS before it aborted
    start = time.time()
    _write_outputs(project, ABORTED_LOG)
    assert HmsCmdr._verify_run(True, RUN, project.project_folder, start, project) is False


def test_shipped_results_from_an_earlier_run_fail(project):
    # A finished log and DSS that predate this run (for example a sample's
    # shipped results) are not evidence that this run computed.
    _write_outputs(project, FINISHED_LOG, age_s=3600)
    start = time.time()
    assert HmsCmdr._verify_run(True, RUN, project.project_folder, start, project) is False


def test_stale_results_dss_fails(project):
    start = time.time()
    log_path, dss_path = _write_outputs(project, FINISHED_LOG)
    old = start - 3600
    os.utime(dss_path, (old, old))
    assert HmsCmdr._verify_run(True, RUN, project.project_folder, start, project) is False


def test_missing_log_fails(project):
    log_path, _ = _outputs(project)
    log_path.unlink(missing_ok=True)
    assert HmsCmdr._verify_run(True, RUN, project.project_folder, time.time(), project) is False


def test_failed_script_stays_a_failure(project):
    start = time.time()
    _write_outputs(project, FINISHED_LOG)
    assert HmsCmdr._verify_run(False, RUN, project.project_folder, start, project) is False


def test_failure_reason_and_log_lines_are_logged(project, caplog):
    import logging
    start = time.time()
    _write_outputs(project, ABORTED_LOG)
    logger = logging.getLogger("hms_commander.HmsCmdr")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.ERROR, logger="hms_commander.HmsCmdr"):
            HmsCmdr._verify_run(True, RUN, project.project_folder, start, project)
    finally:
        logger.removeHandler(caplog.handler)
    text = caplog.text
    assert "aborted the run" in text
    assert "ERROR 20137" in text


# ---------------------------------------------------------------------------
# Version selection
# ---------------------------------------------------------------------------

@pytest.fixture
def installs(tmp_path):
    """A folder layout like C:/Program Files/HEC/HEC-HMS with several versions."""
    base = tmp_path / "HEC-HMS"
    for name in ["4.7.1", "4.9", "4.10", "4.11", "4.13"]:
        (base / name).mkdir(parents=True)
        (base / name / "hms.jar").write_bytes(b"")
    (base / "notes").mkdir()  # not an installation
    return base


def _find(installs, version=None):
    return HmsJython.find_hms_executable(
        version=version, search_paths=[installs], include_defaults=False
    )


def test_installs_are_ordered_by_number(installs):
    names = list(HmsJython._installed_hms_versions([installs], include_defaults=False))
    assert names == ["4.13", "4.11", "4.10", "4.9", "4.7.1"]


def test_no_version_selects_the_newest(installs):
    assert _find(installs).name == "4.13"


def test_project_version_is_selected_exactly(installs):
    version = HmsPrj().initialize(PROJECT_411).hms_version
    assert version == "4.11"
    assert _find(installs, version).name == "4.11"


def test_same_major_minor_is_used(installs):
    assert _find(installs, "4.7").name == "4.7.1"


def test_next_newer_version_is_used(installs):
    assert _find(installs, "4.12").name == "4.13"
    version = HmsPrj().initialize(PROJECT_33).hms_version
    assert version == "3.3"
    assert _find(installs, version).name == "4.7.1"


def test_an_older_version_is_never_substituted(installs):
    shutil.rmtree(installs / "4.13")
    assert _find(installs, "4.13") is None
    assert _find(installs, "4.14") is None


def test_compute_setup_uses_the_project_version(installs, tmp_path):
    dest = tmp_path / "A1000000"
    shutil.copytree(PROJECT_411, dest)
    prj = HmsPrj().initialize(dest)
    exe = HmsCmdr._ensure_hms_executable(prj, search_paths=[installs], include_defaults=False)
    assert exe.name == "4.11" and prj.hms_exe_path == exe


def test_compute_setup_refuses_when_only_older_versions_exist(installs, tmp_path):
    for name in ["4.11", "4.13"]:
        shutil.rmtree(installs / name)
    dest = tmp_path / "A1000000"
    shutil.copytree(PROJECT_411, dest)
    prj = HmsPrj().initialize(dest)
    with pytest.raises(RuntimeError, match="4.11"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[installs], include_defaults=False)
    assert prj.hms_exe_path is None


def test_explicit_executable_is_kept(installs, tmp_path):
    dest = tmp_path / "A1000000"
    shutil.copytree(PROJECT_411, dest)
    prj = HmsPrj().initialize(dest, hms_exe_path=installs / "4.9")
    exe = HmsCmdr._ensure_hms_executable(prj, search_paths=[installs], include_defaults=False)
    assert exe == installs / "4.9"


# ---------------------------------------------------------------------------
# Real HEC-HMS: tenk with its own version and with a mismatched one
# ---------------------------------------------------------------------------

def _installed(version):
    try:
        return HmsExamples.get_hms_exe(version)
    except (ValueError, FileNotFoundError):
        return None


def _fresh_tenk(tmp_path, name):
    folder = HmsExamples.extract_project("tenk", version="4.13", output_path=tmp_path / name)
    for stale in ("Jan_96_storm.dss", "Jan_96_storm.log"):
        (folder / stale).unlink(missing_ok=True)
    return folder


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_tenk_computes_with_its_declared_version(tmp_path):
    if _installed("4.13") is None:
        pytest.skip("HEC-HMS 4.13 not installed")
    folder = _fresh_tenk(tmp_path, "own")
    prj = HmsPrj().initialize(folder)  # no hms_exe_path: chosen from Version: 4.13
    assert prj.hms_version == "4.13"
    assert HmsCmdr.compute_run("Jan 96 storm", hms_object=prj, timeout=900) is True
    assert Path(prj.hms_exe_path).name == "4.13"
    assert "NOTE 15302" in (folder / "Jan_96_storm.log").read_text()


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_tenk_on_hms_410_is_reported_as_failed(tmp_path):
    if _installed("4.13") is None or _installed("4.10") is None:
        pytest.skip("HEC-HMS 4.13 sample and HEC-HMS 4.10 both needed")
    folder = _fresh_tenk(tmp_path, "mismatch")
    prj = HmsPrj().initialize(folder, hms_exe_path=_installed("4.10"))
    assert HmsCmdr.compute_run("Jan 96 storm", hms_object=prj, timeout=900) is False
    assert "WARNING 15303" in (folder / "Jan_96_storm.log").read_text()
