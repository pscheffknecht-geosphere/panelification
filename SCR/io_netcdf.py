import numpy as np
import netCDF4 as nc

import logging
logger = logging.getLogger(__name__)

def read_data_netcdf(nc_file_path, parameter, valid_time, **kwargs):
    """
    Reads data from a NetCDF file, fixed to work with daily timesteps and
    robustly handle common coordinate variable names.
    """
    parameter = "precipitation"
    get_lonlat_data = kwargs.get("get_lonlat_data", False)
    with nc.Dataset(nc_file_path, 'r') as ds:
        if parameter not in ds.variables:
            logger.error(f"Parameter '{parameter}' not found in file: {nc_file_path}")
            return None
        var = ds.variables[parameter]
        time_dim_name = [d for d in var.dimensions if d.startswith('time')][0]
        time_var = ds.variables[time_dim_name]
        file_times = nc.num2date(time_var[:], units=time_var.units)
        time_idx = (np.abs(file_times - valid_time)).argmin()
        if np.abs(file_times[time_idx] - valid_time) > dt.timedelta(minutes=30):
            logger.error(f"Requested valid time {valid_time} not found in file {nc_file_path}")
            return None
        data = var[time_idx, ...]
        logger.info(f"The time index is {time_idx} and valid time is {valid_time}")
        if get_lonlat_data:
            lat_names = ['lat', 'latitude', 'lats', 'Latitude']
            lon_names = ['lon', 'longitude', 'lons', 'Longitude']
            lat_var_name = None
            for name in lat_names:
                if name in ds.variables:
                    lat_var_name = name
                    break
            lon_var_name = None
            for name in lon_names:
                if name in ds.variables:
                    lon_var_name = name
                    break
            if not lat_var_name or not lon_var_name:
                logger.error(f"Could not find latitude or longitude variables in {nc_file_path}")
                return None, None, None
            lat = ds.variables[lat_var_name][:]
            lon = ds.variables[lon_var_name][:]
            if lat.ndim == 1 and lon.ndim == 1:
                lon_2d, lat_2d = np.meshgrid(lon, lat)
            else:
                lon_2d, lat_2d = lon, lat

            return lon_2d, lat_2d, data
        else:
            return data
