"""HmsAorc.download keeps the hours the caller asks for (no network: a local store)."""

import sys
import types

import numpy as np
import pandas as pd
import pytest

xr = pytest.importorskip("xarray")
pytest.importorskip("netCDF4")

from hms_commander import HmsAorc  # noqa: E402


@pytest.fixture
def aorc_store(monkeypatch):
    """One hourly store per year from 2019-12-31 to 2020-01-02, on the AORC layout."""
    aorc_module = sys.modules["hms_commander.HmsAorc"]
    monkeypatch.setattr(aorc_module, "_check_aorc_dependencies", lambda: None)
    fake_s3fs = types.ModuleType("s3fs")
    fake_s3fs.S3FileSystem = lambda anon=True: object()
    fake_s3fs.S3Map = lambda root, s3: root
    monkeypatch.setitem(sys.modules, "s3fs", fake_s3fs)

    stamps = pd.date_range("2019-12-31 00:00", "2020-01-02 23:00", freq="h")
    values = np.arange(len(stamps) * 4, dtype=np.float32).reshape(len(stamps), 2, 2)
    full = xr.Dataset(
        {HmsAorc.PRECIP_VAR: (("time", "latitude", "longitude"), values)},
        coords={"time": stamps, "latitude": [41.0, 41.1], "longitude": [-77.5, -77.4]},
    )

    def open_zarr(store):
        year = int(str(store).rsplit("/", 1)[-1].split(".")[0])
        return full.sel(time=full.time.dt.year == year)

    monkeypatch.setattr(xr, "open_zarr", open_zarr)


BOUNDS = (-77.6, 40.9, -77.3, 41.2)


def _download(tmp_path, start, end):
    nc = HmsAorc.download(BOUNDS, start, end, tmp_path / "aorc.nc")
    with xr.open_dataarray(nc) as data:
        return pd.DatetimeIndex(data.time.values), dict(data.attrs)


def test_download_keeps_the_requested_hours(aorc_store, tmp_path):
    stamps, _ = _download(tmp_path, "2020-01-01 06:00", "2020-01-01 09:00")
    assert list(stamps) == list(pd.date_range("2020-01-01 06:00", "2020-01-01 09:00", freq="h"))


def test_download_end_of_day_includes_the_stamp_at_midnight(aorc_store, tmp_path):
    # The hour 23:00-24:00 on 1 January carries the stamp 2 January 00:00.
    stamps, _ = _download(tmp_path, "2020-01-01 01:00", "2020-01-02 00:00")
    assert len(stamps) == 24
    assert stamps[-1] == pd.Timestamp("2020-01-02 00:00")


def test_download_keeps_hours_across_a_year_boundary(aorc_store, tmp_path):
    stamps, _ = _download(tmp_path, "2019-12-31 22:00", "2020-01-01 02:00")
    assert list(stamps) == list(pd.date_range("2019-12-31 22:00", "2020-01-01 02:00", freq="h"))


def test_download_records_the_time_convention(aorc_store, tmp_path):
    _, attrs = _download(tmp_path, "2020-01-01 06:00", "2020-01-01 07:00")
    assert attrs["time_semantics"] == "one-hour accumulation ending at the UTC timestamp"
    assert attrs["accumulation_interval_hours"] == 1.0
