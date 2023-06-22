# DEFINE REGIONS FOR PLOTTING
import cartopy.crs as ccrs

# ADD YOUR REGION HERE
# example:
# "My Country": {
#     "central_longitude": float: center of projection,
#     "central_latitude": float, center of projection,
#     "extent": floats [lon_min, lon_max, lat_min, lat_max]
#     "verification_subdomain": dict of subdomains using the extent
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
            "Default": [23.0, 28.0, 59.00, 61.50]
        }
    }
}

class Region():
    def __init__(self, region_name="Europe"):
        self.extent=regions[region_name]['extent']
        self.data_projection = ccrs.PlateCarree()
        self.plot_rojection = None
        self.set_projection(region_name)
        print(regions[region_name])
        self.verification_subdomains = regions[region_name]['verification_subdomains']

    def set_projection(self, region_name="Europe"):
        self.plot_projection = ccrs.LambertConformal(
            central_longitude = regions[region_name]['central_longitude'],
            central_latitude = regions[region_name]['central_latitude'])

    def set_custom_projection(self, clon, clat):
        self.plot_projection = ccrs.LambertConformal(
            central_longitude = clon,
            central_latitude = clat)
