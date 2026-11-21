#!/usr/bin/env python3
"""Build the 'rocks' layer: interesting rocks and geology in Great Britain.

Usage: python3 scripts/layers/rocks/run.py [OUTPUT.json] [--raw-dir DIR] [--use-raw] [--no-photos]
       (default output scripts/work/layers/rocks.json, raw cache scripts/work/raw/rocks)

Sources (queries in queries/ beside this script):
  Wikidata SPARQL (CC0): erratics, arches, sea stacks, tors, exposures, fossil sites, gorges...
  OpenStreetMap (ODbL): named rock features, read from the downloaded extract (scripts/osm/osm_extract.py)
    or else Overpass in tiles.
  NatureScot Geological Conservation Review sites (OGL v3; ArcGIS item 68c862b5d3a1437bb4b477dcd4cd8ffc).
  Natural Resources Wales Geological Conservation Review sites (OGL v3; DataMapWales inspire-nrw:NRW_GCR_SITES).
  Natural England Limestone Pavement Orders (OGL v3; ArcGIS item 509f8e3a23684412b104d1f0660b3ae1).
  England has no open GCR dataset. Photos from Wikimedia Commons (CC BY / CC BY-SA / CC0 / PD).
Hand inclusions/exclusions: curation.json beside this script.
--use-raw reuses cached raw downloads where present and fetches only what is missing (photo licences
are always looked up fresh).
"""
import sys, os, re, json, time, math, html, datetime, argparse, unicodedata, urllib.request, urllib.parse

UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().isoformat()
OVERPASS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass-api.de/api/interpreter']
sys.path.insert(0, os.path.join(HERE, '..', '..', 'osm'))
import osm_extract  # answers the OSM queries from the downloaded extract when it has been built
SPARQL = 'https://query.wikidata.org/sparql'
COMMONS = 'https://commons.wikimedia.org/w/api.php'
GCR_SCOT = 'https://services1.arcgis.com/LM9GyVFsughzHdbO/arcgis/rest/services/Geological_Conservation_Review_sites/FeatureServer/0'
GCR_WALES = 'https://services.arcgis.com/hQoYDJEEJMaPw8Sy/arcgis/rest/services/NRW_GCR_Geological_Conservation_Review_sites/FeatureServer/0'
LPO_ENG = 'https://services.arcgis.com/JJzESW51TqeY9uat/arcgis/rest/services/Limestone_Pavement_Orders_England/FeatureServer/0'
GCR_WIKI = 'https://en.wikipedia.org/wiki/Geological_Conservation_Review'

# Overpass tiles (south, west, north, east): split so no single request is heavy.
TILES = []
for (s, n) in [(49.8, 51.0), (51.0, 52.0), (52.0, 53.0), (53.0, 54.0), (54.0, 55.0), (55.0, 56.0), (56.0, 57.0), (57.0, 58.0), (58.0, 61.0)]:
    for (w, e) in [(-9.0, -4.0), (-4.0, -2.0), (-2.0, 2.0)]:
        TILES.append((s, w, n, e))

# Wikidata root classes -> group. Priority order decides the group when several match.
ROOTS = [
    ('Q372934', 'Erratic'), ('Q954501', 'Natural arch'), ('Q747957', 'Sea stack'), ('Q1343179', 'Tor'),
    ('Q729136', 'Limestone pavement'), ('Q876798', 'Exposure'), ('Q9096832', 'Fossil site'),
    ('Q150784', 'Gorge'), ('Q3699460', 'Gorge'), ('Q2042028', 'Gorge'), ('Q6554495', 'Gorge'),
    ('Q531953', 'Exposure'), ('Q10376531', 'Geology site'), ('Q2179685', 'Geology site'),
    ('Q631305', 'Rock formation'), ('Q1404150', 'Rock formation'), ('Q581776', 'Rock formation'),
    ('Q653139', 'Rock formation'), ('Q85793331', 'Rock formation'), ('Q1139493', 'Rock formation'),
]
GROUP_PRIORITY = ['Erratic', 'Natural arch', 'Sea stack', 'Tor', 'Limestone pavement', 'Exposure',
                  'Fossil site', 'Gorge', 'Geology site', 'Rock formation']
# direct classes that disqualify an item (skerries, submerged rocks, mass rocks, lifting stones, geoparks)
BAD_CLASSES = {'Q216851', 'Q34198935', 'Q1907312', 'Q3997677', 'Q1324355', 'Q53444003', 'Q5', 'Q486972'}
KIND = {'Erratic': 'Glacial erratic', 'Tor': 'Tor', 'Rock formation': 'Rock formation', 'Natural arch': 'Natural arch',
        'Sea stack': 'Sea stack', 'Limestone pavement': 'Limestone pavement', 'Exposure': 'Rock exposure',
        'Fossil site': 'Fossil site', 'Gorge': 'Gorge or ravine', 'Geology site': 'Geological site'}
ACCESS_PRIVATE = {'private', 'no'}
GCR_SKIP = re.compile(r'quarry|pit\b|borehole|cutting|\bmine\b|brickworks|railway|roadstone|sandpit|gravel|opencast|\btip\b|\bworks\b', re.I)
OSM_SKIP_NAME = re.compile(r'standing stone|stone circle|cairn|\bcross\b|memorial|milestone|boundary|marker|\bmegalith|burial|\bgrave|\bwell\b|\bbridge\b|\bhouse\b|\bfarm\b|\binn\b|\bhotel\b|\bchurch\b', re.I)
FOSSIL_BLOCK = re.compile(r'chordata|palaeobot|fossil|reptil|mammal|fish|palaeontolog|invertebrat|insect|arthropod|dinosaur|vertebrate|plant|fauna|flora|trilobite|ammonite|brachiopod|mollus', re.I)
FREE_LIC = re.compile(r'^(CC[ -]BY(-SA)?[ -]\d|CC0|Public domain|PD[ -]|PDM)', re.I)
BAD_LIC = re.compile(r'\b(NC|ND)\b|GFDL|fair use|non-?free', re.I)
BAD_FILE = re.compile(r'\.(svg|pdf|tiff?|ogv|webm|ogg|djvu)$|\bmap\b|\blogo\b|\bdiagram\b|\bflag\b|\bcoat of arms\b', re.I)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def http(url, data=None, headers=None, timeout=300, retries=4):
    h = {'User-Agent': UA}
    h.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as ex:
            wait = 10 * (i + 1)
            log('  retry', i + 1, str(ex)[:100], 'wait', wait)
            time.sleep(wait)
    raise RuntimeError('failed: ' + url[:120])


def cached(raw, name, use_raw, fetch):
    p = os.path.join(raw, name)
    if use_raw and os.path.exists(p):
        return json.load(open(p))
    d = fetch()
    json.dump(d, open(p, 'w'))
    return d


def load_q(name):
    return open(os.path.join(HERE, 'queries', name)).read()


# ---------- geography ----------
def in_gb(lat, lon):
    if not (49.85 <= lat <= 60.9 and -8.7 <= lon <= 1.9):
        return False
    if lon < -5.5 and lat < 55.0:      # Ireland / NI south of Kintyre
        return False
    if lon < -6.0 and lat < 55.4:
        return False
    if 53.9 <= lat <= 54.45 and -4.95 <= lon <= -4.2:  # Isle of Man
        return False
    return True


def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    x = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


STOP = {'the', 'of', 'and', 'a', 'at', 'on', 'in', 'near', 'site', 'sssi', 'nnr'}


def toks(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\(.*?\)|\[.*?\]', ' ', s)
    return frozenset(t for t in re.findall(r"[a-z0-9]+", s) if t not in STOP)


def name_match(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return None
    if ta == tb:
        return 'exact'
    small, big = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if small <= big and len(' '.join(small)) >= 5:
        return 'contain'
    return None


# ---------- Wikidata ----------
def sparql(query, retries=3):
    time.sleep(2)
    # The query service stops a query after 60 s, so waiting longer than that only delays the retry.
    raw = http(SPARQL, {'query': query}, {'Accept': 'application/sparql-results+json'}, timeout=75, retries=retries)
    return json.loads(raw)['results']['bindings']


def wd_rows(bindings):
    out = {}
    for b in bindings:
        q = b['x']['value'].rsplit('/', 1)[-1]
        v = lambda k: b[k]['value'] if k in b else ''
        m = re.match(r'Point\(([-\d.eE]+) ([-\d.eE]+)\)', v('c'))
        if not m:
            continue
        out[q] = dict(qid=q, label=v('xLabel'), desc=v('xDescription'), lon=float(m.group(1)), lat=float(m.group(2)),
                      wp=v('wp'), p17=v('p17').rsplit('/', 1)[-1], cat=v('cat'),
                      imgs=[i for i in v('imgs').split('|') if i], classes=set(c for c in v('classes').split('|') if c),
                      loc=v('loc'), dissolved=bool(v('dissolved')))
    return out


MISSING = []  # Wikidata classes that could not be fetched this run


def wd_tiled(root):
    """The whole-GB query for a big class can exceed the query service's 60 s limit. Find the items box
    by box instead (a few seconds each), then fetch their details in batches."""
    qids = set()
    for s in (49.8, 51.8, 53.8, 55.8, 57.8, 59.8):
        for w in (-8.7, -6.2, -3.7, -1.2):
            q = load_q('wikidata-class-tile.rq')
            for k, v in (('{ROOT}', root), ('{SOUTH}', s), ('{WEST}', w), ('{NORTH}', round(min(s + 2, 60.9), 1)), ('{EAST}', round(min(w + 2.5, 1.9), 1))):
                q = q.replace(k, str(v))
            qids |= {b['x']['value'].rsplit('/', 1)[-1] for b in sparql(q)}
    log('  tiles found', len(qids), 'items of', root)
    rows, qids = [], sorted(qids)
    for i in range(0, len(qids), 150):
        rows += sparql(load_q('wikidata-qids.rq').replace('{VALUES}', ' '.join('wd:' + q for q in qids[i:i + 150])))
    return rows


def fetch_wikidata(raw, use_raw):
    allrows = {}
    for root, group in ROOTS:
        def f(root=root):
            log('wikidata', root)
            try:
                return sparql(load_q('wikidata-class.rq').replace('{ROOT}', root), retries=1)
            except RuntimeError:
                log('  whole-GB query failed; trying box by box')
                return wd_tiled(root)
        try:
            rows = wd_rows(cached(raw, 'wikidata-%s.json' % root, use_raw, f))
        except RuntimeError:
            # The query service is often overloaded; keep going and say so. Re-run with --use-raw to fill the gap.
            log('  WIKIDATA FAILED for', root, group, '- re-run with --use-raw later to fill it in')
            MISSING.append('%s (%s)' % (root, group))
            continue
        for q, r in rows.items():
            e = allrows.setdefault(q, r)
            e.setdefault('roots', set()).add(root)
            e['classes'] |= r['classes']
        log(' ', root, group, len(rows))
    return allrows


def fetch_wikidata_qids(raw, use_raw, qids, tag):
    qids = sorted(set(qids))
    if not qids:
        return {}
    rows = {}
    for i in range(0, len(qids), 150):
        chunk = qids[i:i + 150]
        def f(chunk=chunk):
            log('wikidata qids', tag, len(chunk))
            return sparql(load_q('wikidata-qids.rq').replace('{VALUES}', ' '.join('wd:' + q for q in chunk)))
        rows.update(wd_rows(cached(raw, 'wikidata-%s-%d.json' % (tag, i), use_raw, f)))
    return rows


def wd_group(r, override):
    if r['qid'] in override:
        return override[r['qid']]
    roots = r.get('roots', set())
    gs = {g for root, g in ROOTS if root in roots}
    for g in GROUP_PRIORITY:
        if g in gs:
            return g
    return 'Rock formation'


def wd_to_rec(r, override, group=None):
    g = group or wd_group(r, override)
    rec = dict(name=r['label'], group=g, ll=[r['lat'], r['lon']], approx=False, kind=KIND[g],
               about=r['desc'], url=r['wp'] or ('https://www.wikidata.org/wiki/' + r['qid']), wikidata=r['qid'],
               access='gone' if r['dissolved'] else 'open', srcs=['wikidata ' + r['qid']],
               loc=r['loc'], files=[x for x in r['imgs']], cat=r['cat'], wp=bool(r['wp']), kinds=set(r['classes']))
    return rec


# ---------- OSM ----------
def fetch_overpass(raw, use_raw):
    feats, places = [], []
    if osm_extract.available():  # the extract answers the whole country at once
        bbox = '49.8,-9.0,61.0,2.0'
        feats = osm_extract.query(load_q('overpass-features.ql').replace('{BBOX}', bbox))['elements']
        places = osm_extract.query(load_q('overpass-places.ql').replace('{BBOX}', bbox))['elements']
        log('extract: features', len(feats), 'places', len(places))
        return feats, places
    for i, t in enumerate(TILES):
        bbox = ','.join(str(x) for x in t)
        for kind, tmpl, store in (('f', 'overpass-features.ql', feats), ('p', 'overpass-places.ql', places)):
            def f(tmpl=tmpl, bbox=bbox):
                log('overpass', kind, bbox)
                q = load_q(tmpl).replace('{BBOX}', bbox)
                for k in range(6):
                    ep = OVERPASS[k % 2]
                    try:
                        time.sleep(6)
                        return json.loads(http(ep, {'data': q}, retries=1, timeout=300))
                    except Exception as ex:
                        log('  overpass fail', ep, str(ex)[:80]); time.sleep(20)
                raise RuntimeError('overpass failed ' + bbox)
            d = cached(raw, 'overpass-%s-%d.json' % (kind, i), use_raw, f)
            store.extend(d.get('elements', []))
    return feats, places


def osm_group(tags):
    g = tags.get('geological', '')
    nat = tags.get('natural', '')
    rock = tags.get('rock', '')
    name = tags.get('name', '')
    if g == 'glacial_erratic' or rock == 'erratic' or re.search(r'erratic', name, re.I):
        return 'Erratic'
    if nat == 'arch' or rock == 'arch':
        return 'Natural arch'
    if nat in ('stack', 'sea_stack') or rock == 'stack':
        return 'Sea stack'
    if g == 'limestone_pavement':
        return 'Limestone pavement'
    if g == 'palaeontological_site':
        return 'Fossil site'
    if rock == 'tor' or re.search(r'\btor\b', name, re.I):
        return 'Tor'
    if g == 'outcrop':
        return 'Exposure'
    if g in ('geotope', 'volcanic_vent', 'dyke'):
        return 'Geology site'
    return 'Rock formation'


def osm_to_rec(el):
    t = el['tags']
    lat = el.get('lat') or el.get('center', {}).get('lat')
    lon = el.get('lon') or el.get('center', {}).get('lon')
    if lat is None or not in_gb(lat, lon):
        return None
    if t.get('historic') or t.get('megalith_type') or OSM_SKIP_NAME.search(t['name']):
        return None
    g = osm_group(t)
    wp = ''
    if t.get('wikipedia'):
        lang, _, title = t['wikipedia'].partition(':')
        if title:
            wp = 'https://%s.wikipedia.org/wiki/%s' % (lang, urllib.parse.quote(title.replace(' ', '_')))
    files = []
    if t.get('wikimedia_commons'):
        files = [t['wikimedia_commons']]
    ref = '%s/%d' % (el['type'], el['id'])
    acc = 'private' if t.get('access') in ACCESS_PRIVATE else 'open'
    return dict(name=t['name'], group=g, ll=[lat, lon], approx=el['type'] != 'node', kind=KIND[g],
                about='', url=wp or 'https://www.openstreetmap.org/' + ref, wikidata=t.get('wikidata', ''),
                access=acc, srcs=['osm %s %d' % (el['type'], el['id'])], loc='', files=files, cat='', wp=bool(wp),
                kinds=set(), osm_desc=t.get('description', ''))


# ---------- ArcGIS (GCR, LPO) ----------
def arcgis_all(url, where='1=1'):
    out, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(where=where, outFields='*', returnGeometry='false', returnCentroid='true', outSR=4326, f='json',
                                       resultOffset=off, resultRecordCount=500, orderByFields='OBJECTID'))
        d = json.loads(http(url + '/query?' + q))
        fs = d.get('features', [])
        out.extend(fs)
        if not d.get('exceededTransferLimit') or not fs:
            break
        off += len(fs)
        time.sleep(1)
    return out


def gcr_recs(raw, use_raw):
    recs = {}
    sc = cached(raw, 'gcr-scotland.json', use_raw, lambda: arcgis_all(GCR_SCOT))
    wl = cached(raw, 'gcr-wales.json', use_raw, lambda: arcgis_all(GCR_WALES))
    rows = []
    for f in sc:
        a = f['attributes']
        if a.get('TYPE') and a['TYPE'].upper() == 'BIOLOGICAL':
            continue
        rows.append((a['NAME'], str(a.get('GCR_NO') or ''), a.get('GCR_BLOCK') or '', f['centroid'], 'Scotland'))
    for f in wl:
        a = f['attributes']
        rows.append((a['GCR_Site_n'], str(int(a['GCR_No'])) if a.get('GCR_No') else '', a.get('FULL_BLOCK') or '', f['centroid'], 'Wales'))
    for name, no, block, c, nation in rows:
        name = re.sub(r'\s*\[.*?\]', '', (name or '')).strip()
        if not name or GCR_SKIP.search(name) or not c:
            continue
        key = (name.lower(), nation)
        e = recs.setdefault(key, dict(name=name, pts=[], nos=set(), blocks=set(), nation=nation))
        e['pts'].append((c['y'], c['x']))
        if no:
            e['nos'].add(no)
        if block:
            e['blocks'].add(block)
    out = []
    for e in recs.values():
        lat = sum(p[0] for p in e['pts']) / len(e['pts'])
        lon = sum(p[1] for p in e['pts']) / len(e['pts'])
        if not in_gb(lat, lon):
            continue
        blocks = sorted(e['blocks'])
        g = 'Fossil site' if any(FOSSIL_BLOCK.search(b) for b in blocks) else 'Geology site'
        about = 'Geological Conservation Review site, listed for its %s interest.' % ' and '.join(b.rstrip('.') for b in blocks[:2]) if blocks else 'Geological Conservation Review site.'
        out.append(dict(name=e['name'], group=g, ll=[lat, lon], approx=True, kind=KIND[g], about=about, url=GCR_WIKI, wikidata='',
                        access='unknown', srcs=['gcr ' + '/'.join(sorted(e['nos']))] if e['nos'] else ['gcr ' + e['nation'].lower()],
                        loc='', files=[], cat='', wp=False, kinds=set(), nation=e['nation']))
    return out


def lpo_recs(raw, use_raw):
    d = cached(raw, 'lpo-england.json', use_raw, lambda: arcgis_all(LPO_ENG))
    out = []
    for f in d:
        a = f['attributes']
        c = f.get('centroid')
        if not c or not a.get('SITE_NAME'):
            continue
        name = a['SITE_NAME'].strip()
        if not re.search(r'pavement', name, re.I):
            name += ' limestone pavement'
        loc = ', '.join(x.strip() for x in (a.get('LOCATION'), a.get('COUNTY')) if x and x.strip())
        out.append(dict(name=name, group='Limestone pavement', ll=[c['y'], c['x']], approx=True, kind=KIND['Limestone pavement'],
                        about='Limestone pavement protected by a Limestone Pavement Order%s.' % (' (confirmed %s)' % a['DATE_CONF'].strip() if a.get('DATE_CONF', '').strip() else ''),
                        url=GCR_WIKI.replace('Geological_Conservation_Review', 'Limestone_pavement'), wikidata='', access='unknown',
                        srcs=['lpo ' + (a.get('Ref_Num') or str(a['OBJECTID']))], loc=loc, files=[], cat='', wp=False, kinds=set()))
    return out


# ---------- merge ----------
def merge(recs):
    """Merge records that share a Wikidata id, or have matching names within 100 m (500 m for identical names;
    up to 3 km for GCR/LPO area centroids against a contained name)."""
    out = []
    byq = {}
    for r in recs:
        tgt = None
        if r.get('wikidata') and r['wikidata'] in byq:
            tgt = byq[r['wikidata']]
        else:
            for o in out:
                d = hav(r['ll'], o['ll']) if abs(r['ll'][0] - o['ll'][0]) < 0.04 and abs(r['ll'][1] - o['ll'][1]) < 0.07 else 1e9
                if d > 3000:
                    continue
                m = name_match(r['name'], o['name'])
                area = r['approx'] and r['srcs'][0].split()[0] in ('gcr', 'lpo') or o['approx'] and o['srcs'][0].split()[0] in ('gcr', 'lpo')
                if m and (d <= 100 or (m == 'exact' and d <= 500) or (area and d <= 3000)):
                    tgt = o
                    break
        if tgt is None:
            out.append(r)
            if r.get('wikidata'):
                byq[r['wikidata']] = r
            continue
        mergeinto(tgt, r)
        if tgt.get('wikidata'):
            byq[tgt['wikidata']] = tgt
    return out


def rank(r):
    return {'curated': 0, 'wikidata': 0, 'osm': 1, 'lpo': 2, 'gcr': 3}[r['srcs'][0].split()[0]]


def mergeinto(tgt, other):
    hi, lo = (tgt, other) if rank(tgt) <= rank(other) else (other, tgt)
    m = dict(hi)
    for k in ('about', 'wikidata', 'loc', 'cat', 'osm_desc'):
        if not m.get(k):
            m[k] = lo.get(k, '')
    if not m['url'] or (m['url'].startswith('https://www.openstreetmap.org') or m['url'] == GCR_WIKI) and lo['url'] and not lo['url'].startswith('https://www.openstreetmap.org') and lo['url'] != GCR_WIKI:
        m['url'] = lo['url']
    m['srcs'] = hi['srcs'] + [x for x in lo['srcs'] if x not in hi['srcs']]
    m['files'] = hi['files'] + [x for x in lo['files'] if x not in hi['files']]
    m['kinds'] = set(hi['kinds']) | set(lo['kinds'])
    m['wp'] = hi['wp'] or lo['wp']
    # a precise point beats an area centroid
    if hi['approx'] and not lo['approx']:
        m['ll'], m['approx'] = lo['ll'], False
    if hi['group'] in ('Geology site', 'Rock formation') and lo['group'] not in ('Geology site', 'Rock formation'):
        m['group'] = lo['group']; m['kind'] = lo['kind']
    if 'private' in (hi['access'], lo['access']):
        m['access'] = 'private'
    elif 'limited' in (hi['access'], lo['access']) and 'open' not in (hi['access'], lo['access']):
        m['access'] = 'limited'
    elif 'gone' in (hi['access'], lo['access']):
        m['access'] = 'gone'
    elif 'open' in (hi['access'], lo['access']):
        m['access'] = 'open'
    tgt.clear()
    tgt.update(m)


# ---------- nearest place ----------
def nearest_place(pts, ll):
    best, bd = '', 1e9
    for p in pts:
        if abs(p[0] - ll[0]) > 0.15 or abs(p[1] - ll[1]) > 0.25:
            continue
        d = hav(ll, (p[0], p[1]))
        if d < bd:
            best, bd = p[2], d
    return best


# ---------- photos ----------
def clean(s):
    s = re.sub(r'<[^>]+>', '', s or '')
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def file_title(f):
    f = f.strip()
    if f.startswith('http'):
        f = urllib.parse.unquote(f.rsplit('/', 1)[-1])
    f = re.sub(r'^(File|Image):', '', f, flags=re.I)
    return 'File:' + f.replace('_', ' ')


def imageinfo(titles, raw, use_raw):
    """titles -> {normalised title: info or None}. Batched 40 per request."""
    res = {}
    titles = sorted(set(titles))
    for i in range(0, len(titles), 40):
        chunk = titles[i:i + 40]
        def f(chunk=chunk):
            time.sleep(0.6)
            q = dict(action='query', titles='|'.join(chunk), prop='imageinfo', iiprop='url|extmetadata|mime', iiurlwidth=1280,
                     redirects=1, format='json', formatversion=2)
            return json.loads(http(COMMONS + '?' + urllib.parse.urlencode(q)))
        d = f()  # always fresh: licences can change
        q = d['query']
        alias = {}
        for n in q.get('normalized', []):
            alias[n['from']] = n['to']
        for n in q.get('redirects', []):
            alias[n['from']] = n['to']
        pages = {p['title']: p for p in q.get('pages', [])}
        for t in chunk:
            tt = alias.get(t, t)
            tt = alias.get(tt, tt)
            res[t] = pages.get(tt)
    return res


def photo_from(p):
    if not p or 'imageinfo' not in p:
        return None
    ii = p['imageinfo'][0]
    if not ii.get('mime', '').startswith('image/') or ii['mime'] in ('image/svg+xml', 'image/tiff', 'image/vnd.djvu'):
        return None
    md = ii.get('extmetadata', {})
    lic = clean(md.get('LicenseShortName', {}).get('value'))
    if not lic or not FREE_LIC.match(lic) or BAD_LIC.search(lic):
        return None
    if md.get('NonFree', {}).get('value', '').lower() in ('true', '1'):
        return None
    artist = clean(md.get('Artist', {}).get('value'))[:120]
    if not artist:
        if re.match(r'^(CC0|Public domain|PD)', lic, re.I):
            artist = 'Unknown'
        else:
            return None
    title = p['title'][5:]
    if BAD_FILE.search(title):
        return None
    return dict(src=ii.get('thumburl') or ii['url'], page=ii.get('descriptionurl') or 'https://commons.wikimedia.org/wiki/' + urllib.parse.quote(p['title'].replace(' ', '_')),
                license=lic, artist=artist, title=title)


def category_files(cat, raw):
    time.sleep(0.6)
    q = dict(action='query', list='categorymembers', cmtitle='Category:' + cat, cmtype='file', cmlimit=12, format='json', formatversion=2)
    try:
        d = json.loads(http(COMMONS + '?' + urllib.parse.urlencode(q), retries=2))
    except Exception:
        return []
    return [m['title'] for m in d.get('query', {}).get('categorymembers', []) if re.search(r'\.(jpe?g|png|webp)$', m['title'], re.I)]


def add_photos(recs, raw, use_raw):
    # 1) explicit files (P18 / OSM wikimedia_commons)
    cand = {}
    catneeds = []
    for r in recs:
        fs = []
        for f in r['files']:
            if f.lower().startswith('category:'):
                r['cat'] = r['cat'] or f[9:]
            else:
                fs.append(file_title(f))
        cand[r['id']] = fs
    allt = [t for fs in cand.values() for t in fs]
    log('photos: explicit files', len(allt))
    info = imageinfo(allt, raw, use_raw)
    # 2) fall back to the Commons category for places with < 2 usable photos
    got = {}
    need = []
    for r in recs:
        ph = []
        for t in cand[r['id']]:
            p = photo_from(info.get(t))
            if p and p['page'] not in [x['page'] for x in ph]:
                ph.append(p)
        got[r['id']] = ph
        if len(ph) < 2 and r['cat']:
            need.append(r)
    log('photos: category lookups', len(need))
    extra = {}
    for r in need:
        extra[r['id']] = [t for t in category_files(r['cat'], raw) if not BAD_FILE.search(t)]
    info2 = imageinfo([t for v in extra.values() for t in v], raw, use_raw)
    for r in need:
        for t in extra[r['id']]:
            if len(got[r['id']]) >= 2:
                break
            p = photo_from(info2.get(t))
            if p and p['page'] not in [x['page'] for x in got[r['id']]]:
                got[r['id']].append(p)
    for r in recs:
        r['photos'] = got[r['id']][:2]


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', nargs='?', default=os.path.join(HERE, '..', '..', 'work', 'layers', 'rocks.json'))
    ap.add_argument('--raw-dir', default=os.path.join(HERE, '..', '..', 'work', 'raw', 'rocks'))
    ap.add_argument('--use-raw', action='store_true')
    ap.add_argument('--no-photos', action='store_true')
    a = ap.parse_args()
    raw = os.path.abspath(a.raw_dir)
    os.makedirs(raw, exist_ok=True)
    cur = json.load(open(os.path.join(HERE, 'curation.json')))
    override = cur.get('group_override', {})

    # Wikidata
    wd = fetch_wikidata(raw, a.use_raw)
    inc = fetch_wikidata_qids(raw, a.use_raw, cur.get('include_qids', []), 'include')
    recs = []
    for q, r in wd.items():
        if r['classes'] & BAD_CLASSES or not r['label'] or re.match(r'^Q\d+$', r['label']):
            continue
        if r['p17'] and r['p17'] != 'Q145':
            continue
        if not in_gb(r['lat'], r['lon']):
            continue
        recs.append(wd_to_rec(r, override))
    for q, r in inc.items():
        if q in wd:
            continue
        g = cur.get('include_qid_group', {}).get(q, 'Rock formation')
        recs.append(wd_to_rec(r, override, g))
    log('wikidata records', len(recs))

    # OSM
    feats, places = fetch_overpass(raw, a.use_raw)
    seen, osm = set(), []
    for el in feats:
        k = (el['type'], el['id'])
        if k in seen or not el.get('tags', {}).get('name'):
            continue
        seen.add(k)
        r = osm_to_rec(el)
        if r:
            osm.append(r)
    qids = sorted({r['wikidata'] for r in osm if re.match(r'^Q\d+$', r['wikidata'])} - set(wd) - set(inc))
    osmq = fetch_wikidata_qids(raw, a.use_raw, qids, 'osm')
    for r in osm:
        w = osmq.get(r['wikidata']) or wd.get(r['wikidata']) or inc.get(r['wikidata'])
        if w:
            r['files'] += [x for x in w['imgs'] if x not in r['files']]
            r['cat'] = r['cat'] or w['cat']
            if w['wp'] and not r['wp']:
                r['url'], r['wp'] = w['wp'], True
            r['loc'] = w['loc']
            r['about'] = r['about'] or w['desc']
    log('osm records', len(osm))
    recs += osm

    # NE limestone pavements, GCR
    lpo = lpo_recs(raw, a.use_raw)
    gcr = gcr_recs(raw, a.use_raw)
    log('lpo', len(lpo), 'gcr', len(gcr))
    recs += lpo + gcr

    for x in cur.get('include', []):
        recs.append(dict(name=x['name'], group=x['group'], ll=x['ll'], approx=x.get('approx', False), kind=x.get('kind', KIND[x['group']]),
                         about=x.get('about', ''), url=x['url'], wikidata=x.get('wikidata', ''), access=x.get('access', 'open'),
                         srcs=['wikidata ' + x['wikidata']] if x.get('wikidata') else ['curated'],
                         loc=x.get('place', ''), files=x.get('files', []), cat=x.get('cat', ''), wp=bool(re.search('wikipedia', x['url'])), kinds=set()))

    recs = merge(recs)
    log('after merge', len(recs))

    # exclusions
    ex = cur.get('exclude', {})
    pats = [re.compile(p, re.I) for p in ex.get('name_patterns', [])]
    recs = [r for r in recs if r.get('wikidata') not in ex.get('qids', []) and not any(p.search(r['name']) for p in pats)]

    # places for "near X"
    pts = [(e['lat'], e['lon'], e['tags']['name']) for e in places if e.get('tags', {}).get('name') and 'lat' in e]
    # ids
    used = {}
    for r in sorted(recs, key=lambda r: (rank(r), r['name'])):
        r['place'] = r['loc'] or ('near ' + nearest_place(pts, r['ll']) if pts else '')
        if r['place'] == 'near ':
            r['place'] = ''
        base = slug(r['name']) or 'rock'
        i = base
        if i in used:
            i = base + '-' + (slug(r['place']) or 'x')
        n = 2
        while i in used:
            i = '%s-%d' % (base, n); n += 1
        used[i] = r
        r['id'] = i
    recs = [r for r in recs if r['id'] not in ex.get('ids', [])]

    if not a.no_photos:
        add_photos(recs, raw, a.use_raw)
    else:
        for r in recs:
            r['photos'] = []

    t1q, t1n = set(cur.get('tier1', {}).get('qids', [])), {n.lower() for n in cur.get('tier1', {}).get('names', [])}
    out = []
    for r in recs:
        about = r['about'] or r.get('osm_desc', '')
        if not about or len(about) < 12:
            about = '%s%s.' % (r['kind'], ' ' + r['place'] if r['place'] else '')
        about = about[0].upper() + about[1:]
        if not about.endswith('.'):
            about += '.'
        tier = 1 if (r['wp'] or r['photos'] or r.get('wikidata') in t1q or r['name'].lower() in t1n) else 2
        o = dict(id=r['id'], cat='rocks', name=r['name'], group=r['group'], ll=[round(r['ll'][0], 5), round(r['ll'][1], 5)],
                 approx=bool(r['approx']), place=r['place'], access=r['access'], kind=r['kind'], about=about, url=r['url'])
        if r.get('wikidata'):
            o['wikidata'] = r['wikidata']
        o.update(tier=tier, src='; '.join(r['srcs']), fetched=TODAY, photos=r['photos'])
        out.append(o)
    out.sort(key=lambda o: (o['tier'], o['group'], o['name']))
    validate(out)
    json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)
    summary(out)
    if MISSING:
        log('INCOMPLETE: Wikidata classes not fetched:', ', '.join(MISSING))
        sys.exit(3)


def validate(out):
    ids = set()
    for o in out:
        assert o['id'] not in ids, 'dup id ' + o['id']
        ids.add(o['id'])
        assert in_gb(*o['ll']), 'outside GB ' + o['id']
        assert o['group'] in GROUP_PRIORITY and o['access'] in ('open', 'limited', 'gone', 'unknown', 'private')
        for p in o['photos']:
            assert FREE_LIC.match(p['license']) and not BAD_LIC.search(p['license']), 'licence ' + o['id']
    json.loads(json.dumps(out))
    log('validated', len(out))


def summary(out):
    from collections import Counter
    c = Counter((o['group'], o['tier']) for o in out)
    for g in GROUP_PRIORITY:
        log('%-20s tier1 %4d  tier2 %4d' % (g, c[(g, 1)], c[(g, 2)]))
    log('total', len(out), 'with photos', sum(1 for o in out if o['photos']), 'two photos', sum(1 for o in out if len(o['photos']) == 2))
    log('multi-source', sum(1 for o in out if ';' in o['src']))


if __name__ == '__main__':
    main()
