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
        "path_template"    : {'precip': "/perm/kmek/panelification/MODEL/arome/%Y%m%d/arome_%H+%LLLL.grb",
                              'precip2': "/perm/kmek/panelification/MODEL/arome/%Y%m%d/arome_%H+%LLLL.grb",
        # "path_template"    : {'precip': "/perm/kmek/panelification/MODEL/arome/%Y%m%d/%H/arome_%H+%LLLL.grb",
                              'else': "/arome_arch/aladin/ARCHIVE/AROMEaut/%Y%m%d/%H/AROMEaut+%LLLL.grb"},
        "unit_factor"      : {'sunshine': 1./3600.,
                              'else': 1.},
        "on_mars"          : False,
        "color"            : "blue"
        },
    "claef1k-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb",
        "ecfs_path_template" : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb",
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "claef1k-control-arch": {
        "base_experiment"  : "arome",
        "path_template"    : "/perm/kmek/panelification/MODEL/claef1k/%Y%m%d/claef_1k_%H+%LLLL.grb",
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "claef1k-mean": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-mean_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "claef1k-median": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef1k-median_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "ifs-highres": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 240, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/home/kmek/panelification/MODEL/ifs-highres/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        "unit_factor"      : 1000.,
        "on_mars"          : True,
        "color"            : "black"
        },
    "claef_SPP_m01": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 60,
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "on_mars"          : False,
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF01+%LLLL.grb",
        "nice_name"        : "SPP M01",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m02": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF02+%LLLL.grb",
        "nice_name"        : "SPP M02",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m03": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF03+%LLLL.grb",
        "nice_name"        : "SPP M03",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m04": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF04+%LLLL.grb",
        "nice_name"        : "SPP M04",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m05": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF05+%LLLL.grb",
        "nice_name"        : "SPP M05",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m06": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF06+%LLLL.grb",
        "nice_name"        : "SPP M06",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m07": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF07+%LLLL.grb",
        "nice_name"        : "SPP M07",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m08": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF08+%LLLL.grb",
        "nice_name"        : "SPP M08",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m09": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF09+%LLLL.grb",
        "nice_name"        : "SPP M09",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m10": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF10+%LLLL.grb",
        "nice_name"        : "SPP M10",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m11": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF11+%LLLL.grb",
        "nice_name"        : "SPP M11",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m12": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF12+%LLLL.grb",
        "nice_name"        : "SPP M12",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m13": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF13+%LLLL.grb",
        "nice_name"        : "SPP M13",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m14": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF14+%LLLL.grb",
        "nice_name"        : "SPP M14",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m15": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF15+%LLLL.grb",
        "nice_name"        : "SPP M15",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_SPP_m16": {
        "base_experiment"  : "claef_SPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/SPP/%Y%m%d%H/CLAEF16+%LLLL.grb",
        "nice_name"        : "SPP M16",
        "ensemble"         : "SPP",
        "color"            : "navy"
    },
    "claef_FDSPP_m01": {
        "init_interval"    : 24,
        "output_interval"  : 1,
        "max_leadtime"     : 60,
        "accumulated"      : True,
        "unit_factor"      : 1.,
        "on_mars"          : False,
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF01+%LLLL.grb",
        "nice_name"        : "FDSPP M01",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m02": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF02+%LLLL.grb",
        "nice_name"        : "FDSPP M02",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m03": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF03+%LLLL.grb",
        "nice_name"        : "FDSPP M03",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m04": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF04+%LLLL.grb",
        "nice_name"        : "FDSPP M04",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m05": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF05+%LLLL.grb",
        "nice_name"        : "FDSPP M05",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m06": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF06+%LLLL.grb",
        "nice_name"        : "FDSPP M06",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m07": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF07+%LLLL.grb",
        "nice_name"        : "FDSPP M07",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m08": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF08+%LLLL.grb",
        "nice_name"        : "FDSPP M08",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m09": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF09+%LLLL.grb",
        "nice_name"        : "FDSPP M09",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m10": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF10+%LLLL.grb",
        "nice_name"        : "FDSPP M10",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m11": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF11+%LLLL.grb",
        "nice_name"        : "FDSPP M11",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m12": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF12+%LLLL.grb",
        "nice_name"        : "FDSPP M12",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m13": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF13+%LLLL.grb",
        "nice_name"        : "FDSPP M13",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m14": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF14+%LLLL.grb",
        "nice_name"        : "FDSPP M14",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m15": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF15+%LLLL.grb",
        "nice_name"        : "FDSPP M15",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
    "claef_FDSPP_m16": {
        "base_experiment"  : "claef_FDSPP_m01",
        "path_template"    : "/ec/res4/scratch/kmcw/endi/%Y%m/FDSPP/%Y%m%d%H/CLAEF16+%LLLL.grb",
        "nice_name"        : "FDSPP M16",
        "ensemble"         : "FDSPP",
        "color"            : "firebrick"
    },
}
