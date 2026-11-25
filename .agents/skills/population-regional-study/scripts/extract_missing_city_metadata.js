//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let city_metadata_extractor = {
    ARTICLE_INVERT_RE: /^.+,\s*(?:Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,

    /**
     * Converts a legacy `historical_names` array or compact `date: string` map into a sorted `{ "yyyy.m.d": "Name" }` map.
     * @alias city_metadata_extractor.buildHistoryMap
     *
     * @param {Array<Object>|Object} arg0_raw_history
     *
     * @returns {Object}
     */
    buildHistoryMap (arg0_raw_history) {
      //Convert from parameters
      let raw = arg0_raw_history;

      //Declare local instance variables
      let out_map = {};
      let pairs = [];

      //Function body
      if (Array.isArray(raw)) {
        for (let i = 0; i < raw.length; i++) {
          let item = raw[i];
          if (!item || typeof item !== "object") continue;
          let d_str = String(item.date || "").trim();
          let n_str = String(item.name || "").trim();
          if (d_str && n_str && viscount_entity_audit.isValidCalendarDate(d_str))
            pairs.push({ date: d_str, name: n_str });
        }
      } else if (raw && typeof raw === "object") {
        let keys = Object.keys(raw);
        for (let i = 0; i < keys.length; i++) {
          let d_str = String(keys[i] || "").trim();
          let n_str = String(raw[keys[i]] || "").trim();
          if (d_str && n_str && viscount_entity_audit.isValidCalendarDate(d_str))
            pairs.push({ date: d_str, name: n_str });
        }
      }

      let that = this;
      pairs.sort(function (arg0_a, arg1_b) {
        let ta = that.parseDateTuple(arg0_a.date);
        let tb = that.parseDateTuple(arg1_b.date);
        if (ta[0] !== tb[0]) return ta[0] - tb[0];
        if (ta[1] !== tb[1]) return ta[1] - tb[1];
        return ta[2] - tb[2];
      });

      let prev_low = "";
      for (let i = 0; i < pairs.length; i++) {
        let cur_low = pairs[i].name.toLowerCase();
        if (cur_low === prev_low) continue;
        out_map[pairs[i].date] = pairs[i].name;
        prev_low = cur_low;
      }

      //Return statement
      return out_map;
    },

    /**
     * Computes a deterministic `[lng, lat]` 5-decimal coordinate signature key.
     * @alias city_metadata_extractor.coordKey
     *
     * @param {number} arg0_lng
     * @param {number} arg1_lat
     *
     * @returns {string}
     */
    coordKey (arg0_lng, arg1_lat) {
      //Convert from parameters
      let lat = Number(arg1_lat);
      let lng = Number(arg0_lng);

      //Return statement
      return `${lng.toFixed(5)},${lat.toFixed(5)}`;
    },

    /**
     * Deduplicates strings case-insensitively, retaining the highest-quality cased representative and excluding forbidden matches.
     * @alias city_metadata_extractor.deduplicateNamesCI
     *
     * @param {Array<string>} arg0_names
     * @param {Array<string>} [arg1_exclude]
     *
     * @returns {Array<string>}
     */
    deduplicateNamesCI (arg0_names, arg1_exclude) {
      //Convert from parameters
      let exclude = Array.isArray(arg1_exclude) ? arg1_exclude : [];
      let raw_list = Array.isArray(arg0_names) ? arg0_names : [];

      //Declare local instance variables
      let best_by_low = new Map();
      let exclude_low = new Set();
      let order = [];
      let scoreCase = function (arg0_str) {
        let has_upper = /[A-Z\u00C0-\u00DE]/.test(arg0_str);
        let has_lower = /[a-z\u00DF-\u00FF]/.test(arg0_str);
        let has_diacritic = /[\u00C0-\u024F]/.test(arg0_str);
        return (has_upper && has_lower ? 4 : (has_upper ? 1 : 2)) + (has_diacritic ? 1 : 0);
      };

      //Function body
      for (let i = 0; i < exclude.length; i++) {
        let s = String(exclude[i] || "").trim().toLowerCase();
        if (s) exclude_low.add(s);
      }

      for (let i = 0; i < raw_list.length; i++) {
        let s = String(raw_list[i] || "").trim();
        if (!s) continue;
        let low = s.toLowerCase();
        if (exclude_low.has(low)) continue;
        if (!best_by_low.has(low)) {
          best_by_low.set(low, s);
          order.push(low);
        } else if (scoreCase(s) > scoreCase(best_by_low.get(low))) {
          best_by_low.set(low, s);
        }
      }

      let out = [];
      for (let i = 0; i < order.length; i++)
        out.push(best_by_low.get(order[i]));

      //Return statement
      return out;
    },

    /**
     * Checks whether a candidate settlement string is valid and uncorrupted according to Dataview standards.
     * @alias city_metadata_extractor.isCleanName
     *
     * @param {string} arg0_name
     *
     * @returns {boolean}
     */
    isCleanName (arg0_name) {
      //Convert from parameters
      let raw_name = arg0_name;

      //Guard clauses
      if (typeof raw_name !== "string") return false;
      let s = raw_name.trim();
      if (s.length === 0) return false;
      if (s === "0" || s === "Unknown" || s === "Settlement") return false;
      if (/^[?\s\-_.,]+$/.test(s)) return false;
      if (s.includes("?") || s.includes("\uFFFD") || s.includes("\u00EF\u00BF\u00BD")) return false;
      if (s.includes("`")) return false;
      if (this.ARTICLE_INVERT_RE.test(s)) return false;
      if ((s.match(/,/g) || []).length >= 2 && /\d{3,}/.test(s)) return false;

      //Return statement
      return true;
    },

    /**
     * Loads city metadata records from partitioned `city_metadata/` (`00_capitals.json` + region shard)
     * or falls back to legacy monolithic `city_metadata.json`.
     * @alias city_metadata_extractor.loadMetadataRecords
     *
     * @param {string} arg0_dataview_root
     * @param {string} arg1_dataset_id
     * @param {string} [arg2_project_key]
     *
     * @returns {{ is_partitioned: boolean, records: Array<Object> }}
     */
    loadMetadataRecords (arg0_dataview_root, arg1_dataset_id, arg2_project_key) {
      //Convert from parameters
      let dataset_id = arg1_dataset_id;
      let dataview_root = arg0_dataview_root;
      let project_key = String(arg2_project_key || "").toUpperCase();

      //Declare local instance variables
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let part_dir = path.join(stadester_dir, "city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let records = [];

      //Function body
      if (fs.existsSync(man_path)) {
        let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
        let shards = Array.isArray(man.shards) ? man.shards.slice() : [];
        shards.sort(function (arg0_a, arg1_b) {
          return Number(arg0_a.tier !== undefined ? arg0_a.tier : 1) - Number(arg1_b.tier !== undefined ? arg1_b.tier : 1);
        });
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          let is_cap = sh.key === "CAPITALS" || sh.file === "00_capitals.json";
          if (project_key && !is_cap && sh.key !== project_key && sh.key !== "UNASSIGNED") continue;
          let sp = path.join(part_dir, sh.file);
          if (!fs.existsSync(sp)) continue;
          let arr = JSON.parse(fs.readFileSync(sp, "utf8"));
          for (let x = 0; x < arr.length; x++)
            records.push({ entry: arr[x], index: x, is_capital_shard: is_cap, shard_file: sh.file, tier: is_cap ? 0 : 1 });
        }
        return { is_partitioned: true, records: records };
      }

      let versioned_meta = path.join(stadester_dir, "city_metadata.json");
      let legacy_meta = path.join(dataview_root, "data/stadester/city_metadata.json");
      let meta_path = fs.existsSync(versioned_meta) ? versioned_meta : legacy_meta;
      if (fs.existsSync(meta_path)) {
        let arr = JSON.parse(fs.readFileSync(meta_path, "utf8"));
        for (let i = 0; i < arr.length; i++)
          records.push({ entry: arr[i], index: i, is_capital_shard: false, shard_file: "city_metadata.json", tier: 1 });
      }

      //Return statement
      return { is_partitioned: false, records: records };
    },

    /**
     * Normalises a settlement name for fuzzy phonetic comparison across Latin transliterations.
     * @alias city_metadata_extractor.normaliseName
     *
     * @param {string} arg0_name
     * @param {boolean} [arg1_phonetic]
     *
     * @returns {string}
     */
    normaliseName (arg0_name, arg1_phonetic) {
      //Convert from parameters
      let raw_name = arg0_name;
      let use_phonetic = Boolean(arg1_phonetic);

      //Function body
      let clean = String(raw_name || "")
        .replace(/\s*\([^)]*\)/g, "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase();

      if (use_phonetic) {
        clean = clean
          .replace(/j/g, "y")
          .replace(/ya/g, "a")
          .replace(/ye/g, "e")
          .replace(/yo/g, "o")
          .replace(/yu/g, "u")
          .replace(/ch/g, "c")
          .replace(/sh/g, "s")
          .replace(/zh/g, "z");
      }

      //Return statement
      return clean.replace(/[^a-z0-9]/g, "");
    },

    /**
     * Parses CLI arguments for `extract_missing_city_metadata.js`.
     * @alias city_metadata_extractor.parseCliArgs
     *
     * @param {Array<string>} arg0_argv
     *
     * @returns {Object}
     */
    parseCliArgs (arg0_argv) {
      //Convert from parameters
      let argv = Array.isArray(arg0_argv) ? arg0_argv : [];

      //Declare local instance variables
      let args = {
        batch_size: 0,
        dataset: "stadester_2.0",
        dataview_root: "",
        max_batch_size: 0,
        max_concurrency: 0,
        min_batch_size: 0,
        out_dir: "",
        pass: "both",
        project: "",
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project=")) args.project = tok.slice(10).trim().toUpperCase();
        else if (tok === "--project" && i + 1 < argv.length) args.project = argv[++i].trim().toUpperCase();
        else if (tok.startsWith("--dataset=")) args.dataset = tok.slice(10).trim();
        else if (tok.startsWith("--svea-root=")) args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataview-root=")) args.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--batch-size=")) args.batch_size = Math.max(1, Number(tok.slice(13)) || 0);
        else if (tok.startsWith("--min-batch-size=")) args.min_batch_size = Math.max(1, Number(tok.slice(17)) || 0);
        else if (tok.startsWith("--max-batch-size=")) args.max_batch_size = Math.max(1, Number(tok.slice(17)) || 0);
        else if (tok.startsWith("--max-concurrency=")) args.max_concurrency = Math.max(1, Math.min(24, Number(tok.slice(18)) || 24));
        else if (tok.startsWith("--pass=")) args.pass = tok.slice(7).trim().toLowerCase();
        else if (tok === "--pass" && i + 1 < argv.length) args.pass = argv[++i].trim().toLowerCase();
        else if (tok.startsWith("--out-dir=")) args.out_dir = tok.slice(10).trim();
      }

      //Return statement
      return args;
    },

    /**
     * Parses a `YYYY.M.D` string into `[year, month, day]`.
     * @alias city_metadata_extractor.parseDateTuple
     *
     * @param {string} arg0_date_str
     *
     * @returns {Array<number>}
     */
    parseDateTuple (arg0_date_str) {
      //Convert from parameters
      let parts = String(arg0_date_str || "").split(".");

      //Guard clauses
      if (parts.length !== 3) return [0, 1, 1];

      //Return statement
      return [Number(parts[0]) || 0, Number(parts[1]) || 1, Number(parts[2]) || 1];
    },

    /**
     * Runs 2-pass extraction comparing Viscount settlements against Dataview partitioned `city_metadata/`:
     * - Pass 1 (`pass1/`): settlements with `max_pop > 10k` (at any year) OR `is_capital`, chunked adaptively
     *   to `<= 24` compact batches per wave using minimal `[lng, lat]` + `date: string` maps.
     * - Pass 2 (`pass2/residuals.json`): residual settlements (`max_pop <= 10k && !is_capital`) routed to
     *   deterministic WHG + GeoHack resolution (zero LLM agents).
     * @alias city_metadata_extractor.runExtraction
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runExtraction (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let counts = {
        capital_audit: 0,
        corrupted_names: 0,
        empty_historical_names: 0,
        indigenous_stub: 0,
        missing_entry: 0,
        pass1_count: 0,
        pass2_count: 0,
        single_entry_major_stub: 0,
        suspicious_existing_name: 0,
        total_checked: 0,
        under_covered_history: 0,
        up_to_date: 0
      };
      let dataset_id = (options.dataset) ? String(options.dataset).replace(/\.json$/i, "") : "stadester_2.0";
      let pass_mode = String(options.pass || "both").toLowerCase();
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let topo_policy = (profiles && profiles.toponymy_pipeline_policy) ? profiles.toponymy_pipeline_policy : {};
      let mun_rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
      let max_concurrency = Math.min(24, Math.max(1, Number(options.max_concurrency || topo_policy.max_concurrent_subagents) || 24));
      let min_batch_size = Math.max(1, Number(options.min_batch_size || topo_policy.pass1_min_batch_size) || 40);
      let max_batch_size = Math.max(min_batch_size, Number(options.max_batch_size || topo_policy.pass1_max_batch_size) || 200);
      let pass1_min_pop = Number(topo_policy.pass1_min_peak_pop) || 10000;
      let municipal_snap_km = Number(mun_rules.municipal_coord_snap_km) || 2.5;
      let indig_regions = new Set(Array.isArray(profiles.indigenous_endonym_regions) ? profiles.indigenous_endonym_regions : []);
      let is_indig_project = Boolean(options.project && indig_regions.has(options.project));
      let pass1_batch_files = [];
      let pass1_candidates = [];
      let pass2_candidates = [];

      //Guard clauses
      let loader_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/ViscountGazetteerLoader.js");
      let prec_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
      if (!fs.existsSync(loader_path)) {
        console.error(`[extract_missing_city_metadata] ViscountGazetteerLoader not found: ${loader_path}`);
        return { batch_files: [], counts: counts };
      }

      let meta_loaded = this.loadMetadataRecords(dataview_root, dataset_id, options.project);
      if (meta_loaded.records.length === 0) {
        console.error(`[extract_missing_city_metadata] Dataview city_metadata not found for ${dataset_id}`);
        return { batch_files: [], counts: counts };
      }

      //Function body
      require(loader_path);
      let load_opts = { project_root: svea_root };
      if (options.project) load_opts.only_project = options.project;

      let settlements_obj = global.ViscountGazetteerLoader.getViscountRegionalObject(load_opts);
      let settlement_keys = Object.keys(settlements_obj);
      let spatial_grid = new Map();

      for (let i = 0; i < meta_loaded.records.length; i++) {
        let rec_wrap = meta_loaded.records[i];
        let entry = rec_wrap.entry;
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;

        let lat = Number(entry.coords[1]);
        let lng = Number(entry.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

        let norm_set = new Set();
        let phon_set = new Set();
        let hist_map = this.buildHistoryMap(entry.historical_names || entry.names);
        let all_alias_strings = [entry.name];
        if (Array.isArray(entry.other_names)) all_alias_strings = all_alias_strings.concat(entry.other_names);
        let h_keys = Object.keys(hist_map);
        for (let x = 0; x < h_keys.length; x++)
          all_alias_strings.push(hist_map[h_keys[x]]);

        for (let x = 0; x < all_alias_strings.length; x++) {
          let ns = this.normaliseName(all_alias_strings[x], false);
          let ps = this.normaliseName(all_alias_strings[x], true);
          if (ns) norm_set.add(ns);
          if (ps) phon_set.add(ps);
        }

        let grid_key = `${Math.round(lat*2)},${Math.round(lng*2)}`;
        if (!spatial_grid.has(grid_key)) spatial_grid.set(grid_key, []);
        spatial_grid.get(grid_key).push({
          entry: entry,
          hist_map: hist_map,
          index: rec_wrap.index,
          is_capital_shard: rec_wrap.is_capital_shard,
          lat: lat,
          lng: lng,
          norm_set: norm_set,
          phon_set: phon_set,
          shard_file: rec_wrap.shard_file,
          tier: rec_wrap.tier
        });
      }

      for (let i = 0; i < settlement_keys.length; i++) {
        let key = settlement_keys[i];
        let city = settlements_obj[key];
        if (!city || !Array.isArray(city.coords) || city.coords.length < 2) continue;

        counts.total_checked++;
        let clat = Number(city.coords[0]);
        let clng = Number(city.coords[1]);
        let gx = Math.round(clat*2);
        let gy = Math.round(clng*2);
        let nearby = [];

        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            let bucket = spatial_grid.get(`${gx + dx},${gy + dy}`);
            if (bucket) {
              for (let x = 0; x < bucket.length; x++) nearby.push(bucket[x]);
            }
          }
        }

        let city_aliases = [city.name];
        if (Array.isArray(city.original_names)) city_aliases = city_aliases.concat(city.original_names);
        if (Array.isArray(city.other_names)) city_aliases = city_aliases.concat(city.other_names);

        let c_norms = new Set();
        let c_phons = new Set();
        for (let x = 0; x < city_aliases.length; x++) {
          let ns = this.normaliseName(city_aliases[x], false);
          let ps = this.normaliseName(city_aliases[x], true);
          if (ns) c_norms.add(ns);
          if (ps) c_phons.add(ps);
        }

        // Collect all overlapping municipal-cluster records at this [lng, lat] (Tier-0 capitals prioritised)
        let cluster_matches = [];
        for (let x = 0; x < nearby.length; x++) {
          let cand = nearby[x];
          let d_km = viscount_audit_utils.haversineKm(clat, clng, cand.lat, cand.lng);
          if (d_km > 15.0) continue;

          let matched_name = false;
          for (let cn of c_norms) {
            for (let mn of cand.norm_set) {
              if (mn === cn || (mn.length >= 4 && cn.length >= 4 && (mn.includes(cn) || cn.includes(mn)))) {
                matched_name = true;
                break;
              }
            }
            if (matched_name) break;
          }
          if (!matched_name) {
            for (let cp of c_phons) {
              for (let mp of cand.phon_set) {
                if (mp === cp) { matched_name = true; break; }
              }
              if (matched_name) break;
            }
          }
          if (!matched_name && viscount_entity_audit.areEquivalentExonyms(city.name || key, cand.entry.name || "", profiles))
            matched_name = true;

          // Only snap onto a nearby record without a name match when practically co-located (<= 0,35 km),
          // preventing neighbouring suburbs <= 2,5 km from hijacking a Tier-0 capital pin!
          if (d_km <= 0.35 || (matched_name && d_km <= 15.0))
            cluster_matches.push({ cand: cand, dist_km: d_km, matched_name: matched_name });
        }

        cluster_matches.sort(function (arg0_a, arg1_b) {
          if (arg0_a.matched_name !== arg1_b.matched_name)
            return arg0_a.matched_name ? -1 : 1;
          if (arg0_a.cand.is_capital_shard !== arg1_b.cand.is_capital_shard)
            return arg0_a.cand.is_capital_shard ? -1 : 1;
          return arg0_a.dist_km - arg1_b.dist_km;
        });

        let best_match = cluster_matches.length > 0 ? cluster_matches[0].cand : null;

        // Consolidate entire existing history at this [lng, lat] across municipal-cluster records
        let consolidated_hist_pairs = [];
        for (let m_i = 0; m_i < cluster_matches.length; m_i++) {
          let cm = cluster_matches[m_i];
          if (!cm.matched_name && cm.dist_km > 0.35) continue;
          let hmap = cm.cand.hist_map || {};
          let hkeys = Object.keys(hmap);
          for (let h_i = 0; h_i < hkeys.length; h_i++)
            consolidated_hist_pairs.push({ date: hkeys[h_i], name: hmap[hkeys[h_i]] });
        }
        let consolidated_names_map = this.buildHistoryMap(consolidated_hist_pairs);
        let consolidated_dates = Object.keys(consolidated_names_map);

        let pop_obj = (city.population && typeof city.population === "object") ? city.population : {};
        let pop_years = Object.keys(pop_obj).map(Number).filter(Number.isFinite).sort(function (arg0_a, arg1_b) {
          return arg0_a - arg1_b;
        });
        let max_pop = 0;
        for (let x = 0; x < pop_years.length; x++) {
          let pv = Number(pop_obj[String(pop_years[x])] || 0);
          if (pv > max_pop) max_pop = pv;
        }
        let earliest_yr = pop_years.length > 0 ? pop_years[0] : null;
        let latest_yr = pop_years.length > 0 ? pop_years[pop_years.length - 1] : null;
        let is_capital = Boolean(
          city.is_capital ||
          city.capital ||
          (best_match && (best_match.is_capital_shard || (best_match.entry.capital && Object.keys(best_match.entry.capital).length > 0)))
        );

        let reason = "";
        if (!best_match) {
          reason = "missing_entry";
          counts.missing_entry++;
        } else if (consolidated_dates.length === 0) {
          reason = "empty_historical_names";
          counts.empty_historical_names++;
        } else {
          let has_corrupt = !this.isCleanName(best_match.entry.name);
          let has_suspicious = Boolean(viscount_entity_audit.isSuspiciousToponym(best_match.entry.name, profiles));
          let prev_stem = "";
          for (let x = 0; x < consolidated_dates.length; x++) {
            let h_date = consolidated_dates[x];
            let h_name = consolidated_names_map[h_date];
            if (!this.isCleanName(h_name) || !viscount_entity_audit.isValidCalendarDate(h_date)) {
              has_corrupt = true;
              break;
            }
            if (viscount_entity_audit.isSuspiciousToponym(h_name, profiles)) has_suspicious = true;
            let h_stem = viscount_entity_audit.normaliseEntityStem(h_name);
            if (prev_stem && h_stem && h_stem === prev_stem && h_name !== consolidated_names_map[consolidated_dates[x - 1]])
              has_suspicious = true;
            prev_stem = h_stem;
          }
          if (has_corrupt) {
            reason = "corrupted_names";
            counts.corrupted_names++;
          } else if (has_suspicious) {
            reason = "suspicious_existing_name";
            counts.suspicious_existing_name++;
          } else if (is_capital && consolidated_dates.length === 1 && consolidated_dates[0] === "1900.1.1") {
            reason = "capital_audit";
            counts.capital_audit++;
          } else if (earliest_yr !== null && earliest_yr < 1850) {
            let first_h_yr = this.parseDateTuple(consolidated_dates[0])[0];
            if (!Number.isFinite(first_h_yr) || first_h_yr > earliest_yr + 100 || (consolidated_dates.length === 1 && (latest_yr - earliest_yr) >= 200)) {
              reason = "under_covered_history";
              counts.under_covered_history++;
            }
          } else if (consolidated_dates.length === 1 && is_indig_project && max_pop > pass1_min_pop && consolidated_dates[0] === "1900.1.1") {
            reason = "indigenous_stub";
            counts.indigenous_stub++;
          } else if (consolidated_dates.length === 1 && max_pop > pass1_min_pop && consolidated_dates[0] === "1900.1.1") {
            reason = "single_entry_major_stub";
            counts.single_entry_major_stub++;
          }
        }

        if (!reason) {
          counts.up_to_date++;
          continue;
        }

        // Anchor coordinates in [lng, lat] GeoJSON/Dataview order (prefer Tier-0 capital coord if matched)
        let out_lng = Number((best_match && best_match.is_capital_shard ? best_match.lng : clng).toFixed(5));
        let out_lat = Number((best_match && best_match.is_capital_shard ? best_match.lat : clat).toFixed(5));
        let clean_seed_name = String((best_match && this.isCleanName(best_match.entry.name) ? best_match.entry.name : (city.name || key))).trim();
        let seed_names_map = consolidated_dates.length > 0 ? consolidated_names_map : {};

        if (Object.keys(seed_names_map).length === 0) {
          let safe_yr = Number.isFinite(earliest_yr) ? earliest_yr : 1900;
          if (safe_yr === 0) safe_yr = -1;
          if (safe_yr < -10000) safe_yr = -10000;
          if (safe_yr > 2026) safe_yr = 2026;
          seed_names_map[`${safe_yr}.1.1`] = clean_seed_name;
        }

        let dedup_aliases = this.deduplicateNamesCI(city_aliases, [clean_seed_name].concat(Object.values(seed_names_map)));
        let is_pass1 = Boolean(is_capital || max_pop > pass1_min_pop);

        let full_meta_record = {
          coord_key: this.coordKey(out_lng, out_lat),
          coords: [out_lng, out_lat],
          country: city.country || "",
          earliest_year: earliest_yr,
          existing_meta_index: best_match ? best_match.index : null,
          existing_meta_name: best_match ? best_match.entry.name : null,
          existing_shard_file: best_match ? best_match.shard_file : null,
          is_capital: is_capital,
          key: key,
          known_aliases: dedup_aliases,
          latest_year: latest_yr,
          max_pop: Math.round(max_pop),
          name: clean_seed_name,
          names: seed_names_map,
          reason: reason,
          region: city.region || "",
          sources: Array.isArray(city.sources) ? city.sources.slice() : []
        };

        if (is_pass1) {
          pass1_candidates.push(full_meta_record);
        } else {
          pass2_candidates.push(full_meta_record);
        }
      }

      // Collapse any exact-coordinate collisions at [lng, lat] into ONE full-history record (Pass 1 takes precedence over Pass 2)
      let by_coord_dedup = new Map();
      let absorbCandidate = (arg0_rec, arg1_is_pass1) => {
        let ck = arg0_rec.coord_key;
        let prev = by_coord_dedup.get(ck);
        if (!prev) {
          by_coord_dedup.set(ck, { is_pass1: arg1_is_pass1, rec: arg0_rec });
          return;
        }
        let tgt = prev.rec;
        let merged_pairs = [];
        let t_dates = Object.keys(tgt.names || {});
        for (let i = 0; i < t_dates.length; i++) merged_pairs.push({ date: t_dates[i], name: tgt.names[t_dates[i]] });
        let r_dates = Object.keys(arg0_rec.names || {});
        for (let i = 0; i < r_dates.length; i++) merged_pairs.push({ date: r_dates[i], name: arg0_rec.names[r_dates[i]] });
        tgt.names = this.buildHistoryMap(merged_pairs);
        if (arg0_rec.is_capital && !tgt.is_capital) {
          tgt.is_capital = true;
          tgt.name = arg0_rec.name;
          tgt.key = arg0_rec.key;
          tgt.existing_shard_file = arg0_rec.existing_shard_file;
        } else if (!tgt.is_capital && (arg0_rec.max_pop || 0) > (tgt.max_pop || 0)) {
          tgt.name = arg0_rec.name;
          tgt.key = arg0_rec.key;
        }
        tgt.max_pop = Math.max(tgt.max_pop || 0, arg0_rec.max_pop || 0);
        if (arg0_rec.earliest_year !== null && (tgt.earliest_year === null || arg0_rec.earliest_year < tgt.earliest_year))
          tgt.earliest_year = arg0_rec.earliest_year;
        tgt.known_aliases = this.deduplicateNamesCI(
          (tgt.known_aliases || []).concat(arg0_rec.known_aliases || []).concat([arg0_rec.name]),
          [tgt.name].concat(Object.values(tgt.names || {}))
        );
        if (arg1_is_pass1 || tgt.is_capital || tgt.max_pop > pass1_min_pop)
          prev.is_pass1 = true;
      };
      for (let i = 0; i < pass1_candidates.length; i++) absorbCandidate(pass1_candidates[i], true);
      for (let i = 0; i < pass2_candidates.length; i++) absorbCandidate(pass2_candidates[i], false);

      pass1_candidates = [];
      pass2_candidates = [];
      by_coord_dedup.forEach(function (arg0_wrap) {
        if (arg0_wrap.is_pass1) pass1_candidates.push(arg0_wrap.rec);
        else pass2_candidates.push(arg0_wrap.rec);
      });
      counts.pass1_count = pass1_candidates.length;
      counts.pass2_count = pass2_candidates.length;

      // Sort Pass 1: capitals first, then geographically clustered by 2-deg latitude/longitude bands
      pass1_candidates.sort(function (arg0_a, arg1_b) {
        if (arg0_a.is_capital !== arg1_b.is_capital) return arg0_a.is_capital ? -1 : 1;
        let band_a = Math.floor(arg0_a.coords[1]/2)*1000 + Math.floor(arg0_a.coords[0]/2);
        let band_b = Math.floor(arg1_b.coords[1]/2)*1000 + Math.floor(arg1_b.coords[0]/2);
        if (band_a !== band_b) return band_a - band_b;
        return (arg1_b.max_pop || 0) - (arg0_a.max_pop || 0);
      });

      pass2_candidates.sort(function (arg0_a, arg1_b) {
        return (arg1_b.max_pop || 0) - (arg0_a.max_pop || 0);
      });

      let project_slug = options.project ? options.project.toLowerCase() : "all_projects";
      if (options.project && fs.existsSync(prec_path)) {
        let prec = JSON5.parse(fs.readFileSync(prec_path, "utf8"));
        let plist = Array.isArray(prec.projects) ? prec.projects : [];
        for (let i = 0; i < plist.length; i++) {
          if (String(plist[i].key || "").toUpperCase() === options.project && plist[i].slug) {
            project_slug = plist[i].slug;
            break;
          }
        }
      }

      let out_dir = (options.out_dir) ? path.resolve(options.out_dir) :
        path.join(svea_root, "tests/toponymy_batches", project_slug);
      let pass1_dir = path.join(out_dir, "pass1");
      let pass2_dir = path.join(out_dir, "pass2");

      fs.mkdirSync(out_dir, { recursive: true });

      // Adaptive batch size: spread Pass-1 settlements into <= 24 batches per wave
      let eff_batch_size = (options.batch_size > 0) ?
        Math.min(max_batch_size, Math.max(1, options.batch_size)) :
        Math.min(max_batch_size, Math.max(min_batch_size, Math.ceil(Math.max(1, pass1_candidates.length)/max_concurrency)));

      let pass1_index_by_coord = {};
      if (pass_mode === "1" || pass_mode === "both") {
        if (fs.existsSync(pass1_dir)) {
          let old_p1 = fs.readdirSync(pass1_dir);
          for (let i = 0; i < old_p1.length; i++) {
            if (/^(?:batch_\d+|batch_index|manifest)\.json$/i.test(old_p1[i]))
              fs.unlinkSync(path.join(pass1_dir, old_p1[i]));
          }
        }
        fs.mkdirSync(pass1_dir, { recursive: true });

        for (let i = 0; i < pass1_candidates.length; i += eff_batch_size) {
          let batch_idx = Math.floor(i/eff_batch_size) + 1;
          let slice = pass1_candidates.slice(i, i + eff_batch_size);
          let compact_batch = [];

          for (let x = 0; x < slice.length; x++) {
            let item = slice[x];
            let compact_row = {
              coords: item.coords,
              names: item.names
            };
            if (item.is_capital) compact_row.cap = true;
            compact_batch.push(compact_row);

            pass1_index_by_coord[item.coord_key] = {
              batch_index: batch_idx,
              coords: item.coords,
              country: item.country,
              earliest_year: item.earliest_year,
              existing_meta_index: item.existing_meta_index,
              existing_meta_name: item.existing_meta_name,
              existing_shard_file: item.existing_shard_file,
              is_capital: item.is_capital,
              key: item.key,
              known_aliases: item.known_aliases,
              latest_year: item.latest_year,
              max_pop: item.max_pop,
              name: item.name,
              reason: item.reason,
              region: item.region,
              sources: item.sources
            };
          }

          let batch_name = `batch_${String(batch_idx).padStart(3, "0")}.json`;
          let batch_path = path.join(pass1_dir, batch_name);
          fs.writeFileSync(batch_path, JSON.stringify(compact_batch), "utf8");
          pass1_batch_files.push(batch_path);
        }

        fs.writeFileSync(path.join(pass1_dir, "batch_index.json"), JSON.stringify({
          project: options.project || "ALL",
          schema_version: "3.0_compact_coord_map",
          by_coord: pass1_index_by_coord
        }, null, 2), "utf8");

        fs.writeFileSync(path.join(pass1_dir, "manifest.json"), JSON.stringify({
          batch_count: pass1_batch_files.length,
          batch_files: pass1_batch_files,
          batch_size: eff_batch_size,
          generated_at_gmt0: new Date().toISOString(),
          max_concurrency: max_concurrency,
          pass: 1,
          pass1_min_peak_pop: pass1_min_pop,
          project: options.project || "ALL",
          schema_version: "3.0_compact_coord_map",
          settlement_count: pass1_candidates.length
        }, null, 2), "utf8");
      }

      let pass2_file = "";
      if (pass_mode === "2" || pass_mode === "both") {
        fs.mkdirSync(pass2_dir, { recursive: true });
        pass2_file = path.join(pass2_dir, "residuals.json");
        fs.writeFileSync(pass2_file, JSON.stringify({
          count: pass2_candidates.length,
          generated_at_gmt0: new Date().toISOString(),
          mode: "whg_geohack_deterministic",
          pass: 2,
          project: options.project || "ALL",
          schema_version: "3.0_compact_coord_map",
          settlements: pass2_candidates
        }, null, 2), "utf8");
      }

      let summary = {
        counts: counts,
        generated_at_gmt0: new Date().toISOString(),
        is_partitioned_source: meta_loaded.is_partitioned,
        max_concurrency: max_concurrency,
        out_dir: out_dir,
        pass1: {
          batch_count: pass1_batch_files.length,
          batch_files: pass1_batch_files,
          batch_size: eff_batch_size,
          dir: pass1_dir,
          settlement_count: pass1_candidates.length
        },
        pass2: {
          dir: pass2_dir,
          residuals_file: pass2_file,
          settlement_count: pass2_candidates.length
        },
        project: options.project || "ALL",
        schema_version: "3.0_compact_coord_map"
      };
      fs.writeFileSync(path.join(out_dir, "manifest.json"), JSON.stringify(summary, null, 2), "utf8");

      console.log(
        `[extract_missing_city_metadata] Checked ${counts.total_checked} (${options.project || "ALL"}): ` +
        `Pass 1 (>10k or capital)=${pass1_candidates.length} -> ${pass1_batch_files.length} compact batch(es) (size<=${eff_batch_size}, cap=${max_concurrency}); ` +
        `Pass 2 (WHG/GeoHack residuals)=${pass2_candidates.length} -> ${pass2_file || "skipped"}`
      );

      //Return statement
      return summary;
    }
  };

  if (require.main === module) {
    let cli_args = city_metadata_extractor.parseCliArgs(process.argv.slice(2));
    city_metadata_extractor.runExtraction(cli_args);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_extractor: city_metadata_extractor };
  }
}
