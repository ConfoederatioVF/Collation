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

global.cubic_spline = require("cubic-spline");
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h3, "GDP_PPP/GDP_PPP.js"));

(async () => {
  console.log("=== Precomputing National Development Index (-10000 BC to 2025 AD) ===");
  let start_time = Date.now();
  
  let geocode_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let national_pop_file = path.join(h2, "population_Stadester/stadester_national_populations.json");
  let national_populations = JSON.parse(fs.readFileSync(national_pop_file, "utf8"));
  
  let hyde_years = landuse_HYDE.sorted_hyde_years;
  let out_file = path.join(h2, "population_Stadester/stadester_national_development_index.json");
  let cache_obj = {};
  if (fs.existsSync(out_file)) {
    try {
      cache_obj = JSON.parse(fs.readFileSync(out_file, "utf8"));
    } catch (e) {}
  }
  let has_all_years = hyde_years.every((y) => cache_obj[y] && Object.keys(cache_obj[y]).length > 0);
  
  if (!has_all_years) {
    let total_pixels = geocode_raster.data.length / 4;
    for (let idx = 0; idx < hyde_years.length; idx++) {
      let year = hyde_years[idx];
      let y_name = landuse_HYDE._getHYDEYearName(year);
    let pop_path = path.join(h2, `population_Stadester/stadester_population_rasters/stadester_population_${year}.png`);
    let urb_path = path.join(h2, `population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`);
    let crop_path = path.join(h2, `landuse_HYDE/rasters/cropland${y_name}.png`);
    let past_path = path.join(h2, `landuse_HYDE/rasters/pasture${y_name}.png`);
    
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
      let ag = (cr + pa) / 2;
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
    }
    }
  } else {
    console.log("- Pass 1 raster data already cached for all years; ensuring agricultural indicator = (cropland + pasture) / 2...");
    for (let yr in cache_obj) {
      for (let c in cache_obj[yr]) {
        let entry = cache_obj[yr][c];
        let cr = entry.cropland || 0;
        let pa = entry.pasture || 0;
        let p = entry.pop || 0;
        let ag = (cr + pa) / 2;
        entry.agri = +ag.toFixed(2);
        entry.ag_cap = (p > 0) ? +(ag / p).toFixed(6) : 0;
        entry.u_rate = (p > 0) ? +Math.min(1.0, (entry.urban || 0) / p).toFixed(5) : 0;
      }
    }
  }
  
  // Pass 2: Calculate intensive development index relative to empirical 100% baseline
  console.log("- Calculating intensive dev_index relative to empirical 100% baseline...");
  
  // 1. Calibrate empirical urbanization slope beta_u and agricultural indicator slope beta_ag dynamically via OLS across pre-industrial Maddison entries (y <= 1700)
  let maddison_csv_path = path.join(h1, "GDP_PPP/gdp_ppp_national_eoscala_1.4.csv");
  let raw_maddison_csv = File.loadCSVAsJSON(maddison_csv_path, { delimiter: ",", mode: "vertical" });
  let delong_baseline_obj = GDP_PPP.getDelongBaselineObject();
  let delong_hg_base = delong_baseline_obj[-10000];
  
  let reg_points = [];
  [1, 1000, 1500, 1600, 1700].forEach((yr) => {
    let hyde_y = (yr === 1) ? 0 : yr;
    let base_y = delong_baseline_obj[hyde_y];
    let tot_ag = 0;
    let tot_p = 0;
    for (let c in cache_obj[hyde_y]) {
      tot_ag += cache_obj[hyde_y][c].agri || 0;
      tot_p += cache_obj[hyde_y][c].pop || 0;
    }
    let world_ag_pc = (tot_p > 0) ? (tot_ag / tot_p) : 0;
    
    for (let c in raw_maddison_csv[yr]) {
      let val = raw_maddison_csv[yr][c]?.[0];
      if (val && val !== "") {
        let pop = national_populations[hyde_y]?.[c];
        let d_entry = cache_obj[hyde_y]?.[c];
        if (pop > 10000 && d_entry) {
          let pc = parseFloat(val) / pop;
          let rel_pc = pc / base_y;
          let u = d_entry.u_rate || 0;
          let ag_ratio = (world_ag_pc > 0) ? ((d_entry.ag_cap || 0) / world_ag_pc) : 1.0;
          reg_points.push({ ag_ratio: ag_ratio, rel_pc: rel_pc, u: u });
        }
      }
    }
  });
  
  // Multivariate OLS: rel_pc = alpha + beta_u * u + beta_ag * ag_ratio
  let n_reg = reg_points.length;
  let xtx = [[0, 0, 0], [0, 0, 0], [0, 0, 0]];
  let xty = [0, 0, 0];
  reg_points.forEach((p) => {
    let row = [1, p.u, p.ag_ratio];
    for (let r = 0; r < 3; r++) {
      xty[r] += row[r] * p.rel_pc;
      for (let c = 0; c < 3; c++) xtx[r][c] += row[r] * row[c];
    }
  });
  
  let det = xtx[0][0] * (xtx[1][1] * xtx[2][2] - xtx[1][2] * xtx[2][1]) -
    xtx[0][1] * (xtx[1][0] * xtx[2][2] - xtx[1][2] * xtx[2][0]) +
    xtx[0][2] * (xtx[1][0] * xtx[2][1] - xtx[1][1] * xtx[2][0]);
  let inv_xtx = [
    [
      (xtx[1][1] * xtx[2][2] - xtx[1][2] * xtx[2][1]) / det,
      (xtx[0][2] * xtx[2][1] - xtx[0][1] * xtx[2][2]) / det,
      (xtx[0][1] * xtx[1][2] - xtx[0][2] * xtx[1][1]) / det
    ],
    [
      (xtx[1][2] * xtx[2][0] - xtx[1][0] * xtx[2][2]) / det,
      (xtx[0][0] * xtx[2][2] - xtx[0][2] * xtx[2][0]) / det,
      (xtx[0][2] * xtx[1][0] - xtx[0][0] * xtx[1][2]) / det
    ],
    [
      (xtx[1][0] * xtx[2][1] - xtx[1][1] * xtx[2][0]) / det,
      (xtx[0][1] * xtx[2][0] - xtx[0][0] * xtx[2][1]) / det,
      (xtx[0][0] * xtx[1][1] - xtx[0][1] * xtx[1][0]) / det
    ]
  ];
  
  let beta_u = 0;
  let beta_ag = 0;
  for (let c = 0; c < 3; c++) {
    beta_u += inv_xtx[1][c] * xty[c];
    beta_ag += inv_xtx[2][c] * xty[c];
  }
  console.log(`  Dynamically calibrated empirical slopes: beta_u = ${beta_u.toFixed(4)}, beta_ag = ${beta_ag.toFixed(4)} (N=${n_reg})`);
  
  // 2. Precompute development index D_{y, c} for each HYDE keyframe
  for (let idx = 0; idx < hyde_years.length; idx++) {
    let year = hyde_years[idx];
    let base_y = delong_baseline_obj[year] || delong_hg_base;
    let floor_ratio = Math.min(1.0, delong_hg_base / base_y);
    
    if (year === -10000) {
      for (let c in cache_obj[year]) cache_obj[year][c].dev_index = 1.0;
      continue;
    }
    
    // Determine maximum empirical urbanization rate for that era to bound artificial polygon clipping
    let maddison_lookup_year = (year === 0) ? 1 : year;
    let max_u_era = 0;
    if (raw_maddison_csv[maddison_lookup_year]) {
      for (let c in raw_maddison_csv[maddison_lookup_year]) {
        let val = raw_maddison_csv[maddison_lookup_year][c]?.[0];
        let p = national_populations[year]?.[c];
        if (val && p > 50000) {
          let u = cache_obj[year]?.[c]?.u_rate || 0;
          if (u > max_u_era) max_u_era = u;
        }
      }
    }
    if (max_u_era === 0) max_u_era = 0.20; // Default empirical pre-industrial ceiling if no direct year record
    
    let total_ag = 0;
    let total_pop = 0;
    for (let c in cache_obj[year]) {
      total_ag += cache_obj[year][c].agri || 0;
      total_pop += cache_obj[year][c].pop || 0;
    }
    let world_ag_pc = (total_pop > 0) ? (total_ag / total_pop) : 0;
    
    let raw_scores = {};
    let weighted_sum = 0;
    for (let c in cache_obj[year]) {
      let entry = cache_obj[year][c];
      let p = entry.pop || 0;
      if (p > 0) {
        let ag_ratio = (world_ag_pc > 0) ? ((entry.ag_cap || 0) / world_ag_pc) : 1.0;
        let u_bounded = Math.min(max_u_era, entry.u_rate || 0);
        let s = Math.max(floor_ratio, 1.0 + beta_u * u_bounded + beta_ag * (ag_ratio - 1.0));
        raw_scores[c] = s;
        weighted_sum += s * p;
      }
    }
    
    let world_avg_s = (total_pop > 0) ? (weighted_sum / total_pop) : 1.0;
    for (let c in cache_obj[year]) {
      let entry = cache_obj[year][c];
      if (raw_scores[c] !== undefined) {
        let d = raw_scores[c] / world_avg_s;
        entry.dev_index = +d.toFixed(5);
      } else {
        entry.dev_index = +floor_ratio.toFixed(5);
      }
    }
  }
  
  fs.writeFileSync(out_file, JSON.stringify(cache_obj, null, 2), "utf8");
  let stat = fs.statSync(out_file);
  console.log(`\nSuccessfully created ${out_file} (${stat.size} bytes in ${((Date.now() - start_time) / 1000).toFixed(1)}s)`);
})();
