"""
Export everything the browser app needs into app/data/.

  sites.json   curated sites + 720-point terrain horizons (80 m LOLA), or a flat horizon outside the DEM
  sky.json     hourly Sun direction + Earth position in the Moon-fixed frame (from one Horizons reference site)
  terrain_near.png / terrain_far.png   heights as "terrain-RGB" PNGs for custom-site horizons in the browser
  map.png      hillshade of the south pole for the site map
  meta.json    grid geometry for the PNGs

AI disclosure: written with assistance from Claude (Anthropic) during NASA Space Apps 2026.
Usage: python export_web.py --sky horizonline_sky_2027_2029.json
"""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

from skyvec import R, body_position

DEM = "data/LDEM_80S_80MPP_ADJ.TIF"
OUT = Path("../app/data")
FLAT_DIP = -np.degrees(np.sqrt(2 * 0.002 / R))  # 2 m mast on a smooth sphere: horizon dips ~0.09 deg


def block(z, x0_m, half_m, px_in, factor):
    """Crop a square of +-half_m around the pole and block-average by factor. Returns grid + geometry."""
    i0 = int(round((-half_m - x0_m) / px_in))
    n_in = int(round(2 * half_m / px_in)) // factor * factor
    c = z[i0:i0 + n_in, i0:i0 + n_in]
    n = n_in // factor
    g = np.nanmean(c.reshape(n, factor, n, factor), axis=(1, 3))
    return g, {"x0": x0_m + i0 * px_in, "y0": -(x0_m + i0 * px_in), "px": px_in * factor, "n": n}


def terrain_png(g, path):
    v = np.clip(np.nan_to_num(g, nan=-32768) + 32768, 0, 65535).astype(np.uint32)
    rgb = np.stack([(v >> 8).astype(np.uint8), (v & 255).astype(np.uint8), np.zeros_like(v, np.uint8)], -1)
    Image.fromarray(rgb, "RGB").save(path, optimize=True)


def hillshade(g, px, az=315.0, alt=12.0):
    gy, gx = np.gradient(np.nan_to_num(g, nan=np.nanmean(g)), px)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, e = np.radians(az), np.radians(alt)
    s = np.sin(e) * np.cos(slope) + np.cos(e) * np.sin(slope) * np.cos(a - aspect)
    return (np.clip(s, 0, 1) ** 0.8 * 235 + 20).astype(np.uint8)


def export_sky(path):
    d = json.loads(Path(path).read_text())
    ref = d["ref"]
    out = {"t0": d["t0"], "step_h": d["step_h"], "source": d["source"]}
    for body in ("sun", "earth"):
        b = d[body]
        pos = body_position(ref["lat"], ref["lon"], ref["h_km"], np.array(b["az"]), np.array(b["el"]), np.array(b["range_km"]))
        if body == "sun":  # direction only; solar parallax across the Moon is < 0.001 deg
            out["sun"] = np.round(pos / np.linalg.norm(pos, axis=1, keepdims=True), 6).ravel().tolist()
        else:
            out["earth"] = np.round(pos, 1).ravel().tolist()
    out["n"] = len(d["sun"]["az"])
    (OUT / "sky.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"sky.json: {out['n']} hours from {out['t0']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sky", help="horizonline_sky_*.json from the Horizons browser fetch")
    ap.add_argument("--skip-terrain", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    sites = []
    for s in json.loads(Path("sites.json").read_text())["sites"]:
        hz = Path(f"data/horizons/{s['id']}.json")
        if s.get("flat"):
            el, ground, terrain = [round(FLAT_DIP, 3)] * 720, None, "none"
        elif hz.exists():
            h = json.loads(hz.read_text())
            assert len(h["el"]) == 720, s["id"]
            el, ground, terrain = h["el"], h["ground_m"], "LOLA 80 m"
        else:
            print("skip", s["id"]); continue
        sites.append({k: s.get(k) for k in ("id", "name", "group", "lat", "lon", "source")} |
                     {"mast_m": s.get("height_m", 2), "ground_m": ground, "terrain": terrain, "horizon": el})
    (OUT / "sites.json").write_text(json.dumps({"sites": sites}, separators=(",", ":")))
    print(f"sites.json: {len(sites)} sites")

    if not args.skip_terrain:
        with rasterio.open(DEM) as src:
            z = src.read(1).astype("float32")
            x0 = src.transform.c
            assert src.transform.a == 80 and src.transform.c == -src.transform.f
        near, gn = block(z, x0, 200_000, 80, 3)    # 240 m, +-200 km
        far, gf = block(z, x0, 300_000, 80, 12)    # 960 m, +-300 km
        mp, gm = block(z, x0, 210_000, 80, 5)      # 400 m map
        terrain_png(near, OUT / "terrain_near.png")
        terrain_png(far, OUT / "terrain_far.png")
        Image.fromarray(hillshade(mp, gm["px"]), "L").save(OUT / "map.png", optimize=True)
        (OUT / "meta.json").write_text(json.dumps({"R_m": R * 1000, "near": gn, "far": gf, "map": gm}, indent=1))
        for f in ("terrain_near.png", "terrain_far.png", "map.png"):
            print(f, f"{(OUT / f).stat().st_size / 1e6:.2f} MB")

    if args.sky:
        export_sky(args.sky)


if __name__ == "__main__":
    main()
