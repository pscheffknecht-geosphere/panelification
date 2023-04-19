import pandas as pd
import nclcmaps
import matplotlib.cm as cm
import numpy as np
from matplotlib.colors import BoundaryNorm as bnorm
import matplotlib.colors as mplcolors

model_archive_paths = {
    'precip': {
        'arome' : "/lus/h2resw01/scratch/kmek/panelification/MODEL/arome/{:s}/AROMEaut+00{:02d}.grb",
        'CY46_1250m_DHC' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_CY46_1250m_DHC/outfile_00{:02d}_iFlipped.grib",
        'CY46_500m_DHC' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_CY46_500m_DHC/outfile_00{:02d}_iFlipped.grib",
        'CY46_DOWN' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_CY46_DOWN/outfile_00{:02d}_iFlipped.grib",
        'CY46_DOWN_HYDRO' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_CY46_DOWN_HYDRO/outfile_00{:02d}_iFlipped.grib",
        'CY46_DOWN_HYDRO_CPL' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_CY46_DOWN_HYDRO_CPL/outfile_00{:02d}_iFlipped.grib",
        'GL2B' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_GL2B/outfile_00{:02d}_iFlipped.grib",
        'GL6J' : "/home/kmek/panelification/MODEL/{:s}_GL6J/outfile_00{:02d}_iFlipped.grib",
        'GL7J' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_GL7J/outfile_00{:02d}_iFlipped.grib",
        'OPER' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_OPER/outfile_00{:02d}_iFlipped.grib",
        'REF_CY46' : "/ec/res4/scratch/kmek/panelification/MODEL/{:s}_REF_CY46/outfile_00{:02d}_iFlipped.grib"
        }
    }

models_to_flip = ['CY46_1250m_DHC', 'CY46_500m_DHC','CY46_DOWN', 'CY46_DOWN_HYDRO' , 'CY46_DOWN_HYDRO_CPL', 'OPER', 'REF_CY46']
        
# model_archive_paths = {
#     'precip': {
#         'arome' : "/arome_arch/aladin/ARCHIVE/AROMEaut/{:s}/AROMEaut+00{:02d}.grb",
#         'aromeruc' : "/arome_arch/aladin/ARCHIVE/AROME_RUC_EXTRACTED/{:s}/AROMEruc+00{:02d}.00.grb",
#         'claef-members' : "/ment_arch2/pscheff/CLAEF_data/{:s}/ICMSHAROM+{:d}_{:d}"},
#     'hail': {
#         'arome' : "/arome_arch/aladin/ARCHIVE/AROMEaut/{:s}/AROMEaut+00{:02d}.grb",
#         'aromeruc' : "/arome_arch/aladin/ARCHIVE/AROME_RUC/{:s}/AROMEaut_EXTRACTED+00{:02d}.grb",
#         'claef-members' : "/ment_arch2/pscheff/CLAEF_data/{:s}/ICMSHAROM+{:d}_{:d}"},
#     'sunshine': {
#         'arome' : "/arome_arch/aladin/ARCHIVE/AROMEaut/{:s}/AROMEaut+00{:02d}.grb",
#         'aromeruc' : "/arome_arch/aladin/ARCHIVE/AROME_RUC/{:s}/AROMEaut+00{:02d}.grb",},
#     'lightning': {
#         'arome' : "/arome_arch/aladin/ARCHIVE/AROMEaut_EXTRACTED/{:s}/AROMEaut_lightning+00{:02d}.grb",
#         'aromeruc' : "/arome_arch/aladin/ARCHIVE/AROME_RUC_EXTRACTED/{:s}/AROMEruc+00{:02d}.00.grb",
#         'claef-members' : "/ment_arch2/pscheff/CLAEF_data/{:s}/ICMSHAROM+{:d}_{:d}"},
# }


model_current_prod_paths = {
    'aromeruc'         : "/ment_arch/aladin/AROME_RUC/PRODUCTION/GRIB/{:02d}/AROMEruc+00{:02d}.{:02d}.grb",
    'arome'      : "/ment_arch/aladin/AROME/PRODUCTION/GRIB/{:02d}/AROMEaut+00{:02d}.grb", 
    'claef-control' : "/ment_arch/aladin/CLAEF/PRODUCTION/GRIB/{:02d}/CLAEF_00+00{:02d}:00.grb",
    #'ecmwf' : "/modelle/ecmwf/ecmin/AZDMMDDHH00MMDDHH001
    'ecmwf' : "/modelle/ecmwf/ecmin/AZD{:s}00{:s}001"
}

inca_fc_paths = {
    'precip'        : "/mapp_arch2/mgruppe/arc/inca_l_fc/prec/{:s}/RR_FC_INCA-{:s}00.bil.gz",
    'sunshine'      : "/mapp_arch2/mgruppe/arc/inca_l_fc/prec/{:s}/SSD_FC_INCA-{:s}00.bil.gz",
}

inca_ana_paths = {
    'sunshine'      : "/mapp_arch/mgruppe/arc/inca_l/mslp/{:s}/INCA_SSD-{:s}.asc.gz"
}

# ARCHIVE DATA:
# MODEL            FORMAT   INIT_INTERVAL  LENGTH  OUTPUT FREQ.
# alaro5           GRIB     6              72      3
# arome            GRIB     3              60      1
# aromepeps-mean   GRIB2    3              48      6
# aromeruc         GRIB     1              12      1
# arpege           GRIB     12             72      6
# cosmo1           GRIB2    3              33      1
# cosmo7           GRIB2    12             72      1
# cosmod2          GRIB     3              27      1
# ecmwf            GRIB     6              72      3
# ecmwf-mean       GRIB     12             72      6
# ecmwf-median     GRIB     12             72      6
# icon             GRIB     6              72      6
# icon-eu          GRIB     3              72      3
# claef-control    GRIB     12             48      3
# claef-mean       GRIB     12             48      3
# claef-median     GRIB     12             48      3
# laef-det         GRIB     12             72      3
# laef-mean        GRIB     12             72      3
# laef-median      GRIB     12             72      3

# list of lists for the dataframe of sims
simdata = [['alaro5', 6, 72, 3, '.grb'], 
    ['arome', 3, 60, 1, '.grb'], 
    ['aromeesuite', 3, 60, 1, '.grb'], 
    ['aromeruc', 1, 12, 1, '.*grb'],
    ['aromerucesuite', 1, 12, 1, '.*grb'],
    ['aromemf', 24, 24, 24, '.*grb'],
    ['cosmo1', 3, 33, 1, '.grb2'],
    ['cosmo1e', 3, 33, 1, '.grb2'],
    ['cosmo7', 12, 72, 1, '.grb2'],
    ['cosmod2', 3, 27, 1, '.grb'],
    ['arpege', 12, 72, 6, '.grb'],
    ['ecmwf', 6, 72, 3, '.grb'], # precip in m instead of mm!!
    ['ecmwf-mean', 12, 72, 6, '.grb'], # precip in m instead of mm!!
    ['ecmwf-median', 12, 72, 6, '.grb'], # precip in m instead of mm!!
    ['icon', 6, 72, 6, '.grb'], # precip in m instead of mm!!
    ['icon-eu', 3, 72, 3, '.grb'], # precip in m instead of mm!!
    ['icond2', 3, 45, 1, '.grb'], # precip in m instead of mm!!
    ['claef-control', 12, 48, 1, '.grb'],
    ['claef-mean', 12, 48, 3, '.grb'],
    ['claef-median', 12, 48, 3, '.grb'],
    ['claef-members', 12, 48, 1, 'grb'], # is grib but no suffix - hashtag  E X T R A W U R S T
    ['laef-det', 12, 72, 3, '.grb'],
    ['laef-mean', 12, 72, 3, '.grb'],
    ['laef-median', 12, 72, 3, '.grb'],
    ['laef-median', 12, 72, 3, '.grb'],
    ['CY46_1250m_DHC', 24, 18, 6, '.grb'],
    ['CY46_500m_DHC', 24, 18, 6, '.grb'],
    ['CY46_DOWN', 24, 18, 6, '.grb'],
    ['CY46_DOWN_HYDRO', 24, 18, 6, '.grb'],
    ['CY46_DOWN_HYDRO_CPL', 24, 18, 6, '.grb'],
    ['GL2B', 24, 18, 6, '.grb'],
    ['GL6J', 24, 18, 6, '.grb'],
    ['GL7J', 24, 18, 6, '.grb'],
    ['OPER', 24, 18, 6, '.grb'],
    ['REF_CY46', 24, 18, 6, '.grb'],
    ['inca-fc', 1, 6, 1, '.bil', False, 1.], # only up to 6 hours, it becomes too bad after that
    ['inca_plus-fc', 1, 6, 1, '.grb2', False, 1.]] # only up to 6 hours, it becomes too bad after that
simdf = pd.DataFrame(simdata, 
    columns=['name', 'init_interval', 'max_lead_time', 'lead_time_interval', 'grib_suffix',
             'accumulated', 'unit_factor'])

# model_vardata organized as
# model_vardata = {
#     'model': {
#         'variable': [accumulated, factor]
#     ...

model_vardata = {
    'alaro5' : {
        'precip': [True, 1.],
        },
    'arome' : {
        'precip': [True, 1.],
        'hail': [False, 1.],
        'lightning': [True, 1.],
        'sunshine': [True, 1/3600.]
        },
    'aromeesuite' : {
        'precip': [True, 1.],
        'hail': [False, 1.],
        'lightning': [True, 1.],
        'sunshine': [True, 1./3600.]
        },
    'aromeruc' : {
        'precip': [True, 1.],
        'hail': [False, 1.],
        'lightning': [True, 1.],
        'sunshine': [True, 1./3600.]
        },
    'aromerucesuite' : { 
        'precip': [True, 1.],
        'hail': [False, 1.],
        'sunshine': [True, 1./3600.]
        },
    'claef-members' : {
        'precip': [True, 1000.],
        'hail': [False, 1.],
        'lightning': [True, 1.],
        'sunshine': [True, 1/3600.]
        },
    'aromemf' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'cosmo1' : {
        'precip': [False, 1.],
        'sunshine': [True, 1.]
        },
    'cosmo1e' : {
        'precip': [False, 1.],
        'sunshine': [True, 1.]
        },
    'cosmo7' : {
        'precip': [False, 1.],
        'sunshine': [True, 1.]
        },
    'cosmod2' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'arpege' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'ecmwf' : {
        'precip': [True, 1.],
        'sunshine': [True, 1./3600.]
        },
    'ecmwf-mean' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'ecmwf-median' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'icon' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'icon-eu' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'icond2' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'claef-control' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'claef-mean' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'claef-median' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'laef-det' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'laef-mean' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'laef-median' : {
        'precip': [True, 1.],
        'sunshine': [True, 1.]
        },
    'CY46_1250m_DHC' : {
        'precip': [True, 1.],
        },
    'CY46_500m_DHC' : {
        'precip': [True, 1.],
        },
    'CY46_DOWN' : {
        'precip': [True, 1.],
        },
    'CY46_DOWN_HYDRO' : {
        'precip': [True, 1.],
        },
    'CY46_DOWN_HYDRO_CPL' : {
        'precip': [True, 1.],
        },
    'GL2B' : {
        'precip': [True, 1.],
        },
    'GL6J' : {
        'precip': [True, 1.],
        },
    'GL7J' : {
        'precip': [True, 1.],
        },
    'OPER' : {
        'precip': [True, 1.],
        },
    'REF_CY46' : {
        'precip': [True, 1.],
        },
    'inca-fc' : {
        'precip': [False, 1.],
        'sunshine': [True, 1.]
        },
    'inca_plus-fc' : {
        'precip': [False, 1.],
        'sunshine': [True, 1.]
        }
}
path="/ment_arch3/aladin/PRECIP_ARCH/" # standard precipitation archive
path2="/arome_arch/aladin/ARCHIVE/AROMEaut/" # AROME archive (alternative)

verification_subdomains = {
    'Vienna' : [16., 16.66, 48., 48.4],
    'Lower_Austria' : [14.33, 17.33, 47.4, 49.2],
    'Upper_Austria' : [12.66, 15., 47.4, 49.],
    'Salzburg' : [12., 14.3, 46.8, 48.2],
    'Tyrol' : [10., 13., 46.6, 48.2],
    'Vorarlberg' : [9.33, 10.33, 46.8, 47.8],
    'Carinthia' : [12.66, 15.33, 46.2, 47.2],
    'Styria' : [13.33, 16.33, 46.2, 48.],
    'Burgenland' : [16., 17.33, 46.6, 48.2],
    'East_Tyrol' : [12., 13., 46.6, 47.2],
    'Austria' : [9.33, 17.33, 46.2, 49.2],
    'Wechsel' : [15.58, 16.24, 47.30, 47.76],
    'Nockberge' : [13.85, 14.51, 46.75, 47,21],
    'Kitzbuehel' : [12.10, 12.76, 47.24, 47.70],
    # HYENA VERBUND RIVER BASINS
    'Drau': [12.066, 15.101, 46.326, 47.203],
    'Enns': [13.266, 15.569, 47.147, 48.283],
    'Inn_Salzach': [11.490, 13.767, 46.965, 48.607],
    'Mur': [13.253, 16.178, 46.558, 47.860],
    'Obere_Donau': [ 8.098, 13.513, 47.048, 49.479],
    'Obere_Inn': [ 9.524, 12.397, 46.288, 47.730],
    'Untere_Donau': [13.074, 16.611, 47.367, 49.020],
    # OTHER
    'Hallein': [12.1, 14.1, 47.20, 48.20],
    'Finland': [20.0, 29.0, 59.00, 62.50],
    'Custom' : [None, None, None, None]
}
subdomain_precip_thresholds = {
    'Vienna' :        { 'draw_avg' : 5., 'draw_max' :  20., 'score_avg' : 1., 'score_max' : 2. },
    'Lower_Austria' : { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Upper_Austria' : { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Salzburg' :      { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Tyrol' :         { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Vorarlberg' :    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Carinthia' :     { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Styria' :        { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Burgenland' :    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'East_Tyrol' :    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Austria' :       { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Wechsel' :       { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Nockberge' :     { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Kitzbuehel' :    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Drau':           { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Enns':           { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Inn_Salzach':    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Mur':            { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Obere_Donau':    { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Obere_Inn':      { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Untere_Donau':   { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Hallein':        { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Finland':        { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. },
    'Custom' :        { 'draw_avg' : 5., 'draw_max' : 100., 'score_avg' : 1., 'score_max' : 5. }
}

default_subdomains = ['Austria', 'Lower_Austria', 'Upper_Austria', 'Salzburg', 'Tyrol', 'Vorarlberg', 'Carinthia',
                      'Styria', 'Burgenland', 'Vienna', 'Wechsel', 'Nockberge', 'Kitzbuehel']

GRIB_indicators_inca_plus = [{
     'parameterNumber' : 8,
     'typeOfGeneratingProcess' : 2,
     'forecastTime' : None}]

def get_norm(levels, cmap):
    norm = bnorm(levels,ncolors=cm.get_cmap(cmap).N)
    return norm

def get_rain_levels_cmap_norm():
    levels = [0., 0.1, 0.2, 0.5,  1.0,  5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,  50.0, 100.0]
    # if args.cmap == "mycolors":
    mycolors = [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
            (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
            (150,0,150),(255,0,0)]
    mycolors2 = tuple(np.array(mycolors)/255.)    
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


rain_levels, rain_cmap, rain_norm = get_rain_levels_cmap_norm()

param_pars =  {
    # 2, 6, 21, 11, 6
     1:    {'surface':           {'name': 'MLSP [Pa]',
                                  'fname': 'pressure',
                                  'level': 'Surface'},
            'heightAboveGround': {'name': 'Pressure [Pa]',
                                  'fname': 'pressure',
                                  'level': '{:d} mAGL'}},
     2:    {'meanSea':           {'name': 'MSLP [Pa]',
                                  'fname': 'mslp',
                                  'level': '',
                                  'factor': 1./100.,
                                  'cmap': 'gist_ncar',
                                  'levels': range(970, 1026, 1)}},
     6:    {'isothermZero':      {'name': 'Height of the 0$^\circ$C isotherm',
                                  'fname': 'ZeroIsotherm',
                                  'level': '',
                                  'levels': range(0, 5001, 100)}},
     11:   {'surface':           {'name': 'Surface Temperature [$^\circ$C]',
                                  'fname': 'SurfTemp',
                                  'level': '',
                                  'offset': -273.15,
                                  'levels': range(-24, 51, 4)}},
                                  # THIS IS ONLY THE COLUMN MAX FOR 15 m AGL!!!
     21:   {'heightAboveGround': {'name': 'Composite Simulated Reflectivity [dBz]',
                                  'fname': 'SimReflZ',
                                  'level': '{:d} mAGL',
                                  'norm': get_norm([0., 11.6, 13.8, 18.8, 21.8, 26.5, 29.8, 33.8, 37.8, 41.6, 45.8,
                                                    50., 53.9, 57.8, 61.7], nclcmaps.cmap('rad_aut')),
                                  'cmap': nclcmaps.cmap('rad_aut'),
                                  # 'cmap': nclcmaps.cmap('nexrad_b'),
                                  'levels': [0., 11.6, 13.8, 18.8, 21.8, 26.5, 29.8, 33.8, 37.8, 41.6, 45.8, 50.,
                                             53.9, 57.8, 61.7]}},
                                  # 'levels': range(0,81,5)}},
     61:    {'surface':          {'name': 'Total Precipitation [mm]',
                                  'fname': 'TotPrecip',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     130:  {'surface':           {'name': '10 m Wind Gusts U [m s$^{-1}$]',
                                  'fname': 'GustsU',
                                  'level': '',
                                  'levels': range(4, 49, 4)}},
     131:  {'surface':           {'name': '10 m Wind Gusts V [m s$^{-1}$]',
                                  'fname': 'GustsV',
                                  'level': '',
                                  'levels': range(0, 51, 2)}},
     1300:  {'surface':          {'name': '10 m Wind Gusts [m s$^{-1}$]',
                                  'fname': '10mGusts',
                                  'level': '',
                                  'cmap': nclcmaps.cmap('WhiteBlueGreenYellowRed'),
                                  'levels': range(0, 51, 2)}},
     171:   {'surface':          {'name': 'Total Cloud Cover',
                                  'fname': 'TotalCloudCover',
                                  'level': '',
                                  'levels': np.arange(0, 1.01, 0.1)}},
     173:   {'surface':          {'name': 'Blended Cloud Cover (red: low, green: mid, blue: high)',
                                  'fname': 'LowClouds',
                                  'level': '',
                                  'cmap': nclcmaps.non_normalized_cmap('BlackRed'),
                                  'levels': np.arange(0, 1.01, 0.1)}},
     174:   {'surface':          {'name': ' ',
                                  'fname': 'MidClouds',
                                  'level': '',
                                  'cmap': nclcmaps.non_normalized_cmap('BlackGreen'),
                                  'levels': np.arange(0, 1.01, 0.1)}},
     175:   {'surface':          {'name': ' ',
                                  'fname': 'HighClouds',
                                  'level': '',
                                  'cmap': nclcmaps.non_normalized_cmap('BlackBlue'),
                                  'levels': np.arange(0, 1.01, 0.1)}},
     181:    {'surface':               {'name': 'rain [mm]',
                                  'fname': 'rain',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     184:    {'surface':                {'name': 'snow [mm]',
                                  'fname': 'snow',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     196:   {'surface':          {'name': 'Hail [mm h$^{-1}$]',
                                  'fname': 'Hail',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     197:    {'surface':          {'name': 'rain [mm]',
                                  'fname': 'rain',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     198:    {'surface':          {'name': 'snow [mm]',
                                  'fname': 'snow',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     199:    {'surface':          {'name': 'graupel [mm]',
                                  'fname': 'graupel',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     201:    {'surface':                {'name': 'graupel [mm]',
                                  'fname': 'graupel',
                                  'level': '',
                                  'levels': rain_levels,
                                  'cmap': rain_cmap,
                                  'norm': rain_norm}},
     246:   {'surface':          {'name': 'Lightnig Strikes [km$^{-2}$ h$^{-1}$]',
                                  'fname': 'Lightning',
                                  'level': '',
                                  'norm': get_norm([0., 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20,
                                                    25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120],
                                                   nclcmaps.cmap('ment_lightning2')),
                                  # 'norm': get_norm([0.1, 0.2, 0.3, 0.5, 0.7, 1., 1.2, 1.5], nclcmaps.cmap('ment_lightning')), 
                                  'cmap': nclcmaps.cmap('ment_lightning2'),
                                  # 'cmap': nclcmaps.cmap('ment_lightning'),
                                  'levels': [0., 0.1, 0.2, 0.3, 0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25,
                                             30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120]}},
                                  # 'levels': [0.1, 0.2, 0.3, 0.5, 0.7, 1., 1.2, 1.5]}},
                                  # 'levels': np.arange(0,10.1,0.5)}},
     248:   {'surface':          {'name': 'Sunshine duration during the last hour [s]',
                                  'fname': 'Sunshine',
                                  'level': '',
                                  #'factor': 1./3600.,
                                  'levels': np.arange(0, 3601., 300.)}}
    }

