"""Resolve authors.tsv names to Wikidata QIDs. Decisions live in data/author_matches.json;
only names absent from that file are searched (wbsearchentities + wbgetentities, see requests/).
Writes writer-raw/picked2.json (accepted authors, with current book counts)."""
import csv,json,time,urllib.request,urllib.parse
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
W={'Q36180','Q6625963','Q49757','Q214917','Q4853732','Q28389','Q11774202','Q1930187','Q482980','Q18844224','Q4263842','Q15980158','Q1209498','Q333634','Q10297252','Q37226','Q201788','Q3055126','Q2516866','Q16533','Q1622272','Q187685','Q4964182','Q39631','Q11513337','Q10800557','Q864380','Q3589290','Q1234713','Q13590141','Q12144794','Q5322166'}
def api(**p):
    p['format']='json'
    for i in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(p),headers={'User-Agent':UA}),timeout=30))
        except Exception: time.sleep(2)
    return {}
import os
TSV=os.environ.get('AUTHORS_TSV','authors.tsv')
rows=list(csv.reader(open(TSV),delimiter='\t'))[1:]
MP=os.environ.get('AUTHOR_MATCHES','author_matches.json')  # private: lists every author on the shelves
M=json.load(open(MP))
new=0
for name,n,titles in rows:
    if name in M: continue
    n=int(n); clean=name.strip().rstrip('.').strip()
    ids=[x['id'] for x in api(action='wbsearchentities',search=clean,language='en',limit=8,type='item').get('search',[])]
    best=None
    if ids:
        e=api(action='wbgetentities',ids='|'.join(ids),props='claims|sitelinks|labels')
        c=[]
        for q,v in e.get('entities',{}).items():
            cl=v.get('claims',{})
            if any(x['mainsnak'].get('datavalue',{}).get('value',{}).get('id')!='Q5' for x in cl.get('P31',[])) and 'P31' in cl and not any(x['mainsnak'].get('datavalue',{}).get('value',{}).get('id')=='Q5' for x in cl['P31']): continue
            occ={x['mainsnak'].get('datavalue',{}).get('value',{}).get('id') for x in cl.get('P106',[])}
            if occ&W: c.append((len(v.get('sitelinks',{})),q,v.get('labels',{}).get('en',{}).get('value','')))
        c.sort(reverse=True)
        if c and c[0][0]>=(5 if n>=2 else 30): best=c[0]
    M[name]=dict(status='accepted',q=best[1],label=best[2],sl=best[0],by='auto %s (review titles: %s)'%(time.strftime('%Y-%m-%d'),titles[:80])) if best else dict(status='rejected',reason='no writer match above threshold')
    new+=1; time.sleep(0.2)
json.dump(M,open(MP,'w'),indent=1,ensure_ascii=False)
P={name:dict(q=M[name]['q'],n=int(n),label=M[name].get('label',''),sl=M[name].get('sl',0),titles=titles) for name,n,titles in rows if M[name]['status']=='accepted'}
json.dump(P,open('writer-raw/picked2.json','w'),indent=1)
print('authors: %d accepted, %d new names resolved this run'%(len(P),new))
