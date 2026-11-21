import sys,json,urllib.request,urllib.parse,time
UA='goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)'
def sparql(q):
    for i in range(4):
        try:
            r=urllib.request.Request('https://query.wikidata.org/sparql',urllib.parse.urlencode({'query':q}).encode(),{'User-Agent':UA,'Accept':'application/json'})
            return json.load(urllib.request.urlopen(r,timeout=120))['results']['bindings']
        except Exception as e:
            print('retry',e,file=sys.stderr);time.sleep(5*(i+1))
    raise SystemExit('fail')
if __name__=='__main__':
    for t in sys.argv[1:]:
        u='https://www.wikidata.org/w/api.php?action=wbsearchentities&language=en&limit=6&format=json&search='+urllib.parse.quote(t)
        r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA})))
        print(t,[(x['id'],x.get('description','')[:40]) for x in r['search']])
