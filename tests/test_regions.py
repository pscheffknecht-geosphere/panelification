"""Tests for regions.py — geographic regions, grids, and resampling."""

import numpy as np
import pytest

import regions


# =====================================================================
# arc_length
# =====================================================================

class TestArcLength:

    def test_zero_distance(self):
        d = regions.arc_length(13.0, 47.5, 13.0, 47.5)
        assert d == pytest.approx(0.0, abs=1e-10)

    def test_known_distance_vienna_salzburg(self):
        # Vienna (16.37, 48.21) → Salzburg (13.05, 47.80): ~250 km
        d = regions.arc_length(16.37, 48.21, 13.05, 47.80)
        assert 240 < d < 260

    def test_symmetry(self):
        d1 = regions.arc_length(10.0, 45.0, 15.0, 50.0)
        d2 = regions.arc_length(15.0, 50.0, 10.0, 45.0)
        assert d1 == pytest.approx(d2, abs=1e-6)

    def test_equator_one_degree(self):
        # 1 degree at equator ≈ 111.2 km
        d = regions.arc_length(0.0, 0.0, 1.0, 0.0)
        assert 110 < d < 113


# =====================================================================
# Region class
# =====================================================================

TEST_REGION_DEF = {
    "central_longitude": 13.0,
    "central_latitude": 47.5,
    "extent": [8.0, 19.0, 45.0, 50.0],
    "verification_subdomains": {
        "Default": {
            "central_longitude": 13.0,
            "central_latitude": 47.5,
            "x_size": 200.,
            "y_size": 150.,
            "thresholds": {
                "draw_avg": 0., "draw_max": 0.,
                "score_avg": 0., "score_max": 0.,
            },
        }
    },
}


class TestRegion:

    @pytest.fixture
    def test_region(self):
        regions.regions["_Test"] = TEST_REGION_DEF
        return regions.Region("_Test", ["Default"])

    def test_creation(self, test_region):
        assert test_region.name == "_Test"
        assert "Default" in test_region.subdomains

    def test_subdomain_has_grid(self, test_region):
        sd = test_region.subdomains["Default"]
        assert "lon" in sd
        assert "lat" in sd
        assert sd["lon"].shape == sd["lat"].shape

    def test_resample_output_shape(self, test_region):
        # create a simple data field on a regular lon/lat grid
        lon_1d = np.linspace(6.0, 21.0, 200)
        lat_1d = np.linspace(43.0, 52.0, 200)
        lon, lat = np.meshgrid(lon_1d, lat_1d)
        data = np.ones_like(lon) * 10.0
        result, rlon, rlat = test_region.resample_to_subdomain(
            data, lon, lat, "Default", fix_nans=False)
        sd = test_region.subdomains["Default"]
        assert result.shape == sd["lon"].shape

    def test_resample_preserves_uniform(self, test_region):
        """Uniform field should stay uniform after resampling."""
        lon_1d = np.linspace(6.0, 21.0, 200)
        lat_1d = np.linspace(43.0, 52.0, 200)
        lon, lat = np.meshgrid(lon_1d, lat_1d)
        data = np.ones_like(lon) * 42.0
        result, _, _ = test_region.resample_to_subdomain(
            data, lon, lat, "Default", fix_nans=True)
        # all non-NaN values should be close to 42
        valid = result[~np.isnan(result)]
        if len(valid) > 0:
            np.testing.assert_allclose(valid, 42.0, atol=0.5)
