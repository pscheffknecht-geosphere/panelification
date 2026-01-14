#!/bin/bash
set -x
day=20251224
for hour in $(seq -w 11 01 12); do
  python main.py --loglevel debug --parameter cma --verif_dataset SAF_cma --forcedraw --forcescore --region Dynamic -s ${day}${hour} -d 3 -l $hour $hour --custom_experiments arome_hun_test ecmwf_hun_test --custom_experiment_file custom_experiments_test --save_full_fss
  done
