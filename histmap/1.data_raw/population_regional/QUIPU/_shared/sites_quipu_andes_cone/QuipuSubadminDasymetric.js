//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Strictly Mass-Conserving (Pycnophylactic) Historical GIS Sub-Administrative Dasymetric
   * Disaggregation & Areal Scaling Engine for Operation Viscount Project QUIPU.
   *
   * Reads `QUIPU/_shared/subadmin_hgis/rasters/subadmin_id_<yr>.png` (24-bit RGB integer IDs:
   * `(R << 16) | (G << 8) | B`) and `subadmin_meta_<yr>.json`, disaggregates verified colonial
   * and republican sub-administrative enumerations (`1600..2025 AD`) onto the sharpened
   * 5-arcminute Andean/Southern Cone suitability surface `w(x, t)` via Tobler pycnophylactic
   * multiplier relaxation, enforcing exact per-unit mass conservation (`worst_unit_rel_err <= 1e-4`).
   *
   * @class QuipuSubadminDasymetric
   */
  global.QuipuSubadminDasymetric = class {
    /**
     * Applies strictly mass-conserving pycnophylactic sub-administrative dasymetric disaggregation
     * across `1600..2025` onto `2.population_rasters/popc_<yr>.png` and writes
     * `QUIPU/_shared/subadmin_hgis/subadmin_mass_conservation_audit.json`.
     * @alias QuipuSubadminDasymetric.applyAllYears
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
      let hgis_dir = path.join(root_dir, "histmap/1.data_raw/population_regional/QUIPU/_shared/subadmin_hgis");
      let raster_dir = path.join(hgis_dir, "rasters");
      let pop_dir = path.join(mask_data.domain_dir, "2.population_rasters");

      if (!fs.existsSync(raster_dir) || !fs.existsSync(pop_dir)) {
        console.log("[QuipuSubadminDasymetric] No subadmin HGIS rasters directory found; skipping.");
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
        let is_rgb24 = (meta.id_encoding === "rgb24_big_endian");
        let u_list = Array.isArray(meta.units) ? meta.units : [];
        let unit_id = new Int32Array(n_valid);
        let unit_pixels = new Map();
        let units_by_id = new Map();

        for (let i = 0; i < u_list.length; i++)
          units_by_id.set(Number(u_list[i].id), u_list[i]);

        for (let v = 0; v < n_valid; v++) {
          let p4 = valid_indices[v]*4;

          if (png.data[p4 + 3] === 0) continue;
          let uid = is_rgb24 ?
            ((png.data[p4] << 16) | (png.data[p4 + 1] << 8) | png.data[p4 + 2]) :
            ((png.data[p4] << 8) | png.data[p4 + 1]);

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

        if (snap_cache.size >= 3) {
          let first_k = snap_cache.keys().next().value;

          snap_cache.delete(first_k);
        }
        snap_cache.set(arg0_snap_yr, obj);
        return obj;
      };

      //Precompute 4-connected valid neighbours for 1-px pycnophylactic multiplier relaxation
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let n_up = new Int32Array(n_valid).fill(-1);

      for (let v = 0; v < n_valid; v++) {
        let gidx = valid_indices[v];
        let c = gidx % grid_w;
        let r = Math.floor(gidx/grid_w);

        if (r > 0) n_up[v] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[v] = p2v[(r + 1)*grid_w + c];
        n_left[v] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[v] = p2v[r*grid_w + ((c + 1) % grid_w)];
      }

      let pop_files = fs.readdirSync(pop_dir)
        .filter(function (arg0_f) { return /^popc_-?\d+\.png$/.test(arg0_f); })
        .sort();

      for (let f = 0; f < pop_files.length; f++) {
        let m_yr = pop_files[f].match(/^popc_(-?\d+)\.png$/);

        if (!m_yr) continue;
        let yr = parseInt(m_yr[1], 10);

        //For pre-1600 benchmark years (-10000..1500), apply strictly mass-conserving thresholded
        //cliff-wall softening to eliminate HYDE 3.5 synthetic meridian walls (e.g. -70.12W Atacama)
        //while preserving 100% of normal fluvial/topographic sharpness & exact domain mass.
        if (yr < 1600) {
          let pre_path = path.join(pop_dir, pop_files[f]);
          let pre_png = PNG.sync.read(fs.readFileSync(pre_path));
          let pre_dv = new DataView(pre_png.data.buffer, pre_png.data.byteOffset, pre_png.data.byteLength);
          let pre_pop = new Float32Array(n_valid);
          let pre_mass = 0;

          for (let v = 0; v < n_valid; v++) {
            let pv = this.readPosF32(pre_png.data, pre_dv, valid_indices[v]*4);

            pre_pop[v] = pv;
            pre_mass += pv;
          }
          if (pre_mass > 0) {
            let dom_pxs = [];
            let all_in = new Uint8Array(n_valid);

            for (let v = 0; v < n_valid; v++) {
              if (pre_pop[v] > 0) {
                dom_pxs.push(v);
                all_in[v] = 1;
              }
            }
            let dom_map = new Map([[1, dom_pxs]]);
            let targ_map = new Map([[1, pre_mass]]);

            this.softenExtremeCliffsPycnophylactic(
              pre_pop,
              all_in,
              [1],
              dom_map,
              targ_map,
              { n_down: n_down, n_left: n_left, n_right: n_right, n_up: n_up },
              n_valid,
              yr
            );
            for (let v = 0; v < n_valid; v++) {
              if (pre_pop[v] > 0)
                pre_dv.setFloat32(valid_indices[v]*4, Math.max(1e-5, pre_pop[v]), false);
            }
            fs.writeFileSync(pre_path, PNG.sync.write(pre_png, { colorType: 6, deflateLevel: 6, filterType: 0 }));
          }
          continue;
        }
        let snap_yr = this.resolveSnapshotYear(yr, avail_snaps);
        let snap = loadSnapshot(snap_yr);

        if (!snap) continue;
        let pop_path = path.join(pop_dir, pop_files[f]);
        let png = PNG.sync.read(fs.readFileSync(pop_path));
        let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
        let base_w = new Float32Array(n_valid);

        for (let v = 0; v < n_valid; v++)
          base_w[v] = this.readPosF32(png.data, dv, valid_indices[v]*4);

        //Remove any residual modern sub_iso border step strictly for pre-1945 years before historical scaling
        let sub_iso_v = (surface && surface.bio_covs && surface.bio_covs.sub_iso_valid) ? surface.bio_covs.sub_iso_valid : null;

        if (yr >= 1800 && yr <= 1945 && sub_iso_v) {
          base_w = this.removePre1945ModernBorderSteps(mask_data, base_w, sub_iso_v, {
            n_down: n_down, n_left: n_left, n_right: n_right, n_up: n_up
          });
        }

        //Pre-industrial urban-core guard (prevents modern Lima/Bogotá/Buenos Aires/Santiago cores from absorbing rural mass pre-1850)
        let uopp_v = (surface && surface.bio_covs && surface.bio_covs.uopp_valid) ? surface.bio_covs.uopp_valid : null;

        if (yr <= 1850 && uopp_v) {
          for (let v = 0; v < n_valid; v++) {
            if (uopp_v[v] > 3.8 && base_w[v] > 0) {
              let att = 1.0/(1.0 + 0.055*(uopp_v[v] - 3.8));

              base_w[v] *= Math.max(0.42, att);
            }
          }
        }

        //1. Screen units for genuine direct census enumerations vs fallback/sliver/anomalous single-year drops
        let dup_sig_counts = new Map();
        let unit_active = [];
        let unit_base_sum = new Map();
        let unit_interp_val = new Map();
        let unit_is_trusted_census = new Map();

        snap.unit_pixels.forEach(function (arg0_pxs, arg1_uid) {
          let u_meta = snap.units_by_id.get(arg1_uid);

          if (!u_meta) return;
          let b_sum = 0;

          for (let k = 0; k < arg0_pxs.length; k++)
            b_sum += base_w[arg0_pxs[k]];
          if (!(b_sum > 0)) return;

          unit_base_sum.set(arg1_uid, b_sum);
          unit_active.push(arg1_uid);

          let pts = Array.isArray(u_meta.series) ? u_meta.series : [];
          let is_dc = Boolean(u_meta.is_direct_census);

          if (!is_dc || pts.length === 0) return;
          let y_min = Number(pts[0][0]);
          let y_max = Number(pts[pts.length - 1][0]);

          if (yr < y_min - 25 || yr > y_max + 25) return;
          let t_val = global.QuipuSubadminDasymetric.interpolateSubadminSeries(pts, yr);

          if (!(t_val > 0)) return;
          unit_interp_val.set(arg1_uid, t_val);

          let sig = `${u_meta.country || "X"}|${Math.round(t_val)}`;

          dup_sig_counts.set(sig, (dup_sig_counts.get(sig) || 0) + 1);
        });

        if (unit_active.length === 0) continue;

        let country_base_dc = new Map();
        let country_enum_dc = new Map();

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let b_sum = unit_base_sum.get(uid);
          let t_val = unit_interp_val.get(uid);

          if (!(t_val > 0)) continue;
          let cc = u_meta.country || "QUIPU";
          let sig = `${cc}|${Math.round(t_val)}`;
          let is_dup_national = (t_val > 250000 && (dup_sig_counts.get(sig) || 0) >= 2);
          let ratio = t_val/Math.max(1.0, b_sum);
          let is_extreme_outlier = (ratio > 15.0 || ratio < 0.04);
          let is_tiny_sliver = (u_meta.pixel_count <= 2 && t_val > 250000);

          if (is_dup_national || is_extreme_outlier || is_tiny_sliver) continue;
          unit_is_trusted_census.set(uid, true);
          country_base_dc.set(cc, (country_base_dc.get(cc) || 0) + b_sum);
          country_enum_dc.set(cc, (country_enum_dc.get(cc) || 0) + t_val);
        }

        //Assign exact mass-conserving targets:
        //- Census era (1876+): exact direct sub-administrative census mass for trusted census units
        //- Pre-census colonial/early-republican era (1600..1875): scale trusted sub-admin shares within each country's base_w total
        let use_exact_census = (yr >= 1876);
        let unit_target = new Map();

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let b_sum = unit_base_sum.get(uid);

          if (!unit_is_trusted_census.get(uid)) {
            unit_target.set(uid, b_sum);
            continue;
          }
          let t_raw = unit_interp_val.get(uid);

          if (use_exact_census) {
            unit_target.set(uid, t_raw);
          } else {
            let cc = u_meta.country || "QUIPU";
            let c_base = country_base_dc.get(cc) || b_sum;
            let c_enum = country_enum_dc.get(cc) || t_raw;
            let scaled = t_raw*(c_base/Math.max(1.0, c_enum));
            let clamped = Math.max(b_sum*0.25, Math.min(b_sum*3.8, scaled));

            unit_target.set(uid, clamped);
          }
        }

        //2. Initialise pycnophylactic dasymetric density field inside every sub-administrative unit
        let cur_pop = Float32Array.from(base_w);
        let in_sub = new Uint8Array(n_valid);

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let pxs = snap.unit_pixels.get(uid);
          let sc = unit_target.get(uid)/Math.max(1e-9, unit_base_sum.get(uid));

          for (let k = 0; k < pxs.length; k++) {
            let v = pxs[k];

            if (base_w[v] > 0) {
              cur_pop[v] = base_w[v]*sc;
              in_sub[v] = 1;
            }
          }
        }

        //3. Tobler Pycnophylactic Multiplier Relaxation (3 passes, exact per-unit re-normalisation each pass)
        let log_m = new Float32Array(n_valid);
        let next_m = new Float32Array(n_valid);
        let relax_passes = 3;

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

              if (nv >= 0 && base_w[nv] > 0 && cur_pop[nv] > 0) {
                acc += log_m[nv];
                wsum += 1.0;
              }
            }
            next_m[v] = acc/wsum;
          }
          for (let v = 0; v < n_valid; v++) {
            if (in_sub[v] && base_w[v] > 0)
              cur_pop[v] = base_w[v]*Math.exp(Math.max(-4.0, Math.min(4.0, next_m[v])));
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

        //3b. Strictly pycnophylactic thresholded extreme-cliff limiter (1600..2025)
        this.softenExtremeCliffsPycnophylactic(
          cur_pop,
          in_sub,
          unit_active,
          snap.unit_pixels,
          unit_target,
          { n_down: n_down, n_left: n_left, n_right: n_right, n_up: n_up },
          n_valid,
          yr
        );

        //4. Verify strict mass conservation per unit & per country and write updated float32 GeoPNG
        let c_act = new Map();
        let c_targ = new Map();
        let max_u_err = 0;
        let tot_actual = 0;
        let tot_target = 0;

        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let u_meta = snap.units_by_id.get(uid);
          let cc = u_meta.country || "QUIPU";
          let pxs = snap.unit_pixels.get(uid);
          let targ = unit_target.get(uid);
          let act = 0;

          for (let k = 0; k < pxs.length; k++) act += cur_pop[pxs[k]];
          let rel_err = Math.abs(act - targ)/Math.max(1.0, targ);

          if (rel_err > max_u_err) max_u_err = rel_err;
          tot_target += targ;
          tot_actual += act;
          c_targ.set(cc, (c_targ.get(cc) || 0) + targ);
          c_act.set(cc, (c_act.get(cc) || 0) + act);
        }
        let max_c_err = 0;

        c_targ.forEach(function (arg0_t, arg1_cc) {
          let a = c_act.get(arg1_cc) || 0;
          let ce = Math.abs(a - arg0_t)/Math.max(1.0, arg0_t);

          if (ce > max_c_err) max_c_err = ce;
        });
        if (max_u_err > worst_unit_err) worst_unit_err = max_u_err;
        if (max_c_err > worst_country_err) worst_country_err = max_c_err;

        for (let v = 0; v < n_valid; v++) {
          if (!in_sub[v]) continue;
          let p4 = valid_indices[v]*4;

          if (cur_pop[v] > 0)
            dv.setFloat32(p4, Math.max(1e-5, cur_pop[v]), false);
        }
        fs.writeFileSync(pop_path, PNG.sync.write(png, { colorType: 6, deflateLevel: 6, filterType: 0 }));

        if (yr % 50 === 0 || yr === 1870 || yr === 1890 || yr === 1910 || yr === 1930 || yr === 1960 || yr === 1990 || yr === 2010 || yr === 2020) {
          audit_years[String(yr)] = {
            active_units: unit_active.length,
            direct_census_units_applied: unit_is_trusted_census.size,
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
        mass_conservation_passed: (worst_unit_err < 1e-4 && worst_country_err < 1e-4),
        sample_years: audit_years,
        worst_country_rel_err: Number(worst_country_err.toExponential(3)),
        worst_unit_rel_err: Number(worst_unit_err.toExponential(3)),
        years_scaled: years_scaled
      };
      let audit_p = path.join(hgis_dir, "subadmin_mass_conservation_audit.json");

      fs.writeFileSync(audit_p, JSON.stringify(audit_out, null, 2));

      //Return statement
      return audit_out;
    }


    /**
     * Interpolates a historical sub-administrative enumeration series `[[year, pop], ...]` log-linearly at `yr`.
     * @alias QuipuSubadminDasymetric.interpolateSubadminSeries
     *
     * @param {Array<Array<number>>} arg0_series
     * @param {number} arg1_year
     *
     * @returns {number}
     */
    static interpolateSubadminSeries (arg0_series, arg1_year) {
      //Convert from parameters
      let pts = arg0_series;
      let yr = Number(arg1_year) || 1900;

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

          return (p0 > 0 && p1 > 0) ?
            Math.exp((1 - t)*Math.log(p0) + t*Math.log(p1)) :
            (1 - t)*p0 + t*p1;
        }
      }

      //Return statement
      return 0;
    }


    /**
     * Reads a positive finite Big-Endian float32 value from an RGBA PNG buffer.
     * @alias QuipuSubadminDasymetric.readPosF32
     *
     * @param {Buffer} arg0_data
     * @param {DataView} arg1_dv
     * @param {number} arg2_p4
     *
     * @returns {number}
     */
    static readPosF32 (arg0_data, arg1_dv, arg2_p4) {
      let b0 = arg0_data[arg2_p4];
      let b1 = arg0_data[arg2_p4 + 1];
      let b2 = arg0_data[arg2_p4 + 2];
      let b3 = arg0_data[arg2_p4 + 3];

      if ((b0 | b1 | b2 | b3) === 0) return 0;
      let val = arg1_dv.getFloat32(arg2_p4, false);

      //Return statement
      return (Number.isFinite(val) && val > 0) ? val : 0;
    }


    /**
     * QUIPU-only pre-1945 cross-`sub_iso` de-cliffer removing residual modern national border steps
     * before historical sub-administrative scaling.
     * @alias QuipuSubadminDasymetric.removePre1945ModernBorderSteps
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_base_w
     * @param {Int32Array} arg2_sub_iso
     * @param {Object} arg3_nbrs
     *
     * @returns {Float32Array}
     */
    static removePre1945ModernBorderSteps (arg0_mask_data, arg1_base_w, arg2_sub_iso, arg3_nbrs) {
      //Convert from parameters
      let base_w = arg1_base_w;
      let mask_data = arg0_mask_data;
      let nbrs = arg3_nbrs;
      let sub_iso = arg2_sub_iso;

      //Guard clauses
      if (!mask_data || !base_w || !sub_iso) return base_w;

      //Declare local instance variables
      let n_valid = mask_data.valid_cell_count;
      let dist = new Int16Array(n_valid).fill(99);
      let has_pos = new Uint8Array(n_valid);
      let log_f = new Float32Array(n_valid);
      let queue = [];

      //Function body
      for (let v = 0; v < n_valid; v++) {
        if (base_w[v] > 0) {
          log_f[v] = Math.log(base_w[v] + 0.05);
          has_pos[v] = 1;
        }
      }
      for (let v = 0; v < n_valid; v++) {
        let sv = sub_iso[v];

        if (sv <= 0) continue;
        let ns = [nbrs.n_up[v], nbrs.n_down[v], nbrs.n_left[v], nbrs.n_right[v]];

        for (let d = 0; d < 4; d++) {
          let nv = ns[d];

          if (nv >= 0 && sub_iso[nv] > 0 && sub_iso[nv] !== sv) {
            dist[v] = 0;
            queue.push(v);
            break;
          }
        }
      }
      for (let qh = 0; qh < queue.length; qh++) {
        let curr = queue[qh];
        let cd = dist[curr];

        if (cd >= 12) continue;
        let ns = [nbrs.n_up[curr], nbrs.n_down[curr], nbrs.n_left[curr], nbrs.n_right[curr]];

        for (let d = 0; d < 4; d++) {
          let nv = ns[d];

          if (nv >= 0 && dist[nv] > cd + 1) {
            dist[nv] = cd + 1;
            queue.push(nv);
          }
        }
      }

      let l_cross = Float32Array.from(log_f);
      let l_same = Float32Array.from(log_f);
      let tmp_c = new Float32Array(n_valid);
      let tmp_s = new Float32Array(n_valid);

      for (let pass = 0; pass < 10; pass++) {
        for (let v = 0; v < n_valid; v++) {
          if (!has_pos[v] || dist[v] > 12) {
            tmp_c[v] = l_cross[v];
            tmp_s[v] = l_same[v];
            continue;
          }
          let ac = 2.0*l_cross[v];
          let as = 2.0*l_same[v];
          let ns = [nbrs.n_up[v], nbrs.n_down[v], nbrs.n_left[v], nbrs.n_right[v]];
          let sv = sub_iso[v];
          let wc = 2.0;
          let ws = 2.0;

          for (let d = 0; d < 4; d++) {
            let nv = ns[d];

            if (nv >= 0 && has_pos[nv]) {
              ac += l_cross[nv];
              wc += 1.0;
              if (sub_iso[nv] === sv) {
                as += l_same[nv];
                ws += 1.0;
              }
            }
          }
          tmp_c[v] = ac/wc;
          tmp_s[v] = as/ws;
        }
        l_cross.set(tmp_c);
        l_same.set(tmp_s);
      }

      let out = Float32Array.from(base_w);

      for (let v = 0; v < n_valid; v++) {
        if (!has_pos[v] || dist[v] > 12) continue;
        let delta = Math.max(-1.5, Math.min(1.5, l_cross[v] - l_same[v]));
        let w_b = Math.exp(-(dist[v]*dist[v])/(2.0*4.5*4.5));

        out[v] = Math.max(1e-5, Math.exp(log_f[v] + w_b*delta) - 0.05);
      }

      //Return statement
      return out;
    }


    /**
     * Resolves the exact or nearest historical GIS boundary snapshot for benchmark year `yr`.
     * @alias QuipuSubadminDasymetric.resolveSnapshotYear
     *
     * @param {number} arg0_year
     * @param {Array<number>} arg1_avail_years
     *
     * @returns {number}
     */
    static resolveSnapshotYear (arg0_year, arg1_avail_years) {
      //Convert from parameters
      let avail = (Array.isArray(arg1_avail_years) && arg1_avail_years.length > 0) ? arg1_avail_years : [1600];
      let yr = Number(arg0_year) || 1900;

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


    /**
     * Strictly mass-conserving thresholded nonlinear log-diffusion limiter softening only
     * unphysical extreme single-pixel arid/Andean border cliffs (`|dlog10| > 0.52`), re-normalising
     * every sub-administrative polygon back to its exact target mass on every pass.
     * @alias QuipuSubadminDasymetric.softenExtremeCliffsPycnophylactic
     *
     * @param {Float32Array} arg0_cur_pop
     * @param {Uint8Array} arg1_in_sub
     * @param {Array<number>} arg2_unit_active
     * @param {Map<number, Array<number>>} arg3_unit_pixels
     * @param {Map<number, number>} arg4_unit_target
     * @param {Object} arg5_nbrs
     * @param {number} arg6_n_valid
     * @param {number} arg7_year
     */
    static softenExtremeCliffsPycnophylactic (arg0_cur_pop, arg1_in_sub, arg2_unit_active, arg3_unit_pixels, arg4_unit_target, arg5_nbrs, arg6_n_valid, arg7_year) {
      //Convert from parameters
      let cur_pop = arg0_cur_pop;
      let in_sub = arg1_in_sub;
      let n_valid = arg6_n_valid;
      let nbrs = arg5_nbrs;
      let unit_active = arg2_unit_active;
      let unit_pixels = arg3_unit_pixels;
      let unit_target = arg4_unit_target;
      let yr = Number(arg7_year) || 1900;

      //Declare local instance variables
      let ln10 = Math.LN10;
      let log10_arr = new Float32Array(n_valid);
      let next_log = new Float32Array(n_valid);
      let passes = (yr >= 1950) ? 28 : 22;
      let thresh = 0.48;

      //Function body
      for (let pass = 0; pass < passes; pass++) {
        let changed = 0;

        for (let v = 0; v < n_valid; v++)
          log10_arr[v] = (cur_pop[v] >= 0.05) ? Math.log(cur_pop[v])/ln10 : -99.0;

        for (let v = 0; v < n_valid; v++) {
          let lv = log10_arr[v];

          if (lv < -50.0) {
            next_log[v] = lv;
            continue;
          }
          let flux = 0.0;
          let ns = [nbrs.n_up[v], nbrs.n_down[v], nbrs.n_left[v], nbrs.n_right[v]];

          for (let d = 0; d < 4; d++) {
            let nv = ns[d];

            if (nv < 0) continue;
            let lnv = log10_arr[nv];

            if (lnv < -50.0) continue;
            let diff = lnv - lv;
            let ad = Math.abs(diff);

            if (ad > thresh) {
              let excess = ad - thresh;

              flux += (diff > 0 ? 1.0 : -1.0)*excess*0.21;
              changed++;
            }
          }
          next_log[v] = lv + Math.max(-0.45, Math.min(0.45, flux));
        }

        if (changed === 0) break;
        for (let v = 0; v < n_valid; v++) {
          if (log10_arr[v] >= -50.0 && Math.abs(next_log[v] - log10_arr[v]) > 1e-6)
            cur_pop[v] = Math.max(0.05, Math.pow(10.0, next_log[v]));
        }

        //Exact pycnophylactic mass re-normalisation inside EVERY sub-administrative polygon
        for (let i = 0; i < unit_active.length; i++) {
          let uid = unit_active[i];
          let pxs = unit_pixels.get(uid);
          let s_now = 0;

          for (let k = 0; k < pxs.length; k++) s_now += cur_pop[pxs[k]];
          if (s_now > 0) {
            let corr = unit_target.get(uid)/s_now;

            for (let k = 0; k < pxs.length; k++)
              cur_pop[pxs[k]] *= corr;
          }
        }
      }
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { QuipuSubadminDasymetric: global.QuipuSubadminDasymetric };
