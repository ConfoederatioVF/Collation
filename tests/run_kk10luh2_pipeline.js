let fs = require("fs");
let path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
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
require(path.join(h2, "population_Global/population_Global.js"));
require(path.join(h2, "population_KK10LUH2/population_KK10LUH2.js"));
require(path.join(h3, "population_Substrata.northern_america/population_Substrata_northern_america.js"));
require(path.join(h3, "population_Substrata.outlier_removal/population_Substrata_outlier_removal.js"));

(async () => {
  try {
    let t_start = Date.now();
    console.log("=== Starting Reprocessed KK10LUH2 Pipeline ===");

    // Execute all stages: A, B, B2, C, D, E, F, G
    console.log("\n--- [Step A] Sum LUH2 Stocks ---");
    await population_KK10LUH2.A_averageLUH2Rasters();

    console.log("\n--- [Step B] Blend KK10 & LUH2 Land Use Fractions ---");
    await population_KK10LUH2.B_generateKK10LUH2Rasters();

    console.log("\n--- [Step B2] Generate ALCC Physical Area (km^2/cell) ---");
    await population_KK10LUH2.B2_generateALCCAreaRasters();

    console.log("\n--- [Step C] Calibrate Unscaled Population Proxy ---");
    await population_KK10LUH2.C_convertKK10LUH2RastersToRGBA({
      fallback_mode: "kk10luh2_domain"
    });

    console.log("\n--- [Step D] Scale to Regional HYDE Aggregates ---");
    await population_KK10LUH2.D_scaleKK10LUH2RastersToHYDE();

    console.log("\n--- [Step E] Scale to OWID Aggregates ---");
    await population_KK10LUH2.E_scaleKK10LUH2RastersToOWID();

    console.log("\n--- [Step F] Scale to Statista Regions ---");
    await population_KK10LUH2.F_scaleKK10LUH2RastersToStatista();

    console.log("\n--- [Step G] Scale to Global Population Totals ---");
    await population_KK10LUH2.G_scaleKK10LUH2RastersToGlobal();

    let elapsed = ((Date.now() - t_start) / 1000).toFixed(1);
    console.log(`\n=== KK10LUH2 Pipeline Completed Successfully in ${elapsed}s! ===`);
  } catch (err) {
    console.error("Error in KK10LUH2 pipeline execution:", err);
    process.exit(1);
  }
})();
