import numpy as np
import copy
import os
import pandas as pd
import fss_FFT
import fss_SAT
import parameter_settings
import csv


import logging
logger = logging.getLogger(__name__)

from paths import PAN_DIR_SCORES

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
            s = 1. / (1. - 0.5)
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


def voronoi_widths_1d(values, clip_min=0.0):
    """Per-point Voronoi cell widths for a 1-D non-uniform grid, in raw units.

    Interior cells use the half-distance to nearest neighbours. The first and
    last cells are extrapolated by half the adjacent interval (i.e. the cell
    is symmetric around its grid point). When `clip_min` is not None, the
    lower edge is clamped to it — used here to prevent negative precipitation
    thresholds or sub-zero window sizes from extending the first cell below
    a physical floor.
    """
    v = np.asarray(values, dtype=float)
    n = len(v)
    if n == 1:
        return np.array([1.0])
    midpoints = 0.5 * (v[:-1] + v[1:])
    left = v[0] - 0.5 * (v[1] - v[0])
    if clip_min is not None:
        left = max(clip_min, left)
    right = v[-1] + 0.5 * (v[-1] - v[-2])
    edges = np.concatenate([[left], midpoints, [right]])
    return np.diff(edges)


def weighted_fss_condensed_rect(sim, obs, levels):
    """Linear-Voronoi (rectangle) area-weighted condensed FSS on the fixed
    `(threshold x window)` grid, normalised to [0, 1], restricted to the
    obs-supported integration domain.

    Computes a weighted mean of the clamped-and-rescaled FSS values, with
    weights = `cell_area * l_fac * w_fac`. The cell area is the Voronoi
    cell area of the grid point on the raw `(t, w)` plane (Cartesian
    grid, so this reduces to the product of per-axis half-distances to
    nearest neighbours; corner cells extrapolated by half the adjacent
    interval, threshold lower edge clipped at 0).

    **N1 rule (obs-supported domain):** any threshold row for which the
    observation has no grid point above the threshold
    (`(obs > t).sum() == 0`) is skipped from both numerator and
    denominator. FSS is ill-defined as a spatial-skill metric when the
    observed binary field is empty, and including such cells with their
    full weight would conflate spatial-skill signal with false-alarm
    signal (especially severe at heavy thresholds where the cell
    weights are largest). False-alarm signal belongs in `bias` or a FAR
    count, not in cwFSS.

    Linear (raw-unit) Voronoi is used on both axes for consistency with
    the uniform R2 sampler in `CWFSS`: both then estimate the same
    functional over the obs-supported range.

    The result is dimensionless in [0, 1] and is directly comparable
    to the `CWFSS.cwfss` value produced by the quasi-random sampler in
    `ranking_check` (provided the R2 sampler is run on the same
    integration range). It is **not** on the same numerical scale as
    the legacy `fss_condensed_weighted` (which is an un-normalised
    sum). The companion `score_arr` returned here holds the
    un-normalised per-cell contributions for diagnostic use (zero for
    skipped cells).
    """
    obs_field = obs['precip_data_resampled']

    score_arr = np.zeros(sim['fssf'].values.shape)
    wins = np.asarray([np.max(w) for w in sim['fss_windows']], dtype=float)
    lvls = np.asarray(levels, dtype=float)

    dl = voronoi_widths_1d(lvls, clip_min=0.0)
    dw = voronoi_widths_1d(wins, clip_min=0.0)
    cell_area = np.outer(dl, dw)

    weighted_sum = 0.0
    weight_sum = 0.0
    skipped_thresholds = []

    max_l = np.max(levels[0:9])
    max_w = wins.max()
    for ii, t in enumerate(sim['fss_thresholds']):
        l = levels[ii]
        if (obs_field > l).sum() == 0:
            skipped_thresholds.append(l)
            continue
        a_ = sim['fss'].values[ii, :]
        a = copy.copy(a_)
        if t == 1.:
            a = np.where(a == 1., 1., 0.)
        else:
            s = 1. / (1. - 0.5)
            a = s * (a - 1) + 1
        a = clamp_array(a)
        for jj, w in enumerate(sim['fss_windows']):
            w = np.max(w)
            if not np.isnan(a[jj]):
                l_fac = (max_l + l) / max_l
                w_fac = 2. * max_w / (max_w + w)
                weight = cell_area[ii, jj] * l_fac * w_fac
                weighted_sum += weight * a[jj]
                weight_sum += weight
                score_arr[ii, jj] = weight * a[jj]

    if skipped_thresholds:
        logger.debug(
            f"{sim['name']}: N1 skipped {len(skipped_thresholds)} thresholds "
            f"(obs has no pixels above): {skipped_thresholds}")

    cwfss = weighted_sum / weight_sum if weight_sum > 0.0 else np.nan
    return cwfss, score_arr


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


def write_scores_to_csv(data_list, start_date, end_date, args, verification_subdomain, windows, thresholds):
    name_part = '' # if args.mode == 'None' else args.mode+'_'
    csv_file = "../SCORES/"+args.name+"RR_"+name_part+"score_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.csv'
    logging.info("Saving {csv_file}")
    start_date_str = start_date.strftime("%Y%m%d_%H")
    end_date_str = end_date.strftime("%Y%m%d_%H")
    csv_file = f"{PAN_DIR_SCORES}/{args.name}RR_{name_part}score_{start_date_str}UTC_{args.duration:02d}h_acc_{verification_subdomain}.csv"
    with open(csv_file, 'w') as f:
        score_writer = csv.writer(f, delimiter=';')
        col_labels = ["conf", "init", "lead", "name", "maximum", "average", "99th", "95th", "90th", "75th", "50th",
                      "bias", "mae", "rms", "corr", "d90", "fss_condensed", "fss_condensed_weighted",
                      "rank_mae", "rank_bias", "rank_rms", "rank_corr", "rank_d90", "rank_fss_condensed", "rank_fss_condensed_weighted"]
        score_writer.writerow(col_labels)
        for sim in data_list:
            percs = [sim["precip_data_resampled"].max(), sim["precip_data_resampled"].mean()]
            for p in [99., 95., 90., 75., 50.]:
                percs.append(np.percentile(sim["precip_data_resampled"], p))
            score_writer.writerow([
                sim['conf'], sim['init'], sim['lead'], sim['name'], 
                percs[0], percs[1], percs[2], percs[3], percs[4], percs[5], percs[6],
                sim['bias_real'], sim['mae'], sim['rms'], sim['corr'], sim['d90'], 
                sim['fss_condensed'], sim['fss_condensed_weighted'], 
                sim['rank_mae'], sim['rank_bias'], sim['rank_rms'], sim['rank_corr'], sim['rank_d90'], 
                sim['rank_fss_condensed'], sim['rank_fss_condensed_weighted']])
    if args.save_percentiles:
        csv_file = f"{PAN_DIR_SCORES}/{args.name}RR_percentiles_{name_part}score_{start_date_str}UTC_{args.duration:02d}h_acc_{verification_subdomain}.csv"
        logging.info("Saving percentiles to {csv_file}")
        with open(csv_file, 'w') as f:
            score_writer = csv.writer(f, delimiter=';')
            col_labels = ["conf", "init", "lead", "name"]
            for p in range(0, 101):
                col_labels.append(f"{p:d}th")
            score_writer.writerow(col_labels)
            for sim in data_list:
                percs = []
                for p in range(0, 101):
                    percs.append(np.percentile(sim["precip_data_resampled"], p))
                write_data = [sim['conf'], sim['init'], sim['lead'], sim['name'], *percs]
                score_writer.writerow(write_data)


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
    #windows=[10,20,30,40,60,80,100,120,140,160,180,200] # itt inkább térjen vissza egy függvénnyel 
    windows = parameter_settings.get_windows(args)

    ny, nx = sim["precip_data_resampled"].shape
    windows = prep_windows(windows, args.fss_calc_mode, nx, ny)
    fss_calc_func = fss_SAT.fss_cumsum_frame
    if args.fss_method == 'legacy':
        logger.info("FSS method is set to legacy, using old FFT approximation!")
        fss_calc_func = fss_FFT.fss_frame
    if sim['type'] == 'obs':
        sim['bias'] = 999
        sim['bias_real'] = 999
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
        sim['fss_condensed_weighted_rect'] = -999
        sim['fss'] = None
        sim['fssp'] = None
        sim['fss_num'] = None
        sim['fssp_num'] = None
        sim['fss_den'] = None
        sim['fssp_den'] = None
        # also add bogus init and lead for csv output
        sim['init'] = "1900-01-01 00:00:00"
        sim['lead'] = -1
    else:
        thresholds = []
        thresholds_percs = []
        for level in levels:
            thresholds.append(0.5)
            # thresholds.append((1+float((obs["precip_data_resampled"] > level).sum())/float(obs["precip_data_resampled"].size)))
        for perc in percs:
            thresholds_percs.append(0.5)
            # thresholds_percs.append(0.5*(1+perc/100.))
        sim['fss_thresholds'] = thresholds
        sim['fss_thresholds_percs'] = thresholds_percs
        sim['fssf_thresholds'] = thresholds + thresholds_percs
        # NaN-aware over jointly-valid pixels: observation fields (e.g. OPERA)
        # may carry NaN where there is no radar coverage. Restrict every
        # point statistic to pixels valid in *both* fields so a single NaN
        # does not poison the whole score.
        _mod = sim["precip_data_resampled"]
        _obs = obs["precip_data_resampled"]
        valid = ~(np.isnan(_mod) | np.isnan(_obs))
        n_valid = int(valid.sum())
        if n_valid < 2:
            logger.warning("%s: fewer than 2 jointly-valid pixels vs obs, "
                           "point scores set to NaN", sim['name'])
            bias = mae = rms = corr = np.nan
        else:
            _diff = _mod[valid] - _obs[valid]
            bias = np.mean(_diff)
            mae = np.mean(np.abs(_diff))
            rms = np.sqrt(np.mean(np.square(_diff)))
            corr = np.corrcoef(_mod[valid], _obs[valid])[0, 1]
            if n_valid < _mod.size:
                logger.debug("%s: point scores over %d/%d valid pixels (%.1f%% masked)",
                             sim['name'], n_valid, _mod.size,
                             100.0 * (1.0 - n_valid / _mod.size))
        threshold_mode = getattr(args, 'fss_threshold_mode', 'over')
        tolerance = getattr(args, 'fss_tolerance', 0.1)
        fss_num, fss_den, fss, ovest = fss_calc_func(
            sim["precip_data_resampled"],
            obs["precip_data_resampled"],
            windows,levels,percentiles=False, mode=args.fss_calc_mode.replace("_adaptive", ""),
            threshold_mode=threshold_mode, tolerance=tolerance)
        fssp_num, fssp_den, fssp, ovestp = fss_calc_func(
            np.copy(sim["precip_data_resampled"]), # circumvent numpy issue #21524
            np.copy(obs["precip_data_resampled"]), # circumvent numpy issue #21524
            windows,percs,percentiles=True, mode=args.fss_calc_mode.replace("_adaptive", ""),
            threshold_mode=threshold_mode, tolerance=tolerance)
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
        sim['fss_condensed_weighted_rect'], sim['fss_normalized_weighted_rect_arr'] = weighted_fss_condensed_rect(sim, obs, levels)
        logger.info(
            f"{sim['name']}: fss_condensed_weighted = {sim['fss_condensed_weighted']:.4f} (sum), "
            f"fss_condensed_weighted_rect = {sim['fss_condensed_weighted_rect']:.4f} (cwFSS in [0, 1])")
        sim['d90'] = fss_d90(sim["precip_data_resampled"], obs["precip_data_resampled"], args)
    return(sim)


def fss_d90(rrm, rro, args):
    """
    Estimate the displacement of the 90th-percentile precipitation field.

    Computes the FSS between the surplus (non-overlapping) parts of the
    binary p90 fields at increasing window sizes, and finds the half-window
    at which the FSS reaches 0.5 via linear interpolation.

    Returns the displacement in km (half-window size), or 9999. / np.nan
    for degenerate cases.
    """
    fss_calc_func = fss_SAT.fss_cumsum_frame
    if args.fss_method == 'legacy':
        logger.info("FSS method is set to legacy, using old FFT approximation for D90!")
        fss_calc_func = fss_FFT.fss_frame
    windows = [3, 5, 7, 11, 21, 31, 41, 51, 61, 81, 101, 121, 141, 181, 251, 351, 501, 701]
    windows_2d = prep_windows(windows, args.mode, *rrm.shape)
    levels = [0.5]
    # NaN-aware: observation fields (e.g. OPERA) may contain NaN where there is
    # no radar coverage. A plain np.percentile would return NaN and silently
    # turn the binary intense field into all-zeros. Use nanpercentile and treat
    # unobserved pixels as non-events in both fields so they add no displacement.
    obs_unobserved = np.isnan(rro)
    if obs_unobserved.all() or np.isnan(rrm).all():
        logger.warning("Observation or model field is entirely NaN, returning no d90!")
        return np.nan
    p90_obs = np.nanpercentile(np.copy(rro), 90)
    p90_mod = np.nanpercentile(np.copy(rrm), 90)
    # comparisons against NaN yield False, so NaN pixels become 0 (non-event)
    _rro = np.where(rro >= p90_obs, 1, 0)
    _rrm = np.where(rrm >= p90_mod, 1, 0) # circumvent numpy issue #21524
    # do not credit/penalise displacement where the obs is unobserved
    _rrm[obs_unobserved] = 0
    if np.sum(_rrm) == 0:
        logger.warning("No precipitation in model array, returning no d90!")
        return np.nan
    if np.sum(_rro) == 0:
        logger.warning("No intense precipitation in observation array "
                       "(after NaN masking), returning no d90!")
        return np.nan
    # if p90 threshold equals the field minimum, the percentile cannot
    # distinguish intense from non-intense pixels (e.g. constant or all-zero field)
    if p90_mod <= np.nanmin(rrm):
        logger.warning("Model p90 threshold (%.4f) equals field minimum — "
                        "cannot identify intense precipitation area, returning no d90!", p90_mod)
        return np.nan
    # surplus fields: non-overlapping parts of the binary p90 fields
    rro_s = np.maximum(_rro - _rrm, 0)
    rrm_s = np.maximum(_rrm - _rro, 0)
    _, _, _arr, _ = fss_calc_func(
        rro_s.astype(float), rrm_s.astype(float), windows_2d, levels,
        mode=args.fss_calc_mode)
    arr = _arr.values.flatten()
    logger.debug("FSS array for D90 calculation:")
    logger.debug(arr)
    # monotonicity check with tolerance for numerical noise
    for ii in range(1, len(arr)):
        if arr[ii] - arr[ii-1] < -0.01:
            logger.info("non-monotonous FSS array in D90, returning no d90!")
            return 9999.
    if arr[0] >= 0.5:
        return 0.
    # find where the array exceeds 0.5 and interpolate
    ii = 0
    while arr[ii] < 0.5:
        ii += 1
        if ii == len(arr) - 1:
            logger.info("FSS never reaches 0.5, returning no d90!")
            return 9999.
    t = (0.5 - arr[ii-1]) / (arr[ii] - arr[ii-1])
    d = windows[ii-1] + t * float(windows[ii] - windows[ii-1])
    if d < 0:
        d = 0.
    return 0.5 * d
