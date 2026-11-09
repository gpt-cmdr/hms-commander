"""The ``dss`` extra requests the native engine only where it has published wheels.

ras-commander-fast-dss 0.1.1 ships abi3 wheels for CPython on Windows AMD64 and Linux
x86_64/aarch64, and no macOS wheels. The marker must match, so pip never builds the Rust
sdist of this optional engine.
"""
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")
markers = pytest.importorskip("packaging.markers")
requirements = pytest.importorskip("packaging.requirements")

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def _engine_requirement():
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    reqs = [requirements.Requirement(r)
            for r in data["project"]["optional-dependencies"]["dss"]]
    found = [r for r in reqs if r.name == "ras-commander-fast-dss"]
    assert len(found) == 1
    return found[0]


def _env(system, machine, impl="CPython"):
    return {"platform_system": system, "platform_machine": machine,
            "platform_python_implementation": impl}


def test_engine_floor_is_0_1_1_below_0_2():
    req = _engine_requirement()
    assert str(req.specifier) in {">=0.1.1,<0.2", "<0.2,>=0.1.1"}
    assert not req.specifier.contains("0.1.0")
    assert req.specifier.contains("0.1.1")
    assert not req.specifier.contains("0.2.0")


@pytest.mark.parametrize("env, expected", [
    (_env("Windows", "AMD64"), True),
    (_env("Linux", "x86_64"), True),
    (_env("Linux", "aarch64"), True),
    (_env("Darwin", "arm64"), False),
    (_env("Darwin", "x86_64"), False),
    (_env("Windows", "ARM64"), False),
    (_env("Linux", "x86_64", impl="PyPy"), False),
])
def test_engine_marker_matches_published_wheels(env, expected):
    assert _engine_requirement().marker.evaluate(env) is expected
