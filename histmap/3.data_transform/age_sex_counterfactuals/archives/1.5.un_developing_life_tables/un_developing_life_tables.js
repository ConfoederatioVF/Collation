//Initialise functions
{
  if (!global.UNDevelopingLifeTables)
    /**
     * UNDevelopingLifeTables implements the United Nations Model Life Tables for Developing Countries (Pre-1950).
     * Calibrated for high-mortality, pre-demographic transition regimes (e0 < 45) with elevated infant and maternal
     * mortality profiles and infectious epidemiological disease burdens.
     * Directly loads from source CSV (un_developing_life_tables.csv).
     *
     * @class UNDevelopingLifeTables
     */
    global.UNDevelopingLifeTables = class {
      static key = "un_developing_life_tables";
      static name = "UN Life Tables for Developing Countries (pre-1950)";
      static family = "Life Tables";
      static source_csv_path = path.join(__dirname, "un_developing_life_tables.csv");

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
       * Loads and parses source UN Developing Life Tables CSV data.
       *
       * @returns {Object}
       */
      static loadSourceTables () {
        if (this._table_cache) return this._table_cache;

        //Declare local instance variables
        let csv_path = (fs.existsSync(this.source_csv_path)) ?
          this.source_csv_path :
          path.join(h3, "age_sex_counterfactuals/1.5.un_developing_life_tables/un_developing_life_tables.csv");
        let lines = [];
        let raw_txt = "";
        let table_tree = {};

        if (!fs.existsSync(csv_path)) {
          console.warn(`[WARN] UN Developing source table ${csv_path} not found on disk.`);
          return null;
        }

        raw_txt = fs.readFileSync(csv_path, "utf8");
        lines = raw_txt.split(/\r?\n/);
        for (let i = 1; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line) continue;
          let cols = line.split(",");
          if (cols.length < 7) continue;

          let type = cols[0];
          let sex = (cols[1] === "1" || cols[1] === "1.0") ? "m" : "f";
          let age = Math.round(parseFloat(cols[2]));
          let e0 = Math.round(parseFloat(cols[3]));
          let mx = parseFloat(cols[4]);
          let lx = parseFloat(cols[5]);
          let Lx = parseFloat(cols[6]);

          if (!table_tree[type]) table_tree[type] = {};
          if (!table_tree[type][sex]) table_tree[type][sex] = {};
          if (!table_tree[type][sex][e0]) table_tree[type][sex][e0] = {};

          table_tree[type][sex][e0][age] = { Lx: Lx, lx: lx, mx: mx };
        }

        this._table_cache = table_tree;

        //Return statement
        return table_tree;
      }

      /**
       * UN High-Mortality Developing Country Life Table baseline logit survival parameters across 18 age bands.
       */
      static developing_tables = {
        age_midpoints: [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 84.0],
        band_durations: [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10],
        female_slope: [-0.038, -0.034, -0.028, -0.024, -0.020, -0.018, -0.017, -0.016, -0.015, -0.014, -0.014, -0.014, -0.015, -0.016, -0.017, -0.018, -0.020, -0.024],
        female_standard_logit: [-1.45, -1.22, -1.02, -0.90, -0.78, -0.66, -0.55, -0.44, -0.32, -0.19, -0.04, 0.14, 0.35, 0.60, 0.90, 1.28, 1.76, 2.45],
        male_slope: [-0.040, -0.036, -0.030, -0.025, -0.022, -0.020, -0.019, -0.018, -0.017, -0.016, -0.016, -0.016, -0.017, -0.018, -0.019, -0.020, -0.022, -0.026],
        male_standard_logit: [-1.38, -1.15, -0.95, -0.84, -0.72, -0.60, -0.48, -0.36, -0.24, -0.10, 0.06, 0.25, 0.48, 0.74, 1.05, 1.44, 1.94, 2.65]
      };

      /**
       * Trains the pre-1950 developing country model mapping.
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
        let cohorts = this.getCohorts();
        let default_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture", "rel_pop_growth"
        ];
        let e0_train = [];
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
          let old = y[34] + y[35];
          let youth = 0;
          for (let c = 0; c < 10; c++) youth += y[c];

          //Calibrate e0 bounded strongly in developing regime [22, 50]
          let est_e0 = 32.0 + 8.0*(old/0.08) - 10.0*(infant/0.14);
          e0_train.push(Math.max(22.0, Math.min(50.0, est_e0)));
          r_train.push((youth - 0.28)*0.04);
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

        let e0_model = fitModel(e0_train, 10.0);
        let r_model = fitModel(r_train, 5.0);

        let artifact = {
          covariates: cov_names,
          e0_model: e0_model,
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
        let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
        let age_starts = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80];
        let e0 = artifact.e0_model.bias;
        let prediction = {};
        let r = artifact.r_model.bias;
        let table_tree = (this._table_cache) ? this._table_cache : this.loadSourceTables();

        for (let j = 0; j < x.length; j++) {
          let z = (x[j] - artifact.means[j])/(artifact.sds[j] || 1.0);
          e0 += (artifact.e0_model.weights[j] || 0)*z;
          r += (artifact.r_model.weights[j] || 0)*z;
        }

        e0 = Math.max(22.0, Math.min(48.0, e0));
        r = Math.max(-0.015, Math.min(0.035, r));

        let f_Lx = new Array(18).fill(0);
        let m_Lx = new Array(18).fill(0);

        //Query from table_tree if available, else fallback to analytical logit
        let primary_type = (table_tree && table_tree["UN_Chilean"]) ? "UN_Chilean" : (table_tree ? Object.keys(table_tree)[0] : null);

        if (primary_type && table_tree[primary_type]) {
          let e0_floor = Math.max(20, Math.min(45, Math.floor(e0/5)*5));
          let e0_ceil = Math.min(45, e0_floor + 5);
          let w_ceil = (e0_ceil === e0_floor) ? 0 : (e0 - e0_floor)/(e0_ceil - e0_floor);
          let w_floor = 1.0 - w_ceil;

          for (let a = 0; a < 18; a++) {
            let age = age_starts[a];
            let f_lf = (table_tree[primary_type]["f"][e0_floor] && table_tree[primary_type]["f"][e0_floor][age]) ? table_tree[primary_type]["f"][e0_floor][age].Lx : 10000;
            let f_lc = (table_tree[primary_type]["f"][e0_ceil] && table_tree[primary_type]["f"][e0_ceil][age]) ? table_tree[primary_type]["f"][e0_ceil][age].Lx : f_lf;
            let m_lf = (table_tree[primary_type]["m"][e0_floor] && table_tree[primary_type]["m"][e0_floor][age]) ? table_tree[primary_type]["m"][e0_floor][age].Lx : 10000;
            let m_lc = (table_tree[primary_type]["m"][e0_ceil] && table_tree[primary_type]["m"][e0_ceil][age]) ? table_tree[primary_type]["m"][e0_ceil][age].Lx : m_lf;

            f_Lx[a] = w_floor*f_lf + w_ceil*f_lc;
            m_Lx[a] = w_floor*m_lf + w_ceil*m_lc;
          }
        } else {
          //Analytical fallback
          let durations = this.developing_tables.band_durations;
          let f_slopes = this.developing_tables.female_slope;
          let f_std = this.developing_tables.female_standard_logit;
          let m_slopes = this.developing_tables.male_slope;
          let m_std = this.developing_tables.male_standard_logit;

          let f_cum = 1.0;
          let m_cum = 1.0;
          for (let a = 0; a < 18; a++) {
            let f_logit = f_std[a] + f_slopes[a]*(e0 - 35.0);
            let m_logit = m_std[a] + m_slopes[a]*(e0 - 35.0);
            let f_p = 1.0/(1.0 + Math.exp(2.0*f_logit));
            let m_p = 1.0/(1.0 + Math.exp(2.0*m_logit));
            let n = durations[a];
            f_Lx[a] = 0.5*(f_cum + f_p)*n;
            m_Lx[a] = 0.5*(m_cum + m_p)*n;
            f_cum = f_p;
            m_cum = m_p;
          }
        }

        //Apply Lotka stable population discounting exp(-r * x_mid)
        let f_pop = new Array(18).fill(0);
        let m_pop = new Array(18).fill(0);
        let midpoints = this.developing_tables.age_midpoints;
        let total = 0;
        let srb = 1.05;

        for (let a = 0; a < 18; a++) {
          let disc = Math.exp(-r*midpoints[a]);
          f_pop[a] = f_Lx[a]*disc*(1.0/(1.0 + srb));
          m_pop[a] = m_Lx[a]*disc*(srb/(1.0 + srb));
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
  module.exports = global.UNDevelopingLifeTables;
