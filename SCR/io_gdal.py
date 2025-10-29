import numpy as np
from osgeo import gdal

import logging
logger = logging.getLogger(__name__)

def read_data_gdal(file_path, parameter, lead, get_lonlat_data=False):
    """ calls the grib handle check and returns fields with or without lon and lat data,
    depending on selection"""
    dataset = gdal.Open(file_path)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray()
    data = np.flipud(data)  # Flip the data to match the new latitude order
    if get_lonlat_data:
        ulx, xres, xskew, uly, yskew, yres = dataset.GetGeoTransform()
        nrows, ncols = data.shape
        lons = np.linspace(ulx, ulx + ncols * xres, ncols)
        lats = np.linspace(uly, uly + nrows * yres, nrows)  # yres is negative
        lats = lats[::-1]
        lon, lat = np.meshgrid(lons, lats)
        return lon, lat, data
    else:
        return data
