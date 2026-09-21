//Initialise functions
{
  if (!global.GompertzMakehamSiler)
    /**
     * GompertzMakehamSiler implements the classic parametric demographic hazard model:
     * h(x) = a1 * exp(-b1 * x) + a2 + a3 * exp(b3 * x)
     *   Term 1 (a1, b1): Infant / juvenile mortality deceleration
     *   Term 2 (a2): Age-independent accidental background mortality (Makeham constant)
     *   Term 3 (a3, b3): Senescent exponential mortality acceleration (Gompertz component)
     * Directly loads from calibrated reference tables (siler_hazard_reference_tables.csv).
     *
     * @class GompertzMakehamSiler
     */
    global.GompertzMakehamSiler = class {
      static key = "gompertz_makeham_siler";
      static name = "Gompertz-Makeham + Siler";
      static family = "Parametric Hazard";
      static source_csv_path = path.join(__dirname, "siler_hazard_reference_tables.csv");

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
       * Loads and parses Siler hazard reference tables from CSV.
       *
       * @returns {Object}
       */
      static loadSourceTables () {
        if (this._table_cache) return this._table_cache;

        //Declare local instance variables
        let csv_path = (fs.existsSync(this.source_csv_path)) ?
          this.source_csv_path :
          path.join(h3, "age_sex_counterfactuals/2.0.gompertz_makeham_siler/siler_hazard_reference_tables.csv");
        let lines = [];
        let raw_txt = "";
        let table_cache = {};

        if (!fs.existsSync(csv_path)) {
          console.warn(`[WARN] Siler source table ${csv_path} not found on disk.`);
          return null;
        }

        raw_txt = fs.readFileSync(csv_path, "utf8");
        lines = raw_txt.split(/\r?\n/);
        for (let i = 1; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line) continue;
          let cols = line.split(",");
          if (cols.length < 9) continue;

          let regime = cols[0];
          let sex = cols[1];
          let age = Math.round(parseFloat(cols[2]));
          let lx = parseFloat(cols[3]);
          let nLx = parseFloat(cols[4]);

          let key = `${regime}_${sex}`;
          if (!table_cache[key]) table_cache[key] = new Array(18).fill(0);
          let age_idx = Math.min(17, Math.max(0, (age === 0) ? 0 : (age === 1) ? 1 : Math.floor(age/5) + 1));
          table_cache[key][age_idx] = nLx;
        }

        this._table_cache = table_cache;

        //Return statement
        return table_cache;
      }

      static age_grid = {
        band_durations: [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10],
        ends: [1.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 95.0],
        midpoints: [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 84.0],
        starts: [0.0, 1.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 80.0]
      };

      /**
       * Computes cumulative Siler hazard H(x) = (a1/b1)*(1 - exp(-b1*x)) + a2*x + (a3/b3)*(exp(b3*x) - 1).
       *
       * @param {number} arg0_x
       * @param {Object} arg1_params - { a1, b1, a2, a3, b3 }
       *
       * @returns {number}
       */
      static silerCumulativeHazard (arg0_x, arg1_params) {
        //Convert from parameters
        let x = arg0_x;
        let params = arg1_params;

        //Declare local instance variables
        let h_infant = (params.a1/params.b1)*(1.0 - Math.exp(-params.b1*x));
        let h_makeham = params.a2*x;
        let h_senescence = (params.a3/params.b3)*(Math.exp(params.b3*x) - 1.0);

        //Return statement
        return h_infant + h_makeham + h_senescence;
      }

      /**
       * Trains the Siler parameter regressors against empirical training pyramids.
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
        let a1_train = [];
        let a2_train = [];
        let a3_train = [];
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
          let infant = y[0] + y[1];
          let adult_acc = y[8] + y[9] + y[10] + y[11];
          let old = y[32] + y[33] + y[34] + y[35];
          let youth = 0;
          for (let c = 0; c < 10; c++) youth += y[c];

          //Empirical proxies for hazard components:
          //a1: infant mortality parameter
          let est_a1 = 0.05 + 0.55*Math.max(0.01, infant);
          //a2: accidental background mortality
          let est_a2 = 0.002 + 0.012*(adult_acc/0.25);
          //a3: senescent baseline hazard
          let est_a3 = 0.0001 + 0.0008*(old/0.05);

          a1_train.push(est_a1);
          a2_train.push(est_a2);
          a3_train.push(est_a3);
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

        let a1_model = fitModel(a1_train, 8.0);
        let a2_model = fitModel(a2_train, 12.0);
        let a3_model = fitModel(a3_train, 10.0);
        let r_model = fitModel(r_train, 5.0);

        let artifact = {
          a1_model: a1_model,
          a2_model: a2_model,
          a3_model: a3_model,
          covariates: cov_names,
          fixed_b1: 2.5,
          fixed_b3: 0.088,
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
        let a1 = artifact.a1_model.bias;
        let a2 = artifact.a2_model.bias;
        let a3 = artifact.a3_model.bias;
        let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
        let b1 = artifact.fixed_b1 || 2.5;
        let b3 = artifact.fixed_b3 || 0.088;
        let durations = this.age_grid.band_durations;
        let ends = this.age_grid.ends;
        let midpoints = this.age_grid.midpoints;
        let prediction = {};
        let r = artifact.r_model.bias;
        let starts = this.age_grid.starts;

        for (let j = 0; j < x.length; j++) {
          let z = (x[j] - artifact.means[j])/(artifact.sds[j] || 1.0);
          a1 += (artifact.a1_model.weights[j] || 0)*z;
          a2 += (artifact.a2_model.weights[j] || 0)*z;
          a3 += (artifact.a3_model.weights[j] || 0)*z;
          r += (artifact.r_model.weights[j] || 0)*z;
        }

        a1 = Math.max(0.01, Math.min(0.8, a1));
        a2 = Math.max(0.0005, Math.min(0.03, a2));
        a3 = Math.max(0.00002, Math.min(0.005, a3));
        r = Math.max(-0.02, Math.min(0.04, r));

        let params_f = { a1: a1*0.95, a2: a2*0.9, a3: a3*0.85, b1: b1, b3: b3 };
        let params_m = { a1: a1*1.05, a2: a2*1.1, a3: a3*1.15, b1: b1, b3: b3 };

        let f_nLx = new Array(18).fill(0);
        let m_nLx = new Array(18).fill(0);

        for (let a = 0; a < 18; a++) {
          let x0 = starts[a];
          let x1 = ends[a];
          let h_f0 = this.silerCumulativeHazard(x0, params_f);
          let h_f1 = this.silerCumulativeHazard(x1, params_f);
          let s_f0 = Math.exp(-h_f0);
          let s_f1 = Math.exp(-h_f1);
          f_nLx[a] = 0.5*(s_f0 + s_f1)*durations[a];

          let h_m0 = this.silerCumulativeHazard(x0, params_m);
          let h_m1 = this.silerCumulativeHazard(x1, params_m);
          let s_m0 = Math.exp(-h_m0);
          let s_m1 = Math.exp(-h_m1);
          m_nLx[a] = 0.5*(s_m0 + s_m1)*durations[a];
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
  module.exports = global.GompertzMakehamSiler;
