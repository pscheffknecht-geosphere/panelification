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
    logger.info(f"checking for panels: {PAN_DIR_PLOTS}/*claef-AA-comparison*{ttstr}*.png")
    logger.info(f"checking for panels: {PAN_DIR_PLOTS}/*samos-RegAust*{ttstr}*.png")
    d_curr_str = d_curr.strftime("%Y%m%d")
    flist = glob.glob(f"{PAN_DIR_PLOTS}/*cast*{d_curr_str}*png")
    logger.info(f"Found {len(flist)} files with *cast*")
    flist2 = glob.glob(f"{PAN_DIR_PLOTS}/*claef-AA-comparison*{d_curr_str}*png")
    flist3 = glob.glob(f"{PAN_DIR_PLOTS}/*samos-RegAust*{d_curr_str}*png")
    if len(flist2) > 0:
        logger.info(f"Found {len(flist2)} files with *claef-AA-comparison*")
        flist += flist2
    if len(flist3) > 0:
        logger.info(f"Found {len(flist3)} files with *samos-RegAust*")
        flist += flist3
    if flist == []:
        logger.info("No panels found for today, sending nothing.")
    else:
        for fil in flist:
            os.system("scp -i /export/home/anamod/pscheffknecht/.ssh/id_rsa "+fil+" mgruppe@vvhmod-dev:"+remote_base_path+".")


def clean_old_panels(d_curr=today()):
    logger.info("Clean up older panle graphics from 160 to 167 days ago")
    for dd_diff in range(160, 167):  # do entire week, in case some days were skipped
        newday = d_curr - dt.timedelta(days=dd_diff)
        logger.info("Checking for "+remote_base_path+"*"+newday.strftime("%Y%m%d")+"*.png")
        old_files = glob.glob(remote_base_path+"*"+newday.strftime("%Y%m%d")+"*.png")
        if len(old_files) > 0:
            for fil in old_files:
                logger.info(f"Removing {fil}")
                delete_cmd = "ssh mgruppe@vvhmod-dev 'rm "+fil+"'"
                logger.info(delete_cmd)
                # os.system(delete_cmd)

def send_html_to_mgruppe():
    logger.info("Copying template to mgruppe")
    logger.debug("scp -i /export/home/anamod/pscheffknecht/.ssh/id_rsa verif_panels.html mgruppe@vvhmod-dev:/modelle/prod/mgruppe/WEB/HTML/.")
    os.system("scp -i /export/home/anamod/pscheffknecht/.ssh/id_rsa verif_panels.html mgruppe@vvhmod-dev:/modelle/prod/mgruppe/WEB/HTML/.")
    

def get_file_lists(d_curr):
    fclist = []
    nclist = []
    aalist = []
    ralist = []
    t_ = d_curr
    while d_curr > t_ - dt.timedelta(days=160):
        d_curr_str = d_curr.strftime("%Y%m%d")
        _fclist = glob.glob(f"../PLOTS/*forecast*{d_curr_str}*png")
        _nclist = glob.glob(f"../PLOTS/*nowcast*{d_curr_str}*png")
        _aalist = glob.glob(f"../PLOTS/*claef-AA-comparison*{d_curr_str}*png")
        _ralist = glob.glob(f"../PLOTS/*samos-RegAust*{d_curr_str}*png")
        for _fc in _fclist:
            logger.info("Found panel: {file}".format(
                file = _fc))
            fclist.append(_fc)
        for _nc in _nclist:
            logger.info("Found panel: {file}".format(
                file = _nc))
            nclist.append(_nc)
        for _aa in _aalist:
            logger.info("Found panel: {file}".format(
                file = _aa))
            aalist.append(_aa)
        for _ra in _ralist:
            logger.info("Found panel: {file}".format(
                file = _ra))
            ralist.append(_ra)
        d_curr += -dt.timedelta(days=1)
    return fclist, nclist, aalist, ralist


def make_file_list_html(flist):
    fstr = ''
    for fil in flist:
        print(f"processing {fil}")
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
    logger.info("Fill in html template")
    d_work = today() if not d_work else d_work
    fclist, nclist, aalist, ralist = get_file_lists(d_work)
    fcliststr = make_file_list_html(fclist)
    ncliststr = make_file_list_html(nclist)
    aaliststr = make_file_list_html(aalist)
    raliststr = make_file_list_html(ralist)
    with open('blank.html', 'r') as htmlfile:
        blank_html_str = htmlfile.read()
        blank_html_str = blank_html_str.replace("FORECASTLINKLIST", fcliststr)
        blank_html_str = blank_html_str.replace("AALINKLIST", aaliststr)
        blank_html_str = blank_html_str.replace("RALINKLIST", raliststr)
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
