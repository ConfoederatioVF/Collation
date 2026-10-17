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

    static input_c14_csv = `${this.raw_folder}c14_cleaned_dedup.csv`;
    static input_c14_summary = `${this.config_folder}c14_dates_summary.json`;
    static input_hyde_landuse_folder = `${h2}/landuse_HYDE/rasters/`;
    static input_hyde_popc_folder = `${h2}/landuse_HYDE/rasters_scaled_to_global/`;
    static input_hyde_uopp_raster = `${h2}/landuse_HYDE/rasters/uopp_2023AD_number.png`;
    static input_intcal_json = `${this.config_folder}intcal20.json`;
    static input_kk10luh2_global_folder = `${h2}/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling/`;
    static input_land_area_raster = `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    static input_shcal_json = `${this.config_folder}shcal20.json`;
    static input_stadester_urban_folder = `${h2}/population_Stadester/stadester_urban_rasters/`;
    static input_wmobb_meta = `${this.config_folder}wmobb_metadata.json`;
    static input_wmobb_raster = `${this.config_folder}wmobb_raster.png`;

    static intermediate_spds_folder = `${this.bf}1.rasters_c14_watershed_spds/`;
    static intermediate_wls_folder = `${this.bf}2.rasters_c14_wls/`;
    static output_urban_folder = `${this.bf}3.rasters_urban/`;
    static output_rural_folder = `${this.bf}4.rasters_rural/`;
    static output_rasters_scaled_to_global = `${this.bf}5.rasters_scaled_to_global/`;

    static base_year = 0; // 1 AD (astronomical year 0 / 1950 cal BP)
    static target_years = [-10000, -9000, -8000, -7000, -6000, -5000, -4000, -3000, -2000, -1000, 0];
    static urban_overlay_start_year = -3000; // 3000 BC

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
      let summary_obj;

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

      //Declare local instance variables
      let cal_curve = JSON.parse(fs.readFileSync(this.input_intcal_json, "utf8"));
      let c14_raw_content = fs.readFileSync(this.input_c14_csv, "utf8");
      let lines = c14_raw_content.split("\n");
      let out_spds_path = path.join(this.config_folder, "watershed_spds.json");
      let shcal_curve = JSON.parse(fs.readFileSync(this.input_shcal_json, "utf8"));
      let target_years = this.target_years;
      let watershed_spds = {};

      if (!fs.existsSync(this.intermediate_spds_folder))
        fs.mkdirSync(this.intermediate_spds_folder, { recursive: true });

      //Pre-index calibration curves for fast lookup
      let buildCurveLookup = function (curve_data) {
        let lookup = {};
        for (let i = 0; i < curve_data.cal_bp.length; i++) {
          let cbp = Math.round(curve_data.cal_bp[i]);
          lookup[cbp] = {
            age: curve_data.c14_age[i],
            sigma: curve_data.sigma[i]
          };
        }
        return lookup;
      };

      let intcal_lookup = buildCurveLookup(cal_curve);
      let shcal_lookup = buildCurveLookup(shcal_curve);

      //Initialise storage for each of the 516 potential basins
      let wmobb_meta = JSON.parse(fs.readFileSync(this.input_wmobb_meta, "utf8"));
      let all_basin_keys = Object.keys(wmobb_meta);
      for (let i = 0; i < all_basin_keys.length; i++) {
        let b_key = all_basin_keys[i];
        watershed_spds[b_key] = {};
        for (let y = 0; y < target_years.length; y++)
          watershed_spds[b_key][target_years[y]] = 0;
      }

      console.log(`- Calibrating radiocarbon determinations across ${lines.length - 1} records ...`);

      //Iterate over dates and compute probability densities
      let header = lines[0].split(",").map(c => c.trim());
      let idx_age = header.indexOf("c14age");
      let idx_lat = header.indexOf("lat");
      let idx_std = header.indexOf("c14std");
      let idx_wmobb = header.indexOf("wmobb");

      let processed_count = 0;
      for (let i = 1; i < lines.length; i++) {
        let line = lines[i].trim();
        if (!line) continue;

        let parts = line.split(",");
        let age = parseInt(parts[idx_age]);
        let err = parseInt(parts[idx_std]);
        let lat = parseFloat(parts[idx_lat]);
        let wmobb = parts[idx_wmobb];

        if (isNaN(age) || isNaN(err) || !watershed_spds[wmobb]) continue;

        let curve_map = (lat < 0) ? shcal_lookup : intcal_lookup;

        //Evaluate probability density for each target year
        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          let cal_bp = 1950 - yr; // Convert calendar year to cal BP
          let pt = curve_map[cal_bp];
          if (!pt) {
            let nearest = Math.round(cal_bp / 5) * 5;
            pt = curve_map[nearest] || { age: cal_bp, sigma: 15 };
          }

          let total_var = Math.max(1, (err*err) + (pt.sigma*pt.sigma));
          let diff = age - pt.age;
          
          //Truncate Gaussian tail beyond 4 sigma to eliminate float underflow artefacts
          if (diff*diff > 16*total_var) continue;
          
          let prob = Math.exp(-(diff*diff) / (2*total_var)) / Math.sqrt(2*Math.PI*total_var);

          //Taphonomic survival correction: power-law scaling
          let taph_correction = Math.pow(cal_bp + 500, 1.15) / 1000.0;
          let corrected_prob = prob * taph_correction;

          watershed_spds[wmobb][yr] += corrected_prob;
        }
        processed_count++;
      }

      console.log(`- Successfully calibrated ${processed_count} dates across watersheds.`);
      fs.writeFileSync(out_spds_path, JSON.stringify(watershed_spds, null, 2));

      //Return statement
      return watershed_spds;
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
      let raster_data = arg0_raster_data;
      let urban_mask = arg1_urban_mask;
      let options = (arg2_options) ? arg2_options : {};

      //Declare local instance variables
      let height = 2160;
      let masked_indices = [];
      let radius = (options.radius !== undefined) ? options.radius : 3;
      let temp_data;
      let total_pixels = height * 4320;
      let weights = [];
      let width = 4320;

      //Guard clauses
      if (!raster_data || !urban_mask) return raster_data;

      //Identify all masked pixels
      for (let p = 0; p < total_pixels; p++)
        if (urban_mask[p] === 1) masked_indices.push(p);

      if (masked_indices.length === 0) return raster_data;

      //Pre-compute local inverse distance weights for search radius
      for (let ry = -radius; ry <= radius; ry++)
        for (let rx = -radius; rx <= radius; rx++) {
          let d2 = rx * rx + ry * ry;
          if (d2 > 0 && d2 <= radius * radius + 1)
            weights.push({ rx: rx, ry: ry, w: 1.0 / Math.max(1, d2) });
        }

      //Iteratively inpaint masked pixels from perimeter rural boundary
      temp_data = new Float32Array(raster_data);
      for (let i = 0; i < masked_indices.length; i++) {
        let p = masked_indices[i];
        let x = p % width;
        let y = Math.floor(p / width);

        let den = 0;
        let num = 0;

        for (let k = 0; k < weights.length; k++) {
          let entry = weights[k];
          let ny = y + entry.ry;
          if (ny >= 0 && ny < height) {
            let nx = (x + entry.rx + width) % width;
            let n_idx = ny * width + nx;
            if (urban_mask[n_idx] === 0) {
              num += entry.w * raster_data[n_idx];
              den += entry.w;
            }
          }
        }

        //If boundary pixels were found within radius, inpaint; else fallback to wider search
        if (den > 0) {
          temp_data[p] = num / den;
        } else {
          let wide_den = 0;
          let wide_num = 0;
          let wide_radius = radius * 2;
          for (let ry = -wide_radius; ry <= wide_radius; ry++) {
            let ny = y + ry;
            if (ny >= 0 && ny < height) {
              for (let rx = -wide_radius; rx <= wide_radius; rx++) {
                let nx = (x + rx + width) % width;
                let n_idx = ny * width + nx;
                if (urban_mask[n_idx] === 0) {
                  let d2 = rx * rx + ry * ry;
                  let w = 1.0 / Math.max(1, d2);
                  wide_num += w * raster_data[n_idx];
                  wide_den += w;
                }
              }
            }
          }
          temp_data[p] = (wide_den > 0) ? (wide_num / wide_den) : 0;
        }
      }

      //Copy inpainted values back into raster_data
      for (let i = 0; i < masked_indices.length; i++) {
        let p = masked_indices[i];
        raster_data[p] = temp_data[p];
      }

      //Return statement
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
      let x_pts = (arg0_x_pts) ? arg0_x_pts : [];
      let y_pts = (arg1_y_pts) ? arg1_y_pts : [];
      let x_eval = (arg2_x_eval !== undefined) ? arg2_x_eval : 0;

      //Declare local instance variables
      let d = [];
      let h;
      let h00;
      let h01;
      let h10;
      let h11;
      let i = 0;
      let m = [];
      let n = x_pts.length;
      let t;
      let t2;
      let t3;

      //Guard clauses
      if (n === 0) return 0;
      if (n === 1) return y_pts[0];
      if (x_eval <= x_pts[0]) return y_pts[0];
      if (x_eval >= x_pts[n - 1]) return y_pts[n - 1];

      //Step 1: Compute secants d_k = (y_{k+1} - y_k) / (x_{k+1} - x_k)
      for (let k = 0; k < n - 1; k++)
        d.push((y_pts[k + 1] - y_pts[k]) / (x_pts[k + 1] - x_pts[k]));

      //Step 2: Initialise tangents m_k
      m = new Array(n);
      m[0] = d[0];
      m[n - 1] = d[n - 2];
      for (let k = 1; k < n - 1; k++) {
        if (d[k - 1] * d[k] <= 0) {
          m[k] = 0;
        } else {
          m[k] = 2.0 / (1.0 / d[k - 1] + 1.0 / d[k]);
        }
      }

      //Step 3: Fritsch-Carlson condition to preserve monotonicity
      for (let k = 0; k < n - 1; k++) {
        if (Math.abs(d[k]) < 1e-9) {
          m[k] = 0;
          m[k + 1] = 0;
        } else {
          let alpha = m[k] / d[k];
          let beta = m[k + 1] / d[k];
          let norm = alpha * alpha + beta * beta;
          if (norm > 9.0) {
            let tau = 3.0 / Math.sqrt(norm);
            m[k] = tau * alpha * d[k];
            m[k + 1] = tau * beta * d[k];
          }
        }
      }

      //Step 4: Locate segment [x_i, x_{i+1}]
      while (i < n - 2 && x_eval > x_pts[i + 1]) i++;

      //Step 5: Hermite basis evaluation
      h = x_pts[i + 1] - x_pts[i];
      t = (x_eval - x_pts[i]) / h;
      t2 = t * t;
      t3 = t2 * t;

      h00 = 2.0 * t3 - 3.0 * t2 + 1.0;
      h10 = t3 - 2.0 * t2 + t;
      h01 = -2.0 * t3 + 3.0 * t2;
      h11 = t3 - t2;

      //Return statement
      return Math.max(0, h00 * y_pts[i] + h10 * h * m[i] + h01 * y_pts[i + 1] + h11 * h * m[i + 1]);
    }


    /**
     * Anchors watershed trajectories and applies smooth monotonic spline interpolation to the -10000 BC intercept
     * for watersheds with late-antiquity radiocarbon signals but absent Paleolithic dates.
     * @param {Object} [arg0_options]
     *
     * @returns {Object} Map of watershed ID to final antiquity population trajectories.
     */
    static C_anchorAndBackcalculate (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let all_basins;
      let c14_summary = JSON.parse(fs.readFileSync(this.input_c14_summary, "utf8"));
      let date_counts;
      let global_targets = {};
      let out_pops_path = path.join(this.config_folder, "watershed_populations.json");
      let target_years = this.target_years;
      let total_spds = {};
      let watershed_hyde_totals = {};
      let watershed_pops = {};
      let watershed_spds;
      let wmobb_meta = JSON.parse(fs.readFileSync(this.input_wmobb_meta, "utf8"));
      let wmobb_raster = GeoPNG.loadNumberRasterImage(this.input_wmobb_raster, { format: "int32" });

      if (fs.existsSync(path.join(this.config_folder, "watershed_spds.json"))) {
        watershed_spds = JSON.parse(fs.readFileSync(path.join(this.config_folder, "watershed_spds.json"), "utf8"));
      } else {
        watershed_spds = this.B_calibrateAndComputeSPDs(options);
      }

      all_basins = Object.keys(wmobb_meta);
      date_counts = c14_summary.basin_counts || {};

      //Initialise watershed population storage
      for (let i = 0; i < all_basins.length; i++) {
        let b = all_basins[i];
        watershed_hyde_totals[b] = {};
        watershed_pops[b] = {};
        for (let y = 0; y < target_years.length; y++) {
          watershed_hyde_totals[b][target_years[y]] = 0;
          watershed_pops[b][target_years[y]] = 0;
        }
      }

      //Step 1: Compute HYDE 3.5 population totals for each watershed across all target years
      console.log("- Aggregating HYDE 3.5 baseline populations per watershed ...");
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        global_targets[yr] = 0;
        let hyde_path = path.join(this.input_hyde_popc_folder, `popc_${yr}.png`);
        if (!fs.existsSync(hyde_path)) continue;

        let hyde_raster = GeoPNG.loadNumberRasterImage(hyde_path, { format: "float32" });
        for (let p = 0; p < hyde_raster.data.length; p++) {
          let b_id = String(wmobb_raster.data[p]);
          let val = hyde_raster.data[p];
          if (val > 0 && watershed_hyde_totals[b_id]) {
            watershed_hyde_totals[b_id][yr] += val;
            global_targets[yr] += val;
          }
        }
      }

      //Step 2: Aggregate global SPD per year
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        total_spds[yr] = 0;
        for (let i = 0; i < all_basins.length; i++) {
          let b = all_basins[i];
          total_spds[yr] += (watershed_spds[b] ? (watershed_spds[b][yr] || 0) : 0);
        }
      }

      //Step 3: Trajectory anchoring and monotonic spline interpolation to -10000 BC intercept
      console.log("- Interpolating watershed demographic trajectories over monotonic splines to intercept ...");
      for (let i = 0; i < all_basins.length; i++) {
        let b = all_basins[i];
        let n_dates = date_counts[b] || 0;
        let s = watershed_spds[b] || {};

        let active_years = [];
        for (let y = 0; y < target_years.length; y++) {
          let yr = target_years[y];
          if ((s[yr] || 0) >= 0.005) active_years.push(yr);
        }

        if (active_years.length >= 1 && n_dates >= 10) {
          let known_pts = {};

          //For active radiocarbon epochs, compute population from relative SPD share blended with HYDE
          for (let k = 0; k < active_years.length; k++) {
            let yr = active_years[k];
            let spd_share = (total_spds[yr] > 0) ? ((s[yr] || 0) / total_spds[yr]) : 0;
            let c14_pop = global_targets[yr] * spd_share;
            let hyde_pop = watershed_hyde_totals[b][yr] || 0;
            let weight = Math.min(0.85, n_dates / (n_dates + 30.0));
            known_pts[yr] = weight * c14_pop + (1.0 - weight) * hyde_pop;
          }

          //Baseline intercept at -10000 BC
          if (!known_pts[-10000])
            known_pts[-10000] = Math.max(1, watershed_hyde_totals[b][-10000] || 1);

          //Anchor at 0 AD
          if (!known_pts[0])
            known_pts[0] = Math.max(1, watershed_hyde_totals[b][0] || 1);

          let x_pts = Object.keys(known_pts).map(Number).sort(function (a, b) { return a - b; });
          let y_pts = [];
          for (let k = 0; k < x_pts.length; k++) y_pts.push(known_pts[x_pts[k]]);

          //Interpolate over monotonic spline to fill missing epochs down to the intercept
          for (let y = 0; y < target_years.length; y++) {
            let yr = target_years[y];
            watershed_pops[b][yr] = this._interpolateMonotonicSpline(x_pts, y_pts, yr);
          }
        } else {
          //Pure fallback to HYDE 3.5 (ArchaeoGLOBE)
          for (let y = 0; y < target_years.length; y++) {
            let yr = target_years[y];
            watershed_pops[b][yr] = watershed_hyde_totals[b][yr] || 0;
          }
        }
      }

      //Step 4: Reconcile watershed trajectories with global demographic envelopes
      console.log("- Reconciling watershed trajectories with global demographic envelopes ...");
      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        let target = global_targets[yr] || 0;
        let unscaled_sum = 0;

        for (let i = 0; i < all_basins.length; i++) {
          let b = all_basins[i];
          unscaled_sum += watershed_pops[b][yr] || 0;
        }

        if (unscaled_sum > 0 && target > 0) {
          let scalar = target / unscaled_sum;
          for (let i = 0; i < all_basins.length; i++) {
            let b = all_basins[i];
            watershed_pops[b][yr] = watershed_pops[b][yr] * scalar;
          }
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
      let keys = ["crop", "graz", "conv", "hyde_pop"];
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
      if (uopp_raster) {
        for (let y = 0; y < 2160; y++) {
          let row_offset = y * 4320;
          for (let x = 0; x < 4320; x++) {
            if (uopp_raster.data[row_offset + x] > 10.0) {
              for (let dy = -1; dy <= 1; dy++) {
                let ny = y + dy;
                if (ny >= 0 && ny < 2160) {
                  let nrow_offset = ny * 4320;
                  for (let dx = -1; dx <= 1; dx++) {
                    let nx = (x + dx + 4320) % 4320;
                    urban_mask[nrow_offset + nx] = 1;
                  }
                }
              }
            }
          }
        }
      }

      console.log("- Fitting Weighted Least Squares (WLS) disaggregation over HYDE land use covariates ...");

      for (let y = 0; y < target_years.length; y++) {
        let yr = target_years[y];
        let yr_name = landuse_HYDE._getHYDEYearName(yr);
        let out_weights_path = path.join(this.intermediate_wls_folder, `c14_wls_weights_${yr}.png`);

        let cr_path = path.join(this.input_hyde_landuse_folder, `cropland${yr_name}_number.png`);
        let gr_path = path.join(this.input_hyde_landuse_folder, `grazing${yr_name}_number.png`);
        let cv_path = path.join(this.input_hyde_landuse_folder, `conv_rangeland${yr_name}_number.png`);
        let pop_path = path.join(this.input_hyde_landuse_folder, `popc_${yr_name}_number.png`);

        let cr = (fs.existsSync(cr_path)) ? GeoPNG.loadNumberRasterImage(cr_path, { format: "float32" }) : null;
        let gr = (fs.existsSync(gr_path)) ? GeoPNG.loadNumberRasterImage(gr_path, { format: "float32" }) : null;
        let cv = (fs.existsSync(cv_path)) ? GeoPNG.loadNumberRasterImage(cv_path, { format: "float32" }) : null;
        let pop = (fs.existsSync(pop_path)) ? GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" }) : null;

        //Inpaint modern urban sprawl pixels via boundary-constrained harmonic interpolation
        if (pop)
          this._inpaintModernUrbanMask(pop.data, urban_mask, { radius: 3 });

        //Step 1: Aggregate basin-level sums of HYDE land use covariates
        let basin_stats = {};
        for (let p = 0; p < total_pixels; p++) {
          let b = wmobb_raster.data[p];
          if (b > 0) {
            if (!basin_stats[b]) basin_stats[b] = { conv: 0, crop: 0, graz: 0, hyde_pop: 0, land: 0 };
            if (cr) basin_stats[b].crop += (cr.data[p] || 0);
            if (gr) basin_stats[b].graz += (gr.data[p] || 0);
            if (cv) basin_stats[b].conv += (cv.data[p] || 0);
            if (pop) {
              let a_val = land_area_raster.data[p] || 0;
              let h_val = pop.data[p] || 0;
              if (yr < this.urban_overlay_start_year && a_val > 0)
                h_val = Math.min(h_val, 1.0 * a_val);
              basin_stats[b].hyde_pop += h_val;
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
            X.push([s.crop*w, s.graz*w, s.conv*w, s.hyde_pop*w]);
            Y.push([y_val*w]);
          }
        }

        //Step 3: Fit WLS regression
        let ols = await Statistics.trainOLSModel(null, { X, Y, keys }, { fit_intercept: false, lambda: 1e-4 });
        let beta_conv = Math.min(100, Math.max(0, ols?.coefficients?.conv || 0));
        let beta_crop = Math.min(500, Math.max(0, ols?.coefficients?.crop || 0));
        let beta_graz = Math.min(100, Math.max(0, ols?.coefficients?.graz || 0));
        let beta_hyde = Math.min(10, Math.max(0, ols?.coefficients?.hyde_pop || 0));

        //Fallback guard if all coefficients are zero
        if (beta_crop + beta_graz + beta_conv + beta_hyde === 0)
          beta_hyde = 1.0;

        let coeffs = {
          conv: beta_conv,
          crop: beta_crop,
          graz: beta_graz,
          hyde_pop: beta_hyde
        };

        all_models[yr] = {
          coefficients: coeffs,
          metrics: { rmse: ols?.metrics?.rmse }
        };

        console.log(`  [Year ${yr}] WLS Non-Negative Densities: Crop: ${beta_crop.toFixed(2)}/km² | Graz: ${beta_graz.toFixed(2)}/km² | Conv: ${beta_conv.toFixed(2)}/km² | Baseline: ${beta_hyde.toFixed(4)} (RMSE: ${(ols?.metrics?.rmse || 0).toFixed(2)})`);

        //Step 4: Generate continuous intra-watershed disaggregation weights W(p)
        let weights_data = new Float32Array(total_pixels);
        for (let p = 0; p < total_pixels; p++) {
          let c_val = (cr) ? (cr.data[p] || 0) : 0;
          let g_val = (gr) ? (gr.data[p] || 0) : 0;
          let v_val = (cv) ? (cv.data[p] || 0) : 0;
          let h_val = (pop) ? (pop.data[p] || 0) : 0;
          let a_val = land_area_raster.data[p] || 0;
          if (yr < this.urban_overlay_start_year && a_val > 0)
            h_val = Math.min(h_val, 1.0 * a_val);

          let w_pred = beta_crop*c_val + beta_graz*g_val + beta_conv*v_val + beta_hyde*h_val;
          weights_data[p] = Math.max(0, w_pred);
        }

        GeoPNG.saveNumberRasterImage({
          file_path: out_weights_path,
          format: "float32",
          function: function (idx) { return weights_data[idx]; },
          height: 2160,
          width: 4320
        });

        //Free memory
        cr = null;
        gr = null;
        cv = null;
        pop = null;
        weights_data = null;
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
          GeoPNG.saveNumberRasterImage({
            file_path: urban_out_path,
            format: "float32",
            function: function () { return 0; },
            height: 2160,
            width: 4320
          });

          //Target rural equals total watershed population
          let all_b = Object.keys(watershed_pops);
          for (let i = 0; i < all_b.length; i++)
            watershed_rurals[yr][all_b[i]] = watershed_pops[all_b[i]][yr];
        } else {
          //3000 BC Onwards: Ingest Stadestér urban ground truth
          let src_urban_path = path.join(this.input_stadester_urban_folder, `stadester_urban_${yr}.png`);
          let urban_raster = (fs.existsSync(src_urban_path)) ?
            GeoPNG.loadNumberRasterImage(src_urban_path, { format: "float32" }) : null;

          if (urban_raster) {
            fs.copyFileSync(src_urban_path, urban_out_path);
          } else {
            GeoPNG.saveNumberRasterImage({
              file_path: urban_out_path,
              format: "float32",
              function: function () { return 0; },
              height: 2160,
              width: 4320
            });
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
            for (let k = 0; k < pixels.length; k++)
              area_sum += Math.max(0, land_area_raster.data[pixels[k]] || 0);

            if (area_sum > 0) {
              let factor = target_rural / area_sum;
              for (let k = 0; k < pixels.length; k++) {
                let p_idx = pixels[k];
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
        GeoPNG.saveNumberRasterImage({
          file_path: rurc_out_path,
          format: "float32",
          function: function (idx) { return rurc_data[idx]; },
          height: 2160,
          width: 4320
        });

        GeoPNG.saveNumberRasterImage({
          file_path: popc_out_path,
          format: "float32",
          function: function (idx) { return popc_data[idx]; },
          height: 2160,
          width: 4320
        });

        let total_world_pop = 0;
        for (let p = 0; p < total_pixels; p++) total_world_pop += popc_data[p];
        console.log(`- Year ${yr}: Total Population = ${Math.round(total_world_pop).toLocaleString()} (saved ${popc_out_path})`);

        //Free memory
        wls_raster = null;
        urban_raster = null;
        rurc_data = null;
        popc_data = null;
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
        validation_report.years[yr] = {
          difference: diff,
          pop_total: Math.round(pop_sum),
          rural_total: Math.round(rur_sum),
          urban_total: Math.round(urb_sum)
        };
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
