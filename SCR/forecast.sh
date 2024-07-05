#!/bin/bash
. ~/.bashrc
source /ment_arch/pscheff/miniconda3-py3.8/bin/activate panelification_web
set -x
if [ $# == 0 ]; then
  rundate=$(date "+%Y%m%d%H" --date "now -13 hours")
else
  rundate=$1
fi
# 2021-06-28 replaced cosmo1 with cosmo1e and cosmod2 with icond2
/ment_arch/pscheff/miniconda3-py3.8/envs/panelification_web/bin/python main.py -n forecast --region Austria -s ${rundate} -d 3 -l 12 15 --custom_experiments arome aromeesuite claef-control claef-mean claef-median claef1k-control claef1k-mean claef1k-median cosmo1e icond2 ecmwf icon-eu --draw --fix_nans --logfile ../LOG/forecast_${rundate}.log 
