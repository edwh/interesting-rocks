#!/usr/bin/env bash
# Download the Geofabrik United Kingdom extract (England, Scotland, Wales and Northern Ireland,
# the same area as the old Overpass queries' ISO3166-1=GB) and check its MD5.
# OpenStreetMap data, ODbL 1.0: credit "© OpenStreetMap contributors".
# Geofabrik updates it daily; there is no need to fetch more than once a day.
# Usage: scripts/osm/fetch-extract.sh [DIR]   (default scripts/work/raw/osm)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:-$HERE/../work/raw/osm}"
URL=https://download.geofabrik.de/europe/united-kingdom/united-kingdom-latest.osm.pbf
UA="goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)"
mkdir -p "$DIR"
cd "$DIR"
F=united-kingdom-latest.osm.pbf
# -z only downloads when the remote copy is newer than ours; -R keeps the server's date.
SINCE=(); [ -f "$F" ] && SINCE=(-z "$F")
curl -fsSL -A "$UA" -R "${SINCE[@]}" -o "$F.part" "$URL"
if [ -s "$F.part" ]; then mv "$F.part" "$F"; else rm -f "$F.part"; echo "extract unchanged"; fi
curl -fsSL -A "$UA" -o "$F.md5" "$URL.md5"
echo "$(cut -d' ' -f1 "$F.md5")  $F" | md5sum -c -
osmium fileinfo -g header.option.osmosis_replication_timestamp "$F" | sed 's/^/data as of /'
