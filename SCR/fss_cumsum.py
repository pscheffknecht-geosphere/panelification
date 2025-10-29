import numpy as np
import time
from joblib import Parallel, delayed
from scipy.stats import bootstrap

def compute_integral_table(field):
    return field.cumsum(1).cumsum(0)

def integral_filter(field, n):
    """
    Fast summed area table version of the sliding accumulator.
    :param field: nd-array of binary hits/misses.
    :param n: window size.
    """
    w = n // 2
    if w < 1.:
        return field
    
    r, c = np.mgrid[0:field.shape[0], 0:field.shape[1]]

    r = r.astype(int)
    c = c.astype(int)
    w = int(w)

    r0, c0 = (np.clip(r - w, 0, field.shape[0] - 1),
              np.clip(c - w, 0, field.shape[1] - 1))
    r1, c1 = (np.clip(r + w, 0, field.shape[0] - 1),
              np.clip(c + w, 0, field.shape[1] - 1))

    integral_table = np.zeros(field.shape).astype(np.int64)
    integral_table += np.take(field, np.ravel_multi_index((r1, c1), field.shape))
    integral_table += np.take(field, np.ravel_multi_index((r0, c0), field.shape))
    integral_table -= np.take(field, np.ravel_multi_index((r0, c1), field.shape))
    integral_table -= np.take(field, np.ravel_multi_index((r1, c0), field.shape))
    return integral_table


def fss(fcst, obs, t1, t2, window, fcst_cache, obs_cache, threshold_mode="over"):
    """
    Compute the fraction skill score using summed area tables.
    :param fcst: nd-array, forecast field.
    :param obs: nd-array, observation field.
    :param window: integer, window size.
    :return: tuple of FSS numerator, denominator and score.
    """
    if threshold_mode == "over":
        fhat = integral_filter(fcst_cache, window)
        ohat = integral_filter(obs_cache, window)
    elif threshold_mode == "under":
        fhat = integral_filter(fcst_cache, window)
        ohat = integral_filter(obs_cache, window)
    elif threshold_mode == "between":
        fhat = integral_filter(fcst_cache, window)
        ohat = integral_filter(obs_cache, window)
    elif threshold_mode == "tolerance":
        fhat = integral_filter(fcst_cache, window)
        ohat = integral_filter(obs_cache, window)

    num = np.nanmean(np.power(fhat - ohat, 2))
    denom = np.nanmean(np.power(fhat, 2) + np.power(ohat, 2))
    with np.errstate(divide='ignore', invalid='ignore'):
        ret = num, denom, 1. - num / denom
    return ret


def fss_threshold(fcst, obs, t1, t2, windows, threshold_mode="over", tolerance=0.1):
    num_t = np.zeros(windows.shape)
    den_t = np.zeros(windows.shape)
    fss_t = np.zeros(windows.shape)
    if threshold_mode == "over":
        obs_bin = compute_integral_table((obs > t1).astype(int))
        mod_bin = compute_integral_table((fcst > t1).astype(int))
    elif threshold_mode == "under":
        obs_bin = compute_integral_table((obs <= t1).astype(int))
        mod_bin = compute_integral_table((fcst <= t1).astype(int))
    elif threshold_mode == "between":
        obs_bin = compute_integral_table(((obs > t1) & (obs <= t2)).astype(int))
        mod_bin = compute_integral_table(((fcst > t1) & (fcst <= t2)).astype(int))
    elif threshold_mode == "tolerance":
        obs_bin = compute_integral_table(((obs > (1.-tolerance) * t1) & (obs <= (1.+tolerance)*t1)).astype(int))
        mod_bin = compute_integral_table(((fcst > (1.-tolerance) * t1) & (fcst <= (1.+tolerance)*t1)).astype(int))
    for jj, window in enumerate(windows):
        num_t[jj], den_t[jj], fss_t[jj] = fss(fcst, obs, t1, t2, window, 
                                                fcst_cache=mod_bin, obs_cache=obs_bin, threshold_mode=threshold_mode)
    return num_t, den_t, fss_t
    
def fss_cumsum_parallel(fcst, obs, thresholds, windows, threshold_mode="over", tolerance=0.1):
    if not isinstance(thresholds, np.ndarray):
        thresholds = np.array(thresholds)
    if not isinstance(windows, np.ndarray):
        windows = np.array(windows)
    ret = None
    if threshold_mode == "between":
        thresholds = np.insert(thresholds, 0, -1.) # insert -1 to retain zero values as OK
        ret = Parallel(n_jobs=16)(delayed(fss_threshold)(
            fcst, obs, thresholds[ii], thresholds[ii+1], windows, threshold_mode=threshold_mode) for ii in range(thresholds.size-1))
    elif threshold_mode == "over" or threshold_mode == "under" or threshold_mode == "tolerance":
        ret = Parallel(n_jobs=16)(delayed(fss_threshold)(
            fcst, obs, t, None, windows, threshold_mode=threshold_mode, tolerance=tolerance) for t in thresholds)
    ret_arr = np.swapaxes(np.array(ret), 0, 1)
    return ret_arr

### Randomized thresholds and windows
# pseudo-random 2D vlaues with good coverage and non-fixed smaple count
def R2(N):
    g = 1.32471795724474602596
    a1 = 1.0 / g
    a2 = 1.0 / (g * g)
    x = (0.5 + a1 * N) %1 
    y = (0.5 + a2 * N) %1 
    return x, y

class CWFSS:
    def __init__(self, fcst, obs, nsamples=500, threshold_limits=(0.1, 100.), window_limits=(1, 601),
                threshold_max_weight=2., window_max_weight=2., threshold_limiting="relative"):
        self.wmin = int(window_limits[0])
        self.wmax = int(window_limits[1])
        #print(f"Using window sizes within [{self.wmin:d}, {self.wmax:d}]")
        if threshold_limiting == "relative":
            self.tmin = threshold_limits[0] * obs.max() / 100.
            self.tmax = threshold_limits[1] * obs.max() / 100.
            #print(f"Using relative thresholds [{self.tmin:.2f}, {self.tmax:.2f}]")
        elif threshold_limiting == "absolute":
            self.tmin = threshold_limits[0]
            self.tmax = threshold_limits[1]
            #print(f"Using absolute thresholds [{self.tmin:.2f}, {self.tmax:.2f}]")
        elif threshold_limiting == "percentiles":
            self.tmin = np.percentile(obs, threshold_limits[0])
            self.tmax = np.percentile(obs, threshold_limits[1])
        self.nsamples = nsamples
        self.denominators = np.zeros(nsamples)
        self.numerators = np.zeros(nsamples)
        self.values = np.zeros(nsamples)
        self.windows = np.zeros(nsamples) 
        self.thresholds = np.zeros(nsamples)
        self.__calc__(fcst, obs)
        self.__calc_cwfss()

    def __calc__(self, fcst, obs):
        for N in range(self.nsamples):
            x, y = R2(N)
            t = self.tmin + y * (self.tmax - self.tmin)
            w = int(self.wmin + x * (self.wmax - self.wmin))
            # print(x, y, t, w)
            self.windows[N] = w
            self.thresholds[N] = t
            obs_bin = compute_integral_table((obs > t).astype(int))
            mod_bin = compute_integral_table((fcst > t).astype(int))
            ohat = integral_filter(obs_bin, w)
            fhat = integral_filter(mod_bin, w)
            self.numerators[N] = np.nanmean(np.power(fhat - ohat, 2))
            self.denominators[N] = np.nanmean(np.power(fhat, 2) + np.power(ohat, 2))
            self.values[N] = 1. - self.numerators[N] / self.denominators[N]

    def __calc_cwfss(self):
        t_factor = (self.tmax + self.thresholds) / self.tmax
        w_factor = 2. * self.wmax / (self.wmax + self.windows)
        weighted_fss = (2. * (self.values - 0.5)).clip(0., 1.) * t_factor * w_factor
        weighted_fss_max = t_factor * w_factor
        self.cwfss = np.nanmean(weighted_fss) / np.nanmean(weighted_fss_max)

    def bootstrap(self, N=500):
        self.bootstrap_info = np.zeros(N)
        t_factor = (self.tmax + self.thresholds) / self.tmax
        w_factor = 2. * self.wmax / (self.wmax + self.windows)
        weighted_fss = (2. * (self.values - 0.5)).clip(0., 1.) * t_factor * w_factor
        weighted_fss_max = t_factor * w_factor
        for ii in range(N):
            idx = (self.nsamples * np.random.rand(self.nsamples)).astype(int)
            self.bootstrap_info[ii] = np.nanmean(weighted_fss[idx]) / np.nanmean(weighted_fss_max[idx])
        
