// Fetch UK museums and galleries from OpenStreetMap, with photos and Wikipedia links from Wikidata.
// Sources: OpenStreetMap (ODbL, © OpenStreetMap contributors): tourism=museum or tourism=gallery with a name,
//          read from the downloaded extract (scripts/osm/osm_extract.py); the query is osm-museums.overpassql.
//          Wikidata (CC0): for places OSM links to a Wikidata item, its photo (P18) and English Wikipedia article.
// Photos: Wikimedia Commons, free licences with a named author only.
// Usage: node scripts/layers/museums/fetch.mjs [output]   (default scripts/work/layers/museums.json)
import fs from 'fs';
import { execFileSync } from 'child_process';

const UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)';
const HERE = new URL('.', import.meta.url).pathname;
const out = process.argv[2] || 'scripts/work/layers/museums.json';
const fetched = new Date().toISOString().slice(0, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const getJson = async u => {
  for (let i = 0; i < 4; i++) {
    const r = await fetch(u, { headers: { 'User-Agent': UA } }).catch(() => null);
    if (r?.ok) return r.json();
    await sleep(5000 * (i + 1));
  }
  throw new Error('failed: ' + u.slice(0, 80));
};

const els = JSON.parse(execFileSync('python3', [new URL('../../osm/osm_extract.py', import.meta.url).pathname, 'query', HERE + 'osm-museums.overpassql'],
  { maxBuffer: 1 << 30 })).elements;
const type = { n: 'node', w: 'way', r: 'relation' };
const KIND = { museum: 'Museum', gallery: 'Gallery' };
const MUSEUM = { history: 'History museum', local: 'Local museum', art: 'Art museum', transport: 'Transport museum', military: 'Military museum',
  railway: 'Railway museum', science: 'Science museum', technology: 'Science and technology museum', natural_history: 'Natural history museum',
  archaeological: 'Archaeology museum', open_air: 'Open-air museum', heritage: 'Heritage museum', industrial: 'Industrial museum',
  living_history: 'Living history museum', maritime: 'Maritime museum', children: "Children's museum" };
const commonsFile = v => {
  v = v && (/commons\.wikimedia\.org\/wiki\/(File:[^?#]+)/.exec(v)?.[1] || v);
  return v && /^File:/i.test(v) ? decodeURIComponent(v).replace(/_/g, ' ') : null;
};
const records = els.map(e => {
  const t = e.tags, lat = e.lat ?? e.center.lat, lon = e.lon ?? e.center.lon;
  const wp = t.wikipedia && /^en:/.test(t.wikipedia) ? 'https://en.wikipedia.org/wiki/' + encodeURIComponent(t.wikipedia.slice(3).replace(/ /g, '_')) : null;
  return {
    id: `osm-${e.type[0]}${e.id}`, name: t.name, ll: [+lat.toFixed(5), +lon.toFixed(5)],
    kind: MUSEUM[t.museum] || KIND[t.tourism],
    place: t['addr:city'] || t['addr:town'] || t['addr:village'] || undefined,
    about: t.description || undefined,
    url: wp || t.website || t['contact:website'] || `https://www.openstreetmap.org/${type[e.type[0]]}/${e.id}`,
    wikidata: /^Q\d+$/.test(t.wikidata || '') ? t.wikidata : undefined,
    file: commonsFile(t.wikimedia_commons || t.image),
    // Public access, not opening hours: free entry is "free public access", a charge is "paid entry or booking",
    // no fee recorded is unknown, and a private collection is left off the map.
    access: ['private', 'no'].includes(t.access) ? 'private' : t.fee === 'no' || t.fee === 'free' ? 'open' : t.fee === 'yes' ? 'limited' : 'unknown',
    src: `osm ${type[e.type[0]]} ${e.id}` + (t.wikidata ? `; wikidata ${t.wikidata}` : ''), fetched,
  };
});
console.log(`openstreetmap: ${records.length} museums and galleries, ${records.filter(r => r.wikidata).length} linked to Wikidata`);

// Wikidata: photo and English Wikipedia article for linked items, 50 at a time.
const linked = records.filter(r => r.wikidata);
for (let i = 0; i < linked.length; i += 50) {
  const batch = linked.slice(i, i + 50);
  const j = await getJson('https://www.wikidata.org/w/api.php?' + new URLSearchParams({
    action: 'wbgetentities', ids: [...new Set(batch.map(r => r.wikidata))].join('|'), props: 'claims|sitelinks|descriptions', languages: 'en', sitefilter: 'enwiki', format: 'json',
  }));
  for (const r of batch) {
    const e = j.entities?.[r.wikidata];
    if (!e || e.missing !== undefined) continue;
    const img = e.claims?.P18?.[0]?.mainsnak?.datavalue?.value;
    if (img && !r.file) r.file = 'File:' + img;
    const title = e.sitelinks?.enwiki?.title;
    if (title && !/wikipedia\.org/.test(r.url)) r.url = 'https://en.wikipedia.org/wiki/' + encodeURIComponent(title.replace(/ /g, '_'));
    if (!r.about && e.descriptions?.en?.value) r.about = e.descriptions.en.value.replace(/^./, c => c.toUpperCase()) + '.';
  }
  process.stdout.write(`\rwikidata ${Math.min(i + 50, linked.length)}/${linked.length}   `);
  await sleep(300);
}
console.log();

// Commons licences: free licences with a named author only.
const FREE = /^(CC BY(-SA)? \d\.\d( [a-z]{2})?|CC0( 1\.0)?|Public domain)$/i;
const strip = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const withFile = records.filter(r => r.file);
for (let i = 0; i < withFile.length; i += 50) {
  const batch = withFile.slice(i, i + 50);
  const j = await getJson('https://commons.wikimedia.org/w/api.php?' + new URLSearchParams({
    action: 'query', titles: batch.map(r => r.file).join('|'), prop: 'imageinfo', iiprop: 'url|extmetadata', iiurlwidth: '1280', format: 'json',
  }));
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
for (const r of records) {
  delete r.file;
  r.tier = r.photos || /wikipedia\.org/.test(r.url) || r.wikidata ? 1 : 2;
}
fs.writeFileSync(out, JSON.stringify(records));
console.log(`wrote ${records.length} (${records.filter(r => r.tier === 1).length} highlights, ${records.filter(r => r.photos).length} with photos) to ${out}`);
