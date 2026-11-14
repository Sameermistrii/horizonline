"""Convert USGS Artemis III region 1 km grid bounding boxes (LPS projection) to centre lat/lon."""
import json, sys
from pyproj import CRS, Transformer

# Projection from the USGS shapefile .prj (Moon 2015 sphere, south polar stereographic)
LPS = CRS.from_proj4("+proj=stere +lat_0=-90 +lon_0=0 +k=0.994 +x_0=500000 +y_0=500000 +R=1737400 +units=m +no_defs")
GEO = CRS.from_proj4("+proj=longlat +R=1737400 +no_defs")
inv = Transformer.from_crs(LPS, GEO, always_xy=True)

def centre(bbox):
    xmin, ymin, xmax, ymax = bbox
    lon, lat = inv.transform((xmin + xmax) / 2, (ymin + ymax) / 2)
    return round(lat, 4), round(lon, 4)

if __name__ == "__main__":
    for name, bbox in json.load(sys.stdin).items():
        print(name, centre(bbox), f"{(bbox[2]-bbox[0])/1000:.0f} x {(bbox[3]-bbox[1])/1000:.0f} km")
