// "Places near": pick a starting point (a town, postcode, a place on the map, or your location), then a
// slider sets how far to look, as the crow flies. Searches go to postcodes.io (open OS and ONS data);
// your location stays in the browser.
import { icon } from './icons.js';

const API = 'https://api.postcodes.io';
const POSTCODE = /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i;
const OUTCODE = /^[A-Z]{1,2}\d[A-Z\d]?$/i;
export const STEPS = [1, 2, 3, 5, 7, 10, 15, 20, 25, 30, 40, 50, 75, 100]; // miles
const MILE = 1609.344;
const $ = id => document.getElementById(id);

export const fmtMiles = m => {
  const mi = m / MILE;
  return mi < 10 ? `${mi.toFixed(1)} mi` : `${Math.round(mi)} mi`;
};

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) return null;
  return (await r.json()).result;
}

// Towns and villages (OS Open Names), full postcodes and postcode districts.
async function lookup(q) {
  if (POSTCODE.test(q)) {
    const r = await getJson(`${API}/postcodes/${encodeURIComponent(q)}`);
    return r ? [{ name: r.postcode, sub: r.admin_district || '', ll: [r.latitude, r.longitude] }] : [];
  }
  const out = [];
  if (OUTCODE.test(q)) {
    const r = await getJson(`${API}/outcodes/${encodeURIComponent(q)}`);
    if (r && r.latitude) out.push({ name: r.outcode, sub: 'Postcode district' + (r.admin_district?.length ? ', ' + r.admin_district.slice(0, 2).join(', ') : ''), ll: [r.latitude, r.longitude] });
  }
  const rs = (await getJson(`${API}/places?q=${encodeURIComponent(q)}&limit=6`)) || [];
  for (const p of rs) {
    if (p.latitude == null) continue;
    out.push({ name: p.name_1, sub: [p.local_type, p.district_borough || p.county_unitary, p.region].filter(Boolean).join(', '), ll: [p.latitude, p.longitude] });
  }
  return out;
}

export function initFrom({ map, findPlaces, layerOf, saved, onChange }) {
  const input = $('from-q'), sugg = $('from-sugg'), range = $('from-range'), slider = $('from-r');
  slider.max = String(STEPS.length - 1);
  let centre = null;  // { name, ll, mine }
  let step = Number.isInteger(saved?.step) ? saved.step : STEPS.indexOf(10);
  let pin = null, circle = null, options = [], active = -1, seq = 0, timer;

  const accent = () => getComputedStyle(document.documentElement).getPropertyValue('--sand').trim() || '#a5442b';
  const radius = () => STEPS[step] * MILE;

  function emit() {
    onChange(centre ? { name: centre.name, ll: L.latLng(centre.ll), r: radius(), mine: !!centre.mine, step } : null);
  }
  function label() {
    $('from-label').textContent = `Within ${STEPS[step]} mile${STEPS[step] === 1 ? '' : 's'} of ${centre.name}`;
    slider.value = String(step);
    slider.setAttribute('aria-valuetext', `${STEPS[step]} miles`);
  }
  function fit() { map.fitBounds(circle.getBounds(), { padding: [24, 24] }); }

  function setCentre(c, { quiet } = {}) {
    centre = c;
    closeSugg();
    pin?.remove(); circle?.remove();
    pin = L.circleMarker(c.ll, { radius: 7, color: '#fff', weight: 2.5, fillColor: accent(), fillOpacity: 1, interactive: false }).addTo(map);
    circle = L.circle(c.ll, { radius: radius(), color: accent(), weight: 2, fillColor: accent(), fillOpacity: 0.06, interactive: false }).addTo(map);
    input.value = c.mine ? '' : c.name;
    range.hidden = false;
    label();
    if (!quiet) fit();
    emit();
  }
  function clear() {
    centre = null;
    pin?.remove(); circle?.remove(); pin = circle = null;
    range.hidden = true;
    input.value = '';
    emit();
  }

  // Suggestions: matching places already on the map first, then towns and postcodes.
  function closeSugg() { sugg.hidden = true; sugg.textContent = ''; options = []; active = -1; input.setAttribute('aria-expanded', 'false'); }
  function showSugg(list) {
    sugg.textContent = '';
    options = list;
    active = -1;
    if (!list.length) { closeSugg(); return; }
    list.forEach((o, i) => {
      const li = document.createElement('li');
      li.id = 'from-opt-' + i;
      li.setAttribute('role', 'option');
      if (o.layer) {
        const p = document.createElement('span');
        p.className = 'pin mini';
        p.style.cssText = `--c:${o.layer.color};--k:${o.layer.ink}`;
        p.innerHTML = icon(o.layer.icon, 9);
        li.append(p);
      } else {
        const d = document.createElement('span');
        d.className = 'placedot';
        li.append(d);
      }
      const t = document.createElement('span');
      t.innerHTML = '<b></b><small></small>';
      t.querySelector('b').textContent = o.name;
      t.querySelector('small').textContent = o.sub;
      li.append(t);
      li.addEventListener('mousedown', e => { e.preventDefault(); setCentre(o); });
      sugg.append(li);
    });
    sugg.hidden = false;
    input.setAttribute('aria-expanded', 'true');
  }
  function highlight(i) {
    active = i;
    [...sugg.children].forEach((li, j) => li.setAttribute('aria-selected', String(j === i)));
    input.setAttribute('aria-activedescendant', i >= 0 ? 'from-opt-' + i : '');
  }
  async function search(q, pickFirst) {
    const mine = ++seq;
    const local = q.length >= 3 ? findPlaces(q).slice(0, 4).map(s => ({ name: s.name, sub: [layerOf(s).name, s.place].filter(Boolean).join(' · '), ll: s.ll, layer: layerOf(s) })) : [];
    let remote = [];
    try { remote = await lookup(q); } catch { /* offline: local matches only */ }
    if (mine !== seq) return;
    const list = [...remote.slice(0, 6), ...local];
    if (pickFirst && list.length) setCentre(list[0]); else showSugg(list);
    if (pickFirst && !list.length) { $('from-label').textContent = ''; input.setCustomValidity('Nothing found'); input.reportValidity(); }
  }

  input.addEventListener('input', () => {
    input.setCustomValidity('');
    clearTimeout(timer);
    const q = input.value.trim();
    if (q.length < 2) { closeSugg(); return; }
    timer = setTimeout(() => search(q, false), 300);
  });
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown' && options.length) { e.preventDefault(); highlight((active + 1) % options.length); }
    else if (e.key === 'ArrowUp' && options.length) { e.preventDefault(); highlight((active - 1 + options.length) % options.length); }
    else if (e.key === 'Escape') closeSugg();
    else if (e.key === 'Enter') {
      e.preventDefault();
      if (active >= 0) setCentre(options[active]);
      else if (input.value.trim()) { clearTimeout(timer); search(input.value.trim(), true); }
    }
  });
  input.addEventListener('blur', () => setTimeout(closeSugg, 150));

  $('from-me').onclick = () => {
    const b = $('from-me');
    if (!navigator.geolocation) { b.title = 'Location is not available in this browser'; return; }
    b.disabled = true;
    navigator.geolocation.getCurrentPosition(pos => {
      b.disabled = false;
      setCentre({ name: 'your location', ll: [pos.coords.latitude, pos.coords.longitude], mine: true });
    }, () => { b.disabled = false; b.title = 'Location blocked: allow it in your browser settings'; b.classList.add('blocked'); }, { timeout: 10000, maximumAge: 60000 });
  };
  $('from-clear').onclick = clear;

  let refreshTimer;
  slider.addEventListener('input', () => {
    step = +slider.value;
    circle?.setRadius(radius());
    label();
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(emit, 120);
  });
  slider.addEventListener('change', () => { if (circle) fit(); });

  // Bring back a searched starting point from last time (not a location: that would be out of date).
  if (saved?.ll && saved.name && !saved.mine) setCentre({ name: saved.name, ll: saved.ll }, { quiet: true });
  return { fit: () => circle && fit(), active: () => !!centre };
}
