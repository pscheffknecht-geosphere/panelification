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
        "init_interval"    : 3,
        "output_interval"  : 1,
        "max_leadtime"     : 60, 
        "accumulated"      : True,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/arome_%H+%LLLL.grb",
        "unit_factor"      : 1.
        },
    "aromeruc": {
        "base_experiment"  : "arome",
        "init_interval"    : 1,
        "output_interval"  : 1,
        "max_leadtime"     : 12, 
        "accumulated"      : True,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeruc_%H+%LLLL.00.grb",
        },
    "ifs-highres": {
        "init_interval"    : 6,
        "output_interval"  : 1, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/ecmwf_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
    },
    "claef-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-control_%H+%LLLL.grb",
    },
    "claef-mean": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-mean_%H+%LLLL.grb",
    },
    "claef-median": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-median_%H+%LLLL.grb",
    },
    "claef1k-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
    },
    "claef1k-mean": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-mean_%H+%LLLL.grb",
    },
    "claef1k-median": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-median_%H+%LLLL.grb",
    },
    "icon": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icon_%H+%LLLL.grb",
    },
    "icond2": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icond2_%H+%LLLL.grb",
    },
    "icon-eu": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icon-eu_%H+%LLLL.grb",
    },
    "arpege": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/arpege_%H+%LLLL.grb",
    },
    "cosmo1e": {
        "init_interval"    : 3,
        "output_interval"  : 1, 
        "max_leadtime"     : 33,
        "accumulated"      : False,
        "unit_factor"      : 1.,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/cosmo1e_%H+%LLLL.grb2",
    },
}


