import json,re,unicodedata as U
cur=json.load(open('writer-raw/curated.json'));pl=json.load(open('writer-raw/plaques_sel.json'));rev=json.load(open('writer-raw/rev.json'))
_OV=json.load(open('writer-scripts/data/place_overrides.json'))
NAMEFIX=_OV['stageD.NAMEFIX']


SPECIAL={"Q1264867":"Dulwich College"}
REG={'England':{
 'East of England':['Cambridgeshire','Bedford','Essex','Hertfordshire','Norfolk','Suffolk','Peterborough','Luton'],
 'South East':['Buckinghamshire','East Sussex','West Sussex','Brighton','Hampshire','Isle of Wight','Kent','Medway','Oxfordshire','Surrey','Berkshire','Southampton','Portsmouth','Milton Keynes','Reading'],
 'South West':['Devon','Dorset','Bournemouth','Somerset','Wiltshire','Gloucestershire','Cornwall','Kernow','Bath','West of England','Torbay','Bristol','Swindon'],
 'Midlands':['East Midlands','West Midlands','Warwickshire','Worcestershire','Derbyshire','Nottinghamshire','Leicester','Shropshire','Staffordshire','Herefordshire','Northamptonshire','Lincolnshire','Rutland'],
 'Yorkshire':['West Yorkshire','York and North Yorkshire','Hull','South Yorkshire','Yorkshire'],
 'North West':['Greater Manchester','Liverpool','Cheshire','Cumbria','Westmorland','Lancashire','Halton','Merseyside'],
 'North East':['North East','Tyne and Wear','Durham','Northumberland','Teesside']}}
def region(a,lat,lon):
    st=a.get('state') or ''; cc=a.get('country_code')
    if cc=='ie': return 'Ireland'
    if 'Scotland' in st: return 'Scotland'
    if 'Wales' in st: return 'Wales'
    if 'Northern Ireland' in st: return 'Northern Ireland'
    s=' '.join(filter(None,[a.get('state_district'),a.get('county'),a.get('city'),a.get('town')]))
    for r,l in REG['England'].items():
        if any(t.lower() in s.lower() for t in l): return r
    if 51.28<=lat<=51.70 and -0.52<=lon<=0.34: return 'London'
    return None
def locality(a):
    for k in ('hamlet','village','suburb','town','city_district','city','municipality','county'):
        if a.get(k): return a[k]
    return ''
def slug(s):
    s=U.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',s).strip('-')
def kfn(la,lo): return '%.5f,%.5f'%(la,lo)
recs=[];seen={}
def uid(b):
    i=seen.get(b,0);seen[b]=i+1
    return b if i==0 else '%s-%d'%(b,i+1)
unk=[]
for c in cur:
    a=rev.get(kfn(c['lat'],c['lon']),{})
    rg=region(a,c['lat'],c['lon'])
    name=NAMEFIX.get(c['spec'],c['label'])
    auth=c['author']; grp=c['group']
    if grp=='Grave': name='Grave of %s, %s'%(auth.split(' (')[0],name) if auth not in name else name
    if rg is None: unk.append((name,c['lat'],c['lon'],a))
    rec=dict(id=uid(slug('%s-%s'%(auth.split()[-1],name))),cat='writers',name=name,author=auth,authorQid=c['aq'],booksOwned=c['n'],group=grp,
      ll=[round(c['lat'],5),round(c['lon'],5)],approx=bool(grp=='Grave' or c.get('osm') or c.get('forceapprox')),
      src=('wikidata %s P625; author %s'%(c['q'],c['aq'])) if c.get('q') else (('osm %s; author %s'%(c['osmid'],c['aq'])) if c.get('osmid') else ('manual %s; author %s'%(c['spec'],c['aq']))),place=locality(a),region=rg,access=c['access'],kind=c['kind'],
      _desc=c.get('desc',''),_note=c.get('note',''),_wp=c.get('wp',''),_web=c.get('web',''),_spec=c['spec'],_label=c['label'])
    if c.get('q'): rec['wikidata']=c['q']
    recs.append(rec)
for p in pl:
    a=rev.get(kfn(p['latitude'],p['longitude']),{})
    rg=region(a,p['latitude'],p['longitude'])
    road=a.get('road','')
    name='%s plaque%s'%(p['author'],(', '+road) if road else '')
    if rg is None: unk.append((name,p['latitude'],p['longitude'],a))
    recs.append(dict(id=uid(slug('%s-plaque-%d'%(p['author'].split()[-1],p['id']))),cat='writers',name=name,author=p['author'],authorQid=p['aq'],booksOwned=p['n'],group='Plaque',
      ll=[round(p['latitude'],5),round(p['longitude'],5)],approx=False,src='openplaques %d; author %s'%(p['id'],p['aq']),place=locality(a),region=rg,access='open',kind='%s plaque'%(p.get('colour_name') or 'commemorative').capitalize(),
      _desc='',_note='',_wp='',_web='',_ins=p['inscription'],url='https://openplaques.org/plaques/%d'%p['id']))
for u in unk: print('UNK',u[0],u[1],u[2],u[3].get('city'),u[3].get('town'),u[3].get('suburb'))
json.dump(recs,open('writer-raw/stageD.json','w'),indent=1)
print(len(recs))
