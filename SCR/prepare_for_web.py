import os
import glob
import datetime as dt

import logging
logger = logging.getLogger(__name__)

from paths import PAN_DIR_PLOTS

remote_base_path = "/modelle/prod/mgruppe/WEB/PRECIP_VERIF_PANELS/"


def today():
    t_ = dt.datetime.now() 
    d_curr = dt.datetime(t_.year, t_.month, t_.day)
    return(d_curr)


def send_panels_to_mgruppe(d_curr=None):
    d_curr = today() - dt.timedelta(days=1) if not d_curr else d_curr
    ttstr = d_curr.strftime("%Y%m%d")
    logger.info(f"checking for panels: {PAN_DIR_PLOTS}/*cast*{ttstr}*.png")
    d_curr_str = d_curr.strftime("%Y%m%d")
    flist = glob.glob(f"{PAN_DIR_PLOTS}/*cast*{d_curr_str}*png")
    if flist == []:
        logger.info("No panels found for today, sending nothing.")
    else:
        for fil in flist:
            os.system("scp "+fil+" mgruppe@vvhmod-dev:"+remote_base_path+".")


def clean_old_panels(d_curr=today()):
    for dd_diff in range(160, 167):  # do entire week, in case some days were skipped
        newday = d_curr - dt.timedelta(days=dd_diff)
        logger.info("Checking for "+remote_base_path+"*"+newday.strftime("%Y%m%d")+"*.png")
        old_files = glob.glob(remote_base_path+"*"+newday.strftime("%Y%m%d")+"*.png")
        if len(old_files) > 0:
            for fil in old_files:
                delete_cmd = "ssh mgruppe@vvhmod-dev 'rm "+fil+"'"
                logger.info(delete_cmd)
                # os.system(delete_cmd)

def send_html_to_mgruppe():
    os.system("scp verif_panels.html mgruppe@vvhmod-dev:/modelle/prod/mgruppe/WEB/HTML/.")
    

def get_file_lists(d_curr):
    fclist = []
    nclist = []
    t_ = d_curr
    while d_curr > t_ - dt.timedelta(days=160):
        d_curr_str = d_curr.strftime("%Y%m%d")
        _fclist = glob.glob(f"{PAN_DIR_PLOTS}/*forecast*{d_curr_str}*png")
        _nclist = glob.glob(f"{PAN_DIR_PLOTS}/*nowcast*d_curr_str*png")
        for _fc in _fclist:
            logger.info("Found panel: {file}".format(
                file = _fc))
            fclist.append(_fc)
        for _nc in _nclist:
            logger.info("Found panel: {file}".format(
                file = _nc))
            nclist.append(_nc)
        d_curr += -dt.timedelta(days=1)
    return fclist, nclist


def make_file_list_html(flist):
    fstr = ''
    for fil in flist:
        parts = fil.split("_")
        pidx = 0
        for idx, part in enumerate(parts):
            if part == "panel":
                pidx = idx
                break
        pretty_str = dt.datetime.strptime(parts[pidx+1], "%Y%m%d").strftime("%Y-%m-%d") + " " + \
            parts[pidx+2].replace("UTC", " UTC") + " " + \
            parts[pidx+3].replace("0", "").replace("h", " hour accumulated rain") + " " + \
            parts[pidx+5].replace(".png", "")
        fil = fil.replace("PLOTS", "PRECIP_VERIF_PANELS")    
        fstr += "<a href=\""+fil+"\" target=\"_blank=\" rel=\"noopener noreferrer\">"+pretty_str+"</a><br>\n"
    return fstr


def complete_blank_html(d_work=None):
    d_work = today() if not d_work else d_work
    fclist, nclist = get_file_lists(d_work)
    fcliststr = make_file_list_html(fclist)
    ncliststr = make_file_list_html(nclist)
    with open('blank.html', 'r') as htmlfile:
        blank_html_str = htmlfile.read()
        blank_html_str = blank_html_str.replace("FORECASTLINKLIST", fcliststr)
        blank_html_str = blank_html_str.replace("NOWCASTLINKLIST", ncliststr)
    with open('verif_panels.html', 'w') as outfile:
        outfile.write(blank_html_str)


# for manually updates to intranet:
if __name__ == "__main__":
    complete_blank_html()
    send_panels_to_mgruppe()
    send_html_to_mgruppe()
    clean_old_panels()
    # upload backlog:
    # tt = today()
    # while tt >= dt.datetime(2024,10, 3):
    #     send_panels_to_mgruppe(tt)
    #     tt -= dt.timedelta(days=1)
