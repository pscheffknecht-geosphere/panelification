"""Tests for convert_legacy_output.py — legacy score CSV files and FSS pickles to NetCDF score files.

The converter is standalone, so these tests write the legacy files themselves
instead of using the legacy writers of panelification.
"""

import os
import pickle
import subprocess
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import xarray as xr

import convert_legacy_output as legacy


START = datetime(2024, 7, 15, 12)
STEM = "20240715_12UTC_01h_acc_Lower_Austria"
NETCDF_NAME = "TEST_precip_scores_20240715_12UTC_01h_acc_Austria_Lower_Austria.nc"
THRESHOLDS = [0.1, 1., 5., 10., 25., 35., 50., 75., 100., 99999.]
WINDOWS = [10, 20, 30, 40, 60, 80, 100, 120, 140, 160, 180, 200]
PERCENTILES = [25, 50, 75, 90, 95]

# forecasts of the legacy test run: sim name, conf, init time, lead time in hours
FORECASTS = [
    ("M0 2024-07-15 09", "M0", "2024-07-15 09:00:00", 3),
    ("M0 2024-07-15 06", "M0", "2024-07-15 06:00:00", 6),
    ("M1 2024-07-15 09", "M1", "2024-07-15 09:00:00", 3),
]
PSEUDO_MEMBER = ("claef1k_20240715_09_mean", "claef1k_20240715_09_mean", "2024-07-15 09:00:00", 3)


def _scores(k):
    """Scores and field statistics of row k of a legacy score file, row 0 is the observation."""
    return {
        "maximum": 50. + k, "average": 5. + k,
        "99th": 40. + k, "95th": 30. + k, "90th": 20. + k, "75th": 10. + k, "50th": 1. + k,
        "bias": 0.5 * k - 0.75, "mae": 1.25 * k, "rms": 2.5 * k, "corr": 1. - 0.25 * k,
        "d90": 9999. if k == 2 else 10. * k,
        "fss_condensed": 3. * k, "fss_condensed_weighted": 4. * k,
        "rank_mae": k, "rank_bias": k, "rank_rms": k, "rank_corr": k, "rank_d90": k,
        "rank_fss_condensed": k, "rank_fss_condensed_weighted": k,
    }


def _fss_frames(k):
    """FSS data frames of forecast k as in legacy FSS pickles, the last threshold is the dummy row."""
    num = (k + 1) * np.outer(np.arange(1, 11), np.arange(1, 13)) / 997.
    den = 2. * num + 0.5
    num[-1], den[-1] = 0., 0.
    with np.errstate(invalid="ignore", divide="ignore"):
        fss = 1. - num / den
    pnum = (k + 1) * np.outer(np.arange(1, 6), np.arange(1, 13)) / 991.
    pden = 3. * pnum + 0.25
    return {
        "fss": pd.DataFrame(fss, index=THRESHOLDS, columns=WINDOWS),
        "fssp": pd.DataFrame(1. - pnum / pden, index=PERCENTILES, columns=WINDOWS),
        "fss_num": pd.DataFrame(num, index=THRESHOLDS, columns=WINDOWS),
        "fssp_num": pd.DataFrame(pnum, index=PERCENTILES, columns=WINDOWS),
        "fss_den": pd.DataFrame(den, index=THRESHOLDS, columns=WINDOWS),
        "fssp_den": pd.DataFrame(pden, index=PERCENTILES, columns=WINDOWS),
    }


def _write_legacy_run(directory, scores=True, fss=True, percentiles=False, forecasts=FORECASTS):
    """Write the legacy output files of one run in the format used since late 2025."""
    rows = [{"conf": "OPERA", "init": "1900-01-01 00:00:00", "lead": -1, "name": "OPERA", **_scores(0)}]
    rows += [{"conf": conf, "init": init, "lead": lead, "name": name, **_scores(k + 1)}
             for k, (name, conf, init, lead) in enumerate(forecasts)]
    if scores:
        pd.DataFrame(rows).to_csv(directory / f"TEST_RR_score_{STEM}.csv", sep=";", index=False)
    if percentiles:
        percentile_rows = [{**{key: row[key] for key in ["conf", "init", "lead", "name"]},
                            **{f"{p}th": p + k for p in range(101)}} for k, row in enumerate(rows)]
        pd.DataFrame(percentile_rows).to_csv(directory / f"TEST_RR_percentiles_score_{STEM}.csv",
                                             sep=";", index=False)
    if fss:
        with open(directory / f"TEST_FSS_data_{STEM}.p", "wb") as f:
            pickle.dump({name: _fss_frames(k) for k, (name, *_) in enumerate(forecasts)}, f)
    return str(directory)


def _convert(directory, region="Austria", **kwargs):
    runs = legacy.find_legacy_runs(directory, directory)
    assert len(runs) == 1
    return legacy.convert_run(runs[0], region, **kwargs)


def _at(ds, var, conf, lead):
    """Values of one forecast, without the single valid_time and subdomain."""
    return ds[var].sel(conf=conf, lead_hours=lead).isel(valid_time=0, subdomain=0)


def test_imports_no_panelification_module():
    scr_dir = os.path.dirname(legacy.__file__)
    core_modules = sorted(name[:-3] for name in os.listdir(scr_dir)
                          if name.endswith(".py") and name != "convert_legacy_output.py")
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import convert_legacy_output; "
            "print(' '.join(sorted(set(sys.argv[2:]) & set(sys.modules))))")
    result = subprocess.run([sys.executable, "-c", code, scr_dir, *core_modules],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == ""


# =====================================================================
# finding legacy runs
# =====================================================================

class TestFindLegacyRuns:

    def test_groups_files_of_one_run(self, tmp_path):
        for name in ["INCA_RR_score_20250701_03UTC_03h_acc_Lower_Austria.csv",
                     "INCA_RR_percentiles_score_20250701_03UTC_03h_acc_Lower_Austria.csv",
                     "INCA_FSS_data_20250701_03UTC_03h_acc_Lower_Austria.p",
                     "OTHER_RR_score_20250701_03UTC_03h_acc_Tyrol.csv"]:
            (tmp_path / name).touch()
        runs = legacy.find_legacy_runs(str(tmp_path), str(tmp_path))
        assert [run.name for run in runs] == ["INCA_", "OTHER_"]
        run = runs[0]
        assert (run.start, run.duration, run.subdomain) == (datetime(2025, 7, 1, 3), 3, "Lower_Austria")
        assert os.path.basename(run.scores_csv) == "INCA_RR_score_20250701_03UTC_03h_acc_Lower_Austria.csv"
        assert os.path.basename(run.percentiles_csv).startswith("INCA_RR_percentiles_score_")
        assert os.path.basename(run.fss_pickle) == "INCA_FSS_data_20250701_03UTC_03h_acc_Lower_Austria.p"

    def test_name_filter(self, tmp_path):
        (tmp_path / "INCA_RR_score_20250701_03UTC_03h_acc_Default.csv").touch()
        (tmp_path / "OTHER_RR_score_20250701_03UTC_03h_acc_Default.csv").touch()
        runs = legacy.find_legacy_runs(str(tmp_path), str(tmp_path), name="INCA")
        assert [run.name for run in runs] == ["INCA_"]

    def test_old_file_name_with_drawing_mode(self, tmp_path):
        (tmp_path / "old_RR_normal_score_20230419_12UTC_24h_acc_Default.csv").touch()
        run, = legacy.find_legacy_runs(str(tmp_path), str(tmp_path))
        assert (run.name, run.start, run.duration) == ("old_", datetime(2023, 4, 19, 12), 24)

    def test_precip2_for_long_accumulations(self):
        assert legacy.run_parameter("precip", 12) == "precip"
        assert legacy.run_parameter("precip", 24) == "precip2"
        assert legacy.run_parameter("cma", 24) == "cma"


# =====================================================================
# converting one run
# =====================================================================

class TestConvertRun:

    def test_forecast_grid_and_axes(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path))
        grid = ("valid_time", "conf", "subdomain", "lead_hours")
        assert ds["conf"].values.tolist() == ["M0", "M1"]
        assert ds["lead_hours"].values.tolist() == [3, 6]
        assert ds["subdomain"].values.tolist() == ["Lower_Austria"]
        assert ds["valid_time"].values[0] == np.datetime64(START, "ns")
        assert ds["threshold"].values.tolist() == THRESHOLDS[:-1]
        assert ds["window"].values.tolist() == WINDOWS
        assert ds["pct_threshold"].values.tolist() == PERCENTILES
        assert ds["percentile"].values.tolist() == [50, 75, 90, 95, 99]
        assert ds["mae"].dims == grid
        assert ds["fss_num"].dims == grid + ("threshold", "window")
        assert ds["fssp_num"].dims == grid + ("pct_threshold", "window")
        assert ds["obs_percentile"].dims == ("valid_time", "subdomain", "percentile")

    def test_scores_and_statistics(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path))
        for k, (_, conf, _, lead) in enumerate(FORECASTS, start=1):
            expected = _scores(k)
            for var in ["bias", "mae", "rms", "corr", "fss_condensed", "fss_condensed_weighted",
                        "rank_mae", "rank_fss_condensed_weighted"]:
                assert _at(ds, var, conf, lead) == expected[var], var
            assert _at(ds, "forecast_max", conf, lead) == expected["maximum"]
            assert _at(ds, "forecast_mean", conf, lead) == expected["average"]
            assert _at(ds, "forecast_percentile", conf, lead).sel(percentile=90) == expected["90th"]
        assert _at(ds, "d90", "M0", 3) == 10.
        assert np.isnan(_at(ds, "d90", "M0", 6))  # legacy 9999
        assert np.isnan(_at(ds, "mae", "M1", 6))  # no forecast
        assert ds["obs_max"].item() == 50.
        assert ds["obs_percentile"].values.ravel().tolist() == [1., 10., 20., 30., 40.]

    def test_fss_arrays_without_dummy_threshold(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path))
        for k, (_, conf, _, lead) in enumerate(FORECASTS):
            frames = _fss_frames(k)
            for var in ["fss", "fss_num", "fss_den"]:
                np.testing.assert_array_equal(_at(ds, var, conf, lead).values, frames[var].to_numpy()[:-1])
            for var in ["fssp", "fssp_num", "fssp_den"]:
                np.testing.assert_array_equal(_at(ds, var, conf, lead).values, frames[var].to_numpy())
        assert np.isnan(_at(ds, "fss_num", "M1", 6)).all()

    def test_run_metadata(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path), verif_dataset="INCAPlus")
        assert ds.attrs["schema_version"] == legacy.SCHEMA_VERSION
        assert ds.attrs["experiment_name"] == "TEST"
        assert ds.attrs["parameter"] == "precip"
        assert ds.attrs["parameter_units"] == "mm"
        assert ds.attrs["region"] == "Austria"
        assert ds.attrs["verif_dataset"] == "INCAPlus"
        assert ds.attrs["accumulation_hours"] == 1
        assert ds.attrs["valid_start"] == START.isoformat()
        assert ds.attrs["converted_from"] == f"TEST_RR_score_{STEM}.csv TEST_FSS_data_{STEM}.p"
        assert "fss_threshold_mode" not in ds.attrs

    def test_percentiles_file(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path, percentiles=True))
        assert ds["percentile"].values.tolist() == list(range(101))
        assert _at(ds, "forecast_percentile", "M1", 3).values.tolist() == [p + 3. for p in range(101)]
        assert ds["obs_percentile"].values.ravel().tolist() == [float(p) for p in range(101)]

    def test_pseudo_member_conf_without_init(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path, forecasts=FORECASTS + [PSEUDO_MEMBER]))
        assert ds["conf"].values.tolist() == ["M0", "M1", "claef1k_mean"]
        np.testing.assert_array_equal(_at(ds, "fss_num", "claef1k_mean", 3).values,
                                      _fss_frames(3)["fss_num"].to_numpy()[:-1])

    def test_score_file_only(self, tmp_path):
        ds = _convert(_write_legacy_run(tmp_path, fss=False))
        assert "mae" in ds
        assert "fss_num" not in ds

    def test_fss_pickle_only(self, tmp_path, caplog):
        ds = _convert(_write_legacy_run(tmp_path, scores=False, forecasts=FORECASTS + [PSEUDO_MEMBER]))
        # without score file, pseudo members cannot be placed, they have no init time in their name
        assert ds["conf"].values.tolist() == ["M0", "M1"]
        assert "cannot determine conf and init time of claef1k_20240715_09_mean" in caplog.text
        assert "mae" not in ds
        assert np.isnan(ds["obs_max"]).all()
        np.testing.assert_array_equal(_at(ds, "fss_num", "M0", 6).values, _fss_frames(1)["fss_num"].to_numpy()[:-1])

    def test_old_comma_separated_score_file(self, tmp_path):
        """Score files before September 2025: comma separated, underscores in names, no observation row."""
        (tmp_path / "old_RR_normal_score_20230419_12UTC_12h_acc_Default.csv").write_text(
            "name,bias,mae,rms,corr,d90,rank_bias,rank_mae,rank_rms,rank_corr,rank_d90,"
            "fss_rank_score,fss_success_rate_abs,fss_percentiles_rank_score,fss_success_rate_rel\n"
            "arome_hun_2023-04-19_06,0.50000,1.20000,2.00000,0.80000,9999.00000,1,1,1,1,1,"
            "3.00000,0.50000,2.00000,0.40000\n"
            "ecmwf_2023-04-19_00,-0.25000,1.50000,2.50000,0.70000,12.50000,2,2,2,2,2,"
            "1.00000,0.20000,1.00000,0.10000\n")
        ds = _convert(str(tmp_path))
        assert ds["conf"].values.tolist() == ["arome_hun", "ecmwf"]
        assert ds["lead_hours"].values.tolist() == [6, 12]
        assert _at(ds, "mae", "arome_hun", 6) == 1.2
        assert _at(ds, "bias", "ecmwf", 12) == -0.25
        assert np.isnan(_at(ds, "d90", "arome_hun", 6))
        assert np.isnan(ds["obs_max"]).all()
        assert np.isnan(ds["forecast_max"]).all()
        assert "fss_rank_score" not in ds

    def test_duplicate_forecasts_raise(self, tmp_path):
        with pytest.raises(ValueError, match="same conf and lead time"):
            _convert(_write_legacy_run(tmp_path, forecasts=FORECASTS + [FORECASTS[0]]))

    def test_warns_about_thresholds_of_other_parameter(self, tmp_path, caplog):
        directory = _write_legacy_run(tmp_path)
        _convert(directory)
        assert "differ from the thresholds" not in caplog.text
        _convert(directory, parameter="precip3")
        assert "differ from the thresholds of parameter precip3" in caplog.text


# =====================================================================
# command line
# =====================================================================

class TestMain:

    def _argv(self, directory, *extra):
        return ["--region", "Austria", "--scores_dir", directory, "--data_dir", directory, *extra]

    def test_writes_netcdf_next_to_the_score_files(self, tmp_path):
        directory = _write_legacy_run(tmp_path)
        assert legacy.main(self._argv(directory)) == 0
        assert NETCDF_NAME in os.listdir(directory)
        assert not [name for name in os.listdir(directory) if ".tmp" in name]
        with xr.open_dataset(tmp_path / NETCDF_NAME) as ds:
            assert ds["fss_num"].dtype == np.float32
            assert ds["mae"].dtype == np.float64
            np.testing.assert_allclose(_at(ds, "fss_num", "M0", 3).values,
                                       _fss_frames(0)["fss_num"].to_numpy()[:-1], rtol=1e-6)

    def test_output_dir(self, tmp_path):
        output_dir = tmp_path / "NETCDF"
        assert legacy.main(self._argv(_write_legacy_run(tmp_path), "--output_dir", str(output_dir))) == 0
        assert os.listdir(output_dir) == [NETCDF_NAME]

    def test_existing_file_only_replaced_with_overwrite(self, tmp_path):
        directory = _write_legacy_run(tmp_path)
        target = tmp_path / NETCDF_NAME
        target.write_text("existing file")
        assert legacy.main(self._argv(directory)) == 0
        assert target.read_text() == "existing file"
        assert legacy.main(self._argv(directory, "--overwrite")) == 0
        with xr.open_dataset(target) as ds:
            assert "mae" in ds

    def test_dry_run_writes_nothing(self, tmp_path):
        directory = _write_legacy_run(tmp_path)
        files = sorted(os.listdir(directory))
        assert legacy.main(self._argv(directory, "--dry_run")) == 0
        assert sorted(os.listdir(directory)) == files

    def test_failed_run_does_not_stop_the_others(self, tmp_path):
        directory = _write_legacy_run(tmp_path)
        (tmp_path / "BROKEN_RR_score_20240715_12UTC_01h_acc_Default.csv").touch()
        assert legacy.main(self._argv(directory)) == 1
        assert NETCDF_NAME in os.listdir(directory)
