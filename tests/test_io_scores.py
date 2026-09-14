"""Tests for io_scores.py — NetCDF score file output."""

import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest
import xarray as xr

import io_scores
import scoring


START = datetime(2024, 7, 15, 12)
END = datetime(2024, 7, 15, 13)


def _entry(field, conf, lead, entry_type="model"):
    init = START - timedelta(hours=lead)
    return {
        "exp": conf, "conf": conf, "type": entry_type,
        "init": init, "lead": lead, "name": f"{conf} {init:%Y-%m-%d %H}",
        "lon": np.zeros_like(field), "lat": np.zeros_like(field),
        "precip_data": field, "precip_data_resampled": field.copy(),
        "color": None, "ensemble": None,
    }


def _build(data_list, args):
    return io_scores.build_run_dataset(data_list, START, END, "TestDom", args)


def _at(ds, var, conf, lead):
    """Values of one forecast, without the single valid_time and subdomain."""
    return ds[var].sel(conf=conf, lead_hours=lead).isel(valid_time=0, subdomain=0)


@pytest.fixture
def scored_run(make_test_args, small_fields):
    """Scored data_list: obs, conf M0 at leads 3 and 6, conf M1 at lead 3 only."""
    args = make_test_args()
    obs_field, fcst_field = small_fields
    data_list = [
        _entry(obs_field, "OBS", 0, entry_type="obs"),
        _entry(fcst_field, "M0", 3),
        _entry(np.roll(obs_field, 4, axis=1), "M0", 6),
        _entry(1.5 * obs_field, "M1", 3),
    ]
    for sim in data_list:
        scoring.calc_scores(sim, data_list[0], args)
    scoring.rank_scores(data_list)
    return data_list, args


# =====================================================================
# structure
# =====================================================================

class TestStructure:

    def test_forecast_grid(self, scored_run):
        ds = _build(*scored_run)
        assert ds["conf"].values.tolist() == ["M0", "M1"]
        assert ds["lead_hours"].values.tolist() == [3, 6]
        assert ds["subdomain"].values.tolist() == ["TestDom"]
        assert ds["valid_time"].values[0] == np.datetime64(START, "ns")

    def test_dimensions_of_variables(self, scored_run):
        ds = _build(*scored_run)
        grid = ("valid_time", "conf", "subdomain", "lead_hours")
        assert ds["mae"].dims == grid
        assert ds["forecast_percentile"].dims == grid + ("percentile",)
        assert ds["fss_num"].dims == grid + ("threshold", "window")
        assert ds["fssp_num"].dims == grid + ("pct_threshold", "window")
        assert ds["obs_percentile"].dims == ("valid_time", "subdomain", "percentile")

    def test_fss_axes_from_data_frames(self, scored_run):
        data_list, args = scored_run
        ds = _build(data_list, args)
        sim = data_list[1]
        # the last threshold is the dummy row separating the sections of the FSS plots
        assert sim["fss"].index[-1] >= io_scores.DUMMY_THRESHOLD
        np.testing.assert_array_equal(ds["threshold"].values, sim["fss"].index[:-1])
        np.testing.assert_array_equal(ds["window"].values, sim["fss"].columns)
        np.testing.assert_array_equal(ds["pct_threshold"].values, sim["fssp"].index)

    def test_default_percentiles(self, scored_run):
        ds = _build(*scored_run)
        assert ds["percentile"].values.tolist() == [50, 75, 90, 95, 99]

    def test_all_percentiles(self, scored_run):
        data_list, args = scored_run
        args.save_percentiles = True
        ds = _build(data_list, args)
        assert ds["percentile"].values.tolist() == list(range(101))

    def test_run_metadata(self, scored_run):
        ds = _build(*scored_run)
        assert ds.attrs["schema_version"] == io_scores.SCHEMA_VERSION
        assert ds.attrs["experiment_name"] == "TEST"
        assert ds.attrs["parameter"] == "precip"
        assert ds.attrs["parameter_units"] == "mm"
        assert ds.attrs["region"] == "unknown"
        assert ds.attrs["accumulation_hours"] == 1
        assert ds.attrs["valid_start"] == START.isoformat()
        assert ds.attrs["valid_end"] == END.isoformat()
        assert ds.attrs["fss_threshold_mode"] == "over"

    def test_subdomain_bounds_from_region(self, scored_run):
        data_list, args = scored_run
        lon, lat = np.meshgrid(np.linspace(10., 12., 5), np.linspace(46., 47., 3))
        args.region = SimpleNamespace(name="Austria", subdomains={"TestDom": {"lon": lon, "lat": lat}})
        ds = _build(data_list, args)
        assert ds.attrs["region"] == "Austria"
        assert ds.attrs["subdomain_lon_min"] == 10.
        assert ds.attrs["subdomain_lat_max"] == 47.
        assert (ds.attrs["subdomain_ny"], ds.attrs["subdomain_nx"]) == (3, 5)


# =====================================================================
# values
# =====================================================================

class TestValues:

    def test_scalar_scores_match_sims(self, scored_run):
        data_list, args = scored_run
        ds = _build(data_list, args)
        for sim in data_list[1:]:
            conf, lead = sim["conf"], sim["lead"]
            assert _at(ds, "bias", conf, lead) == sim["bias_real"]
            for key in ["mae", "rms", "corr", "fss_condensed", "fss_condensed_weighted",
                        "fss_condensed_weighted_rect", "rank_mae", "rank_fss_condensed_weighted"]:
                assert _at(ds, key, conf, lead) == sim[key], key

    def test_fss_arrays_match_data_frames(self, scored_run):
        data_list, args = scored_run
        ds = _build(data_list, args)
        for sim in data_list[1:]:
            conf, lead = sim["conf"], sim["lead"]
            for var in ["fss", "fss_num", "fss_den"]:
                np.testing.assert_array_equal(_at(ds, var, conf, lead).values, sim[var].to_numpy()[:-1])
            for var in ["fssp", "fssp_num", "fssp_den"]:
                np.testing.assert_array_equal(_at(ds, var, conf, lead).values, sim[var].to_numpy())

    def test_missing_forecast_is_nan(self, scored_run):
        ds = _build(*scored_run)
        assert np.isnan(_at(ds, "mae", "M1", 6))
        assert np.isnan(_at(ds, "fss_num", "M1", 6)).all()

    def test_field_statistics_ignore_missing_values(self, scored_run):
        data_list, args = scored_run
        obs_field = data_list[0]["precip_data_resampled"]
        obs_field[:5, :5] = np.nan  # coverage gap in the observation
        ds = _build(data_list, args)
        assert ds["obs_max"].item() == np.nanmax(obs_field)
        assert ds["obs_mean"].item() == pytest.approx(np.nanmean(obs_field))
        np.testing.assert_allclose(ds["obs_percentile"].values.ravel(),
                                   np.nanpercentile(obs_field, [50, 75, 90, 95, 99]))
        sim = data_list[3]
        assert _at(ds, "forecast_max", "M1", 3) == np.nanmax(sim["precip_data_resampled"])

    def test_undefined_d90_is_nan(self, scored_run):
        data_list, args = scored_run
        data_list[1]["d90"] = io_scores.D90_UNDEFINED
        ds = _build(data_list, args)
        assert np.isnan(_at(ds, "d90", "M0", 3))


# =====================================================================
# rules
# =====================================================================

class TestRules:

    def test_lead_hours_derived_from_init(self, scored_run):
        data_list, args = scored_run
        data_list[1]["lead"] = 99  # an inconsistent lead must not matter
        ds = _build(data_list, args)
        assert ds["lead_hours"].values.tolist() == [3, 6]

    def test_duplicate_forecast_raises(self, scored_run):
        data_list, args = scored_run
        data_list.append(dict(data_list[1]))
        with pytest.raises(ValueError, match="same conf and lead time"):
            _build(data_list, args)

    def test_pseudo_member_conf_without_init(self, scored_run):
        data_list, args = scored_run
        data_list.append(dict(data_list[1], conf="claef1k_20240715_09_mean",
                              name="claef1k_20240715_09_mean", pseudo=True))
        ds = _build(data_list, args)
        assert ds["conf"].values.tolist() == ["M0", "M1", "claef1k_mean"]

    def test_without_full_fss(self, scored_run):
        data_list, args = scored_run
        args.save_full_fss = False
        ds = _build(data_list, args)
        for var in ["fss", "fss_num", "fss_den", "fssp", "fssp_num", "fssp_den"]:
            assert var not in ds
        assert "mae" in ds

    def test_optional_scores_only_when_present(self, scored_run):
        data_list, args = scored_run
        assert "cwfss_robust" not in _build(data_list, args)
        data_list[1]["cwfss_robust"] = 0.5
        ds = _build(data_list, args)
        assert _at(ds, "cwfss_robust", "M0", 3) == 0.5
        assert np.isnan(_at(ds, "cwfss_robust", "M1", 3))


# =====================================================================
# file output
# =====================================================================

class TestFileOutput:

    def test_file_name(self, make_test_args):
        args = make_test_args(region=SimpleNamespace(name="Austria", subdomains={}))
        path = io_scores.score_file_path(args, START, "Default")
        assert os.path.basename(path) == "TEST_precip_scores_20240715_12UTC_01h_acc_Austria_Default.nc"

    def test_parameter_in_file_name(self, make_test_args):
        precip = io_scores.score_file_path(make_test_args(parameter="precip"), START, "Default")
        cma = io_scores.score_file_path(make_test_args(parameter="cma"), START, "Default")
        assert precip != cma

    def test_written_file_matches_dataset(self, scored_run, tmp_path):
        data_list, args = scored_run
        with patch("io_scores.PAN_DIR_SCORES", str(tmp_path)):
            path = io_scores.save_scores(data_list, START, END, "TestDom", args)
        # only the final file is left, no temporary file
        assert os.listdir(tmp_path) == [os.path.basename(path)]
        expected = _build(data_list, args)
        with xr.open_dataset(path) as ds:
            assert set(ds.data_vars) == set(expected.data_vars)
            for var in expected.data_vars:
                np.testing.assert_allclose(ds[var].values, expected[var].values, rtol=1e-6)
            assert ds["fss_num"].dtype == np.float32
            assert ds["mae"].dtype == np.float64
            assert ds.attrs["parameter"] == "precip"
            assert ds.attrs["source"].startswith("panelification ")

    def test_failed_write_leaves_no_file(self, scored_run, tmp_path):
        data_list, args = scored_run

        def partial_write(self, path, **kwargs):
            with open(path, "w") as f:
                f.write("partial")
            raise OSError("disk full")

        with patch("io_scores.PAN_DIR_SCORES", str(tmp_path)), \
                patch.object(xr.Dataset, "to_netcdf", partial_write):
            with pytest.raises(OSError):
                io_scores.save_scores(data_list, START, END, "TestDom", args)
        assert os.listdir(tmp_path) == []
