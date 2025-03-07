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
    #myproj=pyproj.Proj("""epsg:31287 +units=m +proj=lcc +lat_1=49 +lat_2=46 +lat_0=47.5 +lon_0=13.33333333333333 +x_0=400000 +y_0=400000 +ellps=bessel +towgs84=577.326,90.129,463.919,5.137,1.474,5.297,2.4232 +no_defs""")
    myproj=pyproj.Proj("""+proj=laea +lat_0=55.0 +lon_0=10.0 +x_0=1950000.0 +y_0=+2100000.0 +units=m +ellps=WGS84""")
    NX=1900
    NY=2200
    X=np.arange(NX)*2000.
    Y=np.arange(NY)*2000.
    XX,YY=np.meshgrid(X,Y)
    lon_OPERA,lat_OPERA=myproj(XX,YY,inverse=True)
    return lon_OPERA,lat_OPERA


def read_from_hdf(filename):
    # open file and read data field
    h5file=h5py.File(filename,"r")
    dataset=h5file['dataset1']
    datagroup=dataset['data1']
    data=np.array(datagroup['data'],dtype=np.float)
    # read parameters
    whatgroup=dataset['what']
    gain=whatgroup.attrs.get('gain')
    offset=whatgroup.attrs.get('offset')
    nodata=whatgroup.attrs.get('nodata')
    undetect=whatgroup.attrs.get('undetect')
    # field values to units, undetect set to zero, nodata is set to np.nan
    data[data==undetect]=0
    data[data==nodata]=np.nan
    data=data*gain+offset
    return data


def read_OPERA(data_list, start_date, end_date, args):
    duration = end_date - start_date
    dim = int(duration.total_seconds() / 900)
    data = np.zeros((dim, 2200, 1900))
    idx = 0
    read_dt = dt.timedelta(minutes=60)
    for read_opera_date in loop_datetime(start_date + dt.timedelta(minutes=0), end_date, read_dt):
        dat_str = read_opera_date.strftime("%Y%m%d%H%M")
        dat_str2 = read_opera_date.strftime("%Y/%m/%d")
        opera_file_name = f"/scratch/snh02/DE_observations/opera/{dat_str2}/radar/composite/cirrus_nimbus/acrr/pash_acrr_1hr/{dat_str}00.rad.euoc.image.acrr.pash_acrr_1hr.hdf"
        # opera_file_name = f"/ec/res4/scratch/esp0754/auto_obs_db/OPERA/T_PASH22_C_EUOC_{dat_str}00.hdf"
        # opera_file_name = "../OBS/OPERA/ODC.LAM_{:s}_000100.h5".format(read_opera_date.strftime("%Y%m%d%H%M"))
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
