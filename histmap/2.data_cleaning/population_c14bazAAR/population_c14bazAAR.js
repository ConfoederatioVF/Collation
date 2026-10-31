//Initialise functions
{
  if (!global.population_c14bazAAR) global.population_c14bazAAR = {};

  if (typeof require !== "undefined") {
    let cur_dir = (typeof __dirname !== "undefined") ? __dirname : path.resolve(`${global.h2 || "./histmap/2.data_cleaning/"}/population_c14bazAAR/`);
    try {
      if (!global.population_c14bazAAR_watersheds && fs.existsSync(path.join(cur_dir, "c14_watersheds.js")))
        require(path.join(cur_dir, "c14_watersheds.js"));
    } catch (e) {
      console.warn(`[population_c14bazAAR] Failed to load companion modules:`, e);
    }
  }

  /**
   * Historical Demographics Pipeline based on c14bazAAR radiocarbon dates.
   * Calibrates radiocarbon samples via IntCal20/SHCal20, applies taphonomic loss correction,
   * bins Summed Probability Distributions (SPDs) into WMO watersheds (Kelly et al. 2025),
   * anchors to 1 AD actual population with HYDE 3.5 (ArchaeoGLOBE) fallback for sparse/zero basins,
   * models intra-watershed disaggregation weights via Weighted Least Squares (WLS) on HYDE land use covariates,
   * overlays Stadestér urban centres from 3000 BC onwards, and downscales dasymetrically.
   *
   * @class population_c14bazAAR
   */
  global.population_c14bazAAR = class {
    static bf = `${h2}/population_c14bazAAR/`;
    static raw_folder = `${h1}/population_c14bazAAR/`;
    static config_folder = `${this.bf}config/`;

    static input_archaeoglobe_csv = `${h1}/landuse_ArchaeoGLOBE/ARCHAEOGLOBE_CONSENSUS_ASSESSMENT.csv`;
    static input_archaeoglobe_folder = `${h1}/landuse_ArchaeoGLOBE/`;
    static input_archaeoglobe_meta = `${this.config_folder}archaeoglobe_metadata.json`;
    static input_archaeoglobe_watershed_fractions = `${this.config_folder}archaeoglobe_watershed_fractions.json`;
    static input_archaeoglobe_watershed_indicators = `${this.config_folder}archaeoglobe_watershed_indicators.json`;
    static input_archaeoglobe_watershed_map = `${this.config_folder}archaeoglobe_watershed_map.json`;
    static input_c14_csv = `${this.raw_folder}c14_cleaned_dedup.csv`;
    static input_c14_summary = `${this.config_folder}c14_dates_summary.json`;
    static input_hyde_landuse_folder = `${h2}/landuse_HYDE/rasters/`;
    static input_hyde_popc_folder = `${h2}/landuse_HYDE/rasters_scaled_to_global/`;
    static input_hyde_uopp_raster = `${h2}/landuse_HYDE/rasters/uopp_2023AD.png`;
    static input_intcal_json = `${this.config_folder}intcal20.json`;
    static input_kk10luh2_global_folder = `${h2}/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling/`;
    static input_land_area_raster = `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    static input_outlier_rasters = `${h3}/population_Substrata.outlier_removal/rasters_outliers/`;
    static input_shcal_json = `${this.config_folder}shcal20.json`;

    static input_stadester_population_folder = `${h2}/population_Stadester/stadester_population_rasters/`;
    static input_stadester_urban_folder = `${h2}/population_Stadester/stadester_urban_rasters/`;
    static input_wmobb_meta = `${this.config_folder}wmobb_metadata.json`;
    static input_wmobb_raster = `${this.config_folder}wmobb_raster.png`;

    static intermediate_spds_folder = `${this.bf}1.rasters_c14_watershed_spds/`;
    static intermediate_wls_folder = `${this.bf}2.rasters_c14_wls/`;
    static output_urban_folder = `${this.bf}3.rasters_urban/`;
    static output_rural_folder = `${this.bf}4.rasters_rural/`;
    static output_rasters_scaled_to_global = `${this.bf}5.rasters_scaled_to_global/`;
    static output_density_folder = `${this.bf}6.rasters_density/`;

    static base_year = 0; // 1 AD (astronomical year 0 / 1950 cal BP)
    static anchor_years = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0];
    static target_years = Array.from({ length: 101 }, (_, i) => -10000 + i*100);
    static urban_overlay_start_year = -3000; // 3000 BC

    /**
     * Identifies watersheds that intersect the glaciated outlier masks in population_Substrata.outlier_removal/rasters_outliers/.
     * @param {Object} [arg0_options]
     *
     * @returns {Set<string>} Set of watershed IDs subject to targeted glaciation correction.
     */
    static _getGlaciatedOutlierBasins (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Return statement
      return population_c14bazAAR_watersheds.getGlaciatedOutlierBasins(options);
    }


    /**
     * Computes and caches calibrated prehistoric date counts (cal_yr <= 100) and local millennial window counts
     * (|cal_yr - yr| <= 1000) per WMO watershed so sample-sparse basins and epochs smoothly fall back to HYDE.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} { n_local: Object, n_pre: Object }
     */
    static _getWatershedPrehistoricCounts (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Return statement
      return population_c14bazAAR_watersheds.getWatershedPrehistoricCounts(options);
    }


    /**
     * Inpaints buffered modern urban mask pixels via inverse-distance weighted boundary interpolation,
     * delegating to shared GeoPNG.inpaintUrbanMask.
     * @param {Float32Array} [arg0_raster_data] - Global float32 raster buffer.
     * @param {Uint8Array} [arg1_urban_mask] - Binary mask of modern urban pixels.
     * @param {Object} [arg2_options]
     *
     * @returns {Float32Array} Inpainted raster buffer.
     */
    static _inpaintModernUrbanMask (arg0_raster_data, arg1_urban_mask, arg2_options) {
      //Convert from parameters
      let raster_data = arg0_raster_data;
      let urban_mask = arg1_urban_mask;
      let options = (arg2_options) ? arg2_options : {};

      //Return statement
      return GeoPNG.inpaintUrbanMask(raster_data, urban_mask, options);
    }


    /**
     * Evaluates a piecewise cubic Hermite interpolating polynomial (PCHIP) at a target evaluation point,
     * ensuring strict monotonicity preservation without overshooting or negative oscillations.
     * @param {Array<number>} [arg0_x_pts] - Strict ascending order x-coordinates.
     * @param {Array<number>} [arg1_y_pts] - Corresponding y-coordinates.
     * @param {number} [arg2_x_eval] - Target evaluation point.
     *
     * @returns {number} Interpolated value.
     */
    static _interpolateMonotonicSpline (arg0_x_pts, arg1_y_pts, arg2_x_eval) {
      //Convert from parameters
      let x_pts = arg0_x_pts;
      let y_pts = arg1_y_pts;
      let x_eval = arg2_x_eval;

      //Return statement
      return population_c14bazAAR_watersheds.interpolateMonotonicSpline(x_pts, y_pts, x_eval);
    }


    /**
     * Ingests and verifies deduplicated radiocarbon dataset.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Summary metadata object.
     */
    static A_ingestC14Data (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let summary_obj = null;

      //Guard clauses
      if (!fs.existsSync(this.input_c14_csv)) {
        console.error(`- [population_c14bazAAR.A_ingestC14Data] Missing ${this.input_c14_csv}.`);
        return null;
      }

      if (fs.existsSync(this.input_c14_summary)) {
        summary_obj = JSON.parse(fs.readFileSync(this.input_c14_summary, "utf8"));
        console.log(`- Loaded c14bazAAR summary: ${summary_obj.total_dates} dates across ${summary_obj.total_basins} basins.`);
      }

      //Return statement
      return summary_obj;
    }


    /**
     * Calibrates radiocarbon determinations and computes Watershed Summed Probability Distributions (W-SPDs).
     * Incorporates site-phase grouping to remove excavation bias and taphonomic decay correction.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Map of watershed ID to year-probability distributions.
     */
    static B_calibrateAndComputeSPDs (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Return statement
      return population_c14bazAAR_watersheds.calibrateAndComputeSPDs(options);
    }


    /**
     * Calibrates radiocarbon SPD intensity against pre-normalised ArchaeoGLOBE priors and HYDE 3.5 empirical baselines,
     * applying smooth sample-sufficiency HYDE fallbacks when radiocarbon dates are sparse and anchoring smoothed SPDs
     * to late-prehistoric levels so steady hunter-gatherer watersheds are never crushed below HYDE.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Map of watershed ID to final antiquity population trajectories.
     */
    static C_anchorAndBackcalculate (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Return statement
      return population_c14bazAAR_watersheds.anchorAndBackcalculate(options);
    }


    /**
     * Fits Weighted Least Squares (WLS) models over HYDE land use covariates across all antiquity time slices,
     * masking modern cities (HYDE 2023 uopp > 10 km² + 1px buffer) with KK10LUH2 fallback,
     * estimating non-negative density coefficients to determine continuous intra-watershed disaggregation weights.
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<Object>} Map of target years to WLS model parameters and metrics.
     */
    static async D_fitWLSDisaggregation (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let all_models = {};
      let anchor_years = this.anchor_years;
      let glaciated_basins = this._getGlaciatedOutlierBasins(options);
      let keys = ["crop", "graz", "conv", "stadester_pop"];
      let land_area_raster = GeoPNG.loadNumberRasterImage(this.input_land_area_raster, { format: "int32" });
      let model_path = path.join(this.config_folder, "c14_wls_disaggregation_models.json");
      let rural_targets;
      let target_years = this.target_years;
      let total_pixels = 4320*2160;
      let uopp_raster = (fs.existsSync(this.input_hyde_uopp_raster)) ?
        GeoPNG.loadNumberRasterImage(this.input_hyde_uopp_raster, { format: "float32" }) : null;
      let urban_mask = new Uint8Array(total_pixels);
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });

      if (!fs.existsSync(this.intermediate_wls_folder))
        fs.mkdirSync(this.intermediate_wls_folder, { recursive: true });

      //Ensure rural targets exist or compute from watershed populations
      if (fs.existsSync(path.join(this.config_folder, "watershed_rural_targets.json"))) {
        rural_targets = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_rural_targets.json"), "utf8"));
      } else {
        let watershed_pops = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_populations.json"), "utf8"));
        rural_targets = {};
        for (let i = 0; i < target_years.length; i++) {
          let yr = target_years[i];
          rural_targets[yr] = {};
          let all_b = Object.keys(watershed_pops);
          for (let x = 0; x < all_b.length; x++)
            rural_targets[yr][all_b[x]] = watershed_pops[all_b[x]][yr] || 0;
        }
      }

      //Generate 1-pixel buffered modern urban mask via shared GeoPNG.getModernUrbanMask
      console.log("- Constructing 1px-buffered modern urban mask from HYDE 2023 uopp ...");
      urban_mask = GeoPNG.getModernUrbanMask(uopp_raster || this.input_hyde_uopp_raster, {
        buffer_radius: 1,
        threshold: 10.0
      });

      console.log("- Fitting Weighted Least Squares (WLS) disaggregation over HYDE land use covariates ...");

      for (let y = 0; y < anchor_years.length; y++) {
        let yr = anchor_years[y];
        let yr_name = landuse_HYDE._getHYDEYearName(yr);
        let out_weights_path = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);

        let cr_path = path.join(this.input_hyde_landuse_folder, `cropland${yr_name}.png`);
        let cv_path = path.join(this.input_hyde_landuse_folder, `conv_rangeland${yr_name}.png`);
        let gr_path = path.join(this.input_hyde_landuse_folder, `grazing${yr_name}.png`);
        let kk_path = path.join(this.input_kk10luh2_global_folder, `popc_${yr}.png`);
        let pop_path = path.join(this.input_stadester_population_folder, `stadester_population_${yr}.png`);
        let urb_path = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);
        let urbc_mcevedy_path = path.join(h2, "landuse_HYDE/rasters_mcevedy", `urbc_${yr}.png`);
        let urbc_raw_path = path.join(this.input_hyde_landuse_folder, `urbc_${yr_name}.png`);
        let urbc_mask_path = (fs.existsSync(urbc_mcevedy_path)) ? urbc_mcevedy_path : urbc_raw_path;
        let yr_urban_mask = GeoPNG.getModernUrbanMask(uopp_raster || this.input_hyde_uopp_raster, {
          buffer_radius: 1,
          threshold: 10.0,
          urbc_raster: urbc_mask_path
        });

        let cr = (fs.existsSync(cr_path)) ? GeoPNG.loadNumberRasterImage(cr_path, { format: "float32" }) : null;
        let cv = (fs.existsSync(cv_path)) ? GeoPNG.loadNumberRasterImage(cv_path, { format: "float32" }) : null;
        let gr = (fs.existsSync(gr_path)) ? GeoPNG.loadNumberRasterImage(gr_path, { format: "float32" }) : null;
        let kk = (fs.existsSync(kk_path)) ? GeoPNG.loadNumberRasterImage(kk_path, { format: "float32" }) : null;
        let pop = (fs.existsSync(pop_path)) ? GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" }) : null;
        let urb = (fs.existsSync(urb_path)) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;

        //Inpaint modern & HYDE urban sprawl pixels via boundary-constrained IDW interpolation
        if (pop)
          this._inpaintModernUrbanMask(pop.data, yr_urban_mask || urban_mask, {
            fallback_data: (kk) ? kk.data : null,
            land_area: land_area_raster.data,
            radius: 3
          });

        //Step 1: Aggregate basin-level sums of HYDE land use covariates and Stadestér rural population
        let basin_stats = {};
        for (let p = 0; p < total_pixels; p++) {
          let b = wmobb_raster.data[p];
          if (b > 0) {
            if (!basin_stats[b]) basin_stats[b] = { conv: 0, crop: 0, graz: 0, land: 0, stadester_pop: 0 };
            if (cr) basin_stats[b].crop += (cr.data[p] || 0);
            if (gr) basin_stats[b].graz += (gr.data[p] || 0);
            if (cv) basin_stats[b].conv += (cv.data[p] || 0);
            if (pop) {
              let a_val = land_area_raster.data[p] || 0;
              let u_val = (urb) ? (urb.data[p] || 0) : 0;
              let p_val = pop.data[p] || 0;
              //Subtract urban population to isolate rural component and avoid double counting urban pixels
              let rur_val = Math.max(0, p_val - u_val);
              if (yr < this.urban_overlay_start_year && a_val > 0 && glaciated_basins.has(String(b))) {
                let max_forager_density = (yr <= -5000) ? 0.05 : 0.20;
                rur_val = Math.min(rur_val, max_forager_density*a_val);
              }
              basin_stats[b].stadester_pop += rur_val;
            }
            basin_stats[b].land += (land_area_raster.data[p] || 0);
          }
        }

        //Step 2: Construct WLS matrices weighted by 1 / sqrt(land_area)
        let b_keys = Object.keys(basin_stats);
        let X = [];
        let Y = [];
        for (let i = 0; i < b_keys.length; i++) {
          let b = b_keys[i];
          let y_val = rural_targets[yr] ? (rural_targets[yr][b] || 0) : 0;
          let s = basin_stats[b];
          if (s.land > 0) {
            let w = 1.0/Math.sqrt(s.land);
            X.push([s.crop*w, s.graz*w, s.conv*w, s.stadester_pop*w]);
            Y.push([y_val*w]);
          }
        }

        //Step 3: Fit WLS regression
        let ols = await Statistics.trainOLSModel(null, { X, Y, keys }, { fit_intercept: false, lambda: 1e-4 });
        let beta_conv = Math.min(100, Math.max(0, ols?.coefficients?.conv || 0));
        let beta_crop = Math.min(500, Math.max(0, ols?.coefficients?.crop || 0));
        let beta_graz = Math.min(100, Math.max(0, ols?.coefficients?.graz || 0));
        let beta_sta = Math.min(10, Math.max(0, ols?.coefficients?.stadester_pop || 0));

        //Fallback guard if all coefficients are zero
        if (beta_crop + beta_graz + beta_conv + beta_sta === 0)
          beta_sta = 1.0;

        let coeffs = { conv: beta_conv, crop: beta_crop, graz: beta_graz, stadester_pop: beta_sta };
        all_models[yr] = { coefficients: coeffs, metrics: { rmse: ols?.metrics?.rmse } };

        console.log(`  [Year ${yr}] WLS Non-Negative Densities: Crop: ${beta_crop.toFixed(2)}/km² | Graz: ${beta_graz.toFixed(2)}/km² | Conv: ${beta_conv.toFixed(2)}/km² | Baseline: ${beta_sta.toFixed(4)} (RMSE: ${(ols?.metrics?.rmse || 0).toFixed(2)})`);

        //Step 4: Generate continuous intra-watershed disaggregation weights W(p)
        let weights_data = new Float32Array(total_pixels);
        for (let p = 0; p < total_pixels; p++) {
          let u_val = (urb) ? (urb.data[p] || 0) : 0;
          //Explicitly zero out rural disaggregation weights on urban pixels to guarantee no double counting
          if (u_val > 0) {
            weights_data[p] = 0;
            continue;
          }

          let c_val = (cr) ? (cr.data[p] || 0) : 0;
          let g_val = (gr) ? (gr.data[p] || 0) : 0;
          let v_val = (cv) ? (cv.data[p] || 0) : 0;
          let p_val = (pop) ? (pop.data[p] || 0) : 0;
          let s_val = Math.max(0, p_val - u_val);
          let b_id = String(wmobb_raster.data[p]);
          if (yr < this.urban_overlay_start_year && glaciated_basins.has(b_id)) {
            let a_val = land_area_raster.data[p] || 0;
            if (a_val > 0) {
              let max_forager_density = (yr <= -5000) ? 0.05 : 0.20;
              s_val = Math.min(s_val, max_forager_density*a_val);
            }
          }

          let w_pred = beta_crop*c_val + beta_graz*g_val + beta_conv*v_val + beta_sta*s_val;
          weights_data[p] = Math.max(0, w_pred);
        }

        GeoPNG.saveNumberRasterImage({ file_path: out_weights_path, format: "float32", function: function (idx) { return weights_data[idx]; }, height: 2160, width: 4320 });

        //Free memory
        cr = null; cv = null; gr = null; kk = null; pop = null; urb = null; weights_data = null;
        await new Promise((resolve) => setImmediate(resolve));
        if (typeof global.gc === "function") global.gc();
      }

      //Interpolate WLS weights linearly across intermediate 100-year intervals
      console.log("- Linearly interpolating continuous WLS weights across intermediate 100-year intervals ...");
      for (let a = 0; a < anchor_years.length - 1; a++) {
        let y0 = anchor_years[a], y1 = anchor_years[a + 1];
        let p0 = path.join(this.intermediate_wls_folder, `c14_wls_weights_${y0}.png`);
        let p1 = path.join(this.intermediate_wls_folder, `c14_wls_weights_${y1}.png`);
        let r0 = GeoPNG.loadNumberRasterImage(p0, { format: "float32" });
        let r1 = GeoPNG.loadNumberRasterImage(p1, { format: "float32" });

        for (let step = 1; step < 10; step++) {
          let yr = y0 + step*100, f = step/10.0, out_p = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);
          let inter_data = new Float32Array(total_pixels), u_p = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);
          let u_r = (fs.existsSync(u_p)) ? GeoPNG.loadNumberRasterImage(u_p, { format: "float32" }) : null;
          for (let p = 0; p < total_pixels; p++)
            inter_data[p] = (u_r && u_r.data[p] > 0) ? 0 : ((1 - f)*r0.data[p] + f*r1.data[p]);
          GeoPNG.saveNumberRasterImage({ file_path: out_p, format: "float32", function: (idx) => inter_data[idx], height: 2160, width: 4320 });
          inter_data = null; u_r = null;
        }
        r0 = null; r1 = null;
        await new Promise((resolve) => setImmediate(resolve));
        if (typeof global.gc === "function") global.gc();
      }

      fs.writeFileSync(model_path, JSON.stringify(all_models, null, 2));
      console.log(`- Saved WLS disaggregation weights to ${this.intermediate_wls_folder}.`);

      //Return statement
      return all_models;
    }


    /**
     * Overlays Stadestér historical urban populations from 3000 BC onwards.
     * Computes urban totals and balances rural residuals per watershed.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Map of target years to watershed rural allocations.
     */
    static E_integrateStadesterUrban (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let target_years = this.target_years;
      let urban_overlay_year = this.urban_overlay_start_year;
      let watershed_pops = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_populations.json"), "utf8"));
      let watershed_rurals = {};
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });

      if (!fs.existsSync(this.output_urban_folder))
        fs.mkdirSync(this.output_urban_folder, { recursive: true });

      console.log("- Processing Stadestér urban overlay from 3000 BC onwards ...");

      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        watershed_rurals[yr] = {};
        let urban_out_path = path.join(this.output_urban_folder, `urbc_${yr}.png`);

        if (yr < urban_overlay_year) {
          //Pre-3000 BC: Pure rural/forager regime (urbc = 0)
          GeoPNG.saveNumberRasterImage({ file_path: urban_out_path, format: "float32", function: function () { return 0; }, height: 2160, width: 4320 });

          //Target rural equals total watershed population
          let all_b = Object.keys(watershed_pops);
          for (let i = 0; i < all_b.length; i++)
            watershed_rurals[yr][all_b[i]] = watershed_pops[all_b[i]][yr];
        } else {
          //3000 BC Onwards: Ingest Stadestér urban ground truth or interpolate
          let src_urban_path = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);
          let urban_raster = (fs.existsSync(src_urban_path)) ?
            GeoPNG.loadNumberRasterImage(src_urban_path, { format: "float32" }) : null;

          if (urban_raster) {
            fs.copyFileSync(src_urban_path, urban_out_path);
          } else {
            //Interpolate urban raster between surrounding Stadestér anchors [-3000, -2000, -1000, 0]
            let u_anchors = [-3000, -2000, -1000, 0];
            let y0 = -3000, y1 = 0;
            for (let a = 0; a < u_anchors.length - 1; a++) {
              if (yr >= u_anchors[a] && yr <= u_anchors[a + 1]) {
                y0 = u_anchors[a]; y1 = u_anchors[a + 1]; break;
              }
            }
            let p0 = path.join(this.input_stadester_urban_folder, `stadester_urban_${y0}.png`);
            let p1 = path.join(this.input_stadester_urban_folder, `stadester_urban_${y1}.png`);
            let u0 = (fs.existsSync(p0)) ? GeoPNG.loadNumberRasterImage(p0, { format: "float32" }) : null;
            let u1 = (fs.existsSync(p1)) ? GeoPNG.loadNumberRasterImage(p1, { format: "float32" }) : null;
            if (u0 && u1) {
              let f = (yr - y0)/(y1 - y0);
              let u_data = new Float32Array(4320*2160);
              for (let p = 0; p < u_data.length; p++)
                u_data[p] = (1 - f)*u0.data[p] + f*u1.data[p];
              urban_raster = { data: u_data, height: 2160, width: 4320 };
              GeoPNG.saveNumberRasterImage({ file_path: urban_out_path, format: "float32", function: (idx) => u_data[idx], height: 2160, width: 4320 });
              u_data = null;
            } else {
              GeoPNG.saveNumberRasterImage({ file_path: urban_out_path, format: "float32", function: () => 0, height: 2160, width: 4320 });
            }
            u0 = null; u1 = null;
          }

          //Sum urban population per watershed
          let watershed_urbans = {};
          if (urban_raster)
            for (let p = 0; p < urban_raster.data.length; p++) {
              let b_id = String(wmobb_raster.data[p]);
              let u_val = urban_raster.data[p];
              if (u_val > 0)
                watershed_urbans[b_id] = (watershed_urbans[b_id] || 0) + u_val;
            }

          //Allocate rural residuals
          let all_b = Object.keys(watershed_pops);
          for (let i = 0; i < all_b.length; i++) {
            let b = all_b[i];
            let tot_pop = watershed_pops[b][yr] || 0;
            let urb_pop = watershed_urbans[b] || 0;

            if (urb_pop >= tot_pop && urb_pop > 0) {
              //Floor total watershed population to accommodate verified metropolis
              watershed_pops[b][yr] = urb_pop*1.05;
              watershed_rurals[yr][b] = urb_pop*0.05;
            } else {
              watershed_rurals[yr][b] = Math.max(0, tot_pop - urb_pop);
            }
          }
        }
      }

      fs.writeFileSync(path.join(this.config_folder, "watershed_rural_targets.json"), JSON.stringify(watershed_rurals, null, 2));

      //Return statement
      return watershed_rurals;
    }


    /**
     * Dasymetrically downscales rural population using WLS land use disaggregation weights
     * strictly conserving mass across each watershed boundary, and combines with Stadestér urban centres.
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<void>}
     */
    static async F_generateDownscaledRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let land_area_raster = GeoPNG.loadNumberRasterImage(this.input_land_area_raster, { format: "int32" });
      let target_years = this.target_years;
      let total_pixels = 4320*2160;
      let watershed_rurals = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_rural_targets.json"), "utf8"));
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });

      if (!fs.existsSync(this.output_rural_folder))
        fs.mkdirSync(this.output_rural_folder, { recursive: true });
      if (!fs.existsSync(this.output_rasters_scaled_to_global))
        fs.mkdirSync(this.output_rasters_scaled_to_global, { recursive: true });

      //Pre-index watershed pixel indices to ensure high-performance downscaling
      console.log("- Pre-indexing watershed pixel indices ...");
      let basin_pixels = {};
      for (let p = 0; p < total_pixels; p++) {
        let b = wmobb_raster.data[p];
        if (b > 0) {
          if (!basin_pixels[b]) basin_pixels[b] = [];
          basin_pixels[b].push(p);
        }
      }

      console.log("- Downscaling and generating final population rasters (popc, rurc, urbc) ...");

      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        let popc_out_path = path.join(this.output_rasters_scaled_to_global, `popc_${yr}.png`);
        let rurc_out_path = path.join(this.output_rural_folder, `rurc_${yr}.png`);
        let urbc_out_path = path.join(this.output_urban_folder, `urbc_${yr}.png`);
        let wls_path = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);

        let urban_raster = (fs.existsSync(urbc_out_path)) ?
          GeoPNG.loadNumberRasterImage(urbc_out_path, { format: "float32" }) : null;
        let wls_raster = (fs.existsSync(wls_path)) ?
          GeoPNG.loadNumberRasterImage(wls_path, { format: "float32" }) : null;

        let rurc_data = new Float32Array(total_pixels);
        let popc_data = new Float32Array(total_pixels);

        let all_basins = Object.keys(basin_pixels);
        for (let i = 0; i < all_basins.length; i++) {
          let b = all_basins[i];
          let pixels = basin_pixels[b];
          let target_rural = watershed_rurals[yr][b] || 0;

          if (target_rural <= 0) continue;

          //Sum WLS weights within this basin
          let weight_sum = 0;
          if (wls_raster)
            for (let k = 0; k < pixels.length; k++)
              weight_sum += wls_raster.data[pixels[k]];

          if (weight_sum > 0) {
            let factor = target_rural/weight_sum;
            for (let k = 0; k < pixels.length; k++) {
              let p_idx = pixels[k];
              rurc_data[p_idx] = wls_raster.data[p_idx]*factor;
            }
          } else {
            //Fallback to habitable land area if basin has zero WLS weight
            let area_sum = 0;
            for (let k = 0; k < pixels.length; k++) {
              let p_idx = pixels[k];
              if (!urban_raster || urban_raster.data[p_idx] <= 0)
                area_sum += Math.max(0, land_area_raster.data[pixels[k]] || 0);
            }

            if (area_sum > 0) {
              let factor = target_rural/area_sum;
              for (let k = 0; k < pixels.length; k++) {
                let p_idx = pixels[k];
                if (!urban_raster || urban_raster.data[p_idx] <= 0)
                  rurc_data[p_idx] = Math.max(0, land_area_raster.data[p_idx] || 0)*factor;
              }
            }
          }
        }

        //Combine Urban + Rural into Total popc
        for (let p = 0; p < total_pixels; p++) {
          let u_val = (urban_raster) ? urban_raster.data[p] : 0;
          let r_val = rurc_data[p];
          popc_data[p] = u_val + r_val;
        }

        //Save rurc and popc rasters in Big-endian float32 GeoPNG
        GeoPNG.saveNumberRasterImage({ file_path: rurc_out_path, format: "float32", function: function (idx) { return rurc_data[idx]; }, height: 2160, width: 4320 });
        GeoPNG.saveNumberRasterImage({ file_path: popc_out_path, format: "float32", function: function (idx) { return popc_data[idx]; }, height: 2160, width: 4320 });

        //Compute and save density raster
        if (!fs.existsSync(this.output_density_folder)) fs.mkdirSync(this.output_density_folder, { recursive: true });
        let popd_out_path = path.join(this.output_density_folder, `popd_${yr}.png`);
        let popd_data = new Float32Array(total_pixels);
        for (let p = 0; p < total_pixels; p++) {
          let a_val = land_area_raster.data[p] || 0;
          popd_data[p] = (a_val > 0) ? (popc_data[p]/a_val) : 0;
        }
        GeoPNG.saveNumberRasterImage({ file_path: popd_out_path, format: "float32", function: function (idx) { return popd_data[idx]; }, height: 2160, width: 4320 });

        let total_world_pop = 0;
        for (let p = 0; p < total_pixels; p++) total_world_pop += popc_data[p];
        if (yr % 500 === 0 || yr === 0)
          console.log(`- Year ${yr}: Total Population = ${Math.round(total_world_pop).toLocaleString()} (saved ${popc_out_path})`);

        //Free memory
        wls_raster = null;
        urban_raster = null;
        rurc_data = null;
        popc_data = null;
        popd_data = null;
        await new Promise((resolve) => setImmediate(resolve));
        if (typeof global.gc === "function") global.gc();
      }
    }


    /**
     * Validates output raster series for mass conservation and non-negativity.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Validation metrics report.
     */
    static G_validateOutputs (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let target_years = this.target_years;
      let validation_report = { years: {} };

      console.log("- Validating output rasters ...");
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        let pop_path = path.join(this.output_rasters_scaled_to_global, `popc_${yr}.png`);
        let rur_path = path.join(this.output_rural_folder, `rurc_${yr}.png`);
        let urb_path = path.join(this.output_urban_folder, `urbc_${yr}.png`);

        let pop_sum = GeoPNG.getImageSum(pop_path, { format: "float32" });
        let rur_sum = GeoPNG.getImageSum(rur_path, { format: "float32" });
        let urb_sum = GeoPNG.getImageSum(urb_path, { format: "float32" });

        let diff = Math.abs(pop_sum - (rur_sum + urb_sum));
        validation_report.years[yr] = { difference: diff, pop_total: Math.round(pop_sum), rural_total: Math.round(rur_sum), urban_total: Math.round(urb_sum) };
        if (yr % 1000 === 0 || yr === 0 || diff > 0.01)
          console.log(`  [Year ${yr}] Pop: ${Math.round(pop_sum).toLocaleString()} | Rural: ${Math.round(rur_sum).toLocaleString()} | Urban: ${Math.round(urb_sum).toLocaleString()} (Δ: ${diff.toFixed(4)})`);
      }

      fs.writeFileSync(path.join(this.config_folder, "validation_report.json"), JSON.stringify(validation_report, null, 2));

      //Return statement
      return validation_report;
    }


    /**
     * Executes the complete end-to-end population_c14bazAAR pipeline.
     * @param {Object} [arg0_options]
     *
     * @returns {Promise<void>}
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let start_time = Date.now();

      console.log("=== Starting population_c14bazAAR Pipeline Execution ===");
      this.A_ingestC14Data(options);
      this.B_calibrateAndComputeSPDs(options);
      this.C_anchorAndBackcalculate(options);
      this.E_integrateStadesterUrban(options);
      await this.D_fitWLSDisaggregation(options);
      await this.F_generateDownscaledRasters(options);
      this.G_validateOutputs(options);

      console.log(`=== Pipeline completed successfully in ${((Date.now() - start_time)/1000).toFixed(1)}s ===`);
    }
  };
}
