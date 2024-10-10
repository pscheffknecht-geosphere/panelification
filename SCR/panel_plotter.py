import argparse
import datetime as dt
import os
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
    for yy in range(ny):
        for xx in range(nx):
            xedge = -0.5 + np.array([xx+pad, xx+pad, xx+1-pad, xx+1-pad, xx+pad])
            yedge = -0.5 + np.array([yy+pad, yy+1-pad, yy+1-pad, yy+pad, yy+pad])
            if args.fss_mode == 'ranks':
                col = fss_rank_cols[sim['fss_ranks'][yy, xx]]
            elif args.fss_mode == 'relative':
                fss_rel = sim['fss_rel'][yy, xx] 
                pos_in_cmap = 0.5 + fss_rel * 10. # map [-.05, .05] to [0, 1]
                pos_in_cmap = 0. if pos_in_cmap < 0. else pos_in_cmap
                pos_in_cmap = 1. if pos_in_cmap > 1. else pos_in_cmap
                col = fss_cmap(pos_in_cmap)
            if sim['fss_ranks'][yy, xx] == 1 and yy < 9: #only for bad but not nan
                if sim['fss_overestimated'].to_numpy()[yy,xx] > 0.:
                    xedget = -0.5 + np.array([xx+3*pad, xx+1-3*pad, xx+0.5, xx+3*pad])
                    yedget = -0.5 + np.array([yy+1-3*pad, yy+1-3*pad, yy+3*pad, yy+1-3*pad])
                    col = 'navy'
                else:
                    xedget = -0.5 + np.array([xx+3*pad, xx+1-3*pad, xx+0.5, xx+3*pad])
                    yedget = -0.5 + np.array([yy+3*pad, yy+3*pad, yy+1-3*pad, yy+3*pad])
                    col = 'firebrick'
            if yy == 9:
                col = 'black' # fix red separation line for fiels that contain nans
            ax.fill(xedge, yedge, facecolor=col)
            if sim['fss_ranks'][yy, xx] == 1 and yy < 9: #only for bad but not nan
                ax.fill(xedget, yedget, facecolor='white')
    make_fss_rank_plot_axes(ax, args)
    ax.set_xlim([-0.5, nx-0.5])
    ax.set_ylim([ny-0.5, -0.5])
    #ax.set_aspect(float(nx)/float(ny))
    # ax.grid(color='w', linewidth=0.5)
            

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
    fig = plt.figure(figsize=(12, 0.9), dpi=150)
    if args.fss_mode == "relative":
        ax_rr = fig.add_axes([0.325,0.8,0.650,0.1])
        ax_rel = fig.add_axes([0.025,0.8,0.275,0.1])
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
    plt.savefig('../TMP/'+tmp_string+'/cbar.png')


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
    fig = plt.figure(dpi=150, figsize=(total_width, total_height))
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
                    norm=norm) #, extend='max')
    # c = ax.contourf(lon, lat, precip_data,
    #                 levels,cmap=cmap,transform=args.region.data_projection,
    #                 norm=norm, extend='max')
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
    ax.set_extent(args.region.extent)
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
    plt.savefig('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".png")
    plt.close('all')
    if sim['conf'] == 'INCA' or sim['conf'] == 'OPERA':
        draw_solo_colorbar(levels, cmap, norm, tmp_string, args)


def define_panel_and_plot_dimensions(data_list, args, time_series_scores):
    """ Make a dummy map to obtain the aspect ratio, calculate lines
    and columns. This happens in the same function to make use of
    the aspect ratio when determining the cols/lins (not implemented
    yet)
    data_list ...... list of all model data
    args.region .....instance of Region class, contains info on the map
                     that is being drawn"""
    ax = plt.axes(projection=args.region.plot_projection)
    ax.set_extent(args.region.extent)
    r = ax.get_data_ratio()
    # Automatically determine necessary size of the panel plot
    N = len(data_list)
    if args.rank_score_time_series:
        N += len(time_series_scores)
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


def score_time_series(data_list, r, tmp_string, time_series_scores):
    score_names = {
        "fss_total_abs_score": "Old FSS Rank Score", 
        "fss_condensed": "New FSS Score", 
        "fss_condensed_weighted": "New FSS Score Weighted"}
    for sidx, s in enumerate(time_series_scores):
        fig, ax = plt.subplots(1, 1, figsize=(3.5/r, 3.5), dpi=150)
        logger.info("Making time series plot for " + score_names[s])
        score = {}
        init = {}
        color = {}
        for sim in data_list[1::]:
            if not sim['conf'] in score.keys():
                color[sim['conf']] = sim['color']
                score[sim['conf']] = []
                init[sim['conf']] = []
            score[sim['conf']].append(sim[s])
            init[sim['conf']].append(sim['init'])
        for key, ss in score.items():
            ax.plot(init[key], ss, 'o-', color=color[key], label=key)
        ax.legend()
        ax.set_ylabel("score")
        ax.set_xlabel("model init time")
        ax.tick_params(axis='x', labelrotation=30)
        title = score_names[s] + " by model and init"
        ax.set_title(title, loc='left')
        plt.tight_layout()
        plt.savefig('../TMP/' + tmp_string + '/' + str(990 + sidx) + '.png')
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
    time_series_scores = [args.rank_by_fss_metric]
    r, cols, lins, nplots = define_panel_and_plot_dimensions(data_list, args, time_series_scores)
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
    outfilename = "../PLOTS/"+args.name+"_"+args.parameter+"_"+name_part+"panel_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.png' #+args.output_format
    # generate a random subdirectory within TMP to avoid collisions if multiple instances of panelification are
    # run at the same time
    tmp_string = dt.datetime.now().strftime("%Y%m%d%H%M%S")+str(np.random.randint(1000000000)).zfill(9)
    # generate figure and axes objects for loop and go
    os.system('mkdir ../TMP/'+tmp_string)
    logger.debug('mkdir ../TMP/'+tmp_string)
    # dump data for each model into a single pickle file
    if args.rank_score_time_series:
        score_time_series(data_list, r, tmp_string, time_series_scores)
    for jj, sim in enumerate(data_list):
        pickle.dump([sim, data_list[0], r, jj, levels, cmap,
            norm, verification_subdomain, rank_colors, data_list[0]['max_rank'], args, tmp_string], 
            open('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".p", 'wb'))
    # generate a list of commands, one for each model, these will call panel_plotter.py to draw a single model
    cmd_list = ['python panel_plotter.py -p '+pickle_file for pickle_file in glob.glob('../TMP/'+tmp_string+'/???.p')]
    # execute the commands in parallel
    Parallel(n_jobs=2)(delayed(os.system)(cmd) for cmd in cmd_list)
    logger.debug('montage ../TMP/{:s}/???.png -geometry +0+0 -tile {:d}x{:d} -title {:s} ../TMP/{:s}/999.png'.format(
        tmp_string, lins, cols, suptit, tmp_string))
    # use the individual panels and combine them into one large plot using imagemagick
    os.system('montage ../TMP/{:s}/???.png -geometry +0+0 -tile {:d}x{:d} -title {:s} ../TMP/{:s}/999.png'.format(
        tmp_string, lins, cols, suptit, tmp_string))
    # add the color bar using imagemagick
    os.system('convert ../TMP/'+tmp_string+'/999.png ../TMP/'+tmp_string+'/cbar.png -gravity center -append '+outfilename)
    # os.system('rm ../TMP/'+tmp_string+'/???.p ../TMP/'+tmp_string+'/*.png')
    # clear temporary data directory
    os.system('rm -R ../TMP/'+tmp_string)
    return outfilename


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
