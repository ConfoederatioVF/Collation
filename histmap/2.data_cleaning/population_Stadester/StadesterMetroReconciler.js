//Import modules
let fs = require("fs");
let JSON5 = require("json5");
let path = require("path");

/**
 * Spatiotemporally agnostic 3-Phase Metropolitan Reconciliation engine for Operation Viscount & Stadestér.
 *
 * Eliminates double counting across mixed `city_proper`, `suburb` and `metro` datasets for all historical
 * epochs (`-10000` to `2025`), smoothly bridging pre-1975 transport-era envelopes with `1975-2025` GHSL DEGURBA:
 * - Phase 1: Subtract `city_proper` and constituent `suburb` populations from `metro` (`R = P_metro - S_sys`).
 * - Positive Residual (`R > 0`): `metro` retains `R`; constituents stay exact.
 * - Non-Positive Residual (`R <= 0`): Phase 2 computes constituent shares `w_i = P_i / S_sys`; Phase 3
 *   proportionally subtracts `|R|` from constituents (`P_i' = P_i + w_i*R`, yielding `P_metro*w_i` when
 *   `u = 1`) and removes the separate `metro` datapoint for year `t` whilst the persistent municipal
 *   `city_proper` datapoint continues existing uninterrupted (shock-free C^0 raster normalisation).
 */
class StadesterMetroReconciler {
  /**
   * Constructs a `StadesterMetroReconciler` instance backed by `viscount_skill_profiles.json5` defaults.
   *
   * @param {Object} [arg0_options]
   *  @param {number} [arg0_options.degurba_start_year=1975]
   *  @param {number} [arg0_options.degurba_taper_start_year=1965]
   *  @param {Object} [arg0_options.profiles]
   *  @param {boolean} [arg0_options.remove_absorbed_metros=true]
   *  @param {boolean} [arg0_options.use_trailing_carry=false]
   */
  constructor (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

    //Declare local instance variables
    let profiles = (options.profiles) ? options.profiles : this.loadDefaultProfiles();
    let policy = (profiles && profiles.metro_reconciliation_policy) ? profiles.metro_reconciliation_policy : {};

    //Function body
    this.conservation_tol = Number(policy.conservation_abs_tolerance) || 1.0;
    this.degurba_start_year = Number(options.degurba_start_year || policy.degurba_start_year || 1975);
    this.degurba_taper_start_year = Number(options.degurba_taper_start_year || policy.degurba_taper_start_year || 1965);
    this.remove_absorbed_metros = (options.remove_absorbed_metros !== undefined) ? Boolean(options.remove_absorbed_metros) : true;
    this.transport_envelopes = Array.isArray(policy.transport_era_envelopes) ? policy.transport_era_envelopes : [
      { coeff_km: 2.5, end_year: 1829, exponent: 0.35, id: "pre_rail_walking", max_radius_km: 12.0, start_year: -10000 },
      { coeff_km: 5.5, end_year: 1944, exponent: 0.35, id: "rail_tram", max_radius_km: 28.0, start_year: 1830 },
      { coeff_km: 8.5, end_year: 1974, exponent: 0.35, id: "automobile_pre_degurba", max_radius_km: 45.0, start_year: 1945 }
    ];
    this.use_trailing_carry = Boolean(options.use_trailing_carry);
  }

  /**
   * Computes the transport-era allometric catchment radius (in km) for a metro of population `arg0_pop` at year `arg1_year`.
   *
   * @param {number} arg0_pop
   * @param {number} arg1_year
   *
   * @returns {number}
   */
  computeTransportEnvelopeKm (arg0_pop, arg1_year) {
    //Convert from parameters
    let pop = Math.max(1000, Number(arg0_pop) || 10000);
    let year = Number(arg1_year) || 1900;

    //Declare local instance variables
    let env = this.transport_envelopes[this.transport_envelopes.length - 1];

    //Function body
    for (let i = 0; i < this.transport_envelopes.length; i++) {
      let cand = this.transport_envelopes[i];
      if (year >= Number(cand.start_year) && year <= Number(cand.end_year)) {
        env = cand;
        break;
      }
    }

    let raw_km = Number(env.coeff_km)*Math.pow(pop/10000.0, Number(env.exponent));
    let clamped_km = Math.min(Number(env.max_radius_km), Math.max(4.0, raw_km));

    //Return statement
    return clamped_km;
  }

  /**
   * Extracts normalised base settlement name (stripping `(agglomeration)`, `Greater `, `Metro `, country suffixes).
   *
   * @param {string} arg0_name
   *
   * @returns {string}
   */
  extractBaseName (arg0_name) {
    //Convert from parameters
    let raw = String(arg0_name || "");

    //Function body
    let clean = raw
      .replace(/\s*\([^)]*\)/g, "")
      .replace(/^(?:greater|metropolitan|metro|grand)\s+/i, "")
      .replace(/\s+(?:agglomeration|metropolitan area|metro area|conurbation|urban area)$/i, "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "");

    //Return statement
    return clean;
  }

  /**
   * Computes great-circle Haversine distance in km between two `[lat, lng]` coordinate pairs.
   *
   * @param {Array<number>} arg0_coords_a
   * @param {Array<number>} arg1_coords_b
   *
   * @returns {number}
   */
  haversineKm (arg0_coords_a, arg1_coords_b) {
    //Convert from parameters
    let lat1 = Number(arg0_coords_a[0]);
    let lon1 = Number(arg0_coords_a[1]);
    let lat2 = Number(arg1_coords_b[0]);
    let lon2 = Number(arg1_coords_b[1]);

    //Declare local instance variables
    let d_lat = (lat2 - lat1)*Math.PI/180.0;
    let d_lon = (lon2 - lon1)*Math.PI/180.0;
    let r1 = lat1*Math.PI/180.0;
    let r2 = lat2*Math.PI/180.0;

    //Function body
    let a = Math.sin(d_lat/2)*Math.sin(d_lat/2) +
      Math.cos(r1)*Math.cos(r2)*Math.sin(d_lon/2)*Math.sin(d_lon/2);

    //Return statement
    return 6371.0*2.0*Math.atan2(Math.sqrt(a), Math.sqrt(Math.max(0.0, 1.0 - a)));
  }

  /**
   * Determines whether a settlement record represents a metropolitan / agglomeration datapoint.
   *
   * @param {Object} arg0_city
   *
   * @returns {boolean}
   */
  isMetroRecord (arg0_city) {
    //Convert from parameters
    let city = arg0_city;

    //Guard clauses
    if (!city || typeof city !== "object") return false;

    //Function body
    if (city.population_scope === "metro" || city.extent_type === "metro" || city.is_agglomeration === true)
      return true;
    let nm = String(city.name || "").toLowerCase();
    let ky = String(city.key || "").toLowerCase();

    //Return statement
    return nm.includes("agglomeration") || nm.startsWith("greater ") || nm.includes("metropolitan") ||
      ky.includes("(agglomeration)") || ky.includes("greater ");
  }

  /**
   * Loads default `viscount_skill_profiles.json5` if present relative to SVEA root.
   *
   * @returns {Object}
   */
  loadDefaultProfiles () {
    //Declare local instance variables
    let cand = path.resolve(__dirname, "../../../.agents/skills/population-regional-study/config/viscount_skill_profiles.json5");

    //Function body
    try {
      if (fs.existsSync(cand))
        return JSON5.parse(fs.readFileSync(cand, "utf8"));
    } catch (e) {}

    //Return statement
    return {};
  }

  /**
   * Tests whether a non-metro settlement shares a canonical core name with a metropolitan record.
   *
   * @param {Object} arg0_city
   * @param {Object} arg1_metro
   *
   * @returns {boolean}
   */
  matchesMetroCoreName (arg0_city, arg1_metro) {
    //Convert from parameters
    let city = arg0_city;
    let metro = arg1_metro;

    //Function body
    let m_base = this.extractBaseName(metro.is_agglomeration_of || metro.name || metro.key);
    if (!m_base || m_base.length < 3) return false;

    let c_names = [city.name, city.key];
    if (Array.isArray(city.other_names)) c_names = c_names.concat(city.other_names);
    if (Array.isArray(city.original_names)) c_names = c_names.concat(city.original_names);

    for (let i = 0; i < c_names.length; i++) {
      let cb = this.extractBaseName(c_names[i]);
      if (cb && cb === m_base) return true;
    }

    //Return statement
    return false;
  }

  /**
   * Executes the full 3-Phase Spatiotemporally Agnostic Metropolitan Reconciliation over a Stadestér object.
   *
   * Mutates `arg0_stadester_obj` in place and returns `{ stats, stadester_obj }`:
   * - Positive residual (`R > 0`): `metro` retains `R`, constituents unchanged.
   * - Non-positive residual (`R <= 0`): redistributes `R` proportionally across `city_proper + suburbs`
   *   and deletes `metro.population[yr]`, whilst the persistent municipal `city_proper` datapoint continues existing.
   *
   * @param {Object} arg0_stadester_obj
   *
   * @returns {{ stadester_obj: Object, stats: Object }}
   */
  reconcile (arg0_stadester_obj) {
    //Convert from parameters
    let stadester_obj = (arg0_stadester_obj && typeof arg0_stadester_obj === "object") ? arg0_stadester_obj : {};

    //Declare local instance variables
    let all_keys = Object.keys(stadester_obj);
    let cell_deg = 1.0;
    let constituent_grid = new Map();
    let metros = [];
    let non_metros = [];
    let stats = {
      absorbed_metros_removed: 0,
      max_conservation_err: 0.0,
      metros_inspected: 0,
      multi_metro_normalisations: 0,
      reconciled_negative_pairs: 0,
      reconciled_positive_pairs: 0,
      removed_metro_year_points: 0
    };

    //Function body
    //1. Partition settlements into metros vs constituents and build 1-degree spatial hash over constituents
    for (let i = 0; i < all_keys.length; i++) {
      let k = all_keys[i];
      let c = stadester_obj[k];
      if (!c || typeof c !== "object" || !Array.isArray(c.coords) || c.coords.length < 2) continue;
      if (!c.key) c.key = k;

      if (this.isMetroRecord(c)) {
        metros.push(c);
      } else {
        non_metros.push(c);
        let gx = Math.floor(Number(c.coords[0])/cell_deg);
        let gy = Math.floor(Number(c.coords[1])/cell_deg);
        let gkey = `${gx},${gy}`;
        if (!constituent_grid.has(gkey)) constituent_grid.set(gkey, []);
        constituent_grid.get(gkey).push(c);
      }
    }

    stats.metros_inspected = metros.length;
    if (metros.length === 0)
      return { stadester_obj: stadester_obj, stats: stats };

    //Collect every year present on any metro record
    let all_years_set = new Set();
    for (let i = 0; i < metros.length; i++) {
      let pop = metros[i].population;
      if (!pop || typeof pop !== "object") continue;
      let ykeys = Object.keys(pop);
      for (let x = 0; x < ykeys.length; x++) {
        let yi = Number(ykeys[x]);
        let pv = Number(pop[ykeys[x]]);
        if (Number.isFinite(yi) && Number.isFinite(pv) && pv > 0) all_years_set.add(yi);
      }
    }
    let all_years = Array.from(all_years_set).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });

    //Track persistent municipal core presence per metro
    let metro_has_persistent_core = new Set();

    //2. Process each year independently so overlapping multi-metro weights satisfy sum_m u_{i,m}(t) <= 1
    for (let yi = 0; yi < all_years.length; yi++) {
      let yr = all_years[yi];
      let yr_str = String(yr);

      //Map metro_idx -> Array<{ city, dist_km, is_core, raw_u }>
      let metro_members = new Map();
      let city_total_u = new Map();

      for (let m_idx = 0; m_idx < metros.length; m_idx++) {
        let metro = metros[m_idx];
        let p_metro = (metro.population && metro.population[yr_str] !== undefined) ? Number(metro.population[yr_str]) : NaN;
        if (!Number.isFinite(p_metro) || p_metro <= 0) continue;

        let radius_km = this.computeTransportEnvelopeKm(p_metro, yr);
        let max_search_km = Math.max(radius_km, 25.0);
        let gx = Math.floor(Number(metro.coords[0])/cell_deg);
        let gy = Math.floor(Number(metro.coords[1])/cell_deg);
        let deg_rad = Math.max(1, Math.ceil(max_search_km/80.0));
        let members = [];

        for (let dx = -deg_rad; dx <= deg_rad; dx++) {
          for (let dy = -deg_rad; dy <= deg_rad; dy++) {
            let bucket = constituent_grid.get(`${gx + dx},${gy + dy}`);
            if (!bucket) continue;
            for (let b = 0; b < bucket.length; b++) {
              let cand = bucket[b];
              let c_pop = this.resolveConstituentPopAtYear(cand, yr);
              if (!(c_pop > 0)) continue;

              let d_km = this.haversineKm(metro.coords, cand.coords);
              if (d_km > max_search_km) continue;

              let explicit_link = (cand.metro_parent_key === metro.key || cand.metro_key === metro.key);
              let is_core = this.matchesMetroCoreName(cand, metro) && d_km <= 25.0;
              let same_country = (!metro.country || !cand.country || String(metro.country).toLowerCase() === String(cand.country).toLowerCase());
              let same_uc = Boolean(metro._ghsl_uc_id && cand._ghsl_uc_id && metro._ghsl_uc_id === cand._ghsl_uc_id);

              let u_pre = 0.0;
              if (explicit_link || is_core) {
                u_pre = 1.0;
              } else if (d_km <= radius_km && (same_country || d_km <= 15.0) && c_pop < p_metro*1.05) {
                // Only pull independent suburbs within the transport envelope (avoid swallowing a rival larger city)
                u_pre = 1.0;
              }

              let raw_u = u_pre;
              if (yr >= this.degurba_taper_start_year && yr < this.degurba_start_year && (metro._ghsl_uc_id || cand._ghsl_uc_id)) {
                let alpha = (yr - this.degurba_taper_start_year)/(this.degurba_start_year - this.degurba_taper_start_year);
                let u_deg = (same_uc || is_core) ? 1.0 : 0.0;
                raw_u = (1.0 - alpha)*u_pre + alpha*u_deg;
              } else if (yr >= this.degurba_start_year && (metro._ghsl_uc_id || cand._ghsl_uc_id)) {
                raw_u = (same_uc || is_core || explicit_link) ? 1.0 : 0.0;
              }

              if (raw_u > 1e-6) {
                if (is_core) metro_has_persistent_core.add(metro.key);
                members.push({ city: cand, dist_km: d_km, is_core: is_core, pop: c_pop, raw_u: raw_u });
                city_total_u.set(cand.key, (city_total_u.get(cand.key) || 0.0) + raw_u);
              }
            }
          }
        }

        if (members.length > 0) metro_members.set(m_idx, members);
      }

      //Accumulate proportional adjustments across all metros in year t without mutating baseline pops prematurely
      let city_delta_map = new Map();

      metro_members.forEach(function (arg0_members, arg1_m_idx) {
        let metro = metros[arg1_m_idx];
        let p_metro = Number(metro.population[yr_str]);
        let s_sys = 0.0;
        let eff_items = [];

        for (let i = 0; i < arg0_members.length; i++) {
          let mem = arg0_members[i];
          let tot_u = city_total_u.get(mem.city.key) || mem.raw_u;
          let u_norm = (tot_u > 1.0) ? (mem.raw_u/tot_u) : mem.raw_u;
          if (tot_u > 1.0 + 1e-9) stats.multi_metro_normalisations++;
          let p_eff = u_norm*mem.pop;
          s_sys += p_eff;
          eff_items.push({ city: mem.city, p_eff: p_eff, u_norm: u_norm });
          mem.city.metro_key = metro.key;
        }

        if (!(s_sys > 0)) return;

        //Phase 1: Subtract city_proper + constituent suburbs from metro population
        let r_metro = p_metro - s_sys;

        if (r_metro > 0.0) {
          //Positive residual: metro keeps ONLY the unenumerated hinterland residual
          metro.population[yr_str] = Math.round(r_metro);
          stats.reconciled_positive_pairs++;

          let cons_err = Math.abs((metro.population[yr_str] + s_sys) - p_metro);
          if (cons_err > stats.max_conservation_err) stats.max_conservation_err = cons_err;
        } else {
          //Non-positive residual (R <= 0):
          //Phase 2: Calculate each constituent's exact share w_i = P_eff_i / S_sys
          //Phase 3: Proportionally redistribute negative residual R onto constituents (Delta_i = w_i * R <= 0)
          //         and REMOVE the separate metro datapoint for year t whilst persistent city_proper continues existing
          let redistributed_sum = 0.0;
          for (let i = 0; i < eff_items.length; i++) {
            let it = eff_items[i];
            let share_w = it.p_eff/s_sys;
            let delta = share_w*r_metro;
            redistributed_sum += (it.p_eff + delta);
            city_delta_map.set(it.city.key, (city_delta_map.get(it.city.key) || 0.0) + delta);
          }

          delete metro.population[yr_str];
          stats.reconciled_negative_pairs++;
          stats.removed_metro_year_points++;

          let cons_err = Math.abs(redistributed_sum - p_metro);
          if (cons_err > stats.max_conservation_err) stats.max_conservation_err = cons_err;
        }
      });

      //Apply accumulated Phase-3 deltas atomically for year t
      city_delta_map.forEach(function (arg0_delta, arg1_ckey) {
        let city = stadester_obj[arg1_ckey];
        if (!city || !city.population || city.population[yr_str] === undefined) return;
        let orig = Number(city.population[yr_str]);
        if (!Number.isFinite(orig)) return;
        city.population[yr_str] = Math.max(0, Math.round(orig + arg0_delta));
      });
    }

    //3. Remove fully absorbed metro shells ONLY when a persistent municipal city_proper datapoint exists
    if (this.remove_absorbed_metros) {
      for (let i = 0; i < metros.length; i++) {
        let m = metros[i];
        let rem_years = Object.keys(m.population || {}).filter(function (arg0_y) {
          return Number(m.population[arg0_y]) > 0;
        });
        if (rem_years.length === 0 && metro_has_persistent_core.has(m.key)) {
          delete stadester_obj[m.key];
          stats.absorbed_metros_removed++;
        }
      }
    }

    //Return statement
    return { stadester_obj: stadester_obj, stats: stats };
  }

  /**
   * Resolves a constituent settlement's population at year `arg1_year` (with optional trailing carry).
   *
   * @param {Object} arg0_city
   * @param {number} arg1_year
   *
   * @returns {number}
   */
  resolveConstituentPopAtYear (arg0_city, arg1_year) {
    //Convert from parameters
    let city = arg0_city;
    let yr = Number(arg1_year);
    let yr_str = String(yr);

    //Guard clauses
    if (!city || !city.population || typeof city.population !== "object") return 0;

    //Function body
    let direct = Number(city.population[yr_str]);
    if (Number.isFinite(direct) && direct > 0) return direct;

    if (this.use_trailing_carry && Number.isFinite(city._raw_max_year) &&
        yr > city._raw_max_year && (yr - city._raw_max_year) <= 30) {
      let carried = Number(city.population[String(city._raw_max_year)]);
      if (Number.isFinite(carried) && carried > 0) return carried;
    }

    //Return statement
    return 0;
  }
}

if (typeof global !== "undefined")
  global.StadesterMetroReconciler = StadesterMetroReconciler;
if (typeof module !== "undefined" && module.exports)
  module.exports = { StadesterMetroReconciler: StadesterMetroReconciler };
