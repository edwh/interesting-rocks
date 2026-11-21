# Plaques layer: sources, licences, attribution

Run: `python3 -I build_plaques.py OUTPUT.json [--raw DIR] [--refresh] [--no-osm] [--no-photos]`
Queries beside the script: `wd-subjects.rq`, `wd-plaques.rq`, `osm-plaques.ql`.

| Source | Licence | Used | Attribution wording |
|---|---|---|---|
| Open Plaques UK data dump (S3 `open-plaques-United-Kingdom-<date>.json`, found via the /data page or its Wayback copy because openplaques.org returned 503 on 21 Nov 2026) | Public Domain Dedication and Licence 1.0 (stated on openplaques.org/data: "no claim of copyright... re-use in any way you see fit"; attribution optional) | Backbone: coordinates, inscription, colour, address, year, subjects | "Plaque data from Open Plaques (openplaques.org), PDDL 1.0." |
| Wikidata | CC0 | P1430 (subject id -> QID), English Wikipedia sitelinks, plaque items (P31 Q885849 / Q721747 with P625) not in Open Plaques | "Wikidata (CC0)" |
| OpenStreetMap via Overpass | ODbL 1.0 | historic=memorial + memorial=plaque; only records absent from the other sources are added, tagged `"lic":"ODbL"`; matches only add a `osm ...` entry to `src` | "(c) OpenStreetMap contributors, ODbL" |
| Wikimedia Commons imageinfo | per file (script keeps only CC0 / CC BY / CC BY-SA / public domain; rejects NC and ND) | photo of the plaque for tier 1 records, via Open Plaques photo links to Commons | per photo `artist` and `license`, link in `page` |

## Rejected
- English Heritage London blue plaques list: EH site content is (c) English Heritage, no open licence; its plaques are already in Open Plaques (PDDL) and Wikidata.
- Open Plaques photos hosted on Flickr / elsewhere: many are CC BY-NC(-ND), not stored.
- Open Plaques records with no coordinates (about 1,055), not current (about 239) or outside the UK box.
