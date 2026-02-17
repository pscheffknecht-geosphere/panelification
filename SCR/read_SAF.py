import numpy as np
from shutil import copyfile
import os
from model_parameters import inca_ana_paths
from paths import PAN_DIR_TMP
import netCDF4
from netCDF4 import Dataset
import datetime as dt
from misc import loop_datetime
from datetime import timedelta
from pyproj import CRS, Transformer
import gzip
from io import BytesIO

import regions


import logging
logger = logging.getLogger(__name__)

#------------------  SAF CM Variables -------------------------*/
# these variables apply to the extension of the full imported SAF image 
# at a further stage I'd delinate it with the shape file of Hungary boundary, same for the forecast data 
Num_rows = 480
Num_columns = 640

def lonlat_from_nwc_geos(
    *,
    gdal_projection: str,
    gdal_geotransform: tuple,
    ny: int,
    nx: int,
) -> "tuple[np.ndarray, np.ndarray]":
    """
    Return 2D lon/lat arrays for NWC/GEO products (MSG, MSG-IODC, MTG).

    Handles both:
    - Earth-metric GEOS projections
    - Normalized GEOS projections (MTG / MSG-IODC)

    Parameters
    ----------
    gdal_projection : str
        NetCDF global attribute 'gdal_projection'
    gdal_geotransform : tuple
        NetCDF global attribute 'gdal_geotransform_table'
    ny, nx : int
        Grid dimensions

    Returns
    -------
    lon, lat : 2D numpy.ndarray
    """

    # --- Source CRS ---
    crs_src = CRS.from_proj4(gdal_projection)

    # --- Decide target CRS based on ellipsoid size ---
    a = crs_src.ellipsoid.semi_major_metre

    if a > 1e6:
        # Earth-sized ellipsoid → standard WGS84 lon/lat
        crs_dst = CRS.from_epsg(4326)
    else:
        # Normalized ellipsoid → build matching lon/lat CRS
        crs_dst = CRS.from_proj4(
            f"+proj=longlat +a={crs_src.ellipsoid.semi_major_metre} "
            f"+b={crs_src.ellipsoid.semi_minor_metre} +no_defs"
        )

    transformer = Transformer.from_crs(
        crs_src, crs_dst, always_xy=True
    )

    # --- Build grid ---
    x0, dx, _, y0, _, dy = gdal_geotransform

    x = x0 + dx * np.arange(nx)
    y = y0 + dy * np.arange(ny)

    xx, yy = np.meshgrid(x, y)

    # --- Transform ---
    lon, lat = transformer.transform(xx, yy)

    return lat, lon

def read_SAF_obs(data_list, start_date, end_date, args):# is it the data_list from main? 

    saf_data, lat, lon, nc_fill_value = read_saf_data(args, start_date, end_date)
    if saf_data.ndim ==3:
        assert saf_data.shape[0] ==1, f"Unexpected multiple time dimensions in SAF data. Expected 2d or 3d with first dimension having size 1 but found {saf_data.shape}"
        saf_data = saf_data[0, :, :]  # in case there is a time dimension

    logging.info("Finished reading SAF data.")
    logging.info(f"  SAF data shape: {saf_data.shape}")
    valid_mask = saf_data != nc_fill_value
    saf_data = np.where(valid_mask, saf_data, np.nan)
    logging.info(f"  Valid data points: {np.sum(valid_mask)} / {saf_data.size}")
    if np.sum(valid_mask) <saf_data.size:
        saf_data, lat, lon = crop_to_region_extent(args, saf_data, lat, lon)

    data_list.insert(0, {
        'conf': 'SAF',
        'type': 'obs',
        'name': 'SAF cma',
        'lat': np.asarray(lat),
        'lon': np.asarray(lon),
        'precip_data': saf_data
    })

    return data_list 

def crop_to_region_extent(args, saf_data, lat, lon):
    logging.warning("  Missing data points detected in SAF data! Cropping to region extent. This may fail")
    xmin, xmax, ymin, ymax = detect_lonlat_bounds(lon, lat, args.region)
    saf_data = saf_data[ymin:ymax, xmin:xmax]
    lon = lon[ymin:ymax, xmin:xmax]
    lat = lat[ymin:ymax, xmin:xmax]
    logging.debug(f"  Cropped lon range: {lon.min()} to {lon.max()}")
    logging.debug(f"  Cropped lat range: {lat.min()} to {lat.max()}")
    logging.info(f"  Cropped SAF data shape: {saf_data.shape}")
    return saf_data,lat,lon

def read_saf_data(args, start_date, end_date):
    read_dt = dt.timedelta(hours=1) #we have SAF cma image in every hour 
    dtype = float # we do not know which data type the SAF cma data will be stored, so we use float
    first = True
    read_time = start_date
    while read_time < end_date:

        saf_file_path = check_paths(read_time, args)
        logging.info(f"reading SAF {args.parameter} at {str(read_time)} from {saf_file_path}")
        if saf_file_path.endswith('.gz'):
            with gzip.open(saf_file_path, 'rb') as gz:
                decompressed = BytesIO(gz.read())
                nc = Dataset('in_memory.nc', mode='r', memory=decompressed.getvalue())
        else:
            nc = Dataset(saf_file_path, 'r')
        if first:
            saf_data = nc.variables[args.parameter][:].astype(dtype)
            lat, lon = lonlat_from_nwc_geos(
                    gdal_projection=nc.gdal_projection,
                    gdal_geotransform=nc.gdal_geotransform_table,
                    ny=nc.dimensions['ny'].size,
                    nx=nc.dimensions['nx'].size
                )
            nc_fill_value = nc.variables[args.parameter]._FillValue
            first = False
        else:
            saf_data += nc.variables[args.parameter][:].astype(dtype)
        nc.close()
        read_time += read_dt
    return saf_data,lat,lon,nc_fill_value
    

def detect_lonlat_bounds(lon, lat, region):
    logger.debug(f"Lon min and max: {np.min(lon)}, {np.max(lon)}")
    logger.debug(f"Lat min and max: {np.min(lat)}, {np.max(lat)}")
    lon_min, lon_max, lat_min, lat_max = region.extent
    lon_mask = (lon >= lon_min) & (lon <= lon_max)
    lat_mask = (lat >= lat_min) & (lat <= lat_max)
    combined_mask = lon_mask & lat_mask
    logging.debug(f"Detecting grid points within subdomain: {region.name}")
    logging.debug(f"  Lon bounds: {lon_min} to {lon_max}")
    logging.debug(f"  Lat bounds: {lat_min} to {lat_max}")

    indices = np.where(combined_mask)
    if indices[0].size == 0 or indices[1].size == 0:
        raise ValueError("No grid points found within the specified subdomain.")
    logging.debug(f"  Found {indices[0].size} grid points within subdomain.")

    row_min = np.min(indices[0])
    row_max = np.max(indices[0]) + 1  # +1 to include the max index
    col_min = np.min(indices[1])
    col_max = np.max(indices[1]) + 1  # +1 to include the max index

    logging.debug(f"  Row indices: {row_min} to {row_max}") 
    logging.debug(f"  Column indices: {col_min} to {col_max}")

    logging.debug(f"corners of the subdomain in the original grid: ({row_min}, {col_min}) to ({row_max}, {col_max})")
    logging.debug(f"this corresponds to lon/lat: ({lon[row_min, col_min]}, {lat[row_min, col_min]}) to ({lon[row_max-1, col_max-1]}, {lat[row_max-1, col_max-1]})")
    logging.debug(f"{row_min}, {row_max}, {col_min}, {col_max}.")
    return col_min, col_max, row_min, row_max

def check_paths(date, args):
    date_str = date.strftime("%Y%m%dT%H")
    date_str_short = date.strftime("%Y%m%d")
    date_str_m5m = (date - dt.timedelta(minutes=5)).strftime("%Y%m%d_%H%M")


    if args.parameter =='cma':
        obs_file_templates = [
            f"/ment_arch/aladin/ASSIM/OPLACE_archive/{date_str_short}/S_NWC_CMA_MTI1_Europe-NR_{date_str}0000Z.nc.gz",
            f"/mnt/CDS6/satellite/bMma/bMma{date_str_m5m}.nc",
            f"/ment_arch2/pscheff/DEV_PAN/flowermapping-panelification/TEST_DATA/SAF/S_NWC_CMA_MTI1_Europe-NR_{date_str}0000Z.nc",
            f"/ment_arch2/pscheff/DEV_PAN/flowermapping-panelification/TEST_DATA/SAF/S_NWC_CMA_MSG3_Europe-VISIR_{date_str}0000Z.nc",

            
        ]
    else:
        raise ValueError(f"SAF parameter {args.parameter} not supported.")
    #if args.parameter =='ct':
            # add Cloud Type data folder 
    
    #change the path to CDS6 when in operational use at HungaroMEt 
    for oft in obs_file_templates:
        logger.debug(f"Check for file {oft}...")
        if os.path.isfile(oft):
            return oft
    
    for oft in obs_file_templates:
        logger.error(f" {oft} does not exist")
    logger.critical(f"Did not find OBS file in any of the paths")
    raise FileNotFoundError
