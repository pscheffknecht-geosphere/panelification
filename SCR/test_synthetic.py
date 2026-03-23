"""
Synthetic test suite for the panelification scoring, ranking, and plotting pipeline.

Generates a 5x5 grid of synthetic models (5 offsets x 5 scale factors),
resamples them onto a verification subdomain, then runs them through
the full scoring, ranking, ranking-robustness check, and panel plotting pipeline.

Usage:
    python test_synthetic.py
"""

import numpy as np
import argparse
import logging
import os
import sys
from datetime import datetime, timedelta

import scoring
import parameter_settings
import regions
import panel_plotter
import ranking_check
from paths import PAN_DIR_SCORES, PAN_DIR_PLOTS, PAN_DIR_TMP

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------

# test region: central Europe
TEST_REGION_DEF = {
    "central_longitude": 13.0,
    "central_latitude": 47.5,
    "extent": [8.0, 19.0, 45.0, 50.0],
    "verification_subdomains": {
        "Default": {
            "central_longitude": 13.0,
            "central_latitude": 47.5,
            "x_size": 600.,
            "y_size": 400.,
            "thresholds": {
                "draw_avg": 0., "draw_max": 0.,
                "score_avg": 0., "score_max": 0.,
            },
        }
    },
}

ATOL = 1e-6  # absolute tolerance for float comparisons

# 5x5 parameter grid
OFFSETS_KM = [20, 35, 50, 70, 90]        # east-west displacement in km
# SCALE_FACTORS = [0.3, 0.725, 1.15, 1.575, 2.0]  # multiplicative bias
SCALE_FACTORS = np.arange(0.3, 3.01, 0.3)  # multiplicative bias

# colors for the 5 offset groups (used in time series plots)
OFFSET_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]

# time series scores to plot
TIME_SERIES_SCORES = [
    "bias", "mae", "rms", "corr",
    "fss_condensed_weighted", "cwfss_robust", "cwfss_std",
]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def make_args(region, **overrides):
    """Return an argparse.Namespace that satisfies scoring AND plotting."""
    defaults = dict(
        # scoring
        parameter="precip",
        d_windows=[],
        fss_calc_mode="same",
        fss_method="default",
        duration=1,
        name="TEST_",
        save_percentiles=False,
        mode="normal",
        rank_by_fss_metric="fss_condensed_weighted",
        threads=4,
        # plotting
        region=region,
        dpi=100,
        clean=False,
        hidden=False,
        draw_p90=False,
        draw_subdomain=True,
        fss_mode="ranks",
        greens=True,
        zoom_to_subdomain=False,
        panel_rows_columns=None,
        rank_score_time_series=TIME_SERIES_SCORES,
        tile=[None, None],
        cmap="mycolors",
        print_colors=True,
        start="2024071500",
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def make_model_lon_lat(nx=900, ny=900):
    """Return 2D lon/lat grids covering well beyond the plot extent."""
    lon_1d = np.linspace(6.0, 21.0, nx)
    lat_1d = np.linspace(43.0, 52.0, ny)
    lon, lat = np.meshgrid(lon_1d, lat_1d)
    return lon, lat


def make_obs_field(ny, nx, seed=42):
    """Gaussian storm cell centered 100 km west of domain center, no noise."""
    y, x = np.mgrid[0:ny, 0:nx]
    cx, cy = nx // 2, ny // 2
    # 100 km west: at 47.5°N, 1° lon ≈ 75 km; grid spans 15° over nx points
    # so 100 km ≈ 1.33° ≈ nx * 1.33/15 ≈ 80 gridpoints for nx=900
    deg_per_gp = 15.0 / nx
    km_per_gp = deg_per_gp * 111.32 * np.cos(np.radians(47.5))
    west_shift = int(round(100.0 / km_per_gp))
    cx_shifted = cx - west_shift
    # main storm cell, no noise
    field = 50.0 * np.exp(-((x - cx_shifted) ** 2 + (y - cy) ** 2) / (2 * 20 ** 2))
    return np.maximum(field, 0.0)


def make_entry(name, field, lon, lat, entry_type="model", conf=None,
               init=None, lead=6, color=None):
    """Build a data_list entry dict."""
    if conf is None:
        conf = name
    if init is None:
        init = datetime(2024, 7, 15, 0, 0, 0)
    return {
        "case": "test_case",
        "exp": name,
        "conf": conf,
        "type": entry_type,
        "init": init,
        "lead": lead,
        "name": name,
        "lon": lon,
        "lat": lat,
        "precip_data": field,
        "color": color,
        "ensemble": None,
    }


def km_to_gridpoints(km, lon_1d, lat_center=47.5):
    """Convert east-west km offset to gridpoints on the given lon grid."""
    deg_per_gp = (lon_1d[-1] - lon_1d[0]) / (len(lon_1d) - 1)
    km_per_deg = 111.32 * np.cos(np.radians(lat_center))
    km_per_gp = deg_per_gp * km_per_deg
    return int(round(km / km_per_gp))


# ---------------------------------------------------------------------------
# test-case catalogue
# ---------------------------------------------------------------------------

def build_test_data_list(lon, lat):
    """Return (data_list, meta) with 1 obs + 25 models (5 offsets x 5 scales).

    Models are grouped by offset (= conf), with different scale factors
    mapped to different pseudo-init times so that the time series plots
    show score variation across scales for each offset group.
    """
    obs_field = make_obs_field(ny=lon.shape[0], nx=lon.shape[1])

    obs = make_entry("OBS", obs_field, lon, lat, entry_type="obs", conf="INCA")
    data_list = [obs]
    meta = {}

    lon_1d = lon[0, :]
    base_init = datetime(2024, 7, 15, 0, 0, 0)

    for oi, offset_km in enumerate(OFFSETS_KM):
        shift_gp = km_to_gridpoints(offset_km, lon_1d)
        shifted = np.roll(obs_field, shift_gp, axis=1)
        conf_name = f"Off_{offset_km:03d}km"
        color = OFFSET_COLORS[oi]

        for si, scale in enumerate(SCALE_FACTORS):
            name = f"O{offset_km:03d}_S{scale:.2f}"
            field = shifted * scale
            # use scale index as pseudo-init offset (6h apart)
            init = base_init + timedelta(hours=6 * si)
            data_list.append(make_entry(
                name, field, lon, lat, lead=6,
                conf=conf_name, init=init, color=color,
            ))
            meta[name] = {
                "offset_km": offset_km, "scale": scale,
                "shift_gp": shift_gp, "conf": conf_name,
            }

    return data_list, meta


# ---------------------------------------------------------------------------
# resampling
# ---------------------------------------------------------------------------

def resample_all(data_list, region, fix_nans=False):
    """Resample all entries onto the verification subdomain."""
    for subdomain_name in region.subdomains:
        for sim in data_list:
            data, rlon, rlat = region.resample_to_subdomain(
                sim["precip_data"], sim["lon"], sim["lat"],
                subdomain_name, fix_nans=fix_nans,
            )
            sim["precip_data_resampled"] = data
            sim["lon_resampled"] = rlon
            sim["lat_resampled"] = rlat


# ---------------------------------------------------------------------------
# run scoring pipeline
# ---------------------------------------------------------------------------

def run_scoring(data_list, args):
    """Run calc_scores on every entry, then rank."""
    obs = data_list[0]
    for sim in data_list:
        scoring.calc_scores(sim, obs, args)
    scoring.rank_scores(data_list)


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def check(self, condition, description):
        if condition:
            self.passed += 1
        else:
            self.failed += 1
            self.errors.append(description)
            logger.error("FAIL: %s", description)

    def summary(self):
        total = self.passed + self.failed
        logger.info("=" * 60)
        logger.info("Results: %d / %d checks passed", self.passed, total)
        if self.errors:
            logger.info("Failures:")
            for e in self.errors:
                logger.info("  - %s", e)
        logger.info("=" * 60)
        return self.failed == 0


def by_name(data_list, name):
    return next(s for s in data_list if s["name"] == name)


def validate(data_list, meta):
    v = ValidationResult()

    # --- obs sanity ---
    obs = data_list[0]
    v.check(obs["type"] == "obs", "obs type is 'obs'")
    v.check(obs["bias"] == 999, "obs bias placeholder is 999")
    v.check(obs["fss"] is None, "obs fss is None")
    v.check("max_rank" in obs, "max_rank set on obs dict")

    # --- For each model: basic consistency ---
    for sim in data_list[1:]:
        name = sim["name"]
        v.check(sim["mae"] >= 0, f"{name} MAE >= 0")
        v.check(sim["rms"] >= 0, f"{name} RMS >= 0")

    # --- Scale=1.15 (closest to 1.0) at smallest offset should be best ---
    best_name = f"O{OFFSETS_KM[0]:03d}_S{SCALE_FACTORS[2]:.2f}"
    best = by_name(data_list, best_name)
    worst_name = f"O{OFFSETS_KM[-1]:03d}_S{SCALE_FACTORS[0]:.2f}"
    worst = by_name(data_list, worst_name)
    v.check(
        best["fss_condensed_weighted"] > worst["fss_condensed_weighted"],
        f"Best case ({best_name}) FSS > worst case ({worst_name}) FSS",
    )

    # --- For fixed scale, first 4 offsets (before wrap-around) should show increasing MAE ---
    for scale in SCALE_FACTORS:
        maes = []
        for offset_km in OFFSETS_KM[:4]:
            name = f"O{offset_km:03d}_S{scale:.2f}"
            maes.append(by_name(data_list, name)["mae"])
        v.check(
            maes == sorted(maes),
            f"Scale={scale:.2f}: MAE increases with offset 30-195 ({[f'{m:.2f}' for m in maes]})",
        )

    # --- For fixed scale, first 4 offsets should show decreasing FSS ---
    for scale in SCALE_FACTORS:
        fss_vals = []
        for offset_km in OFFSETS_KM[:4]:
            name = f"O{offset_km:03d}_S{scale:.2f}"
            fss_vals.append(by_name(data_list, name)["fss_condensed_weighted"])
        v.check(
            fss_vals == sorted(fss_vals, reverse=True),
            f"Scale={scale:.2f}: FSS decreases with offset 30-195 ({[f'{f:.4f}' for f in fss_vals]})",
        )

    # --- For fixed offset, scale=1.15 (closest to 1) should have best corr ---
    for offset_km in OFFSETS_KM:
        best_scale_name = f"O{offset_km:03d}_S{SCALE_FACTORS[2]:.2f}"
        best_corr = by_name(data_list, best_scale_name)["corr"]
        for scale in SCALE_FACTORS:
            if scale == SCALE_FACTORS[2]:
                continue
            name = f"O{offset_km:03d}_S{scale:.2f}"
            v.check(
                by_name(data_list, name)["corr"] <= best_corr + 1e-6,
                f"{best_scale_name} has best corr at offset {offset_km} km",
            )

    # --- Bias direction: scale < 1 -> negative bias_real, scale > 1 -> positive ---
    for offset_km in OFFSETS_KM:
        low_name = f"O{offset_km:03d}_S{SCALE_FACTORS[0]:.2f}"
        high_name = f"O{offset_km:03d}_S{SCALE_FACTORS[-1]:.2f}"
        v.check(
            by_name(data_list, low_name)["bias_real"] < 0,
            f"{low_name} bias_real < 0 (underestimated)",
        )
        v.check(
            by_name(data_list, high_name)["bias_real"] > 0,
            f"{high_name} bias_real > 0 (overestimated)",
        )

    # --- Ranking robustness: cwfss_robust and cwfss_std should exist ---
    for sim in data_list[1:]:
        name = sim["name"]
        v.check("cwfss_robust" in sim, f"{name} has cwfss_robust")
        v.check("cwfss_std" in sim, f"{name} has cwfss_std")
        v.check(sim["cwfss_std"] >= 0, f"{name} cwfss_std >= 0")

    return v


# ---------------------------------------------------------------------------
# CSV output test
# ---------------------------------------------------------------------------

def test_csv_output(data_list, args):
    """Write CSV and verify the file was created."""
    os.makedirs(PAN_DIR_SCORES, exist_ok=True)
    start_date = datetime(2024, 7, 15, 0, 0, 0)
    end_date = datetime(2024, 7, 15, 1, 0, 0)
    windows = parameter_settings.get_windows(args)
    thresholds = parameter_settings.get_fss_thresholds(args)
    scoring.write_scores_to_csv(
        data_list, start_date, end_date, args, "TestDomain", windows, thresholds
    )
    expected_csv = os.path.join(
        PAN_DIR_SCORES,
        f"{args.name}RR_score_20240715_00UTC_{args.duration:02d}h_acc_TestDomain.csv",
    )
    if os.path.isfile(expected_csv):
        logger.info("CSV written successfully: %s", expected_csv)
        return True
    else:
        logger.error("CSV not found at expected path: %s", expected_csv)
        return False


# ---------------------------------------------------------------------------
# plotting
# ---------------------------------------------------------------------------

def run_plotting(data_list, args):
    """Draw panels using panel_plotter.draw_panels."""
    os.makedirs(PAN_DIR_PLOTS, exist_ok=True)
    os.makedirs(PAN_DIR_TMP, exist_ok=True)
    start_date = datetime(2024, 7, 15, 0, 0, 0)
    end_date = datetime(2024, 7, 15, 1, 0, 0)
    outfile = panel_plotter.draw_panels(
        data_list, start_date, end_date, "TestDomain", args,
    )
    return outfile


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    # --- set up test region ---
    logger.info("Setting up test region ...")
    regions.regions["Test"] = TEST_REGION_DEF
    region = regions.Region("Test", ["Default"])

    args = make_args(region)
    lon, lat = make_model_lon_lat()

    # --- build synthetic data ---
    logger.info("Building synthetic test data ...")
    data_list, meta = build_test_data_list(lon, lat)
    logger.info(
        "Created %d entries (1 obs + %d models)", len(data_list), len(data_list) - 1
    )

    # --- resample onto subdomain ---
    logger.info("Resampling onto verification subdomain ...")
    resample_all(data_list, region, fix_nans=True)
    resampled_shape = data_list[0]["precip_data_resampled"].shape
    logger.info("Resampled grid shape: %s", resampled_shape)

    # --- score and rank ---
    logger.info("Running scoring pipeline ...")
    run_scoring(data_list, args)

    # --- ranking robustness check ---
    logger.info("Running ranking robustness check ...")
    ranking_check.add_rank_robustness_info(data_list, args)
    ranking_check.extract_cwfss_array(data_list)

    # --- validate ---
    logger.info("Validating results ...")
    v = validate(data_list, meta)

    # --- CSV output ---
    logger.info("Testing CSV output ...")
    csv_ok = test_csv_output(data_list, args)
    v.check(csv_ok, "CSV output file created successfully")

    # --- panel plot (includes time series) ---
    logger.info("Drawing panel plot ...")
    outfile = run_plotting(data_list, args)
    plot_ok = outfile is not None and os.path.isfile(outfile)
    v.check(plot_ok, f"Panel plot created at {outfile}")
    if plot_ok:
        logger.info("Panel plot saved to: %s", outfile)

    # --- ranking confidence plot ---
    logger.info("Drawing ranking confidence plot ...")
    start_date = datetime(2024, 7, 15, 0, 0, 0)
    end_date = datetime(2024, 7, 15, 1, 0, 0)
    ranking_check.draw_ranking_confidence_plot(
        data_list, start_date, end_date, "TestDomain", args,
    )

    ok = v.summary()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
