//Import modules
let fs = require("fs");
let path = require("path");
let { viscount_audit_utils } = require("./viscount_audit_utils");

//Initialise functions
{
  let municipal_district_consolidator = {
    _cached_intra_regexes: null,

    /**
     * Deduplicates `.other_names` case-insensitively, dropping any exact match to `arg0_canonical_name`.
     * @alias municipal_district_consolidator.deduplicateOtherNamesCI
     *
     * @param {string} arg0_canonical_name
     * @param {Array<string>} arg1_aliases
     *
     * @returns {Array<string>}
     */
    deduplicateOtherNamesCI (arg0_canonical_name, arg1_aliases) {
      //Convert from parameters
      let aliases = Array.isArray(arg1_aliases) ? arg1_aliases : [];
      let canonical_low = String(arg0_canonical_name || "").trim().toLowerCase();

      //Declare local instance variables
      let out = [];
      let seen = new Set();

      //Function body
      if (canonical_low) seen.add(canonical_low);
      for (let i = 0; i < aliases.length; i++) {
        let s = String(aliases[i] || "").trim();
        let low = s.toLowerCase();
        if (!s || seen.has(low)) continue;
        seen.add(low);
        out.push(s);
      }

      //Return statement
      return out;
    },

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
     * Loads city-proper municipal boundary polygons from a GeoJSON FeatureCollection for exact same-municipality grouping.
     * Rejects features tagged as metropolitan areas / agglomerations so metro areas are NEVER collapsed into one point.
     * @alias municipal_district_consolidator.loadMunicipalBoundaries
     *
     * @param {string} arg0_geojson_path
     *
     * @returns {Array<Object>}
     */
    loadMunicipalBoundaries (arg0_geojson_path) {
      //Convert from parameters
      let gj_path = arg0_geojson_path;

      //Declare local instance variables
      let out = [];

      //Guard clauses
      if (!gj_path || !fs.existsSync(gj_path)) return out;

      //Function body
      let gj = JSON.parse(fs.readFileSync(gj_path, "utf8"));
      let feats = Array.isArray(gj.features) ? gj.features : [];
      for (let i = 0; i < feats.length; i++) {
        let f = feats[i];
        let props = (f && f.properties) ? f.properties : {};
        let scope = String(props.population_scope || props.boundary_type || props.type || "").toLowerCase();
        if (scope.includes("metro") || scope.includes("agglomeration") || scope.includes("degurba"))
          continue;
        let geom = f && f.geometry;
        if (!geom || !geom.coordinates) continue;

        let polys = [];
        if (geom.type === "Polygon") polys.push(geom.coordinates);
        else if (geom.type === "MultiPolygon") {
          for (let x = 0; x < geom.coordinates.length; x++) polys.push(geom.coordinates[x]);
        }
        if (polys.length === 0) continue;

        let min_x = 999;
        let min_y = 999;
        let max_x = -999;
        let max_y = -999;
        for (let p = 0; p < polys.length; p++) {
          let ring = polys[p][0] || [];
          for (let r = 0; r < ring.length; r++) {
            let x = Number(ring[r][0]);
            let y = Number(ring[r][1]);
            if (x < min_x) min_x = x;
            if (x > max_x) max_x = x;
            if (y < min_y) min_y = y;
            if (y > max_y) max_y = y;
          }
        }
        out.push({
          bbox: [min_x, min_y, max_x, max_y],
          id: String(props.municipality_id || props.id || props.name || `mun_${i}`),
          name: String(props.name || props.municipality_name || "").trim(),
          polys: polys
        });
      }

      //Return statement
      return out;
    },

    /**
     * Tests whether `[lat, lng]` lies inside a GeoJSON Polygon/MultiPolygon exterior ring (respecting holes).
     * @alias municipal_district_consolidator.pointInMunicipality
     *
     * @param {number} arg0_lat
     * @param {number} arg1_lng
     * @param {Object} arg2_mun
     *
     * @returns {boolean}
     */
    pointInMunicipality (arg0_lat, arg1_lng, arg2_mun) {
      //Convert from parameters
      let lat = Number(arg0_lat);
      let lng = Number(arg1_lng);
      let mun = arg2_mun;

      //Guard clauses
      if (!mun || !mun.bbox) return false;
      if (lng < mun.bbox[0] || lng > mun.bbox[2] || lat < mun.bbox[1] || lat > mun.bbox[3]) return false;

      //Function body
      let pointInRing = function (arg0_x, arg1_y, arg2_ring) {
        let inside = false;
        for (let i = 0, j = arg2_ring.length - 1; i < arg2_ring.length; j = i++) {
          let xi = arg2_ring[i][0];
          let yi = arg2_ring[i][1];
          let xj = arg2_ring[j][0];
          let yj = arg2_ring[j][1];
          let inter = ((yi > arg1_y) !== (yj > arg1_y)) &&
            (arg0_x < (xj - xi)*(arg1_y - yi)/((yj - yi) || 1e-12) + xi);
          if (inter) inside = !inside;
        }
        return inside;
      };

      for (let p = 0; p < mun.polys.length; p++) {
        let outer = mun.polys[p][0];
        if (!outer || outer.length < 3) continue;
        if (!pointInRing(lng, lat, outer)) continue;
        let in_hole = false;
        for (let h = 1; h < mun.polys[p].length; h++) {
          if (pointInRing(lng, lat, mun.polys[p][h])) {
            in_hole = true;
            break;
          }
        }
        if (!in_hole) return true;
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
     * Consolidates settlements obeying Structural Rule for Merging #1:
     * 1. Accidental duplicate points or intra-municipal subdivisions sharing the SAME city-proper municipal boundary
     *    are merged up to one unified municipality (capital status overrides largest population).
     * 2. Distinct municipalities in the same metro area are NEVER collapsed together (preserved as separate city_proper/suburb points).
     * @alias municipal_district_consolidator.consolidateSettlements
     *
     * @param {Object} arg0_settlements_obj
     * @param {Object} [arg1_options]
     *  @param {Set<string>} [arg1_options.capital_keys] - Known capital city keys/stems (override largest population)
     *  @param {Array<Object>|string} [arg1_options.municipal_boundaries] - Loaded municipal boundary polygons or GeoJSON path
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
      let mun_polys = (typeof options.municipal_boundaries === "string") ?
        this.loadMunicipalBoundaries(options.municipal_boundaries) :
        (Array.isArray(options.municipal_boundaries) ? options.municipal_boundaries : []);
      let out = {};
      let profiles = options.profiles || viscount_audit_utils.loadSkillProfiles();
      let report = [];

      //Function body
      let districts = [];
      let top_level = [];

      for (let i = 0; i < keys.length; i++) {
        let k = keys[i];
        let rec = settlements[k];
        if (!rec || typeof rec !== "object") continue;

        let is_metro = Boolean(rec.population_scope === "metro" || rec.extent_type === "metro" || rec.is_agglomeration);
        let is_intra = !is_metro && (Boolean(rec.is_intra_municipal_district) || this.isIntraMunicipalSubdivision(rec.name || k, profiles));

        let max_pop = 0;
        let pop = rec.population || {};
        let py = Object.keys(pop);
        for (let x = 0; x < py.length; x++) {
          let v = Number(pop[py[x]] || 0);
          if (v > max_pop) max_pop = v;
        }

        let mun_id = rec.municipal_boundary_id || "";
        let mun_name = rec.parent_municipal_city || "";
        if (!is_metro && !mun_id && mun_polys.length > 0 && Array.isArray(rec.coords) && rec.coords.length >= 2) {
          for (let m = 0; m < mun_polys.length; m++) {
            if (this.pointInMunicipality(rec.coords[0], rec.coords[1], mun_polys[m])) {
              mun_id = mun_polys[m].id;
              if (!mun_name && mun_polys[m].name) mun_name = mun_polys[m].name;
              break;
            }
          }
        }

        let item = {
          coords: Array.isArray(rec.coords) ? rec.coords : null,
          country: String(rec.country || ""),
          is_capital: Boolean(rec.is_capital || rec.capital || cap_keys.has(k) || cap_keys.has(String(rec.name || "").toLowerCase())),
          is_metro: is_metro,
          key: k,
          max_pop: max_pop,
          mun_id: mun_id,
          parent_city: mun_name,
          rec: rec
        };
        if (is_intra) districts.push(item);
        else top_level.push(item);
      }

      // 1. Merge accidental split points sharing the EXACT SAME city-proper municipal_boundary_id
      //    (never merges separate municipalities in the same metro area)
      let by_mun_id = new Map();
      let unified_top = [];
      for (let i = 0; i < top_level.length; i++) {
        let it = top_level[i];
        if (!it.is_metro && it.mun_id) {
          let mk = `${it.country.toLowerCase()}|${it.mun_id}`;
          if (!by_mun_id.has(mk)) by_mun_id.set(mk, []);
          by_mun_id.get(mk).push(it);
        } else {
          unified_top.push(it);
        }
      }

      let that = this;
      by_mun_id.forEach(function (arg0_group) {
        if (arg0_group.length === 1) {
          unified_top.push(arg0_group[0]);
          return;
        }
        // Precedence: capital overrides largest population; then non-district municipal name; then largest population
        arg0_group.sort(function (arg0_a, arg1_b) {
          if (arg0_a.is_capital !== arg1_b.is_capital) return arg0_a.is_capital ? -1 : 1;
          return arg1_b.max_pop - arg0_a.max_pop;
        });
        let lead = arg0_group[0];
        let merged_pop = Object.assign({}, lead.rec.population || {});
        let aliases = Array.isArray(lead.rec.other_names) ? lead.rec.other_names.slice() : [];

        for (let i = 1; i < arg0_group.length; i++) {
          let sub = arg0_group[i];
          let sub_pop = sub.rec.population || {};
          let yrs = Object.keys(sub_pop);
          for (let y = 0; y < yrs.length; y++) {
            let v = Number(sub_pop[yrs[y]] || 0);
            if (!(v > 0)) continue;
            // Backfill missing years; for overlapping years inside same municipal boundary, avoid double-counting unified totals
            if (merged_pop[yrs[y]] === undefined)
              merged_pop[yrs[y]] = Math.round(v);
            else if (sub.rec.is_split_municipal_part)
              merged_pop[yrs[y]] = Math.round(Number(merged_pop[yrs[y]]) + v);
            else if (v > Number(merged_pop[yrs[y]]))
              merged_pop[yrs[y]] = Math.round(v);
          }
          if (sub.rec.name) aliases.push(sub.rec.name);
          if (Array.isArray(sub.rec.other_names)) aliases = aliases.concat(sub.rec.other_names);
          collapsed_count++;
          report.push({
            action: "merged_same_municipal_boundary_point",
            merged_key: sub.key,
            municipal_boundary_id: lead.mun_id,
            target_key: lead.key
          });
        }

        let canonical_name = lead.is_capital ? (lead.rec.name || lead.parent_city || lead.key) : (lead.parent_city || lead.rec.name || lead.key);
        let dedup_other = that.deduplicateOtherNamesCI(canonical_name, aliases);
        let merged_rec = Object.assign({}, lead.rec, {
          name: canonical_name,
          population: merged_pop,
          population_scope: lead.rec.population_scope || "city_proper"
        });
        if (dedup_other.length > 0) merged_rec.other_names = dedup_other;
        else delete merged_rec.other_names;
        lead.rec = merged_rec;
        unified_top.push(lead);
      });

      for (let i = 0; i < unified_top.length; i++) {
        let it = unified_top[i];
        let dedup_o = this.deduplicateOtherNamesCI(it.rec.name || it.key, it.rec.other_names);
        let copy = Object.assign({}, it.rec, {
          population_scope: it.rec.population_scope || (it.is_metro ? "metro" : "city_proper")
        });
        if (dedup_o.length > 0) copy.other_names = dedup_o;
        else delete copy.other_names;
        out[it.key] = copy;
      }

      // 2. Match explicit intra-municipal districts to their parent municipality (by boundary ID first, else radius)
      let orphan_groups = new Map();
      for (let i = 0; i < districts.length; i++) {
        let d = districts[i];
        let matched_parent = null;
        let best_dist = intra_rad_km;

        if (d.parent_city && out[d.parent_city]) {
          matched_parent = { key: d.parent_city, rec: out[d.parent_city] };
        } else if (d.mun_id) {
          for (let x = 0; x < unified_top.length; x++) {
            if (!unified_top[x].is_metro && unified_top[x].mun_id === d.mun_id && unified_top[x].country === d.country) {
              matched_parent = unified_top[x];
              break;
            }
          }
        }
        if (!matched_parent && d.coords && d.coords.length >= 2) {
          for (let x = 0; x < unified_top.length; x++) {
            let p = unified_top[x];
            if (p.is_metro || !p.coords || p.country !== d.country) continue;
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
          let gkey = d.mun_id || d.parent_city || `${d.country}|${d.coords ? Math.round(d.coords[0]*5) : 0},${d.coords ? Math.round(d.coords[1]*5) : 0}`;
          if (!orphan_groups.has(gkey)) orphan_groups.set(gkey, []);
          orphan_groups.get(gkey).push(d);
        }
      }

      // 3. Aggregate district-only municipalities (capital status overrides largest population)
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
        let clean_name = lead.is_capital ? (lead.rec.name || lead.parent_city || lead.key) : (lead.parent_city || lead.rec.name || lead.key);
        let clean_key = lead.parent_city ? `${clean_name}-${lead.country}` : lead.key;
        let dedup_o = that.deduplicateOtherNamesCI(clean_name, lead.rec.other_names);
        let merged = Object.assign({}, lead.rec, {
          consolidated_intra_districts: arg0_group.length,
          name: clean_name,
          population: agg_pop,
          population_scope: "city_proper"
        });
        if (dedup_o.length > 0) merged.other_names = dedup_o;
        else delete merged.other_names;
        out[clean_key] = merged;

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
        kept_extra_municipal: unified_top.length,
        report: report,
        settlements: out
      };
    }
  };

  if (require.main === module) {
    let argv = process.argv.slice(2);
    let boundaries = "";
    let dry_run = false;
    let in_file = "";
    let out_file = "";
    for (let i = 0; i < argv.length; i++) {
      if (argv[i] === "--dry-run") dry_run = true;
      else if (argv[i].startsWith("--out=")) out_file = argv[i].slice(6);
      else if (argv[i].startsWith("--municipal-boundaries=")) boundaries = argv[i].slice(23);
      else if (!argv[i].startsWith("--") && !in_file) in_file = argv[i];
    }
    if (!in_file || !fs.existsSync(in_file)) {
      console.error("[consolidate_municipal_districts] Usage: node consolidate_municipal_districts.js <settlements.json> [--municipal-boundaries=<geojson>] [--out=<file>] [--dry-run]");
      process.exit(1);
    }
    let data = viscount_audit_utils.loadJsonOrJson5(in_file);
    let res = municipal_district_consolidator.consolidateSettlements(data, { municipal_boundaries: boundaries });
    if (!dry_run && out_file)
      fs.writeFileSync(out_file, JSON.stringify(res.settlements, null, 2), "utf8");
    console.log(`[consolidate_municipal_districts] Kept ${res.kept_extra_municipal} top-level/extra-municipal settlements, consolidated ${res.collapsed_count} intra-municipal/same-boundary record(s).`);
  } else if (typeof module !== "undefined" && module.exports) {
    module.exports = { municipal_district_consolidator: municipal_district_consolidator };
  }
}
