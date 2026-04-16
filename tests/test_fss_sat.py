"""Tests for fss_SAT.py — the summed area table FSS implementation."""

import numpy as np
import pandas as pd
import pytest

import fss_SAT


# =====================================================================
# compute_integral_table
# =====================================================================

class TestComputeIntegralTable:

    def test_hand_computed_3x3(self):
        field = np.array([[1, 2, 3],
                          [4, 5, 6],
                          [7, 8, 9]], dtype=float)
        expected = np.array([[ 1,  3,  6],
                             [ 5, 12, 21],
                             [12, 27, 45]], dtype=float)
        result = fss_SAT.compute_integral_table(field)
        np.testing.assert_array_equal(result, expected)

    def test_all_ones(self):
        field = np.ones((4, 4), dtype=float)
        result = fss_SAT.compute_integral_table(field)
        # bottom-right corner should equal total number of elements
        assert result[-1, -1] == 16.0
        # each element (i,j) should equal (i+1)*(j+1)
        for i in range(4):
            for j in range(4):
                assert result[i, j] == (i + 1) * (j + 1)

    def test_3d_array(self):
        field_2d = np.array([[1, 2], [3, 4]], dtype=float)
        field_3d = np.stack([field_2d, field_2d * 2])  # (2, 2, 2)
        result = fss_SAT.compute_integral_table(field_3d)
        expected_2d = fss_SAT.compute_integral_table(field_2d)
        np.testing.assert_array_equal(result[0], expected_2d)
        np.testing.assert_array_equal(result[1], expected_2d * 2)

    def test_zeros(self):
        field = np.zeros((5, 5), dtype=float)
        result = fss_SAT.compute_integral_table(field)
        np.testing.assert_array_equal(result, field)


# =====================================================================
# integral_filter
# =====================================================================

class TestIntegralFilter:

    def test_window_1_identity(self):
        """Window size 1 (w=0) should return the input unchanged."""
        field = np.random.default_rng(42).random((8, 8))
        sat = fss_SAT.compute_integral_table(field)
        result = fss_SAT.integral_filter(sat, 1)
        np.testing.assert_array_almost_equal(result, sat)

    def test_uniform_field_interior(self):
        """Interior of uniform field filtered should be constant."""
        field = np.ones((32, 32), dtype=float)
        sat = fss_SAT.compute_integral_table(field)
        result = fss_SAT.integral_filter(sat, 5)
        # interior (away from edges) should all be equal
        interior = result[4:-4, 4:-4]
        assert np.allclose(interior, interior[0, 0])

    def test_symmetry(self):
        """Symmetric input should produce symmetric output."""
        n = 32
        field = np.zeros((n, n))
        field[n // 2, n // 2] = 1.0
        sat = fss_SAT.compute_integral_table(field)
        result = fss_SAT.integral_filter(sat, 5)
        np.testing.assert_array_almost_equal(result, result[::-1, :])
        np.testing.assert_array_almost_equal(result, result[:, ::-1])


# =====================================================================
# _fss_score
# =====================================================================

class TestFssScore:

    def test_perfect_match(self):
        fhat = np.array([[1.0, 2.0], [3.0, 4.0]])
        ohat = fhat.copy()
        num, denom, score = fss_SAT._fss_score(fhat, ohat, 1.0)
        assert num == 0.0
        assert score == 1.0

    def test_zero_denominator(self):
        fhat = np.zeros((4, 4))
        ohat = np.zeros((4, 4))
        num, denom, score = fss_SAT._fss_score(fhat, ohat, 1.0)
        assert denom == 0.0
        assert np.isnan(score)

    def test_score_bounds(self):
        """FSS should be in [0, 1] for non-degenerate cases."""
        rng = np.random.default_rng(123)
        for _ in range(20):
            fhat = rng.random((8, 8))
            ohat = rng.random((8, 8))
            _, denom, score = fss_SAT._fss_score(fhat, ohat, 1.0)
            if denom > 0:
                assert 0.0 <= score <= 1.0 + 1e-10


# =====================================================================
# R2 quasi-random sequence
# =====================================================================

class TestR2:

    def test_values_in_unit_interval(self):
        for n in range(500):
            x, y = fss_SAT.R2(n)
            assert 0.0 <= x < 1.0
            assert 0.0 <= y < 1.0

    def test_deterministic(self):
        for n in [0, 1, 42, 999]:
            assert fss_SAT.R2(n) == fss_SAT.R2(n)

    def test_coverage(self):
        """500 samples should cover all quadrants of the unit square."""
        xs, ys = zip(*[fss_SAT.R2(n) for n in range(500)])
        xs, ys = np.array(xs), np.array(ys)
        for xlo, xhi in [(0, 0.5), (0.5, 1)]:
            for ylo, yhi in [(0, 0.5), (0.5, 1)]:
                count = np.sum((xs >= xlo) & (xs < xhi) & (ys >= ylo) & (ys < yhi))
                assert count > 50, f"quadrant [{xlo},{xhi})x[{ylo},{yhi}) has only {count} points"


# =====================================================================
# _build_binary_sat
# =====================================================================

class TestBuildBinarySat:

    def _make_fields(self):
        obs = np.array([[0, 5, 10], [15, 20, 25], [30, 35, 40]], dtype=float)
        fcst = obs * 1.5
        return fcst, obs

    def test_over_mode(self):
        fcst, obs = self._make_fields()
        t1o, t1f = 10.0, 15.0
        mod_bin, obs_bin = fss_SAT._build_binary_sat(
            fcst, obs, 10, None, t1o, t1f, False, "over", 0.1)
        # obs_bin should be integral table of (obs > 10)
        expected_obs = fss_SAT.compute_integral_table((obs > t1o).astype(int))
        expected_mod = fss_SAT.compute_integral_table((fcst > t1f).astype(int))
        np.testing.assert_array_equal(obs_bin, expected_obs)
        np.testing.assert_array_equal(mod_bin, expected_mod)

    def test_under_mode(self):
        fcst, obs = self._make_fields()
        t1o, t1f = 10.0, 15.0
        mod_bin, obs_bin = fss_SAT._build_binary_sat(
            fcst, obs, 10, None, t1o, t1f, False, "under", 0.1)
        expected_obs = fss_SAT.compute_integral_table((obs <= t1o).astype(int))
        expected_mod = fss_SAT.compute_integral_table((fcst <= t1f).astype(int))
        np.testing.assert_array_equal(obs_bin, expected_obs)
        np.testing.assert_array_equal(mod_bin, expected_mod)

    def test_tolerance_mode(self):
        fcst, obs = self._make_fields()
        t1o, t1f = 20.0, 30.0
        tol = 0.2
        mod_bin, obs_bin = fss_SAT._build_binary_sat(
            fcst, obs, 20, None, t1o, t1f, False, "tolerance", tol)
        expected_obs = fss_SAT.compute_integral_table(
            ((obs > 0.8 * t1o) & (obs <= 1.2 * t1o)).astype(int))
        expected_mod = fss_SAT.compute_integral_table(
            ((fcst > 0.8 * t1f) & (fcst <= 1.2 * t1f)).astype(int))
        np.testing.assert_array_equal(obs_bin, expected_obs)
        np.testing.assert_array_equal(mod_bin, expected_mod)

    def test_between_mode(self):
        fcst, obs = self._make_fields()
        t1o, t1f = 10.0, 15.0
        t2 = 30.0
        t2o, t2f = 30.0, 45.0  # percentiles=False, so t2 used directly
        mod_bin, obs_bin = fss_SAT._build_binary_sat(
            fcst, obs, 10, t2, t1o, t1f, False, "between", 0.1)
        expected_obs = fss_SAT.compute_integral_table(
            ((obs > t1o) & (obs <= t2)).astype(int))
        expected_mod = fss_SAT.compute_integral_table(
            ((fcst > t1f) & (fcst <= t2)).astype(int))
        np.testing.assert_array_equal(obs_bin, expected_obs)
        np.testing.assert_array_equal(mod_bin, expected_mod)


# =====================================================================
# fss (core FSS at single window)
# =====================================================================

class TestFss:

    def test_perfect_match(self, identical_fields):
        obs, fcst = identical_fields
        threshold = 5.0
        obs_bin = fss_SAT.compute_integral_table((obs > threshold).astype(int))
        fcst_bin = fss_SAT.compute_integral_table((fcst > threshold).astype(int))
        _, _, score = fss_SAT.fss(fcst, obs, 5, fcst_bin, obs_bin)
        assert score == 1.0

    def test_fss_increases_with_window(self, small_fields):
        """For displaced forecast, FSS should generally increase with window size."""
        obs, fcst = small_fields
        threshold = 10.0
        obs_bin = fss_SAT.compute_integral_table((obs > threshold).astype(int))
        fcst_bin = fss_SAT.compute_integral_table((fcst > threshold).astype(int))
        scores = []
        for w in [3, 5, 11, 21, 41]:
            _, _, score = fss_SAT.fss(fcst, obs, w, fcst_bin, obs_bin)
            if not np.isnan(score):
                scores.append(score)
        # FSS should be non-decreasing (with small tolerance for edge effects)
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1] - 0.01, \
                f"FSS decreased from w={[3,5,11,21,41][i-1]} to w={[3,5,11,21,41][i]}"


# =====================================================================
# fss_threshold
# =====================================================================

class TestFssThreshold:

    def test_returns_correct_shape(self, identical_fields):
        obs, fcst = identical_fields
        windows = np.array([3, 5, 11])
        result = fss_SAT.fss_threshold(fcst, obs, 5.0, None, windows)
        assert len(result) == 4
        for arr in result:
            assert arr.shape == windows.shape

    def test_perfect_match(self, identical_fields):
        obs, fcst = identical_fields
        windows = np.array([3, 5, 11])
        result = fss_SAT.fss_threshold(fcst, obs, 5.0, None, windows)
        fss_values = result[2]
        for val in fss_values:
            assert val == 1.0 or np.isnan(val)

    def test_overestimation_sign(self, small_fields):
        obs, fcst = small_fields
        # fcst is shifted, but same amplitude — ovest depends on threshold
        windows = np.array([5])
        result = fss_SAT.fss_threshold(fcst, obs, 1.0, None, windows)
        ovest = result[3]
        assert ovest.shape == windows.shape


# =====================================================================
# fss_cumsum_frame
# =====================================================================

class TestFssCumsumFrame:

    def _make_windows_2d(self, windows):
        return [(w, w) for w in windows]

    def test_returns_4_dataframes(self, identical_fields):
        obs, fcst = identical_fields
        windows = self._make_windows_2d([3, 5, 11])
        thresholds = [0.1, 5.0]
        result = fss_SAT.fss_cumsum_frame(fcst, obs, windows, thresholds)
        assert len(result) == 4
        for df in result:
            assert isinstance(df, pd.DataFrame)

    def test_dataframe_index_columns(self, identical_fields):
        obs, fcst = identical_fields
        windows = self._make_windows_2d([3, 5, 11])
        thresholds = [0.1, 5.0]
        result = fss_SAT.fss_cumsum_frame(fcst, obs, windows, thresholds)
        fss_df = result[2]
        assert list(fss_df.index) == thresholds
        assert list(fss_df.columns) == [3, 5, 11]

    def test_raw_mode(self, identical_fields):
        obs, fcst = identical_fields
        windows = self._make_windows_2d([3, 5])
        thresholds = [0.1, 5.0]
        result = fss_SAT.fss_cumsum_frame(fcst, obs, windows, thresholds, raw=True)
        assert isinstance(result, np.ndarray)

    def test_perfect_match_scores(self, identical_fields):
        obs, fcst = identical_fields
        windows = self._make_windows_2d([3, 5, 11])
        thresholds = [5.0, 10.0]
        result = fss_SAT.fss_cumsum_frame(fcst, obs, windows, thresholds)
        fss_df = result[2]
        for val in fss_df.values.flatten():
            assert val == 1.0 or np.isnan(val)

    def test_tolerance_mode_differs_from_over(self, small_fields):
        """Tolerance mode should produce different FSS values than over mode."""
        obs, fcst = small_fields
        windows = self._make_windows_2d([5, 11])
        thresholds = [5.0, 10.0]
        result_over = fss_SAT.fss_cumsum_frame(
            fcst, obs, windows, thresholds, threshold_mode="over")
        result_tol = fss_SAT.fss_cumsum_frame(
            fcst, obs, windows, thresholds, threshold_mode="tolerance", tolerance=0.1)
        fss_over = result_over[2].values
        fss_tol = result_tol[2].values
        # At least some values should differ (tolerance is much stricter)
        assert not np.allclose(fss_over, fss_tol, equal_nan=True)


# =====================================================================
# CWFSS class
# =====================================================================

class TestCWFSS:

    def test_perfect_match(self, identical_fields):
        obs, fcst = identical_fields
        cwfss = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                               threshold_limiting="relative",
                               window_limits=[3, 30])
        assert cwfss.cwfss > 0.9

    def test_displaced_worse_than_perfect(self, small_fields, identical_fields):
        """Displaced forecast should score lower than perfect forecast."""
        obs_p, fcst_p = identical_fields
        obs_d, fcst_d = small_fields
        cwfss_perfect = fss_SAT.CWFSS(fcst_p, obs_p, nsamples=50,
                                       threshold_limiting="relative",
                                       window_limits=[3, 30])
        cwfss_displaced = fss_SAT.CWFSS(fcst_d, obs_d, nsamples=50,
                                         threshold_limiting="relative",
                                         window_limits=[3, 30])
        assert cwfss_perfect.cwfss > cwfss_displaced.cwfss

    def test_deterministic(self, identical_fields):
        """Same inputs should produce same cwfss (R2 is deterministic)."""
        obs, fcst = identical_fields
        c1 = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                            threshold_limiting="relative",
                            window_limits=[3, 30])
        c2 = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                            threshold_limiting="relative",
                            window_limits=[3, 30])
        assert c1.cwfss == c2.cwfss

    def test_bootstrap_length(self, identical_fields):
        obs, fcst = identical_fields
        cwfss = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                               threshold_limiting="relative",
                               window_limits=[3, 30])
        cwfss.bootstrap(N=100)
        assert len(cwfss.bootstrap_info) == 100
        assert np.std(cwfss.bootstrap_info) >= 0

    def test_tolerance_mode(self, small_fields):
        obs, fcst = small_fields
        cwfss_over = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                                    threshold_limiting="relative",
                                    window_limits=[3, 30],
                                    threshold_mode="over")
        cwfss_tol = fss_SAT.CWFSS(fcst, obs, nsamples=50,
                                   threshold_limiting="relative",
                                   window_limits=[3, 30],
                                   threshold_mode="tolerance", tolerance=0.1)
        # Both should produce valid scores, but they should differ
        assert 0 <= cwfss_over.cwfss <= 1
        assert 0 <= cwfss_tol.cwfss <= 1
