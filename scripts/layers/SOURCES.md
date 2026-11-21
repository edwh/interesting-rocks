# Layer sources

Rewritten by `node scripts/build-layers.mjs`; do not edit by hand. To refresh a layer, run its fetch commands, then the build.
Hand corrections that must survive a refresh go in `scripts/layers/overrides.json`, keyed by layer and then by the record's `src` or `id`
(for example `{"listed": {"nhle 1234567": {"hide": true}}}`).

OpenStreetMap data is read from the Geofabrik United Kingdom extract (https://download.geofabrik.de/europe/united-kingdom/united-kingdom-latest.osm.pbf), data as of 2026-11-20T21:21:21Z
(MD5 ee2a678a96dfedc976e83d7afb272ff3), through `scripts/osm/osm_extract.py`, which keeps the tags listed in `scripts/osm/filters.txt`.
Refresh it with `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build` before re-running the OSM-based layers.

| Layer | Places | Highlights | Last fetched | Licence |
|---|---|---|---|---|
| Andy Goldsworthy | 58 | 58 | n/a | MIT (this project) |
| Antony Gormley | 25 | 25 | 2026-11-21 | CC0 and ODbL |
| Land art and sculpture trails | 43 | 43 | 2026-11-21 | CC0 and ODbL |
| Public art | 10656 | 2247 | 2026-11-21 | CC0; ODbL 1.0 |
| Stone circles and standing stones | 1270 | 449 | 2026-11-21 | CC0; ODbL 1.0 |
| Holy wells | 316 | 51 | 2026-11-21 | CC0 and ODbL |
| Green Men | 109 | 109 | 2026-11-21 | Per-photo Commons licences |
| Follies, grottoes and hill figures | 429 | 242 | 2026-11-21 | CC0 |
| Milestones and guide posts | 4898 | 4424 | 2026-11-21 | Open Government Licence v3.0 and ODbL |
| Listed buildings | 60511 | 13304 | 2026-11-21 | Open Government Licence v3.0 |
| Notable trees | 264 | 76 | 2026-11-21 | CC0 and ODbL |
| Caves and show mines | 534 | 204 | 2026-11-21 | CC0 and ODbL |
| Interesting rocks | 3010 | 508 | 2026-11-21 | CC0; ODbL 1.0; Open Government Licence v3.0 |
| Writers' places | 237 | 237 | 2026-11-21 | CC0, public domain (Open Plaques) and ODbL |
| Plaques | 21010 | 12846 | 2026-11-21 | Public domain (Open Plaques, PDDL 1.0); CC0; ODbL 1.0 for plaques found only in OpenStreetMap |
| War memorials | 9833 | 5244 | 2026-11-21 | CC0; ODbL 1.0; Open Government Licence v3.0; public domain (Open Plaques) |
| Ghost signs | 1111 | 156 | 2026-11-21 | Per-photo CC licences (mostly CC BY-SA) |
| Museums and galleries | 4193 | 2170 | 2026-11-21 | ODbL 1.0; CC0 |

## Andy Goldsworthy (`goldsworthy`)

Sheepfolds, arches, cones and other permanent works.

- Source: sheepfoldscumbria.co.uk grid references, Wikimedia Commons, hand placement
- Licence: MIT (this project)
- Attribution: Photos credited individually (Wikimedia Commons, Geograph).
- Fetch: `see README (scripts/sites.mjs ... scripts/curate.mjs)`
- Work files: `scripts/work/layers/goldsworthy.json`
- Built: 58 places (tier 1: 58), 37 with photos

## Antony Gormley (`gormley`)

Iron figures on beaches, hills and rooftops, and the Angel of the North.

- Source: Wikidata, OpenStreetMap, Wikimedia Commons
- Licence: CC0 and ODbL
- Attribution: © OpenStreetMap contributors (ODbL); Wikidata (CC0); photos credited individually.
- Fetch: `python3 scripts/layers/sculpture/run.py`
- Work files: `scripts/work/layers/gormley.json`
- Built: 25 places (tier 1: 25), 19 with photos, fetched 2026-11-21

## Land art and sculpture trails (`landart`)

Skyspaces, landforms, Panopticons and forest sculpture trails.

- Source: Wikidata, OpenStreetMap, Wikimedia Commons
- Licence: CC0 and ODbL
- Attribution: © OpenStreetMap contributors (ODbL); Wikidata (CC0); photos credited individually.
- Fetch: `python3 scripts/layers/sculpture/run.py`
- Work files: `scripts/work/layers/landart.json`
- Built: 43 places (tier 1: 43), 37 with photos, fetched 2026-11-21

## Public art (`artwork`)

Named sculptures, statues and installations recorded in Wikidata and OpenStreetMap (not murals). Highlights have a photo, a Wikipedia article or a Wikidata entry.

- Source: Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: CC0; ODbL 1.0
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `node scripts/layers/artwork/fetch.mjs`, then `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build`, then `node scripts/layers/artwork/fetch-osm.mjs`
- Work files: `scripts/work/layers/artwork.json`, `scripts/work/layers/artwork-osm.json`
- Built: 10656 places (tier 1: 2247, tier 2: 8409), 2018 with photos, fetched 2026-11-21

## Stone circles and standing stones (`prehistoric`)

Stone circles, henges, dolmens and notable standing stones.

- Source: Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: CC0; ODbL 1.0
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch prehistoric`
- Work files: `scripts/work/layers/prehistoric.json`
- Built: 1270 places (tier 1: 449, tier 2: 821), 429 with photos, fetched 2026-11-21

## Holy wells (`wells`)

Holy wells, healing springs and saints' wells.

- Source: Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: CC0 and ODbL
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch wells`
- Work files: `scripts/work/layers/wells.json`
- Built: 316 places (tier 1: 51, tier 2: 265), 49 with photos, fetched 2026-11-21

## Green Men (`greenman`)

Churches with Green Man carvings, found from geotagged photos on Wikimedia Commons. Positions are where the photo was taken.

- Source: Wikimedia Commons
- Licence: Per-photo Commons licences
- Attribution: Photos and positions from Wikimedia Commons, credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch greenman`
- Work files: `scripts/work/layers/greenman.json`
- Built: 109 places (tier 1: 109), 109 with photos, fetched 2026-11-21

## Follies, grottoes and hill figures (`follies`)

Follies, garden grottoes and chalk or turf hill figures.

- Source: Wikidata; Wikimedia Commons
- Licence: CC0
- Attribution: Wikidata (CC0); photos credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch follies`
- Work files: `scripts/work/layers/follies.json`
- Built: 429 places (tier 1: 242, tier 2: 187), 228 with photos, fetched 2026-11-21

## Milestones and guide posts (`milestones`)

Milestones, mileposts and guide posts on old roads and turnpikes: listed ones in England from Historic England, plus others mapped in OpenStreetMap.

- Source: Historic England National Heritage List (NHLE); OpenStreetMap; Wikimedia Commons
- Licence: Open Government Licence v3.0 and ODbL
- Attribution: Contains Historic England data © Historic England. © OpenStreetMap contributors (ODbL). Photos credited individually.
- Fetch: `python3 scripts/layers/milestones/run.py scripts/work/layers/milestones.json`
- Work files: `scripts/work/layers/milestones.json`
- Built: 4898 places (tier 1: 4424, tier 2: 474), 378 with photos, fetched 2026-11-21

## Listed buildings (`listed`)

Grade I and II* listed buildings in England; Category A and B in Scotland; Grade I and II* in Wales. Highlights are Grade I and Category A.

- Source: Historic England National Heritage List (NHLE); Historic Environment Scotland; Cadw
- Licence: Open Government Licence v3.0
- Attribution: Contains Historic England data © Historic England. Contains Historic Environment Scotland data © Crown copyright and database right. Designated Historic Asset GIS Data, The Welsh Historic Environment Service (Cadw), licensed under the Open Government Licence v3.0. Contains OS data © Crown copyright and database right.
- Fetch: `node scripts/layers/listed-england/fetch.mjs scripts/work/layers/listed-england.json`, then `python3 scripts/layers/listed-scotland/fetch.py scripts/work/layers/listed-scotland.json scripts/work/raw/listed-scotland`, then `python3 scripts/layers/listed-wales/fetch.py scripts/work/layers/listed-wales.json scripts/work/raw/listed-wales`
- Work files: `scripts/work/layers/listed-england.json`, `scripts/work/layers/listed-scotland.json`, `scripts/work/layers/listed-wales.json`
- Built: 60511 places (tier 1: 13304, tier 2: 47207), 0 with photos, fetched 2026-11-21

## Notable trees (`trees`)

Named ancient and notable trees.

- Source: Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: CC0 and ODbL
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch trees`
- Work files: `scripts/work/layers/trees.json`
- Built: 264 places (tier 1: 76, tier 2: 188), 66 with photos, fetched 2026-11-21

## Caves and show mines (`caves`)

Show caves and show mines, and named caves and potholes. Most caves need caving skills and kit.

- Source: Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: CC0 and ODbL
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 scripts/layers/interests/run.py scripts/work/layers --refetch caves`
- Work files: `scripts/work/layers/caves.json`
- Built: 534 places (tier 1: 204, tier 2: 330), 144 with photos, fetched 2026-11-21

## Interesting rocks (`rocks`)

Glacial erratics, tors, natural arches, sea stacks, limestone pavements, fossil sites and other geology worth a look. Highlights have a photo or a Wikipedia article.

- Source: Wikidata; OpenStreetMap; Geological Conservation Review sites from NatureScot and Natural Resources Wales; Limestone Pavement Orders from Natural England; Wikimedia Commons
- Licence: CC0; ODbL 1.0; Open Government Licence v3.0
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); contains NatureScot information licensed under the Open Government Licence v3.0; contains Natural Resources Wales information © Natural Resources Wales and database right; © Natural England copyright; contains Ordnance Survey data © Crown copyright and database right; photos credited individually.
- Fetch: `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build`, then `python3 scripts/layers/rocks/run.py --use-raw`
- Work files: `scripts/work/layers/rocks.json`
- Built: 3010 places (tier 1: 508, tier 2: 2502), 467 with photos, fetched 2026-11-21

## Writers' places (`writers`)

Houses, graves, plaques, statues and other places tied to writers.

- Source: Wikidata; Open Plaques; OpenStreetMap (Nominatim) for a few positions; Wikimedia Commons
- Licence: CC0, public domain (Open Plaques) and ODbL
- Attribution: Wikidata (CC0); plaque data from Open Plaques (public domain); some positions © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 scripts/layers/writers/run.py   (private inputs in scripts/work/private/writers/)`
- Work files: `scripts/work/layers/writers.json`
- Built: 237 places (tier 1: 237), 169 with photos, fetched 2026-11-21

## Plaques (`plaques`)

Blue, green and other commemorative plaques. Highlights are blue plaques and plaques to people with a Wikipedia article.

- Source: Open Plaques bulk data; Wikidata; OpenStreetMap; Wikimedia Commons
- Licence: Public domain (Open Plaques, PDDL 1.0); CC0; ODbL 1.0 for plaques found only in OpenStreetMap
- Attribution: Plaque data from Open Plaques (public domain); Wikidata (CC0); © OpenStreetMap contributors (ODbL); photos credited individually.
- Fetch: `python3 -I scripts/layers/plaques/build_plaques.py scripts/work/layers/plaques.json`
- Work files: `scripts/work/layers/plaques.json`
- Built: 21010 places (tier 1: 12846, tier 2: 8164), 4245 with photos, fetched 2026-11-21

## War memorials (`warmemorials`)

Cenotaphs, crosses, statues, plaques and rolls of honour remembering those who died in war. Highlights have a photo or a Wikipedia article.

- Source: Wikidata; OpenStreetMap; Historic England, Historic Environment Scotland and Cadw listings; Open Plaques; Wikimedia Commons
- Licence: CC0; ODbL 1.0; Open Government Licence v3.0; public domain (Open Plaques)
- Attribution: Wikidata (CC0); © OpenStreetMap contributors (ODbL); listed memorials contain Historic England, Historic Environment Scotland and Cadw data under the Open Government Licence v3.0; Open Plaques (public domain); photos credited individually.
- Fetch: `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build`, then `node scripts/layers/warmemorials/fetch.mjs`
- Work files: `scripts/work/layers/warmemorials-wd.json`, `scripts/work/layers/warmemorials-osm.json`
- Built: 9833 places (tier 1: 5244, tier 2: 4589), 5192 with photos, fetched 2026-11-21

## Ghost signs (`ghostsigns`)

Faded hand-painted advertisements on walls. Highlights name what the sign advertised.

- Source: Wikimedia Commons (Ghost signs in the United Kingdom); Geograph
- Licence: Per-photo CC licences (mostly CC BY-SA)
- Attribution: Photos and positions from Wikimedia Commons and Geograph, credited individually.
- Fetch: `python3 -I scripts/layers/ghostsigns/run.py scripts/work/layers/ghostsigns.json`
- Work files: `scripts/work/layers/ghostsigns.json`
- Built: 1111 places (tier 1: 156, tier 2: 955), 1111 with photos, fetched 2026-11-21

## Museums and galleries (`museums`)

Museums and public galleries mapped in OpenStreetMap, with photos and Wikipedia links from Wikidata. Highlights have a photo, a Wikipedia article or a Wikidata entry.

- Source: OpenStreetMap; Wikidata; Wikimedia Commons
- Licence: ODbL 1.0; CC0
- Attribution: © OpenStreetMap contributors (ODbL); Wikidata (CC0); photos credited individually.
- Fetch: `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build`, then `node scripts/layers/museums/fetch.mjs`
- Work files: `scripts/work/layers/museums.json`
- Built: 4193 places (tier 1: 2170, tier 2: 2023), 1485 with photos, fetched 2026-11-21
