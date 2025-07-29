#!/bin/bash
. ~/.bashrc
source /ment_arch/pscheff/miniconda3-py3.8/bin/activate panelification_web
set -x
if [ $# == 0 ]; then
  rundate=$(date "+%Y%m%d%H" --date "now -13 hours") # 15 UTC of previous day
  rundate2=$(date "+%Y%m%d%H" --date "now -16 hours") # 12 UTC of previous day
  rundate3=$(date "+%Y%m%d%H" --date "now -28 hours") # 00 UTC of previous day
else
  rundate=$1
fi
# 2021-06-28 replaced cosmo1 with cosmo1e and cosmod2 with icond2
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n forecast_conv  --region Austria -s ${rundate}  -d 3  -l 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15 12 15  9 12 --custom_experiment_file custom_experiments_geosphere --custom_experiments arome aromeesuite claef-control claef-mean claef-median claef1k-control claef1k-enVar claef1k-mean claef1k-median cosmo1e icond2 ecmwf icon-eu samos --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted --logfile ../LOG/forecast_${rundate}.log
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n forecast_12-24 --region Austria -s ${rundate2} -d 12 -l  3 12  3 12  3 12  3 12  3 12  3 12  3 12  3 12  3 12  3 12  3 12 12 24  6 12  6 12 --custom_experiment_file custom_experiments_geosphere --custom_experiments arome aromeesuite claef-control claef-mean claef-median claef1k-control claef1k-enVar claef1k-mean claef1k-median cosmo1e icond2 ecmwf icon-eu samos --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted --logfile ../LOG/forecast_${rundate}.log
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n forecast_00_12 --region Austria -s ${rundate3} -d 12 -l 15 24 15 24 15 24 15 24 15 24 15 24 15 24 15 24 15 24 15 24 15 24 15 24 18 24 18 24 --custom_experiment_file custom_experiments_geosphere --custom_experiments arome aromeesuite claef-control claef-mean claef-median claef1k-control claef1k-enVar claef1k-mean claef1k-median cosmo1e icond2 ecmwf icon-eu samos --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted --logfile ../LOG/forecast_${rundate}.log
