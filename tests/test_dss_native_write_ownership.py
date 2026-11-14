"""A failed native write removes only a DSS file that the write itself created.

``DssCore._native_write_target`` checks whether the target exists before the write;
another process can create the file before ``ras_commander_fast_dss.create`` runs.
The engine's exclusive create then refuses with ``FileExistsError``, and the rollback
must leave the other writer's file and its record in place (PR #46 follow-up to the
ras-commander PR #794 review, finding P1). The race is injected at the engine's
``create`` boundary with real DSS I/O. Every native writer that shares the helper
(``_native_new_file``) is checked: time series, paired data, multiple paired data
(also behind ``import_atlas14_temporal``) and grids.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

dc = pytest.importorskip("ras_commander_fast_dss")

from hms_commander import HmsDss  # noqa: E402
from hms_commander.dss import _backend  # noqa: E402
from hms_commander.dss.hms_dss_grid import HmsDssGrid  # noqa: E402

if not _backend.native_writes_available():  # pragma: no cover - depends on the wheel
    pytest.skip("installed ras-commander-fast-dss has no writers", allow_module_level=True)

OTHER = "/OTHER/OWNER/FLOW//1HOUR/KEEP/"
HOURS = pd.date_range("2020-01-01 01:00", periods=2, freq="h")


def _write_timeseries(target):
    HmsDss.write_timeseries(target, "/A/B/FLOW//1HOUR/F/", HOURS, [1.0, 2.0])


def _write_paired_data(target):
    HmsDss.write_paired_data(target, "/B/L/STAGE-DAMAGE///R/", [1.0, 2.0, 3.0],
                             [10.0, 20.0, 30.0], x_units="FEET", y_units="$",
                             x_type="LINEAR", y_type="LINEAR")


def _write_multiple_paired_data(target):
    HmsDss.write_multiple_paired_data(target, [
        {"pathname": "//R/FIRST-QUARTILE/24HR//50%/", "x_values": np.array([0.0, 24.0]),
         "y_values": np.array([0.0, 1.0])},
    ])


def _write_grid(target):
    HmsDssGrid.write_grid_timeseries(
        target, "/AORC/T/PRECIP////", np.ones((2, 2, 2)), [35.0, 35.04],
        [-97.0, -96.96], list(HOURS.to_pydatetime()),
    )


WRITERS = {
    "timeseries": _write_timeseries,
    "paired_data": _write_paired_data,
    "multiple_paired_data": _write_multiple_paired_data,
    "grid": _write_grid,
}
#: Engine call that writes the records for each writer.
ENGINE_WRITE = {
    "timeseries": "write_timeseries",
    "paired_data": "write_paired_data",
    "multiple_paired_data": "write_paired_data",
    "grid": "write_grid",
}


class _Interrupted(BaseException):
    """Interrupts a write the way KeyboardInterrupt would; write_multiple_paired_data
    records an ordinary engine error per record instead of raising it."""


@pytest.fixture
def native(monkeypatch):
    monkeypatch.setattr(HmsDss, "backend", "native")
    monkeypatch.delenv(_backend.ENV_VAR, raising=False)


@pytest.mark.parametrize("writer", sorted(WRITERS))
def test_refused_create_keeps_a_competing_writers_file(native, tmp_path, monkeypatch, writer):
    target = tmp_path / "race_target.dss"
    original = dc.create
    sizes = []

    def racing_create(path, version=7):
        # Another process creates and fills the file between the preflight check and
        # this call; then the requested exclusive create runs and must refuse.
        original(path, version)
        dc.write_timeseries(path, OTHER, [99.0, 100.0], times=HOURS.to_numpy(),
                            version=version, units="CFS", data_type="INST-VAL")
        sizes.append(target.stat().st_size)
        return original(path, version)

    monkeypatch.setattr(dc, "create", racing_create)
    with pytest.raises(FileExistsError):
        WRITERS[writer](target)
    monkeypatch.setattr(dc, "create", original)

    assert sizes and target.exists()
    assert target.stat().st_size == sizes[0]
    assert len(HmsDss.get_catalog(target)) == 1
    frame = dc.read_timeseries(str(target), OTHER)
    np.testing.assert_array_equal(frame["value"].to_numpy(), [99.0, 100.0])


@pytest.mark.parametrize("writer", sorted(WRITERS))
def test_failed_write_removes_the_file_it_created(native, tmp_path, monkeypatch, writer):
    target = tmp_path / "sub" / "owned.dss"

    def boom(*args, **kwargs):
        raise _Interrupted("simulated write failure")

    monkeypatch.setattr(dc, ENGINE_WRITE[writer], boom)
    with pytest.raises(_Interrupted, match="simulated write failure"):
        WRITERS[writer](target)
    assert not target.exists()
    assert not target.parent.exists()  # the parent made for it is removed too


@pytest.mark.parametrize("writer", ["timeseries", "paired_data", "grid"])
def test_engine_error_removes_the_file_it_created(native, tmp_path, monkeypatch, writer):
    target = tmp_path / "sub" / "owned.dss"

    def boom(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(dc, ENGINE_WRITE[writer], boom)
    with pytest.raises(RuntimeError, match="simulated write failure"):
        WRITERS[writer](target)
    assert not target.exists()
    assert not target.parent.exists()
