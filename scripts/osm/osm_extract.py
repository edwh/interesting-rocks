#!/usr/bin/env python3
"""Answer the layer scripts' Overpass queries from a downloaded OpenStreetMap extract.

The public Overpass servers often refuse or time out, so the layer scripts read OSM from the
Geofabrik United Kingdom extract instead (scripts/osm/fetch-extract.sh). The queries stay as
Overpass QL files next to each script, so the record of what was asked for does not change.
This module understands the small part of Overpass QL those files use:

    nwr / node / way / rel  with tag filters  ["k"]  [!"k"]  ["k"="v"]  ["k"!="v"]
    ["k"~"regex"]  ["k"!~"regex"]  (",i" for case-insensitive), inside a ( ... ; ... ) union,
    restricted by (area.x) (taken as the whole extract), (south,west,north,east), or (id:1,2,3).

Each answer has the shape of Overpass "out center tags" JSON: nodes with lat/lon, ways and
relations with center (the middle of their bounding box, as Overpass computes it).
Anything else (around:, poly:, difference, recursion) raises Unsupported, so a script can
fall back to Overpass.

Commands:
  osm_extract.py build         filter the extract to the tags in filters.txt and index it (~2 minutes)
  osm_extract.py query FILE    run one query (FILE or - for stdin), print Overpass-style JSON
  osm_extract.py info          show the extract date and index size

Data: OpenStreetMap contributors, ODbL 1.0. Credit "(c) OpenStreetMap contributors".
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.environ.get('OSM_EXTRACT_DIR', os.path.join(HERE, '..', 'work', 'raw', 'osm'))
PBF = os.path.join(DIR, 'united-kingdom-latest.osm.pbf')
INDEX = os.path.join(DIR, 'poi.jsonl')
META = os.path.join(DIR, 'poi.meta.json')
FILTERS = os.path.join(HERE, 'filters.txt')


class Unsupported(Exception):
    pass


def available():
    """True when the index exists and OSM_SOURCE is not set to 'overpass'."""
    return os.environ.get('OSM_SOURCE') != 'overpass' and os.path.exists(INDEX)


def meta():
    return json.load(open(META)) if os.path.exists(META) else {}


# ---------- reading OPL (osmium's text format) ----------
UNESC = re.compile(r'%([0-9a-fA-F]+)%')
WAYNODE = re.compile(r'n(\d+)x([-\d.]*)y([-\d.]*)')


def unesc(s):
    return UNESC.sub(lambda m: chr(int(m.group(1), 16)), s)


def tags_of(field):
    tags = {}
    if field:
        for kv in field.split(','):
            k, _, v = kv.partition('=')
            tags[unesc(k)] = unesc(v)
    return tags


def read_opl(lines):
    """Parse osmium OPL with way node locations. Returns (elements, wanted) where elements are
    Overpass-shaped dicts for every tagged object."""
    nodes, ways, rels = {}, {}, {}   # id -> (tags, data)
    for line in lines:
        f = line.rstrip('\n').split(' ')
        if not f or not f[0]:
            continue
        kind, oid = f[0][0], int(f[0][1:])
        d = {x[0]: x[1:] for x in f[1:] if x}
        tags = tags_of(d.get('T', ''))
        if kind == 'n':
            if d.get('x') and d.get('y'):
                nodes[oid] = (tags, (float(d['y']), float(d['x'])))
        elif kind == 'w':
            pts = [(float(y), float(x)) for _, x, y in WAYNODE.findall(d.get('N', '')) if x and y]
            if pts:
                lats, lons = [p[0] for p in pts], [p[1] for p in pts]
                ways[oid] = (tags, (min(lats), min(lons), max(lats), max(lons)))
        elif kind == 'r':
            mem = []
            for m in d.get('M', '').split(',') if d.get('M') else []:
                ref, _, _role = m.partition('@')
                mem.append((ref[0], int(ref[1:])))
            rels[oid] = (tags, mem)

    def rel_box(rid, seen):
        if rid in seen or rid not in rels:
            return None
        seen.add(rid)
        box = None
        for t, i in rels[rid][1]:
            b = None
            if t == 'n' and i in nodes:
                y, x = nodes[i][1]
                b = (y, x, y, x)
            elif t == 'w' and i in ways:
                b = ways[i][1]
            elif t == 'r':
                b = rel_box(i, seen)
            if b:
                box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
        return box

    def centre(b):
        return {'lat': round((b[0] + b[2]) / 2, 7), 'lon': round((b[1] + b[3]) / 2, 7)}

    out = []
    for i, (tags, (y, x)) in nodes.items():
        if tags:
            out.append({'type': 'node', 'id': i, 'lat': y, 'lon': x, 'tags': tags})
    for i, (tags, b) in ways.items():
        if tags:
            out.append({'type': 'way', 'id': i, 'center': centre(b), 'tags': tags})
    for i, (tags, _) in rels.items():
        if tags:
            b = rel_box(i, set())
            if b:
                out.append({'type': 'relation', 'id': i, 'center': centre(b), 'tags': tags})
    return out


def osmium_opl(src):
    """Stream OPL lines for a pbf, with each way's node locations inline."""
    p = subprocess.Popen(['osmium', 'add-locations-to-ways', '--ignore-missing-nodes', '-F', 'pbf', src,
                          '-f', 'opl,add_metadata=false', '-o', '-'],
                         stdout=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1 << 20)
    yield from p.stdout
    if p.wait():
        raise SystemExit('osmium add-locations-to-ways failed')


# ---------- building the index ----------
def filter_exprs():
    exprs = []
    for line in open(FILTERS):
        line = line.split('#', 1)[0].strip()
        if line:
            exprs.append(line)
    return exprs


def build():
    if not os.path.exists(PBF):
        raise SystemExit(f'no extract at {PBF}; run scripts/osm/fetch-extract.sh first')
    run = lambda *a: subprocess.run(['osmium', *a], check=True)
    with tempfile.TemporaryDirectory(dir=DIR) as tmp:
        main_, named = os.path.join(tmp, 'main.pbf'), os.path.join(tmp, 'named.pbf')
        two_step = [e for e in filter_exprs() if e.startswith('named:')]
        one_step = [e for e in filter_exprs() if not e.startswith('named:')]
        run('tags-filter', PBF, *one_step, '-o', main_, '--overwrite')
        parts = [main_]
        if two_step:
            # "named:nwr/natural=tree" keeps only the named ones (there are millions of street trees).
            wide = os.path.join(tmp, 'wide.pbf')
            run('tags-filter', PBF, *[e[6:] for e in two_step], '-o', wide, '--overwrite')
            run('tags-filter', wide, 'nwr/name', '-o', named, '--overwrite')
            parts.append(named)
        poi = os.path.join(DIR, 'poi.osm.pbf')
        run('merge', *parts, '-o', poi, '--overwrite')
    els = read_opl(osmium_opl(poi))
    with open(INDEX + '.part', 'w', encoding='utf-8') as f:
        for e in els:
            f.write(json.dumps(e, ensure_ascii=False, separators=(',', ':')) + '\n')
    os.replace(INDEX + '.part', INDEX)
    ts = subprocess.run(['osmium', 'fileinfo', '-g', 'header.option.osmosis_replication_timestamp', PBF],
                        capture_output=True, text=True).stdout.strip()
    md5 = open(PBF + '.md5').read().split()[0] if os.path.exists(PBF + '.md5') else ''
    m = {'extract': 'https://download.geofabrik.de/europe/united-kingdom/united-kingdom-latest.osm.pbf',
         'data_as_of': ts, 'md5': md5, 'filters': filter_exprs(), 'elements': len(els),
         'licence': 'ODbL 1.0', 'attribution': '(c) OpenStreetMap contributors'}
    json.dump(m, open(META, 'w'), indent=1)
    print(f'indexed {len(els)} tagged objects; data as of {ts}')


# ---------- answering queries ----------
_ix = None


def index():
    """Load the index once per process, with a lookup by key."""
    global _ix
    if _ix is None:
        els, by_key = [], {}
        for line in open(INDEX, encoding='utf-8'):
            e = json.loads(line)
            els.append(e)
            for k in e['tags']:
                by_key.setdefault(k, []).append(e)
        _ix = (els, by_key)
    return _ix


QSTR = r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''
STMT = re.compile(r'(?<![\w.])(nwr|nw|nr|wr|node|way|relation|rel)((?:\[(?:[^\]"\']|' + QSTR + r')*\])*)((?:\((?:[^)"\']|' + QSTR + r')*\))*)')
BRACKET = re.compile(r'\[((?:[^\]"\']|' + QSTR + r')*)\]')
PAREN = re.compile(r'\(((?:[^)"\']|' + QSTR + r')*)\)')
TOKEN = re.compile(r'\s*(' + QSTR + r'|!~|!=|=|~|!|,|[^\s"\'!=~,]+)')
TYPES = {'nwr': {'node', 'way', 'relation'}, 'nw': {'node', 'way'}, 'nr': {'node', 'relation'},
         'wr': {'way', 'relation'}, 'node': {'node'}, 'way': {'way'}, 'rel': {'relation'}, 'relation': {'relation'}}


def unquote(t):
    if t[:1] in '"\'':
        t = t[1:-1]
        t = re.sub(r'\\(u[0-9a-fA-F]{4}|.)', lambda m: chr(int(m.group(1)[1:], 16)) if m.group(1)[0] == 'u' and len(m.group(1)) == 5
                   else {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)), t)
    return t


def parse_filter(body):
    toks = [m.group(1) for m in TOKEN.finditer(body)]
    if not toks:
        raise Unsupported('empty filter')
    if toks[0] == '!':
        return ('absent', unquote(toks[1]), None)
    if toks[0] == '~':
        raise Unsupported('regex on keys')
    k = unquote(toks[0])
    if len(toks) == 1:
        return ('has', k, None)
    op, v = toks[1], unquote(toks[2])
    flags = re.I if len(toks) > 4 and toks[3] == ',' and toks[4] == 'i' else 0
    if op == '=':
        return ('eq', k, v)
    if op == '!=':
        return ('ne', k, v)
    if op == '~':
        return ('re', k, re.compile(v, flags))
    if op == '!~':
        return ('nre', k, re.compile(v, flags))
    raise Unsupported('filter ' + body)


def matches(e, filters):
    t = e['tags']
    for op, k, v in filters:
        x = t.get(k)
        if op == 'has' and x is None: return False
        if op == 'absent' and x is not None: return False
        if op == 'eq' and x != v: return False
        if op == 'ne' and x == v: return False
        if op == 're' and (x is None or not v.search(x)): return False
        if op == 'nre' and x is not None and v.search(x): return False
    return True


def point(e):
    return (e['lat'], e['lon']) if 'lat' in e else (e['center']['lat'], e['center']['lon'])


def by_ids(refs):
    """Look up objects by id in the full extract, whatever their tags."""
    if not refs:
        return []
    with tempfile.TemporaryDirectory(dir=DIR) as tmp:
        out = os.path.join(tmp, 'ids.pbf')
        subprocess.run(['osmium', 'getid', '-r', PBF, *sorted(refs), '-o', out, '--overwrite'],
                       check=True, capture_output=True)
        want = {(r[0], int(r[1:])) for r in refs}
        return [e for e in read_opl(osmium_opl(out)) if (e['type'][0], e['id']) in want]


def query(ql):
    """Answer an Overpass QL query from the extract; returns Overpass-style JSON."""
    q = re.sub(r'/\*.*?\*/|//[^\n]*', '', ql, flags=re.S)
    if re.search(r'around\s*:|poly\s*:|\bis_in\b|\bforeach\b|\bmap_to_area\b|[<>]\s*;|[;(]\s*-\s*[(a-z]', q):
        raise Unsupported('query uses syntax the local engine does not handle')
    for m in re.finditer(r'->\s*\.(\w+)', q):
        if not re.search(r'area\s*(\[[^;]*)?->\s*\.' + m.group(1) + r'\b', q):
            raise Unsupported('named sets other than an area')
    els, by_key = index()
    seen, out, id_refs = set(), [], set()
    for m in STMT.finditer(q):
        types = TYPES[m.group(1)]
        filters = [parse_filter(b.group(1)) for b in BRACKET.finditer(m.group(2))]
        bbox = None
        for p in PAREN.finditer(m.group(3)):
            body = p.group(1).strip()
            if body.startswith('id:'):
                prefix = {'node': 'n', 'way': 'w', 'relation': 'r'}[next(iter(types))] if len(types) == 1 else None
                if not prefix:
                    raise Unsupported('id: needs node, way or rel')
                id_refs.update(prefix + i.strip() for i in body[3:].split(',') if i.strip())
            elif re.fullmatch(r'area(\.\w+)?', body):
                pass  # the extract is the area
            elif re.fullmatch(r'[-\d.\s]+,[-\d.\s]+,[-\d.\s]+,[-\d.\s]+', body):
                bbox = [float(x) for x in body.split(',')]
            else:
                raise Unsupported('clause (' + body + ')')
        if m.group(3).strip().startswith('(id:'):
            continue
        # Start from the smallest list of objects carrying a key the filters require.
        need = [by_key.get(f[1], []) for f in filters if f[0] in ('has', 'eq', 're')]
        cand = min(need, key=len) if need else els
        for e in cand:
            if e['type'] not in types or (e['type'], e['id']) in seen or not matches(e, filters):
                continue
            if bbox:
                y, x = point(e)
                if not (bbox[0] <= y <= bbox[2] and bbox[1] <= x <= bbox[3]):
                    continue
            seen.add((e['type'], e['id']))
            out.append(e)
    for e in by_ids(id_refs):
        if (e['type'], e['id']) not in seen:
            seen.add((e['type'], e['id']))
            out.append(e)
    return {'version': 0.6, 'generator': 'goldsworthy-map scripts/osm/osm_extract.py',
            'osm3s': {'timestamp_osm_base': meta().get('data_as_of', ''),
                      'copyright': 'The data included in this document is from www.openstreetmap.org. The data is made available under ODbL.'},
            'elements': out}


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'build':
        build()
    elif cmd == 'query':
        src = sys.argv[2] if len(sys.argv) > 2 else '-'
        ql = sys.stdin.read() if src == '-' else open(src).read()
        json.dump(query(ql), sys.stdout, ensure_ascii=False)
    elif cmd == 'info':
        print(json.dumps(meta(), indent=1))
    else:
        print(__doc__)
        sys.exit(1)
