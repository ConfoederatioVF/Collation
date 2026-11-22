//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");
let { viscount_entity_audit } = require("./viscount_entity_and_continuity_audit");

//Initialise functions
{
  let city_metadata_extractor = {
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

      //Return statement
      return true;
    },

    /**
     * Computes great-circle Haversine distance in kilometres between two `[lat, lng]` points.
     * @alias city_metadata_extractor.haversineKm
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
     * Parses `key=value` and `--flag` CLI arguments.
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
        batch_size: 30,
        dataset: "stadester_2.0",
        dataview_root: "",
        out_dir: "",
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
        else if (tok.startsWith("--svea-root="))
          args.svea_root = tok.slice(12).trim();
        else if (tok.startsWith("--dataview-root="))
          args.dataview_root = tok.slice(16).trim();
        else if (tok.startsWith("--batch-size="))
          args.batch_size = Math.max(1, Number(tok.slice(13)) || 30);
        else if (tok.startsWith("--out-dir="))
          args.out_dir = tok.slice(10).trim();
      }

      //Return statement
      return args;
    },

    /**
     * Resolves repository roots, compares Viscount settlements against Dataview per-version `city_metadata.json`,
     * and writes fixed-size JSON batches for Gemini Flash historical toponymy resolution.
     * @alias city_metadata_extractor.runExtraction
     *
     * @param {Object} [arg0_options]
     *  @param {number} [arg0_options.batch_size=30]
     *  @param {string} [arg0_options.dataset="stadester_2.0"]
     *  @param {string} [arg0_options.dataview_root]
     *  @param {string} [arg0_options.out_dir]
     *  @param {string} [arg0_options.project]
     *  @param {string} [arg0_options.svea_root]
     *
     * @returns {Object} Summary statistics and generated batch file list
     */
    runExtraction (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let batch_files = [];
      let batch_size = Math.max(1, Number(options.batch_size) || 30);
      let candidates = [];
      let counts = {
        corrupted_names: 0,
        empty_historical_names: 0,
        missing_entry: 0,
        suspicious_existing_name: 0,
        total_checked: 0,
        under_covered_history: 0,
        up_to_date: 0
      };
      let profiles = viscount_entity_audit.loadSkillProfiles(options.svea_root || path.resolve(__dirname, "../../../.."));
      let dataset_id = (options.dataset) ? String(options.dataset).replace(/\.json$/i, "") : "stadester_2.0";
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        path.resolve(__dirname, "../../../..");
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) :
          path.resolve(svea_root, "../Project 1436 - Dataview"));

      //Guard clauses
      let loader_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/ViscountGazetteerLoader.js");
      let versioned_meta_path = path.join(dataview_root, "data/stadester", dataset_id, "city_metadata.json");
      let legacy_meta_path = path.join(dataview_root, "data/stadester/city_metadata.json");
      let meta_path = fs.existsSync(versioned_meta_path) ? versioned_meta_path : legacy_meta_path;
      let prec_path = path.join(svea_root, "histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5");

      if (!fs.existsSync(loader_path)) {
        console.error(`[extract_missing_city_metadata] ViscountGazetteerLoader not found: ${loader_path}`);
        return { batch_files: [], counts: counts };
      }
      if (!fs.existsSync(meta_path)) {
        console.error(`[extract_missing_city_metadata] Dataview city_metadata.json not found: ${meta_path}`);
        return { batch_files: [], counts: counts };
      }

      //Function body
      require(loader_path);
      let load_opts = { project_root: svea_root };
      if (options.project) load_opts.only_project = options.project;

      let settlements_obj = global.ViscountGazetteerLoader.getViscountRegionalObject(load_opts);
      let settlement_keys = Object.keys(settlements_obj);
      let raw_meta = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      let spatial_grid = new Map();

      for (let i = 0; i < raw_meta.length; i++) {
        let entry = raw_meta[i];
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;

        let lat = Number(entry.coords[1]);
        let lng = Number(entry.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

        let norm_set = new Set();
        let phon_set = new Set();
        let all_alias_strings = [entry.name];
        if (Array.isArray(entry.other_names)) all_alias_strings = all_alias_strings.concat(entry.other_names);
        if (Array.isArray(entry.historical_names)) {
          for (let x = 0; x < entry.historical_names.length; x++) {
            if (entry.historical_names[x] && entry.historical_names[x].name)
              all_alias_strings.push(entry.historical_names[x].name);
          }
        }
        for (let x = 0; x < all_alias_strings.length; x++) {
          let ns = this.normaliseName(all_alias_strings[x], false);
          let ps = this.normaliseName(all_alias_strings[x], true);
          if (ns) norm_set.add(ns);
          if (ps) phon_set.add(ps);
        }

        let gx = Math.round(lat*2);
        let gy = Math.round(lng*2);
        let grid_key = `${gx},${gy}`;
        if (!spatial_grid.has(grid_key)) spatial_grid.set(grid_key, []);
        spatial_grid.get(grid_key).push({
          entry: entry,
          index: i,
          lat: lat,
          lng: lng,
          norm_set: norm_set,
          phon_set: phon_set
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

        let best_match = null;
        let best_dist = 999999;

        for (let x = 0; x < nearby.length; x++) {
          let cand = nearby[x];
          let d_km = this.haversineKm(clat, clng, cand.lat, cand.lng);
          if (d_km > 25.0) continue;

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
                if (mp === cp) {
                  matched_name = true;
                  break;
                }
              }
              if (matched_name) break;
            }
          }
          if (!matched_name && viscount_entity_audit.areEquivalentExonyms(city.name || key, cand.entry.name || "", profiles))
            matched_name = true;

          if (matched_name && d_km < best_dist) {
            best_match = cand;
            best_dist = d_km;
          }
        }

        let pop_years = Object.keys(city.population || {}).map(Number).filter(Number.isFinite).sort(function (arg0_a, arg1_b) {
          return arg0_a - arg1_b;
        });
        let earliest_yr = pop_years.length > 0 ? pop_years[0] : null;
        let latest_yr = pop_years.length > 0 ? pop_years[pop_years.length - 1] : null;

        let reason = "";
        if (!best_match) {
          reason = "missing_entry";
          counts.missing_entry++;
        } else {
          let hn = best_match.entry.historical_names;
          if (!Array.isArray(hn) || hn.length === 0) {
            reason = "empty_historical_names";
            counts.empty_historical_names++;
          } else {
            let has_corrupt = !this.isCleanName(best_match.entry.name);
            let has_suspicious = Boolean(viscount_entity_audit.isSuspiciousToponym(best_match.entry.name, profiles));
            let prev_stem = "";
            for (let x = 0; x < hn.length; x++) {
              let item = hn[x];
              if (!item || !this.isCleanName(item.name) || !viscount_entity_audit.isValidCalendarDate(item.date)) {
                has_corrupt = true;
                break;
              }
              if (viscount_entity_audit.isSuspiciousToponym(item.name, profiles)) has_suspicious = true;
              let h_stem = viscount_entity_audit.normaliseEntityStem(item.name);
              if (prev_stem && h_stem && h_stem === prev_stem && item.name !== hn[x - 1].name)
                has_suspicious = true;
              prev_stem = h_stem;
            }
            if (has_corrupt) {
              reason = "corrupted_names";
              counts.corrupted_names++;
            } else if (has_suspicious) {
              reason = "suspicious_existing_name";
              counts.suspicious_existing_name++;
            } else if (earliest_yr !== null && earliest_yr < 1850) {
              let first_h_yr = Number(String(hn[0].date || "").split(".")[0]);
              if (!Number.isFinite(first_h_yr) || first_h_yr > earliest_yr + 100 || (hn.length === 1 && (latest_yr - earliest_yr) >= 200 && city_aliases.length >= 2)) {
                reason = "under_covered_history";
                counts.under_covered_history++;
              }
            }
          }
        }

        if (!reason) {
          counts.up_to_date++;
          continue;
        }

        let sample_years = (pop_years.length <= 8) ? pop_years :
          [pop_years[0], pop_years[Math.floor(pop_years.length/3)], pop_years[Math.floor(2*pop_years.length/3)], pop_years[pop_years.length - 1]];

        let dedup_aliases = Array.from(new Set(city_aliases.map(function (arg0_s) {
          return String(arg0_s || "").trim();
        }).filter(Boolean)));

        candidates.push({
          coords_lat_lng: [Number(clat.toFixed(5)), Number(clng.toFixed(5))],
          country: city.country || "",
          earliest_year: pop_years.length > 0 ? pop_years[0] : null,
          existing_historical_names: best_match && Array.isArray(best_match.entry.historical_names) ? best_match.entry.historical_names : [],
          existing_meta_index: best_match ? best_match.index : null,
          existing_meta_name: best_match ? best_match.entry.name : null,
          key: key,
          known_aliases: dedup_aliases,
          latest_year: pop_years.length > 0 ? pop_years[pop_years.length - 1] : null,
          name: city.name || key,
          reason: reason,
          region: city.region || "",
          sample_years: sample_years,
          sources: Array.isArray(city.sources) ? city.sources.slice() : []
        });
      }

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

      if (fs.existsSync(out_dir)) {
        let old_files = fs.readdirSync(out_dir);
        for (let i = 0; i < old_files.length; i++) {
          if (/^(batch_\d+|manifest)\.json$/i.test(old_files[i]))
            fs.unlinkSync(path.join(out_dir, old_files[i]));
        }
      }
      if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

      for (let i = 0; i < candidates.length; i += batch_size) {
        let batch_idx = Math.floor(i/batch_size) + 1;
        let batch_slice = candidates.slice(i, i + batch_size);
        let batch_name = `batch_${String(batch_idx).padStart(3, "0")}.json`;
        let batch_path = path.join(out_dir, batch_name);

        fs.writeFileSync(batch_path, JSON.stringify({
          batch_index: batch_idx,
          count: batch_slice.length,
          project: options.project || "ALL",
          settlements: batch_slice
        }, null, 2), "utf8");
        batch_files.push(batch_path);
      }

      let manifest_path = path.join(out_dir, "manifest.json");
      let summary = {
        batch_count: batch_files.length,
        batch_files: batch_files,
        batch_size: batch_size,
        counts: counts,
        generated_at_gmt0: new Date().toISOString(),
        out_dir: out_dir,
        project: options.project || "ALL"
      };
      fs.writeFileSync(manifest_path, JSON.stringify(summary, null, 2), "utf8");

      console.log(`[extract_missing_city_metadata] Checked ${counts.total_checked} settlements (${options.project || "ALL"}): ${candidates.length} need updates (${counts.missing_entry} missing, ${counts.empty_historical_names} empty, ${counts.corrupted_names} corrupt) -> ${batch_files.length} batch(es) in ${out_dir}`);

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
