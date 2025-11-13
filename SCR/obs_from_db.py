import os
import pandas as pd
import pymssql
import logging
import datetime as dt
import numpy as np
import progress
from inca_functions import INCA_grid
# import matplotlib.pyplot as plt

from paths import PAN_DIR_OBS_ARCH

import logging
logger = logging.getLogger(__name__)

server_to_hostname = {
    'SYBWIEN1': {
        'name': 'zaadbs3.zamg.ac.at',
        'port': '8001'
    },
    'SYBWIEN2': {
        'name': 'zaadbs4.zamg.ac.at',
        'port': '8001'
    },
    'SYBGIGA': {
        'name': 'zaadbs5.zamg.ac.at',
        'port': '8001'
    }
}
server = 'SYBGIGA'

user = "rouser"
pswd = "readonly"

lonmin, lonmax, latmin, latmax = ("80000", "175000", "453000", "493000")

def convert_date_to_dat_tim(date, table='hagelw'):
    """ accepts date as datetime.datetime, int or str where
    int and str format must be yyyymmddHHMM[SS] and returns
    two strings "yyyymmdd" and "HHMM" """
    if type(date) == dt.datetime:
        if table == 'hagelw':
            dat = date.strftime("%Y%m%d")
        elif table == 'blitz2':
            y = date.year - 1900
            dat = str(y) + date.strftime("%m%d")
        tim = date.strftime("%H%M")
    else:
        logging.error("convert_date_to_dat_tim in sybase.py: not a valid datetime, got "+str(date)+" ("+str(type(date))+") instead")
        exit()
    return str(dat), str(tim)


def process_time_window_for_sql(start_date, end_date, table):
    if start_date.day == end_date.day and start_date - end_date < dt.timedelta(hours=24):
        start_dat, start_tim = convert_date_to_dat_tim(start_date, table=table)
        end_dat, end_tim = convert_date_to_dat_tim(end_date, table=table)
        return [start_dat], [start_tim], [end_dat], [end_tim]
    elif start_date.day != end_date.day or start_date - end_date >= dt.timedelta(hours=24):
        start_dats, start_tims, end_dats, end_tims = ([], [], [], [])
        _dat, _tim = convert_date_to_dat_tim(start_date, table=table)
        start_dats.append(_dat)
        start_tims.append(_tim)
        end_dats.append(_dat)
        end_tims.append("2400")
        date_curr = start_date + dt.timedelta(days=1)
        while date_curr.date() < end_date.date():
            _dat, _tim = convert_date_to_dat_tim(date_curr, table=table)
            start_dats.append(_dat)
            start_tims.append("0000")
            end_dats.append(_dat)
            end_tims.append("2400")
            date_curr += dt.timedelta(days=1)
        if end_date.hour > 0:
            _dat, _tim = convert_date_to_dat_tim(end_date, table=table)
            start_dats.append(_dat)
            start_tims.append("0000")
            end_dats.append(_dat)
            end_tims.append(_tim)
        return(start_dats, start_tims, end_dats, end_tims)


def add_datetime(df, table="hagelw"):
    """ take Datum and stdmin entries from sybase and convert to datetime"""
    datetime = []
    for _, row in df.iterrows():
        dat = row.Datum
        tim = row.stdmin
        sec = row.sec if table=="blitz2" else "00"
        dat_tim_str = str(dat) + str(tim).zfill(6)
        datetime.append(dt.datetime.strptime(dat_tim_str, "%Y%m%d%H%M%S"))
    df['datetime'] = datetime
    return(df)


def deg_min_sec_to_degdecimal(val):
    """convert DEGMMSS to decimal degrees"""
    secs = val%100
    mins = (val - secs)%10000/100
    degs = (val - 100*mins - secs)/10000
    degsdec = degs + mins/60. + secs/3600.
    return(degsdec)

def conv_lat_lon(df):
    """convert lat and lon entries from deg min sec to decimal degrees"""
    lon = []
    lat = []
    for _, row in df.iterrows():
        lon.append(deg_min_sec_to_degdecimal(row.laenge))
        lat.append(deg_min_sec_to_degdecimal(row.breite))
    df['lon'] = lon
    df['lat'] = lat
    return(df)


def to_grid(df, table="hailw"):
    maxidx = len(df)
    logger.info("Generating gridded obs from {:d} point observations".format(maxidx))
    lon, lat = INCA_grid()
    var = np.zeros(lon.shape)
    event = 0
    progress_update_rate = 100
    progress_counter = 0
    for idx, row in df.iterrows():
        progress_counter += 1
        dist = (lon - row.lon)**2 + (lat - row.lat)**2
        dist_min = np.min(dist)
        if dist_min < 1e-3: # rough estimate to keep it inside the grid
            xx, yy = np.argwhere(dist == dist_min)[0] # comes as list in a list
            if table == 'hailw':
                var[xx, yy] = row.poh if row.poh > var[xx, yy] else var[xx, yy]
            elif table == 'blitz2':
                var[xx, yy] += 1.
            event += 1
        if progress_counter == progress_update_rate:
            progress_counter = 0
            progress.progress_print(idx, maxidx, label="Gridding Observations")
    logger.info(f"Added {event} {table} events to the grid")
    return(var)


def clean_returns(tmp_, columns):
    odb_ret = pd.DataFrame.from_records(tmp_, columns=columns)
    odb_ret = add_datetime(odb_ret)
    odb_ret = conv_lat_lon(odb_ret)
    odb_ret = odb_ret.drop(['Datum', 'stdmin', 'breite', 'laenge'], axis=1)
    return(odb_ret)


def exec_request_pymssl(request):
    host_string = server_to_hostname[server]['name'] + ":" + server_to_hostname[server]['port']
    conn = pymssql.connect(host=host_string, user=user, password=pswd, conn_properties="")
    c_server = conn.cursor()
    c_server.execute(request)
    out = c_server.fetchall()
    c_server.close()
    conn.close()
    return out


def get_hail_from_sybase(start_date, end_date):
    #start_dat, start_tim = convert_date_to_dat_tim(start_date)
    end_dat, end_tim = convert_date_to_dat_tim(end_date)
    start_dat, start_tim = convert_date_to_dat_tim(start_date)
    hail_columns = ["Datum", "stdmin", "breite", "laenge", "poh"]
    if end_tim == "0000":
        end_tim = "2400"
    logging.info("fetching hail from "+str(start_date)+" to "+str(end_date))
    database = "hagelw" + f"_{start_date.year}" if start_date.year < 2023 else "hagelw"
    request = "SELECT Datum, stdmin, breite, laenge, poh from {database} WHERE Datum BETWEEN {start_dat} AND {end_dat} AND stdmin BETWEEN {start_tim} AND {end_tim}".format(
        database = database,
        start_dat = start_dat,
        start_tim = start_tim,
        end_dat = start_dat,
        end_tim = end_tim)
    logger.debug("request: "+request)
    hail = clean_returns(exec_request_pymssl(request), columns=hail_columns)
    return(hail)


def get_lightning_from_db(start_dat, start_tim, end_dat, end_tim, retry=False):
    if retry:
        request = "SELECT * from blitz WHERE datum BETWEEN {start_dat} AND {end_dat} AND stdmin BETWEEN {start_tim} AND {end_tim}".format(
            start_dat = str(int(start_dat) + 19000000),
            start_tim = start_tim,
            end_dat = str(int(end_dat) + 19000000),
            end_tim = end_tim)
    else:
        lightning_columns = ["Datum", "stdmin", "sec", "breite", "laenge", "richtung"]
        request = "SELECT datum, stdmin, sec, breite, laenge, richtung from synop.dbo.blitz2_{yyyy} WHERE datum = {start_dat} AND stdmin > {start_tim} AND stdmin < {end_tim} AND laenge > {lonmin} AND laenge < {lonmax} AND breite > {latmin} AND laenge < {latmax}".format(
            yyyy = str(int(start_dat) + 19000000)[0:4],
            start_dat = start_dat,
            start_tim = start_tim,
            #end_dat = end_dat,
            end_tim = end_tim,
            lonmin = lonmin,
            lonmax = lonmax,
            latmin = latmin,
            latmax = latmax)
    logger.debug("request: "+request)
    lightning = clean_returns(exec_request_pymssl(request), columns=lightning_columns)
    return lightning


def check_dfs(dflist):
    logger.debug("Read {:d} chunks from DB".format(len(dflist)))
    lsum = 0
    for idx, df in enumerate(dflist):
        logger.debug(" Chunk {:d} has {:d} entries".format(idx+1, len(df)))
        lsum += len(df)
    return lsum


def get_lightning_from_sybase(start_date, end_date):
    start_dats, start_tims, end_dats, end_tims = process_time_window_for_sql(start_date, end_date, "blitz2")
    #start_dat, start_tim = convert_date_to_dat_tim(start_date, table='blitz2')
    end_dat, end_tim = convert_date_to_dat_tim(end_date, table='blitz2')
    logger.debug(start_dats, start_tims, end_dats, end_tims)
    dflist=[]
    for start_dat, start_tim, end_dat, end_tim in zip(start_dats, start_tims, end_dats, end_tims):
        logging.info("fetching lightning from "+str(start_date)+" to "+str(end_date))
        dflist.append(get_lightning_from_db(start_dat, start_tim, end_dat, end_tim))
    lsum = check_dfs(dflist)
    if lsum < 10:
        logger.warning("FEWER THAN 10 STRIKES FOUND FOR PERIOD! IS THE DATE AND TIME CORRECT???")
        logger.warning("Retrying more general db read")
        for start_dat, start_tim, end_dat, end_tim in zip(start_dats, start_tims, end_dats, end_tims):
            logging.info("fetching lightning from "+str(start_date)+" to "+str(end_date))
            dflist.append(get_lightning_from_db(start_dat, start_tim, end_dat, end_tim, retry=True))
        lsum = check_dfs(dflist)
    if lsum < 10:
        logger.warning("ALL SOURCES CONTAIN LESS THAN 10 STRIKES. THERE IS NOT POINT IN CONTINUING")
    lightningdf=pd.concat(dflist)
    return(lightningdf)


def array_to_csv(arr, start_date, end_date, param):
    start_date_str = start_date.strftime("%Y%m%d%H%M")
    end_date_str = end_date.strftime("%Y%m%d%H%M")
    fil_nam = f"{PAN_DIR_OBS_ARCH}/{param}_{start_date_str}_{end_date_str}.csv"
    logger.info("Writing {:s} data to {:s}".format(param, fil_nam))
    if param == "lightning":
        fmtstr = "%.0f"
    elif param == "hail":
        fmtstr = "%.5f"
    np.savetxt(fil_nam, arr, fmt=fmtstr)


def read_archived_file(start_date, end_date, param):
    start_date_str = start_date.strftime("%Y%m%d%H%M")
    end_date_str = end_date.strftime("%Y%m%d%H%M")
    fil_nam = f"{PAN_DIR_OBS_ARCH}/{param}_{start_date_str}_{end_date_str}.csv".format(
        param, start_date.strftime("%Y%m%d%H%M"), end_date.strftime("%Y%m%d%H%M"))
    logger.info("Checking for archived obs in {:s}".format(fil_nam))
    if os.path.exists(fil_nam):
        if os.path.getsize(fil_nam) < 500000:
            logger.info("Archive found, but file siye is less than 500 kb")
            os.path.remove(fil_nam)
    if os.path.exists(fil_nam):
        exists = True
        var = np.genfromtxt(fil_nam, delimiter="")
        fail = True if np.isnan(var).any() or var.shape != (401, 701) or var.sum() < 10 else False
    else:
        logger.info("No archived data found, reading from DB")
        return None
    if fail and exists:
        logger.debug("Read from archive failed, deleting archived file {:s} and getting values from DB".format(
            fil_nam))
        os.remove(fil_nam)
        return None
    elif not fail:
        logger.debug("Archived data found, reading lightning from {:s}".format(fil_nam))
        return var
  

def read_lightning(data_list, start_date, end_date):
    lightning = read_archived_file(start_date, end_date, "lightning") # returns None if no archive or corrupt archive is found
    if not lightning is not None: # looks weird but also works if lightning is an array
        lightningdf = get_lightning_from_sybase(start_date, end_date)
        lightning = to_grid(lightningdf, table='blitz2')
        array_to_csv(lightning, start_date, end_date, "lightning")
    lon, lat = INCA_grid()
    data_list.insert(0, {
        'conf' : 'INCA',
        'name' : 'ALDIS lightning strikes',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data' : lightning})
    logger.debug("Lightning min={:.4f} max={:.4f}, avg={:.4f}, sum={:.2f}".format(
        lightning.min(), lightning.max(), lightning.mean(), lightning.sum()))
    return data_list


def read_hail(data_list, start_date, end_date):
    hail = read_archived_file(start_date, end_date, "hail") # returns None if no archive or corrupt archive is found
    if not hail is not None:
        haildf = get_hail_from_sybase(start_date, end_date)
        hail = to_grid(haildf, table='hailw')
        array_to_csv(hail, start_date, end_date, "hail")
    lon, lat = INCA_grid()
    data_list.insert(0, {
        'conf' : 'INCA',
        'name' : 'ATNT Hail',
        'lat' : np.asarray(lat),
        'lon' : np.asarray(lon),
        'precip_data' : hail})
    logger.debug("Hail min={:.4f} max={:.4f}, avg={:.4f}".format(
        hail.min(), hail.max(), hail.mean()))
    return data_list

def main(): 
    lon, lat = INCA_grid()
    logger.debug(lon.min(), lon.max(), lat.min(), lat.max())
    haildf = get_hail_from_sybase(dt.datetime(2021,7,1,9), dt.datetime(2021,7,1,10))
    hail = to_grid(haildf, table='hailw')
    #plt.imshow(hail)
    plt.colorbar()
    plt.show()
    lightningdf = get_lightning_from_sybase(dt.datetime(2021,7,1), dt.datetime(2021,7,1,23,59,59))
    lightning = to_grid(lightningdf, table='blitz2')
    #plt.imshow(lightning)
    plt.colorbar()
    plt.show()
    logger.debug(lightningdf)


if __name__ == "__main__":
    main()

