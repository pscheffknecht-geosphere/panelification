"""Shared fixtures for the panelification test suite."""

import sys
from pathlib import Path

# Add SCR/ to sys.path so bare imports (import fss_SAT, etc.) work
SCR_DIR = str(Path(__file__).resolve().parent.parent / "SCR")
if SCR_DIR not in sys.path:
    sys.path.insert(0, SCR_DIR)

# Set non-interactive matplotlib backend before any plotting imports
import matplotlib
matplotlib.use("Agg")

import argparse
import numpy as np
import pytest


# ---------------------------------------------------------------------------
# synthetic field helpers
# ---------------------------------------------------------------------------

def _gaussian_field(ny, nx, cx, cy, sigma=15, amplitude=50.0):
    """Generate a 2D Gaussian field."""
    y, x = np.mgrid[0:ny, 0:nx]
    return amplitude * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * sigma ** 2))


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def small_fields():
    """Pair of 64x64 fields: obs (centered Gaussian) and fcst (shifted 8px east)."""
    ny, nx = 64, 64
    obs = _gaussian_field(ny, nx, cx=nx // 2, cy=ny // 2)
    fcst = _gaussian_field(ny, nx, cx=nx // 2 + 8, cy=ny // 2)
    return obs.astype(np.float64), fcst.astype(np.float64)


@pytest.fixture
def identical_fields():
    """Pair of identical 64x64 Gaussian fields (perfect forecast)."""
    ny, nx = 64, 64
    field = _gaussian_field(ny, nx, cx=nx // 2, cy=ny // 2)
    return field.astype(np.float64), field.copy().astype(np.float64)


@pytest.fixture
def zero_fields():
    """Pair of all-zero 64x64 fields."""
    z = np.zeros((64, 64), dtype=np.float64)
    return z, z.copy()


@pytest.fixture
def standard_windows():
    """Small set of FSS window sizes for fast tests."""
    return np.array([3, 5, 11, 21])


@pytest.fixture
def standard_thresholds():
    """Small set of FSS thresholds for fast tests."""
    return [0.1, 1.0, 5.0, 10.0]


@pytest.fixture
def make_test_args():
    """Factory fixture returning an argparse.Namespace with sensible defaults."""
    def _make(**overrides):
        defaults = dict(
            parameter="precip",
            d_windows=[],
            fss_calc_mode="same",
            fss_method="default",
            duration=1,
            name="TEST_",
            save_percentiles=False,
            mode="normal",
            rank_by_fss_metric="fss_condensed_weighted",
            threads=1,
            fss_threshold_mode="over",
            fss_tolerance=0.1,
            dpi=72,
            clean=False,
            hidden=False,
            draw_p90=False,
            draw_subdomain=True,
            fss_mode="ranks",
            greens=True,
            zoom_to_subdomain=False,
            panel_rows_columns=None,
            rank_score_time_series=[],
            tile=[None, None],
            cmap="mycolors",
            colormap='print',
            start="2024071500",
            region=None,
        )
        defaults.update(overrides)
        return argparse.Namespace(**defaults)
    return _make
