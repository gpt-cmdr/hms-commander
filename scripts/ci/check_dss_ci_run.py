"""Fail a native/shadow DSS CI run that passed vacuously.

A run where the engine (or Java) was missing would still be green, because those tests
skip cleanly. This check reads the pytest JUnit report and requires:

- no failures or errors;
- the selected backend (``HMS_COMMANDER_DSS_BACKEND``) to be the one ``HmsDss`` reports;
- the native engine to import, at the version the ``dss`` extra requires;
- at least the given number of *passed* tests in each named test module.

Usage:
    python scripts/ci/check_dss_ci_run.py junit.xml --backend native \\
        --min test_dss_engine_wrappers=50 --min test_dss_native_write_ownership=10
"""
from __future__ import annotations

import argparse
import collections
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import PackageNotFoundError, version


def module_counts(junit_path):
    """``{module: {"passed": n, "failed": n, "skipped": n}}`` from a JUnit report."""
    counts = collections.defaultdict(lambda: collections.Counter())
    for case in ET.parse(junit_path).iter("testcase"):
        classname = case.get("classname", "")
        parts = classname.split(".")
        module = next((p for p in parts if p.startswith("test_")), classname)
        if case.find("failure") is not None or case.find("error") is not None:
            counts[module]["failed"] += 1
        elif case.find("skipped") is not None:
            counts[module]["skipped"] += 1
        else:
            counts[module]["passed"] += 1
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("junit")
    parser.add_argument("--backend", required=True, choices=("native", "shadow", "java"))
    parser.add_argument("--min", action="append", default=[], metavar="MODULE=N",
                        help="minimum passed tests in a test module (repeatable)")
    parser.add_argument("--min-total", type=int, default=0)
    args = parser.parse_args(argv)

    problems = []
    counts = module_counts(args.junit)
    totals = collections.Counter()
    for c in counts.values():
        totals.update(c)
    print(f"JUnit: {totals['passed']} passed, {totals['skipped']} skipped, "
          f"{totals['failed']} failed or errored")
    if totals["failed"]:
        problems.append(f"{totals['failed']} test(s) failed or errored")
    if totals["passed"] < args.min_total:
        problems.append(f"only {totals['passed']} tests passed; at least {args.min_total} required")

    for spec in args.min:
        module, _, n = spec.partition("=")
        got = counts.get(module, collections.Counter())
        print(f"  {module}: {got['passed']} passed, {got['skipped']} skipped (minimum {n})")
        if got["passed"] < int(n):
            problems.append(f"{module}: {got['passed']} passed, fewer than {n}; "
                            f"the tests it should run were skipped or missing")

    try:
        engine = version("ras-commander-fast-dss")
        import ras_commander_fast_dss  # noqa: F401  (the wheel must import, not just exist)
        print(f"ras-commander-fast-dss {engine} imports")
        from packaging.version import Version
        if not Version("0.1.2") <= Version(engine) < Version("0.2"):
            problems.append(f"engine {engine} is outside >=0.1.2,<0.2")
    except (PackageNotFoundError, ImportError) as exc:
        problems.append(f"the native engine does not import: {exc!r}")

    from hms_commander import HmsDss
    selected = HmsDss.get_backend()
    print(f"HmsDss.get_backend(): {selected}")
    if selected != args.backend:
        problems.append(f"backend is {selected!r}, expected {args.backend!r}")

    if problems:
        print("\nCI coverage check FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nCI coverage check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
