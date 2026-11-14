"""
Region bboxes (stdin JSON, USGS LPS metres) -> representative site per region, printed as JSON.
Site rule: the highest DEM point inside NASA's region box (rims and peaks get the most sunlight).
"""
import json, sys
import numpy as np
import rasterio
from pyproj import CRS, Transformer
from region_centers import LPS

GEO = CRS.from_proj4('+proj=longlat +R=1737400')
with rasterio.open('data/LDEM_80S_80MPP_ADJ.TIF') as s:
    z = s.read(1)
    lps_to_dem = Transformer.from_crs(LPS, s.crs, always_xy=True)
    dem_to_geo = Transformer.from_crs(s.crs, GEO, always_xy=True)
    out = {}
    for name, (x0, y0, x1, y1) in json.load(sys.stdin).items():
        X, Y = np.meshgrid(np.arange(x0, x1, 80), np.arange(y0, y1, 80))
        dx, dy = lps_to_dem.transform(X.ravel(), Y.ravel())
        rows, cols = rasterio.transform.rowcol(s.transform, dx, dy)
        h = z[np.asarray(rows), np.asarray(cols)]
        k = int(np.nanargmax(h))
        lon, lat = dem_to_geo.transform(dx[k], dy[k])
        out[name] = {"lat": round(lat, 4), "lon": round(lon, 4), "ground_m": round(float(h[k]), 1),
                     "box_median_m": round(float(np.nanmedian(h)), 0)}
print(json.dumps(out, indent=1))
