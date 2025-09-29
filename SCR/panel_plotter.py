import argparse
import datetime as dt
import os
import sys
import glob
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
from matplotlib.colors import BoundaryNorm as bnorm
from matplotlib.colors import Colormap
import matplotlib.colors as mplcolors
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
#from mpl_toolkits.axes_grid.inset_locator import inset_axes
from matplotlib.patches import Rectangle
#import more_color_maps
import numpy as np
from model_parameters import verification_subdomains
import parameter_settings
from joblib import Parallel, delayed
from multiprocessing import Pool
import pickle
import scipy.ndimage as ndimage

from paths import PAN_DIR_TMP, PAN_DIR_PLOTS, PAN_DIR_SCR

import logging
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)


def get_array_edge(arr):
    nx, ny = np.shape(arr)
    e1 = arr[0     , :]
    e2 = arr[1::, ny-1]
    e3 = arr[nx-1, 0:ny-1][::-1]
    e4 = arr[:-1, 0][::-1]
    return np.concatenate((e1, e2, e3, e4), axis=0)


def add_borders(axis):
    borders = cfeature.NaturalEarthFeature(
    category='cultural', name='admin_0_boundary_lines_land',
    scale='10m', facecolor='none')
    axis.add_feature(borders, edgecolor='black', lw=0.5)
    axis.add_feature(cfeature.COASTLINE)


def add_scores(ax, sim, rank_colors):
    """Adds text to a subplot axis that prints the scores
    ax ......... axis object from plt.subplots
    sim ........ dictionary for the corresponding model
    color ...... list of colors for each rank"""
    ax.text(0.1, 0.9, "BIAS: {:.3f} ({})".format(sim['bias_real'], sim['rank_bias']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size=8, backgroundcolor=rank_colors[sim['rank_bias']])
    ax.text(0.1, 0.75, "MAE: {:.3f} ({})".format(sim['mae'], sim['rank_mae']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size=8, backgroundcolor=rank_colors[sim['rank_mae']])
    ax.text(0.1, 0.60, "RMSE: {:.3f} ({})".format(sim['rms'], sim['rank_rms']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size=8, backgroundcolor=rank_colors[sim['rank_rms']])
    ax.text(0.1, 0.45, "R$_{{pearson}}$: {:.3f} ({})".format(sim['corr'], sim['rank_corr']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size=8, backgroundcolor=rank_colors[sim['rank_corr']])
    if sim['d90'] < 9999.:
        ax.text(0.1, 0.30, "D$_{{90}}$: {:.1f} km ({})".format(sim['d90'], sim['rank_d90']), va='top', ha='left',
                rotation='horizontal', rotation_mode='anchor',
                transform=ax.transAxes,size=8, backgroundcolor=rank_colors[sim['rank_d90']])
    # ax.text(1.00, 1.03, "AVG Rank: {:.2f} ({})".format(sim['average_rank'], sim['rank_average_rank']), va='top', ha='right',
    #         rotation='horizontal', rotation_mode='anchor',
    #         transform=ax.transAxes,size='large', 
    #         bbox=dict(boxstyle='round', fc=rank_colors[sim['rank_average_rank']], ec='black', pad=0.2))
    return ax


def make_fss_rank_plot_axes(ax, args):
    """ Add tick labels to the FFS rank plot
    ax ............. axes object from pyplot.add_axes
    args ........... parsed command line arguments"""
    all_ticks = parameter_settings.get_axes_for_fss_rank_plot(args)
    xticks = all_ticks['xticks']
    yticks = all_ticks['yticks']
    ax.set_xticks(xticks)
    ax.set_yticks(yticks)
    xdict = all_ticks['xdict']
    ydict = all_ticks['ydict']
    xlabels = [xticks[i] if t not in xdict.keys() else xdict[t] for i,t in enumerate(xticks)]
    ylabels = [yticks[i] if t not in ydict.keys() else ydict[t] for i,t in enumerate(yticks)]
    # use ha and va to place labels between tickmarks
    ax.set_xticklabels(xlabels, rotation='vertical') #, ha='left')
    ax.set_yticklabels(ylabels) #, va='top')
    ax.tick_params(axis='both', which='major', labelsize=7)
    # return ax


def pick_color_OK(val, threshold):
    # pick a value for the previously white area
    low = np.array([0., 30., 10., 255.]) / 255.
    high = np.array([80., 255., 120., 255.]) / 255.
    t = (val - threshold) / (1. - threshold)
    t = 0. if t < 0. else t
    t = 1. if t > 1. else t
    return t * high + (1. - t) * low

# initial test
def pick_color_notOK(val, ovest):
    t = ovest
    return t

def make_triangle(x0, y0, scale_in):
    scale = abs(scale_in)
    pad = 0.15
    centerX = x0 + 0.5
    centerY = y0 + (pad + 1.) / 3.
    vAx = scale * (x0 + pad - centerX)
    vAy = scale * (y0 + pad - centerY)
    vBx = scale * (x0 + 1. - pad - centerX)
    vBy = vAy
    vCx = 0.
    vCy = scale * (y0 + 1. - pad - centerY)
    xt = np.array([vAx, vBx, vCx, vAx]) + centerX
    yt = np.array([vAy, vBy, vCy, vAy]) + centerY
    if scale_in < 0.:
        yt = -(yt - (y0 + 0.5)) + y0 + 0.5
    return xt - 0.5, yt - 0.5


def add_skill_outline(ax, sim):
    ny, nx = sim['fss_ranks'].shape
    ranks = sim['fss_ranks']
    for yy in range(0, ny):
        for xx in range(0, nx):
            if yy < ny-1:
                if any(ranks[yy:yy+2, xx] == 1) and ranks[yy, xx] != ranks[yy+1, xx]:
                    ax.plot([xx-0.5, xx+0.5], [yy+0.5, yy+0.5], 'k', lw=.5, zorder=999)
            if xx < nx-1:
                if any(ranks[yy, xx:xx+2] == 1) and ranks[yy, xx] != ranks[yy, xx+1]:
                    ax.plot([xx+0.5, xx+0.5], [yy-0.5, yy+0.5], 'k', lw=.5, zorder=999)

def add_fss_plot_new(ax, sim, rank_vmax, jj, args):
    fss_rank_cols = ['white']*rank_vmax
    fss_rank_cols[0:5] = ['black', 'firebrick', 'limegreen', 'gold', 'silver', 'darkorange']
    if args.fss_mode == 'relative':
        fss_cmap = mpl.cm.get_cmap("RdYlBu")
    elif args.fss_mode == 'ranks':
        fss_cmap = mplcolors.ListedColormap(fss_rank_cols)
    # add rank diagram for FSS
    extent = (0, sim['fss_ranks'].shape[1], sim['fss_ranks'].shape[0], 0)
    ny, nx = sim['fss_ranks'].shape
    pad = 0.05
    g_norm = bnorm(np.arange(0.5, 1.01, 0.1), ncolors=mpl.colormaps['Greens'].N)
    rb_norm = bnorm(np.arange(-.22, .221, .04), ncolors=mpl.colormaps['RdBu'].N)
    cmapG = mpl.colormaps['Greens']
    cmapBR = mpl.colormaps['RdBu']
    for yy in range(ny):
        for xx in range(nx):
            xedge = -0.5 + np.array([xx+pad, xx+pad, xx+1-pad, xx+1-pad, xx+pad])
            yedge = -0.5 + np.array([yy+pad, yy+1-pad, yy+1-pad, yy+pad, yy+pad])
            xedge_rank = -0.5 + np.array([xx+pad, xx+1-pad, xx+1-pad, xx+pad])
            yedge_rank = -0.5 + np.array([yy+pad, yy+1-pad, yy+pad, yy+pad])
            col = (1, 1, 1, 1) # white
            if args.greens:
                if sim['fss_ranks'][yy, xx] > 1: # and sim['fssf'][yy, xx] >= sim['fssf_thresholds'][yy]:
                    col = cmapG(g_norm(sim['fssf'].values[yy, xx]))
            if args.fss_mode == 'relative':
                fss_rel = sim['fss_rel'][yy, xx] 
                pos_in_cmap = np.clip(0.5 + fss_rel * 10., -1., 1.) # map [-.05, .05] to [0, 1]
                col = fss_cmap(pos_in_cmap)
            elif args.fss_mode == 'ranks' and sim['fss_ranks'][yy, xx] > 1 and sim['fss_ranks'][yy, xx] < 6:
                rcol = fss_rank_cols[sim['fss_ranks'][yy, xx]]
                radius = 0.25 if args.greens else 0.45
                ax.fill(xedge_rank, yedge_rank, facecolor=rcol, zorder=999)
                # circle = mpl.patches.Circle((xx, yy), radius, color=rcol, zorder=999)
                # ax.add_patch(circle)
            if sim['fss_ranks'][yy, xx] == 1: # and yy < 9: #only for bad but not nan
                bias = sim['fss_overestimated'].to_numpy()[yy, xx]
                if yy > 9:
                    bias = 0 # workaround for bug
                xedget, yedget = make_triangle(xx, yy, np.clip(-bias / 0.22, -1., 1.)) # <-- needs scaled bias to have .22 mapped to 1. for max triangle
                col = cmapBR(rb_norm(bias)) # <-- needs no scaled bias because norm scales the interval to [-1, 1]
            if yy == 9 or sim['fss_ranks'][yy, xx] == 0:
                ax.plot(xedge[[0, 2]], yedge[[0, 2]], 'gray', lw=0.5, zorder=999)
                ax.plot(xedge[[1, 3]], yedge[[1, 3]], 'gray', lw=0.5, zorder=999)
                # col = 'black' # fix red separation line for fiels that contain nans
            else:
                ax.fill(xedge, yedge, facecolor=col, zorder=777)
            if sim['fss_ranks'][yy, xx] == 1 and yy < 9: #only for bad but not nan
                ax.fill(xedget, yedget, facecolor='white', zorder=999)


    make_fss_rank_plot_axes(ax, args)
    ax.set_xlim([-0.5, nx-0.5])
    ax.set_ylim([ny-0.5, -0.5])
    add_skill_outline(ax, sim)
            

def add_fss_plot(ax, sim, rank_vmax, jj, args):
    """ Generate the FSS rank plot
    ax .......... axes object from pyplot.add_axes
    sim ......... dictionary for the correspondign model
    rank_vmax ... maximum rank (corresponds to the number of simulations that
                  are being compared
    jj .......... integer, plot index within the panel
    args ........ command line arguments"""
    fss_rank_cols = ['white']*rank_vmax
    fss_rank_cols[0:5] = ['black', 'red', 'limegreen', 'gold', 'silver', 'darkorange']
    fss_cmap = mplcolors.ListedColormap(fss_rank_cols)
    # add rank diagram for FSS
    extent = (0, sim['fss_ranks'].shape[1], sim['fss_ranks'].shape[0], 0)
    if args.fss_mode == "ranks":
        ax.imshow(sim['fss_ranks'], cmap = fss_cmap, extent=extent, vmin = 0., vmax=rank_vmax)
    elif args.fss_mode == "relative":
        low_mask = np.where(sim['fss_rel'] < -5., 0., np.nan)
        high_mask = np.where(sim['fss_rel'] > 5., 0., np.nan)
        ax.imshow(sim['fss_rel'], cmap = "RdYlBu", vmin = -0.05, vmax=0.05, extent=extent)
        ax.imshow(low_mask, cmap="Greys", vmin=-0.3, vmax=1., extent=extent)
        ax.imshow(high_mask, cmap="Greys", vmin=-1., vmax=0., extent=extent)
    ovest = sim['fss_overestimated']
    ovest = np.where(sim['fss_ranks'] == 1, ovest, np.nan)
    ax.imshow(ovest, cmap='coolwarm_r', vmin=-1., vmax=1., extent=extent)
    ax.grid(color='w', linewidth=0.5)
    ax = make_fss_rank_plot_axes(ax, args)

def prep_plot_data(sim, obs, mode):
    """ Select the correct data for plotting
    sim ........ dictionary for the model
    obs ........ dictionary for the observations
    mode ....... string, select whether to plot original or resampled fields"""
    if mode == 'normal':
        precip_data = sim['precip_data']
        lon = sim['lon']
        lat = sim['lat']
    elif mode == 'resampled':
        precip_data = sim['precip_data_resampled']
        lon = sim['lon_resampled']
        lat = sim['lat_resampled']
    return precip_data, lon, lat


def draw_solo_colorbar(levels, cmap, norm, tmp_string, args):
    """ Draw a colorbar to be used for the panel
    levels ......... np.array with cntour levels
    cmap ........... matplotlib colormap
    norm ........... matplotlib norm for use of non-linear contours
    tmp_string ..... temporary path
    args ........... command line arguments"""
    fig = plt.figure(figsize=(12, 0.9), dpi=args.dpi)
    if args.fss_mode == "relative":
        rel_norm = bnorm(np.arange(-0.05, 0.0501, 0.0025), ncolors=mpl.cm.get_cmap('RdYlBu').N)
        ticks = np.arange(-0.05, 0.0501, 0.025)
        cb_rel = mpl.colorbar.ColorbarBase(ax_rel, cmap="RdYlBu", ticks=ticks,
            orientation='horizontal', extend='both', norm=rel_norm)
        cb_rel.set_label("Deviation from mean useful FSS value")
    else:
        ax_rr = fig.add_axes([0.1,0.8,0.8,0.1])
    cb = mpl.colorbar.ColorbarBase(ax_rr, cmap=cmap, norm=norm, 
        orientation='horizontal', ticks=levels, extend='max')
    cb.cmap.set_bad('gray')
    cb.set_label(parameter_settings.colorbar_label[args.parameter])
    plt.savefig(f"{PAN_DIR_TMP}/{tmp_string}/cbar.png")

def draw_RGB_colorbars(tmp_string, args):
    """ Draw colorbars for greens, blues and reds used to show FSS score
    and frequency bias for no-skill window-threshold-combos"""
    fig = plt.figure(figsize=(12, 0.9), dpi=args.dpi)
    if args.greens:
        ax_green = fig.add_axes([0.525, 0.8, 0.45, 0.1])
        ax_bias  = fig.add_axes([0.025, 0.8, 0.45, 0.1])
        rel_norm = bnorm(np.arange(0.5, 1.01, 0.1), ncolors=mpl.colormaps.get_cmap('Greens').N)
        ticks = np.arange(0.5, 1.01, 0.1)
        cb_rel = mpl.colorbar.ColorbarBase(ax_green, cmap="Greens", ticks=ticks,
            orientation='horizontal', norm=rel_norm)
        cb_rel.set_label("FSS Value")
    else:
        ax_bias  = fig.add_axes([0.275, 0.8, 0.45, 0.1])
    rel_normb = bnorm(100. * np.arange(-.22, .221, .04), ncolors=mpl.colormaps['RdBu'].N)
    ticksb = 100. * np.arange(-.22, .221, 0.04)
    cb_bias = mpl.colorbar.ColorbarBase(ax_bias, cmap="RdBu", ticks=ticksb,
        orientation='horizontal', norm=rel_normb, extend="both")
    cb_bias.set_label("Frequency Bias [% of grid points]")
    plt.savefig(f"{PAN_DIR_TMP}/{tmp_string}/cbar2.png")



def arrange_subplots(r, clean=False):
    """ Calculate size and position of the subplots and the panel
    for a single simulation using the aspect ratio of the map
    that is being drawn. Height of the figure is constant, width and height
    of the two smaller panels (scores, FSS) is also constant, total width
    is adjusted depending on the aspect ratio of the map.
    r .......... float, aspect ratio of the map plot
    clean ...... boolean, omit the smaller panels if no scores are desired
    Returns: 4 lists with the positions and sizes of the subplots"""
    total_height = 3.5 #4.80
    pad = total_height / 12.
    height = total_height - 2. * pad
    if clean:
        total_width = (total_height - 2 * pad) / r + 2 * pad
        map_left = pad / total_width
    else:
        total_width = 0.5 * height + height / r + 2 * pad
        map_left = (0.5 * height + pad)  / total_width
    map_bottom = pad / total_height
    map_height = height / total_height
    map_width = height / r / total_width
    small_left = pad / total_width
    small_width = 0.5 * height / total_width
    small_height = 0.5 * height / total_height
    score_bottom = (0.5 * height + pad) / total_height
    fss_bottom = map_bottom
    map_coords = [map_left, map_bottom, map_width, map_height]
    score_coords = [small_left, score_bottom, small_width, small_height]
    fss_coords = [small_left+0.05*pad, fss_bottom, small_width*0.9, small_height]
    return total_width, total_height, map_coords, score_coords, fss_coords

def draw_single_figure(sim, obs, r, jj, levels, cmap, norm, verification_subdomain, rank_colors, max_rank, args, tmp_string):
    """ Draw a panel plot with the contours of precipitation, scores, and FSS ranks
    sim ......... dictionary .. model data
    obs ......... dictionary .. obs data
    r ........... float ....... aspect ratio of the map in the largest panel
    jj .......... integer ..... index of the subplot within the panel
    levels ...... np.array .... contour levels
    cmap ........ mpl cmape ... color map
    norm ........ mpl norm .... for irregular conour levels
    verification_subdomain .... (str) subdomain for verif, used to draw rectangle
    rank_colors . list ........ list of colors to be used in the FSS rank plto
    max_rank .... int ......... highest rank that occurs
    args ...................... command line arguments
    tmp_string .. string ...... temperary path string

    Draws a plt.subplot with 3 panels (scores, FSS, map) with constant height and saves it
    into ../TMP/tmp_string/*.png for later use"""
    logger.info("Plotting "+sim['name'])
    total_width, total_height, map_coords, score_coords, fss_coords = arrange_subplots(r, clean=args.clean)
    fig = plt.figure(dpi=args.dpi, figsize=(total_width, total_height))
    ax = fig.add_axes(map_coords, projection=args.region.plot_projection)
    if args.clean:
        ax_scores = ax_fss = None
    else:
        ax_scores = fig.add_axes(score_coords)
        ax_scores.axis('off')
        ax_fss = fig.add_axes(fss_coords)
    if jj == 0 and not args.clean:
        ax_fss.axis('off')
    precip_data, lon, lat = prep_plot_data(sim, obs, args.mode)
    c = ax.pcolormesh(lon, lat, precip_data,
                    cmap=cmap,transform=args.region.data_projection,
                    norm=norm, shading='auto')
    ax.set_facecolor("silver")
    if args.draw_p90:
        p90 = np.percentile(np.copy(sim['precip_data_resampled']), 90) # circumvent numpy bug #21524
        sim['rr90'] = np.where(sim['precip_data_resampled'] > p90, 1, 0)
        sim['p90_color'] = 'black' if p90 <= 10. else 'white'
        mpl.rcParams['hatch.linewidth']=0.5
        plt.rcParams.update({'hatch.color': sim['p90_color']})
        ax.contourf(sim['lon_resampled'], sim['lat_resampled'], sim['rr90'], 
            levels=[0.5, 1.5], transform=args.region.data_projection, colors='none', hatches=['/////'])
        ax.contour(sim['lon_resampled'], sim['lat_resampled'], sim['rr90'], 
            linewidths = 0.5, levels=[0.5], transform=args.region.data_projection, colors=[sim['p90_color']])
    # limit drawn area, make the plot nicer and add some info
    ax.set_extent(sim['plot_extent'])
    add_borders(ax)
    ax.plot(get_array_edge(sim['lon']), get_array_edge(sim['lat']), 'k--', lw=0.5,
                transform = args.region.data_projection)
    if args.draw_subdomain:
        ax.plot(get_array_edge(sim['lon_resampled']), get_array_edge(sim['lat_resampled']), 'k',
                transform = args.region.data_projection)
    if args.hidden:
        panel_title = str(jj) if jj > 0 else sim['name']
        panel_title_fc = 'white'
    elif args.clean or sim["conf"] == "INCA" or sim["conf"] == "OPERA":
        panel_title = sim['name']
        panel_title_fc = 'white'
    else:
        panel_title = sim['name'].replace("finland_2017", "")+' ({:d})'.format(int(sim['rank_'+args.rank_by_fss_metric]))
        panel_title_fc = rank_colors[sim['rank_'+args.rank_by_fss_metric]]
    ax.text(0.0, 1.03, panel_title, va='top', ha='left',
        rotation='horizontal', rotation_mode='anchor',
        transform=ax.transAxes,size='large',
        bbox=dict(boxstyle='round', fc=panel_title_fc, ec='black', pad=0.2))
    if jj > 0 and not args.clean:
        add_fss_plot_new(ax_fss, sim, max_rank, jj, args)
        add_scores(ax_scores, sim, rank_colors)
    gl = ax.gridlines(crs=args.region.data_projection, draw_labels=False, dms=True, x_inline=False, y_inline=False)
    gl.left_labels=False
    gl.top_labels=False
    plt.savefig(f"{PAN_DIR_TMP}/{tmp_string}/{str(jj).zfill(3)}.png")
    plt.close('all')
    if sim['type'] == 'obs':
        draw_solo_colorbar(levels, cmap, norm, tmp_string, args)
        draw_RGB_colorbars(tmp_string, args)


def define_panel_and_plot_dimensions(data_list, args):
    """ Make a dummy map to obtain the aspect ratio, calculate lines
    and columns. This happens in the same function to make use of
    the aspect ratio when determining the cols/lins (not implemented
    yet)
    data_list ...... list of all model data
    args.region .....instance of Region class, contains info on the map
                     that is being drawn"""
    ax = plt.axes(projection=args.region.plot_projection)
    ax.set_extent(data_list[0]['plot_extent'])
    r = ax.get_data_ratio()
    # Automatically determine necessary size of the panel plot
    N = len(data_list)
    if args.rank_score_time_series:
        N += len(args.rank_score_time_series)
    if args.tile[0] and args.tile[1]:
        cols = args.tile[1]
        lins = args.tile[0]
    else:
        cols = int(np.ceil(np.sqrt(float(N))))
        lins = int(np.floor(np.sqrt(float(N))))
    while cols*lins < N:
        logger.info(f"Adding 1 line to panels because {lins} lines X {cols} columns < {N}")
        lins = lins + 1
    logger.debug("PLOT ASPECT: {:.2f}".format(r))
    return r, cols, lins, N


def score_time_series(data_list, r, tmp_string, args):
    score_names = {
        "fss_total_abs_score": "Old FSS Rank Score", 
        "fss_condensed": "FSS Condensed", 
        "fss_condensed_weighted": "FSS Condensed Weighted",
        "bias_real": "Bias",
        "bias": "Absolute Value of Bias",
        "rms": "Root Mean Squared Error",
        "mae": "Mean Absolute Error",
        "d90": "90th Percentile Displacement",
        "corr": "Pearson Correlation"}
    total_width, total_height, _, _, _ = arrange_subplots(r, clean=args.clean)
    for sidx, s in enumerate(args.rank_score_time_series):
        s = 'bias_real' if s == 'bias' else s
        if s in score_names.keys():
            nam_str = score_names[s]
        else:
            nam_str = s
        fig, ax = plt.subplots(1, 1, figsize=(total_width, total_height), dpi=args.dpi)
        logger.info("Making time series plot for " + nam_str)
        score = {}
        init = {}
        color = {}
        for sim in data_list[1::]:
            if not sim['conf'] in score.keys():
                color[sim['conf']] = sim['color']
                score[sim['conf']] = []
                init[sim['conf']] = []
            score[sim['conf']].append(sim[s])
            if score[sim['conf']][-1] == 9999 and s == 'd90':
                score[sim['conf']][-1] = np.nan
            init[sim['conf']].append(sim['init'])
        dt_min = dt.datetime(2100, 1, 1)
        dt_max = dt.datetime(1970, 1, 1)
        for key, ss in score.items():
            ax.plot(init[key], ss, 'o-', color=color[key], label=key)
            dt_min = init[key][0] if init[key][0] < dt_min else dt_min
            dt_max = init[key][-1] if init[key][-1] > dt_max else dt_max
        if s == 'bias_real':
            ax.plot([dt_min, dt_max], [0., 0.], 'k', lw=0.5)
        ax.legend()
        ax.set_ylabel("score")
        ax.set_xlabel("model init time")
        ax.tick_params(axis='x', labelrotation=30)
        title = nam_str + " by model and init"
        ax.set_title(title, loc='left')
        # ax.set_ylim([0., 122])
        plt.tight_layout()
        plt.savefig(f"{PAN_DIR_TMP}/{tmp_string}/{str(990 + sidx)}.png")
        # exit()
        

def draw_panels(data_list,start_date, end_date, verification_subdomain, args):
    """ Draw all data onto panels. This function separates the data into pickle files,
    one for each model, then uses the command line to call this modul as __main__, thsi will
    execote draw_sing_figure() and allows it to run in parallel. Matplotlib is not thread safe
    so normal parallelization will not work.
    data_list ........ list with all dictionaries holding the model and obs data
    start_date ....... start_date of the period
    end_date ......... end_date of the period
    verification_subdomain ... info on verificatino subdoamin, used for rectangle
    args ............. command line arguments
    mode ............. string, resampled or original data to be drawn"""
    logger.debug(args.region.extent)
    time_series_scores = args.rank_score_time_series
    if args.zoom_to_subdomain:
        plot_extent=[data_list[1]['lon_resampled'].min()-0.25, data_list[1]['lon_resampled'].max()+0.25,
                     data_list[1]['lat_resampled'].min()-0.25, data_list[1]['lat_resampled'].max()+0.25]
    else:
        plot_extent = args.region.extent
    for sim in data_list:
        sim['plot_extent'] = plot_extent
    r, cols, lins, nplots = define_panel_and_plot_dimensions(data_list, args)
    if args.panel_rows_columns:
        lins_new, cols_new = args.panel_rows_columns
        min_lines = nplots // cols_new + 1
        lins_new = min_lines if min_lines > lins_new else lins_new
        cols, lins = cols_new, lins_new
    logger.info("generating a panel plot with {} lines and {} columns".format(lins, cols))
    levels, cmap, norm = parameter_settings.get_cmap_and_levels(args)
    cmap.set_over('orange')
    rank_colors = 500*['white']
    rank_colors[1:3] = ['gold', 'silver', 'darkorange']
    # init projections
    suptit = "'"+parameter_settings.title_part[args.parameter] + " from "+start_date.strftime("%Y%m%d %H")+" to "+end_date.strftime("%Y%m%d %H UTC")+"'"
    name_part = '' #if args.mode == 'None' else args.mode+'_'
    start_date_str = start_date.strftime("%Y%m%d_%H")
    outfilename = f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_{name_part}panel_{start_date_str}UTC_{args.duration:02d}h_acc_{verification_subdomain}.png"
    # generate a random subdirectory within TMP to avoid collisions if multiple instances of panelification are
    # run at the same time
    tmp_string = dt.datetime.now().strftime("%Y%m%d%H%M%S")+str(np.random.randint(1000000000)).zfill(9)
    # generate figure and axes objects for loop and go
    os.system(f"mkdir {PAN_DIR_TMP}/{tmp_string}")
    logger.debug(f"mkdir {PAN_DIR_TMP}/{tmp_string}")
    # dump data for each model into a single pickle file
    if args.rank_score_time_series:
        score_time_series(data_list, r, tmp_string, args)
    for jj, sim in enumerate(data_list):
        pickle.dump([sim, data_list[0], r, jj, levels, cmap,
            norm, verification_subdomain, rank_colors, data_list[0]['max_rank'], args, tmp_string], 
            open(f"{PAN_DIR_TMP}/{tmp_string}/{str(jj).zfill(3)}.p", 'wb'))
        print(f"saving pickle to {PAN_DIR_TMP}/{tmp_string}/{str(jj).zfill(3)}.p")
    # generate a list of commands, one for each model, these will call panel_plotter.py to draw a single model
    cmd_list = [f"{sys.executable} {PAN_DIR_SCR}/panel_plotter.py -p {pickle_file}" for pickle_file in glob.glob(f"{PAN_DIR_TMP}/{tmp_string}/???.p")]
    # execute the commands in parallel
    Parallel(n_jobs=2)(delayed(os.system)(cmd) for cmd in cmd_list)
    logger.debug(f"montage {PAN_DIR_TMP}/{tmp_string}/???.png -geometry +0+0 -tile {lins}x{cols} -title {suptit} {PAN_DIR_TMP}/{tmp_string}/999.png")
    # use the individual panels and combine them into one large plot using imagemagick
    os.system(f"montage {PAN_DIR_TMP}/{tmp_string}/???.png -geometry +0+0 -tile {lins}x{cols} -title {suptit} {PAN_DIR_TMP}/{tmp_string}/999.png")
    # add the color bar using imagemagick
    os.system(f"convert {PAN_DIR_TMP}/{tmp_string}/999.png {PAN_DIR_TMP}/{tmp_string}/cbar.png -gravity center -append {PAN_DIR_TMP}/{tmp_string}/999A.png")
    os.system(f"convert {PAN_DIR_TMP}/{tmp_string}/999A.png {PAN_DIR_TMP}/{tmp_string}/cbar2.png -gravity center -append {outfilename}")
    # clear temporary data directory
    os.system(f"rm -R {PAN_DIR_TMP}/{tmp_string}")
    return outfilename


def ens_fss_abs(ax, fss_data, name, windows, levels):
    pass


def ens_fss_diff(ax, fss_data, name1, name2, windows, levels):
    pass


def get_value_range(ens_fss_data):
    n_members = len(ens_fss_data)
    val = -9999.
    for jj in range(1, n_members):
        for ii in range(0, n_members-1):
            if ii < jj:
                print(ens_fss_data[ii].pFSS[2])
                print(ens_fss_data[jj].pFSS[2])
                v_ = np.nanmax(np.abs(ens_fss_data[ii].pFSS[2] - ens_fss_data[jj].pFSS[2]))
                if v_ > val:
                    val = v_
    return v_


def ens_fss_plot(ens_data, windows, levels, verification_subdomain, args):
    n_members = len(ens_data)
    fig, ax = plt.subplots(n_members+1, n_members+1, figsize=(4 * n_members, 4 * n_members), sharex=True, sharey=True, dpi=args.dpi)
    vmax = get_value_range(ens_data)

    levels1 = np.arange(0., 1.01, 0.05)
    step = 0.001
    levels2 = np.arange(-vmax, vmax+0.001, step)
    while levels2.size > 50:
        step = 2 * step
        levels2 = np.arange(-vmax, vmax+0.001, step)
    logger.info(f"Using step = {step}, {levels2.size} levels")
    cmap1 = plt.colormaps['coolwarm_r']
    cmap2 = plt.colormaps['RdYlGn']
    norm1 = mpl.colors.BoundaryNorm(levels1, ncolors=cmap1.N)
    norm2 = mpl.colors.BoundaryNorm(levels2, ncolors=cmap2.N)
    
    logger.info("Making pFSS plots")
    ax[0][0].axis('off')
    c1, c2 = None, None
    for ii in range(0, n_members):
        logger.debug(f"  preparing {ens_data[ii].name}")
        c1 = ax[0][ii+1].pcolormesh(ens_data[ii].pFSS[2], cmap=cmap1, norm=norm1)
        ax[0][ii+1].set_title(f"{ens_data[ii].name}", loc="left")
    for jj in range(0, n_members):
        logger.debug(f"  preparing {ens_data[jj].name}")
        ax[jj+1][0].pcolormesh(ens_data[jj].pFSS[2], cmap=cmap1, norm=norm1)
        ax[jj+1][0].set_title(f"{ens_data[jj].name}", loc="left")
        for ii in range(0, n_members):
            if ii != jj:
                logger.debug(f"  preparing {ens_data[ii].name} - {ens_data[jj].name}")
                c2 = ax[jj+1][ii+1].pcolormesh(
                    ens_data[ii].pFSS[2] - ens_data[jj].pFSS[2],
                    cmap=cmap2, norm=norm2)        
                ax[jj+1][ii+1].set_title(f"{ens_data[ii].name} -\n{ens_data[jj].name}", loc="left")
            else:
                ax[jj+1][ii+1].axis('off')

    for N, ax1 in enumerate(ax.flatten()):
        ax1.set_yticks([x+0.5 for x in range(len(levels))])
        ax1.set_xticks([x+0.5 for x in range(len(windows))])
        ax1.set_yticklabels([str(x) for x in levels])
        ax1.set_xticklabels([str(x) for x in windows], rotation=90)
        ax1.set_ylim([9., 0.])
        ax1.set_xlim([0., 8.]) 
        if N%n_members == 0:
            ax1.set_ylabel("preipc. threshold [mm]")
        if N >= n_members * (n_members -1):
            ax1.set_xlabel("window size [km]")

    plt.tight_layout()
    fig.subplots_adjust(bottom=0.12)
    cax1 = fig.add_axes([0.1, 0.05, 0.35, 0.01])
    cax2 = fig.add_axes([0.55, 0.05, 0.35, 0.01])

    cbar1 = plt.colorbar(c1, cax=cax1, orientation="horizontal", label="pFSS") #, extend="min")
    cbar2 = plt.colorbar(c2, cax=cax2, orientation="horizontal", label="pFSS difference") #, extend='both')
    plt.draw()  # Force rendering so labels exist
    tick_labels = [label.get_text() for label in cbar2.ax.get_xticklabels()]
    tick_positions = cbar2.ax.get_xticks()
    cbar2.ax.set_xticks(tick_positions)
    cbar2.ax.set_xticklabels(tick_labels, rotation=30)
    
    start_date_str = dt.datetime.strptime(args.start, "%Y%m%d%H").strftime("%Y%m%d_%H")
    outfilename = f"{PAN_DIR_PLOTS}/{args.name}_{args.parameter}_pFSS_{start_date_str}UTC_acc_{args.duration}_{verification_subdomain}.png"
    plt.savefig(outfilename)


def main():
    """ used when called directly, this will draw a single model from a given pickle file"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--pickle_file", "-p", type=str, default='None')
    args = parser.parse_args()
    if args.pickle_file == 'None':
        exit()
    else:
        arg_data = pickle.load(open(args.pickle_file, 'rb'))
        draw_single_figure(*arg_data)


if __name__ == '__main__':
    main()
