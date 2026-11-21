#!/usr/bin/env python3
"""Wales listed buildings Grade I + II* from Cadw via DataMapWales WFS (OGL v3.0).
Usage: fetch_listed_wales.py OUT.json [RAW_DIR]
Endpoint: https://datamap.gov.wales/geoserver/inspire-wg/ows  typeNames=inspire-wg:Cadw_ListedBuildings
WFS 2.0.0, outputFormat=application/json, srsName=EPSG:4326, CQL_FILTER Grade IN ('I','II*'), paged by startIndex/count."""
import json, sys, time, datetime, urllib.request, urllib.parse, os, re
BASE = 'https://datamap.gov.wales/geoserver/inspire-wg/ows'
UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
out = sys.argv[1]
raw = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'work', 'raw', 'listed-wales')
os.makedirs(raw, exist_ok=True)
feats, start, N = [], 0, 1000
while True:
    p = {'service': 'WFS', 'version': '2.0.0', 'request': 'GetFeature', 'typeNames': 'inspire-wg:Cadw_ListedBuildings',
         'outputFormat': 'application/json', 'srsName': 'EPSG:4326', 'sortBy': 'RecordNumber',
         'cql_filter': "Grade IN ('I','II*')", 'startIndex': start, 'count': N}
    req = urllib.request.Request(BASE + '?' + urllib.parse.urlencode(p), headers={'User-Agent': UA})
    for i in range(4):
        try: d = json.load(urllib.request.urlopen(req, timeout=120)); break
        except Exception as e: print('retry', e, file=sys.stderr); time.sleep(5 * (i + 1))
    else: raise SystemExit('failed')
    json.dump(d, open(os.path.join(raw, f'page{start//N:03d}.json'), 'w'))
    feats += d['features']
    if len(d['features']) < N: break
    start += N; time.sleep(1)
today = datetime.date.today().isoformat()
def tc(s):
    s = re.sub(r'\s+', ' ', s or '').strip()
    if s.isupper(): s = s.title()
    return s
res = []
for f in feats:
    a, g = f['properties'], f['geometry']
    c = g['coordinates']
    if g['type'] == 'MultiPoint': c = c[0]
    n = a['RecordNumber']; gr = a['Grade']
    res.append({'id': f'cadw-{n}', 'name': tc(a['Name']), 'll': [round(c[1], 5), round(c[0], 5)], 'grade': gr,
                'tier': 1 if gr == 'I' else 2, 'kind': f'Listed building, Grade {gr}',
                'place': ', '.join(x for x in (a.get('Community'), a.get('UnitaryAuthority')) if x),
                'url': f'https://cadwpublic-api.azurewebsites.net/reports/listedbuilding/FullReport?lang=en&id={n}',
                'src': f'cadw {n}', 'fetched': today})
json.dump(res, open(out, 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(res), 'records', {g: sum(r['grade'] == g for r in res) for g in ('I', 'II*')})
