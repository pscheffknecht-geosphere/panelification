import pygrib
from grib_handle_check import find_grib_handles
import numpy as np
import pyresample

import logging
logger = logging.getLogger(__name__)


def data_sum(tmp_data_list):
    if len(tmp_data_list) > 1:
        return np.sum(np.array([read_values_from_grib_field(x) for x in tmp_data_list]), axis=0)
    else:
        return read_values_from_grib_field(tmp_data_list[0])


def data_norm(tmp_data_list):
    if not len(tmp_data_list) == 2:
        raise ValueError("tmp_data_list has wrong lenght, must be 2 but is "+str(len(tmp_data_list)))
    else:
        return np.sqrt(read_values_from_grib_field(tmp_data_list[0]) ** 2 + read_values_from_grib_field(tmp_data_list[1]) ** 2)


def read_list_of_fields(f, handles):
    """ takes and unpacks a dictionary of grib handles, then reads all
    field and returns the sum"""
    ret_data = []
    for handle in handles:
        ret_data.append(f.select(**handle)[0])
    return ret_data


def get_lonlat_fallback(grb):
    Nx = None
    Ny = None
    lll = None
    try:
        Nx, Ny = grb['Nx'], grb['Ny']
        lon = grb.longitudes.reshape((Ny, Nx))
        lat = grb.latitudes.reshape((Ny, Nx))
        logger.debug(f"Nx: {Nx}, Ny: {Ny}")
        logger.debug(f"lat: {lat}\nlon: {lon}")
        logger.debug(f"lat.shape: {lat.shape}")
    except:
        logger.critical("Fallback failed on unknown grid type, exiting!!!")
        raise
    return lon, lat


def read_values_from_grib_field(grb):
    if grb['gridType'] == "lambert_lam": # new deode experiments
        return grb.values
    elif grb['gridType'] == "reduced_gg":
        # TODO: workaround for Austria, make this take values from the region!!!
        grb.expand_grid(False)
        data1d, lat1d, lon1d = grb.data()
        if lon1d.max() > 180.:
            lon1d -= 360.
        logger.debug(f"Nx: {lon1d.shape}, Ny: {lat1d.shape}")
        logger.debug(f"lat: {lat1d}\nlon: {lon1d}")
        lo = np.arange(-10., 35.001, 0.025)
        la = np.arange(30., 75.001, 0.025)
        llo, lla = np.meshgrid(lo, la)
        targ_def = pyresample.geometry.SwathDefinition(llo, lla)
        orig_def = pyresample.geometry.SwathDefinition(lon1d, lat1d)
        data = pyresample.kd_tree.resample_nearest(orig_def, data1d, targ_def, reduce_data=False, radius_of_influence=25000)
        return data
    else:
        return grb.data()[0]


def calc_data(tmp_data_list, parameter):
    calc_funcs = {
       "precip" : data_sum,
       "precip2" : data_sum,
       "precip3" : data_sum,
       "sunshine": data_sum,
       "lightning": data_sum,
       "hail": data_sum,
       "gusts" : data_norm
       }
    return calc_funcs[parameter](tmp_data_list)


def read_data_grib(grib_file_path, parameter, lead, **kwargs): #get_lonlat_data=False):
    """ calls the grib handle check and returns fields with or without lon and lat data,
    depending on selection
    
    Returns:
    lon .............. 2D numpy.ndarray
    lat .............. 2D numpy.ndarray
    tmp_data_field ... 2D or 3D numpy.ndarray"""
    with pygrib.open(grib_file_path) as f:
        if "grib_handles" in kwargs.keys():
            grib_handles = kwargs["grib_handles"]
        else:
            grib_handles = find_grib_handles(f, parameter, lead)
        logger.debug("Getting {:s} from file {:s}".format(repr(grib_handles), grib_file_path))
        tmp_data_list = read_list_of_fields(f, grib_handles)
    tmp_data_field = calc_data(tmp_data_list, parameter)
    tmp_data_field = np.where(tmp_data_field>=9000., np.nan, tmp_data_field)
    logger.debug(f"DATA FROM {grib_file_path} parameter {parameter}:")
    logger.debug(f"Type: {type(tmp_data_field)}")
    logger.debug(f"Min: {tmp_data_field.min()}")
    logger.debug(f"Max: {tmp_data_field.max()}")
    logger.debug(f"Sample:")
    logger.debug(tmp_data_field)
    if "get_lonlat_data" in kwargs:
        get_lonlat_data = kwargs["get_lonlat_data"]
    else:
        get_lonlat_data = False
    if get_lonlat_data: #TODO: MOVE THIS SOMEWHERE ELSE
        if tmp_data_list[0]['gridType'] == "lambert_lam":
            logger.debug("gridType lambert_lam detected, going to fallback!")
            lon, lat = get_lonlat_fallback(tmp_data_list[0])
        elif tmp_data_list[0]['gridType'] == "reduced_gg":
            logger.debug("gridType reduced_gg detected, making own!")
            lo = np.arange(-10., 35.001, 0.025)
            la = np.arange(30., 75.001, 0.025)
            lon, lat = np.meshgrid(lo, la)   
        elif tmp_data_list[0]['gridType'] == "unstructured_grid":
            logger.debug("gridType unstructured_grid detected, making own!")
            lo = np.arange(-5., 20.001, 0.0125)
            la = np.arange(44., 51.001, 0.0125)
            lon, lat = np.meshgrid(lo, la)   
        else:
            lat, lon = tmp_data_list[0].latlons()
        if lon.max() > 180.:
            lon = np.where(lon > 180., lon - 360., lon)
        return lon, lat, tmp_data_field
    else:
        return tmp_data_field


### SPECIAL FUNCTIONS ################
# functinos down here are reserved for special cases, ideally this part would be empty
# but we don't live in an ideal world

def get_inca_rain_accumulated(mod):
    grb = pygrib.open(mod.end_file)
    idx_start = 4 * mod.lead + 1
    idx_end = 4 * mod.lead_end + 1
    first = True
    for idx in range(idx_start, idx_end + 1):
        if first:
            rr, lat, lon = grb[idx].data()
            first = False
        else:
            rr_, _, _ = grb[idx].data()
            rr += rr_
    return lon, lat, rr