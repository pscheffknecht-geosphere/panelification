import numpy as np
from shutil import copyfile
import os
from model_parameters import inca_ana_paths

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

def bring(date, inca_file=None):
    DIR_TMP='../TMP/'
    if not inca_file:
        scratch = os.getenv('PERM')
        #DIR_OBS='/mapp_arch/mgruppe/arc/inca_1h/prec/'
        DIR_OBS='/home/kmek/panelification/OBS/inca_1h/prec/'
        file_OBS=DIR_OBS+date[:4]+'/'+date[4:6]+'/'+date[6:8]+'/INCA_RR-'+date[8:10]+'.asc.gz'
    else:
        file_OBS = inca_file
    logger.info("reading: {:s}".format(file_OBS))

    file_TMP=DIR_TMP+'INCA_OBS'+'%05d' %((np.random.rand(1)*10000).astype(int))+'.gz'

    if os.path.isfile(file_OBS):
        copyfile(file_OBS, file_TMP)
        order_unzip="gzip -df "+file_TMP
        os.system(order_unzip)
        try:
            RR=read(file_TMP[:-3])
        except:
            raise
        order_rm="rm "+file_TMP[:-3]
        os.system(order_rm)
        return RR
    else:
        raise

