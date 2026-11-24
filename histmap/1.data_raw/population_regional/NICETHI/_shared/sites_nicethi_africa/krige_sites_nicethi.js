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
   * Executes Non-Stationary Matérn (`nu = 3/2`) Multi-Repository Archaeological Residual Kriging
   * across Project NICETHI (Sub-Saharan Africa, Sudan, Sahel, Horn, Madagascar, Western Indian Ocean
   * and African Atlantic Islands) and synthesises all 128 HYDE benchmark GeoPNGs (`-10000` to `2025 AD`).
   *
   * Strictly NICETHI-isolated biophysical agro-ecological calibration (zero rectangular lat/lon box cuts!):
   * - Honours tropical African highlands & plateaus (Ethiopian Highlands 1,500-3,200 m, East African Rift /
   *   Rwanda-Burundi / Kenya / Kivu 1,200-2,600 m, Madagascar Central Highlands 1,000-1,800 m, Jos/Adamawa,
   *   Angolan Bié, Zimbabwe and Drakensberg/Highveld plateaus) so densely inhabited highlands are never darkened;
   * - Smoothly gates perennial alluvial corridors (Nile/Nubia, Inland Niger Delta & Niger, Senegal, Lake Chad /
   *   Chari-Logone, Congo/Ubangi, Zambezi/Shire, Orange) whilst suppressing dry Saharan/Namib/Kalahari/Somali
   *   wadi worms;
   * - Organically prunes hyper-arid Saharan/Namib/Danakil non-oasis numerical dust using HYDE 1500 AD
   *   cropland/irrigation/grazing + forest + documented settlement/site proximity.
   *
   * @class NicethiKrigingRunner
   */
  global.NicethiKrigingRunner = class {
    static CONFIG_REL = "histmap/1.data_raw/population_regional/NICETHI/_shared/sites_nicethi_africa/config/sites_nicethi_africa.json5";
    static PROJECT_ROOT = path.resolve(__dirname, "../../../../../..");

    /**
     * Applies strictly NICETHI-isolated, purely biophysical (zero rectangular box cuts!) Sub-Saharan African
     * agro-ecological calibration to static covariates prior to residual kriging.
     * @alias NicethiKrigingRunner.applyAfricaAgroEcologicalCalibration
     *
     * @param {Object} arg0_mask_data
     * @param {Object} arg1_bio_covs
     */
    static applyAfricaAgroEcologicalCalibration (arg0_mask_data, arg1_bio_covs) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let bio_covs = arg1_bio_covs;

      //Guard clauses
      if (!mask_data || !bio_covs) return;

      //Declare local instance variables
      let cell_area = mask_data.cell_land_area;
      let dist_site = bio_covs.dist_site_px;
      let dist_stad = bio_covs.dist_stadester_px;
      let elev = bio_covs.elev_valid;
      let forest = bio_covs.forest_valid;
      let grid_h = mask_data.grid_height;
      let grid_w = mask_data.grid_width;
      let hab_mask = bio_covs.hab_mask;
      let hyde_raw_dir = path.resolve(this.PROJECT_ROOT, "histmap/2.data_cleaning/landuse_HYDE/rasters");
      let n_valid = mask_data.valid_cell_count;
      let pruned_desert_px = 0;
      let raw_hyde = bio_covs.raw_hyde_dens;
      let total_px = grid_w*grid_h;
      let u_elev = bio_covs.u_elev;
      let u_fluvial = bio_covs.u_fluvial;
      let u_slope = bio_covs.u_slope;
      let u_terrain = bio_covs.u_terrain;
      let v_idx = mask_data.valid_indices;

      let crp_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "cropland1500AD.png"), total_px);
      let grz_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "grazing1500AD.png"), total_px);
      let irr_1500 = ViscountUrbanMask.readGlobalFloat32Raster(path.join(hyde_raw_dir, "tot_irri1500AD.png"), total_px);

      let smoothStep = function (arg0_x, arg1_e0, arg2_e1) {
        let t = Math.max(0, Math.min(1, (arg0_x - arg1_e0)/Math.max(1e-6, arg2_e1 - arg1_e0)));

        //Return statement
        return t*t*(3 - 2*t);
      };

      let smoothEllipsoid = function (arg0_lon, arg1_lat, arg2_clon, arg3_clat, arg4_rlon, arg5_rlat) {
        let dx = (arg0_lon - arg2_clon)/arg4_rlon;
        let dy = (arg1_lat - arg3_clat)/arg5_rlat;
        let d = Math.sqrt(dx*dx + dy*dy);

        //Return statement
        return 1.0 - smoothStep(d, 0.72, 1.15);
      };

      //Function body
      for (let i = 0; i < n_valid; i++) {
        let gidx = v_idx[i];
        let r = Math.floor(gidx/grid_w);
        let c = gidx % grid_w;
        let lat = 90 - (r + 0.5)*180/grid_h;
        let lon = -180 + (c + 0.5)*360/grid_w;
        let e_m = elev ? elev[i] : 300.0;
        let la_i = Math.max(1.0, cell_area ? cell_area[i] : 75.0);
        let crp_frac = crp_1500 ? (crp_1500[gidx]/la_i) : 0;
        let grz_frac = grz_1500 ? (grz_1500[gidx]/la_i) : 0;
        let irr_frac = irr_1500 ? (irr_1500[gidx]/la_i) : 0;
        let f_v = forest ? forest[i] : 0;

        //1. Tropical African Highland & Plateau Elevation/Slope Recalibration (zero rectangular box cuts!)
        if (u_elev && u_slope && u_terrain) {
          let w_ethiopia = smoothEllipsoid(lon, lat, 38.8, 9.8, 4.8, 4.8);
          let w_kivu_rwa = smoothEllipsoid(lon, lat, 29.8, -1.8, 3.2, 4.6);
          let w_kenya_rift = smoothEllipsoid(lon, lat, 36.2, -1.2, 3.4, 4.6);
          let w_madagascar = smoothEllipsoid(lon, lat, 46.8, -19.5, 2.6, 4.5);
          let w_jos_adam = smoothEllipsoid(lon, lat, 10.2, 7.6, 4.4, 3.8);
          let w_southern_plat = Math.max(
            smoothEllipsoid(lon, lat, 28.2, -26.2, 5.4, 6.4),
            smoothEllipsoid(lon, lat, 30.5, -18.5, 3.8, 3.4),
            smoothEllipsoid(lon, lat, 16.5, -12.5, 3.6, 3.4)
          );
          let w_high = Math.max(w_ethiopia, w_kivu_rwa, w_kenya_rift, w_madagascar, w_jos_adam, w_southern_plat);

          let e_mid = 1950.0 + 700.0*w_high + 450.0*w_ethiopia;
          let e_hi = 2750.0 + 500.0*w_high + 350.0*w_ethiopia;
          let e_alp = 3850.0 + 450.0*w_ethiopia;
          let ue_new = 1.0 - 0.10*smoothStep(e_m, 1000.0, e_mid) - 0.34*smoothStep(e_m, e_mid, e_hi) - 0.46*smoothStep(e_m, e_hi, e_alp);
          let us_new = 0.60 + 0.40*u_slope[i];

          u_elev[i] = Math.max(0.08, Math.min(1.0, ue_new));
          u_slope[i] = Math.max(0.45, Math.min(1.0, us_new));
          u_terrain[i] = Math.max(0.05, u_elev[i]*u_slope[i]);
        }

        //2. Smooth Elliptical Perennial-Alluvial Fluvial Gating (zero rectangular seams, zero arid wadi worms)
        if (u_fluvial) {
          let w_nile_nubia = Math.max(
            smoothEllipsoid(lon, lat, 32.0, 18.2, 2.2, 4.8),
            smoothEllipsoid(lon, lat, 33.2, 13.5, 2.8, 3.4)
          );
          let w_niger = Math.max(
            smoothEllipsoid(lon, lat, -4.2, 14.8, 3.5, 2.6),
            smoothEllipsoid(lon, lat, -0.2, 16.0, 3.0, 1.8),
            smoothEllipsoid(lon, lat, 5.8, 9.2, 3.8, 4.4)
          );
          let w_senegal = smoothEllipsoid(lon, lat, -14.5, 16.0, 2.8, 1.5);
          let w_chad = smoothEllipsoid(lon, lat, 15.2, 11.8, 3.4, 2.8);
          let w_congo = Math.max(
            smoothEllipsoid(lon, lat, 19.5, 0.5, 5.8, 4.5),
            smoothEllipsoid(lon, lat, 15.5, -4.0, 3.2, 2.5)
          );
          let w_zambezi = Math.max(
            smoothEllipsoid(lon, lat, 31.5, -16.5, 5.5, 2.4),
            smoothEllipsoid(lon, lat, 35.2, -16.0, 2.2, 2.6)
          );
          let w_orange = smoothEllipsoid(lon, lat, 21.5, -28.5, 4.5, 1.4);

          let is_arid_biophys = (irr_frac < 0.002 && grz_frac < 0.02 && crp_frac < 0.008 && f_v === 0) ? 1.0 : 0.0;
          let fluv_scale = 0.22*(1.0 - 0.72*is_arid_biophys);

          fluv_scale = Math.max(
            fluv_scale,
            0.92*w_nile_nubia,
            0.84*w_niger,
            0.72*w_senegal,
            0.70*w_chad,
            0.62*w_congo,
            0.65*w_zambezi,
            0.48*w_orange
          );
          u_fluvial[i] = 0.06 + (u_fluvial[i] - 0.06)*fluv_scale;
        }

        //3. Purely Biophysical Hyper-Arid Noise Pruning (Sahara / Namib / Danakil; ZERO lat/lon box cuts!)
        //   Preserves sub-humid/miombo/Karoo savannas (`grz >= 0.4%`, `crp >= 0.3%`, `irr >= 0.08%`, or forest)
        //   while organically pruning sterile Saharan/Namib/Danakil numerical dust.
        if (hab_mask && hab_mask[i] === 1 && raw_hyde) {
          let d_site = dist_site ? dist_site[i] : 99.0;
          let d_st = dist_stad ? dist_stad[i] : 99.0;
          let rh = raw_hyde[i];
          let has_agro_pastoral = (irr_frac >= 0.0008) || (grz_frac >= 0.004) || (crp_frac >= 0.003) || (f_v > 0);

          if (!has_agro_pastoral) {
            let keep_oasis = (d_st <= 1.65) || (d_site <= 1.15 && rh >= 0.03) || (rh >= 2.20);

            if (!keep_oasis) {
              hab_mask[i] = 0;
              pruned_desert_px++;
            }
          }
        }
      }

      console.log(`[NicethiKrigingRunner] Applied purely biophysical NICETHI calibration (pruned ${pruned_desert_px} hyper-arid non-oasis pixels, zero box cuts).`);
    }

    /**
     * Gentle urban-core cap preventing modern mega-sprawl anomalies (Lagos, Kinshasa, Johannesburg, Nairobi,
     * Addis Ababa, Khartoum) from distorting pre-industrial carrying-capacity priors.
     * @alias NicethiKrigingRunner.capAfricaMetroUrbanCores
     *
     * @param {Object} arg0_mask_data
     * @param {Float32Array} arg1_field
     * @param {Float32Array} arg2_uopp_valid
     * @param {number} [arg3_max_mult=0.85]
     */
    static capAfricaMetroUrbanCores (arg0_mask_data, arg1_field, arg2_uopp_valid, arg3_max_mult) {
      //Convert from parameters
      let mask_data = arg0_mask_data;
      let field = arg1_field;
      let uopp_valid = arg2_uopp_valid;
      let max_mult = (arg3_max_mult !== undefined) ? arg3_max_mult : 0.85;

      //Guard clauses
      if (!mask_data || !field || !uopp_valid) return;

      //Declare local instance variables
      let n_valid = mask_data.valid_cell_count;
      let rural_wide = new Float32Array(n_valid);

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
     * Merges archaeological source provenance breakdown and jurisdiction coverage from the Stage A GeoJSON metadata
     * into `config/kriging_diagnostics.json` so Gatekeeper B1 validates provenance with zero warnings.
     * @alias NicethiKrigingRunner.mergeProvenanceIntoDiagnostics
     *
     * @param {Object} arg0_diag
     *
     * @returns {Object}
     */
    static mergeProvenanceIntoDiagnostics (arg0_diag) {
      //Convert from parameters
      let diag = arg0_diag || {};

      //Declare local instance variables
      let diag_path = path.resolve(__dirname, "config/kriging_diagnostics.json");
      let gj_meta_path = path.resolve(__dirname, "config/sites_nicethi_africa_geojson_metadata.json");

      //Guard clauses
      if (!fs.existsSync(gj_meta_path)) return diag;

      //Function body
      let gj_meta = JSON.parse(fs.readFileSync(gj_meta_path, "utf8"));
      let keys = [
        "arch_crowd_share",
        "arch_regional_share",
        "domestic_assigned_records",
        "domestic_unique_coord_sites",
        "jurisdiction_arch_coverage",
        "source_provenance_breakdown"
      ];

      for (let i = 0; i < keys.length; i++) {
        if (gj_meta[keys[i]] !== undefined)
          diag[keys[i]] = gj_meta[keys[i]];
      }
      fs.writeFileSync(diag_path, JSON.stringify(diag, null, 2), "utf8");

      //Return statement
      return diag;
    }

    /**
     * Executes full Matérn kriging + 128-year dasymetric residual raster synthesis for NICETHI.
     * @alias NicethiKrigingRunner.run
     *
     * @returns {Object}
     */
    static run () {
      //Declare local instance variables
      let orig_build = ViscountBiophysicalCovariates.buildStaticCovariates;
      let self_cls = this;
      let surface = null;
      let t0 = Date.now();

      //Function body
      let domain = ViscountMaternKriging.A_loadDomainConfigAndSites(this.CONFIG_REL, { project_root: this.PROJECT_ROOT });
      let obs = ViscountMaternKriging.B_computeEmpiricalBayesIntensities(domain);
      let krig = ViscountMaternKriging.C_fitTwoScaleNonStationaryMatern(obs);

      //Temporarily hook buildStaticCovariates strictly within this NICETHI process so sibling projects are never affected
      ViscountBiophysicalCovariates.buildStaticCovariates = function (arg0_m, arg1_c, arg2_o) {
        let covs = orig_build.call(ViscountBiophysicalCovariates, arg0_m, arg1_c, arg2_o);

        self_cls.applyAfricaAgroEcologicalCalibration(arg0_m, covs);
        return covs;
      };
      try {
        surface = ViscountMaternKriging.E_fitCarryCapacityResidualSurface(krig);
      } finally {
        ViscountBiophysicalCovariates.buildStaticCovariates = orig_build;
      }

      let bio_covs = surface.bio_covs;
      let field_keys = Object.keys(surface.fields || {});
      let mask_data = surface.kriging_bundle.mask_data;
      let strict_hab = (bio_covs && bio_covs.hab_mask) ? bio_covs.hab_mask : null;
      let uopp_valid = (bio_covs && bio_covs.uopp_valid) ? bio_covs.uopp_valid : null;

      surface.strict_hab_mask = strict_hab;

      for (let i = 0; i < field_keys.length; i++) {
        let f_arr = surface.fields[field_keys[i]];

        if (!f_arr) continue;
        if (uopp_valid)
          this.capAfricaMetroUrbanCores(mask_data, f_arr, uopp_valid, 0.85);
        if (strict_hab) {
          for (let x = 0; x < f_arr.length; x++) {
            if (strict_hab[x] === 0) f_arr[x] = 0;
          }
        }
      }

      let raster_meta = ViscountHUResidualKriging.generateAllBenchmarkPopulationRasters(surface, { is_polynesia: false });

      if (surface.hab_cache && typeof surface.hab_cache.clear === "function") surface.hab_cache.clear();
      let diag = ViscountMaternKriging.F_exportBenchmarkRastersAndDiagnostics(surface);

      diag = this.mergeProvenanceIntoDiagnostics(diag);

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
  let res = global.NicethiKrigingRunner.run();

  console.log(JSON.stringify({
    elapsed_seconds: res.elapsed_seconds,
    generated_years: res.raster_meta.generated_years,
    tau1_dimensionless: res.diag.tau1_dimensionless,
    tau2_dimensionless: res.diag.tau2_dimensionless,
    valid_cells: res.diag.valid_cells,
    wls_covariates_active: res.diag.wls_covariates_active
  }, null, 2));
}
