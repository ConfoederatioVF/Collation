import fs from 'fs';

const d = JSON.parse(fs.readFileSync('tests/wikidata_around.json', 'utf8'));
const titles = new Set();
const enTitles = new Set();
const lines = [];

for (const [k, v] of Object.entries(d)) {
  const seen = new Set();
  const uniq = v.filter(x => {
    const id = x.label + '|' + (x.eswiki || '');
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  }).sort((a, b) => a.dist - b.dist);

  const top = uniq.filter(x => x.eswiki || x.enwiki || x.inception || x.dist < 2).slice(0, 5);
  for (const x of top) {
    if (x.eswiki) titles.add(decodeURIComponent(x.eswiki.split('/wiki/')[1]).replace(/_/g, ' '));
    if (x.enwiki) enTitles.add(decodeURIComponent(x.enwiki.split('/wiki/')[1]).replace(/_/g, ' '));
  }
  lines.push(`${k} => ${top.map(x => `${x.label} (${x.dist.toFixed(2)}km${x.inception ? ', inc:' + x.inception.slice(0, 10) : ''}${x.eswiki ? ', es:' + decodeURIComponent(x.eswiki.split('/wiki/')[1]) : ''})`).join(' | ')}`);
}

fs.writeFileSync('tests/wd_summary.txt', lines.join('\n'));
console.log('Summary lines:', lines.length, 'es titles:', titles.size, 'en titles:', enTitles.size);

const UA = 'OperationViscountResearch/1.0 (https://confoederatio.org; research@confoederatio.org)';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function fetchWikiBatch(lang, titleList) {
  const out = {};
  for (let i = 0; i < titleList.length; i += 15) {
    const batch = titleList.slice(i, i + 15);
    const url = `https://${lang}.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&titles=${encodeURIComponent(batch.join('|'))}&redirects=1&format=json`;
    let res = await fetch(url, { headers: { 'User-Agent': UA } });
    if (res.status === 429) {
      console.log('429 on', lang, 'waiting 10s...');
      await sleep(10000);
      res = await fetch(url, { headers: { 'User-Agent': UA } });
    }
    if (!res.ok) {
      console.log('Error', lang, res.status);
      continue;
    }
    const data = await res.json();
    const pages = data.query?.pages || {};
    for (const pid of Object.keys(pages)) {
      if (pid === '-1') continue;
      const p = pages[pid];
      out[p.title] = (p.extract || '').slice(0, 5000);
    }
    await sleep(1500);
  }
  return out;
}

const esPages = await fetchWikiBatch('es', [...titles]);
fs.writeFileSync('tests/es_pages.json', JSON.stringify(esPages, null, 2));
console.log('Fetched esPages:', Object.keys(esPages).length);
