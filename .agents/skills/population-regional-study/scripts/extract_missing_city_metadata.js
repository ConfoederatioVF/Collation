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
        let shards = Array.isArray(man.shards) ? man.shards : [];
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          let is_cap = sh.key === "CAPITALS" || sh.file === "00_capitals.json";
          if (project_key && !is_cap && sh.key !== project_key && sh.key !== "UNASSIGNED") continue;
          let sp = path.join(part_dir, sh.file);
          if (!fs.existsSync(sp)) continue;
          let arr = JSON.parse(fs.readFileSync(sp, "utf8"));
          for (let x = 0; x < arr.length; x++)
            records.push({ entry: arr[x], index: x, is_capital_shard: is_cap, shard_file: sh.file });
        }
        return { is_partitioned: true, records: records };
      }

      let versioned_meta = path.join(stadester_dir, "city_metadata.json");
      let legacy_meta = path.join(dataview_root, "data/stadester/city_metadata.json");
      let meta_path = fs.existsSync(versioned_meta) ? versioned_meta : legacy_meta;
      if (fs.existsSync(meta_path)) {
        let arr = JSON.parse(fs.readFileSync(meta_path, "utf8"));
        for (let i = 0; i < arr.length; i++)
          records.push({ entry: arr[i], index: i, is_capital_shard: false, shard_file: "city_metadata.json" });
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
        batch_size: 25,
        dataset: "stadester_2.0",
        dataview_root: "",
        out_dir: "",
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
        else if (tok.startsWith("--batch-size=")) args.batch_size = Math.max(1, Math.min(30, Number(tok.slice(13)) || 25));
        else if (tok.startsWith("--out-dir=")) args.out_dir = tok.slice(10).trim();
      }

      //Return statement
      return args;
    },

    /**
     * Compares Viscount settlements against Dataview partitioned `city_metadata/` (or legacy file),
     * flagging missing entries, capitals, single-entry stubs >= 10k, indigenous-heritage regions,
     * corrupt/inverted/suspicious names and under-covered timelines into 25-30-city Flash chunks.
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
      let batch_files = [];
      let batch_size = Math.max(1, Math.min(30, Number(options.batch_size) || 25));
      let candidates = [];
      let counts = {
        capital_audit: 0,
        corrupted_names: 0,
        empty_historical_names: 0,
        indigenous_stub: 0,
        missing_entry: 0,
        single_entry_major_stub: 0,
        suspicious_existing_name: 0,
        total_checked: 0,
        under_covered_history: 0,
        up_to_date: 0
      };
      let dataset_id = (options.dataset) ? String(options.dataset).replace(/\.json$/i, "") : "stadester_2.0";
      let svea_root = (options.svea_root) ? path.resolve(options.svea_root) :
        (viscount_audit_utils.findSveaRoot(__dirname) || path.resolve(__dirname, "../../../.."));
      let dataview_root = (options.dataview_root) ? path.resolve(options.dataview_root) :
        (process.env.DATAVIEW_ROOT ? path.resolve(process.env.DATAVIEW_ROOT) : path.resolve(svea_root, "../Project 1436 - Dataview"));
      let profiles = viscount_entity_audit.loadSkillProfiles(svea_root);
      let indig_regions = new Set(Array.isArray(profiles.indigenous_endonym_regions) ? profiles.indigenous_endonym_regions : []);
      let is_indig_project = Boolean(options.project && indig_regions.has(options.project));

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

        let grid_key = `${Math.round(lat*2)},${Math.round(lng*2)}`;
        if (!spatial_grid.has(grid_key)) spatial_grid.set(grid_key, []);
        spatial_grid.get(grid_key).push({
          entry: entry,
          index: rec_wrap.index,
          is_capital_shard: rec_wrap.is_capital_shard,
          lat: lat,
          lng: lng,
          norm_set: norm_set,
          phon_set: phon_set,
          shard_file: rec_wrap.shard_file
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
          let d_km = viscount_audit_utils.haversineKm(clat, clng, cand.lat, cand.lng);
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
                if (mp === cp) { matched_name = true; break; }
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
        let is_capital = Boolean(city.is_capital || city.capital || (best_match && (best_match.is_capital_shard || best_match.entry.capital)));

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
            } else if (is_capital && hn.length === 1 && String(hn[0].date) === "1900.1.1") {
              reason = "capital_audit";
              counts.capital_audit++;
            } else if (earliest_yr !== null && earliest_yr < 1850) {
              let first_h_yr = Number(String(hn[0].date || "").split(".")[0]);
              if (!Number.isFinite(first_h_yr) || first_h_yr > earliest_yr + 100 || (hn.length === 1 && (latest_yr - earliest_yr) >= 200)) {
                reason = "under_covered_history";
                counts.under_covered_history++;
              }
            } else if (hn.length === 1 && is_indig_project && max_pop >= 5000 && String(hn[0].date) === "1900.1.1") {
              reason = "indigenous_stub";
              counts.indigenous_stub++;
            } else if (hn.length === 1 && max_pop >= 10000 && String(hn[0].date) === "1900.1.1") {
              reason = "single_entry_major_stub";
              counts.single_entry_major_stub++;
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
          earliest_year: earliest_yr,
          existing_historical_names: best_match && Array.isArray(best_match.entry.historical_names) ? best_match.entry.historical_names : [],
          existing_meta_index: best_match ? best_match.index : null,
          existing_meta_name: best_match ? best_match.entry.name : null,
          existing_shard_file: best_match ? best_match.shard_file : null,
          is_capital: is_capital,
          is_indigenous_region: is_indig_project,
          key: key,
          known_aliases: dedup_aliases,
          latest_year: latest_yr,
          max_pop: Math.round(max_pop),
          name: city.name || key,
          reason: reason,
          region: city.region || "",
          sample_years: sample_years,
          sources: Array.isArray(city.sources) ? city.sources.slice() : []
        });
      }

      // Sort capitals first, then descending peak population
      candidates.sort(function (arg0_a, arg1_b) {
        if (arg0_a.is_capital !== arg1_b.is_capital) return arg0_a.is_capital ? -1 : 1;
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

      if (fs.existsSync(out_dir)) {
        let old_files = fs.readdirSync(out_dir);
        for (let i = 0; i < old_files.length; i++) {
          if (/^(batch_\d+|manifest)\.json$/i.test(old_files[i]))
            fs.unlinkSync(path.join(out_dir, old_files[i]));
        }
      }
      fs.mkdirSync(out_dir, { recursive: true });

      for (let i = 0; i < candidates.length; i += batch_size) {
        let batch_idx = Math.floor(i/batch_size) + 1;
        let batch_slice = candidates.slice(i, i + batch_size);
        let batch_name = `batch_${String(batch_idx).padStart(3, "0")}.json`;
        let batch_path = path.join(out_dir, batch_name);

        fs.writeFileSync(batch_path, JSON.stringify({
          batch_index: batch_idx,
          count: batch_slice.length,
          is_indigenous_region: is_indig_project,
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
        is_partitioned_source: meta_loaded.is_partitioned,
        out_dir: out_dir,
        project: options.project || "ALL"
      };
      fs.writeFileSync(manifest_path, JSON.stringify(summary, null, 2), "utf8");

      console.log(`[extract_missing_city_metadata] Checked ${counts.total_checked} settlements (${options.project || "ALL"}): ${candidates.length} need updates -> ${batch_files.length} batch(es) of <= ${batch_size} in ${out_dir}`);

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
