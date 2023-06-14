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


def add_borders(axis):
    borders = cfeature.NaturalEarthFeature(
    category='cultural', name='admin_0_boundary_lines_land',
    scale='10m', facecolor='none')
    axis.add_feature(borders, edgecolor='black', lw=0.5)
    axis.add_feature(cfeature.COASTLINE)


def add_scores(ax, sim, rank_colors):
    ax.text(0., 0.95, "BIAS: {:.3f} ({})".format(sim['bias_real'], sim['rank_bias']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_bias']])
    ax.text(0., 0.8, "MAE: {:.3f} ({})".format(sim['mae'], sim['rank_mae']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_mae']])
    ax.text(0., 0.65, "RMSE: {:.3f} ({})".format(sim['rms'], sim['rank_rms']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_rms']])
    ax.text(0., 0.5, "R$_{{pearson}}$: {:.3f} ({})".format(sim['corr'], sim['rank_corr']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_corr']])
    if sim['d90'] < 9999.:
        ax.text(0., 0.35, "D$_{{90}}$: {:.1f} km ({})".format(sim['d90'], sim['rank_d90']), va='top', ha='left',
                rotation='horizontal', rotation_mode='anchor',
                transform=ax.transAxes,size='medium', backgroundcolor=rank_colors[sim['rank_d90']])
    # ax.text(1.00, 1.03, "AVG Rank: {:.2f} ({})".format(sim['average_rank'], sim['rank_average_rank']), va='top', ha='right',
    #         rotation='horizontal', rotation_mode='anchor',
    #         transform=ax.transAxes,size='large', 
    #         bbox=dict(boxstyle='round', fc=rank_colors[sim['rank_average_rank']], ec='black', pad=0.2))
    return ax


def make_fss_rank_plot_axes(little_ax, args):
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
    little_ax.tick_params(axis='both', which='major', labelsize=5)
    return little_ax

def add_fss_rank_plot(ax, sim, rank_vmax, jj, args):
    fss_rank_cols = ['white']*rank_vmax
    # print("max rank is {} and color table has {} colors".format(data_list[0]['max_rank'], len(fss_rank_cols)))
    fss_rank_cols[0:5] = ['black', 'red', 'limegreen', 'gold', 'silver', 'darkorange']
    # print fss_rank_cols
    fss_cmap = mplcolors.ListedColormap(fss_rank_cols)
    # add rank diagram for FSS
    extent = (0, sim['fss_ranks'].shape[1], sim['fss_ranks'].shape[0], 0)
    ax.imshow(sim['fss_ranks'], cmap = fss_cmap, extent=extent, vmin = 0., vmax=rank_vmax)
    ax.grid(color='w', linewidth=0.5)
    ax = make_fss_rank_plot_axes(ax, args)

def prep_plot_data(sim, obs, mode):
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
    fig = plt.figure(figsize=(17,1), dpi=120)
    ax = fig.add_axes([0.1,0.8,0.8,0.1])
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, 
        orientation='horizontal', ticks=levels, extend='max')
    cb.cmap.set_over('orange')
    cb.set_label(parameter_settings.colorbar_label[args.parameter])
    plt.savefig('../TMP/'+tmp_string+'/cbar.png')


def arrange_subplots(r):
    total_height = 4.75
    total_width = 2. + 4. / r + 0.75
    map_bottom = 0.25 / total_height
    map_left = 2.25 / total_width
    map_height = 4. / total_height
    map_width = 4. / r / total_width
    small_left = 0.25 / total_width
    small_width = 2. / total_width
    small_height = 2. / total_height
    score_bottom = 2.5 / total_height
    fss_bottom = map_bottom
    map_coords = [map_left, map_bottom, map_width, map_height]
    score_coords = [small_left, score_bottom, small_width, small_height]
    fss_coords = [small_left, fss_bottom, small_width, small_height]
    return total_width, total_height, map_coords, score_coords, fss_coords

def draw_single_figure(sim, obs, region, r, jj, levels, cmap, norm, mode, verification_subdomain, rank_colors, max_rank, args, tmp_string):
    print("Plotting "+sim['name'])
    total_width, total_height, map_coords, score_coords, fss_coords = arrange_subplots(r)
    fig = plt.figure(dpi=150, figsize=(total_width, total_height))
    ax = fig.add_axes(map_coords, projection=region.plot_projection)
    ax_scores = fig.add_axes(score_coords)
    ax_scores.axis('off')
    ax_fss = fig.add_axes(fss_coords)
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
    plt.tight_layout()
    plt.savefig('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".png")
    plt.close('all')
    if sim['conf'] == 'INCA' or sim['conf'] == 'OPERA':
        draw_solo_colorbar(levels, cmap, norm, tmp_string, args)


def define_panel_and_plot_dimensions(data_list, region):
    ax = plt.axes(projection=region.plot_projection)
    ax.set_extent(region.extent)
    r = ax.get_data_ratio()
    # Automatically determine necessary size of the panel plot
    cols = int(np.ceil(np.sqrt(float(len(data_list)))))
    lins = int(np.floor(np.sqrt(float(len(data_list)))))
    if cols*lins < len(data_list):
        lins = lins + 1
    print("PLOT ASPECT: {:.2f}".format(r))
    return r, cols, lins


def draw_panels(data_list,start_date, end_date, verification_subdomain, args, mode='None'):
    region = Region(region_name=args.region)
    print(region.extent)
    r, cols, lins = define_panel_and_plot_dimensions(data_list, region)
    print("generating a panel plot with {} lines and {} columns".format(lins, cols))
    levels, cmap, norm = parameter_settings.get_cmap_and_levels(mode, args)
    # levels, cmap, norm = get_cmap_and_levels(mode, args)
    # check which mode is being used an adjust levels and color map
    rank_colors = 500*['white']
    rank_colors[1:3] = ['gold', 'silver', 'darkorange']
    # init projections
    suptit = "'"+parameter_settings.title_part[args.parameter] + " from "+start_date.strftime("%Y%m%d %H")+" to "+end_date.strftime("%Y%m%d %H UTC")+"'"
    name_part = '' if args.mode == 'None' else args.mode+'_'
    outfilename = "../PLOTS/"+args.name+"_"+args.parameter+"_"+name_part+"panel_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.'+args.output_format
    tmp_string = dt.datetime.now().strftime("%Y%m%d%H%M%S")+str(np.random.randint(1000000000)).zfill(9)
    # generate figure and axes objects for loop and go
    os.system('mkdir ../TMP/'+tmp_string)
    print('mkdir ../TMP/'+tmp_string)
    for jj, sim in enumerate(data_list):
        pickle.dump([sim, data_list[0], region, r, jj, levels, cmap,
            norm, mode, verification_subdomain, rank_colors, data_list[0]['max_rank'], args, tmp_string], 
            open('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".p", 'wb'))
    cmd_list = ['python panel_plotter.py -p '+pickle_file for pickle_file in glob.glob('../TMP/'+tmp_string+'/???.p')]
    Parallel(n_jobs=6)(delayed(os.system)(cmd) for cmd in cmd_list)
    print('montage ../TMP/{:s}/???.png -geometry +0+0 -tile {:d}x{:d} -title {:s} ../TMP/{:s}/999.png'.format(
        tmp_string, lins, cols, suptit, tmp_string))
    os.system('montage ../TMP/{:s}/???.png -geometry +0+0 -tile {:d}x{:d} -title {:s} ../TMP/{:s}/999.png'.format(
        tmp_string, lins, cols, suptit, tmp_string))
    os.system('convert ../TMP/'+tmp_string+'/999.png ../TMP/'+tmp_string+'/cbar.png -gravity center -append '+outfilename)
    # os.system('rm ../TMP/'+tmp_string+'/???.p ../TMP/'+tmp_string+'/*.png')
    os.system('rm -R ../TMP/'+tmp_string)


def main():
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
