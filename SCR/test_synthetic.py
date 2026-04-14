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
# OFFSETS_KM = [20, 35, 50, 70, 90]        # east-west displacement in km
OFFSETS_KM = [20, 50, 90]        # east-west displacement in km
# SCALE_FACTORS = [0.3, 0.725, 1.15, 1.575, 2.0]  # multiplicative bias
# SCALE_FACTORS = [0.5, 0.75, 0.9, 1., 1.1111111, 1.33333333, 2.]  # multiplicative bias
SCALE_FACTORS = [0.5, 0.75, 1., 1.33333333, 2.]  # multiplicative bias
# SCALE_FACTORS = np.arange(0.2, 2.01, 0.1)  # multiplicative bias

SPLIT_DISPLACEMENT_KM = 30  # east/west displacement for split-Gaussian group

# colors for the offset groups + split group (used in time series plots)
OFFSET_COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

# time series scores to plot
TIME_SERIES_SCORES = [
    "bias", "mae", "rms", "corr", "d90",
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
        threads=8,
        fss_threshold_mode="over",
        fss_tolerance=0.1,
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


def make_split_field(obs_field, lon, split_km=30):
    """Two half-amplitude Gaussians displaced east/west, conserving total precip.

    Takes the obs field and splits it into two copies shifted ±split_km,
    each scaled so that the domain-total precipitation matches the original.
    """
    lon_1d = lon[0, :]
    shift_gp = km_to_gridpoints(split_km, lon_1d)
    east = np.roll(obs_field, shift_gp, axis=1)
    west = np.roll(obs_field, -shift_gp, axis=1)
    combined = 0.5 * east + 0.5 * west
    # rescale to conserve total precipitation
    obs_sum = np.sum(obs_field)
    comb_sum = np.sum(combined)
    if comb_sum > 0:
        combined *= obs_sum / comb_sum
    return combined


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
    """Return (data_list, meta) with 1 obs + models.

    Groups:
    - Offset groups: single Gaussian shifted east by OFFSETS_KM, all scale factors
    - Split group: two half-amplitude Gaussians ±30 km east/west (bias-conserving),
      all scale factors

    Models are grouped by conf, with different scale factors mapped to
    different pseudo-init times for time series plots.
    """
    obs_field = make_obs_field(ny=lon.shape[0], nx=lon.shape[1])

    obs = make_entry("OBS", obs_field, lon, lat, entry_type="obs", conf="INCA")
    data_list = [obs]
    meta = {}

    lon_1d = lon[0, :]
    base_init = datetime(2024, 7, 15, 0, 0, 0)

    # --- offset groups ---
    for oi, offset_km in enumerate(OFFSETS_KM):
        shift_gp = km_to_gridpoints(offset_km, lon_1d)
        shifted = np.roll(obs_field, shift_gp, axis=1)
        conf_name = f"Off_{offset_km:03d}km"
        color = OFFSET_COLORS[oi]

        for si, scale in enumerate(SCALE_FACTORS):
            name = f"O{offset_km:03d}_S{scale:.2f}"
            field = shifted * scale
            init = base_init + timedelta(hours=6 * si)
            data_list.append(make_entry(
                name, field, lon, lat, lead=6,
                conf=conf_name, init=init, color=color,
            ))
            meta[name] = {
                "offset_km": offset_km, "scale": scale,
                "shift_gp": shift_gp, "conf": conf_name,
            }

    # --- split-Gaussian group: two peaks ±30 km, bias-conserving ---
    split_field = make_split_field(obs_field, lon, split_km=SPLIT_DISPLACEMENT_KM)
    conf_name = f"Split_{SPLIT_DISPLACEMENT_KM:02d}km"
    color = OFFSET_COLORS[len(OFFSETS_KM)]

    for si, scale in enumerate(SCALE_FACTORS):
        name = f"SPL{SPLIT_DISPLACEMENT_KM:02d}_S{scale:.2f}"
        field = split_field * scale
        init = base_init + timedelta(hours=6 * si)
        data_list.append(make_entry(
            name, field, lon, lat, lead=6,
            conf=conf_name, init=init, color=color,
        ))
        meta[name] = {
            "offset_km": 0, "scale": scale,
            "split_km": SPLIT_DISPLACEMENT_KM, "conf": conf_name,
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

    # --- Split-Gaussian checks ---
    spl_prefix = f"SPL{SPLIT_DISPLACEMENT_KM:02d}"

    # bias direction for split group
    spl_low = f"{spl_prefix}_S{SCALE_FACTORS[0]:.2f}"
    spl_high = f"{spl_prefix}_S{SCALE_FACTORS[-1]:.2f}"
    v.check(
        by_name(data_list, spl_low)["bias_real"] < 0,
        f"{spl_low} bias_real < 0 (underestimated)",
    )
    v.check(
        by_name(data_list, spl_high)["bias_real"] > 0,
        f"{spl_high} bias_real > 0 (overestimated)",
    )

    # at scale=1 the split field should be nearly bias-neutral
    scale_1_idx = SCALE_FACTORS.index(1.)
    spl_unbiased = f"{spl_prefix}_S{SCALE_FACTORS[scale_1_idx]:.2f}"
    v.check(
        abs(by_name(data_list, spl_unbiased)["bias_real"]) < 0.5,
        f"{spl_unbiased} bias_real near zero (bias-conserving split)",
    )

    # split at scale=1 should have worse FSS than smallest offset at scale=1
    best_offset_name = f"O{OFFSETS_KM[0]:03d}_S{SCALE_FACTORS[scale_1_idx]:.2f}"
    v.check(
        by_name(data_list, spl_unbiased)["fss_condensed_weighted"]
        < by_name(data_list, best_offset_name)["fss_condensed_weighted"],
        f"{spl_unbiased} FSS < {best_offset_name} FSS (split worse than small offset)",
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

def deep_copy_data_list(data_list):
    """Return a deep copy of data_list, preserving numpy arrays."""
    import copy
    return copy.deepcopy(data_list)


def run_mode(data_list, meta, region, mode, tolerance=0.1):
    """Run scoring, ranking, validation, CSV, and plotting for one FSS mode."""
    mode_label = mode.upper()
    name_prefix = f"TEST_{mode_label}_"
    logger.info("=" * 60)
    logger.info("Running pipeline with fss_threshold_mode='%s' (name=%s)", mode, name_prefix)
    logger.info("=" * 60)

    args = make_args(region, name=name_prefix,
                     fss_threshold_mode=mode, fss_tolerance=tolerance)

    # --- score and rank ---
    logger.info("[%s] Running scoring pipeline ...", mode_label)
    run_scoring(data_list, args)

    # --- ranking robustness check ---
    logger.info("[%s] Running ranking robustness check ...", mode_label)
    ranking_check.add_rank_robustness_info(data_list, args)
    ranking_check.extract_cwfss_array(data_list)

    # --- validate ---
    logger.info("[%s] Validating results ...", mode_label)
    v = validate(data_list, meta)

    # --- CSV output ---
    logger.info("[%s] Testing CSV output ...", mode_label)
    csv_ok = test_csv_output(data_list, args)
    v.check(csv_ok, f"[{mode_label}] CSV output file created successfully")

    # --- panel plot (includes time series) ---
    logger.info("[%s] Drawing panel plot ...", mode_label)
    outfile = run_plotting(data_list, args)
    plot_ok = outfile is not None and os.path.isfile(outfile)
    v.check(plot_ok, f"[{mode_label}] Panel plot created at {outfile}")
    if plot_ok:
        logger.info("[%s] Panel plot saved to: %s", mode_label, outfile)

    # --- ranking confidence plot ---
    logger.info("[%s] Drawing ranking confidence plot ...", mode_label)
    start_date = datetime(2024, 7, 15, 0, 0, 0)
    end_date = datetime(2024, 7, 15, 1, 0, 0)
    ranking_check.draw_ranking_confidence_plot(
        data_list, start_date, end_date, "TestDomain", args,
    )

    return v


def main():
    # --- set up test region ---
    logger.info("Setting up test region ...")
    regions.regions["Test"] = TEST_REGION_DEF
    region = regions.Region("Test", ["Default"])

    lon, lat = make_model_lon_lat()

    # --- build synthetic data ---
    logger.info("Building synthetic test data ...")
    data_list, meta = build_test_data_list(lon, lat)
    logger.info(
        "Created %d entries (1 obs + %d models)", len(data_list), len(data_list) - 1
    )

    # --- resample onto subdomain (shared across both modes) ---
    logger.info("Resampling onto verification subdomain ...")
    resample_all(data_list, region, fix_nans=True)
    resampled_shape = data_list[0]["precip_data_resampled"].shape
    logger.info("Resampled grid shape: %s", resampled_shape)

    os.makedirs(PAN_DIR_PLOTS, exist_ok=True)
    os.makedirs(PAN_DIR_TMP, exist_ok=True)
    os.makedirs(PAN_DIR_SCORES, exist_ok=True)

    # --- run both modes ---
    all_ok = True

    # mode 1: normal "over" threshold
    data_over = deep_copy_data_list(data_list)
    v_over = run_mode(data_over, meta, region, "over")
    all_ok = v_over.summary() and all_ok

    # mode 2: "tolerance" threshold
    data_tol = deep_copy_data_list(data_list)
    v_tol = run_mode(data_tol, meta, region, "tolerance", tolerance=0.1)
    all_ok = v_tol.summary() and all_ok

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
