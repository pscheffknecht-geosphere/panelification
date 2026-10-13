"""Write the verified fields of one run to a NetCDF file (--save).

The root group holds the observation and all forecasts resampled to the
verification subdomain, the fields that were scored. They use the dimensions
of the score files of io_scores.py, (valid_time, conf, subdomain, lead_hours)
followed by the grid dimensions (y, x).

With --save_native the fields on their original grids are stored as well, the
observation in the group native_obs and the forecasts of each conf in the
group native_forecasts/<conf> with the dimensions (lead_hours, y, x).

The fields are stored as compressed float32, quantized to FIELD_PRECISION
(least_significant_digit, 0.01 in the units of the parameter).
"""
import os

import numpy as np
import xarray as xr

import io_scores
import parameter_settings
from paths import PAN_DIR_DATA

import logging
logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"

# decimal digits retained by the quantization of the fields, 2 = precision of 0.01
FIELD_PRECISION = 2

FIELD_DIMS = io_scores.SCORE_DIMS + ("y", "x")


def field_file_path(args, start_date, subdomain):
    """ Path of the field file of one verification run """
    start_date_str = start_date.strftime("%Y%m%d_%H")
    file_name = (f"{args.name}{args.parameter}_fields_{start_date_str}UTC_"
                 f"{args.duration:02d}h_acc_{io_scores._region_name(args)}_{subdomain}.nc")
    return os.path.join(PAN_DIR_DATA, file_name)


def save_fields(data_list, start_date, end_date, subdomain, args):
    """ Write the resampled fields of the observation and all forecasts in data_list,
    and with args.save_native also their native fields, to a NetCDF file """
    ds = build_resampled_dataset(data_list, start_date, end_date, subdomain, args)
    groups = [(None, ds, _encoding(ds))]
    if getattr(args, "save_native", False):
        for group, native in build_native_datasets(data_list, start_date, args):
            groups.append((group, native, _encoding(native)))
    path = field_file_path(args, start_date, subdomain)
    io_scores.write_netcdf(path, groups)
    logger.info(f"Fields written to {path}")
    return path


def build_resampled_dataset(data_list, start_date, end_date, subdomain, args):
    """ Observation and forecasts on the verification grid of the subdomain.

    data_list[0] is the observation, all other entries are forecasts. Each
    forecast is placed at (conf, lead_hours), combinations without a forecast
    are NaN."""
    obs = data_list[0]
    forecasts = data_list[1:]
    units = parameter_settings.get_units(args)
    confs, leads, indices = io_scores.forecast_grid(forecasts, start_date)
    obs_field = _as_field(obs["precip_data_resampled"])
    if obs_field.ndim != 2:
        raise ValueError(f"resampled fields must be 2D, got shape {obs_field.shape}")

    forecast_field = np.full((len(confs), len(leads)) + obs_field.shape, np.nan, dtype=np.float32)
    for (ii, jj), sim in zip(indices, forecasts):
        forecast_field[ii, jj] = _as_field(sim["precip_data_resampled"])

    data_vars = {
        "forecast_field": (FIELD_DIMS, forecast_field[np.newaxis, :, np.newaxis, ...],
                           {"long_name": f"forecast {args.parameter} on the verification grid",
                            "units": units}),
        "obs_field": (("valid_time", "subdomain", "y", "x"), obs_field[np.newaxis, np.newaxis, ...],
                      {"long_name": f"observed {args.parameter} on the verification grid",
                       "units": units, "source": str(obs.get("name", ""))}),
    }
    coords = {
        "valid_time": ("valid_time", np.array([start_date], dtype="datetime64[ns]"),
                       {"long_name": "start of the accumulation window"}),
        "conf": ("conf", np.array(confs, dtype=str), {"long_name": "model configuration"}),
        "subdomain": ("subdomain", np.array([subdomain], dtype=str),
                      {"long_name": "verification subdomain"}),
        "lead_hours": ("lead_hours", np.array(leads, dtype=np.int32),
                       {"long_name": "lead time at the start of the accumulation window", "units": "h",
                        "comment": "init time = valid_time - lead_hours"}),
        **_lonlat_coords(obs["lon_resampled"], obs["lat_resampled"], ("y", "x")),
    }
    attrs = {"title": "Panelification verification fields", "schema_version": SCHEMA_VERSION,
             **io_scores.run_attrs(start_date, end_date, subdomain, args),
             "native_fields": int(getattr(args, "save_native", False))}
    return xr.Dataset(data_vars, coords=coords, attrs=io_scores._netcdf_attrs(attrs))


def build_native_datasets(data_list, start_date, args):
    """ (group, dataset) of the observation and of each conf on their original grids.

    The forecasts of one conf are expected on the same grid, if the grid changes
    between lead times the forecasts are split into several groups."""
    units = parameter_settings.get_units(args)
    obs = data_list[0]
    obs_field = _as_field(obs["precip_data"])
    dims = _grid_dims(obs_field.ndim)
    datasets = [("native_obs", xr.Dataset(
        {"obs_field": (dims, obs_field, {"long_name": f"observed {args.parameter} on the native grid",
                                         "units": units, "source": str(obs.get("name", ""))})},
        coords=_lonlat_coords(obs["lon"], obs["lat"], dims)))]

    by_grid = {}
    for sim in data_list[1:]:
        conf = io_scores._output_conf(sim)
        groups = by_grid.setdefault(conf, [])
        for members in groups:
            if _same_grid(members[0], sim):
                members.append(sim)
                break
        else:
            groups.append([sim])

    for conf, groups in sorted(by_grid.items()):
        for nn, members in enumerate(groups):
            members = sorted(members, key=lambda sim: io_scores._lead_hours(sim, start_date))
            leads = [io_scores._lead_hours(sim, start_date) for sim in members]
            field = np.stack([_as_field(sim["precip_data"]) for sim in members])
            dims = _grid_dims(field.ndim - 1)
            name = conf.replace("/", "_") + (f"_grid{nn + 1}" if nn else "")
            if nn:
                logger.warning(f"{conf}: the native grid differs between lead times, "
                               f"lead times {leads} are stored in native_forecasts/{name}")
            ds = xr.Dataset(
                {"forecast_field": (("lead_hours",) + dims, field,
                                    {"long_name": f"forecast {args.parameter} on the native grid",
                                     "units": units})},
                coords={"lead_hours": ("lead_hours", np.array(leads, dtype=np.int32),
                                       {"long_name": "lead time at the start of the accumulation window",
                                        "units": "h", "comment": "init time = valid_time - lead_hours"}),
                        **_lonlat_coords(members[0]["lon"], members[0]["lat"], dims)},
                attrs={"conf": conf})
            datasets.append((f"native_forecasts/{name}", ds))
    return datasets


def _encoding(ds):
    """ Fields are quantized to FIELD_PRECISION digits and compressed, one chunk per 2D field """
    encoding = {}
    for name, var in ds.data_vars.items():
        chunks = tuple(1 if dim in io_scores.SCORE_DIMS else size for dim, size in var.sizes.items())
        encoding[name] = {"dtype": "float32", "zlib": True, "complevel": 4, "shuffle": True,
                          "least_significant_digit": FIELD_PRECISION, "chunksizes": chunks}
    for name in ("lon", "lat"):
        if name in ds.coords:
            encoding[name] = {"zlib": True, "complevel": 4, "_FillValue": None}
    return encoding


def _as_field(data):
    """ float32 array with masked values as NaN """
    return np.ma.filled(np.ma.asarray(data, dtype=np.float32), np.nan)


def _grid_dims(ndim):
    if ndim == 2:
        return ("y", "x")
    if ndim == 1:
        return ("point",)
    raise ValueError(f"fields must be 1D or 2D, got {ndim} dimensions")


def _lonlat_coords(lon, lat, dims):
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    return {"lon": (dims, lon, {"standard_name": "longitude", "units": "degrees_east"}),
            "lat": (dims, lat, {"standard_name": "latitude", "units": "degrees_north"})}


def _same_grid(sim_a, sim_b):
    return all(np.shape(sim_a[key]) == np.shape(sim_b[key]) and
               np.array_equal(sim_a[key], sim_b[key], equal_nan=True) for key in ("lon", "lat"))
