//Initialise functions
{
  if (!global.BrassLogitLifeTables)
    /**
     * BrassLogitLifeTables implements William Brass's Relational Logit Model (1971):
     * logit(l_x) = alpha + beta * logit(l_x_standard)
     * where logit(p) = 0.5 * ln((1 - p)/p).
     * alpha governs overall level of mortality, beta governs the relationship between adult and child mortality.
     * Loads standard life tables directly from source CSV (brass_standard_life_table.csv).
     *
     * @class BrassLogitLifeTables
     */
    global.BrassLogitLifeTables = class {
      static key = "brass_logit_life_tables";
      static name = "Brass-Logit Model Life Tables";
      static family = "Life Tables";
      static source_csv_path = path.join(__dirname, "brass_standard_life_table.csv");

      /**
       * Returns canonical cohort list.
       *
       * @returns {Array<string>}
       */
      static getCohorts () {
        //Declare local instance variables
        let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
        let cohorts = [];

        for (let i = 0; i < age_bands.length; i++) {
          cohorts.push(`f_${age_bands[i]}`);
          cohorts.push(`m_${age_bands[i]}`);
        }

        //Return statement
        return cohorts;
      }

      /**
       * Loads and parses Brass standard life table CSV data.
       *
       * @returns {Object}
       */
      static loadSourceTables () {
        if (this._table_cache) return this._table_cache;

        //Declare local instance variables
        let csv_path = (fs.existsSync(this.source_csv_path)) ?
          this.source_csv_path :
          path.join(h3, "age_sex_counterfactuals/1.4.brass_logit_life_tables/brass_standard_life_table.csv");
        let lines = [];
        let raw_txt = "";
        let table_cache = {
          female_standard_logit: new Array(18).fill(0),
          male_standard_logit: new Array(18).fill(0)
        };

        if (!fs.existsSync(csv_path)) {
          console.warn(`[WARN] Brass source table ${csv_path} not found on disk.`);
          return null;
        }

        raw_txt = fs.readFileSync(csv_path, "utf8");
        lines = raw_txt.split(/\r?\n/);
        for (let i = 1; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line) continue;
          let cols = line.split(",");
          if (cols.length < 5) continue;

          let standard = cols[0];
          let sex = cols[1];
          let age = Math.round(parseFloat(cols[2]));
          let logit = parseFloat(cols[4]);

          //Filter for Brass General Standard
          if (standard.includes("General") || standard.includes("African")) {
            let age_idx = Math.min(17, Math.max(0, (age === 0) ? 0 : (age === 1) ? 1 : Math.floor(age/5) + 1));
            if (sex === "female" || sex === "f") {
              if (table_cache.female_standard_logit[age_idx] === 0 || standard.includes("General"))
                table_cache.female_standard_logit[age_idx] = logit;
            } else {
              if (table_cache.male_standard_logit[age_idx] === 0 || standard.includes("General"))
                table_cache.male_standard_logit[age_idx] = logit;
            }
          }
        }

        //Fallbacks for edge cases
        for (let a = 0; a < 18; a++) {
          if (table_cache.female_standard_logit[a] === 0 || table_cache.female_standard_logit[a] < -5)
            table_cache.female_standard_logit[a] = this.brass_standard.female_standard_logit[a];
          if (table_cache.male_standard_logit[a] === 0 || table_cache.male_standard_logit[a] < -5)
            table_cache.male_standard_logit[a] = this.brass_standard.male_standard_logit[a];
        }

        this._table_cache = table_cache;

        //Return statement
        return table_cache;
      }

      /**
       * Brass African/General Standard Life Table fallback logit values across 18 age bands.
       */
      static brass_standard = {
        age_midpoints: [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 84.0],
        band_durations: [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10],
        female_standard_logit: [-0.94, -0.74, -0.63, -0.56, -0.49, -0.42, -0.35, -0.28, -0.20, -0.11, -0.01, 0.12, 0.27, 0.45, 0.68, 0.98, 1.38, 1.95],
        male_standard_logit: [-0.88, -0.68, -0.58, -0.51, -0.44, -0.37, -0.30, -0.23, -0.15, -0.06, 0.05, 0.19, 0.35, 0.54, 0.78, 1.10, 1.52, 2.10]
      };

      /**
       * Trains Brass relational logit model mappings for alpha, beta, and r.
       *
       * @param {Object} arg0_dataset
       * @param {Object} [arg1_options]
       *
       * @returns {Object}
       */
      static train (arg0_dataset, arg1_options) {
        //Convert from parameters
        let dataset = arg0_dataset;
        let options = (arg1_options) ? arg1_options : {};

        //Declare local instance variables
        let alpha_f_train = [];
        let alpha_m_train = [];
        let beta_f_train = [];
        let beta_m_train = [];
        let cohorts = this.getCohorts();
        let default_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture", "rel_pop_growth"
        ];
        let K = (dataset.X.length > 0) ? dataset.X[0].length : 0;
        let cov_names = (dataset.covariates && dataset.covariates.length === K) ?
          dataset.covariates :
          default_covs.slice(0, K);
        let means = new Array(K).fill(0);
        let N = dataset.X.length;
        let r_train = [];
        let sds = new Array(K).fill(0);

        this.loadSourceTables();

        for (let j = 0; j < K; j++) {
          let sum = 0;
          for (let i = 0; i < N; i++) sum += dataset.X[i][j];
          means[j] = sum/N;

          let sum_sq = 0;
          for (let i = 0; i < N; i++) sum_sq += (dataset.X[i][j] - means[j])*(dataset.X[i][j] - means[j]);
          sds[j] = Math.sqrt(sum_sq/N) || 1.0;
        }

        for (let i = 0; i < N; i++) {
          let y = dataset.Y[i];
          let infant_f = y[0];
          let infant_m = y[1];
          let adult_f = y[10] + y[12] + y[14];
          let adult_m = y[11] + y[13] + y[15];
          let old_f = y[34];
          let old_m = y[35];
          let youth = 0;
          for (let c = 0; c < 10; c++) youth += y[c];

          //Estimate empirical alpha (mortality level) and beta (slope)
          let a_f = 0.5 * Math.log(Math.max(0.05, Math.min(20.0, (infant_f + 0.01)/(old_f + 0.01))));
          let a_m = 0.5 * Math.log(Math.max(0.05, Math.min(20.0, (infant_m + 0.01)/(old_m + 0.01))));
          let b_f = 0.85 + 0.3 * ((adult_f + 0.01)/(infant_f + 0.01) - 1.5);
          let b_m = 0.88 + 0.3 * ((adult_m + 0.01)/(infant_m + 0.01) - 1.5);

          alpha_f_train.push(a_f);
          alpha_m_train.push(a_m);
          beta_f_train.push(Math.max(0.5, Math.min(1.8, b_f)));
          beta_m_train.push(Math.max(0.5, Math.min(1.8, b_m)));
          r_train.push((youth - 0.27)*0.045);
        }

        let fitModel = function (target_vec, lambda) {
          let mean_t = target_vec.reduce((a, b) => a + b, 0)/N;
          let weights = new Array(K).fill(0);
          for (let j = 0; j < K; j++) {
            let cov_xy = 0;
            let var_x = 0;
            for (let i = 0; i < N; i++) {
              let z = (dataset.X[i][j] - means[j])/sds[j];
              cov_xy += z*(target_vec[i] - mean_t);
              var_x += z*z;
            }
            weights[j] = cov_xy/(var_x + lambda*N);
          }
          return { bias: mean_t, weights: weights };
        };

        let alpha_f_model = fitModel(alpha_f_train, 8.0);
        let alpha_m_model = fitModel(alpha_m_train, 8.0);
        let beta_f_model = fitModel(beta_f_train, 15.0);
        let beta_m_model = fitModel(beta_m_train, 15.0);
        let r_model = fitModel(r_train, 5.0);

        let artifact = {
          alpha_f_model: alpha_f_model,
          alpha_m_model: alpha_m_model,
          beta_f_model: beta_f_model,
          beta_m_model: beta_m_model,
          covariates: cov_names,
          means: means,
          model_key: this.key,
          r_model: r_model,
          sds: sds,
          trained_at: new Date().toISOString()
        };

        //Return statement
        return artifact;
      }

      /**
       * Predicts demographic cohort distribution for given covariate vector.
       *
       * @param {Array<number>} arg0_x
       * @param {Object} arg1_artifact
       *
       * @returns {Object} Map of cohort -> fraction.
       */
      static predict (arg0_x, arg1_artifact) {
        //Convert from parameters
        let x = arg0_x;
        let artifact = arg1_artifact;

        //Declare local instance variables
        let a_f = artifact.alpha_f_model.bias;
        let a_m = artifact.alpha_m_model.bias;
        let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
        let b_f = artifact.beta_f_model.bias;
        let b_m = artifact.beta_m_model.bias;
        let durations = this.brass_standard.band_durations;
        let f_std = this.brass_standard.female_standard_logit;
        let m_std = this.brass_standard.male_standard_logit;
        let midpoints = this.brass_standard.age_midpoints;
        let prediction = {};
        let r = artifact.r_model.bias;

        if (!this._table_cache) this.loadSourceTables();
        if (this._table_cache) {
          f_std = this._table_cache.female_standard_logit;
          m_std = this._table_cache.male_standard_logit;
        }

        for (let j = 0; j < x.length; j++) {
          let z = (x[j] - artifact.means[j])/(artifact.sds[j] || 1.0);
          a_f += (artifact.alpha_f_model.weights[j] || 0)*z;
          a_m += (artifact.alpha_m_model.weights[j] || 0)*z;
          b_f += (artifact.beta_f_model.weights[j] || 0)*z;
          b_m += (artifact.beta_m_model.weights[j] || 0)*z;
          r += (artifact.r_model.weights[j] || 0)*z;
        }

        a_f = Math.max(-1.5, Math.min(1.5, a_f));
        a_m = Math.max(-1.5, Math.min(1.5, a_m));
        b_f = Math.max(0.6, Math.min(1.6, b_f));
        b_m = Math.max(0.6, Math.min(1.6, b_m));
        r = Math.max(-0.02, Math.min(0.04, r));

        let f_nLx = new Array(18).fill(0);
        let m_nLx = new Array(18).fill(0);

        //Reconstruct survivorship via inverse logit: l_x = 1 / (1 + exp(2 * Y_x))
        let f_lx = new Array(19).fill(1.0);
        let m_lx = new Array(19).fill(1.0);

        for (let a = 0; a < 18; a++) {
          let y_f = a_f + b_f*f_std[a];
          let y_m = a_m + b_m*m_std[a];
          f_lx[a + 1] = 1.0/(1.0 + Math.exp(2.0*y_f));
          m_lx[a + 1] = 1.0/(1.0 + Math.exp(2.0*y_m));
        }

        for (let a = 0; a < 18; a++) {
          let n = durations[a];
          f_nLx[a] = 0.5*(f_lx[a] + f_lx[a + 1])*n;
          m_nLx[a] = 0.5*(m_lx[a] + m_lx[a + 1])*n;
        }

        //Apply Lotka stable population discounting exp(-r * x_mid)
        let f_pop = new Array(18).fill(0);
        let m_pop = new Array(18).fill(0);
        let total = 0;
        let srb = 1.05;

        for (let a = 0; a < 18; a++) {
          let disc = Math.exp(-r*midpoints[a]);
          f_pop[a] = f_nLx[a]*disc*(1.0/(1.0 + srb));
          m_pop[a] = m_nLx[a]*disc*(srb/(1.0 + srb));
          total += f_pop[a] + m_pop[a];
        }

        let inv_sum = (total > 0) ? (1.0/total) : (1.0/36);
        let result = new Array(36).fill(0);
        for (let a = 0; a < 18; a++) {
          result[a*2] = f_pop[a]*inv_sum;
          result[a*2 + 1] = m_pop[a]*inv_sum;
        }

        //Return statement
        return result;
      }

      /**
       * Predicts a batch of samples.
       *
       * @param {Array<Array<number>>} arg0_x_matrix
       * @param {Object} arg1_model
       *
       * @returns {Array<Array<number>>}
       */
      static predictBatch (arg0_x_matrix, arg1_model) {
        //Convert from parameters
        let x_matrix = arg0_x_matrix;
        let model = arg1_model;

        //Declare local instance variables
        let predictions = [];

        for (let i = 0; i < x_matrix.length; i++)
          predictions.push(this.predict(x_matrix[i], model));

        //Return statement
        return predictions;
      }
    };
}

if (typeof module !== "undefined" && module.exports)
  module.exports = global.BrassLogitLifeTables;
