import numpy as np
import copy
import os
import pandas as pd
import fss_functions
import parameter_settings

import logging
logger = logging.getLogger(__name__)

def array_minus_avg(a, t):
    """
    calculate the average value of an array and subtract it from all
    elements, ignore and keep NaNs, respect fss skill/use thresholds
    a ....... 1d array containing all fss values for one window/threshold
    t ....... float, skillful/useful threshold for the FSS derived from OBS

    Return:
    np.array (1D) with
    10. ......................... if a was a NaN
    -10. ........................ if a was below useful
    original value - AVG  ....... otherwise
    """
    a_filtered = np.where(a > t, a, np.nan)
    avg_filtered = np.nanmean(a_filtered)
    a_normed = a - avg_filtered
    a_normed = np.where(a < t, -10., a_normed)
    a_normed = np.where(np.isnan(a), 10., a_normed)
    return a_normed


def clamp_array(a, xmin=0., xmax=1):
    """ clamp array to values between xmin and xmax """
    a = np.where(a < xmin, xmin, a)
    a = np.where(a > xmax, xmax, a)
    return a


def rank_array(a_in,t):
    """
    dirty and cumbersome ranking funktion for a 1d numpy array

    implemented to circumnavigate the shortcomings of built-in sorting functions
    1. rank NaN with 0
    2. rank anything below the 0.5+0.5f threshold with rank 1
    3. rank perfect scores with 2
    4. rank the rest 3 and higher
       - Rank 3 ..... gold
       - Rank 4 ..... silver
       - Rank 5 ..... bronze
       - Rank 6+ .... white
    5. equal values get the same rank
    6. if N values are equal, the next N-1 ranks are skipped

    Ranks 3 and higher are valid ranks
    """
    a = copy.copy(a_in)
    ranks = np.zeros(len(a))
    for ii in range(len(a)):
        # sort out missing vlaues (-> black)
        if np.isnan(a[ii]):
            a[ii] = -99.
            ranks[ii] = 0.
        # sort out useless values (below the no-skill threshold, -> red)
        elif a[ii] < t:
            a[ii] = -98.
            ranks[ii] = 1.
    jj = 2.
    same = 0.
    previous = -999.
    for ii in range(len(a)):
        if a.max() > -88.:
            idx = np.argmax(a)
            if a[idx] > -88.:
                if a[idx] == 1.:
                    ranks[idx] = 2.
                    jj += 1.
                    a[idx] = -97.
                else:
                    # increment to 3 for gold (best rank but not perfect)
                    # if no perfect score was found before!
                    # this will catch all other ranks
                    if jj == 2.:
                        jj += 1. 
                    if a[idx] == previous:
                        same += 1.
                    else:
                        same = 0.
                    ranks[idx] = jj - same
                    jj += 1.
                    previous = a[idx]
                    a[idx] = -88.
        else:
            break
    return ranks


def fss_condensed(sim):
    """
    assign 0 to 1 points per window/threshold combo where RSS values from 0 to f0
    geet 0 points and values between f0 and 1 are mapped to 0 ... 1
    """
    score = 0.
    score_arr = np.zeros(sim['fss'].values.shape)
    for ii, t in enumerate(sim['fss_thresholds']):
        a_ = sim['fss'].values[ii, :]
        a = copy.copy(a_)
        if t == 1.: #catch cases where the entire domain is above the precip threshold
            a = np.where(a == 1., 1. ,0.) #???
        else:
            s = 1. / (1. - t)
            a = s * (a - 1) + 1
        a = clamp_array(a)
        score_arr [ii, :] = a
        score += np.nansum(a)
    return score, score_arr


def weighted_fss_condensed(sim, levels):
    score = 0.
    score_arr = np.zeros(sim['fssf'].values.shape)
    wins = np.asarray(sim['fss_windows'])
    max_l = np.max(levels[0:9])
    max_w = wins.max()
    for ii, t in enumerate(sim['fss_thresholds']):
        a_ = sim['fss'].values[ii, :]
        a = copy.copy(a_)
        if t == 1.: #catch cases where the entire domain is above the precip threshold
            a = np.where(a == 1., 1. ,0.) #???
        else:
            s = 1. / (1. - 0.5)
            # s = 1. / (1. - t)
            a = s * (a - 1) + 1
        a = clamp_array(a)
        l = levels[ii]
        for jj, w in enumerate(sim['fss_windows']):
            w = np.max(w) # reduce the x and y and take only the larger one
            # linear weighting where smallest window is roughlty 2x the weight of the largest
            # and smallest threshold is roughtly 2x the weight of the largest
            if not np.isnan(a[jj]):
                l_fac = (max_l + l) / max_l      # 2 for max precip, 1 for 0.
                w_fac = 2. * max_w / (max_w + w) # 2 for window size of 0, 1 for max window size
                score += l_fac * w_fac * a[jj]
                score_arr [ii, jj] = l_fac * w_fac * a[jj]
    return score, score_arr


def rank_fss_all(data_list):
    """
    Add some keys to the sim dicts which indicate the
    rank of the respective sim for each metric

    MAE, RMSE ..... lowest is best
    BIAS .......... lowest absolute is best
    CORRELATION ... highest is best
    """
    namelist = [d['name'] for d in data_list]
    
    for metric in ['fss_total_abs_score', 'fss_total_rel_score', 'fss_success_rate_abs', 'fss_success_rate_rel']:
        rank=1
        rank_name='rank_'+metric
        data_list_metric = sorted(data_list, key=lambda k: -k[metric])
        for data_entry in data_list_metric:
            data_list[namelist.index(data_entry['name'])][rank_name] = rank
            rank = rank + 1
    return data_list


def rank_scores(data_list):
    """
    Add some keys to the sim dicts which indicate the
    rank of the respective sim for each metric

    MAE, RMSE ..... lowest is best
    BIAS .......... lowest absolute is best
    CORRELATION ... highest is best
    """
    namelist = [d['name'] for d in data_list]
    logging.info("Ranking")
    for metric in ['mae', 'bias', 'rms', 'corr', 'd90', 'fss_condensed', 'fss_condensed_weighted']:
        rank=1
        rank_name='rank_'+metric
        if metric == 'bias':
            data_list_metric = sorted(data_list, key=lambda k: np.abs(k[metric]))
        elif metric == 'corr' or metric == 'fss_success_rate_abs' or metric == 'fss_success_rate_rel' \
             or metric == 'fss_condensed' or metric == 'fss_condensed_weighted':
            data_list_metric = sorted(data_list, key=lambda k: -k[metric])
        else:
            data_list_metric = sorted(data_list, key=lambda k: k[metric])
        for data_entry in data_list_metric:
            data_list[namelist.index(data_entry['name'])][rank_name] = rank
            rank = rank + 1
    for sim in data_list:
        sim['average_rank'] = 0.25*(float(sim['rank_bias']) + float(sim['rank_mae']) + float(sim['rank_rms']) + float(sim['rank_corr']))
    for metric in ['average_rank']:
        rank=1
        rank_name='rank_'+metric
        data_list_metric = sorted(data_list, key=lambda k: k[metric])
        for data_entry in data_list_metric:
            data_list[namelist.index(data_entry['name'])][rank_name] = rank
            rank = rank + 1
    fss_list = []
    for sim in data_list[1:]:
        fss_list.append(np.asarray(sim['fssf'].values, dtype=float))
    fss = np.asarray(fss_list, dtype=float)
    fss_order = np.zeros(fss.shape, dtype = int)
    fss_rel = np.zeros(fss.shape, dtype = float) 
    for ii in range(fss.shape[1]):
        for jj in range(fss.shape[2]):
            fss_order[:,ii,jj] = rank_array(fss[:,ii,jj], sim['fssf_thresholds'][ii])
            fss_rel[:,ii,jj] = array_minus_avg(fss[:,ii,jj], sim['fssf_thresholds'][ii])
    bogus_fss = np.empty((fss.shape[1],fss.shape[2]))
    bogus_fss[:,:] = -999
    sim['fss_ranks'] = bogus_fss
    data_list[0]['max_rank'] = np.max(fss_order)
    for idx in range(1, fss.shape[0]+1):
        data_list[idx]['fss_ranks'] = fss_order[idx-1,:,:]
        data_list[idx]['fss_rel'] = fss_rel[idx-1,:,:]
    return data_list


def fss_overall_values(fss_ranks, windows, thresholds):
    # takes fss as numpy array, returns some single fss_overall_values
    fss_ranks = np.where(fss_ranks == 2, 3, fss_ranks) # merge number 1 and perfect scores
    fss_ranks_abs = fss_ranks[ 0: 9,:] # ranks for absolute thresholds
    fss_ranks_rel = fss_ranks[10:15,:] # ranks for percentiles
    # fss_ranks_abs_high = fss_ranks[ 4: 9,:] # ranks for absolute thresholds

    fss_total_abs_score = np.sum(np.where(fss_ranks_abs < 2, 0, 1./(fss_ranks_abs-2))) # better rank > more score
    fss_total_rel_score = np.sum(np.where(fss_ranks_rel < 2, 0, 1./(fss_ranks_rel-2))) # better rank > more score
    fss_success_rate_abs = np.mean(np.where(fss_ranks_abs == 1, 0, 1))
    fss_success_rate_rel = np.mean(np.where(fss_ranks_rel == 1, 0, 1))
    return fss_total_abs_score, fss_total_rel_score, fss_success_rate_abs, fss_success_rate_rel


def total_fss_rankings(data_list, windows, thresholds):
    for sim in data_list[1::]:
        sim['fss_total_abs_score'], sim['fss_total_rel_score'], sim['fss_success_rate_abs'], sim['fss_success_rate_rel'] = fss_overall_values(sim['fss_ranks'], windows, thresholds)
    data_list = rank_fss_all(data_list)
    return data_list
    

def write_scores_to_csv(data_list, start_date, end_date, args, verification_subdomain, windows, thresholds):
    # TODO
    # sim['fss'] = fss
    # sim['fss_ranks'] = fss
    import csv
    name_part = '' # if args.mode == 'None' else args.mode+'_'
    csv_file = "../SCORES/"+args.name+"RR_"+name_part+"score_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.csv'
    tmp_file = "../SCORES/"+args.name+"RR_"+name_part+"score_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.tmp'
    score_table = []
    score_table2 = []
    row_labels = []
    with open(csv_file, 'w') as f:
        score_writer = csv.writer(f, delimiter=',')
        col_labels = ['name', 'bias', 'mae', 'rms', 'corr', 'd90', 'rank_bias', 'rank_mae', 'rank_rms', 'rank_corr',
            'rank_d90', 'fss_rank_score', 'fss_success_rate_abs', 'fss_percentiles_rank_score',
            'fss_success_rate_rel']
        col_labels2 = ['Bias', 'MAE', 'RMS', 'Corr']
        col_labels3 = ['FSS', 'SR', 'FSS%', 'SR%']
        score_writer.writerow(col_labels)
        for sim in data_list[1::]:
            fss_total_abs_score, fss_total_rel_score, fss_success_rate_abs, fss_success_rate_rel = fss_overall_values(sim['fss_ranks'], windows, thresholds)
            score_writer.writerow([
                sim['name'].replace(' ','_'), 
                "{:.5f}".format(sim['bias_real']), "{:.5f}".format(sim['mae']), "{:.5f}".format(sim['rms']), "{:.5f}".format(sim['corr']), "{:.5f}".format(sim['d90']),
                str(sim['rank_bias']), str(sim['rank_mae']), str(sim['rank_rms']), str(sim['rank_corr']), str(sim['rank_d90']),
                "{:.5f}".format(fss_total_abs_score), "{:.5f}".format(fss_success_rate_abs), "{:.5f}".format(fss_total_rel_score),
                "{:.5f}".format(fss_success_rate_rel)])
            score_table.append([
                "{:.3f}".format(sim['bias_real']), "{:.3f}".format(sim['mae']), "{:.3f}".format(sim['rms']), "{:.3f}".format(sim['corr'])])
            score_table2.append([
                "{:.3f}".format(fss_total_abs_score), "{:.3f}".format(fss_success_rate_abs), "{:.3f}".format(fss_total_rel_score), "{:.3f}".format(fss_success_rate_rel)])
            row_labels.append(sim['name'])
    os.system("column -t -s , "+csv_file+" > "+tmp_file+" && mv "+tmp_file+" "+csv_file)
    return score_table, score_table2, col_labels2, col_labels3, row_labels


def prep_windows(ww, mode, nx, ny):
    windows_shape = (len(ww), 2)
    windows_ret = np.zeros(windows_shape, dtype=int)
    for idx, w in enumerate(ww):
        windows_ret[idx, 0] = ny if mode == 'valid_adaptive' and w > ny else w
        windows_ret[idx, 1] = nx if mode == 'valid_adaptive' and w > nx else w
    return windows_ret
        
def calc_scores(sim, obs, args):
    """
    calculate verification metrics MAE, RMSE, BIAS and CORRELATION COEFFICIENT

    INCA is perfect, so it gets assinged really bad values manually to exclude it from
    the ranking later on
    """
    logger.info('Calculating scores for '+sim['name'])
    percs=[25, 50, 75, 90, 95]
    levels = parameter_settings.get_fss_thresholds(args)
    windows=[10,20,30,40,60,80,100,120,140,160,180,200]
    ny, nx = sim["precip_data_resampled"].shape
    windows = prep_windows(windows, args.fss_calc_mode, nx, ny)
    if sim['conf'] == 'INCA' or sim['conf'] == 'OPERA':
        sim['bias'] = 999
        sim['mae'] = 999
        sim['rms'] = 999
        sim['corr'] = -999
        sim['d90'] = 9999.
        sim['fss_total_abs_score'] = -999
        sim['fss_total_rel_score'] = -999
        sim['fss_success_rate_abs'] = -999
        sim['fss_success_rate_rel'] = -999
        sim['fss_condensed'] = -999
        sim['fss_condensed_weighted'] = -999
        sim['fss'] = None
        sim['fssp'] = None
        sim['fss_num'] = None
        sim['fssp_num'] = None
        sim['fss_den'] = None
        sim['fssp_den'] = None
    else:
        thresholds = []
        thresholds_percs = []
        for level in levels:
            thresholds.append(0.5*(1+float((obs["precip_data_resampled"] > level).sum())/float(obs["precip_data_resampled"].size)))
        for perc in percs:
            thresholds_percs.append(0.5*(1+perc/100.))
        sim['fss_thresholds'] = thresholds
        sim['fss_thresholds_percs'] = thresholds_percs
        sim['fssf_thresholds'] = thresholds + thresholds_percs
        bias = np.mean(sim["precip_data_resampled"]-obs["precip_data_resampled"])
        mae = np.mean(np.abs(sim["precip_data_resampled"]-obs["precip_data_resampled"]))
        rms = np.sqrt(np.mean(np.square(sim["precip_data_resampled"]-obs["precip_data_resampled"])))
        corr = np.corrcoef(sim["precip_data_resampled"].flatten(),obs["precip_data_resampled"].flatten())[0,1]
        fss_num, fss_den, fss, ovest = fss_functions.fss_frame(
            sim["precip_data_resampled"],
            obs["precip_data_resampled"],
            windows,levels,percentiles=False, mode=args.fss_calc_mode.replace("_adaptive", ""))
        fssp_num, fssp_den, fssp, ovestp = fss_functions.fss_frame(
            np.copy(sim["precip_data_resampled"]), # circumvent numpy issue #21524
            np.copy(obs["precip_data_resampled"]), # circumvent numpy issue #21524
            windows,percs,percentiles=True, mode=args.fss_calc_mode.replace("_adaptive", "")) 
        fssf = pd.concat((fss, fssp), axis=0)
        ovestf = pd.concat((ovest, ovestp), axis=0)
        sim['bias'] = np.abs(bias)
        sim['bias_real'] = bias
        sim['mae'] = mae
        sim['rms'] = rms
        sim['corr'] = corr
        sim['fss_windows'] = windows
        sim['fss'] = fss
        sim['fssp'] = fssp
        sim['fss_num'] = fss_num
        sim['fssp_num'] = fssp_num
        sim['fss_den'] = fss_den
        sim['fssp_den'] = fssp_den
        sim['fssf'] = fssf
        sim['fss_overestimated'] = ovestf
        sim['fss_condensed'], sim['fss_normalized_arr'] = fss_condensed(sim)
        sim['fss_condensed_weighted'], sim['fss_normalized_weighted_arr'] = weighted_fss_condensed(sim, levels)
        sim['d90'] = fss_d90(sim["precip_data_resampled"], obs["precip_data_resampled"], args)
    return(sim)


def fss_d90(rrm, rro, args):
    """
    arr .... array-like

    Loops over array and returns the estimated window size at which arr
    equals 0.5. Values are linearly interpolated between array entries.
    Missing Values / Fails return 9999.
    """
    # consistency check
    windows = [1, 3, 5, 7, 11, 21, 31, 41, 51, 61, 81, 101, 121, 141, 181, 251, 351, 501, 701]
    windows_2d = prep_windows(windows, args.mode, *rrm.shape)
    levels = [0.5]
    _rro = np.where(rro > np.percentile(np.copy(rro), 90), 1, 0)
    rrm = np.where(rrm > np.percentile(np.copy(rrm), 90), 1, 0) # circumvent numpy issue #21524
    #rrm = np.where(rrm > np.percentile(rrm, 90), 1, 0)
    rro_s = np.maximum(_rro-rrm, 0)
    rrm_s = np.maximum(rrm-_rro, 0)
    if np.sum(rrm) == 0:
        logger.warning("No precipitation in model array, returning no d90!")
        return np.nan
    overlap = float(np.sum(_rro*rrm))/float(np.sum(rrm))
    _, _, _arr, _ = fss_functions.fss_frame(rro_s, rrm_s, windows_2d, levels, args.fss_calc_mode)
    arr = _arr.values.flatten()
    for ii in range(1,len(arr)):
        if arr[ii] - arr[ii-1] < 0:
            logger.info("non-monotonous array in argument, returning no d90!")
            return 9999.
    # find where the array exceeds 0.5 and interpolate the window size (km equivalent)
    ii = 0
    while arr[ii] < 0.5:
        ii += 1
        if ii == len(arr)-1:
            logger.info("all elements of argument are <0.5, returning no d90!")
            return 9999.
    t = (0.5-arr[ii-1])/(arr[ii]-arr[ii-1])
    d = windows[ii-1]+t*float(windows[ii]-windows[ii-1])
    if d < 0:
        d = 0.
    return 0.5 * d
