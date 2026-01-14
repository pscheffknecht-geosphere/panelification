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


import logging
logger = logging.getLogger(__name__)

#------------------  SAF CM Variables -------------------------*/
# these variables apply to the extension of the full imported SAF image 
# at a further stage I'd delinate it with the shape file of Hungary boundary, same for the forecast data 
Num_rows = 480
Num_columns = 640

def SAF_grid():
    # read the numpy array that stores coordinates of SAF products, as SAF images are stored separately from a deaafult SAF coordinatefile. 
    # I modified the originally flattened array into a 2D array, the nc_path points to the 2D one. 
    # where is the right place to add the path? 
    # if here:
    nc_path = (r"../TEST_DATA/SAFcoord/fixed_SAFcoord.nc")
    with Dataset(nc_path, 'r') as ds:
        lat_SAF = ds.variables['lat'][:]
        lon_SAF = ds.variables['lon'][:]
  


    return lat_SAF,lon_SAF

    # 

def read_SAF_obs(data_list, start_date, end_date, args):# is it the data_list from main? 

    first = True
    if 'cma' in args.parameter: #  
        read_dt = dt.timedelta(hours=1) #we have SAF cma image in every hour 
        dtype = np.int16

       # relevant bring and checkpath functions is also  modified in the bring_obs library.
    
       
    first = True
    for read_SAF_date in loop_datetime(start_date + dt.timedelta(hours=1), end_date + dt.timedelta(hours=1), read_dt): # itt lesz többidőpont mert ez egy loop
        datetime= read_SAF_date
        logging.info("reading inca at " + str(read_SAF_date))



        # i guess the original code was for accumulating the  precip amount? 
        '''if first:
            var_tmp = bO.bringSAF_netcdf(datestring)
            first = False
        else:
            var_tmp = var_tmp + bO.bringSAF_netcdf(datestring)''' # cma will be for a fixed UTC, no accumulation. But we'll verify multiple UTCs. 
        if first: 
            cma_data = bringSAF_netcdf(datetime)
            first = False
        else:
            cma_data += bringSAF_netcdf(datetime)

    lat, lon = SAF_grid()

    data_list.insert(0, {
        'conf': 'SAF',
        'type': 'obs',
        'name': 'SAF cma {datestring}',
        'lat': np.asarray(lat),
        'lon': np.asarray(lon),
        'precip_data': cma_data
    })

    return data_list # 
    # 
    

def bringSAF_netcdf(date):
    obs_file_path = check_paths(date) 
    logger.info(f"reading saf data from {obs_file_path}")
    if not obs_file_path:
         return False 
    try:
        RR = read_SAF(obs_file_path)  #
    except:
        logging.error(f"Failed to read file {obs_file_path}")
        raise
        return False
    return RR


# I guess I wont need read(file) function in its original form , since the SAF netcdf aleady has the binary image stored in a 2D array (480, 640 extension) 
def read_SAF (file): 
    # file shall be the path of the SAF image file, I'll add it somewhere   
    with Dataset(file, 'r') as nc:
        RR = nc.variables['cma'][:] 
    return RR
#  2D cma 




def check_paths(date):
    OBS = r"/mnt/d/Users/lovasz_v/cma_panelification"

    obs_file_date = date - dt.timedelta(minutes=5)
    obs_file_date_str = obs_file_date.strftime("%Y%m%d_%H%M")
    yyyymmdd = obs_file_date.strftime("%Y%m%d")

    for filename in os.listdir(OBS):

        if filename.startswith(f"bMma{yyyymmdd}_"):
            if filename.endswith(".nc"):

                if filename.replace(".nc", "").endswith(obs_file_date_str):
                    obs_file = os.path.join(OBS, filename)
                    logger.info(f"File found: {obs_file}")
                    return obs_file

    logger.error(f"Did not find any output file in {OBS}")
    raise FileNotFoundError
