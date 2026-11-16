//Initialise functions
{
  let fs = global.fs || require("fs");
  let JSON5 = global.JSON5 || require("json5");
  let path = global.path || require("path");

  /**
   * Partitioned I/O manager for Stadestér city object maps, sharded deterministically across
   * the 14 Operation Viscount macro-regions (`01_centaur.json` through `14_nicethi.json`) with
   * automatic 200 MB sub-sharding so Node.js V8 string length limits are never exceeded.
   *
   * @class StadesterPartitionIO
   */
  global.StadesterPartitionIO = class {
    static _cached_registry = null;
    static _cached_registry_path = "";

    /**
     * Resolves a settlement entry deterministically to one of the 14 Operation Viscount macro-region keys.
     * @alias StadesterPartitionIO.assignCityToViscountRegion
     *
     * @param {Object} arg0_city
     * @param {string} [arg1_city_key]
     * @param {Object} [arg2_registry]
     *
     * @returns {Object} Registry project descriptor `{ order, z_priority, key, slug, shard_prefix, shard_file }`
     */
    static assignCityToViscountRegion (arg0_city, arg1_city_key, arg2_registry) {
      //Convert from parameters
      let city = arg0_city;
      let city_key = (arg1_city_key) ? String(arg1_city_key) : "";
      let registry = (arg2_registry) ? arg2_registry : this.loadPrecedenceRegistry();

      //Declare local instance variables
      let bbox_list = registry.bbox_fallbacks || [];
      let by_key = registry.projects_by_key || {};
      let explicit_key = "";
      let explicit_overrides = registry.explicit_key_overrides || {};
      let norm_country = "";
      let norm_suffix = "";
      let prefixes = registry.country_prefixes || [];

      //Guard clauses
      if (!registry || !Array.isArray(registry.projects) || registry.projects.length === 0) {
        console.error("[StadesterPartitionIO] Empty Viscount precedence registry.");
        return { key: "POLARIS", order: 2, shard_file: "02_polaris.json", shard_prefix: "02_polaris", slug: "polaris", z_priority: 2 };
      }

      //Function body
      //1. Explicit Viscount regional tag assigned during gazetteer loading (respects z_priority)
      if (city && city.viscount_project) {
        let proj_key = String(city.viscount_project).toUpperCase();
        if (by_key[proj_key])
          return by_key[proj_key];
      }

      //2. Key-specific overrides for uncoordinated entries lacking ISO/country suffix
      explicit_key = (city && city.key) ? String(city.key) : city_key;
      if (explicit_key && explicit_overrides[explicit_key] && by_key[explicit_overrides[explicit_key]])
        return by_key[explicit_overrides[explicit_key]];

      let lookupCountryToken = function (arg0_norm_token) {
        if (!arg0_norm_token) return null;
        if (arg0_norm_token === "georgia" && city && Array.isArray(city.coords) && city.coords.length >= 2) {
          let lat = Number(city.coords[0]);
          let lng = Number(city.coords[1]);
          if (Number.isFinite(lat) && Number.isFinite(lng))
            return (lng < -30 && by_key.CENTAUR) ? by_key.CENTAUR : (by_key.HANDBOOK || by_key.CENTAUR);
        }
        if (arg0_norm_token === "indonesia" && city && Array.isArray(city.coords) && city.coords.length >= 2) {
          let lat = Number(city.coords[0]);
          let lng = Number(city.coords[1]);
          if (Number.isFinite(lat) && Number.isFinite(lng) && lng >= 134.5 && lat <= 1.0 && by_key.AUSTRAL)
            return by_key.AUSTRAL;
        }
        for (let i = 0; i < prefixes.length; i++)
          if (arg0_norm_token.startsWith(prefixes[i].prefix) && by_key[prefixes[i].key])
            return by_key[prefixes[i].key];
        if (registry.country_lookup[arg0_norm_token])
          return registry.country_lookup[arg0_norm_token];
        return null;
      };

      //3. Normalised country field lookup (including Georgia and New Guinea geographic splits)
      if (city && city.country) {
        norm_country = this.normaliseCountryString(city.country);
        let resolved_proj = lookupCountryToken(norm_country);
        if (resolved_proj) return resolved_proj;
      }

      //4. GHSL/legacy key suffix lookup (`ghsl-<City>-<Country>`) when `country` field is empty
      if (explicit_key && explicit_key.includes("-")) {
        let parts = explicit_key.split("-");
        let raw_suffix = parts[parts.length - 1];
        if (raw_suffix && raw_suffix !== "#N/A") {
          norm_suffix = this.normaliseCountryString(raw_suffix);
          let resolved_proj = lookupCountryToken(norm_suffix);
          if (resolved_proj) return resolved_proj;
        }
      }

      //5. Geocoordinate bounding-box lookup on `[lat, lng]`
      if (city && Array.isArray(city.coords) && city.coords.length >= 2) {
        let lat = Number(city.coords[0]);
        let lng = Number(city.coords[1]);
        if (Number.isFinite(lat) && Number.isFinite(lng)) {
          for (let i = 0; i < bbox_list.length; i++) {
            let bb = bbox_list[i];
            if (lat >= bb.min_lat && lat <= bb.max_lat && lng >= bb.min_lng && lng <= bb.max_lng) {
              if (by_key[bb.key])
                return by_key[bb.key];
            }
          }
        }
      }

      //Return statement
      let fallback_key = registry.default_fallback_key || "JADE";
      return by_key[fallback_key] || registry.projects[0];
    }


    /**
     * Returns the maximum modification timestamp across a partitioned Stadestér directory or legacy JSON file.
     * @alias StadesterPartitionIO.getDatasetMtimeMs
     *
     * @param {string} arg0_path_or_dir
     *
     * @returns {number}
     */
    static getDatasetMtimeMs (arg0_path_or_dir) {
      //Convert from parameters
      let path_or_dir = arg0_path_or_dir;

      //Declare local instance variables
      let max_mtime = 0;
      let target = this.resolveDatasetTarget(path_or_dir);

      //Guard clauses
      if (!target) return 0;

      //Function body
      if (target.mode === "legacy_file") {
        max_mtime = fs.statSync(target.file_path).mtimeMs;
      } else if (target.mode === "partitioned") {
        max_mtime = fs.statSync(target.manifest_path).mtimeMs;
        try {
          let manifest = JSON.parse(fs.readFileSync(target.manifest_path, "utf8"));
          let regions = Array.isArray(manifest.regions) ? manifest.regions : [];
          for (let i = 0; i < regions.length; i++) {
            let files = Array.isArray(regions[i].files) ? regions[i].files : [];
            for (let x = 0; x < files.length; x++) {
              let shard_path = path.join(target.dir_path, files[x]);
              if (fs.existsSync(shard_path)) {
                let mtime = fs.statSync(shard_path).mtimeMs;
                if (mtime > max_mtime) max_mtime = mtime;
              }
            }
          }
        } catch (e) {
          console.error(`[StadesterPartitionIO] Failed reading manifest mtime at ${target.manifest_path}:`, e);
        }
      }

      //Return statement
      return max_mtime;
    }


    /**
     * Checks whether either a partitioned `stadester_manifest.json` directory or legacy JSON file exists.
     * @alias StadesterPartitionIO.hasDataset
     *
     * @param {string} arg0_path_or_dir
     *
     * @returns {boolean}
     */
    static hasDataset (arg0_path_or_dir) {
      //Convert from parameters
      let path_or_dir = arg0_path_or_dir;

      //Return statement
      return Boolean(this.resolveDatasetTarget(path_or_dir));
    }


    /**
     * Loads and indexes `histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5`.
     * @alias StadesterPartitionIO.loadPrecedenceRegistry
     *
     * @param {string} [arg0_config_path]
     *
     * @returns {Object}
     */
    static loadPrecedenceRegistry (arg0_config_path) {
      //Convert from parameters
      let config_path = arg0_config_path;

      //Declare local instance variables
      let candidate_paths = [];
      let raw_registry;
      let resolved_path = "";

      //Function body
      if (config_path && fs.existsSync(config_path)) {
        resolved_path = path.resolve(config_path);
      } else {
        candidate_paths = [
          path.join(__dirname, "config", "viscount_precedence.json5"),
          path.resolve("./histmap/2.data_cleaning/population_Stadester/config/viscount_precedence.json5")
        ];
        if (typeof global.h2 !== "undefined")
          candidate_paths.unshift(path.resolve(`${global.h2}/population_Stadester/config/viscount_precedence.json5`));
        for (let i = 0; i < candidate_paths.length; i++)
          if (fs.existsSync(candidate_paths[i])) {
            resolved_path = candidate_paths[i];
            break;
          }
      }

      if (!resolved_path) {
        console.error("[StadesterPartitionIO] Could not locate config/viscount_precedence.json5.");
        return { bbox_fallbacks: [], country_lookup: {}, projects: [], projects_by_key: {} };
      }

      if (this._cached_registry && this._cached_registry_path === resolved_path)
        return this._cached_registry;

      try {
        raw_registry = JSON5.parse(fs.readFileSync(resolved_path, "utf8"));
      } catch (e) {
        console.error(`[StadesterPartitionIO] Failed to parse ${resolved_path}:`, e);
        return { bbox_fallbacks: [], country_lookup: {}, projects: [], projects_by_key: {} };
      }

      let country_lookup = {};
      let projects = Array.isArray(raw_registry.projects) ? raw_registry.projects.slice() : [];
      let projects_by_key = {};

      projects.sort(function (arg0_a, arg1_b) {
        return (arg0_a.order || 0) - (arg1_b.order || 0);
      });

      for (let i = 0; i < projects.length; i++) {
        let proj = projects[i];
        projects_by_key[proj.key] = proj;
        let c_list = Array.isArray(proj.countries) ? proj.countries : [];
        for (let x = 0; x < c_list.length; x++) {
          let norm_c = this.normaliseCountryString(c_list[x]);
          if (norm_c) country_lookup[norm_c] = proj;
        }
      }

      let alias_map = raw_registry.normalised_aliases || {};
      let alias_keys = Object.keys(alias_map);
      for (let i = 0; i < alias_keys.length; i++) {
        let ak = this.normaliseCountryString(alias_keys[i]);
        let target_proj_key = alias_map[alias_keys[i]];
        if (ak && projects_by_key[target_proj_key])
          country_lookup[ak] = projects_by_key[target_proj_key];
      }

      this._cached_registry = {
        bbox_fallbacks: Array.isArray(raw_registry.bbox_fallbacks) ? raw_registry.bbox_fallbacks : [],
        country_lookup: country_lookup,
        country_prefixes: Array.isArray(raw_registry.country_prefixes) ? raw_registry.country_prefixes : [],
        default_fallback_key: raw_registry.default_fallback_key || "JADE",
        explicit_key_overrides: raw_registry.explicit_key_overrides || {},
        max_shard_bytes: Number(raw_registry.max_shard_bytes) || 209715200,
        projects: projects,
        projects_by_key: projects_by_key,
        resolution_order: raw_registry.resolution_order || "z_priority_desc",
        version: raw_registry.version || "1.0"
      };
      this._cached_registry_path = resolved_path;

      //Return statement
      return this._cached_registry;
    }


    /**
     * Normalises country names and legacy encoding fragments into lowercase ASCII lookup keys.
     * @alias StadesterPartitionIO.normaliseCountryString
     *
     * @param {string} arg0_raw_str
     *
     * @returns {string}
     */
    static normaliseCountryString (arg0_raw_str) {
      //Convert from parameters
      let raw_str = (arg0_raw_str) ? String(arg0_raw_str) : "";

      //Return statement
      return raw_str
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\uFFFD/g, "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
    }


    /**
     * Loads a partitioned Stadestér dataset directory (or legacy single `.json`) into a unified JS Object.
     * Optionally filters to a single Viscount macro-region when `arg1_options.viscount_key` is set.
     * @alias StadesterPartitionIO.readPartitionedStadester
     *
     * @param {string} arg0_path_or_dir
     * @param {Object} [arg1_options]
     *  @param {string} [arg1_options.viscount_key]
     *
     * @returns {Object}
     */
    static readPartitionedStadester (arg0_path_or_dir, arg1_options) {
      //Convert from parameters
      let path_or_dir = arg0_path_or_dir;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let result_obj = {};
      let target = this.resolveDatasetTarget(path_or_dir);
      let viscount_filter = (options.viscount_key) ? String(options.viscount_key).toUpperCase() : "";

      //Guard clauses
      if (!target) {
        console.error(`[StadesterPartitionIO] Dataset not found at ${path_or_dir}`);
        return {};
      }

      //Function body
      if (target.mode === "legacy_file") {
        try {
          let raw_obj = JSON.parse(fs.readFileSync(target.file_path, "utf8"));
          if (!viscount_filter) return raw_obj;

          let registry = this.loadPrecedenceRegistry();
          let all_keys = Object.keys(raw_obj);
          for (let i = 0; i < all_keys.length; i++) {
            let k = all_keys[i];
            let reg = this.assignCityToViscountRegion(raw_obj[k], k, registry);
            if (reg.key === viscount_filter) result_obj[k] = raw_obj[k];
          }
          return result_obj;
        } catch (e) {
          console.error(`[StadesterPartitionIO] Failed to read legacy Stadestér JSON ${target.file_path}:`, e);
          return {};
        }
      }

      try {
        let manifest = JSON.parse(fs.readFileSync(target.manifest_path, "utf8"));
        let regions = Array.isArray(manifest.regions) ? manifest.regions : [];

        for (let i = 0; i < regions.length; i++) {
          let reg_entry = regions[i];
          if (viscount_filter && reg_entry.key !== viscount_filter) continue;
          let files = Array.isArray(reg_entry.files) ? reg_entry.files : [];

          for (let x = 0; x < files.length; x++) {
            let shard_path = path.join(target.dir_path, files[x]);
            if (!fs.existsSync(shard_path)) continue;
            let shard_obj = JSON.parse(fs.readFileSync(shard_path, "utf8"));
            let shard_keys = Object.keys(shard_obj);
            for (let y = 0; y < shard_keys.length; y++)
              result_obj[shard_keys[y]] = shard_obj[shard_keys[y]];
          }
        }
      } catch (e) {
        console.error(`[StadesterPartitionIO] Failed to read partitioned Stadestér at ${target.manifest_path}:`, e);
        return {};
      }

      //Return statement
      return result_obj;
    }


    /**
     * Convenience wrapper to read only a single Viscount macro-region shard (e.g. `"POLARIS"`).
     * @alias StadesterPartitionIO.readViscountRegionShard
     *
     * @param {string} arg0_path_or_dir
     * @param {string} arg1_viscount_key
     *
     * @returns {Object}
     */
    static readViscountRegionShard (arg0_path_or_dir, arg1_viscount_key) {
      //Convert from parameters
      let path_or_dir = arg0_path_or_dir;
      let viscount_key = arg1_viscount_key;

      //Return statement
      return this.readPartitionedStadester(path_or_dir, { viscount_key: viscount_key });
    }


    /**
     * Resolves a user-supplied file or folder path into `{ mode: "partitioned" | "legacy_file", ... }`.
     * @alias StadesterPartitionIO.resolveDatasetTarget
     *
     * @param {string} arg0_path_or_dir
     *
     * @returns {Object|null}
     */
    static resolveDatasetTarget (arg0_path_or_dir) {
      //Convert from parameters
      let raw_input = arg0_path_or_dir;

      //Guard clauses
      if (!raw_input) return null;

      //Declare local instance variables
      let abs_input = path.resolve(String(raw_input));
      let stem_dir = abs_input.endsWith(".json") ? abs_input.slice(0, -5) : abs_input;
      let stem_file = abs_input.endsWith(".json") ? abs_input : `${abs_input}.json`;

      //Function body
      if (path.basename(abs_input) === "stadester_manifest.json" && fs.existsSync(abs_input)) {
        return {
          dir_path: path.dirname(abs_input),
          manifest_path: abs_input,
          mode: "partitioned"
        };
      }

      let manifest_in_dir = path.join(stem_dir, "stadester_manifest.json");
      if (fs.existsSync(manifest_in_dir)) {
        return {
          dir_path: stem_dir,
          manifest_path: manifest_in_dir,
          mode: "partitioned"
        };
      }

      let versioned_file = path.join(stem_dir, `${path.basename(stem_dir)}.json`);
      if (fs.existsSync(versioned_file) && fs.statSync(versioned_file).isFile()) {
        return {
          file_path: versioned_file,
          mode: "legacy_file"
        };
      }

      if (fs.existsSync(stem_file) && fs.statSync(stem_file).isFile()) {
        return {
          file_path: stem_file,
          mode: "legacy_file"
        };
      }

      //Return statement
      return null;
    }


    /**
     * Stream-writes a top-level dictionary object as formatted JSON with 2-space indentation,
     * splitting into sub-shards automatically if `arg2_max_bytes` would be exceeded.
     * @alias StadesterPartitionIO.streamWriteJsonShard
     *
     * @param {string} arg0_dir_path
     * @param {string} arg1_shard_prefix
     * @param {Array<Array>} arg2_entries - Array of `[key, city_obj]` pairs
     * @param {number} [arg3_max_bytes=209715200]
     *
     * @returns {Object} `{ files: Array<string>, bytes: number }`
     */
    static streamWriteJsonShard (arg0_dir_path, arg1_shard_prefix, arg2_entries, arg3_max_bytes) {
      //Convert from parameters
      let dir_path = arg0_dir_path;
      let shard_prefix = arg1_shard_prefix;
      let entries = Array.isArray(arg2_entries) ? arg2_entries : [];
      let max_bytes = Number(arg3_max_bytes) || 209715200;

      //Declare local instance variables
      let buffer = [];
      let buffer_len = 0;
      let chunk_entry_count = 0;
      let chunk_idx = 0;
      let chunk_paths = [];
      let fd = null;
      let files_written = [];
      let flush_threshold = 8*1024*1024;
      let running_estimate = 2;
      let total_bytes = 0;

      //Function body
      if (entries.length === 0) {
        let single_name = `${shard_prefix}.json`;
        let single_path = path.join(dir_path, single_name);
        fs.writeFileSync(single_path, "{}\n", "utf8");
        return { bytes: fs.statSync(single_path).size, files: [single_name] };
      }

      let openChunk = function (arg0_idx) {
        let temp_name = `${shard_prefix}_${arg0_idx + 1}.json`;
        let temp_path = path.join(dir_path, temp_name);
        chunk_paths.push({ filename: temp_name, full_path: temp_path });
        buffer = ["{\n"];
        buffer_len = 2;
        chunk_entry_count = 0;
        running_estimate = 2;
        return fs.openSync(temp_path, "w");
      };

      let closeChunk = function (arg0_fd) {
        if (arg0_fd === null || arg0_fd === undefined) return;
        buffer.push("\n}\n");
        try {
          fs.writeSync(arg0_fd, buffer.join(""), null, "utf8");
        } finally {
          fs.closeSync(arg0_fd);
        }
        buffer = [];
        buffer_len = 0;
      };

      fd = openChunk(0);
      try {
        for (let i = 0; i < entries.length; i++) {
          let k = entries[i][0];
          let val_obj = entries[i][1];
          let val_str = JSON.stringify(val_obj, null, 2);
          if (val_str === undefined) continue;

          let entry_body = `${JSON.stringify(k)}: ${val_str.replace(/\n/g, "\n  ")}`;
          let entry_bytes = Buffer.byteLength(entry_body, "utf8") + 6;

          if (chunk_entry_count > 0 && (running_estimate + entry_bytes) > max_bytes) {
            closeChunk(fd);
            fd = null;
            chunk_idx++;
            fd = openChunk(chunk_idx);
          }

          let chunk = (chunk_entry_count === 0 ? "  " : ",\n  ") + entry_body;
          buffer.push(chunk);
          buffer_len += chunk.length;
          chunk_entry_count++;
          running_estimate += entry_bytes;

          if (buffer_len >= flush_threshold) {
            fs.writeSync(fd, buffer.join(""), null, "utf8");
            buffer = [];
            buffer_len = 0;
          }
        }
        closeChunk(fd);
        fd = null;
      } catch (e) {
        if (fd !== null) try { fs.closeSync(fd); } catch (err) {}
        console.error(`[StadesterPartitionIO] Failed streaming shard ${shard_prefix}:`, e);
        return { bytes: 0, files: [] };
      }

      if (chunk_paths.length === 1) {
        let final_name = `${shard_prefix}.json`;
        let final_path = path.join(dir_path, final_name);
        if (fs.existsSync(final_path)) try { fs.unlinkSync(final_path); } catch (e) {}
        fs.renameSync(chunk_paths[0].full_path, final_path);
        total_bytes = fs.statSync(final_path).size;
        files_written.push(final_name);
      } else {
        for (let i = 0; i < chunk_paths.length; i++) {
          total_bytes += fs.statSync(chunk_paths[i].full_path).size;
          files_written.push(chunk_paths[i].filename);
        }
      }

      //Return statement
      return { bytes: total_bytes, files: files_written };
    }


    /**
     * Writes a Stadestér Object map partitioned into the 14 Operation Viscount macro-region files
     * (`01_centaur.json` through `14_nicethi.json`) plus `stadester_manifest.json`.
     * @alias StadesterPartitionIO.writePartitionedStadester
     *
     * @param {string} arg0_target_dir
     * @param {Object} arg1_stadester_obj
     * @param {Object} [arg2_options]
     *  @param {number} [arg2_options.max_shard_bytes=209715200]
     *  @param {string} [arg2_options.version="2.0"]
     *
     * @returns {Object} Manifest summary written to `stadester_manifest.json`
     */
    static writePartitionedStadester (arg0_target_dir, arg1_stadester_obj, arg2_options) {
      //Convert from parameters
      let raw_target = arg0_target_dir;
      let stadester_obj = arg1_stadester_obj;
      let options = (arg2_options) ? arg2_options : {};

      //Initialise options
      let target_dir = (String(raw_target).endsWith(".json")) ?
        String(raw_target).slice(0, -5) : String(raw_target);
      let version = (options.version) ? String(options.version) : "2.0";

      //Declare local instance variables
      let all_keys = (stadester_obj && typeof stadester_obj === "object") ? Object.keys(stadester_obj) : [];
      let buckets = new Map();
      let expected_files = new Set(["stadester_manifest.json", "city_metadata.json"]);
      let manifest_obj;
      let max_shard_bytes;
      let region_summaries = [];
      let registry = this.loadPrecedenceRegistry(options.precedence_config_path);

      //Guard clauses
      if (!raw_target || !stadester_obj) {
        console.error("[StadesterPartitionIO] Invalid target directory or Stadestér object.");
        return null;
      }

      //Function body
      max_shard_bytes = Number(options.max_shard_bytes) || registry.max_shard_bytes || 209715200;
      if (!fs.existsSync(target_dir))
        fs.mkdirSync(target_dir, { recursive: true });

      for (let i = 0; i < registry.projects.length; i++)
        buckets.set(registry.projects[i].key, []);

      for (let i = 0; i < all_keys.length; i++) {
        let city_key = all_keys[i];
        let city_obj = stadester_obj[city_key];
        if (!city_obj || typeof city_obj !== "object") continue;
        let proj = this.assignCityToViscountRegion(city_obj, city_key, registry);
        buckets.get(proj.key).push([city_key, city_obj]);
      }

      for (let i = 0; i < registry.projects.length; i++) {
        let proj = registry.projects[i];
        let reg_entries = buckets.get(proj.key) || [];
        let shard_res = this.streamWriteJsonShard(target_dir, proj.shard_prefix, reg_entries, max_shard_bytes);
        for (let x = 0; x < shard_res.files.length; x++)
          expected_files.add(shard_res.files[x]);

        region_summaries.push({
          bytes: shard_res.bytes,
          count: reg_entries.length,
          files: shard_res.files,
          key: proj.key,
          order: proj.order,
          slug: proj.slug,
          z_priority: proj.z_priority
        });
      }

      //Remove stale shard files in target directory no longer referenced by manifest
      let existing_entries = fs.readdirSync(target_dir);
      for (let i = 0; i < existing_entries.length; i++) {
        let f_name = existing_entries[i];
        if (/^\d{2}_[a-z0-9_]+(?:\.part\d+)?\.json$/i.test(f_name) && !expected_files.has(f_name)) {
          try {
            fs.unlinkSync(path.join(target_dir, f_name));
          } catch (e) {}
        }
      }

      manifest_obj = {
        format: "stadester_viscount_v1",
        generated_at: new Date().toISOString(),
        regions: region_summaries,
        total_entries: all_keys.length,
        version: version
      };
      fs.writeFileSync(path.join(target_dir, "stadester_manifest.json"), JSON.stringify(manifest_obj, null, 2), "utf8");

      //Return statement
      return manifest_obj;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { StadesterPartitionIO: global.StadesterPartitionIO };
