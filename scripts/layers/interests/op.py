"""OSM queries: answered from the downloaded extract (scripts/osm/osm_extract.py) when it has been
built, otherwise by the public Overpass servers with backoff. Set OSM_SOURCE=overpass to force Overpass.
ODbL data: credit OpenStreetMap contributors."""
import os, sys, json, urllib.request, urllib.parse, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'osm'))
import osm_extract
UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
ENDPOINTS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']


def op(q):
    if osm_extract.available():
        try:
            return osm_extract.query(q)
        except osm_extract.Unsupported as e:
            print('extract cannot answer this query, using Overpass:', e, file=sys.stderr)
    for i in range(6):
        url = ENDPOINTS[i % len(ENDPOINTS)]
        try:
            r = urllib.request.Request(url, urllib.parse.urlencode({'data': q}).encode(), {'User-Agent': UA})
            return json.load(urllib.request.urlopen(r, timeout=300))
        except Exception as e:
            print('retry', url, e, file=sys.stderr)
            time.sleep(15 * (i + 1))
    raise SystemExit('Overpass failed on every endpoint')
