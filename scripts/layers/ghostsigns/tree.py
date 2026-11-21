import json,urllib.request,urllib.parse,time,sys
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
import os; RAW=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),'work','raw','ghostsigns')+'/'
def api(**p):
    p['format']='json'
    u='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(p)
    for i in range(4):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=60))
        except Exception as e: time.sleep(2)
    raise
def members(cat,typ):
    out=[];c={}
    while True:
        r=api(action='query',list='categorymembers',cmtitle=cat,cmtype=typ,cmlimit=500,**c)
        out+=[m['title'] for m in r['query']['categorymembers']]
        if 'continue' not in r:return out
        c=r['continue']
seen={};files={}
queue=['Category:Ghost signs in England','Category:Ghost signs in Scotland','Category:Ghost signs in Wales']
# also catch UK-level category files
while queue:
    c=queue.pop()
    if c in seen:continue
    seen[c]=1
    queue+=members(c,'subcat')
    for f in members(c,'file'): files.setdefault(f,[]).append(c)
    time.sleep(.2)
for f in members('Category:Ghost signs in the United Kingdom','file'): files.setdefault(f,[]).append('UK')
print(len(seen),'cats',len(files),'files')
json.dump({'cats':list(seen),'files':files},open(RAW+'tree.json','w'))
open(RAW+'categories.txt','w').write('\n'.join(sorted(seen))+'\n')
