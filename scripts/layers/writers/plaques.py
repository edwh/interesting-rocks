import json,time,urllib.request,urllib.parse
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
P=json.load(open('writer-raw/picked2.json'))
qs=sorted({v['q'] for v in P.values()}|{'Q80146'})
ids={}
for i in range(0,len(qs),50):
    e=json.load(urllib.request.urlopen(urllib.request.Request('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(dict(action='wbgetentities',ids='|'.join(qs[i:i+50]),props='claims',format='json')),headers={'User-Agent':UA})))
    for q,v in e['entities'].items():
        c=v.get('claims',{}).get('P1430',[])
        if c: ids[q]=[x['mainsnak']['datavalue']['value'] for x in c]
print(len(ids),flush=True)
out={}
for q,l in ids.items():
    for pid in l:
        try:
            r=json.load(urllib.request.urlopen(urllib.request.Request('https://openplaques.org/people/%s/plaques.json'%pid,headers={'User-Agent':UA}),timeout=30))
            out.setdefault(q,[]).extend(r)
        except Exception as e: print('err',q,pid,e)
        time.sleep(0.7)
json.dump(out,open('writer-raw/plaques.json','w'))
print(sum(len(v) for v in out.values()),len(out))
