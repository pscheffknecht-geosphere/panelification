# from joblib import Parallel, delayed
import numpy as np
import pandas as pd
from scipy import signal


def fourier_filter(field, window, mode):
    return signal.fftconvolve(field, np.ones(window), mode=mode)
        

def fourier_fss(fcst, obs, threshold, window, percentiles, mode):
    """
    Compute the fractional skill score using convolution
    :paramfcst: nd-array, forecast field
    :paramobs: nd-array, observation field.
    :param window: integer, window size.
    :param percentiles: threshold list is treated as percentiles [0 ... 100]
    :return: tuple of FSS numerator, denominator and score.
    """
    ny, nx = fcst.shape
    if mode=='valid' and any(np.array(window) > np.array(fcst.shape)):
      return np.nan, np.nan, np.nan, np.nan
    if percentiles:
      fhat = fourier_filter(fcst > np.percentile(fcst, threshold), window, mode)
      ohat = fourier_filter(obs > np.percentile(obs, threshold), window, mode)
    else:
      fhat = fourier_filter(fcst > threshold, window, mode)
      ohat = fourier_filter(obs > threshold, window, mode)
    num = np.nanmean(np.power(fhat - ohat, 2))
    denom = np.nanmean(np.power(fhat,2) + np.power(ohat,2))
    fhat_avg = np.nanmean(fhat)
    ohat_avg = np.nanmean(ohat)
    if fhat_avg == ohat_avg:
        ovest = 0. # should almost never happen unless domain ist 100% or 0% covered
    else:
        ovest = 1. if fhat_avg > ohat_avg else -1
    return num, denom, 1.-num/denom, ovest


def fss_frame(fcst, obs, windows, levels, percentiles=False, mode='same'):
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
        _data_fft = [fourier_fss(fcst, obs, level, w, percentiles, mode) for w in windows]
        num_data_fft.append([x[0] for x in _data_fft])
        den_data_fft.append([x[1] for x in _data_fft])
        fss_data_fft.append([x[2] for x in _data_fft])
        overestimated.append([x[3] for x in _data_fft])
    return (pd.DataFrame(num_data_fft,  index=levels), #, columns=["{:d}x{:d}".format([*window for window in windows]),
            pd.DataFrame(den_data_fft,  index=levels), #, columns=windows),
            pd.DataFrame(fss_data_fft,  index=levels), #, columns=windows),
            pd.DataFrame(overestimated, index=levels)) #, columns=windows))
           

# class FSS:
#     def __init__(self, obs, mod, windows, thresholds,
#                  percentiles=False, mode='same'):
#         if not obs.shape == mod.shape:
#             logging.critical("Cannot calculate FSS if model and obs aren't on the same grid!")
#             logging.critical("OBS: {:d}x{:d}, MOD: {:d}x{:d}".format(*obs.shape, *mod.shape))
#             exit()
#         self.observations = obs
#         self.forecast = mod
#         self.windows = windows
#         self.thresholds = thresholds
#         self.mode = mode                # same, valid, valid_adaptive 
#         self.percentiles = percentiles  # True, False (are we looking at percentiles?)
#         # calcualte scores
#         self.numerator, self.denominator, self.fss, self.overestimated = fss_frame(
#             self.forecast, self.observations, self.windows, self.thresholds, 
#             percentiles=self.percentiles, mode=self.mode)
# 
# 
#     def set_windows(self, windows):
#         self.windows = windows
# 
# 
#     def set_threshodls(self, thresholds):
#         self.thresholds = thresholds
# 
# 
#     def recalculate_scores():
#         self.numerator, self.denominator, self.fss, self.overestimated = fss_frame(
#             self.forecast, self.observations, self.windows, self.thresholds, 
#             percentiles=self.percentiles, mode=self.mode)

