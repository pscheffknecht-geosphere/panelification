# GRIB Handle for precipitation
GRIB_indicators_arome = {
    'precip': {
        'A': [{ # components of precipitation on other files
             'indicatorOfParameter'       : 197,
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0},
            {'indicatorOfParameter'       : 198,
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0},
            {'indicatorOfParameter'       : 199,
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0}],
        'B': [{ # total precipitation in some files
             'indicatorOfParameter'       : 61,
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0}],
        'C': [{ # components of precipitation on other files
             'indicatorOfParameter'       : 181,
             'name'                       : 'Rain',
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0},
            {'indicatorOfParameter'       : 184,
             'name'                       : 'Snow',
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0},
            {'indicatorOfParameter'       : 201,
             'name'                       : 'Graupel',
             'indicatorOfTypeOfLevel'     : 'surface',
             'level'                      : 0}],
        },
    'hail': [
        {'indicatorOfParameter'       : 196,
         'indicatorOfTypeOfLevel'     : 'surface',}],
    'lightning': [
        {'indicatorOfParameter'       : 246,
         'indicatorOfTypeOfLevel'     : 'surface',
         'level'                      : 0}],
    'snow': [
        {'indicatorOfParameter'       : 197,
         'indicatorOfTypeOfLevel'     : 'surface',
         'level'                      : 0}],
    'temperature': [
        {'indicatorOfParameter'       : 197,
         'indicatorOfTypeOfLevel'     : 'surface',
         'level'                      : 0}],
    'sunshine': [
        {'indicatorOfParameter'       : 248,
         'indicatorOfTypeOfLevel'     : 'surface',
         'level'                      : 0}]

}

GRIB_indicators_ecmwf = {
    'precip': [{'shortName': 'tp'}],
    'sunshine': [{'shortName': 'sund'}]
}


GRIB_indicators_claef_members = {
    'precip': [
        {'indicatorOfParameter'       : 228,
         'indicatorOfTypeOfLevel'     : 1,}],
    'hail': [
        {'indicatorOfParameter'       : 82,
         'indicatorOfTypeOfLevel'     : 1,}],
    'lightning': [
        {'indicatorOfParameter'       : 83,
         'indicatorOfTypeOfLevel'     : 1,}]
}

# note that the grib handle for INCA plus is NOT a list!
GRIB_indicators_inca_plus = {
    'precip':
        {'parameterNumber' : 8,
         'typeOfGeneratingProcess' : 2,
         'forecastTime' : None}
}

GRIB_indicators = {
    'arome': GRIB_indicators_arome,
    'CY46_1250m_DHC': GRIB_indicators_arome,
    'CY46_500m_DHC': GRIB_indicators_arome,
    'CY46_DOWN': GRIB_indicators_arome,
    'CY46_DOWN_HYDRO': GRIB_indicators_arome,
    'CY46_DOWN_HYDRO_CPL': GRIB_indicators_arome,
    'GL2B': GRIB_indicators_arome,
    'GL6J': GRIB_indicators_arome,
    'GL7J': GRIB_indicators_arome,
    'OPER': GRIB_indicators_arome,
    'REF_CY46': GRIB_indicators_arome,
    'aromeruc': GRIB_indicators_arome,
    'claef-members': GRIB_indicators_claef_members,
    'ecmwf': GRIB_indicators_ecmwf,
    'inca_plus-fc': GRIB_indicators_inca_plus
}


# GRIB_indicators_alaro = [{
#      'indicatorOfParameter'       : 202,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 203,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 204,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 205,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0}]
# 
# GRIB_indicators_laef = [{
#      'indicatorOfParameter'       : 209,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 210,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 211,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0},
#     {'indicatorOfParameter'       : 212,
#      'indicatorOfTypeOfLevel'     : 1,
#      'level'                      : 0}]
# 
# GRIB_indicators_cosmo = [{
#      # 'typeOfLevel:'               : 'surface',
#      #'level:'                     : 0
#      'parameterNumber'            : 52
#      #'shortNameECMF:'                 : 'tp'
#      }]
# 
# GRIB_indicators_cosmod2 = [{
#      #'typeOfLevel:'               : 'surface',
