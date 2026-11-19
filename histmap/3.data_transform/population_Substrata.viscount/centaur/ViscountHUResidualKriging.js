//Import modules
let fs = global.fs || require("fs");
let JSON5 = global.JSON5 || require("json5");
let path = global.path || require("path");
let { PNG } = global.pngjs || require("pngjs");
let ccf_p = (typeof __dirname !== "undefined" && fs.existsSync(path.join(__dirname, "ViscountCountyCensusFrontier.js"))) ? path.join(__dirname, "ViscountCountyCensusFrontier.js") : path.join(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountCountyCensusFrontier.js");
let hlp_p = (typeof __dirname !== "undefined" && fs.existsSync(path.join(__dirname, "ViscountHUResidualHelpers.js"))) ? path.join(__dirname, "ViscountHUResidualHelpers.js") : path.join(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualHelpers.js");
let um_p = (typeof __dirname !== "undefined" && fs.existsSync(path.resolve(__dirname, "../ViscountUrbanMask.js"))) ? path.resolve(__dirname, "../ViscountUrbanMask.js") : path.join(process.cwd(), "histmap/3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js");
let ViscountCountyCensusFrontier = global.ViscountCountyCensusFrontier || require(ccf_p).ViscountCountyCensusFrontier;
let ViscountHUResidualHelpers = global.ViscountHUResidualHelpers || require(hlp_p).ViscountHUResidualHelpers;
let ViscountUrbanMask = global.ViscountUrbanMask || require(um_p).ViscountUrbanMask;

//Initialise functions
{
  /**
   * Per-Hydrological-Unit (HU) Declarative Residual Kriging, Cross-Border HYDE De-Cliffing,
   * Documented-Settlement & Dendrochronology Kernel Composer, and Census-to-Satellite Transition Engine
   * for `CENTAUR-II` (`Northern America` & `Hawai'i/American Polynesia`).
   *
   * @class ViscountHUResidualKriging
   */
  global.ViscountHUResidualKriging = class {
    /**
     * Step A: Builds per-pixel smoothed HU admixture arrays (`w_hyde`..`w_coastal`, `t0`, `t1`),
     * documented settlements list, and dendrochronology curves on the domain mask.
     * @alias ViscountHUResidualKriging.A_buildHUAdmixtureAndSettlementContext
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     * @param {Object} arg2_config
     *
     * @returns {Object}
     */
    static A_buildHUAdmixtureAndSettlementContext (arg0_mask_data, arg1_bio_covs, arg2_config) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let config = (arg2_config) ? arg2_config : {};

      //Declare local instance variables
      let adm_cfg_rel = (config.kriging_config && config.kriging_config.hu_admixture_config) ?
        config.kriging_config.hu_admixture_config :
        "histmap/3.data_transform/population_Substrata.viscount/centaur/config/centaur_hu_admixture.json5";
      let adm_cfg_abs = path.resolve(mask_data.project_root || ".", adm_cfg_rel);
      let adm_obj = fs.existsSync(adm_cfg_abs) ? JSON5.parse(fs.readFileSync(adm_cfg_abs, "utf8")) : {};
      let bbox = ViscountHUResidualHelpers.computeMaskBBox(mask_data);
      let def_p = adm_obj.default_admixture || {
        census_taper_end: 1850,
        census_taper_start: 1800,
        w_coastal: 0.08,
        w_dendro: 0.04,
        w_fluvial: 0.10,
        w_hyde: 0.38,
        w_landuse: 0.16,
        w_settlement: 0.24
      };
      let dendro_path = path.join(mask_data.domain_dir || "", "config/dendro_occupation_series.json");
      let dendro_regions = [];
      let h = mask_data.grid_height;
      let hu_assign = new Int16Array(mask_data.valid_cell_count).fill(-1);
      let hu_id_list = ["default"];
      let hu_profiles = adm_obj.hu_profiles || {};
      let manifest_abs = path.resolve(mask_data.project_root || ".", "histmap/1.data_raw/population_regional/CENTAUR/centaur_areal_masks.json5");
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let prof_list = [def_p];
      let sett_path = path.join(mask_data.domain_dir || "", "config/documented_settlements.json");
      let settlements = [];
      let valid_indices = mask_data.valid_indices;
      let w = mask_data.grid_width;

      //Function body
      if (fs.existsSync(manifest_abs)) {
        let man = JSON5.parse(fs.readFileSync(manifest_abs, "utf8"));
        let specs = Array.isArray(man.specialist_masks) ? man.specialist_masks : [];

        for (let i = 0; i < specs.length; i++) {
          let sp = specs[i];
          let m_abs = path.resolve(mask_data.project_root || ".", sp.mask_path || "");

          if (!fs.existsSync(m_abs)) continue;
          let hu_idx = hu_id_list.length;
          let m_png = PNG.sync.read(fs.readFileSync(m_abs));
          let matched_px = 0;

          hu_id_list.push(sp.id);
          prof_list.push(hu_profiles[sp.id] || def_p);
          for (let x = 0; x < n_valid; x++) {
            let gidx = valid_indices[x];
            let p4 = gidx*4;

            if (m_png.data[p4 + 3] > 0 && (m_png.data[p4] | m_png.data[p4 + 1] | m_png.data[p4 + 2]) !== 0) {
              hu_assign[x] = hu_idx;
              matched_px++;
            }
          }
          if (matched_px === 0) {
            hu_id_list.pop();
            prof_list.pop();
          }
        }
      }

      //Fill any coastal/edge valid pixels lacking specialist paint via 8-neighbour multi-source BFS
      let queue = [];
      let step_dirs = [[-1, 0], [1, 0], [0, -1], [0, 1], [-1, -1], [-1, 1], [1, -1], [1, 1]];

      for (let i = 0; i < n_valid; i++)
        if (hu_assign[i] >= 0) queue.push(i);

      for (let q_head = 0; q_head < queue.length; q_head++) {
        let curr = queue[q_head];
        let gidx = valid_indices[curr];
        let r = Math.floor(gidx/w);
        let c = gidx % w;
        let lbl = hu_assign[curr];

        for (let d = 0; d < step_dirs.length; d++) {
          let nr = r + step_dirs[d][0];

          if (nr < 0 || nr >= h) continue;
          let nc = (c + step_dirs[d][1] + w) % w;
          let nv = p2v[nr*w + nc];

          if (nv >= 0 && hu_assign[nv] < 0) {
            hu_assign[nv] = lbl;
            queue.push(nv);
          }
        }
      }

      for (let i = 0; i < n_valid; i++)
        if (hu_assign[i] < 0) hu_assign[i] = 0;

      let w_hyde = new Float32Array(n_valid);
      let w_lu = new Float32Array(n_valid);
      let w_set = new Float32Array(n_valid);
      let w_den = new Float32Array(n_valid);
      let w_fluv = new Float32Array(n_valid);
      let w_coast = new Float32Array(n_valid);
      let t0_arr = new Float32Array(n_valid);
      let t1_arr = new Float32Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let pr = prof_list[hu_assign[i]] || def_p;

        w_hyde[i] = pr.w_hyde;
        w_lu[i] = pr.w_landuse;
        w_set[i] = pr.w_settlement;
        w_den[i] = pr.w_dendro;
        w_fluv[i] = pr.w_fluvial;
        w_coast[i] = pr.w_coastal;
        t0_arr[i] = pr.census_taper_start;
        t1_arr[i] = pr.census_taper_end;
      }

      let b_rad = (n_valid < 2000) ? 2 : 6;

      w_hyde = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_hyde, b_rad, 3, null, false);
      w_lu = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_lu, b_rad, 3, null, false);
      w_set = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_set, b_rad, 3, null, false);
      w_den = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_den, b_rad, 3, null, false);
      w_fluv = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_fluv, b_rad, 3, null, false);
      w_coast = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, w_coast, b_rad, 3, null, false);
      t0_arr = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, t0_arr, b_rad, 3, null, false);
      t1_arr = ViscountHUResidualHelpers.smoothGaussianGrid(mask_data, t1_arr, b_rad, 3, null, false);

      if (fs.existsSync(sett_path)) {
        let raw_s = JSON.parse(fs.readFileSync(sett_path, "utf8"));
        let list = Array.isArray(raw_s.settlements) ? raw_s.settlements : [];

        for (let i = 0; i < list.length; i++) {
          let s = list[i];

          if (s.lon < bbox.min_lon || s.lon > bbox.max_lon || s.lat < bbox.min_lat || s.lat > bbox.max_lat) continue;
          let gx = Math.max(0, Math.min(w - 1, Math.floor((s.lon + 180)*w/360)));
          let gy = Math.max(0, Math.min(h - 1, Math.floor((90 - s.lat)*h/180)));

          settlements.push({
            cos_lat: Math.max(0.18, Math.cos(s.lat*Math.PI/180)),
            gx: gx,
            gy: gy,
            series: s.series || []
          });
        }
      }

      if (fs.existsSync(dendro_path)) {
        let raw_d = JSON.parse(fs.readFileSync(dendro_path, "utf8"));
        let list = Array.isArray(raw_d.regions) ? raw_d.regions : [];

        for (let i = 0; i < list.length; i++) {
          let d = list[i];

          if (d.lon < bbox.min_lon || d.lon > bbox.max_lon || d.lat < bbox.min_lat || d.lat > bbox.max_lat) continue;
          let gx = Math.max(0, Math.min(w - 1, Math.floor((d.lon + 180)*w/360)));
          let gy = Math.max(0, Math.min(h - 1, Math.floor((90 - d.lat)*h/180)));

          dendro_regions.push({
            cos_lat: Math.max(0.20, Math.cos(d.lat*Math.PI/180)),
            gx: gx,
            gy: gy,
            radius_km: Number(d.radius_km) || 55,
            series: d.series || []
          });
        }
      }

      //Return statement
      return {
        county_census_frontier: adm_obj.county_census_frontier || null,
        dendro_regions: dendro_regions,
        settlements: settlements,
        t0_arr: t0_arr,
        t1_arr: t1_arr,
        w_coastal: w_coast,
        w_dendro: w_den,
        w_fluvial: w_fluv,
        w_hyde: w_hyde,
        w_landuse: w_lu,
        w_settlement: w_set
      };
    }


    /**
     * Step B: Computes macro-preserving cross-`sub_iso` de-cliffed urban-masked HYDE 3.5 rural population density
     * and HYDE land-use intensity (`cropland + 1,5*tot_irri + 0,35*grazing`) for year `t`.
     * @alias ViscountHUResidualKriging.B_computeMacroPreservingDeCliffedHYDE
     */
    static B_computeMacroPreservingDeCliffedHYDE (arg0_mask_data, arg1_bio_covs, arg2_year, arg3_config, arg4_cache) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let year = Number(arg2_year) || 0;
      let config = (arg3_config) ? arg3_config : {};
      let cache = arg4_cache;

      //Guard clauses
      let ckey = `hu_hyde_decliff_${year}`;
      if (cache && cache.has(ckey)) return cache.get(ckey);

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let cov_paths = (config.kriging_config && config.kriging_config.covariate_paths) ?
        config.kriging_config.covariate_paths : {};
      let d_raw = new Float32Array(mask_data.valid_cell_count);
      let dist_catch = bio_covs.dist_catch_px;
      let dist_site = bio_covs.dist_site_px;
      let hab_mask = bio_covs.hab_mask;
      let hyde_lbl = ViscountHUResidualHelpers.resolveHYDEYearLabel(year);
      let hyde_raw_dir = path.resolve(mask_data.project_root || ".", cov_paths.hyde_raw_rasters_folder || "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let hyde_rur = ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(mask_data, year, cache, config);
      let hyde_rur_1900 = bio_covs.hyde_rur_1900;
      let is_micro_island = (mask_data.valid_cell_count < 2000);
      let lu_raw = new Float32Array(mask_data.valid_cell_count);
      let min_area = 0.75*mask_data.mean_cell_land_area_km2;
      let n_valid = mask_data.valid_cell_count;
      let perm_ice = bio_covs.perm_ice;
      let total_px = mask_data.grid_width*mask_data.grid_height;
      let valid_indices = mask_data.valid_indices;

      //Function body
      let crp_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `cropland${hyde_lbl}.png`), total_px, cache);
      let irr_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `tot_irri${hyde_lbl}.png`), total_px, cache);
      let grz_grid = ViscountHUResidualHelpers.readCachedGlobalFloat(path.join(hyde_raw_dir, `grazing${hyde_lbl}.png`), total_px, cache);

      for (let i = 0; i < n_valid; i++) {
        let gidx = valid_indices[i];
        let is_hab = (year <= 1650) ?
          (hab_mask ? (hab_mask[i] === 1) : (perm_ice[i] > 0.05)) :
          (perm_ice[i] > 0.05);

        if (!is_hab) continue;
        let local_a = Math.max(min_area, cell_area[i]);
        let d = hyde_rur ? (hyde_rur[i]/local_a) : 0;
        let d_s = dist_site ? dist_site[i] : 99.0;
        let d_c = dist_catch ? dist_catch[i] : 99.0;

        if (d < 0.002) {
          let r19 = hyde_rur_1900 ? (hyde_rur_1900[i]/local_a) : 0;

          if (is_micro_island && d_c <= 5.6) {
            d = Math.max(d, 0.22*r19 + 0.004);
          } else if (d_s <= 3.0 && d_c <= 5.6) {
            d = Math.max(d, Math.exp(-0.55*d_s)*Math.max(0.004, 0.08*r19));
          }
        }
        d_raw[i] = d;
        lu_raw[i] = Math.max(0, (crp_grid[gidx] + 1.5*irr_grid[gidx] + 0.35*grz_grid[gidx])/local_a);
      }

      let d_decliff = (n_valid >= 2000 && bio_covs.sub_iso_valid && year < 1850) ?
        ViscountHUResidualHelpers.removeSubIsoCliffs(mask_data, d_raw, bio_covs.sub_iso_valid, 0.004, 16) :
        d_raw;
      let elig_hab = new Uint8Array(n_valid);

      for (let i = 0; i < n_valid; i++) {
        let is_hab = (year <= 1650) ?
          (hab_mask ? (hab_mask[i] === 1) : (perm_ice[i] > 0.05)) :
          (perm_ice[i] > 0.05);

        if (is_hab) elig_hab[i] = 1;
      }
      ViscountHUResidualHelpers.closeZeroPinholes(mask_data, d_decliff, elig_hab, 4, 0.45, 2, 0);
      let lu_decliff = (n_valid >= 2000 && bio_covs.sub_iso_valid && year < 1850) ?
        ViscountHUResidualHelpers.removeSubIsoCliffs(mask_data, lu_raw, bio_covs.sub_iso_valid, 0.002, 16) :
        lu_raw;
      let out = { d_decliff: d_decliff, lu_decliff: lu_decliff };

      if (cache) cache.set(ckey, out);

      //Return statement
      return out;
    }


    /**
     * Step C: Evaluates per-HU weighted HYDE 3.5 + landuse + documented settlements + dendrochronology
     * prior carrying-capacity density across valid cells.
     * @alias ViscountHUResidualKriging.C_evaluatePriorTrendField
     */
    static C_evaluatePriorTrendField (arg0_mask_data, arg1_bio_covs, arg2_hu_ctx, arg3_year, arg4_config, arg5_cache, arg6_options) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;
      let hu_ctx = arg2_hu_ctx;
      let year = Number(arg3_year) || 0;
      let config = (arg4_config) ? arg4_config : {};
      let cache = arg5_cache;
      let options = (arg6_options) ? arg6_options : {};

      //Declare local instance variables
      let hyde_yr = Number.isFinite(options.hyde_year) ? Number(options.hyde_year) : year;
      let strict_hab = Boolean(year <= 1650 || options.strict_hab);
      let ckey = (hyde_yr === year && !options.strict_hab) ? `hu_prior_${year}` : `hu_prior_${year}_h${hyde_yr}_${strict_hab ? 1 : 0}`;

      if (cache && cache.has(ckey)) return cache.get(ckey);
      let d_obj = this.B_computeMacroPreservingDeCliffedHYDE(mask_data, bio_covs, hyde_yr, config, cache);
      let d_decliff = d_obj.d_decliff;
      let dist_site = bio_covs.dist_site_px;
      let h = mask_data.grid_height;
      let hab_mask = bio_covs.hab_mask;
      let is_micro = (mask_data.valid_cell_count < 2000);
      let lu_decliff = d_obj.lu_decliff;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let perm_ice = bio_covs.perm_ice;
      let prior_dens = new Float32Array(n_valid);
      let u_coast = bio_covs.u_coastal;
      let u_den = new Float32Array(n_valid);
      let u_eco = bio_covs.u_eco;
      let u_fluv = bio_covs.u_fluvial;
      let u_nat = bio_covs.u_nat;
      let u_set = new Float32Array(n_valid);
      let w = mask_data.grid_width;

      //Function body
      let setts = hu_ctx.settlements || [];
      let s_rad_y = is_micro ? 4 : 9;
      let s_max_km = is_micro ? 35.0 : 80.0;

      for (let i = 0; i < setts.length; i++) {
        let s = setts[i];
        let pop = ViscountHUResidualHelpers.interpolateSeries(s.series, year, 80);

        if (pop <= 0) continue;
        let amp = Math.pow(pop, 0.68)/65.0;
        let max_dx = Math.min(s_rad_y*3, Math.ceil((s_rad_y + 0.5)/s.cos_lat));

        for (let dy = -s_rad_y; dy <= s_rad_y; dy++) {
          let ny = s.gy + dy;

          if (ny < 0 || ny >= h) continue;
          for (let dx = -max_dx; dx <= max_dx; dx++) {
            let d_km = 9.26*Math.sqrt(dy*dy + (dx*s.cos_lat)*(dx*s.cos_lat));

            if (d_km >= s_max_km) continue;
            let nx = (s.gx + dx + w) % w;
            let nv = p2v[ny*w + nx];

            if (nv >= 0) {
              let taper = 0.5*(1 + Math.cos(Math.PI*d_km/s_max_km));
              let k = taper*(0.74*Math.exp(-(d_km*d_km)/(2*14.0*14.0)) + 0.26*Math.exp(-(d_km*d_km)/(2*28.0*28.0)));

              u_set[nv] += amp*k;
            }
          }
        }
      }

      let d_regs = hu_ctx.dendro_regions || [];

      for (let i = 0; i < d_regs.length; i++) {
        let d = d_regs[i];
        let inten = ViscountHUResidualHelpers.interpolateSeries(d.series, year, 60);

        if (inten <= 0) continue;
        let d_rad_y = Math.min(18, Math.ceil((d.radius_km*2.2)/9.26));
        let max_dx = Math.min(d_rad_y*3, Math.ceil((d_rad_y + 1)/d.cos_lat));

        for (let dy = -d_rad_y; dy <= d_rad_y; dy++) {
          let ny = d.gy + dy;

          if (ny < 0 || ny >= h) continue;
          for (let dx = -max_dx; dx <= max_dx; dx++) {
            let d_km = 9.26*Math.sqrt(dy*dy + (dx*d.cos_lat)*(dx*d.cos_lat));

            if (d_km >= d.radius_km*2.2) continue;
            let nx = (d.gx + dx + w) % w;
            let nv = p2v[ny*w + nx];

            if (nv >= 0) {
              let dtap = 0.5*(1 + Math.cos(Math.PI*d_km/(d.radius_km*2.2)));

              u_den[nv] += inten*dtap*Math.exp(-(d_km*d_km)/(2*d.radius_km*d.radius_km));
            }
          }
        }
      }

      let d_cnt = 0;
      let d_sum = 0;
      let lu_cnt = 0;
      let lu_sum = 0;

      for (let i = 0; i < n_valid; i++) {
        if (d_decliff[i] > 0) {
          d_sum += Math.pow(d_decliff[i], 0.85);
          d_cnt++;
        }
        if (lu_decliff[i] > 0) {
          lu_sum += lu_decliff[i];
          lu_cnt++;
        }
      }
      let mean_d85 = Math.max(0.015, d_sum/Math.max(1, d_cnt));
      let mean_lu = Math.max(0.005, lu_sum/Math.max(1, lu_cnt));

      for (let i = 0; i < n_valid; i++) {
        let is_hab = hab_mask ? (hab_mask[i] === 1) : (perm_ice[i] > 0.05);

        if (!is_hab && strict_hab && (year <= 1650 || u_set[i] <= 0.02)) {
          prior_dens[i] = 0;
          continue;
        }
        if (perm_ice[i] <= 0.05) {
          prior_dens[i] = 0;
          continue;
        }
        let d_base = Math.pow(Math.max(0, d_decliff[i]), 0.85);
        let u_nat_c = Math.max(0.10, Math.min(2.2, u_nat[i]));
        let lu_val = lu_decliff[i] > 0 ?
          (0.68*Math.pow(lu_decliff[i]/mean_lu, 0.55) + 0.32*(0.75*u_nat_c + 0.25*u_eco[i])) :
          (0.75*u_nat_c + 0.25*u_eco[i]);
        let fluv_val = u_fluv ? (0.35 + 0.65*u_fluv[i]) : 1.0;
        let coast_val = u_coast ? (0.30 + 0.70*u_coast[i]) : 1.0;
        let den_val = 0.50*(0.7*u_nat_c + 0.3*u_eco[i]) + 0.85*Math.min(2.0, u_den[i]);
        let set_norm = Math.min(2.8, u_set[i]);
        let ice_env = (config.kriging_config && config.kriging_config.apply_ice_sheet_mask && year <= -5500) ?
          ViscountHUResidualHelpers.getLaurentideCordilleranIceFactor(mask_data, i, year) : 1.0;

        if (ice_env <= 0.04) {
          prior_dens[i] = 0;
          continue;
        }
        let phi_hu = hu_ctx.w_hyde[i]*1.15 +
          hu_ctx.w_landuse[i]*lu_val +
          hu_ctx.w_dendro[i]*den_val +
          hu_ctx.w_fluvial[i]*fluv_val +
          hu_ctx.w_coastal[i]*coast_val +
          hu_ctx.w_settlement[i]*0.30;
        let sett_add = hu_ctx.w_settlement[i]*mean_d85*1.65*set_norm*(0.40 + 0.60*Math.min(1.5, u_nat_c));
        let dendro_add = (u_den[i] > 0) ? (hu_ctx.w_dendro[i]*mean_d85*1.15*Math.min(2.0, u_den[i])*(0.40 + 0.60*lu_val)) : 0;
        let d_s = dist_site ? dist_site[i] : 99.0;
        let hab_gate = (d_decliff[i] > 0 || set_norm > 0.02 || (d_s <= 2.2)) ? 1.0 : 0.0;

        if (!strict_hab && year > 1650 && !is_hab) hab_gate = (d_decliff[i] > 0 || set_norm > 0.02) ? 0.55 : 0.08;
        if (!strict_hab && year > 1650 && is_hab && hab_gate === 0) hab_gate = 0.25;

        prior_dens[i] = perm_ice[i]*ice_env*hab_gate*(d_base*phi_hu + sett_add + dendro_add);
      }

      let res = { d_decliff: d_decliff, lu_decliff: lu_decliff, prior_dens: prior_dens, u_set: u_set };

      if (cache) cache.set(ckey, res);

      //Return statement
      return res;
    }


    /**
     * Evaluates signed residual Matérn (`nu = 3/2`) fields across 1 or more dual-weight vectors in a single shared pass.
     * @alias ViscountHUResidualKriging.D_evaluateMultiDualMaternFields
     */
    static D_evaluateMultiDualMaternFields (arg0_kriging_bundle, arg1_prior_bundles, arg2_v_vecs, arg3_years) {
      //Convert from parameters
      let bundle = arg0_kriging_bundle;
      let prior_bundles = arg1_prior_bundles;
      let v_vecs = arg2_v_vecs;
      let years = arg3_years;

      //Declare local instance variables
      let cell_area = bundle.mask_data.cell_land_area;
      let cell_r = bundle.obs_bundle.cell_radius_km;
      let cell_ux = bundle.mask_data.cell_ux;
      let cell_uy = bundle.mask_data.cell_uy;
      let cell_uz = bundle.mask_data.cell_uz;
      let earth_r = bundle.mask_data.earth_radius_km || 6371;
      let lut = bundle.matern_lut;
      let lut_scale = 8191/8;
      let mask_data = bundle.mask_data;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_p = v_vecs.length;
      let n_valid = mask_data.valid_cell_count;
      let obs_r = bundle.obs_bundle.obs_radius_km;
      let obs_ux = bundle.obs_bundle.obs_ux;
      let obs_uy = bundle.obs_bundle.obs_uy;
      let obs_uz = bundle.obs_bundle.obs_uz;
      let pop_fields = new Array(n_p);
      let r_acc = new Float64Array(n_p);
      let r_fields = new Array(n_p);
      let sp_ctx = ViscountHUResidualHelpers.getOrBuildSparseMaternMatrix(bundle);

      //Function body
      let c1 = sp_ctx.c1;
      let c2 = sp_ctx.c2;
      let inv_tau1 = sp_ctx.inv_tau1;
      let inv_tau2 = sp_ctx.inv_tau2;
      let min_dot = sp_ctx.min_dot;

      for (let p = 0; p < n_p; p++) {
        pop_fields[p] = new Float32Array(n_valid);
        r_fields[p] = new Float32Array(n_valid);
      }

      for (let i = 0; i < n_valid; i++) {
        let a_i = cell_area[i];
        let cx = cell_ux[i];
        let cy = cell_uy[i];
        let cz = cell_uz[i];
        let ri = cell_r[i];
        let ri2 = ri*ri;

        for (let p = 0; p < n_p; p++) r_acc[p] = 0;

        for (let x = 0; x < n_obs; x++) {
          let dot = cx*obs_ux[x] + cy*obs_uy[x] + cz*obs_uz[x];

          if (dot <= min_dot[x]) continue;
          if (dot > 1) dot = 1;
          else if (dot < -1) dot = -1;
          let c2_c = Math.max(0, 2 - 2*dot);
          let h = earth_r*Math.sqrt(c2_c)*(1 + c2_c/24);
          let rx = obs_r[x];
          let r2_sum = ri2 + rx*rx;
          let u = h/Math.sqrt(0.5*r2_sum);
          let v2 = u*inv_tau2;

          if (v2 >= 7.99) continue;
          let pref = (2*ri*rx)/Math.max(1e-8, r2_sum);
          let m1 = 0;
          let v1 = u*inv_tau1;

          if (v1 < 7.99) {
            let i1 = (v1*lut_scale) | 0;
            let f1 = v1*lut_scale - i1;

            m1 = pref*(lut[i1]*(1 - f1) + lut[i1 + 1]*f1);
          }
          let i2 = (v2*lut_scale) | 0;
          let f2 = v2*lut_scale - i2;
          let m2 = pref*(lut[i2]*(1 - f2) + lut[i2 + 1]*f2);
          let kern = c1*m1 + c2*m2;

          for (let p = 0; p < n_p; p++) {
            let vx = v_vecs[p][x];

            if (vx !== 0) r_acc[p] += vx*kern;
          }
        }

        for (let p = 0; p < n_p; p++) {
          let r_val = r_acc[p];

          r_fields[p][i] = r_val;
          if (prior_bundles[p].prior_dens[i] > 0)
            pop_fields[p][i] = a_i*prior_bundles[p].prior_dens[i]*Math.exp(Math.max(-1.15, Math.min(1.25, 0.85*r_val)));
        }
      }

      if (bundle._bio_covs && bundle._bio_covs.uopp_valid) {
        for (let p = 0; p < n_p; p++) {
          if (years[p] <= 1650)
            ViscountHUResidualHelpers.capUrbanCoreSmooth(mask_data, pop_fields[p], bundle._bio_covs.uopp_valid, 1.05);
        }
      }

      //Return statement
      return { pop_fields: pop_fields, r_fields: r_fields };
    }


    /**
     * Step D: Solves shrinkage-weighted signed residual Matérn (`nu = 3/2`) kriging around `prior_dens`
     * plus fits constrained NNLS `beta` for C1 diagnostic auditability.
     * @alias ViscountHUResidualKriging.D_solveSignedResidualMaternSurface
     */
    static D_solveSignedResidualMaternSurface (arg0_kriging_bundle, arg1_prior_bundle, arg2_z_obs, arg3_s_obs, arg4_year) {
      let bundle = arg0_kriging_bundle;
      let prior_bundle = arg1_prior_bundle;
      let s_obs = arg3_s_obs;
      let year = Number(arg4_year) || 0;
      let z_obs = arg2_z_obs;
      let v_vec = ViscountHUResidualHelpers.solveResidualDualWeights(bundle, prior_bundle, z_obs, s_obs);
      let multi_res = this.D_evaluateMultiDualMaternFields(bundle, [prior_bundle], [v_vec], [year]);

      //Return statement
      return {
        beta: ViscountHUResidualHelpers.fitDiagnosticsWLSBetas(bundle, prior_bundle.d_decliff, z_obs),
        pop_field: multi_res.pop_fields[0],
        r_field: multi_res.r_fields[0]
      };
    }


    /**
     * Evaluates residual kriging period surfaces (`fields[pkey]` + `residual_fields[pkey]`)
     * across all active periods in a single shared Matérn kernel pass.
     * @alias ViscountHUResidualKriging.evaluateAllPeriodResidualSurfaces
     */
    static evaluateAllPeriodResidualSurfaces (arg0_kriging_bundle, arg1_bio_covs, arg2_active_periods, arg3_hab_cache) {
      //Convert from parameters
      let bundle = arg0_kriging_bundle;
      let bio_covs = arg1_bio_covs;
      let active_periods = arg2_active_periods;
      let hab_cache = arg3_hab_cache || new Map();

      //Declare local instance variables
      let cfg = bundle.config;
      let fields = {};
      let hu_ctx = this.A_buildHUAdmixtureAndSettlementContext(bundle.mask_data, bio_covs, cfg);
      let n_valid = bundle.mask_data.valid_cell_count;
      let pkeys = [];
      let prior_bundles = [];
      let rep_years = [];
      let residual_fields = {};
      let v_vecs = [];
      let wls_betas_by_period = {};

      //Function body
      bundle._bio_covs = bio_covs;
      bundle._hu_ctx = hu_ctx;
      for (let p = 0; p < active_periods.length; p++) {
        let ap = active_periods[p];
        let p_cfg = ap.cfg;
        let pkey = ap.pkey;
        let rep_year = Number.isFinite(p_cfg.representative_year) ?
          p_cfg.representative_year :
          0.5*((p_cfg.approx_start_year || p_cfg.start_year || 0) + (p_cfg.approx_end_year || p_cfg.end_year || 0));
        let prior_b = this.C_evaluatePriorTrendField(bundle.mask_data, bio_covs, hu_ctx, rep_year, cfg, hab_cache);
        let v_vec = ViscountHUResidualHelpers.solveResidualDualWeights(bundle, prior_b, ap.model.z_adj, ap.model.s_obs);

        pkeys.push(pkey);
        prior_bundles.push(prior_b);
        rep_years.push(rep_year);
        v_vecs.push(v_vec);
        wls_betas_by_period[pkey] = ViscountHUResidualHelpers.fitDiagnosticsWLSBetas(bundle, prior_b.d_decliff, ap.model.z_adj);
      }
      let multi = this.D_evaluateMultiDualMaternFields(bundle, prior_bundles, v_vecs, rep_years);

      for (let p = 0; p < pkeys.length; p++) {
        let field = multi.pop_fields[p];
        let pkey = pkeys[p];
        let sum = 0;
        let target_sites = Math.max(1, (bundle.obs_bundle.period_totals && bundle.obs_bundle.period_totals[pkey]) ?
          bundle.obs_bundle.period_totals[pkey] : 1);

        if (rep_years[p] <= 1650 && bio_covs.uopp_valid && n_valid >= 2000)
          ViscountHUResidualHelpers.capUrbanCoreSmooth(bundle.mask_data, field, bio_covs.uopp_valid, 0.85);
        for (let i = 0; i < n_valid; i++) sum += field[i];
        let scale = (sum > 0) ? (target_sites/sum) : 1.0;

        for (let i = 0; i < n_valid; i++) field[i] *= scale;
        fields[pkey] = field;
        residual_fields[pkey] = multi.r_fields[p];
      }

      //Return statement
      return { fields: fields, residual_fields: residual_fields, wls_betas_by_period: wls_betas_by_period };
    }


    /**
     * Generates all 128 HYDE benchmark population rasters (`2.population_rasters/popc_<yr>.png`)
     * coupling HYDE-anchored Per-HU Residual Kriging (pre-census) with full Census/GHSL rural rollout (post-census).
     * @alias ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters
     */
    static generateAllBenchmarkPopulationRasters (arg0_surface_bundle, arg1_options) {
      //Convert from parameters
      let surface = arg0_surface_bundle;
      let options = (arg1_options) ? arg1_options : {};

      //Declare local instance variables
      let bio_covs = surface.bio_covs;
      let bundle = surface.kriging_bundle;
      let cache = surface.hab_cache || new Map();
      let cell_area = bundle.mask_data.cell_land_area;
      let cfg = bundle.config;
      let grid_h = bundle.mask_data.grid_height;
      let grid_w = bundle.mask_data.grid_width;
      let hab_mask = bio_covs.hab_mask;
      let horizons_cfg = (cfg.kriging_config && Array.isArray(cfg.kriging_config.chronological_horizons)) ?
        cfg.kriging_config.chronological_horizons : [];
      let hu_ctx = bundle._hu_ctx || this.A_buildHUAdmixtureAndSettlementContext(bundle.mask_data, bio_covs, cfg);
      let hyde_years = cfg.kriging_config.all_hyde_years || [];
      let is_samoa = options.is_polynesia ? new Uint8Array(bundle.mask_data.valid_cell_count) : null;
      let only_years = (options && Array.isArray(options.only_years) && options.only_years.length > 0) ?
        new Set(options.only_years) : null;
      let n_obs = bundle.obs_bundle.obs_count;
      let n_valid = bundle.mask_data.valid_cell_count;
      let out_dir = path.join(bundle.mask_data.domain_dir, cfg.output_population_rasters_subfolder || "2.population_rasters");
      let perm_ice = bio_covs.perm_ice;
      let period_res_fields = surface.residual_fields || null;
      let valid_indices = bundle.mask_data.valid_indices;
      let b_px = (cfg.kriging_config.bermuda_pixel) ?
        bundle.mask_data.pixel_to_valid_idx[cfg.kriging_config.bermuda_pixel.row*grid_w + cfg.kriging_config.bermuda_pixel.col] : -1;

      //Function body
      bundle._bio_covs = bio_covs;
      bundle._hu_ctx = hu_ctx;
      fs.mkdirSync(out_dir, { recursive: true });
      if (is_samoa) {
        for (let i = 0; i < n_valid; i++) {
          let lat = 90 - (Math.floor(valid_indices[i]/grid_w) + 0.5)*180/grid_h;

          if (lat < 0) is_samoa[i] = 1;
        }
      }

      let h_r_list = [];
      let h_z_list = [];

      for (let i = 0; i < horizons_cfg.length; i++) {
        let active_p = Array.isArray(horizons_cfg[i].active_periods) ? horizons_cfg[i].active_periods : [];

        if (period_res_fields) {
          let r_h = new Float32Array(n_valid);
          let w_sum = 0;

          for (let y = 0; y < active_p.length; y++) {
            let pkey = active_p[y];
            let rf = period_res_fields[pkey];

            if (!rf) continue;
            let wt = Math.max(1, (bundle.obs_bundle.period_totals && bundle.obs_bundle.period_totals[pkey]) ?
              bundle.obs_bundle.period_totals[pkey] : 1);

            for (let x = 0; x < n_valid; x++) r_h[x] += wt*rf[x];
            w_sum += wt;
          }
          if (w_sum > 0) {
            let inv_w = 1.0/w_sum;

            for (let x = 0; x < n_valid; x++) r_h[x] *= inv_w;
          }
          h_r_list.push({ r: r_h, year: horizons_cfg[i].year });
        } else {
          let s_h = new Float64Array(n_obs);
          let z_h = new Float64Array(n_obs);

          for (let x = 0; x < n_obs; x++) {
            let d2 = 0;
            let sc = 0;

            for (let y = 0; y < active_p.length; y++) {
              let model = bundle.kriging_models[active_p[y]];

              if (model) {
                if (model.z_adj) d2 += model.z_adj[x]*model.z_adj[x];
                if (model.s_obs) sc += model.s_obs[x];
              }
            }
            z_h[x] = Math.sqrt(d2);
            s_h[x] = sc;
          }
          h_z_list.push({ s: s_h, year: horizons_cfg[i].year, z: z_h });
        }
      }
      h_r_list.sort(function (arg0_a, arg1_b) { return arg0_a.year - arg1_b.year; });
      h_z_list.sort(function (arg0_a, arg1_b) { return arg0_a.year - arg1_b.year; });

      for (let y_idx = 0; y_idx < hyde_years.length; y_idx++) {
        let yr = hyde_years[y_idx];
        if (only_years && !only_years.has(yr)) continue;
        let ccf_cfg = hu_ctx.county_census_frontier || null;
        let use_county_frontier = Boolean(
          !options.is_polynesia &&
          n_valid >= 2000 &&
          ccf_cfg &&
          ccf_cfg.enabled &&
          yr >= Number(ccf_cfg.start_year || 1700) &&
          yr <= Number(ccf_cfg.end_year || 1870)
        );
        let w_krig_max = 0;
        let w_krig = new Float32Array(n_valid);

        for (let i = 0; i < n_valid; i++) {
          let t0 = hu_ctx.t0_arr[i];
          let t1 = Math.max(t0 + 1, hu_ctx.t1_arr[i]);
          let wk = (yr <= t0) ? 1.0 : ((yr >= t1) ? 0.0 : 0.5*(1 + Math.cos(Math.PI*(yr - t0)/(t1 - t0))));

          w_krig[i] = wk;
          if (wk > w_krig_max) w_krig_max = wk;
        }

        ViscountHUResidualHelpers.trimRasterCache(cache, 20, 14);
        let need_hyde_popc = (w_krig_max > 0.001) || use_county_frontier || (yr < 1975);
        let hyde_rur_raw = need_hyde_popc ?
          ViscountUrbanMask.loadUrbanMaskedHYDEPopcRaster(bundle.mask_data, yr, cache, cfg) : null;
        let hyde_sum = 0;

        if (hyde_rur_raw)
          for (let i = 0; i < n_valid; i++) hyde_sum += hyde_rur_raw[i];
        let target_mass = options.is_polynesia ?
          ((yr >= 800) ? Math.max(2e4, Math.round(3e5*Math.exp((yr - 1750)/2500))) : 1e4) :
          ((hyde_sum > 5e4) ? hyde_sum : Math.max(2e5, Math.round(6e5*Math.exp((yr - 1500)/3200))));

        let rk_pop = null;

        if (w_krig_max > 0.001 || use_county_frontier) {
          let prior_opts = use_county_frontier ? { hyde_year: 1600, strict_hab: true } : null;
          let prior_b = this.C_evaluatePriorTrendField(bundle.mask_data, bio_covs, hu_ctx, yr, cfg, cache, prior_opts);

          if (h_r_list.length > 0) {
            let alpha = 0;
            let r_a = h_r_list[0].r;
            let r_b = h_r_list[0].r;

            if (yr >= h_r_list[h_r_list.length - 1].year) {
              r_a = h_r_list[h_r_list.length - 1].r;
              r_b = r_a;
            } else if (yr > h_r_list[0].year) {
              for (let k = 0; k < h_r_list.length - 1; k++) {
                if (yr >= h_r_list[k].year && yr <= h_r_list[k + 1].year) {
                  r_a = h_r_list[k].r;
                  r_b = h_r_list[k + 1].r;
                  alpha = (yr - h_r_list[k].year)/Math.max(1, h_r_list[k + 1].year - h_r_list[k].year);
                  break;
                }
              }
            }
            rk_pop = new Float32Array(n_valid);
            for (let i = 0; i < n_valid; i++) {
              if (prior_b.prior_dens[i] <= 0) continue;
              let r_val = (1 - alpha)*r_a[i] + alpha*r_b[i];
              let res_mult = Math.exp(Math.max(-1.15, Math.min(1.25, 0.85*r_val)));

              rk_pop[i] = cell_area[i]*prior_b.prior_dens[i]*res_mult;
            }
            if (yr <= 1650 && bio_covs.uopp_valid)
              ViscountHUResidualHelpers.capUrbanCoreSmooth(bundle.mask_data, rk_pop, bio_covs.uopp_valid, 0.85);
          } else if (h_z_list.length > 0) {
            let alpha = 0;
            let s_a = h_z_list[0].s;
            let s_b = h_z_list[0].s;
            let z_a = h_z_list[0].z;
            let z_b = h_z_list[0].z;

            if (yr >= h_z_list[h_z_list.length - 1].year) {
              let last_h = h_z_list[h_z_list.length - 1];

              z_a = last_h.z;
              z_b = last_h.z;
              s_a = last_h.s;
              s_b = last_h.s;
            } else if (yr > h_z_list[0].year) {
              for (let k = 0; k < h_z_list.length - 1; k++) {
                if (yr >= h_z_list[k].year && yr <= h_z_list[k + 1].year) {
                  z_a = h_z_list[k].z;
                  z_b = h_z_list[k + 1].z;
                  s_a = h_z_list[k].s;
                  s_b = h_z_list[k + 1].s;
                  alpha = (yr - h_z_list[k].year)/Math.max(1, h_z_list[k + 1].year - h_z_list[k].year);
                  break;
                }
              }
            }
            let s_yr = new Float64Array(n_obs);
            let z_yr = new Float64Array(n_obs);

            for (let i = 0; i < n_obs; i++) {
              z_yr[i] = (1 - alpha)*z_a[i] + alpha*z_b[i];
              s_yr[i] = (1 - alpha)*s_a[i] + alpha*s_b[i];
            }
            rk_pop = this.D_solveSignedResidualMaternSurface(bundle, prior_b, z_yr, s_yr, yr, hu_ctx).pop_field;
          }

          if (rk_pop && is_samoa) {
            let hi_sc = (yr < 950) ? ((yr < 800) ? 0.001 : (0.05 + 0.95*Math.max(0, (yr - 800)/150))) : 1.0;
            let sam_sc = (yr < 950) ? ((yr <= -1000) ? 0.08 : (0.15 + 0.85*Math.max(0, (yr + 1000)/1950))) : 1.0;

            for (let i = 0; i < n_valid; i++) rk_pop[i] *= (is_samoa[i] ? sam_sc : hi_sc);
          }
          let rk_sum = 0;

          if (rk_pop)
            for (let i = 0; i < n_valid; i++) rk_sum += rk_pop[i];
          if (rk_pop && rk_sum > 0 && target_mass > 0) {
            let k_sc = target_mass/rk_sum;

            for (let i = 0; i < n_valid; i++) rk_pop[i] *= k_sc;
          }
        }

        let census_pop = null;

        if (!use_county_frontier && w_krig_max < 0.999) {
          let c_min = 1.0;

          for (let i = 0; i < n_valid; i++)
            if (w_krig[i] < c_min) c_min = w_krig[i];
          if (c_min < 0.999) {
            census_pop = ViscountHUResidualHelpers.evaluateModernCensusAndSatelliteRural(bundle.mask_data, bio_covs, yr, cfg, cache);
            let c_sum = 0;

            for (let i = 0; i < n_valid; i++) c_sum += census_pop[i];
            if (c_sum > 0 && target_mass > 0 && yr < 1975) {
              let c_sc = target_mass/c_sum;

              for (let i = 0; i < n_valid; i++) census_pop[i] *= c_sc;
            }
          }
        }

        let ccf_field = use_county_frontier ?
          ViscountCountyCensusFrontier.C_evaluateCensusCountyAndFrontierSurface(bundle, bio_covs, hu_ctx, rk_pop, yr, ccf_cfg, cache) : null;
        let elig_out = new Uint8Array(n_valid);
        let out_field = new Float32Array(n_valid);

        for (let i = 0; i < n_valid; i++) {
          let wk = w_krig[i];
          let v_rk = rk_pop ? rk_pop[i] : 0;
          let v_cn = census_pop ? census_pop[i] : v_rk;
          let v = 0;

          if (ccf_field) v = ccf_field[i];
          else if (census_pop && rk_pop) v = wk*v_rk + (1 - wk)*v_cn;
          else v = rk_pop ? v_rk : v_cn;

          if (perm_ice[i] <= 0.05) v = 0;
          else if (yr <= 1650 && hab_mask && hab_mask[i] === 0) v = 0;
          else if (ccf_field && v <= 0) v = 0;
          else {
            elig_out[i] = 1;
            v = (v > 0) ? Math.max(1e-5, v) : 0;
          }
          out_field[i] = v;
        }
        ViscountHUResidualHelpers.closeZeroPinholes(bundle.mask_data, out_field, elig_out, 5, 0.45, 2, 1e-4);

        if (b_px >= 0)
          out_field[b_px] = (yr < 1609) ? 0 : Math.max(10, 450 + Math.max(0, yr - 1609)*140);

        let f_buf = new ArrayBuffer(4);
        let f_dv = new DataView(f_buf);
        let img = new PNG({ colorType: 6, height: grid_h, width: grid_w });

        for (let i = 0; i < n_valid; i++) {
          let px = valid_indices[i]*4;

          if (out_field[i] > 0) {
            f_dv.setFloat32(0, out_field[i], false);
            img.data[px] = f_dv.getUint8(0);
            img.data[px + 1] = f_dv.getUint8(1);
            img.data[px + 2] = f_dv.getUint8(2);
            img.data[px + 3] = f_dv.getUint8(3);
          }
        }
        fs.writeFileSync(path.join(out_dir, `popc_${yr}.png`), PNG.sync.write(img, { colorType: 6, deflateLevel: 6 }));
      }

      //Return statement
      return { generated_years: hyde_years.length, out_dir: out_dir };
    }
  };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = { ViscountHUResidualKriging: global.ViscountHUResidualKriging };
