import json,re,time,urllib.request,urllib.parse,unicodedata as U
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
recs=json.load(open('writer-raw/stageE.json'))
def norm(s): return U.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
def wpsearch(q):
    for i in range(3):
        try:
            j=json.load(urllib.request.urlopen(urllib.request.Request('https://en.wikipedia.org/w/api.php?'+urllib.parse.urlencode(dict(action='opensearch',search=q,limit=3,format='json')),headers={'User-Agent':UA}),timeout=30)); return j[1]
        except Exception: time.sleep(2)
    return []
GEN={'church','museum','house','statue','memorial','grave','cemetery','the','and','saint','centre','hall','college','square'}
out=[]
for r in recs:
    g=r['group'];a=r['author'];k=r['kind']
    if g=='Plaque':
        t=r['_ins']; yrs=re.search(r'(\d{4})\s*(?:[-–]|to)\s*(\d{4})',t.split('lived')[-1] if 'lived' in t else t)
        if re.search(r'born',t,re.I) and not re.search(r'lived',t,re.I): v='was born here'
        elif re.search(r'died',t,re.I) and not re.search(r'lived',t,re.I): v='died here'
        elif re.search(r'wrote|worked',t,re.I) and not re.search(r'lived',t,re.I): v='wrote or worked here'
        else: v='lived here'
        r['about']='Plaque recording that %s %s.'%(a,v)
        r['note']='Plaque data from Open Plaques (PDDL).'
    else:
        if g=='House museum': r['about']='%s associated with %s.'%(k,a)
        elif g=='Grave': r['about']='Burial place or last resting place of %s: %s.'%(a,k[0].lower()+k[1:])
        elif g=='Statue or memorial': r['about']='%s commemorating %s.'%(k,a)
        else: r['about']='%s with a link to %s.'%(k,a)
        notes=[]
        if r['_desc']: notes.append(r['_desc'][0].upper()+r['_desc'][1:]+'.' if not r['_desc'].endswith('.') else r['_desc'])
        if r['_note']: notes.append(r['_note'])
        if g=='Grave': notes.append('Coordinates are for the burial ground, not the individual grave.')
        if r.get('approx') and g!='Grave': notes.append('Position approximate.')
        if r['access']=='limited': notes.append('Private or restricted: view from outside only, or check opening arrangements.')
        r['note']=' '.join(notes)
        url=''
        if r['_wp']: url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(r['_wp'].replace(' ','_'))
        elif r['_web']: url=r['_web']
        else:
            want=[t for t in re.findall(r'[a-z]{4,}',norm(r['name'])) if t not in GEN]
            for t in wpsearch(r['name']):
                if any(w in norm(t) for w in want): url='https://en.wikipedia.org/wiki/'+urllib.parse.quote(t.replace(' ','_')); break
            time.sleep(0.3)
        if r.get('wikidata') and not url: url='https://www.wikidata.org/wiki/'+r['wikidata']
        if url: r['url']=url
    for key in [x for x in r if x.startswith('_')]: del r[key]
    if not r.get('note'): r.pop('note',None)
    out.append(r)
json.dump(out,open('writer-raw/stageF.json','w'),indent=1,ensure_ascii=False)
print(len(out),sum(1 for r in out if 'url' not in r))
