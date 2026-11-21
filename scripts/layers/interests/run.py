#!/usr/bin/env python3
"""Whole pipeline.  Usage: run.py <output dir> [--refetch] [layer ...]
Fetches (Wikidata SPARQL, OSM from the downloaded extract or else Overpass, Commons search), builds records, resolves regions
(postcodes.io), photos (Commons imageinfo), applies overrides.json, writes <layer>.json + layers-sources.json."""
import sys,os,json,subprocess
H=os.path.dirname(os.path.abspath(__file__))
OUT=sys.argv[1];os.makedirs(OUT,exist_ok=True)
args=[a for a in sys.argv[2:] if a.startswith('--')];sel=[a for a in sys.argv[2:] if not a.startswith('--')]
WD='Wikidata (CC0)';OSM='OpenStreetMap (ODbL)';CM='photos from Wikimedia Commons'
META={
'wells':('Holy wells','Holy wells, healing springs and saints\' wells.',[WD,OSM],'(c) OpenStreetMap contributors (ODbL)'),
'prehistoric':('Stone circles and standing stones','Stone circles, henges, dolmens and standing stones.',[WD,OSM],'(c) OpenStreetMap contributors (ODbL)'),
'caves':('Caves and show mines','Show caves, show mines and notable caves.',[WD,OSM],'(c) OpenStreetMap contributors (ODbL)'),
'follies':('Follies, grottoes and hill figures','Follies, garden grottoes and hill figures.',[WD],''),
'trees':('Notable and ancient trees','Named veteran, ancient and historic trees.',[WD,OSM],'(c) OpenStreetMap contributors (ODbL)'),
'greenman':('Green Man carvings','Churches with foliate-head carvings; position is the photo location.',['Wikimedia Commons geotagged photos'],''),
}
layers=sel or list(META)
for k in layers:
    r=subprocess.run([sys.executable,H+'/layers.py',k,OUT+'/%s.json'%k]+args)
    if r.returncode:print('layer failed',k)
src=[]
for k in layers:
    p=OUT+'/%s.json'%k
    if os.path.exists(p):
        n,d,s,a=META[k];c=len(json.load(open(p)))
        src.append(dict(key=k,name=n,description=d,source='; '.join(s+[CM]),licence='CC0 / ODbL / per-photo Commons licences',attribution='Contains data from Wikidata (CC0)'+('; '+a if a else '')+'; photos from Wikimedia Commons under the licences shown',count=c))
json.dump(src,open(OUT+'/layers-sources.json','w'),indent=1)
