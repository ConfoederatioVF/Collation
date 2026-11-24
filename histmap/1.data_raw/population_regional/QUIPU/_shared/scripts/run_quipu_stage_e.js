//Isolated-phase Stage E runner for Operation Viscount Project QUIPU (order 11, z_priority 11)
global.child_process = require("child_process");
global.exec = global.child_process.exec;
global.fs = require("fs");
global.JSON5 = require("json5");
global.net = require("net");
global.node_require = require;
global.path = require("path");
global.util = require("util");

let findSveaRoot = function (arg0_start) {
  let cur = path.resolve(arg0_start);
  for (let i = 0; i < 10; i++) {
    if (fs.existsSync(path.join(cur, "histmap")) && fs.existsSync(path.join(cur, "UF")))
      return cur;
    let parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return path.resolve(__dirname, "../../../../../..");
};

let root_dir = findSveaRoot(__dirname);
process.chdir(root_dir);

function lazyGlobal (arg0_prop_name, arg1_require_path, arg2_sub_prop) {
  let cached;
  Object.defineProperty(global, arg0_prop_name, {
    configurable: true,
    enumerable: true,
    get: function () {
      if (!cached) {
        let mod = require(arg1_require_path);
        cached = (arg2_sub_prop) ? mod[arg2_sub_prop] : mod;
      }
      return cached;
    },
    set: function (arg0_val) { cached = arg0_val; }
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

require(path.join(root_dir, "UF/js/vercengen/startup/vercengen_startup.js"));

let preloaded_viscount = [
  "histmap/3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountMaternVariogram.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js",
  "histmap/3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"
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
  ...preloaded_viscount.map(function (arg0_p) { return `!${arg0_p}`; })
]);

for (let i = 0; i < preloaded_viscount.length; i++)
  Object.assign(global, require(path.resolve(process.cwd(), preloaded_viscount[i])));

for (let i = 0; i < files.length; i++) {
  let fp = files[i];
  if (path.extname(fp).toLowerCase() === ".js")
    eval(fs.readFileSync(fp, "utf8"));
}

let phase_arg = process.argv.find(function (arg0_a) { return arg0_a.startsWith("--phase="); });
let phase = phase_arg ? phase_arg.slice(8) : "cde_quipu";

(async function () {
  let t0 = Date.now();
  console.log(`[quipu_stage_e] Bootstrapped ${files.length} files (root=${root_dir}). Running phase=${phase}...`);

  if (phase === "cde_quipu") {
    let registry = global.StadesterPartitionIO.loadPrecedenceRegistry();

    console.log(`[quipu_stage_e] Step A: Initialising isolated QUIPU UUD (only_project="QUIPU")...`);
    let raw_uud = global.population_Stadester_uud.initialiseUUD({
      only_project: "QUIPU",
      raw_folder: global.population_Stadester.raw_folder
    });

    let quipu_uud = {};
    let raw_keys = Object.keys(raw_uud);
    let viscount_tagged = 0;
    let legacy_only = 0;
    for (let i = 0; i < raw_keys.length; i++) {
      let k = raw_keys[i];
      let c = raw_uud[k];
      let reg = global.StadesterPartitionIO.assignCityToViscountRegion(c, k, registry);
      if (reg && reg.key === "QUIPU") {
        quipu_uud[k] = c;
        if (c && c.viscount_project === "QUIPU") viscount_tagged++;
        else legacy_only++;
      }
      delete raw_uud[k];
    }
    raw_uud = null;
    if (global.gc) global.gc();
    console.log(`[quipu_stage_e] Filtered UUD to ${Object.keys(quipu_uud).length} QUIPU settlements (viscount_tagged=${viscount_tagged}, legacy_supplement=${legacy_only}).`);

    console.log(`[quipu_stage_e] Step B: Interpolating QUIPU UUD across HYDE domain...`);
    quipu_uud = global.population_Stadester_uud.interpolateUUD(quipu_uud);

    console.log(`[quipu_stage_e] Step C: Parsing UUD, 3-Phase Metro Reconciliation, Fixes, and 1975-2025 GHSL DEGURBA...`);
    let stadester = global.population_Stadester_uud.parseUUDToStadester(quipu_uud);
    quipu_uud = null;
    if (global.gc) global.gc();

    stadester = global.population_Stadester_uud.flattenStadesterMetros(stadester);
    stadester = global.population_Stadester_uud.fixStadesterErrors(stadester);
    stadester = global.population_Stadester_uud.integrateGHSLIntoStadester(stadester, {
      raw_folder: global.population_Stadester.raw_folder
    });
    if (typeof global.population_Stadester_uud.reconcileCloseSameCountryTwins === "function")
      stadester = global.population_Stadester_uud.reconcileCloseSameCountryTwins(stadester);
    if (global.population_Stadester_ghs_pop && typeof global.population_Stadester_ghs_pop.cleanTransientMetadata === "function")
      global.population_Stadester_ghs_pop.cleanTransientMetadata(stadester);

    //Strict post-C region isolation filter so zero non-QUIPU manual or GHSL records leak into 11_quipu
    let quipu_obj = {};
    let post_c_keys = Object.keys(stadester);
    for (let i = 0; i < post_c_keys.length; i++) {
      let k = post_c_keys[i];
      let c = stadester[k];
      let reg = global.StadesterPartitionIO.assignCityToViscountRegion(c, k, registry);
      if (reg && reg.key === "QUIPU") quipu_obj[k] = c;
      delete stadester[k];
    }
    stadester = null;
    if (global.gc) global.gc();

    //Verify zero negative values and inspect 1974->1975 DEGURBA continuity
    let country_counts = {};
    let neg_vals = 0;
    let degurba_shocks = [];
    let q_keys = Object.keys(quipu_obj);
    for (let i = 0; i < q_keys.length; i++) {
      let c = quipu_obj[q_keys[i]];
      let ctry = String((c && c.country) || "Unknown");
      country_counts[ctry] = (country_counts[ctry] || 0) + 1;
      let pop = (c && c.population && typeof c.population === "object") ? c.population : null;
      if (!pop) continue;
      let is_metro = (c.extent_type === "metro") || /agglomeration|metropolitan/i.test(String(c.name || ""));
      let pyrs = Object.keys(pop);
      for (let x = 0; x < pyrs.length; x++) {
        let v = Number(pop[pyrs[x]]);
        if (Number.isFinite(v) && v < 0) neg_vals++;
      }
      if (is_metro && pop["1974"] > 50000 && pop["1975"] > 0) {
        let r = Number(pop["1975"])/Number(pop["1974"]);
        if (r > 1.35 || r < 0.70)
          degurba_shocks.push(`${c.name}(1974=${Math.round(pop["1974"])}->1975=${Math.round(pop["1975"])})`);
      }
    }
    console.log(`[quipu_stage_e] Post-C audit: cities=${q_keys.length}, negative_vals=${neg_vals}, metro_1974_1975_shocks=${degurba_shocks.length}`);
    console.log(`[quipu_stage_e] Country breakdown:`, JSON.stringify(country_counts));
    if (degurba_shocks.length > 0)
      console.log(`[quipu_stage_e] Metro 1974->1975 shocks:`, degurba_shocks.slice(0, 10));

    console.log(`[quipu_stage_e] Step D: Computing city areas & Angel densities...`);
    quipu_obj = global.population_Stadester_density.processCitiesAreas(quipu_obj, {
      raw_folder: global.population_Stadester.raw_folder
    });
    if (global.population_Stadester_ghs_pop && typeof global.population_Stadester_ghs_pop.cleanTransientMetadata === "function")
      global.population_Stadester_ghs_pop.cleanTransientMetadata(quipu_obj);
    if (global.gc) global.gc();

    console.log(`[quipu_stage_e] Step E: Streaming cacheRadialBuffers & isolated 11_quipu shard writes across all 3 dirs...`);
    let dirs = [
      path.join(root_dir, "histmap/3.data_transform/population_Stadester.transform/stadester"),
      path.join(root_dir, "histmap/5.data_visualisation/stadester/stadester_2.0"),
      "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0"
    ];
    for (let d = 0; d < dirs.length; d++) {
      if (!fs.existsSync(dirs[d])) fs.mkdirSync(dirs[d], { recursive: true });
    }

    let max_bytes = 155*1024*1024;
    let sorted_keys = Object.keys(quipu_obj).sort();
    let total_cities = sorted_keys.length;
    let shard_blobs = [];
    let coord_sync = {};
    let cur_parts = [];
    let cur_count = 0;
    let cur_b = 2;

    let stashShard = function () {
      if (cur_count === 0) return;
      shard_blobs.push({ count: cur_count, txt: "{" + cur_parts.join(",") + "}" });
      cur_parts = [];
      cur_count = 0;
      cur_b = 2;
    };

    let chunk_size = 15000;
    for (let start = 0; start < sorted_keys.length; start += chunk_size) {
      let end = Math.min(start + chunk_size, sorted_keys.length);
      let chunk_obj = {};
      for (let i = start; i < end; i++) {
        let k = sorted_keys[i];
        chunk_obj[k] = quipu_obj[k];
        delete quipu_obj[k];
      }
      chunk_obj = global.population_Stadester_density.cacheRadialBuffers(chunk_obj);
      for (let i = start; i < end; i++) {
        let k = sorted_keys[i];
        let cobj = chunk_obj[k];
        if (cobj) {
          coord_sync[k] = { coords: cobj.coords, country: cobj.country, name: cobj.name, region: cobj.region };
          let entry_s = JSON.stringify(k) + ":" + JSON.stringify(cobj);
          let eb = Buffer.byteLength(entry_s, "utf8") + 1;
          if (cur_count > 0 && cur_b + eb > max_bytes) stashShard();
          cur_parts.push(entry_s);
          cur_count++;
          cur_b += eb;
        }
        delete chunk_obj[k];
      }
      chunk_obj = null;
      if (global.gc) global.gc();
    }
    stashShard();

    let new_files = [];
    let total_bytes = 0;
    for (let p = 0; p < shard_blobs.length; p++) {
      let fn = (shard_blobs.length === 1) ? "11_quipu.json" : `11_quipu_${p + 1}.json`;
      new_files.push(fn);
      let b_len = Buffer.byteLength(shard_blobs[p].txt, "utf8");
      total_bytes += b_len;
      let mb = (b_len/(1024*1024)).toFixed(2);
      for (let d = 0; d < dirs.length; d++)
        fs.writeFileSync(path.join(dirs[d], fn), shard_blobs[p].txt, "utf8");
      console.log(`[quipu_stage_e] Wrote ${fn}: ${shard_blobs[p].count} cities (${mb} MB) across all 3 dirs.`);
      shard_blobs[p].txt = null;
    }

    for (let d = 0; d < dirs.length; d++) {
      let dir_p = dirs[d];
      let existing = fs.readdirSync(dir_p).filter(function (arg0_f) {
        return /^11_quipu(?:_\d+)?\.json$/.test(arg0_f);
      });
      for (let i = 0; i < existing.length; i++) {
        if (!new_files.includes(existing[i]))
          fs.unlinkSync(path.join(dir_p, existing[i]));
      }
      let m_path = path.join(dir_p, "stadester_manifest.json");
      let man = JSON.parse(fs.readFileSync(m_path, "utf8"));
      let tot = 0;
      for (let r = 0; r < man.regions.length; r++) {
        if (man.regions[r].key === "QUIPU") {
          man.regions[r].bytes = total_bytes;
          man.regions[r].count = total_cities;
          man.regions[r].files = new_files;
        }
        tot += Number(man.regions[r].count) || 0;
      }
      man.generated_at = new Date().toISOString();
      man.total_entries = tot;
      man.total_cities = tot;
      fs.writeFileSync(m_path, JSON.stringify(man, null, 2), "utf8");
    }

    let dv_dir = "F:/Active Projects/Project 1436 - Dataview/data/stadester";
    for (let fn of ["stadester_2.0_indexed.json", "stadester_2.0_lite.json", "stadester_city_cache.json"]) {
      let cp = path.join(dv_dir, "cache", fn);
      if (fs.existsSync(cp)) try { fs.unlinkSync(cp); } catch (e) {}
    }
    if (typeof global.population_Stadester.syncDataviewCityCoords === "function")
      global.population_Stadester.syncDataviewCityCoords(dv_dir, coord_sync);

    console.log(`[quipu_stage_e] Phase cde_quipu COMPLETE (${total_cities} cities, ${new_files.length} shard(s), ${(total_bytes/(1024*1024)).toFixed(2)} MB) in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "fg") {
    if (global.GeoPNG && global.GeoPNG.compute_limits && global.GeoPNG.compute_limits.cpu) {
      global.GeoPNG.compute_limits.cpu.pipeline_concurrency = 2;
      global.GeoPNG.compute_limits.cpu.max_workers = 2;
    }
    await global.population_Stadester.F_generateBaseRasters();
    await global.population_Stadester.G_generateUrbanRasters();
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[quipu_stage_e] Phase fg COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "substrata") {
    let disc = global.ViscountSubstrataPipeline.A_discoverActiveViscountContexts({ project_root: root_dir });
    console.log(`[quipu_stage_e] Discovered ${disc.contexts.length} active Viscount substrata contexts.`);
    for (let i = 0; i < disc.contexts.length; i++) {
      let ctx = disc.contexts[i];
      if (ctx.key === "QUIPU" || ctx.key === "PRETA" || ctx.key === "JAGUAR")
        console.log(`  - ${ctx.key}: z_priority=${ctx.z_priority}, valid_px=${ctx.n_valid}, superseded=${ctx.superseded_pixel_count || 0}`);
    }
    await global.ViscountSubstrataPipeline.B_processOrderedProjects(disc, {
      only_projects: ["QUIPU", "PRETA"],
      project_root: root_dir
    });
    global.ViscountSubstrataPipeline.E_preserveAllViscountDomainsInGlobalRasters({
      _viscount_discovery: disc,
      only_projects: ["QUIPU", "PRETA"],
      project_root: root_dir
    });
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[quipu_stage_e] Phase substrata COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "ij") {
    if (global.GeoPNG && global.GeoPNG.compute_limits && global.GeoPNG.compute_limits.cpu) {
      global.GeoPNG.compute_limits.cpu.pipeline_concurrency = 1;
      global.GeoPNG.compute_limits.cpu.max_workers = 1;
    }
    await global.population_Stadester.processRasters({
      concurrency: 1,
      exclude: ["A", "B", "C", "D", "E", "F", "G"]
    });
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[quipu_stage_e] Phase ij COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "velk") {
    await global.population_Velkscala.processRasters();
    await global.population_Stadester_transform.processRasters();
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[quipu_stage_e] Phase velk COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else {
    console.error(`[quipu_stage_e] Unknown phase: ${phase}`);
    process.exit(2);
  }
})().catch(function (arg0_err) {
  console.error("[quipu_stage_e] FATAL:", arg0_err);
  process.exit(1);
});
