"""Self-check for the horizon and scoring math on synthetic terrain. Run: python test_pipeline.py"""
import numpy as np

from horizon import R_MOON, destination, horizon_profile
from score import longest_run, score

# 1. destination(): 10 km due north from the equator lands at the expected latitude
lat, lon = destination(0.0, 0.0, 0.0, 10_000.0)
assert abs(lat - np.degrees(10_000 / R_MOON)) < 1e-9 and abs(lon) < 1e-9

# 2. A 1000 m ring wall 20 km away on a smooth sphere -> known horizon angle everywhere
ring_d, ring_h = 20_000.0, 1000.0
site_lat, site_lon = -88.0, 30.0

def height_at(plat, plon):
    # great-circle distance from the site
    a, b = np.radians(site_lat), np.radians(plat)
    dl = np.radians(plon - site_lon)
    d = R_MOON * np.arccos(np.clip(np.sin(a) * np.sin(b) + np.cos(a) * np.cos(b) * np.cos(dl), -1, 1))
    return np.where(np.abs(d - ring_d) < 300, ring_h, 0.0)

az = np.arange(0, 360, 5.0)
dists = np.geomspace(50, 60_000, 4000)
hz = horizon_profile(height_at, site_lat, site_lon, 2.0, az, dists)
theta = ring_d / R_MOON
expect = np.degrees(np.arctan2((R_MOON + ring_h) * np.cos(theta) - (R_MOON + 2), (R_MOON + ring_h) * np.sin(theta)))
assert np.all(np.abs(hz - expect) < 0.05), (hz.min(), hz.max(), expect)

# 3. Flat horizon at 0 deg, Sun bobbing +-1.5 deg -> about half the time lit
t = np.arange(24 * 365)
sun_el = 1.5 * np.sin(2 * np.pi * t / (29.53 * 24))
r = score(np.array([0, 180.0]), np.array([0, 0.0]), (t * 0.5) % 360, sun_el,
          (t * 0.5) % 360, np.full(t.shape, 5.0), 1.0)
assert 45 < r["power_pct"] < 55 and r["comms_pct"] == 100.0
assert 330 < r["longest_dark_h"] < 380  # about half a lunar day
assert longest_run([True, True, False, True]) == 2

print(f"all checks passed (ring horizon {hz.mean():.3f} deg, expected {expect:.3f})")
