import numpy as np
import netCDF4 as nc
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def save_fss_to_netcdf(output_file, sim_data, start_date, end_date, subdomain, 
                       windows, thresholds, fss_thresholds, model_conf, model_init, 
                       accumulation_duration):
    """Save FSS data to a netCDF file with comprehensive metadata
    
    Args:
        output_file: Path to the output netCDF file
        sim_data: Dictionary containing FSS data (fss, fssp, fss_num, fssp_num, fss_den, fssp_den)
        start_date: Start date of accumulation period
        end_date: End date of accumulation period
        subdomain: Name of the verification subdomain
        windows: Array of window sizes used in FSS calculation
        thresholds: Array of precipitation thresholds
        fss_thresholds: Thresholds applied for FSS calculation
        model_conf: Model configuration
        model_init: Model initialization time
        accumulation_duration: Duration of accumulation in hours
    
    Returns:
        Path to the created netCDF file
    """
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Create the netCDF file
    with nc.Dataset(output_file, 'w', format='NETCDF4') as ds:
        
        # Add global attributes
        ds.title = f"Fractions Skill Score (FSS) Data"
        ds.institution = "Geosphere Austria"
        ds.created = datetime.utcnow().isoformat()
        ds.Conventions = "CF-1.9"
        
        # Metadata about the verification
        ds.model_configuration = str(model_conf)
        ds.model_initialization = str(model_init)
        ds.accumulation_duration = f"{accumulation_duration} hours"
        ds.start_date = start_date.isoformat()
        ds.end_date = end_date.isoformat()
        ds.verification_subdomain = subdomain
        
        # Get dimensions from the FSS data
        if sim_data['fss'] is not None:
            n_thresholds, n_windows = sim_data['fss'].shape
        else:
            logger.warning(f"No FSS data available")
            return output_file
        
        # Get percentile dimensions from fssp if available
        n_percentiles = None
        if sim_data['fssp'] is not None:
            n_percentiles, n_windows_p = sim_data['fssp'].shape
            if n_windows_p != n_windows:
                logger.warning(f"Window count mismatch: FSS has {n_windows}, FSSP has {n_windows_p}. Using FSS value.")
        
        # Create dimensions
        threshold_dim = ds.createDimension('threshold', n_thresholds)
        window_dim = ds.createDimension('window', n_windows)
        if n_percentiles is not None:
            percentile_dim = ds.createDimension('percentile', n_percentiles)
        
        # Create threshold coordinate variable
        threshold_var = ds.createVariable('thresholds', 'f4', ('threshold',))
        threshold_var.units = 'mm'
        threshold_var.long_name = 'Precipitation thresholds for FSS'
        threshold_var[:] = thresholds[:n_thresholds]
        
        # Create percentile coordinate variable if available
        if n_percentiles is not None and len(fss_thresholds) > n_thresholds:
            # fss_thresholds contains both absolute thresholds and percentile thresholds
            # The percentile thresholds are after the absolute ones
            percentile_var = ds.createVariable('percentiles', 'f4', ('percentile',))
            percentile_var.units = 'dimensionless'
            percentile_var.long_name = 'Percentiles for FSS'
            percentile_var[:] = fss_thresholds[n_thresholds:]
        
        # Create window coordinate variable
        window_var = ds.createVariable('windows', 'i4', ('window',))
        window_var.units = 'grid points'
        window_var.long_name = 'Window sizes for FSS'
        # Handle windows which might be 2D (ny, nx)
        if isinstance(windows, np.ndarray) and windows.ndim == 2:
            window_values = np.max(windows, axis=1)
        else:
            window_values = windows
        window_var[:] = window_values[:n_windows]
        
        # Create variables for FSS data (absolute thresholds)
        fss_var = ds.createVariable('fss', 'f4', ('threshold', 'window'), 
                                    zlib=True, complevel=4, fill_value=np.nan)
        fss_var.long_name = 'Fractions Skill Score for absolute thresholds'
        fss_var.standard_name = 'fss'
        if sim_data['fss'] is not None:
            fss_var[:] = sim_data['fss']
        
        # Save FSS numerators if available
        if sim_data['fss_num'] is not None:
            fss_num_var = ds.createVariable('fss_numerator', 'f4', ('threshold', 'window'),
                                           zlib=True, complevel=4, fill_value=np.nan)
            fss_num_var.long_name = 'FSS numerator (sum of squared differences)'
            fss_num_var[:] = sim_data['fss_num']
        
        # Save FSS denominators if available
        if sim_data['fss_den'] is not None:
            fss_den_var = ds.createVariable('fss_denominator', 'f4', ('threshold', 'window'),
                                           zlib=True, complevel=4, fill_value=np.nan)
            fss_den_var.long_name = 'FSS denominator'
            fss_den_var[:] = sim_data['fss_den']
        
        # Save percentile FSS if available (can have different number of percentiles than thresholds)
        if sim_data['fssp'] is not None and n_percentiles is not None:
            fssp_var = ds.createVariable('fssp', 'f4', ('percentile', 'window'),
                                        zlib=True, complevel=4, fill_value=np.nan)
            fssp_var.long_name = 'Fractions Skill Score for percentiles'
            fssp_var[:] = sim_data['fssp']
        
        if sim_data['fssp_num'] is not None and n_percentiles is not None:
            fssp_num_var = ds.createVariable('fssp_numerator', 'f4', ('percentile', 'window'),
                                            zlib=True, complevel=4, fill_value=np.nan)
            fssp_num_var.long_name = 'Percentile FSS numerator'
            fssp_num_var[:] = sim_data['fssp_num']
        
        if sim_data['fssp_den'] is not None and n_percentiles is not None:
            fssp_den_var = ds.createVariable('fssp_denominator', 'f4', ('percentile', 'window'),
                                            zlib=True, complevel=4, fill_value=np.nan)
            fssp_den_var.long_name = 'Percentile FSS denominator'
            fssp_den_var[:] = sim_data['fssp_den']
    
    logger.info(f"FSS data saved to netCDF: {output_file}")
    return output_file
