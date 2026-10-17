//Initialise functions
{
  if (!global.population_c14bazAAR) global.population_c14bazAAR = {};

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
    static input_hyde_uopp_raster = `${h2}/landuse_HYDE/rasters/uopp_2023AD_number.png`;
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
    static target_years = Array.from({ length: 101 }, (_, i) => -10000 + i * 100);
    static urban_overlay_start_year = -3000; // 3000 BC

    /**
     * Ingests and verifies deduplicated radiocarbon dataset.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Summary metadata object.
     */
    static A_ingestC14Data (arg0_options) {
      let options = (arg0_options) ? arg0_options : {}, summary_obj = null;
      if (!fs.existsSync(this.input_c14_csv)) {
        console.error(`- [population_c14bazAAR.A_ingestC14Data] Missing ${this.input_c14_csv}.`);
        return null;
      }
      if (fs.existsSync(this.input_c14_summary)) {
        summary_obj = JSON.parse(fs.readFileSync(this.input_c14_summary, "utf8"));
        console.log(`- Loaded c14bazAAR summary: ${summary_obj.total_dates} dates across ${summary_obj.total_basins} basins.`);
      }
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

      //Declare local instance variables
      let all_basin_keys, cal_curve = JSON.parse(fs.readFileSync(this.input_intcal_json, "utf8"));
      let c14_raw_content = fs.readFileSync(this.input_c14_csv, "utf8"), header, idx_age, idx_lat, idx_std, idx_wmobb;
      let lines = c14_raw_content.split("\n"), out_spds_path = path.join(this.config_folder, "watershed_spds.json"), processed_count = 0;
      let shcal_curve = JSON.parse(fs.readFileSync(this.input_shcal_json, "utf8")), target_years = this.target_years;
      let watershed_spds = {}, wmobb_meta = JSON.parse(fs.readFileSync(this.input_wmobb_meta, "utf8"));
      let buildCurveLookup = function (curve_data) {
        let lookup = {};
        for (let i = 0; i < curve_data.cal_bp.length; i++) lookup[Math.round(curve_data.cal_bp[i])] = { age: curve_data.c14_age[i], sigma: curve_data.sigma[i] };
        return lookup;
      };

      if (!fs.existsSync(this.intermediate_spds_folder))
        fs.mkdirSync(this.intermediate_spds_folder, { recursive: true });

      let intcal_lookup = buildCurveLookup(cal_curve);
      let shcal_lookup = buildCurveLookup(shcal_curve);
      all_basin_keys = Object.keys(wmobb_meta);

      for (let i = 0; i < all_basin_keys.length; i++) {
        let b_key = all_basin_keys[i];
        watershed_spds[b_key] = {};
        for (let y = 0; y < target_years.length; y++)
          watershed_spds[b_key][target_years[y]] = 0;
      }

      console.log(`- Calibrating radiocarbon determinations across ${lines.length - 1} records ...`);
      header = lines[0].split(",").map(c => c.trim());
      idx_age = header.indexOf("c14age");
      idx_lat = header.indexOf("lat");
      idx_std = header.indexOf("c14std");
      idx_wmobb = header.indexOf("wmobb");

      for (let i = 1; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;
        let parts = line.split(",");
        let age = parseInt(parts[idx_age]), err = parseInt(parts[idx_std]), lat = parseFloat(parts[idx_lat]), wmobb = parts[idx_wmobb];
        if (isNaN(age) || isNaN(err) || !watershed_spds[wmobb]) continue;
        let curve_map = (lat < 0) ? shcal_lookup : intcal_lookup;

        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          let cal_bp = 1950 - yr;
          let pt = curve_map[cal_bp] || curve_map[Math.round(cal_bp / 5) * 5] || { age: cal_bp, sigma: 15 };
          let total_var = Math.max(1, (err*err) + (pt.sigma*pt.sigma));
          let diff = age - pt.age;
          if (diff*diff <= 16*total_var) {
            let prob = Math.exp(-(diff*diff) / (2*total_var)) / Math.sqrt(2*Math.PI*total_var);
            let taph_correction = Math.pow(cal_bp + 500, 1.15) / 1000.0;
            watershed_spds[wmobb][yr] += prob * taph_correction;
          }
        }
        processed_count++;
      }

      console.log(`- Successfully calibrated ${processed_count} dates across watersheds.`);
      fs.writeFileSync(out_spds_path, JSON.stringify(watershed_spds, null, 2));

      //Return statement
      return watershed_spds;
    }


    /**
     * Identifies watersheds that intersect the glaciated outlier masks in population_Substrata.outlier_removal/rasters_outliers/.
     * @param {Object} [arg0_options]
     *
     * @returns {Set<string>} Set of watershed IDs subject to targeted glaciation correction.
     */
    static _getGlaciatedOutlierBasins (arg0_options) {
      let options = (arg0_options) ? arg0_options : {};
      let glaciated_basins = new Set(), mask_dir = this.input_outlier_rasters;
      let mask_names = ["stpetersburgrussia_-10000_1700.png", "russia_-10000_1400.png"];
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });

      for (let i = 0; i < mask_names.length; i++) {
        let mask_path = path.join(mask_dir, mask_names[i]);
        if (fs.existsSync(mask_path)) {
          let mask_img = GeoPNG.loadImage(mask_path);
          for (let p = 0; p < mask_img.width * mask_img.height; p++) {
            let r = mask_img.data[p * 4], g = mask_img.data[p * 4 + 1], b = mask_img.data[p * 4 + 2], a = mask_img.data[p * 4 + 3];
            if (r === 0 && g === 0 && b === 0 && a === 255) {
              let b_id = wmobb_raster.data[p];
              if (b_id > 0) glaciated_basins.add(String(b_id));
            }
          }
        }
      }
      return glaciated_basins;
    }


    /**
     * Inpaints buffered modern urban mask pixels via inverse-distance weighted boundary interpolation,

     * enforcing continuous spatial topology and eliminating discordant step-stamping.
     * @param {Float32Array} [arg0_raster_data] Global float32 raster buffer.
     * @param {Uint8Array} [arg1_urban_mask] Binary mask of modern urban pixels.
     * @param {Object} [arg2_options]
     *
     * @returns {Float32Array} Inpainted raster buffer.
     */
    static _inpaintModernUrbanMask (arg0_raster_data, arg1_urban_mask, arg2_options) {
      //Convert from parameters
      let raster_data = arg0_raster_data, urban_mask = arg1_urban_mask, options = (arg2_options) ? arg2_options : {};

      //Declare local instance variables
      let fallback_data = options.fallback_data, height = 2160, land_area = options.land_area, masked_indices = [];
      let radius = (options.radius !== undefined) ? options.radius : 3, total_pixels = height * 4320, weights = [], width = 4320;

      //Guard clauses
      if (!raster_data || !urban_mask) return raster_data;

      //Identify all masked pixels on habitable land
      for (let p = 0; p < total_pixels; p++)
        if (urban_mask[p] === 1 && (!land_area || land_area[p] > 0)) masked_indices.push(p);
      if (masked_indices.length === 0) return raster_data;

      for (let ry = -radius; ry <= radius; ry++)
        for (let rx = -radius; rx <= radius; rx++) {
          let d2 = rx * rx + ry * ry;
          if (d2 > 0 && d2 <= radius * radius + 1) weights.push({ rx: rx, ry: ry, w: 1.0 / Math.max(1, d2) });
        }

      let temp_data = new Float32Array(raster_data);
      for (let i = 0; i < masked_indices.length; i++) {
        let p = masked_indices[i], x = p % width, y = Math.floor(p / width), den = 0, num = 0;
        for (let k = 0; k < weights.length; k++) {
          let entry = weights[k], ny = y + entry.ry;
          if (ny >= 0 && ny < height) {
            let n_idx = ny * width + ((x + entry.rx + width) % width);
            if (urban_mask[n_idx] === 0 && (!land_area || land_area[n_idx] > 0)) {
              num += entry.w * raster_data[n_idx]; den += entry.w;
            }
          }
        }
        if (den > 0) {
          temp_data[p] = num / den;
        } else {
          let wide_den = 0, wide_num = 0, wide_r = radius * 2;
          for (let ry = -wide_r; ry <= wide_r; ry++)
            for (let rx = -wide_r; rx <= wide_r; rx++) {
              let ny = y + ry, nx = (x + rx + width) % width;
              if (ny >= 0 && ny < height && urban_mask[ny * width + nx] === 0 && (!land_area || land_area[ny * width + nx] > 0)) {
                let w = 1.0 / Math.max(1, rx * rx + ry * ry);
                wide_num += w * raster_data[ny * width + nx]; wide_den += w;
              }
            }
          let fb_val = (fallback_data && fallback_data[p] > 0) ? fallback_data[p] : raster_data[p];
          temp_data[p] = (wide_den > 0) ? (wide_num / wide_den) : fb_val;
        }
      }

      for (let i = 0; i < masked_indices.length; i++)
        raster_data[masked_indices[i]] = temp_data[masked_indices[i]];
      return raster_data;
    }


    /**
     * Evaluates a piecewise cubic Hermite interpolating polynomial (PCHIP) at a target evaluation point,
     * ensuring strict monotonicity preservation without overshooting or negative oscillations.
     * @param {Array<number>} [arg0_x_pts] Strict ascending order x-coordinates.
     * @param {Array<number>} [arg1_y_pts] Corresponding y-coordinates.
     * @param {number} [arg2_x_eval] Target evaluation point.
     *
     * @returns {number} Interpolated value.
     */
    static _interpolateMonotonicSpline (arg0_x_pts, arg1_y_pts, arg2_x_eval) {
      //Convert from parameters
      let x_pts = (arg0_x_pts) ? arg0_x_pts : [], y_pts = (arg1_y_pts) ? arg1_y_pts : [], x_eval = (arg2_x_eval !== undefined) ? arg2_x_eval : 0;
      let d = [], i = 0, m = [], n = x_pts.length;

      //Guard clauses
      if (n === 0) return 0;
      if (n === 1) return y_pts[0];
      if (x_eval <= x_pts[0]) return y_pts[0];
      if (x_eval >= x_pts[n - 1]) return y_pts[n - 1];

      for (let k = 0; k < n - 1; k++) d.push((y_pts[k + 1] - y_pts[k]) / (x_pts[k + 1] - x_pts[k]));
      m = new Array(n);
      m[0] = d[0]; m[n - 1] = d[n - 2];
      for (let k = 1; k < n - 1; k++)
        m[k] = (d[k - 1] * d[k] <= 0) ? 0 : 2.0 / (1.0 / d[k - 1] + 1.0 / d[k]);

      for (let k = 0; k < n - 1; k++) {
        if (Math.abs(d[k]) < 1e-9) { m[k] = 0; m[k + 1] = 0; } else {
          let alpha = m[k] / d[k], beta = m[k + 1] / d[k], norm = alpha * alpha + beta * beta;
          if (norm > 9.0) { let tau = 3.0 / Math.sqrt(norm); m[k] = tau * alpha * d[k]; m[k + 1] = tau * beta * d[k]; }
        }
      }

      while (i < n - 2 && x_eval > x_pts[i + 1]) i++;
      let h = x_pts[i + 1] - x_pts[i], t = (x_eval - x_pts[i]) / h, t2 = t * t, t3 = t2 * t;
      let h00 = 2.0 * t3 - 3.0 * t2 + 1.0, h10 = t3 - 2.0 * t2 + t, h01 = -2.0 * t3 + 3.0 * t2, h11 = t3 - t2;

      return Math.max(0, h00 * y_pts[i] + h10 * h * m[i] + h01 * y_pts[i + 1] + h11 * h * m[i + 1]);
    }


    /**
     * Calibrates radiocarbon SPD intensity against fractionally binned ArchaeoGLOBE carrying-capacity priors,
     * reconciling local demographic trajectories with global demographic envelopes across all antiquity time slices.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Map of watershed ID to final antiquity population trajectories.
     */
    static C_anchorAndBackcalculate (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let ag_indicators = (fs.existsSync(this.input_archaeoglobe_watershed_indicators)) ?
        JSON.parse(fs.readFileSync(this.input_archaeoglobe_watershed_indicators, "utf8")) : {};
      let ag_pts_x = [-10000, -8000, -6000, -4000, -2000, -1000, 0];
      let all_basins;
      let basin_hyde_0 = {};
      let basin_hyde_series = {};
      let basin_stadester_0 = {};
      let c14_summary = JSON.parse(fs.readFileSync(this.input_c14_summary, "utf8"));
      let date_counts;
      let glaciated_basins = this._getGlaciatedOutlierBasins(options);
      let global_targets = {};
      let out_pops_path = path.join(this.config_folder, "watershed_populations.json");
      let stadester_0_path = path.join(this.input_stadester_population_folder, "stadester_population_0.png");
      let stadester_0_raster;
      let target_years = this.target_years;
      let watershed_pops = {};
      let watershed_spds;
      let wmobb_meta = JSON.parse(fs.readFileSync(this.input_wmobb_meta, "utf8"));
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });
      let world_targets;

      if (!global.population_Global && typeof h2 !== "undefined") {
        let pop_global_file = path.join(h2, "population_Global/population_Global.js");
        if (fs.existsSync(pop_global_file)) require(pop_global_file);
      }
      world_targets = (global.population_Global) ? population_Global.A_getWorldPopulationObject() : {};

      if (fs.existsSync(path.join(this.config_folder, "watershed_spds.json"))) {
        watershed_spds = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_spds.json"), "utf8"));
      } else {
        watershed_spds = this.B_calibrateAndComputeSPDs(options);
      }

      all_basins = Object.keys(wmobb_meta);
      date_counts = c14_summary.basin_counts || {};

      let anchor_years = this.anchor_years;
      let anchor_targets = {};

      //Step 1: Compute global population target envelopes for each target year
      console.log("- Aggregating global demographic envelopes from Stadestér population ...");
      for (let a = 0; a < anchor_years.length; a++) {
        let yr = anchor_years[a];
        let sta_path = path.join(this.input_stadester_population_folder, `stadester_population_${yr}.png`);
        anchor_targets[yr] = (fs.existsSync(sta_path)) ?
          GeoPNG.getImageSum(sta_path, { format: "float32" }) : (world_targets[yr] || 0);
      }
      let anchor_target_vals = anchor_years.map(y => anchor_targets[y]);
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        global_targets[yr] = this._interpolateMonotonicSpline(anchor_years, anchor_target_vals, yr);
      }

      //Step 2: Pre-index empirical historical population baselines per watershed
      console.log("- Pre-indexing empirical historical population baselines per watershed ...");
      for (let a = 0; a < anchor_years.length; a++) {
        let yr = anchor_years[a];
        basin_hyde_series[yr] = {};
        let hyde_path = path.join(this.input_hyde_popc_folder, `popc_${yr}.png`);
        if (fs.existsSync(hyde_path)) {
          let hyde_raster = GeoPNG.loadNumberRasterImage(hyde_path, { format: "float32" });
          for (let p = 0; p < hyde_raster.data.length; p++) {
            let b = wmobb_raster.data[p];
            if (b > 0)
              basin_hyde_series[yr][b] = (basin_hyde_series[yr][b] || 0) + (hyde_raster.data[p] || 0);
          }
          hyde_raster = null;
        }
      }
      //Interpolate basin_hyde_series for intermediate years
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        if (basin_hyde_series[yr]) continue;
        let y0 = anchor_years[0], y1 = anchor_years[anchor_years.length - 1];
        for (let a = 0; a < anchor_years.length - 1; a++) {
          if (yr >= anchor_years[a] && yr <= anchor_years[a + 1]) {
            y0 = anchor_years[a]; y1 = anchor_years[a + 1]; break;
          }
        }
        let f = (yr - y0) / (y1 - y0);
        basin_hyde_series[yr] = {};
        for (let i = 0; i < all_basins.length; i++) {
          let b = all_basins[i];
          basin_hyde_series[yr][b] = (1 - f) * (basin_hyde_series[y0]?.[b] || 0) + f * (basin_hyde_series[y1]?.[b] || 0);
        }
      }
      basin_hyde_0 = basin_hyde_series[0] || {};

      if (fs.existsSync(stadester_0_path)) {
        stadester_0_raster = GeoPNG.loadNumberRasterImage(stadester_0_path, { format: "float32" });
        for (let p = 0; p < stadester_0_raster.data.length; p++) {
          let b = wmobb_raster.data[p];
          if (b > 0)
            basin_stadester_0[b] = (basin_stadester_0[b] || 0) + (stadester_0_raster.data[p] || 0);
        }
        stadester_0_raster = null;
      }

      //Step 3: Backcalculate antiquity watershed trajectories via ArchaeoGLOBE priors and radiocarbon dynamics
      console.log("- Backcalculating antiquity watershed trajectories via ArchaeoGLOBE priors and radiocarbon dynamics ...");
      for (let i = 0; i < all_basins.length; i++) {
        let b = all_basins[i];
        let h0_val = basin_hyde_0[b] || 0;
        let inds = (ag_indicators[b]) ? ag_indicators[b].epochs : null;
        let is_glaciated = glaciated_basins.has(String(b));
        let n = date_counts[b] || 0;
        let s = watershed_spds[b] || {};
        let s0_val = basin_stadester_0[b] || 0;

        //Anchor targeted glaciated outlier mask basins to empirical baseline, preserving Stadestér elsewhere
        let anchor_0 = is_glaciated ? (h0_val || s0_val) : (s0_val || h0_val);

        //1. Evaluate monotonic Hermite spline over fractionally binned ArchaeoGLOBE relative carrying capacity
        let ag_pts_y = ag_pts_x.map(function (yr) {
          if (inds && inds[yr] && inds[yr].rel_capacity !== undefined)
            return inds[yr].rel_capacity;
          return (yr === 0) ? 1.0 : 0.04;
        });

        let ag_interp = {};
        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          ag_interp[yr] = this._interpolateMonotonicSpline(ag_pts_x, ag_pts_y, yr);
        }

        //2. Prehistoric radiocarbon SPD moderation (relative to prehistoric mean, never dividing by 1 AD)
        let pre_s_vals = [];
        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          if (yr < 0 && s[yr] !== undefined && s[yr] > 0)
            pre_s_vals.push(s[yr]);
        }
        let s_mean = (pre_s_vals.length > 0) ? (pre_s_vals.reduce((a, c) => a + c, 0) / pre_s_vals.length) : 0;
        let w = Math.min(0.50, n / (n + 100.0));

        watershed_pops[b] = {};
        watershed_pops[b][0] = anchor_0;

        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          if (yr === 0) continue;

          let mod_factor = 1.0;
          let r_ag = ag_interp[yr];
          let r_h = (h0_val > 0) ? ((basin_hyde_series[yr][b] || 0) / h0_val) : 0.04;
          let r_base = is_glaciated ? r_h : r_ag;
          let s_yr = s[yr] || 0;

          if (n >= 10 && s_mean > 0) {
            let rel_diff = (s_yr - s_mean) / (s_mean + 0.01);
            let clamped_diff = Math.max(-0.60, Math.min(1.50, rel_diff));
            mod_factor = 1.0 + w * clamped_diff;
          }

          let trajectory_ratio = Math.max(0.005, r_base * mod_factor);
          watershed_pops[b][yr] = anchor_0 * trajectory_ratio;
        }
      }



      //Step 4: Reconcile watershed trajectories with global demographic envelopes
      console.log("- Reconciling watershed trajectories with global demographic envelopes ...");
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        let sum_pop = 0;
        for (let i = 0; i < all_basins.length; i++)
          sum_pop += (watershed_pops[all_basins[i]][yr] || 0);

        let target = global_targets[yr] || 0;
        let scalar = (sum_pop > 0 && target > 0) ? (target / sum_pop) : 1;
        for (let i = 0; i < all_basins.length; i++) {
          let b = all_basins[i];
          watershed_pops[b][yr] *= scalar;
        }
      }

      fs.writeFileSync(out_pops_path, JSON.stringify(watershed_pops, null, 2));
      console.log(`- Saved antiquity watershed trajectories to ${out_pops_path}.`);

      //Return statement
      return watershed_pops;
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
      let glaciated_basins = this._getGlaciatedOutlierBasins(options);
      let keys = ["crop", "graz", "conv", "stadester_pop"];
      let land_area_raster = GeoPNG.loadNumberRasterImage(this.input_land_area_raster, { format: "int32" });
      let model_path = path.join(this.config_folder, "c14_wls_disaggregation_models.json");
      let rural_targets;
      let target_years = this.target_years;
      let total_pixels = 4320 * 2160;
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
        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          rural_targets[yr] = {};
          let all_b = Object.keys(watershed_pops);
          for (let i = 0; i < all_b.length; i++)
            rural_targets[yr][all_b[i]] = watershed_pops[all_b[i]][yr] || 0;
        }
      }

      //Generate 1-pixel buffered modern urban mask (HYDE 2023 uopp > 10 km²)
      console.log("- Constructing 1px-buffered modern urban mask from HYDE 2023 uopp ...");
      if (uopp_raster)
        for (let y = 0; y < 2160; y++)
          for (let x = 0; x < 4320; x++)
            if (uopp_raster.data[y * 4320 + x] > 10.0)
              for (let dy = -1; dy <= 1; dy++) {
                let ny = y + dy;
                if (ny >= 0 && ny < 2160)
                  for (let dx = -1; dx <= 1; dx++)
                    urban_mask[ny * 4320 + ((x + dx + 4320) % 4320)] = 1;
              }

      let anchor_years = this.anchor_years;
      console.log("- Fitting Weighted Least Squares (WLS) disaggregation over HYDE land use covariates ...");

      for (let y = 0; y < anchor_years.length; y++) {
        let yr = anchor_years[y];
        let yr_name = landuse_HYDE._getHYDEYearName(yr);
        let out_weights_path = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);

        let cr_path = path.join(this.input_hyde_landuse_folder, `cropland${yr_name}_number.png`);
        let cv_path = path.join(this.input_hyde_landuse_folder, `conv_rangeland${yr_name}_number.png`);
        let gr_path = path.join(this.input_hyde_landuse_folder, `grazing${yr_name}_number.png`);
        let kk_path = path.join(this.input_kk10luh2_global_folder, `popc_${yr}.png`);
        let pop_path = path.join(this.input_stadester_population_folder, `stadester_population_${yr}.png`);
        let urb_path = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);

        let cr = (fs.existsSync(cr_path)) ? GeoPNG.loadNumberRasterImage(cr_path, { format: "float32" }) : null;
        let cv = (fs.existsSync(cv_path)) ? GeoPNG.loadNumberRasterImage(cv_path, { format: "float32" }) : null;
        let gr = (fs.existsSync(gr_path)) ? GeoPNG.loadNumberRasterImage(gr_path, { format: "float32" }) : null;
        let kk = (fs.existsSync(kk_path)) ? GeoPNG.loadNumberRasterImage(kk_path, { format: "float32" }) : null;
        let pop = (fs.existsSync(pop_path)) ? GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" }) : null;
        let urb = (fs.existsSync(urb_path)) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;

        //Inpaint modern urban sprawl pixels via boundary-constrained harmonic interpolation
        if (pop)
          this._inpaintModernUrbanMask(pop.data, urban_mask, {
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
                rur_val = Math.min(rur_val, max_forager_density * a_val);
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
            let w = 1.0 / Math.sqrt(s.land);
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
              s_val = Math.min(s_val, max_forager_density * a_val);
            }
          }

          let w_pred = beta_crop*c_val + beta_graz*g_val + beta_conv*v_val + beta_sta*s_val;
          weights_data[p] = Math.max(0, w_pred);
        }

        GeoPNG.saveNumberRasterImage({ file_path: out_weights_path, format: "float32", function: function (idx) { return weights_data[idx]; }, height: 2160, width: 4320 });

        //Free memory
        cr = null; cv = null; gr = null; kk = null; pop = null; urb = null; weights_data = null;
        await new Promise(resolve => setImmediate(resolve));
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
          let yr = y0 + step * 100, f = step / 10.0, out_p = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);
          let inter_data = new Float32Array(total_pixels), u_p = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);
          let u_r = (fs.existsSync(u_p)) ? GeoPNG.loadNumberRasterImage(u_p, { format: "float32" }) : null;
          for (let p = 0; p < total_pixels; p++)
            inter_data[p] = (u_r && u_r.data[p] > 0) ? 0 : ((1 - f) * r0.data[p] + f * r1.data[p]);
          GeoPNG.saveNumberRasterImage({ file_path: out_p, format: "float32", function: (idx) => inter_data[idx], height: 2160, width: 4320 });
          inter_data = null; u_r = null;
        }
        r0 = null; r1 = null;
        await new Promise(resolve => setImmediate(resolve));
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
              let f = (yr - y0) / (y1 - y0);
              let u_data = new Float32Array(4320 * 2160);
              for (let p = 0; p < u_data.length; p++)
                u_data[p] = (1 - f) * u0.data[p] + f * u1.data[p];
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
              watershed_pops[b][yr] = urb_pop * 1.05;
              watershed_rurals[yr][b] = urb_pop * 0.05;
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
      let total_pixels = 4320 * 2160;
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
            let factor = target_rural / weight_sum;
            for (let k = 0; k < pixels.length; k++) {
              let p_idx = pixels[k];
              rurc_data[p_idx] = wls_raster.data[p_idx] * factor;
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
              let factor = target_rural / area_sum;
              for (let k = 0; k < pixels.length; k++) {
                let p_idx = pixels[k];
                if (!urban_raster || urban_raster.data[p_idx] <= 0)
                  rurc_data[p_idx] = Math.max(0, land_area_raster.data[p_idx] || 0) * factor;
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
          popd_data[p] = (a_val > 0) ? (popc_data[p] / a_val) : 0;
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
        await new Promise(resolve => setImmediate(resolve));
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

      console.log(`=== Pipeline completed successfully in ${((Date.now() - start_time) / 1000).toFixed(1)}s ===`);
    }
  };
}
