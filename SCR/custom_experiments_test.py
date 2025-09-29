# define custom experiments using a set of variables which allow
# Panelification to contruct paths to files and read precipitation
# fields for the selected experiments. This is meant for models
# not stored in DCMDB and can theoretically also be used on othe
# machines.
from grib_handles import grib_handles_arome, grib_handles_ifs

import logging
logger = logging.getLogger(__name__)


# entries can be dict with entries for specific parameters or str/float with entries valid for
# all parameters. Dict entry 'else' can be used as fallback, i.e. define specific file for
# one parameter and another path for all other parameters.
experiment_configurations = {
    "arome_test": {
        "init_interval"    : 3,
        "output_interval"  : 1,
        "max_leadtime"     : 60, 
        "accumulated"      : {'gusts': False,
                              'hail': False,
                              'else': True},
        "path_template"    : {'precip': "../TEST_DATA/arome/%Y%m%d/arome_%H+%LLLL.grb",
                              'else': None},
        "unit_factor"      : {'sunshine': 1./3600.,
                              'hail': 1000.,
                              'else': 1.},
        "color"            : 'blue'
        },
    "ecmwf_test": {
        "init_interval"    : 6,
        "output_interval"  : 1, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : "../TEST_DATA/ecmwf/%Y%m%d/ecmwf_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "color"            : "black"
    },
}
