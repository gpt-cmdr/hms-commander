"""Shared fixtures for hms-commander test suite.

Session-scoped fixtures provide read-only access to committed test project files.
Function-scoped fixtures create temporary copies for write tests.
"""

import faulthandler
import ipaddress
import os
import shutil
import socket
import sys
import threading
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent
PROJECTS_DIR = TESTS_DIR / "projects" / "2014.08_HMS"
PROJECT_33 = PROJECTS_DIR / "A1000000_baseline_33"
PROJECT_411 = PROJECTS_DIR / "A1000000_upgrade_411"
TAUDEM_FIXTURES_DIR = TESTS_DIR / "fixtures"
SPRING_CREEK_TAUDEM_FIXTURE = TAUDEM_FIXTURES_DIR / "taudem_spring_creek"
EXAMPLE_PROJECTS_DIR = Path(__file__).resolve().parents[1] / "examples" / "hms_example_projects"
RIVER_BEND_EXAMPLE = EXAMPLE_PROJECTS_DIR / "river_bend"


def _require_path(p: Path, label: str) -> Path:
    if not p.exists():
        pytest.skip(f"Test data not found: {label} ({p})")
    return p


# ---------------------------------------------------------------------------
# Session-scoped read-only fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_dir_33():
    """HMS 3.3 baseline project directory."""
    return _require_path(PROJECT_33, "HMS 3.3 project")


@pytest.fixture(scope="session")
def project_dir_411():
    """HMS 4.11 upgrade project directory."""
    return _require_path(PROJECT_411, "HMS 4.11 project")


@pytest.fixture(scope="session")
def basin_path_33(project_dir_33):
    """A100_1PCT.basin — 131 subbasins, Green and Ampt + Clark."""
    return _require_path(project_dir_33 / "A100_1PCT.basin", "basin 3.3")


@pytest.fixture(scope="session")
def basin_path_411(project_dir_411):
    """A100_1PCT.basin — same model, HMS 4.11 format."""
    return _require_path(project_dir_411 / "A100_1PCT.basin", "basin 4.11")


@pytest.fixture(scope="session")
def met_path_33(project_dir_33):
    """1__24HR.met — Frequency Based Hypothetical."""
    return _require_path(project_dir_33 / "1__24HR.met", "met 3.3")


@pytest.fixture(scope="session")
def control_path(project_dir_33):
    """Control_5.control — 5-minute interval."""
    return _require_path(project_dir_33 / "Control_5.control", "control")


@pytest.fixture(scope="session")
def gage_path(project_dir_33):
    """A1000000.gage — 14 gages."""
    return _require_path(project_dir_33 / "A1000000.gage", "gage")


@pytest.fixture(scope="session")
def run_path(project_dir_33):
    """A1000000.run — 10 runs."""
    return _require_path(project_dir_33 / "A1000000.run", "run")


@pytest.fixture(scope="session")
def hms_path(project_dir_33):
    """A1000000.hms — project file."""
    return _require_path(project_dir_33 / "A1000000.hms", "hms project")


@pytest.fixture(scope="session")
def geo_path(project_dir_33):
    """A100-GEO.geo — geo coordinates."""
    return _require_path(project_dir_33 / "A100-GEO.geo", "geo")


@pytest.fixture(scope="session")
def basin_content(basin_path_33):
    """Pre-read basin file content for parser tests."""
    from hms_commander._parsing import HmsFileParser
    return HmsFileParser.read_file(basin_path_33)


@pytest.fixture(scope="session")
def spring_creek_taudem_fixture_root():
    """Spring Creek-derived TauDEM fixture workspace."""
    return _require_path(SPRING_CREEK_TAUDEM_FIXTURE, "Spring Creek TauDEM fixture")


@pytest.fixture(scope="session")
def river_bend_example_dir():
    """Checked-in HMS 4.13 example project used for round-trip testing."""
    return _require_path(RIVER_BEND_EXAMPLE, "river_bend example project")


# ---------------------------------------------------------------------------
# Function-scoped writable fixtures (copies into tmp_path)
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_basin(basin_path_33, tmp_path):
    """Writable copy of basin file."""
    dest = tmp_path / basin_path_33.name
    shutil.copy2(basin_path_33, dest)
    return dest


@pytest.fixture
def tmp_met(met_path_33, tmp_path):
    """Writable copy of met file."""
    dest = tmp_path / met_path_33.name
    shutil.copy2(met_path_33, dest)
    return dest


@pytest.fixture
def tmp_control(control_path, tmp_path):
    """Writable copy of control file."""
    dest = tmp_path / control_path.name
    shutil.copy2(control_path, dest)
    return dest


@pytest.fixture
def tmp_run(run_path, tmp_path):
    """Writable copy of run file."""
    dest = tmp_path / run_path.name
    shutil.copy2(run_path, dest)
    return dest


@pytest.fixture
def tmp_project(project_dir_33, tmp_path):
    """Full writable project directory copy (for clone tests)."""
    dest = tmp_path / project_dir_33.name
    shutil.copytree(project_dir_33, dest)
    return dest


@pytest.fixture
def tmp_spring_creek_taudem_fixture(spring_creek_taudem_fixture_root, tmp_path):
    """Writable copy of the Spring Creek TauDEM fixture workspace."""
    dest = tmp_path / spring_creek_taudem_fixture_root.name
    shutil.copytree(spring_creek_taudem_fixture_root, dest)
    return dest


@pytest.fixture
def tmp_river_bend_example(river_bend_example_dir, tmp_path):
    """Writable copy of the checked-in river_bend example project."""
    dest = tmp_path / river_bend_example_dir.name
    shutil.copytree(river_bend_example_dir, dest)
    return dest


# ---------------------------------------------------------------------------
# Opt-in CI guards (environment variables; local runs are unaffected)
# ---------------------------------------------------------------------------

#: ``1``: refuse every network connection made while tests run (loopback is allowed).
#: Tests that would download data (HEC Monolith, NOAA, USGS) then fail to reach it and
#: skip through their own guards, so a CI run cannot depend on test-time network data.
OFFLINE_ENV = "HMS_COMMANDER_TEST_OFFLINE"
#: Seconds: after the session, dump every thread's stack to stderr at this interval
#: while the interpreter shuts down, so an exit hang leaves evidence in the log.
EXIT_WATCH_ENV = "HMS_COMMANDER_TEST_EXIT_WATCH"


class NetworkBlockedError(OSError):
    """A test tried to reach the network while HMS_COMMANDER_TEST_OFFLINE=1."""


def _is_loopback(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    if host in ("localhost", "", None):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


def _block_network():
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def connect(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_loopback(address):
            raise NetworkBlockedError(f"network access blocked during tests: {address!r}")
        return real_connect(self, address)

    def connect_ex(self, address):
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _is_loopback(address):
            raise NetworkBlockedError(f"network access blocked during tests: {address!r}")
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not _is_loopback(host if not isinstance(host, bytes) else host.decode()):
            raise socket.gaierror(f"name resolution blocked during tests: {host!r}")
        return real_getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    socket.getaddrinfo = getaddrinfo


def pytest_configure(config):
    if os.environ.get(OFFLINE_ENV) == "1":
        _block_network()


def _stop_async_retriever_loop():
    """Stop async-retriever's event-loop thread before interpreter exit.

    The library registers the same guard at exit once ``HmsHuc`` has used HyRiver
    (``hms_commander._hyriver_exit``). Tests that call pygeohydro directly do not pass
    through it, so the session end runs it as well.
    """
    from hms_commander._hyriver_exit import stop_async_retriever_loop

    stop_async_retriever_loop()


def pytest_unconfigure(config):
    _stop_async_retriever_loop()
    seconds = os.environ.get(EXIT_WATCH_ENV, "").strip()
    if not seconds:
        return
    alive = [t for t in threading.enumerate() if t is not threading.main_thread()]
    sys.__stderr__.write(
        "\n[exit watch] threads alive at session end: "
        + (", ".join(f"{t.name}(daemon={t.daemon})" for t in alive) or "none")
        + f"; jnius loaded: {'jnius' in sys.modules}; "
        f"engine loaded: {'ras_commander_fast_dss' in sys.modules}\n")
    sys.__stderr__.flush()
    # A C-level watchdog: keeps dumping every thread's stack during interpreter
    # shutdown until the process ends. It never ends the process itself.
    faulthandler.dump_traceback_later(float(seconds), repeat=True, file=sys.__stderr__,
                                      exit=False)
