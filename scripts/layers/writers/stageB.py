import json,re,math
P=json.load(open('writer-raw/picked2.json'));d=json.load(open('writer-raw/plaques.json'));cur=json.load(open('writer-raw/curated.json'))
info={}
for k,v in P.items(): info.setdefault(v['q'],(k,v['n'],v.get('sl',0)))
info['Q80146']=('Emily Brontë',1,100)
def dist(a,b,c,d_): return math.hypot((a-c)*111000,(b-d_)*69000)
BL={7948,8370,33096,54584,2357,8285,10023,43935,7880,12964 if False else 0,8660 if False else 0,59650,1189,30325}
out=[]
for q,l in d.items():
    name,n,sl=info[q]
    sur=name.split()[-1].lower().rstrip('.')
    cand=[]
    for p in l:
        if not (p['latitude'] and 49.8<=p['latitude']<=60.95 and -10.8<=p['longitude']<=1.9 and p['is_accurate_geolocation']): continue
        t=p['inscription']
        if sur not in t.lower() and name.split()[0].lower() not in t.lower(): continue
        if re.search(r'former pupils|pupils include|educated here|stayed here|visited|met here|school',t,re.I): continue
        if sur not in t.lower()[:80] and not t.lower().startswith(('in this house','here lived','in a house')): continue
        if p['id'] in BL: continue
        sc=0
        if re.search(r'born',t,re.I): sc+=3
        if re.search(r'lived',t,re.I): sc+=2
        if re.search(r'wrote|worked',t,re.I): sc+=2
        if re.search(r'\d{4}\s*[-–to ]+\s*\d{4}',t): sc+=1
        cand.append((sc,p))
    cand.sort(key=lambda x:-x[0])
    k=3 if n>=5 else 2 if n>=2 else (1 if sl>=50 else 0)
    chosen=[]
    for sc,p in cand:
        if len(chosen)>=k: break
        if sc==0: continue
        if any(dist(p['latitude'],p['longitude'],c['latitude'],c['longitude'])<40 for c in chosen): continue
        if any(dist(p['latitude'],p['longitude'],c['lat'],c['lon'])<60 and c['author']==name for c in cur): continue
        chosen.append(p)
    for p in chosen:
        if p['id']==12964 and name!='Charlotte Brontë': continue
        out.append(dict(author=name,aq=q,n=n,**p))
print(len(out))
json.dump(out,open('writer-raw/plaques_sel.json','w'),indent=1)
for o in out: print(o['author'],o['id'],o['inscription'][:80].replace('\n',' '))
