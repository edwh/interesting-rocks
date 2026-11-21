// Proof of life: when was each photo taken? Looks up the "date taken" (DateTimeOriginal) of every
// Wikimedia Commons photo the layers use, including the Commons copies of Geograph photos, and caches
// it in scripts/work/raw/photo-dates.json. The build uses the latest photo date (or a newer OSM survey
// date) as the place's "last seen" date. Upload dates are not used: they say nothing about the place.
// Usage: node scripts/photos/dates.mjs [--refresh]   (only looks up photos not already cached)
import fs from 'fs';

const UA = 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)';
const CACHE = 'scripts/work/raw/photo-dates.json';
const refresh = process.argv.includes('--refresh');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const cache = !refresh && fs.existsSync(CACHE) ? JSON.parse(fs.readFileSync(CACHE, 'utf8')) : {};

const titleOf = page => {
  const m = /commons\.wikimedia\.org\/wiki\/(File:[^?#]+)/.exec(page || '');
  return m ? decodeURIComponent(m[1]).replace(/_/g, ' ') : null;
};
const titles = new Set();
const add = p => { const t = titleOf(p?.page); if (t) titles.add(t); };
for (const f of fs.readdirSync('scripts/work/layers')) {
  if (!f.endsWith('.json')) continue;
  const d = JSON.parse(fs.readFileSync('scripts/work/layers/' + f, 'utf8'));
  if (Array.isArray(d)) for (const r of d) (r.photos || []).forEach(add);
}
for (const s of JSON.parse(fs.readFileSync('data/sites.json', 'utf8'))) (s.photos || []).forEach(add);
if (fs.existsSync('scripts/layers/geograph-mirrors.json')) Object.values(JSON.parse(fs.readFileSync('scripts/layers/geograph-mirrors.json', 'utf8'))).forEach(add);

const MONTHS = { january: 1, february: 2, march: 3, april: 4, may: 5, june: 6, july: 7, august: 8, september: 9, october: 10, november: 11, december: 12 };
const pad = n => String(n).padStart(2, '0');
const thisYear = new Date().getFullYear();
// Commons dates come as ISO dates, EXIF dates, "4 May 2019", HTML <time> elements or just a year.
function parseDate(v) {
  if (!v) return '';
  const s = String(v);
  let m;
  if ((m = /datetime="(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?/.exec(s))) return [m[1], m[2], m[3]].filter(Boolean).join('-');
  const text = s.replace(/<[^>]+>/g, ' ');
  let out = '';
  if ((m = /\b(1[6-9]\d\d|20\d\d)[-:/](\d{1,2})[-:/](\d{1,2})\b/.exec(text))) out = `${m[1]}-${pad(m[2])}-${pad(m[3])}`;
  else if ((m = /\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(1[6-9]\d\d|20\d\d)\b/i.exec(text))) out = `${m[3]}-${pad(MONTHS[m[2].toLowerCase()])}-${pad(m[1])}`;
  else if ((m = /\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(1[6-9]\d\d|20\d\d)\b/i.exec(text))) out = `${m[2]}-${pad(MONTHS[m[1].toLowerCase()])}`;
  else if ((m = /\b(1[6-9]\d\d|20\d\d)\b/.exec(text))) out = m[1];
  return out && +out.slice(0, 4) <= thisYear ? out : '';
}

const todo = [...titles].filter(t => !(t in cache));
console.log(`${titles.size} Commons photos, ${todo.length} to look up`);
for (let i = 0; i < todo.length; i += 50) {
  const batch = todo.slice(i, i + 50);
  let j = null;
  for (let a = 0; a < 4 && !j; a++) {
    try {
      const r = await fetch('https://commons.wikimedia.org/w/api.php', {
        method: 'POST', headers: { 'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ action: 'query', titles: batch.join('|'), prop: 'imageinfo', iiprop: 'extmetadata', iiextmetadatafilter: 'DateTimeOriginal', redirects: '1', format: 'json', formatversion: '2' }),
      });
      if (r.ok) j = await r.json(); else await sleep(5000 * (a + 1));
    } catch { await sleep(5000 * (a + 1)); }
  }
  if (!j) { console.log(`\nbatch at ${i} failed; run again to retry`); continue; }
  const alias = new Map([...(j.query?.normalized || []), ...(j.query?.redirects || [])].map(n => [n.from, n.to]));
  const pages = new Map((j.query?.pages || []).map(p => [p.title, p]));
  for (const t of batch) {
    const p = pages.get(alias.get(alias.get(t) || t) || alias.get(t) || t);
    cache[t] = parseDate(p?.imageinfo?.[0]?.extmetadata?.DateTimeOriginal?.value);
  }
  if (i % 1000 === 0) fs.writeFileSync(CACHE, JSON.stringify(cache));
  process.stdout.write(`\r${Math.min(i + 50, todo.length)}/${todo.length}   `);
  await sleep(300);
}
fs.writeFileSync(CACHE, JSON.stringify(cache));
const dated = [...titles].filter(t => cache[t]).length;
console.log(`\n${dated} of ${titles.size} photos have a date taken`);
