"""Tests for parameter_settings.py — configuration lookups."""

import argparse
import numpy as np
import pytest

import parameter_settings


def _args(**overrides):
    defaults = dict(parameter="precip", d_windows=[], duration=1,
                    mode="normal", cmap="mycolors", print_colors=True)
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# =====================================================================
# get_fss_thresholds
# =====================================================================

class TestGetFssThresholds:

    def test_precip_returns_10_values(self):
        result = parameter_settings.get_fss_thresholds(_args())
        assert len(result) == 10
        assert result[-1] == 99999.0

    def test_precip2(self):
        result = parameter_settings.get_fss_thresholds(_args(parameter="precip2"))
        assert len(result) == 10
        assert result[0] == 1.0

    def test_all_parameters_non_empty(self):
        for param in ["precip", "precip2", "precip3", "sunshine",
                      "hail", "gusts", "lightning", "cma"]:
            result = parameter_settings.get_fss_thresholds(_args(parameter=param))
            assert len(result) > 0, f"empty thresholds for {param}"

    def test_cma_depends_on_duration(self):
        r1 = parameter_settings.get_fss_thresholds(_args(parameter="cma", duration=1))
        r3 = parameter_settings.get_fss_thresholds(_args(parameter="cma", duration=3))
        assert len(r3) > len(r1)


# =====================================================================
# get_windows
# =====================================================================

class TestGetWindows:

    def test_default_precip(self):
        result = parameter_settings.get_windows(_args())
        assert len(result) == 12
        assert result[0] == 10

    def test_default_cma(self):
        result = parameter_settings.get_windows(_args(parameter="cma"))
        assert len(result) == 5

    def test_custom_windows_passthrough(self):
        custom = [5, 15, 25]
        result = parameter_settings.get_windows(_args(d_windows=custom))
        assert result == custom


# =====================================================================
# get_cmap_and_levels
# =====================================================================

class TestGetCmapAndLevels:

    def test_precip_returns_tuple(self):
        result = parameter_settings.get_cmap_and_levels(_args())
        assert len(result) == 3
        levels, cmap, norm = result
        assert len(levels) > 0

    def test_all_parameters(self):
        for param in ["precip", "precip2", "precip3", "sunshine",
                      "hail", "gusts", "lightning", "cma"]:
            result = parameter_settings.get_cmap_and_levels(_args(parameter=param))
            assert len(result) == 3


# =====================================================================
# title_part / colorbar_label
# =====================================================================

class TestLabels:

    def test_title_part_precip(self):
        result = parameter_settings.title_part(_args())
        assert "Precip" in result

    def test_colorbar_label_precip(self):
        result = parameter_settings.colorbar_label(_args())
        assert "precipitation" in result

    def test_all_parameters_have_titles(self):
        for param in ["precip", "precip2", "precip3", "sunshine",
                      "hail", "gusts", "lightning", "cma"]:
            result = parameter_settings.title_part(_args(parameter=param))
            assert isinstance(result, str) and len(result) > 0
