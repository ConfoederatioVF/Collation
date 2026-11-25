//Import modules
let fs = require("fs");
let path = require("path");

//Initialise functions
{
  let root_dir = path.resolve(__dirname, "../..");
  let contract_path = path.join(root_dir, "tests/alignment/alignment_contract.json5");

  global.fs = fs;
  global.path = path;
  global.JSON5 = require("json5");
  global.h1 = path.join(root_dir, "histmap/1.data_raw");
  global.h2 = path.join(root_dir, "histmap/2.data_cleaning");
  global.h3 = path.join(root_dir, "histmap/3.data_transform");
  global.h5 = path.join(root_dir, "histmap/5.data_visualisation");

  //Load UF utility namespaces (File.loadCSVAsJSON, Object/Array/Geospatiale/Number/String helpers)
  let uf_dirs = ["", "file", "array", "object", "number", "string", "statistics", "geospatiale"];
  for (let d = 0; d < uf_dirs.length; d++) {
    let dir_p = path.join(root_dir, "UF/js", uf_dirs[d]);
    if (!fs.existsSync(dir_p)) continue;
    let files = fs.readdirSync(dir_p).sort();
    for (let f = 0; f < files.length; f++) {
      if (!files[f].endsWith(".js")) continue;
      let fp = path.join(dir_p, files[f]);
      if (fs.statSync(fp).isFile()) {
        try {
          require(fp);
        } catch (err) {
          //Skip browser-only UF modules
        }
      }
    }
  }

  require(path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/population_Stadester.js"));

  /**
   * Checks whether a [lat, lng] coordinate falls inside any configured audit bbox.
   * @param {Array<number>} arg0_coords
   * @param {Array<Object>} arg1_bboxes
   *
   * @returns {boolean}
   */
  let isInAnyBbox = function (arg0_coords, arg1_bboxes) {
    //Convert from parameters
    let coords = Array.isArray(arg0_coords) ? arg0_coords : [];
    let bboxes = Array.isArray(arg1_bboxes) ? arg1_bboxes : [];

    //Declare local instance variables
    let lat = Number(coords[0]);
    let lng = Number(coords[1]);

    //Guard clauses
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;

    //Function body
    for (let i = 0; i < bboxes.length; i++) {
      let b = bboxes[i];
      if (lat >= b.lat_min && lat <= b.lat_max && lng >= b.lng_min && lng <= b.lng_max)
        return true;
    }

    //Return statement
    return false;
  };

  /**
   * Runs the chunk UUD pipeline in memory across all alignment_contract test_bboxes
   * and writes chunk_stadester.json + merge_audit_log.json for Phase 4 visual auditing.
   */
  let runChunkUUD = function () {
    //Declare local instance variables
    let audit_log_array = [];
    let contract = global.JSON5.parse(fs.readFileSync(contract_path, "utf8"));
    let bbox_map = contract.test_bboxes || {};
    let bbox_list = Object.keys(bbox_map).map(function (arg0_k) {
      return bbox_map[arg0_k];
    });
    let raw_folder = `${global.h1}/population_Stadester/`;
    let uud_mod = global.population_Stadester_uud;
    let buffered_bboxes = bbox_list.map(function (arg0_b) {
      return {
        lat_min: arg0_b.lat_min - 2.0,
        lat_max: arg0_b.lat_max + 2.0,
        lng_min: arg0_b.lng_min - 2.0,
        lng_max: arg0_b.lng_max + 2.0
      };
    });

    /**
     * Filters a source DB object to records within buffered_bboxes.
     * @param {Object} arg0_db
     *
     * @returns {Object}
     */
    let filterSourceDB = function (arg0_db) {
      let out = {};
      let ks = Object.keys(arg0_db || {});
      for (let i = 0; i < ks.length; i++) {
        let rec = arg0_db[ks[i]];
        if (rec && isInAnyBbox(rec.coords, buffered_bboxes)) out[ks[i]] = rec;
      }
      return out;
    };

    console.log(`[run_chunk_uud] Loading & filtering source DBs to ${bbox_list.length} contract bboxes...`);
    let source_dbs = {
      populstat: { data: filterSourceDB(uud_mod.getPopulstatObject(raw_folder)) },
      chandler_modelski: { data: filterSourceDB(uud_mod.getWorldcitypopObject(raw_folder)), is_metro: true, precision: 0.1, semantic_precision: 1 },
      devries: { data: filterSourceDB(uud_mod.getDeVriesCitiesObject(raw_folder)), precision: 0.1, semantic_precision: 1 },
      buringh: { data: filterSourceDB(uud_mod.getBuringhObject(raw_folder)), precision: 0.05, semantic_precision: 1 },
      viscount_regional: { data: filterSourceDB(uud_mod.getViscountRegionalObject({ raw_folder: raw_folder })), is_polaris: true, precision: 0.05, semantic_precision: 0.25 }
    };
    console.log(`[run_chunk_uud] Source DBs filtered: populstat=${Object.keys(source_dbs.populstat.data).length}, chandler=${Object.keys(source_dbs.chandler_modelski.data).length}, devries=${Object.keys(source_dbs.devries.data).length}, buringh=${Object.keys(source_dbs.buringh.data).length}, viscount=${Object.keys(source_dbs.viscount_regional.data).length}`);

    let uud_obj = uud_mod.initialiseUUD({
      audit_log_array: audit_log_array,
      raw_folder: raw_folder,
      source_dbs: source_dbs
    });

    uud_obj = uud_mod.interpolateUUD(uud_obj, {
      raw_folder: raw_folder
    });

    let chunk_obj = uud_mod.parseUUDToStadester(uud_obj);
    console.log(`[run_chunk_uud] Parsed ${Object.keys(chunk_obj).length} chunk settlements.`);

    chunk_obj = uud_mod.flattenStadesterMetros(chunk_obj, {
      audit_log_array: audit_log_array
    });
    chunk_obj = uud_mod.fixStadesterErrors(chunk_obj, {
      audit_log_array: audit_log_array
    });
    chunk_obj = uud_mod.integrateGHSLIntoStadester(chunk_obj, {
      audit_log_array: audit_log_array,
      raw_folder: raw_folder
    });
    if (typeof uud_mod.reconcileCloseSameCountryTwins === "function") {
      chunk_obj = uud_mod.reconcileCloseSameCountryTwins(chunk_obj, {
        audit_log_array: audit_log_array
      });
    }
    if (typeof uud_mod.flattenToMunicipalityLevelAndCleanNames === "function") {
      chunk_obj = uud_mod.flattenToMunicipalityLevelAndCleanNames(chunk_obj, {
        audit_log_array: audit_log_array
      });
    }
    if (global.population_Stadester_ghs_pop && typeof global.population_Stadester_ghs_pop.cleanTransientMetadata === "function")
      global.population_Stadester_ghs_pop.cleanTransientMetadata(chunk_obj);

    let out_dir = __dirname;
    if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
    fs.writeFileSync(path.join(out_dir, "chunk_stadester.json"), JSON.stringify(chunk_obj));
    fs.writeFileSync(path.join(out_dir, "merge_audit_log.json"), JSON.stringify(audit_log_array, null, 2));
    console.log(`[run_chunk_uud] Wrote ${Object.keys(chunk_obj).length} settlements and ${audit_log_array.length} audit log events.`);
  };

  runChunkUUD();
}
