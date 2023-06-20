import argparse
import datetime as dt
import os
import glob
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib as mpl
from matplotlib.colors import BoundaryNorm as bnorm
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
from regions import Region

import logging
logger = logging.getLogger(__name__)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

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
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_bias']])
    ax.text(0.1, 0.75, "MAE: {:.3f} ({})".format(sim['mae'], sim['rank_mae']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_mae']])
    ax.text(0.1, 0.60, "RMSE: {:.3f} ({})".format(sim['rms'], sim['rank_rms']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_rms']])
    ax.text(0.1, 0.45, "R$_{{pearson}}$: {:.3f} ({})".format(sim['corr'], sim['rank_corr']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_corr']])
    if sim['d90'] < 9999.:
        ax.text(0.1, 0.30, "D$_{{90}}$: {:.1f} km ({})".format(sim['d90'], sim['rank_d90']), va='top', ha='left',
                rotation='horizontal', rotation_mode='anchor',
                transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_d90']])
    # ax.text(1.00, 1.03, "AVG Rank: {:.2f} ({})".format(sim['average_rank'], sim['rank_average_rank']), va='top', ha='right',
    #         rotation='horizontal', rotation_mode='anchor',
    #         transform=ax.transAxes,size='large', 
    #         bbox=dict(boxstyle='round', fc=rank_colors[sim['rank_average_rank']], ec='black', pad=0.2))
    return ax


def make_fss_rank_plot_axes(little_ax, args):
    """ Add tick labels to the FFS rank plot
    little_ax ...... axes object from pyplot.subplots
    args ........... parsed command line arguments"""
    all_ticks = parameter_settings.get_axes_for_fss_rank_plot(args)
    xticks = all_ticks['xticks']
    yticks = all_ticks['yticks']
    little_ax.set_xticks(xticks)
    little_ax.set_yticks(yticks)
    xdict = all_ticks['xdict']
    ydict = all_ticks['ydict']
    xlabels = [xticks[i] if t not in xdict.keys() else xdict[t] for i,t in enumerate(xticks)]
    ylabels = [yticks[i] if t not in ydict.keys() else ydict[t] for i,t in enumerate(yticks)]
    little_ax.set_xticklabels(xlabels, rotation='vertical')
    little_ax.set_yticklabels(ylabels)
    # little_ax.tick_params(axis='both', which='major', labelsize=5)
    return little_ax

def add_fss_rank_plot(ax, sim, rank_vmax, jj, args):
    """ Generate the FSS rank plot
    ax .......... axes object from pyplot.subplots
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
    ax.imshow(sim['fss_ranks'], cmap = fss_cmap, extent=extent, vmin = 0., vmax=rank_vmax)
    ax.grid(color='w', linewidth=0.5)
    ax = make_fss_rank_plot_axes(ax, args)

def prep_plot_data(sim, obs, mode):
    """ Select the correct data for plotting
    sim ........ dictionary for the model
    obs ........ dictionary for the observations
    mode ....... string, select whether to plot original or resampled fields"""
    if mode == 'None':
        precip_data = sim['precip_data']
        lon = sim['lon']
        lat = sim['lat']
    elif mode == 'resampled':
        precip_data = sim['sim_param_resampled']
        lon = sim['lon_subdomain']
        lat = sim['lat_subdomain']
    return precip_data, lon, lat


def draw_solo_colorbar(levels, cmap, norm, tmp_string, args):
    """ Draw a colorbar to be used for the panel
    levels ......... np.array with cntour levels
    cmap ........... matplotlib colormap
    norm ........... matplotlib norm for use of non-linear contours
    tmp_string ..... temporary path
    args ........... command line arguments"""
    fig = plt.figure(figsize=(17,1), dpi=120)
    ax = fig.add_axes([0.1,0.8,0.8,0.1])
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, 
        orientation='horizontal', ticks=levels, extend='max')
    cb.cmap.set_over('orange')
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
    total_height = 4.80
    if clean:
        total_width = 4. / r + 0.80
        map_left = .40 / total_width
    else:
        total_width = 2. + 4. / r + 0.80
        map_left = 2.40 / total_width
    map_bottom = 0.40 / total_height
    map_height = 4. / total_height
    map_width = 4. / r / total_width
    small_left = 0.40 / total_width
    small_width = 2. / total_width
    small_height = 2. / total_height
    score_bottom = 2.4 / total_height
    fss_bottom = map_bottom
    map_coords = [map_left, map_bottom, map_width, map_height]
    score_coords = [small_left, score_bottom, small_width, small_height]
    fss_coords = [small_left, fss_bottom, small_width, small_height]
    return total_width, total_height, map_coords, score_coords, fss_coords

def draw_single_figure(sim, obs, region, r, jj, levels, cmap, norm, mode, verification_subdomain, rank_colors, max_rank, args, tmp_string):
    """ Draw a panel plot with the contours of precipitation, scores, and FSS ranks
    sim ......... dictionary .. model data
    obs ......... dictionary .. obs data
    r ........... float ....... aspect ratio of the map in the largest panel
    jj .......... integer ..... index of the subplot within the panel
    levels ...... np.array .... contour levels
    cmap ........ mpl cmape ... color map
    norm ........ mpl norm .... for irregular conour levels
    mode ........ string ...... mode (draw original or resampled fields
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
    ax = fig.add_axes(map_coords, projection=region.plot_projection)
    if args.clean:
        ax_scores = ax_fss = None
    else:
        ax_scores = fig.add_axes(score_coords)
        ax_scores.axis('off')
        ax_fss = fig.add_axes(fss_coords)
    if jj == 0 and not args.clean:
        ax_fss.axis('off')
    #fig, ax = plt.subplots(1,1, figsize=(6.4, 4.0), dpi=120, subplot_kw={'projection': region.plot_projection})
    precip_data, lon, lat = prep_plot_data(sim, obs, mode)
    precip_data = np.where(precip_data == np.nan, 0., precip_data)
    precip_data = np.where(precip_data <0., 0., precip_data)
    precip_data_smooth = precip_data #ndimage.gaussian_filter(precip_data, sigma=1., order=0)
    c = ax.contourf(lon, lat, precip_data_smooth,
                    levels,cmap=cmap,transform=region.data_projection,
                    norm=norm, extend='max')
    c.cmap.set_over('orange')
    if args.draw_p90:
        mpl.rcParams['hatch.linewidth']=0.5
        plt.rcParams.update({'hatch.color': sim['p90_color']})
        ax.contourf(sim['lon_subdomain'], sim['lat_subdomain'], sim['rr90'], 
            levels=[0.5, 1.5], transform=region.data_projection, colors='none', hatches=['/////'])
        ax.contour(sim['lon_subdomain'], sim['lat_subdomain'], sim['rr90'], 
            linewidths = 0.5, levels=[0.5], transform=region.data_projection, colors=[sim['p90_color']])
    # limit drawn area, make the plot nicer and add some info
    ax.set_extent(region.extent)
    add_borders(ax)
    if verification_subdomain == 'Custom':
        subdom_lon_lat_limits = args.lonlat_limits
    else:
        subdom_lon_lat_limits = verification_subdomains[verification_subdomain]
    if args.draw_subdomain:
        ax.add_patch(mpatches.Rectangle(xy=[subdom_lon_lat_limits[0], subdom_lon_lat_limits[2]],
            width = subdom_lon_lat_limits[1] - subdom_lon_lat_limits[0],
            height = subdom_lon_lat_limits[3] - subdom_lon_lat_limits[2],
            facecolor = 'None',
            edgecolor = 'black',
            alpha = 1.,
            transform = region.data_projection))
    if args.hidden:
        panel_title = str(jj) if jj > 0 else sim['name']
        panel_title_fc = 'white'
    elif args.clean or sim["conf"] == "INCA" or sim["conf"] == "OPERA":
        panel_title = sim['name']
        panel_title_fc = 'white'
    else:
        panel_title = sim['name'].replace("finland_2017", "")+' ({:d})'.format(int(sim['rank_fss_total_abs_score']))
        panel_title_fc = rank_colors[sim['rank_fss_total_abs_score']]
    ax.text(0.0, 1.03, panel_title, va='top', ha='left',
        rotation='horizontal', rotation_mode='anchor',
        transform=ax.transAxes,size='large',
        bbox=dict(boxstyle='round', fc=panel_title_fc, ec='black', pad=0.2))
    if jj > 0 and not args.clean:
        little_ax = add_fss_rank_plot(ax_fss, sim, max_rank, jj, args)
        ax_scores = add_scores(ax_scores, sim, rank_colors)
    gl = ax.gridlines(crs=region.data_projection, draw_labels=False, dms=True, x_inline=False, y_inline=False)
    gl.left_labels=False
    gl.top_labels=False
    plt.savefig('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".png")
    plt.close('all')
    if sim['conf'] == 'INCA' or sim['conf'] == 'OPERA':
        draw_solo_colorbar(levels, cmap, norm, tmp_string, args)


def define_panel_and_plot_dimensions(data_list, region):
    """ Make a dummy map to obtain the aspect ratio, calculate lines
    and columns. This happens in the same function to make use of
    the aspect ratio when determining the cols/lins (not implemented
    yet)
    data_list ...... list of all model data
    region ......... instance of Region class, contains info on the map
                     that is being drawn"""
    ax = plt.axes(projection=region.plot_projection)
    ax.set_extent(region.extent)
    r = ax.get_data_ratio()
    # Automatically determine necessary size of the panel plot
    cols = int(np.ceil(np.sqrt(float(len(data_list)))))
    lins = int(np.floor(np.sqrt(float(len(data_list)))))
    if cols*lins < len(data_list):
        lins = lins + 1
    logger.debug("PLOT ASPECT: {:.2f}".format(r))
    return r, cols, lins


def draw_panels(data_list,start_date, end_date, verification_subdomain, args, mode='None'):
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
    region = Region(region_name=args.region)
    logger.debug(region.extent)
    r, cols, lins = define_panel_and_plot_dimensions(data_list, region)
    logger.info("generating a panel plot with {} lines and {} columns".format(lins, cols))
    levels, cmap, norm = parameter_settings.get_cmap_and_levels(mode, args)
    # levels, cmap, norm = get_cmap_and_levels(mode, args)
    # check which mode is being used an adjust levels and color map
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
    for jj, sim in enumerate(data_list):
        pickle.dump([sim, data_list[0], region, r, jj, levels, cmap,
            norm, mode, verification_subdomain, rank_colors, data_list[0]['max_rank'], args, tmp_string], 
            open('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".p", 'wb'))
    # generate a list of commands, one for each model, these will call panel_plotter.py to draw a single model
    cmd_list = ['python panel_plotter.py -p '+pickle_file for pickle_file in glob.glob('../TMP/'+tmp_string+'/???.p')]
    # execute the commands in parallel
    Parallel(n_jobs=6)(delayed(os.system)(cmd) for cmd in cmd_list)
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
