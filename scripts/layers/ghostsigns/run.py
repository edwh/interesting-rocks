#!/usr/bin/env python3
"""Re-runnable entry point: python3 -I run.py [output.json]  default -> scripts/work/layers/ghostsigns.json
Stages: tree (Commons category walk) -> info (Commons file metadata) -> geo/geo2 (Geograph KML search)
-> build (filter, cluster, overrides.json) -> finish (postcodes.io region lookup) -> emit (names, JSON).
Hand curation lives only in overrides.json. Request definitions: requests.md. Category list is saved
by tree.py to scripts/work/raw/ghostsigns/categories.txt on every run."""
import subprocess,sys,os
d=os.path.dirname(os.path.abspath(__file__))
if '--refetch-geo' in sys.argv or True:
    for f in ['tree.py','info.py','geo.py','geo2.py','build.py','finish.py','emit.py']:
        print('==',f,flush=True)
        subprocess.run([sys.executable,'-I',os.path.join(d,f)]+(sys.argv[1:2] if f=='emit.py' else []),check=True)
