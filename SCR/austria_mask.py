"""Mask resampled fields to the area inside Austria.

This is a self-contained experiment module. It reads the Austria country
outline (WGS84 lon/lat) from a bundled shapefile and sets every resampled
grid point that lies outside the polygon to NaN. The only entry point used
by the rest of the code base is :func:`mask_data_list_to_austria`, which is
called once after resampling in ``main.py``.
"""

import logging
import os

import numpy as np
import shapefile
from shapely import contains_xy
from shapely.geometry import shape

_SHAPEFILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "aux_data", "austria", "AUT_adm0.shp")

# Cache the (possibly expensive to build) polygon so it is loaded only once.
_austria_polygon = None


def _get_austria_polygon():
    """Load and cache the Austria outline as a single shapely geometry."""
    global _austria_polygon
    if _austria_polygon is None:
        reader = shapefile.Reader(_SHAPEFILE)
        geom = shape(reader.shape(0).__geo_interface__)
        if not geom.is_valid:
            # The bundled outline is not topologically clean; buffer(0) is the
            # standard trick to repair self-intersections without moving the
            # boundary appreciably.
            geom = geom.buffer(0)
        _austria_polygon = geom
        logging.info("Loaded Austria mask polygon from %s", _SHAPEFILE)
    return _austria_polygon


def mask_field_to_austria(lon, lat, field):
    """Return a copy of `field` with points outside Austria set to NaN.

    `lon`, `lat` and `field` are 2D numpy arrays sharing the same shape.
    """
    polygon = _get_austria_polygon()
    inside = contains_xy(polygon, lon, lat)
    masked = field.astype(float, copy=True)
    masked[~inside] = np.nan
    return masked


def mask_data_list_to_austria(data_list):
    """Mask the resampled precipitation of every entry to inside Austria.

    Operates in place on the ``precip_data_resampled`` field of each entry in
    `data_list`, using the matching ``lon_resampled``/``lat_resampled`` grids.
    """
    for entry in data_list:
        entry["precip_data_resampled"] = mask_field_to_austria(
            entry["lon_resampled"],
            entry["lat_resampled"],
            entry["precip_data_resampled"])
    logging.info("Masked %d resampled fields to inside Austria", len(data_list))
