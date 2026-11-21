#!/usr/bin/env python3
"""Build the milestones layer. Usage: run.py <output.json> [--raw DIR] [--refresh]
Sources: OSM (ODbL; downloaded extract, or Overpass), Historic England NHLE (OGL), Wikimedia Commons (free-licence photos)."""
import sys, os, json, re, time, math, html, datetime, urllib.request, urllib.parse
UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(HERE, '..', '..', 'work', 'layers', 'milestones.json')
RAW = os.path.join(HERE, '..', '..', 'work', 'raw', 'milestones')
if '--raw' in sys.argv: RAW = sys.argv[sys.argv.index('--raw') + 1]
REFRESH = '--refresh' in sys.argv
os.makedirs(RAW, exist_ok=True)
TODAY = datetime.date.today().isoformat()
sys.path.insert(0, os.path.join(HERE, '..', '..', 'osm'))
import osm_extract  # answers the OSM query from the downloaded extract when it has been built
OVERPASS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter',
            'https://overpass.kumi.systems/api/interpreter',
            'https://overpass-api.de/api/interpreter',
            'https://overpass.private.coffee/api/interpreter']
NHLE = 'https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/0/query'
COMMONS = 'https://commons.wikimedia.org/w/api.php'

def http(url, data=None, timeout=150):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None,
                                 headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8')

def cached(name, fn):
    p = os.path.join(RAW, name)
    if os.path.exists(p) and not REFRESH:
        return json.load(open(p))
    d = fn(); json.dump(d, open(p, 'w')); return d

def in_gb(lat, lon):
    if not (49.8 <= lat <= 60.95 and -8.7 <= lon <= 1.9): return False
    if 51.3 < lat < 55.4 and lon < -5.5: return False          # island of Ireland
    if 54.0 < lat < 54.45 and -4.9 < lon < -4.3: return False  # Isle of Man
    return True

def hav(a, b):
    R = 6371000; p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1]); dp = p2 - p1
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))

# ---------- OSM ----------
def fetch_tile(s, w, n, e):
    q = open(os.path.join(HERE, 'queries/overpass.ql.tmpl')).read().format(south=s, west=w, north=n, east=e)
    for attempt in range(20):
        ep = OVERPASS[0] if attempt % 4 != 3 else OVERPASS[(attempt // 4) % (len(OVERPASS) - 1) + 1]
        try:
            t = http(ep, {'data': q}, timeout=100)
            d = json.loads(t)
            if re.search(r'runtime error|out of memory|timed out', d.get('remark', ''), re.I): raise RuntimeError('partial: ' + d['remark'][:80])
            time.sleep(6)
            return d['elements']
        except Exception as ex:
            print('  retry', ep, str(ex)[:60], file=sys.stderr); time.sleep(min(20, 2 + attempt))
    raise SystemExit('overpass tile failed %s' % ((s, w, n, e),))

# Each Overpass query has ~15 s fixed cost on the public mirrors, so use few big tiles
# (2 deg lat x 3 deg lon) and a coarse land mask per lat row to skip open sea.
ROWS = [(49.8, 51.8, -6.4, 1.9), (51.8, 53.8, -5.5, 1.9), (53.8, 55.8, -5.2, 0.5),
        (55.8, 57.8, -6.6, -1.0), (57.8, 59.8, -8.0, -1.7), (59.8, 60.95, -1.8, -0.7)]

def get_osm():
    if osm_extract.available():  # the downloaded extract answers the whole of the UK in one go
        q = open(os.path.join(HERE, 'queries/overpass.ql.tmpl')).read().format(south=49.8, west=-8.7, north=60.95, east=1.9)
        return osm_extract.query(q)['elements']
    els = {}
    for s, n, lo, hi in ROWS:
        w = lo
        while w < hi:
            e = min(w + 3, hi)
            tile = cached('osm3_%.1f_%.1f_%.1f_%.1f.json' % (s, w, n, e), lambda: fetch_tile(s, w, n, e))
            for el in tile: els[(el['type'], el['id'])] = el
            w = e
        print('osm row', s, len(els), file=sys.stderr)
    return list(els.values())

# ---------- NHLE ----------
def get_nhle():
    where = open(os.path.join(HERE, 'queries/nhle.where.txt')).read().strip()
    def go():
        feats, off = [], 0
        while True:
            d = json.loads(http(NHLE, {'where': where, 'outSR': 4326, 'outFields': 'ListEntry,Name,Grade',
                                       'f': 'json', 'resultOffset': off, 'resultRecordCount': 2000,
                                       'orderByFields': 'ListEntry'}))
            fs = d.get('features', [])
            feats += fs; off += len(fs)
            if not fs or not d.get('exceededTransferLimit'): break
            time.sleep(1)
        return feats
    return cached('nhle.json', go)

# ---------- helpers ----------
def title(s):
    small = {'of', 'the', 'and', 'on', 'at', 'in', 'to', 'by', 'from', 'near'}
    out = []
    for i, w in enumerate(s.lower().split()):
        if re.match(r'^[ab]\d+[a-z]?(\(m\))?$', w) or re.match(r'^(m|a|b)\d+$', w): out.append(w.upper())
        elif i and w in small: out.append(w)
        else: out.append(re.sub(r"(^|[-(/'])([a-z])", lambda m: m.group(1) + m.group(2).upper(), w) if not w[0].isdigit() else w)
    r = ' '.join(out)
    r = re.sub(r'\bNgr\b', 'NGR', r)
    r = re.sub(r'\b([A-Z])([a-z])\b(?= \d)', lambda m: m.group(1) + m.group(2).upper(), r)
    return r

def kind_of(name, tags=None):
    n = name.lower()
    if tags and tags.get('historic') == 'guidepost': return 'Guide post'
    if 'guide post' in n or 'guidepost' in n or 'finger' in n: return 'Guide post'
    if 'milepost' in n or 'mile post' in n or 'mile-post' in n: return 'Milepost'
    return 'Milestone'

# ---------- Commons ----------
FREE = re.compile(r'^(CC BY(-SA)?( \d\.\d)?( [A-Za-z ]+)?|CC0.*|Public domain.*|PD.*|CC-BY.*|Attribution.*|No restrictions)$', re.I)
def clean(s): return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()

def photo_from_page(p):
    ii = (p.get('imageinfo') or [None])[0]
    if not ii: return None
    m = ii.get('extmetadata', {})
    lic = clean(m.get('LicenseShortName', {}).get('value'))
    art = clean(m.get('Artist', {}).get('value'))
    if not lic or not art or art.lower() in ('unknown', 'anonymous', '?'): return None
    if re.search(r'NC|ND|GFDL|fair use|copyrighted', lic, re.I) and not re.search(r'CC BY(-SA)? ', lic): return None
    if re.search(r'-NC|-ND|NonCommercial', lic, re.I): return None
    if not re.match(r'^(CC BY|CC0|Public domain|PD|CC-BY|CC-Zero)', lic, re.I): return None
    if ii.get('mime', '') not in ('image/jpeg', 'image/png', 'image/webp'): return None
    return {'src': ii.get('thumburl') or ii['url'], 'page': ii['descriptionurl'], 'license': lic,
            'artist': art[:120], 'title': p['title'].replace('File:', '')}

IIPROP = {'prop': 'imageinfo|coordinates', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 800,
          'iiextmetadatafilter': 'LicenseShortName|Artist', 'colprop': 'type', 'coprimary': 'primary'}

def api(params):
    p = {'action': 'query', 'format': 'json', 'formatversion': 2}; p.update(params)
    for a in range(5):
        try:
            d = json.loads(http(COMMONS + '?' + urllib.parse.urlencode(p))); time.sleep(0.5); return d
        except Exception as ex:
            print('  commons retry', str(ex)[:60], file=sys.stderr); time.sleep(5*(a+1))
    return {}

def crawl_categories():
    """Recursively list files in Milestones-in-{England,Scotland,Wales}; returns {title: page}."""
    def go():
        seen, todo, files = set(), ['Category:Milestones in England', 'Category:Milestones in Scotland',
                                    'Category:Milestones in Wales'], {}
        while todo:
            c = todo.pop()
            if c in seen: continue
            seen.add(c)
            cont = {}
            while True:
                d = api(dict({'generator': 'categorymembers', 'gcmtitle': c, 'gcmtype': 'file|subcat',
                              'gcmlimit': 50, **IIPROP}, **cont))
                for p in d.get('query', {}).get('pages', []):
                    if p['title'].startswith('Category:'): todo.append(p['title'])
                    else: files[p['title']] = p
                if 'continue' in d: cont = d['continue']
                else: break
            print('  cat', c, len(files), file=sys.stderr)
        return files
    return cached('commons_cats.json', go)

def files_info(titles):
    out = {}
    for i in range(0, len(titles), 40):
        d = api(dict({'titles': '|'.join(titles[i:i+40])}, **IIPROP))
        for p in d.get('query', {}).get('pages', []): out[p['title']] = p
    return out

def cat_files(cat, limit=3):
    d = api({'list': 'categorymembers', 'cmtitle': cat, 'cmtype': 'file', 'cmlimit': 10})
    return [m['title'] for m in d.get('query', {}).get('categorymembers', [])]

# ---------- main ----------
def main():
    osm = get_osm(); nhle = get_nhle()
    print('osm elements', len(osm), 'nhle', len(nhle), file=sys.stderr)
    recs = []
    for f in nhle:
        a = f['attributes']; g = f.get('geometry') or {}
        pts = g.get('points') or ([[g['x'], g['y']]] if 'x' in g else [])
        if not pts: continue
        lon, lat = pts[0][0], pts[0][1]
        if not in_gb(lat, lon): continue
        raw = a['Name'] or ''
        k = kind_of(raw)
        nm = title(raw)
        name = nm if nm.lower().startswith(('milestone', 'milepost', 'guide', 'mile')) else nm
        grade = (a.get('Grade') or '').strip()
        recs.append({'id': 'nhle-%s' % a['ListEntry'], 'name': name, 'll': [round(lat, 6), round(lon, 6)],
                     'kind': k, 'about': '', 'place': '', 'grade': grade, 'tier': 1,
                     'src': 'nhle %s' % a['ListEntry'], 'fetched': TODAY, 'photos': [], '_nhle': True})
    nh = [r for r in recs]
    stats = {'nhle': len(nh), 'osm_raw': 0, 'merged': 0, 'osm_dropped_outside': 0}
    osmrecs = []
    for el in osm:
        t = el.get('tags', {})
        if el.get('type') == 'node': lat, lon = el['lat'], el['lon']
        else:
            c = el.get('center');
            if not c: continue
            lat, lon = c['lat'], c['lon']
        if not in_gb(lat, lon): stats['osm_dropped_outside'] += 1; continue
        if t.get('historic') not in ('milestone', 'guidepost'): continue
        if t.get('disused') or t.get('historic') == 'guidepost' and t.get('information'): pass
        stats['osm_raw'] += 1
        osmrecs.append((el, t, lat, lon))
    # spatial grid for NHLE
    grid = {}
    for r in nh: grid.setdefault((int(r['ll'][0]*100), int(r['ll'][1]*100)), []).append(r)
    def near_nhle(lat, lon):
        best = None
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for r in grid.get((int(lat*100)+dx, int(lon*100)+dy), []):
                    d = hav((lat, lon), r['ll'])
                    if d <= 30 and (best is None or d < best[0]): best = (d, r)
        return best[1] if best else None
    for el, t, lat, lon in osmrecs:
        ref = '%s %s' % (el['type'], el['id'])
        insc = clean(t.get('inscription') or '').replace('\n', ' / ')
        nm = t.get('name') or ''
        hw = t.get('ref') or t.get('highway_ref') or ''
        place = ' '.join(x for x in [t.get('addr:street') or '', t.get('addr:place') or '', t.get('is_in') or ''] if x)
        k = 'Guide post' if t['historic'] == 'guidepost' else ('Milepost' if re.search(r'milepost|mile post', (nm + ' ' + t.get('milestone', '') + t.get('material', '')).lower()) else 'Milestone')
        m = near_nhle(lat, lon)
        if m:
            stats['merged'] += 1
            m['src'] += '; osm ' + ref
            m.setdefault('_osm', []).append(t)
            if insc and not m['about']: m['about'] = insc
            if t.get('operator') and not m['place']: m['place'] = t['operator']
            continue
        if nm: name = nm
        elif insc: name = ('Milestone: ' + insc)[:80]
        else: name = {'Milestone': 'Milestone', 'Milepost': 'Milepost', 'Guide post': 'Guide post'}[k] + (', ' + hw if hw else '')
        about = insc or ''
        if not about:
            bits = [x for x in [t.get('material'), t.get('operator'), t.get('direction') and 'faces ' + t['direction'], t.get('description')] if x]
            about = ('Recorded in OpenStreetMap' + (': ' + ', '.join(bits) if bits else '') + '.')
        if not place: place = t.get('operator') or ''
        osmrecs_out = {'id': 'osm-%s%s' % (el['type'][0], el['id']), 'name': name, 'll': [round(lat, 6), round(lon, 6)],
                       'kind': k, 'about': about, 'place': place, 'tier': 1 if insc else 2,
                       'src': 'osm ' + ref, 'fetched': TODAY, 'photos': [], '_osm': [t], '_insc': bool(insc)}
        recs.append(osmrecs_out)
    for r in recs:
        for t in r.get('_osm', []):
            if t.get('inscription') and r['tier'] != 1: r['tier'] = 1
        if r['about'] == '' and r.get('_nhle'):
            r['about'] = 'Listed %s %s.' % ('Grade ' + r['grade'] if r.get('grade') else 'structure', r['kind'].lower())
        if r.get('_nhle'): r['about'] = r['about'] or ''
    # ---- photos ----
    cats = crawl_categories()
    pool = []
    for tl, p in cats.items():
        ph = photo_from_page(p)
        co = p.get('coordinates')
        if ph and co: pool.append((co[0]['lat'], co[0]['lon'], ph))
    pgrid = {}
    for lat, lon, ph in pool: pgrid.setdefault((int(lat*100), int(lon*100)), []).append((lat, lon, ph))
    stats['commons_geotagged_free'] = len(pool)
    # explicit OSM tags
    tagged = {}
    for r in recs:
        for t in r.get('_osm', []):
            wc = t.get('wikimedia_commons')
            if wc: tagged.setdefault(r['id'], []).append(wc.split(';')[0].strip())
    need = sorted({w for v in tagged.values() for w in v if w.startswith('File:')} - set(cats))
    info = dict(cats); info.update(files_info(need) if need else {})
    for rid, ws in tagged.items():
        r = next(x for x in recs if x['id'] == rid)
        for w in ws:
            if w.startswith('File:'):
                ph = photo_from_page(info[w]) if w in info else None
                if ph: r['photos'].append(ph)
            elif w.startswith('Category:'):
                for ft in cat_files(w):
                    pg = info.get(ft) or files_info([ft]).get(ft)
                    ph = photo_from_page(pg) if pg else None
                    if ph and len(r['photos']) < 3: r['photos'].append(ph)
    # nearby geotags
    for r in recs:
        lat, lon = r['ll']; cand = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for plat, plon, ph in pgrid.get((int(lat*100)+dx, int(lon*100)+dy), []):
                    d = hav((lat, lon), (plat, plon))
                    if d <= 25: cand.append((d, ph))
        for d, ph in sorted(cand, key=lambda x: x[0]):
            if len(r['photos']) >= 3: break
            if all(ph['page'] != q['page'] for q in r['photos']): r['photos'].append(ph)
    # ---- finalise ----
    out = []
    for r in recs:
        if r['photos'] or r.get('grade') or r.get('_insc') or r['about'] and not r['about'].startswith('Recorded in OpenStreetMap'): r['tier'] = 1 if (r['photos'] or r.get('grade') or r.get('_insc')) else r['tier']
        if r.get('_nhle') is None and not r['photos'] and not r.get('_insc'): r['tier'] = 2
        if not r.get('grade'): r.pop('grade', None)
        for k in [k for k in r if k.startswith('_')]: r.pop(k)
        out.append(r)
    ids = set(); fin = []
    for r in out:
        if r['id'] in ids: continue
        ids.add(r['id']); fin.append(r)
    fin.sort(key=lambda r: (r['tier'], r['id']))
    json.dump(fin, open(OUT, 'w'), ensure_ascii=False, indent=0)
    from collections import Counter
    stats['total'] = len(fin); stats['by_kind'] = Counter(r['kind'] for r in fin)
    stats['by_tier'] = Counter(r['tier'] for r in fin); stats['with_photo'] = sum(1 for r in fin if r['photos'])
    stats['photos'] = sum(len(r['photos']) for r in fin)
    print(json.dumps(stats, indent=1, default=dict))

main()
