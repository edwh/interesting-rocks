import json,re,time,urllib.request,urllib.parse,unicodedata as U
N=lambda x:U.normalize('NFC',x)
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import json as _j
_OV=_j.load(open('writer-scripts/data/place_overrides.json'))
R=json.load(open('writer-raw/resolved_places.json'))
nom=json.load(open('writer-raw/nominatim.json')); nom2=json.load(open('writer-raw/nominatim2.json'))
DROP=_OV['stageA.DROP']
WDQ=_OV['stageA.WDQ']
NOMOVR=_OV['stageA.NOMOVR']
XY=_OV['stageA.XY']

import os as _os,time as _t,urllib.request as _ur,urllib.parse as _up
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
def nmq(q):
    j=nmget('https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':q,'format':'jsonv2','limit':1,'countrycodes':'gb,ie'}))
    return j[0] if j else None
def wdget(q):
    e=json.load(urllib.request.urlopen(urllib.request.Request('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(dict(action='wbgetentities',ids=q,props='labels|descriptions|sitelinks|claims',format='json')),headers={'User-Agent':UA})))['entities'][q]
    c=e['claims'];co=c['P625'][0]['mainsnak']['datavalue']['value']
    return dict(q=q,label=e['labels']['en']['value'],desc=e.get('descriptions',{}).get('en',{}).get('value',''),lat=co['latitude'],lon=co['longitude'],wp=e.get('sitelinks',{}).get('enwiki',{}).get('title',''),web=c.get('P856',[{}])[0].get('mainsnak',{}).get('datavalue',{}).get('value',''))
pts=[]
for r in R:
    s=r['spec']
    if s in DROP: continue
    rec=dict(author=N(r['author']),aq=r['aq'],n=r['n'],group=r['group'],kind=r['kind'],access=r['access'],note=r['note'],spec=s)
    if s in WDQ: x=wdget(WDQ[s]); rec.update(x)
    elif s in NOMOVR:
        x=nmq(NOMOVR[s]); 
        if not x: continue
        rec.update(label=s,lat=float(x['lat']),lon=float(x['lon']),q=None,desc='',wp='',web='',osm=True,osmid=x['osm_type']+' '+str(x['osm_id']),osmtype=x['type'],osmname=x['display_name'][:90])
    elif s in XY and XY[s]:
        rec.update(label="Oscar Wilde Memorial Sculpture",lat=XY[s][0],lon=XY[s][1],q=None,desc='',wp='Oscar Wilde Memorial Sculpture',web='',forceapprox=True)
    elif r['cands']:
        c=r['cands'][0]; rec.update(c)
    else:
        l=nom.get(s) or []
        l2=nom2.get(s) or []
        c=(l or l2)
        if not c: print('MISSING',s); continue
        c=c[0]; rec.update(label=s,lat=c['lat'],lon=c['lon'],q=None,desc='',wp='',web='',osm=True,osmid=c.get('osm',''),osmtype=c['type'],osmname=c['name'])
    pts.append(rec)
print(len(pts))
json.dump(pts,open('writer-raw/curated.json','w'),indent=1)
