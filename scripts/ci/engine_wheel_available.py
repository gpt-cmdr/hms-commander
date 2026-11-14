"""Is there a ras-commander-fast-dss wheel for this platform that hms-commander accepts?

The CI native job runs this before installing. Off macOS it prints ``available=true``
without a network request (the engine publishes Windows and Linux wheels). On macOS it
asks PyPI for a release inside the requirement range of ``pyproject.toml`` with a wheel
for this machine (``macosx_*_arm64`` or ``_x86_64`` / ``universal2``). Without one, it
prints the reason as a GitHub notice and ``available=false``, so the job skips its
install and tests instead of building the Rust sdist.

Usage: python scripts/ci/engine_wheel_available.py [--github-output FILE]
Standard library only (it runs before anything is installed).
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import urllib.request
from pathlib import Path

PACKAGE = "ras-commander-fast-dss"
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _version_tuple(text: str):
    parts = re.match(r"^(\d+(?:\.\d+)*)$", text)
    return tuple(int(p) for p in parts.group(1).split(".")) if parts else None


def requirement_range():
    """``(floor, ceiling)`` of the engine requirement in pyproject.toml."""
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"'ras-commander-fast-dss>=([\d.]+),<([\d.]+);", text)
    if not match:
        raise SystemExit("engine requirement not found in pyproject.toml")
    return _version_tuple(match.group(1)), _version_tuple(match.group(2))


def macos_wheel(floor, ceiling, machine: str):
    """Newest accepted version with a wheel for this Mac, or None, and the reason."""
    with urllib.request.urlopen(f"https://pypi.org/pypi/{PACKAGE}/json", timeout=60) as response:
        releases = json.load(response)["releases"]
    arch = "arm64" if machine in ("arm64", "aarch64") else "x86_64"
    accepted = sorted((v for v in releases if _version_tuple(v) and
                       floor <= _version_tuple(v) < ceiling), key=_version_tuple)
    for version in reversed(accepted):
        for file in releases[version]:
            name = file["filename"]
            if (name.endswith(".whl") and "macosx" in name and not file.get("yanked")
                    and (arch in name or "universal2" in name)):
                return version, name
    return None, (f"no macOS {arch} wheel of {PACKAGE} in "
                  f">={'.'.join(map(str, floor))},<{'.'.join(map(str, ceiling))} on PyPI "
                  f"(versions checked: {', '.join(accepted) or 'none'})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--github-output")
    args = parser.parse_args()
    available = True
    if sys.platform == "darwin":
        floor, ceiling = requirement_range()
        version, detail = macos_wheel(floor, ceiling, platform.machine())
        if version:
            print(f"{PACKAGE} {version} has a macOS wheel: {detail}")
        else:
            available = False
            print(f"::notice title=macOS native leg skipped::{detail}. The leg runs once "
                  f"ras-commander-fast-dss 0.1.3 with macOS wheels is published.")
    else:
        print(f"{sys.platform}: {PACKAGE} publishes wheels for this platform")
    line = f"available={'true' if available else 'false'}"
    print(line)
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
