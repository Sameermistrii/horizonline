"""Predict every site's Sun/Earth az/el from ONE reference site; compare with that site's own Horizons data."""
import json
import numpy as np
from score import read_ephem
from skyvec import body_position, azel_at

from pathlib import Path
sites = {s["id"]: s for s in json.load(open("sites.json"))["sites"] if Path(f"data/ephem/{s['id']}_sun.csv").exists()}
hz = {k: json.load(open(f"data/horizons/{k}.json"))["ground_m"] / 1000 for k in sites}
# Reference: the 3-year Horizons fetch (az/el + range) at de Gerlache Rim 2; first 8760 hours = 2027
d = json.load(open("data/horizonline_sky_2027_2029.json")); r = d["ref"]; k = 8760
sun = body_position(r["lat"], r["lon"], r["h_km"], np.array(d["sun"]["az"][:k]), np.array(d["sun"]["el"][:k]), np.array(d["sun"]["range_km"][:k]))
earth = body_position(r["lat"], r["lon"], r["h_km"], np.array(d["earth"]["az"][:k]), np.array(d["earth"]["el"][:k]), np.array(d["earth"]["range_km"][:k]))
worst = 0
for k, s in sites.items():
    _, tsaz, tsel = read_ephem(f"data/ephem/{k}_sun.csv"); tsaz, tsel = tsaz[:8760], tsel[:8760]
    _, teaz, teel = read_ephem(f"data/ephem/{k}_earth.csv"); teaz, teel = teaz[:8760], teel[:8760]
    pa, pe = azel_at(s["lat"], s["lon"], hz[k] + .002, sun)
    qa, qe = azel_at(s["lat"], s["lon"], hz[k] + .002, earth)
    d = lambda a, b: np.abs((a - b + 180) % 360 - 180)
    errs = [d(pa, tsaz).max(), np.abs(pe - tsel).max(), d(qa, teaz).max(), np.abs(qe - teel).max()]
    worst = max(worst, errs[1], errs[3])
    print(f"{s['name']:20s} sun az {errs[0]:.3f} el {errs[1]:.4f} | earth az {errs[2]:.3f} el {errs[3]:.4f} (max deg)")
print(f"worst elevation error {worst:.4f} deg")
