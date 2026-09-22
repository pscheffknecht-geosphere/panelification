"""Convert legacy panelification output to NetCDF score files.

Legacy runs wrote their results to
    {name}RR_score_{YYYYMMDD_HH}UTC_{DD}h_acc_{subdomain}.csv ............. scores, in SCORES
    {name}RR_percentiles_score_{YYYYMMDD_HH}UTC_{DD}h_acc_{subdomain}.csv .. percentiles, in SCORES (optional)
    {name}FSS_data_{YYYYMMDD_HH}UTC_{DD}h_acc_{subdomain}.p ................ FSS, in DATA
All files of one run are converted into one NetCDF score file in the layout of
io_scores.py (schema version 1.0). Score files from before September 2025 are
comma separated, carry the drawing mode in their name (RR_normal_score_...) and
have no conf, init and lead columns and no observation row; they are converted
as far as their content allows, missing values are NaN.

This script is standalone: it imports no panelification module and keeps its
own copy of the score file layout, which is not updated with io_scores.py.

Parameter and region are not stored in the legacy files and are taken from the
command line. Legacy files are never changed, existing NetCDF score files are
only replaced with --overwrite.

Usage:
    python convert_legacy_output.py --region Austria --name INCAOptAndSAMOS --scores_dir /path/SCORES --data_dir /path/DATA
"""
import argparse
import datetime as dt
import functools
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
import xarray as xr

import logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NetCDF score file layout, copied from io_scores.py (schema version 1.0)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"

# thresholds from this value upwards are dummy rows separating the absolute and
# percentile thresholds in the FSS plots, they carry no information
DUMMY_THRESHOLD = 99999.

# value of d90 when no displacement could be determined
D90_UNDEFINED = 9999.

# percentiles of the fields in legacy score files, legacy percentile files hold 0 ... 100
DEFAULT_PERCENTILES = [50, 75, 90, 95, 99]

SCORE_DIMS = ("valid_time", "conf", "subdomain", "lead_hours")

# scalar scores of legacy score files: column (= variable name), long_name, units
# ("parameter" is replaced by the units of the verified parameter)
SCALAR_SCORES = [
    ("bias", "mean error (forecast minus observation)", "parameter"),
    ("mae", "mean absolute error", "parameter"),
    ("rms", "root mean squared error", "parameter"),
    ("corr", "Pearson correlation coefficient", "1"),
    ("d90", "displacement of the areas above the 90th percentile", "km"),
    ("fss_condensed", "condensed FSS, sum of the rescaled FSS over thresholds and windows", "1"),
    ("fss_condensed_weighted", "weighted condensed FSS, unnormalised sum", "1"),
    ("rank_bias", "rank by absolute bias within this run, 1 = best", "1"),
    ("rank_mae", "rank by mae within this run, 1 = best", "1"),
    ("rank_rms", "rank by rms within this run, 1 = best", "1"),
    ("rank_corr", "rank by corr within this run, 1 = best", "1"),
    ("rank_d90", "rank by d90 within this run, 1 = best", "1"),
    ("rank_fss_condensed", "rank by fss_condensed within this run, 1 = best", "1"),
    ("rank_fss_condensed_weighted", "rank by fss_condensed_weighted within this run, 1 = best", "1"),
]

# FSS data frames (thresholds x windows) of legacy pickles: variable name (= key in the pickle), attributes
FSS_ARRAYS = [
    ("fss", {"long_name": "fractions skill score", "units": "1",
             "comment": "fss = 1 - fss_num / fss_den"}),
    ("fss_num", {"long_name": "FSS numerator", "units": "1"}),
    ("fss_den", {"long_name": "FSS denominator", "units": "1"}),
]
FSSP_ARRAYS = [
    ("fssp", {"long_name": "fractions skill score for percentile thresholds", "units": "1",
              "comment": "fssp = 1 - fssp_num / fssp_den"}),
    ("fssp_num", {"long_name": "FSS numerator for percentile thresholds", "units": "1"}),
    ("fssp_den", {"long_name": "FSS denominator for percentile thresholds", "units": "1"}),
]

# units of the verified parameters, copied from parameter_settings.py
PARAMETER_UNITS = {'precip': 'mm', 'precip2': 'mm', 'precip3': 'mm', 'sunshine': 'h',
                   'lightning': 'km-2', 'gusts': 'm s-1', 'hail': '1', 'cma': 'h'}

# ---------------------------------------------------------------------------
# legacy output files
# ---------------------------------------------------------------------------

RUN_PATTERN = r"(?P<date>\d{8}_\d{2})UTC_(?P<duration>\d{2,})h_acc_(?P<subdomain>.+)"
SCORES_CSV = re.compile(rf"^(?P<name>.*?)RR_(?:(?:normal|resampled|diff)_)?score_{RUN_PATTERN}\.csv$")
PERCENTILES_CSV = re.compile(rf"^(?P<name>.*?)RR_percentiles_score_{RUN_PATTERN}\.csv$")
FSS_PICKLE = re.compile(rf"^(?P<name>.*?)FSS_data_{RUN_PATTERN}\.p$")

# sim names are "<conf> YYYY-MM-DD HH", score files before September 2025 use underscores instead of spaces
SIM_NAME = re.compile(r"^(?P<conf>.+)[ _](?P<date>\d{4}-\d{2}-\d{2})[ _](?P<hour>\d{2})$")


@dataclass
class LegacyRun:
    """ Legacy output files of one verification run """
    name: str
    start: dt.datetime
    duration: int
    subdomain: str
    scores_csv: Optional[str] = None
    percentiles_csv: Optional[str] = None
    fss_pickle: Optional[str] = None

    @property
    def files(self):
        return [path for path in (self.scores_csv, self.percentiles_csv, self.fss_pickle) if path]


def find_legacy_runs(scores_dir, data_dir, name=None):
    """ Group the legacy output files in scores_dir and data_dir by verification run.
    With name, only runs of this experiment (--name of the legacy runs) are returned. """
    prefix = None if name is None else (f"{name.rstrip('_')}_" if name else "")
    runs = {}
    searches = [(scores_dir, [("scores_csv", SCORES_CSV), ("percentiles_csv", PERCENTILES_CSV)]),
                (data_dir, [("fss_pickle", FSS_PICKLE)])]
    for directory, patterns in searches:
        if not os.path.isdir(directory):
            logger.warning(f"Directory {directory} not found")
            continue
        for file_name in sorted(os.listdir(directory)):
            for kind, pattern in patterns:
                match = pattern.match(file_name)
                if match is None or (prefix is not None and match["name"] != prefix):
                    continue
                key = (match["name"], match["date"], int(match["duration"]), match["subdomain"])
                run = runs.setdefault(key, LegacyRun(
                    name=match["name"], start=dt.datetime.strptime(match["date"], "%Y%m%d_%H"),
                    duration=int(match["duration"]), subdomain=match["subdomain"]))
                path = os.path.join(directory, file_name)
                if getattr(run, kind):
                    logger.warning(f"Ignoring {path}, using {getattr(run, kind)} for the same run")
                else:
                    setattr(run, kind, path)
                break
    return [runs[key] for key in sorted(runs)]


def run_parameter(parameter, duration):
    """ main.py verifies precip2 instead of precip for accumulations of 24 hours or more """
    return "precip2" if parameter == "precip" and duration >= 24 else parameter


def output_path(run, region, parameter, output_dir):
    """ Path of the NetCDF score file of a legacy run, named like the files of io_scores.py """
    file_name = (f"{run.name}{run_parameter(parameter, run.duration)}_scores_{run.start:%Y%m%d_%H}UTC_"
                 f"{run.duration:02d}h_acc_{region}_{run.subdomain}.nc")
    return os.path.join(output_dir, file_name)


def convert_run(run, region, parameter="precip", verif_dataset=None):
    """ Read the legacy output files of one run and build its NetCDF score dataset """
    parameter = run_parameter(parameter, run.duration)
    rows = _read_csv(run.scores_csv) if run.scores_csv else pd.DataFrame()
    percentile_rows = _read_csv(run.percentiles_csv) if run.percentiles_csv else None
    percentiles = list(range(101)) if percentile_rows is not None else DEFAULT_PERCENTILES

    # one dict per forecast with name, conf, lead_hours, scores, statistics
    # (max, mean, percentile values of the field) and fss (data frames)
    obs_statistics = None
    forecasts = []
    for index, row in rows.iterrows():
        # the observation is the first row since field statistics are written to the score file
        if index == 0 and "maximum" in rows.columns:
            obs_statistics = _statistics(row, percentile_rows, percentiles)
            continue
        identity = _identity(row)
        if identity is None:
            logger.warning(f"{run.scores_csv}: cannot determine conf and init time of {row['name']}, skipping it")
            continue
        conf, init, pseudo = identity
        forecasts.append({
            "name": str(row["name"]),
            "conf": _output_conf(conf, pseudo),
            "lead_hours": _lead_hours(init, run.start),
            "scores": {name: row[name] for name, _, _ in SCALAR_SCORES if name in rows.columns},
            "statistics": _statistics(row, percentile_rows, percentiles),
            "fss": {},
        })
    if run.fss_pickle:
        _add_fss(run, forecasts)
        _check_thresholds(run, forecasts, parameter)

    created = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    attrs = {
        "title": "Panelification verification scores",
        "schema_version": SCHEMA_VERSION,
        "experiment_name": run.name.rstrip("_"),
        "parameter": parameter,
        "parameter_units": PARAMETER_UNITS.get(parameter, ""),
        "verif_dataset": verif_dataset,
        "region": region,
        "subdomain": run.subdomain,
        "accumulation_hours": run.duration,
        "valid_start": run.start.isoformat(),
        "valid_end": (run.start + dt.timedelta(hours=run.duration)).isoformat(),
        "source": f"legacy panelification output, converted by convert_legacy_output.py ({_code_version()})",
        "converted_from": " ".join(os.path.basename(path) for path in run.files),
        "history": f"{created} {' '.join(sys.argv)}",
        "created": created,
    }
    return _build_dataset(forecasts, obs_statistics, percentiles, run, attrs)


def write_score_file(ds, path):
    """ Write a score dataset like io_scores.py: compressed, FSS arrays as float32 and
    under a temporary name that is renamed once the file is complete """
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    fss_variables = {name for name, _ in FSS_ARRAYS + FSSP_ARRAYS}
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
    logger.info(f"Written {path}")
    return path


def _build_dataset(forecasts, obs_statistics, percentiles, run, attrs):
    """ Place the forecasts on the (conf, lead_hours) grid of the score file layout,
    combinations without a forecast are NaN """
    units = attrs["parameter_units"]
    positions = [(fc["conf"], fc["lead_hours"]) for fc in forecasts]
    duplicates = [pos for pos, count in Counter(positions).items() if count > 1]
    if duplicates:
        names = [fc["name"] for fc, pos in zip(forecasts, positions) if pos in duplicates]
        raise ValueError(f"Several forecasts have the same conf and lead time: {names}")
    confs = sorted({conf for conf, _ in positions})
    leads = sorted({lead for _, lead in positions})
    indices = [(confs.index(conf), leads.index(lead)) for conf, lead in positions]
    grid_shape = (len(confs), len(leads))

    data_vars = {}
    for name, long_name, var_units in SCALAR_SCORES:
        if not any(name in fc["scores"] for fc in forecasts):
            continue
        values = np.full(grid_shape, np.nan)
        for (ii, jj), fc in zip(indices, forecasts):
            if name in fc["scores"]:
                values[ii, jj] = fc["scores"][name]
        var_attrs = {"long_name": long_name, "units": units if var_units == "parameter" else var_units}
        if name == "d90":
            values[values == D90_UNDEFINED] = np.nan
            var_attrs["comment"] = ("half window width in grid points of the ~1 km verification grid, "
                                    "NaN where no displacement could be determined")
        data_vars[name] = (SCORE_DIMS, values[np.newaxis, :, np.newaxis, :], var_attrs)

    forecast_max = np.full(grid_shape, np.nan)
    forecast_mean = np.full(grid_shape, np.nan)
    forecast_percentile = np.full(grid_shape + (len(percentiles),), np.nan)
    for (ii, jj), fc in zip(indices, forecasts):
        if fc["statistics"] is not None:
            forecast_max[ii, jj], forecast_mean[ii, jj], forecast_percentile[ii, jj] = fc["statistics"]
    obs_max, obs_mean, obs_percentile = obs_statistics or (np.nan, np.nan, np.full(len(percentiles), np.nan))
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
        "obs_percentile": (obs_dims + ("percentile",),
                           np.asarray(obs_percentile, dtype=float)[np.newaxis, np.newaxis, :],
                           {"long_name": "percentiles of the observed field", "units": units}),
    })

    coords = {
        "valid_time": ("valid_time", np.array([run.start], dtype="datetime64[ns]"),
                       {"long_name": "start of the accumulation window"}),
        "conf": ("conf", np.array(confs, dtype=str), {"long_name": "model configuration"}),
        "subdomain": ("subdomain", np.array([run.subdomain], dtype=str),
                      {"long_name": "verification subdomain"}),
        "lead_hours": ("lead_hours", np.array(leads, dtype=np.int32),
                       {"long_name": "lead time at the start of the accumulation window", "units": "h",
                        "comment": "init time = valid_time - lead_hours"}),
        "percentile": ("percentile", np.array(percentiles, dtype=np.int32),
                       {"long_name": "percentile of the verified field", "units": "%"}),
    }
    thresholds, windows, fss_vars = _fss_arrays(forecasts, indices, grid_shape, FSS_ARRAYS, "threshold")
    if fss_vars:
        coords["threshold"] = ("threshold", thresholds, {"long_name": "FSS threshold", "units": units})
        coords["window"] = ("window", windows, {
            "long_name": "FSS window width", "units": "grid points",
            "comment": "the verification grid spacing is about 1 km"})
        data_vars.update(fss_vars)
    pct_thresholds, _, fssp_vars = _fss_arrays(forecasts, indices, grid_shape, FSSP_ARRAYS, "pct_threshold")
    if fssp_vars:
        coords["pct_threshold"] = ("pct_threshold", pct_thresholds, {
            "long_name": "FSS percentile threshold", "units": "%"})
        data_vars.update(fssp_vars)

    return xr.Dataset(data_vars, coords=coords, attrs={key: value for key, value in attrs.items() if value is not None})


def _fss_arrays(forecasts, indices, grid_shape, arrays, row_dim):
    """ Place the FSS data frames of all forecasts on the (conf, lead_hours) grid,
    without the dummy threshold rows. Returns the row and window values and the
    data variables, or no variables if no forecast has these FSS data. """
    reference_name = arrays[0][0]
    reference = next((fc["fss"][reference_name] for fc in forecasts if reference_name in fc["fss"]), None)
    if reference is None:
        return None, None, {}
    keep = np.asarray(reference.index, dtype=float) < DUMMY_THRESHOLD
    rows = np.asarray(reference.index)[keep]
    windows = np.asarray(reference.columns)
    data_vars = {}
    for name, attrs in arrays:
        values = np.full(grid_shape + (rows.size, windows.size), np.nan)
        for (ii, jj), fc in zip(indices, forecasts):
            frame = fc["fss"].get(name)
            if frame is None:
                continue
            if not (frame.index.equals(reference.index) and frame.columns.equals(reference.columns)):
                raise ValueError(f"{fc['name']}: thresholds or windows of {name} differ from the other forecasts")
            values[ii, jj] = frame.to_numpy(dtype=float)[keep, :]
        data_vars[name] = (SCORE_DIMS + (row_dim, "window"), values[np.newaxis, :, np.newaxis, ...], attrs)
    return rows, windows, data_vars


def _read_csv(path):
    """ Score files are separated by ; since September 2025 and by , before. The
    round trip float parser reads the written values exactly. """
    with open(path) as f:
        header = f.readline()
    return pd.read_csv(path, sep=";" if ";" in header else ",", float_precision="round_trip")


def _identity(row):
    """ conf, init time and pseudo member flag of a forecast in a legacy score file, None if unknown """
    if "conf" not in row or "init" not in row:
        return _identity_from_name(str(row["name"]))
    try:
        init = dt.datetime.fromisoformat(str(row["init"]))
    except ValueError:
        return None
    conf = str(row["conf"])
    # ensemble mean and median pseudo members are named like their conf, without init time
    pseudo = conf == str(row["name"]) and conf.endswith(("_mean", "_median"))
    return conf, init, pseudo


def _identity_from_name(name):
    """ conf and init time from a sim name, None if the name has no init time """
    match = SIM_NAME.match(name)
    if match is None:
        return None
    return match["conf"], dt.datetime.strptime(f"{match['date']} {match['hour']}", "%Y-%m-%d %H"), False


def _output_conf(conf, pseudo):
    """ Ensemble pseudo members carry the ensemble init time in their name, strip it
    so the conf is the same for all init times (as io_scores.py does) """
    return re.sub(r'_\d{8}_\d{2}(?=_[^_]+$)', '', conf) if pseudo else conf


def _lead_hours(init, start):
    """ Lead time in whole hours at the start of the accumulation window """
    return int(round((start - init).total_seconds() / 3600.))


def _statistics(row, percentile_rows, percentiles):
    """ (max, mean, percentile values) of the field of a score file row, None if they were not written """
    maximum = float(row.get("maximum", np.nan))
    mean = float(row.get("average", np.nan))
    if percentile_rows is not None:
        match = percentile_rows[percentile_rows["name"] == row["name"]]
        columns = [f"{p}th" for p in percentiles]
        values = match.iloc[0][columns].to_numpy(dtype=float) if len(match) else np.full(len(percentiles), np.nan)
    else:
        values = np.array([row.get(f"{p}th", np.nan) for p in percentiles], dtype=float)
    if np.isnan(maximum) and np.isnan(mean) and np.isnan(values).all():
        return None
    return maximum, mean, values


def _add_fss(run, forecasts):
    """ Attach the FSS data frames of the legacy pickle to the forecasts, forecasts
    missing in the score file are added if their name contains the init time """
    by_name = {fc["name"]: fc for fc in forecasts}
    # pd.read_pickle also reads pickles written with pandas < 2, which plain pickle cannot
    for key, frames in pd.read_pickle(run.fss_pickle).items():
        forecast = by_name.get(key) or by_name.get(key.replace(" ", "_"))
        if forecast is None:
            identity = _identity_from_name(key)
            if identity is None:
                logger.warning(f"{run.fss_pickle}: cannot determine conf and init time of {key}, skipping it")
                continue
            conf, init, _ = identity
            forecast = {"name": key, "conf": conf, "lead_hours": _lead_hours(init, run.start),
                        "scores": {}, "statistics": None, "fss": {}}
            forecasts.append(forecast)
        forecast["fss"] = {name: frames[name] for name, _ in FSS_ARRAYS + FSSP_ARRAYS if frames.get(name) is not None}


def _fss_thresholds(parameter, duration):
    """ FSS thresholds of a parameter, copied from parameter_settings.py, None if unknown """
    thresholds = {
        'precip': [0.1, 1., 5., 10., 25., 35., 50., 75., 100., 99999.],
        'precip2': [1.0, 5., 10., 20., 50., 100., 150., 200., 250., 99999.],
        'precip3': [5.0, 10., 20., 50., 100., 150., 200., 300., 400., 99999.],
        'sunshine': list(np.arange(0., 1., 1/6.)) + [999999],
        'hail': [1, 2, 5, 10, 25, 35, 50, 75, 100, 99999],
        'gusts': [5, 10, 15, 20, 25, 30, 40, 50, 70, 99999],
        'lightning': [0.1*x for x in [1, 2, 5, 10, 25, 35, 50, 75, 100]] + [99999],
        'cma': [x + 0.5 for x in range(duration)] + [99999],
    }
    return thresholds.get(parameter)


def _check_thresholds(run, forecasts, parameter):
    """ Warn if the FSS thresholds do not belong to the parameter, e.g. when --parameter is wrong """
    frame = next((fc["fss"]["fss"] for fc in forecasts if "fss" in fc["fss"]), None)
    expected = _fss_thresholds(parameter, run.duration)
    if frame is None or expected is None:
        return
    found = np.asarray(frame.index, dtype=float)
    if found.shape != (len(expected),) or not np.allclose(found, np.asarray(expected, dtype=float)):
        logger.warning(f"{run.fss_pickle}: FSS thresholds {found.tolist()} differ from the thresholds of "
                       f"parameter {parameter} {list(expected)}, check --parameter")


@functools.lru_cache(maxsize=None)
def _code_version():
    """ git describe of the directory of this script, "unknown" outside a git checkout """
    try:
        result = subprocess.run(["git", "describe", "--always", "--dirty"],
                                cwd=os.path.dirname(os.path.abspath(__file__)),
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    version = result.stdout.strip()
    return version if result.returncode == 0 and version else "unknown"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert legacy panelification score CSV files and FSS pickles to NetCDF score files")
    parser.add_argument('--region', type=str, required=True,
        help = 'region of the legacy runs, not stored in the legacy files but part of the NetCDF file name')
    parser.add_argument('--parameter', type=str, default='precip',
        help = 'verified parameter of the legacy runs, precip becomes precip2 for accumulations of 24 hours or more as in main.py')
    parser.add_argument('--verif_dataset', type=str, default=None,
        help = 'verification dataset of the legacy runs, stored as metadata if given')
    parser.add_argument('--name', '-n', type=str, default=None,
        help = 'only convert runs with this name (--name of the legacy runs)')
    parser.add_argument('--scores_dir', type=str, required=True,
        help = 'directory of the legacy score CSV files (SCORES)')
    parser.add_argument('--data_dir', type=str, required=True,
        help = 'directory of the legacy FSS pickles (DATA)')
    parser.add_argument('--output_dir', type=str, default=None,
        help = 'directory for the NetCDF score files, default: the directory of the legacy score files')
    parser.add_argument('--overwrite', action='store_true',
        help = 'replace existing NetCDF score files')
    parser.add_argument('--dry_run', action='store_true',
        help = 'only list the conversions, do not write any files')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    runs = find_legacy_runs(args.scores_dir, args.data_dir, args.name)
    logger.info(f"Found {len(runs)} legacy runs")
    converted, skipped, failed = 0, 0, 0
    for run in runs:
        path = output_path(run, args.region, args.parameter, args.output_dir or args.scores_dir)
        if os.path.exists(path) and not args.overwrite:
            logger.info(f"Skipping {path}, it exists already (use --overwrite to replace it)")
            skipped += 1
        elif args.dry_run:
            logger.info(f"Would convert {', '.join(run.files)} to {path}")
        else:
            try:
                write_score_file(convert_run(run, args.region, args.parameter, args.verif_dataset), path)
                converted += 1
            except Exception:
                logger.exception(f"Converting {', '.join(run.files)} failed")
                failed += 1
    logger.info(f"Converted {converted}, skipped {skipped}, failed {failed} of {len(runs)} legacy runs")
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
