//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");

//Initialise functions
{
  /**
   * Two-regime Historical County Areal Census (`1700–1870`) & Native-American/Pioneer Bleeding Frontier Engine
   * (`CENTAUR-II`). Restricts enumerated US/Canadian counties (`county_id > 0`) from prehistoric kriging while
   * preserving non-stationary Matérn residual kriging plus valley-channelled pioneer spillover outside settled counties.
   *
   * @class ViscountCountyCensusFrontier
   */
  global.ViscountCountyCensusFrontier = class {
    /**
     * Step A: Loads and caches the nearest decennial historical county GeoPNG (`county_id_<yr>.png`)
     * and metadata JSON (`county_meta_<yr>.json`) projected onto the regional domain mask.
     * @alias ViscountCountyCensusFrontier.A_loadCountySnapshotForYear
     *
     * @param {Object} arg0_mask_data
     * @param {number} arg1_year
     * @param {Object} arg2_ccf_cfg
     * @param {Map} arg3_cache
     *
     * @returns {Object|null}
     */
    static A_loadCountySnapshotForYear (arg0_mask_data, arg1_year, arg2_ccf_cfg, arg3_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let year = Number(arg1_year) || 1700;
      let ccf_cfg = (arg2_ccf_cfg) ? arg2_ccf_cfg : {};
      let cache = arg3_cache;

      //Declare local instance variables.
      let end_yr = Number(ccf_cfg.end_year) || 1870;
      let giant_area_thr = Number(ccf_cfg.giant_frontier_area_km2) || 15000;
      let giant_dens_thr = Number(ccf_cfg.giant_frontier_density_km2) || 2.2;
      let n_valid = mask_data.valid_cell_count;
      let proj_root = mask_data.project_root || ".";
      let rasters_rel = ccf_cfg.rasters_folder || "histmap/1.data_raw/population_regional/CENTAUR/_shared/census_counties/rasters";
      let snap_yr = Math.max(Number(ccf_cfg.start_year) || 1700, Math.min(end_yr, Math.round(year/10)*10));
      let valid_indices = mask_data.valid_indices;

      //Guard clauses
      let ckey = `ccf_snap_${snap_yr}_${n_valid}`;
      if (cache && cache.has(ckey)) return cache.get(ckey);

      let meta_path = path.resolve(proj_root, rasters_rel, `county_meta_${snap_yr}.json`);
      let png_path = path.resolve(proj_root, rasters_rel, `county_id_${snap_yr}.png`);
      if (!fs.existsSync(meta_path) || !fs.existsSync(png_path)) return null;

      //Function body
      let county_id = new Int32Array(n_valid);
      let is_giant = new Uint8Array(n_valid);
      let meta_by_id = new Map();
      let png = PNG.sync.read(fs.readFileSync(png_path));
      let raw_meta = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      let counties_obj = raw_meta.counties || {};
      let c_keys = Object.keys(counties_obj);

      for (let i = 0; i < c_keys.length; i++) {
        let m = counties_obj[c_keys[i]];

        if (!m) continue;
        let area_km2 = Math.max(1, Number(m.area_km2) || 1);
        let c_pop = Math.max(0, Number(m.census_pop) || 0);
        let cid = Number(m.id);
        let dens = c_pop/area_km2;
        let giant_flag = Boolean(m.is_giant_frontier || (area_km2 > giant_area_thr && dens < giant_dens_thr));

        meta_by_id.set(cid, {
          area_km2: area_km2,
          census_pop: c_pop,
          country: m.country || "",
          density_per_km2: dens,
          id: cid,
          is_giant_frontier: giant_flag,
          name: m.name || ""
        });
      }

      for (let i = 0; i < n_valid; i++) {
        let p4 = valid_indices[i]*4;

        if (png.data[p4 + 3] === 0) continue;
        let cid = (png.data[p4] << 8) | png.data[p4 + 1];

        if (cid > 0) {
          let meta = meta_by_id.get(cid);

          county_id[i] = cid;
          if (meta && meta.is_giant_frontier) is_giant[i] = 1;
        }
      }

      let out_obj = {
        county_id: county_id,
        is_giant: is_giant,
        meta_by_id: meta_by_id,
        snap_yr: snap_yr
      };

      if (cache) cache.set(ckey, out_obj);

      //Return statement
      return out_obj;
    }


    /**
     * Step B: Computes un-blurred raw HYDE rural suitability, biophysical valley/coastal weight, and
     * documented-settlement pull & urban subtraction arrays for historical census/frontier synthesis.
     * @alias ViscountCountyCensusFrontier.B_computeUnblurredCountyWeights
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {Object} arg2_hu_ctx
     * @param {number} arg3_year
     * @param {Object} arg4_config
     * @param {Object} arg5_ccf_cfg
     * @param {Map} arg6_cache
     *
     * @returns {Object}
     */
    static B_computeUnblurredCountyWeights (arg0_mask_data, arg1_bio_covs, arg2_hu_ctx, arg3_year, arg4_config, arg5_ccf_cfg, arg6_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let hu_ctx = arg2_hu_ctx;
      let year = Number(arg3_year) || 1700;
      let config = (arg4_config) ? arg4_config : {};
      let ccf_cfg = (arg5_ccf_cfg) ? arg5_ccf_cfg : {};
      let cache = arg6_cache;

      //Declare local instance variables.
      let bio_suit = new Float32Array(mask_data.valid_cell_count);
      let cell_area = mask_data.cell_land_area;
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let helpers = global.ViscountHUResidualHelpers || require("./ViscountHUResidualHelpers.js").ViscountHUResidualHelpers;
      let hyde_lbl = helpers.resolveHYDEYearLabel(year);
      let hyde_raw_dens = new Float32Array(mask_data.valid_cell_count);
      let hyde_raw_dir = path.resolve(mask_data.project_root || ".", cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let perm_ice = (bio_covs && bio_covs.perm_ice) ? bio_covs.perm_ice : null;
      let sett_boost_compact = new Float32Array(n_valid);
      let sett_boost_giant = new Float32Array(n_valid);
      let sett_pop_at_v = new Float32Array(n_valid);
      let settlements = (hu_ctx && Array.isArray(hu_ctx.settlements)) ? hu_ctx.settlements : [];
      let sigma_c = Number(ccf_cfg.settlement_sigma_compact_px) || 2.0;
      let sigma_g = Number(ccf_cfg.settlement_sigma_giant_px) || 4.5;
      let total_px = grid_w*grid_h;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let rur_path = path.join(hyde_raw_dir, `rurc${hyde_lbl}.png`);
      let pop_path = path.join(hyde_raw_dir, `popc${hyde_lbl}.png`);
      let raw_path = fs.existsSync(rur_path) ? rur_path : pop_path;
      let raw_grid = fs.existsSync(raw_path) ? helpers.readCachedGlobalFloat(raw_path, total_px, cache) : null;
      let u_coast = (bio_covs && bio_covs.u_coastal) ? bio_covs.u_coastal : null;
      let u_fluv = (bio_covs && bio_covs.u_fluvial) ? bio_covs.u_fluvial : null;
      let u_maxln = (bio_covs && bio_covs.maxln_valid) ? bio_covs.maxln_valid : null;

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        let gidx = valid_indices[i];
        let la_i = Math.max(min_area, cell_area[i]);
        let r_val = (raw_grid && raw_grid[gidx] > 0) ? raw_grid[gidx] : 0;
        let c_t = u_coast ? u_coast[i] : 0;
        let f_t = u_fluv ? u_fluv[i] : 0;
        let m_t = u_maxln ? u_maxln[i] : 0;

        hyde_raw_dens[i] = r_val/la_i;
        bio_suit[i] = Math.max(0.08, (0.45 + 0.55*f_t)*(0.60 + 0.40*c_t)*(0.50 + 0.50*m_t));
      }

      //Accumulate documented settlements at exact target year
      let inv_2s2_c = 0.5/(sigma_c*sigma_c);
      let inv_2s2_g = 0.5/(sigma_g*sigma_g);
      let rc_win = Math.ceil(2.2*sigma_c);
      let rg_win = Math.ceil(2.4*sigma_g);

      for (let i = 0; i < settlements.length; i++) {
        let s = settlements[i];
        let pts = s.series || [];
        let pop_s = 0;

        for (let k = 0; k < pts.length; k++) {
          if (pts[k][0] === year) {
            pop_s = pts[k][1];
            break;
          }
          if (k + 1 < pts.length && pts[k][0] <= year && year <= pts[k + 1][0]) {
            let span = Math.max(1, pts[k + 1][0] - pts[k][0]);
            let t = (year - pts[k][0])/span;

            pop_s = (1 - t)*pts[k][1] + t*pts[k + 1][1];
            break;
          }
        }
        if (pop_s <= 0) continue;

        let gx = s.gx;
        let gy = s.gy;
        let v_center = (p2v) ? p2v[gy*grid_w + gx] : -1;

        if (v_center < 0 && p2v) {
          for (let rad = 1; rad <= 2 && v_center < 0; rad++) {
            for (let dy = -rad; dy <= rad && v_center < 0; dy++) {
              let nr = gy + dy;

              if (nr < 0 || nr >= grid_h) continue;
              for (let dx = -rad; dx <= rad; dx++) {
                let nv = p2v[nr*grid_w + ((gx + dx + grid_w) % grid_w)];

                if (nv >= 0) {
                  v_center = nv;
                  break;
                }
              }
            }
          }
        }
        if (v_center >= 0) sett_pop_at_v[v_center] += pop_s;

        if (!p2v) continue;
        let cos_l = Math.max(0.20, s.cos_lat || 0.70);
        let dc_max_g = Math.min(18, Math.ceil(rg_win/cos_l));
        let wt_pull = Math.log10(1 + pop_s/250);

        for (let dr = -rg_win; dr <= rg_win; dr++) {
          let nr = gy + dr;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dc = -dc_max_g; dc <= dc_max_g; dc++) {
            let nv = p2v[nr*grid_w + ((gx + dc + grid_w) % grid_w)];

            if (nv < 0) continue;
            let dx_m = dc*cos_l;
            let d2 = dr*dr + dx_m*dx_m;

            if (Math.abs(dr) <= rc_win && Math.abs(dx_m) <= rc_win)
              sett_boost_compact[nv] += wt_pull*Math.exp(-d2*inv_2s2_c);
            sett_boost_giant[nv] += wt_pull*Math.exp(-d2*inv_2s2_g);
          }
        }
      }

      for (let i = 0; i < n_valid; i++) {
        if (sett_boost_compact[i] > 3.0) sett_boost_compact[i] = 3.0;
        if (sett_boost_giant[i] > 5.0) sett_boost_giant[i] = 5.0;
      }

      //Return statement
      return {
        bio_suit: bio_suit,
        hyde_raw_dens: hyde_raw_dens,
        sett_boost_compact: sett_boost_compact,
        sett_boost_giant: sett_boost_giant,
        sett_pop_at_v: sett_pop_at_v
      };
    }


    /**
     * Step C: Synthesises the 5-arcminute population surface combining Regime 1 (sharp enumerated county
     * masks + intra-county HYDE/biophysical/settlement structure) and Regime 2 (Indigenous residual kriging +
     * valley-modulated pioneer bleeding frontier) with anti-cliff 2 px county-seam smoothing.
     * @alias ViscountCountyCensusFrontier.C_evaluateCensusCountyAndFrontierSurface
     *
     * @param {Object} arg0_bundle
     * @param {Object} arg1_bio_covs
     * @param {Object} arg2_hu_ctx
     * @param {Float32Array} arg3_rk_pop
     * @param {number} arg4_year
     * @param {Object} arg5_ccf_cfg
     * @param {Map} arg6_cache
     *
     * @returns {Float32Array}
     */
    static C_evaluateCensusCountyAndFrontierSurface (arg0_bundle, arg1_bio_covs, arg2_hu_ctx, arg3_rk_pop, arg4_year, arg5_ccf_cfg, arg6_cache) {
      //Convert from parameters
      let bundle = arg0_bundle;
      let bio_covs = arg1_bio_covs;
      let hu_ctx = arg2_hu_ctx;
      let rk_pop = arg3_rk_pop;
      let year = Number(arg4_year) || 1700;
      let ccf_cfg = (arg5_ccf_cfg) ? arg5_ccf_cfg : {};
      let cache = arg6_cache;

      //Declare local instance variables.
      let bleed_len = Number(ccf_cfg.frontier_bleed_length_px) || 8.5;
      let cell_area = bundle.mask_data.cell_land_area;
      let compact_exp = Number(ccf_cfg.compact_hyde_exponent) || 0.78;
      let giant_exp = Number(ccf_cfg.giant_hyde_exponent) || 1.15;
      let grid_h = bundle.mask_data.grid_height;
      let grid_w = bundle.mask_data.grid_width;
      let mask_data = bundle.mask_data;
      let min_rural_share = Number(ccf_cfg.min_rural_share_of_county) || 0.08;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let perm_ice = (bio_covs && bio_covs.perm_ice) ? bio_covs.perm_ice : null;
      let pioneer_cap = Number(ccf_cfg.frontier_pioneer_density_cap_km2) || 3.2;
      let seam_passes = Number(ccf_cfg.county_seam_blur_passes) || 2;
      let seam_r = Number(ccf_cfg.county_seam_blur_radius_px) || 2;
      let snap = this.A_loadCountySnapshotForYear(mask_data, year, ccf_cfg, cache);
      let valid_indices = mask_data.valid_indices;

      //Guard clauses
      if (!snap) return (rk_pop) ? rk_pop : new Float32Array(n_valid);

      //Function body
      let wts = this.B_computeUnblurredCountyWeights(mask_data, bio_covs, hu_ctx, year, bundle.config, ccf_cfg, cache);
      let bio_suit = wts.bio_suit;
      let county_id = snap.county_id;
      let hyde_raw_dens = wts.hyde_raw_dens;
      let is_giant = snap.is_giant;
      let meta_by_id = snap.meta_by_id;

      //1. Compute per-county urban subtraction & rural target
      let c_doc_urban = new Map();
      let c_rural_target = new Map();

      for (let i = 0; i < n_valid; i++) {
        let cid = county_id[i];

        if (cid > 0 && wts.sett_pop_at_v[i] > 0)
          c_doc_urban.set(cid, (c_doc_urban.get(cid) || 0) + wts.sett_pop_at_v[i]);
      }

      let meta_iter = meta_by_id.entries();
      for (let step = meta_iter.next(); !step.done; step = meta_iter.next()) {
        let cid = step.value[0];
        let m = step.value[1];
        let doc_u = c_doc_urban.get(cid) || 0;
        let rur_t = Math.max(min_rural_share*m.census_pop, m.census_pop - doc_u);

        c_rural_target.set(cid, rur_t);
      }

      //2. Dial's bucketed Chamfer distance (0.1 px units, up to 28.0 px) from compact settled counties
      let max_t = 280;
      let buckets = [];
      let dist_t = new Int16Array(n_valid).fill(max_t + 1);
      let nearest_edge_dens = new Float32Array(n_valid);

      for (let b = 0; b <= max_t; b++) buckets.push([]);
      for (let i = 0; i < n_valid; i++) {
        let cid = county_id[i];

        if (cid > 0 && !is_giant[i] && (!perm_ice || perm_ice[i] > 0.05)) {
          let m = meta_by_id.get(cid);
          let rur_t = c_rural_target.get(cid) || 0;
          let cdens = m ? Math.max(0.15, Math.min(pioneer_cap, rur_t/Math.max(1, m.area_km2))) : 0.25;

          dist_t[i] = 0;
          nearest_edge_dens[i] = cdens;
          buckets[0].push(i);
        }
      }

      if (p2v) {
        let dr_arr = [-1, -1, -1, 0, 0, 1, 1, 1];
        let dc_arr = [-1, 0, 1, -1, 1, -1, 0, 1];
        let cost_arr = [14, 10, 14, 10, 10, 14, 10, 14];

        for (let b = 0; b <= max_t; b++) {
          let q = buckets[b];

          for (let q_idx = 0; q_idx < q.length; q_idx++) {
            let u = q[q_idx];

            if (dist_t[u] < b) continue;
            let gidx = valid_indices[u];
            let cy = Math.floor(gidx/grid_w);
            let cx = gidx % grid_w;
            let ed_u = nearest_edge_dens[u];

            for (let dir = 0; dir < 8; dir++) {
              let nr = cy + dr_arr[dir];

              if (nr < 0 || nr >= grid_h) continue;
              let nv = p2v[nr*grid_w + ((cx + dc_arr[dir] + grid_w) % grid_w)];

              if (nv < 0 || (perm_ice && perm_ice[nv] <= 0.05)) continue;
              let nd = b + cost_arr[dir];

              if (nd <= max_t && nd < dist_t[nv]) {
                dist_t[nv] = nd;
                nearest_edge_dens[nv] = ed_u;
                buckets[nd].push(nv);
              }
            }
          }
        }
      }

      //3. Compute raw intra-county suitability weights (Regime 1) and conserve per county
      let c_weight_sum = new Map();
      let raw_w = new Float32Array(n_valid);
      let reg1_pop = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let cid = county_id[i];

        if (cid <= 0 || (perm_ice && perm_ice[i] <= 0.05)) continue;
        let m = meta_by_id.get(cid);

        if (!m) continue;
        let rur_t = c_rural_target.get(cid) || 0;
        let c_mean_dens = Math.max(0.01, rur_t/Math.max(1, m.area_km2));
        let h_d = Math.max(0, hyde_raw_dens[i]);
        let w_i = 0;

        if (!is_giant[i]) {
          let h_term = Math.pow(h_d + 0.06*c_mean_dens, compact_exp);

          w_i = cell_area[i]*h_term*(0.55 + 0.45*bio_suit[i])*(1.0 + 1.8*wts.sett_boost_compact[i]);
        } else {
          let d_px = dist_t[i]*0.1;
          let h_term = Math.pow(h_d + 0.004*c_mean_dens, giant_exp);
          let prox_c = 0.65 + 0.35*Math.exp(-d_px/14.0);

          w_i = cell_area[i]*h_term*(0.20 + 0.80*bio_suit[i])*(0.25 + 4.5*wts.sett_boost_giant[i])*prox_c;
        }
        w_i = Math.max(1e-6, w_i);
        raw_w[i] = w_i;
        c_weight_sum.set(cid, (c_weight_sum.get(cid) || 0) + w_i);
      }

      for (let i = 0; i < n_valid; i++) {
        let cid = county_id[i];

        if (cid <= 0 || raw_w[i] <= 0) continue;
        let rur_t = c_rural_target.get(cid) || 0;
        let w_tot = c_weight_sum.get(cid) || 1;

        reg1_pop[i] = rur_t*(raw_w[i]/w_tot);
      }

      //4. Normalise Regime 2 Indigenous residual kriging strictly to unenumerated HYDE rural mass
      let hyde_unenum_sum = 0;
      let rk_unenum_sum = 0;
      let rk_unenum = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        if (county_id[i] === 0) {
          hyde_unenum_sum += hyde_raw_dens[i]*cell_area[i];
          if (rk_pop && rk_pop[i] > 0) rk_unenum_sum += rk_pop[i];
        }
      }

      let rk_sc = (rk_unenum_sum > 0 && hyde_unenum_sum > 0) ?
        Math.min(4.0, Math.max(0.15, hyde_unenum_sum/rk_unenum_sum)) : 1.0;

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        let rv = (rk_pop && rk_pop[i] > 0) ? rk_pop[i]*rk_sc : 0;
        let hd = (bio_covs && bio_covs.hyde_hab_dens) ? bio_covs.hyde_hab_dens[i]*cell_area[i]*0.35 : 0;

        rk_unenum[i] = Math.max(rv, 0.5*hyde_raw_dens[i]*cell_area[i], hd);
      }

      //5. Combine Regime 1 & Regime 2 + Bleeding Frontier spillover plume
      let combine_field = new Float32Array(n_valid);
      let u_fluv = (bio_covs && bio_covs.u_fluvial) ? bio_covs.u_fluvial : null;
      let u_maxln = (bio_covs && bio_covs.maxln_valid) ? bio_covs.maxln_valid : null;

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        let cid = county_id[i];
        let d_px = dist_t[i]*0.1;
        let valley_mod = 0.55 + 0.70*(u_fluv ? u_fluv[i] : 0) + 0.25*(u_maxln ? u_maxln[i] : 0);
        let bleed_d = (d_px > 0 && d_px <= 28.0) ?
          Math.min(pioneer_cap, 0.55*nearest_edge_dens[i]*Math.exp(-d_px/(bleed_len*valley_mod))) : 0;

        if (cid > 0) {
          if (is_giant[i]) {
            combine_field[i] = Math.max(reg1_pop[i], 0.75*rk_unenum[i] + 0.35*bleed_d*cell_area[i]);
          } else {
            combine_field[i] = reg1_pop[i];
          }
        } else {
          let reg2_v = rk_unenum[i] + bleed_d*cell_area[i];
          let cap_v = Math.max(rk_unenum[i], nearest_edge_dens[i]*cell_area[i]);

          combine_field[i] = Math.min(cap_v, reg2_v);
        }
      }

      //6. Micro-seam (2 px) county-multiplier smoothing leaving intra-county HYDE/fluvial detail unblurred
      let baseline_tex = new Float32Array(n_valid);
      let is_border = new Uint8Array(n_valid);
      let log_mult = new Float32Array(n_valid);
      let tmp_mult = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        let la_i = Math.max(1.0, cell_area[i]);
        let tex_d = (0.015 + Math.pow(Math.max(0, hyde_raw_dens[i]), 0.85))*(0.55 + 0.45*bio_suit[i]);

        baseline_tex[i] = tex_d;
        let eff_d = Math.max(1e-5, combine_field[i]/la_i);

        log_mult[i] = Math.log(eff_d/Math.max(1e-5, tex_d));

        if (p2v && county_id[i] > 0) {
          let gidx = valid_indices[i];
          let cy = Math.floor(gidx/grid_w);
          let cx = gidx % grid_w;
          let cid_i = county_id[i];

          for (let dy = -2; dy <= 2 && !is_border[i]; dy++) {
            let nr = cy + dy;

            if (nr < 0 || nr >= grid_h) continue;
            for (let dx = -2; dx <= 2; dx++) {
              let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

              if (nv >= 0 && county_id[nv] !== cid_i) {
                is_border[i] = 1;
                break;
              }
            }
          }
        }
      }

      if (p2v && seam_r > 0 && seam_passes > 0) {
        for (let pass = 0; pass < seam_passes; pass++) {
          for (let i = 0; i < n_valid; i++) {
            if (perm_ice && perm_ice[i] <= 0.05) {
              tmp_mult[i] = log_mult[i];
              continue;
            }
            if (county_id[i] > 0 && !is_giant[i] && !is_border[i]) {
              tmp_mult[i] = log_mult[i];
              continue;
            }
            let gidx = valid_indices[i];
            let cy = Math.floor(gidx/grid_w);
            let cx = gidx % grid_w;
            let acc = 0;
            let wsum = 0;

            for (let dc = -seam_r; dc <= seam_r; dc++) {
              let nv = p2v[cy*grid_w + ((cx + dc + grid_w) % grid_w)];

              if (nv >= 0 && (!perm_ice || perm_ice[nv] > 0.05)) {
                let wt = seam_r + 1 - Math.abs(dc);

                acc += log_mult[nv]*wt;
                wsum += wt;
              }
            }
            tmp_mult[i] = (wsum > 0) ? acc/wsum : log_mult[i];
          }
          for (let i = 0; i < n_valid; i++) {
            if (perm_ice && perm_ice[i] <= 0.05) continue;
            if (county_id[i] > 0 && !is_giant[i] && !is_border[i]) continue;
            let gidx = valid_indices[i];
            let cy = Math.floor(gidx/grid_w);
            let cx = gidx % grid_w;
            let acc = 0;
            let wsum = 0;

            for (let dr = -seam_r; dr <= seam_r; dr++) {
              let nr = cy + dr;

              if (nr < 0 || nr >= grid_h) continue;
              let nv = p2v[nr*grid_w + cx];

              if (nv >= 0 && (!perm_ice || perm_ice[nv] > 0.05)) {
                let wt = seam_r + 1 - Math.abs(dr);

                acc += tmp_mult[nv]*wt;
                wsum += wt;
              }
            }
            if (wsum > 0) log_mult[i] = acc/wsum;
          }
        }
      }

      //7. Reconstruct field & re-conserve compact counties cleanly
      let out_field = new Float32Array(n_valid);
      let c_recons_sum = new Map();

      for (let i = 0; i < n_valid; i++) {
        if (perm_ice && perm_ice[i] <= 0.05) continue;
        let la_i = Math.max(1.0, cell_area[i]);
        let val = la_i*baseline_tex[i]*Math.exp(log_mult[i]);

        out_field[i] = Math.max(1e-5, val);
        let cid = county_id[i];

        if (cid > 0 && !is_giant[i])
          c_recons_sum.set(cid, (c_recons_sum.get(cid) || 0) + out_field[i]);
      }

      for (let i = 0; i < n_valid; i++) {
        let cid = county_id[i];

        if (cid > 0 && !is_giant[i] && out_field[i] > 0) {
          let rur_t = c_rural_target.get(cid) || 0;
          let cur_s = c_recons_sum.get(cid) || 1;
          let sc = rur_t/cur_s;

          out_field[i] *= (is_border[i] ? (0.4 + 0.6*sc) : sc);
        }
      }

      //Return statement
      return out_field;
    }


    /**
     * Step D: Loads the binary county coverage mask (`1` = enumerated US/Canadian county polygon,
     * `0` = unenumerated Indigenous/frontier land) onto `ViscountSubstrataMosaic` valid cells.
     * @alias ViscountCountyCensusFrontier.D_loadMosaicCountyMaskForYear
     *
     * @param {Object} arg0_context
     * @param {number} arg1_year
     * @param {Object} arg2_ccf_cfg
     *
     * @returns {Uint8Array|null}
     */
    static D_loadMosaicCountyMaskForYear (arg0_context, arg1_year, arg2_ccf_cfg) {
      //Convert from parameters
      let context = arg0_context;
      let year = Number(arg1_year) || 1700;
      let ccf_cfg = (arg2_ccf_cfg) ? arg2_ccf_cfg : {};

      //Declare local instance variables.
      let end_yr = Number(ccf_cfg.end_year) || 1870;
      let n_valid = context.n_valid;
      let png_path;
      let rasters_rel = ccf_cfg.rasters_folder || "histmap/1.data_raw/population_regional/CENTAUR/_shared/census_counties/rasters";
      let snap_yr = Math.max(Number(ccf_cfg.start_year) || 1700, Math.min(end_yr, Math.round(year/10)*10));
      let valid_indices = context.valid_indices;

      //Guard clauses
      png_path = path.resolve(context.root_dir || ".", rasters_rel, `county_id_${snap_yr}.png`);
      if (!fs.existsSync(png_path)) return null;

      //Function body
      let county_mask = new Uint8Array(n_valid);
      let png = PNG.sync.read(fs.readFileSync(png_path));

      for (let v = 0; v < n_valid; v++) {
        let p4 = valid_indices[v]*4;

        if (png.data[p4 + 3] > 0 && ((png.data[p4] << 8) | png.data[p4 + 1]) > 0)
          county_mask[v] = 1;
      }

      //Return statement
      return county_mask;
    }


    /**
     * Step E: Calibrates frontier-state/territory zones in `ViscountSubstrataMosaic` without crushing
     * unenumerated Indigenous homelands when federal census targets cover only settled county enclaves.
     * @alias ViscountCountyCensusFrontier.E_calibrateZoneWithCountyFrontier
     *
     * @param {Object} arg0_context
     * @param {Object} arg1_zone
     * @param {Uint8Array} arg2_county_mask
     * @param {Float32Array} arg3_base_rural
     * @param {Float32Array} arg4_urban_valid
     * @param {Float32Array} arg5_rural_valid
     * @param {Uint8Array} arg6_touched
     * @param {Int32Array} arg7_active_zone_of_v
     * @param {number} arg8_z_id
     * @param {number} arg9_target_pop
     * @param {Object} arg10_ccf_cfg
     *
     * @returns {Object}
     */
    static E_calibrateZoneWithCountyFrontier (
      arg0_context,
      arg1_zone,
      arg2_county_mask,
      arg3_base_rural,
      arg4_urban_valid,
      arg5_rural_valid,
      arg6_touched,
      arg7_active_zone_of_v,
      arg8_z_id,
      arg9_target_pop,
      arg10_ccf_cfg
    ) {
      //Convert from parameters
      let context = arg0_context;
      let zone = arg1_zone;
      let county_mask = arg2_county_mask;
      let base_rural = arg3_base_rural;
      let urban_valid = arg4_urban_valid;
      let rural_valid = arg5_rural_valid;
      let touched = arg6_touched;
      let active_zone_of_v = arg7_active_zone_of_v;
      let z_id = arg8_z_id;
      let target_pop = arg9_target_pop;
      let ccf_cfg = (arg10_ccf_cfg) ? arg10_ccf_cfg : {};

      //Guard clauses
      if (!county_mask || target_pop <= 0) return { handled: false };

      //Declare local instance variables.
      let county_px = 0;
      let county_rur_sum = 0;
      let county_urb_sum = 0;
      let p2v = context.pixel_to_valid;
      let share_max = Number(ccf_cfg.frontier_county_share_max) || 0.85;
      let share_min = Number(ccf_cfg.frontier_county_share_min) || 0.005;
      let total_px = 0;
      let unenum_rur_sum = 0;
      let unenum_urb_sum = 0;

      //Function body
      for (let a = 0; a < zone.pixels.length; a++) {
        let v_idx = p2v[zone.pixels[a]];

        if (v_idx < 0) continue;
        total_px++;
        if (county_mask[v_idx] === 1) {
          county_px++;
          if (base_rural[v_idx] > 0) county_rur_sum += base_rural[v_idx];
          if (urban_valid[v_idx] > 0) county_urb_sum += urban_valid[v_idx];
        } else {
          if (base_rural[v_idx] > 0) unenum_rur_sum += base_rural[v_idx];
          if (urban_valid[v_idx] > 0) unenum_urb_sum += urban_valid[v_idx];
        }
      }

      let c_share = (total_px > 0) ? county_px/total_px : 0;

      if (c_share < share_min || c_share >= share_max || county_rur_sum <= 0)
        return { handled: false };

      let county_rur_target = 0;
      let settled_scale = 0;

      if (county_urb_sum < 0.90*target_pop) {
        county_rur_target = target_pop - county_urb_sum;
        settled_scale = 1.0;
      } else {
        county_rur_target = 0.10*target_pop;
        settled_scale = 0.90*target_pop/county_urb_sum;
      }

      let scalar = county_rur_target/county_rur_sum;

      for (let a = 0; a < zone.pixels.length; a++) {
        let v_idx = p2v[zone.pixels[a]];

        if (v_idx < 0) continue;
        active_zone_of_v[v_idx] = z_id;
        if (county_mask[v_idx] === 1) {
          if (base_rural[v_idx] > 0) {
            rural_valid[v_idx] = Math.max(1e-4, base_rural[v_idx]*scalar);
            touched[v_idx] = 1;
          }
        } else {
          if (base_rural[v_idx] > 0) {
            rural_valid[v_idx] = Math.max(1e-4, base_rural[v_idx]);
            touched[v_idx] = 1;
          }
        }
      }

      //Return statement
      return {
        handled: true,
        rural_target_pop: county_rur_target + unenum_rur_sum,
        settled_scale: settled_scale,
        target_pop: target_pop + unenum_rur_sum + unenum_urb_sum*settled_scale
      };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountCountyCensusFrontier: global.ViscountCountyCensusFrontier };
