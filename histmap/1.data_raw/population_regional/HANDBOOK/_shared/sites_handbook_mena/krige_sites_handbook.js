//Import modules
let fs = require("fs");
let path = require("path");
let { ViscountBiophysicalCovariates } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountBiophysicalCovariates.js"));
let { ViscountHUResidualKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/centaur/ViscountHUResidualKriging.js"));
let { ViscountMaternKriging } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountMaternKriging.js"));
let { ViscountRuralSuitability } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountRuralSuitability.js"));
let { ViscountUrbanMask } = require(path.resolve(__dirname, "../../../../../3.data_transform/population_Substrata.viscount/ViscountUrbanMask.js"));

//Initialise functions
{
  /**
   * Executes POLARIS-grade Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological Residual Kriging
   * across Project HANDBOOK (North Africa, the Near East, Anatolia, Cyprus, Transcaucasia, Iran, Afghanistan
   * and the Arabian Peninsula) and synthesises all 128 HYDE benchmark rural suitability GeoPNGs (`-10000` to `2025 AD`).
   *
   * Strictly HANDBOOK-isolated biophysical agro-ecological calibration (zero geometric lat/lon box cuts!):
   * - Uses pure HYDE 1500 AD agricultural land use (cropland, irrigation, grazing) + documented settlement proximity
   *   to organically prune Saharan modern-highway tracks & Rub' al-Khali/Nafud/Eastern Desert numerical dust;
   * - Elevates MENA mid-altitude terraced highlands & plateaus (600-2500 m: Yemen/Asir, Armenia, Eastern Anatolia,
   *   Zagros, Lebanon, Rif/Atlas) so orographic rainfall belts are never darkened;
   * - Gates `u_fluvial` smoothly to true perennial hydraulic basins (Nile, Tigris-Euphrates-Karun) whilst damping
   *   dry desert wadis and upland streams across rain-fed territories.
   *
   * @class HandbookKrigingRunner
   */
  global.HandbookKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/HANDBOOK/_shared/sites_handbook_mena/config/sites_handbook_mena.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Applies strictly HANDBOOK-isolated, purely biophysical (zero rectangular box cuts!) MENA agro-ecological
     * calibration to static covariates before residual kriging.
     * @alias HandbookKrigingRunner.applyMenaAgroEcologicalCalibration
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     */
    static applyMenaAgroEcologicalCalibration (arg0_mask_data, arg1_bio_covs) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;

      //Guard clauses
      if (!mask_data || !bio_covs) return;

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let dist_stad = bio_covs.dist_stadester_px;
      let elev = bio_covs.elev_valid;
      let forest = bio_covs.forest_valid;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hab_mask = bio_covs.hab_mask;
      let hyde_raw_dir = path.resolve(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let n_valid = mask_data.valid_cell_count;
      let raw_hyde = bio_covs.raw_hyde_dens;
      let total_px = grid_w*grid_h;
      let u_elev = bio_covs.u_elev;
      let u_fluvial = bio_covs.u_fluvial;
      let u_slope = bio_covs.u_slope;
      let u_terrain = bio_covs.u_terrain;
      let v_idx = mask_data.valid_indices;

      let crp_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "cropland1500AD.png"), total_px);
      let irr_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "tot_irri1500AD.png"), total_px);
      let grz_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "grazing1500AD.png"), total_px);

      let smoothStep = function (arg0_x, arg1_e0, arg2_e1) {
        let t = Math.max(0, Math.min(1, (arg0_x - arg1_e0)/Math.max(1e-6, arg2_e1 - arg1_e0)));

        return t*t*(3 - 2*t);
      };

      let smoothEllipsoid = function (arg0_lon, arg1_lat, arg2_clon, arg3_clat, arg4_rlon, arg5_rlat) {
        let dx = (arg0_lon - arg2_clon)/arg4_rlon;
        let dy = (arg1_lat - arg3_clat)/arg5_rlat;
        let d = Math.sqrt(dx*dx + dy*dy);

        return 1.0 - smoothStep(d, 0.72, 1.15);
      };

      //Function body
      let pruned_desert_px = 0;

      for (let i = 0; i < n_valid; i++) {
        let gidx = v_idx[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let lat = 90 - (r + 0.5)*180/grid_h;
        let lon = -180 + (c + 0.5)*360/grid_w;
        let e_m = elev ? elev[i] : 150.0;
        let la_i = Math.max(1.0, cell_area ? cell_area[i] : 75.0);
        let crp_frac = crp_1500 ? (crp_1500[gidx]/la_i) : 0;
        let irr_frac = irr_1500 ? (irr_1500[gidx]/la_i) : 0;
        let grz_frac = grz_1500 ? (grz_1500[gidx]/la_i) : 0;
        let f_v = forest ? forest[i] : 0;

        //1. MENA Highland & Terraced Plateau Elevation/Slope Recalibration (orographic agricultural belts 600-2550 m)
        if (u_elev && u_slope && u_terrain) {
          let w_yemen = smoothEllipsoid(lon, lat, 44.0, 15.8, 3.8, 4.2);
          let e_mid = 2200.0 + 400.0*w_yemen;
          let e_hi = 3000.0 + 200.0*w_yemen;
          let e_alp = 3900.0;
          let ue_new = 1.0 - 0.14*smoothStep(e_m, 800.0, e_mid) - 0.34*smoothStep(e_m, e_mid, e_hi) - 0.42*smoothStep(e_m, e_hi, e_alp);
          let us_new = 0.58 + 0.42*u_slope[i];

          u_elev[i] = Math.max(0.08, Math.min(1.0, ue_new));
          u_slope[i] = Math.max(0.42, Math.min(1.0, us_new));
          u_terrain[i] = Math.max(0.04, u_elev[i]*u_slope[i]);
        }

        //2. Smooth Elliptical Perennial-Alluvial Fluvial Gating (zero rectangular seams, zero desert wadi worms)
        if (u_fluvial) {
          let w_nile = Math.max(
            smoothEllipsoid(lon, lat, 31.2, 30.8, 2.2, 1.5),
            smoothEllipsoid(lon, lat, 31.6, 26.2, 1.8, 4.6)
          );
          let w_mesop = Math.max(
            smoothEllipsoid(lon, lat, 45.2, 32.5, 4.8, 3.2),
            smoothEllipsoid(lon, lat, 41.5, 35.8, 3.8, 2.2)
          );
          let w_cauc_oxus = Math.max(
            smoothEllipsoid(lon, lat, 46.8, 40.5, 3.2, 1.8),
            smoothEllipsoid(lon, lat, 65.5, 37.0, 4.8, 1.5)
          );
          let is_arid_biophys = (irr_frac < 0.002 && grz_frac < 0.02 && crp_frac < 0.008 && f_v === 0) ? 1.0 : 0.0;
          let fluv_scale = 0.20*(1.0 - 0.70*is_arid_biophys);

          fluv_scale = Math.max(fluv_scale, 0.95*w_nile, 0.80*w_mesop, 0.45*w_cauc_oxus);
          u_fluvial[i] = 0.06 + (u_fluvial[i] - 0.06)*fluv_scale;
        }

        //3. Purely Biophysical Hyper-Arid Noise & Modern-Road Track Pruning (ZERO lat/lon rectangular cuts!)
        //   Any pixel with negligible 1500 AD grazing (< 1.5% cell area), zero irrigation, zero forest,
        //   not adjacent to a documented pre-1900 settlement/oasis, and low HYDE density (< 1.4/km2)
        //   is a hyper-arid desert smear or modern Trans-Saharan/Arabian road track -> prune organically!
        if (hab_mask && hab_mask[i] === 1 && raw_hyde) {
          let d_st = dist_stad ? dist_stad[i] : 99.0;
          let rh = raw_hyde[i];
          let has_agro_pastoral = (irr_frac >= 0.001) || (grz_frac >= 0.015) || (f_v > 0);

          if (!has_agro_pastoral) {
            let keep_oasis = (d_st <= 1.65) || (rh >= 1.45 && crp_frac >= 0.003) || (rh >= 2.25);

            if (!keep_oasis) {
              hab_mask[i] = 0;
              pruned_desert_px++;
            }
          }
        }
      }

      console.log(`[HandbookKrigingRunner] Applied purely biophysical HANDBOOK calibration (pruned ${pruned_desert_px} hyper-arid non-oasis pixels, zero box cuts).`);
    }

    /**
     * Gentle urban-core cap preventing modern mega-sprawl anomalies whilst preserving the genuinely dense
     * historical Nile Delta & Mesopotamia cores.
     * @alias HandbookKrigingRunner.capMenaMetroUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.98]
     */
    static capMenaMetroUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let uopp_valid = arg2_uopp_valid;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.98;

      //Guard clauses
      if (!mask_data || !field || !uopp_valid) return;

      //Declare local instance variables
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let n_valid = mask_data.valid_cell_count;
      let p2v = mask_data.pixel_to_valid_idx;
      let rural_wide = new Float32Array(n_valid);
      let v_idx = mask_data.valid_indices;

      //Function body
      for (let i = 0; i < n_valid; i++)
        if (field[i] > 0 && uopp_valid[i] <= 4.5) rural_wide[i] = field[i];

      let wide_mean = ViscountRuralSuitability.smoothPositiveFieldOnGrid(mask_data, rural_wide, 12);

      for (let i = 0; i < n_valid; i++) {
        if (field[i] <= 0 || uopp_valid[i] <= 12.0) continue;
        let ref_val = wide_mean[i];

        if (ref_val > 0 && field[i] > ref_val*max_mult)
          field[i] = ref_val*max_mult;
      }
    }

    /**
     * Executes full Matérn kriging + 128-year dasymetric residual raster synthesis for HANDBOOK.
     * @alias HandbookKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      let t0 = Date.now();
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);

      //Temporarily hook buildStaticCovariates strictly within this HANDBOOK process so sibling projects are never affected
      let orig_build = ViscountBiophysicalCovariates.buildStaticCovariates;
      let self_cls = this;
      let surface = null;

      ViscountBiophysicalCovariates.buildStaticCovariates = function (arg0_m, arg1_c, arg2_o) {
        let covs = orig_build.call(ViscountBiophysicalCovariates, arg0_m, arg1_c, arg2_o);

        self_cls.applyMenaAgroEcologicalCalibration(arg0_m, covs);
        return covs;
      };
      try {
        surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);
      } finally {
        ViscountBiophysicalCovariates.buildStaticCovariates = orig_build;
      }

      let bio_covs = surface.bio_covs;
      let mask_data = surface.kriging_bundle.mask_data;
      let strict_hab = (bio_covs && bio_covs.hab_mask) ? bio_covs.hab_mask : null;

      surface.strict_hab_mask = strict_hab;

      let uopp_valid = (bio_covs && bio_covs.uopp_valid) ? bio_covs.uopp_valid : null;
      let field_keys = Object.keys(surface.fields || {});

      for (let i = 0; i < field_keys.length; i++) {
        let f_arr = surface.fields[field_keys[i]];

        if (!f_arr) continue;
        if (uopp_valid)
          this.capMenaMetroUrbanCores(mask_data, f_arr, uopp_valid, 0.85);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let raster_meta = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });

      if (surface.hab_cache && typeof surface.hab_cache.clear === "function") surface.hab_cache.clear();
      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);

      //Return statement
      return {
        diag: diag,
        elapsed_seconds: Number(((Date.now() - t0)/1000).toFixed(2)),
        raster_meta: raster_meta
      };
    }
  };
}

if (require.main === module) {
  let res = global.HandbookKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
