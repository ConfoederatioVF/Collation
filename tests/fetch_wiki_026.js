const fs = require('fs');
const path = require('path');

const input = JSON.parse(fs.readFileSync('tests/input_026.json', 'utf8'));

// 1. Load all QUIPU _settlements.json and match exact coordinates
const quipuEntries = [];
function walk(d) {
  for (const e of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, e.name);
    if (e.isDirectory()) walk(p);
    else if (e.name.endsWith('_settlements.json')) {
      const data = JSON.parse(fs.readFileSync(p, 'utf8'));
      const arr = Array.isArray(data) ? data : (data.settlements || Object.values(data).filter(v => v && typeof v === 'object' && v.name));
      const rel = path.relative('histmap/1.data_raw/population_regional/QUIPU', p);
      for (const s of arr) {
        if (!s || !s.name) continue;
        const coords = s.coords || [s.lat, s.lng];
        quipuEntries.push({ rel, s, lat: Number(coords[0]), lng: Number(coords[1]) });
      }
    }
  }
}
walk('histmap/1.data_raw/population_regional/QUIPU');

async function wikiLookup(item) {
  const [lat, lng] = item.ll;
  // Query es.wikipedia search + geosearch
  const q1 = encodeURIComponent(`${item.n} ${item.c}`);
  const q2 = encodeURIComponent(item.n);
  const urlSearch = `https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=${q1}&srlimit=3&format=json`;
  const urlGeo = `https://es.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${lat}|${lng}&gsradius=10000&gslimit=5&format=json`;
  const urlSearchPure = `https://es.wikipedia.org/w/api.php?action=query&list=search&srsearch=${q2}&srlimit=3&format=json`;

  let resSearch = [], resGeo = [], resPure = [];
  try {
    const [r1, r2, r3] = await Promise.all([
      fetch(urlSearch).then(r => r.json()).catch(() => ({})),
      fetch(urlGeo).then(r => r.json()).catch(() => ({})),
      fetch(urlSearchPure).then(r => r.json()).catch(() => ({}))
    ]);
    resSearch = (r1.query?.search || []).map(x => x.title);
    resGeo = (r2.query?.geosearch || []).map(x => `${x.title} (${Math.round(x.dist)}m)`);
    resPure = (r3.query?.search || []).map(x => x.title);
  } catch (e) {}

  // Also fetch extract for top search hit or top geo hit
  const titlesToFetch = new Set();
  if (resSearch[0]) titlesToFetch.add(resSearch[0]);
  if (resGeo[0]) titlesToFetch.add(resGeo[0].replace(/ \(\d+m\)$/, ''));
  if (resPure[0]) titlesToFetch.add(resPure[0]);

  let extracts = {};
  if (titlesToFetch.size > 0) {
    const tParam = encodeURIComponent([...titlesToFetch].slice(0, 3).join('|'));
    const urlExt = `https://es.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=1&explaintext=1&exchars=900&titles=${tParam}&format=json&redirects=1`;
    try {
      const rx = await fetch(urlExt).then(r => r.json());
      for (const p of Object.values(rx.query?.pages || {})) {
        if (p.title && p.extract) extracts[p.title] = p.extract.replace(/\n+/g, ' ');
      }
    } catch (e) {}
  }

  return { resSearch, resGeo, resPure, extracts };
}

(async () => {
  const results = [];
  for (let i = 0; i < input.length; i += 10) {
    const batch = input.slice(i, i + 10);
    const wikiBatch = await Promise.all(batch.map(wikiLookup));
    for (let j = 0; j < batch.length; j++) {
      const item = batch[j];
      const [lat, lng] = item.ll;
      const matches = quipuEntries.filter(q => Math.abs(q.lat - lat) < 0.02 && Math.abs(q.lng - lng) < 0.02)
        .map(q => ({
          file: q.rel,
          name: q.s.name,
          region: q.s.region,
          other_names: q.s.other_names,
          years: Object.keys(q.s.population || q.s.years || {}).sort((a,b)=>Number(a)-Number(b)),
          source: q.s.source || q.s.notes || q.s.citations || q.s.provenance
        }));
      results.push({
        key: item.key,
        n: item.n,
        c: item.c,
        r: item.r,
        ll: item.ll,
        ey: item.ey,
        ly: item.ly,
        ex: item.ex,
        al: item.al,
        quipu: matches,
        wiki: wikiBatch[j]
      });
    }
    console.error(`Processed ${Math.min(i + 10, input.length)}/${input.length}`);
  }
  fs.writeFileSync('tests/research_026.json', JSON.stringify(results, null, 2));
  console.log('Done! Saved tests/research_026.json');
})();
