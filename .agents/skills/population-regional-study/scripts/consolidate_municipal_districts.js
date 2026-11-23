//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let municipal_district_consolidator = {
    _cached_intra_regexes: null,

    /**
     * Checks whether a settlement name represents an intra-municipal administrative subdivision
     * (arrondissement, borough, ward, urban raion, shiyakha, Stadtbezirk, etc.) rather than an extra-municipal suburb.
     * @alias municipal_district_consolidator.isIntraMunicipalSubdivision
     *
     * @param {string} arg0_name
     * @param {Object} [arg1_profiles]
     *
     * @returns {boolean}
     */
    isIntraMunicipalSubdivision (arg0_name, arg1_profiles) {
      //Convert from parameters
      let name = String(arg0_name || "").trim();
      let profiles = arg1_profiles || viscount_audit_utils.loadSkillProfiles();

      //Guard clauses
      if (!name) return false;

      //Function body
      if (!this._cached_intra_regexes) {
        let rules = (profiles && profiles.municipal_decomposition_rules) ? profiles.municipal_decomposition_rules : {};
        let pats = Array.isArray(rules.intra_municipal_suffix_regexes) ? rules.intra_municipal_suffix_regexes : [];
        this._cached_intra_regexes = [];
        for (let i = 0; i < pats.length; i++)
          this._cached_intra_regexes.push(new RegExp(pats[i], "i"));
      }
      for (let i = 0; i < this._cached_intra_regexes.length; i++) {
        if (this._cached_intra_regexes[i].test(name)) return true;
      }

      //Return statement
      return false;
    },

    /**
     * Normalises corrupted ASCII digraphs (e.g. `UEskuedar` -> `Üsküdar` style fixes) and detects raw non-Latin strings.
     * @alias municipal_district_consolidator.sanitiseDistrictLabel
     *
     * @param {string} arg0_name
     *
     * @returns {{ clean_name: string, has_raw_non_latin: boolean }}
     */
    sanitiseDistrictLabel (arg0_name) {
      //Convert from parameters
      let raw = String(arg0_name || "").trim();

      //Function body
      let clean = raw
        .replace(/\s*\(mod_uk\)\s*$/i, "")
        .replace(/^UE([a-z])/, "Ü$1")
        .replace(/^OE([a-z])/, "Ö$1")
        .replace(/^AE([a-z])/, "Ä$1")
        .replace(/ue/g, function (arg0_m, arg1_off, arg2_str) {
          return /[ksczg]$/i.test(arg2_str.slice(0, arg1_off)) ? "ü" : arg0_m;
        })
        .trim();
      let has_non_latin = /[\u0600-\u06FF\u0400-\u04FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/.test(clean);

      //Return statement
      return { clean_name: clean, has_raw_non_latin: has_non_latin };
    },

    /**
     * Consolidates intra-municipal districts in a settlement dictionary onto their single top-level city entity
     * (capital status overrides largest population; extra-municipal suburbs remain untouched).
     * @alias municipal_district_consolidator.consolidateSettlements
     *
     * @param {Object} arg0_settlements_obj
     * @param {Object} [arg1_options]
     *  @param {Set<string>} [arg1_options.capital_keys] - Known capital city keys/stems (override largest population)
     *  @param {Object} [arg1_options.profiles]
     *  @param {number} [arg1_options.intra_radius_km=8.0]
     *
     * @returns {{ collapsed_count: number, kept_extra_municipal: number, report: Array<Object>, settlements: Object }}
     */
    consolidateSettlements (arg0_settlements_obj, arg1_options) {
      //Convert from parameters
      let options = arg1_options || {};
      let settlements = arg0_settlements_obj || {};

      //Declare local instance variables
      let cap_keys = (options.capital_keys instanceof Set) ? options.capital_keys : new Set();
      let collapsed_count = 0;
      let intra_rad_km = Number(options.intra_radius_km) || 8.0;
      let keys = Object.keys(settlements);
      let out = {};
      let profiles = options.profiles || viscount_audit_utils.loadSkillProfiles();
      let report = [];

      //Function body
      //1. Separate explicit intra-municipal subdivisions from standard municipal/suburban records
      let districts = [];
      let top_level = [];

      for (let i = 0; i < keys.length; i++) {
        let k = keys[i];
        let rec = settlements[k];
        if (!rec || typeof rec !== "object") continue;
        let is_intra = Boolean(rec.is_intra_municipal_district) ||
          this.isIntraMunicipalSubdivision(rec.name || k, profiles);

        let max_pop = 0;
        let pop = rec.population || {};
        let py = Object.keys(pop);
        for (let x = 0; x < py.length; x++) {
          let v = Number(pop[py[x]] || 0);
          if (v > max_pop) max_pop = v;
        }
        let item = {
          coords: Array.isArray(rec.coords) ? rec.coords : null,
          country: String(rec.country || ""),
          is_capital: Boolean(rec.is_capital || cap_keys.has(k) || cap_keys.has(String(rec.name || "").toLowerCase())),
          key: k,
          max_pop: max_pop,
          parent_city: rec.parent_municipal_city || "",
          rec: rec
        };
        if (is_intra) districts.push(item);
        else {
          top_level.push(item);
          out[k] = Object.assign({}, rec, {
            population_scope: rec.population_scope || "city_proper"
          });
        }
      }

      //2. Match each intra-municipal district to an existing top-level municipality within intra_rad_km (or group orphan district-only cities)
      let orphan_groups = new Map();
      for (let i = 0; i < districts.length; i++) {
        let d = districts[i];
        let matched_parent = null;
        let best_dist = intra_rad_km;

        if (d.parent_city && out[d.parent_city]) {
          matched_parent = { key: d.parent_city, rec: out[d.parent_city] };
        } else if (d.coords && d.coords.length >= 2) {
          for (let x = 0; x < top_level.length; x++) {
            let p = top_level[x];
            if (!p.coords || p.country !== d.country) continue;
            let dist = viscount_audit_utils.haversineKm(d.coords[0], d.coords[1], p.coords[0], p.coords[1]);
            if (dist <= best_dist && p.max_pop >= d.max_pop*0.5) {
              best_dist = dist;
              matched_parent = p;
            }
          }
        }

        if (matched_parent) {
          collapsed_count++;
          report.push({
            action: "dropped_overlapping_intra_district",
            district_key: d.key,
            parent_key: matched_parent.key
          });
        } else {
          let gkey = d.parent_city || `${d.country}|${d.coords ? Math.round(d.coords[0]*5) : 0},${d.coords ? Math.round(d.coords[1]*5) : 0}`;
          if (!orphan_groups.has(gkey)) orphan_groups.set(gkey, []);
          orphan_groups.get(gkey).push(d);
        }
      }

      //3. For district-only cities lacking a top-level record: aggregate onto single top-level city
      //Precedence: capital city status overrides largest population; otherwise largest-population district inherits name
      orphan_groups.forEach(function (arg0_group) {
        arg0_group.sort(function (arg0_a, arg1_b) {
          if (arg0_a.is_capital !== arg1_b.is_capital) return arg0_a.is_capital ? -1 : 1;
          return arg1_b.max_pop - arg0_a.max_pop;
        });
        let lead = arg0_group[0];
        let agg_pop = {};
        for (let i = 0; i < arg0_group.length; i++) {
          let pmap = arg0_group[i].rec.population || {};
          let yrs = Object.keys(pmap);
          for (let y = 0; y < yrs.length; y++) {
            let val = Number(pmap[yrs[y]] || 0);
            if (val > 0) agg_pop[yrs[y]] = Math.round((agg_pop[yrs[y]] || 0) + val);
          }
        }
        let clean_name = lead.parent_city || lead.rec.name || lead.key;
        let clean_key = lead.parent_city ? `${clean_name}-${lead.country}` : lead.key;
        out[clean_key] = Object.assign({}, lead.rec, {
          consolidated_intra_districts: arg0_group.length,
          name: clean_name,
          population: agg_pop,
          population_scope: "city_proper"
        });
        if (arg0_group.length > 1) {
          collapsed_count += arg0_group.length - 1;
          report.push({
            action: "aggregated_district_only_municipality",
            canonical_key: clean_key,
            districts_merged: arg0_group.length,
            rule: lead.is_capital ? "capital_overrides_largest" : "largest_district_inherits"
          });
        }
      });

      //Return statement
      return {
        collapsed_count: collapsed_count,
        kept_extra_municipal: top_level.length,
        report: report,
        settlements: out
      };
    }
  };

  if (require.main === module) {
    let argv = process.argv.slice(2);
    let in_file = "";
    let out_file = "";
    let dry_run = false;
    for (let i = 0; i < argv.length; i++) {
      if (argv[i] === "--dry-run") dry_run = true;
      else if (argv[i].startsWith("--out=")) out_file = argv[i].slice(6);
      else if (!argv[i].startsWith("--") && !in_file) in_file = argv[i];
    }
    if (!in_file || !fs.existsSync(in_file)) {
      console.error("[consolidate_municipal_districts] Usage: node consolidate_municipal_districts.js <settlements.json> [--out=<file>] [--dry-run]");
      process.exit(1);
    }
    let data = viscount_audit_utils.loadJsonOrJson5(in_file);
    let res = municipal_district_consolidator.consolidateSettlements(data);
    if (!dry_run && out_file)
      fs.writeFileSync(out_file, JSON.stringify(res.settlements, null, 2), "utf8");
    console.log(`[consolidate_municipal_districts] Kept ${res.kept_extra_municipal} top-level/extra-municipal settlements, consolidated ${res.collapsed_count} intra-municipal district(s).`);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { municipal_district_consolidator: municipal_district_consolidator };
  }
}
