#!/usr/bin/env python3
"""Build the "plaques" layer: blue and other commemorative plaques in the UK.

Usage:  python3 build_plaques.py OUTPUT.json [--raw DIR] [--refresh] [--no-osm] [--no-photos]

Sources (see SOURCES.md beside this file for licences):
  1. Open Plaques UK data dump (PDDL 1.0) -- the backbone, ~18k plaques.
  2. Wikidata (CC0)  -- P1430 subject ids -> QID + en.wikipedia article; plaque items
                        (P31 commemorative plaque / blue plaque, with P625) not in Open Plaques.
  3. OpenStreetMap (ODbL), from the downloaded extract or Overpass -- historic=memorial + memorial=plaque or blue_plaque; best effort,
                        records that are only in OSM carry "lic":"ODbL" so they can be filtered.
  4. Wikimedia Commons imageinfo -- free-licence photo for Open Plaques photos hosted on Commons.

Raw downloads go to --raw (default scripts/work/raw/plaques) and are cached; --refresh re-downloads.
Standard library only.  Run python with -I.
"""
import argparse, csv, datetime, html, io, json, math, os, re, sys, time, urllib.parse, urllib.request, urllib.error

UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
HERE = os.path.dirname(os.path.abspath(__file__))
S3 = 'https://openplaques.s3.eu-west-2.amazonaws.com/'
OP_FALLBACK = S3 + 'open-plaques-United-Kingdom-2025-12-15.json'
WIKIDATA_SPARQL = 'https://query.wikidata.org/sparql'
WIKIDATA_API = 'https://www.wikidata.org/w/api.php'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
OVERPASS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
            'https://overpass-api.de/api/interpreter',
            'https://overpass.private.coffee/api/interpreter']
TODAY = datetime.date.today().isoformat()
sys.path.insert(0, os.path.join(HERE, '..', '..', 'osm'))
import osm_extract  # answers the OSM query from the downloaded extract when it has been built
DEDUP_M = 25.0


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def http(url, data=None, accept=None, timeout=120, tries=3):
    for n in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers={'User-Agent': UA, **({'Accept': accept} if accept else {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:
            log('  http error', type(e).__name__, str(e)[:100], url[:80])
            if n == tries - 1:
                raise
            time.sleep(5 * (n + 1))


def cached(path, refresh, fetch):
    if os.path.exists(path) and not refresh and os.path.getsize(path) > 0:
        return open(path, 'rb').read()
    b = fetch()
    with open(path, 'wb') as f:
        f.write(b)
    return b


def sparql(query):
    return http(WIKIDATA_SPARQL, urllib.parse.urlencode({'query': query}).encode(), 'application/sparql-results+json', 170)


# ---------- geometry / text helpers
def dist_m(a, b):
    r = 6371000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dl = math.radians(b[1] - a[1]); dp = p2 - p1
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def squash(s):
    return re.sub(r'\s+', ' ', html.unescape(s or '')).strip()


def trim(s, n=200):
    s = squash(s)
    if len(s) <= n:
        return s
    cut = s[:n]
    sp = cut.rfind(' ')
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(' ,;:-') + '…'


def slug(s):
    import unicodedata
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:50] or 'plaque'


STOP = set('the and of in at to for on a an was is by who this here house lived born died plaque blue green street road from his her with were had that has after near site first one'.split())


def toks(s):
    return {t for t in re.findall(r'[a-z0-9]+', squash(s).lower()) if len(t) > 2 and t not in STOP}


def similar(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / min(len(ta), len(tb)) >= 0.4


COLOUR_SUFFIX = re.compile(r'\s+(blue|green|black|bronze|stone|white|brown|grey|gray|red|brushed metal|film cell|brass|marble|slate|yellow|purple|orange|pink|silver|gold|wooden|ceramic|iron|enamel|glass|granite|lead|copper|steel|plastic|unknown colour)?\s*plaque(\s+№\s*\d+)?$', re.I)


def kind_of(colour):
    c = (colour or '').lower()
    return 'Blue plaque' if c == 'blue' else 'Green plaque' if c == 'green' else 'Plaque'


# ---------- Open Plaques
def find_op_url(raw, refresh):
    """Newest UK json dump: try the live /data page, then the Wayback copy, then the known URL."""
    pages = ['https://openplaques.org/data',
             'https://web.archive.org/web/2026/https://openplaques.org/data']
    for p in pages:
        try:
            t = http(p, timeout=40, tries=1).decode('utf8', 'ignore')
            links = sorted(set(re.findall(r'https://openplaques\.s3\.[^"\']*?open-plaques-United-Kingdom-[\d-]+\.json', t)))
            if links:
                return links[-1]
        except Exception:
            pass
    return OP_FALLBACK


def load_op(raw, refresh):
    url = find_op_url(raw, refresh)
    log('Open Plaques dump:', url)
    name = os.path.join(raw, os.path.basename(url))
    data = cached(name, refresh, lambda: http(url, timeout=600))
    return json.loads(data), os.path.basename(url)


# ---------- Wikidata
def load_subjects(raw, refresh):
    q = open(os.path.join(HERE, 'wd-subjects.rq')).read()
    def f():
        return http(WIKIDATA_SPARQL, urllib.parse.urlencode({'query': q}).encode(), 'text/csv', 170)
    data = cached(os.path.join(raw, 'wd-subjects.csv'), refresh, f).decode('utf8')
    out = {}
    for row in csv.DictReader(io.StringIO(data)):
        qid = row['s'].rsplit('/', 1)[-1]
        prev = out.get(row['opid'])
        if prev is None or (row['art'] and not prev[1]):
            out[row['opid']] = (qid, row['art'])
    return out  # OP subject id -> (QID, enwiki url or '')


def load_wd_plaques(raw, refresh):
    q = open(os.path.join(HERE, 'wd-plaques.rq')).read()
    data = cached(os.path.join(raw, 'wd-plaques.json'), refresh, lambda: sparql(q))
    items = {}
    for b in json.loads(data)['results']['bindings']:
        qid = b['i']['value'].rsplit('/', 1)[-1]
        m = re.match(r'Point\(([-\d.]+) ([-\d.]+)\)', b['coord']['value'])
        it = items.setdefault(qid, {'qid': qid, 'll': [round(float(m.group(2)), 5), round(float(m.group(1)), 5)], 'opid': None, 'subj': set(), 'blue': False})
        if 'opid' in b: it['opid'] = b['opid']['value']
        if 'subj' in b: it['subj'].add(b['subj']['value'].rsplit('/', 1)[-1])
        if b['t']['value'].endswith('Q885849'): it['blue'] = True
    return items


def wd_entities(qids, raw, refresh, props):
    """wbgetentities in batches of 50, cached per call set."""
    qids = sorted(qids)
    out = {}
    for i in range(0, len(qids), 50):
        chunk = qids[i:i + 50]
        key = os.path.join(raw, 'wd-ent-%s-%s.json' % (props.replace('|', '_'), slug('-'.join(chunk))[:40] + str(len(chunk)) + chunk[0]))
        url = WIKIDATA_API + '?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': '|'.join(chunk), 'props': props,
                                                           'languages': 'en', 'sitefilter': 'enwiki', 'format': 'json'})
        d = json.loads(cached(key, refresh, lambda: http(url)))
        out.update(d.get('entities', {}))
        time.sleep(0.5)
    return out


def claim_val(ent, prop):
    for c in ent.get('claims', {}).get(prop, []):
        v = c.get('mainsnak', {}).get('datavalue', {}).get('value')
        if v is not None:
            return v
    return None


# ---------- OSM
def tiles():
    la = 49.8
    while la < 60.9:
        lo = -8.7
        while lo < 2.0:
            yield (round(la, 2), round(lo, 2), round(min(la + 1, 60.9), 2), round(min(lo + 1, 2.0), 2))
            lo += 1.0
        la += 1.0


def overpass_tile(t, raw, refresh):
    path = os.path.join(raw, 'osm-%s_%s.json' % (t[0], t[1]))
    if os.path.exists(path) and not refresh:
        return json.load(open(path))
    ql = open(os.path.join(HERE, 'osm-plaques.ql')).read().replace('{{bbox}}', '%s,%s,%s,%s' % t)
    for ep in OVERPASS:
        try:
            d = json.loads(http(ep, urllib.parse.urlencode({'data': ql}).encode(), timeout=90, tries=1))
            if 'elements' in d and 'remark' not in d:
                json.dump(d, open(path, 'w'))
                return d
        except Exception:
            continue
    return None


def load_osm(raw, refresh):
    els, failed, streak = [], [], 0
    if osm_extract.available():  # the downloaded extract answers the whole of the UK in one go
        ql = open(os.path.join(HERE, 'osm-plaques.ql')).read().replace('{{bbox}}', '49.8,-8.7,60.95,2.0')
        els = osm_extract.query(ql)['elements']
    for t in ([] if els else tiles()):
        d = overpass_tile(t, raw, refresh)
        if d is None:
            failed.append(t)
            streak += 1
            if streak >= 4:   # Overpass is down or overloaded: stop rather than burn hours
                log('Overpass unavailable after 4 consecutive tile failures; skipping the rest of OSM')
                failed += [x for x in tiles() if x > t]
                break
        else:
            streak = 0
            els += d['elements']
        time.sleep(1.5)
    seen, out = set(), []
    for e in els:
        k = (e['type'], e['id'])
        if k in seen:
            continue
        seen.add(k)
        c = (e.get('lat'), e.get('lon')) if e['type'] == 'node' else ((e.get('center') or {}).get('lat'), (e.get('center') or {}).get('lon'))
        if c[0] is None:
            continue
        out.append({'ref': '%s %d' % (e['type'], e['id']), 'll': [round(c[0], 5), round(c[1], 5)], 'tags': e.get('tags', {})})
    return out, failed


# ---------- Commons photos
def commons_photos(files, raw, refresh):
    """files: set of Commons file names -> {name: photo record} for free-licence ones."""
    res = {}
    names = sorted(files)
    for i in range(0, len(names), 50):
        chunk = names[i:i + 50]
        key = os.path.join(raw, 'commons-%04d-%s.json' % (i // 50, slug(chunk[0])[:30]))
        url = COMMONS_API + '?' + urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata', 'iiurlwidth': 1280,
            'titles': '|'.join('File:' + n for n in chunk)})
        try:
            d = json.loads(cached(key, refresh, lambda: http(url)))
        except Exception:
            continue
        norm = {x['to']: x['from'] for x in d.get('query', {}).get('normalized', [])}
        for p in d.get('query', {}).get('pages', {}).values():
            ii = (p.get('imageinfo') or [None])[0]
            if not ii:
                continue
            md = ii.get('extmetadata', {})
            lic = squash(md.get('LicenseShortName', {}).get('value', ''))
            free = re.match(r'(CC0|CC BY|CC BY-SA|Public domain|PD|Attribution)', lic, re.I) and 'NC' not in lic and 'ND' not in lic
            if not free:
                continue
            title = p['title'][5:]
            res[norm.get('File:' + title, 'File:' + title)[5:].replace(' ', '_')] = res[title.replace(' ', '_')] = {
                'src': (ii.get('thumburl') or ii['url']).split('?')[0], 'page': ii['descriptionurl'], 'license': lic,
                'artist': trim(re.sub(r'<[^>]+>', '', md.get('Artist', {}).get('value', '')), 120) or 'Unknown',
                'title': trim(re.sub(r'<[^>]+>', '', md.get('ObjectName', {}).get('value', '')) or title.rsplit('.', 1)[0], 120)}
        time.sleep(1)
    return res


def op_commons_file(photo):
    if 'Wikimedia Commons' not in photo.get('attribution', ''):
        return None
    m = re.search(r'Special:FilePath/([^?]+)', photo.get('thumbnail_url', ''))
    return urllib.parse.unquote(m.group(1)).replace(' ', '_') if m else None


# ---------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--raw', default=os.path.join(os.path.dirname(os.path.dirname(HERE)), 'work', 'raw', 'plaques'))
    ap.add_argument('--refresh', action='store_true')
    ap.add_argument('--no-osm', action='store_true')
    ap.add_argument('--no-photos', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.raw, exist_ok=True)

    op, opname = load_op(a.raw, a.refresh)
    subjects = load_subjects(a.raw, a.refresh)
    wdp = load_wd_plaques(a.raw, a.refresh)
    log('open plaques', len(op), 'subjects with qid', len(subjects), 'wikidata plaque items', len(wdp))

    recs = []          # output records (dicts, with private keys prefixed _)
    by_op = {}
    skipped = {'no-coords': 0, 'not-current': 0, 'no-content': 0, 'outside-uk': 0}
    for x in op:
        if x.get('latitude') is None or x.get('longitude') is None:
            skipped['no-coords'] += 1; continue
        if not x.get('is_current', True):
            skipped['not-current'] += 1; continue
        lat, lon = x['latitude'], x['longitude']
        if not (49.8 < lat < 60.9 and -8.7 < lon < 2.0):
            skipped['outside-uk'] += 1; continue
        subj = squash(x.get('subjects'))
        insc = squash(x.get('inscription'))
        title = COLOUR_SUFFIX.sub('', squash(x.get('title')))
        if not subj and not insc:
            skipped['no-content'] += 1; continue
        name = subj or trim(re.split(r'[\r\n]', x.get('inscription') or '')[0], 70)
        qids, art = [], ''
        for p in x.get('people', []):
            m = re.search(r'/people/(\d+)', p.get('uri', ''))
            if m and m.group(1) in subjects:
                q, w = subjects[m.group(1)]
                qids.append(q)
                if w and not art:
                    art = w
        year = (x.get('erected_at') or '')[:4]
        area = (x.get('area') or {}).get('name', '')
        town = area.split(',')[0].strip()
        addr = squash(x.get('address'))
        place = addr if (not town or town.lower() in addr.lower()) else (addr + ', ' + town if addr else town)
        r = {'id': 'plaque-%s-op%d' % (slug(name), x['id']), 'name': name, 'll': [round(lat, 5), round(lon, 5)],
             'kind': kind_of(x.get('colour_name')), 'about': trim(insc) if insc else '', 'place': place, 'year': year,
             'url': art or ('https://www.wikidata.org/wiki/%s' % qids[0] if qids else x.get('uri', '')),
             'subject': name, 'subjectQid': qids[0] if qids else '',
             'tier': 1 if (x.get('colour_name') == 'blue' or art) else 2,
             'src': ['openplaques %d' % x['id']], 'fetched': TODAY, 'photos': [],
             '_qids': set(qids), '_op': x}
        recs.append(r)
        by_op[str(x['id'])] = r
    log('open plaques kept', len(recs), skipped)

    # ---- Wikidata plaque items: merge by P1893, else spatial/subject match, else add
    grid = {}
    def gkey(ll): return (int(ll[0] * 100), int(ll[1] * 60))
    def add_grid(r): grid.setdefault(gkey(r['ll']), []).append(r)
    def near(ll):
        gx, gy = gkey(ll)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for r in grid.get((gx + dx, gy + dy), []):
                    if dist_m(ll, r['ll']) <= DEDUP_M:
                        yield r
    for r in recs: add_grid(r)

    need = set()
    for it in wdp.values():
        if it['opid'] not in by_op:
            need.add(it['qid']); need |= it['subj']
    ents = wd_entities(need, a.raw, a.refresh, 'labels|descriptions|sitelinks|claims') if need else {}
    merged_wd = merged_wd_geo = added_wd = 0
    for it in wdp.values():
        if it['opid'] in by_op:
            by_op[it['opid']]['src'].append('wikidata ' + it['qid']); merged_wd += 1
            by_op[it['opid']]['_qids'] |= it['subj']
            continue
        e = ents.get(it['qid'], {})
        label = e.get('labels', {}).get('en', {}).get('value', '')
        insc_v = claim_val(e, 'P1684')
        insc = squash(insc_v.get('text') if isinstance(insc_v, dict) else '')
        slabels = [ents.get(q, {}).get('labels', {}).get('en', {}).get('value', '') for q in sorted(it['subj'])]
        cand = [r for r in near(it['ll']) if (it['subj'] & r['_qids']) or similar(' '.join(slabels) + ' ' + label, r['name'] + ' ' + r['about'])]
        if cand:
            cand[0]['src'].append('wikidata ' + it['qid']); merged_wd_geo += 1
            cand[0]['_qids'] |= it['subj']
            continue
        sname = ', '.join(s for s in slabels if s) or COLOUR_SUFFIX.sub('', label)
        if not sname or re.match(r'^Q\d+$', sname):
            continue
        art = ''
        for q in sorted(it['subj']):
            t = ents.get(q, {}).get('sitelinks', {}).get('enwiki', {}).get('title')
            if t:
                art = 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_')); break
        inc = claim_val(e, 'P571')
        yr = re.match(r'\+?(\d{4})', inc['time']).group(1) if isinstance(inc, dict) and inc.get('time') else ''
        sq = sorted(it['subj'])[0] if it['subj'] else ''
        r = {'id': 'plaque-%s-%s' % (slug(sname), it['qid'].lower()), 'name': sname, 'll': it['ll'],
             'kind': 'Blue plaque' if it['blue'] else 'Plaque', 'about': trim(insc or e.get('descriptions', {}).get('en', {}).get('value', '')),
             'place': '', 'year': yr, 'url': art or 'https://www.wikidata.org/wiki/' + it['qid'], 'subject': sname,
             'subjectQid': sq, 'tier': 1 if (it['blue'] or art) else 2, 'src': ['wikidata ' + it['qid']],
             'fetched': TODAY, 'photos': [], '_qids': set(it['subj']), '_wdimg': claim_val(e, 'P18')}
        recs.append(r); add_grid(r); added_wd += 1
    log('wikidata: merged by P1893', merged_wd, 'merged by location', merged_wd_geo, 'added', added_wd)

    # ---- OSM
    osm_added = osm_merged = 0
    osm_failed = []
    if not a.no_osm:
        osm, osm_failed = load_osm(a.raw, a.refresh)
        log('osm elements', len(osm), 'failed tiles', len(osm_failed))
        for o in osm:
            t = o['tags']
            if t.get('historic') != 'memorial' or t.get('memorial') not in ('plaque', 'blue_plaque'):
                continue
            insc = squash(t.get('inscription') or t.get('description') or '')
            sname = squash(t.get('subject') or t.get('name') or '')
            sq = squash(t.get('subject:wikidata', '')).split(';')[0]
            hit = None
            opid = re.search(r'\d+', t.get('openplaques:id', '') or t.get('ref:openplaques', '') or '')
            if opid and opid.group(0) in by_op:
                hit = by_op[opid.group(0)]
            if not hit:
                for r in near(o['ll']):
                    if (sq and sq in r['_qids']) or similar(sname + ' ' + insc, r['name'] + ' ' + r['about']):
                        hit = r; break
            if hit:
                hit['src'].append('osm ' + o['ref']); osm_merged += 1
                if not hit['subjectQid'] and sq.startswith('Q'):
                    hit['subjectQid'] = sq
                continue
            if not (sname or insc):
                continue
            name = sname or trim(insc.split('.')[0], 70)
            col = (t.get('colour') or t.get('plaque_colour') or ('blue' if t.get('memorial') == 'blue_plaque' else '')).lower()
            addr = squash(' '.join(filter(None, [t.get('addr:housenumber'), t.get('addr:street')])))
            r = {'id': 'plaque-%s-%s' % (slug(name), o['ref'].replace(' ', '')), 'name': name, 'll': o['ll'],
                 'kind': kind_of(col), 'about': trim(insc), 'place': squash(', '.join(filter(None, [addr, t.get('addr:city') or t.get('addr:town')]))),
                 'year': (t.get('start_date') or '')[:4], 'url': 'https://www.openstreetmap.org/%s' % o['ref'].replace(' ', '/'),
                 'subject': name, 'subjectQid': sq if sq.startswith('Q') else '',
                 'tier': 1 if col == 'blue' else 2, 'src': ['osm ' + o['ref']], 'fetched': TODAY, 'photos': [],
                 '_qids': {sq} if sq else set(), 'lic': 'ODbL'}
            recs.append(r); add_grid(r); osm_added += 1
        log('osm merged into existing', osm_merged, 'osm-only added', osm_added)

    # ---- Wikipedia link / tier refresh for OSM-only plaques with a QID
    q_only = {r['subjectQid'] for r in recs if r['subjectQid'] and not r['url'].startswith('https://en.wikipedia')}
    if q_only and len(q_only) < 3000:
        e2 = wd_entities(q_only, a.raw, a.refresh, 'sitelinks')
        for r in recs:
            t = e2.get(r['subjectQid'], {}).get('sitelinks', {}).get('enwiki', {}).get('title')
            if t and not r['url'].startswith('https://en.wikipedia'):
                r['url'] = 'https://en.wikipedia.org/wiki/' + urllib.parse.quote(t.replace(' ', '_')); r['tier'] = 1

    # ---- Commons photos (tier 1 only: one photo per plaque)
    nphotos = 0
    if not a.no_photos:
        want = {}
        for r in recs:
            if r['tier'] != 1:
                continue
            f = None
            if '_op' in r:
                ps = sorted(r['_op'].get('photos', []), key=lambda p: ('close' not in (p.get('shot_name') or ''), (p.get('shot_name') or '')))
                for p in ps:
                    f = op_commons_file(p)
                    if f: break
            elif r.get('_wdimg'):
                f = str(r['_wdimg']).replace(' ', '_')
            if f:
                want[r['id']] = f
        ph = commons_photos(set(want.values()), a.raw, a.refresh)
        for r in recs:
            f = want.get(r['id'])
            if f and f in ph:
                r['photos'] = [ph[f]]; nphotos += 1
        log('photos attached', nphotos, 'of', len(want), 'candidates')

    # ---- finish
    out = []
    for r in recs:
        r['src'] = '; '.join(r['src'])
        for k in [k for k in r if k.startswith('_')]:
            del r[k]
        out.append(r)
    ids = {}
    for r in out:
        if r['id'] in ids:
            r['id'] += '-2'
        ids[r['id']] = 1
    out.sort(key=lambda r: (r['tier'], r['id']))
    with open(a.out, 'w') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    kc, tc = {}, {}
    for r in out:
        kc[r['kind']] = kc.get(r['kind'], 0) + 1; tc[r['tier']] = tc.get(r['tier'], 0) + 1
    log('WROTE', a.out, len(out), 'records; kinds', kc, 'tiers', tc, 'osm failed tiles', len(osm_failed))
    if osm_failed:
        log('WARNING: Overpass failed for %d tiles (OSM data incomplete); re-run to resume from cache' % len(osm_failed))


if __name__ == '__main__':
    main()
