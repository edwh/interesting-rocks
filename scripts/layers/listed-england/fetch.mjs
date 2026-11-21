// Fetch England's Grade I and II* listed buildings from Historic England's National Heritage List.
// Source: NHLE feature service, layer 0 "Listed Building points". Licence: Open Government Licence.
// Attribution: Contains Historic England data © Historic England. Contains OS data © Crown copyright.
// Usage: node scripts/layers/listed-england/fetch.mjs [output]   (default scripts/work/layers/listed-england.json)
import fs from 'fs';

const SERVICE = 'https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/0/query';
const WHERE = "Grade IN ('I','II*')";
const FIELDS = 'ListEntry,Name,Grade,ListDate,hyperlink,NGR';
const PAGE = 2000; // the service's maxRecordCount
const UA = { 'User-Agent': 'goldsworthy-map/1.0 (https://github.com/edwh/goldsworthy-map)' };
const out = process.argv[2] || 'scripts/work/layers/listed-england.json';
const fetched = new Date().toISOString().slice(0, 10);

// NHLE names are in capitals. Title-case them, keeping grid references and Roman numerals.
const SMALL = new Set(['a', 'an', 'and', 'but', 'from', 'at', 'by', 'de', 'for', 'in', 'of', 'on', 'or', 'the', 'to', 'with', 'le', 'la']);
function titleCase(s) {
  return s.toLowerCase().replace(/[a-z0-9'’]+/g, (w, i) => {
    if (/^(?=[ivxlc]+$)c{0,3}(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$/.test(w) && w.length <= 5 && w !== 'civil') return w.toUpperCase();
    if (/^(ngr|sd|se|sk|sj|sp|st|su|sx|sy|sz|tq|tl|tf|tg|tr|tm|ta|nz|ny|nx|nu|nt)$/.test(w) && /ngr/i.test(s) && w !== 'st') return w.toUpperCase();
    if (i > 0 && SMALL.has(w)) return w;
    return w.charAt(0).toUpperCase() + w.slice(1);
  }).replace(/\bSt\b(?=\s)/g, 'St').replace(/\bMc([a-z])/g, (m, c) => 'Mc' + c.toUpperCase());
}

async function page(offset) {
  const params = new URLSearchParams({
    where: WHERE, outFields: FIELDS, outSR: '4326', returnGeometry: 'true', orderByFields: 'ListEntry',
    resultOffset: String(offset), resultRecordCount: String(PAGE), f: 'json',
  });
  for (let attempt = 0; attempt < 4; attempt++) {
    const r = await fetch(SERVICE + '?' + params, { headers: UA });
    if (r.ok) { const j = await r.json(); if (!j.error) return j; }
    await new Promise(res => setTimeout(res, 3000 * (attempt + 1)));
  }
  throw new Error(`NHLE page at offset ${offset} failed`);
}

const records = [];
for (let offset = 0; ; offset += PAGE) {
  const j = await page(offset);
  for (const f of j.features) {
    const a = f.attributes;
    const pt = f.geometry?.points?.[0];
    if (!pt) continue;
    records.push({
      id: `nhle-${a.ListEntry}`,
      name: titleCase((a.Name || `List entry ${a.ListEntry}`).replace(/\s*\(SEE DETAILS FOR FURTHER ADDRESS INFORMATION\)/i, '')),
      ll: [+pt[1].toFixed(5), +pt[0].toFixed(5)],
      grade: a.Grade,
      tier: a.Grade === 'I' ? 1 : 2,
      kind: `Listed building, Grade ${a.Grade}`,
      year: a.ListDate ? 'Listed ' + new Date(a.ListDate).getUTCFullYear() : undefined,
      grid: a.NGR || undefined,
      url: a.hyperlink || `https://historicengland.org.uk/listing/the-list/list-entry/${a.ListEntry}`,
      src: `nhle ${a.ListEntry}`,
      fetched,
    });
  }
  process.stdout.write(`\r${records.length} records`);
  if (!j.exceededTransferLimit && j.features.length < PAGE) break;
  await new Promise(res => setTimeout(res, 500));
}
fs.writeFileSync(out, JSON.stringify(records));
console.log(`\nwrote ${records.length} to ${out}`);
