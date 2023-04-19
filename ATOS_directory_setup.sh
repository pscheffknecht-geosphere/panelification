#!/bin/bash
# SETUP SCRIPT FOR PANELIFICATION ON ATOS
#
# create directories for data etc. on home and scratch and the respective symlinks
set -x
panelification_dir=$PWD
scratch_dir=$SCRATCH
# create directories for storage of scores, plots and logs
for dir in SCORES PLOTS LOG; do
  mkdir -p ${panelification_dir}/${dir}
done
# create directoris for temporal storage of model data, obs data, and temp data
# link them back to the current directory
for dir in MODEL DATA OBS TMP; do
  mkdir -p ${scratch_dir}/panelification/${dir}
  ln -sf ${scratch_dir}/panelification/${dir} ${panelification_dir}/${dir}
done 
# link folders from current directory to $SCRATCH/panelification
for dir in SCR LOG SCORES PLOTS DOCUMENTATION; do
  ln -sf ${panelification_dir}/${dir} ${scratch_dir}/panelification/${dir}
done

