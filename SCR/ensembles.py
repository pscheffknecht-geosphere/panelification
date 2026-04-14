import numpy as np
import fss_FFT
import fss_SAT
import parameter_settings
from itertools import combinations
from joblib import Parallel, delayed

from scoring import prep_windows

import logging
logger = logging.getLogger(__name__)

import pickle

### ENSEMBLE SCORING
# TODO: organize this better, remove code duplication, redundancies
# this is bad, but we had no time

# prepare a dictionary of ensemble names in the data and member count
def detect_ensembles(data_list):
    ensembles = {}
    for idx, sim in enumerate(data_list):
        if 'ensemble' in sim.keys():
            logger.info(f"Model {sim['name']} has ensemble {sim['ensemble']}")
            if sim['ensemble']:
                if not sim['ensemble'] in ensembles.keys():
                    ensembles[sim['ensemble']] = {}
                    ensembles[sim['ensemble']]['name'] = sim['ensemble']
                    ensembles[sim['ensemble']]['data_indices'] = [idx]
                    ensembles[sim['ensemble']]['member_count'] = 1
                else:
                    ensembles[sim['ensemble']]['member_count'] += 1
                    ensembles[sim['ensemble']]['data_indices'].append(idx)
        else:
            logger.info(f"Model {sim['name']} has NO ensemble key")
    for key, ens in ensembles.items():
        logger.info(f"Found ensemble {key} with {ens['member_count']} members in input data.")
        logger.info(f"  Indices are: {ens['data_indices']}")
    return ensembles


def add_ensemble_pseudo_members(data_list, ensembles_dict):
    """For each detected ensemble, append two pseudo-model entries to
    data_list: the per-grid-point ensemble mean and median of the
    members' native precip_data fields. These pseudo-models look like
    regular sims so they go through the standard resample/score/plot
    workflow. Members of one ensemble are assumed to share the same
    native grid (lon/lat from the first member). For lagged ensembles
    the latest member init is used as the pseudo-model init."""
    pseudo_specs = [("mean", np.mean), ("median", np.median)]
    for ens_name, ens in ensembles_dict.items():
        member_indices = ens['data_indices']
        ref = data_list[member_indices[0]]
        stack = np.stack([data_list[i]['precip_data'] for i in member_indices], axis=0)
        latest_init = max(data_list[i]['init'] for i in member_indices)
        for stat_name, stat_func in pseudo_specs:
            field = stat_func(stack, axis=0)
            pseudo = {
                'case': ref.get('case', ''),
                'exp':  f"{ens_name}_{stat_name}",
                'conf': f"{ens_name}_{stat_name}",
                'type': 'model',
                'init': latest_init,
                'lead': ref.get('lead', 0),
                'name': f"{ens_name}_{stat_name}",
                'lon':  ref['lon'],
                'lat':  ref['lat'],
                'precip_data': field,
                'color': 'black' if stat_name == 'mean' else 'dimgray',
                'ensemble': None,
                'pseudo': True,
            }
            data_list.append(pseudo)
            logger.info(f"Added pseudo-member {pseudo['name']} from {len(member_indices)} members "
                        f"(init={latest_init})")
    return data_list


class Ensemble:
    def __init__(self, data_list, single_ens_dict, ens_name, args):
        self.member_count = single_ens_dict['member_count']
        self.name = single_ens_dict['name']
        self.data_indices = single_ens_dict['data_indices']
        nx, ny = data_list[self.data_indices[0]]['precip_data_resampled'].shape
        self.precip_field_shape = (self.member_count, nx, ny)
        self.precip_data_resampled = np.zeros(self.precip_field_shape)
        for ii, idx in enumerate(self.data_indices):
            self.precip_data_resampled[ii, :, :] = data_list[idx]['precip_data_resampled']
        self.obs_data_resampled = data_list[0]['precip_data_resampled']
        self.obs_name = data_list[0].get('name', 'Observations')
        self.lon = data_list[0]['lon_resampled']
        self.lat = data_list[0]['lat_resampled']
        logger.info(f"Created ensemble {self.name} with {self.member_count} members")
        self.thresholds = parameter_settings.get_fss_thresholds(args)
        ww = [10,20,30,40,60,80,100,120,140,160,180,200]
        self.windows = prep_windows(ww, args.fss_calc_mode, nx, ny)
        self.fss_method = args.fss_method
        self.threads = args.threads
        self.calc_scores()
        self.save()
        
    def calc_scores(self):
        logger.info(f"  Calculating pFSS for {self.name}")
        if self.fss_method == "legacy":
            self.pFSS = fss_FFT.fss_frame_eps(self.precip_data_resampled, self.obs_data_resampled, self.windows, self.thresholds)
        else:
            self.pFSS = fss_SAT.fss_cumsum_frame(self.precip_data_resampled, self.obs_data_resampled, self.windows, self.thresholds, eps=True)
        logger.info(f"  Calculating emFSS for {self.name}")
        if self.fss_method == "legacy":
            self.emFSS = fss_FFT.fss_frame(np.mean(self.precip_data_resampled, axis=0), self.obs_data_resampled, self.windows, self.thresholds)
        else:
            self.emFSS = fss_SAT.fss_cumsum_frame(np.mean(self.precip_data_resampled, axis=0), self.obs_data_resampled, self.windows, self.thresholds)
        logger.info(f"  Calculating dFSS for {self.name}")
        self.calc_dFSS()
        logger.info(f"  Calculating CRPS for {self.name}")
        self.calc_CRPS()


    def calc_dFSS(self):
        combos = list(combinations([x for x in range(self.member_count)], 2))
        if self.fss_method == "legacy":
            self.dFSS = Parallel(n_jobs=self.threads, backend='threading')(delayed(fss_FFT.fss_raw)(
            self.precip_data_resampled[combo[0]],
            self.precip_data_resampled[combo[1]],
            self.windows,
            self.thresholds
            ) for combo in combos)
        else:
            self.dFSS = Parallel(n_jobs=self.threads, backend='threading')(delayed(fss_SAT.fss_cumsum_frame)(
            self.precip_data_resampled[combo[0]], 
            self.precip_data_resampled[combo[1]], 
            self.windows, 
            self.thresholds, 
            raw=True) for combo in combos)
        self.dFSSmean = np.nanmean(self.dFSS, axis=0)
        self.dFSSstdev = np.nanstd(self.dFSS, axis=0)

    def calc_CRPS(self):
        t1 = np.mean(np.abs(self.precip_data_resampled - self.obs_data_resampled), axis=0)
        diffs = np.abs(self.precip_data_resampled[:, None, :, :] - self.precip_data_resampled[None, :, :, :])
        t2 = 0.5 * np.mean(diffs, axis=(0, 1))
        self.CRPS = t1 - t2
    
    def save(self):
        with open(f"ENS_{self.name}.p", "wb") as f:
            pickle.dump(self, f)
