const fs = require('fs');
const { JSDOM } = require('jsdom');

const ucHtml = fs.readFileSync('tests/polaris_w4/ukraine-cities.htm', 'utf8');
const dom = new JSDOM(ucHtml);
const trs = [...dom.window.document.querySelectorAll('table tr')];
const galObls = new Set(['Львівська', 'Івано-Франківська', 'Тернопільська']);
const allObls = new Set(['м. Київ','Вінницька','Волинська','Дніпропетровська','Донецька','Житомирська','Закарпатська','Запорізька','Івано-Франківська','Київська','Кіровоградська','Луганська','Львівська','Миколаївська','Одеська','Полтавська','Рівненська','Сумська','Тернопільська','Харківська','Херсонська','Хмельницька','Черкаська','Чернівецька','Чернігівська','Автономна Республіка Крим','м. Севастополь']);

let curObl = '';
const galCities = [];
for (let i = 1; i < trs.length; i++) {
  const tr = trs[i];
  const ths = tr.querySelectorAll('th');
  let cells;
  if (ths.length > 0) {
    const t0 = ths[0].textContent.trim();
    if (allObls.has(t0)) { curObl = t0; continue; }
    cells = [...ths].map(x => x.textContent.trim());
  } else {
    cells = [...tr.querySelectorAll('td')].map(x => x.textContent.trim());
  }
  if (!galObls.has(curObl) || cells.length < 10) continue;
  const uk = cells[0].replace(/^м\.\s*/, '').trim();
  const refPop = parseInt((cells[4] || cells[8] || cells[10] || '0').replace(/[^\d]/g, ''), 10) || 0;
  if (uk) galCities.push({ obl: curObl, uk, lat: cells[1].replace(/^m\.\s*/, '').trim(), refPop });
}

(async () => {
  const found = {};
  for (let i = 0; i < galCities.length; i += 40) {
    const batch = galCities.slice(i, i + 40);
    const url = 'https://uk.wikipedia.org/w/api.php?action=query&redirects=1&titles=' + encodeURIComponent(batch.map(x => x.uk).join('|')) + '&prop=revisions&rvprop=content&format=json';
    const j = await (await fetch(url, { headers: { 'User-Agent': 'SVEA-POLARIS/1.0' } })).json();
    const redirs = {};
    for (const r of (j.query.redirects || [])) redirs[r.to] = r.from;
    for (const p of Object.values(j.query.pages || {})) {
      const c = p.revisions?.[0]?.['*'] || '';
      if (!c) continue;
      const origTitle = redirs[p.title] || p.title;
      const city = galCities.find(x => x.uk === origTitle || x.uk === p.title);
      const refPop = city ? city.refPop : 0;
      const hits = {};
      for (const yr of ['1880', '1890', '1900', '1910', '1921', '1931']) {
        // Strict structured templates only (no prose hyphens/ranges)
        const pats = [
          new RegExp(`bar:${yr}\\s+from:0\\s+till:(\\d+)`, 'i'),
          new RegExp(`bar:${yr}\\s+at:\\s*([\\d.,]+)(?!\\s*тис)`, 'i'),
          new RegExp(`Рік\\d+\\s*=\\s*${yr}[^|\\n]*\\|\\s*Значення\\d+\\s*=\\s*([\\d\\s\\u00a0.,]+)`, 'i'),
          new RegExp(`!\\s*${yr}\\s*\\n\\s*\\|\\s*([\\d\\s\\u00a0.,]+)`, 'i'),
          new RegExp(`\\|\\s*${yr}\\s*\\|\\|\\s*([\\d\\s\\u00a0.,]+)`, 'i')
        ];
        for (const rx of pats) {
          const m = c.match(rx);
          if (m) {
            const raw = m[1].replace(/[\s\u00a0.,]/g, '');
            if (/^\d+$/.test(raw)) {
              const val = parseInt(raw, 10);
              if (val >= 200 && val <= 500000 && (!refPop || (val >= refPop * 0.15 && val <= refPop * 4.5))) {
                hits[yr] = val;
                break;
              }
            }
          }
        }
      }
      if (Object.keys(hits).length > 0) {
        found[origTitle] = { title: p.title, obl: city?.obl, hits, url: 'https://uk.wikipedia.org/wiki/' + encodeURIComponent(p.title.replace(/ /g, '_')) };
      }
    }
  }
  fs.writeFileSync('tests/polaris_w4/galicia_wiki_strict.json', JSON.stringify(found, null, 2));
  console.log('Strict Galicia wiki structured census records:', Object.keys(found).length);
  console.log('Sample:', Object.entries(found).slice(0, 12));
})();