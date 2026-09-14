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

# Output

For every verification run and subdomain the scores are written to one NetCDF file:

`SCORES/{name}{parameter}_scores_{YYYYMMDD_HH}UTC_{DD}h_acc_{region}_{subdomain}.nc`

The file contains
- run metadata as global attributes: parameter and its units, verification dataset, region and subdomain, accumulation period, FSS settings, code version and command line
- scalar scores, ranks and statistics of the forecast fields on the dimensions `(valid_time, conf, subdomain, lead_hours)`, e.g. `bias`, `mae`, `rms`, `corr`, `d90`, `fss_condensed_weighted_rect`, `rank_mae`, `forecast_max`, `forecast_percentile`
- statistics of the observed field, `obs_max`, `obs_mean` and `obs_percentile`, on `(valid_time, subdomain)`
- the full FSS arrays `fss`, `fss_num` and `fss_den` on `(valid_time, conf, subdomain, lead_hours, threshold, window)`, and `fssp`, `fssp_num` and `fssp_den` for the percentile thresholds on `(..., pct_threshold, window)`, unless `--save_full_fss False` is set

`valid_time` is the start of the accumulation window and `lead_hours` the lead time at that point, so the forecast init time is `valid_time - lead_hours`. Combinations of `conf` and `lead_hours` without a forecast are NaN. Windows are given in grid points of the ~1 km verification grid, and `fss = 1 - fss_num / fss_den`.

Combining and aggregating score files is left to downstream tools. The old CSV score files and FSS pickles can still be written with `--legacy_output`.

Existing legacy output (score CSV files and FSS pickles) can be converted to NetCDF score files with the standalone script `convert_legacy_output.py`. It uses no other panelification module and keeps its own copy of the score file layout, which is not updated with `io_scores.py`. Parameter and region are not stored in the legacy files and have to be given:

`python convert_legacy_output.py --region Austria --name INCAOptAndSAMOS --scores_dir /path/to/SCORES --data_dir /path/to/DATA`

Legacy files are not changed, existing NetCDF files are only replaced with `--overwrite`, and `--dry_run` lists the conversions without writing anything.
