import pickle
import os
import custom_experiments
from data_from_dcmdb import fill_path_file_template
import custom_experiments
from custom_experiments import model_configurations as cmcs
import datetime as dt
import pygrib

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
    try:
        f.select(shortName='twatp')
        f.select(shortName='tsnowp')
        return {"shortnames": ["twatp", "tsnowp"]} 
    except:
        pass
    try:
        f.select(parameterNumber=8)
        return {"parameterNumber": 8}
    except:
        pass
    try:
        f.select(shortName='tp')
        return {"shortNames": ["tp"]}
    except:
        pass
    # try:
    #     f.select(indicatorOfParameter=197, indicatorOfTypeOfLevel=1, level=0)
    #     f.select(indicatorOfParameter=198, indicatorOfTypeOfLevel=1, level=0)
    #     f.select(indicatorOfParameter=199, indicatorOfTypeOfLevel=1, level=0)
    #     return [
    #         {"indicatorOfParameter": 197, "indicatorOfTypeOfLevel": 1, "level": 0},
    #         {"indicatorOfParameter": 198, "indicatorOfTypeOfLevel": 1, "level": 0},
    #         {"indicatorOfParameter": 199,"indicatorOfTypeOfLevel": 1,"level": 0}]


def read_data(grib_file_path, get_lonlat_data=False):
    first = True
    with pygrib.open(grib_file_path) as f:
        grib_handles = check_fields(f)
        logger.debug("Getting {:s} from file {:s}".format(repr(grib_handles), grib_file_path))
        if "shortNames" in grib_handles.keys():
            for sn in grib_handles["shortNames"]:
                if first:
                    tmp_data = f.select(shortName=sn)[0]
                    first = False
                else:
                    tmp_date += f.select(shortName=sn)[0]
    if get_lonlat_data:
        lat, lon = tmp_data.latlons()
        return lon, lat, tmp_data.values
    else:
        return tmp_data.values


class ModelConfiguration:
    def __init__(self, custom_experiment_name, init, lead, duration):
        self.valid=False
        self.init = init #datetime
        self.lead = lead #int
        self.lead_end = lead + duration
        self.experiment_name = custom_experiment_name
        self.path_template = cmcs[custom_experiment_name]["path_template"]
        self.init_intervall = cmcs[custom_experiment_name]["init_interval"]
        self.max_leadtime = cmcs[custom_experiment_name]["max_leadtime"]
        self.output_intervall = cmcs[custom_experiment_name]["output_interval"]
        self.grib_handles = cmcs[custom_experiment_name]["grib_handles"]
        self.unit_factor = cmcs[custom_experiment_name]["unit_factor"]
        if self.__times_valid():
            self.end_file = self.get_file_path(self.lead_end)
            self.start_file = self.get_file_path(self.lead)
            self.valid = self.__files_valid()
            self.print()
        else:
            logger.info("Model {:s} with init {:s} has no output for the requested time window.".format(
                self.experiment_name, self.init.strftime("%Y-%m-%d %H")))



    def print(self):
        logger.debug("init: {:s}".format(self.init.strftime("%Y-%m-%d %H")))
        logger.debug("lead: {:d}".format(self.lead))
        logger.debug("start file: {:s}".format(str(self.start_file)))
        logger.debug("end file: {:s}".format(str(self.end_file)))
        logger.debug("model is valid: {:s}".format(str(self.valid)))

    def __times_valid(self):
        """ Checks the requested init and lead time to see if they
        are availabled depending on the model configuration's init
        and lead time intervalls"""
        logger.debug("Init inverval: {:d}".format(self.init_intervall))
        logger.debug("Init hour: {:d}".format(self.init.hour))
        logger.debug("Output inverval: {:d}".format(self.output_intervall))
        logger.debug("Output hour: {:d}".format(self.lead))
        logger.debug("Output hour: {:d}".format(self.lead_end))
        time_checks = [
            self.lead%self.output_intervall == 0,
            self.init.hour%self.init_intervall == 0,
            self.lead_end%self.output_intervall == 0]
        print(time_checks)
        return True if all(time_checks) else False

    def __files_valid(self):        
        if self.start_file:
            if not os.path.isfile(self.start_file):
                return False
            elif os.path.getsize(self.start_file) == 0:
                return False
        if not os.path.isfile(self.end_file):
            return False
        if os.path.getsize(self.end_file) == 0:
            return False
        return True

    def get_data(self):
        lon, lat, tmp_data = read_data(self.end_file, get_lonlat_data=True)
        if self.start_file:
            start_tmp_data = read_data(self.start_file)
        return lon, lat, self.unit_factor * tmp_data


    def get_file_path(self, l):
        if l == 0:
            return None
        path = fill_path_file_template(self.path_template, self.init, l)
        if self.experiment_name == "ifs-highres" and not os.path.isfile(path):
            path = mars_request(self.init, l)
        logger.info("Got path: {:s}".format(path))
        return path
            
    
    def file_path(self, lead):
        tt = self.init + dt.timedelta(hours=lead)
        if tt == self.init:
            return None
        else:
            return fill_path_file_template(self.path_template, self.init, tt)




def get_sims_and_file_list(data_list, args):
    if len(args.lead) == 1:
        leadmin = 0
        leadmax = args.lead[0]
    else:
        leadmin = args.lead[0]
        leadmax = args.lead[1]
    for exp_lead in range(leadmin, leadmax + 1):
        max_lead = exp_lead + args.duration
        exp_init_date = dt.datetime.strptime(args.start, "%Y%m%d%H") - dt.timedelta(hours=exp_lead)
        for model_name in args.custom_models:
            logging.debug("Checking for {:s} at {:s}".format(
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
                    "start_file": mod.file_path(exp_lead),
                    "end_file": mod.end_file,
                    "grib_handles": mod.grib_handles,
                    "lon": lon,
                    "lat": lat,
                    "precip_data": precip}
                data_list.append(sim)
                print(sim["lon"], sim["lat"], sim["precip_data"])
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
