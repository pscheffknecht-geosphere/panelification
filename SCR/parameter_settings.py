from matplotlib.colors import BoundaryNorm as bnorm
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mplcolors
#import more_color_maps

""" THIS FILE CONTAINS A RANGE OF OPTIONS FOR THE PLOTS

For each parameter, this file contains the color maps, contour
levels, titles, and other settings. This is partly cosmectic
and partly necessary for the correct function of Panelification.

MODIFY AT YOUR OWN RISK!!!
"""

# string for use in the title of the entire panel
title_part = {
    'precip': 'Acc. Precip. [mm]',
    'sunshine': 'Acc. Sunshine Duration [h]',
    'lightning': 'lightning strikes [km$^{-2}$]',
    'hail': 'Hail [??]'
}
# label for the color bar
colorbar_label = {
    'precip': 'accumulated precipitation [mm]',
    'sunshine': 'sunshine duration [h]',
    'lightning': 'lightning strikes [km$^{-2}$]',
    'hail': 'hail [??]'
}

# thresholds for the calculation of the FSS depending on the parameter
def get_fss_thresholds(args):
    thresholds_for_fss = {
        'precip' : [0.1,1.,5.,10.,25.,35.,50.,75.,100., 99999.],
        'sunshine' : list(np.arange(0., 1., 1/6.)) + [999999],
        'hail' : [1, 2, 5, 10, 25, 35, 50, 75, 100, 99999],
        'lightning' : [0.1*x for x in [1, 2, 5, 10, 25, 35, 50, 75, 100]] + [99999]
        # 'sunshine' : [x*args.duration for x in range(0, 1, 1/6.)] + [999999]
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
        'yticks' : range(15),
        'ydict': {
            0 : '0.1', 1 : '1', 2 : '5', 3 : '10', 4 : '25', 5 : '35', 6 : '50', 7 : '75', 
            8 : '100', 9 : '', 10 : '25%', 11 : '50%', 12 : '75%', 13 : '90%', 14 : '95%'},
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
    (255, 255, 212), 
    (255, 255, 169), 
    (255, 255, 126), 
    (255, 255,  83), 
    (255, 230,  40), 
    (255, 205,   0), 
    (255, 180,   0), 
    (255, 155,   0), 
    (255, 130,   0), 
    (255, 105,   0), 
    (255,  80,   0), 
    (255,  55,   0), 
    (255,  30,   0), 
    (255,   0,   0)]

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



def lightning_cmap_and_levels(mode, args):
    levels = [0.1*x for x in [0., 1. , 2. ,  5.,  10.,  20.,  30.,  50.,  75., 100.]]
    mycolors =  warn_colors
         #  [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
         #   (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
         #   (150,0,150),(255,0,0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


def hail_cmap_and_levels(mode, args):
    levels = [0., 1. , 3. ,  5.,  10.,  15.,  20.,  30.,  40.,  50.,  60.,  80., 100., 150.,  200., 250.]
    mycolors = warn_colors 
         #  [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
         #   (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
         #   (150,0,150),(255,0,0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    return levels, cmap, norm


def sunshine_cmap_and_levels(mode, args):
    levels = [x/3.*float(args.duration) for x in [0., 0.4, 0.8, 1.2, 1.6, 2., 2.4, 2.8, 3.]]
    mycolors = [(96, 96, 91), (149, 150, 128), (190, 192, 139), (216, 218, 138), (232, 231, 116),
        (242, 240, 96), (251, 250, 65), (255, 255, 0)]
    mycolors2 = tuple(np.array(mycolors)/255.)        
    norm = bnorm(levels,ncolors=len(mycolors))
    cmap = mplcolors.ListedColormap(mycolors2)
    # levels = np.arange(0., 3600.1, 300) * args.duration
    # cmap = 'MPL_rainbow'
    # norm = bnorm(levels,ncolors=cm.get_cmap(cmap).N)
    return levels, cmap, norm



def precip_cmap_and_levels(mode, args):
    mycolors = None # only change if required
    if mode == 'None' or mode == 'resampled':
        if args.duration >= 24:
            levels = [0., 1. , 3. ,  5.,  10.,  15.,  20.,  30.,  40.,  50.,  60.,  80., 100., 150.,  200., 250.]
        else:
            levels = [0., 0.1, 0.2, 0.5,  1.0,  5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0,  50.0, 100.0]
        if args.cmap == "mycolors":
            mycolors = [(255.,255.,255.),(0,254,150),(0,254,200),(0,254,254),(0,200,254),(0,150,254),
                    (0,50,254),(50,0,254),(100,0,254),(150,0,254),(200,0,254),(250,0,254),(200,0,200),
                    (150,0,150),(255,0,0)]
            mycolors2 = tuple(np.array(mycolors)/255.)        
            norm = bnorm(levels,ncolors=len(mycolors))
            cmap = mplcolors.ListedColormap(mycolors2)
        else:
            norm = bnorm(levels,ncolors=cm.get_cmap(args.cmap).N)
            cmap = args.cmap
    elif mode == 'diff':
        levels = [-100.,-50.,-45.,-40,-35.,-30.,-25.,-20.,-15.,-10.,-5.,-1.,-0.5,-0.2,-0.1,0.,0.1,0.2,0.5,1.,5.,10.,15.,20.,25.,30.,35.,40.,45.,50.,100.]
        cmap = 'NCV_jaisnd'
        norm = bnorm(levels,ncolors=cm.get_cmap(cmap).N)
    return levels, cmap, norm

# function to decide which function to call for each param
# dirty and primitive but it works, but a good candidate
# for refactoring
def get_cmap_and_levels(mode, args):
    if args.parameter == 'precip':
        return precip_cmap_and_levels(mode, args)
    elif args.parameter == 'hail':
        return hail_cmap_and_levels(mode, args)
    elif args.parameter == 'lightning':
        return lightning_cmap_and_levels(mode, args)
    elif args.parameter == 'sunshine':
        return sunshine_cmap_and_levels(mode, args)



