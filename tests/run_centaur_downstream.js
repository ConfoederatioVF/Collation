//Import modules
let child_process = require("child_process");
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let util = require("util");

//Declare globals matching core/startup.js for headless Node execution
global.child_process = child_process;
global.fs = fs;
global.JSON5 = JSON5;
global.path = path;
global.util = util;
global.node_require = require;

function lazyGlobal (arg0_prop_name, arg1_require_path, arg2_sub_prop) {
  //Convert from parameters
  let prop_name = arg0_prop_name;
  let require_path = arg1_require_path;
  let sub_prop = arg2_sub_prop;

  //Declare local instance variables
  let cached;

  //Function body
  Object.defineProperty(global, prop_name, {
    get: function () {
      if (!cached) {
        let node_req = global.node_require || require;
        let mod = node_req(require_path);
        cached = (sub_prop) ? mod[sub_prop] : mod;
      }

      //Return statement
      return cached;
    },
    set: function (arg0_val) {
      cached = arg0_val;
    },
    configurable: true,
    enumerable: true
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

if (typeof window === "undefined") global.window = global;
if (typeof global.self === "undefined") global.self = global;
let _win_listeners = {};
window.addEventListener = function (arg0_ev, arg1_cb) {
  if (!_win_listeners[arg0_ev]) _win_listeners[arg0_ev] = [];
  _win_listeners[arg0_ev].push(arg1_cb);
};
window.removeEventListener = function () {};
global.is_naissance = true;
if (!fs.existsSync("./saves/")) fs.mkdirSync("./saves/", { recursive: true });

process.on("unhandledRejection", function (arg0_err) {
  console.error("[run_centaur_downstream] unhandledRejection:", arg0_err);
  process.exit(1);
});

require(path.resolve("./UF/js/vercengen/startup/vercengen_startup.js"));

let target_stage = String(process.argv[2] || "all").toLowerCase();

/**
 * Runs requested downstream CENTAUR-II pipeline stage(s) via headless Vercengen bootstrap.
 * @returns {Promise<void>}
 */
async function runStage () {
  //Declare local instance variables
  let exit_code = 0;

  //Function body
  try {
    // Re-load key Viscount/pipeline classes via native Node require() so __dirname resolves to each module directory
    let rebind_files = [
      "./histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataMosaic.js",
      "./histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataPipeline.js",
      "./histmap/2.data_cleaning/population_Stadester/StadesterPartitionIO.js",
      "./histmap/2.data_cleaning/population_Stadester/ViscountGazetteerLoader.js",
      "./histmap/2.data_cleaning/population_Stadester/stadester_uud_fixes.js",
      "./histmap/2.data_cleaning/population_Stadester/stadester_uud.js",
      "./histmap/2.data_cleaning/population_Stadester/population_Stadester.js",
      "./histmap/2.data_cleaning/population_Velkscala/population_Velkscala.js"
    ];
    for (let i = 0; i < rebind_files.length; i++) {
      let abs_p = path.resolve(rebind_files[i]);
      if (fs.existsSync(abs_p)) require(abs_p);
    }

    if (target_stage === "outlier" || target_stage === "all") {
      console.log("[run_centaur_downstream] Stage: population_Substrata_outlier_removal...");
      await population_Substrata_outlier_removal.processRasters({ exclude: ["A", "B2"] });
    }
    if (target_stage === "stadester" || target_stage === "all") {
      console.log("[run_centaur_downstream] Stage: population_Stadester...");
      await population_Stadester.processRasters({ overwrite: true });
      if (typeof population_Stadester_transform !== "undefined" && typeof population_Stadester_transform.processRasters === "function") {
        console.log("[run_centaur_downstream] Stage: population_Stadester_transform...");
        await population_Stadester_transform.processRasters();
      }
    }
    if (target_stage === "velkscala" || target_stage === "all") {
      console.log("[run_centaur_downstream] Stage: population_Velkscala...");
      await population_Velkscala.processRasters({ overwrite: true });
    }
    console.log(`[run_centaur_downstream] Stage '${target_stage}' completed cleanly.`);
  } catch (err) {
    console.error("[run_centaur_downstream] Pipeline error:", err);
    exit_code = 1;
  } finally {
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();
    process.exit(exit_code);
  }
}

console.log("[run_centaur_downstream] Calling ve.start...");
ve.start({
  is_browser: false,
  load_files: [
    "common",
    "!core/preload.js",
    "!core/startup.js",
    "histmap",
    "!histmap/1.data_raw",
    "!histmap/3.data_transform/age_sex_counterfactuals/archives",
    "!histmap/**/_rasters",
    "!histmap/**/stadester_*_rasters",
    "!histmap/**/velkscala_*_rasters",
    "!histmap/**/rasters*",
    "!histmap/**/geonames*",
    "!UF/js/geospatiale/files/png/png_worker.js",
    "!UF/js/geospatiale/maptalks.formats.min.js",
    "!UF/js/vercengen/db/NDJSON_worker.js",
    "!**/archives/**"
  ],
  special_function: function () {
    console.log("[run_centaur_downstream] special_function invoked!");
    if (!global._centaur_stage_started) {
      global._centaur_stage_started = true;
      runStage();
    }
  }
});
console.log("[run_centaur_downstream] ve.start returned; globals:",
  "outlier=", typeof global.population_Substrata_outlier_removal,
  "stadester=", typeof global.population_Stadester,
  "velkscala=", typeof global.population_Velkscala
);
setImmediate(function () {
  if (!global._centaur_stage_started && typeof global.population_Substrata_outlier_removal !== "undefined") {
    global._centaur_stage_started = true;
    console.log("[run_centaur_downstream] Running stage directly after ve.start load...");
    runStage();
  } else if (!global._centaur_stage_started) {
    console.error("[run_centaur_downstream] ERROR: SVEA classes did not load during ve.start.");
    process.exit(1);
  }
});
