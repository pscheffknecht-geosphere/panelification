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
    "aromeruc": {
        "base_experiment"  : "arome",
        "init_interval"    : 1,
        "output_interval"  : 1,
        "max_leadtime"     : 12, 
        "accumulated"      : True,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeruc_%H+%LLLL.00.grb",
        "color"            : "navy"
        },
    "aromeesuite": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/aromeesuite_%H+%LLLL.grb"
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
    "ecmwf": {
        "init_interval"    : 6,
        "output_interval"  : 1, # 3 for some lead times, but panelification can sort that out
        "max_leadtime"     : 120,
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/ecmwf_%H+%LLLL.grb",
        "accumulated"      : True,
        "unit_factor"      : 1000.,
        "color"            : "black"
    },
    "claef-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-control_%H+%LLLL.grb",
        "color"            : "skyblue"
    },
    "claef-mean": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-mean_%H+%LLLL.grb",
        "color"            : "skyblue"
    },
    "claef-median": {
        "base_experiment"  : "arome",
        "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef-median_%H+%LLLL.grb",
        "color"            : "skyblue"
    },
    "claef1k-control": {
        "base_experiment"  : "arome",
        "path_template"    : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb",
        "ecfs_path_template" : "/ec/ws2/tc/zat2/tcwork/claef1k/DATA/%Y%m%d/%H/MEM_00/ADDGRIB/CLAEF00+%LLLL:00.grb"
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
        "color"            : "dodgerblue"
    },
    "claef1k-control-arch": {
        "base_experiment"  : "claef1k-control",
        "path_template"    : "/perm/kmek/panelification/MODEL/claef1k/%Y%m%d/claef_1k_%H+%LLLL.grb",
        # "path_template"    : "/ment_arch3/aladin/PRECIP_ARCH/%Y%m%d/claef_1k_%H+%LLLL.grb",
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
    },
    "ifs-highres": {
        "init_interval"    : 6,
        "output_interval"  : 1,
        "max_leadtime"     : 240, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/home/kmek/panelification/MODEL/ifs-highres/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        "unit_factor"      : 1000.,
        "on_mars"          : True,
        "color"            : "black"
        },
    "deode_test": {
        "init_interval"    : 3,
        "output_interval"  : 1,
        "max_leadtime"     : 96, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/ec/res4/scratch/kmw/deode/CASE_1/archive/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "unit_factor"      : 1.,
        "color"            : "navy"
        },
    "deode_arome_500_austria": {
        "init_interval"    : 6,
        "output_interval"  : 1,
        "max_leadtime"     : 48, 
        "accumulated"      : True,
        # "path_template"    : "/ment_arch2/aladin/DEODE/CASE_1/%Y%m%d_%H/GRIBPFDEODAUSTRIA_500m+%LLLLh00m00s",
        "path_template"    : "/perm/kmek/deode500/CY48t3_AROME_CASES/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        # "path_template"    : "/home/kmek/panelification/MODEL/DEODE_AT_500m/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        # "ecfs_path_template":"ectmp:/{USER}/deode/CY48t3_AROME_CASE{CASE}/archive/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        "unit_factor"      : 1.,
        "on_mars"          : False,
        "color"            : "navy"
        },
    "arome-paris" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/rm6/meteofrance/paris500/%Y%m%d00/rain%Y%m%d%H%LL.grib"
        # "path_template"    : "/scratch/rm6/meteofrance/paris500/2024072700/rain202407270028.grib"
    },
    "arome-paris-rdp-500" : {
        "base_experiment"  : "deode_arome_500_austria",
        # "path_template"    : "/scratch/snh02/deode/PARIS_RDP_CY46h1_500M_cold/archive/2024/08/05/06/GRIBPFDEODPARIS_LARGE+0003h00m00s"
        "path_template"    : "/perm/kmek/panelification/MODEL/PARIS_RDP_CY46h1_500M_cold/%Y/%m/%d/%H/GRIBPFDEODPARIS_LARGE_500m+%LLLLh00m00s",
        # "path_template"    : "/scratch/snh02/deode/PARIS_RDP_CY46h1_500M_cold/archive/%Y/%m/%d/%H/GRIBPFDEODPARIS_LARGE+%LLLLh00m00s"
        # "path_template"    : "/scratch/rm6/meteofrance/paris500/2024072700/rain202407270028.grib"
    },
    "arome-paris-rdp-200" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/perm/kmek/panelification/MODEL/PARIS_RDP_CY46h1_200M/%Y/%m/%d/%H/GRIBPFDEODPARIS_LARGE_200m+%LLLLh00m00s",
        # "path_template"    : "/scratch/snh02/deode/PARIS_RDP_CY46h1_200M/archive/%Y/%m/%d/%H/GRIBPFDEODPARIS_LARGE_200m+%LLLLh00m00s"
        # "path_template"    : "/scratch/rm6/meteofrance/paris500/2024072700/rain202407270028.grib"
    },
    "aromeCorsica" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_corsica_flooding/archive/%Y/%m/%d/%H/GRIBPFDEODCUBIC_1500x1500_500m+%LLLLh00m00s"
        # "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_corsica_flooding/archive/2024/08/15/00/GRIBPFDEODCUBIC_1500x1500_500m+0014h00m00s"
    },

    "arome_500_d2" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/kay/deode/CY48t3_AROME_d2_500m/archive/%Y/%m/%d/%H/GRIBPFDEODCUBIC_1500x1500_500m+%LLLLh00m00s"
        # "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_corsica_flooding/archive/2024/08/15/00/GRIBPFDEODCUBIC_1500x1500_500m+0014h00m00s"
    },
    "arome_500_d5" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/kay/deode/CY48t3_AROME_d5 500m/archive/%Y/%m/%d/%H/GRIBPFDEODCUBIC_1500x1500_500m+%LLLLh00m00s"
        # "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_corsica_flooding/archive/2024/08/15/00/GRIBPFDEODCUBIC_1500x1500_500m+0014h00m00s"
    },
    "arome_500_d2a5" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/kay/deode/CY48t3_AROME_d5_1000m5_1000m%d/%H/GRIBPFDEODCUBIC_1500x1500_500m+%LLLLh00m00s"
        # "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_corsica_flooding/archive/2024/08/15/00/GRIBPFDEODCUBIC_1500x1500_500m+0014h00m00s"
    },
    "aromeFRse" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_SEFrance_w33_2024/archive/%Y/%m/%d/%H/GRIBPFDEODSEFrance_w33_2024+%LLLLh00m00s"
        # "path_template"    : "/scratch/nhad/deode/CY48t3_AROME_SEFrance_w33_2024/archive/2024/08/14/00/GRIBPFDEODSEFrance_w33_2024+0010h00m00s"
    },
    "ifs-dt": {
        "base_experiment"  : "ifs-highres",
        "init_interval"    : 24,
        "max_leadtime"     : 120, 
        "path_template"    : "/home/kmek/panelification/MODEL/ifs-dt/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        },
    "ifs-dt-nc": {
        "base_experiment"  : "ifs-highres",
        "init_interval"    : 24,
        "path_template"    : "/home/kmek/panelification/MODEL/dt_nc/ecmwf_precip_%Y%m%d_%H+%LLLL.grb",
        },
    "arome-dt-48t3" : {
        "base_experiment"   : "deode_arome_500_austria",
        "path_template"    : "/home/kmek/panelification/MODEL/WITT_KSTMK/%Y/%m/%d/%H/GRIBPFDEODAUSTRIA_CASES+%LLLLh00m00s",
        "ecfs_path_template" : "ec:/kay/deode/CY48t3_AROME_KSTMK/archive/%Y/%m/%d/%H/GRIBPFDEODPARIS_LARGE+%LLLLh00m00s",
        },
    # /scratch/sp3c/deode/CY48t3_AROME_nwp_PRT_500m_20241015/archive/2024/10/15
    "CY48t3_AROME_nwp_PRT_500m_20241015" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/sp3c/deode/CY48t3_AROME_nwp_PRT_500m_20241015/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/sink/deode/CY48t3_AROME_nwp_DEMO_60x80_2500m_20241015/archive/2024/10/15
    "CY48t3_AROME_nwp_DEMO_60x80_2500m_20241015" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/sink/deode/CY48t3_AROME_nwp_DEMO_60x80_2500m_20241015/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/nhad/deode/CY46h1_HARMONIE_AROME_nwp_IT_500m_conve_2_20241017/archive/2024/10/17
    "CY46h1_HARMONIE_AROME_nwp_IT_500m_conve_2_20241017" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/nhad/deode/CY46h1_HARMONIE_AROME_nwp_IT_500m_conve_2_20241017/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_S_ITA_500m_20241018/archive/2024/10/18
    "CY48t3_AROME_nwp_S_ITA_500m_20241018" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_S_ITA_500m_20241018/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_PRT_500m_20241015/archive/2024/10/15
    "CY48t3_AROME_nwp_PRT_500m_20241015" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_PRT_500m_20241015/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_IT_500m_conve_2_20241017/archive/2024/10/17
    "CY48t3_AROME_nwp_IT_500m_conve_2_20241017" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_IT_500m_conve_2_20241017/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_N_ITA_500m_20241018/archive/2024/10/18
    "CY48t3_AROME_nwp_N_ITA_500m_20241018" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_N_ITA_500m_20241018/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_ESP_500m_20241016/archive/2024/10/16
    "CY46h1_HARMONIE_AROME_nwp_ESP_500m_20241016" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_ESP_500m_20241016/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241018/archive/2024/10/18
    "CY48t3_AROME_nwp_FRA_500m_20241018" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241018/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_IRL_500m_storm_1_20241018/archive/2024/10/18
    "CY46h1_HARMONIE_AROME_nwp_IRL_500m_storm_1_20241018" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_IRL_500m_storm_1_20241018/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241015/archive/2024/10/15
    "CY48t3_AROME_nwp_FRA_500m_20241015" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241015/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_ISL_500m_20241017/archive/2024/10/17
    "CY46h1_HARMONIE_AROME_nwp_ISL_500m_20241017" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY46h1_HARMONIE_AROME_nwp_ISL_500m_20241017/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241016/archive/2024/10/16
    "CY48t3_AROME_nwp_FRA_500m_20241016" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241016/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241017/archive/2024/10/17
    "CY48t3_AROME_nwp_FRA_500m_20241017" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_FRA_500m_20241017/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
    # /scratch/aut6432/deode/CY48t3_AROME_nwp_IT_500m_storm_4_20241016/archive/2024/10/16
    "CY48t3_AROME_nwp_IT_500m_storm_4_20241016" : {
        "base_experiment"  : "deode_arome_500_austria",
        "path_template"    : "/scratch/aut6432/deode/CY48t3_AROME_nwp_IT_500m_storm_4_20241016/archive/%Y/%m/%d/%H/GRIBPFDEOD+%LLLLh00m00s"
    },
}
