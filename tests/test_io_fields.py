"""Tests for io_fields.py — NetCDF field file output (--save)."""

import os
from datetime import datetime, timedelta
from unittest.mock import patch

import netCDF4
import numpy as np
import pytest
import xarray as xr

import io_fields


START = datetime(2024, 7, 15, 12)
END = datetime(2024, 7, 15, 13)
NY, NX = 20, 30


def _grid(ny, nx, lon0=10., lat0=46.):
    return np.meshgrid(lon0 + 0.01 * np.arange(nx), lat0 + 0.01 * np.arange(ny))


def _entry(conf, lead, native, resampled, entry_type="model", grid=None):
    init = START - timedelta(hours=lead)
    lon, lat = grid if grid is not None else _grid(*native.shape)
    lon_r, lat_r = _grid(NY, NX)
    return {
        "exp": conf, "conf": conf, "type": entry_type,
        "init": init, "lead": lead, "name": f"{conf} {init:%Y-%m-%d %H}",
        "lon": lon, "lat": lat, "precip_data": native,
        "lon_resampled": lon_r, "lat_resampled": lat_r, "precip_data_resampled": resampled,
    }


@pytest.fixture
def run(make_test_args):
    """obs on a 25x35 grid, conf M0 at leads 3 and 6 on a 40x50 grid, conf M1 at lead 3 on a 15x15 grid"""
    rng = np.random.default_rng(0)
    def field(ny, nx):
        return rng.gamma(0.5, 4., size=(ny, nx))
    data_list = [
        _entry("OBS", 0, field(25, 35), field(NY, NX), entry_type="obs"),
        _entry("M0", 3, field(40, 50), field(NY, NX)),
        _entry("M0", 6, field(40, 50), field(NY, NX)),
        _entry("M1", 3, field(15, 15), field(NY, NX)),
    ]
    return data_list, make_test_args()


def _save(data_list, args, tmp_path):
    with patch("io_fields.PAN_DIR_DATA", str(tmp_path)):
        return io_fields.save_fields(data_list, START, END, "TestDom", args)


class TestResampled:

    def test_dimensions(self, run):
        ds = io_fields.build_resampled_dataset(run[0], START, END, "TestDom", run[1])
        assert ds["forecast_field"].dims == ("valid_time", "conf", "subdomain", "lead_hours", "y", "x")
        assert ds["obs_field"].dims == ("valid_time", "subdomain", "y", "x")
        assert ds["conf"].values.tolist() == ["M0", "M1"]
        assert ds["lead_hours"].values.tolist() == [3, 6]
        assert ds["lon"].shape == (NY, NX)

    def test_missing_forecast_is_nan(self, run):
        ds = io_fields.build_resampled_dataset(run[0], START, END, "TestDom", run[1])
        assert np.isnan(ds["forecast_field"].sel(conf="M1", lead_hours=6)).all()

    def test_file_name(self, run, tmp_path):
        path = _save(*run, tmp_path)
        assert os.path.basename(path) == "TEST_precip_fields_20240715_12UTC_01h_acc_unknown_TestDom.nc"
        assert os.listdir(tmp_path) == [os.path.basename(path)]

    def test_precision(self, run, tmp_path):
        data_list, args = run
        path = _save(data_list, args, tmp_path)
        with xr.open_dataset(path) as ds:
            assert ds["forecast_field"].dtype == np.float32
            for sim in data_list[1:]:
                stored = ds["forecast_field"].sel(conf=sim["conf"], lead_hours=sim["lead"]).squeeze()
                assert np.abs(stored.values - sim["precip_data_resampled"]).max() <= 0.005
            obs_error = np.abs(ds["obs_field"].squeeze().values - data_list[0]["precip_data_resampled"])
            assert obs_error.max() <= 0.005
            np.testing.assert_array_equal(ds["lon"].values, data_list[0]["lon_resampled"])

    def test_compression(self, run, tmp_path):
        path = _save(*run, tmp_path)
        with netCDF4.Dataset(path) as nc:
            var = nc["forecast_field"]
            assert var.filters()["zlib"] and var.filters()["shuffle"]
            assert var.least_significant_digit == io_fields.FIELD_PRECISION
            assert var.chunking() == [1, 1, 1, 1, NY, NX]

    def test_nan_and_masked_values(self, run, tmp_path):
        data_list, args = run
        data_list[1]["precip_data_resampled"][0, 0] = np.nan
        data_list[2]["precip_data_resampled"] = np.ma.masked_less(data_list[2]["precip_data_resampled"], 1.)
        path = _save(data_list, args, tmp_path)
        with xr.open_dataset(path) as ds:
            assert np.isnan(ds["forecast_field"].sel(conf="M0", lead_hours=3).squeeze()[0, 0])
            lead6 = ds["forecast_field"].sel(conf="M0", lead_hours=6).squeeze().values
            np.testing.assert_array_equal(np.isnan(lead6), data_list[2]["precip_data_resampled"].mask)

    def test_no_native_fields_by_default(self, run, tmp_path):
        path = _save(*run, tmp_path)
        with netCDF4.Dataset(path) as nc:
            assert nc.groups == {}
            assert nc.native_fields == 0


class TestNative:

    def test_groups(self, run, tmp_path):
        data_list, args = run
        args.save_native = True
        path = _save(data_list, args, tmp_path)
        with netCDF4.Dataset(path) as nc:
            assert set(nc.groups) == {"native_obs", "native_forecasts"}
            assert set(nc["native_forecasts"].groups) == {"M0", "M1"}

    def test_native_fields(self, run, tmp_path):
        data_list, args = run
        args.save_native = True
        path = _save(data_list, args, tmp_path)
        with xr.open_dataset(path, group="native_obs") as ds:
            assert np.abs(ds["obs_field"].values - data_list[0]["precip_data"]).max() <= 0.005
            np.testing.assert_array_equal(ds["lat"].values, data_list[0]["lat"])
        with xr.open_dataset(path, group="native_forecasts/M0") as ds:
            assert ds["forecast_field"].dims == ("lead_hours", "y", "x")
            assert ds["lead_hours"].values.tolist() == [3, 6]
            assert ds.attrs["conf"] == "M0"
            for sim in data_list[1:3]:
                stored = ds["forecast_field"].sel(lead_hours=sim["lead"]).values
                assert np.abs(stored - sim["precip_data"]).max() <= 0.005
            np.testing.assert_array_equal(ds["lon"].values, data_list[1]["lon"])
        with xr.open_dataset(path, group="native_forecasts/M1") as ds:
            assert ds["forecast_field"].shape == (1, 15, 15)

    def test_changing_grid_is_split(self, run, tmp_path):
        data_list, args = run
        args.save_native = True
        data_list[2]["lon"], data_list[2]["lat"] = _grid(40, 50, lon0=11.)
        path = _save(data_list, args, tmp_path)
        with netCDF4.Dataset(path) as nc:
            assert set(nc["native_forecasts"].groups) == {"M0", "M0_grid2", "M1"}
        with xr.open_dataset(path, group="native_forecasts/M0_grid2") as ds:
            assert ds["lead_hours"].values.tolist() == [6]
