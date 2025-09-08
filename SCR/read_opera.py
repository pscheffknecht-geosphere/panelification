import h5py
import numpy as np
import pyproj
import datetime as dt
from misc import loop_datetime

import logging
logger = logging.getLogger(__name__)

# returns data field in units from ODIM HDF5
# OPERA GRID
#     LL_lat = 31.746215319325056
#     LL_lon = -10.434576838640398
#     LR_lat = 31.98765027794496
#     LR_lon = 29.421038635578032
#     UL_lat = 67.02283275830867
#     UL_lon = -39.5357864125034
#     UR_lat = 67.62103710275053
#     UR_lon = 57.81196475014995
#     projdef = +proj=laea +lat_0=55.0 +lon_0=10.0 +x_0=1950000.0 +y_0=-2100000.0 +units=m +ellps=WGS84
#     xscale = 2000.0
#     xsize = 1900
#     yscale = 2000.0
#     ysize = 2200


def OPERA_grid():
    # NEW VALUES FOUND USING MINIMIZATION OF CORNER ERROR
    myproj = pyproj.Proj("""+proj=laea +lat_0=55.0 +lon_0=10.0 +x_0=1950000.0 +y_0=+2300000.0 +units=m +ellps=WGS84""")
    NX=1900
    NY=2200
    # NEW VALUES FOUND USING MINIMIZATION OF CORNER ERROR
    X=np.arange(NX) * 2001.0888671875
    Y=np.arange(NY) * 2000.90625
    XX,YY=np.meshgrid(X,Y)
    lon_OPERA,lat_OPERA=myproj(XX,YY,inverse=True)
    return lon_OPERA,lat_OPERA


# def read_from_hdf(filename):
#     # open file and read data field
#     logger.info(f"Reading {filename}")
#     h5file=h5py.File(filename,"r")
#     dataset=h5file['dataset1']
#     datagroup=dataset['data1']
#     data=np.array(datagroup['data'],dtype=float)
#     # read parameters
#     whatgroup=dataset['what']
#     gain=whatgroup.attrs.get('gain')
#     offset=whatgroup.attrs.get('offset')
#     nodata=whatgroup.attrs.get('nodata')
#     undetect=whatgroup.attrs.get('undetect')
#     # field values to units, undetect set to zero, nodata is set to np.nan
#     logger.debug(f"HDF OPERA gain = {gain}")
#     logger.debug(f"HDF OPERA offset = {offset}")
#     logger.debug(f"HDF OPERA nodata = {nodata}")
#     logger.debug(f"HDF OPERA undetect = {undetect}")
#     data[data==undetect]=0
#     data[data==nodata]=np.nan
#     data=data*gain+offset
#     return data

def read_from_hdf(filename):
    # open file and read data field
    logger.info(f"Reading {filename}")
    h5file=h5py.File(filename,"r")
    dataset=h5file['dataset1']
    datagroup=dataset['data1']
    data=np.array(datagroup['data'],dtype=float)
    data[data<0.] = 0.
    return data


def read_OPERA(data_list, start_date, end_date, args):
    duration = end_date - start_date
    dim = int(duration.total_seconds() / 900)
    data = np.zeros((dim, 2200, 1900))
    idx = 0
    read_dt = dt.timedelta(minutes=60)
    for read_opera_date in loop_datetime(start_date + dt.timedelta(minutes=0), end_date, read_dt):
        dat_str = read_opera_date.strftime("%Y%m%d%H%M")
        year, month, day, hour = read_opera_date.year, read_opera_date.month, read_opera_date.day, read_opera_date.hour
        opera_file_name = f"/scratch/snh02/DE_observations/opera/{year}/{month:02d}/{day:02d}/T_PASH22_C_EUOC_{year}{month:02d}{day:02d}{hour:02d}0000.hdf"
        logger.info("reading OPERA for {:s} ".format(read_opera_date.strftime("%Y-%m-%d %H:%M")))
        data[idx, :, :] = read_from_hdf(opera_file_name)
        idx += 1
    lon, lat = OPERA_grid()
    tmp_precip = np.nansum(data, 0)
    tmp_precip = np.where(tmp_precip>2000., np.nan, tmp_precip)
    tmp_precip = np.flip(tmp_precip, 0)
    logger.info("OPERA max precip: {:f}".format(
        np.nanmax(tmp_precip)))
    data_list.insert(0,{
        'conf' : 'OPERA',
        'type' : 'obs',
        'name' : 'OPERA',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data': tmp_precip})
    return data_list
