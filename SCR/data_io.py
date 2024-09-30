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
import pyresample
import matplotlib.pyplot as plt
from mars_request_templates import mars_request_templates

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


def mars_request(exp_name, init, step,path=None):
    if not path:
        path = "../MODEL/{:s}/ecmwf_precip_{:s}+{:04d}.grb".format(
            exp_name,
            init.strftime("%Y%m%d_%H"), step) 
    else:
        path = fill_path_file_template(path, init, step)
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
    with open("../TMP/mars_request_tmp", "w") as f: 
        f.write(request) 
    os.system("mars ../TMP/mars_request_tmp") 
    if os.path.isfile(path): # check if operation produced the target file
        return path
    else:
        return None


def ecfs_request(ec_path_template, path_template, init, step):
    # TODO: add failsafe of sorts
    ecpath = fill_path_file_template(ec_path_template, init, step)
    path = fill_path_file_template(path_template, init, step)
    ret = os.system("ecp ecpath path")
    return path if ret == 0 else None


def get_lonlat_fallback(grb):
    Nx = None
    Ny = None
    lll = None
    try:
        Nx, Ny = grb['Nx'], grb['Ny']
        lon = grb.longitudes.reshape((Ny, Nx))
        lat = grb.latitudes.reshape((Ny, Nx))
        logger.debug(f"Nx: {Nx}, Ny: {Ny}")
        logger.debug(f"lat: {lat}\nlon: {lon}")
        logger.debug(f"lat.shape: {lat.shape}")
    except:
        logger.critical("Fallback failed on unknown grid type, exiting!!!")
        raise
    return lon, lat


def read_values_from_grib_field(grb):
    if grb['gridType'] == "lambert_lam": # new deode experiments
        return grb.values
    elif grb['gridType'] == "reduced_gg":
        # TODO: workaround for Austria, make this take values from the region!!!
        grb.expand_grid(False)
        data1d, lat1d, lon1d = grb.data()
        if lon1d.max() > 180.:
            lon1d -= 360.
        logger.debug(f"Nx: {lon1d.shape}, Ny: {lat1d.shape}")
        logger.debug(f"lat: {lat1d}\nlon: {lon1d}")
        lo = np.arange(-8., 25.001, 0.025)
        la = np.arange(40., 58.001, 0.025)
        llo, lla = np.meshgrid(lo, la)
        targ_def = pyresample.geometry.SwathDefinition(llo, lla)
        orig_def = pyresample.geometry.SwathDefinition(lon1d, lat1d)
        data = pyresample.kd_tree.resample_nearest(orig_def, data1d, targ_def, reduce_data=False, radius_of_influence=25000)
        # exit()
        return data
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


def calc_data(tmp_data_list, parameter):
    calc_funcs = {
       "precip" : data_sum,
       "precip2" : data_sum,
       "sunshine": data_sum,
       "lightning": data_sum,
       "hail": data_sum,
       "gusts" : data_norm
       }
    return calc_funcs[parameter](tmp_data_list)


def read_data(grib_file_path, parameter, get_lonlat_data=False):
    """ calls the grib handle check and returns fields with or without lon and lat data,
    depending on selection"""
    with pygrib.open(grib_file_path) as f:
        grib_handles = find_grib_handles(f, parameter)
        logger.debug("Getting {:s} from file {:s}".format(repr(grib_handles), grib_file_path))
        tmp_data_list = read_list_of_fields(f, grib_handles)
    tmp_data_field = calc_data(tmp_data_list, parameter)
    logger.debug(type(tmp_data_field))
    logger.debug(tmp_data_field)
    tmp_data_field = np.where(tmp_data_field==9999.0, np.nan, tmp_data_field)
    if get_lonlat_data:
        if tmp_data_list[0]['gridType'] == "lambert_lam":
            logger.info("gridType lambert_lam detected, going to fallback!")
            lon, lat = get_lonlat_fallback(tmp_data_list[0])
        elif tmp_data_list[0]['gridType'] == "reduced_gg":
            logger.info("gridType reduced_gg detected, making own!")
            lo = np.arange(-8., 25.001, 0.025)
            la = np.arange(40., 58.001, 0.025)
            lon, lat = np.meshgrid(lo, la)   
        else:
            lat, lon = tmp_data_list[0].latlons()
        return lon, lat, tmp_data_field
    else:
        return tmp_data_field


class ModelConfiguration:
    def __init__(self, custom_experiment_name, init, lead, duration, parameter):
        self.read = 0
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
        self.init_interval   = self.__pick_value_by_parameter(cmc["init_interval"])
        self.max_leadtime    = self.__pick_value_by_parameter(cmc["max_leadtime"])
        self.output_interval = self.__pick_value_by_parameter(cmc["output_interval"])
        self.accumulated     = self.__pick_value_by_parameter(cmc["accumulated"])
        self.unit_factor     = self.__pick_value_by_parameter(cmc["unit_factor"])
        self.on_mars         = self.__pick_value_by_parameter(cmc["on_mars"])
        if "ecfs_path_template" in cmc:
            self.ecfs_path_template = self.__pick_value_by_parameter(cmc["ecfs_path_template"])
        else:
            self.ecfs_path_template = None
        if self.__times_valid():
            if self.accumulated:
                self.end_file = self.get_file_path(self.lead_end)
                self.start_file = self.get_file_path(self.lead)
                print(self.start_file)
            else:
                self.file_list = self.get_file_list()
            self.valid = self.__files_valid()
            self.print()
            print(self.valid)
            print(self.__files_valid())
        else:
            logger.debug("Model {:s} with init {:s} has no output for the requested time window.".format(
                self.experiment_name, self.init.strftime("%Y-%m-%d %H")))


    def __pick_value_by_parameter(self, custom_experiment_item):
        """ If path template is a dictionary, return the correct item for the given parameter
            if it is a string, return the string
            else raise a ValueError"""
        ret = None
        if isinstance(custom_experiment_item, dict):
            for key, item in custom_experiment_item.items():
                if self.parameter in key or self.parameter == key:
                    ret = custom_experiment_item[self.parameter]
            if ret == None and 'else' in custom_experiment_item.keys():
                ret = custom_experiment_item['else']
            elif not 'else' in custom_experiment_item.keys():
                logger.debug("Found invalid entry in custom_experiments for experiment {self.experiment_name}")
                for key, item in custom_experiment_item.items():
                    logger.debug(f"{str(key)}: {str(item)}")
                logger.critical(f"If parameter is not a dict key, dict needs an 'else': .... entry to fall back onto.")
        else:
            ret = custom_experiment_item
        logger.debug(f"Picked {ret} for {self.parameter} in experiment {self.experiment_name}")
        return ret

        
    def __fill_cmc_with_base_values(self, cmc):
        """ if the experiment is deried from a base experiment, not all keys
        need values, only experiments which do not refer to a base_experiment
        need all their values filled"""
        keys = ["path_template", "init_interval", "max_leadtime", 
                "output_interval", "unit_factor", "accumulated"]
        for key in keys:
            if not key in cmc.keys():
                logger.debug("Replacing {:s} in {:s} with value from base_experiment {:s}:".format(
                    key, self.experiment_name, cmc["base_experiment"]))
                cmc[key] = custom_experiments.experiment_configurations[cmc["base_experiment"]][key]
                logger.debug("  {:s}".format(str(cmc[key])))
        if not "on_mars" in cmc.keys():
            if "on_mars" in custom_experiments.experiment_configurations[cmc["base_experiment"]].keys():
                cmc["on_mars"] = custom_experiments.experiment_configurations[cmc["base_experiment"]]["on_mars"]
            else:
                cmc["on_mars"] = False
              

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
        if self.accumulated and not self.end_file:
            return False
        for fil in files_to_check:
            if fil:
                if not os.path.isfile(str(fil)): 
                    return False
                elif os.path.getsize(fil) == 0:
                    return False
        return True


    def get_data(self, param):
        if param == 'gusts':
            return self.__get_data_max()
        else:
            if self.accumulated:
                return self.__get_data_accumulated()
            else:
                return self.__get_data_not_accumulated()


    def __get_data_not_accumulated(self):
        first = True
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data(fil, self.parameter, get_lonlat_data=True)
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
        self.read += 1
        logger.info("Reading end file: {:s}".format(self.end_file))
        lon, lat, tmp_data = read_data(self.end_file, self.parameter, get_lonlat_data=True)
        if self.start_file:
            logger.info("Reading start file: {:s}".format(self.start_file))
            start_tmp_data = read_data(self.start_file, self.parameter)
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



    def get_ecfs_file(self, init, l):
        # pull some dirty tricks to search a bit
        ret = 1
        check_list = []
        use_file = None
        for user in ["kmek", "kay", "kmw"]:
            for case in ["", "1", "2", "3"]:
                user_case_path_template = self.ecfs_path_template.replace("{USER}", user).replace("{CASE}", case)
                check_list.append(fill_path_file_template(user_case_path_template, self.init, l))
        for fil in check_list:
            ret = int(os.system(f"els {fil}") / 256)
            if ret == 1:
                print(fil)
            elif ret == 0:
                use_file = fil
                break
        if not use_file:
            return None
        return os.system("ecp {:s} {:s}".format(
            use_file,
            fill_path_file_template(self.path_template, self.init, l)))

    def get_file_path(self, l):
        if l == 0:
            return None
        path = fill_path_file_template(self.path_template, self.init, l)
        if self.on_mars and not os.path.isfile(path):
            if not os.path.isdir(f"/home/kmek/panelification/MODEL/{self.experiment_name}"):
                logger.debug(f"MODEL/{self.experiment_name} not found, creating directory")
                os.system(f"mkdir -p /home/kmek/panelification/MODEL/{self.experiment_name}")
            path = mars_request(self.experiment_name, self.init, l)
        if self.ecfs_path_template and not os.path.isfile(path):
            ret = self.get_ecfs_file(self.init, l)
            if ret != 0:
                return None
        return path
            
    
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


def get_sims_and_file_list(data_list, args):
    if len(args.lead) == 1:
        leadmin = 0
        leadmax = args.lead[0]
    else:
        leadmin = args.lead[0]
        leadmax = args.lead[1]
    for model_name in args.custom_experiments:
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
                    "precip_data": precip}
                data_list.append(sim)
    return data_list


################################################################################
### SAVING DATA AND VERIFICATION RESULTS
def save_data(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    start_date_str = start_date.strftime("%Y%m%d_%HUTC_")
    outfilename = "../DATA/{args.name}RR_data_{start_date_str}{args.duration:02d}h_acc_{verification_subdomain}.p"
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
