//Initialise functions
{
  if (!global.CounterfactualsEvaluator)
    /**
     * CounterfactualsEvaluator provides unified dataset extraction and out-of-sample
     * demographic evaluation for candidate counterfactual age/sex models.
     * Evaluates R^2(male), R^2(female), and Utility = [R^2(male) + R^2(female)]/2.
     *
     * @class CounterfactualsEvaluator
     */
    global.CounterfactualsEvaluator = class {
      /**
       * Calculates Pearson correlation coefficient between two numeric vectors.
       *
       * @param {Array<number>} arg0_x
       * @param {Array<number>} arg1_y
       *
       * @returns {number}
       */
      static calculatePearsonCorrelation (arg0_x, arg1_y) {
        //Convert from parameters
        let x = arg0_x;
        let y = arg1_y;

        //Declare local instance variables
        let denom_x = 0;
        let denom_y = 0;
        let n = x.length;
        let numerator = 0;
        let sum_x = 0;
        let sum_x_sq = 0;
        let sum_y = 0;
        let sum_y_sq = 0;
        let sum_xy = 0;

        //Guard clauses
        if (n === 0) return 0;

        for (let i = 0; i < n; i++) {
          sum_x += x[i];
          sum_y += y[i];
          sum_x_sq += x[i]*x[i];
          sum_y_sq += y[i]*y[i];
          sum_xy += x[i]*y[i];
        }

        numerator = n*sum_xy - sum_x*sum_y;
        denom_x = n*sum_x_sq - sum_x*sum_x;
        denom_y = n*sum_y_sq - sum_y*sum_y;

        if (denom_x <= 0 || denom_y <= 0) return 0;

        //Return statement
        return numerator/Math.sqrt(denom_x*denom_y);
      }

      /**
       * Calculates demographic R^2 between predicted and ground truth vectors.
       *
       * @param {Array<number>} arg0_y_pred
       * @param {Array<number>} arg1_y_true
       *
       * @returns {number}
       */
      static calculateR2 (arg0_y_pred, arg1_y_true) {
        //Convert from parameters
        let y_pred = arg0_y_pred;
        let y_true = arg1_y_true;

        //Declare local instance variables
        let mean_true = 0;
        let n = y_true.length;
        let ss_res = 0;
        let ss_tot = 0;
        let sum_true = 0;

        //Guard clauses
        if (n === 0) return 0;

        for (let i = 0; i < n; i++)
          sum_true += y_true[i];
        mean_true = sum_true/n;

        for (let i = 0; i < n; i++) {
          ss_tot += (y_true[i] - mean_true)*(y_true[i] - mean_true);
          ss_res += (y_true[i] - y_pred[i])*(y_true[i] - y_pred[i]);
        }

        //Return statement
        return (ss_tot > 0) ? (1 - ss_res/ss_tot) : 0;
      }

      /**
       * Evaluates multi-level demographic goodness-of-fit:
       * Separates male and female curves and computes:
       *   R^2(male), R^2(female), and Utility = [R^2(male) + R^2(female)]/2.
       *
       * @param {Array<Array<number>>} arg0_y_pred - Matrix of predicted proportions [N_samples x 36 cohorts].
       * @param {Array<Array<number>>} arg1_y_true - Matrix of ground truth proportions [N_samples x 36 cohorts].
       * @param {Array<string>} [arg2_cohorts] - Cohort identifiers (defaults to age_sex.getCohorts()).
       * @param {Array<string>} [arg3_country_labels] - Country geocodes for per-country analysis.
       *
       * @returns {Object} Comprehensive evaluation metrics.
       */
      static evaluateDemographicUtility (arg0_y_pred, arg1_y_true, arg2_cohorts, arg3_country_labels) {
        //Convert from parameters
        let y_pred = arg0_y_pred;
        let y_true = arg1_y_true;
        let cohorts = (arg2_cohorts) ? arg2_cohorts : ((global.age_sex) ? age_sex.getCohorts() : null);
        let country_labels = (arg3_country_labels) ? arg3_country_labels : [];

        //Declare local instance variables
        let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
        let country_female_r2 = [];
        let country_male_r2 = [];
        let country_pyramid_r2 = [];
        let country_utilities = [];
        let f_indices = [];
        let m_indices = [];
        let num_cohorts = 36;
        let num_samples = y_true.length;
        let per_country_table = [];
        let pred_female_flat = [];
        let pred_male_flat = [];
        let r2_female_pooled = 0;
        let r2_male_pooled = 0;
        let sum_abs_error = 0;
        let sum_sq_error = 0;
        let total_points = 0;
        let true_female_flat = [];
        let true_male_flat = [];

        //Guard clauses
        if (!cohorts) {
          cohorts = [];
          for (let i = 0; i < age_bands.length; i++) {
            cohorts.push(`f_${age_bands[i]}`);
            cohorts.push(`m_${age_bands[i]}`);
          }
        }
        num_cohorts = cohorts.length;

        for (let c = 0; c < num_cohorts; c++) {
          if (cohorts[c].startsWith("f_")) {
            f_indices.push(c);
          } else {
            m_indices.push(c);
          }
        }

        //Flatten predictions and actuals by sex
        for (let i = 0; i < num_samples; i++) {
          for (let k = 0; k < f_indices.length; k++) {
            let f_idx = f_indices[k];
            let pred_val = y_pred[i][f_idx];
            let true_val = y_true[i][f_idx];
            pred_female_flat.push(pred_val);
            true_female_flat.push(true_val);

            sum_abs_error += Math.abs(true_val - pred_val);
            sum_sq_error += (true_val - pred_val)*(true_val - pred_val);
          }

          for (let k = 0; k < m_indices.length; k++) {
            let m_idx = m_indices[k];
            let pred_val = y_pred[i][m_idx];
            let true_val = y_true[i][m_idx];
            pred_male_flat.push(pred_val);
            true_male_flat.push(true_val);

            sum_abs_error += Math.abs(true_val - pred_val);
            sum_sq_error += (true_val - pred_val)*(true_val - pred_val);
          }
        }

        total_points = num_samples*num_cohorts;
        r2_female_pooled = this.calculateR2(pred_female_flat, true_female_flat);
        r2_male_pooled = this.calculateR2(pred_male_flat, true_male_flat);

        //Compute per-country metrics
        for (let i = 0; i < num_samples; i++) {
          let label = (country_labels[i]) ? country_labels[i] : `Country_${i}`;
          let pred_f = f_indices.map(idx => y_pred[i][idx]);
          let pred_m = m_indices.map(idx => y_pred[i][idx]);
          let pred_tot = y_pred[i];
          let true_f = f_indices.map(idx => y_true[i][idx]);
          let true_m = m_indices.map(idx => y_true[i][idx]);
          let true_tot = y_true[i];

          let r2_c_f = this.calculateR2(pred_f, true_f);
          let r2_c_m = this.calculateR2(pred_m, true_m);
          let r2_c_tot = this.calculateR2(pred_tot, true_tot);
          let utility_c = (r2_c_m + r2_c_f)/2;
          let r_c = this.calculatePearsonCorrelation(pred_tot, true_tot);
          let mae_c = true_tot.reduce((acc, v, idx) => acc + Math.abs(v - pred_tot[idx]), 0)/num_cohorts;

          country_female_r2.push(r2_c_f);
          country_male_r2.push(r2_c_m);
          country_pyramid_r2.push(r2_c_tot);
          country_utilities.push(utility_c);

          per_country_table.push({
            country: label,
            mae_pct: (mae_c*100).toFixed(3) + "%",
            pearson_r: r_c.toFixed(4),
            pyramid_r2: (r2_c_tot*100).toFixed(2) + "%",
            r2_female: (r2_c_f*100).toFixed(2) + "%",
            r2_male: (r2_c_m*100).toFixed(2) + "%",
            utility: (utility_c*100).toFixed(2) + "%"
          });
        }

        let mean_country_f_r2 = (num_samples > 0) ? country_female_r2.reduce((a, b) => a + b, 0)/num_samples : 0;
        let mean_country_m_r2 = (num_samples > 0) ? country_male_r2.reduce((a, b) => a + b, 0)/num_samples : 0;
        let mean_country_pyramid_r2 = (num_samples > 0) ? country_pyramid_r2.reduce((a, b) => a + b, 0)/num_samples : 0;
        let mean_country_utility = (num_samples > 0) ? country_utilities.reduce((a, b) => a + b, 0)/num_samples : 0;
        let pooled_utility = (r2_male_pooled + r2_female_pooled)/2;

        //Return statement
        return {
          mae_pct: (total_points > 0) ? (sum_abs_error/total_points)*100 : 0,
          mean_country_female_r2: mean_country_f_r2,
          mean_country_male_r2: mean_country_m_r2,
          mean_country_pyramid_r2: mean_country_pyramid_r2,
          mean_country_utility: mean_country_utility,
          per_country_table: per_country_table,
          r2_female: r2_female_pooled,
          r2_male: r2_male_pooled,
          rmse_pct: (total_points > 0) ? Math.sqrt(sum_sq_error/total_points)*100 : 0,
          sample_count: num_samples,
          utility: pooled_utility
        };
      }

      /**
       * Loads historical HMD country data and extracts population-weighted country covariate vectors for a specific year.
       *
       * @param {number} arg0_year
       * @param {Object} [arg1_options]
       *
       * @returns {Object|null}
       */
      static loadHMDYear (arg0_year, arg1_options) {
        //Convert from parameters
        let year = arg0_year;
        let options = (arg1_options) ? arg1_options : {};

        //Declare local instance variables
        let cohorts = (global.age_sex) ? age_sex.getCohorts() : null;
        let colour_to_geocode = {};
        let country_covs = {};
        let country_pops = {};
        let cov_rasters = {};
        let geocode_obj = admin_modern.getHMDColourcodesObject();
        let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
        let key_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture"
        ];
        let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
        let raw_hmd_data = age_sex_HMD.A_getHMDObject();
        let stadester_raster = null;
        let total_pixels = 0;
        let training_covs = [...key_covs, "rel_pop_growth"];
        let X = [];
        let Y = [];

        //Guard clauses
        if (!fs.existsSync(pop_path)) return null;
        stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });
        if (!cohorts) {
          cohorts = [];
          let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
          for (let i = 0; i < age_bands.length; i++) {
            cohorts.push(`f_${age_bands[i]}`);
            cohorts.push(`m_${age_bands[i]}`);
          }
        }

        //Index geocodes
        Object.iterate(geocode_obj, (geocode, data) => {
          let in_domain = true;
          if (data.domain) {
            if (year < data.domain[0] || year > data.domain[1]) in_domain = false;
          }
          if (!in_domain) return;
          if (data.colours) {
            for (let i = 0; i < data.colours.length; i++) {
              let colour = data.colours[i];
              if (!colour_to_geocode[colour]) colour_to_geocode[colour] = [];
              colour_to_geocode[colour].push(geocode);
            }
          }
        });

        //Load covariate rasters
        for (let k = 0; k < key_covs.length; k++) {
          let entry = age_sex.covariates_obj[key_covs[k]](year);
          let fmt = Array.isArray(entry) ? entry[1] : "float32";
          let p = Array.isArray(entry) ? entry[0] : entry;
          if (fs.existsSync(p))
            cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
        }

        total_pixels = geocode_raster.data.length/4;
        for (let i = 0; i < total_pixels; i++) {
          let r = geocode_raster.data[i*4];
          let g = geocode_raster.data[i*4 + 1];
          let b = geocode_raster.data[i*4 + 2];
          let colour_str = `${r},${g},${b}`;
          let geocodes = colour_to_geocode[colour_str];
          if (!geocodes || geocodes.length === 0) continue;
          let country_code = geocodes[0];
          if (!raw_hmd_data[country_code] || !raw_hmd_data[country_code][String(year)]) continue;

          let pop = stadester_raster.data[i];
          if (pop <= 0 || isNaN(pop)) continue;

          if (!country_pops[country_code]) {
            country_pops[country_code] = 0;
            country_covs[country_code] = {};
            for (let k = 0; k < key_covs.length; k++)
              country_covs[country_code][key_covs[k]] = 0;
          }

          country_pops[country_code] += pop;
          for (let k = 0; k < key_covs.length; k++) {
            let c_name = key_covs[k];
            let val = cov_rasters[c_name] ? cov_rasters[c_name].data[i] : 0;
            if (!isNaN(val)) country_covs[country_code][c_name] += val*pop;
          }
        }

        let countries = Object.keys(country_pops).filter(c => country_pops[c] > 0);
        for (let c = 0; c < countries.length; c++) {
          let code = countries[c];
          let pop = country_pops[code];
          let x_row = key_covs.map(k => country_covs[code][k]/pop);
          let rel_growth = country_covs[code]["delta_popc_"]/pop;
          x_row.push(rel_growth);
          X.push(x_row);

          let t_entry = raw_hmd_data[code][String(year)];
          let counts = cohorts.map(k => t_entry[k] || 0);
          let tot = counts.reduce((a, b) => a + b, 0);
          Y.push(counts.map(v => (tot > 0 ? v/tot : 0)));
        }

        //Return statement
        return {
          cohorts: cohorts,
          countries: countries,
          covariates: training_covs,
          X: X,
          Y: Y,
          year: year
        };
      }

      /**
       * Loads global UNWPP 1950 ground truth across 144+ countries and extracts national covariate profiles.
       *
       * @param {Object} [arg0_options]
       *
       * @returns {Promise<Object>}
       */
      static async loadUNWPP1950 (arg0_options) {
        //Convert from parameters
        let options = (arg0_options) ? arg0_options : {};

        //Declare local instance variables
        let cohorts = (global.age_sex) ? age_sex.getCohorts() : null;
        let country_covs = {};
        let country_pops = {};
        let cov_rasters = {};
        let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
        let iso3_obj = admin_modern.getISO3ColourcodesObject();
        let key_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture"
        ];
        let pop_path = `${population_Stadester.input_popc_folder}stadester_population_1950.png`;
        let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });
        let total_pixels = geocode_raster.data.length/4;
        let training_covs = [...key_covs, "rel_pop_growth"];
        let unwpp_data = await age_sex_UNWPP.A_getUNWPPGroups();
        let X = [];
        let Y = [];

        if (!cohorts) {
          cohorts = [];
          let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
          for (let i = 0; i < age_bands.length; i++) {
            cohorts.push(`f_${age_bands[i]}`);
            cohorts.push(`m_${age_bands[i]}`);
          }
        }

        for (let k = 0; k < key_covs.length; k++) {
          let entry = age_sex.covariates_obj[key_covs[k]](1950);
          let fmt = Array.isArray(entry) ? entry[1] : "float32";
          let p = Array.isArray(entry) ? entry[0] : entry;
          if (fs.existsSync(p))
            cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
        }

        for (let i = 0; i < total_pixels; i++) {
          let r = geocode_raster.data[i*4];
          let g = geocode_raster.data[i*4 + 1];
          let b = geocode_raster.data[i*4 + 2];
          let colour_str = `${r},${g},${b}`;
          let iso_code = iso3_obj[colour_str];
          if (!iso_code || !unwpp_data[iso_code] || !unwpp_data[iso_code]["1950"]) continue;

          let pop = stadester_raster.data[i];
          if (pop <= 0 || isNaN(pop)) continue;

          if (!country_pops[iso_code]) {
            country_pops[iso_code] = 0;
            country_covs[iso_code] = {};
            for (let k = 0; k < key_covs.length; k++)
              country_covs[iso_code][key_covs[k]] = 0;
          }

          country_pops[iso_code] += pop;
          for (let k = 0; k < key_covs.length; k++) {
            let c_name = key_covs[k];
            let val = cov_rasters[c_name] ? cov_rasters[c_name].data[i] : 0;
            if (!isNaN(val)) country_covs[iso_code][c_name] += val*pop;
          }
        }

        let countries = Object.keys(country_pops).filter(c => country_pops[c] > 1e5 && unwpp_data[c] && unwpp_data[c]["1950"]);
        for (let i = 0; i < countries.length; i++) {
          let code = countries[i];
          let pop = country_pops[code];
          let x_row = key_covs.map(k => country_covs[code][k]/pop);
          let rel_growth = country_covs[code]["delta_popc_"]/pop;
          x_row.push(rel_growth);
          X.push(x_row);

          let counts = cohorts.map(k => unwpp_data[code]["1950"][k] || 0);
          let tot = counts.reduce((a, b) => a + b, 0);
          Y.push(counts.map(v => (tot > 0 ? v/tot : 0)));
        }

        let unwpp_obj = {
          cohorts: cohorts,
          countries: countries,
          covariates: training_covs,
          X: X,
          Y: Y,
          year: 1950
        };

        this._cached_unwpp_1950 = unwpp_obj;

        //Return statement
        return unwpp_obj;
      }

      /**
       * Assembles a structured out-of-sample benchmarking dataset:
       * Splits empirical data into training set (HMD historical anchors) and
       * out-of-sample test set (held-out nations in UNWPP 1950 and held-out HMD countries).
       *
       * @param {Object} [arg0_options]
       *
       * @returns {Promise<Object>}
       */
      static async getEvaluationDataset (arg0_options) {
        //Convert from parameters
        let options = (arg0_options) ? arg0_options : {};

        //Guard clauses
        if (this._cached_dataset && !options.refresh)
          return this._cached_dataset;

        //Declare local instance variables
        let anchor_years = [1850, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940];
        let test_countries = [];
        let test_x = [];
        let test_y = [];
        let train_countries = [];
        let train_x = [];
        let train_y = [];
        let unwpp_1950 = await this.loadUNWPP1950(options);

        //Load all available HMD anchor years
        for (let i = 0; i < anchor_years.length; i++) {
          let year_data = this.loadHMDYear(anchor_years[i]);
          if (!year_data) continue;

          for (let x = 0; x < year_data.countries.length; x++) {
            train_countries.push(`${year_data.countries[x]}_${anchor_years[i]}`);
            train_x.push(year_data.X[x]);
            train_y.push(year_data.Y[x]);
          }
        }

        //Hold out 1950 UNWPP countries as the primary out-of-sample evaluation pool
        for (let i = 0; i < unwpp_1950.countries.length; i++) {
          test_countries.push(unwpp_1950.countries[i]);
          test_x.push(unwpp_1950.X[i]);
          test_y.push(unwpp_1950.Y[i]);
        }

        let dataset = {
          cohorts: unwpp_1950.cohorts,
          covariates: unwpp_1950.covariates,
          test: {
            cohorts: unwpp_1950.cohorts,
            countries: test_countries,
            covariates: unwpp_1950.covariates,
            X: test_x,
            Y: test_y
          },
          train: {
            cohorts: unwpp_1950.cohorts,
            countries: train_countries,
            covariates: unwpp_1950.covariates,
            X: train_x,
            Y: train_y
          }
        };

        this._cached_dataset = dataset;

        //Return statement
        return dataset;
      }
    };
}
