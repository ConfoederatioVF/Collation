let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");

let root_dir = path.resolve(__dirname, "..");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
  }
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

require(path.join(h2, "metadata_HYDE/metadata_HYDE.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "age_sex_HMD/age_sex_HMD.js"));
require(path.join(h3, "age_sex/age_sex.js"));

(async () => {
  let year = 1940;
  console.log(`================================================================================`);
  console.log(`ANALYSIS OF 1940 COMPOSITE AGE/SEX RASTERS`);
  console.log(`================================================================================\n`);

  let cohorts = age_sex.getCohorts();
  let ages = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
  let band_widths = [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5];

  let comp_dir = age_sex.output_rasters;
  let popc_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
  let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });

  let comp_rasters = {};
  for (let c of cohorts) {
    let p = `${comp_dir}${c}_${year}.png`;
    if (!fs.existsSync(p)) {
      console.error(`Missing composite raster: ${p}`);
      return;
    }
    comp_rasters[c] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
  }

  // Check HMD rasters existence
  let hmd_rasters = {};
  let has_hmd = false;
  if (fs.existsSync(age_sex_HMD.output_clamped_to_stadester)) {
    let p0 = `${age_sex_HMD.output_clamped_to_stadester}global_${cohorts[0]}_${year}.png`;
    if (fs.existsSync(p0)) {
      has_hmd = true;
      for (let c of cohorts) {
        hmd_rasters[c] = GeoPNG.loadNumberRasterImage(`${age_sex_HMD.output_clamped_to_stadester}global_${c}_${year}.png`, { format: "float32" });
      }
    }
  }
  console.log(`HMD rasters available for 1940: ${has_hmd}`);

  // Admin countries
  let geocode_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let total_pixels = 4320 * 2160;

  // Selected test countries:
  // HMD countries in 1940: SWE (Sweden), GBR (United Kingdom), FRA (France), USA (United States)
  // Non-HMD countries in 1940: CHN (China), IND (India), BRA (Brazil), DEU (Germany - if HMD or non-HMD), JPN (Japan), NGA (Nigeria)
  let target_countries = ["SWE", "GBR", "FRA", "USA", "DEU", "CHN", "IND", "BRA", "JPN", "NGA", "RUS"];
  let country_pixels = {};
  for (let c of target_countries) country_pixels[c] = [];

  // Map colour to ISO3
  let colour_to_iso3 = {};
  for (let col in geocode_obj) {
    let iso3_list = geocode_obj[col];
    if (iso3_list && iso3_list.length > 0) {
      colour_to_iso3[col] = iso3_list[0];
    }
  }

  for (let i = 0; i < total_pixels; i++) {
    let b = i * 4;
    let col = `${geocode_raster.data[b]},${geocode_raster.data[b+1]},${geocode_raster.data[b+2]}`;
    let iso3 = colour_to_iso3[col];
    if (iso3 && country_pixels[iso3]) {
      country_pixels[iso3].push(i);
    }
  }

  // 1. Global Aggregation
  let global_f = new Float64Array(ages.length);
  let global_m = new Float64Array(ages.length);
  let global_stade_pop = 0;
  let global_comp_pop = 0;
  let cell_pop_err_sum = 0;
  let max_cell_pop_err = 0;

  for (let i = 0; i < total_pixels; i++) {
    let sp = popc_raster.data[i];
    if (sp > 0) global_stade_pop += sp;

    let cell_comp_sum = 0;
    for (let a = 0; a < ages.length; a++) {
      let fv = comp_rasters[`f_${ages[a]}`].data[i];
      let mv = comp_rasters[`m_${ages[a]}`].data[i];
      if (fv > 0) { global_f[a] += fv; cell_comp_sum += fv; }
      if (mv > 0) { global_m[a] += mv; cell_comp_sum += mv; }
    }
    global_comp_pop += cell_comp_sum;

    if (sp > 0.01) {
      let err = Math.abs(sp - cell_comp_sum);
      cell_pop_err_sum += err;
      if (err > max_cell_pop_err) max_cell_pop_err = err;
    }
  }

  console.log(`--- GLOBAL POPULATION IDENTITY CHECK ---`);
  console.log(`Global Stadestér Pop 1940: ${global_stade_pop.toLocaleString()} (${(global_stade_pop / 1e9).toFixed(4)}B)`);
  console.log(`Global Composite Pop 1940: ${global_comp_pop.toLocaleString()} (${(global_comp_pop / 1e9).toFixed(4)}B)`);
  console.log(`Discrepancy: ${(global_comp_pop - global_stade_pop).toFixed(2)} (${(((global_comp_pop - global_stade_pop) / global_stade_pop) * 100).toFixed(6)}%)`);
  console.log(`Max pixel error: ${max_cell_pop_err.toFixed(6)}, Total abs pixel error: ${cell_pop_err_sum.toFixed(2)}\n`);

  console.log(`--- GLOBAL AGE/SEX PYRAMID (1940) ---`);
  console.log(`Age   | Width | Female (M)   | Male (M)     | Total (M)    | Share (%) | Sex Ratio | Ann Dens (M/yr) | Monotonic?`);
  console.log(`-------------------------------------------------------------------------------------------------------------`);

  let prev_dens = Infinity;
  let monotonic_violations = 0;
  for (let a = 0; a < ages.length; a++) {
    let f_m = global_f[a] / 1e6;
    let m_m = global_m[a] / 1e6;
    let tot_m = f_m + m_m;
    let share = (global_f[a] + global_m[a]) / global_comp_pop * 100;
    let sr = m_m / f_m;
    let dens = tot_m / band_widths[a];

    let mono = "OK";
    if (a >= 2) { // from 05 onwards
      if (dens > prev_dens + 1e-4) {
        mono = `BULGE (+${((dens - prev_dens)/prev_dens*100).toFixed(1)}%)`;
        monotonic_violations++;
      }
    }
    prev_dens = dens;

    console.log(`${ages[a].padEnd(5)} | ${String(band_widths[a]).padEnd(5)} | ${f_m.toFixed(2).padStart(12)} | ${m_m.toFixed(2).padStart(12)} | ${tot_m.toFixed(2).padStart(12)} | ${share.toFixed(2).padStart(9)} | ${sr.toFixed(3).padStart(9)} | ${dens.toFixed(2).padStart(15)} | ${mono}`);
  }
  console.log(`Monotonicity violations (from 05+): ${monotonic_violations}\n`);

  // 2. Country-level checks
  console.log(`================================================================================`);
  console.log(`NATIONAL AGE/SEX STRUCTURES & HMD CONSISTENCY`);
  console.log(`================================================================================\n`);

  for (let iso3 of target_countries) {
    let p_idx = country_pixels[iso3];
    if (!p_idx || p_idx.length === 0) continue;

    let country_f = new Float64Array(ages.length);
    let country_m = new Float64Array(ages.length);
    let country_hmd_f = new Float64Array(ages.length);
    let country_hmd_m = new Float64Array(ages.length);
    let country_stade = 0;
    let country_comp = 0;
    let country_hmd_tot = 0;

    for (let idx of p_idx) {
      let sp = popc_raster.data[idx];
      if (sp > 0) country_stade += sp;

      for (let a = 0; a < ages.length; a++) {
        let fv = comp_rasters[`f_${ages[a]}`].data[idx];
        let mv = comp_rasters[`m_${ages[a]}`].data[idx];
        if (fv > 0) { country_f[a] += fv; country_comp += fv; }
        if (mv > 0) { country_m[a] += mv; country_comp += mv; }

        if (has_hmd) {
          let hfv = hmd_rasters[`f_${ages[a]}`].data[idx];
          let hmv = hmd_rasters[`m_${ages[a]}`].data[idx];
          if (hfv > 0) { country_hmd_f[a] += hfv; country_hmd_tot += hfv; }
          if (hmv > 0) { country_hmd_m[a] += hmv; country_hmd_tot += hmv; }
        }
      }
    }

    if (country_comp < 1000) continue;

    let is_hmd_active = (country_hmd_tot > 0.5 * country_stade);
    console.log(`--- ${iso3} (Pop: ${(country_comp / 1e6).toFixed(2)}M, Type: ${is_hmd_active ? "HMD EMPIRICAL" : "MODEL / DASYMETRIC PAVA"}) ---`);
    console.log(`Stadestér Pop: ${(country_stade/1e6).toFixed(2)}M | Composite Pop: ${(country_comp/1e6).toFixed(2)}M | HMD Raster Pop: ${(country_hmd_tot/1e6).toFixed(2)}M`);

    let c_prev_dens = Infinity;
    let c_mono_errs = 0;
    let diff_vs_hmd_sum = 0;

    console.log(`Age   | Female (%) | Male (%)   | Total (%)  | Sex Ratio | Ann Dens (%/yr) | Monotonic? | ${is_hmd_active ? "HMD Match Error" : ""}`);
    console.log(`---------------------------------------------------------------------------------------------------------`);

    for (let a = 0; a < ages.length; a++) {
      let f_pct = country_f[a] / country_comp * 100;
      let m_pct = country_m[a] / country_comp * 100;
      let tot_pct = f_pct + m_pct;
      let sr = (country_f[a] > 0) ? (country_m[a] / country_f[a]) : 0;
      let dens_pct = tot_pct / band_widths[a];

      let mono = "OK";
      if (a >= 2) {
        if (dens_pct > c_prev_dens + 0.05) {
          mono = `BULGE (+${((dens_pct - c_prev_dens)/c_prev_dens*100).toFixed(1)}%)`;
          c_mono_errs++;
        }
      }
      c_prev_dens = dens_pct;

      let hmd_str = "";
      if (is_hmd_active) {
        let hmd_tot_a = country_hmd_f[a] + country_hmd_m[a];
        let diff = Math.abs((country_f[a] + country_m[a]) - hmd_tot_a);
        diff_vs_hmd_sum += diff;
        hmd_str = `Diff: ${diff.toFixed(0)} (${(diff / hmd_tot_a * 100).toFixed(2)}%)`;
      }

      console.log(`${ages[a].padEnd(5)} | ${f_pct.toFixed(2).padStart(10)} | ${m_pct.toFixed(2).padStart(10)} | ${tot_pct.toFixed(2).padStart(10)} | ${sr.toFixed(3).padStart(9)} | ${dens_pct.toFixed(3).padStart(15)} | ${mono.padEnd(15)} | ${hmd_str}`);
    }

    if (is_hmd_active) {
      console.log(`Total Abs Difference vs HMD: ${diff_vs_hmd_sum.toFixed(0)} (${(diff_vs_hmd_sum / country_hmd_tot * 100).toFixed(4)}%)\n`);
    } else {
      console.log(`Monotonicity violations: ${c_mono_errs}\n`);
    }
  }
})();
