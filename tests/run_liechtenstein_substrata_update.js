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
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

require(path.join(h2, "metadata_HYDE/metadata_HYDE.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "population_Global/population_Global.js"));
require(path.join(h2, "population_KK10LUH2/population_KK10LUH2.js"));
require(path.join(h3, "population_Substrata.northern_america/population_Substrata_northern_america.js"));
require(path.join(h3, "population_Substrata.outlier_removal/population_Substrata_outlier_removal.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));

(async () => {
  try {
    let start_t = Date.now();
    // 1. Create liechtenstein_-10000_1930.png
    let geocode_obj = admin_modern.getISO3ColourcodesObject();
    let geocode_img = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
    let mask_png = new pngjs.PNG({ width: 4320, height: 2160, colorType: 6 });
    mask_png.data.fill(0);

    let lie_indices = [];
    for (let i = 0; i < 4320*2160; i++) {
      let b = i*4;
      let col = `${geocode_img.data[b]},${geocode_img.data[b + 1]},${geocode_img.data[b + 2]}`;
      let codes = geocode_obj[col];
      if (codes && codes[0] === "LIE") {
        mask_png.data[b] = 0;
        mask_png.data[b + 1] = 0;
        mask_png.data[b + 2] = 0;
        mask_png.data[b + 3] = 255;
        lie_indices.push(i);
      }
    }

    let mask_path = path.join(population_Substrata_outlier_removal.input_outlier_rasters, "liechtenstein_-10000_1930.png");
    fs.writeFileSync(mask_path, pngjs.PNG.sync.write(mask_png, { deflateLevel: 9 }));
    console.log(`Created ${mask_path} with ${lie_indices.length} LIE pixels:`, lie_indices);

    // Verify reading back via A_getHYDEOutlierMasksObject and GeoPNG.loadImage
    let masks_obj = await population_Substrata_outlier_removal.A_getHYDEOutlierMasksObject();
    console.log("Mask entry:", masks_obj[mask_path]);

    // 2. Run Substrata for affected HYDE years <= 1930
    let affected_years = landuse_HYDE.sorted_hyde_years.filter((y) => y <= 1930);
    console.log(`Running Substrata outlier removal & scaling for ${affected_years.length} years (<= 1930)...`);
    await population_Substrata_outlier_removal.processRasters({
      concurrency: 8,
      hyde_years: affected_years
    });

    // 3. Reconcile Stadester Population, Rural, and Density rasters for affected years
    console.log(`Running Stadester I_generatePopulationRasters & J_prepareIntermediates for ${affected_years.length} years...`);
    await population_Stadester.I_generatePopulationRasters({
      concurrency: 8,
      years: affected_years
    });
    await population_Stadester.J_prepareIntermediates({
      concurrency: 8,
      years: affected_years
    });

    // 4. Print LIE trajectory in updated Stadester rasters
    let check_years = [-10000, -5000, -3000, -1000, 0, 500, 1000, 1500, 1700, 1800, 1850, 1900, 1920, 1930, 1940, 1950, 2025];
    console.log("\n=== Updated Stadester LIE Trajectory ===");
    for (let i = 0; i < check_years.length; i++) {
      let yr = check_years[i];
      let p_file = path.join(population_Stadester.input_popc_folder, `stadester_population_${yr}.png`);
      let r = GeoPNG.loadNumberRasterImage(p_file, { format: "float32" });
      let sum = 0;
      for (let x = 0; x < lie_indices.length; x++) sum += r.data[lie_indices[x]];
      console.log(`  Year ${String(yr).padStart(6)}: LIE = ${sum.toFixed(1)} (${(sum/118).toFixed(2)}/km²)`);
    }

    console.log(`Done in ${((Date.now() - start_t)/1000).toFixed(1)}s`);
    if (GeoPNG.terminateAllWorkers) GeoPNG.terminateAllWorkers();
    process.exit(0);
  } catch (err) {
    console.error("Fatal error:", err);
    if (GeoPNG.terminateAllWorkers) GeoPNG.terminateAllWorkers();
    process.exit(1);
  }
})();

