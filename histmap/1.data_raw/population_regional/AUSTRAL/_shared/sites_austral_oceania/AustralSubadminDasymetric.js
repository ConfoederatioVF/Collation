//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Strictly Mass-Conserving (Pycnophylactic) Historical GIS Sub-Administrative Dasymetric
   * Disaggregation & Gradient-Limited Cliff Regularisation Engine for Operation Viscount Project AUSTRAL.
   *
   * For every enumerated AD HYDE benchmark year (`0..2025`), reads the corresponding historical GIS
   * sub-administrative division GeoPNG (`subadmin_id_<year>.png`, 16-bit ID) and longitudinal
   * enumeration metadata (`subadmin_meta_<year>.json`), disaggregates every enumerated sub-administrative
   * unit onto the sharpened 5-arcminute physical/fluvial/archaeological suitability surface `w(x, t)`
   * via Tobler pycnophylactic multiplier relaxation, and applies a strictly mass-conserving thresholded
   * log-cliff limiter (leaving all physical gradients `|Δlog10| <= 0.56` untouched while eliminating
   * coastal-sliver and GHSL/mountain single-pixel step walls across all 128 HYDE years `-10000..2025`).
   *
   * @class AustralSubadminDasymetric
   */
  global.AustralSubadminDasymetric = class {
    /**
     * Applies strictly mass-conserving pycnophylactic sub-administrative dasymetric disaggregation
     * across all enumerated AD HYDE years (`0..2025`) and cliff-wall regularisation across all 128
     * benchmark rasters (`-10000..2025`), writing `config/subadmin_mass_conservation_audit.json`.
     * @alias AustralSubadminDasymetric.applyAllYears
     *
     * @param {Object} arg0_surface
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static applyAllYears (arg0_surface, arg1_options) {
      //Convert from parameters
      let options = (arg1_options) ? arg1_options : {};
      let surface = arg0_surface;

      //Declare local instance variables
      let mask_data = (surface && surface.kriging_bundle) ? surface.kriging_bundle.mask_data : null;
      let t0 = Date.now();

      //Guard clauses
      if (!mask_data) return { elapsed_seconds: 0, years_scaled: 0 };

      let root_dir = options.project_root || mask_data.project_root || path.resolve(__dirname, "../../../../../..");
      let hgis_dir = path.join(root_dir, "histmap/1.data_raw/population_regional/AUSTRAL/_shared/subadmin_hgis");
      let pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");
      let raster_dir = path.join(hgis_dir, "rasters");

      if (!fs.existsSync(raster_dir) || !fs.existsSync(pop_dir)) {
        console.log("[AustralSubadminDasymetric] No subadmin HGIS rasters directory found; skipping.");
        return { elapsed_seconds: 0, years_scaled: 0 };
      }

      let avail_snaps = [];
      let r_files = fs.readdirSync(raster_dir);

      for (let i = 0; i < r_files.length; i++) {
        let m = r_files[i].match(/^subadmin_id_(\d+)\.png$/);

        if (m) avail_snaps.push(parseInt(m[1], 10));
      }
      avail_snaps.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      if (avail_snaps.length === 0) return { elapsed_seconds: 0, years_scaled: 0 };

      let audit_years = {};
      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let snap_cache = new Map();
      let valid_indices = mask_data.valid_indices;
      let worst_country_err = 0;
      let worst_unit_err = 0;
      let years_scaled = 0;

      //Function body
      let loadSnapshot = function (arg0_snap_yr) {
        if (snap_cache.has(arg0_snap_yr)) return snap_cache.get(arg0_snap_yr);
        let meta_p = path.join(raster_dir, `subadmin_meta_${arg0_snap_yr}.json`);
        let png_p = path.join(raster_dir, `subadmin_id_${arg0_snap_yr}.png`);

        if (!fs.existsSync(png_p) || !fs.existsSync(meta_p)) return null;
        let meta = JSON.parse(fs.readFileSync(meta_p, "utf8"));
        let png = PNG.sync.read(fs.readFileSync(png_p));
        let u_list = Array.isArray(meta.units) ? meta.units : [];
        let unit_id = new Int32Array(n_valid);
        let unit_pixels = new Map();
        let units_by_id = new Map();

        for (let i = 0; i < u_list.length; i++)
          units_by_id.set(Number(u_list[i].id), u_list[i]);

        for (let v = 0; v < n_valid; v++) {
          let p4 = valid_indices[v]*4;

          if (png.data[p4 + 3] === 0) continue;
          let uid = (png.data[p4] << 8) | png.data[p4 + 1];

          if (uid > 0 && units_by_id.has(uid)) {
            unit_id[v] = uid;
            let arr = unit_pixels.get(uid);

            if (!arr) {
              arr = [];
              unit_pixels.set(uid, arr);
            }
            arr.push(v);
          }
        }
        let obj = { meta: meta, unit_id: unit_id, unit_pixels: unit_pixels, units_by_id: units_by_id };

        if (snap_cache.size >= 4) {
          let first_k = snap_cache.keys().next().value;

          snap_cache.delete(first_k);
        }
        snap_cache.set(arg0_snap_yr, obj);
        return obj;
      };

      //Precompute antimeridian-aware 4-connected valid neighbours
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let n_up = new Int32Array(n_valid).fill(-1);

      for (let v = 0; v < n_valid; v++) {
        let gidx = valid_indices[v];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;

        if (r > 0) n_up[v] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[v] = p2v[(r + 1)*grid_w + c];
        n_left[v] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[v] = p2v[r*grid_w + ((c + 1) % grid_w)];
      }
      let nbrs_bundle = { n_down: n_down, n_left: n_left, n_right: n_right, n_up: n_up };

      let pop_files = fs.readdirSync(pop_dir)
        .filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); })
        .sort();
      let uopp_v = (surface && surface.bio_covs && surface.bio_covs.uopp_valid) ? surface.bio_covs.uopp_valid : null;

      for (let f = 0; f < pop_files.length; f++) {
        let m_yr = pop_files[f].match(/^popc_(-?\d+)\.png$/);

        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);
        let pop_path = path.join(pop_dir, pop_files[f]);
        let png = PNG.sync.read(fs.readFileSync(pop_path));
        let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
        let base_w = new Float32Array(n_valid);

        for (let v = 0; v < n_valid; v++)
          base_w[v] = this.readPosF32(png.data, dv, valid_indices[v]*4);

        //BC years: strictly domain-mass-conserving thresholded cliff regularisation only (preserves coastal/fluvial micro-texture)
        if (yr < 0) {
          let bc_sum = 0;

          for (let v = 0; v < n_valid; v++) bc_sum += base_w[v];
          this.regulariseExtremeCliffs(base_w, nbrs_bundle, null, null, null, bc_sum, 8, 0.56);
          for (let v = 0; v < n_valid; v++) {
            let p4 = valid_indices[v]*4;

            if (base_w[v] > 0) dv.setFloat32(p4, Math.max(1e-5, base_w[v]), false);
          }
          fs.writeFileSync(pop_path, PNG.sync.write(png, { colorType: 6, deflateLevel: 6, filterType: 0 }));
          continue;
        }

        let snap_yr = this.resolveSnapshotYear(yr, avail_snaps);
        let snap = loadSnapshot(snap_yr);

        if (!snap) continue;

        //Pre-industrial urban-core guard preventing modern Sydney/Melbourne/Auckland footprints from absorbing rural mass
        if (yr <= 1850 && uopp_v) {
          for (let v = 0; v < n_valid; v++) {
            if (uopp_v[v] > 3.8 && base_w[v] > 0) {
              let att = 1.0/(1.0 + 0.05*(uopp_v[v] - 3.8));

              base_w[v] *= Math.max(0.42, att);
            }
          }
        }

        //1. Assemble exact target populations for every enumerated sub-administrative polygon
        //   (skip Z1_FALLBACK/Z3_CSHAPES/Z4_OHM placeholder sliver polygons so they stay smooth at base_w)
        let unit_active = [];
        let unit_base_sum = new Map();
        let unit_target = new Map();

        snap.unit_pixels.forEach(function (arg0_pxs, arg1_uid) {
          let u_meta = snap.units_by_id.get(arg1_uid);

          if (!u_meta || !arg0_pxs || arg0_pxs.length === 0) return;
          let cc = String(u_meta.country || "");

          if (cc.startsWith("Z")) return;
          let target_raw = (snap_yr === yr && Number.isFinite(Number(u_meta.population_at_year)) && Number(u_meta.population_at_year) > 0) ?
            Number(u_meta.population_at_year) :
            global.AustralSubadminDasymetric.interpolateSubadminSeries(u_meta.series, yr);

          if (!(target_raw > 0)) return;
          let b_sum = 0;

          for (let k = 0; k < arg0_pxs.length; k++)
            b_sum += base_w[arg0_pxs[k]];

          if (!(b_sum > 0)) {
            for (let k = 0; k < arg0_pxs.length; k++) {
              base_w[arg0_pxs[k]] = 1e-4;
              b_sum += 1e-4;
            }
          }
          unit_active.push(arg1_uid);
          unit_base_sum.set(arg1_uid, b_sum);
          unit_target.set(arg1_uid, target_raw);
        });

        if (unit_active.length === 0) continue;

        //2. Initialise pycnophylactic dasymetric density field inside every active sub-administrative unit
        let cur_pop = Float32Array.from(base_w);
        let in_sub = new Uint8Array(n_valid);

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let pxs = snap.unit_pixels.get(uid);
          let sc = unit_target.get(uid)/Math.max(1e-12, unit_base_sum.get(uid));

          for (let k = 0; k < pxs.length; k++) {
            let v = pxs[k];

            if (base_w[v] > 0) {
              cur_pop[v] = base_w[v]*sc;
              in_sub[v] = 1;
            }
          }
        }

        //3. Four-pass Tobler Pycnophylactic Multiplier Relaxation (smooths ONLY log(P/w) across polygon
        //   boundaries, preserving 100% of 5' physical texture, with exact per-unit mass re-normalisation)
        let log_m = new Float32Array(n_valid);
        let next_m = new Float32Array(n_valid);
        let relax_passes = 4;

        for (let pass = 0; pass < relax_passes; pass++) {
          for (let v = 0; v < n_valid; v++) {
            if (base_w[v] > 0 && cur_pop[v] > 0)
              log_m[v] = Math.log(cur_pop[v]/base_w[v]);
            else
              log_m[v] = 0;
          }
          for (let v = 0; v < n_valid; v++) {
            if (!in_sub[v] || base_w[v] <= 0) {
              next_m[v] = log_m[v];
              continue;
            }
            let acc = 2.0*log_m[v];
            let nbrs = [n_up[v], n_down[v], n_left[v], n_right[v]];
            let wsum = 2.0;

            for (let d = 0; d < 4; d++) {
              let nv = nbrs[d];

              if (nv >= 0 && in_sub[nv] && base_w[nv] > 0 && cur_pop[nv] > 0) {
                acc += log_m[nv];
                wsum += 1.0;
              }
            }
            next_m[v] = acc/wsum;
          }
          for (let v = 0; v < n_valid; v++) {
            if (in_sub[v] && base_w[v] > 0)
              cur_pop[v] = base_w[v]*Math.exp(Math.max(-4.5, Math.min(4.5, next_m[v])));
          }
          for (let i = 0; i < unit_active.length; i++) {
            let uid = unit_active[i];
            let pxs = snap.unit_pixels.get(uid);
            let s_now = 0;

            for (let k = 0; k < pxs.length; k++) s_now += cur_pop[pxs[k]];
            if (s_now > 0) {
              let corr = unit_target.get(uid)/s_now;

              for (let k = 0; k < pxs.length; k++)
                cur_pop[pxs[k]] *= corr;
            }
          }
        }

        //4. Strictly mass-conserving thresholded log-cliff limiter (eliminates >3.6x single-pixel
        //   coastal-sliver / GHSL ridge walls while leaving all fine fluvial/topographic texture intact)
        let cliff_passes = (yr >= 1975) ? 14 : 8;

        this.regulariseExtremeCliffs(cur_pop, nbrs_bundle, unit_active, snap.unit_pixels, unit_target, 0, cliff_passes, 0.56);

        //5. Verify strict per-unit & per-country mass conservation and write updated float32 GeoPNG
        let c_act = new Map();
        let c_targ = new Map();
        let max_u_err = 0;
        let tot_actual = 0;
        let tot_target = 0;

        for (let v = 0; v < n_valid; v++) {
          let p4 = valid_indices[v]*4;

          if (cur_pop[v] > 0) {
            let val_f32 = Math.max(1e-5, cur_pop[v]);

            dv.setFloat32(p4, val_f32, false);
            cur_pop[v] = dv.getFloat32(p4, false);
          }
        }

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let cc = u_meta.country || "OC";
          let pxs = snap.unit_pixels.get(uid);
          let targ = unit_target.get(uid);
          let act = 0;

          for (let k = 0; k < pxs.length; k++) act += cur_pop[pxs[k]];
          let rel_err = Math.abs(act - targ)/Math.max(1.0, targ);

          if (rel_err > max_u_err) max_u_err = rel_err;
          tot_actual += act;
          tot_target += targ;
          c_act.set(cc, (c_act.get(cc) || 0) + act);
          c_targ.set(cc, (c_targ.get(cc) || 0) + targ);
        }

        let max_c_err = 0;

        c_targ.forEach(function (arg0_t, arg1_cc) {
          let a = c_act.get(arg1_cc) || 0;
          let ce = Math.abs(a - arg0_t)/Math.max(1.0, arg0_t);

          if (ce > max_c_err) max_c_err = ce;
        });
        if (max_u_err > worst_unit_err) worst_unit_err = max_u_err;
        if (max_c_err > worst_country_err) worst_country_err = max_c_err;

        fs.writeFileSync(pop_path, PNG.sync.write(png, { colorType: 6, deflateLevel: 6, filterType: 0 }));

        if (yr % 100 === 0 || yr === 1780 || yr === 1850 || yr === 1880 || yr === 1910 || yr === 1950 || yr === 1980 || yr === 2020) {
          audit_years[String(yr)] = {
            active_units: unit_active.length,
            max_country_rel_err: Number(max_c_err.toExponential(3)),
            max_unit_rel_err: Number(max_u_err.toExponential(3)),
            snapshot_year: snap_yr,
            total_actual_pop: Math.round(tot_actual),
            total_target_pop: Math.round(tot_target)
          };
        }
        years_scaled++;
      }

      let audit_out = {
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        generated_at_gmt0: new Date().toISOString(),
        mass_conservation_passed: (worst_unit_err <= 1e-4 && worst_country_err <= 1e-4),
        sample_years: audit_years,
        worst_country_rel_err: Number(worst_country_err.toExponential(3)),
        worst_unit_rel_err: Number(worst_unit_err.toExponential(3)),
        years_scaled: years_scaled
      };
      let domain_audit_p = path.join(mask_data.domain_dir, "config/subadmin_mass_conservation_audit.json");
      let hgis_audit_p = path.join(hgis_dir, "subadmin_mass_conservation_audit.json");

      fs.writeFileSync(domain_audit_p, JSON.stringify(audit_out, null, 2));
      fs.writeFileSync(hgis_audit_p, JSON.stringify(audit_out, null, 2));

      //Return statement
      return audit_out;
    }


    /**
     * Interpolates a historical sub-administrative enumeration series `[[year, pop], ...]` log-linearly at `yr`.
     * @alias AustralSubadminDasymetric.interpolateSubadminSeries
     *
     * @param {Array<Array<number>>} arg0_series
     * @param {number} arg1_year
     *
     * @returns {number}
     */
    static interpolateSubadminSeries (arg0_series, arg1_year) {
      //Convert from parameters
      let pts = arg0_series;
      let yr = Number.isFinite(Number(arg1_year)) ? Number(arg1_year) : 1900;

      //Guard clauses
      if (!Array.isArray(pts) || pts.length === 0) return 0;
      if (yr <= pts[0][0]) return Math.max(0, Number(pts[0][1]) || 0);
      if (yr >= pts[pts.length - 1][0]) return Math.max(0, Number(pts[pts.length - 1][1]) || 0);

      //Function body
      for (let i = 0; i < pts.length - 1; i++) {
        let y0 = pts[i][0];
        let y1 = pts[i + 1][0];

        if (yr >= y0 && yr <= y1) {
          let p0 = Math.max(0, Number(pts[i][1]) || 0);
          let p1 = Math.max(0, Number(pts[i + 1][1]) || 0);

          if (y1 === y0) return p0;
          let t = (yr - y0)/(y1 - y0);

          if (p0 > 0 && p1 > 0) return Math.exp((1 - t)*Math.log(p0) + t*Math.log(p1));
          return (1 - t)*p0 + t*p1;
        }
      }

      //Return statement
      return 0;
    }


    /**
     * Reads a positive finite Big-Endian float32 value from an RGBA PNG buffer.
     * @alias AustralSubadminDasymetric.readPosF32
     *
     * @param {Buffer|Uint8Array} arg0_data
     * @param {DataView} arg1_dv
     * @param {number} arg2_p4
     *
     * @returns {number}
     */
    static readPosF32 (arg0_data, arg1_dv, arg2_p4) {
      //Convert from parameters
      let data = arg0_data;
      let dv = arg1_dv;
      let p4 = arg2_p4;

      //Guard clauses
      if ((data[p4] | data[p4 + 1] | data[p4 + 2] | data[p4 + 3]) === 0) return 0;

      //Function body
      let val = dv.getFloat32(p4, false);

      //Return statement
      return (Number.isFinite(val) && val > 0) ? val : 0;
    }


    /**
     * Strictly mass-conserving thresholded log10-cliff limiter: relaxes ONLY adjacent pixel pairs
     * whose `|log10(P_i) - log10(P_j)|` exceeds `threshold_log10` (preserving all fine physical
     * gradients below the threshold), followed by exact pycnophylactic mass re-normalisation on every pass.
     * @alias AustralSubadminDasymetric.regulariseExtremeCliffs
     *
     * @param {Float32Array} arg0_field
     * @param {Object} arg1_nbrs
     * @param {Array<number>|null} arg2_unit_active
     * @param {Map|null} arg3_unit_pixels
     * @param {Map|null} arg4_unit_target
     * @param {number} arg5_domain_target
     * @param {number} arg6_passes
     * @param {number} arg7_threshold_log10
     */
    static regulariseExtremeCliffs (arg0_field, arg1_nbrs, arg2_unit_active, arg3_unit_pixels, arg4_unit_target, arg5_domain_target, arg6_passes, arg7_threshold_log10) {
      //Convert from parameters
      let domain_target = Number(arg5_domain_target) || 0;
      let field = arg0_field;
      let n_down = arg1_nbrs.n_down;
      let n_left = arg1_nbrs.n_left;
      let n_right = arg1_nbrs.n_right;
      let n_up = arg1_nbrs.n_up;
      let passes = Number(arg6_passes) || 6;
      let thr = Number(arg7_threshold_log10) || 0.56;
      let unit_active = arg2_unit_active;
      let unit_pixels = arg3_unit_pixels;
      let unit_target = arg4_unit_target;

      //Declare local instance variables
      let inv_ln10 = 1.0/Math.LN10;
      let n_valid = field.length;
      let log10_f = new Float32Array(n_valid);
      let next_l = new Float32Array(n_valid);

      //Function body
      for (let pass = 0; pass < passes; pass++) {
        for (let v = 0; v < n_valid; v++)
          log10_f[v] = (field[v] >= 0.02) ? (Math.log(field[v])*inv_ln10) : -99.0;

        let any_changed = false;

        for (let v = 0; v < n_valid; v++) {
          let lv = log10_f[v];

          if (lv < -50.0) {
            next_l[v] = lv;
            continue;
          }
          let delta = 0.0;
          let hits = 0;
          let nbrs = [n_up[v], n_down[v], n_left[v], n_right[v]];

          for (let d = 0; d < 4; d++) {
            let nv = nbrs[d];

            if (nv < 0) continue;
            let lnv = log10_f[nv];

            if (lnv < -50.0) continue;
            let diff = lnv - lv;
            let ad = Math.abs(diff);

            if (ad > thr) {
              let excess = ad - thr;

              delta += (diff > 0 ? excess : -excess);
              hits++;
            }
          }
          if (hits > 0) {
            next_l[v] = lv + 0.24*(delta/hits);
            any_changed = true;
          } else {
            next_l[v] = lv;
          }
        }
        if (!any_changed) break;

        for (let v = 0; v < n_valid; v++) {
          if (next_l[v] > -50.0 && next_l[v] !== log10_f[v])
            field[v] = Math.max(1e-5, Math.pow(10.0, next_l[v]));
        }

        //Exact pycnophylactic mass re-normalisation inside EVERY sub-administrative unit (or domain for BC)
        if (unit_active && unit_pixels && unit_target) {
          for (let i = 0; i < unit_active.length; i++) {
            let uid = unit_active[i];
            let pxs = unit_pixels.get(uid);
            let s_now = 0;

            for (let k = 0; k < pxs.length; k++) s_now += field[pxs[k]];
            if (s_now > 0) {
              let corr = unit_target.get(uid)/s_now;

              for (let k = 0; k < pxs.length; k++) field[pxs[k]] *= corr;
            }
          }
        } else if (domain_target > 0) {
          let s_dom = 0;

          for (let v = 0; v < n_valid; v++) s_dom += field[v];
          if (s_dom > 0) {
            let corr = domain_target/s_dom;

            for (let v = 0; v < n_valid; v++) field[v] *= corr;
          }
        }
      }
    }


    /**
     * Resolves the exact or nearest historical GIS boundary snapshot year for benchmark year `yr`.
     * @alias AustralSubadminDasymetric.resolveSnapshotYear
     *
     * @param {number} arg0_year
     * @param {Array<number>} arg1_avail_years
     *
     * @returns {number}
     */
    static resolveSnapshotYear (arg0_year, arg1_avail_years) {
      //Convert from parameters
      let avail = (Array.isArray(arg1_avail_years) && arg1_avail_years.length > 0) ? arg1_avail_years : [1900];
      let yr = Number.isFinite(Number(arg0_year)) ? Number(arg0_year) : 1900;

      //Guard clauses
      if (avail.indexOf(yr) >= 0) return yr;

      //Function body
      let best = avail[0];
      let best_d = Math.abs(yr - best);

      for (let i = 1; i < avail.length; i++) {
        let d = Math.abs(yr - avail[i]);

        if (d < best_d) {
          best_d = d;
          best = avail[i];
        }
      }

      //Return statement
      return best;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { AustralSubadminDasymetric: global.AustralSubadminDasymetric };
