"""
HorizonLine - combine Sun/Earth sky paths with each site's terrain horizon into app-ready JSON.

AI disclosure: written with assistance from Claude (Anthropic) during NASA Space Apps 2026.

Usage:
    python score.py sites.json --ephem data/ephem --horizons data/horizons --out ../app/data
"""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

import numpy as np

SUN_RADIUS_DEG = 0.2666   # apparent solar disk radius from the Moon
SKY_EVERY = 3             # keep every 3rd sample of the sky paths for the panorama


def parse_time(s):
    for fmt in ("%Y-%b-%d %H:%M", "%Y-%b-%d %H:%M:%S", "%Y-%b-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    raise ValueError(f"unknown time format: {s!r}")


def read_ephem(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    t = [parse_time(r["utc"]) for r in rows]
    az = np.array([float(r["az_deg"]) for r in rows])
    el = np.array([float(r["el_deg"]) for r in rows])
    return t, az, el


def longest_run(mask):
    """Length of the longest run of True values."""
    best = cur = 0
    for m in mask:
        cur = cur + 1 if m else 0
        best = max(best, cur)
    return best


def score(hz_az, hz_el, sun_az, sun_el, earth_az, earth_el, step_h):
    sun_hz = np.interp(sun_az, hz_az, hz_el, period=360.0)
    earth_hz = np.interp(earth_az, hz_az, hz_el, period=360.0)
    # fraction of the solar disk above the terrain (linear approximation across the disk)
    sun_frac = np.clip((sun_el - sun_hz + SUN_RADIUS_DEG) / (2 * SUN_RADIUS_DEG), 0.0, 1.0)
    earth_up = earth_el > earth_hz
    return {
        "sun_frac": sun_frac,
        "earth_up": earth_up,
        "power_pct": round(float(sun_frac.mean() * 100), 1),
        "comms_pct": round(float(earth_up.mean() * 100), 1),
        "longest_dark_h": round(longest_run(sun_frac < 0.5) * step_h, 1),
        "longest_comms_gap_h": round(longest_run(~earth_up) * step_h, 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites")
    ap.add_argument("--ephem", default="data/ephem")
    ap.add_argument("--horizons", default="data/horizons")
    ap.add_argument("--out", default="../app/data")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "sites").mkdir(parents=True, exist_ok=True)
    index = []

    for s in json.loads(Path(args.sites).read_text())["sites"]:
        hz_path = Path(args.horizons) / f"{s['id']}.json"
        sun_path = Path(args.ephem) / f"{s['id']}_sun.csv"
        earth_path = Path(args.ephem) / f"{s['id']}_earth.csv"
        if not (hz_path.exists() and sun_path.exists() and earth_path.exists()):
            print(f"skip {s['id']}: missing horizon or ephemeris")
            continue
        hz = json.loads(hz_path.read_text())
        t, sun_az, sun_el = read_ephem(sun_path)
        t2, earth_az, earth_el = read_ephem(earth_path)
        assert t == t2, f"{s['id']}: Sun and Earth time steps differ"
        step_h = (t[1] - t[0]).total_seconds() / 3600.0

        r = score(np.array(hz["az"]), np.array(hz["el"]), sun_az, sun_el, earth_az, earth_el, step_h)

        days = {}
        for ti, f, e in zip(t, r["sun_frac"], r["earth_up"]):
            d = days.setdefault(ti.strftime("%Y-%m-%d"), [0.0, 0.0, 0])
            d[0] += f; d[1] += e; d[2] += 1
        daily = [{"date": k, "power": round(v[0] / v[2] * 100), "comms": round(v[1] / v[2] * 100)}
                 for k, v in sorted(days.items()) if v[2] * step_h >= 12]  # drop partial days (e.g. the closing midnight sample)

        summary = {k: r[k] for k in ("power_pct", "comms_pct", "longest_dark_h", "longest_comms_gap_h")}
        site = {
            "id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"],
            "ground_m": hz["ground_m"], "summary": summary,
            "horizon": {"az": hz["az"], "el": hz["el"]},
            "sky": {
                "t": [x.strftime("%Y-%m-%dT%H:%M") for x in t[::SKY_EVERY]],
                "sun": [sun_az[::SKY_EVERY].round(2).tolist(), sun_el[::SKY_EVERY].round(3).tolist()],
                "earth": [earth_az[::SKY_EVERY].round(2).tolist(), earth_el[::SKY_EVERY].round(3).tolist()],
            },
            "daily": daily,
        }
        (out / "sites" / f"{s['id']}.json").write_text(json.dumps(site, separators=(",", ":")))
        index.append({"id": s["id"], "name": s["name"], "lat": s["lat"], "lon": s["lon"], **summary})
        print(f"{s['id']}: power {summary['power_pct']}%  comms {summary['comms_pct']}%  "
              f"longest dark {summary['longest_dark_h']} h")

    (out / "index.json").write_text(json.dumps({"sites": index}, indent=1))
    print(f"wrote {len(index)} sites -> {out}")


if __name__ == "__main__":
    main()
