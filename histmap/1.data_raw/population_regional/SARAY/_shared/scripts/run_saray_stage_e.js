//Bootstrap Node globals matching core/startup.js for Project SARAY Stage E integration
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

require(path.resolve(process.cwd(), "UF/js/vercengen/startup/vercengen_startup.js"));

let preloaded_viscount = [
  "histmap/3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountMaternVariogram.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js",
  "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualHelpers.js",
  "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountCountyCensusFrontier.js",
  "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js",
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
    console.log(`[SARAY StageE] Bootstrapped ${files.length} files cleanly.`);

    let shards_only = process.argv.includes("--shards-only");
    let skip_deltas = process.argv.includes("--skip-deltas");
    let skip_shards = process.argv.includes("--skip-shards");
    let skip_substrata = process.argv.includes("--skip-substrata");

    if (shards_only) {
      console.log("[SARAY StageE] Shards-only refresh (Steps A-E) -> SVEA + Dataview...");
      await population_Stadester.processRasters({ exclude: ["F", "G", "H", "I", "J"], overwrite: true, concurrency: 4 });
    } else {
      if (!skip_shards) {
        console.log("[SARAY StageE] 1/5 Refreshing Stadestér 2.0 shards & base urban rasters (A-F)...");
        await population_Stadester.processRasters({ exclude: ["G", "H", "I", "J"], overwrite: true, concurrency: 4 });
      }

      if (!skip_substrata) {
        console.log("[SARAY StageE] 2/5 Running ViscountSubstrataPipeline (only_projects: ['SARAY']) + global scaling + GHSL interpolation...");
        await population_Substrata_outlier_removal.processRasters({ exclude: ["A", "B2"], only_projects: ["SARAY"], concurrency: 4 });
      }

      console.log("[SARAY StageE] 3/5 Reconciling Stadestér urban/rural/total/density rasters (G-J)...");
      await population_Stadester.processRasters({ exclude: ["A", "B", "C", "D", "E", "F"], concurrency: 4 });

      console.log("[SARAY StageE] 4/5 Running population_Velkscala (218 timesteps + Viscount antiquity)...");
      await population_Velkscala.processRasters({ concurrency: 4 });

      if (!skip_deltas) {
        console.log("[SARAY StageE] 5/5 Refreshing population_Stadester_transform deltas...");
        await population_Stadester_transform.processRasters();
      }
    }

    //Mirror Stadestér 2.0 shards + manifest to Dataview/data/stadester/stadester_2.0/ (preserving stadester_1.0 and 1.1)
    let src_vis = path.resolve(process.cwd(), "histmap/5.data_visualisation/stadester/stadester_2.0");
    let dst_dv = "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0";
    let dv_cache_dir = "F:/Active Projects/Project 1436 - Dataview/data/stadester/cache";
    if (fs.existsSync(src_vis) && fs.existsSync(path.dirname(dst_dv))) {
      if (!fs.existsSync(dst_dv)) fs.mkdirSync(dst_dv, { recursive: true });
      let src_files = fs.readdirSync(src_vis).filter((arg0_f) => arg0_f.endsWith(".json"));
      let src_set = new Set(src_files);
      let old_dv = fs.readdirSync(dst_dv);
      for (let i = 0; i < old_dv.length; i++) {
        let fn = old_dv[i];
        if (/^08_saray.*\.json$/i.test(fn) && !src_set.has(fn)) {
          fs.unlinkSync(path.join(dst_dv, fn));
          console.log(`[SARAY StageE] Evicted stale SARAY shard in Dataview: ${fn}`);
        }
        if (/^stadester_2\.0_.*\.json$/i.test(fn)) {
          fs.unlinkSync(path.join(dst_dv, fn));
          console.log(`[SARAY StageE] Evicted stale Dataview cache: ${fn}`);
        }
      }
      if (fs.existsSync(dv_cache_dir)) {
        let c_files = fs.readdirSync(dv_cache_dir);
        for (let i = 0; i < c_files.length; i++) {
          if (/^stadester_2\.0_.*\.json$/i.test(c_files[i])) {
            fs.unlinkSync(path.join(dv_cache_dir, c_files[i]));
            console.log(`[SARAY StageE] Evicted stale Dataview cache dir file: ${c_files[i]}`);
          }
        }
      }
      let copied = 0;
      for (let i = 0; i < src_files.length; i++) {
        let fn = src_files[i];
        if (fn === "city_metadata.json") continue;
        fs.copyFileSync(path.join(src_vis, fn), path.join(dst_dv, fn));
        copied++;
      }
      console.log(`[SARAY StageE] Mirrored ${copied} Stadestér 2.0 shard/manifest files to Dataview.`);
    }

    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();

    console.log(`[SARAY StageE] COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s`);
    process.exit(0);
  } catch (err) {
    console.error("[SARAY StageE] FATAL:", err);
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();
    process.exit(1);
  }
})();
