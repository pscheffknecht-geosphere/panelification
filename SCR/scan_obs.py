import numpy as np
import pandas as pd
from model_parameters import verification_subdomains, default_subdomains, subdomain_precip_thresholds

import logging
logger = logging.getLogger(__name__)

def get_rain_mean_max(lon_o, lat_o, RR_obs, limits):
        dists_min = (lon_o - limits[0])**2 + (lat_o - limits[2])**2
        dists_max = (lon_o - limits[1])**2 + (lat_o - limits[3])**2
        idx_min = np.where(dists_min==dists_min.min())
        idx_max = np.where(dists_max==dists_max.min())
        logger.debug(idx_min)
        logger.debug(idx_max)
        logger.debug((idx_min[0][0], idx_max[0][0], idx_min[1][0], idx_max[1][0]))
        logger.debug((idx_min[0][0], idx_max[0][0], idx_min[1][0], idx_max[1][0]))
        RR_obs_subdomain_mean = np.mean(RR_obs[idx_min[0][0]:idx_max[0][0],idx_min[1][0]:idx_max[1][0]])
        RR_obs_subdomain_max = np.max(RR_obs[idx_min[0][0]:idx_max[0][0],idx_min[1][0]:idx_max[1][0]])
        return RR_obs_subdomain_mean, RR_obs_subdomain_max


def get_interesting_subdomains(inca_data, args):
    """ check all subdomains and get the 3 with the highest precipitation """
    lon_o = inca_data['lon']
    lat_o = inca_data['lat']
    RR_obs = inca_data['precip_data']
    RR_means, RR_maxes, RR_names, RR_draw, RR_score = ([] for _ in range(5))
    loop_subdomains = args.subdomains if args.subdomains else default_subdomains
    logger.debug(args.subdomains)
    logger.debug(default_subdomains)
    logger.debug(loop_subdomains)
    for name in loop_subdomains:
        if not name in subdomain_precip_thresholds.keys():
            logger.warning("Subdomain {:s} has no precipitation thresholds, using default values")
            threshold_name = 'Default'
        else:
            threshold_name = name

        draw_avg = subdomain_precip_thresholds[threshold_name]['draw_avg']
        draw_max = subdomain_precip_thresholds[threshold_name]['draw_max']
        score_avg = subdomain_precip_thresholds[threshold_name]['score_avg']
        score_max = subdomain_precip_thresholds[threshold_name]['score_max']
        if name == 'Custom':
            limits = args.lonlat_limits
        else:
            limits = verification_subdomains[name]
        RR_obs_subdomain_mean, RR_obs_subdomain_max = get_rain_mean_max(lon_o, lat_o, RR_obs, limits)
        RR_means.append(RR_obs_subdomain_mean)
        RR_maxes.append(RR_obs_subdomain_max)
        RR_names.append(name)
        if ((RR_obs_subdomain_mean >  draw_avg or RR_obs_subdomain_max > draw_max) and args.draw) or args.forcedraw:
            RR_draw.append(True)
        else:
            RR_draw.append(False)
        if (RR_obs_subdomain_mean > score_avg or RR_obs_subdomain_max > score_max) or args.forcescore:
            RR_score.append(True)
        else:
            RR_score.append(False)
    df_subdomain_details = pd.DataFrame(
        list(zip(RR_names, RR_means, RR_maxes, RR_draw, RR_score)), columns=['name', 'mean', 'max', 'draw', 'score'])
    logger.info("Subomains to use are:")
    logger.info(df_subdomain_details)
    return df_subdomain_details

