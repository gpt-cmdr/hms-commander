"""Pure DSS pathname and catalog helpers.

This module intentionally has no Java, pyjnius, or DSS file dependency. It
centralizes HMS result-path selection so adapters can stay focused on file IO.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence


DEFAULT_RESULT_PATTERNS: Mapping[str, str] = {
    "flow": r"/FLOW[^/]*/|/FLOW/",
    "flow-total": r"/FLOW/",
    "precipitation": r"/PRECIP[^/]*/|/PRECIP/",
    "precip-inc": r"/PRECIP-INC/",
    "precip-cum": r"/PRECIP-CUM/",
    "stage": r"/STAGE/",
    "storage": r"/STORAGE[^/]*/|/STORAGE/",
}


def parse_pathname(pathname: str) -> Dict[str, str]:
    """Parse a DSS pathname into A-F parts and common HMS convenience fields."""

    parts = str(pathname).split("/")
    if parts and parts[0] == "":
        parts = parts[1:]
    if parts and parts[-1] == "":
        parts = parts[:-1]

    result = {
        "A": parts[0] if len(parts) > 0 else "",
        "B": parts[1] if len(parts) > 1 else "",
        "C": parts[2] if len(parts) > 2 else "",
        "D": parts[3] if len(parts) > 3 else "",
        "E": parts[4] if len(parts) > 4 else "",
        "F": parts[5] if len(parts) > 5 else "",
        "full_path": pathname,
    }
    result["element_name"] = result["B"]
    result["data_type"] = result["C"]
    result["time_interval"] = result["E"]
    result["run_name"] = result["F"][4:] if result["F"].upper().startswith("RUN:") else result["F"]
    return result


def create_pathname(
    basin: str,
    element: str,
    data_type: str,
    interval: str,
    run_name: str = "",
    date_block: str = "",
) -> str:
    """Create a DSS pathname from A-F components."""

    f_part = f"RUN:{run_name}" if run_name else ""
    return f"/{basin}/{element}/{data_type}/{date_block}/{interval}/{f_part}/"


def _contains(value: str, expected: Optional[str]) -> bool:
    if expected is None:
        return True
    return str(expected).upper() in str(value).upper()


def _equals(value: str, expected: Optional[str]) -> bool:
    if expected is None:
        return True
    return str(value).upper() == str(expected).upper()


def filter_catalog(
    catalog: Sequence[str],
    pattern: Optional[str] = None,
    data_type: Optional[str] = None,
    element: Optional[str] = None,
    run_name: Optional[str] = None,
    exact_run: bool = True,
) -> List[str]:
    """Filter a DSS catalog by regex and parsed pathname components."""

    filtered: Iterable[str] = catalog
    if pattern:
        regex = re.compile(pattern, re.IGNORECASE)
        filtered = [path for path in filtered if regex.search(path)]

    results: List[str] = []
    for path in filtered:
        parts = parse_pathname(path)
        if not _contains(parts["data_type"], data_type):
            continue
        if not _contains(parts["element_name"], element):
            continue
        if run_name is not None:
            run_matches = _equals if exact_run else _contains
            if not run_matches(parts["run_name"], run_name):
                continue
        results.append(path)
    return results


def is_table_path(pathname: str) -> bool:
    """Return True for DSS paths that represent table/paired-data records."""

    parts = parse_pathname(pathname)
    return any(part.upper() == "TABLE" for part in parts.values() if isinstance(part, str))


def matches_result_type(
    pathname: str,
    result_type: str,
    result_patterns: Optional[Mapping[str, str]] = None,
) -> bool:
    """Return True when a pathname matches an HMS result category."""

    patterns = result_patterns or DEFAULT_RESULT_PATTERNS
    key = result_type.lower()
    if key == "flow-total":
        return parse_pathname(pathname)["data_type"].upper() == "FLOW"
    pattern = patterns.get(key)
    if pattern:
        return bool(re.search(pattern, pathname, re.IGNORECASE))
    return True


def select_result_paths(
    catalog: Sequence[str],
    result_type: str = "flow",
    element_names: Optional[Sequence[str]] = None,
    run_name: Optional[str] = None,
    exclude_tables: bool = True,
    result_patterns: Optional[Mapping[str, str]] = None,
) -> List[str]:
    """Select HMS result paths with deterministic catalog-order output."""

    element_filter = {str(name).upper() for name in element_names or []}
    selected: List[str] = []
    for path in catalog:
        if exclude_tables and is_table_path(path):
            continue
        if not matches_result_type(path, result_type, result_patterns):
            continue
        parts = parse_pathname(path)
        if element_filter and parts["element_name"].upper() not in element_filter:
            continue
        if run_name is not None and parts["run_name"].upper() != str(run_name).upper():
            continue
        selected.append(path)
    return selected


def unique_elements(paths: Sequence[str]) -> List[str]:
    """Return unique B-parts in first-seen order."""

    seen = set()
    elements: List[str] = []
    for path in paths:
        element = parse_pathname(path)["element_name"]
        key = element.upper()
        if key in seen:
            continue
        seen.add(key)
        elements.append(element)
    return elements


def group_paths_by_element(paths: Sequence[str]) -> Dict[str, List[str]]:
    """Group pathnames by element name while preserving path order."""

    grouped: Dict[str, List[str]] = {}
    for path in paths:
        element = parse_pathname(path)["element_name"]
        grouped.setdefault(element, []).append(path)
    return grouped
