"""Build the Antony Gormley and land art layers.

The places are hand-curated in gormley_places.py and landart_places.py. A place either names an
OpenStreetMap element (osm='n123' / 'w123' / 'r123'), whose current position this script fetches,
or carries its own ll with src saying where it came from. Photos come from Wikimedia Commons
(free licences only) and are cached in scripts/work/raw/sculpture/photos.json; pass --refresh-photos
to look them up again.

Usage: python3 scripts/layers/sculpture/run.py [--refresh-photos]
Writes scripts/work/layers/gormley.json and scripts/work/layers/landart.json.
Sources: OpenStreetMap (ODbL; downloaded extract, or Overpass), Wikidata (CC0), Wikimedia Commons (per-photo licences).
"""
import datetime, json, os, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import commons, gormley_places as G, landart_places as L
sys.path.insert(0, os.path.join(HERE, '..', '..', 'osm'))
import osm_extract  # answers the OSM query from the downloaded extract when it has been built

ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RAW = os.path.join(ROOT, 'scripts/work/raw/sculpture')
OUT = os.path.join(ROOT, 'scripts/work/layers')
OVERPASS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']
UA = {'User-Agent': 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'}
TODAY = datetime.date.today().isoformat()
# Photos whose titles show they are of something else (a car park, a sign) are dropped.
PHOTO_SKIP = ('car park', 'entrance to', 'plaque')
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def records():
    recs = []
    for p in G.P:
        p = dict(p)
        p.update(cat='gormley', artist=p.get('artist', 'Antony Gormley'), group=p.get('group', 'Antony Gormley'))
        recs.append(p)
    for lab, ref in G.sixes:
        recs.append(dict(id='6-times-' + lab.lower(), cat='gormley', name='6 TIMES: ' + lab, artist='Antony Gormley',
                         group='6 TIMES, Water of Leith', year='2010', osm=ref, place='Water of Leith, Edinburgh',
                         region='Scotland', access='open', kind='Cast iron figure',
                         about='One of six cast-iron body forms placed along the Water of Leith between the galleries on Belford Road and the sea at Leith. After years in store the river figures were refixed upright and reinstalled from 2019.',
                         note='Free; walk the Water of Leith Walkway. Position from OpenStreetMap; the title of each figure follows the OSM label.',
                         url='https://www.antonygormley.com/works/sculpture/permanent/6-times',
                         q='6 Times Gormley Water of Leith', kw=['powderhall'] if lab == 'Right' else ['zzzz']))
    for p in L.P:
        p = dict(p)
        p['cat'] = 'landart'
        recs.append(p)
    return recs


def fetch_osm(refs):
    """Fetch the named OSM elements by id; returns {'n123': element}."""
    ids = {'n': [], 'w': [], 'r': []}
    for r in refs:
        ids[r[0]].append(r[1:])
    parts = ''.join(f'{t}(id:{",".join(v)});' for t, v in (('node', ids['n']), ('way', ids['w']), ('rel', ids['r'])) if v)
    q = f'[out:json][timeout:90];({parts});out center tags;'
    open(os.path.join(HERE, 'osm-query.txt'), 'w').write(q + '\n')
    if osm_extract.available():
        els = osm_extract.query(q)['elements']
        json.dump(els, open(os.path.join(RAW, 'osm.json'), 'w'))
        return {e['type'][0] + str(e['id']): e for e in els}
    for attempt in range(6):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            r = requests.post(url, data={'data': q}, headers=UA, timeout=120)
            if r.ok:
                els = r.json()['elements']
                json.dump(els, open(os.path.join(RAW, 'osm.json'), 'w'))
                return {e['type'][0] + str(e['id']): e for e in els}
            print(f'{url} answered {r.status_code}, retrying')
        except requests.RequestException as err:
            print(f'{url} failed ({err}), retrying')
        time.sleep(10 * (attempt + 1))
    raise SystemExit('Overpass failed on every endpoint')


def main():
    refresh = '--refresh-photos' in sys.argv
    recs = records()
    osm = fetch_osm([p['osm'] for p in recs if p.get('osm')])
    missing = []
    for p in recs:
        ref = p.pop('osm', None)
        if ref:
            e = osm.get(ref)
            if not e:
                missing.append(f"{p['id']} ({ref})")
                p.setdefault('src', 'hand')
                if 'll' not in p:
                    continue
            else:
                c = e.get('center') or e
                p['ll'] = [c['lat'], c['lon']]
                p['src'] = {'n': 'osm node ', 'w': 'osm way ', 'r': 'osm relation '}[ref[0]] + ref[1:]
                if ref[0] in 'wr' and p['cat'] == 'landart' and any(w in p['kind'].lower() for w in ('park', 'trail', 'landform', 'landscape')):
                    p['approx'] = True
        p.setdefault('src', 'hand')
        p['ll'] = [round(x, 5) for x in p['ll']]
        p['fetched'] = TODAY
    cache_file = os.path.join(RAW, 'photos.json')
    cache = {} if refresh or not os.path.exists(cache_file) else json.load(open(cache_file))
    for p in recs:
        q, kw = p.pop('q', None), p.pop('kw', None)
        if p['id'] not in cache:
            try:
                cache[p['id']] = commons.photos(q=q, ll=p.get('ll'), kw=kw)
            except Exception as err:
                print('photo lookup failed', p['id'], err)
                cache[p['id']] = []
            json.dump(cache, open(cache_file, 'w'), indent=1)
            time.sleep(0.3)
        good = [ph for ph in cache[p['id']] if not any(w in ph['title'].lower() for w in PHOTO_SKIP)]
        p['photos'] = good or cache[p['id']]
        for k in [k for k, v in p.items() if v is None]:
            del p[k]
    recs = [p for p in recs if 'll' in p]
    for cat in ('gormley', 'landart'):
        out = [p for p in recs if p['cat'] == cat]
        json.dump(out, open(os.path.join(OUT, cat + '.json'), 'w'), indent=1, ensure_ascii=False)
        print(f'{cat}: {len(out)} places')
    if missing:
        print('OSM elements not found (deleted or merged?), check by hand:', ', '.join(missing))


if __name__ == '__main__':
    main()
