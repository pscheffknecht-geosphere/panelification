"""Tests for weather_regimes.py and the weather regime variables of the score files."""

import os
from datetime import date, datetime, timedelta
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

import io_scores
import weather_regimes
from test_io_scores import END, START, _entry


WLK_LINES = [
    "20240714\t 04AAD 04ACD 04ACD 05 15 15",
    "20240715\t 03CAD 03CCD 01ACD 34 34 12",
    "20240716\t 00ACD 00AAD 00AAD 21 21 21",
    "20240717\t 07ACD 00AAD",
    "",
]


@pytest.fixture
def wlk_file(tmp_path):
    path = tmp_path / "WLK.txt"
    path.write_text("\n".join(WLK_LINES))
    yield str(path)
    weather_regimes.read_wlk.cache_clear()


class TestReadWlk:

    def test_parses_regime_and_cyclonality(self, wlk_file):
        days = weather_regimes.read_wlk(wlk_file)
        assert days[date(2024, 7, 14)] == (4, 0, 0)
        assert days[date(2024, 7, 15)] == (3, 1, 0)
        assert days[date(2024, 7, 16)] == (0, 0, 1)

    def test_skips_unknown_regime(self, wlk_file):
        assert date(2024, 7, 17) not in weather_regimes.read_wlk(wlk_file)

    def test_missing_file(self, tmp_path):
        assert weather_regimes.read_wlk(str(tmp_path / "missing.txt")) == {}


class TestWlkFile:

    def test_explicit_path(self, tmp_path):
        assert weather_regimes.wlk_file(str(tmp_path / "x.txt")) == str(tmp_path / "x.txt")

    def test_first_existing_file(self, tmp_path, wlk_file):
        candidates = [str(tmp_path / "missing.txt"), wlk_file]
        with patch("weather_regimes.WLK_FILES", candidates):
            assert weather_regimes.wlk_file() == wlk_file
            assert weather_regimes.wlk_file(None) == wlk_file

    def test_operational_file_preferred(self, tmp_path, wlk_file):
        fallback = tmp_path / "fallback.txt"
        fallback.write_text("")
        with patch("weather_regimes.WLK_FILES", [wlk_file, str(fallback)]):
            assert weather_regimes.wlk_file() == wlk_file

    def test_none_existing_gives_fallback(self, tmp_path):
        candidates = [str(tmp_path / "a.txt"), str(tmp_path / "b.txt")]
        with patch("weather_regimes.WLK_FILES", candidates):
            assert weather_regimes.wlk_file() == candidates[-1]


class TestLabel:

    def test_label(self):
        day = date(2024, 7, 15)
        assert weather_regimes.label(day, (3, 1, 0)) == "NW, 925 hPa cycl., 500 hPa anticycl."
        assert weather_regimes.label(day, (4, 0, 1)) == "weak gradient, 925 hPa anticycl., 500 hPa cycl."

    def test_unknown(self):
        assert weather_regimes.label(date(2024, 7, 15), None) == "weather regime unknown"

    def test_several_days(self):
        assert weather_regimes.label(None, None) == "several days, no weather regime"


class TestRegimeDate:

    @pytest.mark.parametrize("start, hours", [
        (datetime(2024, 7, 15, 0), 24),
        (datetime(2024, 7, 15, 0), 1),
        (datetime(2024, 7, 15, 6), 12),
        (datetime(2024, 7, 15, 12), 12),
        (datetime(2024, 7, 15, 23), 1),
    ])
    def test_within_one_day(self, start, hours):
        assert weather_regimes.regime_date(start, start + timedelta(hours=hours)) == date(2024, 7, 15)

    @pytest.mark.parametrize("start, hours", [
        (datetime(2024, 7, 15, 12), 24),
        (datetime(2024, 7, 15, 23), 2),
        (datetime(2024, 7, 15, 0), 48),
        (datetime(2024, 7, 14, 6), 72),
    ])
    def test_several_days(self, start, hours):
        assert weather_regimes.regime_date(start, start + timedelta(hours=hours)) is None

    def test_several_days_not_looked_up(self, wlk_file):
        start = datetime(2024, 7, 15, 12)
        assert weather_regimes.weather_regime(start, start + timedelta(hours=24), wlk_file) == (None, None)


class TestScoreFile:

    def _data_list(self, small_fields):
        obs_field, fcst_field = small_fields
        return [_entry(obs_field, "OBS", 0, entry_type="obs"), _entry(fcst_field, "M0", 3)]

    def test_stored_in_dataset(self, small_fields, make_test_args, wlk_file):
        args = make_test_args(weather_regime_file=wlk_file)
        ds = io_scores.build_run_dataset(self._data_list(small_fields), START, END, "TestDom", args)
        assert ds["weather_regime"].dims == ("valid_time",)
        assert ds["weather_regime"].item() == 3
        assert ds["cyclonality_925"].item() == 1
        assert ds["cyclonality_500"].item() == 0
        assert ds["weather_regime"].attrs["flag_meanings"] == "NE SE SW NW weak_gradient"

    def test_unclassified_day_is_missing(self, small_fields, make_test_args, wlk_file):
        args = make_test_args(weather_regime_file=wlk_file)
        start = datetime(2025, 1, 1, 12)
        ds = io_scores.build_run_dataset(self._data_list(small_fields), start, start + timedelta(hours=1),
                                         "TestDom", args)
        for name in io_scores.WEATHER_REGIME_VARIABLES:
            assert np.isnan(ds[name].item())

    def test_several_days_is_missing(self, small_fields, make_test_args, wlk_file):
        args = make_test_args(weather_regime_file=wlk_file)
        ds = io_scores.build_run_dataset(self._data_list(small_fields), START, START + timedelta(hours=24),
                                         "TestDom", args)
        for name in io_scores.WEATHER_REGIME_VARIABLES:
            assert np.isnan(ds[name].item())
        assert "more than one day" in ds["weather_regime"].attrs["comment"]

    def test_written_as_int8(self, small_fields, make_test_args, wlk_file, tmp_path):
        args = make_test_args(weather_regime_file=wlk_file)
        with patch("io_scores.PAN_DIR_SCORES", str(tmp_path)):
            path = io_scores.save_scores(self._data_list(small_fields), START, END, "TestDom", args)
        with xr.open_dataset(path, mask_and_scale=False) as ds:
            assert ds["weather_regime"].dtype == np.int8
            assert ds["weather_regime"].item() == 3
        with xr.open_dataset(path) as ds:
            assert ds["cyclonality_925"].item() == 1

    def test_missing_written_as_fill_value(self, small_fields, make_test_args, tmp_path):
        args = make_test_args(weather_regime_file=str(tmp_path / "missing.txt"))
        with patch("io_scores.PAN_DIR_SCORES", str(tmp_path)):
            path = io_scores.save_scores(self._data_list(small_fields), START, END, "TestDom", args)
        weather_regimes.read_wlk.cache_clear()
        with xr.open_dataset(path, mask_and_scale=False) as ds:
            assert ds["weather_regime"].item() == io_scores.WEATHER_REGIME_FILL
        with xr.open_dataset(path) as ds:
            assert np.isnan(ds["weather_regime"].item())
