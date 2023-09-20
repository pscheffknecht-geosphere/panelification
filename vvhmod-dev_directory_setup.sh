#!/bin/bash
# SETUP SCRIPT FOR PANELIFICATION ON ATOS
#
# create directories for data etc. on home and scratch and the respective symlinks
set -x
panelification_dir=$PWD
work_dir=/ment_arch2/$(whoami)
# create directories for storage of scores, plots and logs
for dir in SCORES PLOTS LOG; do
  mkdir -p ${panelification_dir}/${dir}
done
# create directoris for temporal storage of model data, obs data, and temp data
# link them back to the current directory
for dir in MODEL DATA TMP; do
  mkdir -p ${work_dir}/panelification/${dir}
  ln -sf ${work_dir}/panelification/${dir} ${panelification_dir}/${dir}
done 
mkdir -p ${work_dir}/panelification/OBS
ln -sf ${work_dir}/panelification/OBS ${panelification_dir}/OBS
# link folders from current directory to $WORKDIR/panelification
for dir in SCR LOG SCORES PLOTS DOCUMENTATION; do
  ln -sf ${panelification_dir}/${dir} ${work_dir}/panelification/${dir}
done

