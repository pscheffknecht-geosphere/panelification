#!/bin/bash
day=20251125
for hour in $(seq -w 11 02 15); do
   python main.py --loglevel debug --parameter cma --verif_dataset SAF_cma --forcedraw --region Dynamic -s ${day}${hour} -d 1 -l $hour $hour --custom_experiments arome_hun_test --custom_experiment_file custom_experiments_test
done



