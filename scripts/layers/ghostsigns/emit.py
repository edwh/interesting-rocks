import json,re,collections,unicodedata,string,sys
import os; D=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
groups=json.load(open(RAW+'groups.json'));pc=json.load(open(RAW+'pc.json'))
REG={'North East':'North East','North West':'North West','Yorkshire and The Humber':'Yorkshire','East Midlands':'Midlands','West Midlands':'Midlands','East of England':'East of England','London':'London','South East':'South East','South West':'South West'}
STREET=re.compile(r"\b((?:[A-Z][\w'’]+ ){1,3}(?:Street|Road|Lane|Avenue|Place|Square|Terrace|Walk|Row|Gate|Way|Parade|Hill|Close|Drive|Crescent|Broadway|Wynd|Vennel|Market|Quay|Bridge|Passage|Arcade|Yard|Mews))\b")
GEN=r"(?:ghost|faded|old|painted|former|fading|large|another|hand[- ]?painted|wall|advertising|advert|sign|brick|a|the|an|one|two|another|\d+)"
def clean(t):
    t=re.sub(r' - geograph\.org\.uk - \d+','',t)
    t=re.sub(r'[“”‘’"`]',"'",t) if False else t
    t=re.sub(r'\s*\(?\b\d{1,2}\)?\s*$','',t) if False else t
    return t.strip(" ,-_.")
def brand_from(title,desc):
    t=clean(title)
    t=re.sub(r"^[A-Z]{1,2}\d{2,10} : ",'',t)
    cands=[]
    m=re.search(r"ghost[ -]?signs? (?:for|advertising|of|to)\s+(?:the\s+)?(.{3,45}?)(?:,| on | in | at | - | by |\.|$| \(|\d{2}$)",t,re.I)
    if m:cands.append(m.group(1))
    m=re.search(r"^(?:(?:an?|the)\s+)?(?:faded |old |former |painted |fading )?['\"]?(.{2,40}?)['\"]?[,:]? +(?:\(.*?\) +)?(?:ghost[ -]?signs?|ghost advert\w*|painted (?:wall )?sign|faded (?:wall )?sign|advert)\b",t,re.I)
    if m:cands.append(m.group(1))
    m=re.search(r"ghost[ -]?signs?\s*[:(\-–]\s*['\"]?([^'\",()]{3,40})",t,re.I)
    if m:cands.append(m.group(1))
    m=re.search(r"\b(?:advertis\w+|for)\s+(?:the\s+)?([A-Z][\w'&.\- ]{2,30}?)(?:,|\.| on | in | at |$)",desc)
    if not cands and m and re.search(r'ghost|faded|painted',desc,re.I):cands.append(m.group(1))
    for c in cands:
        c=c.strip(" '\"-–,:")
        c=re.sub(r"^(?:(?:an?|the)\s+)",'',c,flags=re.I)
        if len(c)<3 or len(c)>40:continue
        if re.fullmatch(r"(?:%s|\s|[-,])*"%GEN,c,re.I):continue
        if re.search(r"\b(?:street|road|lane|avenue|square|wall|building|shop|corner|house|junction|church|pub|station|\bin\b|\bon\b|\bat\b|view|looking|showing|detail|photo|side|former|beside|opposite|near)\b",c,re.I):continue
        if re.search(r"\d{2,}",c):continue
        if c.islower():c=string.capwords(c)
        return c
    return None
def slug(s):
    s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')
GONE=re.compile(r"(?:ghost[- ]?sign|sign|advert\w*|painting|wall)(?: has| have)? (?:now |since |subsequently )?(?:been (?:repainted|removed|obliterated|destroyed|demolished|covered over)|no longer (?:exists?|visible|there)|gone|was (?:painted over|destroyed|demolished|removed)|is (?:now )?(?:gone|lost|no longer (?:visible|there|exists?)))|(?:has|have) now been (?:repainted|painted over|removed)|\[Edit[^\]]*no longer exists",re.I)
for g in groups:
    ex=[x for x in g if not x['approx']] or g
    g[0]['_ll']=(sum(x['lat'] for x in ex)/len(ex),sum(x['lon'] for x in ex)/len(ex));g[0]['_approx']=not [x for x in g if not x['approx']]
import datetime
FETCHED=datetime.date.today().isoformat()
out=[];seen=collections.Counter()
for g in groups:
    if re.search(r'not a ghost sign',' '.join(x['title'] for x in g),re.I):continue
    p=pc[('%.5f,%.5f')%g[0]['_ll']]
    lat,lon=g[0]['_ll']
    region=REG.get(p['region']) if p['country']=='England' else p['country']
    if region not in('Scotland','Wales') and region not in REG.values():
        continue
    par=re.sub(r',? ?unparished area','',p['parish'] or '').strip()
    town=par or p['admin_district'] or ''
    if p['admin_district'] in('City of Edinburgh','City of Westminster'):town=p['admin_district'].replace('City of ','')
    if p['admin_district']=='Hammersmith and Fulham' or p['admin_district'] in('Westminster','Lambeth','Southwark','Greenwich','Brent','Ealing','Wandsworth'):town=p['admin_district']
    # nicer town for London boroughs etc. keep admin_district
    txt=' '.join(x['title']+' . '+x['desc'] for x in g)
    st=None
    for x in g:
        m=STREET.search(x['title']) or STREET.search(x['desc'][:300])
        if m:st=m.group(1);break
    if st and re.match(r"^(?:The |A |An |Ghost|Faded|Old|Painted|Sign|Sign on|Another|Former|Large)\b",st):
        st=re.sub(r"^(?:The |A |An |Ghost |Faded |Old |Painted |Sign |Another |Former |Large )+",'',st) or None
    if st and (' ' not in st or len(st)>40):st=None
    town=re.sub(r', City of$','',town)
    place=', '.join([x for x in [st or p['admin_ward'],town] if x])
    place=place or town
    brand=None
    for x in g:
        brand=brand_from(x['title'],x['desc'])
        if brand and (brand.lower() in {(p['admin_district'] or '').lower(),town.lower(),(p['admin_ward'] or '').lower(),'london','edinburgh','glasgow','scotland','wales','england','manchester','leeds','bristol','birmingham','liverpool'} or re.search(r'\b(london|scotland)\b',brand,re.I) or brand.lower().startswith(('ghost','sign','painted'))):brand=None
        if brand:
            brand=brand.replace('^','&').split(':')[-1].strip()
            if brand.isupper() and len(brand)>5:brand=string.capwords(brand.lower())
            if re.search(r"flickr|not a|fragment|mosaic|pharmacy$|travel agent|^blind|^home front|\bSt\b|, [A-Z]\d|ghost|\bsigns?\b|cobbler|^old |^former|unknown|unidentified|^advert|\\bis\\b| with\\b|\\b(and|visible)$|^shops|^impressive|^launderette",brand,re.I) or brand.lower() in (place+' '+town).lower() or (place+' '+town).lower().find(brand.lower().split(',')[0])>=0:brand=None
        if brand:break
    SMALL={'and','&','of','the','for','to','in','&c','co','ltd','son','sons','bros'}
    if brand:
        ws=brand.split()
        bad=re.search(r"\b(half|closeup|close-up|well|lone|preserved|railway|bridge|photographer|photo|view|side|wall|above|below|building|remains|remnants?|traces?|large|small|big|another|several|faded|ghostly|visible|bits?|part|section|painted|sign|signs|advert\w*|shop|shops|window|windows|door|house|street|road|corner|then|now|with|indecipherable|illegible|woodworking|bowes|restored|palimpsest|static|removals|tobacco|rubber|agent|private|taxis|lockups|water|source|mat|from|which|that|this)\b",brand,re.I)
        if bad or ',' in brand or len(ws)>6 or any(w[0].islower() and w.lower() not in SMALL for w in ws if w[0].isalpha()) or re.search(r"[a-z]'S\b",brand) or re.match(r"^(and|&|of|the)\b",brand,re.I):brand=None
    areaname=((st+', ') if st else '')+(town or p['admin_ward'] or '')
    areaname=areaname.strip(', ')
    if brand: name=f"{brand} ghost sign, {areaname}"
    else: name=f"Ghost sign, {areaname}"
    name=re.sub(r'\s+',' ',name)
    if brand: about=f"A faded painted advertisement for {brand} on a wall in {town or areaname}."
    else: about=f"A faded hand-painted advertising sign on a wall in {town or areaname}; the sources do not say what it advertised."
    photos=[]
    seenp=set()
    for x in g:
        if x['photo']['page'] in seenp:continue
        seenp.add(x['photo']['page']);photos.append(x['photo'])
        if len(photos)==3:break
    approx=g[0]['_approx']
    base=slug(name) or 'ghost-sign'
    seen[base]+=1
    idv=base if seen[base]==1 else f"{base}-{seen[base]}"
    if not brand and seen[base]>=1 and False:pass
    out.append(dict(id=idv,cat='ghostsigns',name=name,group='Ghost sign',ll=[round(lat,5),round(lon,5)],**({'approx':True} if approx else {}),
       src=' + '.join(sorted({x['src'] for x in g})),fetched=FETCHED,
       place=place,region=region,access='gone' if GONE.search(txt) and re.search(r'sign|advert',txt,re.I) else 'open',kind='Painted wall sign',tier=1 if (brand or len(g)>=3) else 2,about=about,photos=photos))
json.dump(out,open(sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','layers','ghostsigns.json'),'w'),ensure_ascii=False,indent=1)
print(len(out),sum(1 for o in out if o['name'].startswith('Ghost sign,')),'unnamed;',collections.Counter(o['region'] for o in out),sum(o['access']=='gone' for o in out),sum(1 for o in out if o.get('approx')))
