//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Non-blurring 2D Screened-Laplace (Helmholtz) Cross-Frontier Harmoniser for Operation Viscount Project SARAY.
   *
   * Eliminates the Soviet Virgin Lands (Tselina) HYDE 3.5 backprojection plateau and aligns SARAY's northern
   * and western Kazakh steppe substrata seamlessly with canonical POLARIS calibrated frontier densities across
   * all pre-contemporary epochs (`-10000` to `1919 AD`), whilst leaving southern Central Asia (oases, Syr Darya,
   * Ferghana, Mawarannahr, Khwarazm, Kopet Dag, Semirechye and Pamir-Alay) strictly untouched (`u = 0`) and
   * preserving 100% of fine fluvial, lacustrine, topographic and settlement texture without blurring.
   *
   * Logical flow is prefixed with step letters (`A_` through `D_`):
   * - `A_buildHarmoniserContext`: Loads POLARIS and SARAY areal-mask contexts and indexes northern frontier geometry.
   * - `B_solveScreenedLaplaceField`: Solves metric-isotropic `(grad^2 - kappa^2) u = 0` via Red-Black SOR.
   * - `C_harmoniseYearPopulationField`: Fixed-point mass-conserving frontier harmonisation for one benchmark year.
   * - `D_harmoniseAllRasters`: Harmonises all `1.kriged_rasters` and pre-1920 `2.population_rasters` in place.
   *
   * @class SarayPolarisFrontierHarmoniser
   */
  global.SarayPolarisFrontierHarmoniser = class {
    static DEFAULT_BORDER_ARC_SMOOTH_PASSES = 1;
    static DEFAULT_SCREENING_LENGTH_PX = 44.0;
    static DEFAULT_SOUTH_LAT_CUT = 44.5;
    static DEFAULT_TAPER_END_YEAR = 1920;
    static DEFAULT_TAPER_START_YEAR = 1870;

    /**
     * Step A: Loads canonical POLARIS and SARAY areal-mask contexts (read-only) and precomputes
     * SARAY northern frontier boundary pairs, 1D border-arc neighbours and isotropic latitude metric weights.
     * @alias SarayPolarisFrontierHarmoniser.A_buildHarmoniserContext
     *
     * @param {Object} arg0_mask_data
     * @param {Object} [arg1_options]
     *  @param {string} [arg1_options.project_root]
     *  @param {number} [arg1_options.screening_length_px=34.0]
     *  @param {number} [arg1_options.south_lat_cut=44.5]
     *
     * @returns {Object}
     */
    static A_buildHarmoniserContext (arg0_mask_data, arg1_options) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let options = (arg1_options) ? arg1_options : {};

      //Guard clauses
      if (!mask_data || !mask_data.valid_indices) {
        console.error("[SarayPolarisFrontierHarmoniser] Invalid mask_data passed to Step A.");
        return null;
      }

      //Declare local instance variables
      let grid_h = mask_data.grid_height || 2160;
      let grid_w = mask_data.grid_width || 4320;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let root_dir = (options.project_root) ? options.project_root : (mask_data.project_root || path.resolve(__dirname, "../../../../../.."));
      let screening_len_px = Number.isFinite(options.screening_length_px) ? Number(options.screening_length_px) : this.DEFAULT_SCREENING_LENGTH_PX;
      let south_lat_cut = Number.isFinite(options.south_lat_cut) ? Number(options.south_lat_cut) : this.DEFAULT_SOUTH_LAT_CUT;
      let valid_indices = mask_data.valid_indices;

      //Function body
      if (!global.fs) global.fs = fs;
      if (!global.path) global.path = path;
      if (!global.pngjs) global.pngjs = { PNG: PNG };
      if (!global.h1) global.h1 = path.join(root_dir, "histmap/1.data_raw");
      if (!global.h2) global.h2 = path.join(root_dir, "histmap/2.data_cleaning");
      if (!global.h3) global.h3 = path.join(root_dir, "histmap/3.data_transform");

      if (!global.ViscountSubstrataMosaic)
        require(path.join(root_dir, "histmap/3.data_transform/population_Substrata.viscount/ViscountSubstrataMosaic.js"));
      if (!global.population_Substrata_russia)
        require(path.join(root_dir, "histmap/3.data_transform/population_Substrata.russia/population_Substrata_russia.js"));

      let mos = global.ViscountSubstrataMosaic;
      let rus = global.population_Substrata_russia;
      let pol_ctx = rus.A_loadManifestAndMasks({
        config_path: path.join(root_dir, "histmap/1.data_raw/population_regional/POLARIS/russia_areal_masks.json5"),
        project_root: root_dir
      });
      let sar_cfg = JSON5.parse(fs.readFileSync(path.join(root_dir, "histmap/3.data_transform/population_Substrata.viscount/config/saray.json5"), "utf8"));
      let sar_ctx = mos.loadGenericProjectContext(sar_cfg, { project_root: root_dir });

      //Build fast SARAY mask lookup and exclude any overlapping pixels from POLARIS boundary seeds
      let pol_p2v = pol_ctx.pixel_to_valid;
      let sar_mask = mask_data.mask_grid;
      let border_arc_nbrs = new Array(n_valid);
      let border_list = [];
      let inv_cos2 = new Float32Array(n_valid);
      let is_north_border = new Uint8Array(n_valid);
      let lat_arr = new Float32Array(n_valid);
      let pol_nbrs = new Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let lat = 90.0 - (r + 0.5)*180.0/grid_h;
        let cos_lat = Math.max(0.40, Math.cos(lat*Math.PI/180.0));

        lat_arr[i] = lat;
        inv_cos2[i] = 1.0/(cos_lat*cos_lat);

        if (lat < south_lat_cut) continue;
        let touches_pol = false;

        for (let dr = -1; dr <= 1 && !touches_pol; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -1; dc <= 1; dc++) {
            if (dr === 0 && dc === 0) continue;
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;

            if (sar_mask[nidx] === 0 && pol_p2v[nidx] >= 0) {
              touches_pol = true;
              break;
            }
          }
        }
        if (!touches_pol) continue;

        let pn = [];

        for (let dr = -2; dr <= 2; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -2; dc <= 2; dc++) {
            let nc = (c + dc + grid_w) % grid_w;
            let nidx = nr*grid_w + nc;
            let pvi = (sar_mask[nidx] === 0) ? pol_p2v[nidx] : -1;

            if (pvi >= 0) {
              let d2 = dr*dr + (dc*cos_lat)*(dc*cos_lat);
              let wt = Math.exp(-d2/2.5);

              pn.push([pvi, wt]);
            }
          }
        }
        if (pn.length > 0) {
          is_north_border[i] = 1;
          pol_nbrs[i] = pn;
          border_list.push(i);
        }
      }

      for (let i = 0; i < border_list.length; i++) {
        let vi = border_list[i];
        let gidx = valid_indices[vi];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let arc = [];

        for (let dr = -2; dr <= 2; dr++) {
          let nr = r + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -2; dc <= 2; dc++) {
            let nc = (c + dc + grid_w) % grid_w;
            let nv = p2v[nr*grid_w + nc];

            if (nv >= 0 && is_north_border[nv] === 1) {
              let d2 = dr*dr + dc*dc;

              arc.push([nv, Math.exp(-d2/2.5)]);
            }
          }
        }
        border_arc_nbrs[vi] = arc;
      }

      //Precompute 4-connected grid neighbours inside SARAY valid mask for ultra-fast Red-Black SOR
      let n_down = new Int32Array(n_valid).fill(-1);
      let n_left = new Int32Array(n_valid).fill(-1);
      let n_right = new Int32Array(n_valid).fill(-1);
      let n_up = new Int32Array(n_valid).fill(-1);
      let parity = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;

        parity[i] = (r + c) & 1;
        if (r > 0) n_up[i] = p2v[(r - 1)*grid_w + c];
        if (r + 1 < grid_h) n_down[i] = p2v[(r + 1)*grid_w + c];
        n_left[i] = p2v[r*grid_w + ((c + grid_w - 1) % grid_w)];
        n_right[i] = p2v[r*grid_w + ((c + 1) % grid_w)];
      }

      //Return statement
      return {
        border_arc_nbrs: border_arc_nbrs,
        border_list: Int32Array.from(border_list),
        grid_h: grid_h,
        grid_w: grid_w,
        inv_cos2: inv_cos2,
        is_north_border: is_north_border,
        lat_arr: lat_arr,
        mask_data: mask_data,
        mos: mos,
        n_down: n_down,
        n_left: n_left,
        n_right: n_right,
        n_up: n_up,
        n_valid: n_valid,
        parity: parity,
        pol_ctx: pol_ctx,
        pol_nbrs: pol_nbrs,
        root_dir: root_dir,
        rus: rus,
        sar_ctx: sar_ctx,
        screening_len_px: screening_len_px,
        south_lat_cut: south_lat_cut
      };
    }


    /**
     * Step B: Solves the metric-isotropic 2D screened Laplace (Helmholtz) equation `(grad^2 - kappa^2) u = 0`
     * over active steppe pixels (`is_solve === 1`) using Red-Black Successive Over-Relaxation (SOR), enforcing
     * Dirichlet `u = u_dirichlet_n` on the POLARIS border, Dirichlet `u = 0` on the southern oasis boundary,
     * and zero-flux Neumann conditions on external coastline/non-POLARIS edges.
     * @alias SarayPolarisFrontierHarmoniser.B_solveScreenedLaplaceField
     *
     * @param {Object} arg0_ctx
     * @param {Uint8Array} arg1_is_solve
     * @param {Uint8Array} arg2_is_dirichlet_n
     * @param {Float32Array} arg3_u_dirichlet_n
     * @param {Float32Array} [arg4_u_init]
     * @param {Object} [arg5_options]
     *  @param {number} [arg5_options.iterations=180]
     *  @param {number} [arg5_options.omega=1.82]
     *  @param {number} [arg5_options.screening_length_px]
     *
     * @returns {Float32Array}
     */
    static B_solveScreenedLaplaceField (arg0_ctx, arg1_is_solve, arg2_is_dirichlet_n, arg3_u_dirichlet_n, arg4_u_init, arg5_options) {
      //Convert from parameters
      let ctx = arg0_ctx;
      let is_solve = arg1_is_solve;
      let is_dir_n = arg2_is_dirichlet_n;
      let u_dir_n = arg3_u_dirichlet_n;
      let u_init = arg4_u_init;
      let options = (arg5_options) ? arg5_options : {};

      //Declare local instance variables
      let inv_cos2 = ctx.inv_cos2;
      let iters = Number.isFinite(options.iterations) ? Math.max(20, Math.round(options.iterations)) : 180;
      let kappa2 = 1.0/Math.max(16.0, Math.pow(
        Number.isFinite(options.screening_length_px) ? Number(options.screening_length_px) : ctx.screening_len_px,
        2
      ));
      let n_down = ctx.n_down;
      let n_left = ctx.n_left;
      let n_right = ctx.n_right;
      let n_up = ctx.n_up;
      let n_valid = ctx.n_valid;
      let omega = Number.isFinite(options.omega) ? Number(options.omega) : 1.82;
      let parity = ctx.parity;
      let u = u_init ? Float32Array.from(u_init) : new Float32Array(n_valid);

      //Function body
      let black_nodes = [];
      let red_nodes = [];

      for (let i = 0; i < n_valid; i++) {
        if (is_solve[i] === 0) {
          u[i] = 0;
          continue;
        }
        if (is_dir_n[i] === 1) {
          u[i] = u_dir_n[i];
          continue;
        }
        if (parity[i] === 0) red_nodes.push(i);
        else black_nodes.push(i);
      }

      let sweepGroup = function (arg0_nodes) {
        for (let k = 0; k < arg0_nodes.length; k++) {
          let i = arg0_nodes[k];
          let wx = inv_cos2[i];
          let num = 0;
          let den = kappa2;
          let nu = n_up[i];
          let nd = n_down[i];
          let nl = n_left[i];
          let nr = n_right[i];

          if (nu >= 0) { num += u[nu]; den += 1.0; }
          if (nd >= 0) { num += u[nd]; den += 1.0; }
          if (nl >= 0) { num += wx*u[nl]; den += wx; }
          if (nr >= 0) { num += wx*u[nr]; den += wx; }
          let u_gs = num/den;

          u[i] = u[i] + omega*(u_gs - u[i]);
        }
      };

      for (let iter = 0; iter < iters; iter++) {
        sweepGroup(red_nodes);
        sweepGroup(black_nodes);
      }

      //Return statement
      return u;
    }


    /**
     * Step C: Performs fixed-point mass-conserving cross-frontier harmonisation of a single SARAY
     * benchmark year's `2.population_rasters` array against canonical POLARIS calibrated frontier densities.
     * Simulates `ViscountSubstrataMosaic` zone calibration (including internal log-multiplier blurring and
     * interior-pinned conservation) inside the fixed-point loop so the final composited `rasters_2` surface
     * is guaranteed continuous across the Kazakhstan-Russia frontier without blurring fine texture.
     * @alias SarayPolarisFrontierHarmoniser.C_harmoniseYearPopulationField
     *
     * @param {Object} arg0_ctx
     * @param {Float32Array} arg1_base_field
     * @param {number} arg2_year
     * @param {Object} [arg3_options]
     *
     * @returns {Object}
     */
    static C_harmoniseYearPopulationField (arg0_ctx, arg1_base_field, arg2_year, arg3_options) {
      //Convert from parameters
      let ctx = arg0_ctx;
      let base_field = arg1_base_field;
      let yr = Number(arg2_year);
      let options = (arg3_options) ? arg3_options : {};

      //Declare local instance variables
      let n_valid = ctx.n_valid;
      let out_field = Float32Array.from(base_field);
      let taper_end = Number.isFinite(options.taper_end_year) ? Number(options.taper_end_year) : this.DEFAULT_TAPER_END_YEAR;
      let taper_start = Number.isFinite(options.taper_start_year) ? Number(options.taper_start_year) : this.DEFAULT_TAPER_START_YEAR;
      let w_yr = (yr <= taper_start) ? 1.0 :
        ((yr >= taper_end) ? 0.0 : 0.5*(1.0 + Math.cos(Math.PI*(yr - taper_start)/(taper_end - taper_start))));

      //Guard clauses
      if (w_yr <= 0.001) {
        return {
          applied: false,
          field: out_field,
          u_field: new Float32Array(n_valid),
          w_yr: 0
        };
      }

      //Function body
      //1. Evaluate canonical POLARIS calibrated density for year `yr` (read-only, raster-only urban load to avoid 2.6GB JSON churn)
      let pol_ctx = ctx.pol_ctx;
      let rus = ctx.rus;
      let pol_urban = this.loadUrbanRasterOnlyForContext(pol_ctx, ctx.root_dir, yr, ctx.mos);
      let pol_mosaic = rus.B_mosaicKrigedSubstrataForYear(pol_ctx, yr, pol_urban);
      let pol_cal_obj = rus.C_computeCalibratedFieldForYear(pol_ctx, pol_mosaic, yr, pol_urban);
      let pol_cal = pol_cal_obj.calibrated_rural;
      let pol_comb = new Float32Array(pol_ctx.n_valid);

      for (let i = 0; i < pol_ctx.n_valid; i++) {
        let rv = (pol_cal[i] > 0) ? pol_cal[i] : 0;

        pol_comb[i] = (yr <= 0) ? Math.max(rv, pol_urban[i]) : rv;
      }

      //2. Resolve SARAY active zones, urban settlements and border-touching northern steppe zones for year `yr`
      let mos = ctx.mos;
      let sar_ctx = ctx.sar_ctx;
      let sar_urban = this.loadUrbanRasterOnlyForContext(ctx.sar_ctx, ctx.root_dir, yr, mos);
      let zone_info = this.resolveActiveSarayZones(ctx, yr, sar_urban);
      let active_zone_of_v = zone_info.active_zone_of_v;
      let border_zone_set = zone_info.border_zone_set;
      let zones = zone_info.zones;
      let is_solve = new Uint8Array(n_valid);
      let lat_arr = ctx.lat_arr;
      let south_cut = ctx.south_lat_cut;

      for (let i = 0; i < n_valid; i++) {
        let zid = active_zone_of_v[i];

        if (zid >= 0 && border_zone_set.has(zid) && lat_arr[i] > south_cut)
          is_solve[i] = 1;
      }

      //3. Build POLARIS boundary target log-densities on positive SARAY northern border pixels
      let border_list = ctx.border_list;
      let is_dir_n = new Uint8Array(n_valid);
      let log_p_target = new Float32Array(n_valid);
      let pol_nbrs = ctx.pol_nbrs;
      let active_border = [];

      for (let k = 0; k < border_list.length; k++) {
        let vi = border_list[k];

        if (is_solve[vi] === 0 || base_field[vi] <= 0) continue;
        let pn = pol_nbrs[vi];
        let l_sum = 0;
        let w_sum = 0;

        for (let m = 0; m < pn.length; m++) {
          let pv = pol_comb[pn[m][0]];

          if (pv > 1e-4) {
            l_sum += pn[m][1]*Math.log(pv);
            w_sum += pn[m][1];
          }
        }
        if (w_sum > 0) {
          is_dir_n[vi] = 1;
          log_p_target[vi] = l_sum/w_sum;
          active_border.push(vi);
        }
      }

      if (active_border.length < 20) {
        return {
          applied: false,
          field: out_field,
          u_field: new Float32Array(n_valid),
          w_yr: w_yr
        };
      }

      //4. Fixed-point iteration matching exact post-calibration ViscountSubstrataMosaic frontier values
      let arc_nbrs = ctx.border_arc_nbrs;
      let blur_passes = (sar_ctx.manifest && sar_ctx.manifest.smoothing && Number.isFinite(sar_ctx.manifest.smoothing.interior_multiplier_blur_passes)) ?
        Math.max(3, sar_ctx.manifest.smoothing.interior_multiplier_blur_passes) : 4;
      let blur_r = (sar_ctx.manifest && sar_ctx.manifest.smoothing && Number.isFinite(sar_ctx.manifest.smoothing.interior_multiplier_blur_radius_px)) ?
        sar_ctx.manifest.smoothing.interior_multiplier_blur_radius_px : 10;
      let n_fp = Number.isFinite(options.fixed_point_iters) ? Number(options.fixed_point_iters) : 6;
      let orig_zone_sum = new Float64Array(zones.length);
      let u = new Float32Array(n_valid);
      let u_b = new Float32Array(n_valid);
      let u_b_sm = new Float32Array(n_valid);
      let w_int = mos.computeZoneInteriorWeights(sar_ctx, active_zone_of_v);

      for (let i = 0; i < n_valid; i++) {
        let zid = active_zone_of_v[i];

        if (zid >= 0 && border_zone_set.has(zid) && base_field[i] > 0)
          orig_zone_sum[zid] += base_field[i];
      }

      let applyModulatedPreservingZoneMass = function (arg0_u_arr) {
        let res_f = new Float32Array(n_valid);
        let new_zone_sum = new Float64Array(zones.length);

        for (let i = 0; i < n_valid; i++) {
          if (base_field[i] <= 0) continue;
          let v = (is_solve[i] === 1) ? Math.max(1e-5, base_field[i]*Math.exp(arg0_u_arr[i])) : base_field[i];

          res_f[i] = v;
          let zid = active_zone_of_v[i];

          if (zid >= 0 && border_zone_set.has(zid)) new_zone_sum[zid] += v;
        }
        for (let i = 0; i < n_valid; i++) {
          let zid = active_zone_of_v[i];

          if (zid >= 0 && border_zone_set.has(zid) && res_f[i] > 0 && new_zone_sum[zid] > 0 && orig_zone_sum[zid] > 0)
            res_f[i] *= orig_zone_sum[zid]/new_zone_sum[zid];
        }
        return res_f;
      };

      for (let fp = 0; fp < n_fp; fp++) {
        let trial_base = applyModulatedPreservingZoneMass(u);

        //Simulate exact ViscountSubstrataMosaic calibration pipeline for this year
        let sim_cal = this.simulateSarayMosaicCalibration(sar_ctx, trial_base, sar_urban, zones, active_zone_of_v, w_int, blur_r, blur_passes);
        let step_gain = (fp < 2) ? 0.80 : 0.72;

        for (let k = 0; k < active_border.length; k++) {
          let vi = active_border[k];
          let s_val = sim_cal[vi];

          if (s_val <= 1e-5) continue;
          let err = w_yr*(log_p_target[vi] - Math.log(s_val));
          let cand = u_b[vi] + step_gain*err;

          u_b[vi] = Math.max(-3.6, Math.min(2.6, cand));
        }

        //1 gentle 1D border-arc smoothing pass removes 1-px raster staircasing while preserving river corridors
        for (let k = 0; k < active_border.length; k++) {
          let vi = active_border[k];
          let arc = arc_nbrs[vi];
          let acc = 0;
          let wsum = 0;

          for (let m = 0; m < arc.length; m++) {
            let nv = arc[m][0];

            if (is_dir_n[nv] === 1) {
              acc += arc[m][1]*u_b[nv];
              wsum += arc[m][1];
            }
          }
          u_b_sm[vi] = (wsum > 0) ? (acc/wsum) : u_b[vi];
        }

        u = this.B_solveScreenedLaplaceField(ctx, is_solve, is_dir_n, u_b_sm, u, {
          iterations: (fp === 0) ? 200 : 110,
          screening_length_px: options.screening_length_px
        });
      }

      //5. Compute final harmonised field (preserving steppe-zone mass in 2.population_rasters) & diagnostics
      out_field = applyModulatedPreservingZoneMass(u);

      let final_sim = this.simulateSarayMosaicCalibration(sar_ctx, out_field, sar_urban, zones, active_zone_of_v, w_int, blur_r, blur_passes);
      let abs_diffs = [];
      let signed_diffs = [];

      for (let k = 0; k < active_border.length; k++) {
        let vi = active_border[k];

        if (final_sim[vi] > 1e-5) {
          let d = (Math.log(final_sim[vi]) - log_p_target[vi])/Math.LN10;

          signed_diffs.push(d);
          abs_diffs.push(Math.abs(d));
        }
      }
      abs_diffs.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      signed_diffs.sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });
      let med_abs = abs_diffs[Math.floor(0.50*abs_diffs.length)] || 0;
      let p90_abs = abs_diffs[Math.floor(0.90*abs_diffs.length)] || 0;
      let med_signed = signed_diffs[Math.floor(0.50*signed_diffs.length)] || 0;

      //Return statement
      return {
        applied: true,
        border_count: active_border.length,
        field: out_field,
        med_abs_log10: Number(med_abs.toFixed(4)),
        med_signed_log10: Number(med_signed.toFixed(4)),
        p90_abs_log10: Number(p90_abs.toFixed(4)),
        u_field: u,
        w_yr: Number(w_yr.toFixed(3))
      };
    }


    /**
     * Step D: Harmonises all pre-1920 `2.population_rasters/popc_<yr>.png` files in place and transfers the
     * epoch-matched non-blurring northern steppe log-modulation onto `1.kriged_rasters/*.png` (updating
     * `surface.fields` before `F_exportBenchmarkRastersAndDiagnostics` if called pre-export, or rewriting
     * the GeoPNGs cleanly).
     * @alias SarayPolarisFrontierHarmoniser.D_harmoniseAllRasters
     *
     * @param {Object} arg0_surface_bundle
     * @param {Object} [arg1_options]
     *
     * @returns {Object}
     */
    static D_harmoniseAllRasters (arg0_surface_bundle, arg1_options) {
      //Convert from parameters
      let surface = arg0_surface_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let bundle = surface.kriging_bundle;
      let cfg = bundle.config;
      let domain_dir = bundle.mask_data.domain_dir;
      let hyde_years = (options.only_years && Array.isArray(options.only_years)) ?
        options.only_years : (cfg.kriging_config.all_hyde_years || []);
      let mask_data = bundle.mask_data;
      let out_pop_dir = path.join(domain_dir, cfg.output_population_rasters_subfolder || "2.population_rasters");
      let t0 = Date.now();
      let u_by_year = new Map();
      let year_diagnostics = {};

      //Function body
      let { ViscountHUResidualHelpers } = global.ViscountHUResidualHelpers ?
        global : require(path.join(mask_data.project_root, "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualHelpers.js"));
      let ctx = this.A_buildHarmoniserContext(mask_data, options);
      let mos = ctx.mos;

      for (let i = 0; i < hyde_years.length; i++) {
        let yr = Number(hyde_years[i]);

        if (yr >= (options.taper_end_year || this.DEFAULT_TAPER_END_YEAR)) continue;
        let pop_path = path.join(out_pop_dir, `popc_${yr}.png`);

        if (!fs.existsSync(pop_path)) continue;
        let base_field = this.readValidFloat32Raster(mask_data, pop_path, mos);
        let res = this.C_harmoniseYearPopulationField(ctx, base_field, yr, options);

        if (res.applied) {
          ViscountHUResidualHelpers.writeFloat32GeoPNG(mask_data, res.field, pop_path);
          u_by_year.set(yr, res.u_field);
          year_diagnostics[yr] = {
            med_abs_log10: res.med_abs_log10,
            med_signed_log10: res.med_signed_log10,
            p90_abs_log10: res.p90_abs_log10,
            w_yr: res.w_yr
          };
        }
      }

      //Transfer converged epoch-matched northern-steppe log-modulation to `surface.fields` (`1.kriged_rasters`)
      let avail_yrs = Array.from(u_by_year.keys()).sort(function (arg0_a, arg1_b) { return arg0_a - arg1_b; });

      if (avail_yrs.length > 0 && surface.fields && Array.isArray(cfg.periods)) {
        for (let i = 0; i < cfg.periods.length; i++) {
          let p_cfg = cfg.periods[i];
          let pkey = p_cfg.key;
          let f_arr = surface.fields[pkey];

          if (!f_arr) continue;
          let rep_yr = Number(p_cfg.representative_year || 0);
          let best_yr = avail_yrs[0];
          let best_d = Math.abs(avail_yrs[0] - rep_yr);

          for (let x = 1; x < avail_yrs.length; x++) {
            let d = Math.abs(avail_yrs[x] - rep_yr);

            if (d < best_d) {
              best_d = d;
              best_yr = avail_yrs[x];
            }
          }
          let u_p = u_by_year.get(best_yr);

          if (!u_p) continue;
          //Apply smooth multiplicative modulation strictly where u_p !== 0 (northern steppe only; Southern SARAY 100% untouched)
          for (let x = 0; x < f_arr.length; x++) {
            if (f_arr[x] > 0 && u_p[x] !== 0)
              f_arr[x] = f_arr[x]*Math.exp(u_p[x]);
          }
        }
      }

      //Return statement
      return {
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        harmonised_years: Object.keys(year_diagnostics).length,
        year_diagnostics: year_diagnostics
      };
    }


    /**
     * Loads urban settlements from PNG rasters (`stadester_base` / `stadester_urban` / `c14bazAAR`)
     * onto any project context's valid indices without triggering multi-gigabyte global shard JSON parses.
     * @alias SarayPolarisFrontierHarmoniser.loadUrbanRasterOnlyForContext
     *
     * @param {Object} arg0_proj_ctx
     * @param {string} arg1_root_dir
     * @param {number} arg2_year
     * @param {Object} arg3_mos
     *
     * @returns {Float32Array}
     */
    static loadUrbanRasterOnlyForContext (arg0_proj_ctx, arg1_root_dir, arg2_year, arg3_mos) {
      //Convert from parameters
      let proj_ctx = arg0_proj_ctx;
      let root_dir = arg1_root_dir;
      let yr = Number(arg2_year);
      let mos = arg3_mos;

      //Declare local instance variables
      let base_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_base_rasters", `stadester_base_${yr}.png`);
      let n_valid = proj_ctx.n_valid;
      let u_arr = new Float32Array(n_valid);
      let urb_path = path.join(root_dir, "histmap/2.data_cleaning/population_Stadester/stadester_urban_rasters", `stadester_urban_${yr}.png`);
      let read_p = fs.existsSync(base_path) ? base_path : urb_path;
      let valid_indices = proj_ctx.valid_indices;

      //Function body
      if (fs.existsSync(read_p)) {
        let u_png = PNG.sync.read(fs.readFileSync(read_p));
        let u_dv = new DataView(u_png.data.buffer, u_png.data.byteOffset, u_png.data.byteLength);

        for (let i = 0; i < n_valid; i++) {
          let v = mos.readPositiveFloat32(u_png.data, u_dv, valid_indices[i]*4);

          if (v >= 0.01) u_arr[i] = v;
        }
      }
      if (yr <= 0) {
        let c14_p = path.join(root_dir, "histmap/2.data_cleaning/population_c14bazAAR/3.rasters_urban", `urbc_${yr}.png`);

        if (fs.existsSync(c14_p)) {
          let c_png = PNG.sync.read(fs.readFileSync(c14_p));
          let c_dv = new DataView(c_png.data.buffer, c_png.data.byteOffset, c_png.data.byteLength);

          for (let i = 0; i < n_valid; i++) {
            let v = mos.readPositiveFloat32(c_png.data, c_dv, valid_indices[i]*4);

            if (v > u_arr[i]) u_arr[i] = v;
          }
        }
      }

      //Return statement
      return u_arr;
    }


    /**
     * Reads a 4320x2160 big-endian float32 GeoPNG onto `mask_data.valid_indices`.
     * @alias SarayPolarisFrontierHarmoniser.readValidFloat32Raster
     *
     * @param {Object} arg0_mask_data
     * @param {string} arg1_png_path
     * @param {Object} arg2_mos
     *
     * @returns {Float32Array}
     */
    static readValidFloat32Raster (arg0_mask_data, arg1_png_path, arg2_mos) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let png_path = arg1_png_path;
      let mos = arg2_mos;

      //Declare local instance variables
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let png = PNG.sync.read(fs.readFileSync(png_path));
      let dv = new DataView(png.data.buffer, png.data.byteOffset, png.data.byteLength);
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++)
        out[i] = mos.readPositiveFloat32(png.data, dv, v_idx[i]*4);

      //Return statement
      return out;
    }


    /**
     * Resolves active SARAY areal-mask zones, rural targets and border-touching steppe zone IDs for year `arg1_year`.
     * @alias SarayPolarisFrontierHarmoniser.resolveActiveSarayZones
     *
     * @param {Object} arg0_ctx
     * @param {number} arg1_year
     * @param {Float32Array} arg2_urban_valid
     *
     * @returns {Object}
     */
    static resolveActiveSarayZones (arg0_ctx, arg1_year, arg2_urban_valid) {
      //Convert from parameters
      let ctx = arg0_ctx;
      let yr = Number(arg1_year);
      let urban_valid = arg2_urban_valid;

      //Declare local instance variables
      let active_zone_of_v = new Int32Array(ctx.n_valid).fill(-1);
      let border_zone_set = new Set();
      let is_north_border = ctx.is_north_border;
      let mos = ctx.mos;
      let p2v = ctx.mask_data.pixel_to_valid_idx;
      let sar_ctx = ctx.sar_ctx;
      let target_groups = [
        sar_ctx.macro_entry ? [sar_ctx.macro_entry] : [],
        sar_ctx.specialist_entries || [],
        sar_ctx.national_epoch_entries || []
      ];
      let zones = [];

      //Function body
      for (let g = 0; g < target_groups.length; g++) {
        let group = target_groups[g];

        for (let x = 0; x < group.length; x++) {
          let entry = group[x];

          if (entry.domain && (yr < entry.domain[0] || yr > entry.domain[1])) continue;
          let zlist = entry.zones || [];

          for (let z = 0; z < zlist.length; z++) {
            let zone = zlist[z];

            if (!zone.pixels || zone.pixels.length === 0) continue;
            if (zone.domain && (yr < zone.domain[0] || yr > zone.domain[1])) continue;
            let raw_t = mos.resolveZoneTargetPopulation(zone.population, yr);

            if (raw_t < 0) continue;
            let target_pop = raw_t*(zone.domain_fraction !== undefined ? zone.domain_fraction : 1.0);
            let z_id = zones.length;
            let v_pixels = [];
            let settled_sum = 0;
            let b_hits = 0;

            for (let a = 0; a < zone.pixels.length; a++) {
              let vi = p2v[zone.pixels[a]];

              if (vi >= 0) {
                active_zone_of_v[vi] = z_id;
                v_pixels.push(vi);
                if (urban_valid[vi] > 0) settled_sum += urban_valid[vi];
                if (is_north_border[vi] === 1) b_hits++;
              }
            }
            let rural_target_pop = 0;
            let settled_scale = 0;

            if (target_pop > 0) {
              if (settled_sum < 0.90*target_pop) {
                rural_target_pop = target_pop - settled_sum;
                settled_scale = 1.0;
              } else {
                rural_target_pop = 0.10*target_pop;
                settled_scale = 0.90*target_pop/settled_sum;
              }
            }
            zones.push({
              border_hits: b_hits,
              key: zone.key,
              rural_target_pop: rural_target_pop,
              settled_scale: settled_scale,
              target_pop: target_pop,
              v_pixels: Int32Array.from(v_pixels)
            });
            if (b_hits >= 50) border_zone_set.add(z_id);
          }
        }
      }

      //Return statement
      return {
        active_zone_of_v: active_zone_of_v,
        border_zone_set: border_zone_set,
        zones: zones
      };
    }


    /**
     * Exact fast mirror of `ViscountSubstrataMosaic.calibrateAndCompositeGenericProject` per-year calibration
     * (zone scaling + 4-pass separable tent smoothing of `log_mult` + interior-pinned conservation + urban add).
     * @alias SarayPolarisFrontierHarmoniser.simulateSarayMosaicCalibration
     *
     * @param {Object} arg0_sar_ctx
     * @param {Float32Array} arg1_base_rural
     * @param {Float32Array} arg2_urban_valid
     * @param {Array<Object>} arg3_zones
     * @param {Int32Array} arg4_active_zone_of_v
     * @param {Float32Array} arg5_w_int
     * @param {number} arg6_blur_r
     * @param {number} arg7_blur_passes
     *
     * @returns {Float32Array}
     */
    static simulateSarayMosaicCalibration (arg0_sar_ctx, arg1_base_rural, arg2_urban_valid, arg3_zones, arg4_active_zone_of_v, arg5_w_int, arg6_blur_r, arg7_blur_passes) {
      //Convert from parameters
      let sar_ctx = arg0_sar_ctx;
      let base_rural = arg1_base_rural;
      let urban_valid = arg2_urban_valid;
      let zones = arg3_zones;
      let active_zone_of_v = arg4_active_zone_of_v;
      let w_int = arg5_w_int;
      let blur_r = arg6_blur_r;
      let blur_passes = arg7_blur_passes;

      //Declare local instance variables
      let h = sar_ctx.height;
      let log_mult = new Float32Array(sar_ctx.n_valid);
      let n_valid = sar_ctx.n_valid;
      let p2v = sar_ctx.pixel_to_valid;
      let rural_valid = Float32Array.from(base_rural);
      let tmp_mult = new Float32Array(n_valid);
      let touched = new Uint8Array(n_valid);
      let valid_indices = sar_ctx.valid_indices;
      let w = sar_ctx.width;

      //Function body
      for (let z = 0; z < zones.length; z++) {
        let zobj = zones[z];
        let vp = zobj.v_pixels;
        let curr_sum = 0;

        for (let a = 0; a < vp.length; a++) {
          let vi = vp[a];

          if (active_zone_of_v[vi] === z && base_rural[vi] > 0) curr_sum += base_rural[vi];
        }
        if (curr_sum > 0 && zobj.rural_target_pop > 0) {
          let sc = zobj.rural_target_pop/curr_sum;

          for (let a = 0; a < vp.length; a++) {
            let vi = vp[a];

            if (active_zone_of_v[vi] === z && base_rural[vi] > 0) {
              rural_valid[vi] = Math.max(1e-4, base_rural[vi]*sc);
              touched[vi] = 1;
            }
          }
        }
      }

      for (let v = 0; v < n_valid; v++) {
        log_mult[v] = (touched[v] && base_rural[v] > 0) ?
          Math.log(Math.max(1e-6, rural_valid[v])/Math.max(1e-6, base_rural[v])) : 0;
      }

      for (let pass = 0; blur_r > 0 && pass < blur_passes; pass++) {
        for (let v = 0; v < n_valid; v++) {
          if (!touched[v] || base_rural[v] <= 0) { tmp_mult[v] = 0; continue; }
          let px = valid_indices[v];
          let r = Math.floor(px/w);
          let c = px % w;
          let acc = 0;
          let wt_sum = 0;

          for (let dc = -blur_r; dc <= blur_r; dc++) {
            let nc = (c + dc + w) % w;
            let nv = p2v[r*w + nc];

            if (nv >= 0 && touched[nv] && base_rural[nv] > 0) {
              let wt = blur_r + 1 - Math.abs(dc);

              acc += log_mult[nv]*wt;
              wt_sum += wt;
            }
          }
          tmp_mult[v] = (wt_sum > 0) ? (acc/wt_sum) : log_mult[v];
        }
        for (let v = 0; v < n_valid; v++) {
          if (!touched[v] || base_rural[v] <= 0) continue;
          let px = valid_indices[v];
          let r = Math.floor(px/w);
          let c = px % w;
          let acc = 0;
          let wt_sum = 0;

          for (let dr = -blur_r; dr <= blur_r; dr++) {
            let nr = r + dr;

            if (nr < 0 || nr >= h) continue;
            let nv = p2v[nr*w + c];

            if (nv >= 0 && touched[nv] && base_rural[nv] > 0) {
              let wt = blur_r + 1 - Math.abs(dr);

              acc += tmp_mult[nv]*wt;
              wt_sum += wt;
            }
          }
          log_mult[v] = (wt_sum > 0) ? (acc/wt_sum) : tmp_mult[v];
        }
      }

      for (let v = 0; v < n_valid; v++) {
        if (!touched[v] || base_rural[v] <= 0) {
          if (rural_valid[v] <= 0) rural_valid[v] = 0;
          continue;
        }
        rural_valid[v] = Math.max(1e-4, base_rural[v]*Math.exp(log_mult[v]));
      }

      global.ViscountSubstrataMosaic.conserveZoneTargetsInteriorPinned(rural_valid, active_zone_of_v, w_int, zones);

      let comb = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let az = active_zone_of_v[i];
        let u_sc = (az >= 0 && zones[az]) ? zones[az].settled_scale : 1.0;

        comb[i] = (az >= 0 && zones[az].target_pop === 0) ? 0 : (rural_valid[i] + urban_valid[i]*u_sc);
      }

      //Return statement
      return comb;
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { SarayPolarisFrontierHarmoniser: global.SarayPolarisFrontierHarmoniser };
