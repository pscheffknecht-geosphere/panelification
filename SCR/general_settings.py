""" THIS FILE CONTAINS THE GENERAL SETTINGS OF THE VERIFICATION

Scientific choices which apply to all parameters. They work well for most
events, but every one of them changes the scores. Settings which depend on
the verified parameter (thresholds, units, colour maps, ...) are in
parameter_settings.py.

Window sizes are in grid points of the verification grid, which has a
spacing of 1 km (see regions.py), so they are also in km.

MODIFY AT YOUR OWN RISK!!!
"""

# RESAMPLING ONTO THE VERIFICATION SUBDOMAIN
# nearest neighbour search radius in m; subdomain points without a source
# point within this distance are missing (NaN). 25 km still covers source grids
# up to ~35 km spacing, but for high-resolution grids it fills a strip of up to
# 25 km outside the source domain with the values at its edge, which are then
# scored. Missing values inside a source grid (e.g. OPERA outside radar
# coverage) stay missing.
RESAMPLING_RADIUS = 25000.

# IMPLAUSIBLE VALUES
# resampled values above this are missing (NaN)
IMPLAUSIBLE_VALUE = 9999.
# with --fix_nans, resampled values above this are set to 0
FIX_NANS_IMPLAUSIBLE_VALUE = 2500.
# OPERA accumulations above this (mm) are missing (NaN)
OPERA_MAX_ACCUMULATION = 2000.

# FSS
# skill threshold f0: FSS values up to f0 count as no skill, values from f0
# to 1 are mapped to 0 ... 1 in the condensed FSS and the cwFSS, and the
# FSS rank plot only ranks forecasts above f0. Fixed instead of 0.5 + f_obs/2
# (Roberts & Lean 2008) on purpose: that threshold reaches 1 when the
# observation exceeds the threshold everywhere, so a single missed grid point
# makes the forecast unskillful, which happens on small domains. The FSS is
# used to compare and colour forecasts, so this is the accepted trade-off for
# being too lenient at low thresholds with widespread rain.
FSS_SKILL_THRESHOLD = 0.5
# FSS windows, unless --d_windows is set. Points outside the subdomain count
# as dry, so once a window is twice the subdomain size every window contains
# the whole subdomain: the FSS then only compares the total rain areas (a bias
# measure) and stays constant for all larger windows. Several subdomains in
# regions.py are much smaller than 200 km (e.g. 40 x 40 km, where 80 ... 200
# all give the same FSS), but these windows still count in the cwFSS.
DEFAULT_WINDOWS = [10, 20, 30, 40, 60, 80, 100, 120, 140, 160, 180, 200]

# cwFSS
# weight of the largest threshold relative to threshold 0, the weight is linear in between
CWFSS_THRESHOLD_MAX_WEIGHT = 2.
# weight of window 0 relative to the largest window, w_max * W / (w_max + (W - 1) * w) in between
CWFSS_WINDOW_MAX_WEIGHT = 2.

# RANKING ROBUSTNESS CHECK (--check_ranking)
# number of quasi-random (threshold, window) samples of the cwFSS
RANKING_CHECK_SAMPLES = 1250
# number of bootstrap draws from these samples
RANKING_CHECK_BOOTSTRAP = 10000
# seed of the bootstrap, so repeated runs give the same result. All forecasts
# use the same seed, so each draw resamples the same (threshold, window) pairs
# for every forecast and the ranks of a draw compare like with like
RANKING_CHECK_SEED = 0
# threshold range of the samples in percent of the observed maximum,
# the window range is that of the FSS windows
RANKING_CHECK_THRESHOLD_LIMITS = (0.1, 100.)

# d90
# percentile which defines the intense precipitation areas of forecast and
# observation (the 90 in d90), also used for the areas drawn with --draw_p90
D90_PERCENTILE = 90
# windows of the FSS between the non-overlapping parts of these areas
D90_WINDOWS = [3, 5, 7, 11, 21, 31, 41, 51, 61, 81, 101, 121, 141, 181, 251, 351, 501, 701]
# the displacement is half the window at which this FSS is reached
D90_FSS = 0.5
# the FSS has to increase with the window size, decreases up to this are numerical noise
D90_MONOTONICITY_TOLERANCE = 0.01

# SCORE FILES
# percentiles of the forecast and observation fields, 0 ... 100 with --save_percentiles
STATISTICS_PERCENTILES = [50, 75, 90, 95, 99]
