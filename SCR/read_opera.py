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

def read_from_hdf(filename, qi_threshold=0.8):
    """Read OPERA ACRR precip and mask by quality index.

    Returns precip in mm with:
        nodata   (no radar coverage) -> NaN
        undetect (valid, dry)        -> 0.0
        QI < qi_threshold            -> NaN (low-confidence retrieval)

    qi_threshold is the minimum total quality index (0..1) required to keep
    a pixel. Set to 0.0 to mask only the QI==0 (effectively nodata) cells.
    The quality field lives in dataset1/data1/quality1 (task
    pl.imgw.quality.qi_total).
    """
    logger.info(f"Reading {filename}")
    with h5py.File(filename, "r") as h5file:
        datagroup = h5file['dataset1']['data1']

        what     = datagroup['what'].attrs
        gain     = what.get('gain', 1.0)
        offset   = what.get('offset', 0.0)
        nodata   = what.get('nodata')
        undetect = what.get('undetect')
        logger.debug("HDF OPERA gain={}, offset={}, nodata={}, undetect={}".format(
            gain, offset, nodata, undetect))

        raw = np.array(datagroup['data'], dtype=float)

        # quality index (0..1); gain/offset are 1.0/0.0 but apply for safety
        if 'quality1' in datagroup:
            q_what = datagroup['quality1']['what'].attrs
            qi = (np.array(datagroup['quality1']['data'], dtype=float)
                  * q_what.get('gain', 1.0) + q_what.get('offset', 0.0))
            logger.debug("HDF OPERA quality index range: {:.3f} - {:.3f}".format(
                np.nanmin(qi), np.nanmax(qi)))
        else:
            # no quality field: keep every pixel (QI masking becomes a no-op)
            logger.warning("No quality1 group in %s; skipping QI masking", filename)
            qi = np.full_like(raw, np.inf)

    # identify sentinels BEFORE scaling
    is_nodata   = raw == nodata
    is_undetect = raw == undetect
    is_low_qi   = qi < qi_threshold

    data = raw * gain + offset
    data[is_undetect] = 0.0            # dry
    data[is_nodata]   = np.nan         # no coverage
    data[is_low_qi]   = np.nan         # low quality

    logger.debug("HDF OPERA masked fractions: nodata={:.1%}, undetect/dry={:.1%}, "
                 "low-QI(<{:.2f})={:.1%}".format(
                     np.mean(is_nodata), np.mean(is_undetect),
                     qi_threshold, np.mean(is_low_qi & ~is_nodata)))
    nan_frac = np.mean(np.isnan(data))
    logger.info("OPERA raw field NaN fraction: {:.1%} (max precip {:.2f} mm)".format(
        nan_frac, np.nanmax(data) if nan_frac < 1.0 else float('nan')))
    if nan_frac > 0.95:
        logger.warning("OPERA field %s is %.1f%% NaN at QI threshold %.2f",
                       filename, 100.0 * nan_frac, qi_threshold)

    return data


def read_OPERA(data_list, start_date, end_date, args):
    duration = end_date - start_date
    dim = int(duration.total_seconds() / 900)
    qi_threshold = getattr(args, 'opera_qi_threshold', 0.8)
    logger.info("Accumulating OPERA from {:s} to {:s} (QI threshold {:.2f})".format(
        start_date.strftime("%Y-%m-%d %H:%M"),
        end_date.strftime("%Y-%m-%d %H:%M"), qi_threshold))
    data = np.full((dim, 2200, 1900), np.nan)
    idx = 0
    read_dt = dt.timedelta(minutes=60)
    read_opera_date = start_date + dt.timedelta(minutes=60)
    while read_opera_date <= end_date:
        dat_str = read_opera_date.strftime("%Y%m%d%H%M")
        year, month, day, hour = read_opera_date.year, read_opera_date.month, read_opera_date.day, read_opera_date.hour
        opera_file_name = f"/scratch/snh02/DE_observations/opera/{year}/{month:02d}/{day:02d}/T_PASH22_C_EUOC_{year}{month:02d}{day:02d}{hour:02d}0000.hdf"
        opera_file_name = f"/home/pscheff/coding-geosphere/panelification/OBS/opera/{year}/{month:02d}/{day:02d}/T_PASH22_C_EUOC_{year}{month:02d}{day:02d}{hour:02d}0000.hdf"
        logger.info("reading OPERA for {:s} ".format(read_opera_date.strftime("%Y-%m-%d %H:%M")))
        data[idx, :, :] = read_from_hdf(opera_file_name, qi_threshold=qi_threshold)
        idx += 1
        read_opera_date += dt.timedelta(minutes=60)
    if idx == 0:
        logger.warning("No OPERA files read for %s - %s; returning empty field",
                       start_date, end_date)
    lon, lat = OPERA_grid()
    # the array is over-allocated at 15-min granularity but filled hourly, so
    # keep only the slots we actually read before checking for coverage gaps
    data = data[:idx]
    logger.debug("Read %d hourly OPERA fields", idx)
    # only accumulate pixels that are valid (non-NaN) for *every* hour;
    # a pixel masked in any hour stays NaN so we never under-count coverage gaps
    valid_all_hours = ~np.any(np.isnan(data), axis=0)
    tmp_precip = np.where(valid_all_hours, np.nansum(data, 0), np.nan)
    n_clamped = int(np.sum(tmp_precip > 2000.))
    if n_clamped:
        logger.warning("Clamping %d OPERA pixels with accumulation > 2000 mm to NaN",
                       n_clamped)
    tmp_precip = np.where(tmp_precip>2000., np.nan, tmp_precip)
    tmp_precip = np.flip(tmp_precip, 0)
    nan_frac = np.mean(np.isnan(tmp_precip))
    logger.info("OPERA accumulated field: {:d} valid pixels ({:.1%}), NaN fraction {:.1%}".format(
        int(valid_all_hours.sum()), valid_all_hours.mean(), nan_frac))
    if nan_frac > 0.95:
        logger.warning("Accumulated OPERA field is %.1f%% NaN at QI threshold %.2f - "
                       "consider lowering --opera_qi_threshold", 100.0 * nan_frac, qi_threshold)
    logger.info("OPERA max precip: {:f}".format(
        np.nanmax(tmp_precip) if nan_frac < 1.0 else float('nan')))
    data_list.insert(0,{
        'conf' : 'OPERA',
        'type' : 'obs',
        'name' : 'OPERA',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data': tmp_precip})
    return data_list
