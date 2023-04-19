import numpy as np


def get_quadrants(df_fss, validity_thresholds=None, rr_max_obs=None):
    """ arguments:
    df_fss .................. pandas dataframe containing FSS data
    precip_threshold ........ float
    window_size_threshold ... int

    Splits an FSS dataframe into 4 quadrants. If no thresholds are given,
    the split attempts to make the quadrants equal size. The smaller windows
    and higher precpitation parts are rounded down if size is uneven.

    Returns:
    df_small_high ..... pandas dataframe for small scale high precipitation
    df_large_high ..... pandas dataframe for large scale high precipitation
    df_small_low ...... pandas dataframe for small scale low precipitation
    df_large_low ...... pandas dataframe for large scale low precipitation
    """
    thresholds = df_fss.axes[0].values
    if rr_max_obs is None:
        th_mid = len(thresholds)/2
        th_low = thresholds[0:th_mid]
        th_high = thresholds[th_mid+1:]
    else:
        th_max_ind = np.where(thresholds==np.max(thresholds[thresholds<rr_max_obs]))[0][0]
        th_mid = th_max_ind/2
        th_low = thresholds[0:th_mid]
        th_high = thresholds[th_mid+1:th_max_ind]
    windows = df_fss.axes[1].values
    wd_mid = len(windows)/2
    wd_small = windows[0:wd_mid]
    wd_large = windows[wd_mid+1:]
    df1 = df_fss[wd_small][0:thresholds[th_mid]]
    df_small_low  = df_fss[wd_small][0:thresholds[th_mid]]
    df_small_high = df_fss[wd_small][thresholds[th_mid+1]:9999]
    df_large_low  = df_fss[wd_large][0:thresholds[th_mid]]
    df_large_high = df_fss[wd_large][thresholds[th_mid+1]:9999]
    if validity_thresholds is not None:
        vt_low = validity_thresholds[0:th_mid]
        vt_high = validity_thresholds[th_mid:]
    return df_small_low, df_small_high, df_large_low, df_large_high, vt_low, vt_high


def fss_success_rate(df_fss, thresholds):
    fss_data = df_fss.values
    print(fss_data.shape)
    print(len(thresholds))
    print(thresholds)
    # fss_data = df_fss.to_numpy() only works from version 0.24
    n_entries = fss_data.shape[0]*fss_data.shape[1]
    fss_success_rate = 0.
    for ii, threshold in enumerate(thresholds):
        fss_success_rate += np.sum(np.where(fss_data[ii] > threshold, 1, 0))/float(n_entries)
    return fss_success_rate


def quadrant_success_rate(df_fss, fo_list, rr_max_obs=None, precip_threshold=None, window_size_threshold=None):
    df_sl, df_sh, df_ll, df_lh, vt_low, vt_high = get_quadrants(df_fss, validity_thresholds=fo_list, rr_max_obs=rr_max_obs)
    print(fo_list)
    print(vt_low, vt_high)
    sr_sl = fss_success_rate(df_sl, vt_low)
    sr_sh = fss_success_rate(df_sh, vt_high)
    sr_ll = fss_success_rate(df_ll, vt_low)
    sr_lh = fss_success_rate(df_lh, vt_high)
    return sr_sl, sr_sh, sr_ll, sr_lh


def rank_array(a,t):
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
    6. if N values are equal, the next N-1 tanks are skipped

    Ranks 3 and higher are valid ranks
    """
    # print("Threshold is {:7.5f} Array to rank:".format(t))
    # print(a)
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
                # deal with perfect ranks first (-> green)
                # print("a[{}] is {}".format(idx, a[idx]))
                if a[idx] == 1.:
                    ranks[idx] = 2.
                    jj += 1.
                    a[idx] = -97.
                else:
                    # increment to 3 for gold (best rank but not perfect)
                    # if no perfect score was fond before!
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
    # for ii, rank in enumerate(ranks):
        # print("{}: {} is ranked at {}".format(ii, b[ii], rank))
    return ranks
