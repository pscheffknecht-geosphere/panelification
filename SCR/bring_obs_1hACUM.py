import numpy as np
from shutil import copyfile
import os
from model_parameters import inca_ana_paths
from paths import PAN_DIR_TMP

import logging
logger = logging.getLogger(__name__)

#------------------  INCA Variables -------------------------*/
imin=20    # INCA grid western boundary index */
imax=720    # INCA grid eastern boundary index */
jmin=220    # INCA grid southern boundary index */
jmax=620    # INCA grid northern boundary index */
NI=(imax-imin+1)
NJ=(jmax-jmin+1)

def read(file):
    RR=np.zeros([NI*NJ])
    f=open(file,"r")
    i=0 
    for line in f:
        line = line.strip()
        columns = line.split()
        n_elements=np.size(columns)
        RR[i:i+n_elements]=columns
        i=i+n_elements
    f.close()
    RR=np.reshape(RR, [NJ,NI])
    return RR

def check_paths(date):
    DIRS_OBS = ['/mapp_arch/mgruppe/arc/inca_1h/prec/',
               '/home/kmek/panelification/OBS/inca_1h/prec/']
    for DIR_OBS in DIRS_OBS:
        file_OBS_test=DIR_OBS+date[:4]+'/'+date[4:6]+'/'+date[6:8]+'/INCA_RR-'+date[8:10]+'.asc.gz'
        logger.debug(f"Checking for file {file_OBS_test}")
        if os.path.isfile(file_OBS_test):
            return file_OBS_test
    return False

def bring(date, inca_file=None):
    if inca_file:
        file_OBS = inca_file
    else:
        file_OBS = check_paths(date)
        if not file_OBS:
            return False
    logger.info("reading: {:s}".format(file_OBS))
    file_TMP=PAN_DIR_TMP+'INCA_OBS'+'%05d' %((np.random.rand(1)*10000).astype(int))+'.gz'

    copyfile(file_OBS, file_TMP)
    order_unzip="gzip -df "+file_TMP
    os.system(order_unzip)
    try:
        RR=read(file_TMP[:-3])
    except:
        return False
    order_rm="rm "+file_TMP[:-3]
    os.system(order_rm)
    return RR
