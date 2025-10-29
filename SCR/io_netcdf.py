import 
import netCDF4 as nc


def read_data_netcdf(nc_file_path, parameter, valid_time, **kwargs):
    """
    Reads data from a NetCDF file, fixed to work with daily timesteps and
    robustly handle common coordinate variable names.
    """
    parameter = "precipitation"
    get_lonlat_data = kwargs.get("get_lonlat_data", False)
    with nc.Dataset(nc_file_path, 'r') as ds:
        if parameter not in ds.variables:
            logger.error(f"Parameter '{parameter}' not found in file: {nc_file_path}")
            return None
        var = ds.variables[parameter]
        time_dim_name = [d for d in var.dimensions if d.startswith('time')][0]
        time_var = ds.variables[time_dim_name]
        file_times = nc.num2date(time_var[:], units=time_var.units)
        time_idx = (np.abs(file_times - valid_time)).argmin()
        if np.abs(file_times[time_idx] - valid_time) > dt.timedelta(minutes=30):
            logger.error(f"Requested valid time {valid_time} not found in file {nc_file_path}")
            return None
        data = var[time_idx, ...]
        logger.info(f"The time index is {time_idx} and valid time is {valid_time}")
        if get_lonlat_data:
            lat_names = ['lat', 'latitude', 'lats', 'Latitude']
            lon_names = ['lon', 'longitude', 'lons', 'Longitude']
            lat_var_name = None
            for name in lat_names:
                if name in ds.variables:
                    lat_var_name = name
                    break
            lon_var_name = None
            for name in lon_names:
                if name in ds.variables:
                    lon_var_name = name
                    break
            if not lat_var_name or not lon_var_name:
                logger.error(f"Could not find latitude or longitude variables in {nc_file_path}")
                return None, None, None
            lat = ds.variables[lat_var_name][:]
            lon = ds.variables[lon_var_name][:]
            if lat.ndim == 1 and lon.ndim == 1:
                lon_2d, lat_2d = np.meshgrid(lon, lat)
            else:
                lon_2d, lat_2d = lon, lat

    # Extract init_time from the first file path (assuming consistent naming)
    # FC_samos_prec_YYYYmmddHH_ltHHHh.nc
    if not sorted_file_paths:
        logger.warning("No files to read.")
        return [], []

    first_filename = Path(sorted_file_paths[0]).name
    try:
        init_time_str = first_filename.split('_')[3]
        init_time = dt.datetime.strptime(init_time_str, '%Y%m%d%H')
    except IndexError:
        logger.error(f"Could not extract initialization time from filename: {first_filename}")
        raise ValueError("Invalid filename format for extracting initialization time.")
    except ValueError:
        logger.error(f"Could not parse initialization time '{init_time_str}' from filename: {first_filename}")
        raise ValueError("Invalid initialization time format in filename.")


    for i, filepath in enumerate(sorted_file_paths):
        try:
            filename_basename = Path(filepath).name
            logger.info(f"  Reading file ({i+1}/{len(sorted_file_paths)}): {filename_basename}")
            ds = xr.open_dataset(filepath, decode_cf=False)
            
            # Extract lead time from filename for valid_time calculation
            match = re.search(r"_lt(\d{3})h\.nc$", filename_basename)
            if match:
                lead = int(match.group(1))
                valid_time = init_time + dt.timedelta(hours=lead)
                NWP_list_dates.append(valid_time)
            else:
                logger.warning(f"Could not extract lead time from {filename_basename}. Valid time might be incorrect.")
                # Fallback: try to get time from dataset or use a dummy.
                # For this specific case, the watchdog ensures 12 files so we expect a match.
                NWP_list_dates.append(init_time + dt.timedelta(hours=i+1)) # Best guess

            RR_list.append(ds['prec'].values[0])  # Assuming 'prec' is the variable and needs first slice
            ds.close()
        except FileNotFoundError:
            logger.error(f"File not found: {filepath}.")
            raise
        except KeyError:
            logger.error(f"Variable 'prec' not found in {filepath}. Check NetCDF file structure.")
            raise
        except Exception as e:
            logger.error(f"Error opening or reading {filepath}: {e}", exc_info=True)
            raise
    
    logger.info(f"Successfully read {len(RR_list)} precipitation arrays.")
    return RR_list, NWP_list_dates