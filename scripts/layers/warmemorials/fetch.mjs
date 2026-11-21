// Fetch UK war memorials from Wikidata and OpenStreetMap.
// Sources: Wikidata (CC0): items that are a war memorial (Q575759) or a subclass, in the UK, with a position.
//          OpenStreetMap (ODbL, © OpenStreetMap contributors): historic=memorial with memorial=war_memorial,
//          or a memorial named "war memorial", "cenotaph" or "roll of honour". Read from the downloaded extract
//          (scripts/osm/osm_extract.py); the queries are the .overpassql files beside this script.
// Photos: Wikimedia Commons, free licences with a named author only.
// War memorials already in other layers (public art, listed buildings, plaques) are moved into this layer by
// the build ("claims" in scripts/layers.config.json).
// Usage: node scripts/layers/warmemorials/fetch.mjs   (writes scripts/work/layers/warmemorials-wd.json and -osm.json)
import fs from 'fs';
import { execFileSync } from 'child_process';

const UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)';
const HERE = new URL('.', import.meta.url).pathname;
const OUT = 'scripts/work/layers/';
const fetched = new Date().toISOString().slice(0, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const QUERY = `SELECT ?item ?itemLabel ?itemDescription ?loc ?image ?inception ?article ?nhle ?hes ?cadw WHERE {
  ?item wdt:P31/wdt:P279* wd:Q575759; wdt:P17 wd:Q145; wdt:P625 ?loc.
  OPTIONAL { ?item wdt:P18 ?image }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?item wdt:P1216 ?nhle }
  OPTIONAL { ?item wdt:P709 ?hes }
  OPTIONAL { ?item wdt:P1459 ?cadw }
  OPTIONAL { ?article schema:about ?item; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}`;
fs.writeFileSync(HERE + 'wikidata.rq', QUERY + '\n');

async function sparql(q) {
  for (let i = 0; i < 4; i++) {
    const r = await fetch('https://query.wikidata.org/sparql', {
      method: 'POST', body: new URLSearchParams({ query: q }),
      headers: { 'User-Agent': UA, Accept: 'application/sparql-results+json', 'Content-Type': 'application/x-www-form-urlencoded' },
    }).catch(() => null);
    if (r?.ok) return (await r.json()).results.bindings;
    console.log(`  Wikidata answered ${r?.status || 'nothing'}, retrying`);
    await sleep(15000 * (i + 1));
  }
  throw new Error('Wikidata query failed');
}

// Free-licence photo details for Commons files, 50 at a time.
const FREE = /^(CC BY(-SA)? \d\.\d( [a-z]{2})?|CC0( 1\.0)?|Public domain)$/i;
const strip = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
async function addPhotos(records) {
  const withFile = records.filter(r => r.file);
  for (let i = 0; i < withFile.length; i += 50) {
    const batch = withFile.slice(i, i + 50);
    const u = 'https://commons.wikimedia.org/w/api.php?' + new URLSearchParams({
      action: 'query', titles: batch.map(r => r.file).join('|'), prop: 'imageinfo', iiprop: 'url|extmetadata', iiurlwidth: '1280', format: 'json',
    });
    const j = await (await fetch(u, { headers: { 'User-Agent': UA } })).json();
    const norm = new Map((j.query?.normalized || []).map(n => [n.from, n.to]));
    const pages = new Map(Object.values(j.query?.pages || {}).map(p => [p.title, p]));
    for (const r of batch) {
      const ii = pages.get(norm.get(r.file) || r.file)?.imageinfo?.[0];
      const m = ii?.extmetadata || {};
      const license = strip(m.LicenseShortName?.value), artist = strip(m.Artist?.value).slice(0, 80);
      if (ii && FREE.test(license) && (artist || !/^CC BY/i.test(license))) {
        r.photos = [{ src: ii.thumburl || ii.url, page: ii.descriptionurl, license, artist: artist || 'Unknown', title: r.file.replace(/^File:/, '') }];
      }
    }
    process.stdout.write(`\rphotos ${Math.min(i + 50, withFile.length)}/${withFile.length}   `);
    await sleep(400);
  }
  console.log();
  for (const r of records) delete r.file;
}
const commonsFile = v => {
  v = v && (/commons\.wikimedia\.org\/wiki\/(File:[^?#]+)/.exec(v)?.[1] || v);
  return v && /^File:/i.test(v) ? decodeURIComponent(v).replace(/_/g, ' ') : null;
};

// ---- Wikidata
const items = new Map();
for (const b of await sparql(QUERY)) {
  const qid = b.item.value.split('/').pop();
  const m = /Point\(([-\d.]+) ([-\d.]+)\)/.exec(b.loc.value);
  if (!m || /^Q\d+$/.test(b.itemLabel?.value || '')) continue;
  const r = items.get(qid) || {
    id: 'wd-' + qid.toLowerCase(), name: b.itemLabel.value, ll: [+(+m[2]).toFixed(5), +(+m[1]).toFixed(5)], kind: 'War memorial',
    about: b.itemDescription?.value ? b.itemDescription.value.replace(/^./, c => c.toUpperCase()) + '.' : undefined,
    url: b.article?.value || `https://www.wikidata.org/wiki/${qid}`, wikidata: qid,
    year: b.inception?.value ? b.inception.value.slice(0, 4).replace(/^0+/, '') : undefined,
    refs: new Set([`wikidata ${qid}`]), fetched,
  };
  if (b.nhle) r.refs.add('nhle ' + b.nhle.value);
  if (b.hes) r.refs.add('hes ' + b.hes.value);
  if (b.cadw) r.refs.add('cadw ' + b.cadw.value);
  if (b.image && !r.file) r.file = 'File:' + decodeURIComponent(b.image.value.split('/').pop()).replace(/_/g, ' ');
  items.set(qid, r);
}
const wd = [...items.values()].map(({ refs, ...r }) => ({ ...r, src: [...refs].join('; ') }));
console.log(`wikidata: ${wd.length} war memorials`);
await addPhotos(wd);
for (const r of wd) r.tier = r.photos || /wikipedia\.org/.test(r.url) ? 1 : 2;
fs.writeFileSync(OUT + 'warmemorials-wd.json', JSON.stringify(wd));

// ---- OpenStreetMap, from the extract
const query = f => JSON.parse(execFileSync('python3', [new URL('../../osm/osm_extract.py', import.meta.url).pathname, 'query', HERE + f],
  { maxBuffer: 1 << 30 })).elements;
const els = query('osm-warmemorials.overpassql');
const towns = query('osm-places.overpassql').map(e => [e.lat, e.lon, e.tags.name]);
const grid = new Map();
for (const t of towns) { const k = `${Math.round(t[0] * 20)},${Math.round(t[1] * 12)}`; grid.set(k, [...(grid.get(k) || []), t]); }
function nearestTown(lat, lon) {
  let best = null, bd = 1e9;
  const [a, b] = [Math.round(lat * 20), Math.round(lon * 12)];
  for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) for (const t of grid.get(`${a + i},${b + j}`) || []) {
    const d = (t[0] - lat) ** 2 + ((t[1] - lon) * Math.cos(lat * Math.PI / 180)) ** 2;
    if (d < bd) { bd = d; best = t[2]; }
  }
  return best;
}
const FORM = { plaque: 'War memorial plaque', plate: 'War memorial plaque', cross: 'War memorial cross', stone_cross: 'War memorial cross',
  obelisk: 'War memorial obelisk', statue: 'War memorial statue', cenotaph: 'Cenotaph', stone: 'War memorial stone', window: 'Memorial window',
  wall: 'War memorial wall', gate: 'Memorial gate', bench: 'Memorial bench' };
const type = { n: 'node', w: 'way', r: 'relation' };
const osm = els.map(e => {
  const t = e.tags, lat = e.lat ?? e.center.lat, lon = e.lon ?? e.center.lon;
  const town = nearestTown(lat, lon);
  const form = t['memorial:type'] || t.memorial_type || '';
  const kind = /cenotaph/i.test(t.name || '') ? 'Cenotaph' : FORM[form] || 'War memorial';
  const insc = (t.inscription || '').replace(/\s+/g, ' ').trim();
  return {
    id: `osm-${e.type[0]}${e.id}`, name: t.name || 'War memorial', ll: [+lat.toFixed(5), +lon.toFixed(5)], kind,
    place: t.name ? (t['addr:city'] || t['addr:town'] || t['addr:village'] || (town ? 'near ' + town : undefined)) : (town ? 'near ' + town : undefined),
    about: insc ? `Inscription: "${insc.length > 400 ? insc.slice(0, 397) + '…' : insc}"` : t.description || undefined,
    year: t.start_date ? t.start_date.slice(0, 4) : undefined,
    url: t.wikipedia ? 'https://en.wikipedia.org/wiki/' + encodeURIComponent(t.wikipedia.replace(/^en:/, '').replace(/ /g, '_')) : `https://www.openstreetmap.org/${type[e.type[0]]}/${e.id}`,
    wikidata: t.wikidata || undefined, file: commonsFile(t.wikimedia_commons || t.image),
    access: ['private', 'no'].includes(t.access) ? 'private' : 'open',
    src: `osm ${type[e.type[0]]} ${e.id}` + (t.wikidata ? `; wikidata ${t.wikidata}` : ''), fetched,
  };
});
console.log(`openstreetmap: ${osm.length} war memorials (${osm.filter(r => r.name === 'War memorial').length} unnamed, labelled by the nearest place)`);
await addPhotos(osm);
for (const r of osm) r.tier = r.photos || /wikipedia\.org/.test(r.url) ? 1 : 2;
fs.writeFileSync(OUT + 'warmemorials-osm.json', JSON.stringify(osm));
