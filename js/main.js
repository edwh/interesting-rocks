// Map of interesting places: loads layers as they are turned on, draws clustered pins,
// and keeps the list in step with the map.
import { visited, wanted, prefs } from './store.js';
import { icon } from './icons.js';
import { buildGpx, download } from './gpx.js';
import { initModal, openPlace, ACCESS, fmtDate } from './modal.js';
import { initFrom, fmtMiles } from './from.js';

const TITLE = 'Interesting Rocks';
const LIST_CAP = 200;

const $ = id => document.getElementById(id);
let layers = [];
const layerByKey = {};
const loaded = new Map(); // file path -> places from that file (or a pending promise)
let places = [];          // every place loaded so far
let query = '';

// Viewer choices, remembered in this browser. Layers marked defaultOn start visible.
const saved = prefs.value;
let shownLayers = null;   // set once the manifest is known
const hiddenAccess = new Set(saved.hiddenAccess || []);
let hideVisited = !!saved.hideVisited;
let highlightsOnly = saved.highlightsOnly !== false;
let wantedOnly = false; // not remembered: it's a view of the wishlist, not a setting
// "Places near": a starting point and a crow-flies distance, or null. A searched point is remembered;
// the viewer's own location is not.
let near = null;
let nearSaved = saved.near || null;

function savePrefs() {
  prefs.value = { ...prefs.value, shownLayers: [...shownLayers], hiddenAccess: [...hiddenAccess], hideVisited, highlightsOnly, near: nearSaved, openFams: [...openFams] };
  prefs.save();
}

// Distance from the starting point, worked out once per place for each starting point.
let nearVersion = 0;
function dist(s) {
  if (s._dv !== nearVersion) { s._d = near.ll.distanceTo(s.ll); s._dv = nearVersion; }
  return s._d;
}

const map = L.map('map', { zoomControl: true }).setView([54.4, -2.8], 6);
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const cluster = L.markerClusterGroup({
  chunkedLoading: true,
  disableClusteringAtZoom: 14,
  maxClusterRadius: 44,
  showCoverageOnHover: false,
  iconCreateFunction: c => {
    const n = c.getChildCount();
    const size = n < 10 ? 30 : n < 100 ? 36 : n < 1000 ? 42 : 48;
    return L.divIcon({ className: '', html: `<span class="cluster" style="width:${size}px;height:${size}px">${n.toLocaleString('en-GB')}</span>`, iconSize: [size, size] });
  },
}).addTo(map);

function pinHtml(s) {
  const layer = layerByKey[s.cat];
  const cls = ['pin', s.access, s.count > 1 ? 'multi' : '', visited.has(s.id) ? 'visited' : '', wanted.has(s.id) ? 'wanted' : ''].join(' ');
  return `<span class="${cls}" style="--c:${layer.color};--k:${layer.ink}">${icon(layer.icon, 11)}</span>`;
}
function pinIcon(s) {
  const size = s.count > 1 ? 24 : 20;
  return L.divIcon({ className: '', html: pinHtml(s), iconSize: [size, size], iconAnchor: [size / 2, size / 2] });
}
function marker(s) {
  if (!s.marker) {
    s.marker = L.marker(s.ll, { icon: pinIcon(s), title: s.name, keyboard: true })
      .bindTooltip(s.name, { direction: 'top', offset: [0, -10] })
      .on('click', () => openPlace(s));
  }
  return s.marker;
}

// Load the files a layer needs: its highlights, plus the rest when "Highlights only" is off.
function filesWanted(layer) {
  return layer.files.filter(f => f.tier === 1 || !highlightsOnly);
}
function loadFile(layer, f) {
  if (!loaded.has(f.file)) {
    loaded.set(f.file, fetch(f.file).then(r => r.json()).then(recs => {
      for (const s of recs) {
        s.cat = layer.key; s.tier = s.tier || f.tier; s.access = s.access || layer.defaultAccess || 'open'; s.photos = s.photos || [];
      }
      const ids = new Set(recs.map(s => s.id));
      for (const stub of places.filter(p => p.stub && ids.has(p.id))) stub.marker && cluster.removeLayer(stub.marker);
      places = places.filter(p => !(p.stub && ids.has(p.id))).concat(recs);
      loaded.set(f.file, recs);
      return recs;
    }).catch(() => { loaded.delete(f.file); return []; }));
  }
  return loaded.get(f.file);
}
async function ensureLoaded() {
  const pending = layers.filter(l => shownLayers.has(l.key)).flatMap(l => filesWanted(l).map(f => [l, f]))
    .filter(([, f]) => !Array.isArray(loaded.get(f.file)));
  if (!pending.length) return;
  $('loading').hidden = false;
  await Promise.all(pending.map(([l, f]) => loadFile(l, f)));
  $('loading').hidden = true;
}

function isShown(s) {
  if (near && dist(s) > near.r) return false;
  if (wantedOnly) return wanted.has(s.id);
  return shownLayers.has(s.cat) && !hiddenAccess.has(s.access) && !(hideVisited && visited.has(s.id))
    && (!highlightsOnly || s.tier === 1);
}

// Wishlist places whose layer isn't loaded are shown from what the wishlist saved.
function addWantedStubs() {
  const have = new Set(places.map(p => p.id));
  for (const [id, w] of Object.entries(wanted.map)) {
    if (have.has(id) || !layerByKey[w.cat]) continue;
    places.push({ id, cat: w.cat, name: w.name, ll: w.ll, access: 'open', tier: 1, photos: [], stub: true });
  }
}
function matches(s) {
  if (!query) return true;
  return [s.name, s.place, s.artist, s.author, s.group, s.kind].some(v => v && v.toLowerCase().includes(query));
}

function refreshMarkers() {
  cluster.clearLayers();
  const want = places.filter(s => isShown(s) && matches(s));
  for (const s of want) marker(s).setIcon(pinIcon(s));
  cluster.addLayers(want.map(s => s.marker));
}

function renderProgress() {
  const reachable = places.filter(s => s.access !== 'gone' && isShown(s));
  const done = reachable.filter(s => visited.has(s.id)).length;
  $('progress').innerHTML = `<span><b>${done}</b> of ${reachable.length.toLocaleString('en-GB')} places shown visited</span>`;
}

const FAMILIES = { art: 'Art in the landscape', old: 'Old Britain', listed: 'Old Britain', nature: 'Nature and underground', people: 'People and streets', museums: 'Museums and galleries' };

async function setAllLayers(on) {
  shownLayers = new Set(on ? layers.map(l => l.key) : []);
  savePrefs();
  renderLayerChips();
  await ensureLoaded();
  refreshAll();
}

// Layers come in folded groups. A group opens when tapped, or by itself when "Find a layer" matches
// something in it. Which groups are open is remembered in this browser, like the layer choices.
const openFams = new Set(saved.openFams || []);
let layerQuery = '';
const CHEV = '<svg class="chev" viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M4 6l4 4 4-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
function layerMatches(layer) {
  if (!layerQuery) return true;
  return [layer.name, layer.description, FAMILIES[layer.family]].some(v => v && v.toLowerCase().includes(layerQuery));
}

function renderLayerChips() {
  const f = $('layers');
  f.textContent = '';
  $('layersum').textContent = `${shownLayers.size} of ${layers.length} on`;
  $('all-on').disabled = layers.every(l => shownLayers.has(l.key));
  $('all-off').disabled = !shownLayers.size;
  const groups = new Map();
  for (const layer of layers) {
    const fam = FAMILIES[layer.family] || 'More';
    if (!groups.has(fam)) groups.set(fam, []);
    groups.get(fam).push(layer);
  }
  let any = false;
  for (const [fam, inFam] of groups) {
    const show = inFam.filter(layerMatches);
    if (!show.length) continue;
    any = true;
    const d = document.createElement('details');
    d.className = 'famgroup';
    d.open = layerQuery ? true : openFams.has(fam);
    const n = inFam.filter(l => shownLayers.has(l.key)).length;
    const pins = inFam.map(l => `<span class="pin mini${shownLayers.has(l.key) ? '' : ' off'}" style="--c:${l.color};--k:${l.ink}">${icon(l.icon, 9)}</span>`).join('');
    d.innerHTML = `<summary><span class="famname"></span><span class="fampins" aria-hidden="true">${pins}</span><span class="lsum">${n} of ${inFam.length} on</span>${CHEV}</summary><div class="famrow"></div>`;
    d.querySelector('.famname').textContent = fam;
    d.addEventListener('toggle', () => {
      if (layerQuery || d.open === openFams.has(fam)) return;
      if (d.open) openFams.add(fam); else openFams.delete(fam);
      savePrefs();
    });
    const row = d.querySelector('.famrow');
    f.append(d);
    for (const layer of show) addLayerChip(layer, row);
  }
  if (!any) {
    const p = document.createElement('p');
    p.className = 'empty tight';
    p.textContent = 'No layer matches. Try another word.';
    f.append(p);
  }
}

function addLayerChip(layer, row) {
  const on = shownLayers.has(layer.key);
  const total = filesWanted(layer).reduce((n, x) => n + x.count, 0);
  const done = places.filter(s => s.cat === layer.key && visited.has(s.id)).length;
  const b = document.createElement('button');
  b.className = 'chip layer';
  b.setAttribute('aria-pressed', String(on));
  b.title = layer.description;
  b.innerHTML = `<span class="pin mini" style="--c:${layer.color};--k:${layer.ink}">${icon(layer.icon, 9)}</span><span class="ln"></span><span class="lc"></span>`;
  b.querySelector('.ln').textContent = layer.name;
  b.querySelector('.lc').textContent = done ? `${done}/${total.toLocaleString('en-GB')}` : total.toLocaleString('en-GB');
  b.onclick = async () => {
    if (on) shownLayers.delete(layer.key); else shownLayers.add(layer.key);
    savePrefs();
    renderLayerChips();
    await ensureLoaded();
    refreshAll();
  };
  row.append(b);
}

// Filters live behind the Filters button, as on/off toggles in two labelled groups. The button shows
// how many are narrowing the map.
function renderFilterChips() {
  const f = $('filters');
  f.textContent = '';
  const active = (highlightsOnly ? 1 : 0) + (hideVisited ? 1 : 0) + (wantedOnly ? 1 : 0) + hiddenAccess.size;
  $('filtercount').textContent = active ? String(active) : '';
  let row;
  const group = label => {
    const g = document.createElement('div');
    g.className = 'fgroup';
    g.innerHTML = '<span class="flabel"></span><div class="frow"></div>';
    g.querySelector('.flabel').textContent = label;
    row = g.querySelector('.frow');
    f.append(g);
  };
  const chip = (html, pressed, onclick, title) => {
    const b = document.createElement('button');
    b.className = 'toggle';
    b.setAttribute('aria-pressed', String(pressed));
    b.innerHTML = html;
    if (title) b.title = title;
    b.onclick = onclick;
    row.append(b);
  };
  group('Show');
  chip('Highlights only', highlightsOnly, async () => {
    highlightsOnly = !highlightsOnly; savePrefs(); renderFilterChips(); renderLayerChips();
    await ensureLoaded(); refreshAll();
  }, 'Highlights are places with a photo, a top listing grade or a place in a curated layer');
  chip('Hide visited', hideVisited, () => {
    hideVisited = !hideVisited; savePrefs(); renderFilterChips(); refreshAll();
  });
  const n = Object.keys(wanted.map).length;
  chip(`Want to visit only${n ? ` <span class="lc">${n}</span>` : ''}`, wantedOnly, () => {
    wantedOnly = !wantedOnly; addWantedStubs(); renderFilterChips(); refreshAll();
    if (wantedOnly && n) map.fitBounds(L.latLngBounds(Object.values(wanted.map).map(w => w.ll)), { padding: [40, 40], maxZoom: 12 });
  }, 'Show only the places on your list, wherever they are. Download GPX then saves your list.');
  group('Access');
  for (const k of Object.keys(ACCESS)) {
    chip(`<span class="pin mini ${k}" style="--c:var(--muted);--k:var(--panel)"></span>${{ open: 'Open', limited: 'Ticketed or by arrangement', gone: 'Lost or unconfirmed' }[k]}`,
      !hiddenAccess.has(k), () => {
        if (hiddenAccess.has(k)) hiddenAccess.delete(k); else hiddenAccess.add(k);
        savePrefs(); renderFilterChips(); refreshAll();
      });
  }
}

// The list follows the map: places in view, every match when searching, or everything within the
// distance of a starting point. Grouped by layer, except near a starting point, where it is nearest first.
function listed() {
  const shown = places.filter(s => isShown(s) && matches(s));
  const within = near ? ` within ${Math.round(near.r / 1609.344)} mi` : '';
  if (wantedOnly) return { items: shown, label: `${shown.length} on your list${within}` };
  if (query) return { items: shown, label: `${shown.length.toLocaleString('en-GB')} match${shown.length === 1 ? '' : 'es'}${within}` };
  if (near) return { items: shown, label: `${shown.length.toLocaleString('en-GB')}${within} of ${near.name}` };
  const b = map.getBounds();
  const inView = shown.filter(s => b.contains(s.ll));
  return { items: inView, label: `${inView.length.toLocaleString('en-GB')} in view` };
}

function itemButton(s) {
  const layer = layerByKey[s.cat];
  const b = document.createElement('button');
  b.className = 'item' + (visited.has(s.id) ? ' is-visited' : '');
  b.innerHTML = `<span class="pin mini ${s.access}" style="--c:${layer.color};--k:${layer.ink}">${icon(layer.icon, 9)}</span><span><span class="nm"></span><span class="pl"></span></span><span class="tag"></span>`;
  b.querySelector('.nm').textContent = s.name;
  b.querySelector('.pl').textContent = [s.artist || s.author, s.place || s.kind || layer.kinds?.[s.grade]].filter(Boolean).join(' · ');
  b.querySelector('.tag').textContent = visited.has(s.id) ? '✓ ' + fmtDate(visited.date(s.id)) : wanted.has(s.id) ? '★' : near ? fmtMiles(dist(s)) : (s.count > 1 ? '×' + s.count : '');
  b.onclick = () => { openPlace(s); zoomTo(s, Math.max(map.getZoom(), 14)); closeSheet(); };
  return b;
}

function renderList() {
  const list = $('list');
  list.textContent = '';
  const { items, label } = listed();
  $('count').textContent = label;
  $('gpx').disabled = !items.length;
  if (!items.length) {
    const p = document.createElement('p');
    p.className = 'empty';
    p.textContent = wantedOnly ? (near ? 'Nothing on your list within this distance.' : 'Your list is empty. Open a place and tap "Want to visit" to add it.')
      : near ? 'Nothing within this distance. Move the slider further, or turn on more layers.'
      : query ? 'No places match. Try another word, or turn on more layers.' : 'No places in view. Zoom out, move the map or turn on more layers.';
    list.append(p);
    return;
  }
  if (near) {
    const sec = document.createElement('section');
    sec.className = 'region';
    const h = document.createElement('h3');
    h.textContent = 'Nearest first';
    sec.append(h);
    for (const s of items.sort((a, b) => dist(a) - dist(b)).slice(0, LIST_CAP)) sec.append(itemButton(s));
    list.append(sec);
    if (items.length > LIST_CAP) {
      const p = document.createElement('p');
      p.className = 'empty';
      p.textContent = `Showing the nearest ${LIST_CAP} of ${items.length.toLocaleString('en-GB')}. Shorten the distance to narrow the list.`;
      list.append(p);
    }
    return;
  }
  const c = map.getCenter();
  const order = query ? (a, b) => a.name.localeCompare(b.name) : (a, b) => c.distanceTo(a.ll) - c.distanceTo(b.ll);
  let rest = LIST_CAP;
  for (const layer of layers) {
    if (rest <= 0) break;
    const inLayer = items.filter(s => s.cat === layer.key);
    if (!inLayer.length) continue;
    const sec = document.createElement('section');
    sec.className = 'region';
    const h = document.createElement('h3');
    h.textContent = `${layer.name} · ${inLayer.length.toLocaleString('en-GB')}`;
    sec.append(h);
    for (const s of inLayer.sort(order).slice(0, rest)) { sec.append(itemButton(s)); rest--; }
    list.append(sec);
  }
  if (items.length > LIST_CAP) {
    const p = document.createElement('p');
    p.className = 'empty';
    p.textContent = `Showing the nearest ${LIST_CAP} of ${items.length.toLocaleString('en-GB')}. Zoom in to narrow the list.`;
    list.append(p);
  }
}

// Each layer that is turned on credits its data source in the footer.
function renderAttribution() {
  $('attrib').textContent = layers.filter(l => shownLayers.has(l.key) && l.attribution)
    .map(l => `${l.name}: ${l.attribution}`).join(' ');
}

function refreshAll() { refreshMarkers(); renderList(); renderProgress(); renderLayerChips(); renderAttribution(); }

function zoomTo(s, z = 15) { map.setView(s.ll, z); }

$('gpx').onclick = () => {
  const { items } = listed();
  download(buildGpx(items, {
    title: TITLE,
    layerName: s => layerByKey[s.cat].name,
    accessLabel: s => ACCESS[s.access],
    visitedDate: s => visited.date(s.id),
  }), wantedOnly ? 'want-to-visit.gpx' : 'interesting-rocks.gpx');
};

let searchTimer;
$('q').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    query = e.target.value.trim().toLowerCase();
    refreshMarkers(); renderList();
    // Bring the matches into view: one match is zoomed to, several are fitted.
    const hits = query.length >= 2 ? places.filter(s => isShown(s) && matches(s)) : [];
    if (hits.length === 1) zoomTo(hits[0], Math.max(map.getZoom(), 14));
    else if (hits.length) map.fitBounds(L.latLngBounds(hits.map(s => s.ll)), { padding: [40, 40], maxZoom: 14 });
  }, 300);
});

let ready = false;
const from = initFrom({
  map,
  saved: nearSaved,
  layerOf: s => layerByKey[s.cat],
  findPlaces: q => { q = q.toLowerCase(); return places.filter(s => !s.stub && s.name.toLowerCase().includes(q)).sort((a, b) => a.name.length - b.name.length); },
  onChange: n => {
    near = n;
    nearVersion++;
    // Remember a searched starting point and the distance; never the viewer's own location.
    nearSaved = n ? (n.mine ? { step: n.step } : { name: n.name, ll: [n.ll.lat, n.ll.lng], step: n.step }) : (nearSaved && { step: nearSaved.step });
    savePrefs();
    if (ready) refreshAll();
  },
});

map.on('moveend', () => { if (!query && !near) renderList(); });

// Phone list sheet
const sheet = $('side');
const toggle = $('listtoggle');
function closeSheet() { sheet.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); toggle.textContent = 'List'; }
toggle.onclick = () => {
  const open = !sheet.classList.contains('open');
  sheet.classList.toggle('open', open);
  toggle.setAttribute('aria-expanded', String(open));
  toggle.textContent = open ? 'Map' : 'List';
};

addEventListener('storage', e => {
  if (e.key === visited.key) { visited.reload(); refreshAll(); }
  if (e.key === wanted.key) { wanted.reload(); renderFilterChips(); refreshAll(); }
});

initModal({ layer: s => layerByKey[s.cat], onVisitedChange: () => { renderFilterChips(); refreshAll(); }, zoomTo });

$('filterbtn').onclick = () => {
  const open = $('filters').hidden;
  $('filters').hidden = !open;
  $('filterbtn').setAttribute('aria-expanded', String(open));
};
$('all-on').onclick = () => setAllLayers(true);
$('all-off').onclick = () => setAllLayers(false);
$('layerq').addEventListener('input', e => { layerQuery = e.target.value.trim().toLowerCase(); renderLayerChips(); });

async function start() {
  layers = (await (await fetch('data/layers.json')).json()).filter(l => l.files.length);
  for (const l of layers) layerByKey[l.key] = l;
  shownLayers = new Set(saved.shownLayers || layers.filter(l => l.defaultOn).map(l => l.key));
  renderFilterChips();
  renderLayerChips();
  await ensureLoaded();
  addWantedStubs();
  ready = true;
  refreshAll();
  if (!location.hash.slice(1)) from.fit();
  await openById(location.hash.slice(1));
}

// A link to a place opens it, loading its layer (or the rest of the layer) first if needed.
async function openById(id) {
  if (!id) return;
  let s = places.find(x => x.id === id && !x.stub);
  if (!s) {
    for (const l of layers) for (const f of l.files) await loadFile(l, f);
    s = places.find(x => x.id === id);
    if (!s) return;
    shownLayers.add(s.cat);
    if (s.tier > 1) highlightsOnly = false;
    renderFilterChips();
    refreshAll();
  }
  zoomTo(s, 14);
  openPlace(s);
}
addEventListener('hashchange', () => { const id = location.hash.slice(1); if (id && !$('modal').open) openById(id); });

start();
