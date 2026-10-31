let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.JSON5 = require("json5");
global.pngjs = require("pngjs");

let root_dir = process.cwd();
global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");

function loadDir (arg0_rel_dir) {
  let full_dir = path.join(root_dir, arg0_rel_dir);
  if (!fs.existsSync(full_dir)) return;
  let files = fs.readdirSync(full_dir).filter((f) => f.endsWith(".js") && !f.includes("worker"));
  for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
}
loadDir("UF/js/number");
loadDir("UF/js/string");
loadDir("UF/js/colour");
loadDir("UF/js/object");
loadDir("UF/js/array");
loadDir("UF/js/geospatiale/operations");
loadDir("UF/js/geospatiale/files/png");

require(path.join(root_dir, "histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_Global/population_Global.js"));
require(path.join(root_dir, "histmap/2.data_cleaning/population_c14bazAAR/population_c14bazAAR.js"));

//Read previous broken watershed_populations.json from disk BEFORE running C_anchorAndBackcalculate
let out_pops_path = path.join(population_c14bazAAR.config_folder, "watershed_populations.json");
let prev_pops = JSON.parse(fs.readFileSync(out_pops_path, "utf8"));

//Run actual C_anchorAndBackcalculate() (writes updated watershed_populations.json)
let fixed_pops = population_c14bazAAR.C_anchorAndBackcalculate();

//Also compute exact 0a3d547 reference for verification
let wmobb_meta = JSON.parse(fs.readFileSync(population_c14bazAAR.input_wmobb_meta, "utf8"));
let c14_summary = JSON.parse(fs.readFileSync(population_c14bazAAR.input_c14_summary, "utf8"));
let date_counts = c14_summary.basin_counts || {};
let ag_indicators = JSON.parse(fs.readFileSync(population_c14bazAAR.input_archaeoglobe_watershed_indicators, "utf8"));
let watershed_spds = JSON.parse(fs.readFileSync(path.join(population_c14bazAAR.config_folder, "watershed_spds.json"), "utf8"));
let wmobb_raster = GeoPNG.loadNumberRasterImage(population_c14bazAAR.input_wmobb_raster, { format: "int32" });
let glaciated_basins = population_c14bazAAR._getGlaciatedOutlierBasins();
let anchor_years = population_c14bazAAR.anchor_years;
let target_years = population_c14bazAAR.target_years;
let all_basins = Object.keys(wmobb_meta);

let anchor_targets = {};
let basin_hyde_series = {};
for (let i = 0; i < anchor_years.length; i++) {
  let yr = anchor_years[i];
  anchor_targets[yr] = GeoPNG.getImageSum(path.join(population_c14bazAAR.input_stadester_population_folder, `stadester_population_${yr}.png`), { format: "float32" });
  basin_hyde_series[yr] = {};
  let hr = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_hyde_popc_folder, `popc_${yr}.png`), { format: "float32" });
  for (let x = 0; x < hr.data.length; x++) {
    let b = wmobb_raster.data[x];
    if (b > 0) basin_hyde_series[yr][b] = (basin_hyde_series[yr][b] || 0) + (hr.data[x] || 0);
  }
}
for (let i = 0; i < target_years.length; i++)
  if (!basin_hyde_series[target_years[i]]) basin_hyde_series[target_years[i]] = {};
for (let i = 0; i < all_basins.length; i++) {
  let b = all_basins[i];
  let vals = anchor_years.map((yr) => basin_hyde_series[yr][b] || 0);
  for (let x = 0; x < target_years.length; x++) {
    let yr = target_years[x];
    if (basin_hyde_series[yr][b] === undefined)
      basin_hyde_series[yr][b] = population_c14bazAAR._interpolateMonotonicSpline(anchor_years, vals, yr);
  }
}
let anchor_target_vals = anchor_years.map((yr) => anchor_targets[yr]);
let global_targets = {};
for (let i = 0; i < target_years.length; i++)
  global_targets[target_years[i]] = population_c14bazAAR._interpolateMonotonicSpline(anchor_years, anchor_target_vals, target_years[i]);

let basin_stadester_0 = {};
let sta0 = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_stadester_population_folder, "stadester_population_0.png"), { format: "float32" });
for (let i = 0; i < sta0.data.length; i++) {
  let b = wmobb_raster.data[i];
  if (b > 0) basin_stadester_0[b] = (basin_stadester_0[b] || 0) + (sta0.data[i] || 0);
}

let ag_pts_x = [-10000, -8000, -6000, -4000, -2000, -1000, 0];
let orig_pops = {};
for (let i = 0; i < all_basins.length; i++) {
  let b = all_basins[i];
  let h0_val = basin_hyde_series[0][b] || 0;
  let s0_val = basin_stadester_0[b] || 0;
  let is_glaciated = glaciated_basins.has(String(b));
  let anchor_0 = is_glaciated ? (h0_val || s0_val) : (s0_val || h0_val);
  let inds = ag_indicators[b]?.epochs || null;
  let ag_pts_y = ag_pts_x.map((yr) => (inds && inds[yr] && inds[yr].rel_capacity !== undefined) ? inds[yr].rel_capacity : ((yr === 0) ? 1.0 : 0.04));
  let n = date_counts[b] || 0;
  let s = watershed_spds[b] || {};
  let pre_s_vals = [];
  for (let x = 0; x < target_years.length; x++) {
    let yr = target_years[x];
    if (yr < 0 && s[yr] > 0) pre_s_vals.push(s[yr]);
  }
  let s_mean = (pre_s_vals.length > 0) ? (pre_s_vals.reduce((a, c) => a + c, 0)/pre_s_vals.length) : 0;
  let w = Math.min(0.50, n/(n + 100.0));
  orig_pops[b] = { 0: anchor_0 };
  for (let x = 0; x < target_years.length; x++) {
    let yr = target_years[x];
    if (yr === 0) continue;
    let r_ag = population_c14bazAAR._interpolateMonotonicSpline(ag_pts_x, ag_pts_y, yr);
    let r_h = (h0_val > 0) ? (basin_hyde_series[yr][b]/h0_val) : 0.04;
    let r_base = is_glaciated ? r_h : r_ag;
    let mod_factor = 1.0;
    if (n >= 10 && s_mean > 0) {
      let rel_diff = ((s[yr] || 0) - s_mean)/(s_mean + 0.01);
      let clamped_diff = Math.max(-0.60, Math.min(1.50, rel_diff));
      mod_factor = 1.0 + w*clamped_diff;
    }
    orig_pops[b][yr] = anchor_0*Math.max(0.005, r_base*mod_factor);
  }
}
for (let i = 0; i < target_years.length; i++) {
  let yr = target_years[i];
  let sum_pop = 0;
  for (let x = 0; x < all_basins.length; x++) sum_pop += orig_pops[all_basins[x]][yr];
  let scalar = (sum_pop > 0 && global_targets[yr] > 0) ? (global_targets[yr]/sum_pop) : 1;
  for (let x = 0; x < all_basins.length; x++) orig_pops[all_basins[x]][yr] *= scalar;
}

//Check global envelope conservation
let max_rel_err = 0;
for (let i = 0; i < target_years.length; i++) {
  let yr = target_years[i];
  let sum_fixed = 0;
  for (let x = 0; x < all_basins.length; x++) sum_fixed += fixed_pops[all_basins[x]][yr];
  let rel_err = Math.abs(sum_fixed - global_targets[yr])/Math.max(1, global_targets[yr]);
  if (rel_err > max_rel_err) max_rel_err = rel_err;
}
console.log(`Max global envelope error across 101 epochs: ${(max_rel_err*100).toExponential(3)}%`);

console.log("\n=== KEY RADIOCARBON-RICH WATERSHEDS (0a3d547 ORIG -> BROKEN 94e7578 -> FIXED) ===");
let rich_ids = ["642", "635", "639", "606", "607", "603", "662", "694", "695", "280", "162", "452", "423", "451"];
for (let i = 0; i < rich_ids.length; i++) {
  let b = rich_ids[i];
  let cols = [-8000, -5000, -3000, -1000].map((yr) => {
    let o = Math.round(orig_pops[b][yr]);
    let pr = Math.round(prev_pops[b][yr]);
    let fx = Math.round(fixed_pops[b][yr]);
    return `${yr}: ${o} -> ${pr} (${(pr/Math.max(1, o)).toFixed(2)}x) -> ${fx} (${(fx/Math.max(1, o)).toFixed(2)}x)`;
  });
  console.log(`[${b}] n=${date_counts[b]} ${(wmobb_meta[b]?.name || "").slice(0, 26)} | ${cols.join(" | ")}`);
}

console.log("\n=== REMOTE / PATAGONIA & AGRICULTURAL EDGE CASES (0a3d547 ORIG -> FIXED vs HYDE) ===");
let edge_ids = ["372", "375", "378", "389", "393", "316", "172", "458", "246", "254"];
for (let i = 0; i < edge_ids.length; i++) {
  let b = edge_ids[i];
  let cols = [-8000, -5000, -3000, -1000].map((yr) => {
    let o = Math.round(orig_pops[b][yr]);
    let pr = Math.round(prev_pops[b][yr]);
    let fx = Math.round(fixed_pops[b][yr]);
    let hy = Math.round(basin_hyde_series[yr][b]);
    return `${yr}: ${o}->${fx} (was ${pr}, H=${hy})`;
  });
  console.log(`[${b}] n=${date_counts[b] || 0} ${(wmobb_meta[b]?.name || "").slice(0, 26)} | ${cols.join(" | ")}`);
}
