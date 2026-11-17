//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

//Initialise functions
{
  let viscount_entity_audit = {
    _cached_profiles: null,

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

      //Declare local instance variables
      let groups = Array.isArray(profiles.romanisation_equivalences) ? profiles.romanisation_equivalences : [];

      //Function body
      for (let i = 0; i < groups.length; i++) {
        let g = groups[i];
        if (!Array.isArray(g)) continue;
        let has_a = false;
        let has_b = false;
        for (let x = 0; x < g.length; x++) {
          let item = String(g[x] || "");
          if (item === a) has_a = true;
          if (item === b) has_b = true;
        }
        if (has_a && has_b) return true;
      }

      //Return statement
      return false;
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
      for (let i = 0; i < quals.length; i++) {
        let q = String(quals[i] || "").trim();
        if (!q) continue;
        let escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        let re = new RegExp(`\\b${escaped}\\b`, "i");
        if (re.test(raw_name)) return true;
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

      // Inspect Dataview stadester_2.0/city_metadata.json for explicitly tagged orphans & corrupted entries
      let meta_path = path.join(dataview_root, "data/stadester/stadester_2.0/city_metadata.json");
      if (fs.existsSync(meta_path)) {
        let meta_arr = JSON.parse(fs.readFileSync(meta_path, "utf8"));
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
