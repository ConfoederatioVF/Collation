let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

let manifest = JSON5.parse(fs.readFileSync("histmap/1.data_raw/population_regional/CENTAUR/centaur_gazetteers.json5", "utf8"));
let cities = [];
for (let g of manifest.gazetteers) {
  let obj = JSON.parse(fs.readFileSync(g.path, "utf8"));
  for (let k of Object.keys(obj)) {
    let pop = obj[k] && obj[k].population ? obj[k].population : null;
    if (!pop) continue;
    let yrs = [];
    let pmap = {};
    for (let yk of Object.keys(pop)) {
      let yi = Number(yk);
      let pv = Number(pop[yk] || 0);
      if (Number.isFinite(yi) && pv >= 0.01) {
        yrs.push(yi);
        pmap[yi] = pv;
      }
    }
    if (yrs.length > 0) {
      yrs.sort((a, b) => a - b);
      cities.push({ start_yr: yrs[0], end_yr: yrs[yrs.length - 1], pmap: pmap, yrs: yrs });
    }
  }
}

let y0 = Array.isArray(manifest.annual_continuity_span) ? Number(manifest.annual_continuity_span[0]) : 1850;
let y1 = Array.isArray(manifest.annual_continuity_span) ? Number(manifest.annual_continuity_span[1]) : 2025;
let splice_set = new Set(Array.isArray(manifest.border_splice_years) ? manifest.border_splice_years.map(Number) : []);

let annual_counts = {};
for (let yr = y0; yr <= y1; yr++) {
  let act = 0;
  for (let i = 0; i < cities.length; i++) {
    let c = cities[i];
    let in_range = (yr >= c.start_yr && yr <= c.end_yr) || (c.end_yr >= 1975 && yr >= 1975 && yr <= 2026);
    if (!in_range) continue;
    if (c.pmap[yr] !== undefined || yr <= c.start_yr || yr >= c.end_yr) {
      act++;
    } else {
      let lo = 0;
      let hi = c.yrs.length;
      for (let iter = 0; lo < hi && iter < 32; iter++) {
        let mid = (lo + hi) >> 1;
        if (c.yrs[mid] < yr) lo = mid + 1;
        else hi = mid;
      }
      if (lo > 0 && lo < c.yrs.length && (c.yrs[lo] - c.yrs[lo - 1]) <= 200)
        act++;
    }
  }
  annual_counts[yr] = act;
}

let jumps = [];
let max_pct = 0;
let max_yr = null;
for (let yr = y0 + 1; yr <= y1; yr++) {
  let prev_c = annual_counts[yr - 1] || 0;
  let cur_c = annual_counts[yr] || 0;
  if (prev_c < 25) continue;
  let pct = 100.0 * Math.abs(cur_c - prev_c) / prev_c;
  if (!splice_set.has(yr) && !splice_set.has(yr - 1)) {
    if (pct > max_pct) { max_pct = pct; max_yr = yr; }
    if (pct > 3.0) jumps.push(`${yr}: ${prev_c} -> ${cur_c} (${pct.toFixed(2)}%)`);
  }
}
console.log(JSON.stringify({ total_cities: cities.length, span: [y0, y1], max_yoy_pct: Number(max_pct.toFixed(2)), max_yoy_year: max_yr, jumps: jumps, counts_sample: { 1850: annual_counts[1850], 1900: annual_counts[1900], 1950: annual_counts[1950], 1989: annual_counts[1989], 1990: annual_counts[1990], 1999: annual_counts[1999], 2000: annual_counts[2000], 2009: annual_counts[2009], 2010: annual_counts[2010], 2019: annual_counts[2019], 2020: annual_counts[2020], 2025: annual_counts[2025] } }, null, 2));
