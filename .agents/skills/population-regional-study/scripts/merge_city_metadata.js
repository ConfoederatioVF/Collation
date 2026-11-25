//Import modules
let crypto = require("crypto");
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let city_metadata_merger = {
    ARTICLE_INVERT_RE: /^.+,\s*(?:Al|El|As|Ash|Ar|Az|Ad|An|At|Le|La|Les|L'|Los|Las|Il|Lo|De|Den|Het|Der|Die|Das|The)$/i,
    NON_LATIN_RE: /[\u0370-\u03FF\u0400-\u04FF\u0530-\u058F\u0590-\u05FF\u0600-\u06FF\u0900-\u097F\u0E00-\u0E7F\u10A0-\u10FF\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]/,

    /**
     * Converts a `date: string` map or `[{ date, name }]` array into a validated array of `{ date, name }` objects.
     * @alias city_metadata_merger.coerceHistoryEntries
     *
     * @param {Array<Object>|Object} arg0_raw_hist
     * @param {Array<RegExp>} [arg1_mun_regexes]
     * @param {Object} [arg2_profiles]
     * @param {boolean} [arg3_verified=false]
     *
     * @returns {{ dropped: number, entries: Array<{ date: string, name: string }> }}
     */
    coerceHistoryEntries (arg0_raw_hist, arg1_mun_regexes, arg2_profiles, arg3_verified) {
      //Convert from parameters
      let mun_regexes = Array.isArray(arg1_mun_regexes) ? arg1_mun_regexes : [];
      let profiles = arg2_profiles || viscount_entity_audit.loadSkillProfiles();
      let raw = arg0_raw_hist;
      let verified = Boolean(arg3_verified);

      //Declare local instance variables
      let date_regex = /^-?\d+\.\d+\.\d+$/;
      let dropped = 0;
      let entries = [];
      let raw_pairs = [];

      //Function body
      if (Array.isArray(raw)) {
        for (let i = 0; i < raw.length; i++) {
          let h = raw[i];
          if (h && typeof h === "object")
            raw_pairs.push([String(h.date || "").trim(), String(h.name || "").trim()]);
          else
            dropped++;
        }
      } else if (raw && typeof raw === "object") {
        let keys = Object.keys(raw);
        for (let i = 0; i < keys.length; i++)
          raw_pairs.push([String(keys[i] || "").trim(), String(raw[keys[i]] || "").trim()]);
      }

      for (let i = 0; i < raw_pairs.length; i++) {
        let h_date = raw_pairs[i][0];
        let h_name = this.stripParenthetical(raw_pairs[i][1]);
        if (!date_regex.test(h_date) || !viscount_entity_audit.isValidCalendarDate(h_date) || this.isCorruptedCityName(h_name)) {
          dropped++;
          continue;
        }
        if (this.NON_LATIN_RE.test(h_name)) {
          dropped++;
          continue;
        }
        if (!verified && viscount_entity_audit.isSuspiciousToponym(h_name, profiles)) {
          dropped++;
          continue;
        }
        if (!verified && mun_regexes.some(function (arg0_r) { return arg0_r.test(h_name); })) {
          dropped++;
          continue;
        }
        entries.push({ date: h_date, name: h_name });
      }

      //Return statement
      return { dropped: dropped, entries: entries };
    },

    /**
     * Computes a deterministic `[lng, lat]` 5-decimal coordinate signature key.
     * @alias city_metadata_merger.coordKey
     *
     * @param {number} arg0_lng
     * @param {number} arg1_lat
     *
     * @returns {string}
     */
    coordKey (arg0_lng, arg1_lat) {
      //Return statement
      return `${Number(arg0_lng).toFixed(5)},${Number(arg1_lat).toFixed(5)}`;
    },

    /**
     * Parses a `YYYY.M.D` (including negative BCE years) date string into numeric tuple `[year, month, day]`.
     * @alias city_metadata_merger.dateSortTuple
     *
     * @param {string} arg0_date_str
     *
     * @returns {Array<number>}
     */
    dateSortTuple (arg0_date_str) {
      //Convert from parameters
      let parts = String(arg0_date_str || "").split(".");

      //Guard clauses
      if (parts.length !== 3) return [0, 1, 1];

      //Return statement
      return [Number(parts[0]) || 0, Number(parts[1]) || 1, Number(parts[2]) || 1];
    },

    /**
     * Drops duplicate `.other_names` and any string matching canonical `.name` or `.historical_names` (case-insensitive).
     * Retains the best-cased / diacritic-preserving representative per unique lowercase string.
     * @alias city_metadata_merger.deduplicateOtherNamesCI
     *
     * @param {string} arg0_canonical_name
     * @param {Array<Object>} arg1_historical_names
     * @param {Array<string>} arg2_raw_aliases
     * @param {string} [arg3_country]
     * @param {Array<number>} [arg4_coords_lat_lng]
     *
     * @returns {Array<string>}
     */
    deduplicateOtherNamesCI (arg0_canonical_name, arg1_historical_names, arg2_raw_aliases, arg3_country, arg4_coords_lat_lng) {
      //Convert from parameters
      let canonical = String(arg0_canonical_name || "").trim();
      let coords_lat_lng = Array.isArray(arg4_coords_lat_lng) ? arg4_coords_lat_lng : [];
      let country = String(arg3_country || "");
      let hist = Array.isArray(arg1_historical_names) ? arg1_historical_names : [];
      let raw_aliases = Array.isArray(arg2_raw_aliases) ? arg2_raw_aliases : [];

      //Declare local instance variables
      let best_by_low = new Map();
      let excluded_low = new Set();
      let order = [];
      let scoreCase = function (arg0_str) {
        let has_upper = /[A-Z\u00C0-\u00DE]/.test(arg0_str);
        let has_lower = /[a-z\u00DF-\u00FF]/.test(arg0_str);
        let has_diacritic = /[\u00C0-\u024F]/.test(arg0_str);
        return (has_upper && has_lower ? 4 : (has_upper ? 1 : 2)) + (has_diacritic ? 1 : 0);
      };

      //Function body
      if (canonical) excluded_low.add(canonical.toLowerCase());
      for (let i = 0; i < hist.length; i++) {
        let hn = (hist[i] && hist[i].name) ? String(hist[i].name).trim().toLowerCase() : "";
        if (hn) excluded_low.add(hn);
      }

      for (let i = 0; i < raw_aliases.length; i++) {
        let a_str = this.stripParenthetical(raw_aliases[i]);
        if (!a_str || this.isCorruptedCityName(a_str)) continue;
        if (this.isForeignScriptNoiseForCountry(a_str, country, coords_lat_lng)) continue;
        let low = a_str.toLowerCase();
        if (excluded_low.has(low)) continue;
        if (!best_by_low.has(low)) {
          best_by_low.set(low, a_str);
          order.push(low);
        } else if (scoreCase(a_str) > scoreCase(best_by_low.get(low))) {
          best_by_low.set(low, a_str);
        }
      }

      let out = [];
      for (let i = 0; i < order.length; i++)
        out.push(best_by_low.get(order[i]));

      //Return statement
      return out;
    },

    /**
     * Checks whether a settlement label contains an archaeological or topographic site qualifier.
     * @alias city_metadata_merger.hasArchSiteQualifier
     *
     * @param {string} arg0_name
     *
     * @returns {boolean}
     */
    hasArchSiteQualifier (arg0_name) {
      //Return statement
      return viscount_entity_audit.hasArchSiteQualifier(arg0_name, viscount_entity_audit.loadSkillProfiles());
    },

    /**
     * Returns true when a metadata record holds active capital timelines.
     * @alias city_metadata_merger.hasCapitalTimeline
     *
     * @param {Object} arg0_entry
     *
     * @returns {boolean}
     */
    hasCapitalTimeline (arg0_entry) {
      //Convert from parameters
      let entry = arg0_entry;

      //Guard clauses
      if (!entry || typeof entry !== "object") return false;

      //Return statement
      return Boolean(
        (entry.capital && typeof entry.capital === "object" && Object.keys(entry.capital).length > 0) ||
        (Array.isArray(entry.capital_records) && entry.capital_records.length > 0)
      );
    },

    /**
     * Mirrors Dataview `isCorruptedCityName`: returns true when name is corrupted, comma-inverted or address-junk.
     * @alias city_metadata_merger.isCorruptedCityName
     *
     * @param {string} arg0_name
     *
     * @returns {boolean}
     */
    isCorruptedCityName (arg0_name) {
      //Convert from parameters
      let raw_name = arg0_name;

      //Guard clauses
      if (typeof raw_name !== "string") return true;
      let trimmed = raw_name.trim();
      if (trimmed.length === 0) return true;
      if (trimmed === "0" || trimmed === "Unknown" || trimmed === "Settlement") return true;
      if (/^[?\s\-_.,]+$/.test(trimmed)) return true;
      if (trimmed.includes("?") || trimmed.includes("\uFFFD") || trimmed.includes("\u00EF\u00BF\u00BD")) return true;
      if (trimmed.includes("`")) return true;
      if (this.ARTICLE_INVERT_RE.test(trimmed)) return true;
      if ((trimmed.match(/,/g) || []).length >= 2 && /\d{3,}/.test(trimmed)) return true;

      //Return statement
      return false;
    },

    /**
     * Returns true when an alias contains non-indigenous foreign-script noise for Latin-only countries.
     * @alias city_metadata_merger.isForeignScriptNoiseForCountry
     *
     * @param {string} arg0_alias
     * @param {string} arg1_country
     * @param {Array<number>} [arg2_coords]
     *
     * @returns {boolean}
     */
    isForeignScriptNoiseForCountry (arg0_alias, arg1_country, arg2_coords) {
      //Convert from parameters
      let alias = String(arg0_alias || "");
      let coords = Array.isArray(arg2_coords) ? arg2_coords : [];
      let country = String(arg1_country || "").trim();
      let profiles = viscount_entity_audit.loadSkillProfiles();

      //Guard clauses
      if (!country || !viscount_entity_audit.isLatinScriptOnlyCountry(country, coords, profiles))
        return false;

      //Return statement
      return /[\u0400-\u04FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/.test(alias) ||
        /^Ist\s+Pitc/i.test(alias);
    },

    /**
     * Loads compact or legacy resolved batch files from `pass1/`, `pass2/`, or flat `in_dir`,
     * joining compact `[lng, lat]` + `date: string` records against local `batch_index.json` when present.
     * @alias city_metadata_merger.loadIncomingRecords
     *
     * @param {string} arg0_in_dir
     *
     * @returns {{ pass1_records: Array<Object>, pass2_records: Array<Object> }}
     */
    loadIncomingRecords (arg0_in_dir) {
      //Convert from parameters
      let in_dir = arg0_in_dir;

      //Declare local instance variables
      let pass1_records = [];
      let pass2_records = [];

      //Function body
      let loadDir = (arg0_dir, arg1_default_tier) => {
        if (!fs.existsSync(arg0_dir)) return;
        let idx_by_coord = {};
        let idx_path = path.join(arg0_dir, "batch_index.json");
        if (fs.existsSync(idx_path)) {
          try {
            let idx_raw = JSON.parse(fs.readFileSync(idx_path, "utf8"));
            if (idx_raw && idx_raw.by_coord) idx_by_coord = idx_raw.by_coord;
          } catch (e) {}
        }

        let files = fs.readdirSync(arg0_dir).sort();
        for (let i = 0; i < files.length; i++) {
          let fn = files[i];
          if (!/^(?:resolved|out)_batch_\d+\.json$|^resolved_pass2_whg_geohack\.json$/i.test(fn))
            continue;
          let payload = JSON.parse(fs.readFileSync(path.join(arg0_dir, fn), "utf8"));
          let is_p2 = /^resolved_pass2_/i.test(fn) || payload.pass === 2 || payload.pass_tier === "pass2_whg_geohack" || arg1_default_tier === "pass2_whg_geohack";
          let list = Array.isArray(payload.cities) ? payload.cities :
            (Array.isArray(payload.settlements) ? payload.settlements : (Array.isArray(payload) ? payload : []));

          for (let x = 0; x < list.length; x++) {
            let rec = list[x];
            if (!rec || typeof rec !== "object") continue;

            // Normalise compact `{ coords: [lng, lat], names: { "yyyy.m.d": "Name" } }` or legacy `{ coords_lat_lng, historical_names }`
            let lng = NaN;
            let lat = NaN;
            if (Array.isArray(rec.coords) && rec.coords.length >= 2) {
              lng = Number(rec.coords[0]);
              lat = Number(rec.coords[1]);
            } else if (Array.isArray(rec.coords_lat_lng) && rec.coords_lat_lng.length >= 2) {
              lat = Number(rec.coords_lat_lng[0]);
              lng = Number(rec.coords_lat_lng[1]);
            }
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

            let ck = this.coordKey(lng, lat);
            let sidecar = idx_by_coord[ck] || {};
            let norm_rec = {
              canonical_name: rec.canonical_name || rec.name || sidecar.name || "",
              coords_lat_lng: [lat, lng],
              coords_lng_lat: [Number(lng.toFixed(5)), Number(lat.toFixed(5))],
              country: rec.country || sidecar.country || "",
              earliest_year: (rec.earliest_year !== undefined) ? rec.earliest_year : sidecar.earliest_year,
              existing_meta_index: (rec.existing_meta_index !== undefined) ? rec.existing_meta_index : sidecar.existing_meta_index,
              existing_shard_file: rec.existing_shard_file || sidecar.existing_shard_file || null,
              is_capital: Boolean(rec.is_capital || rec.cap || sidecar.is_capital),
              is_pass2: is_p2,
              key: rec.key || sidecar.key || ck,
              known_aliases: Array.isArray(rec.known_aliases) ? rec.known_aliases : (Array.isArray(sidecar.known_aliases) ? sidecar.known_aliases : []),
              latest_year: (rec.latest_year !== undefined) ? rec.latest_year : sidecar.latest_year,
              other_names: Array.isArray(rec.other_names) ? rec.other_names : [],
              raw_history: (rec.names && typeof rec.names === "object") ? rec.names : rec.historical_names,
              verified_settlement: Boolean(rec.verified_settlement || payload.approved_by_auditor)
            };

            if (is_p2) pass2_records.push(norm_rec);
            else pass1_records.push(norm_rec);
          }
        }
      };

      let p1_sub = path.join(in_dir, "pass1");
      let p2_sub = path.join(in_dir, "pass2");
      if (fs.existsSync(p1_sub)) loadDir(p1_sub, "pass1_swarm");
      if (fs.existsSync(p2_sub)) loadDir(p2_sub, "pass2_whg_geohack");
      loadDir(in_dir, "pass1_swarm");

      //Return statement
      return { pass1_records: pass1_records, pass2_records: pass2_records };
    },

    /**
     * Normalises a settlement name for phonetic matching.
     * @alias city_metadata_merger.normaliseName
     *
     * @param {string} arg0_name
     *
     * @returns {string}
     */
    normaliseName (arg0_name) {
      //Return statement
      return String(arg0_name || "")
        .replace(/\s*\([^)]*\)/g, "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/j/g, "y")
        .replace(/ya/g, "a")
        .replace(/ye/g, "e")
        .replace(/yo/g, "o")
        .replace(/yu/g, "u")
        .replace(/ch/g, "c")
        .replace(/sh/g, "s")
        .replace(/zh/g, "z")
        .replace(/[^a-z0-9]/g, "");
    },

    /**
     * Parses CLI flags for `merge_city_metadata.js`.
     * @alias city_metadata_merger.parseCliArgs
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
        dataset: "stadester_2.0",
        dataview_root: "",
        dry_run: false,
        in_dir: "",
        project: "",
        require_auditor_signoff: false,
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project=")) args.project = tok.slice(10).trim().toUpperCase();
        else if (tok === "--project" && i + 1 < argv.length) args.project = argv[++i].trim().toUpperCase();
        else if (tok.startsWith("--dataset=")) args.dataset = tok.slice(10).trim();
        else if (tok.startsWith("--in-dir=")) args.in_dir = tok.slice(9).trim();
        else if (tok.startsWith("--svea-root=")) args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataview-root=")) args.dataview_root = tok.slice(16).trim();
        else if (tok === "--dry-run") args.dry_run = true;
        else if (tok === "--require-auditor-signoff") args.require_auditor_signoff = true;
      }

      //Return statement
      return args;
    },

    /**
     * Non-destructively merges and simplifies the entire historical timeline at `[lng, lat]`:
     * - Protects Tier-0 capitals and richer multi-era histories from being truncated or overridden by sparse stubs or sub-districts.
     * - Resolves date ties by priority tier (Pass-1 verified > existing > Pass-2 heuristic) and date specificity (`YYYY.M.D` > `YYYY.1.1`).
     * - Drops consecutive case-insensitive duplicates and orthographic-only noise variants.
     * @alias city_metadata_merger.simplifyHistoryAtCoord
     *
     * @param {Array<Object>} arg0_existing_hist
     * @param {Array<Object>} arg1_incoming_hist
     * @param {Object} [arg2_options]
     *  @param {boolean} [arg2_options.existing_is_capital=false]
     *  @param {boolean} [arg2_options.incoming_is_pass2=false]
     *  @param {boolean} [arg2_options.incoming_is_auditor_verified=false]
     *  @param {Array<RegExp>} [arg2_options.mun_regexes]
     *  @param {Array<string>} [arg2_options.dropped_variants]
     *
     * @returns {Array<{ date: string, name: string }>}
     */
    simplifyHistoryAtCoord (arg0_existing_hist, arg1_incoming_hist, arg2_options) {
      //Convert from parameters
      let existing_hist = Array.isArray(arg0_existing_hist) ? arg0_existing_hist : [];
      let incoming_hist = Array.isArray(arg1_incoming_hist) ? arg1_incoming_hist : [];
      let opts = (arg2_options) ? arg2_options : {};

      //Declare local instance variables
      let dropped_variants = Array.isArray(opts.dropped_variants) ? opts.dropped_variants : null;
      let existing_is_capital = Boolean(opts.existing_is_capital);
      let incoming_is_pass2 = Boolean(opts.incoming_is_pass2);
      let incoming_verified = Boolean(opts.incoming_is_auditor_verified);
      let mun_regexes = Array.isArray(opts.mun_regexes) ? opts.mun_regexes : [];

      //Function body
      // Filter any stale intra-municipal district intrusions from existing history first
      let clean_existing = [];
      for (let i = 0; i < existing_hist.length; i++) {
        let e = existing_hist[i];
        if (!e || !e.date || !e.name) continue;
        let nm = this.stripParenthetical(e.name);
        if (this.isCorruptedCityName(nm) || !viscount_entity_audit.isValidCalendarDate(e.date)) continue;
        if (mun_regexes.some(function (arg0_r) { return arg0_r.test(nm); })) {
          if (dropped_variants) dropped_variants.push(nm);
          continue;
        }
        clean_existing.push({ date: String(e.date).trim(), name: nm, prio: existing_is_capital ? 3 : 2 });
      }

      // Pass-2 WHG/GeoHack heuristics NEVER overwrite a capital or an existing multi-entry curated timeline
      if (incoming_is_pass2 && (existing_is_capital || clean_existing.length >= 2))
        return this.sortAndDedupHistoricalNames(clean_existing, dropped_variants);

      let clean_incoming = [];
      for (let i = 0; i < incoming_hist.length; i++) {
        let e = incoming_hist[i];
        if (!e || !e.date || !e.name) continue;
        let nm = this.stripParenthetical(e.name);
        if (this.isCorruptedCityName(nm) || !viscount_entity_audit.isValidCalendarDate(e.date)) continue;
        if (mun_regexes.some(function (arg0_r) { return arg0_r.test(nm); })) continue;
        clean_incoming.push({ date: String(e.date).trim(), name: nm, prio: incoming_verified ? 4 : (incoming_is_pass2 ? 1 : 2) });
      }

      // Guard: a sparse single-entry incoming stub must never erase a richer existing multi-era history
      if (clean_existing.length >= 2 && clean_incoming.length <= 1 && !incoming_verified)
        return this.sortAndDedupHistoricalNames(clean_existing, dropped_variants);

      // Union full history when merging (or adopt auditor-verified full replacement if it covers earliest span)
      let combined = [];
      if (incoming_verified && clean_incoming.length > 0 && clean_existing.length > 0) {
        let ex_min_y = this.dateSortTuple(clean_existing[0].date)[0];
        let in_min_y = this.dateSortTuple(clean_incoming[0].date)[0];
        if (in_min_y <= ex_min_y + 50 && clean_incoming.length >= clean_existing.length) {
          combined = clean_incoming;
        } else {
          combined = clean_existing.concat(clean_incoming);
        }
      } else {
        combined = clean_existing.concat(clean_incoming);
      }

      // Resolve exact same-date collisions by priority tier, then date specificity
      let by_date = new Map();
      for (let i = 0; i < combined.length; i++) {
        let item = combined[i];
        let prev = by_date.get(item.date);
        if (!prev || item.prio > prev.prio)
          by_date.set(item.date, item);
      }

      //Return statement
      return this.sortAndDedupHistoricalNames(Array.from(by_date.values()), dropped_variants);
    },

    /**
     * Validates and merges Pass-1 & Pass-2 resolved toponymy outputs into partitioned `city_metadata/`
     * (`00_capitals.json` + target regional shard) in full Dataview-compatible JSON format,
     * simplifying full timelines at `[lng, lat]` and deduplicating `.other_names` case-insensitively.
     * @alias city_metadata_merger.runMerge
     *
     * @param {Object} [arg0_options]
     *
     * @returns {Object}
     */
    runMerge (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let counts = {
        cache_files_removed: 0,
        inserted: 0,
        pass1_applied: 0,
        pass2_applied: 0,
        protected_capitals_preserved: 0,
        rejected_items: 0,
        rejected_name_entries: 0,
        updated: 0
      };
      let dataset_id = (options.dataset) ? String(options.dataset).replace(/\.json$/i, "") : "stadester_2.0";
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let mun_rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
      let overlay_policy = (profiles && profiles.overlay_binding_policy) ? profiles.overlay_binding_policy : {};
      let snap_km = Number(mun_rules.municipal_coord_snap_km) || 2.5;
      let max_match_km = Number(overlay_policy.default_max_radius_km) || 10.0;
      let mun_regexes = (Array.isArray(mun_rules.intra_municipal_suffix_regexes) ? mun_rules.intra_municipal_suffix_regexes : []).map(function (arg0_r) {
        return new RegExp(arg0_r, "i");
      });

      let project_slug = options.project ? options.project.toLowerCase() : "all_projects";
      let shard_prefix = "";
      let prec_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
      if (options.project && fs.existsSync(prec_path)) {
        let prec = JSON5.parse(fs.readFileSync(prec_path, "utf8"));
        let plist = Array.isArray(prec.projects) ? prec.projects : [];
        for (let i = 0; i < plist.length; i++) {
          if (String(plist[i].key || "").toUpperCase() === options.project) {
            if (plist[i].slug) project_slug = plist[i].slug;
            if (plist[i].shard_prefix) shard_prefix = plist[i].shard_prefix;
            break;
          }
        }
      }

      let in_dir = (options.in_dir) ? path.resolve(options.in_dir) :
        path.join(svea_root, "tests/toponymy_batches", project_slug);
      let stadester_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let part_dir = path.join(stadester_dir, "city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let mono_path = fs.existsSync(path.join(stadester_dir, "city_metadata.json")) ?
        path.join(stadester_dir, "city_metadata.json") :
        path.join(dataview_root, "data/stadester/city_metadata.json");
      let is_partitioned = fs.existsSync(man_path);

      //Guard clauses
      if (!fs.existsSync(in_dir)) {
        console.error(`[merge_city_metadata] Input batch directory not found: ${in_dir}`);
        return counts;
      }
      if (options.require_auditor_signoff) {
        let p1_so = path.join(in_dir, "pass1", "auditor_signoff.json");
        let flat_so = path.join(in_dir, "auditor_signoff.json");
        let signoff_p = fs.existsSync(p1_so) ? p1_so : flat_so;
        if (!fs.existsSync(signoff_p)) {
          console.error(`[merge_city_metadata] Refusing merge without Pass-1 separate toponymy_auditor sign-off: ${signoff_p}`);
          return counts;
        }
        let so = JSON.parse(fs.readFileSync(signoff_p, "utf8"));
        if (so.approved !== true || Number(so.errors_remaining || 0) !== 0) {
          console.error(`[merge_city_metadata] Refusing merge: auditor_signoff.json not approved or errors_remaining=${so.errors_remaining}`);
          return counts;
        }
      }
      if (!is_partitioned && !fs.existsSync(mono_path)) {
        console.error(`[merge_city_metadata] Dataview city_metadata not found in ${stadester_dir}`);
        return counts;
      }

      //Function body
      let incoming = this.loadIncomingRecords(in_dir);
      // Apply Pass-1 verified records FIRST, then Pass-2 WHG/GeoHack heuristics (which cannot override Pass-1/Capitals)
      let ordered_records = incoming.pass1_records.concat(incoming.pass2_records);
      if (ordered_records.length === 0) {
        console.error(`[merge_city_metadata] No resolved Pass-1 or Pass-2 files found in ${in_dir}`);
        return counts;
      }

      let manifest = is_partitioned ? JSON.parse(fs.readFileSync(man_path, "utf8")) : null;
      let shard_arrays = new Map();
      let dirty_shards = new Set();
      let target_region_file = "15_unassigned.json";

      if (is_partitioned) {
        let shards = Array.isArray(manifest.shards) ? manifest.shards : [];
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          let is_cap = sh.key === "CAPITALS" || sh.file === "00_capitals.json";
          if (sh.key === options.project) target_region_file = sh.file;
          if (!options.project || is_cap || sh.key === options.project || sh.key === "UNASSIGNED") {
            let sp = path.join(part_dir, sh.file);
            shard_arrays.set(sh.file, fs.existsSync(sp) ? JSON.parse(fs.readFileSync(sp, "utf8")) : []);
          }
        }
      } else {
        target_region_file = "city_metadata.json";
        shard_arrays.set("city_metadata.json", JSON.parse(fs.readFileSync(mono_path, "utf8")));
      }

      let spatial_grid = new Map();
      shard_arrays.forEach(function (arg0_arr, arg1_file) {
        let is_cap_shard = arg1_file === "00_capitals.json";
        for (let i = 0; i < arg0_arr.length; i++) {
          let entry = arg0_arr[i];
          if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;
          let lat = Number(entry.coords[1]);
          let lng = Number(entry.coords[0]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
          let gkey = `${Math.round(lat*2)},${Math.round(lng*2)}`;
          if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
          spatial_grid.get(gkey).push({ entry: entry, index: i, is_cap_shard: is_cap_shard, lat: lat, lng: lng, shard_file: arg1_file });
        }
      });

      for (let i = 0; i < ordered_records.length; i++) {
        let rec = ordered_records[i];
        let clat = Number(rec.coords_lat_lng[0]);
        let clng = Number(rec.coords_lat_lng[1]);
        let coerced = this.coerceHistoryEntries(rec.raw_history, mun_regexes, profiles, rec.verified_settlement);
        counts.rejected_name_entries += coerced.dropped;
        if (coerced.entries.length === 0) {
          counts.rejected_items++;
          continue;
        }

        let dropped_variants = [];
        let incoming_sorted = this.sortAndDedupHistoricalNames(coerced.entries, dropped_variants);
        let derived_modern = incoming_sorted[incoming_sorted.length - 1].name;
        let clean_modern = this.stripParenthetical(derived_modern || rec.canonical_name || "");
        if (this.isCorruptedCityName(clean_modern) || this.NON_LATIN_RE.test(clean_modern)) {
          counts.rejected_items++;
          continue;
        }
        if (!rec.verified_settlement && mun_regexes.some(function (arg0_r) { return arg0_r.test(clean_modern); })) {
          counts.rejected_items++;
          continue;
        }

        // Match existing municipal-cluster record across loaded shards (Tier-0 capitals strictly prioritised)
        let matched_ref = null;
        let pref_shard = rec.existing_shard_file || (is_partitioned ? target_region_file : "city_metadata.json");
        if (Number.isInteger(rec.existing_meta_index) && shard_arrays.has(pref_shard)) {
          let arr = shard_arrays.get(pref_shard);
          let indexed = arr[rec.existing_meta_index];
          if (indexed && Array.isArray(indexed.coords) && indexed.coords.length >= 2) {
            let d = viscount_audit_utils.haversineKm(clat, clng, indexed.coords[1], indexed.coords[0]);
            if (d <= max_match_km)
              matched_ref = { entry: indexed, index: rec.existing_meta_index, is_cap_shard: pref_shard === "00_capitals.json", shard_file: pref_shard };
          }
        }

        if (!matched_ref) {
          let gx = Math.round(clat*2);
          let gy = Math.round(clng*2);
          let best_dist = 999999;
          let best_is_cap = false;
          let rec_norm = this.normaliseName(clean_modern);

          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              let bucket = spatial_grid.get(`${gx + dx},${gy + dy}`);
              if (!bucket) continue;
              for (let y = 0; y < bucket.length; y++) {
                let cand = bucket[y];
                let d = viscount_audit_utils.haversineKm(clat, clng, cand.lat, cand.lng);
                if (d > max_match_km) continue;
                let c_norm = this.normaliseName(cand.entry.name);
                let stems_match = Boolean(rec_norm && c_norm && (c_norm === rec_norm || viscount_entity_audit.areEquivalentExonyms(clean_modern, cand.entry.name, profiles)));
                let qualifies = (d <= snap_km) || (d <= max_match_km && stems_match);
                if (!qualifies) continue;

                if ((cand.is_cap_shard && !best_is_cap && d <= snap_km) || (cand.is_cap_shard === best_is_cap && d < best_dist)) {
                  best_dist = d;
                  best_is_cap = cand.is_cap_shard;
                  matched_ref = cand;
                }
              }
            }
          }
        }

        if (matched_ref) {
          let target = matched_ref.entry;
          let target_is_capital = matched_ref.is_cap_shard || this.hasCapitalTimeline(target);

          // Pass-2 heuristics MUST NOT overwrite a Tier-0 capital record
          if (rec.is_pass2 && target_is_capital) {
            counts.protected_capitals_preserved++;
            continue;
          }

          let existing_hist = this.coerceHistoryEntries(target.historical_names || target.names, [], profiles, true).entries;
          let simplified_hist = this.simplifyHistoryAtCoord(existing_hist, incoming_sorted, {
            dropped_variants: dropped_variants,
            existing_is_capital: target_is_capital,
            incoming_is_auditor_verified: Boolean(!rec.is_pass2 && rec.verified_settlement),
            incoming_is_pass2: rec.is_pass2,
            mun_regexes: mun_regexes
          });

          if (simplified_hist.length === 0) continue;
          target.historical_names = simplified_hist;

          let terminal_name = simplified_hist[simplified_hist.length - 1].name;
          let can_update_name = Boolean(
            terminal_name &&
            !this.hasArchSiteQualifier(terminal_name) &&
            !mun_regexes.some(function (arg0_r) { return arg0_r.test(terminal_name); }) &&
            (!target_is_capital || (!rec.is_pass2 && rec.verified_settlement) || this.isCorruptedCityName(target.name))
          );
          if (can_update_name) target.name = terminal_name;
          if (rec.country && !target.country) target.country = rec.country;

          let raw_aliases = []
            .concat(Array.isArray(target.other_names) ? target.other_names : [])
            .concat(rec.known_aliases)
            .concat(rec.other_names)
            .concat(dropped_variants);
          let clean_other = this.deduplicateOtherNamesCI(target.name, target.historical_names, raw_aliases, target.country || rec.country, rec.coords_lat_lng);
          if (clean_other.length > 0) target.other_names = clean_other;
          else delete target.other_names;

          dirty_shards.add(matched_ref.shard_file);
          counts.updated++;
        } else {
          let dest_file = (is_partitioned && rec.is_capital) ? "00_capitals.json" : target_region_file;
          if (!shard_arrays.has(dest_file)) shard_arrays.set(dest_file, []);
          let dest_arr = shard_arrays.get(dest_file);
          let new_entry = {
            coords: [Number(clng.toFixed(5)), Number(clat.toFixed(5))],
            country: rec.country || "",
            historical_names: incoming_sorted,
            name: clean_modern
          };
          if (options.project) new_entry.region_shard = options.project;

          let raw_aliases = [].concat(rec.known_aliases).concat(rec.other_names).concat(dropped_variants);
          let clean_other = this.deduplicateOtherNamesCI(clean_modern, incoming_sorted, raw_aliases, rec.country, rec.coords_lat_lng);
          if (clean_other.length > 0) new_entry.other_names = clean_other;

          let new_idx = dest_arr.length;
          dest_arr.push(new_entry);
          let gkey = `${Math.round(clat*2)},${Math.round(clng*2)}`;
          if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
          spatial_grid.get(gkey).push({ entry: new_entry, index: new_idx, is_cap_shard: dest_file === "00_capitals.json", lat: clat, lng: clng, shard_file: dest_file });

          dirty_shards.add(dest_file);
          counts.inserted++;
        }

        if (rec.is_pass2) counts.pass2_applied++;
        else counts.pass1_applied++;
      }

      if (!options.dry_run && dirty_shards.size > 0) {
        if (is_partitioned) {
          let shards = Array.isArray(manifest.shards) ? manifest.shards : [];
          dirty_shards.forEach(function (arg0_sf) {
            let arr = shard_arrays.get(arg0_sf) || [];
            let json_str = JSON.stringify(arr, null, 2);
            let tmp_p = path.join(part_dir, `${arg0_sf}.tmp`);
            fs.writeFileSync(tmp_p, json_str, "utf8");
            fs.renameSync(tmp_p, path.join(part_dir, arg0_sf));
            let sha = crypto.createHash("sha256").update(json_str).digest("hex");
            for (let i = 0; i < shards.length; i++) {
              if (shards[i].file === arg0_sf) {
                shards[i].count = arr.length;
                shards[i].sha256 = sha;
                break;
              }
            }
          });
          manifest.updated_at_gmt0 = new Date().toISOString();
          fs.writeFileSync(man_path, JSON.stringify(manifest, null, 2), "utf8");
        } else {
          let tmp_p = `${mono_path}.tmp`;
          fs.writeFileSync(tmp_p, JSON.stringify(shard_arrays.get("city_metadata.json") || [], null, 2), "utf8");
          fs.renameSync(tmp_p, mono_path);
        }

        let shard_cache_dir = path.join(dataview_root, "data/stadester/cache", dataset_id, "shards");
        if (fs.existsSync(shard_cache_dir) && shard_prefix) {
          let cfiles = fs.readdirSync(shard_cache_dir);
          for (let i = 0; i < cfiles.length; i++) {
            if (cfiles[i].toLowerCase().startsWith(shard_prefix.toLowerCase())) {
              fs.unlinkSync(path.join(shard_cache_dir, cfiles[i]));
              counts.cache_files_removed++;
            }
          }
        }
      }

      console.log(
        `[merge_city_metadata] Updated ${counts.updated}, inserted ${counts.inserted} ` +
        `(pass1=${counts.pass1_applied}, pass2=${counts.pass2_applied}, protected_capitals=${counts.protected_capitals_preserved}, rejected=${counts.rejected_items}), ` +
        `dirty shards [${Array.from(dirty_shards).join(", ")}].`
      );

      //Return statement
      return counts;
    },

    /**
     * Sorts historical name entries chronologically and collapses consecutive case-insensitive or phonetic-variant duplicates.
     * @alias city_metadata_merger.sortAndDedupHistoricalNames
     *
     * @param {Array<Object>} arg0_entries
     * @param {Array<string>} [arg1_dropped_variants]
     *
     * @returns {Array<{ date: string, name: string }>}
     */
    sortAndDedupHistoricalNames (arg0_entries, arg1_dropped_variants) {
      //Convert from parameters
      let dropped_variants = Array.isArray(arg1_dropped_variants) ? arg1_dropped_variants : null;
      let entries = Array.isArray(arg0_entries) ? arg0_entries.slice() : [];

      //Function body
      let seen_date_name = new Set();
      let unique_entries = [];
      for (let i = 0; i < entries.length; i++) {
        let e = entries[i];
        let sig = `${e.date}|${String(e.name || "").toLowerCase()}`;
        if (!seen_date_name.has(sig)) {
          seen_date_name.add(sig);
          unique_entries.push({ date: e.date, name: e.name });
        }
      }

      let that = this;
      unique_entries.sort(function (arg0_a, arg1_b) {
        let ta = that.dateSortTuple(arg0_a.date);
        let tb = that.dateSortTuple(arg1_b.date);
        if (ta[0] !== tb[0]) return ta[0] - tb[0];
        if (ta[1] !== tb[1]) return ta[1] - tb[1];
        return ta[2] - tb[2];
      });

      let deduped = [];
      for (let i = 0; i < unique_entries.length; i++) {
        let cur = unique_entries[i];
        if (deduped.length > 0) {
          let prev = deduped[deduped.length - 1];
          let prev_stem = viscount_entity_audit.normaliseEntityStem(prev.name);
          let cur_stem = viscount_entity_audit.normaliseEntityStem(cur.name);
          if (prev.name.toLowerCase() === cur.name.toLowerCase() || (prev_stem && cur_stem && prev_stem === cur_stem)) {
            if (dropped_variants && cur.name.toLowerCase() !== prev.name.toLowerCase())
              dropped_variants.push(cur.name);
            continue;
          }
        }
        deduped.push(cur);
      }

      //Return statement
      return deduped;
    },

    /**
     * Strips parenthetical qualifiers from a settlement name and trims whitespace.
     * @alias city_metadata_merger.stripParenthetical
     *
     * @param {string} arg0_name
     *
     * @returns {string}
     */
    stripParenthetical (arg0_name) {
      //Return statement
      return String(arg0_name || "").replace(/\s*\([^)]*\)/g, "").trim();
    }
  };

  if (require.main === module) {
    let cli_args = city_metadata_merger.parseCliArgs(process.argv.slice(2));
    city_metadata_merger.runMerge(cli_args);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_merger: city_metadata_merger };
  }
}
