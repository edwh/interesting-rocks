import json,re,unicodedata as U,os,datetime
recs=json.load(open('writer-raw/stageF.json'))
def norm(s): return U.normalize('NFKD',s).encode('ascii','ignore').decode().lower()
GEN={'church','museum','house','statue','memorial','grave','cemetery','churchyard','cathedral','hall','street','square','college','plaque','blue','the','and','saint','abbey','centre','center','road','place','court','park','theatre','school','inn','monument','shop','gaol','prison','window','tomb','sculpture','cottage'}
def toks(s): return [t for t in re.findall(r"[a-z]{4,}",norm(s)) if t not in GEN]
JUNK=re.compile(r'British School|Bundesarchiv|AGILE|Dalek|Masterman|Auberon|Life and Letters|woodcut|Allingham Place|Thomas Paine Hotel|Roman Conrad|Millicent|Jenny Lind|Henry Dale|Boots',re.I)
out=[]
for r in recs:
    g=r['group'];ph=[p for p in r['photos'] if not JUNK.search(p['title'])]
    sur=norm(r['author'].split()[-1]).strip('.')
    if g=='Plaque': ph=[p for p in ph if sur in norm(p['title'])]
    elif g=='Grave': ph=[p for p in ph if sur in norm(p['title']) and re.search(r'grave|tomb|headstone|burial|memorial|churchyard|cemetery|hearts?',norm(p['title']))]
    else:
        want=toks(r['name'])
        ph=[p for p in ph if any(w in norm(p['title']) for w in want)]
    r['photos']=ph[:2]
    if r['name']=="Grave of Charlotte Brontë, St Mary's Church, Scarborough":
        r.update(author='Anne Brontë',authorQid='Q44520',booksOwned=1,name="Grave of Anne Brontë, St Mary's Church, Scarborough",id='bronte-grave-of-anne-bronte-scarborough')
        r['about']='Burial place of Anne Brontë: churchyard grave overlooking Scarborough.'
    out.append(r)
for r in out:
    r['about']=r['about'].replace("poets' Corner, abbey","abbey burial in Poets' Corner").replace("poets' Corner","Poets' Corner")
pl=[r for r in out if r['id']=='hardy-plaque-42284'][0]
out.append(dict(id='hardy-hardy-s-cottage',cat='writers',name="Hardy's Cottage",author='Thomas Hardy',authorQid='Q132805',booksOwned=8,group='House museum',ll=pl['ll'],approx=True,
  src='openplaques 42284; author Q132805',place='Higher Bockhampton',region='South West',access='open',kind='Birthplace cottage (National Trust)',
  about="Thatched cottage near Dorchester where Thomas Hardy was born and later wrote Under the Greenwood Tree.",note='Position taken from the plaque on the cottage; National Trust property, check opening times.',
  url='https://en.wikipedia.org/wiki/Hardy%27s_Cottage',photos=[p for p in pl['photos'] if 'cottage' in p['title'].lower()][:2]))
# unique ids
ids=set()
for r in out:
    assert r['id'] not in ids,r['id']; ids.add(r['id'])
for r in out: r['fetched']=datetime.date.today().isoformat()
order=['id','cat','name','author','authorQid','booksOwned','group','year','ll','approx','src','fetched','wikidata','place','region','access','kind','about','note','url','photos']
out=[{k:r[k] for k in order if k in r} for r in out]
OUT=os.environ.get('WRITERS_OUT','../layers/writers.json')
os.makedirs(os.path.dirname(os.path.abspath(OUT)),exist_ok=True)
json.dump(out,open(OUT,'w'),indent=1,ensure_ascii=False)
# validate
REG={"Scotland","North East","North West","Yorkshire","Midlands","Wales","East of England","London","South East","South West","Northern Ireland","Ireland"}
LIC=re.compile(r'^(CC BY(-SA)? \d\.\d|CC0|Public domain|PD)',re.I)
bad=0
for r in out:
    la,lo=r['ll']
    if not(49.8<=la<=60.95 and -10.8<=lo<=1.9): print('BBOX',r['id']);bad+=1
    if r['region'] not in REG: print('REGION',r['id'],r['region']);bad+=1
    if not r['place']: print('NOPLACE',r['id'])
    for p in r['photos']:
        if not LIC.match(p['license']): print('LIC',r['id'],p['license']);bad+=1
import collections
print(len(out),'bad',bad,collections.Counter(r['group'] for r in out),collections.Counter(r['region'] for r in out))
print('with photos',sum(1 for r in out if r['photos']),'authors',len({r['authorQid'] for r in out}))
print(collections.Counter(p['license'] for r in out for p in r['photos']))
