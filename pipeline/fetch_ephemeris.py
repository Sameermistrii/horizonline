"""
HorizonLine - fetch Sun and Earth sky positions for each lunar site from JPL Horizons.

AI disclosure: this script was written with assistance from Claude (Anthropic),
an AI assistant, during NASA Space Apps Challenge 2026.

Data source: NASA/JPL Horizons System, https://ssd.jpl.nasa.gov/horizons/

Usage:
    python fetch_ephemeris.py sites.json --start 2027-01-01 --stop 2028-01-01 --step "1 h"

Output (one pair per site):
    data/ephem/<site_id>_sun.csv
    data/ephem/<site_id>_earth.csv
    columns: utc, az_deg, el_deg   (azimuth clockwise from north, elevation above the
                                    local reference surface, NOT yet corrected for terrain)
"""
import argparse
import csv
import json
import time
from pathlib import Path

import requests

API = "https://ssd.jpl.nasa.gov/api/horizons.api"
BODIES = {"sun": "10", "earth": "399"}


def fetch(body_id, lon_e, lat, alt_km, start, stop, step):
    """Return [(utc, az_deg, el_deg), ...] for one body seen from one lunar surface point."""
    params = {
        "format": "json",
        "COMMAND": f"'{body_id}'",
        "OBJ_DATA": "'NO'",
        "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'",
        "CENTER": "'coord@301'",          # user-defined site on the Moon (body 301)
        "COORD_TYPE": "'GEODETIC'",
        "SITE_COORD": f"'{lon_e:.6f},{lat:.6f},{alt_km:.4f}'",  # E-longitude, latitude, height (km)
        "START_TIME": f"'{start}'",
        "STOP_TIME": f"'{stop}'",
        "STEP_SIZE": f"'{step}'",
        "QUANTITIES": "'4'",               # apparent azimuth & elevation
        "ANG_FORMAT": "'DEG'",
        "CSV_FORMAT": "'YES'",
    }
    r = requests.get(API, params=params, timeout=180)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    text = data["result"]
    if "$$SOE" not in text:
        raise RuntimeError("Horizons returned no ephemeris. First part of reply:\n" + text[:3000])

    body = text.split("$$SOE")[1].split("$$EOE")[0]
    rows = []
    for line in body.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        nums = []
        for p in parts[1:]:
            try:
                nums.append(float(p))
            except ValueError:
                pass  # empty columns and flag columns
        if len(nums) < 2:
            continue
        az, el = nums[-2], nums[-1]
        rows.append((parts[0], az, el))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sites", help="sites.json")
    ap.add_argument("--start", default="2027-01-01")
    ap.add_argument("--stop", default="2028-01-01")
    ap.add_argument("--step", default="1 h")
    ap.add_argument("--out", default="data/ephem")
    ap.add_argument("--only", help="comma-separated site ids to fetch (default: all)")
    args = ap.parse_args()

    sites = json.loads(Path(args.sites).read_text())["sites"]
    if args.only:
        keep = set(args.only.split(","))
        sites = [s for s in sites if s["id"] in keep]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for s in sites:
        if s.get("lat") is None or s.get("lon") is None:
            print(f"skip {s['id']}: no coordinates yet")
            continue
        lon_e = s["lon"] % 360.0
        alt_km = (s.get("height_m") or 0.0) / 1000.0
        for name, body_id in BODIES.items():
            print(f"{s['id']}: fetching {name} ...", flush=True)
            rows = fetch(body_id, lon_e, s["lat"], alt_km, args.start, args.stop, args.step)
            path = out / f"{s['id']}_{name}.csv"
            with path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["utc", "az_deg", "el_deg"])
                w.writerows(rows)
            els = [r[2] for r in rows]
            print(f"  {len(rows)} rows, elevation {min(els):.2f} to {max(els):.2f} deg -> {path}")
            time.sleep(1.0)  # be polite to the Horizons server


if __name__ == "__main__":
    main()
