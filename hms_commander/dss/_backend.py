"""Backend selection, capability gates and shadow comparison for hms-commander DSS I/O.

``DssCore``, ``HmsDss`` and ``HmsDssGrid`` read and write DSS files through one of three
backends:

- ``"java"`` (default in this release): HEC Monolith through pyjnius.
- ``"native"``: the optional ``ras_commander_fast_dss`` engine (pure Rust). It never
  starts a JVM and never downloads HEC Monolith.
- ``"shadow"``: runs the Java path and returns its result (or raises its error), then
  repeats the operation natively and logs every difference. The comparison never
  raises. Differences that are known and explained are logged as ``expected`` at
  DEBUG/INFO; anything else is logged at WARNING as ``unexpected``. Writes are repeated
  natively on a temporary copy of the target, never on the caller's file.

The environment variable ``HMS_COMMANDER_DSS_BACKEND``, when set, overrides the class
attribute ``HmsDss.backend``. ``CAPABILITIES`` lists the support matrix that
``HmsDss.get_capabilities()`` reports.

This module is private. The design mirrors ``ras_commander.dss`` (``RasDss.backend``,
``RAS_COMMANDER_DSS_BACKEND``), with one difference: hms-commander's ``shadow`` returns
the Java result for reads as well as writes.

The Java backend never imports the engine. Every import of the engine is guarded, so a
missing or broken wheel (``ImportError``, or for example an ``OSError`` while loading
its extension) cannot break the Java backend.
"""

from __future__ import annotations

import importlib
import logging
import os
import threading
from collections import Counter, deque
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("hms_commander.dss")

#: Import name of the native engine (distribution ``ras-commander-fast-dss``).
ENGINE_MODULE = "ras_commander_fast_dss"
#: Environment variable that overrides ``HmsDss.backend`` when set.
ENV_VAR = "HMS_COMMANDER_DSS_BACKEND"
#: Allowed backend names.
BACKENDS = ("java", "native", "shadow")
#: Default backend for this release.
DEFAULT_BACKEND = "java"

#: HEC missing markers that the Java path returns raw (-901, -902, -FLT_MAX).
JAVA_MISSING_MARKERS = np.array([-901.0, -902.0, float(-np.finfo(np.float32).max)])

_NATIVE_INSTALL_HINT = (
    "The 'native' DSS backend requires the optional ras-commander-fast-dss engine "
    "(import name ras_commander_fast_dss). It is not published on PyPI; install the "
    "wheel you were given with 'pip install ras_commander_fast_dss-<version>-<tag>.whl', "
    "or use HmsDss.backend = 'java'."
)


class DssCapabilityError(RuntimeError):
    """The requested backend cannot perform this operation (no Java fallback)."""


_lock = threading.Lock()
_fallback_warned = False

#: Outcome counts of shadow comparisons: key (operation, outcome, label).
SHADOW_STATS: Counter = Counter()
#: Most recent shadow comparison records (diagnostics and tests).
SHADOW_RECORDS: Deque[Dict[str, Any]] = deque(maxlen=5000)


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------


def normalize_backend(value: Any, source: str) -> str:
    """Validate a backend name and return it lower-cased."""
    name = str(value).strip().lower()
    if name not in BACKENDS:
        raise ValueError(
            f"Invalid DSS backend {value!r} from {source}; expected one of {', '.join(BACKENDS)}"
        )
    return name


def requested_backend(attribute_value: Any) -> str:
    """Backend requested by ``HMS_COMMANDER_DSS_BACKEND`` or ``HmsDss.backend``."""
    env_value = os.environ.get(ENV_VAR, "").strip()
    if env_value:
        return normalize_backend(env_value, f"environment variable {ENV_VAR}")
    if attribute_value is None or str(attribute_value).strip() == "":
        return DEFAULT_BACKEND
    return normalize_backend(attribute_value, "HmsDss.backend")


def _maybe_native():
    """The engine module or None. Never raises: a broken wheel counts as absent."""
    try:
        return importlib.import_module(ENGINE_MODULE)
    except Exception:
        return None


def native_available() -> bool:
    """True when ``ras_commander_fast_dss`` imports (a broken wheel counts as absent)."""
    return _maybe_native() is not None


def import_native():
    """Import the engine or raise an ``ImportError`` that says how to install it.

    A wheel that fails to load (for example an ``OSError`` from its extension) also
    raises ``ImportError``, with the original error chained.
    """
    try:
        return importlib.import_module(ENGINE_MODULE)
    except ImportError as exc:
        raise ImportError(_NATIVE_INSTALL_HINT) from exc
    except Exception as exc:  # broken native wheel
        raise ImportError(
            f"ras-commander-fast-dss is installed but failed to load "
            f"({type(exc).__name__}: {exc}). " + _NATIVE_INSTALL_HINT
        ) from exc


def effective_backend(attribute_value: Any) -> str:
    """Backend to use for this call.

    ``native`` without the engine raises ``ImportError``. ``shadow`` without the engine
    runs Java only and logs one warning per process.
    """
    global _fallback_warned
    backend = requested_backend(attribute_value)
    if backend == "native":
        import_native()
    elif backend == "shadow" and not native_available():
        with _lock:
            if not _fallback_warned:
                _fallback_warned = True
                logger.warning(
                    "DSS backend 'shadow' requested but ras-commander-fast-dss is not "
                    "installed; using the Java backend only. %s",
                    _NATIVE_INSTALL_HINT,
                )
        return "java"
    return backend


def reset_fallback_warning() -> None:
    """Allow the shadow-fallback warning to be logged again (tests)."""
    global _fallback_warned
    with _lock:
        _fallback_warned = False


# ---------------------------------------------------------------------------
# Capability gates
# ---------------------------------------------------------------------------

#: Feature an engine advertises (in ``FEATURES``) once its grid CRS strings are
#: qualified against HEC Monolith.
NATIVE_GRID_FEATURE = "grid_srs_monolith_parity"

#: Engine attributes that make up the writer API (DSS6 and DSS7 time series, paired
#: data and grids). ``native_writes_available`` requires all of them.
NATIVE_WRITE_API = (
    "create",
    "write_timeseries",
    "write_paired_data",
    "write_grid",
    "HEC_MISSING_DSS6",
    "GRID_NODATA",
)
_NATIVE_WRITE_CALLABLES = ("create", "write_timeseries", "write_paired_data", "write_grid")


def engine_features() -> frozenset:
    """Feature names the installed engine advertises (empty when absent or unknown)."""
    dc = _maybe_native()
    if dc is None:
        return frozenset()
    try:
        features = getattr(dc, "FEATURES", None)
        if isinstance(features, Mapping):
            return frozenset(str(k) for k, v in features.items() if v)
        if isinstance(features, (set, frozenset, tuple, list)):
            return frozenset(f for f in features if isinstance(f, str))
    except Exception:
        pass
    return frozenset()


def native_grid_qualified() -> bool:
    """True when the engine advertises ``grid_srs_monolith_parity``.

    A capability check, not a version pin: wheels without ``FEATURES`` (or an engine
    that fails to import) are not qualified.
    """
    return NATIVE_GRID_FEATURE in engine_features()


NATIVE_GRID_GATE_MESSAGE = (
    "Native DSS grid reads are not qualified: the installed ras-commander-fast-dss does "
    "not advertise the 'grid_srs_monolith_parity' feature, so its CRS strings can differ "
    "from HEC Monolith's. hms-commander does not fall back to Java. Use "
    "HmsDss.backend = 'java' (or 'shadow')."
)


def require_native_grid_reads():
    """The engine with qualified grid reads, or ``DssCapabilityError`` (never Java)."""
    dc = import_native()
    if not native_grid_qualified():
        raise DssCapabilityError(NATIVE_GRID_GATE_MESSAGE)
    return dc


def native_writes_available() -> bool:
    """True when the installed engine provides every name in ``NATIVE_WRITE_API``.

    A capability check, not a version pin. Never raises.
    """
    dc = _maybe_native()
    if dc is None:
        return False
    try:
        for name in NATIVE_WRITE_API:
            value = getattr(dc, name, None)
            if value is None:
                return False
            if name in _NATIVE_WRITE_CALLABLES and not callable(value):
                return False
    except Exception:
        return False
    return True


NATIVE_WRITES_GATE_MESSAGE = (
    "The installed ras-commander-fast-dss does not provide the native DSS writers "
    "(create, write_timeseries, write_paired_data and write_grid with DSS6 support). "
    "hms-commander does not fall back to Java. Use an engine build with writer support "
    "(HmsDss.get_capabilities().attrs['native_writes_available']), or use "
    "HmsDss.backend = 'java'."
)


def require_native_writes():
    """The engine with its writers, or ``DssCapabilityError`` (never Java)."""
    dc = import_native()
    if not native_writes_available():
        raise DssCapabilityError(NATIVE_WRITES_GATE_MESSAGE)
    return dc


#: Backend support per public DSS operation. Values: "yes"; "gated" (needs a
#: qualified or writer-capable engine); "java" (runs on Java whatever the backend).
CAPABILITIES = (
    # operation, java, native, shadow, note
    ("get_catalog", "yes", "yes", "yes", ""),
    ("read_timeseries", "yes", "yes", "yes",
     "start_date/end_date are inclusive stamp filters on every backend"),
    ("read_multiple_timeseries", "yes", "yes", "yes", ""),
    ("get_peak_value", "yes", "yes", "yes", "HmsDss.get_peak_flows_batched uses it"),
    ("read_paired_data", "yes", "yes", "yes", "curve 0 only (the HMS dict contract)"),
    ("read_grid", "yes", "gated", "yes",
     "native requires an engine advertising 'grid_srs_monolith_parity'"),
    ("get_file_version", "yes", "yes", "yes", ""),
    ("write_timeseries", "yes", "gated", "yes",
     "regular intervals only; native requires the engine writers; shadow writes with "
     "Java and repeats the write natively on a temporary copy"),
    ("write_paired_data", "yes", "gated", "yes",
     "stored as float32 (PD) as HEC Monolith stores it; DSS6 units/types at most 8 "
     "characters on native"),
    ("write_multiple_paired_data", "yes", "gated", "yes", "as write_paired_data"),
    ("import_atlas14_temporal", "yes", "gated", "yes",
     "y type CUMULATIVE on DSS7, CUMULATI on DSS6 (both backends)"),
    ("write_grid_timeseries", "yes", "gated", "yes",
     "native refuses PER-CUM/PER-AVER grids with equal start and end times"),
)


# ---------------------------------------------------------------------------
# Shadow records
# ---------------------------------------------------------------------------


def _err(exc: Optional[BaseException]) -> Optional[str]:
    if exc is None:
        return None
    return f"{type(exc).__name__}: {str(exc)[:300]}"


def record(
    operation: str,
    outcome: str,
    label: str,
    *,
    dss_file: Any,
    pathname: Optional[str] = None,
    diffs: Optional[List[str]] = None,
    java_seconds: Optional[float] = None,
    native_seconds: Optional[float] = None,
    java_error: Optional[BaseException] = None,
    native_error: Optional[BaseException] = None,
    detail: Optional[Dict[str, Any]] = None,
) -> None:
    """Count, store and log one shadow comparison. Never raises."""
    try:
        rec = {
            "operation": operation,
            "outcome": outcome,
            "label": label,
            "dss_file": str(dss_file),
            "pathname": pathname,
            "diffs": list(diffs or []),
            "java_seconds": java_seconds,
            "native_seconds": native_seconds,
            "java_error": _err(java_error),
            "native_error": _err(native_error),
        }
        if detail:
            rec.update(detail)
        with _lock:
            SHADOW_STATS[(operation, outcome, label)] += 1
            SHADOW_RECORDS.append(rec)
        where = f"{dss_file}" + (f" {pathname}" if pathname else "")
        if outcome == "identical":
            logger.debug("DSS shadow %s identical: %s", operation, where)
        elif outcome in ("expected", "skipped"):
            level = logging.DEBUG if label.startswith("D1") else logging.INFO
            logger.log(
                level,
                "DSS shadow %s %s [%s]: %s (diffs=%s, java_error=%s, native_error=%s)",
                operation, outcome, label, where, rec["diffs"], rec["java_error"],
                rec["native_error"],
            )
        else:
            logger.warning(
                "DSS shadow %s UNEXPECTED difference [%s]: %s (diffs=%s, java_error=%s, "
                "native_error=%s)",
                operation, label, where, rec["diffs"], rec["java_error"], rec["native_error"],
            )
    except Exception as exc:  # pragma: no cover - logging must never break I/O
        logger.debug("DSS shadow record failed: %s", exc)


def reset_shadow_stats() -> None:
    """Clear shadow counters and records."""
    with _lock:
        SHADOW_STATS.clear()
        SHADOW_RECORDS.clear()


def summary() -> Dict[str, int]:
    """Shadow outcome counts as ``{"operation|outcome|label": n}``."""
    with _lock:
        return {"|".join(k): v for k, v in sorted(SHADOW_STATS.items())}


def java_unavailable(exc: Optional[BaseException]) -> bool:
    """True when the Java path could not run at all (no pyjnius, Java or Monolith)."""
    if exc is None:
        return False
    if isinstance(exc, ImportError):
        return True
    return isinstance(exc, RuntimeError) and str(exc).startswith("Java not found")


def _not_found_types() -> tuple:
    dc = _maybe_native()
    return tuple(
        t for t in (
            getattr(dc, "DssPathnameNotFoundError", None) if dc else None,
            getattr(dc, "DssUnsupportedRecordError", None) if dc else None,
        ) if t is not None
    )


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------


def java_missing(values: np.ndarray) -> np.ndarray:
    """Missing mask for Java-path values: NaN or a raw HEC marker."""
    v = np.asarray(values, dtype=np.float64)
    return np.isnan(v) | np.isin(v, JAVA_MISSING_MARKERS)


def _bits_equal(a: Any, b: Any) -> bool:
    a = np.ascontiguousarray(np.asarray(a, dtype=np.float64))
    b = np.ascontiguousarray(np.asarray(b, dtype=np.float64))
    return a.shape == b.shape and bool(np.array_equal(a.view(np.int64), b.view(np.int64)))


def _attr_diffs(java_attrs: Dict[str, Any], native_attrs: Dict[str, Any],
                skip: Tuple[str, ...] = ()) -> List[str]:
    diffs: List[str] = []
    for key in sorted(set(java_attrs) | set(native_attrs)):
        if key in skip:
            continue
        jv = java_attrs.get(key, "<absent>")
        nv = native_attrs.get(key, "<absent>")
        if jv != nv:
            if isinstance(jv, str) and isinstance(nv, str) and jv.strip() == nv.strip():
                diffs.append(f"attr_ws:{key}")
            else:
                diffs.append(f"attr:{key}")
    return diffs


def compare_frames(java_df: pd.DataFrame, native_df: pd.DataFrame,
                   skip_attrs: Tuple[str, ...] = ()) -> List[str]:
    """Differences between a Java and a native ``read_timeseries`` frame.

    Rules: columns, index dtype, length, stamps, missing positions (Java markers or NaN
    against native NaN), the remaining values bitwise, and every ``attrs`` key.
    ``attr_ws:<key>`` marks string attributes that differ only in surrounding blanks.
    """
    diffs: List[str] = []
    if list(java_df.columns) != list(native_df.columns):
        diffs.append("columns")
    if java_df.index.dtype != native_df.index.dtype:
        diffs.append(f"index_dtype:{java_df.index.dtype}->{native_df.index.dtype}")
    if len(java_df) != len(native_df):
        diffs.append("length")
    elif "value" in java_df and "value" in native_df:
        js = java_df.index.to_numpy(dtype="datetime64[s]").astype(np.int64)
        ns = native_df.index.to_numpy(dtype="datetime64[s]").astype(np.int64)
        if not np.array_equal(js, ns):
            diffs.append("index_values")
        jv = java_df["value"].to_numpy(dtype=np.float64)
        nv = native_df["value"].to_numpy(dtype=np.float64)
        jm, nm = java_missing(jv), np.isnan(nv)
        if not np.array_equal(jm, nm):
            diffs.append("missing_positions")
        both = ~jm & ~nm
        if not _bits_equal(jv[both], nv[both]):
            diffs.append("values_bits")
    diffs += _attr_diffs(java_df.attrs, native_df.attrs, skip_attrs)
    return diffs


def java_marker_count(java_df: pd.DataFrame) -> int:
    """Number of raw HEC markers in a Java frame (native frames hold NaN there)."""
    if "value" not in java_df:
        return 0
    v = java_df["value"].to_numpy(dtype=np.float64)
    return int(np.isin(v, JAVA_MISSING_MARKERS).sum())


def classify_timeseries(
    pathname: str,
    java_df: Optional[pd.DataFrame],
    java_exc: Optional[BaseException],
    native_df: Optional[pd.DataFrame],
    native_exc: Optional[BaseException],
) -> Tuple[str, str, List[str]]:
    """Classify one ``read_timeseries`` comparison: ``(outcome, label, diffs)``.

    Labels (``docs/user_guide/dss_native_backend.md``):

    - ``D1``: Java returns raw HEC missing markers; native returns NaN.
    - ``D5``: a time-series pattern (stamps in year 3000) that Java cannot read.
    - ``D9``: units/type differ only in surrounding blanks.
    - ``D4``: no data on either backend (typed native error).
    """
    if java_unavailable(java_exc):
        return "skipped", "java unavailable", []
    typed = _not_found_types()
    if java_df is not None and native_df is not None:
        diffs = compare_frames(java_df, native_df)
        if not diffs:
            if java_marker_count(java_df):
                return "expected", "D1 missing markers mapped to NaN", diffs
            return "identical", "identical", diffs
        if set(diffs) <= {"attr_ws:type", "attr_ws:units"}:
            return "expected", "D9 blank units/type whitespace", diffs
        return "unexpected", "frame difference", diffs
    if java_df is None and native_df is not None:
        no_data = (isinstance(java_exc, ValueError)
                   and str(java_exc).startswith("No data found"))
        if no_data and len(native_df) and native_df.index[0].year == 3000:
            return "expected", "D5 pattern record (Java cannot read)", []
        return "unexpected", "native data, Java error", []
    if java_df is not None and native_df is None:
        if typed and isinstance(native_exc, typed) and "value" in java_df and \
                java_missing(java_df["value"].to_numpy()).all():
            return "expected", "D4 all-missing dataset (error type)", []
        return "unexpected", "Java data, native error", []
    if typed and isinstance(native_exc, typed):
        return "expected", "D4 no data on both backends", []
    return "unexpected", "both failed, untyped native error", []


def classify_catalog(
    java_list: Optional[List[str]], java_exc: Optional[BaseException], native_list: List[str]
) -> Tuple[str, str, List[str]]:
    """Classify one ``get_catalog`` comparison (lists of pathnames)."""
    if java_unavailable(java_exc):
        return "skipped", "java unavailable", []
    if java_list is None:
        return "unexpected", "native catalog, Java error", []
    if list(java_list) == list(native_list):
        return "identical", "identical", []
    if Counter(java_list) == Counter(native_list):
        return "expected", "C1 catalog order", ["order"]
    return "unexpected", "catalog difference", ["entries"]


def compare_peak(java: Optional[Dict[str, Any]], native: Optional[Dict[str, Any]]) -> List[str]:
    """Differences between two ``get_peak_value`` results."""
    if java is None or native is None:
        return [] if java is None and native is None else ["presence"]
    diffs = []
    for key in sorted(set(java) | set(native)):
        jv, nv = java.get(key), native.get(key)
        if isinstance(jv, float) and isinstance(nv, float):
            if not _bits_equal([jv], [nv]):
                diffs.append(key)
        elif jv != nv:
            diffs.append(key)
    return diffs


def compare_paired_data(java: Optional[Dict[str, Any]],
                        native: Optional[Dict[str, Any]]) -> List[str]:
    """Differences between two ``read_paired_data`` dicts (the HMS contract)."""
    if java is None or native is None:
        return [] if java is None and native is None else ["presence"]
    diffs = []
    for key in ("x_values", "y_values"):
        ja, na = np.asarray(java.get(key)), np.asarray(native.get(key))
        if ja.dtype != na.dtype:
            diffs.append(f"{key}_dtype")
        elif not _bits_equal(ja, na):
            diffs.append(key)
    for key in ("x_units", "y_units", "x_label", "y_label", "pathname"):
        jv, nv = java.get(key), native.get(key)
        if jv != nv:
            if isinstance(jv, str) and isinstance(nv, str) and jv.strip() == nv.strip():
                diffs.append(f"ws:{key}")
            else:
                diffs.append(key)
    return diffs


def classify_paired_data(java, java_exc, native, native_exc) -> Tuple[str, str, List[str]]:
    """Classify one ``read_paired_data`` comparison. ``PD3`` labels blank-only
    differences in unit/type strings."""
    if java_unavailable(java_exc):
        return "skipped", "java unavailable", []
    if java_exc is not None or native_exc is not None:
        return "unexpected", "error difference", []
    diffs = compare_paired_data(java, native)
    if not diffs:
        if java is None:
            return "expected", "no record on both backends", []
        return "identical", "identical", []
    if all(d.startswith("ws:") for d in diffs):
        return "expected", "PD3 unit/type whitespace", diffs
    return "unexpected", "paired-data difference", diffs


def _same(a: Any, b: Any) -> bool:
    a_missing = a is None or (isinstance(a, (pd.Timestamp, type(pd.NaT))) and pd.isna(a))
    b_missing = b is None or (isinstance(b, (pd.Timestamp, type(pd.NaT))) and pd.isna(b))
    if a_missing or b_missing:
        return a_missing and b_missing
    if isinstance(a, float) and isinstance(b, float):
        return _bits_equal([a], [b])
    try:
        return bool(a == b)
    except Exception:  # pragma: no cover - defensive
        return False


#: Grid dict keys compared by shadow reads (cells are compared separately).
GRID_META_KEYS = ("pathname", "shape", "units", "data_type", "grid_type", "cell_size",
                  "lower_left_cell", "cell_zero", "crs", "start_time", "end_time")


def compare_grids(java: Dict[str, Any], native: Dict[str, Any]) -> Tuple[List[str], bool]:
    """Differences between two ``read_grid`` dicts and whether extra native NaN cells
    are only -901/-902 or the specified null value (``G1``)."""
    diffs: List[str] = []
    for key in GRID_META_KEYS:
        jv, nv = java.get(key), native.get(key)
        if not _same(jv, nv):
            if isinstance(jv, str) and isinstance(nv, str) and jv.strip() == nv.strip():
                diffs.append(f"ws:{key}")
            else:
                diffs.append(key)
    jd = np.asarray(java.get("data"), dtype=np.float32)
    nd = np.asarray(native.get("data"), dtype=np.float32)
    extra_ok = False
    if jd.shape != nd.shape:
        diffs.append("cells_shape")
        return diffs, extra_ok
    jm, nm = np.isnan(jd), np.isnan(nd)
    if np.any(jm & ~nm):
        diffs.append("cells_missing_java_only")
    extra = nm & ~jm
    if np.any(extra):
        markers = [-901.0, -902.0]
        if native.get("null_value") is not None:
            markers.append(native["null_value"])
        extra_ok = bool(np.all(np.isin(jd[extra], np.asarray(markers, dtype=np.float32))))
        diffs.append("cells_missing_native_only")
    both = ~jm & ~nm
    if not np.array_equal(jd[both].view(np.int32), nd[both].view(np.int32)):
        diffs.append("cells_bits")
    return diffs, extra_ok


def classify_grid(java, java_exc, native, native_exc) -> Tuple[str, str, List[str]]:
    """Classify one ``read_grid`` comparison.

    - ``G1``: native maps -901/-902 and a specified grid's null value to NaN; Java maps
      only -FLT_MAX.
    - ``G2``: blank-only differences in strings.
    """
    if java_unavailable(java_exc):
        return "skipped", "java unavailable", []
    if java is not None and native is not None:
        diffs, extra_ok = compare_grids(java, native)
        if not diffs:
            return "identical", "identical", []
        rest = set(diffs)
        labels = []
        if "cells_missing_native_only" in rest and extra_ok:
            rest.discard("cells_missing_native_only")
            labels.append("G1 native maps grid null/-901/-902 to NaN")
        ws = {d for d in rest if d.startswith("ws:")}
        if ws:
            rest -= ws
            labels.append("G2 whitespace")
        if rest:
            return "unexpected", "grid difference", diffs
        return "expected", "; ".join(labels), diffs
    if java is None and native is None:
        typed = _not_found_types()
        if typed and isinstance(native_exc, typed) and isinstance(java_exc, ValueError):
            return "expected", "not found on both backends", []
        return "unexpected", "both failed", []
    if native is not None:
        return "unexpected", "native grid, Java error", []
    return "unexpected", "Java grid, native error", []


def classify_file_version(java_v, java_exc, native_v, native_exc) -> Tuple[str, str, List[str]]:
    """Classify one ``get_file_version`` comparison."""
    if java_unavailable(java_exc):
        return "skipped", "java unavailable", []
    if java_exc is None and native_exc is None:
        if java_v == native_v:
            return "identical", "identical", []
        return "unexpected", "version difference", ["version"]
    if java_exc is not None and native_exc is not None:
        return "expected", "invalid file on both backends", []
    return "unexpected", "error difference", []


# ---------------------------------------------------------------------------
# Shadow writes
# ---------------------------------------------------------------------------
#
# Under ``shadow`` every write runs on Java (its result and errors are what the caller
# gets). The native writer then repeats the write on a temporary copy of the target
# (or into a new temporary file), and both files are read back with the native reader
# and compared. Both read-backs use the same reader, so a difference comes from the
# writers. The comparison never raises.

#: Larger existing targets are not copied and the comparison is skipped.
SHADOW_COPY_LIMIT_MB_DEFAULT = 256.0
SHADOW_COPY_LIMIT_ENV = "HMS_COMMANDER_DSS_SHADOW_COPY_LIMIT_MB"

#: Known differences between a Java- and a native-written file. Logged as ``expected``.
WRITE_REFUSAL_LABEL = "W1 native writer refuses input the Java path accepts"
NATIVE_WRITERS_MISSING_LABEL = "native writers not available"


def shadow_copy_limit_bytes(attribute_mb: Any) -> int:
    """Byte limit for shadow-write copies (env var overrides the attribute)."""
    env_value = os.environ.get(SHADOW_COPY_LIMIT_ENV, "").strip()
    raw, source = ((env_value, f"environment variable {SHADOW_COPY_LIMIT_ENV}") if env_value
                   else (attribute_mb, "HmsDss.shadow_copy_limit_mb"))
    try:
        mb = float(raw)
    except (TypeError, ValueError):
        mb = float("nan")
    if not np.isfinite(mb) or mb < 0:
        raise ValueError(f"invalid shadow copy limit {raw!r} from {source}: expected MB >= 0")
    return int(mb * 1024 * 1024)


def shadow_snapshot(dss_file: Any, attribute_mb: Any) -> Dict[str, Any]:
    """Prepare a shadow write: copy an existing target to a temporary directory before
    the Java write changes it. Never raises."""
    import shutil
    import tempfile

    ctx: Dict[str, Any] = {"tmpdir": None, "copy": None, "existed": False, "skip": None}
    try:
        target = Path(dss_file)
        ctx["existed"] = target.is_file()
        tmpdir = Path(tempfile.mkdtemp(prefix="hmsdss_shadow_write_"))
        ctx["tmpdir"] = tmpdir
        ctx["copy"] = tmpdir / (target.name or "shadow.dss")
        if ctx["existed"]:
            size = target.stat().st_size
            limit = shadow_copy_limit_bytes(attribute_mb)
            if size > limit:
                ctx["skip"] = (f"target is {size} bytes, above the shadow copy limit "
                               f"({limit} bytes)")
            else:
                shutil.copy2(target, ctx["copy"])
    except Exception as exc:
        ctx["skip"] = f"snapshot failed: {type(exc).__name__}: {exc}"
    return ctx


def shadow_cleanup(ctx: Dict[str, Any]) -> None:
    """Remove a shadow snapshot directory. Never raises."""
    import shutil

    if ctx.get("tmpdir") is not None:
        shutil.rmtree(ctx["tmpdir"], ignore_errors=True)


def classify_write(native_exc: Optional[BaseException], diffs: List[str]
                   ) -> Tuple[str, str, List[str]]:
    """Classify one shadow write comparison.

    - The native writer refused the input (``ValueError``, ``DssUnsupportedRecordError``):
      ``expected`` ``W1``.
    - ``DssCapabilityError`` (no engine writers) or ``DssLockedError`` on the temporary
      copy: ``skipped``.
    - Any other native error, or any difference: ``unexpected``.
    """
    if native_exc is not None:
        if isinstance(native_exc, DssCapabilityError):
            return "skipped", NATIVE_WRITERS_MISSING_LABEL, list(diffs)
        dc = _maybe_native()
        unsupported = getattr(dc, "DssUnsupportedRecordError", None) if dc else None
        locked = getattr(dc, "DssLockedError", None) if dc else None
        if isinstance(native_exc, ValueError) or (
                unsupported is not None and isinstance(native_exc, unsupported)):
            return "expected", WRITE_REFUSAL_LABEL, list(diffs)
        if locked is not None and isinstance(native_exc, locked):
            return "skipped", "native write: temporary copy locked", list(diffs)
        return "unexpected", "native write error", list(diffs)
    if diffs:
        return "unexpected", "write difference", list(diffs)
    return "identical", "identical", []


def make_parents(path: Any) -> List[Path]:
    """Create the missing parent directories of ``path``; return them, deepest first."""
    created = []
    parent = Path(path).parent
    while not parent.exists():
        created.append(parent)
        if parent.parent == parent:
            break
        parent = parent.parent
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return created


def remove_created_dirs(created: List[Path]) -> None:
    """Remove directories made by ``make_parents`` while they are empty. Never raises."""
    for directory in created:
        try:
            directory.rmdir()
        except OSError:
            break
