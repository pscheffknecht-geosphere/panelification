"""Tests for fss_FFT.py — legacy FFT-based FSS implementation."""

import numpy as np
import pandas as pd
import pytest

import fss_FFT
import fss_SAT


# =====================================================================
# fourier_filter
# =====================================================================

class TestFourierFilter:

    def test_uniform_field_mode_same(self):
        """Uniform field convolved should preserve shape."""
        field = np.ones((16, 16))
        window = (5, 5)
        result = fss_FFT.fourier_filter(field, window, mode="same")
        assert result.shape == field.shape

    def test_output_shape_same_mode(self):
        field = np.random.default_rng(42).random((32, 32))
        window = (7, 7)
        result = fss_FFT.fourier_filter(field, window, mode="same")
        assert result.shape == field.shape


# =====================================================================
# fourier_fss
# =====================================================================

class TestFourierFss:

    def test_perfect_match(self, identical_fields):
        obs, fcst = identical_fields
        window = (5, 5)
        num, denom, score, ovest = fss_FFT.fourier_fss(fcst, obs, 5.0, window, False, "same")
        if not np.isnan(score):
            assert score == pytest.approx(1.0, abs=1e-10)

    def test_score_bounds(self, small_fields):
        obs, fcst = small_fields
        window = (5, 5)
        num, denom, score, ovest = fss_FFT.fourier_fss(fcst, obs, 5.0, window, False, "same")
        if not np.isnan(score):
            assert 0.0 <= score <= 1.0 + 1e-10

    def test_percentile_mode(self, identical_fields):
        obs, fcst = identical_fields
        window = (5, 5)
        num, denom, score, ovest = fss_FFT.fourier_fss(fcst, obs, 90, window, True, "same")
        if not np.isnan(score):
            assert score == pytest.approx(1.0, abs=1e-10)


# =====================================================================
# fss_frame
# =====================================================================

class TestFssFrame:

    def test_returns_4_dataframes(self, identical_fields):
        obs, fcst = identical_fields
        windows = [(3, 3), (5, 5), (11, 11)]
        levels = [0.1, 5.0]
        result = fss_FFT.fss_frame(fcst, obs, windows, levels)
        assert len(result) == 4
        for df in result:
            assert isinstance(df, pd.DataFrame)

    def test_shape(self, identical_fields):
        obs, fcst = identical_fields
        windows = [(3, 3), (5, 5), (11, 11)]
        levels = [0.1, 5.0, 10.0]
        result = fss_FFT.fss_frame(fcst, obs, windows, levels)
        fss_df = result[2]
        assert fss_df.shape == (3, 3)  # 3 levels x 3 windows

    def test_perfect_match_scores(self, identical_fields):
        obs, fcst = identical_fields
        windows = [(5, 5), (11, 11)]
        levels = [5.0, 10.0]
        result = fss_FFT.fss_frame(fcst, obs, windows, levels)
        fss_df = result[2]
        for val in fss_df.values.flatten():
            if not np.isnan(val):
                assert val == pytest.approx(1.0, abs=1e-10)


# =====================================================================
# Cross-validation: SAT vs FFT
# =====================================================================

class TestSatVsFft:

    def test_agreement_on_identical_fields(self, identical_fields):
        """SAT and FFT should agree closely for identical fields."""
        obs, fcst = identical_fields
        windows_2d = [(5, 5), (11, 11)]
        thresholds = [5.0, 10.0]
        fft_result = fss_FFT.fss_frame(fcst, obs, windows_2d, thresholds)
        sat_result = fss_SAT.fss_cumsum_frame(fcst, obs, windows_2d, thresholds)
        fft_fss = fft_result[2].values
        sat_fss = sat_result[2].values
        # Both should be 1.0 or NaN for perfect match
        for i in range(fft_fss.shape[0]):
            for j in range(fft_fss.shape[1]):
                if np.isnan(fft_fss[i, j]) or np.isnan(sat_fss[i, j]):
                    continue
                assert fft_fss[i, j] == pytest.approx(sat_fss[i, j], abs=1e-6)

    def test_agreement_on_displaced_fields(self, small_fields):
        """SAT and FFT should agree within tolerance for displaced fields."""
        obs, fcst = small_fields
        windows_2d = [(5, 5), (11, 11), (21, 21)]
        thresholds = [5.0, 10.0]
        fft_result = fss_FFT.fss_frame(fcst, obs, windows_2d, thresholds)
        sat_result = fss_SAT.fss_cumsum_frame(fcst, obs, windows_2d, thresholds)
        fft_fss = fft_result[2].values
        sat_fss = sat_result[2].values
        for i in range(fft_fss.shape[0]):
            for j in range(fft_fss.shape[1]):
                if np.isnan(fft_fss[i, j]) or np.isnan(sat_fss[i, j]):
                    continue
                assert fft_fss[i, j] == pytest.approx(sat_fss[i, j], abs=0.05), \
                    f"SAT ({sat_fss[i,j]:.4f}) vs FFT ({fft_fss[i,j]:.4f}) differ at [{i},{j}]"
