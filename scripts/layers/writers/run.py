"""Rebuild the writers layer: places tied to authors on the owner's shelves.

Usage: python3 scripts/layers/writers/run.py [authors.tsv] [output.json]
  authors.tsv defaults to scripts/work/private/writers/authors.tsv, output to scripts/work/layers/writers.json.

The inputs are private and stay out of git (scripts/work/private/writers/): authors.tsv (exported from
Booktastic) and author_matches.json (accepted and rejected author-to-Wikidata matches; only names missing
from it are resolved, then appended). The curated, public inputs live here in data/: places_specs.txt
(hand-listed places: author|place name or QID|group|kind|access|note) and place_overrides.json.
Caches: scripts/work/private/writers/writer-raw/ (Nominatim results are cached; at least 1.1 s between requests).
Request templates: requests/*.txt. Sources: Wikidata (CC0), Open Plaques (PDDL), OpenStreetMap via
Nominatim (ODbL), Wikimedia Commons photos (per-photo licences)."""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WORK = os.environ.get('WRITERS_WORK', os.path.join(REPO, 'scripts', 'work', 'private', 'writers'))
tsv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, 'authors.tsv')
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, 'scripts', 'work', 'layers', 'writers.json')
os.makedirs(os.path.join(WORK, 'writer-raw'), exist_ok=True)
# The stages open writer-scripts/data/... relative to the work folder, so link it to this folder.
link = os.path.join(WORK, 'writer-scripts')
if not os.path.exists(link):
    os.symlink(HERE, link)
env = dict(os.environ, AUTHORS_TSV=os.path.abspath(tsv), WRITERS_OUT=os.path.abspath(out),
           AUTHOR_MATCHES=os.path.join(WORK, 'author_matches.json'))
for s in ['resolve_authors', 'resolve_places', 'nominatim', 'nominatim2', 'stageA', 'plaques', 'stageB',
          'stageC', 'stageD', 'photos', 'stageF', 'final']:
    t = time.time()
    print('== %s' % s, flush=True)
    if subprocess.run([sys.executable, '-I', os.path.join(HERE, s + '.py')], cwd=WORK, env=env).returncode:
        sys.exit('stage %s failed' % s)
    print('   %.0fs' % (time.time() - t), flush=True)
print('done')
