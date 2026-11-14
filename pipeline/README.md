# HorizonLine data pipeline

Turns NASA LOLA terrain + JPL Horizons ephemerides into small JSON files the web app reads.

## Setup
```
pip install -r requirements.txt
python test_pipeline.py          # should print "all checks passed"
```

## Run
1. Put the LOLA south-pole DEM in `data/`:
   https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF (181 MB, 80 m/px, 80–90°S)
2. Fill site coordinates in `sites.json`.
3. Run:
```
python fetch_ephemeris.py sites.json --start 2027-01-01 --stop 2028-01-01 --step "1 h"
python horizon.py data/<dem>.tif sites.json
python score.py sites.json --out ../app/data
```
Tip: test one site first with `--only pole-test` on the fetch step.

Alternative used for the submitted data: Horizons was queried from a browser tab on ssd.jpl.nasa.gov
(same API and parameters), saved as `horizonline_ephem_all.json`, then converted with
`python import_browser_ephem.py horizonline_ephem_all.json`.

Science checks (after score.py): `python check_science.py` - Earth direction vs geometry, Sun height vs theory, longest continuous sunlight.

Site points: `echo '{"Haworth":[447000,575000,478000,605000]}' | python site_heights.py`
(bounding box in USGS LPS metres -> highest LOLA point in the box).

## Web export (what the app reads)
```
python export_web.py --sky horizonline_sky_2027_2029.json
```
Writes `app/data/` sites.json (horizons), sky.json (Moon-fixed Sun/Earth, hourly), terrain_near.png / terrain_far.png
(heights as terrain-RGB for custom sites), map.png (hillshade) and meta.json. `validate_skyvec.py` checks the sky method.

## Data sources
- NASA LRO Lunar Orbiter Laser Altimeter (LOLA) DEMs, NASA GSFC Planetary Geodynamics Data Archive
- NASA/JPL Horizons System ephemerides (Sun, Earth seen from each lunar site)

## Known limits
- Horizon uses only terrain inside the DEM (80–90°S); farther terrain is below the horizon anyway because of lunar curvature for most sites.
- The Sun is treated as a disk with a linear visible fraction; Earth counts as visible when its center clears the terrain.

## AI use
Code written with assistance from Claude (Anthropic), reviewed and run by the author.
