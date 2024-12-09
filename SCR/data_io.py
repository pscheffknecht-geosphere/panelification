import pickle
import os
from grib_handle_check import find_grib_handles
import custom_experiments
from data_from_dcmdb import fill_path_file_template
import custom_experiments
# from custom_experiments import model_configurations as cmcs
import datetime as dt
import pygrib
import numpy as np
import urllib.request
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# template to request precipitation over Europe on a Full Gaussian grid
request_template = """retrieve,
  class = od,
  type = fc,
  stream = oper,
  expver = 0001,
  levtype = sfc,
  param = 228.128,
  date = {date},
  time = {time},
  step = {step},
  padding = 0,
  expect = any,
  repres = gg,
  area=E,
  grid=F1280,
  database = marsod,
  target = {target}"""


def mars_request(init, step):
    path = "../MODEL/IFS_HIGHRES/ecmwf_precip_{:s}+{:04d}.grb".format(
        init.strftime("%Y%m%d_%H"), step) 
    logger.info("Requesting from precipitation from MARS for {:s} +{:d}h".format(
        init.strftime("%Y-%m-%d %H"), step))
    logger.info("Target file: {:s}".format(path))
    replace_dict = { 
        "{date}": init.strftime("%Y%m%d"), 
        "{time}": "{:04d}".format(init.hour),
        "{step}": "{:d}".format(step), 
        "{target}": "\"{:s}\"".format(path)
    } 
    request = request_template
    for key, val in replace_dict.items(): 
        request = request.replace(key, val) 
    with open("../TMP/mars_request_tmp", "w") as f: 
        f.write(request) 
    os.system("mars ../TMP/mars_request_tmp") 
    if os.path.isfile(path): # check if operation produced the target file
        return path
    else:
        return None


# def get_inca_rain_accumulated(fil, t_start, t_end):
def get_inca_rain_accumulated(mod):
    grb = pygrib.open(mod.end_file)
    idx_start = 4 * mod.lead + 1
    idx_end = 4 * mod.lead_end + 1
    first = True
    for idx in range(idx_start, idx_end + 1):
        if first:
            rr, lat, lon = grb[idx].data()
            first = False
        else:
            rr_, _, _ = grb[idx].data()
            rr += rr_
    return lon, lat, rr


def get_lonlat_fallback(grb):
    Nx = None
    Ny = None
    lll = None
    try:
        Nx, Ny = grb['Nx'], grb['Ny']
        lon = grb.longitudes.reshape((Ny, Nx))
        lat = grb.latitudes.reshape((Ny, Nx))
    except:
        logger.critical("Fallback failed on unknown grid type, exiting!!!")
        raise
    return lon, lat


def read_values_from_grib_field(grb):
    if grb['gridType'] == "lambert_lam": # new deode experiments
        return grb.values
    else:
        return grb.data()[0]

def read_list_of_fields(f, handles):
    """ takes and unpacks a dictionary of grib handles, then reads all
    field and returns the sum"""
    ret_data = []
    for handle in handles:
        ret_data.append(f.select(**handle)[0])
    return ret_data


def data_sum(tmp_data_list):
    if len(tmp_data_list) > 1:
        return np.sum(np.array([read_values_from_grib_field(x) for x in tmp_data_list]), axis=0)
    else:
        return read_values_from_grib_field(tmp_data_list[0])

def data_norm(tmp_data_list):
    if not len(tmp_data_list) == 2:
        raise ValueError("tmp_data_list has wrong lenght, must be 2 but is "+str(len(tmp_data_list)))
    else:
        return np.sqrt(read_values_from_grib_field(tmp_data_list[0]) ** 2 + read_values_from_grib_field(tmp_data_list[1]) ** 2)


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


def calc_data(tmp_data_list, parameter):
    calc_funcs = {
       "precip" : data_sum,
       "precip2" : data_sum,
       "precip3" : data_sum,
       "sunshine": data_sum,
       "lightning": data_sum,
       "hail": data_sum,
       "gusts" : data_norm
       }
    return calc_funcs[parameter](tmp_data_list)


def read_data(grib_file_path, parameter, lead, get_lonlat_data=False):
    """ calls the grib handle check and returns fields with or without lon and lat data,
    depending on selection"""
    with pygrib.open(grib_file_path) as f:
        grib_handles = find_grib_handles(f, parameter, lead)
        logger.debug("Getting {:s} from file {:s}".format(repr(grib_handles), grib_file_path))
        tmp_data_list = read_list_of_fields(f, grib_handles)
    tmp_data_field = calc_data(tmp_data_list, parameter)
    tmp_data_field = np.where(tmp_data_field>=9000., np.nan, tmp_data_field)
    logger.debug(f"DATA FROM {grib_file_path} parameter {parameter}:")
    logger.debug(f"Type: {type(tmp_data_field)}")
    logger.debug(f"Min: {tmp_data_field.min()}")
    logger.debug(f"Max: {tmp_data_field.max()}")
    logger.debug(f"Sample:")
    logger.debug(tmp_data_field)
    if get_lonlat_data:
        if tmp_data_list[0]['gridType'] == "lambert_lam":
            logger.info("gridType lambert_lam detected, going to fallback!")
            lon, lat = get_lonlat_fallback(tmp_data_list[0])
        else:
            lat, lon = tmp_data_list[0].latlons()
        return lon, lat, tmp_data_field
    else:
        return tmp_data_field


class ModelConfiguration:
    def __init__(self, custom_experiment_name, init, lead, duration, parameter):
        self.valid=False
        self.init = init #datetime
        self.lead = lead #int
        self.lead_end = lead + duration
        self.experiment_name = custom_experiment_name
        self.parameter = parameter
        cmc = custom_experiments.experiment_configurations[custom_experiment_name]
        if "base_experiment" in cmc:
            self.__fill_cmc_with_base_values(cmc)
        self.path_template   = self.__pick_value_by_parameter(cmc["path_template"])
        if not isinstance(self.path_template, list):
            self.path_template = [self.path_template]
        self.init_interval   = self.__pick_value_by_parameter(cmc["init_interval"])
        self.max_leadtime    = self.__pick_value_by_parameter(cmc["max_leadtime"])
        self.output_interval = self.__pick_value_by_parameter(cmc["output_interval"])
        self.accumulated     = self.__pick_value_by_parameter(cmc["accumulated"])
        self.unit_factor     = self.__pick_value_by_parameter(cmc["unit_factor"])
        self.color           = self.__pick_value_by_parameter(cmc["color"])
        if "url_template" in cmc.keys():
            self.url_template = cmc["url_template"]
        else:
            self.url_template = None
        if self.__times_valid():
            if self.accumulated:
                self.end_file = self.get_file_path(self.lead_end)
                self.start_file = self.get_file_path(self.lead)
            else:
                self.file_list = self.get_file_list()
            self.valid = self.__files_valid()
            if self.experiment_name == "inca-opt" and self.lead_end > 48:
                self.valid = False
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

        
    def __fill_cmc_with_base_values(self, cmc):
        """ if the experiment is deried from a base experiment, not all keys
        need values, only experiments which do not refer to a base_experiment
        need all their values filled"""
        keys = ["path_template", "init_interval", "max_leadtime", 
                "output_interval", "unit_factor", "accumulated", "color"]
        for key in keys:
            logger.debug(f"Setting key {key}")
            if not key in cmc.keys():
                if key in custom_experiments.experiment_configurations[cmc["base_experiment"]]:
                    logger.debug("Replacing {:s} in {:s} with value from base_experiment {:s}:".format(
                        key, self.experiment_name, cmc["base_experiment"]))
                    cmc[key] = custom_experiments.experiment_configurations[cmc["base_experiment"]][key]
                    logger.debug("  {:s}".format(str(cmc[key])))
                else:
                    cmc[key] = None
                    logger.debug("Not in base experiment, setting {:s} in {:s} to None:".format(
                        key, self.experiment_name))

        if not "url_template" in cmc.keys():
            cmc["url_template"] = None
              

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


    def __files_valid(self):        
        files_to_check = [self.start_file, self.end_file] if self.accumulated else self.file_list
        for fil in files_to_check:
            if fil:
                if not os.path.isfile(str(fil)): 
                    logger.debug(f"File {fil} not found, discarding experiment {self.experiment_name} {self.init}")
                    return False
                elif os.path.getsize(fil) == 0:
                    logger.debug(f"File {fil} was found but has size 0, discarding experiment {self.experiment_name}")
                    return False
        return True


    def get_data(self, param):
        if param == 'gusts' or param == 'hail':
            return self.__get_data_max()
        else:
            if self.experiment_name == "inca-opt":
                return get_inca_rain_accumulated(self)
            if self.accumulated:
                return self.__get_data_accumulated()
            else:
                return self.__get_data_not_accumulated()


    def __get_data_not_accumulated(self):
        first = True
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data(fil, self.parameter, 0, get_lonlat_data=True) # 0 for lead time, unused for unaccmulated models
                first = False
            else:
                tmp_data += read_data(fil, self.parameter)
        tmp_data = np.where(tmp_data < 0., 0., tmp_data)
        return lon, lat, self.unit_factor * tmp_data


    def __get_data_max(self):
        first = True
        tmp_data_list = []
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data(fil, self.parameter, get_lonlat_data=True)
                first = False
            else:
                td2 = read_data(fil, self.parameter)
                tmp_data = np.where(td2 > tmp_data, td2, tmp_data)
        tmp_data = np.where(tmp_data < 0., 0., tmp_data)
        return lon, lat, self.unit_factor * tmp_data


    def __get_data_accumulated(self):
        logger.info("Reading end file: {:s}".format(self.end_file))
        lon, lat, tmp_data = read_data(self.end_file, self.parameter, self.lead_end, get_lonlat_data=True)
        if self.start_file:
            logger.info("Reading start file: {:s}".format(self.start_file))
            start_tmp_data = read_data(self.start_file, self.parameter, self.lead)
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


    def get_file_path(self, l):
        if l == 0:
            return None
        print(self.path_template)
        for path_template in self.path_template:
            path = fill_path_file_template(path_template, self.init, l)
            if self.experiment_name == "ifs-highres" and not os.path.isfile(path):
                path = mars_request(self.init, l)
            if not os.path.isfile(path) and self.url_template:
                path = self.download_file(path, l)
            if os.path.isfile(path):#  and self.url_template:
                return path
        logger.info(f"File {path} was not found, {self.experiment_name} {self.init} will not be used.")
        return 'None'
            
    
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
        leadmin, leadmax = get_minmax_lead(args, ce)
        for exp_lead in reversed(range(leadmin, leadmax + 1)):
            max_lead = exp_lead + args.duration
            exp_init_date = dt.datetime.strptime(args.start, "%Y%m%d%H") - dt.timedelta(hours=exp_lead)
            logger.debug("Checking for {:s} at {:s}".format(
                model_name, exp_init_date.strftime("%Y-%m-%d %H")))
            mod = ModelConfiguration(model_name, exp_init_date, exp_lead, args.duration, args.parameter)
            if mod.valid:
                lon, lat, precip = mod.get_data(args.parameter)
                sim = {
                    "case": args.case[0],
                    "exp": model_name,
                    "conf": model_name,
                    "init": exp_init_date,
                    "name": "{:s} {:s}".format(model_name, exp_init_date.strftime("%Y-%m-%d %H")),
                    # "start_file": mod.file_path(exp_lead),
                    # "end_file": mod.end_file,
                    # "grib_handles": mod.grib_handles,
                    "lon": lon,
                    "lat": lat,
                    "precip_data": precip,
                    "color" : mod.color}
                data_list.append(sim)
    return data_list


################################################################################
### SAVING DATA AND VERIFICATION RESULTS
def save_data(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    start_date_str = start_date.strftime("%Y%m%d_%HUTC_")
    outfilename = f"../DATA/{args.name}RR_data_{start_date_str}{args.duration:02d}h_acc_{verification_subdomain}.p"
    with open(outfilename, 'wb') as f:
        pickle.dump(data_list, f)
    logger.info(outfilename+" written sucessfully.")


def save_fss(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    start_date_str = start_date.strftime("%Y%m%d_%HUTC_")
    outfilename = f"../DATA/{args.name}FSS_data_{start_date_str}{args.duration:02d}h_acc_{verification_subdomain}.p"
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
