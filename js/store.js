// Per-browser state: the visited list and the viewer's filter choices.
// Storage can be blocked (private windows), so every access is guarded and state falls back to memory.
const VISITED_KEY = 'goldsworthy-visited-v1'; // kept from the Goldsworthy map so earlier visits carry over
const PREFS_KEY = 'detour-prefs-v1';
const WANTED_KEY = 'detour-wanted-v1';

function read(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; } catch { return fallback; }
}
function write(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* keep in memory only */ }
}

export const visited = {
  map: read(VISITED_KEY, {}),
  has(id) { return !!this.map[id]; },
  date(id) { return this.map[id]; },
  toggle(id) {
    if (this.map[id]) delete this.map[id]; else this.map[id] = new Date().toISOString().slice(0, 10);
    write(VISITED_KEY, this.map);
  },
  reload() { this.map = read(VISITED_KEY, {}); },
  key: VISITED_KEY,
};

// Places the viewer wants to visit. Each entry keeps the name, layer and position, so the wishlist
// can be shown and exported even when that place's layer isn't loaded.
export const wanted = {
  map: read(WANTED_KEY, {}),
  has(id) { return !!this.map[id]; },
  toggle(s) {
    if (this.map[s.id]) delete this.map[s.id];
    else this.map[s.id] = { d: new Date().toISOString().slice(0, 10), cat: s.cat, name: s.name, ll: s.ll };
    write(WANTED_KEY, this.map);
  },
  reload() { this.map = read(WANTED_KEY, {}); },
  key: WANTED_KEY,
};

export const prefs = {
  value: read(PREFS_KEY, { hiddenLayers: [], hiddenAccess: [], hideVisited: false }),
  save() { write(PREFS_KEY, this.value); },
};
