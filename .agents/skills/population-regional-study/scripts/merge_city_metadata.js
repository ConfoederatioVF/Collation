//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise functions
{
  let city_metadata_merger = {
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
      let date_str = String(arg0_date_str || "");

      //Function body
      let parts = date_str.split(".");
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
      //Convert from parameters
      let raw_name = String(arg0_name || "");

      //Return statement
      return /\b(Site|Gorodishche|Kurgan|Mound|Cemetery|Frontier|Ford|Steppe|Approach|Castle|Hillfort|Barrow|Shelter|Complex|Terrace|Bronze|Palaeolithic|Neolithic)\b/i.test(raw_name);
    },

    /**
     * Computes great-circle Haversine distance in kilometres between two `[lat, lng]` points.
     * @alias city_metadata_merger.haversineKm
     *
     * @param {number} arg0_lat1
     * @param {number} arg1_lng1
     * @param {number} arg2_lat2
     * @param {number} arg3_lng2
     *
     * @returns {number}
     */
    haversineKm (arg0_lat1, arg1_lng1, arg2_lat2, arg3_lng2) {
      //Convert from parameters
      let lat1 = Number(arg0_lat1);
      let lng1 = Number(arg1_lng1);
      let lat2 = Number(arg2_lat2);
      let lng2 = Number(arg3_lng2);

      //Declare local instance variables
      let d_lat = (lat2 - lat1)*Math.PI/180;
      let d_lng = (lng2 - lng1)*Math.PI/180;
      let rad1 = lat1*Math.PI/180;
      let rad2 = lat2*Math.PI/180;

      //Function body
      let a = Math.sin(d_lat/2)*Math.sin(d_lat/2) +
        Math.cos(rad1)*Math.cos(rad2)*Math.sin(d_lng/2)*Math.sin(d_lng/2);

      //Return statement
      return 6371*2*Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    },

    /**
     * Mirrors Dataview `isCorruptedCityName`: returns true when name is corrupted and must be rejected.
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

      //Return statement
      return false;
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
      //Convert from parameters
      let raw_name = arg0_name;

      //Return statement
      return String(raw_name || "")
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
        svea_root: ""
      };

      //Function body
      for (let i = 0; i < argv.length; i++) {
        let tok = String(argv[i] || "");
        if (tok.startsWith("--project="))
          args.project = tok.slice(10).trim().toUpperCase();
        else if (tok.startsWith("--dataset="))
          args.dataset = tok.slice(10).trim();
        else if (tok.startsWith("--in-dir="))
          args.in_dir = tok.slice(9).trim();
        else if (tok.startsWith("--svea-root="))
          args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataview-root="))
          args.dataview_root = tok.slice(16).trim();
        else if (tok === "--dry-run")
          args.dry_run = true;
      }

      //Return statement
      return args;
    },

    /**
     * Validates and merges Gemini Flash toponymy outputs into Dataview per-version `city_metadata.json`,
     * transposing SVEA `[lat, lng]` coordinates to Dataview `[lng, lat]` and clearing stale caches for that version.
     * @alias city_metadata_merger.runMerge
     *
     * @param {Object} [arg0_options]
     *  @param {string} [arg0_options.dataset="stadester_2.0"]
     *  @param {string} [arg0_options.dataview_root]
     *  @param {boolean} [arg0_options.dry_run=false]
     *  @param {string} [arg0_options.in_dir]
     *  @param {string} [arg0_options.project]
     *  @param {string} [arg0_options.svea_root]
     *
     * @returns {Object} Merge summary counters
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
        path.resolve(__dirname, "../../../..");
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) :
          path.resolve(svea_root, "../Project 1436 - Dataview"));

      let project_slug = options.project ? options.project.toLowerCase() : "all_projects";
      let prec_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");
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

      let in_dir = (options.in_dir) ? path.resolve(options.in_dir) :
        path.join(svea_root, "tests/toponymy_batches", project_slug);
      let versioned_meta_dir = path.join(dataview_root, "data/stadester", dataset_id);
      let meta_path = fs.existsSync(versioned_meta_dir) ?
        path.join(versioned_meta_dir, "city_metadata.json") :
        path.join(dataview_root, "data/stadester/city_metadata.json");
      let cache_dir = path.join(dataview_root, "data/stadester/cache");

      //Guard clauses
      if (!fs.existsSync(in_dir)) {
        console.error(`[merge_city_metadata] Input batch directory not found: ${in_dir}`);
        return counts;
      }
      if (!fs.existsSync(meta_path)) {
        console.error(`[merge_city_metadata] Dataview city_metadata.json not found: ${meta_path}`);
        return counts;
      }

      //Function body
      let meta_array = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      let all_files = fs.readdirSync(in_dir).sort();
      let resolved_files = all_files.filter(function (arg0_f) {
        return /^resolved_batch_\d+\.json$/i.test(arg0_f);
      });
      if (resolved_files.length === 0) {
        console.error(`[merge_city_metadata] No resolved_batch_*.json files found in ${in_dir}`);
        return counts;
      }

      let spatial_grid = new Map();
      for (let i = 0; i < meta_array.length; i++) {
        let entry = meta_array[i];
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;
        let lat = Number(entry.coords[1]);
        let lng = Number(entry.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

        let gx = Math.round(lat*2);
        let gy = Math.round(lng*2);
        let gkey = `${gx},${gy}`;
        if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
        spatial_grid.get(gkey).push({ entry: entry, index: i, lat: lat, lng: lng });
      }

      for (let i = 0; i < resolved_files.length; i++) {
        let payload = JSON.parse(fs.readFileSync(path.join(in_dir, resolved_files[i]), "utf8"));
        let records = Array.isArray(payload.settlements) ? payload.settlements :
          (Array.isArray(payload) ? payload : []);

        for (let x = 0; x < records.length; x++) {
          let rec = records[x];
          if (!rec || !Array.isArray(rec.coords_lat_lng) || rec.coords_lat_lng.length < 2) {
            console.error("[merge_city_metadata] Skipping record without valid coords_lat_lng:", rec && rec.key);
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

          let raw_hist = Array.isArray(rec.historical_names) ? rec.historical_names : [];
          let valid_hist = [];
          for (let y = 0; y < raw_hist.length; y++) {
            let h = raw_hist[y];
            if (!h || typeof h !== "object") {
              counts.rejected_name_entries++;
              continue;
            }
            let h_date = String(h.date || "").trim();
            let h_name = this.stripParenthetical(h.name || "");
            if (!date_regex.test(h_date) || this.isCorruptedCityName(h_name)) {
              console.error(`[merge_city_metadata] Rejected historical entry for ${rec.key}: date="${h_date}" name="${h_name}"`);
              counts.rejected_name_entries++;
              continue;
            }
            valid_hist.push({ date: h_date, name: h_name });
          }

          if (valid_hist.length === 0) {
            console.error(`[merge_city_metadata] No valid historical_names remained for ${rec.key}; skipping.`);
            counts.rejected_items++;
            continue;
          }

          let promoted_site_alias = "";
          let sorted_hist = this.sortAndDedupHistoricalNames(valid_hist);
          if (sorted_hist.length > 0 && this.hasArchSiteQualifier(clean_modern)) {
            let last_hist = sorted_hist[sorted_hist.length - 1];
            let last_year = this.dateSortTuple(last_hist.date)[0];
            if (last_year >= 1400 && !this.isCorruptedCityName(last_hist.name) && !this.hasArchSiteQualifier(last_hist.name)) {
              promoted_site_alias = clean_modern;
              clean_modern = last_hist.name;
            }
          }

          let existing_idx = null;
          if (Number.isInteger(rec.existing_meta_index) &&
              rec.existing_meta_index >= 0 &&
              rec.existing_meta_index < meta_array.length) {
            let indexed = meta_array[rec.existing_meta_index];
            if (indexed && Array.isArray(indexed.coords) && indexed.coords.length >= 2) {
              let dist = this.haversineKm(clat, clng, indexed.coords[1], indexed.coords[0]);
              if (dist <= 25.0) existing_idx = rec.existing_meta_index;
            }
          }

          if (existing_idx === null) {
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
                  let d = this.haversineKm(clat, clng, cand.lat, cand.lng);
                  let c_norm = this.normaliseName(cand.entry.name);
                  let target_is_corrupt_or_arch = this.isCorruptedCityName(cand.entry.name) || this.hasArchSiteQualifier(cand.entry.name);
                  let stems_match = Boolean(rec_norm && c_norm && c_norm === rec_norm);
                  if ((d <= 2.5 && (target_is_corrupt_or_arch || stems_match)) || (d <= 25.0 && stems_match)) {
                    if (d < best_dist) {
                      best_dist = d;
                      existing_idx = cand.index;
                    }
                  }
                }
              }
            }
          }

          let clean_aliases = [];
          let raw_aliases = []
            .concat(Array.isArray(rec.known_aliases) ? rec.known_aliases : [])
            .concat(Array.isArray(rec.other_names) ? rec.other_names : []);
          if (promoted_site_alias && !this.isCorruptedCityName(promoted_site_alias) && promoted_site_alias !== clean_modern)
            clean_aliases.push(promoted_site_alias);
          for (let y = 0; y < raw_aliases.length; y++) {
            let a_str = this.stripParenthetical(raw_aliases[y]);
            if (!this.isCorruptedCityName(a_str) && a_str !== clean_modern) clean_aliases.push(a_str);
          }
          for (let y = 0; y < valid_hist.length; y++) {
            if (valid_hist[y].name !== clean_modern) clean_aliases.push(valid_hist[y].name);
          }

          if (existing_idx !== null) {
            let target = meta_array[existing_idx];
            let is_arch_qualifier = this.hasArchSiteQualifier(clean_modern);
            if (!is_arch_qualifier &&
                (this.isCorruptedCityName(target.name) || this.hasArchSiteQualifier(target.name))) {
              target.name = clean_modern;
            }

            let combined_hist = [];
            let existing_hist = Array.isArray(target.historical_names) ? target.historical_names : [];
            for (let y = 0; y < existing_hist.length; y++) {
              let eh = existing_hist[y];
              if (eh && date_regex.test(String(eh.date || "").trim()) && !this.isCorruptedCityName(this.stripParenthetical(eh.name || "")))
                combined_hist.push({ date: String(eh.date).trim(), name: this.stripParenthetical(eh.name) });
            }
            for (let y = 0; y < valid_hist.length; y++) combined_hist.push(valid_hist[y]);

            target.historical_names = this.sortAndDedupHistoricalNames(combined_hist);

            let prev_other = Array.isArray(target.other_names) ? target.other_names : [];
            let merged_other = [];
            for (let y = 0; y < prev_other.length; y++) {
              let po = this.stripParenthetical(prev_other[y]);
              if (!this.isCorruptedCityName(po) && po !== target.name) merged_other.push(po);
            }
            for (let y = 0; y < clean_aliases.length; y++) merged_other.push(clean_aliases[y]);
            if (merged_other.length > 0) target.other_names = Array.from(new Set(merged_other));

            counts.updated++;
          } else {
            let new_entry = {
              coords: [Number(clng.toFixed(5)), Number(clat.toFixed(5))],
              historical_names: this.sortAndDedupHistoricalNames(valid_hist),
              name: clean_modern
            };
            if (clean_aliases.length > 0) new_entry.other_names = Array.from(new Set(clean_aliases));

            let new_idx = meta_array.length;
            meta_array.push(new_entry);

            let gx = Math.round(clat*2);
            let gy = Math.round(clng*2);
            let gkey = `${gx},${gy}`;
            if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
            spatial_grid.get(gkey).push({ entry: new_entry, index: new_idx, lat: clat, lng: clng });

            counts.inserted++;
          }
        }
      }

      if (!options.dry_run) {
        fs.writeFileSync(meta_path, JSON.stringify(meta_array, null, 2), "utf8");
        if (fs.existsSync(cache_dir)) {
          let stale_names = [
            `${dataset_id}_lite.json`,
            `${dataset_id}_indexed.json`,
            "stadester_city_cache.json"
          ];
          for (let i = 0; i < stale_names.length; i++) {
            let stale_path = path.join(cache_dir, stale_names[i]);
            if (fs.existsSync(stale_path)) {
              fs.unlinkSync(stale_path);
              counts.cache_files_removed++;
            }
          }
        }
      }

      console.log(`[merge_city_metadata] Updated ${counts.updated}, inserted ${counts.inserted}, rejected items ${counts.rejected_items}, rejected name entries ${counts.rejected_name_entries}, removed ${counts.cache_files_removed} cache file(s) for ${dataset_id}.`);

      //Return statement
      return counts;
    },

    /**
     * Sorts historical name entries chronologically and collapses consecutive duplicate names.
     * @alias city_metadata_merger.sortAndDedupHistoricalNames
     *
     * @param {Array<Object>} arg0_entries
     *
     * @returns {Array<Object>}
     */
    sortAndDedupHistoricalNames (arg0_entries) {
      //Convert from parameters
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
        if (deduped.length > 0 && deduped[deduped.length - 1].name === cur.name) continue;
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
      //Convert from parameters
      let raw_name = String(arg0_name || "");

      //Return statement
      return raw_name.replace(/\s*\([^)]*\)/g, "").trim();
    }
  };

  if (require.main === module) {
    let cli_args = city_metadata_merger.parseCliArgs(process.argv.slice(2));
    city_metadata_merger.runMerge(cli_args);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { city_metadata_merger: city_metadata_merger };
  }
}
