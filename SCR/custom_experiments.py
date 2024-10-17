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
                              'hail': False,
                              'else': True},
        "path_template"    : {'precip': "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/arome_%H+%LLLL.grb",
                              'else': "/arome_arch/aladin/ARCHIVE/AROMEaut/%Y%m%d/%H/AROMEaut+%LLLL.grb"},
        "unit_factor"      : {'sunshine': 1./3600.,
                              'hail': 1000.,
                              'else': 1.},
        "color"            : 'blue'
        },
    "aromeruc": {
        "base_experiment"  : "arome",
        "init_interval"    : 1,
        "output_interval"  : 1,
        "max_leadtime"     : 12, 
        "accumulated"      : True,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeruc_%H+%LLLL.00.grb",
        "color"            : "navy"
        },
    "inca-opt": {
        "init_interval"    : 1,
        "output_interval"  : 1,
        "max_leadtime"     : 48,
        "accumulated"      : True, # technically not, but does not matter
        "unit_factor"      : 1.,
        # "path_template"    : "/incaplus_arch1/iplus/out/INCA_15m/2024/09/13/INCA_15m_RR_FC_202409130000.grb2"
        "path_template"    : "/incaplus_arch1/iplus/out/INCA_15m/%Y/%m/%d/INCA_15m_RR_FC_%Y%m%d%H00.grb2",
        "color"            : "red"
    },
    "aromeesuite": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeesuite_%H+%LLLL.grb"
        },
    "ecmwf": {
        "init_interval"    : 6,
        "output_interval"  : 1, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : ["/ment_arch2/pscheff/event_archive/ECMWF/ecmwf_%Y%m%d_%H+%LLLL.grb",
                             #  "/ment_arch2/pscheff/WEB_PAN/panelification/MODEL/ecmwf/ecmwf_precip_%Y%m%d_%H+%LLLL.grb"],
                              "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/ecmwf_%H+%LLLL.grb"],
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "color"            : "black"
    },
    "gfs": {
        "init_interval"    : 6,
        "output_interval"  : 3, # 6 for some lead times, but panelification can sort that out
        "max_leadtime"     : 192,
        "url_template"     : "https://data.rda.ucar.edu/d084001/%Y/%Y%m%d/gfs.0p25.%Y%m%d%H.f%LLL.grib2",
        "path_template"    : ["/ment_arch2/pscheff/event_archive/GFS/%Y/%m/%d/%H/GFS+%LLLL_rr.grb2",
                              "/ment_arch2/pscheff/event_archive/GFS/%Y/%m/%d/%H/GFS+%LLLL.grb2"],
        "accumulated"      : True,
        "unit_factor"      : 1.,
        "color"            : "gray"
    },
    "icon_global_long": {
        "init_interval"    : 6,
        "output_interval"  : 1, # 6 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        # "url_template"     : "https://data.rda.ucar.edu/d084001/%Y/%Y%m%d/gfs.0p25.%Y%m%d%H.f%LLL.grib2",
        "path_template"    : "/ment_arch2/pscheff/event_archive/ICON/%Y/%m/%d/%H/ICON+%LLLL_rr.grb",
        # "path_template"    : "../MODEL/gfs/%Y/%m/%d/gfs.0p25.%Y%m%d%H.f%LLL.grib2",
        "accumulated"      : True,
        "unit_factor"      : 1.,
        "color"            : "darkgoldenrod"
    },
    "graphcast": {
        "init_interval"    : 24,
        "output_interval"  : 6, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/dmgc_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "color"            : "purple"
    },
    "aifs": {
        "init_interval"    : 24,
        "output_interval"  : 6, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aifs_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "color"            : "fuchsia"
    },
    "claef-control": {
        "init_interval"    : 12,
        "base_experiment"  : "arome",
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-control_%H+%LLLL.grb",
        "path_template"    : {'hail': "/ment_arch2/pscheff/WEB_PAN/panelification/MODEL/CLAEF_CONTROL/%Y%m%d%H/CLAEF_00_%Y%m%d%H+%LL.grb",
                              'else': "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-control_%H+%LLLL.grb"},
        "color"            : "skyblue"
    },
    "claef-mean": {
        "base_experiment"  : "claef-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-mean_%H+%LLLL.grb",
    },
    "claef-median": {
        "base_experiment"  : "claef-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-median_%H+%LLLL.grb",
    },
    "claef1k-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "claef1k-mean": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-mean_%H+%LLLL.grb",
    },
    "claef1k-median": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-median_%H+%LLLL.grb",
    },
    "icon": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icon_%H+%LLLL.grb",
        "color"            : "darkgoldenrod"
    },
    "icond2": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icond2_%H+%LLLL.grb",
        "color"            : "orange"
    },
    "icon-eu": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/icon-eu_%H+%LLLL.grb",
        "color"            : "darkorange"
    },
    "arpege": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/arpege_%H+%LLLL.grb",
        "color"            : "darkgreen"
    },
    "cosmo1e": {
        "init_interval"    : 3,
        "output_interval"  : 1, 
        "max_leadtime"     : 33,
        "accumulated"      : False,
        "unit_factor"      : 1.,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/cosmo1e_%H+%LLLL.grb2",
    },
    "claef1k-all-members": {
        "dummy_val"        : "all claef members, this is replaced in main.py"
    },
    "claef1k-m01": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_01_%H+%LLLL.grb",
    },
    "claef1k-m02": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_02_%H+%LLLL.grb",
    },
    "claef1k-m03": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_03_%H+%LLLL.grb",
    },
    "claef1k-m04": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_04_%H+%LLLL.grb",
    },
    "claef1k-m05": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_05_%H+%LLLL.grb",
    },
    "claef1k-m06": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_06_%H+%LLLL.grb",
    },
    "claef1k-m07": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_07_%H+%LLLL.grb",
    },
    "claef1k-m08": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_08_%H+%LLLL.grb",
    },
    "claef1k-m09": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_09_%H+%LLLL.grb",
    },
    "claef1k-m10": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_10_%H+%LLLL.grb",
    },
    "claef1k-m11": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_11_%H+%LLLL.grb",
    },
    "claef1k-m12": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_12_%H+%LLLL.grb",
    },
    "claef1k-m13": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_13_%H+%LLLL.grb",
    },
    "claef1k-m14": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_14_%H+%LLLL.grb",
    },
    "claef1k-m15": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_15_%H+%LLLL.grb",
    },
    "claef1k-m16": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_16_%H+%LLLL.grb",
    },
}


