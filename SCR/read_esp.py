import pygrib
import numpy as np
from netCDF4 import Dataset
import datetime as dt
import pyresample

import logging
logger = logging.getLogger(__name__)


def read_esp(data_list, start_date, end_date, args):
    duration = end_date - start_date
    tt = start_date
    first = True
    lon1d, lat1d, rr1d = None, None, None
    while tt < end_date:
        dat_str = start_date.strftime("%Y%m%d")
        read_file = f"/home/kmek/panelification/OBS/esp_ana/{dat_str}.nc"
        logger.info("reading ESP for {:s}".format(tt.strftime("%Y-%m-%d %H:%M")))
        data_tmp = Dataset(read_file, "r")
        if first:
            rr1d = data_tmp.variables['precipitation'][:]
            lon1d = data_tmp.variables['longitude'][:]
            lat1d = data_tmp.variables['latitude'][:]
            first = False
        else:
            rr1d += data_tmp.variables['precipitation']
        tt += dt.timedelta(hours=24)
    lo = np.arange(-10., 4., 0.025)
    la = np.arange(35., 44., 0.025)
    llo, lla = np.meshgrid(lo, la)
    targ_def = pyresample.geometry.SwathDefinition(llo, lla)
    orig_def = pyresample.geometry.SwathDefinition(lon1d, lat1d)
    data = pyresample.kd_tree.resample_nearest(orig_def, rr1d, targ_def, reduce_data=False, radius_of_influence=25000)

    data_list.insert(0, {
        'conf' : "ESP_ana",
        'type' : "obs",
        'name' : "ESP_ana",
        'lat' : lla,
        'lon' : llo,
        'precip_data' : data})
    logger.debug(data_list[0]["precip_data"])
    logger.debug(data_list[0]["precip_data"].max())
    logger.debug(data_list[0]["precip_data"].min())
    return data_list
