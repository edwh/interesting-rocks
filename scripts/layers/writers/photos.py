import json,re,time,html,urllib.request,urllib.parse,unicodedata as U
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
recs=json.load(open('writer-raw/stageD.json'))
def api(base,**p):
    p['format']='json'
    for i in range(3):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(base+'?'+urllib.parse.urlencode(p),headers={'User-Agent':UA}),timeout=40))
        except Exception: time.sleep(3)
    return {}
C='https://commons.wikimedia.org/w/api.php'
GEN={'church','museum','house','statue','memorial','grave','cemetery','churchyard','cathedral','hall','street','square','college','plaque','blue','the','and','saint','abbey','centre','center','road','place','court','park','theatre','school','inn','monument','shop','gaol','prison','window','tomb'}
def norm(s): return U.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
def toks(s): return [t for t in re.findall(r"[a-z]{4,}",norm(s)) if t not in GEN]
ALLOW=re.compile(r'^(CC BY(-SA)? \d\.\d|CC0|Public domain|PD[- ]|CC-BY|CC BY)',re.I)
def licok(l): return bool(l) and ALLOW.match(l) and not re.search(r'NC|ND|GFDL|fair|non-?free',l,re.I)
import math
def dist(a,b,c,d): return math.hypot((a-c)*111000,(b-d)*69000)
def info(titles,ll=None,R=700):
    out=[]
    for i in range(0,len(titles),20):
        d=api(C,action='query',titles='|'.join(titles[i:i+20]),prop='imageinfo|coordinates',iiprop='url|extmetadata|mime',iiurlwidth=1280,coprimary='all',colimit=50)
        for pg in d.get('query',{}).get('pages',{}).values():
            ii=(pg.get('imageinfo') or [None])[0]
            if not ii or ii.get('mime') not in ('image/jpeg','image/png','image/webp','image/tiff','image/gif'): continue
            co=(pg.get('coordinates') or [None])[0]
            if co and ll and dist(co['lat'],co['lon'],ll[0],ll[1])>R: continue
            hasco=bool(co)
            md=ii.get('extmetadata',{})
            lic=md.get('LicenseShortName',{}).get('value','')
            if not licok(lic): continue
            art=re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',md.get('Artist',{}).get('value','')))).strip() or 'Unknown'
            out.append(dict(src=ii.get('thumburl') or ii['url'],page=ii['descriptionurl'],license=lic,artist=art[:120],title=pg['title'].replace('File:',''),_geo=hasco))
    return out
def search(q,n=8):
    d=api(C,action='query',list='search',srsearch=q,srnamespace=6,srlimit=n)
    return [x['title'] for x in d.get('query',{}).get('search',[])]
def geo(la,lo,r=80):
    d=api(C,action='query',list='geosearch',gscoord='%s|%s'%(la,lo),gsradius=r,gsnamespace=6,gslimit=20)
    return [x['title'] for x in d.get('query',{}).get('geosearch',[])]
def p18(q):
    d=api('https://www.wikidata.org/w/api.php',action='wbgetentities',ids=q,props='claims')
    c=d.get('entities',{}).get(q,{}).get('claims',{}).get('P18',[])
    return ['File:'+c[0]['mainsnak']['datavalue']['value']] if c else []
BADN=re.compile(r'\b(map|logo|flag|coat of arms|signature|poster|cover|diagram)\b',re.I)

def need_name(t,toklist):
    nt=norm(t); hits=sum(1 for w in toklist if w in nt)
    return hits>=min(2,len(toklist)) and hits>0
for n,r in enumerate(recs):
    sur=norm(r['author'].split()[-1]).strip('.'); first=norm(r['author'].split()[0]).strip('.')
    g=r['group']; ll=r['ll']; titles=[]; strict=[]
    if g=='Plaque':
        titles=[t for t in geo(ll[0],ll[1],45) if sur in norm(t) or 'plaque' in norm(t)]
        road=norm(r['name'].split(', ')[-1]) if ', ' in r['name'] else ''
        if not titles and road:
            titles=[t for t in search('%s plaque %s'%(r['author'],road.title()),6) if sur in norm(t) and road.split()[0] in norm(t)]
        ph=info(titles,ll,150) if titles else []
    elif g=='Grave':
        place=r['name'].split(', ')[-1]
        for q in ['%s grave'%r['author'],'%s grave %s'%(r['author'],place),'%s tomb %s'%(r['author'],place)]:
            titles+=[t for t in search(q,6) if sur in norm(t) and re.search(r'grave|tomb|headstone|burial|memorial|churchyard|cemetery',norm(t))]
        titles+=[t for t in geo(ll[0],ll[1],400) if sur in norm(t)]
        titles=[t for t in dict.fromkeys(titles) if (sur in norm(t) and first in norm(t)) or True]
        ph=info(list(dict.fromkeys(titles))[:12],ll,900)
        ph=[p for p in ph if p['_geo'] or (first in norm(p['title']))]
    else:
        want=toks(r['name'])
        if r.get('wikidata'): titles+=p18(r['wikidata'])
        cand=[]
        for q in [r['name'],'%s %s'%(r['name'],r['place'])]:
            for t in search(q,8):
                if want and need_name(t,want) and not BADN.search(t): cand.append(t)
        cand+=[t for t in geo(ll[0],ll[1],120) if not BADN.search(t)][:6]
        titles+=cand
        ph=info(list(dict.fromkeys(titles))[:14],ll,800)
        # non-geotagged files only if title matches name tokens
        ph=[p for p in ph if p['_geo'] or need_name(p['title'],want) or r.get('wikidata') and False]
    for p in ph: p.pop('_geo',None)
    r['photos']=ph[:2]
    print(n,r['id'],len(ph),flush=True)
    time.sleep(0.3)
json.dump(recs,open('writer-raw/stageE.json','w'),indent=1)
print('DONE')
