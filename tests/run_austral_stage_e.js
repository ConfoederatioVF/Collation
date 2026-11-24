//Bootstrap Node globals matching core/startup.js for fast AUSTRAL-only Stage E refresh
global.child_process = require("child_process");
global.exec = global.child_process.exec;
global.fs = require("fs");
global.JSON5 = require("json5");
global.net = require("net");
global.node_require = require;
global.path = require("path");
global.util = require("util");

function lazyGlobal (arg0_prop_name, arg1_require_path, arg2_sub_prop) {
  let prop_name = arg0_prop_name;
  let req_path = arg1_require_path;
  let sub_prop = arg2_sub_prop;
  let cached;

  Object.defineProperty(global, prop_name, {
    configurable: true,
    enumerable: true,
    get: function () {
      if (!cached) {
        let mod = require(req_path);
        cached = (sub_prop) ? mod[sub_prop] : mod;
      }
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

async function streamFilterRegion (arg0_file_path, arg1_region_key) {
  let readline = require("readline");
  let registry = StadesterPartitionIO.loadPrecedenceRegistry();
  let target_key = String(arg1_region_key).toUpperCase();
  let out = {};
  let rl = readline.createInterface({
    input: fs.createReadStream(arg0_file_path, { encoding: "utf8", highWaterMark: 4*1024*1024 }),
    crlfDelay: Infinity
  });
  let buf = [];
  let in_entry = false;
  let total = 0;
  let kept = 0;
  for await (let line of rl) {
    if (!in_entry) {
      if (line.startsWith('  "') && line.endsWith('{')) {
        in_entry = true;
        buf = [line];
      }
      continue;
    }
    if (line === "  }," || line === "  }") {
      buf.push("  }");
      total++;
      let parsed = JSON.parse("{\n" + buf.join("\n") + "\n}");
      let k = Object.keys(parsed)[0];
      let val = parsed[k];
      let proj = StadesterPartitionIO.assignCityToViscountRegion(val, k, registry);
      if (proj && proj.key === target_key) {
        out[k] = val;
        kept++;
      }
      buf = [];
      in_entry = false;
    } else {
      buf.push(line);
    }
  }
  console.log(`- Stream-filtered ${kept}/${total} entries for region ${target_key} from ${arg0_file_path}.`);
  return out;
}

function updateRegionShardInDir (arg0_dir, arg1_region_key, arg2_region_obj) {
  let target_dir = path.resolve(arg0_dir);
  if (!fs.existsSync(target_dir)) fs.mkdirSync(target_dir, { recursive: true });
  let registry = StadesterPartitionIO.loadPrecedenceRegistry();
  let proj = registry.projects_by_key[arg1_region_key];
  let max_bytes = registry.max_shard_bytes || 209715200;

  // Remove old shards for this region only (e.g. 13_austral.json, 13_austral_1.json, ...)
  let prefix_re = new RegExp(`^${proj.shard_prefix}(?:_\\d+)?\\.json$`, "i");
  for (let fn of fs.readdirSync(target_dir)) {
    if (prefix_re.test(fn)) {
      try { fs.unlinkSync(path.join(target_dir, fn)); } catch (e) {}
    }
  }

  let entries = Object.keys(arg2_region_obj).map((k) => [k, arg2_region_obj[k]]);
  let res = StadesterPartitionIO.streamWriteJsonShard(target_dir, proj.shard_prefix, entries, max_bytes);

  let man_path = path.join(target_dir, "stadester_manifest.json");
  let man = fs.existsSync(man_path) ? JSON.parse(fs.readFileSync(man_path, "utf8")) : {
    format: "stadester_viscount_v1",
    regions: [],
    version: "2.0"
  };
  let found = false;
  for (let i = 0; i < man.regions.length; i++) {
    if (man.regions[i].key === arg1_region_key) {
      man.regions[i] = {
        bytes: res.bytes,
        count: entries.length,
        files: res.files,
        key: proj.key,
        order: proj.order,
        slug: proj.slug,
        z_priority: proj.z_priority
      };
      found = true;
      break;
    }
  }
  if (!found) {
    man.regions.push({
      bytes: res.bytes,
      count: entries.length,
      files: res.files,
      key: proj.key,
      order: proj.order,
      slug: proj.slug,
      z_priority: proj.z_priority
    });
  }
  let total_entries = man.regions.reduce((a, r) => a + (Number(r.count) || 0), 0);
  man.generated_at = new Date().toISOString();
  man.total_entries = total_entries;
  man.total_cities = total_entries;
  fs.writeFileSync(man_path, JSON.stringify(man, null, 2), "utf8");
  console.log(`- Updated ${arg1_region_key} shard(s) in ${target_dir}: ${entries.length} entries -> ${res.files.join(", ")} (${(res.bytes/1048576).toFixed(1)} MB)`);
}

(async () => {
  try {
    let t0 = Date.now();
    let phase_arg = (process.argv.find((a) => a.startsWith("--phase=")) || "--phase=austral_shards").slice(8);
    console.log(`[AUSTRAL StageE:${phase_arg}] Bootstrapped ${files.length} files cleanly.`);

    if (phase_arg === "austral_shards") {
      let registry = StadesterPartitionIO.loadPrecedenceRegistry();
      let austral_obj = await streamFilterRegion(population_Stadester.file_flattened_stadester, "AUSTRAL");
      austral_obj = population_Stadester_uud.fixStadesterErrors(austral_obj);
      austral_obj = population_Stadester_uud.integrateGHSLIntoStadester(austral_obj, {
        raw_folder: population_Stadester.raw_folder
      });
      // Prune any non-AUSTRAL GHSL global backfill clusters outside AUSTRAL
      for (let k of Object.keys(austral_obj)) {
        let p = StadesterPartitionIO.assignCityToViscountRegion(austral_obj[k], k, registry);
        if (!p || p.key !== "AUSTRAL") delete austral_obj[k];
      }
      if (typeof population_Stadester_uud.reconcileCloseSameCountryTwins === "function")
        austral_obj = population_Stadester_uud.reconcileCloseSameCountryTwins(austral_obj);
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(austral_obj);

      console.log(`[AUSTRAL StageE:austral_shards] Processing areas & radial buffers for ${Object.keys(austral_obj).length} AUSTRAL cities...`);
      austral_obj = population_Stadester_density.processCitiesAreas(austral_obj, {
        raw_folder: population_Stadester.raw_folder
      });
      austral_obj = population_Stadester_density.cacheRadialBuffers(austral_obj);
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(austral_obj);

      updateRegionShardInDir(population_Stadester.file_stadester_final, "AUSTRAL", austral_obj);
      updateRegionShardInDir(population_Stadester.file_stadester_vis, "AUSTRAL", austral_obj);
      let dv_target = "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0";
      if (fs.existsSync(path.dirname(dv_target))) {
        updateRegionShardInDir(dv_target, "AUSTRAL", austral_obj);
        let dv_dir = path.dirname(dv_target);
        for (let cf of ["stadester_2.0_lite.json", "stadester_2.0_indexed.json", "stadester_city_cache.json"]) {
          let cp = path.join(dv_dir, "cache", cf);
          if (fs.existsSync(cp)) try { fs.unlinkSync(cp); } catch (e) {}
        }
        population_Stadester.syncDataviewCityCoords(dv_dir, austral_obj);
      }
    } else if (phase_arg === "f") {
      await population_Stadester.F_generateBaseRasters({ concurrency: 3 });
    } else if (phase_arg === "substrata") {
      await population_Substrata_outlier_removal.processRasters({ concurrency: 3, exclude: ["A", "B2"], only_projects: ["AUSTRAL"] });
    } else if (phase_arg === "gij") {
      await population_Stadester.processRasters({ concurrency: 3, exclude: ["A", "B", "C", "D", "E", "F"] });
    } else if (phase_arg === "velkscala") {
      await population_Velkscala.processRasters({ concurrency: 4 });
    } else if (phase_arg === "transform") {
      await population_Stadester_transform.processRasters();
    } else {
      throw new Error(`Unknown phase: ${phase_arg}`);
    }

    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();

    console.log(`[AUSTRAL StageE:${phase_arg}] COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s`);
    process.exit(0);
  } catch (err) {
    console.error("[AUSTRAL StageE] FATAL:", err);
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function")
      GeoPNG.terminateAllWorkers();
    process.exit(1);
  }
})();
