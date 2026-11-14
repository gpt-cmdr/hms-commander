"""hms-commander requests the native DSS engine, its default DSS backend, only where the
engine publishes wheels.

ras-commander-fast-dss ships abi3 wheels for CPython on Windows AMD64 and Linux
x86_64/aarch64, and from 0.1.3 on macOS arm64/x86_64. The engine is a core dependency
with a marker that matches, so pip never builds the Rust sdist. The ``dss`` extra keeps
the Java backend's dependencies.
"""
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")
markers = pytest.importorskip("packaging.markers")
requirements = pytest.importorskip("packaging.requirements")

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _project():
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def _engine_requirement():
    reqs = [requirements.Requirement(r) for r in _project()["dependencies"]]
    found = [r for r in reqs if r.name == "ras-commander-fast-dss"]
    assert len(found) == 1
    return found[0]


def _env(system, machine, impl="CPython"):
    return {"platform_system": system, "platform_machine": machine,
            "platform_python_implementation": impl}


def test_engine_is_a_core_dependency_not_an_extra():
    _engine_requirement()
    for extra, reqs in _project()["optional-dependencies"].items():
        names = [requirements.Requirement(r).name for r in reqs]
        assert "ras-commander-fast-dss" not in names, extra
    dss = [requirements.Requirement(r).name for r in _project()["optional-dependencies"]["dss"]]
    assert "pyjnius" in dss


def test_engine_floor_is_0_1_2_below_0_2():
    # The floor moves to 0.1.3 (the first release with macOS wheels) once it is published.
    req = _engine_requirement()
    assert str(req.specifier) in {">=0.1.2,<0.2", "<0.2,>=0.1.2"}
    assert not req.specifier.contains("0.1.1")
    assert req.specifier.contains("0.1.2")
    assert req.specifier.contains("0.1.3")
    assert not req.specifier.contains("0.2.0")


def test_engine_requirement_has_no_extras():
    assert _engine_requirement().extras == set()


@pytest.mark.parametrize("env, expected", [
    (_env("Windows", "AMD64"), True),
    (_env("Linux", "x86_64"), True),
    (_env("Linux", "aarch64"), True),
    (_env("Darwin", "arm64"), True),
    (_env("Darwin", "x86_64"), True),
    (_env("Windows", "ARM64"), False),
    (_env("Linux", "ppc64le"), False),
    (_env("Linux", "x86_64", impl="PyPy"), False),
])
def test_engine_marker_matches_published_wheels(env, expected):
    assert _engine_requirement().marker.evaluate(env) is expected
