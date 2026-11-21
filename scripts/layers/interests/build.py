import json,re,math,os,sys,time,urllib.request,urllib.parse,collections,html
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import os as _os
_REPO=_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
R=_os.path.join(_REPO,'scripts','work','raw','interests')+'/';L=_os.path.join(_REPO,'scripts','work','layers')+'/'
def jl(n):
    p=R+n
    return json.load(open(p)) if os.path.exists(p) else []
def get(url,data=None,tries=4):
    for i in range(tries):
        try:
            rq=urllib.request.Request(url,data,{'User-Agent':UA})
            return json.load(urllib.request.urlopen(rq,timeout=90))
        except Exception as e:
            print('retry',e,file=sys.stderr);time.sleep(4*(i+1))
    return None
def ingb(la,lo):
    if not(49.9<la<60.9 and -7.7<lo<1.9):return False
    if lo<-5.45 and 51.3<la<55.35:return False   # Ireland / NI
    if la<51.0 and lo<-2.0 and False:return False
    return True
def dist(a,b):
    return math.hypot((a[0]-b[0])*111,(a[1]-b[1])*111*math.cos(math.radians(a[0])))
def pt(s):
    m=re.match(r'Point\(([-\d.e]+) ([-\d.e]+)\)',s);return [float(m.group(2)),float(m.group(1))]
BAD=re.compile(r'\b(fuck|shit|cunt)\b',re.I)
def kebab(s):
    s=re.sub(r'[^a-z0-9]+','-',s.lower().replace("'",'')).strip('-');return s[:60] or 'x'
# ---------- candidates ----------
def wdrecs(theme,fn):
    out=[]
    for d in jl('wd-'+theme+'.json'):
        ll=pt(d['co'])
        if not ingb(*ll) or BAD.search(d['name']) or re.match(r'^Q\d+$',d['name']):continue
        r=fn(d)
        if not r:continue
        r.update(name=d['name'],ll=ll,wikidata=d['q'],src='wikidata '+d['q'],_photos=d['photos'][:3],
                 url=d.get('wp'),_desc=d.get('desc',''),_loc=d.get('loc'),year=d.get('inc'),_score=r.get('_score',0)+(3 if d['photos'] else 0)+(3 if d.get('wp') else 0))
        out.append(r)
    return out
def osmrecs(fname,fn):
    out=[]
    for e in jl(fname):
        t=e['tags'];ll=[e.get('lat') or e['center']['lat'],e.get('lon') or e['center']['lon']]
        if not ingb(*ll) or not t.get('name'):continue
        r=fn(t)
        if not r:continue
        r.update(name=t['name'],ll=ll,src='osm %s %s'%(e['type'],e['id']),wikidata=t.get('wikidata'),_photos=[],_commons=t.get('wikimedia_commons'),
                 url=None,_desc='',_loc=None,_score=r.get('_score',0)+(2 if t.get('wikidata') else 0))
        out.append(r)
    return out
def has(d,*c):return any(x in d['cls'] for x in c)
def wells_wd(d):return {'group':'Holy well','kind':'Holy well','access':'open'}
def wells_osm(t):
    n=t['name']
    if re.fullmatch(r'(Holy|Wishing|The Wishing)? ?Well',n,re.I) or n.lower() in('well','spring'):return None
    if re.search(r'Saint (Bronagh|Malachy)|Lough|Co\. ',n):return None
    return {'group':'Holy well','kind':'Holy well or spring','access':'open'}
def pre_wd(d):
    c=d['cls']
    if has(d,'stone circle','recumbent stone circle','four poster stone circle'):g,s='Stone circle',4
    elif has(d,'henge'):g,s='Henge',4
    elif has(d,'dolmen','portal tomb','wedge tomb'):g,s='Dolmen or cromlech',3
    elif has(d,'menhir','standing stones'):g,s='Standing stone',1
    elif has(d,'Gorsedd stones'):g,s='Gorsedd circle',0
    else:g,s='Prehistoric monument',0
    return {'group':g,'kind':g,'access':'open','_score':s}
def pre_osm(t):
    # Older tagging: historic=standing_stone, site_type=*; current: archaeological_site=megalith + megalith_type=*
    h=t.get('historic');st=t.get('site_type','');mt=t.get('megalith_type','')
    if h=='stone_circle' or 'stone_circle' in (st,mt):g='Stone circle'
    elif h=='standing_stone' or mt in('menhir','standing_stone'):g='Standing stone'
    elif 'henge' in (st,mt):g='Henge'
    elif mt in('dolmen','portal_tomb','wedge_tomb'):g='Dolmen or cromlech'
    elif mt=='alignment':g='Stone row'
    else:g='Megalith'
    return {'group':g,'kind':g,'access':'open','_score':3 if g in('Stone circle','Henge') else 1}
def caves_wd(d):
    if has(d,'grotto','shell grotto'):return None
    if has(d,'show mine'):g,s='Show mine',5
    elif has(d,'show cave'):g,s='Show cave',5
    elif has(d,'cave with prehistoric art'):g,s='Cave',4
    elif has(d,'sea cave'):g,s='Sea cave',1
    else:g,s='Cave',1
    return {'group':g,'kind':g,'access':'limited' if s>=5 else 'open','_score':s}
def caves_osm(t):
    n=t['name']
    if t.get('tourism') or t.get('historic')=='mine':g,s='Show cave or mine',4
    else:g,s='Cave',1
    return {'group':g,'kind':g,'access':'limited','_score':s}
def follies_wd(d):
    if has(d,'grotto','shell grotto'):g='Grotto'
    elif has(d,'faux lighthouse','folly tower','folly'):g='Folly'
    else:g='Folly'
    return {'group':g,'kind':g,'access':'limited','_score':1}
def hill_wd(d):return {'group':'Hill figure','kind':'Hill figure','access':'open','_score':5}
def trees_wd(d):return {'group':'Ancient tree','kind':'Notable tree','access':'open','_score':3}
def trees_osm(t):
    n=t['name']
    if re.search(r'memorial|millen|baby|holocaust|peace|coronation|jubilee|wedding|commemor|climbing|history|christmas|apple|cherry|plum|pear|mulberry',n,re.I):return None
    if not re.search(r'Oak|Yew|Elm|Beech|Chestnut|Thorn|Lime|Sycamore|Ash|Hornbeam|Pine|Cedar',n):return None
    if re.fullmatch(r'(Ancient |Old |Mature |Veteran )?(Oak|Ash|Beech|Yew|Elm|Horse Chestnut|Sweet Chestnut|Sycamore|Lime|Pine)( Tree)?\.?',n,re.I) and not t.get('wikidata'):return None
    return {'group':'Ancient tree','kind':'Notable tree','access':'open','_score':1}
def merge(*lists):
    out=[]
    for lst in lists:
        for r in lst:
            dup=None
            for o in out:
                if (r.get('wikidata') and r.get('wikidata')==o.get('wikidata')) or (dist(r['ll'],o['ll'])<0.25 and (r['name'].lower()==o['name'].lower() or dist(r['ll'],o['ll'])<0.04)):
                    dup=o;break
            if dup:
                dup['_score']=max(dup['_score'],r['_score'])
                for k in('wikidata','url','_commons'):
                    if not dup.get(k) and r.get(k):dup[k]=r[k]
                dup['_photos']=dup['_photos']+[p for p in r['_photos'] if p not in dup['_photos']]
                if not dup.get('src','').count(r['src']):dup['src']+='; '+r['src']
            else:out.append(r)
    return out
def pick(recs,n):
    recs=sorted(recs,key=lambda r:(-r['_score'],r['name']));return recs
# ---------- Commons green men ----------
def greenmen():
    d=jl('commons-greenman.json');ok=lambda c:ingb(*c)
    PUB=re.compile(r'pub|inn\b|sign|hotel|festival|jack in|morris|restaurant|brewery|public house|kitchen|house|road|street|avenue|lane|mural|statue|sculpture|graffiti',re.I)
    CH=re.compile(r'church|minster|cathedral|abbey|priory|chapel|misericord|boss|capital|carving|corbel|font|pew|screen|rood|porch|chancel|nave|choir|bench end|foliate',re.I)
    items=[]
    for t,v in d.items():
        if not ok(v['ll']):continue
        cats=' '.join(v['cats'])
        if PUB.search(t) and not re.search(r'church|minster|cathedral|abbey|misericord|boss',t,re.I):continue
        if re.search(r'\bpub\b|public house|\binn\b',cats,re.I):continue
        if not CH.search(t+' '+cats):continue
        items.append((t,v))
    cl=[]
    for t,v in items:
        for c in cl:
            if dist(c['ll'],v['ll'])<0.2:c['f'].append((t,v));break
        else:cl.append({'ll':v['ll'],'f':[(t,v)]})
    out=[]
    for c in cl:
        cats=collections.Counter(x for t,v in c['f'] for x in v['cats'] if re.search(r'church|minster|cathedral|abbey|priory|chapel|St |Saint',x) and not re.search(r'photograph|Buildings in|Images|Files|Content|interior\)? of|by ',x))
        if cats:name=re.sub(r'^Category:','',cats.most_common(1)[0][0]);name=re.sub(r'\s*\((interior|exterior|[a-z ]+)\)$','',name);name=re.sub(r'^(Ceiling|Interior|Roof|Nave|Exterior) of ','',name)
        else:
            name=re.sub(r'^File:','',c['f'][0][0]);name=re.split(r' - |\.jpg|\.JPG|\(',name)[0].strip(' ,')
        out.append({'name':name+' (Green Man)' if not re.search('Green Man',name) else name,'ll':c['ll'],'group':'Green Man carving','kind':'Foliate head carving','access':'limited','_score':len(c['f']),
                    'src':'commons '+c['f'][0][0],'_files':[t for t,v in c['f']],'_photos':[],'url':None,'_desc':'','_loc':None,'wikidata':None,'approx':True})
    return out
# ---------- region/locality via postcodes.io ----------
RMAP={'North East':'North East','North West':'North West','Yorkshire and The Humber':'Yorkshire','East Midlands':'Midlands','West Midlands':'Midlands','East of England':'East of England','London':'London','South East':'South East','South West':'South West'}
def regions(recs):
    for i in range(0,len(recs),100):
        b=recs[i:i+100]
        body=json.dumps({'geolocations':[{'longitude':r['ll'][1],'latitude':r['ll'][0],'radius':2000,'limit':1} for r in b]}).encode()
        rq=urllib.request.Request('https://api.postcodes.io/postcodes',body,{'User-Agent':UA,'Content-Type':'application/json'})
        try:res=json.load(urllib.request.urlopen(rq,timeout=90))['result']
        except Exception as e:print('pc fail',e);res=[{'result':None}]*len(b)
        for r,x in zip(b,res):
            rs=x.get('result') if x else None
            if rs:
                p=rs[0];c=p.get('country')
                r['region']='Scotland' if c=='Scotland' else 'Wales' if c=='Wales' else RMAP.get(p.get('region'),None)
                r['_pc']=p.get('parish') or p.get('admin_district')
            if not r.get('region'):
                la,lo=r['ll'];r['region']='Scotland' if la>55.5 or (la>54.95 and lo<-2.3 and lo>-5 and la>55.0) else 'Wales' if (lo<-2.65 and 51.3<la<53.4 and False) else 'North East' if la>54.5 and lo>-2 else 'North West' if la>53 and lo<-2.2 else 'South West' if la<51.5 and lo<-2.5 else 'Midlands'
                r['approx']=True
        time.sleep(.5)
# ---------- photos ----------
OKL=re.compile(r'^(CC BY(-SA)? [\d.]+( \w+)?|CC0.*|Public domain.*|PD.*|CC BY(-SA)?)$',re.I)
def free(l):
    l=l.strip()
    if re.search(r'NC|ND|GFDL|fair use|non',l,re.I) and not re.match(r'CC0|Public',l):return False
    return bool(re.match(r'^(CC BY|CC0|Public domain|PD)',l,re.I))
def photoinfo(titles):
    out={}
    titles=list(dict.fromkeys(titles))
    for i in range(0,len(titles),40):
        b=titles[i:i+40]
        u='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','format':'json','prop':'imageinfo','iiprop':'url|extmetadata','iiurlwidth':1280,'titles':'|'.join(b)})
        r=get(u)
        if not r:continue
        norm={x['to']:x['from'] for x in r['query'].get('normalized',[])}
        for pg in r['query']['pages'].values():
            ii=pg.get('imageinfo')
            if not ii:continue
            ii=ii[0];m=ii.get('extmetadata',{})
            lic=m.get('LicenseShortName',{}).get('value','')
            if not free(lic):continue
            art=html.unescape(re.sub(r'<[^>]+>','',m.get('Artist',{}).get('value',''))).strip() or 'Unknown'
            t=pg['title'];out[norm.get(t,t)]={'src':ii.get('thumburl') or ii['url'],'page':ii['descriptionurl'],'license':lic,'artist':art[:120],'title':t.replace('File:','')}
            out[t]=out[norm.get(t,t)]
        time.sleep(.3)
    return out
def wdinfo(qids):
    out={}
    qids=list(dict.fromkeys(q for q in qids if q))
    for i in range(0,len(qids),50):
        b=qids[i:i+50]
        r=get('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode({'action':'wbgetentities','format':'json','ids':'|'.join(b),'props':'claims|descriptions|sitelinks','languages':'en','sitefilter':'enwiki'}))
        if not r:continue
        for q,e in r.get('entities',{}).items():
            cl=e.get('claims',{});ph=[]
            for c in cl.get('P18',[]):
                try:ph.append('File:'+c['mainsnak']['datavalue']['value'])
                except:pass
            sl=e.get('sitelinks',{}).get('enwiki',{}).get('title')
            out[q]={'photos':ph,'desc':e.get('descriptions',{}).get('en',{}).get('value',''),'wp':'https://en.wikipedia.org/wiki/'+urllib.parse.quote(sl.replace(' ','_')) if sl else None}
        time.sleep(.3)
    return out
def finish(key,recs,outpath=None,fetched=None,ov=None):
    ov=ov or {}
    recs=[r for r in recs if not any(x in r['src'].split('; ') for x in ov.get('exclude_ids',[])) and r['name'] not in ov.get('exclude_names',[])]
    regions(recs)
    # wikidata enrichment for osm-origin items
    need=[r['wikidata'] for r in recs if r.get('wikidata') and not r['_photos']]
    wi=wdinfo(need)
    for r in recs:
        w=wi.get(r.get('wikidata'))
        if w:
            r['_photos']=[p if p.startswith('File:') else 'File:'+p for p in w['photos']]
            if not r.get('url'):r['url']=w['wp']
            if not r['_desc']:r['_desc']=w['desc']
        if r.get('_commons','') and r['_commons'].startswith('File:') and not r['_photos']:r['_photos']=[r['_commons']]
        r['_photos']=[p if p.startswith('File:') else 'File:'+urllib.parse.unquote(p.split('/')[-1]) for p in r['_photos']]
        if r.get('_files'):r['_photos']=r['_files'][:4]
    info=photoinfo([p for r in recs for p in r['_photos']])
    out=[];ids=set()
    for r in recs:
        ph=[]
        for p in r['_photos']:
            x=info.get(p) or info.get(p.replace('_',' '))
            if x and x not in ph:ph.append(x)
            if len(ph)==2:break
        place=r.get('_loc') or r.get('_pc') or ''
        if re.match(r'^(Q\d+|London Borough of .*)$',place) :place=re.sub('London Borough of ','',place)
        about=r['_desc'].strip()
        if not about or about.lower() in('folly','hill figure','cave','menhir','stone circle'):
            about='%s%s.'%(r['group'],' at '+place if place else '')
            about=about[0].upper()+about[1:]
        else:about=about[0].upper()+about[1:]
        if r['group']=='Green Man carving':about='Foliate-head (Green Man) carving photographed at this location; the map position is where the photo was taken.'
        i=kebab(r['name']);b=i;n=2
        while i in ids:i=b+'-'+str(n);n+=1
        ids.add(i)
        rec={'id':i,'cat':key,'name':r['name'],'group':r['group']}
        if r.get('year') and re.match(r'^\d{4}$',r['year']) and r['year']!='0000':rec['year']=r['year']
        rec.update({'ll':[round(r['ll'][0],5),round(r['ll'][1],5)]})
        if r.get('approx') or r['group'] in('Green Man carving',):rec['approx']=True
        rec.update({'src':r['src'],'place':place,'region':r['region'],'access':r['access'],'kind':r['kind'],'about':about})
        if r.get('wikidata'):rec['wikidata']=r['wikidata']
        if r.get('url'):rec['url']=r['url']
        rec['photos']=ph
        rec['tier']=1 if (ph or r.get('url') or r['group'] in('Show cave','Show mine','Hill figure') or any(x in r['src'].split('; ') for x in ov.get('include_tier1',[]))) else 2
        rec['fetched']=fetched
        out.append(rec)
    json.dump(out,open(outpath or L+key+'.json','w'),indent=1,ensure_ascii=False)
    print(key,len(out),'photos',sum(1 for x in out if x['photos']),'tier1',sum(1 for x in out if x['tier']==1),flush=True)
    return out
