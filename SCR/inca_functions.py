import pyresample
import os
import numpy as np
import pygrib
from datetime import datetime
from datetime import timedelta as dt
import bring_obs_1hACUM as bO
import pyproj
import gzip
import glob
from misc import loop_datetime
from model_parameters import verification_subdomains, inca_ana_paths
import grib_handles
from netCDF4 import Dataset
import urllib.request

import logging
logger = logging.getLogger(__name__)

def get_subdomain_grid(lon, lat, RR, limits):
    dists_min = (lon - limits[0])**2 + (lat - limits[2])**2
    dists_max = (lon - limits[1])**2 + (lat - limits[3])**2
    idx_min = np.where(dists_min==dists_min.min())
    idx_max = np.where(dists_max==dists_max.min())
    # idx vars end up as list of arrays, so use [0]
    lon_subdomain = lon[idx_min[0][0]:idx_max[0][0],idx_min[1][0]:idx_max[1][0]] 
    lat_subdomain = lat[idx_min[0][0]:idx_max[0][0],idx_min[1][0]:idx_max[1][0]]
    RR_subdomain = RR[idx_min[0][0]:idx_max[0][0],idx_min[1][0]:idx_max[1][0]]
    return lon_subdomain, lat_subdomain, RR_subdomain


def resample_sim(sim, obs, limits, destination_grid="OBS"):
    if destination_grid == "MODEL":
        old_grid_sim = obs
        new_grid_sim = sim
    elif destination_grid == "OBS":
        old_grid_sim = sim
        new_grid_sim = obs
    # the parameter that is already on the destination grid will NOT get resampled
    # it only gets cut out in get_subdomain_grid()
    lon_subdomain, lat_subdomain, RR_not_regridded = get_subdomain_grid(new_grid_sim['lon'], 
        new_grid_sim['lat'], new_grid_sim['precip_data'], limits)
    targ_def = pyresample.geometry.SwathDefinition(lons=lon_subdomain, lats=lat_subdomain)
    orig_def = pyresample.geometry.SwathDefinition(lons=old_grid_sim['lon'], lats=old_grid_sim['lat'])
    RR_regridded = pyresample.kd_tree.resample_gauss(orig_def, old_grid_sim['precip_data'],
        targ_def, radius_of_influence=25000, neighbours=20,
        sigmas=250000, fill_value=None)
    if destination_grid=="OBS":
        sim['sim_param_resampled'] = RR_regridded
        sim['obs_param_resampled'] = RR_not_regridded
    elif destination_grid=="MODEL":
        sim['sim_param_resampled'] = RR_not_regridded
        sim['obs_param_resampled'] = RR_regridded
    sim['lon_subdomain'] = lon_subdomain
    sim['lat_subdomain'] = lat_subdomain
    return sim


def resample_data(data_list, verification_subdomain, args):
    """
    loop over data_list to resample all sims to INCA grid

    The subdomain is implemented by reducing the resampling INCA grid to within
    the limits of the desired subdomain. This automatically reduces the sampled
    area in resample_sim()
    """
    logging.info("Resampling to {}!".format(verification_subdomain))
    if verification_subdomain == 'Custom':
        limits = args.lonlat_limits
        logging.info("""custom corners:
            Longitude from {:5.2f} to {:5.2f}
            Latitude from {:5.2f} to {:5.2f}""".format(*limits))
    else:
        limits = verification_subdomains[verification_subdomain]
    data_list = [resample_sim(sim, data_list[0], limits=limits, destination_grid=args.resample_target) for ii, sim in enumerate(data_list)]
    for sim in data_list:
        p90 = np.percentile(np.copy(sim['sim_param_resampled']), 90) # circumvent numpy bug #21524
        #p90 = np.percentile(sim['sim_param_resampled'], 90)
        sim['rr90'] = np.where(sim['sim_param_resampled'] > p90, 1, 0)
        sim['p90_color'] = 'black' if p90 <= 10. else 'white'
    return data_list

def INCA_grid(INCAplus=False):
    """
    function that returns a meshgrid of latitudes and longitudes
    for plotting INCA data

    usage: lon, lat = INCA_grid()
    """
    if INCAplus:
        myproj=pyproj.Proj("""epsg:31287 +units=m +proj=lcc +lat_1=49 +lat_2=46 +lat_0=47.5 +lon_0=13.33333333333333 +x_0=400000 +y_0=400000 +ellps=bessel +towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +no_defs""")
        NX=701
        NY=431
        X=20000.+np.arange(NX)*1000.
        Y=190000.+np.arange(NY)*1000.
    else:
        myproj=pyproj.Proj("""epsg:31287 +units=km +proj=lcc +lat_1=49 +lat_2=46 +lat_0=47.5 +lon_0=13.33333333333333 +x_0=400000 +y_0=400000 +datum=hermannskogel +no_defs +ellps=bessel +towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232""")
        NX=701
        NY=401
        X=20.+np.arange(NX) #*1000.
        Y=220.+np.arange(NY) #*1000.
    XX,YY=np.meshgrid(X,Y)
    lon_INCA,lat_INCA=myproj(XX,YY,inverse=True)
    logging.debug("############################################################################")
    logging.debug(lon_INCA)
    logging.debug(lon_INCA.min())
    logging.debug(lon_INCA.max())
    logging.debug(lat_INCA)
    logging.debug(lat_INCA.min())
    logging.debug(lat_INCA.max())
    logging.debug("############################################################################")
    return lon_INCA,lat_INCA


def read_INCA(data_list, start_date, end_date, args):
    first=True
    if args.parameter == 'precip' or args.parameter == 'precip2':
        read_dt = dt(hours=1)
        dtype = np.int16
    elif args.parameter == 'sunshine':
        read_dt = dt(minutes=15)
        dtype = np.int32
    elif args.parameter == 'gusts':
        read_dt = dt(minutes=10)
        dtype = np.int16
    read_inca_date = start_date + read_dt
    while read_inca_date <= end_date:
    # for read_inca_date in loop_datetime(start_date + read_dt, end_date + read_dt, read_dt):
        datestring=read_inca_date.strftime("%Y%m%d%H")
        dstr = read_inca_date.strftime("%Y-%m-%d %H:%M")
        logging.info(f"reading inca at {dstr}")
        if "precip" in args.parameter:
            if first:
                var_tmp = bO.bring(datestring, inca_file=None)
                first = False
            else:
                var_tmp = var_tmp + bO.bring(datestring, inca_file=None)
        elif args.parameter == "gusts":
            logging.info("reading INCA gusts")
            inca_file = inca_ana_paths['gusts'].format(
                read_inca_date.strftime("%Y%m%d"),
                read_inca_date.strftime("%H%M"))
            logging.debug(f"reading INCA gusts from {inca_file}")
            f_tmp = bO.bring(datestring, inca_file=inca_file) 
            logger.debug(f_tmp)
            if first:
                var_tmp = f_tmp
                first = False
            else:
                var_tmp = np.where(f_tmp > var_tmp, f_tmp, var_tmp)
        elif args.parameter == "sunshine":
            logging.info("reading INCA sunshine")
            inca_file = inca_ana_paths['sunshine'].format(
                read_inca_date.strftime("%Y%m%d"),
                read_inca_date.strftime("%H%M"))
            logging.debug(inca_file)
            if first:
                var_tmp = 1./3600.*bO.bring(datestring, inca_file=inca_file) 
                first = False
            else:
                var_tmp += 1./3600.*bO.bring(datestring, inca_file=inca_file)
        read_inca_date += read_dt
    lon, lat = INCA_grid()
    data_list.insert(0,{
        'conf' : 'INCA',
        'type' : 'obs',
        'name' : 'INCA',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data': var_tmp})
    logger.debug(data_list[0]["precip_data"])
    logger.debug(data_list[0]["precip_data"].max())
    logger.debug(data_list[0]["precip_data"].min())
    return data_list
    

def read_inca_fc_accum(sim, args):
    inca_file = sim['inca_file']
    k_start, k_end = sim['inca_indices']
    start_date = datetime.strptime(args.start, "%Y%m%d%H")
    logging.info("reading "+sim['name']+" at "+str(start_date))
    end_date = start_date + dt(hours=args.duration)
    if sim['conf'] == 'inca-fc':
        data = read_INCA_BIL(inca_file,twodim=True)
        rr_tmp = np.sum(data[k_start:k_end,:,:], 0)
    elif sim['conf'] == 'inca_plus-fc':
        rr_tmp = read_INCA_plus(inca_file, k_start, k_end)
    return rr_tmp


def read_INCA_BIL(fname, bilfac=100., dom="L", twodim=False, verbose=True, dtype=np.int16):
    """
    With this function an INCA file of "bil" type is read in. It assumes a
    "conversion factor" of 100, and the domain size is 401 * 701 grid
    points. It checks of input file is zipped or not.

    IN: path and name of INCA bil file (gzipped or not)
        (optional:) conversion factor, domain acronym, switch for verbose
                    output and twodimensional return value

    OUT: numpy array with shape (n_levels, 401, 701) or
                                (n_levels, 401 * 701) or None

    TAKEN and MODIFIED from ingmei's inca_plotter
    """


    # check if file exists
    if not glob.glob(fname):
        logging.error("Could not find file: " + fname)
        return None

    if verbose:
        if twodim == True:
            logging.debug("  Data is returned as array with dimensions " + \
                      "(n_level, nj, ni)")
        else:
            logging.debug("  Data is returned as array with dimensions " + \
                      "(n_level, nj * ni)")

    # as this is a bil file, the domain is per definition L:
    if ( dom == "L" ):
        nx = 701
        ny = 401
    elif ( dom == "ALBINA" ):
        nx = 701
        ny = 431
    elif ( dom == "AT" ):
        nx = 601
        ny = 351
    elif ( dom == "SK" ):
        nx = 501
        ny = 301
    elif ( dom == "CZ" ):
        nx = 531
        ny = 301

    # open file, read data, close file
    if ".gz" in fname:
        with gzip.GzipFile(fname, 'r') as f:
            logging.debug("with gzip.GzipFile...")
            content = np.frombuffer(f.read(), dtype=dtype)/bilfac
    else:
        with open(fname, "r") as f:
            content = np.frombuffer(f.read(), dtype=dtype)/bilfac

    # calculate the number of levels, reshape
    n_levels = int(len(content)/(nx*ny))
    if n_levels > 1:
        if twodim == True:
            content_new = content.reshape(n_levels, ny, nx)
        else:
            content_new = content.reshape(n_levels, nx*ny)
    else:
        if twodim == True:
            content_new = content.reshape(ny, nx)
        else:
            content_new = content

    # return
    return content_new


#{'parameterNumber': 8, 'typeOfGeneratingProcess': 2, 'forecastTime': None}
def read_INCA_plus(inca_file, k_start, k_end):
    try:
        f = pygrib.open(inca_file)
    except:
        logging.error("Could not open "+inca_file)
        return None
    grib_handle = grib_handles.GRIB_indicators['inca_plus-fc']['precip']
    for kk in range(k_start, k_end):
        first = True
        grib_handle['forecastTime'] = kk
        if first:
            rr_tmp = f.select(**grib_handle)[0]
            first = False
        else:
            rr_tmp += f.select(**grib_handle)[0]
    return rr_tmp.values
    

def fetch_inca(month):
    """ fetch INCA netcdf from GeoSphere archive
    example file: https://public.hub.geosphere.at/datahub/resources/inca-v1-1h-1km/filelisting/RR/INCAL_HOURLY_RR_201106.nc"""
    dt_string = month.strftime("%Y%m")
    fetch_file = f"https://public.hub.geosphere.at/datahub/resources/inca-v1-1h-1km/filelisting/RR/INCAL_HOURLY_RR_{dt_string}.nc"
    local_file = f"../OBS/INCA_netcdf/INCAL_HOURLY_RR_{dt_string}.nc"
    logger.info(f"did not find {local_file}")
    logger.info(f"downloading {fetch_file}")
    urllib.request.urlretrieve(fetch_file, local_file)
    return 0


def read_inca_netcdf_archive(data_list, start_date, end_date, args):
    """ read INCA data from netcdf hourly archive"""
    tt = start_date
    # 1. check if all necessary files exist and are up to date:
    fetched_current = False # if current month is found, was it updated?
    rr_tmp = 'None'
    data_tmp = None
    previous_file = None
    this_month = datetime(datetime.now().year, datetime.now().month, 1)
    while tt < end_date:
        tt_str = tt.strftime("%Y%m")
        read_file = f"../OBS/INCA_netcdf/INCAL_HOURLY_RR_{tt_str}.nc"
        if not read_file == previous_file:
            if datetime(tt.year, tt.month, 1) == this_month and not fetched_current:
                fetch_inca(tt)
                fetched_current = True
            elif not os.path.isfile(read_file):
                fetch_inca(tt)
            data_tmp = Dataset(read_file, "r")
            previous_file = read_file
        read_hour = int((tt - datetime(tt.year, tt.month, 1)).total_seconds() / 3600)
        if rr_tmp == 'None':
            rr_tmp = data_tmp.variables['RR'][read_hour, :, :]
        else:
            rr_tmp += data_tmp.variables['RR'][read_hour, :, :]
        tt += dt(hours=1)
    lon, lat = INCA_grid()
    data_list.insert(0,{
        'conf' : 'INCA',
        'type' : 'obs',
        'name' : 'INCA',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data': rr_tmp})
    logger.debug(data_list[0]["precip_data"])
    logger.debug(data_list[0]["precip_data"].max())
    logger.debug(data_list[0]["precip_data"].min())
    return data_list
