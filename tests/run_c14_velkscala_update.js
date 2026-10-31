let fs = require("fs");
let path = require("path");
let pngjs = require("pngjs");
let { execFileSync } = require("child_process");

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
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "population_c14bazAAR/population_c14bazAAR.js"));
require(path.join(h2, "population_Velkscala/population_Velkscala.js"));

(async () => {
  try {
    let t0 = Date.now();
    console.log("=== 1. Running population_c14bazAAR (Antiquity -10000 to 0) ===");
    population_c14bazAAR.A_ingestC14Data();
    if (!fs.existsSync(path.join(population_c14bazAAR.config_folder, "watershed_spds.json")))
      population_c14bazAAR.B_calibrateAndComputeSPDs();
    population_c14bazAAR.C_anchorAndBackcalculate();
    population_c14bazAAR.E_integrateStadesterUrban();
    await population_c14bazAAR.D_fitWLSDisaggregation();
    await population_c14bazAAR.F_generateDownscaledRasters();
    population_c14bazAAR.G_validateOutputs();

    console.log("\n=== 2. Recomputing National Populations & Development Index (--force) ===");
    execFileSync(process.execPath, [path.join(root_dir, "tests/precompute_development_index.js"), "--force"], {
      cwd: root_dir,
      stdio: "inherit"
    });

    console.log("\n=== 3. Running population_Velkscala Compositing & Metadata Sync ===");
    await population_Velkscala.processRasters();

    console.log(`\n=== ALL PIPELINES COMPLETED IN ${((Date.now() - t0)/1000).toFixed(1)}s ===`);
    if (GeoPNG.terminateAllWorkers) GeoPNG.terminateAllWorkers();
    process.exit(0);
  } catch (err) {
    console.error("Fatal error:", err);
    if (GeoPNG.terminateAllWorkers) GeoPNG.terminateAllWorkers();
    process.exit(1);
  }
})();

