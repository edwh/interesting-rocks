import json,re,urllib.request,time,collections,html
import os; D=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
groups=json.load(open(RAW+'groups.json'))
for g in groups:
    ex=[x for x in g if not x['approx']] or g
    g_ll=(sum(x['lat'] for x in ex)/len(ex),sum(x['lon'] for x in ex)/len(ex))
    g[0]['_ll']=g_ll;g[0]['_approx']=not [x for x in g if not x['approx']]
# postcodes.io reverse geocoding
import os
cache=json.load(open(RAW+'pc.json')) if os.path.exists(RAW+'pc.json') else {}
def key(ll):return '%.5f,%.5f'%ll
todo=[g[0]['_ll'] for g in groups if key(g[0]['_ll']) not in cache]
def post(geos):
    req=urllib.request.Request('https://api.postcodes.io/postcodes',data=json.dumps({'geolocations':geos}).encode(),headers={'Content-Type':'application/json','User-Agent':'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'})
    return json.load(urllib.request.urlopen(req,timeout=60))['result']
for rad in (500,2000):
    todo=[ll for ll in todo if key(ll) not in cache]
    for i in range(0,len(todo),100):
        chunk=todo[i:i+100]
        res=post([{'latitude':a,'longitude':b,'radius':rad,'limit':1} for a,b in chunk])
        for ll,r in zip(chunk,res):
            if r['result']:
                x=r['result'][0];cache[key(ll)]={k:x.get(k) for k in('region','country','admin_district','admin_ward','parish')}
        time.sleep(.5)
json.dump(cache,open(RAW+'pc.json','w'))
print('unresolved',sum(1 for g in groups if key(g[0]['_ll']) not in cache))
