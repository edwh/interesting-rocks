import json,re,time,urllib.request,urllib.parse
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
P=json.load(open('writer-raw/picked2.json'))
import unicodedata as U
N=lambda x:U.normalize('NFC',x)
P={N(k):v for k,v in P.items()}
P[N('Emily Brontë')]['q']='Q80146'
def api(**p):
    p['format']='json'
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(p),headers={'User-Agent':UA}),timeout=40))
        except Exception: time.sleep(3)
    return {}
def inuk(lat,lon): return 49.8<=lat<=60.95 and -10.8<=lon<=1.9
def get(q):
    e=api(action='wbgetentities',ids=q,props='labels|descriptions|sitelinks|claims')['entities'][q]
    c=e.get('claims',{})
    co=c.get('P625',[{}])[0].get('mainsnak',{}).get('datavalue',{}).get('value')
    if not co: return None
    return dict(q=q,label=e['labels'].get('en',{}).get('value',''),desc=e.get('descriptions',{}).get('en',{}).get('value',''),lat=co['latitude'],lon=co['longitude'],
      wp=e.get('sitelinks',{}).get('enwiki',{}).get('title',''),web=(c.get('P856',[{}])[0].get('mainsnak',{}).get('datavalue',{}).get('value','')),sl=len(e.get('sitelinks',{})))
out=[]
for line in open('writer-scripts/data/places_specs.txt'):
    f=line.rstrip('\n').split('|')
    if len(f)<5: continue
    a,s,g,k,acc=f[:5]; a=N(a); note=f[5] if len(f)>5 else ''
    if a not in P: print('NOAUTHOR',a); continue
    cands=[]
    if re.fullmatch(r'Q\d+',s): ids=[s]
    else:
        ids=[x['id'] for x in api(action='wbsearchentities',search=s,language='en',limit=5,type='item').get('search',[])]
    for q in ids:
        r=get(q)
        if r and inuk(r['lat'],r['lon']): cands.append(r)
        time.sleep(0.2)
    best=cands[0] if cands else None
    print('%-22s %-40s -> %s'%(a[:22],s[:40],('%s %s | %s | %.4f,%.4f | alt:%s'%(best['q'],best['label'][:40],best['desc'][:40],best['lat'],best['lon'],[c['label'][:20] for c in cands[1:3]])) if best else 'NONE'),flush=True)
    out.append(dict(author=a,aq=P[a]['q'],n=P[a]['n'],spec=s,group=g,kind=k,access=acc,note=note,cands=cands))
json.dump(out,open('writer-raw/resolved_places.json','w'),indent=1)
