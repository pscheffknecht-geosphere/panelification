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
    "arome": {
        "init_interval"    : 3,
        "output_interval"  : 1,
        "max_leadtime"     : 60, 
        "accumulated"      : {'gusts': False,
                              'else': True},
        "path_template"    : {'precip': "/perm/kmek/panelification/MODEL/arome/%Y%m%d/%H/arome_%H+%LLLL.grb",
                              'else': "/arome_arch/aladin/ARCHIVE/AROMEaut/%Y%m%d/%H/AROMEaut+%LLLL.grb"},
        "unit_factor"      : {'sunshine': 1./3600.,
                              'else': 1.},
        "on_mars"          : False
        },
    "aromeruc": {
        "base_experiment"  : "arome",
        "init_interval"    : 1,
        "output_interval"  : 1,
        "max_leadtime"     : 12, 
        "accumulated"      : True,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeruc_%H+%LLLL.00.grb",
        },
    "aromeesuite": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeesuite_%H+%LLLL.grb"
        },
    "ecmwf": {
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
        "path_template"    : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb",
        "ecfs_path_template" : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb"
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
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
    "ifs-highres": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 120, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/home/kmek/panelification/MODEL/ifs-highres/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        "unit_factor"      : 1000.,
        "on_mars"             : True
        },
    "deode_test": {
        "init_interval"    : 3,
        "output_interval"  : 1,
        "max_leadtime"     : 96, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/ec/res4/scratch/kmw/deode/CASE_1/archive/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "unit_factor"      : 1.
        },
    "deode_arome_500_austria": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 48, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/perm/kmek/deode500/CY48t3_AROME_CASES/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        # "path_template"    : "/home/kmek/panelification/MODEL/DEODE_AT_500m/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        # "ecfs_path_template":"ectmp:/{USER}/deode/CY48t3_AROME_CASE{CASE}/archive/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        "unit_factor"      : 1.,
        "on_mars"          : False
        },
    "ifs-dt": {
        "base_experiment"  : "ifs-highres",
        "path_template"    : "/home/kmek/panelification/MODEL/dt/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        },
    "ifs-dt-nc": {
        "base_experiment"  : "ifs-highres",
        "path_template"    : "/home/kmek/panelification/MODEL/dt_nc/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        },
    "arome-dt-48t3" : {
        "base_experiment"   : "deode_arome_500_austria",
        "path_template"    : "/home/kmek/panelification/MODEL/WITT_KSTMK/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        "ecfs_path_template" : "ec:/kay/deode/CY48t3_AROME_KSTMK/archive/%Y/%m/%d/%H/ICMSHDEOD+%LLLLh00m00s",
        },
}


