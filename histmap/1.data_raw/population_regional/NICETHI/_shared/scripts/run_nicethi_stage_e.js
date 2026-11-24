//Isolated-phase Stage E runner for Operation Viscount Project NICETHI (order 14, z_priority 14)
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
let phase = phase_arg ? phase_arg.slice(8) : "cde_nicethi";
let include_handbook_seam = process.argv.includes("--include-handbook");

(async function () {
  let t0 = Date.now();
  console.log(`[nicethi_stage_e] Bootstrapped ${files.length} files (root=${root_dir}). Running phase=${phase}...`);

  if (phase === "cde_nicethi") {
    let registry = global.StadesterPartitionIO.loadPrecedenceRegistry();

    console.log(`[nicethi_stage_e] Step A: Initialising isolated NICETHI UUD (only_project="NICETHI")...`);
    let raw_uud = global.population_Stadester_uud.initialiseUUD({
      only_project: "NICETHI",
      raw_folder: global.population_Stadester.raw_folder
    });

    let nicethi_uud = {};
    let raw_keys = Object.keys(raw_uud);
    let viscount_tagged = 0;
    let legacy_only = 0;
    for (let i = 0; i < raw_keys.length; i++) {
      let k = raw_keys[i];
      let c = raw_uud[k];
      let reg = global.StadesterPartitionIO.assignCityToViscountRegion(c, k, registry);
      if (reg && reg.key === "NICETHI") {
        nicethi_uud[k] = c;
        if (c && c.viscount_project === "NICETHI") viscount_tagged++;
        else legacy_only++;
      }
      delete raw_uud[k];
    }
    raw_uud = null;
    if (global.gc) global.gc();
    console.log(`[nicethi_stage_e] Filtered UUD to ${Object.keys(nicethi_uud).length} NICETHI settlements (viscount_tagged=${viscount_tagged}, legacy_supplement=${legacy_only}).`);

    console.log(`[nicethi_stage_e] Step B: Interpolating NICETHI UUD across HYDE domain...`);
    nicethi_uud = global.population_Stadester_uud.interpolateUUD(nicethi_uud);

    console.log(`[nicethi_stage_e] Step C: Parsing UUD, 3-Phase Metro Reconciliation, Fixes, and 1975-2025 GHSL DEGURBA...`);
    let stadester = global.population_Stadester_uud.parseUUDToStadester(nicethi_uud);
    nicethi_uud = null;
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

    //Strict post-C region isolation filter so zero non-NICETHI manual or GHSL records leak into 14_nicethi
    let nicethi_obj = {};
    let post_c_keys = Object.keys(stadester);
    for (let i = 0; i < post_c_keys.length; i++) {
      let k = post_c_keys[i];
      let c = stadester[k];
      let reg = global.StadesterPartitionIO.assignCityToViscountRegion(c, k, registry);
      if (reg && reg.key === "NICETHI") nicethi_obj[k] = c;
      delete stadester[k];
    }
    stadester = null;
    if (global.gc) global.gc();

    //Post-C NICETHI compiled hygiene: authentic African toponym tags, metro scope tags, and legacy baseline twin/variant-dup reconciliation
    {
      let { viscount_entity_audit } = require(path.join(root_dir, ".agents/skills/population-regional-study/scripts/viscount_entity_and_continuity_audit.js"));
      let profiles = viscount_entity_audit.loadSkillProfiles(root_dir);
      let hy_keys = Object.keys(nicethi_obj);
      let dropped_placeholders = 0;
      let tagged_metros = 0;
      let tagged_verified = 0;

      for (let i = 0; i < hy_keys.length; i++) {
        let k = hy_keys[i];
        let c = nicethi_obj[k];
        if (!c) continue;
        let cname = String(c.name || "").trim();
        if (/^\((?:n\.d\.|n\.n\.|unorg\.)\)/i.test(k) || /^\((?:n\.d\.|n\.n\.|unorg\.)\)/i.test(cname)) {
          delete nicethi_obj[k];
          dropped_placeholders++;
          continue;
        }
        if (/^(?:jinja|sabon-machi)$/i.test(cname)) {
          c.verified_settlement = true;
          tagged_verified++;
        }
        if (/\(agglomeration\)/i.test(`${k} ${cname}`) && c.population_scope !== "metro") {
          c.population_scope = "metro";
          tagged_metros++;
        }
      }

      //Score and deduplicate <= 1.5 km same-country modern twins and <= 25 km same-country variant-spelling/exonym duplicates
      let entries = [];
      let rem_keys = Object.keys(nicethi_obj);
      for (let i = 0; i < rem_keys.length; i++) {
        let k = rem_keys[i];
        let c = nicethi_obj[k];
        if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
        let lat = Number(c.coords[0]);
        let lon = Number(c.coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
        let pop = (c.population && typeof c.population === "object") ? c.population : {};
        let pyrs = Object.keys(pop);
        let peak = 0;
        let max_yr = -99999;
        let pos_n = 0;
        for (let x = 0; x < pyrs.length; x++) {
          let yi = Number(pyrs[x]);
          let pv = Number(pop[pyrs[x]] || 0);
          if (Number.isFinite(yi) && pv > 0) {
            pos_n++;
            if (pv > peak) peak = pv;
            if (yi > max_yr) max_yr = yi;
          }
        }
        let is_viscount = (c.viscount_project === "NICETHI") ? 1 : 0;
        let is_dup_suffix = /_\d+$/.test(k) ? 1 : 0;
        entries.push({
          city: c,
          country: String(c.country || "").trim().toLowerCase(),
          is_dup_suffix: is_dup_suffix,
          is_viscount: is_viscount,
          key: k,
          lat: lat,
          lon: lon,
          max_yr: max_yr,
          name: String(c.name || "").trim(),
          peak: peak,
          pos_n: pos_n,
          scope: String(c.population_scope || "city_proper"),
          stem: viscount_entity_audit.normaliseEntityStem(String(c.name || "").trim())
        });
      }

      //Sort preferred winners first: Viscount NICETHI > non-_2 suffix > higher peak > more data points
      entries.sort(function (arg0_a, arg1_b) {
        if (arg1_b.is_viscount !== arg0_a.is_viscount) return arg1_b.is_viscount - arg0_a.is_viscount;
        if (arg0_a.is_dup_suffix !== arg1_b.is_dup_suffix) return arg0_a.is_dup_suffix - arg1_b.is_dup_suffix;
        if (arg1_b.peak !== arg0_a.peak) return arg1_b.peak - arg0_a.peak;
        return arg1_b.pos_n - arg0_a.pos_n;
      });

      let grid = new Map();
      let merged_dups = 0;
      for (let i = 0; i < entries.length; i++) {
        let cur = entries[i];
        let gx = Math.floor(cur.lat*2);
        let gy = Math.floor(cur.lon*2);
        let winner = null;

        for (let dx = -1; dx <= 1 && !winner; dx++) {
          for (let dy = -1; dy <= 1 && !winner; dy++) {
            let bucket = grid.get(`${gx + dx},${gy + dy}`);
            if (!bucket) continue;
            for (let x = 0; x < bucket.length; x++) {
              let kept = bucket[x];
              if (kept.scope !== cur.scope && (kept.scope === "metro" || cur.scope === "metro")) continue;
              let d_km = viscount_entity_audit.haversineKm(cur.lat, cur.lon, kept.lat, kept.lon);
              let is_modern_twin = (kept.country === cur.country && d_km <= 1.5 && kept.max_yr >= 1900 && cur.max_yr >= 1900);
              let is_variant_dup = (
                d_km <= 25.0 &&
                cur.stem && kept.stem &&
                (cur.stem === kept.stem || viscount_entity_audit.areEquivalentExonyms(cur.name, kept.name, profiles)) &&
                (cur.name.toLowerCase() !== kept.name.toLowerCase() || d_km <= 5.0)
              );
              if (is_modern_twin || is_variant_dup) {
                winner = kept;
                break;
              }
            }
          }
        }

        if (winner) {
          //Merge non-overlapping historical population years into winner and drop duplicate shell
          let w_pop = winner.city.population || {};
          let c_pop = cur.city.population || {};
          let cyrs = Object.keys(c_pop);
          for (let x = 0; x < cyrs.length; x++) {
            let yk = cyrs[x];
            let cv = Number(c_pop[yk] || 0);
            if (cv > 0 && (!w_pop[yk] || Number(w_pop[yk]) <= 0))
              w_pop[yk] = c_pop[yk];
          }
          if (Array.isArray(cur.city.sources)) {
            let ws = Array.isArray(winner.city.sources) ? winner.city.sources : [];
            winner.city.sources = Array.from(new Set(ws.concat(cur.city.sources)));
          }
          delete nicethi_obj[cur.key];
          merged_dups++;
        } else {
          let gk = `${gx},${gy}`;
          if (!grid.has(gk)) grid.set(gk, []);
          grid.get(gk).push(cur);
        }
      }
      console.log(`[nicethi_stage_e] Compiled hygiene: dropped_placeholders=${dropped_placeholders}, tagged_verified=${tagged_verified}, tagged_metros=${tagged_metros}, merged_dups=${merged_dups}, remaining=${Object.keys(nicethi_obj).length}`);
    }

    //Verify zero negative values and inspect 1974->1975 DEGURBA continuity
    let country_counts = {};
    let neg_vals = 0;
    let degurba_shocks = [];
    let n_keys = Object.keys(nicethi_obj);
    for (let i = 0; i < n_keys.length; i++) {
      let c = nicethi_obj[n_keys[i]];
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
    console.log(`[nicethi_stage_e] Post-C audit: cities=${n_keys.length}, negative_vals=${neg_vals}, metro_1974_1975_shocks=${degurba_shocks.length}`);
    console.log(`[nicethi_stage_e] Country breakdown (${Object.keys(country_counts).length} countries):`, JSON.stringify(country_counts));
    if (degurba_shocks.length > 0)
      console.log(`[nicethi_stage_e] Metro 1974->1975 shocks:`, degurba_shocks.slice(0, 15));

    console.log(`[nicethi_stage_e] Step D: Computing city areas & Angel densities...`);
    nicethi_obj = global.population_Stadester_density.processCitiesAreas(nicethi_obj, {
      raw_folder: global.population_Stadester.raw_folder
    });
    if (global.population_Stadester_ghs_pop && typeof global.population_Stadester_ghs_pop.cleanTransientMetadata === "function")
      global.population_Stadester_ghs_pop.cleanTransientMetadata(nicethi_obj);
    if (global.gc) global.gc();

    console.log(`[nicethi_stage_e] Step E: Streaming cacheRadialBuffers & isolated 14_nicethi shard writes across all 3 dirs...`);
    let dirs = [
      path.join(root_dir, "histmap/3.data_transform/population_Stadester.transform/stadester"),
      path.join(root_dir, "histmap/5.data_visualisation/stadester/stadester_2.0"),
      "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0"
    ];
    for (let d = 0; d < dirs.length; d++) {
      if (!fs.existsSync(dirs[d])) fs.mkdirSync(dirs[d], { recursive: true });
    }

    let max_bytes = 155*1024*1024;
    let sorted_keys = Object.keys(nicethi_obj).sort();
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
        chunk_obj[k] = nicethi_obj[k];
        delete nicethi_obj[k];
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
      let fn = (shard_blobs.length === 1) ? "14_nicethi.json" : `14_nicethi_${p + 1}.json`;
      new_files.push(fn);
      let b_len = Buffer.byteLength(shard_blobs[p].txt, "utf8");
      total_bytes += b_len;
      let mb = (b_len/(1024*1024)).toFixed(2);
      for (let d = 0; d < dirs.length; d++)
        fs.writeFileSync(path.join(dirs[d], fn), shard_blobs[p].txt, "utf8");
      console.log(`[nicethi_stage_e] Wrote ${fn}: ${shard_blobs[p].count} cities (${mb} MB) across all 3 dirs.`);
      shard_blobs[p].txt = null;
    }

    for (let d = 0; d < dirs.length; d++) {
      let dir_p = dirs[d];
      let existing = fs.readdirSync(dir_p).filter(function (arg0_f) {
        return /^14_nicethi(?:_\d+)?\.json$/.test(arg0_f);
      });
      for (let i = 0; i < existing.length; i++) {
        if (!new_files.includes(existing[i]))
          fs.unlinkSync(path.join(dir_p, existing[i]));
      }
      let m_path = path.join(dir_p, "stadester_manifest.json");
      let man = JSON.parse(fs.readFileSync(m_path, "utf8"));
      let tot = 0;
      for (let r = 0; r < man.regions.length; r++) {
        if (man.regions[r].key === "NICETHI") {
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

    console.log(`[nicethi_stage_e] Phase cde_nicethi COMPLETE (${total_cities} cities, ${new_files.length} shard(s), ${(total_bytes/(1024*1024)).toFixed(2)} MB) in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "fg") {
    if (global.GeoPNG && global.GeoPNG.compute_limits && global.GeoPNG.compute_limits.cpu) {
      global.GeoPNG.compute_limits.cpu.pipeline_concurrency = 2;
      global.GeoPNG.compute_limits.cpu.max_workers = 2;
    }
    await global.population_Stadester.F_generateBaseRasters();
    await global.population_Stadester.G_generateUrbanRasters();
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[nicethi_stage_e] Phase fg COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "substrata") {
    let disc = global.ViscountSubstrataPipeline.A_discoverActiveViscountContexts({ project_root: root_dir });
    console.log(`[nicethi_stage_e] Discovered ${disc.contexts.length} active Viscount substrata contexts.`);
    for (let i = 0; i < disc.contexts.length; i++) {
      let ctx = disc.contexts[i];
      if (ctx.key === "NICETHI" || ctx.key === "HANDBOOK")
        console.log(`  - ${ctx.key}: z_priority=${ctx.z_priority}, valid_px=${ctx.n_valid}, superseded=${ctx.superseded_pixel_count || 0}, seam_belt=${ctx.z_seam_blend ? ctx.z_seam_blend.belt_v_indices.length : 0}`);
    }
    let target_projects = include_handbook_seam ? ["NICETHI", "HANDBOOK"] : ["NICETHI"];
    console.log(`[nicethi_stage_e] Running ViscountSubstrataPipeline for [${target_projects.join(", ")}]...`);
    await global.ViscountSubstrataPipeline.B_processOrderedProjects(disc, {
      only_projects: target_projects,
      project_root: root_dir
    });
    global.ViscountSubstrataPipeline.E_preserveAllViscountDomainsInGlobalRasters({
      _viscount_discovery: disc,
      only_projects: target_projects,
      project_root: root_dir
    });
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[nicethi_stage_e] Phase substrata COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
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
    console.log(`[nicethi_stage_e] Phase ij COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else if (phase === "velk") {
    await global.population_Velkscala.processRasters();
    await global.population_Stadester_transform.processRasters();
    if (global.GeoPNG && typeof GeoPNG.terminateAllWorkers === "function") GeoPNG.terminateAllWorkers();
    console.log(`[nicethi_stage_e] Phase velk COMPLETE in ${((Date.now() - t0)/1000).toFixed(1)}s.`);
  } else {
    console.error(`[nicethi_stage_e] Unknown phase: ${phase}`);
    process.exit(2);
  }
})().catch(function (arg0_err) {
  console.error("[nicethi_stage_e] FATAL:", arg0_err);
  process.exit(1);
});
