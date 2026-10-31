let fs = require("fs");
let path = require("path");
let pngjs = require("pngjs");

global.fs = fs;
global.path = path;
global.pngjs = pngjs;
global.mathjs = require("mathjs");
global.cubic_spline = require("cubic-spline");
global.JSON5 = require("json5");

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
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
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
require(path.join(h2, "population_Global/population_Global.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "population_c14bazAAR/population_c14bazAAR.js"));
require(path.join(h2, "population_Velkscala/population_Velkscala.js"));

let land_area = GeoPNG.loadNumberRasterImage(population_c14bazAAR.input_land_area_raster, { format: "int32" }).data;
let wmobb = GeoPNG.loadNumberRasterImage(population_c14bazAAR.input_wmobb_raster, { format: "int32" }).data;
let chunk_index = population_c14bazAAR_binning.buildWatershedISO3ChunkIndex({
  land_area_data: land_area,
  wmobb_data: wmobb
});

let geocode_obj = admin_modern.getISO3ColourcodesObject();
let geocode_img = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
let px_iso = new Array(4320*2160);
let iso_area = {};
for (let i = 0; i < 4320*2160; i++) {
  let b = i*4;
  let col = `${geocode_img.data[b]},${geocode_img.data[b + 1]},${geocode_img.data[b + 2]}`;
  let codes = geocode_obj[col];
  let c = (codes && codes.length > 0) ? codes[0] : null;
  px_iso[i] = c;
  if (c && land_area[i] > 0) iso_area[c] = (iso_area[c] || 0) + land_area[i];
}

// 1. Check LIE trajectory across Velkscala, Stadester, and metadata JSONs
let stad_np = JSON.parse(fs.readFileSync(population_Velkscala.file_stadester_national_populations, "utf8"));
let velk_np = JSON.parse(fs.readFileSync(population_Velkscala.file_national_populations, "utf8"));
let velk_ndi = JSON.parse(fs.readFileSync(population_Velkscala.file_national_development_index, "utf8"));

console.log("=== 1. LIECHTENSTEIN (LIE) TRAJECTORY ACROSS PIPELINE & METADATA ===");
let lie_years = [-10000, -5000, -3000, -2000, -1000, -500, -100, 0, 100, 500, 1000, 1500, 1700, 1800, 1850, 1900, 1930, 1940, 1950, 1975, 2000, 2025];
for (let i = 0; i < lie_years.length; i++) {
  let yr = lie_years[i];
  let vp = GeoPNG.loadNumberRasterImage(path.join(population_Velkscala.input_popc_folder, `population_${yr}.png`), { format: "float32" }).data;
  let lie_pop = vp[2218434] + vp[2222754];
  let che_sum = 0;
  let aut_sum = 0;
  for (let p = 0; p < vp.length; p++) {
    if (px_iso[p] === "CHE") che_sum += vp[p];
    else if (px_iso[p] === "AUT") aut_sum += vp[p];
  }
  let ndi_e = velk_ndi[yr]?.LIE;
  console.log(
    `Yr ${String(yr).padStart(6)} | Velk LIE=${lie_pop.toFixed(1).padStart(7)} (${(lie_pop/118).toFixed(2).padStart(6)}/km²) | CHE=${(che_sum/iso_area.CHE).toFixed(2).padStart(6)}/km² | AUT=${(aut_sum/iso_area.AUT).toFixed(2).padStart(6)}/km²` +
    (velk_np[yr] ? ` | velk_np=${String(velk_np[yr].LIE || 0).padStart(8)} | stad_np=${String(stad_np[yr]?.LIE || 0).padStart(8)} | crop=${ndi_e?.cropland ?? "-"} | dev=${ndi_e?.dev_index ?? "-"}` : "")
  );
}

// 2. Check cross-border discontinuities and intra-chunk CV preservation
console.log("\n=== 2. PRE-1 AD CROSS-BORDER ERASURE & INTRA-CHUNK SPATIAL VARIANCE INVARIANCE ===");
let models = JSON.parse(fs.readFileSync(path.join(population_c14bazAAR.config_folder, "c14_wls_disaggregation_models.json"), "utf8"));
let glaciated = population_c14bazAAR._getGlaciatedOutlierBasins();
let uopp_r = GeoPNG.loadNumberRasterImage(population_c14bazAAR.input_hyde_uopp_raster, { format: "float32" });

let evalBorderJumps = function (rur_data, urb_data) {
  let jumps = [];
  let pair_jumps = {};
  for (let i = 0; i < chunk_index.multi_basin_keys.length; i++) {
    let b_entry = chunk_index.basins_obj[chunk_index.multi_basin_keys[i]];
    for (let x = 0; x < b_entry.edges_array.length; x++) {
      let edge = b_entry.edges_array[x];
      let iso_u = b_entry.chunks_array[edge.u].iso3;
      let iso_v = b_entry.chunks_array[edge.v].iso3;
      let pkey = `${iso_u}-${iso_v}`;
      for (let y = 0; y < edge.p1_array.length; y++) {
        let p1 = edge.p1_array[y];
        let p2 = edge.p2_array[y];
        if (urb_data && (urb_data[p1] > 0 || urb_data[p2] > 0)) continue;
        let d1 = (rur_data[p1] || 0)/(land_area[p1] || 1);
        let d2 = (rur_data[p2] || 0)/(land_area[p2] || 1);
        if (d1 > 1e-6 && d2 > 1e-6) {
          let j = Math.abs(Math.log(d2/d1));
          jumps.push(j);
          if (!pair_jumps[pkey]) pair_jumps[pkey] = [];
          pair_jumps[pkey].push(j);
        }
      }
    }
  }
  jumps.sort((a, b) => a - b);
  let mean = jumps.reduce((s, v) => s + v, 0)/Math.max(1, jumps.length);
  let med = jumps[Math.floor(jumps.length*0.5)] || 0;
  let p90 = jumps[Math.floor(jumps.length*0.9)] || 0;
  return { count: jumps.length, mean: mean, med: med, p90: p90, pair_jumps: pair_jumps };
};

let computeChunkCV = function (data, px_arr, urb_data) {
  let vals = [];
  for (let i = 0; i < px_arr.length; i++) {
    let p = px_arr[i];
    if (urb_data && urb_data[p] > 0) continue;
    let a = land_area[p] || 0;
    if (a > 0) vals.push((data[p] || 0)/a);
  }
  if (vals.length < 10) return null;
  let mean = vals.reduce((s, v) => s + v, 0)/vals.length;
  if (mean <= 1e-9) return null;
  let var_s = vals.reduce((s, v) => s + (v - mean)*(v - mean), 0)/vals.length;
  return Math.sqrt(var_s)/mean;
};

for (let yr of [-10000, -5000, -3000, -1000]) {
  let yr_name = landuse_HYDE._getHYDEYearName(yr);
  let cr = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_hyde_landuse_folder, `cropland${yr_name}.png`), { format: "float32" });
  let gr = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_hyde_landuse_folder, `grazing${yr_name}.png`), { format: "float32" });
  let cv = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_hyde_landuse_folder, `conv_rangeland${yr_name}.png`), { format: "float32" });
  let kk = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_kk10luh2_global_folder, `popc_${yr}.png`), { format: "float32" });
  let pop = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.input_stadester_population_folder, `stadester_population_${yr}.png`), { format: "float32" });
  let urb = GeoPNG.loadNumberRasterImage(path.join(population_c14bazAAR.output_urban_folder, `urbc_${yr}.png`), { format: "float32" });
  let urbc_m = path.join(h2, "landuse_HYDE/rasters_mcevedy", `urbc_${yr}.png`);
  let urbc_r = path.join(population_c14bazAAR.input_hyde_landuse_folder, `urbc_${yr_name}.png`);
  let yr_umask = GeoPNG.getModernUrbanMask(uopp_r, { buffer_radius: 1, threshold: 10.0, urbc_raster: fs.existsSync(urbc_m) ? urbc_m : urbc_r });
  GeoPNG.inpaintUrbanMask(pop.data, yr_umask, { fallback_data: kk.data, land_area: land_area, radius: 3 });
  population_c14bazAAR_binning.inpaintOutlierCovariates(yr, [cr, gr, cv], { land_area: land_area, radius: 4 });

  let coeffs = models[yr].coefficients;
  let raw_w = new Float32Array(4320*2160);
  for (let p = 0; p < raw_w.length; p++) {
    let u_val = urb.data[p] || 0;
    if (u_val > 0) continue;
    let s_val = Math.max(0, (pop.data[p] || 0) - u_val);
    if (yr < -3000 && glaciated.has(String(wmobb[p])) && land_area[p] > 0) {
      let max_fd = (yr <= -5000) ? 0.05 : 0.20;
      s_val = Math.min(s_val, max_fd*land_area[p]);
    }
    raw_w[p] = Math.max(0, coeffs.crop*(cr.data[p] || 0) + coeffs.graz*(gr.data[p] || 0) + coeffs.conv*(cv.data[p] || 0) + coeffs.stadester_pop*s_val);
  }

  let fin_rur = GeoPNG.loadNumberRasterImage(path.join(population_Velkscala.input_rurc_folder, `population_rural_${yr}.png`), { format: "float32" }).data;
  let raw_stats = evalBorderJumps(raw_w, urb.data);
  let fin_stats = evalBorderJumps(fin_rur, urb.data);

  let max_cv_diff = 0;
  let checked_chunks = 0;
  for (let i = 0; i < chunk_index.multi_basin_keys.length; i++) {
    let b_entry = chunk_index.basins_obj[chunk_index.multi_basin_keys[i]];
    for (let x = 0; x < b_entry.chunks_array.length; x++) {
      let cv0 = computeChunkCV(raw_w, b_entry.chunks_array[x].pixels_array, urb.data);
      let cv1 = computeChunkCV(fin_rur, b_entry.chunks_array[x].pixels_array, urb.data);
      if (cv0 !== null && cv1 !== null) {
        checked_chunks++;
        let diff = Math.abs(cv1 - cv0);
        if (diff > max_cv_diff) max_cv_diff = diff;
      }
    }
  }

  console.log(
    `Yr ${String(yr).padStart(6)} | Raw |ln(dp/dq)|: med=${raw_stats.med.toFixed(4)} (${Math.exp(raw_stats.med).toFixed(2)}x), mean=${raw_stats.mean.toFixed(4)}, p90=${raw_stats.p90.toFixed(4)} (${Math.exp(raw_stats.p90).toFixed(2)}x)\n` +
    `          | Fin |ln(dp/dq)|: med=${fin_stats.med.toFixed(4)} (${Math.exp(fin_stats.med).toFixed(2)}x), mean=${fin_stats.mean.toFixed(4)}, p90=${fin_stats.p90.toFixed(4)} (${Math.exp(fin_stats.p90).toFixed(2)}x)\n` +
    `          | Intra-chunk CV invariance across ${checked_chunks} chunks: max |ΔCV| = ${max_cv_diff.toExponential(3)}`
  );

  if (yr === -1000) {
    let notable = ["CAN-USA", "IDN-PNG", "GEO-RUS", "MNG-RUS", "IRN-TKM", "MLI-SEN", "CHE-LIE", "AUT-LIE"];
    for (let k = 0; k < notable.length; k++) {
      let pk = notable[k];
      let r_arr = raw_stats.pair_jumps[pk] || [];
      let f_arr = fin_stats.pair_jumps[pk] || [];
      if (r_arr.length > 0 && f_arr.length > 0) {
        let rm = r_arr.reduce((s, v) => s + v, 0)/r_arr.length;
        let fm = f_arr.reduce((s, v) => s + v, 0)/f_arr.length;
        console.log(`    Border ${pk.padEnd(8)}: raw mean jump = ${Math.exp(rm).toFixed(2)}x -> reconciled = ${Math.exp(fm).toFixed(2)}x`);
      }
    }
  }
}

