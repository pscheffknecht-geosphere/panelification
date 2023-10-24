import pandas as pd
import matplotlib.cm as cm
import numpy as np
from matplotlib.colors import BoundaryNorm as bnorm
import matplotlib.colors as mplcolors

""" MOSTLY LOCAL GEOSPHERE SETTINGS 

Users may add their own subdomains for verification.
See documentation for details. This will be cleaned up in
a future version."""

inca_fc_paths = {
    'precip'        : "/mapp_arch2/mgruppe/arc/inca_l_fc/prec/{:s}/RR_FC_INCA-{:s}00.bil.gz",
    'sunshine'      : "/mapp_arch2/mgruppe/arc/inca_l_fc/prec/{:s}/SSD_FC_INCA-{:s}00.bil.gz",
}

inca_ana_paths = {
    'sunshine'      : "/mapp_arch/mgruppe/arc/inca_l/mslp/{:s}/INCA_SSD-{:s}.asc.gz",
    'gusts'         : {"UU": "/mapp_arch/mgruppe/arc/inca_l/wind/{:s}/INCA_UU-{:s}.asc.gz", # 2 components
                       "VV": "/mapp_arch/mgruppe/arc/inca_l/wind/{:s}/INCA_VV-{:s}.asc.gz"}
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
    'Finland': [23.0, 28.0, 59.00, 61.50],
    'Custom' : [None, None, None, None]
}

# use this value for all domains, specify other values if desired
subdomain_precip_thresholds = {
    'Default':        { 'draw_avg' : 2., 'draw_max' : 25., 'score_avg' : 1., 'score_max' : 5. }
}

default_subdomains = ["Austria", "Styria"]
