"""Tests for ranking_check.py — ranking robustness via CWFSS bootstrap."""

import argparse
import numpy as np
import pytest

import scoring
import ranking_check


def _make_scored_data_list(obs_field, model_fields):
    """Build obs + models, run calc_scores, rank, return data_list."""
    args = argparse.Namespace(
        parameter="precip", d_windows=[], fss_calc_mode="same",
        fss_method="default", duration=1, name="TEST_",
        save_percentiles=False, mode="normal",
        rank_by_fss_metric="fss_condensed_weighted",
        threads=1, fss_threshold_mode="over", fss_tolerance=0.1,
    )
    obs = {
        "case": "t", "exp": "t", "conf": "OBS", "type": "obs",
        "init": "2024-01-01", "lead": 1, "name": "OBS",
        "lon": np.zeros_like(obs_field), "lat": np.zeros_like(obs_field),
        "precip_data": obs_field,
        "precip_data_resampled": obs_field.copy(),
        "color": None, "ensemble": None,
    }
    scoring.calc_scores(obs, obs, args)
    data_list = [obs]

    for i, field in enumerate(model_fields):
        sim = {
            "case": "t", "exp": "t", "conf": f"M{i}", "type": "model",
            "init": "2024-01-01", "lead": 1, "name": f"M{i}",
            "lon": np.zeros_like(field), "lat": np.zeros_like(field),
            "precip_data": field,
            "precip_data_resampled": field.copy(),
            "color": f"C{i}", "ensemble": None,
        }
        scoring.calc_scores(sim, obs, args)
        data_list.append(sim)

    scoring.rank_scores(data_list)
    return data_list, args


class TestAddRankRobustnessInfo:

    @pytest.fixture
    def scored_data(self, small_fields):
        obs, fcst = small_fields
        return _make_scored_data_list(obs, [obs.copy(), fcst])

    def test_adds_cwfss_keys(self, scored_data):
        data_list, args = scored_data
        ranking_check.add_rank_robustness_info(data_list, args)
        for sim in data_list[1:]:
            assert "cwfss" in sim
            assert "cwfss_robust" in sim

    def test_cwfss_robust_is_valid(self, scored_data):
        data_list, args = scored_data
        ranking_check.add_rank_robustness_info(data_list, args)
        for sim in data_list[1:]:
            assert 0 <= sim["cwfss_robust"] <= 1


class TestExtractCwfssArray:

    @pytest.fixture
    def robust_data(self, small_fields):
        obs, fcst = small_fields
        data_list, args = _make_scored_data_list(obs, [obs.copy(), fcst])
        ranking_check.add_rank_robustness_info(data_list, args)
        return data_list

    def test_adds_cwfss_std(self, robust_data):
        ranking_check.extract_cwfss_array(robust_data)
        for sim in robust_data[1:]:
            assert "cwfss_std" in sim
            assert sim["cwfss_std"] >= 0

    def test_returns_array(self, robust_data):
        result = ranking_check.extract_cwfss_array(robust_data)
        n_models = len(robust_data) - 1
        assert result.shape == (n_models, 10000)


class TestCwfssOrdering:

    def test_perfect_beats_displaced(self, small_fields):
        """Perfect model should have higher cwfss_robust than displaced."""
        obs, fcst = small_fields
        data_list, args = _make_scored_data_list(obs, [obs.copy(), fcst])
        ranking_check.add_rank_robustness_info(data_list, args)
        perfect = data_list[1]
        displaced = data_list[2]
        assert perfect["cwfss_robust"] > displaced["cwfss_robust"]
