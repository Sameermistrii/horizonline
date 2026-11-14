# HorizonLine

Compare lunar south-pole landing sites and dates by sunlight and direct-to-Earth visibility.
Built for the NASA Space Apps Challenge 2026, **Lunar Landing Site Navigator**.

**Live app:** https://sameermistrii.github.io/horizonline/app/

- `app/` - the web app (static HTML + D3). Open it via any static server or GitHub Pages.
- `pipeline/` - Python scripts that turn NASA data into `app/data/`, plus the validation checks.

## Features
- 11 curated sites: 8 NASA Artemis III candidate regions, the IM-2 (CLPS) target, Chandrayaan-3, Apollo 11
- Custom sites: click the south-pole map or type coordinates; the horizon is traced in the browser through LOLA terrain
- 360-degree horizon view with Sun and Earth paths, animated over the stay
- Live readout: Sun/Earth elevation, height above the local horizon, time to sunset/sunrise and Earthset/Earthrise
- Side-by-side scores for up to 3 sites: power, highest Sun, Earth link, longest darkness, longest Earth blackout
- Daily power calendar, 2027-2029

## How the sky is computed
One JPL Horizons query (a reference site near the pole, hourly, with ranges) is converted to Moon-fixed
Sun directions and Earth positions (`pipeline/skyvec.py`). The browser turns these into azimuth/elevation for
any site, including Earth parallax. `pipeline/validate_skyvec.py` shows this matches Horizons' own per-site
output within 0.0002 deg for all 8 Artemis III sites.

## Run the app locally
```
cd app
python -m http.server 8000
```
Then open http://localhost:8000. Bundled data: 11 curated sites, Sun and Earth hourly for 2027-2029.

## Data
- NASA LRO Lunar Orbiter Laser Altimeter (LOLA) south-pole DEM (LDEM_80S_80MPP_ADJ), NASA GSFC Planetary Geodynamics Data Archive
- NASA/JPL Horizons System: Sun and Earth azimuth, elevation and range, hourly 2027-2029 (reference site); per-site 2027 runs for validation
- Region boxes: USGS, Down Selected Artemis III Candidate Landing Site Navigational Grids, doi:10.5066/P1MEQ6UK
- Site rule: the highest LOLA point inside each region box. Mons Mouton Plateau is not included (its USGS file needs a login).
- IM-2 target: LROC (-84.78, 29.13E). Chandrayaan-3: USGS Gazetteer, Statio Shiv Shakti (-69.37, 32.32E). Apollo 11: NASA NSSDC (0.67416N, 23.47314E).

## Accuracy and limits
- Curated sites use 80 m terrain; custom sites use 240 m terrain (with 960 m beyond 150 km) and can read up to ~10 points sunnier on sharp peaks.
- Terrain beyond 80 S is not modelled: Chandrayaan-3 and Apollo 11 use a smooth Moon.
- Landing safety (slope, boulders) is not assessed.

## AI use
Code written with assistance from Claude (Anthropic); design decisions, data runs and checks by the author.
