"""
Convert horizonline_ephem.json (JPL Horizons data fetched in a browser tab on ssd.jpl.nasa.gov)
into the per-site CSVs that score.py reads. Same data as fetch_ephemeris.py, different transport.

Usage: python import_browser_ephem.py horizonline_ephem.json --out data/ephem
"""
import argparse
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out", default="data/ephem")
args = ap.parse_args()

out = Path(args.out)
out.mkdir(parents=True, exist_ok=True)
for sid, bodies in json.loads(Path(args.src).read_text()).items():
    for body, d in bodies.items():
        assert len(d["az"]) == len(d["el"]), f"{sid} {body}: length mismatch"
        t0, step = datetime.fromisoformat(d["t0"]), timedelta(hours=d["step_h"])
        with open(out / f"{sid}_{body}.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["utc", "az_deg", "el_deg"])
            w.writerows(((t0 + i * step).strftime("%Y-%b-%d %H:%M"), a, e) for i, (a, e) in enumerate(zip(d["az"], d["el"])))
        print(f"{sid} {body}: {len(d['az'])} rows, el {min(d['el']):.2f}..{max(d['el']):.2f}")
