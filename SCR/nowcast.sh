#!/bin/bash
. ~/.bashrc
source /ment_arch/pscheff/miniconda3-py3.8/bin/activate panelification_web
set -x
if [ $# == 0 ]; then
  rundate1=$(date "+%Y%m%d%H" --date "now -16 hours")
  rundate2=$(date "+%Y%m%d%H" --date "now -15 hours")
  rundate3=$(date "+%Y%m%d%H" --date "now -14 hours")
  rundate4=$(date "+%Y%m%d%H" --date "now -13 hours")
elif [ $# == 2 ]; then
  rundate1=$1$2
  rundate2=$(date "+%Y%m%d%H" --date "$1 $2 +1 hours")
  rundate3=$(date "+%Y%m%d%H" --date "$1 $2 +2 hours")
  rundate4=$(date "+%Y%m%d%H" --date "$1 $2 +3 hours")
else
  echo "nowcast.sh needs either no arguments or YYYYMMDD HH"
    exit 1 
  fi
  # 
# 2021-06-28
# REPLACED cosmo1e with cosmo1ee and icond2 with icond2
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n nowcasting --region Austria -s ${rundate1} -d 1 -l 6 15 6 15  6 15 6 15 6 15 6 15 6 15 6 15 0 3 6 12 6 12 3 9  --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'claef1k-control' 'claef1k-mean' 'claef1k-median' 'aromeruc' 'cosmo1e' 'icond2' 'samos' --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted 
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n nowcasting --region Austria -s ${rundate2} -d 1 -l 7 16 7 16  7 16 7 16 7 16 7 16 7 16 7 16 1 4 7 13 7 13 4 10 --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'claef1k-control' 'claef1k-mean' 'claef1k-median' 'aromeruc' 'cosmo1e' 'icond2' 'samos' --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted  
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n nowcasting --region Austria -s ${rundate3} -d 1 -l 8 17 8 17  8 17 8 17 8 17 8 17 8 17 8 17 2 5 8 14 8 14 5 11 --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'claef1k-control' 'claef1k-mean' 'claef1k-median' 'aromeruc' 'cosmo1e' 'icond2' 'samos' --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted  
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n nowcasting --region Austria -s ${rundate4} -d 1 -l 9 18 9 18  9 18 9 18 9 18 9 18 9 18 9 18 3 6 9 15 9 15 6 12 --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'claef1k-control' 'claef1k-mean' 'claef1k-median' 'aromeruc' 'cosmo1e' 'icond2' 'samos' --draw --fix_nans --rank_score_time_series bias mae corr fss_condensed_weighted  
# UPDATE INTRANET GRAPHICS AFTER LAST PANELS FOR THE DAY ARE DONE
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py --intranet_update --logfile ../LOG/send2intranet.log
