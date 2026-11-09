const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const population_Substrata_russia = require('../histmap/3.data_transform/population_Substrata.russia/population_Substrata_russia.js');

function readFloat32PNG(filePath) {
  const buf = fs.readFileSync(filePath);
  const png = PNG.sync.read(buf);
  const out = new Float32Array(png.width * png.height);
  const dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
  for (let i = 0; i < out.length; i++) {
    const v = dv.getFloat32(i * 4, false);
    out[i] = Number.isFinite(v) ? v : 0;
  }
  return out;
}

const ctx = population_Substrata_russia.A_loadManifestAndMasks();
console.log('specialist_entries keys:', ctx.specialist_entries.map(s => Object.keys(s)));
const masks = {};
for (const se of ctx.specialist_entries) {
  const name = se.id || se.mask_key || se.key || se.name;
  const allPx = [];
  for (const z of se.zones) {
    for (const p of z.pixels) allPx.push(p);
  }
  masks[name] = allPx;
}

function corrOnIndices(a, b, idxs) {
  let n = 0, sa = 0, sb = 0, saa = 0, sbb = 0, sab = 0;
  for (let i = 0; i < idxs.length; i++) {
    const idx = idxs[i];
    const va = a[idx], vb = b[idx];
    if (va === 0 && vb === 0) continue;
    n++;
    sa += va; sb += vb;
    saa += va * va; sbb += vb * vb; sab += va * vb;
  }
  if (n < 2) return 0;
  const cov = sab / n - (sa / n) * (sb / n);
  const vaVar = saa / n - (sa / n) ** 2;
  const vbVar = sbb / n - (sb / n) ** 2;
  if (vaVar <= 0 || vbVar <= 0) return 0;
  return Number((cov / Math.sqrt(vaVar * vbVar)).toFixed(3));
}

function sumOnIndices(a, idxs) {
  let s = 0;
  for (let i = 0; i < idxs.length; i++) s += a[idxs[i]];
  return Math.round(s);
}

const years = [600, 700, 800, 900, 1000, 1100, 1200];
const rPre = {}, rPol = {}, rUrb = {}, rVelk = {}, rIa = {}, rBu = {};
for (const yr of years) {
  rPre[yr] = readFloat32PNG(`histmap/3.data_transform/population_Substrata.outlier_removal/rasters_1.northern_america/popc_${yr}.png`);
  rPol[yr] = readFloat32PNG(`histmap/3.data_transform/population_Substrata.outlier_removal/rasters_2.scaled_to_regions/popc_${yr}.png`);
  rUrb[yr] = readFloat32PNG(`histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters/stadester_urban_${yr}.png`);
  rVelk[yr] = readFloat32PNG(`histmap/2.data_cleaning/population_Velkscala/population_rasters/population_${yr}.png`);
  rIa[yr] = readFloat32PNG(`histmap/1.data_raw/population_regional/russia/1.entire_country/sites_IA_RAS/2.population_rasters/popc_${yr}.png`);
  rBu[yr] = readFloat32PNG(`histmap/1.data_raw/population_regional/russia/kievan_rus/sites_belarus_ukraine/2.population_rasters/popc_${yr}.png`);
}

console.log('=== REGIONAL RASTER CORRELATIONS & URBAN SUMS (600..1200 AD) ===');
for (const [mKey, idxs] of Object.entries(masks)) {
  console.log(`\nRegion: ${mKey} (pixels: ${idxs.length})`);
  for (const yr of years) {
    const cVelkPre = corrOnIndices(rVelk[yr], rPre[yr], idxs);
    const cPolPre = corrOnIndices(rPol[yr], rPre[yr], idxs);
    const cRawPre = corrOnIndices((mKey === 'belarus' || mKey === 'ukraine_mainland') ? rBu[yr] : rIa[yr], rPre[yr], idxs);
    const sPre = sumOnIndices(rPre[yr], idxs);
    const sPol = sumOnIndices(rPol[yr], idxs);
    const sUrb = sumOnIndices(rUrb[yr], idxs);
    const sVelk = sumOnIndices(rVelk[yr], idxs);
    console.log(`  ${yr} AD: sumPre=${sPre}, sumPol=${sPol}, sumUrb=${sUrb}, sumVelk=${sVelk} | corr(raw,Pre)=${cRawPre}, corr(Pol,Pre)=${cPolPre}, corr(Velk,Pre)=${cVelkPre}`);
  }
}
