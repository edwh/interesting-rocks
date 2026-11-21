import json,time,urllib.request,urllib.parse
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import json as _j
_OV=_j.load(open('writer-scripts/data/place_overrides.json'))
Q=_OV['nominatim.Q']
































































Q["Emsworth Hampshire Threepwood"]="Emsworth, Hampshire"
Q["Hogarth House Richmond"]="Hogarth House, Hounslow Road? Richmond"

import time as _t,urllib.request as _ur,urllib.parse as _up
_NC='writer-raw/nominatim_cache.json'
try: _C=json.load(open(_NC))
except Exception: _C={}
def nmget(url):
    """Nominatim GET with on-disk cache and >=1.1 s between live requests (usage policy)."""
    if url in _C: return _C[url]
    for i in range(3):
        try:
            r=json.load(_ur.urlopen(_ur.Request(url,headers={'User-Agent':'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'}),timeout=30)); break
        except Exception: r=None; _t.sleep(3)
    _t.sleep(1.2)
    if r is not None: _C[url]=r; json.dump(_C,open(_NC,'w'))
    return r
nm=nmget
R=json.load(open('writer-raw/resolved_places.json'))
out={}
for r in R:
    if r['cands'] or r['spec'] in out: continue
    q=Q.get(r['spec'])
    if not q: print('noq',r['spec']); continue
    j=nm('https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':q,'format':'jsonv2','limit':3,'countrycodes':'gb,ie','addressdetails':0}))
    out[r['spec']]=[dict(lat=float(x['lat']),lon=float(x['lon']),name=x['display_name'][:90],type=x['type'],osm=x['osm_type']+' '+str(x['osm_id'])) for x in (j or [])]
    print(r['spec'][:40],'->',out[r['spec']][:1],flush=True)
json.dump(out,open('writer-raw/nominatim.json','w'),indent=1)
