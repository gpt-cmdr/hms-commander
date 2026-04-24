"""Shared fixtures for hms-commander test suite.

Session-scoped fixtures provide read-only access to committed test project files.
Function-scoped fixtures create temporary copies for write tests.
"""

import shutil
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
