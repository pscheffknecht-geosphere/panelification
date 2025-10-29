# make map plots and panel them nicely to compare multiple simulations
#
import pyresample
from datetime import datetime
from datetime import timedelta as dt
from misc import loop_datetime, str2bool
import argparse
import logging
from joblib import Parallel, delayed
import numpy as np
import os
import sys

from model_parameters import *
import scoring
import inca_functions as inca
import read_opera as opera
import obs_from_db as obs
import read_antilope as antilope
import read_esp as esp
import panel_plotter
import io_main as io
import data_from_dcmdb
import scan_obs
import regions
import prepare_for_web
import parameter_settings
import ensembles

# try avoiding hanging during parallelized portions of the program
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_DYNAMIC'] = 'FALSE'

global args, start_date, end_date
start_date = datetime(2019,8,12,15,0,0)
end_date = datetime(2019,8,12,18,0,0)


def init_logging(args):
    if args.logfile:
        logging.basicConfig(filename=args.logfile, level=translate_logging_levels(args.loglevel))
    else:
        logging.basicConfig(level=translate_logging_levels(args.loglevel))


def translate_logging_levels(lvlstr):
    lvlstr = lvlstr.lower()
    level = logging.INFO #default
    if lvlstr == 'debug': level = logging.DEBUG
    if lvlstr == 'warning': level = logging.WARNING
    if lvlstr == 'error': level = logging.ERROR
    return level


def parse_arguments():
    global args
    parser = argparse.ArgumentParser(conflict_handler="resolve")
    parser.add_argument('--parameter', '-p', type=str, default='precip',
        help = 'parameter to verify/plot')
    parser.add_argument('--precip_verif_dataset', type=str, default = 'INCA',
        help = """select precip data set:
            INCA ... INCA analysis over Austria
            OPERA .. OPERA analysis over Europ (MUST be in ../OBS!!)""")
    parser.add_argument('--region', type=str, default='Austria',
        help = 'select region for plot')
    parser.add_argument('--name', '-n', type=str, default='',
        help = 'name of the panels, if desired, will be used as prefix in the names of the saved files')
    parser.add_argument('--start', '-s', type=str, default=None,
        help = 'starting date as YYYYMMDDHH')
    parser.add_argument('--duration', '-d', type=int, default=1,
        help = 'accumulation duration in hours')
    parser.add_argument('--lead', '-l', type=int, default=[12], nargs='+',
        help = 'maximum lead time up to starting time in hours')
    parser.add_argument('--subdomains', '-u', type=str, default=["Default"],
        nargs='+',
        help = """ Select verification subdomains
            Subdomains are defined in regions.py for each region""")
    parser.add_argument('--sorting', type=str, default='model',
        help = """Sorting of the panels
            default ... sort by model as given in the arguments
            model ..... sort by model name
            init ...... sort by init time""")
    parser.add_argument('--draw_subdomain', nargs='?', default=True, const=True, type=str2bool,
        help = "Draw a rectangle to show the verification subdomain")
    parser.add_argument('--case', '-c', type=str, nargs='+', default="austria_2022",
        help = "Select case to verify")
    parser.add_argument('--experiments', '-e', type=str, nargs='+',
        default = None,
        help = """select experiments, if left empty/None it will select all available""")
    parser.add_argument('--custom_experiment_file', type=str, 
        default = "custom_experiments.py",
        help = """add you own models not listed in DCMDB""")
    parser.add_argument('--custom_experiments', type=str, nargs='+',
        default = None,
        help = """add you own models not listed in DCMDB""")
    # parser.add_argument('--output_format', type=str, default='png',
    #     help = "Desired output format (png, jpg, pdf, eps, ...)")
    parser.add_argument('--lonlat_limits', type=float, nargs='+',
        default = None,
        help = """Select custom corner points of verification subdomain:
            LonMin, LonMax, LatMin, LatMax)""")
    parser.add_argument('--draw', nargs='?', default=False, const=True, type=str2bool,
        help = 'draw panels if average rain is above 5 mm or maximum rain is above 100 mm')
    parser.add_argument('--forcedraw', nargs='?', default=False, const=True, type=str2bool,
        help = 'draw panels for all subdomains, no matter how much rain was observed')
    parser.add_argument('--cmap', type=str, default="mycolors",
        help = 'color map selection')
    parser.add_argument('--forcescore', nargs='?', default=False, const=True, type=str2bool,
        help = 'draw panels for all subdomains, no matter how much rain was observed')
    parser.add_argument('--draw_p90', nargs='?', default=False, const=True, type=str2bool,
        help = 'draw panels for all subdomains, no matter how much rain was observed')
    parser.add_argument('--clean', nargs='?', default=False, const=True, type=str2bool,
        help = 'do not draw/write verification metrics on the panels')
    parser.add_argument('--mode', default='normal', type=str,
        help = """ Drawing mode:
            'normal' (default) ... Draw model data as-is
            'resampled' .......... Draw model data interpolated to INCA grid for verification""")
    #         'diff' ............. Draw interpolated rain field difference to INCA analysis\n
    parser.add_argument('--fix_nans', nargs='?', default=False, const=True, type=str2bool,
        help = 'Fix NaNs in OBS and Model fields by setting them to 0.')
    parser.add_argument('--save', nargs='?', default=False, const=True, type=str2bool,
        help = 'save full fields to pickle files')
    parser.add_argument('--fss_mode', type=str, default='ranks')
    parser.add_argument('--fss_calc_mode', type=str, default='same')
    parser.add_argument('--rank_by_fss_metric',type=str, default='fss_condensed_weighted',
        help = """Select score used when ranking simulation by their FSS performance:
        fss_total_abs_score .................. use the old FSS Rank Score
        fss_condensed ........................ condensed FSS value, uniform weight
        fss_condensed_weighted (default) ..... condensed FSS value, higher weight smaller windows and higher precipitation""")
    parser.add_argument('--save_full_fss', nargs='?', default=False, const=True, type=str2bool,
        help = 'save full FSS, including numerator and denominator')
    parser.add_argument('--hidden', nargs='?', default=False, const=True, type=str2bool,
        help = 'clean panels, with names hidden and numbers used instead')
    parser.add_argument('--panel_rows_columns', nargs='+', default=None, type=int,
        help = """Manually select rows and columns of the panel plot
        If rows x columns is too small, lines will be added to accomodate all panels
        if rows x columns is larger than needed, fewer lines will be filled""")
    # parser.add_argument('--fast', nargs='?', default=False, const=True, type=str2bool,
    #     help = 'faster drawing using pcolormesh')
    parser.add_argument('--logfile', type=str, default=None, help='Name of logfile')
    parser.add_argument('--loglevel', type=str, default='info',
        help = """Logging level:
          debug, info, warning, error""")
    parser.add_argument('--rank_score_time_series', nargs='*', default=None, type=str,
        help = """Draw line plots of model performance, init on x axis, score on y axis""")
    parser.add_argument('--highlight_threshold', '-u', type=int, default=[], nargs='+',
        help = """Highlight specific precipitation contour line""")
    parser.add_argument('--time_series_panel_width', default=0.66, type=float,
        help = """Move the default width of the score time series panel, can be sued
        if config names are too long to fit onto the panel.""")
    parser.add_argument('--tile', nargs=2, default=[None, None], type=int,
        help = "select N and M for the NxM panel, needs to fit the number of plots!")
    parser.add_argument('--check_ecfs', nargs='?', default=False, const=True, type=str2bool,
        help = 'check ecfs for experiments if no files are present on scratch')
    parser.add_argument('--zoom_to_subdomain', nargs='?', default=False, const=True, type=str2bool,
        help = 'zoom in to subdomain regardless of region extent')
    parser.add_argument('--intranet_update', nargs='?', default=False, const=True, type=str2bool,
        help = 'update panels on the intranet website')
    parser.add_argument('--greens', nargs='?', default=True, const=True, type=str2bool,
        help = 'test green instead of white')
    parser.add_argument('--dpi', nargs='?', default=150, const=True, type=int,
        help = 'set DPI of output')
    parser.add_argument('--ensemble_scores', nargs='?', default=False, const=True, type=str2bool,
        help = 'Treat multiple init times of the same ensemble as one ensemble')
    parser.add_argument('--merge_ens_init_times', nargs='?', default=False, const=True, type=str2bool,
        help = 'Treat multiple init times of the same ensemble as one ensemble')
    parser.add_argument('--print_colors', nargs='?', default=False, const=True, type=str2bool,
        help = 'Adapt color map for printing')
    parser.add_argument('--save_percentiles', nargs='?', default=False, const=True, type=str2bool,
        help = 'Save all percentiles to CSV')

    args = parser.parse_args()
    init_logging(args)
    if not args.intranet_update:  # ignore these conditions if only updating intranet
        # replace the string object with a proper instance of Region
        ce = __import__(args.custom_experiment_file)
        args.custom_experiment_data = ce.experiment_configurations
        if args.region != "Dynamic":
            args.region = regions.Region(args.region, args.subdomains)
        if args.subdomains == "Custom" and args.lonlat_limits is None:
            logging.critical("""The subdomain is set to "Custom", then its limits need to be set!
                Use the command line argument:
                  --lonlat_limits LonMin LonMax LatMin LatMax

                exiting...""")
            exit(1)
        if len(args.lead) > 2 and len(args.lead) != 2*len(args.custom_experiments):
            logging.critical("""--lead must have one of the following:
               1 value 
                 maximum lead time before accumulation start period
               2 values
                 minimum and maximum lead time before accumulation start period
               2*len(--config) values
                 minimum and maximum lead time for each config

               exiting...""")
            exit(1)
        if len(args.name) > 0:
            if args.name[-1] != '_':
                args.name += '_' 
        # hidden forces clean too:
        args.clean = True if args.hidden else args.clean
        if args.duration >= 24 and args.parameter == "precip":
            logging.info("Switching from paramter 'precip' to 'precip2' due to long accumulation window")
            args.parameter = "precip2"
        for ii, entry in enumerate(args.custom_experiments):
            if entry == "claef1k-all-members":
                logging.info(f"Found cleaf1k-all-members at position {ii}, replacing...")
                args.custom_experiments[ii] = "claef1k-m16"
                for jj in range(15, 0, -1):
                    args.custom_experiments.insert(ii, f"claef1k-m{jj:02d}")
                args.custom_experiments.insert(ii, f"claef1k-control")

def get_lead_limits(args):
    lead_limits = args.lead
    if len(lead_limits) == 2:
        min_lead = lead_limits[0]
        max_lead = lead_limits[1]
    elif len(lead_limits) == 1:
        min_lead = 0
        max_lead = lead_limits[0]
    elif len(lead_limits) > 2:
        min_lead = lead_limits[::2]
        max_lead = lead_limits[1::2]
    return min_lead, max_lead


def print_some_basics(start_date, end_date, min_lead, max_lead):
    logging.info("Checking precipitation for the {:d} hours from {:s} to {:s}.".format(
        int((end_date - start_date).total_seconds()/3600),
        start_date.strftime("%Y-%m-%d %H UTC"),
        end_date.strftime("%Y-%m-%d %H UTC")))
    if type(max_lead) == int:
        logging.info("Limiting models to lead times between {:d} and {:d} hours before {:s}.".format(
            min_lead, max_lead, start_date.strftime("%Y-%m-%d %H UTC")))
    else:
        for mil, mal in zip(min_lead, max_lead):
            logging.info("Limiting models to lead times between {:d} and {:d} hours before {:s}.".format(
                mil, mal, start_date.strftime("%Y-%m-%d %H UTC")))


def main():
    parse_arguments()
    if args.intranet_update:
        logging.info("Updating intranet...")
        prepare_for_web.complete_blank_html()
        prepare_for_web.send_panels_to_mgruppe()
        prepare_for_web.send_html_to_mgruppe()
        prepare_for_web.clean_old_panels
        sys.exit(0)
    region = args.region
    min_lead, max_lead = get_lead_limits(args)
    start_date = datetime.strptime(args.start, "%Y%m%d%H")
    end_date = start_date + dt(hours=args.duration)
    print_some_basics(start_date, end_date, min_lead, max_lead)
    # generate a list of available simulations and add data, observations and scores
    data_list = []
    if args.experiments:
        data_from_dcmdb.get_sim_and_file_list(data_list, args)
    if args.custom_experiments:
        io.get_sims_and_file_list(data_list, args)
    if len(data_list) == 0:
        logging.critical("No valid models found, exiting...")
        exit()
    #data_list = data_from_dcmdb.read_data(data_list, args)
    # if args.parameter in ['precip', 'sunshine']:
    # if args.parameter in ['precip', 'precip2', 'precip3', 'sunshine']:
    if args.precip_verif_dataset == "INCA":
        data_list = inca.read_INCA(data_list, start_date, end_date, args)
    elif args.precip_verif_dataset == "INCAPlus":
        data_list = inca.read_INCAPlus_ANA(data_list, start_date, end_date, args)
    elif args.precip_verif_dataset == "INCA_archive":
        data_list = inca.read_inca_netcdf_archive(data_list, start_date, end_date, args)
    elif args.precip_verif_dataset == "OPERA":
            data_list = opera.read_OPERA(data_list, start_date, end_date, args)
    elif args.parameter == 'hail':
        data_list = obs.read_hail(data_list, start_date, end_date)
        data_list = io.scale_hail(data_list) # scale all fields to 0...4
    elif args.precip_verif_dataset == "ANTILOPE":
        data_list = antilope.read_ANTILOPE(data_list, start_date, end_date, args)
    elif args.precip_verif_dataset == "ESP":
        data_list = esp.read_esp(data_list, start_date, end_date, args)
    else:
        logging.critical("Unknown verification data set: {:s}, exiting...".format(
            args.precip_verif_dataset))
    # elif args.parameter == 'lightning':
    #     data_list = obs.read_lightning(data_list, start_date, end_date)
    # else:
    #     logging.critical("Parameter {:s} unknown, accepted parameters: precip, sunshine, hail, lightning".format(
    #         args.parameter))
    #     exit(1)
    if args.region == "Dynamic":
        region_data = regions.regions
        region_data = regions.dynamic_region(data_list, region_data)
        # args.region = regions.Region(args.region, args.subdomains)
        args.region = regions.Region(args.region, args.subdomains, region_data=region_data) 
    if args.sorting == 'init':
        newlist = sorted(data_list[1::], key=lambda d: d['init']) 
        newlist.insert(0, data_list[0])
        data_list = newlist
    df_subdomain_details = scan_obs.get_interesting_subdomains(data_list[0], args)
    thresholds = parameter_settings.get_fss_thresholds(args)
    windows = [10,20,30,40,60,80,100,120,140,160,180,200]
    for _, dom in df_subdomain_details.iterrows():
        subdomain_name = dom['name']
        if dom['score'] or dom['draw'] or args.save:
            for sim in data_list:
                _data, _lon, _lat = args.region.resample_to_subdomain(sim["precip_data"], sim["lon"], sim["lat"], subdomain_name, fix_nans=args.fix_nans)
                sim["lon_resampled"] = _lon
                sim["lat_resampled"] = _lat
                sim["precip_data_resampled"] = _data
            Parallel(n_jobs=16,backend='threading')(delayed(scoring.calc_scores)(sim, data_list[0], args) for ii, sim in enumerate(data_list))
            scoring.rank_scores(data_list)
            # scoring.total_fss_rankings(data_list, windows, thresholds)
            if args.ensemble_scores:
                ens_data = ensembles.detect_ensembles(data_list)
                ensemble_data = [ensembles.Ensemble(data_list, ens, nam, args) for nam, ens in ens_data.items()]
        else:
            logging.info("Skipping "+dom['name']+", nothing is requested.")
        if dom['score']:
            scoring.write_scores_to_csv(data_list, start_date, end_date, args, subdomain_name, windows, thresholds)
        if dom['draw']:
            if args.ensemble_scores:
                logging.info("Plotting pFSS for ensembles")
                levels = parameter_settings.get_fss_thresholds(args)
                windows=[10,20,30,40,60,80,100,120,140,160,180,200]
                panel_plotter.ens_fss_plot(ensemble_data, windows, levels, subdomain_name, args)
            plot_start = datetime.now()
            outfilename = panel_plotter.draw_panels(data_list, start_date, end_date, subdomain_name, args) #, mode=args.mode)
            plot_duration = datetime.now() - plot_start
            logging.info("Plotting "+str(len(data_list))+"panels took "+str(plot_duration))
            logging.info("File saved to: " + os.path.abspath(outfilename))
        if dom['score']:
            if args.save:
                io.save_data(data_list, subdomain_name, start_date, end_date, args)
            if args.save_full_fss:
                io.save_fss(data_list, subdomain_name, start_date, end_date, args)


if __name__ == '__main__':
    main()
