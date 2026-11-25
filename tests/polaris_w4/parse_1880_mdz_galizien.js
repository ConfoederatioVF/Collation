const fs = require('fs');
const path = require('path');
const { JSDOM } = require('jsdom');

const mdzDir = 'tests/polaris_w4/mdz_1880';
const skipDists = /^(Biała|Bochnia|Brzesko|Brzozów|Chrzanów|Dąbrowa|Gorlice|Grybów|Jaroslau|Jasło|Kolbuszów|Krakau|Krosno|Łańcut|Limanowa|Lisko|Mielec|Myślenice|Neumarkt|Neusandez|Sandec|Nisko|Pilzno|Przemyśl(?!any)|Ropczyce|Rzeszów|Sanok|Saybusch|Tarnobrzeg|Tarnów|Wadowice|Wieliczka)$/i;

const files = fs.readdirSync(mdzDir).filter(f => /^p\d+\.html$/.test(f)).sort((a, b) => parseInt(a.slice(1), 10) - parseInt(b.slice(1), 10));

function cleanNum(s) {
  const c = (s || '').replace(/[.,\s]/g, '');
  return /^\d+$/.test(c) ? parseInt(c, 10) : NaN;
}

const records = [];
let prevDistrict = 'Lemberg Stadt';
let inSection = 'Gemeinden';

for (const file of files) {
  const pageNum = parseInt(file.slice(1), 10);
  if (pageNum < 7 || pageNum > 513) continue;
  const html = fs.readFileSync(path.join(mdzDir, file), 'utf8');
  const dom = new JSDOM(html);
  const doc = dom.window.document;
  const lines = [...doc.querySelectorAll('.ocr_line')];
  if (lines.length === 0) continue;

  if (pageNum === 7) {
    records.push({ name: 'Lemberg', alt_name: 'Lwów', district: 'Lemberg Stadt', page: 7, year: 1880, population: 109746, male: 55376, female: 54370 });
    prevDistrict = 'Lemberg Stadt';
    continue;
  }

  // Extract page-top district from running header
  const headerText = lines.slice(0, 4).map(l => l.textContent).join(' ').replace(/\s+/g, ' ');
  let pageDist = '';
  const dm = headerText.match(/Galiz[yi]en\s*\(\s*Gal[ilí]c[yi]a\s*\)\s*[.\-\s]*([^.]{2,45})/i);
  if (dm) {
    pageDist = dm[1]
      .replace(/Bezirke.*|Anwesende.*|Häuser.*|\d+.*/gi, '')
      .replace(/\([^)]*\)/g, '')
      .replace(/[,.\-:]+$/g, '')
      .trim();
  }
  if (!pageDist) pageDist = prevDistrict;
  if (skipDists.test(pageDist)) {
    prevDistrict = pageDist;
    inSection = 'Gemeinden';
    continue;
  }

  // Detect column x-centers
  let xMale = null, xFem = null, xTot = null;
  for (const l of lines.slice(0, 28)) {
    for (const w of l.querySelectorAll('.ocrx_word')) {
      const t = w.textContent.trim().toLowerCase();
      const bm = (w.getAttribute('title') || '').match(/bbox (\d+) (\d+) (\d+) (\d+)/);
      if (!bm) continue;
      const xc = (+bm[1] + +bm[3]) / 2;
      if (t.startsWith('männlich') || t.startsWith('męska')) xMale = xMale || xc;
      if (t.startsWith('weiblich') || t.startsWith('żeńska')) xFem = xFem || xc;
      if (t.startsWith('zusammen') || t.startsWith('razem')) xTot = xTot || xc;
    }
  }

  const allWords = [];
  for (const l of lines) {
    for (const w of l.querySelectorAll('.ocrx_word')) {
      const t = w.textContent.trim();
      const bm = (w.getAttribute('title') || '').match(/bbox (\d+) (\d+) (\d+) (\d+)/);
      if (!t || !bm) continue;
      allWords.push({ t, x0: +bm[1], y0: +bm[2], x1: +bm[3], y1: +bm[4], xc: (+bm[1] + +bm[3]) / 2, yc: (+bm[2] + +bm[4]) / 2 });
    }
  }
  allWords.sort((a, b) => a.yc - b.yc || a.x0 - b.x0);
  const rows = [];
  for (const w of allWords) {
    if (rows.length === 0 || Math.abs(w.yc - rows[rows.length - 1].yc) > 14) {
      rows.push({ yc: w.yc, words: [w] });
    } else {
      rows[rows.length - 1].words.push(w);
    }
  }

  const curBezirkeLimit = xMale ? xMale - 130 : 540;
  const numLimitHi = xTot ? xTot + 120 : 1020;

  // If pageDist changed from prevDistrict, wait until we see Bezirks-Hauptmannschaft or Gemeinden on this page if Summe appears early
  const pageTextAll = rows.map(r => r.words.map(w => w.t).join(' ')).join('\n');
  const hasBhStart = /Bezirks\s*-?\s*Hauptmannschaft|starostwo\s+powiatowe/i.test(pageTextAll);
  if (pageDist !== prevDistrict) {
    inSection = hasBhStart ? 'PreDistrict' : 'Gemeinden';
  }

  for (const row of rows) {
    row.words.sort((a, b) => a.x0 - b.x0);
    const leftText = row.words.filter(w => w.x0 < curBezirkeLimit).map(w => w.t).join(' ').replace(/\s+/g, ' ').trim();
    const fullText = row.words.map(w => w.t).join(' ').replace(/\s+/g, ' ').trim();

    if (row.yc < 210 && /Galiz[yi]en/i.test(fullText)) continue;
    if (/Bezirks\s*-?\s*Hauptmannschaft|starostwo\s+powiatowe|Gerichts\s*-?\s*Bezirk|obw[oó]d\s+s[aą]dowy/i.test(fullText)) {
      inSection = 'Gemeinden';
      continue;
    }
    if (/^(?:Gemeinden|Gerneinden|gminy)\s*[,:]?$/i.test(leftText) || /\b(?:Gemeinden|Gerneinden)\s*,\s*gminy/i.test(leftText)) {
      inSection = 'Gemeinden';
      continue;
    }
    if (/Summe\s+der\s+Gutsgebiete|Razem\s+obsz/i.test(fullText)) {
      inSection = 'Gemeinden';
      continue;
    }
    if (/Gutsgebiete|obszary\s+dworskie/i.test(leftText) && !/Bezirke\s*,\s*Gemeinden|Summe\s+der/i.test(leftText)) {
      inSection = 'Gutsgebiete';
      continue;
    }
    if (/Summe\s+der|Razem\s+(?:gminy|obsz)|^Bezirke\s*,\s*Gemeinden|^Powiaty\s*,\s*gminy|^Häuser|^Anwesende|^männlich|^weiblich|^Confession|^Umgspr|^Gerichts|^obw[oó]d\s+s/i.test(leftText)) {
      continue;
    }
    if (inSection !== 'Gemeinden') continue;

    const nums = [];
    for (const w of row.words) {
      if (w.x0 >= curBezirkeLimit - 20 && w.x0 <= numLimitHi) {
        const n = cleanNum(w.t);
        if (!isNaN(n)) nums.push({ n, xc: w.xc });
      }
    }
    let matched = null;
    if (nums.length >= 3) {
      for (let k = 0; k <= nums.length - 3; k++) {
        const m = nums[k].n, f = nums[k + 1].n, tot = nums[k + 2].n;
        if (m > 0 && f > 0 && tot >= 80 && m + f === tot) {
          if (xTot && Math.abs(nums[k + 2].xc - xTot) > 130) continue;
          matched = { m, f, tot };
          break;
        }
      }
    }
    if (!matched) continue;

    if (!leftText || leftText.length < 2) continue;
    if (/^\(|Summe|Razem|Gutsgebiet|obszar|Bezirke|Gemeinden|Act\.\s*Milit|^[a-zżźćńółęąś]/i.test(leftText) && !/^[A-ZŻŹĆĄĘŁÓŚŃ]/.test(leftText)) continue;

    const firstWordX = row.words[0]?.x0 || 0;
    if (firstWordX > 185 && /\((?:Weiler|wolka|Vorstadt|przedmieście|Colonie|kolonia|Attinenz|przysiółek|Ansiedlung|osada|Dorf|wieś)/i.test(leftText)) continue;

    let name = leftText
      .replace(/\([^)]*(?:Dorf|wieś|Stadt|miasto|Markt|miasteczko|Weiler|wolka|Vorstadt|przedmieście|Colonie|kolonia|mit\s+z\.H\.|mit)[^)]*\)?/gi, '')
      .replace(/[,.\s:;]+$/g, '')
      .trim();
    if (!name || name.length < 2 || /^\d+$/.test(name)) continue;

    records.push({
      name,
      district: pageDist,
      page: pageNum,
      year: 1880,
      population: matched.tot,
      male: matched.m,
      female: matched.f
    });
  }
  prevDistrict = pageDist;
}

fs.writeFileSync('tests/polaris_w4/parsed_1880_galizien.json', JSON.stringify(records, null, 2));
console.log('Clean MDZ 1880 Gemeinden records:', records.length);
for (const d of ['Lemberg Stadt', 'Bóbrka', 'Brody', 'Stanislau', 'Tarnopol', 'Żydaczów']) {
  console.log(' ', d, records.filter(x => x.district.toLowerCase().includes(d.toLowerCase().slice(0, 5))).slice(0, 4));
}
