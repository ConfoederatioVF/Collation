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
    let urb_path = path.join(h2, `population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`);
    let crop_path = path.join(h2, `landuse_HYDE/rasters/cropland${y_name}_number.png`);
    
    let urb_raster = fs.existsSync(urb_path) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;
    let crop_raster = fs.existsSync(crop_path) ? GeoPNG.loadNumberRasterImage(crop_path, { format: "float32" }) : null;
    
    let urb_sums = {};
    let crop_sums = {};
    
    if (urb_raster || crop_raster) {
      for (let i = 0; i < total_pixels; i++) {
        let u = urb_raster ? urb_raster.data[i] : 0;
        let c = crop_raster ? crop_raster.data[i] : 0;
        
        if (u > 0 || c > 0) {
          let byte_index = i * 4;
          let col = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index+1]},${geocode_raster.data[byte_index+2]}`;
          let codes = geocode_obj[col];
          if (codes && codes.length > 0) {
            let primary_code = codes[0];
            if (u > 0) urb_sums[primary_code] = (urb_sums[primary_code] || 0) + u;
            if (c > 0) crop_sums[primary_code] = (crop_sums[primary_code] || 0) + c;
          }
        }
      }
    }
    
    cache_obj[year] = {};
    let pop_year = national_populations[year] || {};
    let all_codes = new Set([...Object.keys(pop_year), ...Object.keys(urb_sums), ...Object.keys(crop_sums)]);
    
    all_codes.forEach((code) => {
      let p = pop_year[code] || 0;
      let u = urb_sums[code] || 0;
      let cr = crop_sums[code] || 0;
      let u_rate = (p > 0) ? Math.min(1.0, u / p) : 0;
      let c_cap = (p > 0) ? (cr / p) : 0; // km^2 per capita
      let agri_share = Math.min(1.0, c_cap / 0.005);
      let urb_share = Math.min(1.0, u_rate / 0.15);
      let dev_index = +(urb_share + 0.1 * agri_share).toFixed(5);
      
      cache_obj[year][code] = {
        pop: Math.round(p),
        urban: Math.round(u),
        cropland: +cr.toFixed(2),
        u_rate: +u_rate.toFixed(5),
        c_cap: +c_cap.toFixed(6),
        dev_index: dev_index
      };
    });
    
    if ((idx + 1) % 16 === 0 || idx === hyde_years.length - 1) {
      let elapsed = ((Date.now() - start_time) / 1000).toFixed(1);
      console.log(`[${idx + 1}/${hyde_years.length}] Processed year ${year} (${elapsed}s)`);
    }
  }
  
  let out_file = path.join(h2, "population_Stadester/stadester_national_development_index.json");
  fs.writeFileSync(out_file, JSON.stringify(cache_obj, null, 2), "utf8");
  let stat = fs.statSync(out_file);
  console.log(`\nSuccessfully created ${out_file} (${stat.size} bytes in ${((Date.now() - start_time) / 1000).toFixed(1)}s)`);
})();
