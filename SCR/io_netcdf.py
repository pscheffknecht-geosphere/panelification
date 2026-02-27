import numpy as np
import netCDF4 as nc
import logging
import datetime as dt
import os
import re


import datetime as dt

import logging
logger = logging.getLogger(__name__)


def read_data_netcdf(nc_file_path, parameter, valid_time, **kwargs):
    """
    Reads data from a NetCDF file, fixed to work with daily timesteps and
    robustly handle common coordinate variable names.
    """
    parameter = kwargs.get("netcdf_parameter", "precipitation")
    get_lonlat_data = kwargs.get("get_lonlat_data", False)
    lead_start = kwargs.get("lead_start", 0)
    lead_end = kwargs.get("lead_end")
    accumulated = kwargs.get("accumulated", False)
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


def read_inca_plus_netcdf(nc_file_path, lead_start, lead_end):
    logger.debug(f"Reading time steps {lead_start} to {lead_end} from file {nc_file_path}")
    read_fac = 1
    with nc.Dataset(nc_file_path, 'r') as ds:
        time = ds.variables["time"][:]
        if time.size == 193:
            read_fac = 4
            logger.debug(f"Time has size {time.size}, 15 minute file.")
        elif time.size == 49:
            read_fac = 1
            logger.debug(f"Time has size {time.size}, hourly file.")
        else:
            logger.error(f"Unknown time coordinate length ({time.size}), expected 49 (hourly) or 193 (15 minutes)...")
            return None
        idx_start = 1 + read_fac * lead_start
        idx_end = 1 + read_fac * lead_end
        t1 = dt.datetime(1961, 1, 1) + dt.timedelta(seconds=time[idx_start])
        t2 = dt.datetime(1961, 1, 1) + dt.timedelta(seconds=time[idx_end-1]) # prevent off-by-one error, because indexing start:end will give start, ..., end-1
        logger.info(f"Reading {nc_file_path}, indices [{idx_start}:{idx_end}, :, :], corresponding to {t1} and {t2}")
        tmp_rr = ds.variables["RR"][idx_start:idx_end, :, :].sum(axis=0)
        lon = ds.variables['lon'][:]
        lat = ds.variables['lat'][:]
    return lon, lat, tmp_rr



def read_HungaroMet_netcdf(nc_file_paths, netcdf_variable_name): 
    # this function is for the Total Cloud Cover variable in our AROME netcdfs 
    
   
   # fname = os.path.basename(nc_file_path)

    # Fájlnévből időpont kinyerése, pl. chra20250907_0000+01800
    #match = re.search(r"(\d{8})_(\d{4})\+(\d{2})(\d{3,4})", fname)

    #date_str, init_str, lead_h_str, lead_m_str = match.groups()
    #init_hour = int(init_str[:2])

    # this part if i understood, is unnecessary since i set init_interval =24 in custom_experience? -->
    #if init_hour != 0:
        #logger.info(f"Not a 00UTC init file: {fname}")
       # return None

    # Időpontok
    #init_time = dt.datetime.strptime(date_str + init_str, "%Y%m%d%H%M")
    #lead_hours = int(lead_h_str)
    #lead_minutes = int(lead_m_str)
   # valid_time = init_time + dt.timedelta(hours=lead_hours, minutes=lead_minutes)



    first = True

    for nc_file_path in nc_file_paths:

        with nc.Dataset(nc_file_path, "r") as ds:
            data_tmp = ds.variables[netcdf_variable_name][0, :, :]
            data_tmp = np.where(data_tmp == ds.variables[netcdf_variable_name]._FillValue, np.nan, data_tmp)
            threshold = 0.2
            data_tmp = np.where(data_tmp >= threshold, 1, 0)
            if first:
                ny = ds.dimensions["maxLatPoints"].size
                nx = ds.dimensions["maxLonPoints"].size
                lat0 = float(ds.variables["La1"][0])
                lon0 = float(ds.variables["Lo1"][0])
                dx   = float(ds.variables["Dx"][0])
                dy   = float(ds.variables["Dy"][0])

                lats = np.arange(lat0, lat0 - ny * dy, - dy)[:ny]
                lons = np.arange(lon0, lon0 + nx * dx, dx)[:nx]
                lon2d, lat2d = np.meshgrid(lons, lats)
                data = data_tmp
                first = False
        
            
            else: # máskülönben adja össze az értékekeket a kért időablak mentén 
            #data = ds.variables[netcdf_variable_name][0, :, :]
            #data = np.where(data == ds.variables[netcdf_variable_name]._FillValue, np.nan, data)
            #data += np.where(data == ds.variables[netcdf_variable_name]._FillValue, np.nan, data)
                data += data_tmp

    return lon2d, lat2d, data
