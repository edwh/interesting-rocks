# Interesting Rocks

A map of land art, sculpture and odd corners of Britain. It started as a map of Andy Goldsworthy's
permanent works and now has layers for Antony Gormley, land art and sculpture trails, public art,
prehistoric sites, holy wells, Green Men, follies, milestones, listed buildings, notable trees, caves,
interesting rocks, writers' places, plaques, war memorials, ghost signs, and museums and galleries.

**Live map:** https://edwh.github.io/interesting-rocks/ (the original Goldsworthy-only map stays at
https://edwh.github.io/goldsworthy-map/).

Tap a place for photos, directions and a button to mark it visited. The visited list is kept in your
browser's local storage, so it stays on the device you used and is never sent anywhere. Each place has a
link of the form `#tilberthwaite-touchstone-fold`.

- **Layers** sit in folded groups with All on / All off and a "Find a layer" box; big layers load only when
  turned on. Layer choices and open groups are remembered in the browser.
- **Places near:** search a town or postcode (or use your location), then set how far to look with the
  slider, as the crow flies. The list then shows everything within that distance, nearest first.
- **Filters** (behind the Filters button): highlights only, hide visited, your wishlist, and access.
- **Highlights only** shows the most interesting places in each layer: those with a photo, a Wikipedia
  article or a top grade (Grade I, Category A). Turn it off to see everything.
- **Download GPX** saves the places in view (or matching a search) as waypoints.
- Every place card says where its facts came from, with links to the source records, and credits each
  photo with its author, licence and source.

## Data and how to refresh it

Each layer is built by a script that can be re-run for updates. `scripts/layers.config.json` lists the
layers; `scripts/layers/SOURCES.md` (rewritten by every build) gives each layer's source, licence,
attribution, fetch commands, counts and last fetch date.

```
# 0. Refresh the OpenStreetMap extract (Geofabrik, United Kingdom, about 2.3 GB, updated daily)
#    and index the tags the layers use (about a minute)
scripts/osm/fetch-extract.sh
python3 scripts/osm/osm_extract.py build

# 1. Re-fetch any layer: commands are in scripts/layers/SOURCES.md, for example
node scripts/layers/listed-england/fetch.mjs
python3 scripts/layers/sculpture/run.py
python3 -I scripts/layers/ghostsigns/run.py scripts/work/layers/ghostsigns.json
python3 scripts/layers/interests/layers.py wells scripts/work/layers/wells.json --refetch
python3 scripts/layers/interests/run.py scripts/work/layers --refetch-osm   # only the OSM parts

# 2. Host any new Geograph photos (Geograph asks reusers not to hotlink)
node scripts/photos/geograph.mjs

# 3. Build the app's data files and the sources register
node scripts/build-layers.mjs
```

Fetch scripts write to `scripts/work/layers/` and cache raw downloads in `scripts/work/raw/`; both are
left out of git and can be rebuilt. Every record keeps a stable source id (`src`, for example
`wikidata Q123`, `osm node 456`, `nhle 1234567`) and the date it was fetched.

OpenStreetMap data comes from the downloaded extract, not the public Overpass servers, which often
refuse or time out. Each OSM query is still kept as an Overpass QL file beside its script (for example
`scripts/layers/interests/queries/osm-wells.overpassql`); `scripts/osm/osm_extract.py` answers them from
the extract, giving the same elements and centre points Overpass would. A query that needs a tag the index
doesn't keep needs a line in `scripts/osm/filters.txt` and a rebuild of the index. Without the extract, or
with `OSM_SOURCE=overpass`, the scripts fall back to Overpass. `python3 scripts/osm/osm_extract.py info`
shows the date of the OSM data in use.

Corrections that must survive a refresh go in `scripts/layers/overrides.json`, keyed by layer and then by
the record's `src` or `id`, for example `{"listed": {"nhle 1234567": {"hide": true}}}` or
`{"wells": {"wikidata Q123": {"name": "St Helen's Well"}}}`. Hand-curated layers keep their place lists
in their scripts (`scripts/layers/sculpture/*_places.py`).

The Goldsworthy layer is still built by the original pipeline (`node scripts/sites.mjs` through
`node scripts/curate.mjs`, writing `data/sites.json`).

## Usage rights

Only sources whose licences allow reuse are used, and each is credited in the app (in the footer for
every layer that is on, and on each place card).

| Source | Licence | Used for |
|---|---|---|
| Wikidata | CC0 | Gormley, land art, public art, prehistoric sites, wells, follies, trees, caves, rocks, writers, plaques, war memorials, museum photos and links |
| OpenStreetMap (Geofabrik extract) | ODbL, © OpenStreetMap contributors | Gormley and land art positions; public art, prehistoric sites, wells, trees, caves, rocks, milestones, plaques, war memorials, museums and galleries mapped in OSM; map tiles |
| NatureScot, Natural Resources Wales | Open Government Licence v3.0 | Geological Conservation Review sites (rocks) |
| Natural England | Open Government Licence v3.0 | Limestone Pavement Orders (rocks) |
| postcodes.io (OS Open Names, ONS, Royal Mail) | Open Government Licence v3.0; Royal Mail data © Royal Mail | "Places near" search |
| Open Plaques | Public domain (PDDL 1.0) | Plaques |
| Historic England (NHLE) | Open Government Licence v3.0 | Listed buildings, England |
| Historic Environment Scotland | Open Government Licence v3.0 | Listed buildings, Scotland |
| Cadw | Open Government Licence v3.0 | Listed buildings, Wales |
| Wikimedia Commons | Per photo: CC BY, CC BY-SA, CC0 or public domain | Photos; ghost-sign and Green Man positions |
| Geograph | CC BY-SA 2.0 | Photos (copies hosted in `data/photos/geograph`, as Geograph asks) |

Not used, because their terms don't allow it: Atlas Obscura, the Woodland Trust Ancient Tree Inventory,
the Megalithic Portal, the Ghostsigns archive (History of Advertising Trust), English Heritage's
blue plaque data and the Milestone Society's database. Photos with non-commercial or no-derivatives licences, or with no named author, are
dropped by the build.

## Licence

Code: MIT (see LICENSE). Data files in `data/` keep their sources' licences: files derived from
OpenStreetMap are available under the Open Database Licence (ODbL); listed-building data under the Open
Government Licence v3.0; Wikidata-derived data is CC0. Photos are not covered by this repository's
licence: each is credited with its author and licence. Map tiles and data © OpenStreetMap contributors.
