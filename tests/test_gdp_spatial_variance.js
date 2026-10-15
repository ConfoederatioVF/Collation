let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
let root_dir = path.resolve(".");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter((f) => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
  }
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");

require(path.join(h2, "metadata_HYDE/metadata_HYDE.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h3, "GDP_PPP/GDP_PPP.js"));
require(path.join(h3, "GDP_PPP_pc/GDP_PPP_pc.js"));
require(path.join(h2, "GDP_nominal/GDP_nominal.js"));
require(path.join(h3, "GDP_pc/GDP_pc.js"));

/**
 * Permanent test battery verifying intra-national spatial variance and sanity
 * of GDP per capita rasters across every ISO3 code.
 *
 * @param {Object} [arg0_options]
 *  @param {number} [arg0_options.year=0] - Year to test (default 0 / 1 AD).
 *  @param {string} [arg0_options.mode="PPP"] - "PPP" or "nominal".
 * @returns {Promise<boolean>}
 */
let testGDPSpatialVariance = async function (arg0_options) {
  //Convert from parameters
  let options = (arg0_options) ? arg0_options : {};
  let mode = (options.mode) ? options.mode : "PPP";
  let year = (options.year !== undefined) ? options.year : 0;
  
  //Declare local instance variables
  let country_means = {};
  let failed_countries = [];
  let geocode_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let gdp_class = (mode === "nominal") ? GDP_nominal : GDP_PPP;
  let gdp_obj = gdp_class.getGDPObject ? gdp_class.getGDPObject() : gdp_class.getGDP_PPPObject();
  let gdp_pc_class = (mode === "nominal") ? GDP_pc : GDP_PPP_pc;
  let pc_file_path = path.join(gdp_pc_class.output_gdp_pc_folder, `${gdp_pc_class.pc_prefix}_${year}.png`);
  let delong_hg_base = gdp_class.getDelongBaseline(-10000);
  let pop_file_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
  let sub_floor = delong_hg_base * 0.25;
  
  console.log(`\n========================================================================`);
  console.log(`[TEST] Testing GDP Per Capita Spatial Variance for Year ${year === 0 ? "1 AD (0)" : year + " AD"} [${mode}]`);
  console.log(`Target Raster: ${pc_file_path}`);
  console.log(`DeLong Subsistence Floor: $${sub_floor.toFixed(2)} (Ex-Nordhaus -10000 BC base: $${delong_hg_base.toFixed(2)})`);
  console.log(`========================================================================\n`);
  
  if (!fs.existsSync(pc_file_path)) {
    console.error(`[ERROR] Per-capita raster not found: ${pc_file_path}`);
    return false;
  }
  if (!fs.existsSync(pop_file_path)) {
    console.error(`[ERROR] Population raster not found: ${pop_file_path}`);
    return false;
  }
  
  let pc_raster = GeoPNG.loadNumberRasterImage(pc_file_path, { format: "float32" });
  let pop_raster = GeoPNG.loadNumberRasterImage(pop_file_path, { format: "float32" });
  
  //1. Global Sanity Checks
  let below_floor_count = 0;
  let global_count = 0;
  let global_max = -Infinity;
  let global_min = Infinity;
  let global_pop_sum = 0;
  let global_total_gdp = 0;
  let nan_count = 0;
  
  //Group pixels by ISO3 country code
  let country_cells = {};
  
  for (let idx = 0; idx < pc_raster.data.length; idx++) {
    let p = pop_raster.data[idx];
    let v = pc_raster.data[idx];
    
    if (isNaN(v)) {
      nan_count++;
      continue;
    }
    
    if (p >= 1.0) {
      if (v > 0) {
        global_count++;
        global_pop_sum += p;
        global_total_gdp += v * p;
        if (v < global_min) global_min = v;
        if (v > global_max) global_max = v;
        if (v < sub_floor - 0.05) below_floor_count++;
        
        let byte_index = idx * 4;
        let col_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
        let geocodes = geocode_obj[col_key];
        if (geocodes && geocodes.length > 0) {
          let code = geocodes[0];
          if (!country_cells[code]) country_cells[code] = [];
          country_cells[code].push({ pc: v, pop: p });
        }
      }
    }
  }
  
  let global_pop_weighted_mean = (global_pop_sum > 0) ? (global_total_gdp / global_pop_sum) : 0;
  
  console.log(`--- [1/2] Global Sanity Metrics ---`);
  console.log(`  Populated Pixels:        ${global_count.toLocaleString()}`);
  console.log(`  Global Min GDP pc:       $${global_min.toFixed(2)} (Subsistence Floor: $${sub_floor.toFixed(2)})`);
  console.log(`  Global Max GDP pc:       $${global_max.toFixed(2)}`);
  console.log(`  Global Pop-Weighted Mean:$${global_pop_weighted_mean.toFixed(2)}`);
  console.log(`  Pixels Below Floor:      ${below_floor_count}`);
  console.log(`  NaN Count:               ${nan_count}`);
  
  let global_sane = true;
  if (nan_count > 0) {
    console.error(`  [FAIL] Raster contains ${nan_count} NaNs!`);
    global_sane = false;
  }
  if (below_floor_count > 0) {
    console.error(`  [FAIL] Raster contains ${below_floor_count} pixels below subsistence floor!`);
    global_sane = false;
  }
  if (global_min < 50) {
    console.error(`  [FAIL] Unsanely low minimum GDP pc ($${global_min.toFixed(2)}) detected!`);
    global_sane = false;
  }
  if (global_max > 100000 && year <= 1500) {
    console.error(`  [FAIL] Unsanely high maximum GDP pc ($${global_max.toFixed(2)}) detected for year <= 1500!`);
    global_sane = false;
  }
  if (global_sane) console.log(`  [PASS] Global sanity checks passed.\n`);
  
  //2. Per-ISO3 Intra-National Spatial Variance Checks
  console.log(`--- [2/2] Intra-National Spatial Variance Checks Across ISO3 Codes ---`);
  let tested_countries = 0;
  let single_cell_countries = 0;
  let all_codes = Object.keys(country_cells).sort();
  
  for (let i = 0; i < all_codes.length; i++) {
    let code = all_codes[i];
    let cells = country_cells[code];
    if (cells.length <= 1) {
      single_cell_countries++;
      continue;
    }
    tested_countries++;
    
    let pop_c = cells.reduce((s, c) => s + c.pop, 0);
    let weighted_pc_sum = cells.reduce((s, c) => s + c.pc * c.pop, 0);
    let weighted_mean = weighted_pc_sum / pop_c;
    
    //Compute standard deviation
    let sum_sq_diff = 0;
    let min_c = Infinity;
    let max_c = -Infinity;
    let val_counts = {};
    
    for (let j = 0; j < cells.length; j++) {
      let v = cells[j].pc;
      if (v < min_c) min_c = v;
      if (v > max_c) max_c = v;
      sum_sq_diff += Math.pow(v - weighted_mean, 2);
      let r_val = v.toFixed(1);
      val_counts[r_val] = (val_counts[r_val] || 0) + 1;
    }
    
    let std_dev = Math.sqrt(sum_sq_diff / cells.length);
    let unique_values = Object.keys(val_counts).length;
    let max_modal_count = Math.max(...Object.values(val_counts));
    let modal_pct = (max_modal_count / cells.length) * 100;
    
    country_means[code] = weighted_mean;
    
    //Variance failure condition: zero std dev, single unique value, or >= 95% modal plateau
    let min_std_dev = (mode === "nominal") ? 0.2 : 1.0;
    let is_flat = (unique_values <= 1 || (std_dev < min_std_dev && unique_values < cells.length) || (cells.length >= 20 && modal_pct >= 95));
    if (is_flat) {
      failed_countries.push({
        code: code,
        cells: cells.length,
        std_dev: std_dev,
        unique: unique_values,
        modal_pct: modal_pct,
        min: min_c,
        max: max_c,
        mean: weighted_mean
      });
    }
  }
  
  console.log(`  Total ISO3 Codes with Populated Cells: ${all_codes.length}`);
  console.log(`  Single-Cell Territories (Skipped):     ${single_cell_countries}`);
  console.log(`  Multi-Cell Countries Evaluated:        ${tested_countries}`);
  console.log(`  Countries Failing Variance Test:       ${failed_countries.length}`);
  
  if (failed_countries.length > 0) {
    console.error(`\n[FAIL] ${failed_countries.length} country code(s) exhibit flat spatial distribution:`);
    failed_countries.forEach((f) => {
      console.error(`  - ${f.code}: cells = ${f.cells}, std_dev = $${f.std_dev.toFixed(2)}, unique = ${f.unique}, modal = ${f.modal_pct.toFixed(1)}%, min = $${f.min.toFixed(2)}, max = $${f.max.toFixed(2)}`);
    });
    return false;
  }
  
  console.log(`  [PASS] ALL ${tested_countries} multi-cell countries possess robust continuous spatial variance!\n`);
  
  //3. Historical Relative Ranking Sniff Test (Year 0 / 1 AD)
  if (year === 0) {
    console.log(`--- [3/3] Historical Relative Ranking Sniff Test (Year 0 / 1 AD) ---`);
    let cze_mean = country_means["CZE"] || 0;
    let egy_mean = country_means["EGY"] || 0;
    let fra_mean = country_means["FRA"] || 0;
    let grc_mean = country_means["GRC"] || 0;
    let ita_mean = country_means["ITA"] || 0;
    let rus_mean = country_means["RUS"] || 0;
    
    // Novgorod coords: lat 58.52, lon 31.27; Lyon coords: lat 45.76, lon 4.83
    let nov_idx = Math.floor(((31.27 + 180) / 360) * 4320) + Math.floor(((90 - 58.52) / 180) * 2160) * 4320;
    let lyo_idx = Math.floor(((4.83 + 180) / 360) * 4320) + Math.floor(((90 - 45.76) / 180) * 2160) * 4320;
    let nov_pc = pc_raster.data[nov_idx];
    let lyo_pc = pc_raster.data[lyo_idx];
    
    console.log(`  ITA (Roman heartland):           $${ita_mean.toFixed(2)}`);
    console.log(`  EGY (Ptolemaic/Roman Egypt):     $${egy_mean.toFixed(2)}`);
    console.log(`  GRC (Ancient Greece):            $${grc_mean.toFixed(2)}`);
    console.log(`  FRA (Roman Gaul mean):           $${fra_mean.toFixed(2)}`);
    console.log(`  CZE (Bohemian tribal territory): $${cze_mean.toFixed(2)}`);
    console.log(`  RUS (Tribal Russia mean):        $${rus_mean.toFixed(2)}`);
    console.log(`  Lyon cell (Lugdunum):            $${lyo_pc.toFixed(2)}`);
    console.log(`  Novgorod cell:                   $${nov_pc.toFixed(2)}`);
    
    let ranking_ok = true;
    if (cze_mean >= ita_mean) {
      console.error(`  [FAIL] Czechia ($${cze_mean.toFixed(2)}) ranks above or equal to Roman Italy ($${ita_mean.toFixed(2)})!`);
      ranking_ok = false;
    }
    if (cze_mean >= egy_mean) {
      console.error(`  [FAIL] Czechia ($${cze_mean.toFixed(2)}) ranks above or equal to Egypt ($${egy_mean.toFixed(2)})!`);
      ranking_ok = false;
    }
    if (cze_mean >= grc_mean) {
      console.error(`  [FAIL] Czechia ($${cze_mean.toFixed(2)}) ranks above or equal to Greece ($${grc_mean.toFixed(2)})!`);
      ranking_ok = false;
    }
    if (rus_mean >= fra_mean) {
      console.error(`  [FAIL] Russia ($${rus_mean.toFixed(2)}) ranks above or equal to Roman Gaul ($${fra_mean.toFixed(2)})!`);
      ranking_ok = false;
    }
    if (nov_pc >= lyo_pc) {
      console.error(`  [FAIL] Novgorod pixel ($${nov_pc.toFixed(2)}) ranks above or equal to Lyon ($${lyo_pc.toFixed(2)})!`);
      ranking_ok = false;
    }
    if (ranking_ok) {
      console.log(`  [PASS] Historical relative rankings pass sniff test (Rome/Egypt/Greece > Czechia and Gaul > Russia/Novgorod)!\n`);
    } else {
      return false;
    }
  }
  
  return global_sane;
};

//Command-line runner
if (require.main === module) {
  (async () => {
    let target_years = [0, 100];
    let all_passed = true;
    
    for (let yr of target_years) {
      let ppp_ok = await testGDPSpatialVariance({ mode: "PPP", year: yr });
      let nom_ok = await testGDPSpatialVariance({ mode: "nominal", year: yr });
      if (!ppp_ok || !nom_ok) all_passed = false;
    }
    
    if (all_passed) {
      console.log(`\n========================================================================`);
      console.log(`[SUCCESS] All GDP Spatial Variance and Sanity Tests Passed!`);
      console.log(`========================================================================\n`);
      process.exit(0);
    } else {
      console.error(`\n[FAILURE] One or more spatial variance tests failed.`);
      process.exit(1);
    }
  })();
}

module.exports = { testGDPSpatialVariance };
