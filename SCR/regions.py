# DEFINE REGIONS FOR PLOTTING
import os
import cartopy.crs as ccrs
import pyproj
import numpy as np
import pyresample 
import pickle
from math import sin, cos, sqrt, atan2, radians

# ADD YOUR REGION HERE
# example:
# "My Country": {
#     "central_longitude": float: center of projection,
#     "central_latitude": float, center of projection,
#     "extent": floats [lon_min, lon_max, lat_min, lat_max]
#     "verification_subdomain": dict of subdomains
#
# SUBDOMAIN DEFINITION
#
# The verification subdomain is given by providing
# central_longitude ...... float, center of the verification subdomain in EW direction
# central_latitude ....... float, center of the verification subdomain in NS direction
# x_size ................. float, width of the verification subdoain along EW in km
# y_size ................. float, width of the verification subdoain along NS in km
#
# the Region class will use pyproj and numpy to generate a lon lat grid with
# a grid spacing of 1 km, centered over central_longitude and central_latitude

import logging
logger = logging.getLogger(__name__)

# set default thresholds for scoring and drawing, in case the user does not set them
default_thresholds =  {'draw_avg' : 2., 'draw_max' : 25., 'score_avg' : 1., 'score_max' : 5. }

logger.info("Yeah, it's working here")
regions = {
    "Europe": {
        "central_longitude": 15.,
        "central_latitude": 45.,
        "extent": [-10., 40., 35., 70.],
        "verification_subdomains": {
            "Default": {
                "central_longitude": 20., "central_latitude": 52.5,
                "x_size": 1500, "y_size": 1500}
        }
    },
    "Alps": {
        "central_longitude": 9.,
        "central_latitude": 45.,
        "extent": [3., 19., 43., 49.5],
        "verification_subdomains": {
            "Default": {
                "central_longitude": 9., "central_latitude": 46.25,
                "x_size": 1000, "y_size": 500}
        }
    },
    "Austria": {
        "central_longitude": 13.,
        "central_latitude": 48.3,
        "extent": [9., 17.5, 46., 49.4],
        "verification_subdomains": {
            "Default": {
                "central_longitude": 13.25,
                "central_latitude": 47.7,
                "x_size": 600., "y_size": 325.},
            "Lower_Austria": {
                "central_longitude": 15.83, "central_latitude": 48.31,
                "x_size": 222., "y_size": 200.},
            "Carinthia": {
                'central_longitude': 14.00, 'central_latitude': 46.7, 
                'x_size': 210, 'y_size': 111},
            "Styria": {
                'central_longitude': 14.83, 'central_latitude': 47.1, 
                'x_size': 221, 'y_size': 200},
            "Vienna": {
                'central_longitude': 16.33, 'central_latitude': 48.20,
                'x_size': 40, 'y_size': 40},
            "Upper_Austria": {
                'central_longitude': 13.83, 'central_latitude': 48.2, 
                'x_size': 171, 'y_size': 178},
            "Salzburg": {
                'central_longitude': 13.15, 'central_latitude': 47.5, 
                'x_size': 173, 'y_size': 156},
            "Tyrol": {
                'central_longitude': 11.5, 'central_latitude': 47.2, 
                'x_size': 227, 'y_size': 133},
            "Vorarlberg": {
                'central_longitude': 9.83, 'central_latitude': 47.3, 
                'x_size': 75, 'y_size': 111},
            "NorthWest": {
                'central_longitude': 12.165, 'central_latitude': 47.75, 
                'x_size': 424, 'y_size': 167},
            "SouthEast": {
                'central_longitude': 15.165, 'central_latitude': 46.85, 
                'x_size': 279, 'y_size': 145},
            "West": {
                'central_longitude': 11.25, 'central_latitude': 47.45,
                'x_size': 338, 'y_size': 234},
            "O_KTN": {
                'central_longitude': 13.5, 'central_latitude': 46.7, 
                'x_size': 180, 'y_size': 90},
            "U_KTN": {
                'central_longitude': 14.5, 'central_latitude': 46.7, 
                'x_size': 180, 'y_size': 90},
            "SO_STMK": {
                'central_longitude': 15.5, 'central_latitude': 46.85, 
                'x_size': 180, 'y_size': 100},
            },
            # "Vienna" :        [16.,   16.66, 48., 4 8.4],
            # "Lower_Austria" : [14.33, 17.33, 47.4,  49.2],
            # "Upper_Austria" : [12.66, 15.,   47.4,  49.],
            # "Salzburg" :      [12.,   14.3,  46.8,  48.2],
            # "Tyrol" :         [10.,   13.,   46.6,  48.2],
            # "Vorarlberg" :    [9.33,  10.33, 46.8,  47.8],
            # "Carinthia" :     [12.66, 15.33, 46.2,  47.2],
            # "Styria" :        [13.33, 16.33, 46.2,  48.],
            # "Burgenland" :    [16.,   17.33, 46.6,  48.2],
            # "East_Tyrol" :    [12.,   13.,   46.6,  47.2],
            # "Wechsel" :       [15.58, 16.24, 47.30, 47.76],
            # "Nockberge" :     [13.85, 14.51, 46.75, 47,21],
            # "Kitzbuehel" :    [12.10, 12.76, 47.24, 47.70],
    },
    "Austria_East": {
        "central_longitude": 14.25,
        "central_latitude": 48.3,
        "extent": [13., 17.5, 46., 49.4],
        "verification_subdomains": {
            "Default": {
                "central_longitude": 14.25,
                "central_latitude": 47.7,
                "x_size": 300., "y_size": 325.}
        },
    },
    # for the Finland 2017 case, south of Finland only
    "Finland": {
        "central_longitude": 24.5,
        "central_latitude" : 61.,
        "extent": [20.0, 30.0, 58.50, 62.0],
        "verification_subdomains": {
            "Default": {
                "central_longitude": 25.,
                "central_latitude": 60.25,
                "x_size": 500.,
                "y_size": 300.,
                "thresholds": {'draw_avg' : 2., 'draw_max' : 25., 'score_avg' : 1., 'score_max' : 5.},
            },
            "Finland_Small": {
                # works for the small 200m domain
                "central_longitude": 25.5, "central_latitude": 60.35, "x_size": 220., "y_size": 220.
            }
        }
    }
}



class Region():
    def __init__(self, region_name="Europe", subdomains=["Default"]):
        self.name = region_name
        self.extent=regions[region_name]['extent']
        self.data_projection = ccrs.PlateCarree()
        self.plot_rojection = None
        self.__set_projection(region_name)
        self.__prep_subdomains(region_name, subdomains)

    def __set_projection(self, region_name="Europe"):
        self.plot_projection = ccrs.LambertConformal(
            central_longitude = regions[region_name]['central_longitude'],
            central_latitude = regions[region_name]['central_latitude'])

    # currently unused
    # def __set_custom_projection(self, clon, clat):
    #     self.plot_projection = ccrs.LambertConformal(
    #         central_longitude = clon,
    #         central_latitude = clat)


    def __make_grid(self, subdomain_data, k=1.):
        """ Use pyproj to generate a rectangular 1-km-grid on a steregraphic projection
        with given center and dimensions in km (grid points) in each direction"""
        proj_string = "epsg:31287 +proj=stere +units=km +lon_0={:.8f} lat_0={:.8f} k={:.8f}".format(
                subdomain_data["central_longitude"], subdomain_data["central_latitude"], k)
        myproj=pyproj.Proj(proj_string)
        NX = subdomain_data["x_size"]
        NY = subdomain_data["y_size"]
        X = np.arange(NX) - subdomain_data["x_size"] / 2.
        Y = np.arange(NY) - subdomain_data["y_size"] / 2.
        XX, YY = np.meshgrid(X, Y)
        lon,lat=myproj(XX, YY, inverse=True)
        return lon, lat

    def __prep_subdomains(self, region_name, subdomain_name_list):
        self.subdomains = {}
        for subdomain_name in subdomain_name_list:
            logger.info("Preparing subdomain {:s}".format(subdomain_name))
            k = self.__get_scale_factor(regions[region_name]["verification_subdomains"][subdomain_name])
            lon, lat = self.__make_grid(regions[region_name]["verification_subdomains"][subdomain_name], k=k)
            if "thresholds" in regions[region_name]["verification_subdomains"][subdomain_name].keys():
                thresholds = regions[region_name]["verification_subdomains"][subdomain_name]["thresholds"]
            else:
                thresholds = default_thresholds
            self.subdomains[subdomain_name] = {
                "name": subdomain_name,
                "lon": lon,
                "lat": lat,
                "thresholds": thresholds}

          
    def resample_to_subdomain(self, data, lon, lat, subdomain_name, fix_nans=False):
        logger.info("Resampling onto subdomain {:s} requested".format(
            subdomain_name))
        targ_def = pyresample.geometry.SwathDefinition(
            lons = self.subdomains[subdomain_name]["lon"],
            lats = self.subdomains[subdomain_name]["lat"])
        orig_def = pyresample.geometry.SwathDefinition(
            lons=lon, lats=lat)
        data_resampled =  pyresample.kd_tree.resample_nearest(
            orig_def, data, targ_def, reduce_data=False,
            radius_of_influence=25000.)
        data_resampled = np.where(data_resampled > 9999., np.nan, data_resampled)
        if np.isnan(data_resampled).sum() > 0:
            if fix_nans:
                logging.warning("--fix_nans is set to True, replaced {:d} NaNs with 0.!".format(
                    np.isnan(data_resampled).sum()))
                data_resampled = np.where(np.isnan(data_resampled), 0., data_resampled)
            else:
                logging.warning("""Your resampled data contains missing values! you can use --fix_nans to set them to 0., but this can change scores!""")
        return data_resampled, self.subdomains[subdomain_name]["lon"], self.subdomains[subdomain_name]["lat"]


    def __make_subdomain_key(self, subdomain_data):
        key_str = "{:.8f}_{:.8f}__{:.8f}_{:.8f}".format(
                subdomain_data["central_longitude"],
                subdomain_data["central_latitude"],
                subdomain_data["x_size"],
                subdomain_data["y_size"])
        logger.info("Current subdomain: {:s}".format(key_str))
        logger.info("Current subdomain key: {:s}".format(key_str))
        return key_str


    def __calcualte_distance_on_globe(self, lon1, lat1, lon2, lat2):
        # Approximate radius of earth in km
        R = 6373.0
        d = np.zeros(lon1.shape)
        imax, jmax = lon1.shape
        for ii in range(imax):
            for jj in range(jmax):
                dlon = radians(lon2[ii, jj]) - radians(lon1[ii, jj])
                dlat = radians(lat2[ii, jj]) - radians(lat1[ii, jj])

                a = sin(dlat / 2)**2 + cos(radians(lat1[ii, jj])) * cos(radians(lat2[ii, jj])) * sin(dlon / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                d[ii, jj] = R * c
        return d

    def __calculate_grid_error(self, arr, val, score="bias"):
        """ return score for array and constant val, only bias working"""
        if score.lower() == "bias":
            return np.mean(arr - val)
        #elif score.lower() == "mae":
        #    return np.mean(np.abs(arr-val))
        #elif score.lower() == "rmse":
        #    return np.sqrt(np.mean(np.square(np.abs(arr-val))))
        

    def __calculate_optimal_k(self, subdomain_data):
        nx = subdomain_data["x_size"]
        ny = subdomain_data["y_size"]
        d = 1.
        k = 1.0
        kstep = 0.01
        ksteps = []
        ds = [1e20]
        score = "bias"
        maxiter = 50
        logger.info(" Optimizing k for selected projection parameters, maximum {:d} iterations:".format(maxiter))
        for ii in range(maxiter):
            if ii > 2:
                if np.abs(ds[-1] - ds[-2]) < 0.0000001 or np.abs(ds[-1]) < 0.0000001:
                    # either the last iteration had very little impact or the last score was great
                    break
                kstep = kstep * 0.5 if np.abs(ds[-1]) < np.abs(ds[-2]) else -0.5 * kstep
                k += kstep
            else:
                k += 0.1 * kstep # do a small step to get directions first
            lon2, lat2 = self.__make_grid(subdomain_data, k=k)
            xend, yend = lon2.shape
            distance21 = self.__calcualte_distance_on_globe(lon2[0:xend-2, :], lat2[0:xend-2, :], lon2[1:xend-1, :], lat2[1:xend-1, :])
            distance22 = self.__calcualte_distance_on_globe(lon2[:, 0:yend-2], lat2[:, 0:yend-2], lon2[:, 1:yend-1], lat2[:, 1:yend-1])
            dbias = 0.5 * (np.mean(distance21) + np.mean(distance22))
            dist_err = 0.5 * (self.__calculate_grid_error(distance21, d, score=score) +
                              self.__calculate_grid_error(distance22, d, score=score))
            logger.info("  N = {:d}, k = {:.10f}, {:s} = {:.10f}".format(ii, k, score, dist_err))
            ksteps.append(kstep)
            ds.append(dist_err)
        
        logger.info(" Using k = {:.10f} for projection.".format(k))
        return k


    def __get_scale_factor(self, subdomain_data):
        current_key = self.__make_subdomain_key(subdomain_data)
        if os.path.isfile("subdomain_scale_factors.p"):
            with open("subdomain_scale_factors.p", "rb") as f:
                scale_factor_dict = pickle.load(f)
        else:
            logger.info("No stored scale factors found, the current one will be the first stored in the new file")
            scale_factor_dict = {}
        if current_key in scale_factor_dict.keys():
            logger.info("Scale factor found: k = {:.8f}".format(scale_factor_dict[current_key]))
            return scale_factor_dict[current_key]
        else:
            logger.info("No scale factor found for current subdomain, calculating new one...")
            scale_factor = self.__calculate_optimal_k(subdomain_data)
            logger.info("Updating scale factor dictionary with current key:")
            logger.info(repr({current_key: scale_factor}))
            scale_factor_dict[current_key] = scale_factor
            logger.info("Updating scale factor pickle file.")
            with open("subdomain_scale_factors.p", "wb") as f:
                pickle.dump(scale_factor_dict, f)
            return scale_factor


