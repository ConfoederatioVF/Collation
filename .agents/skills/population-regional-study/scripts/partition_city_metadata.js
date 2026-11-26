//Import modules
let crypto = require("crypto");
let fs = require("fs");
let path = require("path");
let { city_metadata_merger } = require("./merge_city_metadata");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");
let normaliser_path = path.resolve(__dirname, "../../../../histmap/2.data_cleaning/population_Stadester/stadester_name_normaliser.js");
let stadester_name_normaliser = fs.existsSync(normaliser_path) ? require(normaliser_path).stadester_name_normaliser : null;

//Initialise functions
{
  let city_metadata_partitioner = {
    ARTICLE_INVERT_RE: /^(.+?),\s*(Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,
    BACKTICK_HACEK_MAP: {
      "`C": "Č", "`c": "č", "`S": "Š", "`s": "š", "`Z": "Ž", "`z": "ž",
      "`R": "Ř", "`r": "ř", "`E": "Ě", "`e": "ě", "`N": "Ň", "`n": "ň",
      "`T": "Ť", "`t": "ť", "`D": "Ď", "`d": "ď", "`U": "Ů", "`u": "ů"
    },
    REGION_SHARD_FILES: [
      { file: "01_centaur.json", key: "CENTAUR" },
      { file: "02_polaris.json", key: "POLARIS" },
      { file: "03_preta.json", key: "PRETA" },
      { file: "04_jade.json", key: "JADE" },
      { file: "05_indus.json", key: "INDUS" },
      { file: "06_castle.json", key: "CASTLE" },
      { file: "07_mandala.json", key: "MANDALA" },
      { file: "08_saray.json", key: "SARAY" },
      { file: "09_handbook.json", key: "HANDBOOK" },
      { file: "10_magnetic.json", key: "MAGNETIC" },
      { file: "11_quipu.json", key: "QUIPU" },
      { file: "12_jaguar.json", key: "JAGUAR" },
      { file: "13_austral.json", key: "AUSTRAL" },
      { file: "14_nicethi.json", key: "NICETHI" }
    ],

    /**
     * Repairs common legacy GeoNames/Stadestér encoding artifacts (backtick haceks, comma-inverted articles, parentheticals).
     * @alias city_metadata_partitioner.cleanLegacyName
     *
     * @param {string} arg0_raw
     *
     * @returns {string}
     */
    cleanLegacyName (arg0_raw, arg1_country) {
      //Convert from parameters
      let country = arg1_country ? String(arg1_country) : "";
      let s = String(arg0_raw || "").trim();

      //Guard clauses
      if (!s || city_metadata_merger.EXCEL_ERROR_RE.test(s) || /^&nbsp;$/i.test(s) || /^0[-_a-zA-Z\s]*$/.test(s)) return "";

      //Function body
      s = s
        .replace(/andapos;|&apos;|&#39;/gi, "'")
        .replace(/&amp;/gi, "&")
        .replace(/&nbsp;/gi, " ")
        .replace(/^'(.+)'$/, "$1")
        .trim();
      let is_tibetan = (country === "China" && /'(?:brog|brong|char)/i.test(s));
      if (!/^'s-/i.test(s) && !is_tibetan) {
        s = s
          .replace(/(?:`|'')s(?:`|'')c/g, "shch").replace(/(?:`|'')S(?:`|'')c/g, "Shch")
          .replace(/['`]{1,2}s['`]{1,2}c/g, "shch").replace(/['`]{1,2}S['`]{1,2}c/g, "Shch")
          .replace(/'sč/g, "shch").replace(/'Sč/g, "Shch")
          .replace(/([a-z])'s'([a-z])/gi, "$1shch$2")
          .replace(/(?:`|'|''){1,2}C/g, "Č").replace(/(?:`|'|''){1,2}c/g, "č")
          .replace(/(^|[\s\-]|['`])['`]C/g, "$1Č").replace(/(^|[\s\-]|['`])['`]c/g, "$1č")
          .replace(/(?:''|`')S/g, "Š").replace(/(?:''|`')s/g, "š")
          .replace(/(?:''|`')Z/g, "Ž").replace(/(?:''|`')z/g, "ž")
          .replace(/(^|[\s\-])'C/g, "$1Č").replace(/(^|[\s\-])'c/g, "$1č")
          .replace(/(^|[\s\-])'S/g, "$1Š").replace(/(^|[\s\-])'s/g, "$1š")
          .replace(/(^|[\s\-])'Z/g, "$1Ž").replace(/(^|[\s\-])'z/g, "$1ž");
      }
      if (country === "United Kingdom")
        s = s.replace(/^'([A-Z])/, "$1");
      if (s.includes(";"))
        s = s.split(";")[0].trim();

      let keys = Object.keys(this.BACKTICK_HACEK_MAP);
      for (let i = 0; i < keys.length; i++) {
        if (s.includes(keys[i]))
          s = s.split(keys[i]).join(this.BACKTICK_HACEK_MAP[keys[i]]);
      }
      s = s.replace(/`/g, "");
      s = s.replace(/\s*\([^)]*\)/g, "").trim();

      let inv = s.match(this.ARTICLE_INVERT_RE);
      if (inv) {
        let base = inv[1].trim();
        let art = inv[2].trim();
        let art_low = art.toLowerCase();
        if (art_low === "al" || art_low === "el" || art_low === "as" || art_low === "ash" ||
            art_low === "ar" || art_low === "az" || art_low === "ad" || art_low === "an" || art_low === "at") {
          s = `${art}-${base}`;
        } else if (art_low === "l'") {
          s = `L'${base}`;
        } else {
          s = `${art} ${base}`;
        }
      }

      if (stadester_name_normaliser) {
        let norm_res = stadester_name_normaliser.normaliseCityName(s, country);
        if (norm_res && norm_res.name) s = norm_res.name;
      }

      //Return statement
      return s.replace(/\s+/g, " ").trim();
    },

    /**
     * Checks whether a coordinate `[lng, lat]` lies within a state's `states.json` bbox (with margin)
     * OR matches an explicit country-consistent entry in `state_capitals.json`.
     * @alias city_metadata_partitioner.isValidCapitalBinding
     *
     * @param {number} arg0_lng
     * @param {number} arg1_lat
     * @param {string} arg2_country
     * @param {string|number} arg3_state_id
     * @param {Map<string, Object>} arg4_states_map
     * @param {Object} arg5_state_capitals_obj
     *
     * @returns {boolean}
     */
    isValidCapitalBinding (arg0_lng, arg1_lat, arg2_country, arg3_state_id, arg4_states_map, arg5_state_capitals_obj) {
      //Convert from parameters
      let country_low = String(arg2_country || "").trim().toLowerCase();
      let lat = Number(arg1_lat);
      let lng = Number(arg0_lng);
      let sid_str = String(arg3_state_id);
      let state_capitals = arg5_state_capitals_obj || {};
      let states_map = arg4_states_map;

      //Function body
      let st = states_map ? states_map.get(sid_str) : null;
      if (!st || !Array.isArray(st.bbox) || st.bbox.length < 4)
        return true;

      let [x0, y0, x1, y1] = st.bbox;
      if (lng >= x0 - 3.0 && lng <= x1 + 3.0 && lat >= y0 - 3.0 && lat <= y1 + 3.0)
        return true;

      // Allow genuine exile/headquarters capitals ONLY when state_capitals.json explicitly names this city's country in its key
      let sc = state_capitals[sid_str];
      if (sc && Array.isArray(sc.timeline) && country_low) {
        for (let i = 0; i < sc.timeline.length; i++) {
          let tk = String(sc.timeline[i].key || "").toLowerCase();
          if (tk && (tk.endsWith("-" + country_low) || tk.includes("-" + country_low + "-")))
            return true;
        }
      }

      //Return statement
      return false;
    },

    /**
     * Builds a spatial index of all compiled `stadester_2.0` shard cities so every metadata entry
     * maps deterministically to its canonical regional shard (`01_centaur.json`..`14_nicethi.json`).
     * @alias city_metadata_partitioner.loadRegionalSpatialIndex
     *
     * @param {string} arg0_stadester_dir
     *
     * @returns {Map<string, Array<{ lat: number, lng: number, region_key: string, country: string }>>}
     */
    loadRegionalSpatialIndex (arg0_stadester_dir) {
      //Convert from parameters
      let stadester_dir = arg0_stadester_dir;

      //Declare local instance variables
      let grid = new Map();
      let man_path = path.join(stadester_dir, "stadester_manifest.json");

      //Guard clauses
      if (!fs.existsSync(man_path)) return grid;

      //Function body
      let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
      let regions = Array.isArray(man.regions) ? man.regions : [];
      for (let i = 0; i < regions.length; i++) {
        let rkey = String(regions[i].key || "").toUpperCase();
        let files = Array.isArray(regions[i].files) ? regions[i].files : [];
        for (let x = 0; x < files.length; x++) {
          let fp = path.join(stadester_dir, files[x]);
          if (!fs.existsSync(fp)) continue;
          let obj = JSON.parse(fs.readFileSync(fp, "utf8"));
          let vals = Object.values(obj);
          for (let y = 0; y < vals.length; y++) {
            let c = vals[y];
            if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
            let lat = Number(c.coords[0]);
            let lng = Number(c.coords[1]);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
            let gkey = `${Math.round(lat*4)},${Math.round(lng*4)}`;
            if (!grid.has(gkey)) grid.set(gkey, []);
            grid.get(gkey).push({ country: c.country || "", lat: lat, lng: lng, region_key: rkey });
          }
        }
      }

      //Return statement
      return grid;
    },

    /**
     * Loads `data/atlas/temp/states.json` into a Map keyed by string `state_id`.
     * @alias city_metadata_partitioner.loadStatesMap
     *
     * @param {string} arg0_dataview_root
     *
     * @returns {Map<string, Object>}
     */
    loadStatesMap (arg0_dataview_root) {
      //Convert from parameters
      let states_path = path.join(arg0_dataview_root, "data/atlas/temp/states.json");

      //Declare local instance variables
      let map = new Map();

      //Guard clauses
      if (!fs.existsSync(states_path)) return map;

      //Function body
      try {
        let arr = JSON.parse(fs.readFileSync(states_path, "utf8"));
        if (Array.isArray(arr)) {
          for (let i = 0; i < arr.length; i++) {
            if (arr[i] && arr[i].state_id !== undefined)
              map.set(String(arr[i].state_id), arr[i]);
          }
        }
      } catch (e) {}

      //Return statement
      return map;
    },

    /**
     * Parses CLI arguments for `partition_city_metadata.js`.
     * @alias city_metadata_partitioner.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let out = {
        all: false,
        clean_existing: false,
        dataset: "stadester_2.0",
        dataview_root: "",
        dry_run: false,
        no_backup: false,
        project: "",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--dataview-root=")) out.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--svea-root=")) out.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataset=")) out.dataset = tok.slice(10).trim();
        else if (tok.startsWith("--project=")) out.project = tok.slice(10).trim().toUpperCase();
        else if (tok === "--project" && i + 1 < argv.length) out.project = argv[++i].trim().toUpperCase();
        else if (tok === "--clean-existing") out.clean_existing = true;
        else if (tok === "--all") out.all = true;
        else if (tok === "--dry-run") out.dry_run = true;
        else if (tok === "--no-backup") out.no_backup = true;
      }

      //Return statement
      return out;
    },

    /**
     * Prunes cross-continent / out-of-bbox state IDs from a record's `.capital` map and removes orphaned null transitions.
     * @alias city_metadata_partitioner.pruneInvalidCapitalEntries
     *
     * @param {Object} arg0_rec
     * @param {Map<string, Object>} arg1_states_map
     * @param {Object} arg2_state_capitals
     *
     * @returns {{ kept_sids: number, pruned_sids: number }}
     */
    pruneInvalidCapitalEntries (arg0_rec, arg1_states_map, arg2_state_capitals) {
      //Convert from parameters
      let rec = arg0_rec;
      let state_capitals = arg2_state_capitals || {};
      let states_map = arg1_states_map;

      //Guard clauses
      if (!rec || !rec.capital || typeof rec.capital !== "object")
        return { kept_sids: 0, pruned_sids: 0 };

      //Declare local instance variables
      let coords = Array.isArray(rec.coords) ? rec.coords : [NaN, NaN];
      let lng = Number(coords[0]);
      let lat = Number(coords[1]);
      let dates = Object.keys(rec.capital).sort(function (arg0_a, arg1_b) {
        let ta = city_metadata_merger.dateSortTuple(arg0_a);
        let tb = city_metadata_merger.dateSortTuple(arg1_b);
        if (ta[0] !== tb[0]) return ta[0] - tb[0];
        if (ta[1] !== tb[1]) return ta[1] - tb[1];
        return ta[2] - tb[2];
      });
      let kept_sids = 0;
      let new_cap = {};
      let prev_was_active = false;
      let pruned_sids = 0;

      //Function body
      for (let i = 0; i < dates.length; i++) {
        let d = dates[i];
        let val = rec.capital[d];
        if (val === null || val === undefined) {
          if (prev_was_active) {
            new_cap[d] = null;
            prev_was_active = false;
          }
          continue;
        }
        if (this.isValidCapitalBinding(lng, lat, rec.country || "", val, states_map, state_capitals)) {
          new_cap[d] = val;
          kept_sids++;
          prev_was_active = true;
        } else {
          pruned_sids++;
        }
      }

      if (kept_sids > 0) rec.capital = new_cap;
      else delete rec.capital;

      //Return statement
      return { kept_sids: kept_sids, pruned_sids: pruned_sids };
    },

    /**
     * Resolves a coordinate `[lat, lng]` to its Viscount macro-region key via nearest regional shard city (<= 150 km) or fallback bbox.
     * @alias city_metadata_partitioner.resolveRegionForCoords
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lng
     * @param {Map} arg2_grid
     *
     * @returns {{ country: string, region_key: string }}
     */
    resolveRegionForCoords (arg0_lat, arg1_lng, arg2_grid) {
      //Convert from parameters
      let grid = arg2_grid;
      let lat = Number(arg0_lat);
      let lng = Number(arg1_lng);

      //Function body
      let gx = Math.round(lat*4);
      let gy = Math.round(lng*4);
      let best_d = 999999;
      let best_reg = "";
      let best_country = "";

      let center_b = grid.get(`${gx},${gy}`);
      if (center_b) {
        for (let i = 0; i < center_b.length; i++) {
          let d_sq = (lat - center_b[i].lat)*(lat - center_b[i].lat) + (lng - center_b[i].lng)*(lng - center_b[i].lng);
          if (d_sq < best_d) {
            best_d = d_sq;
            best_reg = center_b[i].region_key;
            best_country = center_b[i].country;
            if (d_sq < 0.0025) return { country: best_country, region_key: best_reg };
          }
        }
        if (best_reg) return { country: best_country, region_key: best_reg };
      }

      for (let dx = -2; dx <= 2; dx++) {
        for (let dy = -2; dy <= 2; dy++) {
          if (dx === 0 && dy === 0) continue;
          let b = grid.get(`${gx + dx},${gy + dy}`);
          if (!b) continue;
          for (let i = 0; i < b.length; i++) {
            let d_sq = (lat - b[i].lat)*(lat - b[i].lat) + (lng - b[i].lng)*(lng - b[i].lng);
            if (d_sq < best_d) {
              best_d = d_sq;
              best_reg = b[i].region_key;
              best_country = b[i].country;
            }
          }
        }
      }
      if (best_reg && best_d <= 2.25)
        return { country: best_country, region_key: best_reg };

      if (lng <= -30) {
        if (lat >= 32.5 || (lat >= 18 && lng <= -150)) return { country: "", region_key: "CENTAUR" };
        if (lat >= 7.0) return { country: "", region_key: "JAGUAR" };
        if (lng <= -68.0 || lat <= -34.0) return { country: "", region_key: "QUIPU" };
        return { country: "", region_key: "PRETA" };
      }
      if (lng >= 110 && lat <= 0) return { country: "", region_key: "AUSTRAL" };
      if (lat <= 20 && lng >= -25 && lng <= 55) return { country: "", region_key: "NICETHI" };
      if (lat >= 35 && lng >= -25 && lng <= 28) return { country: "", region_key: "MAGNETIC" };
      if (lat >= 44 && lng > 28 && lng <= 180) return { country: "", region_key: "POLARIS" };

      //Return statement
      return { country: "", region_key: "UNASSIGNED" };
    },

    /**
     * Remediates existing partitioned `stadester_2.0/city_metadata/` shards in place whilst preserving
     * 100% current Dataview JSON compatibility:
     * - Strips all case-insensitive duplicate `.other_names` and `.name`/`.historical_names` exact repeats.
     * - Prunes cross-continent capital misbindings failing `states.json` spatial bbox checks and demotes non-capitals.
     * - Merges same-municipality split capital collisions (`<= 3,0 km` sharing stem/alias/state_id or sub-district).
     * - Restores capital city canonical names when overridden by intra-municipal sub-districts (`Cairo`/`Al-Dawâwîn`,
     *   `Paris 05 Panthéon`, `Istanbul`/`Kepos`, etc.) and simplifies full timelines chronologically at `[lng, lat]`.
     * @alias city_metadata_partitioner.runCleanExisting
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runCleanExisting (arg0_options) {
      //Convert from parameters
      let opts = (arg0_options) ? arg0_options : {};
      let dataset_id = String(opts.dataset || "stadester_2.0").replace(/\.json$/i, "");
      let svea_root = opts.svea_root ? path.resolve(opts.svea_root) : (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = opts.dataview_root ? path.resolve(opts.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));

      //Declare local instance variables
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let part_dir = path.join(stadester_dir, "city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let capitals_path = path.join(dataview_root, "data/stadester/state_capitals.json");
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let mun_rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
      let overlay_policy = (profiles && profiles.overlay_binding_policy) ? profiles.overlay_binding_policy : {};
      let cap_merge_km = Number(overlay_policy.capital_split_merge_radius_km) || 3.0;
      let mun_regexes = (Array.isArray(mun_rules.intra_municipal_suffix_regexes) ? mun_rules.intra_municipal_suffix_regexes : []).map(function (arg0_r) {
        return new RegExp(arg0_r, "i");
      });

      //Guard clauses
      if (!fs.existsSync(man_path)) {
        console.error(`[partition_city_metadata] Partitioned manifest not found: ${man_path}`);
        return { success: false };
      }

      //Function body
      let manifest = JSON.parse(fs.readFileSync(man_path, "utf8"));
      let states_map = this.loadStatesMap(dataview_root);
      let state_capitals = fs.existsSync(capitals_path) ? JSON.parse(fs.readFileSync(capitals_path, "utf8")) : {};
      let reg_grid = this.loadRegionalSpatialIndex(stadester_dir);

      // Build sid -> authoritative capital city names from state_capitals.json for Structural Rule #3 restoration
      let sid_to_cap_names = new Map();
      if (state_capitals && typeof state_capitals === "object") {
        let sids = Object.keys(state_capitals);
        for (let i = 0; i < sids.length; i++) {
          let sc = state_capitals[sids[i]];
          if (!sc || sc.acapital || !Array.isArray(sc.timeline)) continue;
          let names = [];
          for (let t = 0; t < sc.timeline.length; t++) {
            let cn = this.cleanLegacyName(sc.timeline[t].city || "");
            if (cn && !names.includes(cn)) names.push(cn);
          }
          if (names.length > 0) sid_to_cap_names.set(sids[i], names);
        }
      }

      let shards = Array.isArray(manifest.shards) ? manifest.shards : [];
      let shard_map = new Map();
      for (let i = 0; i < shards.length; i++) {
        let sp = path.join(part_dir, shards[i].file);
        shard_map.set(shards[i].file, fs.existsSync(sp) ? JSON.parse(fs.readFileSync(sp, "utf8")) : []);
      }

      let stats = {
        aliases_deduped: 0,
        capitals_demoted_out_of_bbox: 0,
        capitals_name_restored: 0,
        capitals_split_merged: 0,
        history_simplified: 0,
        invalid_capital_links_pruned: 0,
        subdistrict_entries_stripped: 0
      };

      // Step 1: Validate & clean `00_capitals.json` first (bbox check, sub-district restoration, split-capital consolidation)
      let raw_caps = shard_map.get("00_capitals.json") || [];
      let surviving_caps = [];
      let demoted_to_region = [];

      for (let i = 0; i < raw_caps.length; i++) {
        let rec = raw_caps[i];
        if (!rec || !Array.isArray(rec.coords) || rec.coords.length < 2) continue;

        let prune_res = this.pruneInvalidCapitalEntries(rec, states_map, state_capitals);
        stats.invalid_capital_links_pruned += prune_res.pruned_sids;

        if (prune_res.kept_sids === 0 && !(Array.isArray(rec.capital_records) && rec.capital_records.length > 0)) {
          demoted_to_region.push(rec);
          stats.capitals_demoted_out_of_bbox++;
          continue;
        }
        surviving_caps.push(rec);
      }

      // Collapse same-municipality split capitals in 00_capitals.json (e.g. Constantinople + Kepos, Arolsen + Bad Arolsen)
      let merged_caps = [];
      let cap_grid = new Map();
      let getCapSidSet = function (arg0_r) {
        let set = new Set();
        if (arg0_r && arg0_r.capital && typeof arg0_r.capital === "object") {
          let vals = Object.values(arg0_r.capital);
          for (let v = 0; v < vals.length; v++) {
            if (vals[v] !== null && vals[v] !== undefined) set.add(String(vals[v]));
          }
        }
        return set;
      };
      let getAllStems = function (arg0_r) {
        let set = new Set();
        let strs = [arg0_r.name];
        if (Array.isArray(arg0_r.other_names)) strs = strs.concat(arg0_r.other_names);
        if (Array.isArray(arg0_r.historical_names)) {
          for (let h = 0; h < arg0_r.historical_names.length; h++)
            if (arg0_r.historical_names[h] && arg0_r.historical_names[h].name) strs.push(arg0_r.historical_names[h].name);
        }
        for (let s = 0; s < strs.length; s++) {
          let st = viscount_entity_audit.normaliseEntityStem(strs[s]);
          if (st && st.length >= 3) set.add(st);
        }
        return set;
      };

      // Sort richer / more authoritative capitals first so split fragments merge into the primary capital
      surviving_caps.sort(function (arg0_a, arg1_b) {
        let ca = arg0_a.capital ? Object.keys(arg0_a.capital).length : 0;
        let cb = arg1_b.capital ? Object.keys(arg1_b.capital).length : 0;
        if (ca !== cb) return cb - ca;
        let ha = Array.isArray(arg0_a.historical_names) ? arg0_a.historical_names.length : 0;
        let hb = Array.isArray(arg1_b.historical_names) ? arg1_b.historical_names.length : 0;
        return hb - ha;
      });

      for (let i = 0; i < surviving_caps.length; i++) {
        let rec = surviving_caps[i];
        let lng = Number(rec.coords[0]);
        let lat = Number(rec.coords[1]);
        let gx = Math.round(lat*10);
        let gy = Math.round(lng*10);
        let rec_sids = getCapSidSet(rec);
        let rec_stems = getAllStems(rec);
        let rec_name_stem = viscount_entity_audit.normaliseEntityStem(rec.name);
        let rec_is_sub = mun_regexes.some(function (arg0_r) { return arg0_r.test(String(rec.name || "")); }) ||
          /^unfinished\s+obelisk$/i.test(String(rec.name || ""));

        let merge_target = null;
        for (let dx = -1; dx <= 1 && !merge_target; dx++) {
          for (let dy = -1; dy <= 1 && !merge_target; dy++) {
            let bucket = cap_grid.get(`${gx + dx},${gy + dy}`);
            if (!bucket) continue;
            for (let b = 0; b < bucket.length; b++) {
              let cand = bucket[b];
              let d_km = viscount_audit_utils.haversineKm(lat, lng, cand.lat, cand.lng);
              if (d_km > cap_merge_km) continue;

              let shares_sid = false;
              rec_sids.forEach(function (arg0_sid) {
                if (cand.sids.has(arg0_sid)) shares_sid = true;
              });
              let shares_stem = Boolean(
                (rec_name_stem && cand.stems.has(rec_name_stem)) ||
                (cand.name_stem && rec_stems.has(cand.name_stem)) ||
                viscount_entity_audit.areEquivalentExonyms(rec.name || "", cand.rec.name || "", profiles)
              );
              if (!shares_stem) {
                rec_stems.forEach(function (arg0_st) {
                  if (arg0_st && arg0_st.length >= 3 && cand.stems.has(arg0_st)) shares_stem = true;
                });
              }

              // Structural Rule for Merging #1: merge ONLY same-municipality splits (exact coord <= 0.35 km, shared capital state_id, shared stem/alias, or intra-municipal sub-district) — NEVER distinct neighbouring municipalities!
              if (d_km <= 0.35 || shares_sid || shares_stem || rec_is_sub) {
                merge_target = cand;
                break;
              }
            }
          }
        }

        if (merge_target) {
          stats.capitals_split_merged++;
          let tgt = merge_target.rec;
          // Union capital intervals cleanly
          if (rec.capital && typeof rec.capital === "object") {
            if (!tgt.capital) tgt.capital = {};
            let ckeys = Object.keys(rec.capital);
            for (let c = 0; c < ckeys.length; c++) {
              if (tgt.capital[ckeys[c]] === undefined || (tgt.capital[ckeys[c]] === null && rec.capital[ckeys[c]] !== null))
                tgt.capital[ckeys[c]] = rec.capital[ckeys[c]];
            }
            rec_sids.forEach(function (arg0_s) { merge_target.sids.add(arg0_s); });
          }
          if (!rec_is_sub && !/-l[eè]s-|\b\d{2}\b|weststadt|oststadt|nordstadt|südstadt|meckenbeuren|delicias/i.test(String(rec.name || ""))) {
            let merged_hist = city_metadata_merger.simplifyHistoryAtCoord(
              tgt.historical_names,
              rec.historical_names,
              { existing_is_capital: true, incoming_is_auditor_verified: false, incoming_is_pass2: false, mun_regexes: mun_regexes }
            );
            if (merged_hist.length > 0) tgt.historical_names = merged_hist;
          }
          let extra = [rec.name].concat(Array.isArray(rec.other_names) ? rec.other_names : []);
          tgt.other_names = (Array.isArray(tgt.other_names) ? tgt.other_names : []).concat(extra);
          rec_stems.forEach(function (arg0_st) { merge_target.stems.add(arg0_st); });
          continue;
        }

        let wrap = { lat: lat, lng: lng, name_stem: rec_name_stem, rec: rec, sids: rec_sids, stems: rec_stems };
        merged_caps.push(rec);
        let gk = `${gx},${gy}`;
        if (!cap_grid.has(gk)) cap_grid.set(gk, []);
        cap_grid.get(gk).push(wrap);
      }

      // Restore capital canonical names when overridden by sub-districts/quarters (Structural Rule #3)
      for (let i = 0; i < merged_caps.length; i++) {
        let rec = merged_caps[i];
        let sids = getCapSidSet(rec);
        let auth_cap_names = [];
        sids.forEach(function (arg0_sid) {
          let list = sid_to_cap_names.get(arg0_sid);
          if (list) {
            for (let x = 0; x < list.length; x++) {
              if (!auth_cap_names.includes(list[x])) auth_cap_names.push(list[x]);
            }
          }
        });

        let cur_stem = viscount_entity_audit.normaliseEntityStem(rec.name || "");
        let matches_any_auth = auth_cap_names.some(function (arg0_an) {
          return viscount_entity_audit.normaliseEntityStem(arg0_an) === cur_stem ||
            viscount_entity_audit.areEquivalentExonyms(rec.name || "", arg0_an, profiles);
        });

        if (!matches_any_auth && auth_cap_names.length > 0) {
          // Check if one of the authoritative capital names appears in other_names (proving override e.g. Al-Dawâwîn overriding Cairo!)
          let other_arr = Array.isArray(rec.other_names) ? rec.other_names : [];
          let matched_auth = "";
          for (let a_i = 0; a_i < auth_cap_names.length && !matched_auth; a_i++) {
            let an = auth_cap_names[a_i];
            let an_stem = viscount_entity_audit.normaliseEntityStem(an);
            for (let o_i = 0; o_i < other_arr.length; o_i++) {
              if (viscount_entity_audit.normaliseEntityStem(other_arr[o_i]) === an_stem ||
                  viscount_entity_audit.areEquivalentExonyms(other_arr[o_i], an, profiles)) {
                matched_auth = an;
                break;
              }
            }
          }
          if (matched_auth) {
            let old_name = rec.name;
            rec.name = matched_auth;
            if (!Array.isArray(rec.other_names)) rec.other_names = [];
            if (old_name) rec.other_names.push(old_name);
            // Replace single-entry sub-district historical_names with the restored capital name
            if (Array.isArray(rec.historical_names) && rec.historical_names.length === 1 &&
                viscount_entity_audit.normaliseEntityStem(rec.historical_names[0].name) === cur_stem) {
              rec.historical_names[0].name = matched_auth;
            }
            stats.capitals_name_restored++;
          }
        }
      }

      // Specific verified capital timeline restorations where prior destructive merges wiped centuries of history
      for (let i = 0; i < merged_caps.length; i++) {
        let rec = merged_caps[i];
        let lng = Number(rec.coords[0]);
        let lat = Number(rec.coords[1]);
        // Istanbul / Constantinople (merged Constantinople + Kepos)
        if (Math.abs(lat - 41.01) < 0.05 && Math.abs(lng - 28.97) < 0.06) {
          rec.name = "Istanbul";
          rec.country = "Turkey";
          rec.historical_names = [
            { date: "-657.1.1", name: "Byzantium" },
            { date: "330.5.11", name: "Constantinople" },
            { date: "1930.3.28", name: "Istanbul" }
          ];
          stats.capitals_name_restored++;
        }
        // Cairo (restored from Al-Dawâwîn sub-district overwrite)
        if (Math.abs(lat - 30.044) < 0.05 && Math.abs(lng - 31.236) < 0.05 && String(rec.country || "").toLowerCase() === "egypt") {
          rec.name = "Cairo";
          rec.historical_names = [
            { date: "641.1.1", name: "Fustat" },
            { date: "969.7.6", name: "Cairo" }
          ];
          stats.capitals_name_restored++;
        }
        // Kyiv (align modern canonical name with 1991.8.24 Ukraine entry)
        if (Math.abs(lat - 50.45) < 0.05 && Math.abs(lng - 30.52) < 0.05 && String(rec.country || "").toLowerCase() === "ukraine") {
          rec.name = "Kyiv";
          rec.historical_names = [
            { date: "482.1.1", name: "Kyiv" },
            { date: "1569.1.1", name: "Kijow" },
            { date: "1654.1.1", name: "Kiev" },
            { date: "1991.8.24", name: "Kyiv" }
          ];
          stats.capitals_name_restored++;
        }
        // Paris (preserve city-centre coordinates [2.35138, 48.85755])
        if (Math.abs(lat - 48.85) < 0.06 && Math.abs(lng - 2.34) < 0.06 && String(rec.country || "").toLowerCase() === "france" && /^(?:paris|lutetia|lucotetia)$/i.test(String(rec.name || ""))) {
          rec.coords = [2.35138, 48.85755];
        }
        // Baghdad / Ctesiphon separation (SC-04)
        if (Math.abs(lat - 33.315) < 0.08 && Math.abs(lng - 44.366) < 0.08 && String(rec.country || "").toLowerCase() === "iraq") {
          rec.name = "Baghdad";
          rec.historical_names = [
            { date: "762.7.30", name: "Baghdad" }
          ];
          stats.capitals_name_restored++;
        }
        // Ctesiphon / Salman Pak at [44.5808, 33.1003]
        if (Math.abs(lat - 33.10) < 0.06 && Math.abs(lng - 44.58) < 0.06 && String(rec.country || "").toLowerCase() === "iraq") {
          rec.name = "Salman Pak";
          rec.historical_names = [
            { date: "-140.1.1", name: "Ctesiphon" },
            { date: "637.1.1", name: "Al-Mada'in" },
            { date: "1700.1.1", name: "Salman Pak" }
          ];
          stats.capitals_name_restored++;
        }
        // Tikrīt (sunset Birtha at 637 AD)
        if (Math.abs(lat - 34.60) < 0.06 && Math.abs(lng - 43.68) < 0.06 && String(rec.country || "").toLowerCase() === "iraq") {
          rec.name = "Tikrīt";
          rec.historical_names = [
            { date: "-600.1.1", name: "Birtha" },
            { date: "637.1.1", name: "Tikrīt" }
          ];
          stats.capitals_name_restored++;
        }
        // Patna / Pataliputra
        if (Math.abs(lat - 25.60) < 0.06 && Math.abs(lng - 85.13) < 0.06 && String(rec.country || "").toLowerCase() === "india") {
          rec.name = "Patna";
          rec.historical_names = [
            { date: "-490.1.1", name: "Pataliputra" },
            { date: "1541.1.1", name: "Patna" }
          ];
          stats.capitals_name_restored++;
        }
      }

      shard_map.set("00_capitals.json", merged_caps);

      // Repair known corrupted capital timelines in 00_capitals.json
      let capital_fixes = {
        "adana": { strip_names: ["Seyhan"] },
        "aquincum": { canonical: "Budapest", hist: [{ date: "100.1.1", name: "Aquincum" }, { date: "1241.1.1", name: "Buda" }, { date: "1873.11.17", name: "Budapest" }] },
        "athens": { strip_names: ["Gazi", "Agora. Athens"] },
        "hamburg": { strip_names: ["Neustadt"] },
        "izmir": { strip_names: ["Agora"] },
        "lyon": { strip_names: ["Sainte-Foy-lès-Lyon", "Lyon 03"] },
        "metz": { strip_names: ["Montigny-lès-Metz"] },
        "naples": { canonical: "Napoli", coords: [14.26812, 40.85177], strip_names: ["Casalnuovo di Napoli"] },
        "napoli": { canonical: "Napoli", coords: [14.26812, 40.85177], strip_names: ["Casalnuovo di Napoli"] },
        "rouen": { strip_names: ["Sotteville-lès-Rouen"] },
        "schwerin": { strip_names: ["Weststadt", "Meckenbeuren"] },
        "valletta": { coords: [14.5141, 35.89924], hist: [{ date: "1566.3.28", name: "Valletta" }] },
        "zaragoza": { strip_names: ["Delicias"] }
      };
      for (let i = 0; i < merged_caps.length; i++) {
        let cap_r = merged_caps[i];
        let fold_c = stadester_name_normaliser ? stadester_name_normaliser.foldAscii(cap_r.name) : String(cap_r.name || "").toLowerCase();
        let fix = capital_fixes[fold_c];
        if (!fix) continue;
        if (fix.canonical) cap_r.name = fix.canonical;
        if (Array.isArray(fix.coords)) cap_r.coords = fix.coords.slice();
        if (Array.isArray(fix.hist)) {
          cap_r.historical_names = fix.hist.slice();
          stats.capitals_name_restored++;
        } else if (Array.isArray(fix.strip_names) && Array.isArray(cap_r.historical_names)) {
          let strip_set = new Set(fix.strip_names.map(function (arg0_s) { return arg0_s.toLowerCase(); }));
          let filtered_h = cap_r.historical_names.filter(function (arg0_h) {
            return arg0_h && !strip_set.has(String(arg0_h.name || "").toLowerCase());
          });
          if (filtered_h.length > 0 && filtered_h.length !== cap_r.historical_names.length) {
            cap_r.historical_names = filtered_h;
            stats.capitals_name_restored++;
          }
        }
      }

      // Re-route demoted out-of-bbox records back to their proper regional shard
      let region_file_by_key = new Map();
      for (let i = 0; i < this.REGION_SHARD_FILES.length; i++)
        region_file_by_key.set(this.REGION_SHARD_FILES[i].key, this.REGION_SHARD_FILES[i].file);
      region_file_by_key.set("UNASSIGNED", "15_unassigned.json");

      for (let i = 0; i < demoted_to_region.length; i++) {
        let rec = demoted_to_region[i];
        let rk = rec.region_shard && region_file_by_key.has(rec.region_shard) ? rec.region_shard :
          this.resolveRegionForCoords(Number(rec.coords[1]), Number(rec.coords[0]), reg_grid).region_key;
        rec.region_shard = rk;
        let dest_f = region_file_by_key.get(rk) || "15_unassigned.json";
        if (!shard_map.has(dest_f)) shard_map.set(dest_f, []);
        shard_map.get(dest_f).push(rec);
      }

      // Deterministic Latinisation helper for raw non-Latin canonical names (Cyrillic/Hangul/Greek/bilingual Arabic)
      let non_latin_re = /(?:[\u0370-\u03B7\u03B9-\u03FF]|[\u0370-\u03FF]{2,}|[\u0400-\u052F\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\u0900-\u0DFF\u0E00-\u10FF\u1200-\u137F\u1780-\u17FF\u3040-\u30FF\u3400-\u4DBF\u4E00-\u9FFF\uAC00-\uD7AF])/;
      let cyr_map = {
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "Yo", "Ж": "Zh", "З": "Z",
        "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R",
        "С": "S", "Т": "T", "У": "U", "Ф": "F", "Х": "Kh", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Shch",
        "Ъ": "", "Ы": "Y", "Ь": "", "Э": "E", "Ю": "Yu", "Я": "Ya", "І": "I", "Ї": "Yi", "Є": "Ye", "Ґ": "G", "Ў": "U",
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z",
        "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r",
        "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya", "і": "i", "ї": "yi", "є": "ye", "ґ": "g", "ў": "u"
      };
      let hangul_lead = ["g", "kk", "n", "d", "tt", "r", "m", "b", "pp", "s", "ss", "", "j", "jj", "ch", "k", "t", "p", "h"];
      let hangul_vowel = ["a", "ae", "ya", "yae", "eo", "e", "yeo", "ye", "o", "wa", "wae", "oe", "yo", "u", "wo", "we", "wi", "yu", "eu", "ui", "i"];
      let hangul_tail = ["", "k", "k", "k", "n", "n", "n", "t", "l", "l", "l", "l", "l", "l", "l", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"];
      let toCleanLatin = function (arg0_str) {
        let s = String(arg0_str || "").trim();
        if (!s || !non_latin_re.test(s)) return s;
        // Strip stray Arabic/Hebrew vowel marks attached to Latin words (e.g. `ِAlbosor`)
        let stripped_marks = s.replace(/[\u064B-\u065F\u0670\u06D6-\u06ED]/g, "").trim();
        if (stripped_marks && !non_latin_re.test(stripped_marks)) return stripped_marks;
        // Extract trailing/embedded Latin name from bilingual strings (e.g. `زوکت Zukot`, `اورگونت پائین Ūrgūnt-e Pāyān`)
        let latin_runs = stripped_marks.match(/[A-Za-z\u00C0-\u024F\u1E00-\u1EFF][A-Za-z0-9\u00C0-\u024F\u1E00-\u1EFF'\-\s]{1,}/g);
        if (latin_runs && latin_runs.length > 0) {
          let best_lat = latin_runs.sort(function (arg0_a, arg1_b) { return arg1_b.trim().length - arg0_a.trim().length; })[0].trim();
          if (best_lat.length >= 2 && !non_latin_re.test(best_lat)) return best_lat;
        }
        // Cyrillic transliteration
        if (/[\u0400-\u052F]/.test(s)) {
          if (/^(?:АЗС|АГЗС)$/i.test(s) || /(?:микрорайон|район)$/i.test(s)) return "";
          let out_c = "";
          for (let c_i = 0; c_i < s.length; c_i++) out_c += (cyr_map[s[c_i]] !== undefined ? cyr_map[s[c_i]] : s[c_i]);
          out_c = out_c.replace(/\s+/g, " ").trim();
          if (out_c && !non_latin_re.test(out_c)) return out_c;
        }
        // Korean Hangul deterministic Revised Romanization
        if (/[\uAC00-\uD7AF]/.test(s)) {
          let out_h = "";
          for (let h_i = 0; h_i < s.length; h_i++) {
            let cp = s.charCodeAt(h_i);
            if (cp >= 0xAC00 && cp <= 0xD7A3) {
              let idx = cp - 0xAC00;
              let l = Math.floor(idx/588);
              let v = Math.floor((idx%588)/28);
              let t = idx%28;
              out_h += hangul_lead[l] + hangul_vowel[v] + hangul_tail[t];
            } else {
              out_h += s[h_i];
            }
          }
          out_h = out_h.replace(/\s+/g, " ").trim();
          if (out_h && !non_latin_re.test(out_h))
            return out_h.charAt(0).toUpperCase() + out_h.slice(1);
        }
        return "";
      };

      // Step 2: Clean EVERY target shard — Latinise/drop non-Latin stubs, strip intra-municipal intrusions,
      // deduplicate <= 1,5 km collisions across shards (Tier-0 capitals first), simplify timelines, deduplicate .other_names CI
      let target_files = [];
      for (let i = 0; i < shards.length; i++) {
        let sh = shards[i];
        let is_cap = sh.key === "CAPITALS" || sh.file === "00_capitals.json";
        if (opts.all || !opts.project || is_cap || sh.key === opts.project)
          target_files.push(sh.file);
      }
      // Guarantee `00_capitals.json` is processed first so regional duplicates merge into their Tier-0 capital
      target_files.sort(function (arg0_a, arg1_b) {
        if (arg0_a === "00_capitals.json") return -1;
        if (arg1_b === "00_capitals.json") return 1;
        return arg0_a.localeCompare(arg1_b);
      });

      let global_col_grid = new Map();
      let dirty_cap_from_regional = false;
      stats.collisions_merged = 0;
      stats.non_latin_remediated = 0;

      for (let f_i = 0; f_i < target_files.length; f_i++) {
        let sf = target_files[f_i];
        let arr = shard_map.get(sf) || [];
        let is_cap_shard = sf === "00_capitals.json";
        let kept_arr = [];

        for (let i = 0; i < arr.length; i++) {
          let rec = arr[i];
          if (!rec || typeof rec !== "object") continue;

          // Clean name & deterministic Latinisation of canonical name
          let orig_raw_name = String(rec.name || "").trim();
          if ((stadester_name_normaliser && stadester_name_normaliser.isJunkOrSurveyCode(orig_raw_name)) ||
              city_metadata_merger.isCorruptedCityName(orig_raw_name)) {
            stats.subdistrict_entries_stripped++;
            continue;
          }
          let extra_native_aliases = [];
          if (orig_raw_name.includes(";")) {
            let semi_parts = orig_raw_name.split(";");
            for (let sp_i = 1; sp_i < semi_parts.length; sp_i++) {
              let sp_tok = semi_parts[sp_i].trim();
              if (sp_tok && !/^\d+[A-Za-z]?$/.test(sp_tok)) extra_native_aliases.push(sp_tok);
            }
          }
          if (rec.name) rec.name = this.cleanLegacyName(rec.name, rec.country || "");
          if (!rec.name || city_metadata_merger.isCorruptedCityName(rec.name)) {
            stats.subdistrict_entries_stripped++;
            continue;
          }
          if (!is_cap_shard && !rec.capital && !rec.verified_settlement && rec.name &&
              mun_regexes.some(function (arg0_r) { return arg0_r.test(rec.name); })) {
            stats.subdistrict_entries_stripped++;
            continue;
          }
          if (rec.name && non_latin_re.test(rec.name)) {
            let lat_nm = toCleanLatin(rec.name);
            if (!lat_nm && Array.isArray(rec.historical_names)) {
              for (let h_k = rec.historical_names.length - 1; h_k >= 0; h_k--) {
                let cand_hn = this.cleanLegacyName(rec.historical_names[h_k] ? rec.historical_names[h_k].name : "");
                if (cand_hn && !non_latin_re.test(cand_hn)) { lat_nm = cand_hn; break; }
              }
            }
            if (!lat_nm && Array.isArray(rec.other_names)) {
              for (let o_k = 0; o_k < rec.other_names.length; o_k++) {
                let cand_on = this.cleanLegacyName(rec.other_names[o_k]);
                if (cand_on && !non_latin_re.test(cand_on)) { lat_nm = cand_on; break; }
              }
            }
            if (!lat_nm) {
              stats.non_latin_remediated++;
              continue; // Drop untransliterated non-Latin OSM/GHSL stub so Pass 2 WHG/GeoHack can resolve it cleanly
            }
            extra_native_aliases.push(orig_raw_name);
            rec.name = lat_nm;
            stats.non_latin_remediated++;
          }

          let raw_hist = Array.isArray(rec.historical_names) ? rec.historical_names : [];
          let dropped_vars = [];
          let cleaned_hist = [];
          for (let h = 0; h < raw_hist.length; h++) {
            let item = raw_hist[h];
            if (!item || typeof item !== "object") continue;
            let hn = this.cleanLegacyName(item.name || "", rec.country || "");
            let hd = String(item.date || "").trim();
            if (!hn || !viscount_entity_audit.isValidCalendarDate(hd)) continue;
            if (non_latin_re.test(hn)) {
              let lat_hn = toCleanLatin(hn);
              if (lat_hn) {
                extra_native_aliases.push(hn);
                hn = lat_hn;
                stats.non_latin_remediated++;
              } else {
                extra_native_aliases.push(hn);
                stats.non_latin_remediated++;
                continue;
              }
            }
            if (mun_regexes.some(function (arg0_r) { return arg0_r.test(hn); })) {
              stats.subdistrict_entries_stripped++;
              continue;
            }
            cleaned_hist.push({ date: hd, name: hn });
          }

          if (cleaned_hist.length > 0) {
            let simplified = city_metadata_merger.sortAndDedupHistoricalNames(cleaned_hist, dropped_vars);
            if (simplified.length !== raw_hist.length) stats.history_simplified++;
            rec.historical_names = simplified;
          } else if (rec.name) {
            rec.historical_names = [{ date: "1900.1.1", name: rec.name }];
          }

          let prev_other_len = Array.isArray(rec.other_names) ? rec.other_names.length : 0;
          let cleaned_existing_others = [];
          if (Array.isArray(rec.other_names)) {
            for (let oi = 0; oi < rec.other_names.length; oi++) {
              let co = this.cleanLegacyName(rec.other_names[oi], rec.country || "");
              if (co) cleaned_existing_others.push(co);
            }
          }
          let raw_aliases = cleaned_existing_others.concat(dropped_vars).concat(extra_native_aliases);
          let dedup_other = city_metadata_merger.deduplicateOtherNamesCI(
            rec.name,
            rec.historical_names,
            raw_aliases,
            rec.country || "",
            Array.isArray(rec.coords) ? [Number(rec.coords[1]), Number(rec.coords[0])] : []
          );

          if (dedup_other.length < prev_other_len)
            stats.aliases_deduped += (prev_other_len - dedup_other.length);

          if (dedup_other.length > 0) rec.other_names = dedup_other;
          else delete rec.other_names;

          if (!is_cap_shard && rec.capital && Object.keys(rec.capital).length === 0)
            delete rec.capital;

          // Global spatial collision check (<= 0,15 km exact duplicate or <= 1,5 km same-stem)
          let coords = Array.isArray(rec.coords) ? rec.coords : [];
          let lng = Number(coords[0]);
          let lat = Number(coords[1]);
          let stem = viscount_entity_audit.normaliseEntityStem(rec.name || "");
          let collided_with = null;
          if (Number.isFinite(lat) && Number.isFinite(lng)) {
            let gx = Math.round(lat*20);
            let gy = Math.round(lng*20);
            for (let dx = -1; dx <= 1 && !collided_with; dx++) {
              for (let dy = -1; dy <= 1 && !collided_with; dy++) {
                let cb = global_col_grid.get(`${gx + dx},${gy + dy}`);
                if (!cb) continue;
                for (let z = 0; z < cb.length; z++) {
                  let d_km = viscount_audit_utils.haversineKm(lat, lng, cb[z].lat, cb[z].lng);
                  if (d_km <= 0.15 || (d_km <= 2.5 && ((stem && cb[z].stem === stem) || viscount_entity_audit.areEquivalentExonyms(rec.name, cb[z].rec.name, profiles)))) {
                    collided_with = cb[z];
                    break;
                  }
                }
              }
            }

            if (collided_with) {
              stats.collisions_merged++;
              let tgt = collided_with.rec;
              let allow_hist_merge = !(collided_with.is_cap_shard && !is_cap_shard) &&
                !/-l[eè]s-|\b\d{2}\b|weststadt|oststadt|nordstadt|südstadt|meckenbeuren|delicias/i.test(String(rec.name || ""));
              if (allow_hist_merge) {
                let merged_h = city_metadata_merger.simplifyHistoryAtCoord(
                  tgt.historical_names,
                  rec.historical_names,
                  { existing_is_capital: collided_with.is_cap_shard, incoming_is_auditor_verified: false, incoming_is_pass2: false, mun_regexes: mun_regexes }
                );
                if (merged_h.length > 0) tgt.historical_names = merged_h;
              }
              let merged_aliases = (Array.isArray(tgt.other_names) ? tgt.other_names : [])
                .concat([rec.name])
                .concat(Array.isArray(rec.other_names) ? rec.other_names : []);
              let dedup_tgt = city_metadata_merger.deduplicateOtherNamesCI(
                tgt.name,
                tgt.historical_names,
                merged_aliases,
                tgt.country || "",
                Array.isArray(tgt.coords) ? [Number(tgt.coords[1]), Number(tgt.coords[0])] : []
              );
              if (dedup_tgt.length > 0) tgt.other_names = dedup_tgt;
              else delete tgt.other_names;
              if (collided_with.is_cap_shard && !is_cap_shard) dirty_cap_from_regional = true;
              continue;
            }

            let gk = `${gx},${gy}`;
            if (!global_col_grid.has(gk)) global_col_grid.set(gk, []);
            global_col_grid.get(gk).push({ is_cap_shard: is_cap_shard, lat: lat, lng: lng, rec: rec, stem: stem });
          }

          kept_arr.push(rec);
        }

        shard_map.set(sf, kept_arr);
      }

      if (dirty_cap_from_regional && !target_files.includes("00_capitals.json"))
        target_files.unshift("00_capitals.json");

      // Step 3: Canonical `stadester_2.0` Key & Coordinate Alignment Pass (SC-08)
      // Guarantees 100% deterministic key binding in Dataview's stadester_metadata.ts without touching protected TS files
      let st_grid = new Map();
      let st_files = fs.existsSync(stadester_dir) ? fs.readdirSync(stadester_dir).filter(function (arg0_f) {
        return arg0_f.endsWith(".json") && !arg0_f.includes("manifest") && !arg0_f.includes("city_metadata");
      }) : [];
      for (let sf_i = 0; sf_i < st_files.length; sf_i++) {
        let st_obj = JSON.parse(fs.readFileSync(path.join(stadester_dir, st_files[sf_i]), "utf8"));
        let st_keys = Object.keys(st_obj);
        for (let sk_i = 0; sk_i < st_keys.length; sk_i++) {
          let sk = st_keys[sk_i];
          let sc = st_obj[sk];
          if (!sc || !Array.isArray(sc.coords) || sc.coords.length < 2) continue;
          let s_lat = Number(sc.coords[0]);
          let s_lng = Number(sc.coords[1]);
          if (!Number.isFinite(s_lat) || !Number.isFinite(s_lng)) continue;
          let max_p = 0;
          if (sc.population && typeof sc.population === "object") {
            let pvals = Object.values(sc.population);
            for (let pv_i = 0; pv_i < pvals.length; pv_i++) {
              let pv = Number(pvals[pv_i] || 0);
              if (pv > max_p) max_p = pv;
            }
          }
          let s_stems = new Set();
          let add_s = function (arg0_n) {
            let ns = viscount_entity_audit.normaliseEntityStem(arg0_n || "");
            if (ns && ns.length >= 2) s_stems.add(ns);
          };
          add_s(sc.name);
          if (Array.isArray(sc.other_names)) {
            for (let on_i = 0; on_i < sc.other_names.length; on_i++) add_s(sc.other_names[on_i]);
          }
          let is_agg = Boolean(sc.is_agglomeration || sc.population_scope === "metro" || /\(agglomeration\??\)|\(metro\)/i.test(String(sc.name || sk || "")));
          let sgx = Math.round(s_lat*4);
          let sgy = Math.round(s_lng*4);
          let sgk = `${sgx},${sgy}`;
          if (!st_grid.has(sgk)) st_grid.set(sgk, []);
          st_grid.get(sgk).push({
            country: String(sc.country || ""),
            is_agg: is_agg,
            is_capital: Boolean(sc.is_capital),
            key: sc.key || sk,
            lat: s_lat,
            lng: s_lng,
            max_pop: max_p,
            name: String(sc.name || ""),
            stems: s_stems
          });
        }
      }

      if (st_grid.size > 0) {
        let claimed_st_keys = new Map();
        for (let f_i = 0; f_i < target_files.length; f_i++) {
          let sf = target_files[f_i];
          let is_cap_shard = sf === "00_capitals.json";
          let arr = shard_map.get(sf) || [];
          let aligned_arr = [];

          for (let i = 0; i < arr.length; i++) {
            let rec = arr[i];
            if (!rec || !Array.isArray(rec.coords) || rec.coords.length < 2) {
              aligned_arr.push(rec);
              continue;
            }
            let r_lng = Number(rec.coords[0]);
            let r_lat = Number(rec.coords[1]);
            let r_stems = new Set();
            let r_main_stem = viscount_entity_audit.normaliseEntityStem(rec.name || "");
            if (r_main_stem) r_stems.add(r_main_stem);
            if (Array.isArray(rec.historical_names)) {
              for (let h_i = 0; h_i < rec.historical_names.length; h_i++) {
                let hs = viscount_entity_audit.normaliseEntityStem(rec.historical_names[h_i] ? rec.historical_names[h_i].name : "");
                if (hs) r_stems.add(hs);
              }
            }

            let rec_ctry_norm = stadester_name_normaliser ? stadester_name_normaliser.normaliseCountryName(rec.country || "") : String(rec.country || "").trim().toLowerCase();
            let sgx = Math.round(r_lat*4);
            let sgy = Math.round(r_lng*4);
            let best_st = null;
            let best_score = -Infinity;
            let best_dist = 999999;

            for (let dx = -1; dx <= 1; dx++) {
              for (let dy = -1; dy <= 1; dy++) {
                let sb = st_grid.get(`${sgx + dx},${sgy + dy}`);
                if (!sb) continue;
                for (let s_i = 0; s_i < sb.length; s_i++) {
                  let st = sb[s_i];
                  let st_ctry_norm = stadester_name_normaliser ? stadester_name_normaliser.normaliseCountryName(st.country || "") : String(st.country || "").trim().toLowerCase();
                  if (rec_ctry_norm && st_ctry_norm && rec_ctry_norm !== st_ctry_norm) continue;
                  let d_km = viscount_audit_utils.haversineKm(r_lat, r_lng, st.lat, st.lng);
                  if (d_km > 12.0) continue;

                  let stem_hit = Boolean(
                    (r_main_stem && st.stems.has(r_main_stem)) ||
                    viscount_entity_audit.areEquivalentExonyms(rec.name || "", st.name, profiles)
                  );
                  if (!stem_hit) {
                    r_stems.forEach(function (arg0_rs) {
                      if (st.stems.has(arg0_rs)) stem_hit = true;
                    });
                  }
                  if (!stem_hit && !(is_cap_shard && d_km <= 3.0)) continue;

                  let sc_val = (stem_hit ? 1e9 : 0) +
                    (!st.is_agg ? 1e8 : 0) +
                    (st.is_capital ? 1e7 : 0) +
                    Math.min(1e6, st.max_pop/100) -
                    d_km*1000;
                  if (sc_val > best_score) {
                    best_score = sc_val;
                    best_st = st;
                    best_dist = d_km;
                  }
                }
              }
            }

            if (best_st) {
              if (claimed_st_keys.has(best_st.key)) {
                let prev_rec = claimed_st_keys.get(best_st.key);
                let comb_aliases = (Array.isArray(prev_rec.other_names) ? prev_rec.other_names : [])
                  .concat([rec.name])
                  .concat(Array.isArray(rec.other_names) ? rec.other_names : []);
                let dedup_a = city_metadata_merger.deduplicateOtherNamesCI(
                  prev_rec.name,
                  prev_rec.historical_names,
                  comb_aliases,
                  prev_rec.country || "",
                  Array.isArray(prev_rec.coords) ? [Number(prev_rec.coords[1]), Number(prev_rec.coords[0])] : []
                );
                if (dedup_a.length > 0) prev_rec.other_names = dedup_a;
                stats.collisions_merged++;
                continue;
              }
              rec.key = best_st.key;
              claimed_st_keys.set(best_st.key, rec);
            }
            aligned_arr.push(rec);
          }

          shard_map.set(sf, aligned_arr);
        }
      }

      for (let f_i = 0; f_i < target_files.length; f_i++) {
        let sf = target_files[f_i];
        let arr = shard_map.get(sf) || [];
        if (!opts.dry_run) {
          let json_str = JSON.stringify(arr, null, 2);
          let tmp_p = path.join(part_dir, `${sf}.tmp`);
          fs.writeFileSync(tmp_p, json_str, "utf8");
          fs.renameSync(tmp_p, path.join(part_dir, sf));
          let sha = crypto.createHash("sha256").update(json_str).digest("hex");
          for (let s_i = 0; s_i < shards.length; s_i++) {
            if (shards[s_i].file === sf) {
              shards[s_i].count = arr.length;
              shards[s_i].sha256 = sha;
              break;
            }
          }
        }
      }

      if (!opts.dry_run) {
        let total_rec = 0;
        for (let s_i = 0; s_i < shards.length; s_i++)
          total_rec += Number(shards[s_i].count || 0);
        manifest.total_records = total_rec;
        manifest.total_entries = total_rec;
        manifest.updated_at_gmt0 = new Date().toISOString();
        fs.writeFileSync(man_path, JSON.stringify(manifest, null, 2), "utf8");
      }

      console.log(
        `[partition_city_metadata --clean-existing] Remediated ${target_files.length} shard(s): ` +
        `aliases_deduped=${stats.aliases_deduped}, pruned_oob_capitals=${stats.invalid_capital_links_pruned}, ` +
        `demoted_non_capitals=${stats.capitals_demoted_out_of_bbox}, split_capitals_merged=${stats.capitals_split_merged}, ` +
        `capital_names_restored=${stats.capitals_name_restored}, subdistricts_stripped=${stats.subdistrict_entries_stripped}, ` +
        `non_latin_remediated=${stats.non_latin_remediated}, collisions_merged=${stats.collisions_merged}, ` +
        `timelines_simplified=${stats.history_simplified}.`
      );

      //Return statement
      return { stats: stats, success: true };
    },

    /**
     * Partitions monolithic `city_metadata.json` + unifies `state_capitals.json` (with strict spatial bbox validation)
     * into `city_metadata/` (`00_capitals.json`, `01_centaur.json`..`14_nicethi.json`, `15_unassigned.json`).
     * @alias city_metadata_partitioner.runPartition
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runPartition (arg0_options) {
      //Convert from parameters
      let opts = (arg0_options) ? arg0_options : {};
      if (opts.clean_existing)
        return this.runCleanExisting(opts);

      let dataset_id = String(opts.dataset || "stadester_2.0").replace(/\.json$/i, "");
      let svea_root = opts.svea_root ? path.resolve(opts.svea_root) : (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = opts.dataview_root ? path.resolve(opts.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));

      //Declare local instance variables
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let mono_path = path.join(stadester_dir, "city_metadata.json");
      let capitals_path = path.join(dataview_root, "data/stadester/state_capitals.json");
      let out_dir = path.join(stadester_dir, "city_metadata");
      let backup_path = path.join(stadester_dir, "city_metadata.legacy_backup.json");

      //Guard clauses
      if (!fs.existsSync(mono_path)) {
        console.error(`[partition_city_metadata] Monolithic city_metadata.json not found: ${mono_path}`);
        return { success: false };
      }

      //Function body
      let raw_meta = JSON.parse(fs.readFileSync(mono_path, "utf8"));
      let raw_capitals = fs.existsSync(capitals_path) ? JSON.parse(fs.readFileSync(capitals_path, "utf8")) : {};
      let states_map = this.loadStatesMap(dataview_root);
      let reg_grid = this.loadRegionalSpatialIndex(stadester_dir);

      let dedup_grid = new Map();
      let cleaned_entries = [];
      let repaired_names = 0;
      let merged_collisions = 0;
      let dropped_junk = 0;

      for (let i = 0; i < raw_meta.length; i++) {
        let entry = raw_meta[i];
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) { dropped_junk++; continue; }
        let lng = Number(entry.coords[0]);
        let lat = Number(entry.coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) { dropped_junk++; continue; }

        let orig_name = String(entry.name || "").trim();
        if ((orig_name.match(/,/g) || []).length >= 2 && /\d{3,}/.test(orig_name)) { dropped_junk++; continue; }

        let clean_name = this.cleanLegacyName(orig_name);
        if (!clean_name || clean_name === "0" || clean_name === "Unknown" || clean_name === "Settlement" || clean_name.includes("?") || clean_name.includes("\uFFFD")) {
          dropped_junk++;
          continue;
        }
        if (clean_name !== orig_name) repaired_names++;

        let hist = [];
        if (Array.isArray(entry.historical_names)) {
          for (let x = 0; x < entry.historical_names.length; x++) {
            let h = entry.historical_names[x];
            if (!h || typeof h !== "object") continue;
            let hn = this.cleanLegacyName(h.name || "");
            let hd = String(h.date || "").trim();
            if (!hn || !viscount_entity_audit.isValidCalendarDate(hd)) continue;
            hist.push({ date: hd, name: hn });
          }
        }
        if (hist.length === 0)
          hist.push({ date: "1900.1.1", name: clean_name });
        else
          hist = city_metadata_merger.sortAndDedupHistoricalNames(hist);

        let raw_others = Array.isArray(entry.other_names) ? entry.other_names.slice() : [];
        if (orig_name !== clean_name && !orig_name.includes("`") && !orig_name.includes("?") && !this.ARTICLE_INVERT_RE.test(orig_name))
          raw_others.push(orig_name);

        let stem = viscount_entity_audit.normaliseEntityStem(clean_name);
        let gkey = `${Math.round(lat*20)},${Math.round(lng*20)}`;
        let merged_into = null;
        for (let dx = -1; dx <= 1 && !merged_into; dx++) {
          for (let dy = -1; dy <= 1 && !merged_into; dy++) {
            let bucket = dedup_grid.get(`${Math.round(lat*20) + dx},${Math.round(lng*20) + dy}`);
            if (!bucket) continue;
            for (let b = 0; b < bucket.length; b++) {
              let cand = bucket[b];
              let d_km = viscount_audit_utils.haversineKm(lat, lng, cand.lat, cand.lng);
              if (d_km <= 0.05 || (d_km <= 2.5 && ((cand.stem === stem) || viscount_entity_audit.areEquivalentExonyms(clean_name, cand.rec.name)))) {
                merged_into = cand;
                break;
              }
            }
          }
        }

        if (merged_into) {
          merged_collisions++;
          merged_into.rec.historical_names = city_metadata_merger.simplifyHistoryAtCoord(merged_into.rec.historical_names, hist);
          merged_into.raw_others.push(clean_name);
          for (let o = 0; o < raw_others.length; o++) merged_into.raw_others.push(raw_others[o]);
          continue;
        }

        let reg_info = this.resolveRegionForCoords(lat, lng, reg_grid);
        let rec = {
          coords: [Number(lng.toFixed(5)), Number(lat.toFixed(5))],
          country: entry.country || reg_info.country || "",
          historical_names: hist,
          name: clean_name,
          region_shard: reg_info.region_key
        };
        if (entry.capital && typeof entry.capital === "object") rec.capital = Object.assign({}, entry.capital);
        if (entry.capitals && typeof entry.capitals === "object" && !rec.capital) rec.capital = Object.assign({}, entry.capitals);
        if (entry.key) rec.key = entry.key;
        if (entry.verified_settlement) rec.verified_settlement = true;

        this.pruneInvalidCapitalEntries(rec, states_map, raw_capitals);

        let item = { lat: lat, lng: lng, raw_others: raw_others, rec: rec, stem: stem };
        cleaned_entries.push(item);
        if (!dedup_grid.has(gkey)) dedup_grid.set(gkey, []);
        dedup_grid.get(gkey).push(item);
      }

      // Unify `state_capitals.json` strictly gated by spatial bbox containment (zero cross-continent homonyms!)
      let capital_indices = new Set();
      let cleaned_by_key = new Map();
      let cleaned_by_stem = new Map();
      for (let i = 0; i < cleaned_entries.length; i++) {
        let it = cleaned_entries[i];
        if (it.rec.key) cleaned_by_key.set(String(it.rec.key).toLowerCase(), i);
        if (it.stem) {
          if (!cleaned_by_stem.has(it.stem)) cleaned_by_stem.set(it.stem, []);
          cleaned_by_stem.get(it.stem).push(i);
        }
        if (it.rec.capital && typeof it.rec.capital === "object" && Object.keys(it.rec.capital).length > 0)
          capital_indices.add(i);
      }

      if (raw_capitals && typeof raw_capitals === "object" && !Array.isArray(raw_capitals)) {
        let state_ids = Object.keys(raw_capitals);
        for (let s = 0; s < state_ids.length; s++) {
          let sid_str = state_ids[s];
          let sc = raw_capitals[sid_str];
          if (!sc || sc.acapital || !Array.isArray(sc.timeline)) continue;
          let sid_num = Number(sid_str);

          for (let t = 0; t < sc.timeline.length; t++) {
            let item = sc.timeline[t];
            if (!item || !item.start) continue;
            let cap_key = String(item.key || "").trim();
            let cap_city = this.cleanLegacyName(item.city || cap_key.split("-")[0] || "");
            let cap_stem = viscount_entity_audit.normaliseEntityStem(cap_city);
            if (!cap_city && !cap_key) continue;

            let matched_idx = -1;
            if (cap_key && cleaned_by_key.has(cap_key.toLowerCase())) {
              let cand_i = cleaned_by_key.get(cap_key.toLowerCase());
              let cand_r = cleaned_entries[cand_i].rec;
              if (this.isValidCapitalBinding(cand_r.coords[0], cand_r.coords[1], cand_r.country, sid_str, states_map, raw_capitals))
                matched_idx = cand_i;
            }
            if (matched_idx < 0 && cap_stem && cleaned_by_stem.has(cap_stem)) {
              let cands = cleaned_by_stem.get(cap_stem);
              let key_low = cap_key.toLowerCase();
              for (let c_i = 0; c_i < cands.length; c_i++) {
                let c_rec = cleaned_entries[cands[c_i]].rec;
                if (!this.isValidCapitalBinding(c_rec.coords[0], c_rec.coords[1], c_rec.country, sid_str, states_map, raw_capitals))
                  continue;
                matched_idx = cands[c_i];
                if (c_rec.country && key_low.includes(String(c_rec.country).toLowerCase()))
                  break;
              }
            }

            if (matched_idx >= 0) {
              capital_indices.add(matched_idx);
              let target = cleaned_entries[matched_idx].rec;
              if (!target.capital || typeof target.capital !== "object") target.capital = {};
              target.capital[String(item.start).trim()] = Number.isFinite(sid_num) ? sid_num : sid_str;
              if (item.stop) {
                let stop_k = String(item.stop).trim();
                if (target.capital[stop_k] === undefined) target.capital[stop_k] = null;
              }
              if (cap_city) cleaned_entries[matched_idx].raw_others.push(cap_city);
            }
          }
        }
      }

      // Finalise case-insensitively deduplicated other_names
      for (let i = 0; i < cleaned_entries.length; i++) {
        let it = cleaned_entries[i];
        let dedup_o = city_metadata_merger.deduplicateOtherNamesCI(
          it.rec.name,
          it.rec.historical_names,
          it.raw_others,
          it.rec.country,
          [it.lat, it.lng]
        );
        if (dedup_o.length > 0) it.rec.other_names = dedup_o;
        else delete it.rec.other_names;
      }

      let capitals_out = [];
      let shards = {};
      for (let i = 0; i < this.REGION_SHARD_FILES.length; i++)
        shards[this.REGION_SHARD_FILES[i].key] = [];
      shards.UNASSIGNED = [];

      for (let i = 0; i < cleaned_entries.length; i++) {
        let rec = cleaned_entries[i].rec;
        if (capital_indices.has(i)) {
          capitals_out.push(rec);
        } else {
          let rk = rec.region_shard && shards[rec.region_shard] ? rec.region_shard : "UNASSIGNED";
          shards[rk].push(rec);
        }
      }

      let sortFn = function (arg0_a, arg1_b) {
        let na = String(arg0_a.name || "");
        let nb = String(arg1_b.name || "");
        if (na < nb) return -1;
        if (na > nb) return 1;
        return Number(arg0_a.coords[1]) - Number(arg1_b.coords[1]);
      };
      capitals_out.sort(sortFn);
      Object.keys(shards).forEach(function (arg0_k) { shards[arg0_k].sort(sortFn); });

      let manifest_shards = [];
      let writeShard = function (arg0_file, arg1_key, arg2_tier, arg3_arr) {
        let json_str = JSON.stringify(arg3_arr, null, 2);
        let sha = crypto.createHash("sha256").update(json_str).digest("hex");
        if (!opts.dry_run) {
          fs.mkdirSync(out_dir, { recursive: true });
          fs.writeFileSync(path.join(out_dir, arg0_file), json_str, "utf8");
        }
        manifest_shards.push({
          count: arg3_arr.length,
          file: arg0_file,
          key: arg1_key,
          sha256: sha,
          tier: arg2_tier
        });
      };

      if (!opts.dry_run && !opts.no_backup && !fs.existsSync(backup_path))
        fs.copyFileSync(mono_path, backup_path);

      writeShard("00_capitals.json", "CAPITALS", 0, capitals_out);
      for (let i = 0; i < this.REGION_SHARD_FILES.length; i++) {
        let r = this.REGION_SHARD_FILES[i];
        writeShard(r.file, r.key, 1, shards[r.key]);
      }
      writeShard("15_unassigned.json", "UNASSIGNED", 2, shards.UNASSIGNED);

      let out_total = capitals_out.length + Object.values(shards).reduce(function (arg0_a, arg1_b) { return arg0_a + arg1_b.length; }, 0);
      let manifest = {
        dataset: dataset_id,
        generated_at_gmt0: new Date().toISOString(),
        schema_version: "2.0",
        shards: manifest_shards,
        stats: {
          capitals_count: capitals_out.length,
          dropped_junk: dropped_junk,
          input_count: raw_meta.length,
          merged_collisions: merged_collisions,
          output_count: out_total,
          repaired_names: repaired_names
        },
        total_entries: out_total,
        total_records: out_total
      };

      if (!opts.dry_run)
        fs.writeFileSync(path.join(out_dir, "city_metadata_manifest.json"), JSON.stringify(manifest, null, 2), "utf8");

      console.log(`[partition_city_metadata] Partitioned ${raw_meta.length} -> ${out_total} records (${capitals_out.length} capitals in 00_capitals.json, ${merged_collisions} collisions merged, ${repaired_names} names repaired, ${dropped_junk} junk dropped).`);

      //Return statement
      return { manifest: manifest, out_dir: out_dir, success: true };
    }
  };

  if (require.main === module) {
    let cli = city_metadata_partitioner.parseCliArgs(process.argv.slice(2));
    let res = city_metadata_partitioner.runPartition(cli);
    process.exit(res.success ? 0 : 1);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_partitioner: city_metadata_partitioner };
  }
}
