import json,time,urllib.request,urllib.parse
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
cur=json.load(open('writer-raw/curated.json'));pl=json.load(open('writer-raw/plaques_sel.json'))
pts=[(c['lat'],c['lon']) for c in cur]+[(p['latitude'],p['longitude']) for p in pl]
try: cache=json.load(open('writer-raw/rev.json'))
except Exception: cache={}
for la,lo in pts:
    k='%.5f,%.5f'%(la,lo)
    if k in cache: continue
    for t in range(3):
        try:
            cache[k]=json.load(urllib.request.urlopen(urllib.request.Request('https://nominatim.openstreetmap.org/reverse?'+urllib.parse.urlencode(dict(lat=la,lon=lo,format='jsonv2',zoom=16,addressdetails=1)),headers={'User-Agent':UA}),timeout=30)).get('address',{}); break
        except Exception: time.sleep(3)
    time.sleep(1.1)
    if len(cache)%20==0: json.dump(cache,open('writer-raw/rev.json','w'))
json.dump(cache,open('writer-raw/rev.json','w')); print('DONE',len(cache))
