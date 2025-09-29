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
title_part = {
    'precip': 'Acc. Precip. [mm]',
    'precip2': 'Acc. Precip. [mm]',
    'precip3': 'Acc. Precip. [mm]',
    'sunshine': 'Acc. Sunshine Duration [h]',
    'lightning': 'lightning strikes [km$^{-2}$]',
    'gusts': 'wind gusts [m s$^{-1}$]',
    'hail': 'Hail [??]'
}
# label for the color bar
colorbar_label = {
    'precip': 'accumulated precipitation [mm]',
    'precip2': 'accumulated precipitation [mm]',
    'precip3': 'accumulated precipitation [mm]',
    'sunshine': 'sunshine duration [h]',
    'lightning': 'lightning strikes [km$^{-2}$]',
    'gusts': 'gust speed [m s$^{-1}$]',
    'hail': 'hail [??]'
}

# thresholds for the calculation of the FSS depending on the parameter
def get_fss_thresholds(args):
    thresholds_for_fss = {
        'precip' :  [0.1, 1.,   5., 10.,  25.,  35.,  50.,  75., 100., 99999.],
        'precip2' : [1.0, 5.,  10., 20.,  50., 100., 150., 200., 250., 99999.],
        'precip3' : [5.0, 10., 20., 50., 100., 150., 200., 300., 400., 99999.], # for EXTREME events or LONG windows
        'sunshine' : list(np.arange(0., 1., 1/6.)) + [999999],
        'hail' : [1, 2, 5, 10, 25, 35, 50, 75, 100, 99999],
        'gusts' : [5, 10, 15, 20, 25, 30, 40, 50, 70, 99999],
        'lightning' : [0.1*x for x in [1, 2, 5, 10, 25, 35, 50, 75, 100]] + [99999]
    }
    return thresholds_for_fss[args.parameter]

# customize the tick labels for each parameter
def make_fss_axis_sunshine(args):
    ydict = {}
    for idx, val in enumerate(get_fss_thresholds(args)[:-1]):
        ydict[idx] = str(int(args.duration*val))
        maxval = val
    ydict[maxval+1] = ''
    for idx, val in enumerate(['25%', '50%', '75%', '90%', '95%']):
        ydict[maxval+2+idx] = val
    return ydict


def get_axes_for_fss_rank_plot(args):
    ax_ticks = {
    'precip' : {
        'xticks' : range(12),
        'yticks' : range(15),
        'ydict': {
            0 : '0.1', 1 : '1', 2 : '5', 3 : '10', 4 : '25', 5 : '35', 6 : '50', 7 : '75', 
            8 : '100', 9 : '', 10 : '25%', 11 : '50%', 12 : '75%', 13 : '90%', 14 : '95%'},
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        },
    'precip2' : {
        'xticks' : range(12),
        'yticks' : range(15),
        'ydict': {
            0 : '1', 1 : '5', 2 : '10', 3 : '20', 4 : '50', 5 : '100', 6 : '150', 7 : '200',
            8 : '250', 9 : '', 10 : '25%', 11 : '50%', 12 : '75%', 13 : '90%', 14 : '95%'},
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        },
    'precip3' : {
        'xticks' : range(12),
        'yticks' : range(15),
        'ydict': {
            0 : '5', 1 : '10', 2 : '20', 3 : '50', 4 : '100', 5 : '150', 6 : '200', 7 : '300', 
            8 : '400', 9 : '', 10 : '25%', 11 : '50%', 12 : '75%', 13 : '90%', 14 : '95%'},
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        },
    'sunshine' : {
        'xticks' : range(12),
        'yticks' : range(14),
        'ydict': make_fss_axis_sunshine(args),
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        },
    'hail' : {
        'xticks' : range(12),
        'yticks' : range(14),
        'ydict': {
            0 : '0.5', 1 : '1.0', 2 : '1.5', 3 : '2.0', 4 : '2.5', 5 : '3.0', 6 : '3.5', 7 : '4.0', 
            8 : '', 9 : '25%', 10 : '50%', 11 : '75%', 12 : '90%', 13 : '95%'},
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        },
    'lightning' : {
        'xticks' : range(12),
        'yticks' : range(15),
        'ydict': {
            0 : '0.1', 1 : '0.2', 2 : '.5', 3 : '1', 4 : '2.5', 5 : '3.5', 6 : '5.0', 7 : '7.5', 
            8 : '10.0', 9 : '', 10 : '25%', 11 : '50%', 12 : '75%', 13 : '90%', 14 : '95%'},
        'xdict' : {
            0 : '10', 1 : '20', 2 : '30', 3 : '40', 4 : '60', 5 : '80', 6 : '100', 7 : '120', 
            8 : '140', 9 : '160', 10 : '180', 11 : '200'}
        }
    }
    return ax_ticks[args.parameter]
        
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


def sunshine_cmap_and_levels(args):
    levels = [x/3.*float(args.duration) for x in [0., 0.4, 0.8, 1.2, 1.6, 2., 2.4, 2.8, 3.]]
    mycolors = [(96, 96, 91), (149, 150, 128), (190, 192, 139), (216, 218, 138), (232, 231, 116),
        (242, 240, 96), (251, 250, 65), (255, 255, 0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


def precip3_cmap_and_levels(args):
    # levels = [0.1, 0.2, 0.5, 1., 2., 5., 10., 15., 25., 35., 50., 75., 100., 150., 200., 300., 400., 500.]
    levels = [0., 0.5, 1.0, 2.0, 5.0,  10.0,  25.0, 50.0, 75.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0,  400.0]
    # norm = bnorm(levels,ncolors=len(precip3_colors))
    # cmap = mplcolors.ListedColormap(precip3_colors)
    mycolors = [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
            (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
            (150,0,150),(255,0,0)]
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
            if not args.print_colors:
                mycolors = [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
                        (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
                        (150,0,150),(255,0,0)]
            else:
                mycolors = [(255,255,255),(226,255,243),(189,255,241),(173,255,255),(133,231,255),(77,184,255),
                        (65,97,240),(34,0,184),(95,50,230),(140,92,230),(201,148,255),(254,191,255),(242,107,199),
                        (163,20,99),(254,0,0)]
            mycolors2 = tuple(np.array(mycolors)/255.)        
            norm = bnorm(levels,ncolors=len(mycolors))
            cmap = mplcolors.ListedColormap(mycolors2)
        else:
            norm = bnorm(levels,ncolors=cm.get_cmap(args.cmap).N)
            cmap = args.cmap
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



