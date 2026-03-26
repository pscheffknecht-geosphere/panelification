"""Tests for scoring.py — verification metrics and ranking."""

import copy
import os
import numpy as np
import pandas as pd
import pytest

import scoring
import parameter_settings


# =====================================================================
# array_minus_avg
# =====================================================================

class TestArrayMinusAvg:

    def test_all_above_threshold(self):
        a = np.array([0.8, 0.9, 0.7, 0.85])
        t = 0.5
        result = scoring.array_minus_avg(a, t)
        expected_avg = np.mean(a)
        np.testing.assert_allclose(result, a - expected_avg)

    def test_below_threshold_gets_minus_10(self):
        a = np.array([0.8, 0.3, 0.9])
        t = 0.5
        result = scoring.array_minus_avg(a, t)
        assert result[1] == -10.0

    def test_nan_gets_10(self):
        a = np.array([0.8, np.nan, 0.9])
        t = 0.5
        result = scoring.array_minus_avg(a, t)
        assert result[1] == 10.0

    def test_all_below_threshold(self):
        a = np.array([0.1, 0.2, 0.3])
        t = 0.5
        result = scoring.array_minus_avg(a, t)
        np.testing.assert_array_equal(result, [-10., -10., -10.])


# =====================================================================
# clamp_array
# =====================================================================

class TestClampArray:

    def test_basic_clamping(self):
        a = np.array([-0.5, 0.0, 0.5, 1.0, 1.5])
        result = scoring.clamp_array(a)
        np.testing.assert_array_equal(result, [0.0, 0.0, 0.5, 1.0, 1.0])

    def test_custom_bounds(self):
        a = np.array([1, 5, 10, 15, 20])
        result = scoring.clamp_array(a, xmin=5, xmax=15)
        np.testing.assert_array_equal(result, [5, 5, 10, 15, 15])

    def test_no_op_when_in_range(self):
        a = np.array([0.2, 0.5, 0.8])
        result = scoring.clamp_array(a)
        np.testing.assert_array_equal(result, a)


# =====================================================================
# rank_array
# =====================================================================

class TestRankArray:

    def test_nan_gets_rank_0(self):
        a = np.array([0.8, np.nan, 0.6])
        ranks = scoring.rank_array(a, 0.5)
        assert ranks[1] == 0.0

    def test_below_threshold_gets_rank_1(self):
        a = np.array([0.8, 0.3, 0.6])
        ranks = scoring.rank_array(a, 0.5)
        assert ranks[1] == 1.0

    def test_perfect_score_gets_rank_2(self):
        a = np.array([1.0, 0.8, 0.6])
        ranks = scoring.rank_array(a, 0.5)
        assert ranks[0] == 2.0

    def test_ordering_best_gets_3(self):
        a = np.array([0.9, 0.7, 0.6])
        ranks = scoring.rank_array(a, 0.5)
        assert ranks[0] == 3.0  # gold (best non-perfect)
        assert ranks[1] == 4.0  # silver
        assert ranks[2] == 5.0  # bronze

    def test_ties_share_rank(self):
        a = np.array([0.9, 0.9, 0.6])
        ranks = scoring.rank_array(a, 0.5)
        assert ranks[0] == ranks[1]  # tied


# =====================================================================
# prep_windows
# =====================================================================

class TestPrepWindows:

    def test_basic_shape(self):
        ww = [10, 20, 30]
        result = scoring.prep_windows(ww, "normal", 100, 100)
        assert result.shape == (3, 2)
        np.testing.assert_array_equal(result[:, 0], [10, 20, 30])
        np.testing.assert_array_equal(result[:, 1], [10, 20, 30])

    def test_valid_adaptive_clamps(self):
        ww = [10, 200, 500]
        result = scoring.prep_windows(ww, "valid_adaptive", 100, 80)
        # 200 > ny=80 → clamped to 80; 200 > nx=100 → clamped to 100
        assert result[1, 0] == 80   # ny
        assert result[1, 1] == 100  # nx
        assert result[2, 0] == 80
        assert result[2, 1] == 100


# =====================================================================
# fss_condensed
# =====================================================================

class TestFssCondensed:

    def test_all_perfect_fss(self):
        sim = {
            'fss': pd.DataFrame(np.ones((3, 4))),
            'fss_thresholds': [0.5, 0.5, 0.5],
        }
        score, score_arr = scoring.fss_condensed(sim)
        assert score == 12.0  # 3*4 all mapped to 1.0
        np.testing.assert_array_equal(score_arr, 1.0)

    def test_all_zero_fss(self):
        sim = {
            'fss': pd.DataFrame(np.zeros((3, 4))),
            'fss_thresholds': [0.5, 0.5, 0.5],
        }
        score, score_arr = scoring.fss_condensed(sim)
        assert score == 0.0

    def test_half_fss(self):
        """FSS=0.5 should map to 0 (it's the no-skill boundary)."""
        sim = {
            'fss': pd.DataFrame(np.full((2, 3), 0.5)),
            'fss_thresholds': [0.5, 0.5],
        }
        score, score_arr = scoring.fss_condensed(sim)
        assert score == 0.0


# =====================================================================
# calc_scores
# =====================================================================

class TestCalcScores:

    def _make_sim_dict(self, field, lon=None, lat=None, entry_type="model"):
        ny, nx = field.shape
        if lon is None:
            lon = np.zeros((ny, nx))
        if lat is None:
            lat = np.zeros((ny, nx))
        return {
            "case": "test", "exp": "test", "conf": "test",
            "type": entry_type, "init": "2024-01-01", "lead": 1,
            "name": "test_sim", "lon": lon, "lat": lat,
            "precip_data": field, "precip_data_resampled": field.copy(),
            "color": None, "ensemble": None,
        }

    def test_obs_gets_sentinels(self, make_test_args):
        args = make_test_args()
        field = np.ones((64, 64))
        obs = self._make_sim_dict(field, entry_type="obs")
        scoring.calc_scores(obs, obs, args)
        assert obs["bias"] == 999
        assert obs["fss"] is None

    def test_model_gets_all_keys(self, make_test_args, identical_fields):
        args = make_test_args()
        obs_f, fcst_f = identical_fields
        obs = self._make_sim_dict(obs_f, entry_type="obs")
        scoring.calc_scores(obs, obs, args)
        sim = self._make_sim_dict(fcst_f)
        scoring.calc_scores(sim, obs, args)
        for key in ["bias", "bias_real", "mae", "rms", "corr", "d90",
                     "fss", "fssp", "fss_condensed", "fss_condensed_weighted"]:
            assert key in sim, f"missing key: {key}"

    def test_perfect_model(self, make_test_args, identical_fields):
        args = make_test_args()
        obs_f, fcst_f = identical_fields
        obs = self._make_sim_dict(obs_f, entry_type="obs")
        scoring.calc_scores(obs, obs, args)
        sim = self._make_sim_dict(fcst_f)
        scoring.calc_scores(sim, obs, args)
        assert sim["mae"] == 0.0
        assert sim["rms"] == 0.0
        assert sim["corr"] == pytest.approx(1.0)
        assert sim["bias_real"] == 0.0


# =====================================================================
# rank_scores
# =====================================================================

class TestRankScores:

    def _make_scored_list(self, make_test_args, fields_list):
        """Build obs + n models, run calc_scores, return data_list."""
        args = make_test_args()
        obs_field = fields_list[0]
        obs = {
            "case": "t", "exp": "t", "conf": "OBS", "type": "obs",
            "init": "2024-01-01", "lead": 1, "name": "OBS",
            "lon": np.zeros_like(obs_field), "lat": np.zeros_like(obs_field),
            "precip_data": obs_field, "precip_data_resampled": obs_field.copy(),
            "color": None, "ensemble": None,
        }
        scoring.calc_scores(obs, obs, args)
        data_list = [obs]
        for i, field in enumerate(fields_list[1:]):
            sim = {
                "case": "t", "exp": "t", "conf": f"M{i}", "type": "model",
                "init": "2024-01-01", "lead": 1, "name": f"M{i}",
                "lon": np.zeros_like(field), "lat": np.zeros_like(field),
                "precip_data": field, "precip_data_resampled": field.copy(),
                "color": None, "ensemble": None,
            }
            scoring.calc_scores(sim, obs, args)
            data_list.append(sim)
        scoring.rank_scores(data_list)
        return data_list

    def test_rank_keys_exist(self, make_test_args, identical_fields):
        obs_f, _ = identical_fields
        shifted = np.roll(obs_f, 5, axis=1)
        data_list = self._make_scored_list(make_test_args, [obs_f, obs_f.copy(), shifted])
        for sim in data_list[1:]:
            for key in ["rank_mae", "rank_bias", "rank_rms", "rank_corr",
                         "rank_fss_condensed", "rank_fss_condensed_weighted"]:
                assert key in sim

    def test_rank_ordering(self, make_test_args, identical_fields):
        """Perfect model should rank better than displaced model."""
        obs_f, _ = identical_fields
        shifted = np.roll(obs_f, 10, axis=1)
        data_list = self._make_scored_list(make_test_args, [obs_f, obs_f.copy(), shifted])
        perfect = data_list[1]
        displaced = data_list[2]
        assert perfect["rank_mae"] < displaced["rank_mae"]
        assert perfect["rank_fss_condensed_weighted"] < displaced["rank_fss_condensed_weighted"]


# =====================================================================
# fss_d90
# =====================================================================

class TestFssD90:

    def test_zero_fields_returns_nan(self, make_test_args):
        args = make_test_args()
        z = np.zeros((64, 64))
        result = scoring.fss_d90(z, z, args)
        assert np.isnan(result)

    def test_identical_fields_returns_zero(self, make_test_args, small_fields):
        """Identical fields with non-trivial structure should give d90=0."""
        args = make_test_args()
        obs, _ = small_fields
        result = scoring.fss_d90(obs, obs, args)
        # surplus is zero for identical fields → d90 should be 0 or NaN
        assert result == 0.0 or np.isnan(result)


# =====================================================================
# write_scores_to_csv
# =====================================================================

class TestWriteScoresToCsv:

    def test_csv_created(self, make_test_args, identical_fields, tmp_path):
        from unittest.mock import patch
        from datetime import datetime

        args = make_test_args()
        obs_f, fcst_f = identical_fields

        obs = {
            "case": "t", "exp": "t", "conf": "OBS", "type": "obs",
            "init": "2024-01-01", "lead": 1, "name": "OBS",
            "lon": np.zeros_like(obs_f), "lat": np.zeros_like(obs_f),
            "precip_data": obs_f, "precip_data_resampled": obs_f.copy(),
            "color": None, "ensemble": None,
        }
        sim = {
            "case": "t", "exp": "t", "conf": "M0", "type": "model",
            "init": "2024-01-01", "lead": 1, "name": "M0",
            "lon": np.zeros_like(fcst_f), "lat": np.zeros_like(fcst_f),
            "precip_data": fcst_f, "precip_data_resampled": fcst_f.copy(),
            "color": None, "ensemble": None,
        }
        scoring.calc_scores(obs, obs, args)
        scoring.calc_scores(sim, obs, args)
        data_list = [obs, sim]
        scoring.rank_scores(data_list)

        windows = parameter_settings.get_windows(args)
        thresholds = parameter_settings.get_fss_thresholds(args)
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 1, 1)

        with patch("scoring.PAN_DIR_SCORES", str(tmp_path)):
            scoring.write_scores_to_csv(
                data_list, start, end, args, "TestDom", windows, thresholds)

        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) == 1
        assert csv_files[0].stat().st_size > 0
