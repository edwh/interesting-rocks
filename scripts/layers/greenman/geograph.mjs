// Green Man carvings photographed on Geograph, to add to the Green Men layer.
// Source: Geograph Britain and Ireland, via its public JSON feed (syndicator.php). Every photo is licensed
// CC BY-SA 2.0 by its photographer, who is credited with a link to the photo page. Geograph asks reusers
// not to hotlink, so the build swaps each photo for a Commons copy or our own copy
// (node scripts/photos/geograph.mjs). The date each photo was taken is kept as proof of life.
// Pubs called the Green Man are dropped; photos of the same church are grouped into one place.
// Usage: node scripts/layers/greenman/geograph.mjs   (writes scripts/work/layers/greenman-geograph.json)
import fs from 'fs';
import { execFileSync } from 'child_process';

const UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)';
const OUT = 'scripts/work/layers/greenman-geograph.json';
const RAW = 'scripts/work/raw/greenman';
const QUERIES = ['"green man" church', '"green man" carving', '"green man" boss', '"green man" corbel', '"green man" misericord',
  '"green man" cathedral', '"green man" abbey', '"green man" priory', '"foliate head"', '"foliate mask"', '"jack in the green" carving',
  // The feed stops at 400 results per search, so narrower searches reach the rest.
  '"green man" nave', '"green man" porch', '"green man" chancel', '"green man" screen', '"green man" bench', '"green man" roof',
  '"green man" capital', '"green man" font', '"green man" tomb', '"green man" norman', '"green man" medieval', '"green man" century'];
const fetched = new Date().toISOString().slice(0, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
fs.mkdirSync(RAW, { recursive: true });
fs.writeFileSync(new URL('./geograph-queries.txt', import.meta.url), QUERIES.join('\n') + '\n');

async function getJson(url) {
  for (let i = 0; i < 4; i++) {
    const r = await fetch(url, { headers: { 'User-Agent': UA } }).catch(() => null);
    if (r?.ok) return r.json().catch(() => null);
    await sleep(5000 * (i + 1));
  }
  return null;
}

// Every query, following the feed's "next" links. Raw results are cached so a rerun is cheap.
const items = new Map();
for (const q of QUERIES) {
  const file = `${RAW}/${q.replace(/\W+/g, '_')}.json`;
  let got = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : null;
  if (!got) {
    got = [];
    let url = 'https://www.geograph.org.uk/syndicator.php?' + new URLSearchParams({ q, format: 'JSON', perpage: '100' });
    for (let page = 0; url && page < 30; page++) {
      const j = await getJson(url);
      if (!j?.items?.length) break;
      got.push(...j.items);
      url = j.nextURL && j.nextURL !== url ? j.nextURL : null;
      await sleep(2000);
    }
    fs.writeFileSync(file, JSON.stringify(got));
  }
  for (const it of got) items.set(it.guid, it);
  console.log(`${q}: ${got.length} photos (${items.size} distinct so far)`);
}

// Keep carvings, drop pubs and inn signs.
const CARVING = /church|chapel|cathedral|abbey|priory|minster|carv|boss|corbel|capital|misericord|bench end|screen|font|tomb|monument|porch|chancel|nave|tympanum|foliate/i;
const PUB = /\b(pub|public house|inn|tavern|hotel|bar|brewery|restaurant|beer|ales?|pub sign|inn sign|mural|graffiti|street art|shopping)\b/i;
const text = it => `${it.title} ${it.description || ''} ${it.tags || ''}`;
const keep = [...items.values()].filter(it => /green man|foliate|jack in the green/i.test(text(it)) && CARVING.test(text(it)) && !PUB.test(`${it.title} ${it.description || ''}`)
  && it.lat && it.long && /creativecommons\.org\/licenses\/by-sa\/2\.0/.test(it.licence || ''));
console.log(`${keep.length} photos of carvings after dropping pubs and other mentions`);

// Nearest village or town, for the place line, from the OpenStreetMap extract.
const towns = JSON.parse(execFileSync('python3', [new URL('../../osm/osm_extract.py', import.meta.url).pathname, 'query', '-'],
  { input: '[out:json];node["place"~"^(city|town|village|hamlet|suburb)$"]["name"];out;', maxBuffer: 1 << 30 })).elements
  .map(e => [e.lat, e.lon, e.tags.name]);
const nearestTown = (lat, lon) => {
  let best = null, bd = 0.0009; // within about 3 km
  for (const t of towns) {
    const d = (t[0] - lat) ** 2 + ((t[1] - lon) * Math.cos(lat * Math.PI / 180)) ** 2;
    if (d < bd) { bd = d; best = t[2]; }
  }
  return best;
};

// Group photos taken of the same church: within about 120 m of each other.
const m = (a, b) => Math.hypot((a[0] - b[0]) * 111320, (a[1] - b[1]) * 111320 * Math.cos(a[0] * Math.PI / 180));
const groups = [];
for (const it of keep.sort((a, b) => (b.imageTaken || '').localeCompare(a.imageTaken || ''))) {
  const ll = [+it.lat, +it.long];
  const g = groups.find(x => m(x.ll, ll) < 120);
  if (g) g.items.push(it); else groups.push({ ll, items: [it] });
}
// Church names as photographers write them: "St.John the Baptist's church", "All Saints' Church", "Beguildy church".
const DEDICATION = /\b((?:St\.\s*|St\s+|Saint\s+)[A-Z][\w.]*(?:\s+(?:the|and|of|&)\s+[A-Z]\w*|\s+[A-Z]\w*)*|All Saints|Holy (?:Trinity|Cross|Rood|Sepulchre)|Christ Church|Our Lady)('s|’s|')?\s+(church|chapel|cathedral|priory|abbey|minster)\b/i;
const PLACECHURCH = /\b([A-Z][a-z]+(?:[- ][A-Z][a-z]+)?)\s+([Cc]hurch|[Cc]athedral|[Pp]riory|[Aa]bbey|[Mm]inster)\b/;
const NOTPLACE = /^(The|This|A|An|In|On|At|Parish|Norman|Medieval|Victorian|Saxon|Old|New|Green|Man|Our|St|Saint)$/;
const cap = w => w[0].toUpperCase() + w.slice(1).toLowerCase();
function churchOf(s) {
  let m = DEDICATION.exec(s);
  if (m && /^[A-Z]/.test(m[1])) return `${m[1].replace(/^(St\.?\s*|Saint\s+)/, 'St ')}${m[2] ? (m[2] === "'" ? "'" : "'s") : ''} ${cap(m[3])}`;
  m = PLACECHURCH.exec(s);
  if (m && !NOTPLACE.test(m[1].split(/[- ]/)[0])) return `${m[1]} ${cap(m[2])}`;
  return null;
}
const strip = s => (s || '').replace(/https?:\/\/\S+/g, '').replace(/\s+/g, ' ').trim();
const records = groups.map(g => {
  const town = nearestTown(...g.ll);
  const church = g.items.map(it => churchOf(strip(it.description)) || churchOf(it.title)).find(Boolean);
  const inName = church && town && church.toLowerCase().includes(town.toLowerCase());
  const name = church ? `Green Man, ${church}${town && !inName ? ', ' + town : ''}` : `Green Man${town ? ' near ' + town : ''}`;
  const best = g.items.find(it => strip(it.description).length > 30) || g.items[0];
  const photos = g.items.slice(0, 4).map(it => ({
    src: it.thumb.replace(/_120x120\.jpg$/, '.jpg'), page: `https://www.geograph.org.uk/photo/${it.guid}`,
    license: 'CC BY-SA 2.0', artist: it.author, title: strip(it.title.replace(/^[A-Z]{1,2}\d+\s*:\s*/, '')), date: it.imageTaken || undefined,
  }));
  return {
    id: 'geo-' + g.items[0].guid, name, ll: [+g.ll[0].toFixed(5), +g.ll[1].toFixed(5)], group: 'Green Man carving', kind: 'Foliate head carving',
    place: town || undefined, about: strip(best.description).slice(0, 300) || undefined, url: photos[0].page,
    access: 'unknown', photos, tier: 1,
    src: g.items.map(it => 'geograph ' + it.guid).join('; '), fetched,
  };
});
fs.writeFileSync(OUT, JSON.stringify(records));
console.log(`wrote ${records.length} places (${records.filter(r => !r.name.includes(' near ') && r.name !== 'Green Man').length} named after their church) to ${OUT}`);
