//Bootstrap Node globals matching core/startup.js for fast CENTAUR Stage E refresh
global.child_process = require("child_process");
global.exec = global.child_process.exec;
global.fs = require("fs");
global.JSON5 = require("json5");
global.net = require("net");
global.node_require = require;
global.path = require("path");
global.util = require("util");

/**
 * Defines a lazy global getter for heavy pipeline libraries.
 *
 * @param {string} arg0_prop_name
 * @param {string} arg1_require_path
 * @param {string} [arg2_sub_prop]
 */
function lazyGlobal (arg0_prop_name, arg1_require_path, arg2_sub_prop) {
  //Convert from parameters
  let prop_name = arg0_prop_name;
  let req_path = arg1_require_path;
  let sub_prop = arg2_sub_prop;

  //Declare local instance variables
  let cached;

  //Function body
  Object.defineProperty(global, prop_name, {
    configurable: true,
    enumerable: true,
    get: function () {
      if (!cached) {
        let mod = require(req_path);
        cached = (sub_prop) ? mod[sub_prop] : mod;
      }

      //Return statement
      return cached;
    },
    set: function (arg0_val) {
      cached = arg0_val;
    }
  });
}

lazyGlobal("cubic_spline", "cubic-spline");
lazyGlobal("geotiff", "geotiff");
lazyGlobal("JSDOM", "jsdom", "JSDOM");
lazyGlobal("mathjs", "mathjs");
lazyGlobal("ml_matrix", "ml-matrix");
lazyGlobal("netcdfjs", "netcdfjs");
lazyGlobal("pngjs", "pngjs");
lazyGlobal("polylabel", "polylabel");

global.h1 = "./histmap/1.data_raw/";
global.h2 = "./histmap/2.data_cleaning/";
global.h3 = "./histmap/3.data_transform/";
global.h4 = "./histmap/4.data_exports/";
global.h5 = "./histmap/5.data_visualisation/";

require("../UF/js/vercengen/startup/vercengen_startup.js");

let preloaded_viscount = [
  "histmap/3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountMaternVariogram.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountHUResidualHelpers.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountCountyCensusFrontier.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountHUResidualKriging.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataMosaic.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataPipeline.js"
];

let files = ve.getImportFiles([
  "UF/js",
  "UF/libraries/turf.min.js",
  "!UF/archives",
  "!UF/libraries",
  "!UF/js/ontology",
  "!UF/js/vercengen",
  "!UF/js/date/History.js",
  "!UF/js/geospatiale/maptalks.formats.min.js",
  "!UF/js/geospatiale/shp.min.js",
  "!UF/js/geospatiale/files/png/png_worker.js",
  "common",
  "histmap/2.data_cleaning/landuse_HYDE",
  "histmap/2.data_cleaning/metadata_HYDE",
  "histmap/2.data_cleaning/population_GHSL",
  "histmap/2.data_cleaning/population_Global",
  "histmap/2.data_cleaning/population_KK10LUH2",
  "histmap/2.data_cleaning/population_Stadester",
  "histmap/2.data_cleaning/population_Velkscala",
  "histmap/3.data_transform/population_Substrata.viscount",
  "histmap/3.data_transform/population_Substrata.russia",
  "histmap/3.data_transform/population_Substrata.outlier_removal",
  "histmap/3.data_transform/population_Stadester.transform",
  "!histmap/1.data_raw",
  "!histmap/**/_rasters",
  "!histmap/**/stadester_*_rasters",
  "!histmap/**/velkscala_*_rasters",
  "!histmap/**/rasters*",
  "!**/archives/**",
  ...preloaded_viscount.map((arg0_p) => `!${arg0_p}`)
]);

for (let i = 0; i < preloaded_viscount.length; i++)
  Object.assign(global, require(path.resolve(process.cwd(), preloaded_viscount[i])));

for (let i = 0; i < files.length; i++) {
  let fp = files[i];
  if (path.extname(fp).toLowerCase() === ".js")
    eval(fs.readFileSync(fp, "utf8"));
}

(async () => {
  try {
    let t0 = Date.now();
    console.log(`[StageE-Fast] Bootstrapped ${files.length} files cleanly.`);

    let skip_deltas = process.argv.includes("--skip-deltas");
    let skip_shards = process.argv.includes("--skip-shards");
    let skip_substrata = process.argv.includes("--skip-substrata");

    if (!skip_shards) {
      console.log("[StageE-Fast] 1/5 Refreshing Stadestér shards, Dataview shards & base urban rasters (A–F)...");
      await population_Stadester.processRasters({ exclude: ["G", "H", "I", "J"], overwrite: true });
    } else {
      console.log("[StageE-Fast] 1/5 Skipped Stadestér A–F (--skip-shards).");
    }

    if (!skip_substrata) {
      console.log("[StageE-Fast] 2/5 Running ViscountSubstrataPipeline (CENTAUR) + global scaling + GHSL interpolation...");
      await population_Substrata_outlier_removal.processRasters({ exclude: ["A", "B2"], only_projects: ["CENTAUR"] });
    } else {
      console.log("[StageE-Fast] 2/5 Skipped ViscountSubstrataPipeline (--skip-substrata).");
    }

    console.log("[StageE-Fast] 3/5 Reconciling Stadestér urban/rural/total rasters (G–J)...");
    await population_Stadester.processRasters({ exclude: ["A", "B", "C", "D", "E", "F"] });

    console.log("[StageE-Fast] 4/5 Running population_Velkscala (Viscount antiquity + 2D harmonic diffusion)...");
    await population_Velkscala.processRasters();

    if (!skip_deltas) {
      console.log("[StageE-Fast] 5/5 Refreshing population_Stadester_transform deltas...");
      await population_Stadester_transform.processRasters();
    } else {
      console.log("[StageE-Fast] 5/5 Skipped population_Stadester_transform (--skip-deltas).");
    }

    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();

    console.log(`[StageE-Fast] COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s`);
    process.exit(0);
  } catch (err) {
    console.error("[StageE-Fast] FATAL:", err);
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();
    process.exit(1);
  }
})();
