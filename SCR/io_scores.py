"""Write the verification results of one run to a self-describing NetCDF file.

One file per verification run (accumulation window x verification subdomain)
holds the scalar scores, ranks and field statistics of all forecasts and the
full FSS arrays, together with the metadata needed to interpret them.

All variables use the dimensions (valid_time, conf, subdomain, lead_hours, ...)
with a single valid time and subdomain per file, so files of one experiment can
be stacked by downstream tools. Reading, combining and aggregating score files
is not part of panelification.
"""
import datetime as dt
import functools
import os
import re
import subprocess
import sys
from collections import Counter

import numpy as np
import xarray as xr

import parameter_settings
from paths import PAN_DIR_SCORES, PAN_DIR_SCR

import logging
logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

# thresholds from this value upwards are dummy rows separating the absolute and
# percentile thresholds in the FSS plots, they carry no information
DUMMY_THRESHOLD = 99999.

# value returned by scoring.fss_d90 when no displacement can be determined
D90_UNDEFINED = 9999.

# percentiles of the forecast and observation fields, 0 ... 100 with --save_percentiles
DEFAULT_PERCENTILES = [50, 75, 90, 95, 99]

SCORE_DIMS = ("valid_time", "conf", "subdomain", "lead_hours")

# scalar scores of each forecast: file variable, key in the sim dict, long_name, units
# ("parameter" is replaced by the units of the verified parameter)
SCALAR_SCORES = [
    ("bias", "bias_real", "mean error (forecast minus observation)", "parameter"),
    ("mae", "mae", "mean absolute error", "parameter"),
    ("rms", "rms", "root mean squared error", "parameter"),
    ("corr", "corr", "Pearson correlation coefficient", "1"),
    ("d90", "d90", "displacement of the areas above the 90th percentile", "km"),
    ("fss_condensed", "fss_condensed",
     "condensed FSS, sum of the rescaled FSS over thresholds and windows", "1"),
    ("fss_condensed_weighted", "fss_condensed_weighted",
     "weighted condensed FSS, unnormalised sum", "1"),
    ("fss_condensed_weighted_rect", "fss_condensed_weighted_rect",
     "area weighted condensed FSS (cwFSS) in [0, 1]", "1"),
    ("cwfss_robust", "cwfss_robust", "cwFSS from quasi-random threshold and window samples", "1"),
    ("cwfss_std", "cwfss_std", "bootstrap standard deviation of cwfss_robust", "1"),
    ("rank_bias", "rank_bias", "rank by absolute bias within this run, 1 = best", "1"),
    ("rank_mae", "rank_mae", "rank by mae within this run, 1 = best", "1"),
    ("rank_rms", "rank_rms", "rank by rms within this run, 1 = best", "1"),
    ("rank_corr", "rank_corr", "rank by corr within this run, 1 = best", "1"),
    ("rank_d90", "rank_d90", "rank by d90 within this run, 1 = best", "1"),
    ("rank_fss_condensed", "rank_fss_condensed",
     "rank by fss_condensed within this run, 1 = best", "1"),
    ("rank_fss_condensed_weighted", "rank_fss_condensed_weighted",
     "rank by fss_condensed_weighted within this run, 1 = best", "1"),
]

# FSS data frames (thresholds x windows) of each forecast: file variable, key in the sim dict, attributes
FSS_ARRAYS = [
    ("fss", "fss", {"long_name": "fractions skill score", "units": "1",
                    "comment": "fss = 1 - fss_num / fss_den"}),
    ("fss_num", "fss_num", {"long_name": "FSS numerator", "units": "1"}),
    ("fss_den", "fss_den", {"long_name": "FSS denominator", "units": "1"}),
]
FSSP_ARRAYS = [
    ("fssp", "fssp", {"long_name": "fractions skill score for percentile thresholds", "units": "1",
                      "comment": "fssp = 1 - fssp_num / fssp_den"}),
    ("fssp_num", "fssp_num", {"long_name": "FSS numerator for percentile thresholds", "units": "1"}),
    ("fssp_den", "fssp_den", {"long_name": "FSS denominator for percentile thresholds", "units": "1"}),
]


def score_file_path(args, start_date, subdomain):
    """ Path of the score file of one verification run """
    start_date_str = start_date.strftime("%Y%m%d_%H")
    file_name = (f"{args.name}{args.parameter}_scores_{start_date_str}UTC_"
                 f"{args.duration:02d}h_acc_{_region_name(args)}_{subdomain}.nc")
    return os.path.join(PAN_DIR_SCORES, file_name)


def save_scores(data_list, start_date, end_date, subdomain, args):
    """ Write the scores of all forecasts in data_list for one subdomain to a NetCDF file.

    The file is written under a temporary name and renamed once it is complete,
    so parallel or aborted runs never leave partially written score files."""
    ds = build_run_dataset(data_list, start_date, end_date, subdomain, args)
    path = score_file_path(args, start_date, subdomain)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fss_variables = {name for name, _, _ in FSS_ARRAYS + FSSP_ARRAYS}
    encoding = {}
    for name in ds.data_vars:
        encoding[name] = {"zlib": True, "complevel": 4}
        if name in fss_variables:
            encoding[name]["dtype"] = "float32"
    # coordinates are never missing and need no fill value
    for name in ds.coords:
        if ds[name].dtype.kind == "f":
            encoding[name] = {"_FillValue": None}
    tmp_path = f"{path}.tmp{os.getpid()}"
    try:
        ds.to_netcdf(tmp_path, format="NETCDF4", engine="netcdf4", encoding=encoding)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    logger.info(f"Scores written to {path}")
    return path


def build_run_dataset(data_list, start_date, end_date, subdomain, args):
    """ Collect the scores of one verification run into an xarray Dataset.

    data_list[0] is the observation, all other entries are forecasts. Each
    forecast is placed at (conf, lead_hours), combinations without a forecast
    are NaN."""
    obs = data_list[0]
    forecasts = data_list[1:]
    units = parameter_settings.get_units(args)
    percentiles = list(range(101)) if getattr(args, "save_percentiles", False) else DEFAULT_PERCENTILES

    positions = [(_output_conf(sim), _lead_hours(sim, start_date)) for sim in forecasts]
    duplicates = [pos for pos, count in Counter(positions).items() if count > 1]
    if duplicates:
        names = [sim['name'] for sim, pos in zip(forecasts, positions) if pos in duplicates]
        raise ValueError(f"Several forecasts have the same conf and lead time, "
                         f"their scores cannot be stored: {names}")
    confs = sorted({conf for conf, _ in positions})
    leads = sorted({lead for _, lead in positions})
    indices = [(confs.index(conf), leads.index(lead)) for conf, lead in positions]
    grid_shape = (len(confs), len(leads))

    data_vars = {}
    for name, key, long_name, var_units in SCALAR_SCORES:
        if not any(key in sim for sim in forecasts):
            continue
        values = np.full(grid_shape, np.nan)
        for (ii, jj), sim in zip(indices, forecasts):
            if sim.get(key) is not None:
                values[ii, jj] = sim[key]
        attrs = {"long_name": long_name, "units": units if var_units == "parameter" else var_units}
        if name == "d90":
            values[values == D90_UNDEFINED] = np.nan
            attrs["comment"] = ("half window width in grid points of the ~1 km verification grid, "
                                "NaN where no displacement could be determined")
        data_vars[name] = (SCORE_DIMS, values[np.newaxis, :, np.newaxis, :], attrs)

    forecast_max = np.full(grid_shape, np.nan)
    forecast_mean = np.full(grid_shape, np.nan)
    forecast_percentile = np.full(grid_shape + (len(percentiles),), np.nan)
    for (ii, jj), sim in zip(indices, forecasts):
        forecast_max[ii, jj], forecast_mean[ii, jj], forecast_percentile[ii, jj] = _field_statistics(
            sim["precip_data_resampled"], percentiles)
    obs_max, obs_mean, obs_percentile = _field_statistics(obs["precip_data_resampled"], percentiles)
    obs_dims = ("valid_time", "subdomain")
    data_vars.update({
        "forecast_max": (SCORE_DIMS, forecast_max[np.newaxis, :, np.newaxis, :],
                         {"long_name": "maximum of the forecast field", "units": units}),
        "forecast_mean": (SCORE_DIMS, forecast_mean[np.newaxis, :, np.newaxis, :],
                          {"long_name": "mean of the forecast field", "units": units}),
        "forecast_percentile": (SCORE_DIMS + ("percentile",),
                                forecast_percentile[np.newaxis, :, np.newaxis, :, :],
                                {"long_name": "percentiles of the forecast field", "units": units}),
        "obs_max": (obs_dims, np.full((1, 1), obs_max),
                    {"long_name": "maximum of the observed field", "units": units}),
        "obs_mean": (obs_dims, np.full((1, 1), obs_mean),
                     {"long_name": "mean of the observed field", "units": units}),
        "obs_percentile": (obs_dims + ("percentile",), obs_percentile[np.newaxis, np.newaxis, :],
                           {"long_name": "percentiles of the observed field", "units": units}),
    })

    coords = {
        "valid_time": ("valid_time", np.array([start_date], dtype="datetime64[ns]"),
                       {"long_name": "start of the accumulation window"}),
        "conf": ("conf", np.array(confs, dtype=str), {"long_name": "model configuration"}),
        "subdomain": ("subdomain", np.array([subdomain], dtype=str),
                      {"long_name": "verification subdomain"}),
        "lead_hours": ("lead_hours", np.array(leads, dtype=np.int32),
                       {"long_name": "lead time at the start of the accumulation window", "units": "h",
                        "comment": "init time = valid_time - lead_hours"}),
        "percentile": ("percentile", np.array(percentiles, dtype=np.int32),
                       {"long_name": "percentile of the verified field", "units": "%"}),
    }

    if getattr(args, "save_full_fss", True):
        thresholds, windows, fss_vars = _fss_arrays(forecasts, indices, grid_shape, FSS_ARRAYS, "threshold")
        if fss_vars:
            coords["threshold"] = ("threshold", thresholds, {
                "long_name": "FSS threshold", "units": units,
                "comment": f"threshold mode: {getattr(args, 'fss_threshold_mode', 'over')}"})
            coords["window"] = ("window", windows, {
                "long_name": "FSS window width", "units": "grid points",
                "comment": "the verification grid spacing is about 1 km"})
            data_vars.update(fss_vars)
        pct_thresholds, _, fssp_vars = _fss_arrays(forecasts, indices, grid_shape, FSSP_ARRAYS, "pct_threshold")
        if fssp_vars:
            coords["pct_threshold"] = ("pct_threshold", pct_thresholds, {
                "long_name": "FSS percentile threshold", "units": "%"})
            data_vars.update(fssp_vars)

    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    attrs = {
        "title": "Panelification verification scores",
        "schema_version": SCHEMA_VERSION,
        "experiment_name": args.name.rstrip("_"),
        "parameter": args.parameter,
        "parameter_units": units,
        "verif_dataset": getattr(args, "verif_dataset", None),
        "region": _region_name(args),
        "subdomain": subdomain,
        **_subdomain_attrs(args, subdomain),
        "accumulation_hours": args.duration,
        "valid_start": start_date.isoformat(),
        "valid_end": end_date.isoformat(),
        "fss_method": getattr(args, "fss_method", None),
        "fss_calc_mode": getattr(args, "fss_calc_mode", None),
        "fss_threshold_mode": getattr(args, "fss_threshold_mode", "over"),
        "fss_tolerance": getattr(args, "fss_tolerance", None),
        "fix_nans": getattr(args, "fix_nans", None),
        "opera_qi_threshold": getattr(args, "opera_qi_threshold", None),
        "source": f"panelification {_code_version()}",
        "history": f"{created} {' '.join(sys.argv)}",
        "created": created,
    }
    return xr.Dataset(data_vars, coords=coords, attrs=_netcdf_attrs(attrs))


def _fss_arrays(forecasts, indices, grid_shape, arrays, row_dim):
    """ Place the FSS data frames of all forecasts on the (conf, lead_hours) grid,
    without the dummy threshold rows. Returns the row and window values and the
    data variables, or no variables if no forecast has FSS data. """
    reference = next((sim[arrays[0][1]] for sim in forecasts if sim.get(arrays[0][1]) is not None), None)
    if reference is None:
        return None, None, {}
    keep = np.asarray(reference.index, dtype=float) < DUMMY_THRESHOLD
    rows = np.asarray(reference.index)[keep]
    windows = np.asarray(reference.columns)
    data_vars = {}
    for name, key, attrs in arrays:
        values = np.full(grid_shape + (rows.size, windows.size), np.nan)
        for (ii, jj), sim in zip(indices, forecasts):
            frame = sim.get(key)
            if frame is None:
                continue
            if not (frame.index.equals(reference.index) and frame.columns.equals(reference.columns)):
                raise ValueError(f"{sim['name']}: thresholds or windows of {key} differ from the other forecasts")
            values[ii, jj] = frame.to_numpy(dtype=float)[keep, :]
        data_vars[name] = (SCORE_DIMS + (row_dim, "window"), values[np.newaxis, :, np.newaxis, ...], attrs)
    return rows, windows, data_vars


def _output_conf(sim):
    """ Ensemble pseudo members (mean, median) carry the ensemble init time in
    their name, strip it so the conf is the same for all init times """
    conf = str(sim['conf'])
    if sim.get('pseudo'):
        conf = re.sub(r'_\d{8}_\d{2}(?=_[^_]+$)', '', conf)
    return conf


def _lead_hours(sim, start_date):
    """ Lead time at the start of the accumulation window, derived from the init time """
    init = sim['init']
    if not isinstance(init, dt.datetime):
        raise TypeError(f"{sim['name']}: init time must be a datetime, got {init!r}")
    return int(round((start_date - init).total_seconds() / 3600.))


def _field_statistics(field, percentiles):
    """ Maximum, mean and percentiles of a field, ignoring missing values """
    field = np.asarray(field, dtype=float)
    if np.isnan(field).all():
        return np.nan, np.nan, np.full(len(percentiles), np.nan)
    return np.nanmax(field), np.nanmean(field), np.nanpercentile(field, percentiles)


def _region_name(args):
    region = getattr(args, "region", None)
    if region is None:
        return "unknown"
    return getattr(region, "name", str(region))


def _subdomain_attrs(args, subdomain):
    """ Bounds and size of the verification grid, if the region defines the subdomain """
    subdomains = getattr(getattr(args, "region", None), "subdomains", None) or {}
    if subdomain not in subdomains:
        return {}
    lon = np.asarray(subdomains[subdomain]["lon"])
    lat = np.asarray(subdomains[subdomain]["lat"])
    return {
        "subdomain_lon_min": float(lon.min()),
        "subdomain_lon_max": float(lon.max()),
        "subdomain_lat_min": float(lat.min()),
        "subdomain_lat_max": float(lat.max()),
        "subdomain_ny": int(lon.shape[0]),
        "subdomain_nx": int(lon.shape[1]),
    }


def _netcdf_attrs(attrs):
    """ NetCDF attributes cannot hold None or booleans """
    clean = {}
    for key, value in attrs.items():
        if value is None:
            continue
        if isinstance(value, (bool, np.bool_)):
            value = int(value)
        elif not isinstance(value, (str, int, float, np.integer, np.floating)):
            value = str(value)
        clean[key] = value
    return clean


@functools.lru_cache(maxsize=None)
def _code_version():
    """ git describe of the panelification code, "unknown" outside a git checkout """
    try:
        result = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=PAN_DIR_SCR,
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    version = result.stdout.strip()
    return version if result.returncode == 0 and version else "unknown"
