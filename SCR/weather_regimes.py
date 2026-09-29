"""Daily weather regime classification (WLK) of the verified period.

The WLK file has one line per day: the date (YYYYMMDD) followed by a code like
"03ACD", i.e. the regime (00 NE, 01 SE, 02 SW, 03 NW, 04 variable / weak gradient)
and the cyclonality at 925 and 500 hPa (C cyclonic, A anticyclonic). The last
letter of the code and all further columns are not used.
"""
import datetime as dt
import functools
import os

from paths import PAN_DIR_DATA

import logging
logger = logging.getLogger(__name__)

# the operational file is kept up to date, the copy in DATA/ is a static fallback
WLK_FILES = ["/modelle/prod/mgruppe/ZAMG/ECMWF/WLK/WLK.txt", os.path.join(PAN_DIR_DATA, "WLK.txt")]

REGIME_NAMES = ["NE", "SE", "SW", "NW", "weak_gradient"]
# cyclonality letters and the values they are stored as
CYCLONALITY = {"A": 0, "C": 1}
CYCLONALITY_NAMES = ["anticyclonic", "cyclonic"]


def wlk_file(path=None):
    """ The WLK file to use: path if given, otherwise the first existing file of WLK_FILES """
    if path:
        return path
    return next((candidate for candidate in WLK_FILES if os.path.exists(candidate)), WLK_FILES[-1])


@functools.lru_cache(maxsize=None)
def read_wlk(path):
    """ Classification of each day in the WLK file as {date: (regime, cyclonality 925, cyclonality 500)}.
    An empty dict if the file does not exist. """
    if not os.path.exists(path):
        logger.warning(f"Weather regime file {path} not found, no weather regimes are stored with the scores")
        return {}
    logger.info(f"Reading weather regimes from {path}")
    days = {}
    with open(path) as wlk:
        for line_number, line in enumerate(wlk, 1):
            columns = line.split()
            if not columns:
                continue
            try:
                date = dt.datetime.strptime(columns[0], "%Y%m%d").date()
                code = columns[1]
                regime = int(code[:2])
                if not 0 <= regime < len(REGIME_NAMES):
                    raise ValueError(f"unknown regime {regime}")
                classification = (regime, CYCLONALITY[code[2]], CYCLONALITY[code[3]])
                if days.get(date, classification) != classification:
                    logger.warning(f"{path}:{line_number}: {date} is classified differently than before, "
                                   f"the last classification is used")
                days[date] = classification
            except (IndexError, KeyError, ValueError) as err:
                logger.warning(f"{path}:{line_number}: cannot parse weather regime ({err!r}), line skipped")
    return days


def regime_date(start_date, end_date):
    """ The day an accumulation window is classified by, None if the window extends over
    more than one day. The WLK classification is valid for 12 UTC, so it is used for windows
    within 00 - 24 UTC of that day. """
    date = start_date.date()
    day_end = dt.datetime.combine(date, dt.time()) + dt.timedelta(days=1)
    return date if end_date <= day_end else None


def weather_regime(start_date, end_date, path=None):
    """ Day and classification (regime, cyclonality 925, cyclonality 500) of an accumulation
    window. The day is None if the window extends over more than one day, the classification
    is None then or if the day is not in the WLK file. path defaults to the first existing
    file of WLK_FILES """
    date = regime_date(start_date, end_date)
    if date is None:
        return None, None
    path = wlk_file(path)
    classification = read_wlk(path).get(date)
    if classification is None and read_wlk(path):
        logger.warning(f"No weather regime for {date} in {path}")
    return date, classification


def label(date, classification):
    """ Short description of a classification for plot titles, e.g. "NW, 925 hPa cycl., 500 hPa anticycl." """
    if date is None:
        return "several days, no weather regime"
    if classification is None:
        return "weather regime unknown"
    regime, cyclonality_925, cyclonality_500 = classification
    short = ["anticycl.", "cycl."]
    return f"{REGIME_NAMES[regime].replace('_', ' ')}, 925 hPa {short[cyclonality_925]}, 500 hPa {short[cyclonality_500]}"
