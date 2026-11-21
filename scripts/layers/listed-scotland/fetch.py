#!/usr/bin/env python3
"""Scotland listed buildings Category A+B from HES ArcGIS REST (OGL v3.0).
Usage: fetch_listed_scotland.py OUT.json [RAW_DIR]
Endpoint: https://inspire.hes.scot/arcgis/rest/services/HES/HES_Designations/MapServer/0/query
(Server rejects resultOffset/resultRecordCount, so we list object IDs and fetch by id batches.)"""
import json, sys, time, datetime, urllib.request, urllib.parse, os, re
Q = 'https://inspire.hes.scot/arcgis/rest/services/HES/HES_Designations/MapServer/0/query'
UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
out = sys.argv[1]
raw = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'work', 'raw', 'listed-scotland')
os.makedirs(raw, exist_ok=True)
def post(params):
    params['f'] = 'json'
    req = urllib.request.Request(Q, urllib.parse.urlencode(params).encode(), headers={'User-Agent': UA})
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as e:
            print('retry', e, file=sys.stderr); time.sleep(5 * (i + 1))
    raise SystemExit('failed')
ids = sorted(post({'where': "CATEGORY in ('A','B') AND DES_TYPE='Listed Building'", 'returnIdsOnly': 'true'})['objectIds'])
print(len(ids), 'ids')
feats = []
for i in range(0, len(ids), 1000):
    chunk = ids[i:i + 1000]
    d = post({'objectIds': ','.join(map(str, chunk)), 'outFields': '*', 'outSR': 4326, 'returnGeometry': 'true'})
    json.dump(d, open(os.path.join(raw, f'batch{i//1000:03d}.json'), 'w'))
    feats += d['features']
    time.sleep(1)
def tc(s):
    s = re.sub(r'\s+', ' ', s or '').strip()
    if s.isupper():
        s = re.sub(r"[A-Za-z']+", lambda m: m.group(0).capitalize() if m.group(0).lower() not in ('of','the','and','at','on','in','to','for') else m.group(0).lower(), s)
        s = s[:1].upper() + s[1:]
    return s
today = datetime.date.today().isoformat()
# A listing can have several points (one per address or part). Keep one record per listing: the
# designation title and the middle of its points.
groups = {}
for f in feats:
    a, g = f['attributes'], f.get('geometry')
    if not g or a['CATEGORY'] not in ('A', 'B'): continue
    groups.setdefault(a['DES_REF'], []).append((a, g))
res = []
for ref, parts in groups.items():  # ref e.g. LB31
    a = parts[0][0]
    cat = a['CATEGORY']
    title = a.get('ENT_TITLE') if len(parts) == 1 and a.get('ENT_TITLE') else a['DES_TITLE']
    lat = sum(g['y'] for _, g in parts) / len(parts)
    lon = sum(g['x'] for _, g in parts) / len(parts)
    place = ', '.join(x.strip() for x in (a.get('PARBUR'), a.get('LOCAL_AUTH')) if x and x.strip())
    res.append({'id': 'hes-' + ref.lower(), 'name': tc(title),
                'll': [round(lat, 5), round(lon, 5)], 'grade': cat, 'tier': 1 if cat == 'A' else 2,
                'kind': f'Listed building, Category {cat}', 'place': place,
                'url': a['LINK'] or 'https://portal.historicenvironment.scot/designation/' + ref,
                'src': 'hes ' + ref, 'fetched': today})
json.dump(res, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(res), 'records', {c: sum(r['grade'] == c for r in res) for c in 'AB'})
