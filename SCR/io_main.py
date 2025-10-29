import pickle
import os
import datetime as dt
import numpy as np
import urllib.request
from pathlib import Path

from grib_handle_check import find_grib_handles
from data_from_dcmdb import fill_path_file_template
from mars_request_templates import mars_request_templates

from io_grib import read_data_grib, get_inca_rain_accumulated, get_icon_unstructured
from io_gdal import read_data_gdal
from io_netcdf import read_data_netcdf

from paths import PAN_DIR_TMP, PAN_DIR_MODEL, PAN_DIR_MODEL2, PAN_DIR_DATA

import logging
logger = logging.getLogger(__name__)


def mars_request(exp_name, init, step,path=None):
    year, month, day, hour = init.year, init.month, init.day, init.hour
    if not path:
        path = f"{PAN_DIR_MODEL}/{exp_name}/{year}{month:02d}{day:02d}/{hour:02d}/{exp_name}_{hour:04d}.grb"
    else:
        path = fill_path_file_template(path, init, step)
    dir_part = path.rpartition("/")[0]
    if not os.path.isdir(dir_part):
        logger.info(f"MARS REQUEST: {dir_part} does not exist, creating it now")
        os.system(f"mkdir -p {dir_part}")
    logger.info("Requesting from precipitation from MARS for {:s} +{:d}h".format(
        init.strftime("%Y-%m-%d %H"), step))
    logger.info("Target file: {:s}".format(path))
    stream = "oper" if init.hour in [0, 12] else "scda"
    replace_dict = { 
        "{date}": init.strftime("%Y%m%d"), 
        "{time}": "{:02d}".format(init.hour),
        "{step}": "{:d}".format(step), 
        "{target}": "\"{:s}\"".format(path),
        "{stream}": stream
    } 
    request = mars_request_templates[exp_name]
    for key, val in replace_dict.items(): 
        request = request.replace(key, val) 
    with open(f"{PAN_DIR_TMP}/mars_request_tmp", "w") as f: 
        f.write(request) 
    os.system(f"/usr/local/bin/mars {PAN_DIR_TMP}/mars_request_tmp") 
    if os.path.isfile(path): # check if operation produced the target file
        return path
    else:
        return None


def scale_hail(data_list):
    """ scale the hail data, PoH in obs is 0 ... 100, model is different. 
    Scale to low, moderate, high:
    Qualitative: zero ............ low ............. moderate ................ high 
    OBS:         0 ............... 25 ............... 50 ..................... >75
    AROME:       0 ............... 16 ............... 20 ..................... >24
    New Scale:   0 ............... 1 ................ 2 ...................... >3"""
    for sim in data_list:
        new_arr = sim['precip_data']
        if sim['conf'] == ['INCA']:
            new_arr = sim['precip_data'] = 0.04 * new_arr # scale to [0, 4]
        else:
            new_arr = np.where(new_arr<16., 0.0625 * new_arr, new_arr)
            new_arr = np.where(new_arr>=16., 1. + (new_arr - 16.) * 0.25, new_arr)
            sim['precip_data'] = new_arr
    return data_list


file_type_indicators = {
    "NetCDF": ["nc", "ncf", "ncd"],
    "GRIB": ["grb", "grib", "grb2", "grib2"],
    "GDAL": ["grd"]
}

read_func_dict = {
    "GRIB": read_data_grib,
    "NetCDF": read_data_netcdf,
    "GDAL": read_data_gdal
}

class ModelConfiguration:
    def __init__(self, custom_experiment_name, init, lead, args):
        """THIS CLASS HANDLES ONE RUN OF ONE MODEL
        
        Every model and run in the verification is handled here. It contains some
        basic sanity checks, handles locating the files and reading them etc."""
        # grab information from custom_experiments file
        cmc = args.custom_experiment_data[custom_experiment_name]
        # grab information from base experiment if provided
        self.valid = False
        self.init = init #datetime
        self.lead = lead #int in hours
        self.lead_end = lead + args.duration
        self.experiment_name = custom_experiment_name
        self.parameter = args.parameter
        self.check_ecfs = args.check_ecfs
        self.path_template   = self.__pick_value_by_parameter(cmc["path_template"])
        if "base_experiment" in cmc.keys(): 
            self.__fill_cmc_with_base_values(cmc, args)
        if not isinstance(self.path_template, list) and isinstance(self.path_template, str):
            self.path_template = [self.path_template]
        logger.debug(f"Path template(s) for model {self.experiment_name} is:")
        for tmpl in self.path_template:
            logger.debug(f"   {tmpl}")
        for anam in ["init_interval", "max_leadtime", "output_interval", "accumulated", "unit_factor"]:
            setattr(self, anam, self.__pick_value_by_parameter(cmc[anam]))
        for anam in ["ensemble", "grib_handle", "lagged_ensemble", "color"]:
            setattr(self, anam, self.__pick_value_by_parameter(cmc[anam]) if anam in cmc else None)
        # is the simulation part of an ensemble or lagged ensemble?
        if self.ensemble and not (args.merge_ens_init_times or self.lagged_ensemble):
            init_str = self.init.strftime("%Y%m%d_%H")
            self.ensemble += f"_{init_str}"
            logger.debug(f"Treating different init times as different ensembles, changed to {self.ensemble}")
        # are we on ATOS and using MARS?
        self.on_mars = self.__pick_value_by_parameter(cmc["on_mars"]) if "on_mars" in cmc.keys() else False
        self.ecfs_path_template = self.__pick_value_by_parameter(cmc["ecfs_path_template"]) if "ecfs_path_template" in cmc else None
        self.url_template = cmc["url_template"] if "url_template" in cmc.keys() else None
        if self.__times_valid():
            if self.accumulated:
                self.end_file = self.get_file_path(self.lead_end)
                self.start_file = self.get_file_path(self.lead)
            else:
                self.file_list = self.get_file_list()
            self.valid = self.__files_valid()
            self.print()
        else:
            logger.debug("Model {:s} with init {:s} has no output for the requested time window.".format(
                self.experiment_name, self.init.strftime("%Y-%m-%d %H")))


    def __pick_value_by_parameter(self, custom_experiment_item):
        """ If path template is a dictionary, return the correct item for the given parameter
            if it is a string, return the string
            else raise a ValueError"""
        ret = None
        useparam = "precip" if "precip" in self.parameter else self.parameter
        if isinstance(custom_experiment_item, dict):
            for key, item in custom_experiment_item.items():
                if useparam in key or useparam == key:
                    ret = custom_experiment_item[useparam]
            if ret == None and 'else' in custom_experiment_item.keys():
                ret = custom_experiment_item['else']
            elif not 'else' in custom_experiment_item.keys():
                logger.debug("Found invalid entry in custom_experiments for experiment {self.experiment_name}")
                for key, item in custom_experiment_item.items():
                    logger.debug(f"{str(key)}: {str(item)}")
                logger.critical(f"If parameter is not a dict key, dict needs an 'else': .... entry to fall back onto.")
        else:
            ret = custom_experiment_item
        # logger.debug(f"Picked {ret} for {self.parameter} in experiment {self.experiment_name}")
        return ret

        
    def __fill_cmc_with_base_values(self, cmc, args):
        """ if the experiment is deried from a base experiment, not all keys
        need values, only experiments which do not refer to a base_experiment
        need all their values filled"""
        keys = ["init_interval", "max_leadtime", 
                "output_interval", "unit_factor", "accumulated", "color", "ensemble"]
        for key in keys:
            logger.debug(f"Setting key {key}")
            if not key in cmc.keys():
                if key in args.custom_experiment_data[cmc["base_experiment"]]:
                    logger.debug("Replacing {:s} in {:s} with value from base_experiment {:s}:".format(
                        key, self.experiment_name, cmc["base_experiment"]))
                    cmc[key] = args.custom_experiment_data[cmc["base_experiment"]][key]
                    logger.debug("  {:s}".format(str(cmc[key])))
                else:
                    cmc[key] = None
                    logger.debug("Not in base experiment, setting {:s} in {:s} to None:".format(
                        key, self.experiment_name))
              

    def print(self):
        logger.debug("init: {:s}".format(self.init.strftime("%Y-%m-%d %H")))
        logger.debug("lead: {:d}".format(self.lead))
        logger.debug("model is valid: {:s}".format(str(self.valid)))
        if self.accumulated:
            logger.debug("start file: {:s}".format(str(self.start_file)))
            logger.debug("end file: {:s}".format(str(self.end_file)))
        else:
            for i, fil in enumerate(self.file_list):
                logger.debug("file ({:d}): {:s}".format(i, str(fil)))


    def __times_valid(self):
        """ Checks the requested init and lead time to see if they
        are availabled depending on the model configuration's init
        and lead time intervals"""
        time_checks = [
            self.lead%self.output_interval == 0,
            self.init.hour%self.init_interval == 0,
            self.lead_end%self.output_interval == 0]
        return True if all(time_checks) else False


    def __get_file_type(self, file_list):
        file_type_list = []
        for ii, fil in enumerate([f for f in file_list if f is not None]):
            file_type_list.append(fil.split(".")[-1]) #get file ending
            logger.debug(f"file {ii} has ending {file_type_list[-1]}")
        first = file_type_list[0]
        if all(first == ft for ft in file_type_list):
            logger.debug(f"all files are of type {first}")
            for ftype, suffixList in file_type_indicators.items():
                if first in suffixList:
                    logger.info(f" model uses {ftype} files")
                    return ftype
        return None

    def __files_valid(self):        
        files_to_check = [self.start_file, self.end_file] if self.accumulated else self.file_list
        if self.accumulated and not self.end_file:
            return False
        if not self.accumulated and not any(self.file_list):
            logger.debug(f"Model {self.experiment_name} has no accumulated values, but the file list is")
            for fil in self.file_list:
                logger.debug(f"  fil")
            return False
        for fil in files_to_check:
            if fil:
                if not os.path.isfile(str(fil)): 
                    logger.info(f"File {fil} not found, discarding experiment {self.experiment_name} {self.init}")
                    return False
                elif os.path.getsize(fil) == 0:
                    logger.info(f"File {fil} was found but has size 0, discarding experiment {self.experiment_name}")
                    return False
        self.file_type = self.__get_file_type(files_to_check)
        return False if self.file_type is None else True


    def get_data(self, param):
        if param == 'gusts' or param == 'hail':
            return self.__get_data_max()
        else:
            # 1. check if experiment is an INCA forecast of any kind
            if any([s in self.experiment_name for s in ["INCA", "inca", "Inca"]]):
                return get_inca_rain_accumulated(self) # TODO: create common INCA read function
            # catch raw icon ensemble members
            if "ICOND2_m" in self.experiment_name:
                return get_icon_unstructured(self)
            if self.accumulated:
                return self.__get_data_accumulated()
            else:
                return self.__get_data_not_accumulated()


    def __get_data_not_accumulated(self):
        first = True
        read_data = read_data_gdal if "samos" in self.experiment_name else read_data_grib
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data(fil, self.parameter, 0, get_lonlat_data=True) # 0 for lead time, unused for unaccmulated models
                first = False
            else:
                tmp_data += read_data(fil, self.parameter, 0)
        tmp_data = np.where(tmp_data < 0., 0., tmp_data)
        return lon, lat, self.unit_factor * tmp_data


    def __get_data_max(self):
        first = True
        tmp_data_list = []
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data_grib(fil, self.parameter, 0, get_lonlat_data=True)
                first = False
            else:
                td2 = read_data_grib(fil, self.parameter, 0)
                tmp_data = np.where(td2 > tmp_data, td2, tmp_data)
        tmp_data = np.where(tmp_data < 0., 0., tmp_data)
        return lon, lat, self.unit_factor * tmp_data


    def __get_data_accumulated(self):
        logger.info("Reading end file: {:s}".format(self.end_file))
        lon, lat, tmp_data = read_data_grib(self.end_file, self.parameter, self.lead_end, get_lonlat_data=True)
        if self.start_file:
            logger.info("Reading start file: {:s}".format(self.start_file))
            start_tmp_data = read_data_grib(self.start_file, self.parameter, self.lead)
            tmp_data -= start_tmp_data
        # clamp to 0 because apparently this difference can be negative???
        # this is NOT a pygrib or panelification problem, also happens when
        # reading values using EPYGRAM
        # TODO: figure out if this is a problem anywhere else
        tmp_data = np.where(tmp_data < 0., 0., tmp_data) 
        logger.debug("{:s}: lon lat extent is: {:.2f} - {:.2f}, {:.2f} - {:.2f}".format(
            self.experiment_name, lon.min(), lon.max(), lat.min(), lat.max()))
        logger.debug("{:s}: Precipitation is between {:.3f} and {:.3f} mm".format(
            self.experiment_name, self.unit_factor * tmp_data.min(), self.unit_factor * tmp_data.max()))
        return lon, lat, self.unit_factor * tmp_data

    def gen_panelification_path(self, l):
        init_str = self.init.strftime("%Y%m%d")
        hour_str = self.init.strftime("%H")
        tmp_dir = f"{PAN_DIR_MODEL}/{self.experiment_name}/{init_str}/{hour_str}"
        tmp_fil = f"{self.experiment_name}_{l:04d}.grb"
        return f"{tmp_dir}/{tmp_fil}"


    def get_file_from_ecfs(self, l):
        logger.debug(f"{self.experiment_name} {self.init} has no existing files, trying ecfs")
        logger.debug(f"template: {self.path_template}")
        logger.debug(f"ecfs template: {self.ecfs_path_template}")
        init_str = self.init.strftime("%Y%m%d")
        hour_str = self.init.strftime("%H")
        tmp_dir = f"{PAN_DIR_MODEL}/{self.experiment_name}/{init_str}/{hour_str}"
        tmp_fil = f"{self.experiment_name}_{l:04d}.grb"
        logger.debug(f"ecfs file: ec:{tmp_dir}/{tmp_fil}")
        if not os.path.isdir(tmp_dir):
            logger.info(f"creating {tmp_dir}")
            os.system(f"mkdir -p {tmp_dir}")
        if not isinstance(self.ecfs_path_template, list):
            self.ecfs_path_template = [self.ecfs_path_template]
        for ecfs_path_template in self.ecfs_path_template:
            ecfs_file = fill_path_file_template(ecfs_path_template, self.init, l)
            logger.debug(f"looking for: {ecfs_file}")
            ret = os.system(f"/usr/local/bin/els ec:{ecfs_file}")
            if ret == 0:
                logger.info(f"copying from ec:{ecfs_file}")
                logger.info(f"to {tmp_dir}/{tmp_fil}")
                os.system(f"/usr/local/bin/ecp ec:{ecfs_file} {tmp_dir}/{tmp_fil}")
                return f"{tmp_dir}/{tmp_fil}"
            else:
                logger.debug(f"{ecfs_file} not found")
        return None


    def download_file(self, path, l):
        file_url = fill_path_file_template(self.url_template, self.init, l)
        logger.info(f"File {path} not found, but url_template is present")
        logger.info(f"Attempting to download from {file_url}")
        parent_directory_path = str(Path(path).parent)
        if not os.path.isdir(parent_directory_path):
            logger.info(f"Path {parent_directory_path} does not exist, creating it now")
            os.makedirs(parent_directory_path)
        urllib.request.urlretrieve(file_url, path)
        directory_path, file_name = os.path.split(path)
        grib_copy_command = f"grib_copy -w shortName=tp,stepRange=0-{l} {path} {directory_path}/tmp_rr.grb2"
        logger.debug(grib_copy_command)
        os.system(grib_copy_command)
        cdo_command = f"cdo sellonlatbox,0,30,40,60 {directory_path}/tmp_rr.grb2 {directory_path}/tmp_rr_small.grb2"
        logger.debug(cdo_command)
        os.system(cdo_command)
        os.system(f"rm {path} {directory_path}/tmp_rr.grb2")
        logger.debug(f"rm {path} {directory_path}/tmp_rr.grb2")
        os.system(f"mv {directory_path}/tmp_rr_small.grb2 {path}")
        logger.debug(f"mv {directory_path}/tmp_rr_small.grb2 {path}")
        logger.debug({path})
        return f"{directory_path}/GFS+{l:04d}_rr.grb2"

    def check_pan_path_existence(self):
        if not os.path.isdir(f"{PAN_DIR_MODEL}/{self.experiment_name}"):
            logger.info(f"MODEL/{self.experiment_name} not found, creating directory")
            os.system(f"mkdir -p {PAN_DIR_MODEL}/{self.experiment_name}")
        return 0

    def get_file_path(self, lead):
        """CHECK FOR INPUT FILES
        1. check path template given in custom_experiments
           This can be a list of multiple locations, they will all be checked in order
        2. check panelification path
           this will only exist if the file was previously obtained for one of these 3 locations:
           a) file was copied from MARS on ATOS
           b) file was copied from ECFS on ATOS
           c) file was downloaded using the url_template
        3. Check other sources in this order:
           a) check whether files are on MARS
              This only happens if
              - on_mars is set to True
              - mars_request_templates.py has an entry for the current experiment_name
           b) check whether files are on ECFS
              This only happens if
              - ecfs_file_template exists
           c) check whether files can be downloaded
              This only happens if
              - url_template has a value"""
        logger.debug(f"Getting file path for model {self.experiment_name}")
        path = None
        if lead == 0:
            return None
        # 1. path from given template
        for path_template in self.path_template:
            template_path = fill_path_file_template(path_template, self.init, lead)
            logger.debug(f"Checking use of path template: {template_path}")
            if os.path.isfile(template_path):
                return template_path
        # 2. panelification path
        panelification_path = self.gen_panelification_path(lead)
        logger.debug(f"Checking panelficiation path: {panelification_path}")
        if os.path.isfile(panelification_path):
            return panelification_path
        # 3.a if on mars, try that
        if self.on_mars:
            logger.debug(f"Checking MARS archive")
            self.check_pan_path_existence()
            path = mars_request(self.experiment_name, self.init, lead, path=panelification_path)
            if path:
                return path
        # 3.b try ecfs
        if self.ecfs_path_template:
            logger.debug(f"Trying ECFS: {self.ecfs_path_template}")
            self.check_pan_path_existence()
            path = self.get_file_from_ecfs(lead)
        # 3.c try online
        if self.url_template:
            logger.info(f"Attempting to download...")
            self.check_pan_path_existence()
            path = self.download_file(panelification_path, lead)
        return None
            
    
    def file_path(self, lead):
        tt = self.init + dt.timedelta(hours=lead)
        if tt == self.init:
            return None
        else:
            return fill_path_file_template(self.path_template, self.init, tt)


    def get_file_list(self):
        lead = self.lead + self.output_interval
        file_list = []
        while lead <= self.lead_end:
            file_list.append(self.get_file_path(lead))
            lead += self.output_interval
        return file_list


def get_minmax_lead(args, ce):
    if len(args.lead) == 1:
        leadmin = 0
        leadmax = args.lead[0]
    elif len(args.lead) == 2:
        leadmin = args.lead[0]
        leadmax = args.lead[1]
    else:
        leadmin = args.lead[::2][ce]
        leadmax = args.lead[1::2][ce]
    return leadmin, leadmax


def get_sims_and_file_list(data_list, args):
    for ce, model_name in enumerate(args.custom_experiments):
        leadmin, leadmax = get_minmax_lead(args, ce) #TODO: add check for correct length of args.lead
        for exp_lead in reversed(range(leadmin, leadmax + 1)):
            max_lead = exp_lead + args.duration
            exp_init_date = dt.datetime.strptime(args.start, "%Y%m%d%H") - dt.timedelta(hours=exp_lead)
            logger.debug("Checking for {:s} at {:s}".format(
                model_name, exp_init_date.strftime("%Y-%m-%d %H")))
            mod = ModelConfiguration(model_name, exp_init_date, exp_lead, args)
            if mod.valid:
                lon, lat, mod_field_data = mod.get_data(args.parameter)
                sim = {
                    "case": args.case[0],
                    "exp": model_name,
                    "conf": model_name,
                    "type": "model",
                    "init": exp_init_date,
                    "lead": leadmin,
                    "name": "{:s} {:s}".format(model_name, exp_init_date.strftime("%Y-%m-%d %H")),
                    "lon": lon,
                    "lat": lat,
                    "precip_data": mod_field_data,
                    "color" : mod.color,
                    "ensemble" : mod.ensemble}
                data_list.append(sim)
    return data_list


################################################################################
### SAVING DATA AND VERIFICATION RESULTS
def save_data(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    start_date_str = start_date.strftime("%Y%m%d_%HUTC_")
    outfilename = f"{PAN_DIR_DATA}/{args.name}RR_data_{start_date_str}{args.duration:02d}h_acc_{verification_subdomain}.p"
    with open(outfilename, 'wb') as f:
        pickle.dump(data_list, f)
    logger.info(outfilename+" written sucessfully.")


def save_fss(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    start_date_str = start_date.strftime("%Y%m%d_%HUTC_")
    outfilename = f"{PAN_DIR_DATA}/{args.name}FSS_data_{start_date_str}{args.duration:02d}h_acc_{verification_subdomain}.p"
    fss_dict = {}
    for sim in data_list[1::]:
        sim_dict = {
            'fss'      : sim['fss'],
            'fssp'     : sim['fssp'],
            'fss_num'  : sim['fss_num'],
            'fssp_num' : sim['fssp_num'],
            'fss_den'  : sim['fss_den'],
            'fssp_den' : sim['fssp_den']}
        fss_dict[sim['name']] = sim_dict
    with open(outfilename, 'wb') as f:
        pickle.dump(fss_dict, f)
    logger.info(outfilename+" written sucessfully.")
