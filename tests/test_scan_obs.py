"""Tests for scan_obs.py — selection of the subdomains to score and draw."""

from types import SimpleNamespace

import numpy as np
import pytest

import scan_obs


THRESHOLDS = {"draw_avg": 2., "draw_max": 25., "score_avg": 1., "score_max": 5.}


def _scan(field, parameter, draw=True, forcescore=False, forcedraw=False):
    """ Scan one subdomain whose resampled observation is `field` """
    region = SimpleNamespace(
        subdomains={"Dom": {"thresholds": THRESHOLDS}},
        resample_to_subdomain=lambda data, lon, lat, name, fix_nans=False: (data, lon, lat))
    args = SimpleNamespace(parameter=parameter, region=region, subdomains=["Dom"], fix_nans=False,
                           draw=draw, forcescore=forcescore, forcedraw=forcedraw)
    obs = {"lon": np.zeros_like(field), "lat": np.zeros_like(field), "precip_data": field}
    return scan_obs.get_interesting_subdomains(obs, args).iloc[0]


DRY = np.zeros((10, 10))
WET = np.full((10, 10), 30.)


class TestThresholds:

    @pytest.mark.parametrize("parameter", ["precip", "precip2", "precip3"])
    def test_precipitation_uses_thresholds(self, parameter):
        assert not _scan(DRY, parameter)["score"]
        assert not _scan(DRY, parameter)["draw"]
        assert _scan(WET, parameter)["score"]
        assert _scan(WET, parameter)["draw"]

    @pytest.mark.parametrize("parameter", ["cma", "gusts", "hail", "lightning", "sunshine"])
    def test_other_parameters_always_selected(self, parameter):
        assert _scan(DRY, parameter)["score"]
        assert _scan(DRY, parameter)["draw"]

    def test_draw_needs_draw_option(self):
        assert not _scan(WET, "gusts", draw=False)["draw"]

    def test_force_options(self):
        result = _scan(DRY, "precip", draw=False, forcescore=True, forcedraw=True)
        assert result["score"] and result["draw"]

    def test_missing_values_ignored(self):
        field = WET.copy()
        field[0, 0] = np.nan
        result = _scan(field, "precip")
        assert result["mean"] == 30.
        assert result["score"]
