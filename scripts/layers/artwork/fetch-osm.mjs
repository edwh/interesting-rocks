// Fetch named public artworks (sculpture, statues, installations; not murals or paintings) in the UK
// from OpenStreetMap, and look up licences for any linked Wikimedia Commons photos.
// Source: OpenStreetMap, read from the downloaded Geofabrik extract (scripts/osm/osm_extract.py) when it
// has been built, otherwise from the Overpass API in tiles. Licence: ODbL. Attribution: © OpenStreetMap contributors.
// Usage: node scripts/layers/artwork/fetch-osm.mjs [output]   (default scripts/work/layers/artwork-osm.json)
// Set OSM_SOURCE=overpass to skip the extract.
import fs from 'fs';
import { execFileSync } from 'child_process';

const ENDPOINTS = ['https://maps.mail.ru/osm/tools/overpass/api/interpreter', 'https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'];
const UA = { 'User-Agent': 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)' };
const out = process.argv[2] || 'scripts/work/layers/artwork-osm.json';
const fetched = new Date().toISOString().slice(0, 10);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const EXTRACT = new URL('../../osm/osm_extract.py', import.meta.url).pathname;
const INDEX = new URL('../../work/raw/osm/poi.jsonl', import.meta.url).pathname;

// The query for one tile (Overpass) or, with no box, for the whole extract.
const FILTER = '["tourism"="artwork"]["name"]["artwork_type"!~"mural|graffiti|painting|mosaic"]';
const query = (s, w, n, e) => `[out:json][timeout:120];area["ISO3166-1"="GB"][admin_level=2]->.gb;
(nwr${FILTER}${s === undefined ? '' : `(${s},${w},${n},${e})`}(area.gb););
out center tags;`;
fs.writeFileSync(new URL('./osm-query.txt', import.meta.url), query() + '\n');

async function overpass(q) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const url = ENDPOINTS[attempt % ENDPOINTS.length];
    try {
      const r = await fetch(url, { method: 'POST', body: new URLSearchParams({ data: q }), headers: UA });
      if (r.ok) return (await r.json()).elements;
      console.log(`  ${url} answered ${r.status}, retrying`);
    } catch (err) { console.log(`  ${url} failed (${err.message}), retrying`); }
    await sleep(15000 * (attempt + 1));
  }
  throw new Error('Overpass failed for a tile');
}

const els = new Map();
if (process.env.OSM_SOURCE !== 'overpass' && fs.existsSync(INDEX)) {
  const got = JSON.parse(execFileSync('python3', [EXTRACT, 'query', '-'], { input: query(), maxBuffer: 1 << 30 })).elements;
  for (const e of got) els.set(e.type[0] + e.id, e);
  console.log(`extract: ${els.size} artworks`);
} else {
  for (let s = 49.8; s < 61; s += 2) {
    for (let w = -8.8; w < 2; w += 2) {
      const got = await overpass(query(s, w, +(s + 2).toFixed(1), +(w + 2).toFixed(1)));
      for (const e of got) els.set(e.type[0] + e.id, e);
      process.stdout.write(`\rtile ${s},${w}: ${els.size} artworks so far   `);
      await sleep(3000);
    }
  }
}

const commonsFile = t => {
  const v = t.wikimedia_commons || (t.image && /commons\.wikimedia\.org\/wiki\/(File:[^?#]+)/.exec(t.image)?.[1]);
  return v && /^File:/i.test(v) ? decodeURIComponent(v).replace(/_/g, ' ') : null;
};
const cap = s => s && s.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
const records = [...els.values()].map(e => {
  const t = e.tags;
  const lat = e.lat ?? e.center?.lat, lon = e.lon ?? e.center?.lon;
  const type = { n: 'node', w: 'way', r: 'relation' }[e.type[0]];
  return {
    id: `osm-${e.type[0]}${e.id}`, name: t.name, ll: [+lat.toFixed(5), +lon.toFixed(5)],
    artist: t.artist_name || t.artist || undefined, kind: cap(t.artwork_type) || 'Artwork',
    year: t.start_date || undefined, about: t.description || undefined,
    url: t.wikipedia ? 'https://en.wikipedia.org/wiki/' + encodeURIComponent(t.wikipedia.replace(/^en:/, '').replace(/ /g, '_')) : (t.website || undefined),
    wikidata: t.wikidata || undefined, photoFile: commonsFile(t),
    access: t.access === 'private' ? 'limited' : 'open',
    src: `osm ${type} ${e.id}` + (t.wikidata ? `; wikidata ${t.wikidata}` : ''), fetched,
  };
});

// Licences for linked Commons photos, 50 files per request; only free licences are kept.
const FREE = /^(CC BY(-SA)?( \d\.\d)?|CC0|Public domain|PD|FAL)/i;
const strip = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const withFile = records.filter(r => r.photoFile);
for (let i = 0; i < withFile.length; i += 50) {
  const batch = withFile.slice(i, i + 50);
  const u = 'https://commons.wikimedia.org/w/api.php?' + new URLSearchParams({
    action: 'query', titles: batch.map(r => r.photoFile).join('|'), prop: 'imageinfo',
    iiprop: 'url|extmetadata', iiurlwidth: '1280', format: 'json',
  });
  const j = await (await fetch(u, { headers: UA })).json();
  const norm = new Map((j.query?.normalized || []).map(n => [n.from, n.to]));
  const pages = new Map(Object.values(j.query?.pages || {}).map(p => [p.title, p]));
  for (const r of batch) {
    const ii = pages.get(norm.get(r.photoFile) || r.photoFile)?.imageinfo?.[0];
    const m = ii?.extmetadata || {};
    const license = strip(m.LicenseShortName?.value);
    if (ii && FREE.test(license) && !/NC|ND/.test(license)) {
      r.photos = [{ src: ii.thumburl || ii.url, page: ii.descriptionurl, license, artist: strip(m.Artist?.value).slice(0, 80) || 'Unknown', title: r.photoFile.replace(/^File:/, '') }];
    }
  }
  await sleep(500);
}
for (const r of records) {
  delete r.photoFile;
  r.tier = r.photos || r.wikidata || r.url?.includes('wikipedia') ? 1 : 2;
}
fs.writeFileSync(out, JSON.stringify(records));
console.log(`\nwrote ${records.length} artworks (${records.filter(r => r.tier === 1).length} highlights, ${records.filter(r => r.photos).length} with photos) to ${out}`);
