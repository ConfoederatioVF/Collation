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
     * Validates and merges resolved toponymy outputs into partitioned `city_metadata/` (`00_capitals.json` +
     * target regional shard) or legacy `city_metadata.json`, invalidating ONLY the modified regional shard caches.
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
        rejected_items: 0,
        rejected_name_entries: 0,
        updated: 0
      };
      let dataset_id = (options.dataset) ? String(options.dataset).replace(/\.json$/i, "") : "stadester_2.0";
      let date_regex = /^-?\d+\.\d+\.\d+$/;
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));

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
        let signoff_p = path.join(in_dir, "auditor_signoff.json");
        if (!fs.existsSync(signoff_p)) {
          console.error(`[merge_city_metadata] Refusing merge without separate toponymy_auditor sign-off: ${signoff_p}`);
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
      let all_files = fs.readdirSync(in_dir).sort();
      let resolved_files = all_files.filter(function (arg0_f) {
        return /^(?:resolved|out)_batch_\d+\.json$/i.test(arg0_f);
      });
      if (resolved_files.length === 0) {
        console.error(`[merge_city_metadata] No resolved_batch_*.json files found in ${in_dir}`);
        return counts;
      }

      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let mun_rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
      let mun_regexes = (Array.isArray(mun_rules.intra_municipal_suffix_regexes) ? mun_rules.intra_municipal_suffix_regexes : []).map(function (arg0_r) {
        return new RegExp(arg0_r, "i");
      });

      // Load active shard buckets (`00_capitals.json` + target region shard when partitioned, else monolithic)
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

      // Build unified spatial index across loaded shards
      let spatial_grid = new Map();
      let replaced_refs = new Set();
      shard_arrays.forEach(function (arg0_arr, arg1_file) {
        for (let i = 0; i < arg0_arr.length; i++) {
          let entry = arg0_arr[i];
          if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;
          let lat = Number(entry.coords[1]);
          let lng = Number(entry.coords[0]);
          if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
          let gkey = `${Math.round(lat*2)},${Math.round(lng*2)}`;
          if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
          spatial_grid.get(gkey).push({ entry: entry, index: i, lat: lat, lng: lng, shard_file: arg1_file });
        }
      });

      for (let i = 0; i < resolved_files.length; i++) {
        let payload = JSON.parse(fs.readFileSync(path.join(in_dir, resolved_files[i]), "utf8"));
        let records = Array.isArray(payload.settlements) ? payload.settlements : (Array.isArray(payload) ? payload : []);

        for (let x = 0; x < records.length; x++) {
          let rec = records[x];
          if (!rec || !Array.isArray(rec.coords_lat_lng) || rec.coords_lat_lng.length < 2) {
            counts.rejected_items++;
            continue;
          }

          let clat = Number(rec.coords_lat_lng[0]);
          let clng = Number(rec.coords_lat_lng[1]);
          let clean_modern = this.stripParenthetical(rec.canonical_name || rec.name || "");
          if (this.isCorruptedCityName(clean_modern)) {
            console.error(`[merge_city_metadata] Rejected corrupted canonical name for ${rec.key}: "${rec.canonical_name || rec.name}"`);
            counts.rejected_items++;
            continue;
          }
          if (!rec.verified_settlement && viscount_entity_audit.isSuspiciousToponym(clean_modern, profiles)) {
            console.error(`[merge_city_metadata] Rejected suspicious canonical name for ${rec.key}: "${clean_modern}"`);
            counts.rejected_items++;
            continue;
          }
          if (!rec.verified_settlement && mun_regexes.some(function (arg0_r) { return arg0_r.test(clean_modern); })) {
            console.error(`[merge_city_metadata] Rejected intra-municipal district name for ${rec.key}: "${clean_modern}"`);
            counts.rejected_items++;
            continue;
          }

          let raw_hist = Array.isArray(rec.historical_names) ? rec.historical_names : [];
          let valid_hist = [];
          let collapsed_variants = [];
          for (let y = 0; y < raw_hist.length; y++) {
            let h = raw_hist[y];
            if (!h || typeof h !== "object") { counts.rejected_name_entries++; continue; }
            let h_date = String(h.date || "").trim();
            let h_name = this.stripParenthetical(h.name || "");
            if (!date_regex.test(h_date) || !viscount_entity_audit.isValidCalendarDate(h_date) || this.isCorruptedCityName(h_name)) {
              counts.rejected_name_entries++;
              continue;
            }
            if (!rec.verified_settlement && viscount_entity_audit.isSuspiciousToponym(h_name, profiles)) {
              counts.rejected_name_entries++;
              continue;
            }
            valid_hist.push({ date: h_date, name: h_name });
          }

          if (valid_hist.length === 0) { counts.rejected_items++; continue; }

          let promoted_site_alias = "";
          let sorted_hist = this.sortAndDedupHistoricalNames(valid_hist, collapsed_variants);
          if (sorted_hist.length > 0 && this.hasArchSiteQualifier(clean_modern)) {
            let last_hist = sorted_hist[sorted_hist.length - 1];
            let last_year = this.dateSortTuple(last_hist.date)[0];
            if (last_year >= 1400 && !this.isCorruptedCityName(last_hist.name) && !this.hasArchSiteQualifier(last_hist.name)) {
              promoted_site_alias = clean_modern;
              clean_modern = last_hist.name;
            }
          }

          let earliest_year = Number(rec.earliest_year);
          if (Number.isFinite(earliest_year) && earliest_year < 1900 && sorted_hist.length > 0) {
            let first_hist_yr = this.dateSortTuple(sorted_hist[0].date)[0];
            if (first_hist_yr > earliest_year + 100) {
              console.error(`[merge_city_metadata] Rejected ${rec.key}: earliest historical_names year (${first_hist_yr}) lags earliest_year (${earliest_year}) by > 100y.`);
              counts.rejected_items++;
              continue;
            }
          }

          let latest_year = Number(rec.latest_year || 0);
          if (latest_year >= 1950 && !rec.is_renamed_post_1950 && sorted_hist.length > 0) {
            let last_entry = sorted_hist[sorted_hist.length - 1];
            if (this.normaliseName(last_entry.name) !== this.normaliseName(clean_modern)) {
              console.error(`[merge_city_metadata] Rejected ${rec.key}: terminal historical name "${last_entry.name}" (${last_entry.date}) mismatches modern "${clean_modern}".`);
              counts.rejected_items++;
              continue;
            }
          }

          // Match existing record across loaded shards
          let matched_ref = null;
          let pref_shard = rec.existing_shard_file || (is_partitioned ? target_region_file : "city_metadata.json");
          if (Number.isInteger(rec.existing_meta_index) && shard_arrays.has(pref_shard)) {
            let arr = shard_arrays.get(pref_shard);
            let indexed = arr[rec.existing_meta_index];
            if (indexed && Array.isArray(indexed.coords) && indexed.coords.length >= 2) {
              let d = viscount_audit_utils.haversineKm(clat, clng, indexed.coords[1], indexed.coords[0]);
              if (d <= 25.0) matched_ref = { entry: indexed, index: rec.existing_meta_index, shard_file: pref_shard };
            }
          }

          if (!matched_ref) {
            let gx = Math.round(clat*2);
            let gy = Math.round(clng*2);
            let best_dist = 999999;
            let rec_norm = this.normaliseName(clean_modern);

            for (let dx = -1; dx <= 1; dx++) {
              for (let dy = -1; dy <= 1; dy++) {
                let bucket = spatial_grid.get(`${gx + dx},${gy + dy}`);
                if (!bucket) continue;
                for (let y = 0; y < bucket.length; y++) {
                  let cand = bucket[y];
                  let d = viscount_audit_utils.haversineKm(clat, clng, cand.lat, cand.lng);
                  let c_norm = this.normaliseName(cand.entry.name);
                  let stems_match = Boolean(rec_norm && c_norm && (c_norm === rec_norm || viscount_entity_audit.areEquivalentExonyms(clean_modern, cand.entry.name, profiles)));
                  if ((d <= 1.5) || (d <= 25.0 && stems_match)) {
                    if (d < best_dist) {
                      best_dist = d;
                      matched_ref = cand;
                    }
                  }
                }
              }
            }
          }

          let clean_aliases = [];
          let raw_aliases = []
            .concat(Array.isArray(rec.known_aliases) ? rec.known_aliases : [])
            .concat(Array.isArray(rec.other_names) ? rec.other_names : [])
            .concat(collapsed_variants);
          if (promoted_site_alias && !this.isCorruptedCityName(promoted_site_alias) && promoted_site_alias !== clean_modern)
            clean_aliases.push(promoted_site_alias);
          for (let y = 0; y < raw_aliases.length; y++) {
            let a_str = this.stripParenthetical(raw_aliases[y]);
            if (!this.isCorruptedCityName(a_str) && !this.isForeignScriptNoiseForCountry(a_str, rec.country, rec.coords_lat_lng) && a_str !== clean_modern)
              clean_aliases.push(a_str);
          }
          for (let y = 0; y < valid_hist.length; y++) {
            if (valid_hist[y].name !== clean_modern) clean_aliases.push(valid_hist[y].name);
          }

          if (matched_ref) {
            let target = matched_ref.entry;
            let ref_sig = `${matched_ref.shard_file}:${matched_ref.index}`;
            if (!this.hasArchSiteQualifier(clean_modern)) target.name = clean_modern;
            if (rec.country && !target.country) target.country = rec.country;

            let should_replace = Boolean((rec.replace_historical_names || true) && !replaced_refs.has(ref_sig) && valid_hist.length > 0);
            if (should_replace) replaced_refs.add(ref_sig);
            let combined_hist = should_replace ? valid_hist.slice() :
              (Array.isArray(target.historical_names) ? target.historical_names.slice() : []).concat(valid_hist);
            target.historical_names = this.sortAndDedupHistoricalNames(combined_hist, collapsed_variants);

            let prev_other = Array.isArray(target.other_names) ? target.other_names : [];
            let merged_other = [];
            for (let y = 0; y < prev_other.length; y++) {
              let po = this.stripParenthetical(prev_other[y]);
              if (!this.isCorruptedCityName(po) && po !== target.name) merged_other.push(po);
            }
            for (let y = 0; y < clean_aliases.length; y++) merged_other.push(clean_aliases[y]);
            if (merged_other.length > 0) target.other_names = Array.from(new Set(merged_other));

            dirty_shards.add(matched_ref.shard_file);
            counts.updated++;
          } else {
            let dest_file = (is_partitioned && rec.is_capital) ? "00_capitals.json" : target_region_file;
            if (!shard_arrays.has(dest_file)) shard_arrays.set(dest_file, []);
            let dest_arr = shard_arrays.get(dest_file);
            let new_entry = {
              coords: [Number(clng.toFixed(5)), Number(clat.toFixed(5))],
              country: rec.country || "",
              historical_names: sorted_hist,
              name: clean_modern
            };
            if (rec.is_capital) new_entry.capital = true;
            if (options.project) new_entry.region_shard = options.project;
            if (clean_aliases.length > 0) new_entry.other_names = Array.from(new Set(clean_aliases));

            let new_idx = dest_arr.length;
            dest_arr.push(new_entry);
            let gkey = `${Math.round(clat*2)},${Math.round(clng*2)}`;
            if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
            spatial_grid.get(gkey).push({ entry: new_entry, index: new_idx, lat: clat, lng: clng, shard_file: dest_file });

            dirty_shards.add(dest_file);
            counts.inserted++;
          }
        }
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

        // Targeted per-shard cache invalidation ONLY (never invalidate unmodified regional namespaces like CENTAUR!)
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

      console.log(`[merge_city_metadata] Updated ${counts.updated}, inserted ${counts.inserted}, rejected items ${counts.rejected_items}, dirty shards [${Array.from(dirty_shards).join(", ")}], invalidated ${counts.cache_files_removed} targeted shard cache file(s).`);

      //Return statement
      return counts;
    },

    /**
     * Sorts historical name entries chronologically and collapses consecutive exact or phonetic-variant duplicates.
     * @alias city_metadata_merger.sortAndDedupHistoricalNames
     *
     * @param {Array<Object>} arg0_entries
     * @param {Array<string>} [arg1_dropped_variants]
     *
     * @returns {Array<Object>}
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
        let sig = `${e.date}|${e.name}`;
        if (!seen_date_name.has(sig)) {
          seen_date_name.add(sig);
          unique_entries.push(e);
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
          if (prev.name === cur.name || (prev_stem && cur_stem && prev_stem === cur_stem)) {
            if (dropped_variants && cur.name !== prev.name) dropped_variants.push(cur.name);
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
