import numpy as np
from shutil import copyfile
import os
from model_parameters import inca_ana_paths
from paths import PAN_DIR_TMP
import netCDF4
from netCDF4 import Dataset

import logging
logger = logging.getLogger(__name__)

#------------------  SAF CM Variables -------------------------*/
# these variables apply to the extension of the full imported SAF image 
# at a further stage I'd delinate it with the shape file of Hungary boundary, same for the forecast data 
Num_rows = 480
Num_columns = 640



# I guess I wont need read(file) function in its original form , since the SAF netcdf aleady has the binary image stored in a 2D array (480, 640 extension) 
def read_SAF (file): 
    # file shall be the path of the SAF image file, I'll add it somewhere   
    with Dataset('file', 'r') as nc:
        RR = nc.variables['cma'][:] 
    return RR
#  2D cma 

def check_paths(date): # 
    OBS = (r"/home/lovasz_v/Desktop/Panelification_PScheffknecht/panelification/TEST_DATA/SAF") # obs folder became broken?? 
    # our SAF cma filenames are like: bMma20250907_1755.nc   (ends with UTC) 
    # checking if there are files with the given day, and we'll use all UTC for verification 
    yyyymmdd = date[:8]
    formatum = f"bMma{yyyymmdd}_*.nc"
    for filename in os.listdir(OBS):
            if filename.startswith(f"bMma{yyyymmdd}_") and filename.endswith(".nc"):
                obs_file = os.path.join(OBS, filename)
                logger.info(f"File found: {obs_file}")

                return obs_file # 
            
    return False

def bringSAF_netcdf(date):
    
    
    
    obs_file_path = check_paths(date) 
    
    if not obs_file_path:
         return False 
    
    try:
        RR = read_SAF(obs_file_path)  #
    except:
        logger.error(f"Failed to read file {obs_file_path}: {e}")
        return False

    return RR
