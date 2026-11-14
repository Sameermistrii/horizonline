"""
HorizonLine - compute the terrain horizon (360 deg) around each lunar site from a LOLA DEM.

AI disclosure: written with assistance from Claude (Anthropic) during NASA Space Apps 2026.
Data: NASA LRO/LOLA DEM (NASA GSFC Planetary Geodynamics Data Archive, pgda.gsfc.nasa.gov).

Method: for each azimuth, march outward over the DEM and keep the highest elevation angle,
correcting for lunar curvature (the published horizon-mask method, e.g. NTRS 20150014706).

Usage:
    python horizon.py <dem.tif> sites.json --out data/horizons
"""
import argparse
import json
from pathlib import Path

import numpy as np

R_MOON = 1737400.0  # m, LOLA reference sphere


def destination(lat_deg, lon_deg, az_deg, dist_m):
    """Spherical forward problem: points at dist_m along bearing az_deg (clockwise from north)."""
    lat1, lon1 = np.radians(lat_deg), np.radians(lon_deg)
    az, d = np.radians(az_deg), dist_m / R_MOON
    lat2 = np.arcsin(np.sin(lat1) * np.cos(d) + np.cos(lat1) * np.sin(d) * np.cos(az))
    lon2 = lon1 + np.arctan2(np.sin(az) * np.sin(d) * np.cos(lat1), np.cos(d) - np.sin(lat1) * np.sin(lat2))
    return np.degrees(lat2), np.degrees(lon2)


def horizon_profile(height_at, lat, lon, h_obs, az_deg, dists):
    """
    height_at(lat, lon) -> terrain height (m, NaN outside the DEM).
    Returns max elevation angle (deg) of the terrain for every azimuth in az_deg.
    """
    A, D = np.meshgrid(az_deg, dists, indexing="ij")          # (n_az, n_dist)
    plat, plon = destination(lat, lon, A, D)
    h = height_at(plat, plon)
    # angle of a point at height h, distance d (arc), seen from radius R+h_obs on a sphere
    theta = D / R_MOON
    r_obs, r_pt = R_MOON + h_obs, R_MOON + h
    x = r_pt * np.sin(theta)
    z = r_pt * np.cos(theta) - r_obs
    ang = np.degrees(np.arctan2(z, x))
    ang = np.where(np.isnan(ang), -90.0, ang)
    return ang.max(axis=1)


def main():
    import rasterio
    from pyproj import CRS, Transformer
    from scipy.ndimage import map_coordinates

    ap = argparse.ArgumentParser()
    ap.add_argument("dem")
    ap.add_argument("sites")
    ap.add_argument("--out", default="data/horizons")
    ap.add_argument("--max-km", type=float, default=300.0)
    ap.add_argument("--az-step", type=float, default=0.5)
    args = ap.parse_args()

    with rasterio.open(args.dem) as src:
        z = src.read(1).astype("float32")
        if src.nodata is not None:
            z[z == src.nodata] = np.nan
        inv = ~src.transform
        dem_crs = src.crs
        px = abs(src.transform.a)
        scale = src.scales[0] if src.scales else 1.0
        offset = src.offsets[0] if src.offsets else 0.0
    z = z * scale + offset
    print(f"DEM {z.shape}, {px:.0f} m/px, height {np.nanmin(z):.0f}..{np.nanmax(z):.0f} m")

    # shortcut: assumes the DEM's projection is on the 1737.4 km sphere (true for PGDA LOLA products)
    geo = CRS.from_proj4(f"+proj=longlat +R={R_MOON} +no_defs")
    to_xy = Transformer.from_crs(geo, CRS.from_user_input(dem_crs), always_xy=True)

    def height_at(lat, lon):
        x, y = to_xy.transform(lon, lat)
        col, row = inv * (np.asarray(x), np.asarray(y))
        return map_coordinates(z, [row - 0.5, col - 0.5], order=1, mode="constant", cval=np.nan)

    az = np.arange(0.0, 360.0, args.az_step)
    dists = np.geomspace(2 * px, args.max_km * 1000.0, 2500)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for s in json.loads(Path(args.sites).read_text())["sites"]:
        if s.get("lat") is None:
            print(f"skip {s['id']}: no coordinates yet")
            continue
        ground = float(height_at(np.array([s["lat"]]), np.array([s["lon"]]))[0])
        if np.isnan(ground):
            print(f"skip {s['id']}: outside DEM")
            continue
        h_obs = ground + s.get("height_m", 2)
        hz = horizon_profile(height_at, s["lat"], s["lon"], h_obs, az, dists)
        (out / f"{s['id']}.json").write_text(json.dumps({
            "id": s["id"], "ground_m": round(ground, 1),
            "az": az.round(2).tolist(), "el": hz.round(3).tolist(),
        }))
        print(f"{s['id']}: ground {ground:.0f} m, horizon {hz.min():.2f}..{hz.max():.2f} deg")


if __name__ == "__main__":
    main()
