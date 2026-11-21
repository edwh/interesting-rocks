// Small 12x12 glyphs drawn inside map pins and layer chips. Each layer names one in layers.json.
const P = {
  fold: '<path d="M2 11V6.5a4 4 0 0 1 8 0V11" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M1 11h10" stroke="currentColor" stroke-width="1.6"/>',
  figure: '<circle cx="6" cy="2.4" r="1.6" fill="currentColor"/><path d="M6 4.6v4M3 6h6M6 8.6l-2 2.8M6 8.6l2 2.8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" fill="none"/>',
  spiral: '<path d="M6 6.2a.9.9 0 1 1 .9-.9 2 2 0 0 1-2 2 2.9 2.9 0 0 1-2.9-2.9A3.9 3.9 0 0 1 6 1.5a4.6 4.6 0 0 1 4.6 4.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>',
  book: '<path d="M6 3.2C4.8 2.3 3 2 1.2 2.2v7.4C3 9.4 4.8 9.7 6 10.6c1.2-.9 3-1.2 4.8-1V2.2C9 2 7.2 2.3 6 3.2zM6 3.2v7.4" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/>',
  tree: '<path d="M6 1.2 2.4 6.4h2.1L2.6 9h6.8L7.5 6.4h2.1z" fill="currentColor"/><path d="M6 9v2.4" stroke="currentColor" stroke-width="1.5"/>',
  well: '<path d="M6 1.4C4.4 4 3 5.6 3 7.4a3 3 0 0 0 6 0C9 5.6 7.6 4 6 1.4z" fill="currentColor"/>',
  stones: '<path d="M2.4 11V4.5M6 11V2.2M9.6 11V5.4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
  cave: '<path d="M1 11c0-5 2.2-8.5 5-8.5S11 6 11 11zM4.3 11c0-2.4.8-4 1.7-4s1.7 1.6 1.7 4" fill="currentColor" fill-rule="evenodd"/>',
  tower: '<path d="M3.5 11V4.2h5V11M3 4.2V2h1.4v1h1.1V2h1.1v1h1.1V2H9v2.2" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M5.2 11V8.4h1.6V11" fill="currentColor"/>',
  horse: '<path d="M1.5 9.5c1.5-3 3.5-4.2 6-4.2l1.8-2.5.8 1.6-1 1.2c.6.9.6 2 .2 3M3 9.4v2M8.6 8.6v2.6" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>',
  star: '<path d="M6 1.3l1.4 3 3.3.4-2.4 2.3.6 3.3L6 8.7 3.1 10.3l.6-3.3L1.3 4.7l3.3-.4z" fill="currentColor"/>',
  cross: '<path d="M6 1.5v9M3.2 4.3h5.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
  leaf: '<path d="M2 10.5C2 5 5.5 1.5 10.5 1.5 10.5 6.5 7 10 2 10.5z" fill="currentColor"/><path d="M2 10.5 7.5 5" stroke="var(--c, #000)" stroke-width="1" fill="none"/>',
  columns: '<path d="M1.2 4.2 6 1.4l4.8 2.8zM1.5 10.6h9M2.6 5.2v4.6M5 5.2v4.6M7 5.2v4.6M9.4 5.2v4.6" fill="currentColor" stroke="currentColor" stroke-width="1.2"/>',
  plaque: '<circle cx="6" cy="6" r="5" fill="currentColor"/><circle cx="6" cy="6" r="3.5" fill="none" stroke="var(--c, #000)" stroke-width=".9"/>',
  sign: '<rect x="1.2" y="2.4" width="9.6" height="7.2" rx=".6" fill="none" stroke="currentColor" stroke-width="1.3"/><path d="M3 4.8h6M3 7.2h4" stroke="currentColor" stroke-width="1.2"/>',
  milestone: '<path d="M3 11V4.5a3 3 0 0 1 6 0V11z" fill="currentColor"/><path d="M4.6 6.2h2.8M4.6 8h2.8" stroke="var(--c, #000)" stroke-width="1"/>',
  rock: '<path d="M1.5 10.5 3.6 5l2.2 1.8L8 3l2.5 7.5z" fill="currentColor"/>',
  frame: '<rect x="1.4" y="1.8" width="9.2" height="8.4" rx=".5" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M3 8.6l2.2-2.8 1.6 1.7 1.2-1.1L9 8.6z" fill="currentColor"/><circle cx="8" cy="4.4" r=".9" fill="currentColor"/>',
  poppy: '<circle cx="6" cy="3.5" r="2.3" fill="currentColor"/><circle cx="3.4" cy="6.3" r="2.3" fill="currentColor"/><circle cx="8.6" cy="6.3" r="2.3" fill="currentColor"/><circle cx="6" cy="8.7" r="2.1" fill="currentColor"/><circle cx="6" cy="6.1" r="1.2" fill="var(--c, #000)"/>',
  ghost: '<path d="M2.4 11.2V5.6a3.6 3.6 0 0 1 7.2 0v5.6l-1.2-1-1.2 1-1.2-1-1.2 1-1.2-1z" fill="currentColor"/><circle cx="4.7" cy="5.4" r=".95" fill="var(--c, #000)"/><circle cx="7.3" cy="5.4" r=".95" fill="var(--c, #000)"/>',
  cairn: '<path d="M6 1c2.5 0 4 3.1 4 5.8C10 9.4 8.3 11 6 11S2 9.4 2 6.8C2 4.1 3.5 1 6 1z" fill="currentColor"/><path d="M2.6 5.2h6.8M2.3 7.9h7.4M5 2.6l1 2.6M7 5.2l-.8 2.7M5.2 7.9l.6 3" stroke="var(--c, #000)" stroke-width=".8" fill="none"/>',
  fingerpost: '<path d="M6 11.2V1.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M6.4 2.2h3.4l1.4 1.4-1.4 1.4H6.4zM5.6 5.8H2.2L.8 7.2l1.4 1.4h3.4z" fill="currentColor"/>',
};

export function icon(name, size = 12) {
  return `<svg viewBox="0 0 12 12" width="${size}" height="${size}" aria-hidden="true">${P[name] || P.star}</svg>`;
}
