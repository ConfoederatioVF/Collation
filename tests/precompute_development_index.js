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

require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));

(async () => {
  console.log("=== Precomputing National Development Index (-10000 BC to 2025 AD) ===");
  let start_time = Date.now();
  
  let geocode_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let national_pop_file = path.join(h2, "population_Stadester/stadester_national_populations.json");
  let national_populations = JSON.parse(fs.readFileSync(national_pop_file, "utf8"));
  
  let hyde_years = landuse_HYDE.sorted_hyde_years;
  let cache_obj = {};
  let total_pixels = geocode_raster.data.length / 4;
  
  for (let idx = 0; idx < hyde_years.length; idx++) {
    let year = hyde_years[idx];
    let y_name = landuse_HYDE._getHYDEYearName(year);
    let pop_path = path.join(h2, `population_Stadester/stadester_population_rasters/stadester_population_${year}.png`);
    let urb_path = path.join(h2, `population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`);
    let crop_path = path.join(h2, `landuse_HYDE/rasters/cropland${y_name}_number.png`);
    let past_path = path.join(h2, `landuse_HYDE/rasters/pasture${y_name}_number.png`);
    
    let pop_raster = fs.existsSync(pop_path) ? GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" }) : null;
    let urb_raster = fs.existsSync(urb_path) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;
    let crop_raster = fs.existsSync(crop_path) ? GeoPNG.loadNumberRasterImage(crop_path, { format: "float32" }) : null;
    let past_raster = fs.existsSync(past_path) ? GeoPNG.loadNumberRasterImage(past_path, { format: "float32" }) : null;
    
    let pop_sums = {};
    let urb_sums = {};
    let crop_sums = {};
    let past_sums = {};
    
    if (pop_raster || urb_raster || crop_raster || past_raster) {
      for (let i = 0; i < total_pixels; i++) {
        let p = pop_raster ? pop_raster.data[i] : 0;
        let u = urb_raster ? urb_raster.data[i] : 0;
        let cr = crop_raster ? crop_raster.data[i] : 0;
        let pa = past_raster ? past_raster.data[i] : 0;
        
        if (p > 0 || u > 0 || cr > 0 || pa > 0) {
          let byte_index = i * 4;
          let col = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
          let codes = geocode_obj[col];
          if (codes && codes.length > 0) {
            let primary_code = codes[0];
            if (p > 0) pop_sums[primary_code] = (pop_sums[primary_code] || 0) + p;
            if (u > 0) urb_sums[primary_code] = (urb_sums[primary_code] || 0) + u;
            if (cr > 0) crop_sums[primary_code] = (crop_sums[primary_code] || 0) + cr;
            if (pa > 0) past_sums[primary_code] = (past_sums[primary_code] || 0) + pa;
          }
        }
      }
    }
    
    cache_obj[year] = {};
    let all_codes = new Set([...Object.keys(pop_sums), ...Object.keys(urb_sums), ...Object.keys(crop_sums), ...Object.keys(past_sums)]);
    
    all_codes.forEach((code) => {
      let p = pop_sums[code] || 0;
      let u = urb_sums[code] || 0;
      let cr = crop_sums[code] || 0;
      let pa = past_sums[code] || 0;
      let ag = cr + pa;
      let u_rate = (p > 0) ? Math.min(1.0, u / p) : 0;
      let ag_cap = (p > 0) ? (ag / p) : 0;
      
      cache_obj[year][code] = {
        pop: Math.round(p),
        urban: Math.round(u),
        cropland: +cr.toFixed(2),
        pasture: +pa.toFixed(2),
        agri: +ag.toFixed(2),
        u_rate: +u_rate.toFixed(5),
        ag_cap: +ag_cap.toFixed(6)
      };
    });
    
    if ((idx + 1) % 16 === 0 || idx === hyde_years.length - 1) {
      let elapsed = ((Date.now() - start_time) / 1000).toFixed(1);
      console.log(`[${idx + 1}/${hyde_years.length}] Processed year ${year} (${elapsed}s)`);
    }
  }
  
  // Pass 2: Calculate intensive development index based on empirical agricultural saturation and urbanization
  console.log("- Calculating intensive dev_index relative to empirical pre-industrial saturation...");
  let ag_caps = [];
  let u_rates = [];
  for (let yr in cache_obj) {
    let y = parseInt(yr);
    if (y >= 0 && y <= 1800) {
      for (let c in cache_obj[yr]) {
        let e = cache_obj[yr][c];
        if (e.pop > 10000 && e.ag_cap > 0) ag_caps.push(e.ag_cap);
        if (e.pop > 10000 && e.u_rate > 0) u_rates.push(e.u_rate);
      }
    }
  }
  ag_caps.sort((a, b) => a - b);
  u_rates.sort((a, b) => a - b);
  let a_sat = ag_caps[Math.floor(ag_caps.length * 0.75)]; // 75th percentile of pre-industrial ag_cap
  let u_mean = u_rates.reduce((a, b) => a + b, 0) / u_rates.length; // Mean pre-industrial urbanization rate
  console.log(`  Dynamic empirical saturation: a_sat = ${a_sat.toFixed(6)}, u_mean = ${u_mean.toFixed(6)}`);
  
  for (let yr in cache_obj) {
    let y = parseInt(yr);
    for (let c in cache_obj[yr]) {
      let entry = cache_obj[yr][c];
      if (y === -10000) {
        entry.dev_index = 0.0;
      } else {
        let a_int = Math.min(1.0, (entry.ag_cap || 0) / a_sat);
        let u_int = (entry.u_rate || 0) / u_mean;
        let dev = a_int + u_int;
        entry.dev_index = +Math.max(0.0, dev).toFixed(5);
      }
    }
  }
  
  let out_file = path.join(h2, "population_Stadester/stadester_national_development_index.json");
  fs.writeFileSync(out_file, JSON.stringify(cache_obj, null, 2), "utf8");
  let stat = fs.statSync(out_file);
  console.log(`\nSuccessfully created ${out_file} (${stat.size} bytes in ${((Date.now() - start_time) / 1000).toFixed(1)}s)`);
})();
