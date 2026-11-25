const fs = require('fs');

const nas = fs.readFileSync('tests/polaris_w4/nasmesta_djvu.txt', 'utf8').split('\n');

const govRanges = [
  { key: 'Volhynia', oblHints: ['19', '24', '27', '09'], name: 'Волынская губерния', start: 20645, end: 27531 },
  { key: 'Kiev', oblHints: ['12', '13', '01', '27', '23'], name: 'Киевская губерния', start: 64340, end: 73804 },
  { key: 'Podolia', oblHints: ['23', '09', '17'], name: 'Подольская губерния', start: 134717, end: 142558 },
  { key: 'Poltava', oblHints: ['18', '01', '21', '13'], name: 'Полтавская губерния', start: 142558, end: 151592 },
  { key: 'Kherson', oblHints: ['08', '16', '17', '10', '04'], name: 'Херсонская губерния', start: 210662, end: 215456 },
  { key: 'Chernigov', oblHints: ['02', '21', '13'], name: 'Черниговская губерния', start: 215456, end: 226940 }
];

function cleanNum(s) {
  const c = (s || '').replace(/[.,\s]/g, '');
  return /^\d+$/.test(c) ? parseInt(c, 10) : NaN;
}

const records = [];
for (const g of govRanges) {
  // Concatenate text cleaning out column/page headers
  const cleanedLines = [];
  for (const raw of nas.slice(g.start, g.end)) {
    let l = raw.trim();
    if (!l) continue;
    if (/^[МM]\.?\s*Ж\.?\s*ОБ/i.test(l)) continue;
    if (/^—\s*\d+\s*—$/.test(l) || /^\d{1,3}$/.test(l)) continue;
    if (/^(VIII|XVI|XXXII|XXXIII|XLVII|XLVIII|ХЬіѴІІ|ХІЛ‘111)[\.\s].*губер/i.test(l)) continue;
    if (/^Сокращенія названій/i.test(l)) continue;
    // Remove inline header artifacts
    l = l.replace(/М\.\s*Ж\.\s*ОБ\.\s*П\.?/g, ' ').replace(/\s+/g, ' ').trim();
    if (l) cleanedLines.push(l);
  }

  // Split whenever a line starts with a Cyrillic Capital + lowercase letters + comma, OR split mid-line after a total number followed by Capital Cyrillic + comma
  const joined = [];
  for (const l of cleanedLines) {
    if (/^[А-ЯЁІѢѲ][а-яёіѣѳ\-’'`()]+(?:\s+[А-Яа-яЁёІіѢѣѲѳ\-’'`()]+){0,3}\s*,/.test(l) || joined.length === 0) {
      joined.push(l);
    } else {
      joined[joined.length - 1] += ' ' + l;
    }
  }

  // Split any record that still has two entries glued on one line
  const splitRecs = [];
  for (const r of joined) {
    // Split after 3 numbers where next token is Cyrillic Capital + word + comma
    const parts = r.split(/(?<=\d)\s+(?=[А-ЯЁІѢѲ][а-яёіѣѳ\-]+(?:\s+[А-Яа-яЁёІіѢѣѲѳ\-()]+){0,3}\s*,\s*(?:с\.|д\.|мст\.|г\.|г-|х\.|хутор|сл\.|клн\.|пос\.|флв\.|усадьб|им\.|ст\.|выс\.))/);
    for (const p of parts) splitRecs.push(p.trim());
  }

  let govOk = 0;
  for (const rec of splitRecs) {
    const cm = rec.indexOf(',');
    if (cm < 2) continue;
    const rawName = rec.slice(0, cm).trim();
    if (rawName.length < 2 || rawName.length > 60) continue;
    if (/губерн|уѣзд|Сокращен/i.test(rawName)) continue;

    // Extract last 3 numeric tokens (dots/commas as thousand separators)
    const m = rec.match(/(\d+(?:[.,]\d{3})*)\s+(\d+(?:[.,]\d{3})*)\s+(\d+(?:[.,]\d{3})*)\s*$/);
    if (!m) continue;
    const male = cleanNum(m[1]), fem = cleanNum(m[2]), tot = cleanNum(m[3]);
    if (male > 0 && fem > 0 && tot >= 400 && male + fem === tot) {
      const rest = rec.slice(cm + 1, rec.length - m[0].length).trim();
      const uyezdM = rest.match(/(?:с\.|д\.|мст\.|г\.|х\.|сл\.|клн\.|пос\.|флв\.|ст\.|выс\.|им\.|у\.|и\s+[а-я]+\.)\s*([А-ЯЁІѢѲ][А-Яа-яЁёІіѢѣѲѳ.\-]{1,12})/);
      records.push({
        name: rawName,
        governorate: g.key,
        oblHints: g.oblHints,
        uyezd_abbr: uyezdM ? uyezdM[1] : '',
        year: 1897,
        population: tot,
        male,
        female: fem
      });
      govOk++;
    }
  }
  console.log(g.key, 'verified 1897 entries:', govOk);
}

fs.writeFileSync('tests/polaris_w4/parsed_1897_nasmesta.json', JSON.stringify(records, null, 2));
console.log('Total 1897 Troynitsky checksum-verified records:', records.length);
