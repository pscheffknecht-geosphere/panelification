import numpy as np
import pandas as pd
from model_parameters import verification_subdomains, default_subdomains, subdomain_precip_thresholds

import logging
logger = logging.getLogger(__name__)

def get_interesting_subdomains(obs_data, args):
    """ check all subdomains and get the 3 with the highest precipitation """
    lon_o = obs_data['lon']
    lat_o = obs_data['lat']
    RR_obs = obs_data['precip_data']
    RR_means, RR_maxes, RR_names, RR_draw, RR_score = ([] for _ in range(5))
    logger.debug(args.subdomains)
    for subdomain_name, subdomain_data in args.region.subdomains.items():
    # loop_subdomains = args.subdomains if args.subdomains else default_subdomains
    # for name in loop_subdomains:
        draw_avg = subdomain_data["thresholds"]["draw_avg"]
        draw_max = subdomain_data["thresholds"]["draw_max"]
        score_avg = subdomain_data["thresholds"]["score_avg"]
        score_max = subdomain_data["thresholds"]["score_max"]
        # if name == 'Custom':
        #     limits = args.lonlat_limits
        # else:
        #     limits = verification_subdomains[name]
        RR_obs_subdomain, _, _ = args.region.resample_to_subdomain(RR_obs, lon_o, lat_o, subdomain_name, fix_nans=args.fix_nans)
        RR_obs_subdomain_mean = np.mean(RR_obs_subdomain)
        RR_obs_subdomain_max = np.max(RR_obs_subdomain)
        RR_means.append(RR_obs_subdomain_mean)
        RR_maxes.append(RR_obs_subdomain_max)
        RR_names.append(subdomain_name)
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

