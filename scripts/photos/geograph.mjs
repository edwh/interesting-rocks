// Geograph asks reusers not to hotlink its images (hotlinked images get watermarked and may be blocked)
// and to host their own copy instead. For every Geograph photo in the layer sources this script:
//   1. looks for a copy on Wikimedia Commons (many Geograph photos are mirrored there, same CC BY-SA licence),
//      recording the answer in scripts/layers/geograph-mirrors.json so it is asked only once;
//   2. otherwise downloads Geograph's standard-size image once, politely, into data/photos/geograph/<id>.jpg.
// build-layers.mjs then uses the Commons copy or the local file, and drops any Geograph photo it has neither for.
// Usage: node scripts/photos/geograph.mjs
import fs from 'fs';
import { execFileSync } from 'child_process';

const UA = { 'User-Agent': 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)' };
const MIRRORS = 'scripts/layers/geograph-mirrors.json';
const DIR = 'data/photos/geograph';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const strip = s => (s || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim();
const FREE = /^(CC BY(-SA)? \d\.\d( [a-z]{2})?|CC0( 1\.0)?|Public domain)$/i;

const mirrors = fs.existsSync(MIRRORS) ? JSON.parse(fs.readFileSync(MIRRORS, 'utf8')) : {};
const files = ['data/sites.json', ...fs.readdirSync('scripts/work/layers').map(f => 'scripts/work/layers/' + f)];
const photos = new Map(); // geograph id -> photo
for (const f of files) {
  for (const r of JSON.parse(fs.readFileSync(f, 'utf8'))) {
    for (const p of r.photos || []) {
      const id = /geograph\.org\.uk\/photo\/(\d+)/.exec(p.page || '')?.[1];
      if (id && /geograph\.org\.uk/.test(new URL(p.src).hostname)) photos.set(id, p);
    }
  }
}
console.log(`${photos.size} Geograph photos hotlinked in the sources`);

let found = 0, downloaded = 0, n = 0;
for (const [id, p] of photos) {
  n++;
  if (!(id in mirrors)) {
    const u = 'https://commons.wikimedia.org/w/api.php?' + new URLSearchParams({
      action: 'query', format: 'json', generator: 'search', gsrnamespace: '6', gsrlimit: '3',
      gsrsearch: `intitle:"geograph.org.uk - ${id}"`, prop: 'imageinfo', iiprop: 'url|extmetadata', iiurlwidth: '1280',
    });
    try {
      const j = await (await fetch(u, { headers: UA })).json();
      const page = Object.values(j.query?.pages || {}).find(pg => pg.title.endsWith(`geograph.org.uk - ${id}.jpg`));
      const ii = page?.imageinfo?.[0], m = ii?.extmetadata || {};
      const license = strip(m.LicenseShortName?.value);
      mirrors[id] = ii && FREE.test(license)
        ? { src: ii.thumburl || ii.url, page: ii.descriptionurl, license, artist: strip(m.Artist?.value).slice(0, 80) || p.artist, title: page.title.replace(/^File:/, '') }
        : null;
    } catch { /* leave unknown; try again next run */ }
    if (n % 20 === 0) fs.writeFileSync(MIRRORS, JSON.stringify(mirrors, null, 1));
    await sleep(400);
  }
  if (mirrors[id]) { found++; continue; }
  const local = `${DIR}/${id}.jpg`;
  if (fs.existsSync(local)) continue;
  if (mirrors[id] === undefined) continue; // the Commons check failed; don't download until it has an answer
  const r = await fetch(p.src, { headers: UA });
  if (r.ok && /image\/jpeg/.test(r.headers.get('content-type') || '')) {
    const tmp = local + '.tmp';
    fs.writeFileSync(tmp, Buffer.from(await r.arrayBuffer()));
    execFileSync('convert', [tmp, '-strip', '-resize', '640x640>', '-quality', '82', local]);
    fs.unlinkSync(tmp);
    downloaded++;
  } else {
    console.log(`  could not fetch Geograph ${id} (${r.status})`);
  }
  await sleep(1200);
  if (n % 25 === 0) process.stdout.write(`\r${n}/${photos.size}: ${found} on Commons, ${downloaded} downloaded   `);
}
fs.writeFileSync(MIRRORS, JSON.stringify(mirrors, null, 1));
console.log(`\ndone: ${found} use a Commons copy, ${downloaded} newly downloaded, ${fs.readdirSync(DIR).length} hosted here`);
