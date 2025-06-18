import numpy as np
import fss_functions
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
        logger.info(f"Created ensemble {self.name} with {self.member_count} members")
        self.thresholds = parameter_settings.get_fss_thresholds(args)
        ww = [10,20,30,40,60,80,100,120,140,160,180,200]
        self.windows = prep_windows(ww, args.fss_calc_mode, nx, ny)
        self.calc_scores()
        self.save()
        
    def calc_scores(self):
        logger.info(f"  Calculating pFSS for {self.name}")
        self.pFSS = fss_functions.fss_frame_eps(self.precip_data_resampled, self.obs_data_resampled, self.windows, self.thresholds)
        logger.info(f"  Calculating emFSS for {self.name}")
        self.emFSS = fss_functions.fss_frame(np.mean(self.precip_data_resampled, axis=0), self.obs_data_resampled, self.windows, self.thresholds)
        logger.info(f"  Calculating dFSS for {self.name}")
        self.calc_dFSS()
        logger.info(f"  Calculating CRPS for {self.name}")
        self.calc_CRPS()


    def calc_dFSS(self):
        combos = list(combinations([x for x in range(self.member_count)], 2))
        self.dFSS = Parallel(n_jobs=16, backend='threading')(delayed(fss_functions.fss_raw)(self.precip_data_resampled[combo[0]], self.precip_data_resampled[combo[1]], self.windows, self.thresholds) for combo   in combos)
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
