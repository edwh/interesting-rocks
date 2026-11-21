import os,json,re,math,html,urllib.request,time,collections
import os; D=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))+'/'
RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
tree=json.load(open(RAW+'tree.json'));info=json.load(open(RAW+'info.json'));geo=json.load(open(RAW+'geo.json'))
FREE=re.compile(r'^(CC BY(-SA)? \d\.\d|CC0.*|Public domain.*|PD.*)$',re.I)
def strip(s): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s or ''))).strip()
def in_gb(lat,lon):
    if not(49.8<lat<60.9 and -8.7<lon<1.9):return False
    if lon<-5.4 and 51.5<lat<55.4:return False       # Ireland / NI
    if 54.0<lat<54.5 and -4.9<lon<-4.2:return False   # Isle of Man
    if lat<49.95 and lon>-3:return False              # Channel Islands
    if 49.8<lat<50.0 and -3<lon<-1.9:return False
    return True
items=[]
geoids=set()
rej=collections.Counter()
for t,p in info.items():
    f=t[5:]
    m=re.search(r'geograph\.org\.uk - (\d+)',f)
    if m:geoids.add(m.group(1))
    co=p.get('coordinates')
    ii=(p.get('imageinfo') or [None])[0]
    if not co or not ii:rej['nocoord']+=1;continue
    em=ii['extmetadata']
    lic=em.get('LicenseShortName',{}).get('value','')
    if not FREE.match(lic):rej['licence']+=1;continue
    obj=[c for c in co if 'primary' not in c];pri=[c for c in co if 'primary' in c]
    c=obj[0] if obj else pri[0]
    approx=not obj
    if not in_gb(c['lat'],c['lon']):rej['notGB']+=1;continue
    desc=strip(em.get('ImageDescription',{}).get('value',''))
    title=f[:f.rfind('.')]
    items.append(dict(kind='c',lat=c['lat'],lon=c['lon'],approx=approx,title=title,desc=desc,
      photo=dict(src=ii['thumburl'],page=ii['descriptionurl'],license=lic,artist=strip(em.get('Artist',{}).get('value','')) or 'Unknown',title=f),
      src='commons File:'+f,cats=tree['files'][t]))
GHOST=re.compile(r'ghost[ -]?sign|ghost advert|ghost ad\b|faded (advert|sign|paint)|painted (advert|sign)|fading (advert|sign|paint)|hand[- ]painted',re.I)
for g,r in geo.items():
    if g in geoids:rej['geo_on_commons']+=1;continue
    txt=r['title']+' '+(r['desc'] or '')
    if not GHOST.search(txt):rej['geo_notghost']+=1;continue
    if not r['thumb'] or not r['artist']:rej['geo_nometa']+=1;continue
    if not in_gb(r['lat'],r['lon']):rej['geo_notGB']+=1;continue
    title=re.sub(r'^[A-Z]{1,2}\d{2,10} : ','',r['title'])
    img=r['thumb'].replace('_120x120','')
    items.append(dict(kind='g',lat=r['lat'],lon=r['lon'],approx=True,title=title,desc=strip(r['desc'] or ''),
      photo=dict(src=img,page='https://www.geograph.org.uk/photo/'+g,license='CC BY-SA 2.0',artist=r['artist'],title=title),
      src='geograph '+g,cats=[]))
ov=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'overrides.json')))
ex=set(ov['exclude'])
items=[i for i in items if i['src'].split(' ',1)[1] not in ex and i['src'].split(' ',1)[1].split(' - ')[-1] not in ex]
print(len(items),dict(rej))
# cluster within 30 m (union-find, grid-bucketed)
def dist(a,b):
    return math.hypot((a['lat']-b['lat'])*111320,(a['lon']-b['lon'])*111320*math.cos(math.radians(a['lat'])))
par=list(range(len(items)))
def fd(i):
    while par[i]!=i:par[i]=par[par[i]];i=par[i]
    return i
buck=collections.defaultdict(list)
for i,it in enumerate(items):buck[(round(it['lat']/0.0004),round(it['lon']/0.0006))].append(i)
for (a,b),L in buck.items():
    for da in(-1,0,1):
        for db in(-1,0,1):
            for i in L:
                for j in buck.get((a+da,b+db),[]):
                    if i<j and dist(items[i],items[j])<=30:par[fd(i)]=fd(j)
bysrc={it['src'].split(' ',1)[1]:i for i,it in enumerate(items)}
for m in ov['merge']:
    ids=[bysrc[k] for k in m if k in bysrc]
    for a in ids[1:]:par[fd(a)]=fd(ids[0])
groups=collections.defaultdict(list)
for i in range(len(items)):groups[fd(i)].append(items[i])
groups=list(groups.values())
print(len(groups),'groups')
# commons first, then by title
for g in groups:g.sort(key=lambda x:(x['kind']!='c',not x['approx'] is False,x['title']))
json.dump(groups,open(RAW+'groups.json','w'))
