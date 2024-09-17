import logging
logger = logging.getLogger(__name__)

# since different models may use different grib handles for the same variable, this code
# goes through a number of known used handles and checks if it succeeds in reading them from
# the file. Returns the handles as dictionary, if successful.

def check_precip_fields(grb):
    """Try a number of known passible grib handles that can be used to store precipitation
    in grib files. Return a list of valid handles if found"""
    try:
        grb.select(shortName='twatp')
        grb.select(shortName='tsnowp')
        return [{"shortName": "twatp"},
                {"shortName": "tsnowp"}]
    except:
        pass
    try:
        grb.select(parameterNumber=8)
        return [{"parameterNumber": 8}]
    except:
        pass
    try:
        grb.select(shortName='tp')
        return [{"shortName": "tp"}]
    except:
        pass
    try:
        grb.select(indicatorOfParameter=197) #, indicatorOfTypeOfLevel=1, level=0)
        grb.select(indicatorOfParameter=198) #, indicatorOfTypeOfLevel=1, level=0)
        grb.select(indicatorOfParameter=199) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 197}, #, "indicatorOfTypeOfLevel": 1, "level": 0},
            {"indicatorOfParameter": 198}, #, "indicatorOfTypeOfLevel": 1, "level": 0},
            {"indicatorOfParameter": 199}] #, "indicatorOfTypeOfLevel": 1, "level": 0}]
    except:
        pass
    try:
        grb.select(parameterNumber=65)
        grb.select(parameterNumber=66)
        grb.select(parameterNumber=75)
        return [
            {"parameterNumber": 65},
            {"parameterNumber": 66},
            {"parameterNumber": 75}]
    except:
        pass
    try:
        grb.select(parameterNumber=55)
        grb.select(parameterNumber=56)
        grb.select(parameterNumber=76)
        grb.select(parameterNumber=77)
        return [
            {"parameterNumber": 55},
            {"parameterNumber": 56},
            {"parameterNumber": 76},
            {"parameterNumber": 77}]
    except:
        pass
    try:
        grb.select(shortName="RAIN_CON")
        grb.select(shortName="RAIN_GSP")
        grb.select(shortName="SNOW_CON")
        grb.select(shortName="SNOW_GSP")
    except:
        pass
    return None


def check_gust_fields(grb):
    try:
        logger.debug("trying indicatorOfParamter 130 and 131")
        grb.select(indicatorOfParameter=130) #, indicatorOfTypeOfLevel=1, level=0)
        grb.select(indicatorOfParameter=131) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 130}, #, "indicatorOfTypeOfLevel": 1, "level": 0},
            {"indicatorOfParameter": 131}] #, "indicatorOfTypeOfLevel": 1, "level": 0},
    except:
        logger.debug("Failed to find 130 and 131")
        raise
    return None


def check_hail_fields(grb):
    try:
        logger.debug("trying indicatorOfParamter 82")
        grb.select(indicatorOfParameter=82) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 82}] #, "indicatorOfTypeOfLevel": 1, "level": 0},
    except:
        pass
    try:
        logger.debug("trying indicatorOfParamter 196")
        grb.select(indicatorOfParameter=196) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 196}] #, "indicatorOfTypeOfLevel": 1, "level": 0},
    except:
        logger.debug("Failed to find 196")
        raise
    return None


def check_sunshine_fields(grb):
    try:
        logger.debug("trying indicatorOfParamter 248")
        grb.select(indicatorOfParameter=248) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 248}] #, "indicatorOfTypeOfLevel": 1, "level": 0},
    except:
        logger.debug("Failed to find 248")
        raise
    return None


def check_lightning_fields(grb):
    try:
        logger.debug("trying indicatorOfParamter 246")
        grb.select(indicatorOfParameter=246) #, indicatorOfTypeOfLevel=1, level=0)
        return [
            {"indicatorOfParameter": 246}] #, "indicatorOfTypeOfLevel": 1, "level": 0},
    except:
        logger.debug("Failed to find 246")
        raise
    return None

# factory for grib field checks
def find_grib_handles(grb, param):
    check_function = {
        'precip': check_precip_fields,
        'precip2': check_precip_fields,
        'precip3': check_precip_fields,
        'sunshine': check_sunshine_fields,
        'hail': check_hail_fields,
        'lightning': check_lightning_fields,
        'gusts': check_gust_fields
    }
    ret = check_function[param](grb)
    if not ret:
        logger.critical(f"Fields not found in grib file for variable {param}, exiting...")
        exit()
    return ret
