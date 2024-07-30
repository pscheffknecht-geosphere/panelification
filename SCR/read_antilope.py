import numpy as np
import datetime as dt
import pygrib
import logging
logger = logging.getLogger(__name__)

def read_ANTILOPE(data_list, start_date, end_date, args):
    duration = end_date - start_date
    idx = 0
    read_dt = dt.timedelta(minutes=60)
    tt = start_date
    first = True
    lon, lat = None, None
    while tt < end_date:
        date_str = tt.strftime("%Y%m%d")
        time_str = tt.strftime("%H")    
        antilope_file_name = f"/scratch/rm6/meteofrance/antilope/{date_str}/{date_str}{time_str}.anti_RR1_FRANXL1S100.grib"
        logger.info("reading ANTILOPE for {:s} ".format(tt.strftime("%Y-%m-%d %H:%M")))
        grb = pygrib.open(antilope_file_name)
        rr_field = grb.select(name="Precipitation")[0]
        if first:
            lat, lon = rr_field.latlons()
            rr = rr_field.values
            first = False
        else:
            rr += rr_field.values
        tt += read_dt
    logger.info("ANTILOPE max precip: {:f}".format(
        np.nanmax(rr)))
    data_list.insert(0,{
        'conf' : 'ANTILOPE',
        'name' : 'ANTILOPE',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data': rr})
    return data_list
