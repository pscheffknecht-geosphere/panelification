import os
import datetime as dt
import pygrib
import traceback
from dcmdb.cases import Cases

import logging
logger = logging.getLogger(__name__)


def process_case_and_exp_selection(args):
    """ Process cases and experiments from command line arguments, format the selection for 
    DCMDB's Cases() class"""
    if len(args.case) > 1:
        logger.critical("Multiple Cases not supported :-(")
        exit()
    if args.experiments == ["None"]:
        if len(args.case) == 1:
            return args.case
    else:
        if len(args.case) == 1:
            return {args.case[0]: args.experiments}


def get_ft(fts):
    # takes a list of file templates (strings) and looks for commonly used naming conventions for grib output
    for ft in fts:
        if "grb" in ft or "grib" in ft and not "sfx" in ft:
            return(ft)


def fill_path_file_template(pft, exp_init_date, exp_lead):
    """ Replace placeholders in the path and file pattern, code snipped from cases.py of DCMDB"""
    re_map = { '%Y': '{:04d}'.format(exp_init_date.year),
               '%m': '{:02d}'.format(exp_init_date.month),
               '%d': '{:02d}'.format(exp_init_date.day),
               '%H': '{:02d}'.format(exp_init_date.hour),
               '%M': '{:02d}'.format(exp_init_date.minute),
               '%S': '{:02d}'.format(exp_init_date.second),
               '%LLLL': '{:04d}'.format(exp_lead),
               '%LLL': '{:03d}'.format(exp_lead),
               '%LL': '{:02d}'.format(exp_lead),
               '%LM': '00' # NO MINUTE SUPPORT YET {:02d}'.format(int(exp_lead)),
         }
    for k,v in re_map.items():
        pft = pft.replace(k,str(v))
    return pft


def check_file_paths(exp_name, exp_init_date, file_paths, all_paths_raw):
    """ Checks for existence of the file after generating a file name from path and file pattern. This will
    assure that the requested experiment exists for the selected init time and verification period"""
    all_paths = [p.replace("//", "/") for p in all_paths_raw] # fix double slashes in ECMDB path
    for fil in file_paths:
        if not fil in all_paths and fil != "NoStart":
            return False
    return True


def make_scratch_paths(sim):
    scratchdir = os.environ["SCRATCH"]
    pattern = scratchdir + "/panelification/MODEL/{:s}/{:s}".format(
        sim["exp"], sim["init"].strftime("%Y%m%d/%H/"))
    if "NoStart" in sim["start_file"]:
        start_scratch_path = None
    else:
        start_scratch_path = pattern + sim["start_file"].split("/")[-1]
    end_scratch_path = pattern + sim["end_file"].split("/")[-1]
    return start_scratch_path, end_scratch_path



def ecp_experiment_data(data_list):
    """ copies the grib files from the desired experiments from ec file system to scratch """
    full_file_dict = {}
    for sim in data_list:
        full_file_dict[sim["start_file"]], full_file_dict[sim["end_file"]] = make_scratch_paths(sim)
        sim["start_scratch"] = full_file_dict[sim["start_file"]]
        sim["end_scratch"] = full_file_dict[sim["end_file"]]
    for epath, path in full_file_dict.items():
        if path:
            if not os.path.isfile(path):
                logger.info(f"Copying {epath}\n to -----> {path}")
                os.system(f"ecp {epath} {path}")
    return data_list


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

GRIB_shortNames = ["twatp", "tsnowp"]
def get_fields(f, get_lonlat_data=False):
    first = True
    handle = check_fields(f)
    logger.debug("Handle is:")
    logger.debug(handle)
    if "shortnames" in handle.keys():
        for sn in GRIB_shortNames:
            logger.debug(f"reading {sn} from file")
            if first:
                tmp_data = f.select(shortName=sn)[0]
            else:
                tmp_data += f.select(shortName=sn)[0]
    if "parameterNumber" in handle.keys():
        if first:
            tmp_data = f.select(parameterNumber=8)[0]
        else:
            tmp_data += f.select(parameterNumber=8)[0]
    if get_lonlat_data:
        lat, lon = tmp_data.latlons()
        return lon, lat, tmp_data.values
    else:
        return tmp_data.values


def read_data(data_list):
    for sim in data_list:
        logging.info("Reading "+sim["end_scratch"])
        with pygrib.open(sim["end_scratch"]) as f:
            lon, lat, tmp_data = get_fields(f, get_lonlat_data=True)
        if sim["start_scratch"]:
            logging.info("Reading "+sim["start_scratch"])
            with pygrib.open(sim["start_scratch"]) as f:
                tmp_data -= get_fields(f)
        sim["precip_data"] = tmp_data
        sim["lon"] = lon
        sim["lat"] = lat
    return data_list


def get_sim_and_file_list(args):
    """ use Ulf's DCMDB to search for available experiments that cover the start_date, end_date and lead time
    constraints given in args"""
    data_list = []
    if len(args.lead) == 1:
        leadmin = 0
        leadmax = args.lead[0]
    else:
        leadmin = args.lead[0]
        leadmax = args.lead[1]
    for exp_lead in range(leadmin, leadmax+1): #include end time
        max_lead = exp_lead + args.duration
        exp_init_date = dt.datetime.strptime(args.start, "%Y%m%d%H") - dt.timedelta(hours=exp_lead)
        # exp_end_date = start_date + dt.timedelta(hours=args.duration)
        case_selection = args.case #process_case_and_exp_selection(args)
        logger.info(case_selection)
        cases = Cases(selection=case_selection, printlev=0, path="dcmdb/cases")
        for exp_name in cases.cases.runs.keys():
            if exp_name in args.experiments:
                sim_OK = True
                experiment = cases.cases.runs[exp_name]
                all_experiment_files = experiment.reconstruct()
                pt = experiment.path_template
                fts = experiment.file_templates
                ft = get_ft(fts)
                pft = pt + ft
                start_file_path = fill_path_file_template(pft, exp_init_date, exp_lead) if exp_lead > 0 else 'NoStart'
                end_file_path = fill_path_file_template(pft, exp_init_date, max_lead)
                sim_OK = check_file_paths(exp_name, exp_init_date, [start_file_path, end_file_path], all_experiment_files)
                if sim_OK:
                    sim = {
                        "case" : args.case[0],
                        "exp" : exp_name,
                        "conf" : exp_name, # old code wants this, for now
                        "init" : exp_init_date,
                        "name" : "{:s} {:s} {:s}".format(
                            args.case[0], exp_name, exp_init_date.strftime("%Y-%d-%m %H")),
                        "start_file" : start_file_path, 
                        "end_file" : end_file_path}
                    data_list.append(sim)
    ecp_experiment_data(data_list)
    read_data(data_list)
    return data_list
