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


def add_borders(axis):
    borders = cfeature.NaturalEarthFeature(
    category='cultural', name='admin_0_boundary_lines_land',
    scale='10m', facecolor='none')
    axis.add_feature(borders, edgecolor='black', lw=0.5)
    axis.add_feature(cfeature.COASTLINE)


def add_scores(ax, sim, rank_colors):
    ax.text(0.2, 0.91, "BIAS: {:.3f} ({})".format(sim['bias_real'], sim['rank_bias']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='x-small', backgroundcolor=rank_colors[sim['rank_bias']])
    ax.text(0.2, 0.85, "MAE: {:.3f} ({})".format(sim['mae'], sim['rank_mae']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='x-small', backgroundcolor=rank_colors[sim['rank_mae']])
    ax.text(0.2, 0.79, "RMSE: {:.3f} ({})".format(sim['rms'], sim['rank_rms']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='x-small', backgroundcolor=rank_colors[sim['rank_rms']])
    ax.text(0.2, 0.73, "R$_{{pearson}}$: {:.3f} ({})".format(sim['corr'], sim['rank_corr']), va='top', ha='left',
            rotation='horizontal', rotation_mode='anchor',
            transform=ax.transAxes,size='x-small', backgroundcolor=rank_colors[sim['rank_corr']])
    if sim['d90'] < 9999.:
        ax.text(0.2, 0.67, "D$_{{90}}$: {:.1f} km ({})".format(sim['d90'], sim['rank_d90']), va='top', ha='left',
                rotation='horizontal', rotation_mode='anchor',
                transform=ax.transAxes,size='x-small', backgroundcolor=rank_colors[sim['rank_d90']])
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
    little_ax = ax.inset_axes([0.0, 0.55, 0.16, 0.36])
    # add rank diagram for FSS
    extent = (0, sim['fss_ranks'].shape[1], sim['fss_ranks'].shape[0], 0)
    little_ax.imshow(sim['fss_ranks'], cmap = fss_cmap, extent=extent, vmin = 0., vmax=rank_vmax)
    little_ax.grid(color='w', linewidth=0.5)
    little_ax = make_fss_rank_plot_axes(little_ax, args)
    return little_ax

def prep_plot_data(sim, obs, mode):
    if mode == 'None':
        precip_data = sim['precip_data']
        lon = sim['lon']
        lat = sim['lat']
    elif mode == 'resampled':
        precip_data = sim['sim_param_resampled']
        lon = sim['lon_subdomain']
        lat = sim['lat_subdomain']
    elif mode == 'diff':
        if sim['name'] == 'INCA':
            precip_data = sim['sim_param_resampled']
        else:
            precip_data = sim['sim_param_resampled']-obs['sim_param_resampled']
        lon = sim['lon_subdomain']
        lat = sim['lat_subdomain']
    return precip_data, lon, lat

def prep_projections():
    crs_plot=ccrs.LambertConformal(
        # central_longitude=13.,
        # central_latitude=48.30,
        central_longitude=25.,
        central_latitude=48.3,
        false_easting=0.0,
        false_northing=0.0,
        #secant_latitudes=None,
        #standard_parallels=None,
        globe=None, 
        cutoff=-30)
    crs_data=ccrs.PlateCarree()
    return crs_plot, crs_data


def draw_solo_colorbar(levels, cmap, norm, extend, tmp_string, args):
    fig = plt.figure(figsize=(17,1), dpi=120)
    ax = fig.add_axes([0.1,0.8,0.8,0.1])
    cb = mpl.colorbar.ColorbarBase(ax, cmap=cmap, norm=norm, 
        orientation='horizontal', ticks=levels, extend=extend)
    cb.cmap.set_over('orange')
    if extend == 'both':
        cb.cmap.set_under('pink')
    cb.set_label(parameter_settings.colorbar_label[args.parameter])
    plt.savefig('../TMP/'+tmp_string+'/cbar.png')


def draw_single_figure(sim, obs, jj, crs_data, crs_plot, levels, cmap, norm, mode, verification_subdomain, rank_colors, max_rank, args, tmp_string):
    # fig, axs = plt.subplots(lins, cols, figsize=(5.4*cols, 3.5*lins+1.), dpi=120, subplot_kw={'projection': crs_plot})
    print("Plotting "+sim['name'])
    crs_plot, crs_data = prep_projections()
    crs_plot = crs_data if args.fast else crs_plot
    fig, ax = plt.subplots(1,1, figsize=(6.4, 4.0), dpi=120, subplot_kw={'projection': crs_plot})
    precip_data, lon, lat = prep_plot_data(sim, obs, mode)
    extend = 'both' if args.mode == 'diff' else 'max'
    precip_data = np.where(precip_data == np.nan, 0., precip_data)
    precip_data = np.where(precip_data <0., 0., precip_data)
    #try:
    if args.fast:
        c = ax.pcolormesh(lon, lat, precip_data, transform=crs_data,
                    vmin=min(levels), vmax=max(levels),cmap=cmap, norm=norm)
    else:
        precip_data_smooth = precip_data #ndimage.gaussian_filter(precip_data, sigma=1., order=0)
        print(lat.shape, lat.min(), lat.max())
        print(lon.shape, lon.min(), lon.max())
        print(precip_data.shape, precip_data.min(), precip_data.max())
        c = ax.contourf(lon, lat, precip_data_smooth,
                        levels,cmap=cmap,transform=crs_data,
                        norm=norm, extend=extend)
    c.cmap.set_over('orange')
    if extend == 'both':
        c.cmap.set_under('pink')
    if args.draw_p90:
        mpl.rcParams['hatch.linewidth']=0.5
        plt.rcParams.update({'hatch.color': sim['p90_color']})
        ax.contourf(sim['lon_subdomain'], sim['lat_subdomain'], sim['rr90'], 
            levels=[0.5, 1.5], transform=crs_data, colors='none', hatches=['/////'])
        ax.contour(sim['lon_subdomain'], sim['lat_subdomain'], sim['rr90'], 
            linewidths = 0.5, levels=[0.5], transform=crs_data, colors=[sim['p90_color']])
    # limit drawn area, make the plot nicer and add some info
    # ax.set_extent([13.66, 18.0, 47.4, 49.2])
    if args.fast:
        ax.set_extent([9.,17.5,45.5,51.])
    else:
        # ax.set_extent([3.,23.,43.,55.])
        ax.set_extent([9.,17.5,46.,49.5])
    ax.set_extent([16.0, 31.0, 58.00, 63.0])
    add_borders(ax)
    gl = ax.gridlines(color='black',alpha=0.3)
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
            transform = crs_data))
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
        little_ax = add_fss_rank_plot(ax, sim, max_rank, jj, args)
        ax = add_scores(ax, sim, rank_colors)
    plt.tight_layout()
    plt.savefig('../TMP/'+tmp_string+'/'+str(jj).zfill(3)+".png")
    plt.close('all')
    if sim['conf'] == 'INCA' or sim['conf'] == 'OPERA':
        draw_solo_colorbar(levels, cmap, norm, extend, tmp_string, args)

def draw_panels(data_list,start_date, end_date, verification_subdomain, args, mode='None'):
    # Automaticall determine necessary size of the panel plot
    cols = int(np.ceil(np.sqrt(float(len(data_list)))))
    lins = int(np.floor(np.sqrt(float(len(data_list)))))
    if cols*lins < len(data_list):
        lins = lins + 1
    print("generating a panel plot with {} lines and {} columns".format(lins, cols))
    levels, cmap, norm = parameter_settings.get_cmap_and_levels(mode, args)
    # levels, cmap, norm = get_cmap_and_levels(mode, args)
    # check which mode is being used an adjust levels and color map
    rank_colors = 500*['white']
    rank_colors[1:3] = ['gold', 'silver', 'darkorange']
    # init projections
    crs_plot, crs_data = prep_projections()
    crs_plot = crs_data if args.fast else crs_plot
    suptit = "'"+parameter_settings.title_part[args.parameter] + " from "+start_date.strftime("%Y%m%d %H")+" to "+end_date.strftime("%Y%m%d %H UTC")+"'"
    name_part = '' if args.mode == 'None' else args.mode+'_'
    outfilename = "../PLOTS/"+args.name+"_"+args.parameter+"_"+name_part+"panel_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.'+args.output_format
    tmp_string = dt.datetime.now().strftime("%Y%m%d%H%M%S")+str(np.random.randint(1000000000)).zfill(9)
    # generate figure and axes objects for loop and go
    os.system('mkdir ../TMP/'+tmp_string)
    print('mkdir ../TMP/'+tmp_string)
    for jj, sim in enumerate(data_list):
        pickle.dump([sim, data_list[0], jj, crs_data, crs_plot, levels, cmap,
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
