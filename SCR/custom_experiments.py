# define custom experiments using a set of variables which allow
# Panelification to contruct paths to files and read precipitation
# fields for the selected experiments. This is meant for models
# not stored in DCMDB and can theoretically also be used on othe
# machines.
from grib_handles import grib_handles_arome, grib_handles_ifs

import logging
logger = logging.getLogger(__name__)


experiment_configurations = {
    "arome": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 60, 
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/arome_+%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1.,
        },
    "ifs-highres": {
        "init_interval"    : 24,
        "output_interval"  : 1,

        "max_leadtime"     : 96, # placeholder
        "path_template"    : "/home/kmek/panelification/MODEL/IFS_HIGHRES/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
    },
    "1250_d1": {
        "base_experiment": "arome",
        "max_leadtime": 72,
        "path_template": "/ec/res4/scratch/kmek/moving/%Y%m%d/%H/1250_d1/GRIBPFDEODAUSTRIA_CASE+%LLLL"
    },
    "500_d3": {
        "base_experiment": "arome",
        "max_leadtime": 36,
        "path_template": "/ec/res4/scratch/kmek/moving/%Y%m%d/%H/500_d3/GRIBPFDEODAUSTRIA_CASE+%LLLL"
    },
    "500_d4": {
        "base_experiment": "arome",
        "max_leadtime": 42,
        "path_template": "/ec/res4/scratch/kmek/moving/%Y%m%d/%H/500_d4/GRIBPFDEODAUSTRIA_CASE+%LLLL"
    },
    "500_d5": {
        "base_experiment": "arome",
        "max_leadtime": 48,
        "path_template": "/ec/res4/scratch/kmek/moving/%Y%m%d/%H/500_d5/GRIBPFDEODAUSTRIA_CASE+%LLLL"
    }
}


