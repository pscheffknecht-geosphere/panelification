#!/bin/bash
. ~/.bashrc
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
# # 2021-06-28
# # REPLACED cosmo1e with cosmo1ee and icond2 with icond2
# /ment_arch/pscheff/miniconda3-py3.8/envs/panelification_deode/bin/python main.py -s ${rundate1} -d 1 -l 6 15 6 15  6 15 6 15 2 6 0 3 6 12 6 12  --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'aromeruc' 'cosmo1e' 'icond2' --draw > ../LOG/nowcast_${rundate1}.log
# /ment_arch/pscheff/miniconda3-py3.8/envs/panelification_deode/bin/python main.py -s ${rundate2} -d 1 -l 7 16 7 16  7 16 7 16 3 7 1 4 7 13 7 13  --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'aromeruc' 'cosmo1e' 'icond2' --draw > ../LOG/nowcast_${rundate2}.log
# /ment_arch/pscheff/miniconda3-py3.8/envs/panelification_deode/bin/python main.py -s ${rundate3} -d 1 -l 8 17 8 17  8 17 8 17 4 8 2 5 8 14 8 14  --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'aromeruc' 'cosmo1e' 'icond2' --draw > ../LOG/nowcast_${rundate3}.log
# /ment_arch/pscheff/miniconda3-py3.8/envs/panelification_deode/bin/python main.py -s ${rundate4} -d 1 -l 9 18 9 18  9 18 9 18 5 9 3 6 9 15 9 15  --custom_experiments 'arome' 'aromeesuite' 'claef-control' 'claef-mean' 'claef-median' 'aromeruc' 'cosmo1e' 'icond2' --draw > ../LOG/nowcast_${rundate4}.log
# # UPDATE INTRANET GRAPHICS AFTER LAST PANELS FOR THE DAY ARE DONE
# /ment_arch/pscheff/miniconda3-py3.8/envs/panelification_deode/bin/python main.py --intranet_update
