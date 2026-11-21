// Build data/layers/<key>.json and the data/layers.json manifest from the layer sources.
// Goldsworthy comes from data/sites.json; other layers from scripts/work/layers/<key>.json, which the
// fetch scripts in scripts/layers/<key>/ write. Hand corrections live in scripts/layers/overrides.json,
// keyed by the record's source id (src) or id, so they survive a re-run of the fetch.
// Every record has a tier: 1 for highlights, 2 for the rest. Curated layers are all highlights.
import fs from 'fs';

const REGIONS = ['Scotland', 'North East', 'North West', 'Yorkshire', 'Midlands', 'Wales', 'East of England',
  'London', 'South East', 'South West', 'Northern Ireland', 'Ireland'];
const OLD_REGION = {
  'Edinburgh & Lothians': 'Scotland', 'Dumfries & Galloway': 'Scotland', 'Northumberland': 'North East',
  'Tyne & Wear': 'North East', 'County Durham': 'North East', 'Cumbria & borders': 'North West',
  'Lancashire': 'North West', 'North Yorkshire': 'Yorkshire', 'West Yorkshire': 'Yorkshire',
};
// Photo licences we may reuse: CC BY and CC BY-SA (any version, optionally ported), CC0, public domain.
// Anything else (NC, ND, all rights reserved, fair use) is dropped, as is a CC photo with no named author.
const FREE = /^(CC BY(-SA)? \d\.\d( [a-z]{2})?|CC0( 1\.0)?|Public domain( mark)?|PD-\w+)$/i;
const NEEDS_AUTHOR = /^CC BY/i;
// Geograph asks reusers not to hotlink: use a Commons copy (scripts/photos/geograph.mjs finds them)
// or our own copy in data/photos/geograph; a Geograph photo with neither is dropped.
const geoMirrors = fs.existsSync('scripts/layers/geograph-mirrors.json')
  ? JSON.parse(fs.readFileSync('scripts/layers/geograph-mirrors.json', 'utf8')) : {};
const geoUnhosted = new Set();
function hostPhoto(p) {
  let host = '';
  try { host = new URL(p.src).hostname; } catch { return p; }
  if (!host.endsWith('geograph.org.uk')) return p;
  const id = /geograph\.org\.uk\/photo\/(\d+)/.exec(p.page || '')?.[1];
  if (id && geoMirrors[id]) return { ...geoMirrors[id], artist: geoMirrors[id].artist || p.artist };
  if (id && fs.existsSync(`data/photos/geograph/${id}.jpg`)) return { ...p, src: `data/photos/geograph/${id}.jpg` };
  geoUnhosted.add(id || p.page);
  return null;
}
const ACCESS = new Set(['open', 'limited', 'gone', 'unknown']);
const KEEP = ['id', 'cat', 'name', 'artist', 'author', 'group', 'year', 'll', 'approx', 'place', 'region', 'access',
  'kind', 'count', 'about', 'note', 'url', 'grid', 'grade', 'tier', 'wikidata', 'src', 'fetched', 'photos'];
// Big layers ship compact records: the source id is the record id, the date is in the manifest,
// and the link and type are rebuilt in the app from the layer's "urls" and "kinds".
const COMPACT_DROP = ['cat', 'src', 'fetched', 'region', 'tier'];
const overrides = fs.existsSync('scripts/layers/overrides.json')
  ? JSON.parse(fs.readFileSync('scripts/layers/overrides.json', 'utf8')) : {};

const config = JSON.parse(fs.readFileSync('scripts/layers.config.json', 'utf8'));
const used = new Set();
// Curated places, so bulk layers can drop their copies of the same thing.
const curatedRefs = new Set();
const curatedPlaces = [];
const refsOf = r => [...String(r.src || '').matchAll(/(osm (?:node|way|relation) \d+|wikidata Q\d+|openplaques \d+|nhle \d+|hes LB\d+|cadw \d+)/g)].map(m => m[1])
  .concat(r.wikidata ? ['wikidata ' + r.wikidata] : []);
const words = n => new Set(String(n).toLowerCase().match(/[a-z]{4,}/g) || []);
function metres(a, b) {
  const R = 6371000, toRad = x => x * Math.PI / 180;
  const dLat = toRad(b[0] - a[0]), dLon = toRad(b[1] - a[1]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}
// Same source id always counts; the nearby-and-same-name test only for layers that ask for it ("dedupe": "near").
function duplicateOfCurated(r, layer) {
  if (refsOf(r).some(x => curatedRefs.has(x))) return true;
  if (layer.dedupe !== 'near') return false;
  const w = words(r.name);
  return curatedPlaces.some(c => Math.abs(c.ll[0] - r.ll[0]) < 0.002 && metres(c.ll, r.ll) < 100 && [...words(c.name)].some(x => w.has(x)));
}
const dropped = {};

// A layer built from several sources (Wikidata and OpenStreetMap, say) keeps the first source's copy of a
// place: a later record is dropped when it shares a source id with an earlier source's record, or, for
// "dedupe": "near" layers, sits within 100 m of one whose name contains every distinctive word of the
// shorter name ("Robin Hood" and "Statue of Robin Hood", but not "Watt a Clever Cow" and "Statue of James Watt").
const GENERIC = new Set(['statue', 'sculpture', 'memorial', 'monument', 'figure', 'artwork', 'bust', 'with', 'from']);
const sameName = (a, b) => {
  const [x, y] = [a, b].map(n => new Set([...words(n)].filter(w => !GENERIC.has(w))));
  const [small, big] = x.size <= y.size ? [x, y] : [y, x];
  // A name with nothing distinctive ("War memorial", "Statue") matches anything this close.
  return small.size === 0 || [...small].every(w => big.has(w));
};
function withinLayerDedupe(layer) {
  const refFrom = new Map(), grid = new Map();
  const cell = (lat, lon) => `${Math.round(lat * 200)},${Math.round(lon * 100)}`;
  return r => {
    const refs = refsOf(r);
    let dup = refs.some(x => refFrom.has(x) && refFrom.get(x) !== r._from);
    if (!dup && layer.dedupe === 'near') {
      const [la, lo] = [Math.round(r.ll[0] * 200), Math.round(r.ll[1] * 100)];
      for (let a = -1; a <= 1 && !dup; a++) for (let b = -1; b <= 1 && !dup; b++) {
        dup = (grid.get(`${la + a},${lo + b}`) || []).some(c => c._from !== r._from && metres(c.ll, r.ll) < 100 && sameName(c.name, r.name));
      }
    }
    if (dup) return true;
    refs.forEach(x => refFrom.has(x) || refFrom.set(x, r._from));
    const k = cell(...r.ll);
    grid.set(k, [...(grid.get(k) || []), r]);
    return false;
  };
}

// Ids must survive a re-scan, because visited and wishlist entries are keyed by them. Bulk layers take
// their id from the most stable source reference rather than the name (which a source can change).
// Curated layers keep their readable ids, so existing links keep working.
import crypto from 'crypto';
const hash8 = s => crypto.createHash('sha1').update(s).digest('hex').slice(0, 8);
function stableId(r) {
  const src = String(r.src || '');
  let m;
  if ((m = /openplaques (\d+)/.exec(src))) return 'op-' + m[1];
  if ((m = /wikidata (Q\d+)/.exec(src)) || (r.wikidata && (m = [0, r.wikidata]))) return 'wd-' + m[1].toLowerCase();
  if ((m = /nhle (\d+)/.exec(src))) return 'nhle-' + m[1];
  if ((m = /hes (LB\d+)/i.exec(src))) return 'hes-' + m[1].toLowerCase();
  if ((m = /cadw (\d+)/.exec(src))) return 'cadw-' + m[1];
  if ((m = /osm (node|way|relation) (\d+)/.exec(src))) return `osm-${m[1][0]}${m[2]}`;
  if ((m = /\bgcr (\d+)/.exec(src))) return 'gcr-' + m[1];
  if ((m = /\blpo ([^;]+)/.exec(src))) return 'lpo-' + m[1].trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
  const geo = [...src.matchAll(/geograph (\d+)/g)].map(x => +x[1]).sort((a, b) => a - b);
  const files = [...src.matchAll(/commons (File:[^+;]+?\.(?:jpe?g|png|tiff?|gif))/gi)].map(x => x[1].trim()).sort();
  if (files.length) return 'cm-' + hash8(files[0]);
  if (geo.length) return 'geo-' + geo[0];
  return null;
}
const problems = [];
const manifest = [];

function regionFor(r) {
  if (!r.region) return undefined;
  if (REGIONS.includes(r.region)) return r.region;
  if (OLD_REGION[r.region]) return OLD_REGION[r.region];
  if (r.region === 'South of England') return r.ll[1] > -0.5 && r.ll[0] > 51.6 ? 'East of England' : 'South East';
  problems.push(`${r.cat}/${r.id}: unknown region ${r.region}`);
  return 'South East';
}

function load(layer) {
  if (layer.key === 'goldsworthy') {
    return JSON.parse(fs.readFileSync('data/sites.json', 'utf8')).map(s => ({ ...s, artist: 'Andy Goldsworthy' }));
  }
  const files = (layer.sources || [layer.key]).map(k => `scripts/work/layers/${k}.json`);
  return files.flatMap((f, from) => {
    if (!fs.existsSync(f)) { problems.push(`${layer.key}: no source file ${f} (run its fetch script)`); return []; }
    return JSON.parse(fs.readFileSync(f, 'utf8')).map(r => ({ ...r, _from: from }));
  }).concat((claimed[layer.key] || []).map(r => ({ ...r, _from: files.length })));
}

// A layer can collect matching places from other layers ("claims"): a war memorial recorded as public art,
// a listed building or a plaque moves to the war memorials layer, so it shows once, in the layer it belongs
// to. A place is claimed when its name matches, or when one of the layer's own sources has the same record.
const claimed = {};
const claimRules = config.filter(l => l.claims).map(l => ({
  to: l.key, from: new Set(l.claims.from), re: new RegExp(l.claims.name, 'i'), refs: new Set(load(l).flatMap(refsOf)),
}));
const claimCount = {};
function claimFor(key, r) {
  for (const c of claimRules) {
    if (c.from.has(key) && (c.re.test(r.name) || refsOf(r).some(x => c.refs.has(x)))) return c.to;
  }
  return null;
}

function compact(layer, r) {
  for (const k of COMPACT_DROP) delete r[k];
  for (const [prefix, base] of Object.entries(layer.urls || {})) {
    if (r.id.startsWith(prefix) && r.url === base + r.id.slice(prefix.length)) delete r.url;
  }
  if (layer.kinds && r.kind === layer.kinds[r.grade]) delete r.kind;
  if (!r.photos.length) delete r.photos;
  if (r.access === (layer.defaultAccess || 'open')) delete r.access;
  return r;
}

for (const layer of config) {
  const out = [];
  const fix = overrides[layer.key] || {};
  const seenInLayer = (layer.sources || []).length > 1 ? withinLayerDedupe(layer) : () => false;
  for (const raw of load(layer)) {
    const o = fix[raw.src] || fix[raw.id];
    if (o && o.hide) continue;
    const r = { ...raw, ...(o || {}), cat: layer.key };
    if (!r.name || !Array.isArray(r.ll) || r.ll.length !== 2 || !r.ll.every(Number.isFinite)) {
      problems.push(`${layer.key}/${r.id}: missing name or position, skipped`); continue;
    }
    const [lat, lon] = r.ll;
    if (lat < 49.8 || lat > 61 || lon < -10.7 || lon > 2) { problems.push(`${layer.key}/${r.id}: outside UK/Ireland, skipped`); continue; }
    r.ll = [+lat.toFixed(5), +lon.toFixed(5)];
    const to = claimFor(layer.key, r);
    if (to) {
      if (manifest.some(m => m.key === to)) throw new Error(`${to} claims from ${layer.key}, so it must come after it in layers.config.json`);
      (claimed[to] ||= []).push({ ...raw, ...(o || {}) });
      claimCount[`${to} from ${layer.key}`] = (claimCount[`${to} from ${layer.key}`] || 0) + 1;
      continue;
    }
    if (layer.curated) { refsOf(r).forEach(x => curatedRefs.add(x)); curatedPlaces.push(r); }
    else if (duplicateOfCurated(r, layer) || seenInLayer(r)) { (dropped[layer.key] ||= []).push(r.name); continue; }
    r.region = regionFor(r);
    if (!ACCESS.has(r.access)) r.access = layer.defaultAccess || 'open';
    r.photos = (r.photos || []).map(p => p && p.src && p.page ? hostPhoto(p) : null)
      .filter(p => p && FREE.test((p.license || '').trim()) && !(NEEDS_AUTHOR.test(p.license) && !(p.artist || '').trim() || /^unknown$/i.test((p.artist || '').trim()) && NEEDS_AUTHOR.test(p.license)))
      .slice(0, 4)
      .map(p => ({ src: p.src, page: p.page, license: p.license.trim(), artist: (p.artist || 'Unknown').slice(0, 80), title: p.title || '' }));
    let id = (!layer.curated && stableId(r)) || String(r.id || r.name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    if (used.has(id)) id = `${layer.key}-${id}`;
    for (let n = 2; used.has(id); n++) id = id.replace(/-\d+$/, '') + '-' + n;
    used.add(id);
    r.id = id;
    r.tier = layer.curated ? 1 : (r.tier || (r.photos.length ? 1 : 2));
    const rec = {};
    for (const k of KEEP) if (r[k] !== undefined && r[k] !== null && r[k] !== '') rec[k] = r[k];
    out.push(rec);
  }
  out.sort((a, b) => a.name.localeCompare(b.name));
  const fetched = out.map(r => r.fetched).filter(Boolean).sort().pop();
  const photos = out.filter(r => r.photos.length).length;
  // One file per interest tier, so the app loads the highlights first and the rest only when asked.
  const files = [];
  for (const tier of [1, 2]) {
    const recs = out.filter(r => r.tier === tier);
    if (!recs.length) continue;
    const file = `data/layers/${layer.key}-${tier}.json`;
    fs.writeFileSync(file, JSON.stringify(layer.compact ? recs.map(r => compact(layer, { ...r })) : recs));
    files.push({ tier, file, count: recs.length });
  }
  const { sources, ...meta } = layer;
  manifest.push({ ...meta, files, count: out.length, photos, ...(fetched ? { fetched } : {}) });
}
fs.writeFileSync('data/layers.json', JSON.stringify(manifest, null, 1));
for (const old of fs.readdirSync('data/layers')) {
  if (!manifest.some(m => m.files.some(f => f.file === 'data/layers/' + old))) fs.unlinkSync('data/layers/' + old);
}
for (const m of manifest) {
  console.log(`${m.key.padEnd(15)} ${String(m.count).padStart(6)} places, ${m.photos} with photos; ` +
    m.files.map(f => `tier ${f.tier}: ${f.count} (${Math.round(fs.statSync(f.file).size / 1024)} KB)`).join(', '));
}
// The sources register, rewritten on every build so it always matches the data.
// Which OpenStreetMap extract the OSM-based layers were last read from (scripts/osm/osm_extract.py).
function osmNote() {
  const f = 'scripts/work/raw/osm/poi.meta.json';
  if (!fs.existsSync(f)) return [];
  const m = JSON.parse(fs.readFileSync(f, 'utf8'));
  return [`OpenStreetMap data is read from the Geofabrik United Kingdom extract (${m.extract}), data as of ${m.data_as_of}`,
    `(MD5 ${m.md5}), through \`scripts/osm/osm_extract.py\`, which keeps the tags listed in \`scripts/osm/filters.txt\`.`,
    'Refresh it with `scripts/osm/fetch-extract.sh && python3 scripts/osm/osm_extract.py build` before re-running the OSM-based layers.', ''];
}
const md = ['# Layer sources', '',
  'Rewritten by `node scripts/build-layers.mjs`; do not edit by hand. To refresh a layer, run its fetch commands, then the build.',
  'Hand corrections that must survive a refresh go in `scripts/layers/overrides.json`, keyed by layer and then by the record\'s `src` or `id`',
  '(for example `{"listed": {"nhle 1234567": {"hide": true}}}`).', '',
  ...osmNote(), '| Layer | Places | Highlights | Last fetched | Licence |', '|---|---|---|---|---|',
  ...manifest.map(m => `| ${m.name} | ${m.count} | ${m.files.find(f => f.tier === 1)?.count || 0} | ${m.fetched || 'n/a'} | ${m.licence || ''} |`), ''];
for (const m of config) {
  const built = manifest.find(x => x.key === m.key);
  md.push(`## ${m.name} (\`${m.key}\`)`, '', m.description, '',
    `- Source: ${m.source}`, `- Licence: ${m.licence}`, ...(m.attribution ? [`- Attribution: ${m.attribution}`] : []),
    `- Fetch: ${[].concat(m.fetch || (m.key === 'goldsworthy' ? 'see README (scripts/sites.mjs ... scripts/curate.mjs)' : 'none')).map(c => '`' + c + '`').join(', then ')}`,
    `- Work files: ${(m.sources || [m.key]).map(k => '`scripts/work/layers/' + k + '.json`').join(', ')}`,
    `- Built: ${built.count} places (${built.files.map(f => `tier ${f.tier}: ${f.count}`).join(', ') || 'no data yet'}), ${built.photos} with photos${built.fetched ? ', fetched ' + built.fetched : ''}`, '');
}
fs.writeFileSync('scripts/layers/SOURCES.md', md.join('\n'));

if (geoUnhosted.size) console.log(`${geoUnhosted.size} Geograph photos dropped because they are not hosted yet (run node scripts/photos/geograph.mjs)`);
for (const [k, n] of Object.entries(claimCount)) console.log(`${k}: moved ${n}`);
for (const [k, n] of Object.entries(dropped)) console.log(`${k}: dropped ${n.length} duplicates (of a curated place or an earlier source): ${n.slice(0, 8).join("; ")}`);
if (problems.length) console.log('\n' + problems.join('\n'));
