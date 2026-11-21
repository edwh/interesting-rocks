// The place card: photos with credits, facts, and actions (visited, directions, more info).
import { visited, wanted } from './store.js';

const $ = id => document.getElementById(id);
const modal = $('modal');
let current = null;
let photoIndex = 0;
let ctx = null;

export const ACCESS = { open: 'Open to visit', limited: 'Ticketed, seasonal or by arrangement', gone: 'Lost, unfinished or unconfirmed' };

export function fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  return isNaN(d) ? iso : d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

// Compact layers leave out links that follow from the record id, e.g. a listed building's entry number.
function urlFor(layer, s) {
  for (const [prefix, base] of Object.entries(layer.urls || {})) if (s.id.startsWith(prefix)) return base + s.id.slice(prefix.length);
  return '';
}

// Link a photo's licence name to the licence itself.
function licenceUrl(l) {
  const cc = /^CC BY(-SA)? (\d\.\d)(?: ([a-z]{2}))?$/i.exec(l || '');
  if (cc) return `https://creativecommons.org/licenses/by${cc[1] ? '-sa' : ''}/${cc[2]}/${cc[3] ? cc[3].toLowerCase() + '/' : ''}`;
  if (/^CC0/i.test(l)) return 'https://creativecommons.org/publicdomain/zero/1.0/';
  if (/^(Public domain|PD)/i.test(l)) return 'https://creativecommons.org/publicdomain/mark/1.0/';
  return '';
}

// Where a place's facts came from, as links to the source records.
const SOURCES = [
  [/wikidata (Q\d+)/g, m => [`Wikidata ${m[1]}`, `https://www.wikidata.org/wiki/${m[1]}`]],
  [/osm (node|way|relation) (\d+)/g, m => ['OpenStreetMap', `https://www.openstreetmap.org/${m[1]}/${m[2]}`]],
  [/commons (File:[^+;]+?\.(?:jpe?g|png|tiff?|gif))/gi, m => ['Wikimedia Commons', `https://commons.wikimedia.org/wiki/${encodeURIComponent(m[1].trim().replace(/ /g, '_'))}`]],
  [/geograph (\d+)/g, m => ['Geograph', `https://www.geograph.org.uk/photo/${m[1]}`]],
  [/openplaques (\d+)/g, m => ['Open Plaques', `https://openplaques.org/plaques/${m[1]}`]],
  [/nhle (\d+)/g, m => [`Historic England list entry ${m[1]}`, `https://historicengland.org.uk/listing/the-list/list-entry/${m[1]}`]],
  [/hes (LB\d+)/g, m => [`Historic Environment Scotland ${m[1]}`, `https://portal.historicenvironment.scot/designation/${m[1]}`]],
  [/cadw (\d+)/g, m => [`Cadw record ${m[1]}`, `https://cadwpublic-api.azurewebsites.net/reports/listedbuilding/FullReport?lang=en&id=${m[1]}`]],
  [/gcr ([\d/]+|scotland|wales)/g, m => [/\d/.test(m[1]) ? `Geological Conservation Review site ${m[1].replace(/\//g, ', ')}` : 'Geological Conservation Review', '']],
  [/lpo ([^;]+)/g, m => [`Limestone Pavement Order ${m[1].trim()}`, '']],
];
function sourceRefs(s) {
  // Compact layers drop src because the id carries it.
  let src = s.src || '';
  if (!src) {
    let m;
    if ((m = /^nhle-(\d+)$/.exec(s.id))) src = `nhle ${m[1]}`;
    else if ((m = /^hes-lb(\d+)$/.exec(s.id))) src = `hes LB${m[1]}`;
    else if ((m = /^cadw-(\d+)$/.exec(s.id))) src = `cadw ${m[1]}`;
    else if ((m = /^op-(\d+)$/.exec(s.id))) src = `openplaques ${m[1]}`;
    else if ((m = /^osm-([nwr])(\d+)$/.exec(s.id))) src = `osm ${{ n: 'node', w: 'way', r: 'relation' }[m[1]]} ${m[2]}`;
    else if ((m = /^wd-(q\d+)$/.exec(s.id))) src = `wikidata ${m[1].toUpperCase()}`;
  }
  if (s.wikidata && !src.includes(s.wikidata)) src += `; wikidata ${s.wikidata}`;
  const refs = new Map();
  for (const [re, make] of SOURCES) {
    for (const m of src.matchAll(re)) {
      const [label, href] = make(m);
      const r = refs.get(label);
      if (r) r.n++; else refs.set(label, { label, href, n: 1 });
    }
  }
  if (!refs.size && src) refs.set(src, { label: /^hand$/.test(src) ? 'Placed by hand' : src.replace(/ \(official list\)$/, ''), href: '', n: 1 });
  return [...refs.values()];
}

function showPhoto() {
  const p = current.photos[photoIndex];
  const has = !!p;
  $('m-photo').hidden = !has;
  $('m-credit').hidden = !has;
  modal.classList.toggle('nophoto', !has);
  if (!has) return;
  const img = $('m-img');
  img.src = p.src;
  img.alt = `${current.name}: photo by ${p.artist}`;
  const many = current.photos.length > 1;
  $('m-prev').hidden = $('m-next').hidden = $('m-count').hidden = !many;
  $('m-count').textContent = `${photoIndex + 1} / ${current.photos.length}`;
  const c = $('m-credit');
  const link = (text, href) => {
    if (!href) return document.createTextNode(text);
    const a = document.createElement('a');
    a.href = href; a.target = '_blank'; a.rel = 'noopener'; a.textContent = text;
    return a;
  };
  let geo = false;
  try { geo = new URL(p.page).hostname.endsWith('geograph.org.uk'); } catch { /* not a URL */ }
  c.replaceChildren('Photo: ', link(p.artist, p.page), ', ', link(p.license, licenceUrl(p.license)),
    ', via ', link(geo ? 'Geograph' : 'Wikimedia Commons', p.page));
}

function renderVisitButton() {
  const b = $('m-visit');
  const d = visited.date(current.id);
  b.classList.toggle('done', !!d);
  b.textContent = d ? `✓ Visited ${fmtDate(d)} · Undo` : 'Mark as visited';
  const w = $('m-want');
  w.setAttribute('aria-pressed', String(wanted.has(current.id)));
  w.textContent = wanted.has(current.id) ? '★ On your list' : '☆ Want to visit';
}

export function openPlace(s) {
  current = s;
  photoIndex = 0;
  s.photos = s.photos || [];
  const layer = ctx.layer(s);
  const eyebrow = [layer.name, s.group && s.group !== layer.name && s.group !== s.artist ? s.group : ''].filter(Boolean).join(' · ');
  $('m-group').textContent = eyebrow;
  $('m-group').style.setProperty('--c', layer.color);
  $('m-name').textContent = s.name;
  $('m-place').textContent = s.place || '';
  $('m-about').textContent = s.about || '';
  $('m-about').hidden = !s.about;
  $('m-note').textContent = s.note || '';
  $('m-note').hidden = !s.note;
  const meta = $('m-meta');
  meta.textContent = '';
  const row = (k, v, mono) => {
    if (!v) return;
    const dt = document.createElement('dt'); dt.textContent = k;
    const dd = document.createElement('dd'); dd.textContent = v; if (mono) dd.className = 'mono';
    meta.append(dt, dd);
  };
  row('Artist', s.artist);
  row('Writer', s.author);
  row('Type', (s.kind || layer.kinds?.[s.grade] || '') + (s.count > 1 ? ` (${s.count})` : ''));
  row('Date', s.year);
  row('Access', ACCESS[s.access]);
  row('Grid ref', s.grid, true);
  row('Lat, long', s.ll.join(', ') + (s.approx ? ' (approx.)' : ''), true);
  const refs = sourceRefs(s);
  if (refs.length) {
    const dt = document.createElement('dt'); dt.textContent = 'Source';
    const dd = document.createElement('dd');
    refs.forEach((r, i) => {
      if (i) dd.append(', ');
      const text = r.n > 1 ? `${r.label} (${r.n})` : r.label;
      if (r.href) {
        const a = document.createElement('a');
        a.href = r.href; a.target = '_blank'; a.rel = 'noopener'; a.textContent = text;
        dd.append(a);
      } else dd.append(text);
    });
    meta.append(dt, dd);
  }
  $('m-data').textContent = layer.attribution ? `Data: ${layer.attribution}` : '';
  $('m-data').hidden = !layer.attribution;
  const [lat, lon] = s.ll;
  $('m-dir').href = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
  const url = s.url || urlFor(layer, s);
  $('m-more').hidden = !url;
  if (url) $('m-more').href = url;
  renderVisitButton();
  showPhoto();
  if (!modal.open) { modal.showModal(); modal.focus(); }
  modal.scrollTop = 0;
  if (location.hash !== '#' + s.id) history.replaceState(null, '', '#' + s.id);
}

export function initModal(context) {
  ctx = context;
  $('m-visit').onclick = () => { visited.toggle(current.id); renderVisitButton(); ctx.onVisitedChange(); };
  $('m-want').onclick = () => { wanted.toggle(current); renderVisitButton(); ctx.onVisitedChange(); };
  $('m-zoom').onclick = () => { modal.close(); ctx.zoomTo(current); };
  $('m-close').onclick = () => modal.close();
  $('m-prev').onclick = () => { photoIndex = (photoIndex - 1 + current.photos.length) % current.photos.length; showPhoto(); };
  $('m-next').onclick = () => { photoIndex = (photoIndex + 1) % current.photos.length; showPhoto(); };
  modal.addEventListener('click', e => { if (e.target === modal) modal.close(); });
  modal.addEventListener('close', () => history.replaceState(null, '', location.pathname + location.search));
  modal.addEventListener('keydown', e => {
    if (!current || current.photos.length < 2) return;
    if (e.key === 'ArrowLeft') $('m-prev').click();
    if (e.key === 'ArrowRight') $('m-next').click();
  });
}
