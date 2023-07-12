import pickle
import os
import custom_experiments
from data_from_dcmdb import fill_path_file_template
import custom_experiments
# from custom_experiments import model_configurations as cmcs
import datetime as dt
import pygrib
import numpy as np

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



def check_fields(f):
    """Try a number of known passible grib handles that can be used to store precipitation
    in grib files. Return a list of valid handles if found"""
    try:
        f.select(shortName='twatp')
        f.select(shortName='tsnowp')
        return [{"shortName": "twatp"},
                {"shortName": "tsnowp"}]
    except:
        pass
    try:
        f.select(parameterNumber=8)
        return [{"parameterNumber": 8}]
    except:
        pass
    try:
        f.select(shortName='tp')
        return [{"shortName": "tp"}]
    except:
        pass
    try:
        f.select(indicatorOfParameter=197) #, indicatorOfTypeOfLevel=1, level=0)
        f.select(indicatorOfParameter=198) #, indicatorOfTypeOfLevel=1, level=0)
        f.select(indicatorOfParameter=199) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 197}, #, "indicatorOfTypeOfLevel": 1, "level": 0},
            {"indicatorOfParameter": 198}, #, "indicatorOfTypeOfLevel": 1, "level": 0},
            {"indicatorOfParameter": 199}] #, "indicatorOfTypeOfLevel": 1, "level": 0}]
    except:
        pass
    try:
        f.select(parameterNumber=65)
        f.select(parameterNumber=66)
        f.select(parameterNumber=75)
        return [
            {"parameterNumber": 65}, 
            {"parameterNumber": 66}, 
            {"parameterNumber": 75}]
    except:
        pass
    try:
        f.select(parameterNumber=55)
        f.select(parameterNumber=56)
        f.select(parameterNumber=76)
        f.select(parameterNumber=77)
        return [
            {"parameterNumber": 55}, 
            {"parameterNumber": 56}, 
            {"parameterNumber": 76}, 
            {"parameterNumber": 77}]
    except:
        pass
    try:
        f.select(shortName="RAIN_CON")
        f.select(shortName="RAIN_GSP")
        f.select(shortName="SNOW_CON")
        f.select(shortName="SNOW_GSP")
    except:
        pass
    logger.critical("No valid grib handles found in file".format(str(f)))
    exit()



def read_list_of_fields(f, handles):
    """ takes and unpacks a dictionary of grib handles, then reads all
    field and returns the sum"""
    tmp_data = []
    for handle in handles:
        tmp_data.append(f.select(**handle)[0])
    return tmp_data


def read_data(grib_file_path, get_lonlat_data=False):
    """ calls the grib handle check and returns fields with or without lon and lat data,
    depending on selection"""
    with pygrib.open(grib_file_path) as f:
        grib_handles = check_fields(f)
        logger.debug("Getting {:s} from file {:s}".format(repr(grib_handles), grib_file_path))
        tmp_data_list = read_list_of_fields(f, grib_handles)
    tmp_data_field = np.zeros(tmp_data_list[0].values.shape)
    for field in tmp_data_list:
        tmp_data_field += field.values
    tmp_data_field = np.where(tmp_data_field==9999.0, np.nan, tmp_data_field)
    if get_lonlat_data:
        lat, lon = tmp_data_list[0].latlons()
        return lon, lat, tmp_data_field
    else:
        return tmp_data_field


class ModelConfiguration:
    def __init__(self, custom_experiment_name, init, lead, duration):
        self.valid=False
        self.init = init #datetime
        self.lead = lead #int
        self.lead_end = lead + duration
        self.experiment_name = custom_experiment_name
        cmc = custom_experiments.experiment_configurations[custom_experiment_name]
        if "base_experiment" in cmc:
            self.__fill_cmc_with_base_values(cmc)
        self.path_template =    cmc["path_template"]
        self.init_interval =   cmc["init_interval"]
        self.max_leadtime =     cmc["max_leadtime"]
        self.output_interval = cmc["output_interval"]
        self.accumulated =      cmc["accumulated"]
        self.unit_factor =      cmc["unit_factor"]
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
                    return False
                elif os.path.getsize(fil) == 0:
                    return False
        return True


    def get_data(self):
        if self.accumulated:
            return self.__get_data_accumulated()
        else:
            return self.__get_data_not_accumulated()


    def __get_data_not_accumulated(self):
        first = True
        for i, fil in enumerate(self.file_list):
            logger.info("Reading file ({:d}): {:s}".format(i, fil))
            if first:
                lon, lat, tmp_data = read_data(fil, get_lonlat_data=True)
                first = False
            else:
                tmp_data += read_data(fil)
        tmp_data = np.where(tmp_data < 0., 0., tmp_data)
        return lon, lat, self.unit_factor * tmp_data


    def __get_data_accumulated(self):
        logger.info("Reading end file: {:s}".format(self.end_file))
        lon, lat, tmp_data = read_data(self.end_file, get_lonlat_data=True)
        if self.start_file:
            logger.info("Reading start file: {:s}".format(self.start_file))
            start_tmp_data = read_data(self.start_file)
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


    def get_file_path(self, l):
        if l == 0:
            return None
        path = fill_path_file_template(self.path_template, self.init, l)
        if self.experiment_name == "ifs-highres" and not os.path.isfile(path):
            path = mars_request(self.init, l)
        return path
            
    
    def file_path(self, lead):
        tt = self.init + dt.timedelta(hours=lead)
        if tt == self.init:
            return None
        else:
            return fill_path_file_template(self.path_template, self.init, tt)


    def get_file_list(self):
        lead = self.lead + 1
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
            mod = ModelConfiguration(model_name, exp_init_date, exp_lead, args.duration)
            if mod.valid:
                lon, lat, precip = mod.get_data()
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
    outfilename = "../DATA/"+args.name+"RR_data_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.p'
    with open(outfilename, 'wb') as f:
        pickle.dump(data_list, f)
    logger.info(outfilename+" written sucessfully.")


def save_fss(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    outfilename = "../DATA/"+args.name+"FSS_data_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.p'
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
