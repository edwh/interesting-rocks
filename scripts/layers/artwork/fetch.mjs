// Fetch notable public art in the UK from Wikidata: sculptures, statues and installations with a position.
// Source: Wikidata (CC0). Photos: Wikimedia Commons, free licences with a named author only.
// Usage: node scripts/layers/artwork/fetch.mjs [output]   (default scripts/work/layers/artwork.json)
// fetch-osm.mjs is an OpenStreetMap version (ODbL, many more minor works) for when Overpass is reachable.
import fs from 'fs';

const UA = { 'User-Agent': 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)', Accept: 'application/sparql-results+json' };
const out = process.argv[2] || 'scripts/work/layers/artwork.json';
const fetched = new Date().toISOString().slice(0, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const TYPES = { Q860861: 'Sculpture', Q179700: 'Statue', Q20437094: 'Installation' };
const QUERY = `SELECT ?item ?itemLabel ?itemDescription ?loc ?image ?creatorLabel ?inception ?article WHERE {
  ?item wdt:P31 wd:{TYPE}; wdt:P17 wd:Q145; wdt:P625 ?loc.
  OPTIONAL { ?item wdt:P18 ?image }
  OPTIONAL { ?item wdt:P170 ?creator }
  OPTIONAL { ?item wdt:P571 ?inception }
  OPTIONAL { ?article schema:about ?item; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}`;
fs.writeFileSync(new URL('./query.rq', import.meta.url), QUERY + '\n');

async function sparql(q) {
  for (let i = 0; i < 4; i++) {
    const r = await fetch('https://query.wikidata.org/sparql', { method: 'POST', headers: { ...UA, 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams({ query: q }) });
    if (r.ok) return (await r.json()).results.bindings;
    await sleep(10000 * (i + 1));
  }
  throw new Error('Wikidata query failed');
}

const items = new Map();
for (const [type, kind] of Object.entries(TYPES)) {
  for (const b of await sparql(QUERY.replace('{TYPE}', type))) {
    const qid = b.item.value.split('/').pop();
    const m = /Point\(([-\d.]+) ([-\d.]+)\)/.exec(b.loc.value);
    if (!m || /^Q\d+$/.test(b.itemLabel?.value || '')) continue;
    const r = items.get(qid) || {
      id: 'wd-' + qid.toLowerCase(), name: b.itemLabel.value, ll: [+(+m[2]).toFixed(5), +(+m[1]).toFixed(5)],
      kind, about: b.itemDescription?.value ? b.itemDescription.value.replace(/^./, c => c.toUpperCase()) + '.' : undefined,
      url: b.article?.value || `https://www.wikidata.org/wiki/${qid}`, wikidata: qid, artists: new Set(), files: new Set(),
      year: b.inception?.value ? b.inception.value.slice(0, 4).replace(/^0+/, '') : undefined,
      src: `wikidata ${qid}`, fetched,
    };
    if (b.creatorLabel && !/^Q\d+$/.test(b.creatorLabel.value)) r.artists.add(b.creatorLabel.value);
    if (b.image) r.files.add('File:' + decodeURIComponent(b.image.value.split('/').pop()).replace(/_/g, ' '));
    items.set(qid, r);
  }
  console.log(`${kind}: ${items.size} items so far`);
  await sleep(3000);
}

const FREE = /^(CC BY(-SA)? \d\.\d( [a-z]{2})?|CC0( 1\.0)?|Public domain)$/i;
const strip = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const records = [...items.values()];
const withFile = records.filter(r => r.files.size);
for (let i = 0; i < withFile.length; i += 50) {
  const batch = withFile.slice(i, i + 50);
  const titles = batch.map(r => [...r.files][0]);
  const u = 'https://commons.wikimedia.org/w/api.php?' + new URLSearchParams({
    action: 'query', titles: titles.join('|'), prop: 'imageinfo', iiprop: 'url|extmetadata', iiurlwidth: '1280', format: 'json',
  });
  const j = await (await fetch(u, { headers: { 'User-Agent': UA['User-Agent'] } })).json();
  const norm = new Map((j.query?.normalized || []).map(n => [n.from, n.to]));
  const pages = new Map(Object.values(j.query?.pages || {}).map(p => [p.title, p]));
  batch.forEach((r, k) => {
    const ii = pages.get(norm.get(titles[k]) || titles[k])?.imageinfo?.[0];
    const m = ii?.extmetadata || {};
    const license = strip(m.LicenseShortName?.value);
    const artist = strip(m.Artist?.value).slice(0, 80);
    if (ii && FREE.test(license) && (artist || !/^CC BY/i.test(license))) {
      r.photos = [{ src: ii.thumburl || ii.url, page: ii.descriptionurl, license, artist: artist || 'Unknown', title: titles[k].replace(/^File:/, '') }];
    }
  });
  await sleep(500);
}
for (const r of records) {
  r.artist = [...r.artists].join(', ') || undefined;
  delete r.artists; delete r.files;
  r.tier = r.photos || /wikipedia\.org/.test(r.url) ? 1 : 2;
}
fs.writeFileSync(out, JSON.stringify(records));
console.log(`wrote ${records.length} artworks (${records.filter(r => r.tier === 1).length} highlights, ${records.filter(r => r.photos).length} with photos) to ${out}`);
