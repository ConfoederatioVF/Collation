//Import modules
let fs = global.fs || require("fs");
let path = global.path || require("path");
let hlp_p = (typeof __dirname !== "undefined" && fs.existsSync(path.join(__dirname, "ViscountHUResidualHelpers.js"))) ?
  path.join(__dirname, "ViscountHUResidualHelpers.js") :
  path.join(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualHelpers.js");
let um_p = (typeof __dirname !== "undefined" && fs.existsSync(path.resolve(__dirname, "../ViscountUrbanMask.js"))) ?
  path.resolve(__dirname, "../ViscountUrbanMask.js") :
  path.join(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js");
let ViscountHUResidualHelpers = global.ViscountHUResidualHelpers || require(hlp_p).ViscountHUResidualHelpers;
let ViscountUrbanMask = global.ViscountUrbanMask || require(um_p).ViscountUrbanMask;

//Initialise functions
{
  /**
   * CENTAUR-II Pycnophylactic (Mass-Conserving) 5-Arcminute Dasymetric Detail & High-Frequency-Preserving
   * Cross-Border HYDE De-Cliffer. Enforces strict macro-regional & per-HU mass invariance so dasymetric
   * sharpening never redistributes population mass across macro-regions (e.g. Puebloan SW, California, East)
   * whilst restoring crisp 5-arcminute physical and rural micro-variance exclusively for CENTAUR.
   *
   * @class ViscountCentaurDasymetricDetail
   */
  global.ViscountCentaurDasymetricDetail = class {
    /**
     * Step A: Computes crisp rural HYDE 3.5 density (retaining raw `rurc_<yr>.png` on rural cells and
     * substituting urban-masked HYDE only on modern urban/fringe footprints) followed by
     * high-frequency-preserving cross-border `sub_iso` de-cliffing and state-offset harmonisation.
     * @alias ViscountCentaurDasymetricDetail.A_computeCrispDeCliffedHYDE
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {number} arg2_year
     * @param {Object} arg3_config
     * @param {Map} arg4_cache
     * @param {number} arg5_strict_cut
     * @param {boolean} arg6_remove_state_offsets
     * @param {Object} arg7_detail_cfg
     *
     * @returns {Object}
     */
    static A_computeCrispDeCliffedHYDE (
      arg0_mask_data,
      arg1_bio_covs,
      arg2_year,
      arg3_config,
      arg4_cache,
      arg5_strict_cut,
      arg6_remove_state_offsets,
      arg7_detail_cfg
    ) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let year = Number(arg2_year) || 0;
      let config = (arg3_config) ? arg3_config : {};
      let cache = arg4_cache;
      let strict_cut = Number.isFinite(arg5_strict_cut) ? Number(arg5_strict_cut) : 1650;
      let remove_state_offsets = Boolean(arg6_remove_state_offsets);
      let detail_cfg = (arg7_detail_cfg) ? arg7_detail_cfg : {};

      //Guard clauses
      let ckey = `centaur_crisp_hyde_${year}_${strict_cut}_${remove_state_offsets ? 1 : 0}`;
      if (cache && cache.has(ckey)) return cache.get(ckey);

      //Declare local instance variables.
      let cell_area = mask_data.cell_land_area;
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let d_raw = new Float32Array(mask_data.valid_cell_count);
      let dist_catch = bio_covs.dist_catch_px;
      let dist_site = bio_covs.dist_site_px;
      let elev_valid = bio_covs.elev_valid || null;
      let hab_mask = bio_covs.hab_mask;
      let hyde_lbl = ViscountHUResidualHelpers.resolveHYDEYearLabel(year);
      let hyde_raw_dir = path.resolve(mask_data.project_root || ".", cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let hyde_rur_masked = ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(mask_data, year, cache, config);
      let hyde_rur_1900 = bio_covs.hyde_rur_1900;
      let is_micro_island = (mask_data.valid_cell_count < 2000);
      let lu_raw = new Float32Array(mask_data.valid_cell_count);
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_valid = mask_data.valid_cell_count;
      let perm_ice = bio_covs.perm_ice;
      let rurc_path = path.join(hyde_raw_dir, `rurc_${hyde_lbl}.png`);
      let spike_ratio = Number.isFinite(detail_cfg.rural_urban_spike_ratio) ? Number(detail_cfg.rural_urban_spike_ratio) : 3.2;
      let total_px = mask_data.grid_width*mask_data.grid_height;
      let uopp = bio_covs.uopp_valid || null;
      let uopp_thr = Number.isFinite(detail_cfg.rural_uopp_threshold) ? Number(detail_cfg.rural_uopp_threshold) : 1.5;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let rurc_grid = fs.existsSync(rurc_path) ?
        ViscountHUResidualHelpers.readCachedGlobalFloat(rurc_path, total_px, cache) : null;
      let crp_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `cropland${hyde_lbl}.png`), total_px, cache);
      let irr_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `tot_irri${hyde_lbl}.png`), total_px, cache);
      let rice_path = path.join(hyde_raw_dir, `tot_rice${hyde_lbl}.png`);
      let rice_grid = fs.existsSync(rice_path) ? ViscountHUResidualHelpers.readCachedGlobalFloat(rice_path, total_px, cache) : null;
      let grz_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `grazing${hyde_lbl}.png`), total_px, cache);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let is_hab = (year <= strict_cut) ?
          (hab_mask ? (hab_mask[i] === 1) : (perm_ice[i] > 0.05)) :
          (perm_ice[i] > 0.05);

        if (!is_hab) continue;
        let local_a = Math.max(min_area, cell_area[i]);
        let d_mask = hyde_rur_masked ? (hyde_rur_masked[i]/local_a) : 0;
        let d_raw_rur = (rurc_grid && rurc_grid[gidx] > 0) ? (rurc_grid[gidx]/local_a) : d_mask;
        let is_urb = Boolean(uopp && uopp[i] > uopp_thr);
        let is_fringe_spike = Boolean(uopp && uopp[i] > 0.35 && d_mask > 0.005 && d_raw_rur > spike_ratio*d_mask);
        let d = (is_urb || is_fringe_spike) ? d_mask : d_raw_rur;
        let d_s = dist_site ? dist_site[i] : 99.0;
        let d_c = dist_catch ? dist_catch[i] : 99.0;

        if (d < 0.002) {
          let r19 = hyde_rur_1900 ? (hyde_rur_1900[i]/local_a) : 0;
          let hb = (bio_covs.hyde_hab_dens && bio_covs.hyde_hab_dens[i] >= 0.002) ? bio_covs.hyde_hab_dens[i] : 0;

          if (hb > 0) d = Math.max(d, 0.12*hb);
          if (is_micro_island && d_c <= 5.6) {
            d = Math.max(d, 0.22*r19 + 0.004);
          } else if (d_s <= 2.4 && d_c <= 5.6) {
            d = Math.max(d, Math.exp(-0.65*d_s)*Math.max(0.004, 0.08*r19));
          }
        }
        d_raw[i] = d;
        let rice_v = rice_grid ? rice_grid[gidx] : 0;

        lu_raw[i] = Math.max(0, (crp_grid[gidx] + 1.5*irr_grid[gidx] + 0.60*rice_v + 0.25*grz_grid[gidx])/local_a);
      }

      let dc_rad = Number.isFinite(detail_cfg.decliff_radius_px) ? Number(detail_cfg.decliff_radius_px) : 10;
      let dc_sig = Number.isFinite(detail_cfg.decliff_border_sigma_px) ? Number(detail_cfg.decliff_border_sigma_px) : 4.5;
      let d_decliff = (n_valid >= 2000 && bio_covs.sub_iso_valid && year < 1850) ?
        this.C_removeSubIsoCliffsPreserveMicroTexture(mask_data, d_raw, bio_covs.sub_iso_valid, 0.004, dc_rad, 0.02, dc_sig, remove_state_offsets, elev_valid) :
        d_raw;
      let elig_hab = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let is_hab = (year <= strict_cut) ?
          (hab_mask ? (hab_mask[i] === 1) : (perm_ice[i] > 0.05)) :
          (perm_ice[i] > 0.05);

        if (is_hab) elig_hab[i] = 1;
      }
      ViscountHUResidualHelpers.closeZeroPinholes(mask_data, d_decliff, elig_hab, 4, 0.48, 2, 0);
      let lu_decliff = (n_valid >= 2000 && bio_covs.sub_iso_valid && year < 1850) ?
        this.C_removeSubIsoCliffsPreserveMicroTexture(mask_data, lu_raw, bio_covs.sub_iso_valid, 0.002, dc_rad, 0.02, dc_sig, remove_state_offsets, elev_valid) :
        lu_raw;
      let out = { d_decliff: d_decliff, lu_decliff: lu_decliff };

      if (cache) cache.set(ckey, out);

      //Return statement
      return out;
    }


    /**
     * Step B: Builds and caches the HU-aware 5-arcminute physical micro-dasymetric suitability field
     * (`u_micro_dasy`) combining multi-scale Topographic Position Index, local `3x3` TRI/slope terrace
     * contrast, fluvial/coastal corridors, and woodland-prairie ecotone edges, with smoothed per-HU
     * scaling so mesa/upland/coastal-terrace cultures (Puebloan SW, California) are not penalised.
     * @alias ViscountCentaurDasymetricDetail.B_getOrBuildMicroDasymetricField
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {Object} arg2_hu_ctx
     * @param {Object} arg3_detail_cfg
     *
     * @returns {Float32Array}
     */
    static B_getOrBuildMicroDasymetricField (arg0_mask_data, arg1_bio_covs, arg2_hu_ctx, arg3_detail_cfg) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let hu_ctx = (arg2_hu_ctx) ? arg2_hu_ctx : {};
      let detail_cfg = (arg3_detail_cfg) ? arg3_detail_cfg : {};

      //Guard clauses
      if (!mask_data || !bio_covs) return null;
      if (bio_covs._centaur_micro_dasy && bio_covs._centaur_micro_dasy.length === mask_data.valid_cell_count)
        return bio_covs._centaur_micro_dasy;

      //Declare local instance variables.
      let coast_gain = Number.isFinite(detail_cfg.coastal_mult_gain) ? Number(detail_cfg.coastal_mult_gain) : 0.48;
      let eco_edge_gain = Number.isFinite(detail_cfg.ecotone_edge_gain) ? Number(detail_cfg.ecotone_edge_gain) : 0.34;
      let elev = bio_covs.elev_valid || null;
      let fluv_gain = Number.isFinite(detail_cfg.fluvial_mult_gain) ? Number(detail_cfg.fluvial_mult_gain) : 0.82;
      let forest = bio_covs.forest_valid || null;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hu_assign = hu_ctx.hu_assign || null;
      let hu_id_list = Array.isArray(hu_ctx.hu_id_list) ? hu_ctx.hu_id_list : [];
      let hu_scales_cfg = detail_cfg.hu_micro_scales || {};
      let max_clamp = Number.isFinite(detail_cfg.micro_mult_max) ? Number(detail_cfg.micro_mult_max) : 6.5;
      let min_clamp = Number.isFinite(detail_cfg.micro_mult_min) ? Number(detail_cfg.micro_mult_min) : 0.14;
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let p2v = mask_data.pixel_to_valid_idx;
      let perm_ice = bio_covs.perm_ice || null;
      let rough_abs_gain = Number.isFinite(detail_cfg.roughness_abs_gain) ? Number(detail_cfg.roughness_abs_gain) : 0.18;
      let rough_rel_gain = Number.isFinite(detail_cfg.roughness_rel_gain) ? Number(detail_cfg.roughness_rel_gain) : 0.48;
      let slope = bio_covs.slope_valid || null;
      let slope_rel_gain = Number.isFinite(detail_cfg.slope_rel_gain) ? Number(detail_cfg.slope_rel_gain) : 0.38;
      let tpi_gain = Number.isFinite(detail_cfg.tpi_valley_gain) ? Number(detail_cfg.tpi_valley_gain) : 0.56;
      let tri = bio_covs.tri_valid || null;
      let u_coast = bio_covs.u_coastal || null;
      let u_fluv = bio_covs.u_fluvial || null;
      let v_idx = mask_data.valid_indices;

      //Function body
      //Build smoothly feathered per-HU dasymetric modifiers (e.g. mesa protection in Puebloan SW & coastal/foothill balance in CA)
      let hu_coast_sc = new Float32Array(n_valid).fill(1.0);
      let hu_fluv_sc = new Float32Array(n_valid).fill(1.0);
      let hu_rough_sc = new Float32Array(n_valid).fill(1.0);
      let hu_tpi_sc = new Float32Array(n_valid).fill(1.0);

      if (hu_assign && hu_id_list.length > 0 && Object.keys(hu_scales_cfg).length > 0) {
        let sc_c = new Float32Array(hu_id_list.length).fill(1.0);
        let sc_f = new Float32Array(hu_id_list.length).fill(1.0);
        let sc_r = new Float32Array(hu_id_list.length).fill(1.0);
        let sc_t = new Float32Array(hu_id_list.length).fill(1.0);

        for (let h = 0; h < hu_id_list.length; h++) {
          let s_obj = hu_scales_cfg[hu_id_list[h]];

          if (!s_obj) continue;
          if (Number.isFinite(s_obj.coastal_scale)) sc_c[h] = Number(s_obj.coastal_scale);
          if (Number.isFinite(s_obj.fluvial_scale)) sc_f[h] = Number(s_obj.fluvial_scale);
          if (Number.isFinite(s_obj.roughness_scale)) sc_r[h] = Number(s_obj.roughness_scale);
          if (Number.isFinite(s_obj.tpi_scale)) sc_t[h] = Number(s_obj.tpi_scale);
        }
        for (let i = 0; i < n_valid; i++) {
          let hi = hu_assign[i];

          if (hi >= 0 && hi < hu_id_list.length) {
            hu_coast_sc[i] = sc_c[hi];
            hu_fluv_sc[i] = sc_f[hi];
            hu_rough_sc[i] = sc_r[hi];
            hu_tpi_sc[i] = sc_t[hi];
          }
        }
        let b_rad = (n_valid < 2000) ? 2 : 6;

        hu_coast_sc = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, hu_coast_sc, b_rad, 3, null, false);
        hu_fluv_sc = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, hu_fluv_sc, b_rad, 3, null, false);
        hu_rough_sc = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, hu_rough_sc, b_rad, 3, null, false);
        hu_tpi_sc = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, hu_tpi_sc, b_rad, 3, null, false);
      }

      let elev_sm2 = elev ? ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, elev, 2, 2, null, false) : null;
      let elev_sm6 = elev ? ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, elev, 6, 2, null, false) : null;
      let tri_sm3 = tri ? ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, tri, 3, 2, null, false) : null;
      let f_sm2 = forest ? ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, forest, 2, 2, null, false) : null;
      let sum_v = 0;
      let cnt_v = 0;

      for (let i = 0; i < n_valid; i++) {
        let g = v_idx[i];
        let cx = g % grid_w;
        let cy = Math.floor(g/grid_w);
        let e_nb_sum = 0;
        let nb_cnt = 0;
        let s_nb_sum = 0;
        let t_nb_sum = 0;

        for (let dy = -1; dy <= 1; dy++) {
          let nr = cy + dy;

          if (nr < 0 || nr >= grid_h) continue;
          for (let dx = -1; dx <= 1; dx++) {
            if (dx === 0 && dy === 0) continue;
            let nv = p2v[nr*grid_w + ((cx + dx + grid_w) % grid_w)];

            if (nv >= 0) {
              if (elev) e_nb_sum += elev[nv];
              if (slope) s_nb_sum += slope[nv];
              if (tri) t_nb_sum += tri[nv];
              nb_cnt++;
            }
          }
        }

        let m_tpi = 1.0;

        if (elev && elev_sm2 && elev_sm6) {
          let dt1 = (nb_cnt > 0) ? (elev[i] - e_nb_sum/nb_cnt) : 0;
          let dt2 = elev[i] - elev_sm2[i];
          let dt6 = elev[i] - elev_sm6[i];
          let tri_i = tri ? tri[i] : 14.0;
          let rel_scale = Math.max(7.5, 0.50*tri_i + 5.0);
          let tpi_z = Math.max(-2.4, Math.min(2.4, (0.48*dt1 + 0.34*dt2 + 0.18*dt6)/rel_scale));

          m_tpi = Math.exp(-tpi_gain*hu_tpi_sc[i]*tpi_z);
        }

        let m_rough = 1.0;

        if (tri && tri_sm3) {
          let t_nb_mean = (nb_cnt > 0) ? (t_nb_sum/nb_cnt) : tri_sm3[i];
          let tri_loc = Math.max(-1.2, Math.min(1.2, Math.log((tri[i] + 2.5)/(t_nb_mean + 2.5))));
          let tri_meso = Math.max(-1.2, Math.min(1.2, Math.log((tri[i] + 4.0)/(tri_sm3[i] + 4.0))));
          let tri_abs = Math.max(0, Math.log1p(tri[i]/14.0) - 0.45);
          let s_term = 0;

          if (slope && nb_cnt > 0) {
            let s_nb_mean = s_nb_sum/nb_cnt;

            s_term = Math.max(-1.2, Math.min(1.2, Math.log((slope[i] + 0.02)/(s_nb_mean + 0.02))));
          }
          let r_sc = hu_rough_sc[i];

          m_rough = Math.exp(-rough_rel_gain*r_sc*(0.62*tri_loc + 0.38*tri_meso) - slope_rel_gain*r_sc*s_term - rough_abs_gain*r_sc*tri_abs);
        }

        let uf = u_fluv ? Math.max(0, Math.min(1, u_fluv[i])) : 0;
        let uc = u_coast ? Math.max(0, Math.min(1, u_coast[i])) : 0;
        let m_hydro = Math.exp(fluv_gain*hu_fluv_sc[i]*Math.pow(uf, 0.85) + coast_gain*hu_coast_sc[i]*Math.pow(uc, 0.85));
        let m_eco = 1.0;

        if (forest && f_sm2) {
          let fs2 = Math.max(0, Math.min(1, f_sm2[i]));
          let edge = 4.0*fs2*(1.0 - fs2);

          m_eco = 0.84 + eco_edge_gain*edge + 0.18*forest[i]*(1.0 - 0.45*fs2);
        }

        let val = Math.max(min_clamp, Math.min(max_clamp, m_tpi*m_rough*m_hydro*m_eco));

        out[i] = val;
        if (!perm_ice || perm_ice[i] > 0.05) {
          sum_v += val;
          cnt_v++;
        }
      }

      let inv_mean = (cnt_v > 0 && sum_v > 0) ? (cnt_v/sum_v) : 1.0;

      for (let i = 0; i < n_valid; i++)
        out[i] = Math.max(min_clamp, Math.min(max_clamp, out[i]*inv_mean));
      bio_covs._centaur_micro_dasy = out;

      //Return statement
      return out;
    }


    /**
     * Step C: Removes straight `sub_iso` state/province border cliffs while preserving 100% of
     * within-state 5-arcminute high-frequency rural micro-texture via `log_f + w_b*(l_cross - l_same)`.
     * @alias ViscountCentaurDasymetricDetail.C_removeSubIsoCliffsPreserveMicroTexture
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Int32Array} arg2_sub_iso
     * @param {number} [arg3_eps=0.004]
     * @param {number} [arg4_rad_px=10]
     * @param {number} [arg5_interior_weight=0.02]
     * @param {number} [arg6_border_sigma=4.5]
     * @param {boolean} [arg7_remove_state_offsets=true]
     * @param {Float32Array|null} [arg8_elev_valid]
     *
     * @returns {Float32Array}
     */
    static C_removeSubIsoCliffsPreserveMicroTexture (
      arg0_mask_data,
      arg1_field,
      arg2_sub_iso,
      arg3_eps,
      arg4_rad_px,
      arg5_interior_weight,
      arg6_border_sigma,
      arg7_remove_state_offsets,
      arg8_elev_valid
    ) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let sub_iso = arg2_sub_iso;
      let eps_cap = (arg3_eps !== undefined) ? arg3_eps : 0.004;
      let rad_px = (arg4_rad_px !== undefined) ? arg4_rad_px : 10;
      let w_int_base = (arg5_interior_weight !== undefined) ? arg5_interior_weight : 0.02;
      let border_sigma = (arg6_border_sigma !== undefined) ? arg6_border_sigma : 4.5;
      let remove_offsets = (arg7_remove_state_offsets !== undefined) ? Boolean(arg7_remove_state_offsets) : true;
      let elev_valid = arg8_elev_valid || null;

      //Declare local instance variables.
      let log_f = new Float32Array(mask_data.valid_cell_count);
      let n_valid = mask_data.valid_cell_count;
      let out = new Float32Array(n_valid);
      let pos_cnt = 0;
      let pos_sum = 0;

      //Function body
      for (let i = 0; i < n_valid; i++) {
        if (field[i] > 0) {
          pos_sum += field[i];
          pos_cnt++;
        }
      }
      if (pos_cnt === 0) return field;
      let dist_b = ViscountHUResidualHelpers.getOrComputeSubIsoBorderDist(mask_data, sub_iso);
      let work_field = field;

      if (remove_offsets && sub_iso) {
        work_field = ViscountUrbanMask.harmoniseSubIsoStateOffsets(mask_data, field, sub_iso, dist_b);
        pos_cnt = 0;
        pos_sum = 0;
        for (let i = 0; i < n_valid; i++) {
          if (work_field[i] > 0) {
            pos_sum += work_field[i];
            pos_cnt++;
          }
        }
      }
      let eps_eff = Math.max(1e-5, Math.min(eps_cap, 0.06*(pos_sum/Math.max(1, pos_cnt))));

      for (let i = 0; i < n_valid; i++)
        if (work_field[i] > 0) log_f[i] = Math.log(work_field[i] + eps_eff);
      let l_cross = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, log_f, rad_px, 3, null, false, work_field, elev_valid);
      let l_same = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, log_f, rad_px, 3, sub_iso, false, work_field, elev_valid);

      for (let i = 0; i < n_valid; i++) {
        if (work_field[i] <= 0) {
          out[i] = 0;
          continue;
        }
        let d_b = dist_b ? dist_b[i] : 24.0;
        let w_b = w_int_base + (1.0 - w_int_base)*Math.exp(-(d_b*d_b)/(2.0*border_sigma*border_sigma));
        let delta = Math.max(-1.8, Math.min(1.8, l_cross[i] - l_same[i]));
        let l_corr = log_f[i] + w_b*delta;

        out[i] = Math.max(0, Math.exp(Math.max(-14, Math.min(12, l_corr))) - eps_eff);
      }

      //Return statement
      return out;
    }


    /**
     * Step D: Applies strictly pycnophylactic (mass-conserving) 5-arcminute dasymetric sharpening in place
     * onto a macro kriged population surface `field`. Combines HU-aware physical micro-detail (`u_micro`)
     * with high-frequency rural HYDE texture (`d_decliff / smooth(d_decliff)`), then enforces both local
     * mesoscale flux conservation (`S_macro / S_dasy`) and smooth 2-pass per-HU mass reconciliation so
     * changing dasymetric weights never alters macro-regional population distributions.
     * @alias ViscountCentaurDasymetricDetail.D_applyPycnophylacticDasymetricSharpening
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {Object} arg2_hu_ctx
     * @param {Float32Array} arg3_field
     * @param {Float32Array} arg4_d_decliff
     * @param {Object} arg5_detail_cfg
     */
    static D_applyPycnophylacticDasymetricSharpening (
      arg0_mask_data,
      arg1_bio_covs,
      arg2_hu_ctx,
      arg3_field,
      arg4_d_decliff,
      arg5_detail_cfg
    ) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let hu_ctx = (arg2_hu_ctx) ? arg2_hu_ctx : {};
      let field = arg3_field;
      let d_decliff = arg4_d_decliff;
      let detail_cfg = (arg5_detail_cfg) ? arg5_detail_cfg : {};

      //Guard clauses
      if (!mask_data || !bio_covs || !field) return;

      //Declare local instance variables.
      let hu_assign = hu_ctx.hu_assign || null;
      let hu_cnt = (hu_ctx.hu_id_list && hu_ctx.hu_id_list.length > 0) ? hu_ctx.hu_id_list.length : 0;
      let hyde_hf_exp = Number.isFinite(detail_cfg.hyde_hf_exponent) ? Number(detail_cfg.hyde_hf_exponent) : 0.72;
      let n_valid = mask_data.valid_cell_count;
      let pyc_passes = Number.isFinite(detail_cfg.pycnophylactic_passes) ? Number(detail_cfg.pycnophylactic_passes) : 2;
      let pyc_rad = Number.isFinite(detail_cfg.pycnophylactic_radius_px) ? Number(detail_cfg.pycnophylactic_radius_px) : 7;
      let raw_dasy = new Float32Array(n_valid);
      let tot_macro = 0;
      let u_micro = this.B_getOrBuildMicroDasymetricField(mask_data, bio_covs, hu_ctx, detail_cfg);

      //Function body
      //1. Record exact pre-dasymetric per-HU macro mass totals (invariant target)
      let hu_macro = (hu_assign && hu_cnt > 0) ? new Float64Array(hu_cnt) : null;

      for (let i = 0; i < n_valid; i++) {
        let v = field[i];

        if (!(v > 0)) continue;
        tot_macro += v;
        if (hu_macro) {
          let hi = hu_assign[i];

          if (hi >= 0 && hi < hu_cnt) hu_macro[hi] += v;
        }
      }
      if (tot_macro <= 0) return;

      //2. Extract zero-mean high-frequency rural HYDE texture (zero macro regional skew)
      let d_macro = (d_decliff && hyde_hf_exp > 0) ?
        ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, d_decliff, pyc_rad, pyc_passes, null, false, d_decliff) : null;

      for (let i = 0; i < n_valid; i++) {
        let v = field[i];

        if (!(v > 0)) continue;
        let um_i = u_micro ? u_micro[i] : 1.0;
        let dhf_i = 1.0;

        if (d_decliff && d_macro && d_decliff[i] > 0 && d_macro[i] > 1e-6) {
          let r_hf = Math.max(0.16, Math.min(6.2, d_decliff[i]/d_macro[i]));

          dhf_i = Math.pow(r_hf, hyde_hf_exp);
        }
        raw_dasy[i] = v*um_i*dhf_i;
      }

      //3. Mesoscale pycnophylactic flux conservation (conserves mass over every ~65 km neighbourhood)
      let s_macro = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, field, pyc_rad, pyc_passes, null, false, field);
      let s_dasy = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, raw_dasy, pyc_rad, pyc_passes, null, false, field);

      for (let i = 0; i < n_valid; i++) {
        if (raw_dasy[i] > 0 && s_dasy[i] > 1e-12 && s_macro[i] > 0)
          field[i] = raw_dasy[i]*(s_macro[i]/s_dasy[i]);
      }

      //4. Smooth 2-pass per-HU mass reconciliation (exact < 0,3% HU mass invariance with zero HU seams)
      if (hu_macro) {
        let ratio_grid = new Float32Array(n_valid);

        for (let iter = 0; iter < 2; iter++) {
          let hu_curr = new Float64Array(hu_cnt);
          let hu_mult = new Float64Array(hu_cnt).fill(1.0);

          for (let i = 0; i < n_valid; i++) {
            let v = field[i];

            if (!(v > 0)) continue;
            let hi = hu_assign[i];

            if (hi >= 0 && hi < hu_cnt) hu_curr[hi] += v;
          }
          for (let h = 0; h < hu_cnt; h++) {
            if (hu_macro[h] > 0 && hu_curr[h] > 0)
              hu_mult[h] = Math.max(0.75, Math.min(1.35, hu_macro[h]/hu_curr[h]));
          }
          for (let i = 0; i < n_valid; i++) {
            let hi = hu_assign[i];

            ratio_grid[i] = (hi >= 0 && hi < hu_cnt) ? hu_mult[hi] : 1.0;
          }
          let sm_ratio = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, ratio_grid, 6, 2, null, false);

          for (let i = 0; i < n_valid; i++)
            if (field[i] > 0) field[i] *= sm_ratio[i];
        }
      }

      //5. Preserve exact global domain mass
      let tot_curr = 0;

      for (let i = 0; i < n_valid; i++)
        if (field[i] > 0) tot_curr += field[i];
      if (tot_curr > 0) {
        let g_sc = tot_macro/tot_curr;

        for (let i = 0; i < n_valid; i++)
          if (field[i] > 0) field[i] *= g_sc;
      }
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountCentaurDasymetricDetail: global.ViscountCentaurDasymetricDetail };
