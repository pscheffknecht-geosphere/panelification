# from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from scipy import signal

def pause():
    programPause = raw_input("Press the <ENTER> key to continue...")

def compute_integral_table(field):
    return field.cumsum(1).cumsum(0)

def fourier_filter(field, n):
    return signal.fftconvolve(field, np.ones([n,n]), mode='same')
        
def integral_filter(field, n, table=None):
#    """
#    Fast summed area table version of the sliding accumulator.
#    :param field: nd-array of binary hits/misses
#    :param n: window size.
#    """
    w = n // 2
    if w < 1.:
       return field
    if table is None:
       table = compute_integral_table(field)
       
    r, c = np.mgrid[0:field.shape[0], 0:field.shape[1]]
    r=r.astype(np.int)
    c=c.astype(np.int)
    w=np.int(w)
    
    r0, c0 = (np.clip(r - w, 0, field.shape[0] -1),
      np.clip(c - w, 0, field.shape[1] -1))
    r1, c1 = (np.clip(r + w, 0, field.shape[0] -1),
      np.clip(c + w, 0, field.shape[1] -1))
        
    integral_table = np.zeros(field.shape).astype(np.int64)
    integral_table += np.take(table, np.ravel_multi_index((r1,c1), field.shape))
    integral_table += np.take(table, np.ravel_multi_index((r0,c0), field.shape))
    integral_table -= np.take(table, np.ravel_multi_index((r0,c1), field.shape))
    integral_table -= np.take(table, np.ravel_multi_index((r1,c0), field.shape))
    return integral_table

def fourier_fss(fcst, obs, threshold, window, percentiles):
    """
    Compute the fractional skill score using convolution
    :paramfcst: nd-array, forecast field
    :paramobs: nd-array, observation field.
    :param window: integer, window size.
    :param percentiles: threshold list is treated as percentiles [0 ... 100]
    :return: tuple of FSS numerator, denominator and score.
    """
    if percentiles:
      fhat = fourier_filter(fcst > np.percentile(fcst, threshold), window)
      ohat = fourier_filter(obs > np.percentile(obs, threshold), window)
    else:
      fhat = fourier_filter(fcst > threshold, window)
      ohat = fourier_filter(obs > threshold, window)
    num = np.nanmean(np.power(fhat - ohat, 2))
    denom = np.nanmean(np.power(fhat,2) + np.power(ohat,2))
    return num, denom, 1.-num/denom

def fss(fcst, obs, threshold, window, fcst_cache=None, obs_cache=None):
    """
    Compute the fraction skill score using summed area tables
    :paramfcst: nd-array, forecast field.
    :paramobs: nd-array, observation field.
    :param window: integer, window size.
    :return: tuple of FSS numerator, denominator and score.
    """
    fhat = integral_filter(fcst > threshold, window, fcst_cache)
    ohat = integral_filter(obs > threshold, window, obs_cache)
    num = np.nanmean(np.power(fhat ^ ohat, 2))
    denom = np.nanmean(np.power(fhat, 2) + np.power(ohat, 2))
    return num, denom, 1.-num/denom

def fss_frame(fcst, obs, windows, levels, percentiles=False):
    """
    Compute the fraction skill score data-frame.
    :paramfcst: nd-array, forecast field.
    :paramobs: nd-array, observation field.
    :param window: list, window sizes.
    :param levels: list, threshold levels.
    return: list, dataframes of the FSS: numerator, denominator and score.
    """
    #num_data, den_data, fss_data = [], [], []
    num_data_fft, den_data_fft, fss_data_fft = [], [], []
    
    for level in levels:
        ftable = compute_integral_table(fcst > level)
        otable = compute_integral_table (obs > level)
                
        _data_fft = [fourier_fss(fcst, obs, level, w, percentiles) for w in windows]

        num_data_fft.append([x[0] for x in _data_fft])
        den_data_fft.append([x[1] for x in _data_fft])
        fss_data_fft.append([x[2] for x in _data_fft])
        
    # return  num_data, den_data, fss_data
        
    return (pd.DataFrame(num_data_fft, index=levels, columns=windows),
           pd.DataFrame(den_data_fft, index=levels, columns=windows),
           pd.DataFrame(fss_data_fft, index=levels, columns=windows))

# def fss_frame_parallel(fcst, obs, windows, levels, percentiles=False):
#     """
#     Compute the fraction skill score data-frame.
#     :paramfcst: nd-array, forecast field.
#     :paramobs: nd-array, observation field.
#     :param window: list, window sizes.
#     :param levels: list, threshold levels.
#     return: list, dataframes of the FSS: numerator, denominator and score.
#     """
#     #num_data, den_data, fss_data = [], [], []
#     num_data_fft, den_data_fft, fss_data_fft = [], [], []
    
#     for level in levels:
#         ftable = compute_integral_table(fcst > level)
#         otable = compute_integral_table (obs > level)
                
#         #_data_fft = [fourier_fss(fcst, obs, level, w) for w in windows]
#         _data_fft = Parallel(n_jobs=4)(delayed(fourier_fss)(fcst, obs, level, w, percentiles) for w in windows)

#         num_data_fft.append([x[0] for x in _data_fft])
#         den_data_fft.append([x[1] for x in _data_fft])
#         fss_data_fft.append([x[2] for x in _data_fft])
        
#     # return  num_data, den_data, fss_data
        
#     return (pd.DataFrame(num_data_fft, index=levels, columns=windows),
#            pd.DataFrame(den_data_fft, index=levels, columns=windows),
#            pd.DataFrame(fss_data_fft, index=levels, columns=windows))
def fss_strip(fcst, obs, windows, levels, percentiles=False):
# def fss_strip(fcst, obs, windows, levels,lparallel=False, percentiles=False):
    """
    Grab the essentials and drop the rest to save some memory
    """
    # if lparallel:
    #     fss_stripped=fss_frame_parallel(fcst, obs, windows, levels, percentiles=percentiles)
    # else:
    fss_stripped=fss_frame(fcst, obs, windows, levels, percentiles=percentiles)
    return fss_stripped[2] # only scores!!

