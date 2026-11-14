"""
Science sanity checks on the real pipeline outputs (run after score.py).
1. Azimuth convention: Horizons' mean Earth azimuth must point at the sub-Earth point (0N, 0E)
   using the same bearing maths as horizon.py. A mirrored convention would be off by tens of degrees.
2. Sun elevation range must equal (90 - |lat|) + 1.54 deg (lunar obliquity to the ecliptic).
3. NASA picked these regions for >= 6.5 days of continuous sunlight; report the best such window.
"""
import json
import numpy as np
from pathlib import Path
from score import read_ephem, score

ok = True
for s in (s for s in json.loads(Path("sites.json").read_text())["sites"] if Path(f"data/ephem/{s['id']}_sun.csv").exists()):  # sites with per-site Horizons runs
    sid = s["id"]
    _, saz, sel = read_ephem(f"data/ephem/{sid}_sun.csv")
    _, eaz, eel = read_ephem(f"data/ephem/{sid}_earth.csv")
    p1, l1 = np.radians(s["lat"]), np.radians(s["lon"])
    bearing = np.degrees(np.arctan2(np.sin(-l1), -np.sin(p1) * np.cos(l1))) % 360  # great-circle bearing to (0, 0)
    mean_e = np.degrees(np.angle(np.exp(1j * np.radians(eaz)).mean())) % 360  # circular mean
    d_az = (mean_e - bearing + 180) % 360 - 180
    expect = 90 - abs(s["lat"]) + 1.54
    d_el = sel.max() - expect
    hz = json.loads(Path(f"data/horizons/{sid}.json").read_text())
    r = score(np.array(hz["az"]), np.array(hz["el"]), saz, sel, eaz, eel, 1.0)
    lit = r["sun_frac"] >= 0.5
    best, cur = 0, 0
    for v in lit:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    good = abs(d_az) < 3 and abs(d_el) < 0.15
    ok &= good
    print(f"{s['name']:20s} earth az {mean_e:6.1f} vs bearing {bearing:6.1f} (d {d_az:+.1f})  "
          f"sun max el {sel.max():.2f} vs {expect:.2f}  longest sunlight {best/24:5.1f} d  {'OK' if good else 'CHECK'}")
print("ALL OK" if ok else "SOME CHECKS FAILED")
