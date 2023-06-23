# DEFINE REGIONS FOR PLOTTING
import cartopy.crs as ccrs
import pyproj
import numpy as np
import pyresample 
import logging

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

logger = logging.getLogger(__name__)

# set default thresholds for scoring and drawing, in case the user does not set them
default_thresholds =  {'draw_avg' : 2., 'draw_max' : 25., 'score_avg' : 1., 'score_max' : 5. }

regions = {
    "Europe": {
        "central_longitude": 15.,
        "central_latitude": 45.,
        "extent": [-10., 40., 35., 70.],
        "verification_subdomains": {
            "Default": [-5, 35., 35., 65.]
        }
    },
    "Austria": {
        "central_longitude": 15.,
        "central_latitude": 48.3,
        "extent": [9., 17.5, 45.5, 51.],
        "verification_subdomains": {
            "Default": [9.33, 17.33, 46.2, 49.2],
            "Vienna" : [16., 16.66, 48., 48.4],
            "Lower_Austria" : [14.33, 17.33, 47.4, 49.2],
            "Upper_Austria" : [12.66, 15., 47.4, 49.],
            "Salzburg" : [12., 14.3, 46.8, 48.2],
            "Tyrol" : [10., 13., 46.6, 48.2],
            "Vorarlberg" : [9.33, 10.33, 46.8, 47.8],
            "Carinthia" : [12.66, 15.33, 46.2, 47.2],
            "Styria" : [13.33, 16.33, 46.2, 48.],
            "Burgenland" : [16., 17.33, 46.6, 48.2],
            "East_Tyrol" : [12., 13., 46.6, 47.2],
            "Wechsel" : [15.58, 16.24, 47.30, 47.76],
            "Nockberge" : [13.85, 14.51, 46.75, 47,21],
            "Kitzbuehel" : [12.10, 12.76, 47.24, 47.70],
        }
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


    def __make_grid(self, subdomain):
        """ Use pyproj to generate a rectangular 1-km-grid on a steregraphic projection
        with given center and dimensions in km (grid points) in each direction"""
        proj_string = "epsg:31287 +proj=stere +units=km +lon_0={:.3f} lat_0={:.3f}".format(
                subdomain["central_longitude"], subdomain["central_latitude"])
        myproj=pyproj.Proj(proj_string)
        NX = subdomain["x_size"]
        NY = subdomain["y_size"]
        X = np.arange(NX) - subdomain["x_size"] / 2.
        Y = np.arange(NY) - subdomain["x_size"] / 2 
        XX, YY = np.meshgrid(X, Y)
        lon,lat=myproj(XX, YY, inverse=True)
        return lon, lat

    def __prep_subdomains(self, region_name, subdomain_name_list):
        self.subdomains = {}
        for subdomain_name in subdomain_name_list:
        #for key, item in subdomain_name_list.items():
            lon, lat = self.__make_grid(regions[region_name]["verification_subdomains"][subdomain_name])
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
        data_resampled =  pyresample.kd_tree.resample_gauss(
            orig_def, data, targ_def, 
            radius_of_influence=25000, neighbours=20,
            sigmas=250000, fill_value=None)
        if np.isnan(data_resampled).sum() > 0:
            if fix_nans:
                logging.warning("--fix_nans is set to True, replaced {:d} NaNs with 0.!".format(
                    np.isnan(data_resampled).sum()))
                data_resampled = np.where(np.isnan(data_resampled), 0., data_resampled)
            else:
                logging.warning("""Your resampled data contains missing values! you can use --fix_nans to set them to 0., but this can change scores!""")
        return data_resampled, self.subdomains[subdomain_name]["lon"], self.subdomains[subdomain_name]["lat"]
        

