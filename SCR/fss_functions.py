# from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from scipy import signal


def fourier_filter(field, n):
    return signal.fftconvolve(field, np.ones([n,n]), mode='same')
        

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
    fhat_avg = np.nanmean(fhat)
    ohat_avg = np.nanmean(ohat)
    if fhat_avg == ohat_avg:
        ovest = 0. # should almost never happen unless domain ist 100% or 0% covered
    else:
        ovest = 1. if fhat_avg > ohat_avg else -1
    return num, denom, 1.-num/denom, ovest


def fss_frame(fcst, obs, windows, levels, percentiles=False):
    """
    Compute the fraction skill score data-frame.
    :paramfcst: nd-array, forecast field.
    :paramobs: nd-array, observation field.
    :param window: list, window sizes.
    :param levels: list, threshold levels.
    return: list, dataframes of the FSS: numerator, denominator and score.
    """
    num_data_fft, den_data_fft, fss_data_fft, overestimated = [], [], [], []
    
    for level in levels:
        _data_fft = [fourier_fss(fcst, obs, level, w, percentiles) for w in windows]
        num_data_fft.append([x[0] for x in _data_fft])
        den_data_fft.append([x[1] for x in _data_fft])
        fss_data_fft.append([x[2] for x in _data_fft])
        overestimated.append([x[3] for x in _data_fft])
    return (pd.DataFrame(num_data_fft, index=levels, columns=windows),
           pd.DataFrame(den_data_fft, index=levels, columns=windows),
           pd.DataFrame(fss_data_fft, index=levels, columns=windows),
           pd.DataFrame(overestimated, index=levels, columns=windows))
           

def fss_strip(fcst, obs, windows, levels, percentiles=False):
    """
    Grab the essentials and drop the rest to save some memory
    """
    fss_stripped=fss_frame(fcst, obs, windows, levels, percentiles=percentiles)
    return fss_stripped[2] # only scores!!
