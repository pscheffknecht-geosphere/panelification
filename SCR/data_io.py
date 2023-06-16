import numpy as np
import pygrib
from misc import loop_datetime
import glob
from datetime import timedelta as dt
from model_parameters import *
import grib_handles
import pickle
import inca_functions as inca



def get_file_path(path_to_check):
    """
    takes a file path and check is a file is found
    if no file is found, it returns None, False
    if one or more files are found, it returns file_path, True
    """ 
    print("Checking for file: "+path_to_check)
    list_to_check=glob.glob(path_to_check)
    if len(list_to_check) == 0:
        return None, False
    if len(list_to_check) > 0:
        return list_to_check[0], True


def config_not_found(conf, tt, failed_path=None):
    """ just a diagnostic print """
    print("configuration "+conf+" at "+tt.strftime("%y-%m-%d %H:00:00")+" NOT OK!!!")
    if failed_path is not None:
        print("Cannot open "+failed_path)


def get_offset_and_factor(h):
    curr_dict = param_pars[h['indicatorOfParameter']][h['indicatorOfTypeOfLevel']]
    if 'factor' in curr_dict.keys():
        factor = curr_dict['factor']
    else:
        factor = 1.
    if 'offset' in curr_dict.keys():
        offset = curr_dict['offset']
    else:
        offset = 0.
    return offset, factor


def hours_int(td):
    return int(td.total_seconds()/3600)


def quarter_hours_int(td):
    return int(td.total_seconds()/900)

def hours_float(td):
    return td.total_seconds() / 3600.


def read_inca_fc(conf, tt, to_start, to_end, start_date, end_date, args):
    print("checking for configuration "+conf+" at "+tt.strftime("%y-%m-%d %H:00:00"))
    inca_file = inca_fc_paths[args.parameter].format(
        tt.strftime("%Y%m%d"), tt.strftime("%Y%m%d%H"))
    inca_start_index = quarter_hours_int(to_start)
    inca_end_index = quarter_hours_int(end_date - start_date) + inca_start_index
    print("INCA-fc will start at index {:d} and end at index {:d}".format(inca_start_index, inca_end_index))
    sim = {
        'conf' : conf,
        'name' : conf+" "+tt.strftime("%Y%m%d %H"),
        'inca_file' : inca_file,
        'inca_indices' : [inca_start_index, inca_end_index]}
    return sim


def read_inca_plus_fc(conf, tt, to_start, to_end, start_date, end_date):
    print("checking for configuration "+conf+" at "+tt.strftime("%y-%m-%d %H:00:00"))
    inca_file = "/incaplus_arch1/iplus/out/INCAPlus_1h/inca/{:s}/INCAPlus_1h_RR_FC_{:s}00.grb2".format(
        tt.strftime("%Y/%m/%d"), tt.strftime("%Y%m%d%H"))
    inca_start_index = hours_int(to_start)
    inca_end_index = hours_int(end_date - start_date) + inca_start_index
    print("INCA+ reading will start at {:d} h and end at {:d} h".format(inca_start_index, inca_end_index))
    sim = {
        'conf': conf,
        'name': conf+" "+tt.strftime("%Y%m%d %H"),
        'inca_file': inca_file,
        'inca_indices': [inca_start_index, inca_end_index]}
    return sim


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


### FOR LATER
# def split_claef_members_entry(data_list):
#     """ seeks the entry named claef-members and splits it into
#     separate entries for each member """
#     # find entry with claef-members
#     for sim in data_list:
#         if sim['conf'] == 'claef-members':
#             print(sim)
#             exit()

### TODO
# find a more elegant way of doing this so we don't have to add a new elif for each configuration
# maybe string parsing?
def fill_model_archive_path(conf, tt_init, tt, args, nmember = 0):
    if conf == 'arome':
        file_pattern = model_archive_paths[args.parameter][conf].format(
            tt_init.strftime("%Y%m%d/%H"),
            int((tt.days*86400+tt.seconds)/3600),
            0)
    elif conf == 'aromeruc':
        file_pattern = model_archive_paths[args.parameter][conf].format(
            tt_init.strftime("%Y%m%d/%H"),
            int((tt.days*86400+tt.seconds)/3600),
            0)
    elif conf == 'claef-members':
        file_pattern = model_archive_paths[args.parameter][conf].format(
            tt_init.strftime("%Y%m%d%H"),
            int((tt.days*86400+tt.seconds)/3600),
            nmember)
    # elif conf == 'ecmwf':
    #     tt_curr = tt_init + tt
    #     file_pattern = model_archive_paths[conf].format(
    #         tt_init.strftime("%m%d%H"),
    #         tt_curr.strftime("%m%d%H"))
    return file_pattern


def fill_model_current_prod_path(conf, tt_init, tt):
    if conf == 'arome':
        file_pattern = model_current_prod_paths[conf].format(
            tt_init.hour,
            (tt.days*86400+tt.seconds)/3600,
            0)
    elif conf == 'aromeruc':
        file_pattern = model_current_prod_paths[conf].format(
            tt_init.hour,
            (tt.days*86400+tt.seconds)/3600,
            0)
    elif conf == 'claef' or conf == 'arome':
        file_pattern = model_current_prod_paths[conf].format(
            tt_init.hour,
            (tt.days*86400+tt.seconds)/3600)
    elif conf == 'ecmwf':
        tt_curr = tt_init + tt
        file_pattern = model_current_prod_paths[conf].format(
            tt_init.strftime("%m%d%H"),
            tt_curr.strftime("%m%d%H"))
    return file_pattern
### END TODO


def read_model_accumulated_var(conf, tt, to_start, to_end, start_date, end_date, args, archive=True, member_idx=0):
    print("checking for configuration "+conf+" at "+tt.strftime("%y-%m-%d %H:00:00"))
    if hours_float(to_start) > 0:
        if archive:
            file_pattern = fill_model_archive_path(conf, tt, to_start, args, nmember=member_idx)
        else:
            file_pattern = fill_model_current_prod_path(conf, tt, to_start)
        start_file, file_ok = get_file_path(file_pattern)
        if not file_ok:
            config_not_found(conf, tt, failed_path=file_pattern)
            return None
    else:
        start_file = None
    if archive:
        file_pattern = fill_model_archive_path(conf, tt, to_end, args, nmember=member_idx)
    else:
        file_pattern = fill_model_current_prod_path(conf, tt, to_end, args)
    end_file, file_ok = get_file_path(file_pattern)
    if not file_ok:
        config_not_found(conf, tt, failed_path=file_pattern)
        return None
    if conf == "claef-members":
        sim_name = "claef-member {:02d} {:s}".format(member_idx, tt.strftime("%Y%m%d %H"))
    else:
        sim_name = conf+" "+tt.strftime("%Y%m%d %H")
    sim = {
        'conf': conf,
        'name': sim_name,
        'start_file': start_file,
        'end_file': end_file}
    return sim


def read_model_unaccumulated_var(conf, tt, to_start, to_end, start_date, end_date, args, archive=True):
    sim = None
    fill_model_path = fill_model_archive_path if archive else fill_model_current_prod_path
    print("checking for configuration "+conf+" at "+tt.strftime("%y-%m-%d %H:00:0r"))
    model_file_list = []
    model_files_missing = 0
    for tt_model in loop_datetime(start_date + dt(hours=1), end_date + dt(hours=1), dt(hours=1)):
        to_tt_model = tt_model - tt
        file_pattern = fill_model_path(conf, tt, to_tt_model, args)
        tmp_file, file_ok = get_file_path(file_pattern)
        if file_ok:
            model_file_list.append(tmp_file)
        else:
            model_files_missing=model_files_missing+1
    if model_files_missing==0:
        sim = {
            'conf' : conf,
            'name' : conf+" "+tt.strftime("%Y%m%d %H"),
            'model_file_list' : model_file_list}
    else:
        config_not_found(conf,tt)
    return sim

def get_sims_and_file_list(start_date, end_date, min_lead, max_lead, simdf, args):
    ''' based on two dates and some limits, this function determines a
    list of grib files which contain the start and end of the
    accumulation period and extracts precipitation values for each
    simulation.

    Description of the nested loops:

    conf ..... loop over configurations (arome, aromeruc, alaro5, ...)

    tt ....... loop over possible init times for the simulations

    For each conf and tt, the function checks if output for a given run exists for
    the start and end time of the desired accumulation period. If both files are found
    or if the init time is equal to the start of the accumulation period, the simulation
    is added to the list, otherwise not.

    If the configuration is 'arome', the function checks /arome_arch/aladin/ARCHIVE in
    addition to the precipitation archive, if the files aren't found there.
    '''
    data_list = []
    for cc, conf in enumerate(args.configs):
        if type(min_lead) == list:
            init_start = start_date - dt(hours=max_lead[cc])
            init_end = start_date - dt(hours=min_lead[cc])
        elif type(min_lead) == int:
            init_start = start_date - dt(hours=max_lead)
            init_end = start_date - dt(hours=min_lead)
        conf_freq = simdf[simdf['name'] == conf]['init_interval'].values
        conf_inteval = simdf[simdf['name'] == conf]['lead_time_interval'].values
        max_lead_time = simdf[simdf['name'] == conf]['max_lead_time'].values
        if conf != 'inca-fc':
            grib_suffix = simdf[simdf['name'] == conf]['grib_suffix'].values[0]
        # else:
        #     print("Skipped")
        # accumulated = simdf[simdf['name'] == conf]['accumulated'].values
        accumulated = model_vardata[conf][args.parameter][0]
        print("Working on {:s} and accumulated is {:s}".format(
            conf, str(accumulated)))
        for tt in loop_datetime(init_start, init_end + dt(hours=1), dt(hours=1)):
            # print("checking for sims at "+str(tt))
            if tt.hour%conf_freq == 0:
                to_start = start_date - tt
                to_end = end_date - tt
                if (to_end.days*86400+to_end.seconds)/3600 <= max_lead_time:
                    if conf == 'inca-fc':
                        sim = read_inca_fc(conf, tt, to_start, to_end, start_date, end_date, args)
                    elif conf == 'inca_plus-fc':
                        sim = read_inca_plus_fc(conf, tt, to_start, to_end, start_date, end_date)
                    elif conf == 'claef-members':
                        sims = []
                        for member_idx in range(17): # control + 16 members
                            sims.append(read_model_accumulated_var(conf, tt, to_start, to_end, start_date, end_date, args, member_idx=member_idx))
                    elif accumulated:
                        sim = read_model_accumulated_var(conf, tt, to_start, to_end, start_date, end_date, args)
                    else:
                        sim = read_model_unaccumulated_var(conf, tt, to_start, to_end, start_date, end_date, args)
                    # if claef-members, iterate over sims and check each entry, else just check sim
                    if conf == "claef-members":
                        if len(sims) > 0:
                            for sim in sims:
                                if sim:
                                    data_list.append(sim)
                    else:
                        if sim:
                            data_list.append(sim)
    return data_list


def get_precip_handles(f):
    # checks for indicatorOfParameter 61, 197, 198, 199
    # if 61 is found, it will be used, else if 197, 198, 199 are found
    # they will be used, if neither are found, fail
    res = 0
    for iop in [61, 197, 198, 199]:
        try:
            ff = f.select(indicatorOfParameter = iop)
            for grb in ff:
                res = res + iop
        except ValueError as err:
            pass
            # print("ValueError: no match found for indicatorOfParameter={:d}".format(iop))
            # print("res = {:d}".format(res))
    if res == 61 or res == 655: # all are found
        #print("Using 61: total precipitation")
        return grib_handles.GRIB_indicators['arome']['precip']['B']
    elif res == 594:
        #print("Using 197, 198, 199: rain + snow + graupel")
        return grib_handles.GRIB_indicators['arome']['precip']['A']
    else:
        return ValueError("no match found")


def read_fields(f, grib_handles, args, sim, get_lon_lat=False):
    if args.parameter == 'precip' and 'arome' in sim['conf']:
        grib_handles = get_precip_handles(f)
    for h in grib_handles:
        offset, factor = get_offset_and_factor(h)
        tmp_data = f.select(
            indicatorOfParameter=h['indicatorOfParameter'],
            typeOfLevel=h['indicatorOfTypeOfLevel'],
            level=h['level'])[0]
        field_data = factor*tmp_data.values+offset
        if get_lon_lat:
            lat, lon = tmp_data.latlons()
    if get_lon_lat:
        return field_data, lon, lat
    else:
        return field_data


def read_data(data_list, args):
    """
    loop over all simulations which have the necessary files, then
    call the function to read the data and de-accumulate or accumulate
    as necessary
    """
    #print(args)
    for sim in data_list:
        # print(simdf[simdf['name']==sim['conf']])
        if 'grb' in simdf[simdf['name']==sim['conf']]['grib_suffix'].values[0]:
            GRIB_handles = grib_handles.GRIB_indicators[sim['conf']][args.parameter]
        # accumulated = simdf[simdf['name'] == sim['conf']]['accumulated'].values
        accumulated = model_vardata[sim['conf']][args.parameter][0]
        factor = model_vardata[sim['conf']][args.parameter][1]
        # factor = simdf[simdf['name'] == sim['conf']]['unit_factor'].values
        if sim['conf'] == 'inca-fc':
            rr_tmp = inca.read_inca_fc_accum(sim, args)
            lon, lat = inca.INCA_grid()
            factor = 1.
        elif sim['conf'] == 'inca_plus-fc':
            rr_tmp = inca.read_inca_fc_accum(sim, args)
            if rr_tmp is None:
                rr_tmp = np.full((401, 701), np.nan)
            lon, lat = inca.INCA_grid(INCAplus=True)
            factor = 1.
        else:
            if accumulated:
                end_file = sim['end_file']
                print("reading: "+end_file)
                #end_f = ep.formats.resource(end_file, 'r')
                end_f = pygrib.open(end_file)
                #if sim['conf'] == 'icond2':
                #    rr_field = read_fields(end_f, GRIB_handles)
                #else:
                rr_field, lon, lat = read_fields(end_f, GRIB_handles, args, sim, get_lon_lat=True)
                #lon, lat = rr_field.geometry.get_lonlat_grid()
                if sim['start_file'] is not None:
                    start_file = sim['start_file']
                    print("reading: "+start_file)
                    #start_f = ep.formats.resource(start_file, 'r')
                    start_f = pygrib.open(start_file)
                    if sim['conf'] == 'icond2':
                        rr_field_start = read_fields(start_f, GRIB_handles, args, sim)
                    else:
                        rr_field_start = read_fields(start_f, GRIB_handles, args, sim)
                    rr_tmp = rr_field - rr_field_start
                else:
                    rr_tmp = rr_field
            else:
                first_model_file = True
                for model_file in sim['model_file_list']:
                    print("reading: "+model_file)
                    #f_tmp = ep.formats.resource(model_file, 'r')
                    f_tmp = pygrib.open(model_file)
                    if first_model_file:
                        rr_field, lon, lat = read_fields(f_tmp, GRIB_handles, args, sim, get_lon_lat=True)
                        rr_tmp = rr_field
                        first_model_file = False
                    else:
                        rr_tmp = rr_tmp + read_fields(f_tmp, GRIB_handles, args, sim)
        sim['precip_data']=rr_tmp*factor
        sim['lat']=np.asarray(lat)
        sim['lon']=np.asarray(lon)
    return(data_list)


### SAVING DATA AND VERIFICATION RESULTS
def save_data(data_list, verification_subdomain, start_date, end_date, args):
    """ write all data to a pickle file """
    outfilename = "../DATA/"+args.name+"RR_data_"+start_date.strftime("%Y%m%d_%HUTC_")+'{:02d}h_acc_'.format(args.duration)+verification_subdomain+'.p'
    with open(outfilename, 'wb') as f:
        pickle.dump(data_list, f)
    print(outfilename+" written sucessfully.")


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
    print(outfilename+" written sucessfully.")
