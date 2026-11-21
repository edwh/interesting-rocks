#!/usr/bin/env python3
"""Re-runnable entry point.  Usage: layers.py <layer> <out.json> [--refetch | --refetch-osm]
layers: wells prehistoric caves follies trees greenman
--refetch-osm re-reads only the OSM parts (from the downloaded extract, scripts/osm/osm_extract.py).
Reads queries/*, overrides.json; caches raw downloads in RAW dir (env LAYER_RAW or ../raw); fetches if absent or --refetch.
No hand steps: hand picks live in overrides.json."""
import sys,os,json,time,datetime,urllib.request,urllib.parse
H=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,H)
import build
from q import sparql
from op import op, osm_extract
RAW=os.environ.get('LAYER_RAW',build.R);os.makedirs(RAW,exist_ok=True)
Qd=H+'/queries/'
def wd_fetch(theme):
    out={};tpl=open(Qd+'wikidata-theme.rq').read();cl=json.load(open(Qd+'wikidata-themes.json'))[theme]
    for c in cl:
        clause='VALUES ?cls{wd:%s}'%c if theme=='trees' else '?cls wdt:P279* wd:%s.'%c
        for b in sparql(tpl.replace('{CLASS_CLAUSE}',clause)):
            qid=b['s']['value'].split('/')[-1]
            d=out.setdefault(qid,{'q':qid,'photos':[],'cls':set()})
            d['name']=b['sLabel']['value'];d['desc']=b.get('sDescription',{}).get('value','')
            d['co']=b['co']['value'];d['cls'].add(b['clsLabel']['value'])
            if 'p' in b and b['p']['value'] not in d['photos']:d['photos'].append(b['p']['value'])
            if 'art' in b:d['wp']=b['art']['value']
            if 'locLabel' in b:d['loc']=b['locLabel']['value']
            if 'inc' in b:d['inc']=b['inc']['value'][:4]
        time.sleep(3)
    for d in out.values():d['cls']=sorted(d['cls'])
    return list(out.values())
LAT=[49.8,51.5,52.5,53.5,54.5,55.5,57,61];LON=[-8,-3,2]
def osm_fetch(k):
    q=open(Qd+'osm-%s.overpassql'%k).read();seen={}
    if osm_extract.available():return op(q)['elements']  # the extract answers the whole query at once
    # tiled: each query runs per bbox tile (area clause removed) to keep Overpass requests small
    q=q.replace('area["ISO3166-1"="GB"]->.gb;\n','')
    for a in range(len(LAT)-1):
        for b in range(len(LON)-1):
            bb='(%s,%s,%s,%s)'%(LAT[a],LON[b],LAT[a+1],LON[b+1])
            for e in op(q.replace('(area.gb)',bb))['elements']:seen[(e['type'],e['id'])]=e
            time.sleep(3)
    return list(seen.values())
def commons_fetch():
    def api(**p):
        p['format']='json';return build.get('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(p))
    out={}
    for term in json.load(open(Qd+'commons-greenman-terms.json')):
        off=0
        while off<500:
            r=api(action='query',generator='search',gsrsearch=term+' filetype:bitmap',gsrnamespace=6,gsrlimit=50,gsroffset=off,prop='coordinates|categories',cllimit='max',colimit='max')
            if not r:break
            for pg in r.get('query',{}).get('pages',{}).values():
                if 'coordinates' in pg:
                    c=pg['coordinates'][0]
                    if build.ingb(c['lat'],c['lon']):out[pg['title']]={'ll':[c['lat'],c['lon']],'cats':[x['title'] for x in pg.get('categories',[])]}
            if 'continue' not in r:break
            off=r['continue']['gsroffset'];time.sleep(.5)
    return out
JOBS={ # raw file -> fetcher
 'wd-wells.json':lambda:wd_fetch('wells'),'wd-prehistoric.json':lambda:wd_fetch('prehistoric'),'wd-caves.json':lambda:wd_fetch('caves'),
 'wd-follies.json':lambda:wd_fetch('follies'),'wd-hillfigures.json':lambda:wd_fetch('hillfigures'),'wd-trees.json':lambda:wd_fetch('trees'),
 'osm-wells.json':lambda:osm_fetch('wells'),'osm-caves.json':lambda:osm_fetch('caves'),'osm-trees.json':lambda:osm_fetch('trees'),'osm-trees2.json':lambda:osm_fetch('trees2'),
 'osm-standing.json':lambda:osm_fetch('standing'),'commons-greenman.json':commons_fetch}
NEED={'wells':['wd-wells.json','osm-wells.json'],'prehistoric':['wd-prehistoric.json','osm-standing.json'],'caves':['wd-caves.json','osm-caves.json'],
 'follies':['wd-follies.json','wd-hillfigures.json','wd-caves.json'],'trees':['wd-trees.json','osm-trees.json','osm-trees2.json'],'greenman':['commons-greenman.json']}
def ensure(layer,refetch):
    ds=[]
    for f in NEED[layer]:
        p=RAW+'/'+f
        if refetch or (REFETCH_OSM and f.startswith('osm-')) or not os.path.exists(p):
            try:json.dump(JOBS[f](),open(p,'w'))
            except BaseException as e:print('fetch failed',f,e,file=sys.stderr)
        if os.path.exists(p):ds.append(datetime.date.fromtimestamp(os.path.getmtime(p)))
    return str(min(ds)) if ds else str(datetime.date.today())
if __name__=='__main__':
    layer,outp=sys.argv[1],sys.argv[2];refetch='--refetch' in sys.argv;REFETCH_OSM='--refetch-osm' in sys.argv
    build.R=RAW+'/'
    fetched=ensure(layer,refetch);ov=json.load(open(H+'/overrides.json'))
    B=build;big=10**9
    if layer=='wells':r=B.merge(B.wdrecs('wells',B.wells_wd),B.osmrecs('osm-wells.json',B.wells_osm))
    elif layer=='prehistoric':r=B.merge(B.wdrecs('prehistoric',B.pre_wd),B.osmrecs('osm-standing.json',B.pre_osm))
    elif layer=='caves':r=B.merge(B.wdrecs('caves',B.caves_wd),B.osmrecs('osm-caves.json',B.caves_osm))
    elif layer=='follies':r=B.merge(B.wdrecs('follies',B.follies_wd)+B.wdrecs('hillfigures',B.hill_wd)+B.wdrecs('caves',lambda d:{'group':'Grotto','kind':'Grotto','access':'unknown','_score':1} if B.has(d,'grotto','shell grotto') else None))
    elif layer=='trees':r=B.merge(B.wdrecs('trees',B.trees_wd),B.osmrecs('osm-trees.json',B.trees_osm),B.osmrecs('osm-trees2.json',B.trees_osm))
    elif layer=='greenman':r=B.greenmen()
    B.finish(layer,B.pick(r,big),outp,fetched,ov)
