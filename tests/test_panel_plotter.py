"""Tests for panel_plotter.py — pure helper functions only."""

import numpy as np
import pytest

import panel_plotter


# =====================================================================
# get_array_edge
# =====================================================================

class TestGetArrayEdge:

    def test_3x3_known_result(self):
        arr = np.array([[1, 2, 3],
                        [4, 5, 6],
                        [7, 8, 9]])
        edge = panel_plotter.get_array_edge(arr)
        # e1=top row [1,2,3], e2=right col skip first [6,9],
        # e3=bottom row reversed skip last [8,7], e4=left col reversed skip last [4,1]
        expected = np.array([1, 2, 3, 6, 9, 8, 7, 4, 1])
        np.testing.assert_array_equal(edge, expected)

    def test_edge_length(self):
        """Edge traces the perimeter with one overlapping corner."""
        for m, n in [(4, 5), (3, 3), (10, 7)]:
            arr = np.ones((m, n))
            edge = panel_plotter.get_array_edge(arr)
            # n + (m-1) + (n-1) + (m-1) = 2m + 2n - 3
            expected_len = 2 * m + 2 * n - 3
            assert len(edge) == expected_len, f"({m},{n}): got {len(edge)}, expected {expected_len}"

    def test_4x4_all_values_present(self):
        arr = np.arange(16).reshape(4, 4)
        edge = panel_plotter.get_array_edge(arr)
        # all border values should appear (interior value 5,6,9,10 should not)
        border_vals = {0, 1, 2, 3, 4, 7, 8, 11, 12, 13, 14, 15}
        assert set(edge) == border_vals


# =====================================================================
# arrange_subplots
# =====================================================================

class TestArrangeSubplots:

    def test_returns_6_items(self):
        result = arrange_subplots_result = panel_plotter.arrange_subplots(1.0)
        assert len(result) == 6

    def test_all_positive_dimensions(self):
        tw, th, mc, sc, fc, tc = panel_plotter.arrange_subplots(1.0)
        assert tw > 0
        assert th > 0
        for coords in [mc, sc, fc, tc]:
            for val in coords:
                assert val >= 0

    def test_clean_mode_narrower(self):
        tw_normal, _, _, _, _, _ = panel_plotter.arrange_subplots(1.0, clean=False)
        tw_clean, _, _, _, _, _ = panel_plotter.arrange_subplots(1.0, clean=True)
        assert tw_clean < tw_normal

    def test_different_aspect_ratios(self):
        """Different aspect ratios should produce different widths."""
        tw1, _, _, _, _, _ = panel_plotter.arrange_subplots(0.5)
        tw2, _, _, _, _, _ = panel_plotter.arrange_subplots(2.0)
        assert tw1 != tw2


# =====================================================================
# prep_plot_data
# =====================================================================

class TestPrepPlotData:

    def _make_sim(self):
        return {
            "precip_data": np.ones((10, 10)),
            "lon": np.zeros((10, 10)),
            "lat": np.zeros((10, 10)),
            "precip_data_resampled": np.ones((8, 8)) * 2,
            "lon_resampled": np.zeros((8, 8)),
            "lat_resampled": np.zeros((8, 8)),
        }

    def test_normal_mode(self):
        sim = self._make_sim()
        data, lon, lat = panel_plotter.prep_plot_data(sim, sim, "normal")
        assert data.shape == (10, 10)
        assert data[0, 0] == 1.0

    def test_resampled_mode(self):
        sim = self._make_sim()
        data, lon, lat = panel_plotter.prep_plot_data(sim, sim, "resampled")
        assert data.shape == (8, 8)
        assert data[0, 0] == 2.0


# =====================================================================
# fss_plot_rows — separator row of the FSS rank plot
# =====================================================================

class TestFssPlotRows:

    @staticmethod
    def _sim(n_thresholds, n_percentiles):
        import pandas as pd
        n_rows = n_thresholds + n_percentiles
        return {"fss_ranks": np.full((n_rows, 4), 3), "fssf": pd.DataFrame(np.full((n_rows, 4), 0.8)),
                "fss_rel": np.zeros((n_rows, 4)), "fss_overestimated": pd.DataFrame(np.zeros((n_rows, 4))),
                "fss_thresholds": [0.5] * n_thresholds, "fss_thresholds_percs": [0.5] * n_percentiles}

    def test_separator_between_thresholds_and_percentiles(self):
        ranks, fssf, fss_rel, ovest, separator = panel_plotter.fss_plot_rows(self._sim(3, 2))
        assert separator == 3
        assert ranks.shape == fssf.shape == fss_rel.shape == ovest.shape == (6, 4)
        assert (ranks[3] == 0).all() and np.isnan(fssf[3]).all()
        assert (ranks[[0, 1, 2, 4, 5]] == 3).all()

    def test_no_separator_without_percentiles(self):
        ranks, _, _, _, separator = panel_plotter.fss_plot_rows(self._sim(3, 0))
        assert separator is None
        assert ranks.shape == (3, 4)
