# DEFINE REGIONS FOR PLOTTING
import cartopy.crs as ccrs

regions = {
    "Europe": {
        "central_longitude": 15.,
        "central_latitude": 45.,
        "extent": [-10., 40., 35., 70.]},
    "Austria": {
        "central_longitude": 15.,
        "central_latitude": 48.3,
        "extent": [9., 17.5, 45.5, 51.]},
    # for the Finland 2017 case, south of Finland only
    "Finland": {
        "central_longitude": 24.5,
        "central_latitude" : 61.,
        "extent": [16.0, 31.0, 58.00, 63.0]}
    }

class Region():
    def __init__(self, region_name="Europe"):
        self.extent=regions[region_name]['extent']
        self.data_projection = ccrs.PlateCarree()
        self.plot_rojection = None
        self.set_projection(region_name)

    def set_projection(self, region_name="Europe"):
        self.plot_projection = ccrs.LambertConformal(
            central_longitude = regions[region_name]['central_longitude'],
            central_latitude = regions[region_name]['central_latitude'])

    def set_custom_projection(self, clon, clat):
        self.plot_projection = ccrs.LambertConformal(
            central_longitude = clon,
            central_latitude = clat)
