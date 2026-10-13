from matplotlib.colors import BoundaryNorm as bnorm
from matplotlib.colors import Normalize as nnorm
import nclcmaps
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mplcolors
import logging
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

""" THIS FILE CONTAINS A RANGE OF OPTIONS FOR THE PLOTS

For each parameter, this file contains the color maps, contour
levels, titles, and other settings. This is partly cosmectic
and partly necessary for the correct function of Panelification.

MODIFY AT YOUR OWN RISK!!!
"""

# string for use in the title of the entire panel
def title_part(args):
    title_parts = {
        'precip': 'Acc. Precip. [mm]',
        'precip2': 'Acc. Precip. [mm]',
        'precip3': 'Acc. Precip. [mm]',
        'sunshine': 'Acc. Sunshine Duration [h]',
        'lightning': 'lightning strikes [km$^{-2}$]',
        'gusts': 'wind gusts [m s$^{-1}$]',
        'hail': 'Hail [??]',
        'cma': 'Cloud Cover' if args.duration == 1 else 'Cloud Duration'
    }
    return title_parts[args.parameter]

    
# label for the color bar
def colorbar_label(args):
    colorbar_labels= {
    'precip': 'accumulated precipitation [mm]',
    'precip2': 'accumulated precipitation [mm]',
    'precip3': 'accumulated precipitation [mm]',
    'sunshine': 'sunshine duration [h]',
    'lightning': 'lightning strikes [km$^{-2}$]',

    'gusts': 'gust speed [m s$^{-1}$]',
    'hail': 'hail [??]',
    'cma' : 'Cloud cover' if args.duration == 1 else 'Cloud Duration'
    }
    return colorbar_labels[args.parameter]

# units of the parameter, used in the metadata of the score files
def get_units(args):
    units = {
        'precip': 'mm',
        'precip2': 'mm',
        'precip3': 'mm',
        'sunshine': 'h',
        'lightning': 'km-2',
        'gusts': 'm s-1',
        'hail': '1',
        'cma': 'h',
    }
    return units.get(args.parameter, '')

# thresholds for the calculation of the FSS depending on the parameter
def get_fss_thresholds(args):
    thresholds_for_fss = {
        'precip' :  [0.1, 1.,   5., 10.,  25.,  35.,  50.,  75., 100.],
        'precip2' : [1.0, 5.,  10., 20.,  50., 100., 150., 200., 250.],
        'precip3' : [5.0, 10., 20., 50., 100., 150., 200., 300., 400.], # for EXTREME events or LONG windows
        'sunshine' : [float(x) for x in range(args.duration)], # full hours, the duration cannot be exceeded
        'hail' : [0.5 * x for x in range(1, 9)], # the hail fields are scaled to 0 ... 4
        'gusts' : [5, 10, 15, 20, 25, 30, 40, 50, 70],
        'lightning' : [0.1*x for x in [1, 2, 5, 10, 25, 35, 50, 75, 100]],
        'cma': [x + 0.5 for x in range(args.duration)]
    }
    return thresholds_for_fss[args.parameter]

# percentile thresholds for the calculation of the FSS, none for the cloud mask
def get_fss_percentiles(args):
    return [] if args.parameter == 'cma' else [25, 50, 75, 90, 95]

# FSS window widths in grid points of the ~1 km verification grid, the same for all
# parameters unless set with --d_windows; all window lists are taken from here
DEFAULT_WINDOWS = [10, 20, 30, 40, 60, 80, 100, 120, 140, 160, 180, 200]

def get_windows(args):
    return list(args.d_windows) if args.d_windows else list(DEFAULT_WINDOWS)


# tick labels of the FSS rank plot, rows are the thresholds and, after an empty
# separator row, the percentile thresholds, columns are the windows
def get_axes_for_fss_rank_plot(args):
    window_xdict = get_window_xdict(args)
    threshold_ydict = get_threshold_ydict(args)
    return {
        'xticks' : range(len(window_xdict)),
        'yticks' : range(len(threshold_ydict)),
        'xdict' : window_xdict,
        'ydict' : threshold_ydict}


def get_threshold_ydict(args):
    """ FSS plot labels of the thresholds and percentile thresholds """
    labels = [f"{t:g}" for t in get_fss_thresholds(args)]
    percentiles = get_fss_percentiles(args)
    if percentiles:
        labels += [''] + [f"{p:d}%" for p in percentiles]
    return dict(enumerate(labels))


def get_window_xdict(args):
    """ FSS plot labels of the windows """
    return {index: str(value) for index, value in enumerate(get_windows(args))}


# RGB tuples for custom color maps
warn_colors = [
    (255, 255, 255), 
    (212, 212, 212),
    #(190, 190, 126),
    (126, 126, 126),
    (190, 190,   0),
    #(190, 190,  40),
    (255, 255,   0),
    (255, 169,   0),
    #(255, 126,   0),
    (255,  83,   0),
    #(212,  40,   0),
    (169,   0,   0),
    #(126,   0,   0),
    #( 83,   0,   0),
    ( 40,   0,   0)]

hail_colors = [
        (255, 255, 255),
        (210, 210, 210),
        (180, 180, 180),
        (150, 150, 150),
        (255, 255, 210),
        (255, 255, 180),
        (255, 255, 150),
        (255, 255, 125),
        (255, 210, 210),
        (255, 180, 180),
        (255, 150, 150),
        (255, 120, 125),
        (230, 210, 255),
        (230, 180, 255),
        (230, 150, 255),
        (230, 120, 255)]

precip3_colors = np.array([
    [1.00, 1.00, 1.00], # blue
    [0.85, 0.90, 1.00],
    [0.65, 0.70, 0.85],
    [0.55, 0.55, 0.80],
    [0.35, 0.35, 0.55],
    [0.85, 1.00, 0.85], # green
    [0.55, 0.90, 0.55],
    [0.30, 0.75, 0.30],
    [0.05, 0.45, 0.05],
    [1.00, 1.00, 0.55], # yellow
    [0.90, 0.70, 0.35],
    [0.85, 0.45, 0.25],
    [0.75, 0.15, 0.05],
    [1.00, 0.85, 1.00], # purple
    [0.95, 0.75, 0.95],
    [0.70, 0.45, 0.70],
    [0.40, 0.15, 0.40]])

def lightning_cmap_and_levels(args):
    levels = [0.1*x for x in [0., 5. , 10. ,  15.,  20.,  25.,  30.,  40.,  50., 70.]]
    mycolors =  warn_colors
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


def hail_cmap_and_levels(args):
    #levels = [0., 1. , 3. ,  5.,  10.,  15.,  20.,  30.,  40.,  50.,  60.,  80., 100., 150.,  200., 250.]
    levels = np.arange(0., 4.01, 0.25)
    mycolors = hail_colors 
    mycolors2 = tuple(np.array(mycolors)/255.)
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm

def gusts_cmap_and_levels(args):
    levels = [0., 1. , 2. ,  5.,  10.,  20.,  30.,  50.,  75., 100.]
    cmap = nclcmaps.cmap("WhiteBlueGreenYellowRed")
    norm = nnorm(vmin=0., vmax=100.)
    return levels, cmap, norm

def cma_cmap_and_levels(args):
    levels = [x for x in range(args.duration + 1)] #[0., 0.5, 1., 1.5, 2.0, 3.0]
    # cmap = nclcmaps.cmap("MPL_YlGnBu")
    cmap = nclcmaps.cmap("MPL_gist_gray") 
    cmap = truncate_colormap(cmap, 0.25, 1.)
    norm = nnorm(vmin=0., vmax=args.duration)
    return levels, cmap, norm

def sunshine_cmap_and_levels(args):
    levels = [x/3.*float(args.duration) for x in [0., 0.4, 0.8, 1.2, 1.6, 2., 2.4, 2.8, 3.]]
    mycolors = [(96, 96, 91), (149, 150, 128), (190, 192, 139), (216, 218, 138), (232, 231, 116),
        (242, 240, 96), (251, 250, 65), (255, 255, 0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


_MYCOLORS_DEFAULT = [(255,255,255),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
        (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
        (150,0,150),(255,0,0)]
_MYCOLORS_PRINT = [(255,255,255),(226,255,243),(189,255,241),(173,255,255),(133,231,255),(77,184,255),
        (65,97,240),(34,0,184),(95,50,230),(140,92,230),(201,148,255),(254,191,255),(242,107,199),
        (163,20,99),(254,0,0)]
# "new": L*-stretched variant of the print palette for better on-screen
# separation of the first 8 entries (generated by cmap_variations.py,
# remap_lightness_curved(PRINT_COLORS, 8, 100., 0.85*L*[7], 1.3, 1.5)).
_MYCOLORS_NEW = [(255,255,255),(213,251,236),(148,236,219),(93,208,209),(0,175,205),(0,134,220),
        (0,69,248),(0,0,216),(95,50,230),(140,92,230),(201,148,255),(254,191,255),(242,107,199),
        (163,20,99),(254,0,0)]


def _precip_mycolors(args):
    choice = getattr(args, 'colormap', 'default')
    if choice == 'print':
        return _MYCOLORS_PRINT
    if choice == 'new':
        return _MYCOLORS_NEW
    return _MYCOLORS_DEFAULT


def precip3_cmap_and_levels(args):
    # levels = [0.1, 0.2, 0.5, 1., 2., 5., 10., 15., 25., 35., 50., 75., 100., 150., 200., 300., 400., 500.]
    levels = [0., 0.5, 1.0, 2.0, 5.0,  10.0,  25.0, 50.0, 75.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0,  400.0]
    # norm = bnorm(levels,ncolors=len(precip3_colors))
    # cmap = mplcolors.ListedColormap(precip3_colors)
    mycolors = _precip_mycolors(args)
    # mycolors = [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
    #         (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
    #         (150,0,150),(255,0,0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm

def precip_cmap_and_levels(args):
    mycolors = None # only change if required
    if args.mode == 'normal' or args.mode == 'resampled':
        if args.duration >= 24 or args.parameter == "precip2":
            levels = [0., 1. , 3. ,  5.,  10.,  15.,  20.,  30.,  40.,  50.,  60.,  80., 100., 150.,  200., 250.]
        else:
            # levels = [0., 0.5, 1.5, 4.,   7. , 11. , 16. , 22. , 28. , 36. , 44. , 54. , 64. , 75. ,  87. , 100.0]
            # levels = [0., 0.1, 0.2, 0.5,  1.0,  5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0,  75.0, 100.0]
            levels = [0., 0.1, 0.2, 0.5,  1.0,  5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,  50.0, 100.0]
        if args.cmap == "mycolors":
            mycolors = _precip_mycolors(args)
            mycolors2 = tuple(np.array(mycolors)/255.)        
            norm = bnorm(levels,ncolors=len(mycolors))
            cmap = mplcolors.ListedColormap(mycolors2)
        else:
            norm = bnorm(levels,ncolors=cm.get_cmap(args.cmap).N)
            cmap = args.cmap
        cmap.set_over('orange')
    elif args.mode == 'diff':
        levels = [-100.,-50.,-45.,-40,-35.,-30.,-25.,-20.,-15.,-10.,-5.,-1.,-0.5,-0.2,-0.1,0.,0.1,0.2,0.5,1.,5.,10.,15.,20.,25.,30.,35.,40.,45.,50.,100.]
        cmap = 'NCV_jaisnd'
        norm = bnorm(levels,ncolors=cm.get_cmap(cmap).N)
    return levels, cmap, norm

# function to decide which function to call for each param
# dirty and primitive but it works, but a good candidate
# for refactoring
def get_cmap_and_levels(args):
    logger.info("Getting color map and contour levels for parameter "+args.parameter)
    if args.parameter == 'precip':
        return precip_cmap_and_levels(args)
    elif args.parameter == 'precip2':
        return precip_cmap_and_levels(args)
    elif args.parameter == 'precip3':
        return precip3_cmap_and_levels(args)
    elif args.parameter == 'hail':
        return hail_cmap_and_levels(args)
    elif args.parameter == 'lightning':
        return lightning_cmap_and_levels(args)
    elif args.parameter == 'sunshine':
        return sunshine_cmap_and_levels(args)
    elif args.parameter == 'gusts':
        return gusts_cmap_and_levels(args)
    elif args.parameter == 'cma':
        return cma_cmap_and_levels(args)


# https://stackoverflow.com/questions/18926031/how-to-extract-a-subset-of-a-colormap-as-a-new-colormap-in-matplotlib
def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    new_cmap = mplcolors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap
