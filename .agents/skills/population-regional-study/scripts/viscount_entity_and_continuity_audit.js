//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise functions
{
  let viscount_entity_audit = {
    _cached_arch_regexes: null,
    _cached_exonym_map: null,
    _cached_profiles: null,
    _cached_susp_regexes: null,

    /**
     * Returns true when two stems match either via Bigram Dice threshold or via the shared
     * cross-language historical romanisation equivalence table (`Peking <-> Beijing`, etc.).
     * @alias viscount_entity_audit.areEquivalentExonyms
     *
     * @param {string} arg0_name_a
     * @param {string} arg1_name_b
     * @param {Object} [arg2_profiles]
     *
     * @returns {boolean}
     */
    areEquivalentExonyms (arg0_name_a, arg1_name_b, arg2_profiles) {
      //Convert from parameters
      let a = this.normaliseEntityStem(arg0_name_a);
      let b = this.normaliseEntityStem(arg1_name_b);
      let profiles = (arg2_profiles) ? arg2_profiles : {};

      //Guard clauses
      if (!a || !b) return false;
      if (a === b) return true;

      //Function body
      if (!this._cached_exonym_map) {
        this._cached_exonym_map = new Map();
        let groups = Array.isArray(profiles.romanisation_equivalences) ? profiles.romanisation_equivalences : [];
        for (let i = 0; i < groups.length; i++) {
          let g = groups[i];
          if (!Array.isArray(g)) continue;
          for (let x = 0; x < g.length; x++) {
            let item = String(g[x] || "");
            if (item) this._cached_exonym_map.set(item, i);
          }
        }
      }
      let ga = this._cached_exonym_map.get(a);
      if (ga === undefined) return false;

      //Return statement
      return ga === this._cached_exonym_map.get(b);
    },

    /**
     * Checks whether a settlement label carries an archaeological/topographic site qualifier.
     * @alias viscount_entity_audit.hasArchSiteQualifier
     *
     * @param {string} arg0_name
     * @param {Object} [arg1_profiles]
     *
     * @returns {boolean}
     */
    hasArchSiteQualifier (arg0_name, arg1_profiles) {
      //Convert from parameters
      let profiles = (arg1_profiles) ? arg1_profiles : {};
      let raw_name = String(arg0_name || "");

      //Guard clauses
      if (!raw_name) return false;

      //Declare local instance variables
      let quals = Array.isArray(profiles.arch_site_qualifiers) ? profiles.arch_site_qualifiers : [
        "Site", "Complex", "Hillfort", "Settlement", "Mound", "Kurgan", "Barrow",
        "Tumulus", "Kofun", "Tell", "Tepe", "Hoyuk", "Huaca", "Pueblo", "Sambaqui",
        "Midden", "Shellmound", "Cairn", "Enclosure", "Ruin", "Ruins", "Terrace",
        "Gorodishche", "Suburb", "Culture", "Shelter", "Cave", "Camp", "Earthwork",
        "Cemetery", "Necropolis", "Palaeolithic", "Neolithic", "Bronze", "Iron Age"
      ];

      //Function body
      if (!this._cached_arch_regexes) {
        this._cached_arch_regexes = [];
        for (let i = 0; i < quals.length; i++) {
          let q = String(quals[i] || "").trim();
          if (!q) continue;
          let escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
          this._cached_arch_regexes.push(new RegExp(`\\b${escaped}\\b`, "i"));
        }
      }
      for (let i = 0; i < this._cached_arch_regexes.length; i++) {
        if (this._cached_arch_regexes[i].test(raw_name)) return true;
      }

      //Return statement
      return false;
    },

    /**
     * Returns true when a jurisdiction belongs to the Latin-script-only tier across all 14 macro-regions
     * (excluding legitimate multi-script jurisdictions defined in `viscount_skill_profiles.json5`).
     * @alias viscount_entity_audit.isLatinScriptOnlyCountry
     *
     * @param {string} arg0_country
     * @param {Array<number>} [arg1_coords]
     * @param {Object} [arg2_profiles]
     *
     * @returns {boolean}
     */
    isLatinScriptOnlyCountry (arg0_country, arg1_coords, arg2_profiles) {
      //Convert from parameters
      let coords = Array.isArray(arg1_coords) ? arg1_coords : [];
      let country = String(arg0_country || "").trim().toLowerCase();
      let profiles = (arg2_profiles) ? arg2_profiles : {};

      //Guard clauses
      if (!country) return false;
      if (country === "georgia")
        return Number(coords[1] || 0) < -30.0;

      //Declare local instance variables
      let raw_multi = Array.isArray(profiles.multi_script_countries) ? profiles.multi_script_countries : [];
      let multi_set = new Set();

      //Function body
      for (let i = 0; i < raw_multi.length; i++)
        multi_set.add(String(raw_multi[i] || "").trim().toLowerCase());

      //Return statement
      return !multi_set.has(country);
    },

    /**
     * Loads and caches `.agents/skills/population-regional-study/config/viscount_skill_profiles.json5`.
     * @alias viscount_entity_audit.loadSkillProfiles
     *
     * @param {string} [arg0_svea_root]
     *
     * @returns {Object}
     */
    loadSkillProfiles (arg0_svea_root) {
      //Guard clauses
      if (this._cached_profiles) return this._cached_profiles;

      //Convert from parameters
      let svea_root = arg0_svea_root ? path.resolve(arg0_svea_root) : path.resolve(__dirname, "../../../..");

      //Declare local instance variables
      let candidates = [
        path.resolve(__dirname, "../config/viscount_skill_profiles.json5"),
        path.join(svea_root, ".agents/skills/population-regional-study/config/viscount_skill_profiles.json5")
      ];

      //Function body
      for (let i = 0; i < candidates.length; i++) {
        if (fs.existsSync(candidates[i])) {
          this._cached_profiles = JSON5.parse(fs.readFileSync(candidates[i], "utf8"));
          return this._cached_profiles;
        }
      }

      //Return statement
      return {};
    },

    /**
     * Normalises an entity or city stem across Unicode diacritics and global historical romanisations.
     * @alias viscount_entity_audit.normaliseEntityStem
     *
     * @param {string} arg0_name
     *
     * @returns {string}
     */
    normaliseEntityStem (arg0_name) {
      //Convert from parameters
      let raw = String(arg0_name || "");

      //Declare local instance variables
      let base = raw.split(";")[0].split("(")[0].trim().toLowerCase();

      //Function body
      base = base
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/ł/g, "l")
        .replace(/đ/g, "d")
        .replace(/ø/g, "o")
        .replace(/ß/g, "ss")
        .replace(/æ/g, "ae")
        .replace(/œ/g, "oe");
      base = base.replace(/^(?:st\.?|saint|san|santa|sao|al-|el-)\s+/i, "saint ");
      base = base.replace(/kh/g, "k");
      base = base.replace(/gh/g, "g");
      base = base.replace(/ph/g, "f");
      base = base.replace(/dj/g, "j");
      base = base.replace(/ou/g, "u");
      base = base.replace(/[jy]/g, "i");
      base = base.replace(/ts/g, "c");
      base = base.replace(/[cq]/g, "k");
      base = base.replace(/[^a-z0-9]+/g, "");

      //Return statement
      return base;
    },

    /**
     * Checks whether a `YYYY.M.D` date string represents a valid historical calendar date (non-zero year, valid month/day, `<= 2026`).
     * @alias viscount_entity_audit.isValidCalendarDate
     *
     * @param {string} arg0_date_str
     *
     * @returns {boolean}
     */
    isValidCalendarDate (arg0_date_str) {
      //Convert from parameters
      let raw = String(arg0_date_str || "").trim();

      //Guard clauses
      let m = raw.match(/^(-?\d+)\.(\d+)\.(\d+)$/);
      if (!m) return false;

      //Declare local instance variables
      let day = Number(m[3]);
      let month = Number(m[2]);
      let year = Number(m[1]);

      //Function body
      if (!Number.isInteger(year) || year === 0 || year < -10000 || year > 2026) return false;
      if (!Number.isInteger(month) || month < 1 || month > 12) return false;
      if (!Number.isInteger(day) || day < 1 || day > 31) return false;

      //Return statement
      return true;
    },

    /**
     * Detects non-settlement temple, shrine, monument or raw administrative-unit names using `viscount_skill_profiles.json5`.
     * @alias viscount_entity_audit.isSuspiciousToponym
     *
     * @param {string} arg0_name
     * @param {Object} [arg1_profiles]
     *
     * @returns {string|null}
     */
    isSuspiciousToponym (arg0_name, arg1_profiles) {
      //Convert from parameters
      let profiles = (arg1_profiles) ? arg1_profiles : this.loadSkillProfiles();
      let raw = String(arg0_name || "").trim();

      //Guard clauses
      if (!raw) return null;

      //Declare local instance variables
      let cfg = (profiles && profiles.suspicious_toponym_patterns) ? profiles.suspicious_toponym_patterns : {};
      let low = raw.toLowerCase();
      let raw_allow = Array.isArray(cfg.allowlist) ? cfg.allowlist : [];
      let rel_pats = Array.isArray(cfg.religious_monument_regexes) ? cfg.religious_monument_regexes : [];
      let adm_pats = Array.isArray(cfg.admin_unit_suffix_regexes) ? cfg.admin_unit_suffix_regexes : [];

      //Function body
      if (!this._cached_susp_regexes) {
        let allow_set = new Set();
        for (let i = 0; i < raw_allow.length; i++)
          allow_set.add(String(raw_allow[i] || "").trim().toLowerCase());
        let rel_compiled = [];
        for (let i = 0; i < rel_pats.length; i++)
          rel_compiled.push({ pat: rel_pats[i], re: new RegExp(rel_pats[i], "i") });
        let adm_compiled = [];
        for (let i = 0; i < adm_pats.length; i++)
          adm_compiled.push({ pat: adm_pats[i], re: new RegExp(adm_pats[i], "i") });
        this._cached_susp_regexes = { adm: adm_compiled, allow: allow_set, rel: rel_compiled };
      }

      if (this._cached_susp_regexes.allow.has(low)) return null;
      for (let i = 0; i < this._cached_susp_regexes.rel.length; i++) {
        if (this._cached_susp_regexes.rel[i].re.test(low)) return `religious/monument pattern ${this._cached_susp_regexes.rel[i].pat}`;
      }
      for (let i = 0; i < this._cached_susp_regexes.adm.length; i++) {
        if (this._cached_susp_regexes.adm[i].re.test(low)) return `admin-unit suffix pattern ${this._cached_susp_regexes.adm[i].pat}`;
      }

      //Return statement
      return null;
    },

    /**
     * Computes great-circle Haversine distance in km between two `[lat, lng]` coordinates.
     * @alias viscount_entity_audit.haversineKm
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
     * Audits Dataview `stadester_2.0/city_metadata.json` for regional settlement coverage,
     * historical date validity/earliest-year fallback alignment, suspicious temple/admin names,
     * consecutive variant-spelling renames and near-duplicate metadata records.
     * @alias viscount_entity_audit.verifyCityMetadataQuality
     *
     * @param {Object} arg0_proj
     * @param {string} arg1_dataview_root
     * @param {Array<string>} arg2_shard_files
     * @param {Array<string>} arg3_errors
     * @param {Object} [arg4_options]
     *
     * @returns {Object} Metadata quality telemetry
     */
    verifyCityMetadataQuality (arg0_proj, arg1_dataview_root, arg2_shard_files, arg3_errors, arg4_options) {
      //Convert from parameters
      let dataview_root = arg1_dataview_root;
      let errors = arg3_errors;
      let options = (arg4_options) ? arg4_options : {};
      let proj = (arg0_proj) ? arg0_proj : {};
      let shard_files = Array.isArray(arg2_shard_files) ? arg2_shard_files : [];

      //Declare local instance variables
      let bad_dates = [];
      let consec_variant_dups = [];
      let earliest_gap_hits = [];
      let matched_major = 0;
      let matched_meta_indices = new Set();
      let matched_pre1850 = 0;
      let meta_path = (options.meta_path) ? options.meta_path :
        path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata.json");
      let near_dups = [];
      let pre1850_covered = 0;
      let profiles = this.loadSkillProfiles();
      let spatial_grid = new Map();
      let suspicious_names = [];
      let total_major = 0;

      //Guard clauses
      let part_dir = path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let meta_arr = [];
      if (!options.meta_path && fs.existsSync(man_path)) {
        let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
        let shards = Array.isArray(man.shards) ? man.shards : [];
        let pkey = String(proj.key || "").toUpperCase();
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          if (pkey && sh.key !== "CAPITALS" && sh.key !== pkey && sh.key !== "UNASSIGNED") continue;
          let sp = path.join(part_dir, sh.file);
          if (fs.existsSync(sp)) meta_arr = meta_arr.concat(JSON.parse(fs.readFileSync(sp, "utf8")));
        }
      } else if (fs.existsSync(meta_path)) {
        meta_arr = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      }
      if (!Array.isArray(meta_arr) || meta_arr.length === 0 || shard_files.length === 0)
        return { bad_dates: 0, coverage_pct: 100, near_dups: 0, pre1850_coverage_pct: 100, suspicious_names: 0 };

      //Function body

      for (let i = 0; i < meta_arr.length; i++) {
        let rec = meta_arr[i];
        if (!rec || !Array.isArray(rec.coords) || rec.coords.length < 2) continue;
        let lat = Number(rec.coords[1]);
        let lng = Number(rec.coords[0]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

        let stems = new Set();
        let raw_names = [rec.name];
        if (Array.isArray(rec.other_names)) raw_names = raw_names.concat(rec.other_names);
        if (Array.isArray(rec.historical_names)) {
          for (let x = 0; x < rec.historical_names.length; x++) {
            if (rec.historical_names[x] && rec.historical_names[x].name)
              raw_names.push(rec.historical_names[x].name);
          }
        }
        for (let x = 0; x < raw_names.length; x++) {
          let st = this.normaliseEntityStem(raw_names[x]);
          if (st) stems.add(st);
        }

        let gkey = `${Math.round(lat*2)},${Math.round(lng*2)}`;
        if (!spatial_grid.has(gkey)) spatial_grid.set(gkey, []);
        spatial_grid.get(gkey).push({
          idx: i,
          lat: lat,
          lng: lng,
          rec: rec,
          stem: this.normaliseEntityStem(rec.name),
          stems: stems
        });
      }

      let shard_base = (options.shard_dir) ? options.shard_dir : path.join(dataview_root, "data/stadester/stadester_2.0");
      for (let i = 0; i < shard_files.length; i++) {
        let sp = path.isAbsolute(shard_files[i]) ? shard_files[i] : path.join(shard_base, shard_files[i]);
        if (!fs.existsSync(sp)) continue;
        let sobj = JSON.parse(fs.readFileSync(sp, "utf8"));
        let keys = Object.keys(sobj);

        for (let x = 0; x < keys.length; x++) {
          let city = sobj[keys[x]];
          if (!city || !Array.isArray(city.coords) || city.coords.length < 2) continue;
          let clat = Number(city.coords[0]);
          let clng = Number(city.coords[1]);
          let pop = (city.population && typeof city.population === "object") ? city.population : {};
          let yrs = [];
          let max_pop = 0;
          let ykeys = Object.keys(pop);
          for (let z = 0; z < ykeys.length; z++) {
            let yi = Number(ykeys[z]);
            let pv = Number(pop[ykeys[z]] || 0);
            if (Number.isFinite(yi) && pv > 0) {
              yrs.push(yi);
              if (pv > max_pop) max_pop = pv;
            }
          }
          if (yrs.length === 0) continue;
          yrs.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
          let earliest_yr = yrs[0];
          let is_major_or_hist = (max_pop >= 5000) || (earliest_yr < 1900);
          if (!is_major_or_hist) continue;
          total_major++;

          let c_stem = this.normaliseEntityStem(city.name || keys[x]);
          let gx = Math.round(clat*2);
          let gy = Math.round(clng*2);
          let best = null;
          let best_d = 999999;

          for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
              let bucket = spatial_grid.get(`${gx + dx},${gy + dy}`);
              if (!bucket) continue;
              for (let z = 0; z < bucket.length; z++) {
                let cand = bucket[z];
                let d_km = this.haversineKm(clat, clng, cand.lat, cand.lng);
                if (d_km > 25.0) continue;
                let name_hit = Boolean(c_stem && (cand.stems.has(c_stem) || this.areEquivalentExonyms(city.name || keys[x], cand.rec.name || "", profiles)));
                if (name_hit && d_km < best_d) {
                  best = cand;
                  best_d = d_km;
                }
              }
            }
          }

          if (!best) continue;
          matched_major++;
          matched_meta_indices.add(best.idx);

          let hn = Array.isArray(best.rec.historical_names) ? best.rec.historical_names : [];
          if (earliest_yr < 1850) {
            matched_pre1850++;
            if (hn.length > 0 && this.isValidCalendarDate(hn[0].date)) {
              let first_h_yr = Number(String(hn[0].date).split(".")[0]);
              if (first_h_yr <= earliest_yr + 100)
                pre1850_covered++;
              else
                earliest_gap_hits.push(`${keys[x]}(earliest=${earliest_yr},first_meta=${first_h_yr})`);
            } else {
              earliest_gap_hits.push(`${keys[x]}(earliest=${earliest_yr},missing_hist)`);
            }
          }
        }
      }

      // Inspect every matched regional city_metadata entry for date errors, variant dup renames, suspicious names & near-dups
      let matched_list = [];
      matched_meta_indices.forEach(function (arg0_idx) {
        let rec = meta_arr[arg0_idx];
        if (!rec) return;
        let lat = Number(rec.coords[1]);
        let lng = Number(rec.coords[0]);
        matched_list.push({ idx: arg0_idx, lat: lat, lng: lng, rec: rec, stem: this.normaliseEntityStem(rec.name) });

        let susp = this.isSuspiciousToponym(rec.name, profiles);
        if (susp && !rec.verified_settlement)
          suspicious_names.push(`${rec.name} (${susp})`);

        let hn = Array.isArray(rec.historical_names) ? rec.historical_names : [];
        let prev_yr = -999999;
        let prev_stem = "";
        for (let x = 0; x < hn.length; x++) {
          let item = hn[x];
          if (!item || !this.isValidCalendarDate(item.date)) {
            bad_dates.push(`${rec.name}:${item ? item.date : "null"}`);
            continue;
          }
          let yr = Number(String(item.date).split(".")[0]);
          if (yr < prev_yr)
            bad_dates.push(`${rec.name}:unsorted(${prev_yr}->${yr})`);
          prev_yr = yr;

          let h_susp = this.isSuspiciousToponym(item.name, profiles);
          if (h_susp && !rec.verified_settlement)
            suspicious_names.push(`${rec.name}->${item.name} (${h_susp})`);

          let h_stem = this.normaliseEntityStem(item.name);
          if (prev_stem && h_stem && h_stem === prev_stem && item.name !== hn[x - 1].name)
            consec_variant_dups.push(`${rec.name}:${hn[x - 1].name}->${item.name}`);
          prev_stem = h_stem;
        }
      }, this);

      // Pairwise near-duplicate check across matched regional metadata entries
      matched_list.sort(function (arg0_a, arg1_b) { return arg0_a.lat - arg1_b.lat; });
      for (let i = 0; i < matched_list.length; i++) {
        let a = matched_list[i];
        for (let x = i + 1; x < matched_list.length; x++) {
          let b = matched_list[x];
          if (b.lat - a.lat > 0.16) break;
          let d_km = this.haversineKm(a.lat, a.lng, b.lat, b.lng);
          if (d_km <= 1.5 || (d_km <= 15.0 && a.stem && b.stem && (a.stem === b.stem || this.areEquivalentExonyms(a.rec.name, b.rec.name, profiles))))
            near_dups.push(`${a.rec.name}<->${b.rec.name} (${d_km.toFixed(1)} km)`);
        }
      }

      let cov_pct = (total_major > 0) ? (100.0*matched_major/total_major) : 100.0;
      let pre1850_pct = (matched_pre1850 > 0) ? (100.0*pre1850_covered/matched_pre1850) : 100.0;

      if (total_major >= 20 && cov_pct < 95.0)
        errors.push(`Regional city_metadata.json coverage for ${proj.key || "PROJECT"} is ${matched_major}/${total_major} (${cov_pct.toFixed(1)}% < 95.0% floor).`);
      if (matched_pre1850 >= 10 && pre1850_pct < 90.0)
        errors.push(`Pre-1850 historical_names earliest-year coverage for ${proj.key || "PROJECT"} is ${pre1850_covered}/${matched_pre1850} (${pre1850_pct.toFixed(1)}% < 90.0% floor): ${earliest_gap_hits.slice(0, 5).join(", ")}`);
      if (bad_dates.length > 0)
        errors.push(`Invalid or unsorted historical_names dates in city_metadata.json (${bad_dates.length}): ${bad_dates.slice(0, 5).join(", ")}`);
      if (consec_variant_dups.length > 0)
        errors.push(`Spurious consecutive variant-spelling renames in city_metadata.json (${consec_variant_dups.length}): ${consec_variant_dups.slice(0, 5).join(", ")}`);
      if (suspicious_names.length > 0)
        errors.push(`Suspicious temple/monument/admin names in city_metadata.json (${suspicious_names.length}): ${suspicious_names.slice(0, 5).join(", ")}`);
      if (near_dups.length > 0)
        errors.push(`Near-duplicate city_metadata.json records (${near_dups.length}): ${near_dups.slice(0, 5).join(", ")}`);

      //Return statement
      return {
        bad_dates: bad_dates.length,
        consec_variant_dups: consec_variant_dups.length,
        coverage_pct: Number(cov_pct.toFixed(2)),
        near_dups: near_dups.length,
        pre1850_coverage_pct: Number(pre1850_pct.toFixed(2)),
        suspicious_names: suspicious_names.length
      };
    },

    /**
     * Audits annual `getCitiesAtYear` point-density continuity across the macro-region's manifest
     * modern census span and checks Dataview `city_metadata.json` for regional orphans or corruptions.
     * @alias viscount_entity_audit.verifyAnnualContinuityAndOrphans
     *
     * @param {Object} arg0_proj
     * @param {string} arg1_svea_root
     * @param {string} arg2_dataview_root
     * @param {Array<string>} arg3_shard_files
     * @param {Array<string>} arg4_errors
     *
     * @returns {Object} Continuity and metadata summary
     */
    verifyAnnualContinuityAndOrphans (arg0_proj, arg1_svea_root, arg2_dataview_root, arg3_shard_files, arg4_errors) {
      //Convert from parameters
      let proj = (arg0_proj) ? arg0_proj : {};
      let svea_root = arg1_svea_root;
      let dataview_root = arg2_dataview_root;
      let shard_files = Array.isArray(arg3_shard_files) ? arg3_shard_files : [];
      let errors = arg4_errors;

      //Declare local instance variables
      let bad_meta = 0;
      let cities = [];
      let default_map = (this.loadSkillProfiles(svea_root).macro_region_defaults) || {};
      let max_yoy_pct = 0.0;
      let max_yoy_year = null;
      let meta_orphans = [];
      let proj_countries = new Set();
      let region_def = default_map[String(proj.key || "").toUpperCase()] || {};
      let shard_key_set = new Set();
      let splice_set = new Set(Array.isArray(region_def.default_border_splice_years) ? region_def.default_border_splice_years : []);
      let y0 = Number(region_def.default_modern_census_year || 1850);
      let y1 = 2025;

      //Guard clauses
      if (shard_files.length === 0)
        return { bad_meta: 0, max_yoy_pct: 0, meta_orphans: 0, span: [y0, y1] };

      //Function body
      let gaz_rel = String(proj.gazetteer_manifest || "");
      let gaz_abs = gaz_rel ? path.join(svea_root, gaz_rel) : "";
      if (gaz_abs && fs.existsSync(gaz_abs)) {
        try {
          let gaz_obj = JSON5.parse(fs.readFileSync(gaz_abs, "utf8"));
          if (Array.isArray(gaz_obj.annual_continuity_span) && gaz_obj.annual_continuity_span.length >= 2) {
            y0 = Number(gaz_obj.annual_continuity_span[0]);
            y1 = Number(gaz_obj.annual_continuity_span[1]);
          }
          if (Array.isArray(gaz_obj.border_splice_years)) {
            splice_set = new Set();
            for (let i = 0; i < gaz_obj.border_splice_years.length; i++)
              splice_set.add(Number(gaz_obj.border_splice_years[i]));
          }
        } catch (e) {}
      }

      let raw_c = Array.isArray(proj.countries) ? proj.countries : [];
      for (let i = 0; i < raw_c.length; i++)
        proj_countries.add(String(raw_c[i] || "").trim().toLowerCase());

      for (let i = 0; i < shard_files.length; i++) {
        let sp = path.join(dataview_root, "data/stadester/stadester_2.0", shard_files[i]);
        if (!fs.existsSync(sp)) continue;
        let sobj = JSON.parse(fs.readFileSync(sp, "utf8"));
        let keys = Object.keys(sobj);
        for (let x = 0; x < keys.length; x++) {
          let ck = keys[x];
          shard_key_set.add(ck);
          let pop = sobj[ck] && sobj[ck].population ? sobj[ck].population : null;
          if (!pop || typeof pop !== "object") continue;
          let ykeys = Object.keys(pop);
          let yrs = [];
          let pmap = {};
          for (let z = 0; z < ykeys.length; z++) {
            let yi = Number(ykeys[z]);
            let pv = Number(pop[ykeys[z]] || 0);
            if (Number.isFinite(yi) && pv >= 0.01) {
              yrs.push(yi);
              pmap[yi] = pv;
            }
          }
          if (yrs.length > 0) {
            yrs.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
            cities.push({ end_yr: yrs[yrs.length - 1], pmap: pmap, start_yr: yrs[0], yrs: yrs });
          }
        }
      }

      let annual_counts = {};
      for (let yr = y0; yr <= y1; yr++) {
        let act = 0;
        for (let i = 0; i < cities.length; i++) {
          let c = cities[i];
          let in_range = (yr >= c.start_yr && yr <= c.end_yr) || (c.end_yr >= 1975 && yr >= 1975 && yr <= 2026);
          if (!in_range) continue;
          if (c.pmap[yr] !== undefined || yr <= c.start_yr || yr >= c.end_yr) {
            act++;
          } else {
            let lo = 0;
            let hi = c.yrs.length;
            for (let iter = 0; lo < hi && iter < 32; iter++) {
              let mid = (lo + hi) >> 1;
              if (c.yrs[mid] < yr) lo = mid + 1;
              else hi = mid;
            }
            if (lo > 0 && lo < c.yrs.length && (c.yrs[lo] - c.yrs[lo - 1]) <= 200)
              act++;
          }
        }
        annual_counts[yr] = act;
      }

      let non_splice_jumps = [];
      for (let yr = y0 + 1; yr <= y1; yr++) {
        let prev_c = Number(annual_counts[yr - 1] || 0);
        let cur_c = Number(annual_counts[yr] || 0);
        if (prev_c < 25) continue;
        let pct = 100.0*Math.abs(cur_c - prev_c)/prev_c;
        if (!splice_set.has(yr) && !splice_set.has(yr - 1)) {
          if (pct > max_yoy_pct) {
            max_yoy_pct = pct;
            max_yoy_year = yr;
          }
          if (pct > 3.0)
            non_splice_jumps.push(`${yr}:${prev_c}->${cur_c} (${pct.toFixed(2)}%)`);
        }
      }
      if (non_splice_jumps.length > 0)
        errors.push(`Annual getCitiesAtYear continuity cliff > 3.0% outside border_splice_years [${y0}-${y1}]: ${non_splice_jumps.slice(0, 5).join(", ")}`);

      // Inspect Dataview stadester_2.0/city_metadata/ (or legacy city_metadata.json) for explicitly tagged orphans & corrupted entries
      let part_dir = path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata");
      let man_path = path.join(part_dir, "city_metadata_manifest.json");
      let meta_path = path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata.json");
      let meta_arr = [];
      if (fs.existsSync(man_path)) {
        let man = JSON.parse(fs.readFileSync(man_path, "utf8"));
        let shards = Array.isArray(man.shards) ? man.shards : [];
        let pkey = String(proj.key || "").toUpperCase();
        for (let i = 0; i < shards.length; i++) {
          let sh = shards[i];
          if (pkey && sh.key !== "CAPITALS" && sh.key !== pkey && sh.key !== "UNASSIGNED") continue;
          let sp = path.join(part_dir, sh.file);
          if (fs.existsSync(sp)) meta_arr = meta_arr.concat(JSON.parse(fs.readFileSync(sp, "utf8")));
        }
      } else if (fs.existsSync(meta_path)) {
        meta_arr = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      }
      if (Array.isArray(meta_arr)) {
        for (let i = 0; i < meta_arr.length; i++) {
          let rec = meta_arr[i];
          if (!rec || typeof rec !== "object") continue;
          let nm = String(rec.name || "");
          if (!nm || nm.includes("\uFFFD")) bad_meta++;
          let c_str = String(rec.country || "").trim().toLowerCase();
          let k_str = String(rec.key || "");
          if (c_str && proj_countries.has(c_str) && k_str && !shard_key_set.has(k_str))
            meta_orphans.push(k_str);
        }
      }
      if (bad_meta > 0)
        errors.push(`Dataview city_metadata.json contains ${bad_meta} entry/entries with empty or U+FFFD corrupted name.`);
      if (meta_orphans.length > 0)
        errors.push(`Dataview city_metadata.json contains ${meta_orphans.length} explicitly orphaned ${proj.key} record(s): ${meta_orphans.slice(0, 5).join(", ")}`);

      //Return statement
      return {
        bad_meta: bad_meta,
        max_yoy_pct: Number(max_yoy_pct.toFixed(2)),
        max_yoy_year: max_yoy_year,
        meta_orphans: meta_orphans.length,
        span: [y0, y1]
      };
    }
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { viscount_entity_audit: viscount_entity_audit };
  }
}
