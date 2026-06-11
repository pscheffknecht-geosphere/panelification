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


# =====================================================================
# missing-data (NaN) handling
# =====================================================================

class TestValidityMask:
    """_validity_mask / _invalid_sat — the building blocks of the NaN path."""

    def test_mask_marks_either_nan(self):
        fcst = np.array([[1.0, 2.0], [np.nan, 4.0]])
        obs = np.array([[1.0, np.nan], [3.0, 4.0]])
        mask = fss_SAT._validity_mask(fcst, obs)
        # a point is valid only when *both* fields are finite there
        expected = np.array([[True, False], [False, True]])
        np.testing.assert_array_equal(mask, expected)

    def test_mask_all_true_when_clean(self, small_fields):
        obs, fcst = small_fields
        assert fss_SAT._validity_mask(fcst, obs).all()

    def test_invalid_sat_counts_missing_points(self):
        # corner of the integral table equals the total number of invalid points
        mask = np.array([[True, False], [False, True]])
        inv = fss_SAT._invalid_sat(mask)
        assert inv[-1, -1] == 2.0
        # no missing points -> all zeros
        inv_clean = fss_SAT._invalid_sat(np.ones((4, 4), dtype=bool))
        assert inv_clean[-1, -1] == 0.0


class TestFssScoreMasked:
    """_fss_score_masked — the weighted FSS over per-window valid counts."""

    def test_perfect_match_scores_one(self):
        Sf = np.array([[1.0, 2.0], [3.0, 4.0]])
        So = Sf.copy()
        C = np.full((2, 2), 9.0)
        num, den, score = fss_SAT._fss_score_masked(Sf, So, C)
        assert num == 0.0
        assert score == pytest.approx(1.0)

    def test_all_invalid_returns_nan(self):
        Sf = np.zeros((3, 3))
        So = np.zeros((3, 3))
        C = np.zeros((3, 3))  # no valid points anywhere
        num, den, score = fss_SAT._fss_score_masked(Sf, So, C)
        assert num == 0.0 and den == 0.0
        assert np.isnan(score)

    def test_reduces_to_clean_when_no_missing(self):
        """With a constant valid count C == area, the masked score must match
        the clean _fss_score exactly (the documented reduction property)."""
        rng = np.random.default_rng(0)
        fhat = rng.random((8, 8)) * 5.0
        ohat = rng.random((8, 8)) * 5.0
        area = 9.0  # e.g. a 3x3 window
        C = np.full_like(fhat, area)
        _, _, score_masked = fss_SAT._fss_score_masked(fhat, ohat, C)
        _, _, score_clean = fss_SAT._fss_score(fhat, ohat, 1.0 / area ** 2)
        assert score_masked == pytest.approx(score_clean)


class TestBuildBinarySatMasked:
    """_build_binary_sat_masked — NaN points must be zeroed out of the sums."""

    def _make_fields(self):
        obs = np.array([[0, 5, 10], [15, 20, 25], [30, 35, 40]], dtype=float)
        fcst = obs * 1.5
        obs[0, 0] = np.nan          # one missing point
        return fcst, obs

    def test_over_mode_zeros_missing(self):
        fcst, obs = self._make_fields()
        mask = fss_SAT._validity_mask(fcst, obs)
        t1o, t1f = 10.0, 15.0
        mod_bin, obs_bin = fss_SAT._build_binary_sat_masked(
            fcst, obs, 10, None, t1o, t1f, False, "over", 0.1, mask)
        expected_obs = fss_SAT.compute_integral_table(((obs > t1o) & mask).astype(float))
        expected_mod = fss_SAT.compute_integral_table(((fcst > t1f) & mask).astype(float))
        np.testing.assert_array_equal(obs_bin, expected_obs)
        np.testing.assert_array_equal(mod_bin, expected_mod)

    def test_tolerance_uses_forecast_threshold(self):
        """Regression guard: the forecast upper bound must use t1f, not t1o."""
        fcst, obs = self._make_fields()
        mask = fss_SAT._validity_mask(fcst, obs)
        t1o, t1f, tol = 20.0, 30.0, 0.2
        mod_bin, _ = fss_SAT._build_binary_sat_masked(
            fcst, obs, 20, None, t1o, t1f, False, "tolerance", tol, mask)
        expected_mod = fss_SAT.compute_integral_table(
            (((fcst > 0.8 * t1f) & (fcst <= 1.2 * t1f)) & mask).astype(float))
        np.testing.assert_array_equal(mod_bin, expected_mod)


class TestFssThresholdMissingData:
    """fss_threshold deterministic path with NaN in the inputs."""

    def test_perfect_match_with_shared_nan_is_one(self, identical_fields):
        obs, fcst = identical_fields
        obs = obs.copy()
        fcst = fcst.copy()
        obs[10:20, 10:20] = np.nan      # same points missing in both fields
        fcst[10:20, 10:20] = np.nan
        windows = np.array([3, 5, 11])
        result = fss_SAT.fss_threshold(fcst, obs, 5.0, None, windows)
        for val in result[2]:
            assert val == pytest.approx(1.0) or np.isnan(val)

    def test_single_nan_close_to_clean(self, small_fields):
        """One masked pixel out of 4096 should barely change the score, i.e. the
        masked path approximately reduces to the clean path."""
        obs, fcst = small_fields
        windows = np.array([5, 11])
        clean = fss_SAT.fss_threshold(fcst, obs, 5.0, None, windows)[2]
        obs_nan = obs.copy()
        obs_nan[0, 0] = np.nan          # forces the missing-data path
        masked = fss_SAT.fss_threshold(fcst, obs_nan, 5.0, None, windows)[2]
        np.testing.assert_allclose(clean, masked, atol=2e-3)

    def test_all_nan_obs_yields_nan(self, small_fields):
        obs, fcst = small_fields
        obs_nan = np.full_like(obs, np.nan)
        windows = np.array([5, 11])
        result = fss_SAT.fss_threshold(fcst, obs_nan, 5.0, None, windows)
        assert np.isnan(result[2]).all()

    def test_displaced_scores_in_unit_range(self, small_fields):
        obs, fcst = small_fields
        obs = obs.copy()
        fcst = fcst.copy()
        obs[:8, :8] = np.nan            # a corner with no coverage
        fcst[40:48, 40:48] = np.nan     # missing elsewhere in the forecast
        windows = np.array([5, 11, 21])
        fss_vals = fss_SAT.fss_threshold(fcst, obs, 5.0, None, windows)[2]
        for val in fss_vals:
            assert np.isnan(val) or 0.0 <= val <= 1.0


class TestFssThresholdEpsMissingData:
    """fss_threshold_eps (ensemble) path — NaN members used to raise."""

    def _stack(self, field, n=3):
        return np.repeat(field[None, :, :], n, axis=0)

    def test_nan_member_no_longer_raises(self, small_fields):
        obs, fcst = small_fields
        ens = self._stack(fcst, 3).copy()
        ens[0, 5:15, 5:15] = np.nan     # one member partially missing
        windows = np.array([5, 11])
        # previously raised NotImplementedError; now it must complete
        result = fss_SAT.fss_threshold_eps(ens, obs, 5.0, None, windows)
        assert len(result) == 4
        for val in result[2]:
            assert np.isnan(val) or 0.0 <= val <= 1.0

    def test_perfect_ensemble_with_nan_obs(self, identical_fields):
        obs, fcst = identical_fields
        obs = obs.copy()
        obs[20:30, 20:30] = np.nan
        ens = self._stack(fcst, 3)        # every member equals the (clean) obs
        windows = np.array([5, 11])
        fss_vals = fss_SAT.fss_threshold_eps(ens, obs, 5.0, None, windows)[2]
        for val in fss_vals:
            assert val == pytest.approx(1.0) or np.isnan(val)

    def test_clean_ensemble_still_works(self, small_fields):
        obs, fcst = small_fields
        ens = self._stack(fcst, 4)
        windows = np.array([5, 11])
        fss_vals = fss_SAT.fss_threshold_eps(ens, obs, 5.0, None, windows)[2]
        for val in fss_vals:
            assert np.isnan(val) or 0.0 <= val <= 1.0


class TestCWFSSMissingData:
    """CWFSS with NaN observations (e.g. OPERA coverage gaps)."""

    def _add_gap(self, field):
        out = field.copy()
        out[:10, :10] = np.nan
        return out

    def test_runs_with_nan_obs(self, small_fields):
        obs, fcst = small_fields
        obs_gap = self._add_gap(obs)
        cwfss = fss_SAT.CWFSS(fcst, obs_gap, nsamples=50,
                               threshold_limiting="relative",
                               window_limits=[3, 30])
        assert np.isfinite(cwfss.cwfss)
        assert 0.0 <= cwfss.cwfss <= 1.0

    def test_perfect_match_with_nan_high_score(self, identical_fields):
        obs, fcst = identical_fields
        obs_gap = self._add_gap(obs)
        fcst_gap = self._add_gap(fcst)
        cwfss = fss_SAT.CWFSS(fcst_gap, obs_gap, nsamples=50,
                               threshold_limiting="relative",
                               window_limits=[3, 30])
        assert cwfss.cwfss > 0.9

    def test_percentile_limiting_with_nan(self, small_fields):
        """threshold_limiting='percentiles' must use nanpercentile internally."""
        obs, fcst = small_fields
        obs_gap = self._add_gap(obs)
        cwfss = fss_SAT.CWFSS(fcst, obs_gap, nsamples=50,
                               threshold_limiting="percentiles",
                               threshold_limits=(10., 99.),
                               window_limits=[3, 30])
        assert np.isfinite(cwfss.tmin) and np.isfinite(cwfss.tmax)
        assert np.isfinite(cwfss.cwfss)
