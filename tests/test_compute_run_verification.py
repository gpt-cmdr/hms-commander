"""Regression tests: HmsCmdr must not report an aborted HEC-HMS run as a success.

The run logs under ``tests/fixtures/hms_run_logs`` were captured from real
HEC-HMS computes of the 4.13 ``tenk`` and ``castro`` samples, and the ``.run``
files are the shipped sample files (see the README there). HEC-HMS 4.10
aborts ``tenk``, yet the process exits normally and, before this fix,
``HmsCmdr.compute_run`` returned True. Without ``hms_exe_path`` the old
discovery also picked 4.10 first, because folder names sorted as text.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from hms_commander import HmsCmdr, HmsExamples, HmsJython, HmsPrj

TESTS_DIR = Path(__file__).parent
LOGS = TESTS_DIR / "fixtures" / "hms_run_logs"
RUN_FILES = LOGS / "run_files"
TENK_ABORTED = LOGS / "tenk_hms410_aborted_run_log.txt"
TENK_FINISHED = LOGS / "tenk_hms413_finished_run_log.txt"
TENK_ABORTED_STDOUT = LOGS / "tenk_hms410_aborted_stdout.txt"
CASTRO_FUTURE_FINISHED = LOGS / "castro_hms413_future_finished_run_log.txt"
CASTRO_FUTURE_ABORTED = LOGS / "castro_hms413_future_aborted_run_log.txt"
PROJECT_411 = TESTS_DIR / "projects" / "2014.08_HMS" / "A1000000_upgrade_411"
PROJECT_33 = TESTS_DIR / "projects" / "2014.08_HMS" / "A1000000_baseline_33"
TENK = "Jan 96 storm"   # Log File: Jan_96_storm.log, DSS File: Jan_96_storm.dss
FUTURE = "Future"       # Log File: Future.log, DSS File: Future.dss


def _text(path: Path) -> str:
    return path.read_bytes().decode("latin-1")


def _bytes(*paths: Path) -> bytes:
    return b"".join(p.read_bytes() for p in paths)


# ---------------------------------------------------------------------------
# Run-log judgement on real logs
# ---------------------------------------------------------------------------

def test_aborted_log_is_a_failure():
    ok, reason, lines = HmsCmdr._check_run_log(_text(TENK_ABORTED), TENK)
    assert ok is False
    assert "15303" in reason
    assert any(line.startswith("ERROR 20137:") for line in lines)
    assert any(line.startswith("WARNING 15303:") for line in lines)


def test_finished_log_with_warnings_is_a_success():
    text = _text(TENK_FINISHED)
    assert "WARNING 40503" in text  # warnings alone do not fail a run
    ok, reason, lines = HmsCmdr._check_run_log(text, TENK)
    assert ok is True, reason
    assert lines == []


def test_a_log_of_another_run_is_not_evidence():
    # A finished "Jan 96 storm" log says nothing about run "Future"
    ok, reason, _ = HmsCmdr._check_run_log(_text(TENK_FINISHED), FUTURE)
    assert ok is False and "Future" in reason


def test_only_the_last_attempt_of_the_run_counts():
    assert HmsCmdr._check_run_log(_text(TENK_ABORTED) + _text(TENK_FINISHED), TENK)[0] is True
    assert HmsCmdr._check_run_log(_text(TENK_FINISHED) + _text(TENK_ABORTED), TENK)[0] is False


def test_log_without_finish_note_is_a_failure():
    began_only = _text(TENK_FINISHED).split("NOTE 15302")[0]
    ok, reason, _ = HmsCmdr._check_run_log(began_only, TENK)
    assert ok is False and "15302" in reason
    assert HmsCmdr._check_run_log("", TENK)[0] is False


# Review 1, finding 2: two real run blocks of different runs in one log


@pytest.mark.parametrize("order", ["target_first", "target_last"])
def test_finished_target_is_not_failed_by_another_runs_abort(order):
    blocks = [_text(TENK_FINISHED), _text(CASTRO_FUTURE_ABORTED)]
    text = "".join(blocks if order == "target_first" else blocks[::-1])
    assert HmsCmdr._check_run_log(text, TENK)[0] is True
    assert HmsCmdr._check_run_log(text, FUTURE)[0] is False


@pytest.mark.parametrize("order", ["target_first", "target_last"])
def test_aborted_target_is_not_credited_with_another_runs_success(order):
    blocks = [_text(TENK_ABORTED), _text(CASTRO_FUTURE_FINISHED)]
    text = "".join(blocks if order == "target_first" else blocks[::-1])
    ok, _, lines = HmsCmdr._check_run_log(text, TENK)
    assert ok is False
    assert any(line.startswith("ERROR 20137:") for line in lines)
    assert HmsCmdr._check_run_log(text, FUTURE)[0] is True


def test_sample_run_logs_name_their_run():
    """Every shipped sample run log quotes its own run name in NOTE 15301 and 15302."""
    for path, name in [(TENK_FINISHED, TENK), (CASTRO_FUTURE_FINISHED, FUTURE)]:
        text = _text(path)
        assert re.search(rf'^NOTE 15301:\s+Began computing simulation run "{name}"', text, re.M)
        assert re.search(rf'^NOTE 15302:\s+Finished computing simulation run "{name}"', text, re.M)


# ---------------------------------------------------------------------------
# The generated script's failure line, through the HMS 4.x execution path
# ---------------------------------------------------------------------------

def test_execute_via_java_fails_on_the_script_failure_line(tmp_path, monkeypatch):
    """HEC-HMS exits with 0 after the 4.10 abort; the stdout line decides."""
    install = tmp_path / "4.10"
    (install / "jre" / "bin").mkdir(parents=True)
    (install / "jre" / "bin" / "java.exe").write_bytes(b"")
    (install / "hms.jar").write_bytes(b"")
    script = tmp_path / "hms_script.py"
    script.write_text("# script")
    captured = TENK_ABORTED_STDOUT.read_text()

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=captured, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    ok, stdout, _ = HmsJython._execute_via_java(script, install)
    assert ok is False and stdout == captured

    finished = "Project opened successfully: tenk\nComputation completed for: Jan 96 storm\n"
    monkeypatch.setattr(
        subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=finished, stderr=""),
    )
    assert HmsJython._execute_via_java(script, install)[0] is True


# ---------------------------------------------------------------------------
# _verify_run against a pre-launch snapshot (review 1, finding 1)
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """A folder with the shipped tenk.run and castro.run sample files."""
    folder = tmp_path / "project"
    folder.mkdir()
    for name in ("tenk.run", "castro.run"):
        shutil.copy(RUN_FILES / name, folder / name)
    return folder


def _paths(folder, run=TENK):
    log, dss, problem = HmsCmdr._run_output_files(folder, run)
    assert problem == ""
    return log, dss


def _set_mtime_ns(path: Path, mtime_ns: int):
    os.utime(path, ns=(mtime_ns, mtime_ns))


def test_output_names_come_from_the_run_file(project):
    log, dss = _paths(project)
    assert (log.name, dss.name) == ("Jan_96_storm.log", "Jan_96_storm.dss")


def test_new_finished_log_and_new_dss_are_verified(project):
    snap = HmsCmdr._snapshot_run(project, TENK)
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is True


def test_aborted_run_fails_even_with_a_new_dss(project):
    # HEC-HMS 4.10 created the results DSS before it aborted
    snap = HmsCmdr._snapshot_run(project, TENK)
    log, dss = _paths(project)
    log.write_bytes(TENK_ABORTED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is False


def test_unchanged_recent_outputs_fail(project):
    # Written a moment before launch and not touched by the run
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results")
    snap = HmsCmdr._snapshot_run(project, TENK)
    assert HmsCmdr._verify_run(True, snap) is False
    # The prior log is put back when the run wrote none
    assert log.read_bytes() == TENK_FINISHED.read_bytes()
    assert not HmsCmdr._log_backup_path(log).exists()


# Review 2, finding 2: a run log replaced by identical bytes


def test_byte_identical_log_replacement_is_new_evidence(project):
    """A short repeated run can write exactly the same log bytes."""
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results A")
    stamp = log.stat().st_mtime_ns
    snap = HmsCmdr._snapshot_run(project, TENK)
    assert not log.exists()                                  # moved aside
    assert HmsCmdr._log_backup_path(log).read_bytes() == TENK_FINISHED.read_bytes()
    log.write_bytes(TENK_FINISHED.read_bytes())              # same bytes
    _set_mtime_ns(log, stamp)                                # and the same time
    dss.write_bytes(b"results B")
    assert HmsCmdr._verify_run(True, snap) is True
    assert not HmsCmdr._log_backup_path(log).exists()        # backup removed
    assert log.read_bytes() == TENK_FINISHED.read_bytes()


def test_prior_log_is_put_back_after_a_failed_run_without_a_log(project):
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    snap = HmsCmdr._snapshot_run(project, TENK)
    assert HmsCmdr._verify_run(False, snap) is False
    assert log.read_bytes() == TENK_FINISHED.read_bytes()
    assert not HmsCmdr._log_backup_path(log).exists()


def test_a_failed_run_keeps_its_own_new_log(project):
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    snap = HmsCmdr._snapshot_run(project, TENK)
    log.write_bytes(TENK_ABORTED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is False
    assert log.read_bytes() == TENK_ABORTED.read_bytes()
    assert not HmsCmdr._log_backup_path(log).exists()


def test_a_stale_backup_from_an_interrupted_call_is_replaced(project):
    log, dss = _paths(project)
    HmsCmdr._log_backup_path(log).write_bytes(b"left over")
    log.write_bytes(TENK_ABORTED.read_bytes())
    snap = HmsCmdr._snapshot_run(project, TENK)
    assert HmsCmdr._log_backup_path(log).read_bytes() == TENK_ABORTED.read_bytes()
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is True


def test_prior_log_is_put_back_when_launch_raises(project, monkeypatch):
    log, _ = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())

    def boom(**kwargs):
        raise FileNotFoundError("HMS path not found")

    monkeypatch.setattr(HmsJython, "execute_script", staticmethod(boom))
    with pytest.raises(FileNotFoundError):
        HmsCmdr._execute_and_verify(TENK, project, "# script", hms_exe_path=project)
    assert log.read_bytes() == TENK_FINISHED.read_bytes()
    assert not HmsCmdr._log_backup_path(log).exists()


@pytest.mark.parametrize("skew_s", [-10, +10])
def test_changed_outputs_pass_whatever_the_file_server_clock(project, skew_s):
    """A share whose clock is 10 s behind or ahead of this computer."""
    log, dss = _paths(project)
    log.write_bytes(TENK_ABORTED.read_bytes())
    dss.write_bytes(b"old results")
    snap = HmsCmdr._snapshot_run(project, TENK)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"new results, written by the run")
    for path in (log, dss):
        _set_mtime_ns(path, path.stat().st_mtime_ns + skew_s * 1_000_000_000)
    assert HmsCmdr._verify_run(True, snap) is True


def test_unchanged_outputs_fail_even_with_a_future_time(project):
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results")
    ahead = log.stat().st_mtime_ns + 3600 * 1_000_000_000
    for path in (log, dss):
        _set_mtime_ns(path, ahead)
    snap = HmsCmdr._snapshot_run(project, TENK)
    assert HmsCmdr._verify_run(True, snap) is False


def test_rewrites_with_equal_size_and_time_are_detected(project):
    """Coarse (FAT, network) timestamps: the content decides."""
    log, dss = _paths(project)
    old_log = TENK_FINISHED.read_bytes().replace(b"19:29:", b"18:29:")  # same length
    log.write_bytes(old_log)
    dss.write_bytes(b"results A")
    stamp_log, stamp_dss = log.stat().st_mtime_ns, dss.stat().st_mtime_ns
    snap = HmsCmdr._snapshot_run(project, TENK)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results B")
    _set_mtime_ns(log, stamp_log)
    _set_mtime_ns(dss, stamp_dss)
    assert len(old_log) == log.stat().st_size
    assert HmsCmdr._verify_run(True, snap) is True


def test_unchanged_dss_fails_although_the_log_changed(project):
    log, dss = _paths(project)
    dss.write_bytes(b"results")
    snap = HmsCmdr._snapshot_run(project, TENK)
    log.write_bytes(TENK_FINISHED.read_bytes())
    assert HmsCmdr._verify_run(True, snap) is False


def test_a_finished_section_followed_by_a_new_abort_fails(project):
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())     # an earlier, finished run
    snap = HmsCmdr._snapshot_run(project, TENK)
    log.write_bytes(TENK_FINISHED.read_bytes() + TENK_ABORTED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is False


def test_missing_log_fails(project):
    snap = HmsCmdr._snapshot_run(project, TENK)
    _, dss = _paths(project)
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(True, snap) is False


def test_failed_script_stays_a_failure(project):
    snap = HmsCmdr._snapshot_run(project, TENK)
    log, dss = _paths(project)
    log.write_bytes(TENK_FINISHED.read_bytes())
    dss.write_bytes(b"results")
    assert HmsCmdr._verify_run(False, snap) is False


def test_failure_reason_and_log_lines_are_logged(project, caplog):
    snap = HmsCmdr._snapshot_run(project, TENK)
    log, dss = _paths(project)
    log.write_bytes(TENK_ABORTED.read_bytes())
    dss.write_bytes(b"results")
    logger = logging.getLogger("hms_commander.HmsCmdr")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.ERROR, logger="hms_commander.HmsCmdr"):
            HmsCmdr._verify_run(True, snap)
    finally:
        logger.removeHandler(caplog.handler)
    assert "aborted the run" in caplog.text
    assert "ERROR 20137" in caplog.text


# Review 1, finding 2: a log file shared by two runs


@pytest.fixture
def shared_project(project):
    """tenk.run and castro.run with "Jan 96 storm" and "Future" writing shared.log."""
    for name in ("tenk.run", "castro.run"):
        path = project / name
        path.write_text(re.sub(r"Log File: .*", "Log File: shared.log", path.read_text()))
    return project


def test_shared_log_runs_are_detected(shared_project):
    groups = HmsCmdr._shared_log_runs(shared_project, [TENK, FUTURE, "Current"])
    assert list(groups.values()) == [[TENK, FUTURE, "Current"]]


@pytest.mark.parametrize(
    "target_block, other_block, target_ok",
    [(TENK_FINISHED, CASTRO_FUTURE_ABORTED, True), (TENK_ABORTED, CASTRO_FUTURE_FINISHED, False)],
)
def test_shared_log_credits_each_run_with_its_own_block(shared_project, target_block, other_block, target_ok):
    log, tenk_dss = _paths(shared_project, TENK)
    _, future_dss = _paths(shared_project, FUTURE)
    for order in ([target_block, other_block], [other_block, target_block]):
        snaps = {run: HmsCmdr._snapshot_run(shared_project, run) for run in (TENK, FUTURE)}
        log.write_bytes(_bytes(*order))
        tenk_dss.write_bytes(b"tenk results")
        future_dss.write_bytes(b"castro results")
        assert HmsCmdr._verify_run(True, snaps[TENK]) is target_ok
        assert HmsCmdr._verify_run(True, snaps[FUTURE]) is (not target_ok)
        for path in (log, tenk_dss, future_dss):
            path.unlink()


def test_a_log_holding_only_another_runs_section_is_not_evidence(shared_project):
    # Observed with HEC-HMS 4.13: in one session, a shared Log File holds only
    # the last run's section. compute_batch therefore runs such runs in
    # separate sessions (see the wrapper tests below).
    snaps = {run: HmsCmdr._snapshot_run(shared_project, run) for run in (TENK, FUTURE)}
    log, tenk_dss = _paths(shared_project, TENK)
    _, future_dss = _paths(shared_project, FUTURE)
    log.write_bytes(CASTRO_FUTURE_FINISHED.read_bytes())
    tenk_dss.write_bytes(b"tenk results")
    future_dss.write_bytes(b"castro results")
    assert HmsCmdr._verify_run(True, snaps[TENK]) is False
    assert HmsCmdr._verify_run(True, snaps[FUTURE]) is True


# Review 2, finding 1: compute_batch keeps each shared-log run's evidence


def _batch_project(tmp_path, shared: bool):
    """The committed A1000000 project plus the shipped tenk.run and castro.run."""
    folder = tmp_path / "batch"
    shutil.copytree(PROJECT_411, folder)
    for name in ("tenk.run", "castro.run"):
        text = (RUN_FILES / name).read_text()
        if shared:
            text = re.sub(r"Log File: .*", "Log File: shared.log", text)
        (folder / name).write_text(text)
    install = tmp_path / "HEC-HMS" / "4.13"
    install.mkdir(parents=True)
    (install / "hms.jar").write_bytes(b"")
    return HmsPrj().initialize(folder, hms_exe_path=install)


def _fake_hms(monkeypatch, sections):
    """
    Stand in for HEC-HMS: for each run named in the script, in order, rewrite
    that run's log with its real captured section (as HEC-HMS 4.13 rewrites a
    shared log for every run) and write its results DSS. Records each session.
    """
    sessions = []

    def execute_script(script_content, hms_exe_path, working_dir=None, **kwargs):
        names = ast.literal_eval(re.search(r"^run_names = (\[.*\])$", script_content, re.M).group(1))
        sessions.append(list(names))
        stdout = ""
        for name in names:
            log, dss, _ = HmsCmdr._run_output_files(working_dir, name)
            log.write_bytes(sections[name].read_bytes())
            dss.write_bytes(f"results of {name}, session {len(sessions)}".encode())
            stdout += f"Completed: {name}\n"
        return True, stdout, ""

    monkeypatch.setattr(HmsJython, "execute_script", staticmethod(execute_script))
    return sessions


def test_batch_with_a_shared_log_verifies_every_successful_run(tmp_path, monkeypatch):
    prj = _batch_project(tmp_path, shared=True)
    sessions = _fake_hms(monkeypatch, {TENK: TENK_FINISHED, FUTURE: CASTRO_FUTURE_FINISHED})
    assert HmsCmdr.compute_batch([TENK, FUTURE], hms_object=prj) == {TENK: True, FUTURE: True}
    assert sessions == [[TENK], [FUTURE]]          # one session per run, in order


def test_batch_with_a_shared_log_still_fails_an_aborted_run(tmp_path, monkeypatch):
    prj = _batch_project(tmp_path, shared=True)
    _fake_hms(monkeypatch, {TENK: TENK_ABORTED, FUTURE: CASTRO_FUTURE_FINISHED})
    assert HmsCmdr.compute_batch([TENK, FUTURE], hms_object=prj) == {TENK: False, FUTURE: True}
    _fake_hms(monkeypatch, {TENK: TENK_FINISHED, FUTURE: CASTRO_FUTURE_ABORTED})
    assert HmsCmdr.compute_batch([TENK, FUTURE], hms_object=prj) == {TENK: True, FUTURE: False}


def test_batch_without_shared_logs_uses_one_session(tmp_path, monkeypatch):
    prj = _batch_project(tmp_path, shared=False)
    sessions = _fake_hms(monkeypatch, {TENK: TENK_FINISHED, FUTURE: CASTRO_FUTURE_ABORTED})
    assert HmsCmdr.compute_batch([TENK, FUTURE], hms_object=prj) == {TENK: True, FUTURE: False}
    assert sessions == [[TENK, FUTURE]]


# Review 1, finding 5: results DSS (and log) metadata that cannot be found


def _edit_tenk_run(folder: Path, pattern: str, replacement: str):
    path = folder / "tenk.run"
    text = path.read_text()
    assert re.search(pattern, text)
    path.write_text(re.sub(pattern, replacement, text))


@pytest.mark.parametrize(
    "pattern, replacement, words",
    [
        (r"     DSS File: .*\n", "", "DSS File"),             # entry missing
        (r"DSS File: .*", "DSS File: ", "DSS File"),          # entry blank
        (r"     Log File: .*\n", "", "Log File"),             # log entry missing
    ],
)
def test_missing_output_metadata_fails_clearly(project, pattern, replacement, words, caplog):
    _edit_tenk_run(project, pattern, replacement)
    snap = HmsCmdr._snapshot_run(project, TENK)
    (project / "Jan_96_storm.log").write_bytes(TENK_FINISHED.read_bytes())
    (project / "Jan_96_storm.dss").write_bytes(b"results")
    logger = logging.getLogger("hms_commander.HmsCmdr")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.ERROR, logger="hms_commander.HmsCmdr"):
            assert HmsCmdr._verify_run(True, snap) is False
    finally:
        logger.removeHandler(caplog.handler)
    assert words in caplog.text and "cannot be verified" in caplog.text


def test_run_missing_from_the_run_files_fails(project):
    snap = HmsCmdr._snapshot_run(project, "No such run")
    assert "not defined" in snap["problem"]
    assert HmsCmdr._verify_run(True, snap) is False


def test_run_metadata_is_read_from_the_working_folder(project):
    # The .run file as it is now, not a DataFrame loaded earlier
    _edit_tenk_run(project, r"DSS File: .*", "DSS File: renamed.dss")
    _, dss = _paths(project)
    assert dss.name == "renamed.dss"


# ---------------------------------------------------------------------------
# Version selection (review 1, findings 3 and 4)
# ---------------------------------------------------------------------------

def _layout(tmp_path, names):
    """A folder layout like C:/Program Files/HEC/HEC-HMS with the given versions."""
    base = tmp_path / "HEC-HMS"
    base.mkdir(exist_ok=True)
    for name in names:
        (base / name).mkdir()
        (base / name / "hms.jar").write_bytes(b"")
    return base


@pytest.fixture
def installs(tmp_path):
    base = _layout(tmp_path, ["4.7.1", "4.9", "4.10", "4.11", "4.13"])
    (base / "notes").mkdir()  # not an installation
    return base


def _find(base, version=None):
    return HmsJython.find_hms_executable(
        version=version, search_paths=[base], include_defaults=False
    )


def _name(path):
    return path.name if path is not None else None


def test_installs_are_ordered_by_number(installs):
    names = list(HmsJython._installed_hms_versions([installs], include_defaults=False))
    assert names == ["4.13", "4.11", "4.10", "4.9", "4.7.1"]


def test_no_version_selects_the_newest(installs):
    assert _find(installs).name == "4.13"


def test_project_version_is_selected_exactly(installs):
    version = HmsPrj().initialize(PROJECT_411).hms_version
    assert version == "4.11"
    assert _find(installs, version).name == "4.11"


def test_newer_patch_of_the_same_minor_is_used(installs):
    assert _find(installs, "4.7").name == "4.7.1"


def test_next_newer_minor_is_used(installs):
    assert _find(installs, "4.12").name == "4.13"
    version = HmsPrj().initialize(PROJECT_33).hms_version
    assert version == "3.3"
    assert _find(installs, version).name == "4.7.1"


def test_an_older_minor_is_never_substituted(installs):
    shutil.rmtree(installs / "4.13")
    assert _find(installs, "4.13") is None
    assert _find(installs, "4.14") is None


@pytest.mark.parametrize(
    "installed, wanted, expected",
    [
        (["4.4", "4.5", "4.13"], "4.4.1", "4.5"),        # older patch skipped
        (["4.4"], "4.4.1", None),                         # only an older patch
        (["4.4", "4.4.2", "4.4.3"], "4.4.1", "4.4.3"),    # newer patch, same minor
        (["4.4.0", "4.5"], "4.4", "4.4.0"),               # 4.4.0 equals 4.4
        (["4.5", "4.6", "4.6.1"], "4.4.1", "4.5"),        # nearest newer minor
    ],
)
def test_patch_versions(tmp_path, installed, wanted, expected):
    assert _name(_find(_layout(tmp_path, installed), wanted)) == expected


@pytest.mark.parametrize(
    "installed, wanted, expected",
    [
        (["4.10", "4.13"], "4.13-beta", "4.13"),          # release after its beta
        (["4.13-beta"], "4.13-beta", "4.13-beta"),        # exact name first
        (["4.13-beta", "4.12"], "4.13", None),            # a beta is older than 4.13
        (["4.13-beta", "4.13"], None, "4.13"),            # newest is the release
        (["4.12", "4.13-beta"], "4.12.1", "4.13-beta"),   # next newer minor
        (["4.13-rc1", "4.13-beta"], "4.13-alpha", "4.13-rc1"),
        (["4.13-rc2"], "4.13-rc10", None),                # rc2 is older than rc10
        (["4.13-rc2", "4.13-rc10"], "4.13-rc3", "4.13-rc10"),
        (["4.13-beta2"], "4.13-beta10", None),            # beta2 is older than beta10
        (["4.13-beta10", "4.13-rc2"], "4.13-beta2", "4.13-rc2"),
        (["4.13-rc2", "4.13-rc10"], None, "4.13-rc10"),   # newest is rc10
        (["4.13 Beta 2"], "4.13-beta2", "4.13 Beta 2"),   # separators and case ignored
    ],
)
def test_suffixed_versions(tmp_path, installed, wanted, expected):
    assert _name(_find(_layout(tmp_path, installed), wanted)) == expected


def test_version_ordering():
    names = ["4.13", "4.13.1", "4.9", "4.13-beta", "4.10", "4.13-rc1", "4.4", "4.4.1"]
    assert sorted(names, key=HmsJython._parse_version_text) == [
        "4.4", "4.4.1", "4.9", "4.10", "4.13-beta", "4.13-rc1", "4.13", "4.13.1"
    ]
    numbered = ["4.13-rc10", "4.13-beta10", "4.13-rc2", "4.13-beta2", "4.13-beta", "4.13-alpha1"]
    assert sorted(numbered, key=HmsJython._parse_version_text) == [
        "4.13-alpha1", "4.13-beta", "4.13-beta2", "4.13-beta10", "4.13-rc2", "4.13-rc10"
    ]
    key = HmsJython._parse_version_text
    assert key("4.13-rc2") < key("4.13-rc10") and key("4.13-beta2") < key("4.13-beta10")
    assert key("4.13b2") == key("4.13 Beta 2") == key("4.13-beta.2")
    assert key("4.13-beta") == key("4.13-beta0")


@pytest.mark.parametrize("text", ["4.13-rc1-hotfix", "4.13 custom", "4.13-pre1", "4.13-rc2b", "custom build"])
def test_ambiguous_versions_do_not_parse(text):
    assert HmsJython._parse_version_text(text) is None


@pytest.mark.parametrize("version", ["4.13-rc1-hotfix", "4.13-rc2b"])
def test_compute_setup_refuses_an_ambiguous_project_version(tmp_path, version):
    base = _layout(tmp_path, ["4.13", "4.13-rc2"])
    prj = _project(tmp_path, version)
    with pytest.raises(RuntimeError, match="not a version format"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)


def test_compute_setup_refuses_an_older_numbered_prerelease(tmp_path):
    base = _layout(tmp_path, ["4.13-rc2"])
    prj = _project(tmp_path, "4.13-rc10")
    with pytest.raises(RuntimeError, match="4.13-rc10"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)
    assert HmsJython._parse_version_text("4.4.0") == HmsJython._parse_version_text("4.4")
    assert HmsJython._parse_version_text("not a version") is None


def test_runtime_version_of_a_suffixed_folder(tmp_path):
    assert HmsJython._get_hms_version(tmp_path / "4.13-beta") == (4, 13)
    assert HmsJython._get_hms_version(tmp_path / "4.7.1") == (4, 7, 1)


def _project(tmp_path, version=None):
    dest = tmp_path / "A1000000"
    shutil.copytree(PROJECT_411, dest)
    if version is not None:
        hms = dest / "A1000000.hms"
        hms.write_text(re.sub(r"Version: .*", f"Version: {version}", hms.read_text()))
    return HmsPrj().initialize(dest)


def test_compute_setup_uses_the_project_version(installs, tmp_path):
    prj = _project(tmp_path)
    exe = HmsCmdr._ensure_hms_executable(prj, search_paths=[installs], include_defaults=False)
    assert exe.name == "4.11" and prj.hms_exe_path == exe


def test_compute_setup_refuses_when_only_older_versions_exist(installs, tmp_path):
    for name in ["4.11", "4.13"]:
        shutil.rmtree(installs / name)
    prj = _project(tmp_path)
    with pytest.raises(RuntimeError, match="4.11"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[installs], include_defaults=False)
    assert prj.hms_exe_path is None


def test_compute_setup_refuses_an_older_patch(tmp_path):
    base = _layout(tmp_path, ["4.4"])
    prj = _project(tmp_path, "4.4.1")
    with pytest.raises(RuntimeError, match="4.4.1"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)


def test_compute_setup_accepts_a_suffixed_project_version(tmp_path):
    base = _layout(tmp_path, ["4.10", "4.13"])
    prj = _project(tmp_path, "4.13-beta")
    exe = HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)
    assert exe.name == "4.13"


def test_compute_setup_names_an_unparseable_version(tmp_path):
    base = _layout(tmp_path, ["4.13"])
    prj = _project(tmp_path, "custom build")
    with pytest.raises(RuntimeError, match="not a version format"):
        HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)


def test_explicit_executable_is_kept_with_a_warning_for_an_older_patch(tmp_path, caplog):
    base = _layout(tmp_path, ["4.4", "4.13"])
    prj = _project(tmp_path, "4.4.1")
    prj.hms_exe_path = base / "4.4"
    logger = logging.getLogger("hms_commander.HmsCmdr")
    logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.WARNING, logger="hms_commander.HmsCmdr"):
            exe = HmsCmdr._ensure_hms_executable(prj, search_paths=[base], include_defaults=False)
    finally:
        logger.removeHandler(caplog.handler)
    assert exe == base / "4.4"
    assert "older than the project's version 4.4.1" in caplog.text


# ---------------------------------------------------------------------------
# Real HEC-HMS
# ---------------------------------------------------------------------------

def _installed(version):
    """The HEC-HMS executable of ``version``, or None where it is not installed (CI)."""
    if version not in HmsExamples.detect_installed_versions():
        return None
    return HmsExamples.get_hms_exe(version)


def _fresh(tmp_path, project, name, stale):
    folder = HmsExamples.extract_project(project, version="4.13", output_path=tmp_path / name)
    for f in stale:
        (folder / f).unlink(missing_ok=True)
    return folder


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_tenk_computes_with_its_declared_version(tmp_path):
    if _installed("4.13") is None:
        pytest.skip("HEC-HMS 4.13 not installed")
    folder = _fresh(tmp_path, "tenk", "own", ["Jan_96_storm.dss", "Jan_96_storm.log"])
    prj = HmsPrj().initialize(folder)  # no hms_exe_path: chosen from Version: 4.13
    assert prj.hms_version == "4.13"
    assert HmsCmdr.compute_run(TENK, hms_object=prj, timeout=900) is True
    assert Path(prj.hms_exe_path).name == "4.13"
    assert "NOTE 15302" in (folder / "Jan_96_storm.log").read_text()


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_tenk_on_hms_410_is_reported_as_failed(tmp_path):
    if _installed("4.13") is None or _installed("4.10") is None:
        pytest.skip("HEC-HMS 4.13 sample and HEC-HMS 4.10 both needed")
    folder = _fresh(tmp_path, "tenk", "mismatch", ["Jan_96_storm.dss", "Jan_96_storm.log"])
    prj = HmsPrj().initialize(folder, hms_exe_path=_installed("4.10"))
    assert HmsCmdr.compute_run(TENK, hms_object=prj, timeout=900) is False
    assert "WARNING 15303" in (folder / "Jan_96_storm.log").read_text()


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_tenk_recompute_over_shipped_results_is_verified(tmp_path):
    """The shipped finished log and DSS are replaced by this run's."""
    if _installed("4.13") is None:
        pytest.skip("HEC-HMS 4.13 not installed")
    folder = _fresh(tmp_path, "tenk", "shipped", [])
    assert (folder / "Jan_96_storm.log").exists()
    prj = HmsPrj().initialize(folder)
    assert HmsCmdr.compute_run(TENK, hms_object=prj, timeout=900) is True


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_castro_batch_with_separate_and_shared_logs(tmp_path):
    if _installed("4.13") is None:
        pytest.skip("HEC-HMS 4.13 not installed")
    stale = ["Current.dss", "Future.dss", "Current.log", "Future.log"]

    separate = _fresh(tmp_path, "castro", "separate", stale)
    prj = HmsPrj().initialize(separate)
    assert HmsCmdr.compute_batch(["Current", "Future"], hms_object=prj) == {
        "Current": True, "Future": True,
    }

    shared = _fresh(tmp_path, "castro", "shared", stale)
    run_file = shared / "castro.run"
    run_file.write_text(re.sub(r"Log File: .*", "Log File: shared.log", run_file.read_text()))
    prj = HmsPrj().initialize(shared)
    # HEC-HMS rewrites a shared log for each run, so compute_batch runs each
    # run in its own session and verifies it before the next.
    assert HmsCmdr.compute_batch(["Current", "Future"], hms_object=prj) == {
        "Current": True, "Future": True,
    }
    assert "Future" in (shared / "shared.log").read_text()


@pytest.mark.requires_hms
@pytest.mark.local_hms
@pytest.mark.slow
def test_castro_batch_with_a_shared_log_reports_an_aborted_run(tmp_path):
    """A negative subbasin area in Future's basin model makes HEC-HMS abort Future."""
    if _installed("4.13") is None:
        pytest.skip("HEC-HMS 4.13 not installed")
    stale = ["Current.dss", "Future.dss", "Current.log", "Future.log"]
    shared = _fresh(tmp_path, "castro", "shared_abort", stale)
    run_file = shared / "castro.run"
    run_file.write_text(re.sub(r"Log File: .*", "Log File: shared.log", run_file.read_text()))
    basin = shared / "Castro_2.basin"  # Basin: Castro 2, used only by Future
    text, n = re.subn(r"(\n\s+Area:\s*)[0-9.]+", r"\g<1>-1.0", basin.read_text(), count=1)
    assert n == 1
    basin.write_text(text)
    prj = HmsPrj().initialize(shared)
    assert HmsCmdr.compute_batch(["Current", "Future"], hms_object=prj) == {
        "Current": True, "Future": False,
    }
    log = (shared / "shared.log").read_text()
    assert 'WARNING 15303:  Aborted run "Future"' in log and "ERROR 42282" in log
