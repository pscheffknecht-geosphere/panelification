# Installation

Clone or fork Panelification, depending on whether you want to make you own changes, pick the one you prefer, second if you forked it to your own account:

```
git clone git@github.com:pscheffknecht-geosphere/panelification.git
git clone git@github.com:{YOUR USER NAME}/panelification.git
```

Set up the diretcory structure, it is recommended to install the code in /texttt/home or /texttt/perm, then run ATOS directory setup.sh. This will set up the `MODEL`, `DATA`, and `TMP` directories on `/scratch`, `OBS` on `/perm`, and the other directories within the folder where the reposotory was cloned. That way, model and temporary data will be stored on non-permanent file systems, whereas results and observations will be kept indefinitely. Please check the sizes of these folders occasionally, depending on the use these can still get rather large.

Load the anaconda module: module load conda and set up the conda environment using the `panelification_deode.yml`.
NOTE: Users have reported problems in getting the environment to build from the `.yml` file, I tested the following command to create a working environment:
`conda create --name panelification matplotlib jupyter pandas scipy xarray netCDF4 pyresample sqlite3 pymssql`

# Usage
`python main.py -s YYYYMMDDHH -d H -l H (H) --case [case as in DCMDB] --experiments [experiment names as in DCMDB]`

Documentation will be added shortly.
