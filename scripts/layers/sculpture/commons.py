import requests,re,html,time
UA={'User-Agent':'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'}
API='https://commons.wikimedia.org/w/api.php'
FREE=re.compile(r'^(CC BY(-SA)? [0-9.]+( [A-Za-z]+)?|CC0.*|Public domain|PD.*|CC BY(-SA)? [0-9.]+ .*)$',re.I)
def strip(s):
    s=re.sub(r'<style.*?</style>','',s or '',flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>','',s)).strip()
    if '{' in t: t=t.split('}')[-1].strip()
    return re.sub(r'\s+',' ',t)
def get(params):
    for i in range(4):
        r=requests.get(API,params=dict(params,format='json'),headers=UA,timeout=40)
        if r.status_code==200: return r.json()
        time.sleep(3)
    return {}
def info(titles):
    d=get({'action':'query','titles':'|'.join(titles),'prop':'imageinfo','iiprop':'url|extmetadata|mime','iiurlwidth':1280})
    out=[]
    for p in d.get('query',{}).get('pages',{}).values():
        ii=(p.get('imageinfo') or [None])[0]
        if not ii or not ii.get('mime','').startswith('image/jpeg') and not ii.get('mime','').startswith('image/png'): continue
        m=ii['extmetadata']; lic=strip(m.get('LicenseShortName',{}).get('value',''))
        if not FREE.match(lic) or 'NC' in lic or 'ND' in lic: continue
        if m.get('NonFree',{}).get('value')=='true': continue
        out.append({'src':ii['thumburl'],'page':ii['descriptionurl'],'license':lic,'artist':strip(m.get('Artist',{}).get('value','')) or 'Unknown','title':p['title'].replace('File:','')})
    return out
def search(q,n=15):
    d=get({'action':'query','list':'search','srsearch':q,'srnamespace':6,'srlimit':n})
    return [x['title'] for x in d.get('query',{}).get('search',[])]
def category(cat,n=30):
    d=get({'action':'query','list':'categorymembers','cmtitle':'Category:'+cat,'cmtype':'file','cmlimit':n})
    return [x['title'] for x in d.get('query',{}).get('categorymembers',[])]
def geo(lat,lon,rad=800,n=20):
    d=get({'action':'query','list':'geosearch','gscoord':f'{lat}|{lon}','gsradius':rad,'gsnamespace':6,'gslimit':n})
    return [x['title'] for x in d.get('query',{}).get('geosearch',[])]
def photos(q=None,cat=None,ll=None,kw=None,k=3):
    titles=[]
    if cat: titles+=category(cat)
    if q: titles+=search(q)
    if ll and len(titles)<3: titles+=geo(*ll)
    seen=[];[seen.append(t) for t in titles if t not in seen]
    res=[]
    for i in range(0,len(seen),20):
        res+=info(seen[i:i+20])
    if kw: 
        res=[r for r in res if any(w in r['title'].lower() for w in kw)]
    # order by original order
    order={t.replace('File:',''):i for i,t in enumerate(seen)}
    res.sort(key=lambda r:order.get(r['title'],99))
    return res[:k]
