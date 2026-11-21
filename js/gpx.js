// GPX export: one named waypoint per place, with the place, notes and a link back to the map.
const xml = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function buildGpx(list, { title, layerName, accessLabel, visitedDate }) {
  const base = location.origin + location.pathname;
  const wpts = list.map(s => {
    const desc = [layerName(s), s.place, s.about, s.note, s.grid && 'Grid ref ' + s.grid, accessLabel(s),
      visitedDate(s) && 'Visited ' + visitedDate(s)].filter(Boolean).join('. ');
    return `  <wpt lat="${s.ll[0]}" lon="${s.ll[1]}">
    <name>${xml(s.name)}</name>
    <desc>${xml(desc)}</desc>
    <link href="${xml(base + '#' + s.id)}"><text>${xml(s.name)}</text></link>
    <type>${xml(s.kind || layerName(s))}</type>
  </wpt>`;
  }).join('\n');
  return `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="${xml(title)}" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>${xml(title)}</name>
    <link href="${xml(base)}"><text>${xml(title)}</text></link>
    <time>${new Date().toISOString()}</time>
  </metadata>
${wpts}
</gpx>
`;
}

export function download(text, filename) {
  const blob = new Blob([text], { type: 'application/gpx+xml' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
