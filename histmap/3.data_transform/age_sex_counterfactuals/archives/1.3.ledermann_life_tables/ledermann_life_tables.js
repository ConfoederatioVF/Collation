//Initialise functions
{
  if (!global.LedermannLifeTables)
    /**
     * LedermannLifeTables implements Jean Ledermann's system of continuous model life tables (1969).
     * Uses two demographic indicators (u1 = general mortality level, u2 = adult/child mortality ratio):
     * ln(q_x) = a0_x + a1_x * u1 + a2_x * u2
     * Directly loads and queries from source data (ledermann_life_tables.csv).
     *
     * @class LedermannLifeTables
     */
    global.LedermannLifeTables = class {
      static key = "ledermann_life_tables";
      static name = "Ledermann's Life Tables";
      static family = "Life Tables";
      static source_csv_path = path.join(__dirname, "ledermann_life_tables.csv");

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
       * Loads and parses source Ledermann CSV coefficients and grid.
       *
       * @returns {Object}
       */
      static loadSourceTables () {
        if (this._table_cache) return this._table_cache;

        //Declare local instance variables
        let csv_path = (fs.existsSync(this.source_csv_path)) ?
          this.source_csv_path :
          path.join(h3, "age_sex_counterfactuals/1.3.ledermann_life_tables/ledermann_life_tables.csv");
        let lines = [];
        let raw_txt = "";
        let table_cache = {
          female_a0: new Array(18).fill(-2.0),
          female_a1: new Array(18).fill(0.6),
          female_a2: new Array(18).fill(0.2),
          grid: {},
          male_a0: new Array(18).fill(-2.0),
          male_a1: new Array(18).fill(0.6),
          male_a2: new Array(18).fill(0.2)
        };

        if (!fs.existsSync(csv_path)) {
          console.warn(`[WARN] Ledermann source table ${csv_path} not found on disk.`);
          return null;
        }

        raw_txt = fs.readFileSync(csv_path, "utf8");
        lines = raw_txt.split(/\r?\n/);
        for (let i = 1; i < lines.length; i++) {
          let line = lines[i].trim();
          if (!line) continue;
          let cols = line.split(",");
          if (cols.length < 10) continue;

          let sex = (cols[0] === "female" || cols[0] === "f") ? "f" : "m";
          let u1 = parseFloat(cols[1]);
          let u2 = parseFloat(cols[2]);
          let age = Math.round(parseFloat(cols[3]));
          let nLx = parseFloat(cols[6]);
          let a0 = parseFloat(cols[7]);
          let a1 = parseFloat(cols[8]);
          let a2 = parseFloat(cols[9]);

          let age_idx = Math.min(17, Math.max(0, (age === 0) ? 0 : (age === 1) ? 1 : Math.floor(age/5) + 1));

          if (sex === "f") {
            table_cache.female_a0[age_idx] = a0;
            table_cache.female_a1[age_idx] = a1;
            table_cache.female_a2[age_idx] = a2;
          } else {
            table_cache.male_a0[age_idx] = a0;
            table_cache.male_a1[age_idx] = a1;
            table_cache.male_a2[age_idx] = a2;
          }

          let grid_key = `${sex}_${u1}_${u2}`;
          if (!table_cache.grid[grid_key]) table_cache.grid[grid_key] = new Array(18).fill(0);
          table_cache.grid[grid_key][age_idx] = nLx;
        }

        this._table_cache = table_cache;

        //Return statement
        return table_cache;
      }

      /**
       * Ledermann default regression coefficients across 18 age cohorts.
       */
      static ledermann_coeffs = {
        age_midpoints: [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 84.0],
        band_durations: [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10],
        female_a0: [-2.45, -3.10, -4.50, -5.10, -4.95, -4.75, -4.55, -4.35, -4.10, -3.80, -3.45, -3.05, -2.60, -2.15, -1.65, -1.18, -0.72, -0.32],
        female_a1: [0.82, 0.90, 0.85, 0.78, 0.72, 0.68, 0.65, 0.62, 0.60, 0.58, 0.56, 0.54, 0.52, 0.50, 0.48, 0.45, 0.42, 0.38],
        female_a2: [-0.30, -0.25, -0.15, 0.05, 0.20, 0.30, 0.35, 0.40, 0.45, 0.48, 0.50, 0.52, 0.50, 0.45, 0.38, 0.30, 0.20, 0.10],
        male_a0: [-2.35, -2.98, -4.35, -4.95, -4.70, -4.45, -4.25, -4.05, -3.80, -3.50, -3.15, -2.75, -2.30, -1.85, -1.40, -0.98, -0.58, -0.22],
        male_a1: [0.85, 0.92, 0.87, 0.80, 0.74, 0.70, 0.67, 0.64, 0.62, 0.60, 0.58, 0.56, 0.54, 0.52, 0.50, 0.47, 0.44, 0.40],
        male_a2: [-0.28, -0.22, -0.12, 0.08, 0.25, 0.35, 0.42, 0.48, 0.52, 0.55, 0.58, 0.60, 0.56, 0.50, 0.42, 0.34, 0.24, 0.12]
      };

      /**
       * Trains the Ledermann model mappings for u1, u2, and r.
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
        let K = (dataset.X.length > 0) ? dataset.X[0].length : 0;
        let cov_names = (dataset.covariates && dataset.covariates.length === K) ?
          dataset.covariates :
          default_covs.slice(0, K);
        let means = new Array(K).fill(0);
        let N = dataset.X.length;
        let r_train = [];
        let sds = new Array(K).fill(0);
        let u1_train = [];
        let u2_train = [];

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
          let adult = y[8] + y[9] + y[10] + y[11];
          let old = y[34] + y[35];
          let youth = 0;
          for (let c = 0; c < 10; c++) youth += y[c];

          //u1: overall mortality level proxy
          let u1 = (infant*3.0 + 0.05)/(old*4.0 + 0.05);
          u1_train.push(Math.log(Math.max(0.1, Math.min(10.0, u1))));

          //u2: adult mortality differential
          let u2 = adult/(infant + 1e-4);
          u2_train.push(Math.log(Math.max(0.2, Math.min(5.0, u2))));

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

        let u1_model = fitModel(u1_train, 10.0);
        let u2_model = fitModel(u2_train, 10.0);
        let r_model = fitModel(r_train, 5.0);

        let artifact = {
          covariates: cov_names,
          means: means,
          model_key: this.key,
          r_model: r_model,
          sds: sds,
          trained_at: new Date().toISOString(),
          u1_model: u1_model,
          u2_model: u2_model
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
        let coeffs = (this._table_cache) ? this._table_cache : this.ledermann_coeffs;
        let durations = this.ledermann_coeffs.band_durations;
        let midpoints = this.ledermann_coeffs.age_midpoints;
        let prediction = {};
        let r = artifact.r_model.bias;
        let u1 = artifact.u1_model.bias;
        let u2 = artifact.u2_model.bias;

        if (!this._table_cache) this.loadSourceTables();
        if (this._table_cache) coeffs = this._table_cache;

        for (let j = 0; j < x.length; j++) {
          let z = (x[j] - artifact.means[j])/(artifact.sds[j] || 1.0);
          u1 += (artifact.u1_model.weights[j] || 0)*z;
          u2 += (artifact.u2_model.weights[j] || 0)*z;
          r += (artifact.r_model.weights[j] || 0)*z;
        }

        u1 = Math.max(-1.5, Math.min(2.0, u1));
        u2 = Math.max(-1.5, Math.min(2.0, u2));
        r = Math.max(-0.02, Math.min(0.04, r));

        let f_nLx = new Array(18).fill(0);
        let m_nLx = new Array(18).fill(0);

        //Female table reconstruction
        let f_cum_surv = 1.0;
        for (let a = 0; a < 18; a++) {
          let ln_q = coeffs.female_a0[a] + coeffs.female_a1[a]*u1 + coeffs.female_a2[a]*u2;
          let q = Math.max(0.0005, Math.min(0.95, Math.exp(ln_q)));
          let n = durations[a];
          let lx_start = f_cum_surv;
          let lx_end = lx_start*(1.0 - q);
          f_cum_surv = lx_end;
          f_nLx[a] = 0.5*(lx_start + lx_end)*n;
        }

        //Male table reconstruction
        let m_cum_surv = 1.0;
        for (let a = 0; a < 18; a++) {
          let ln_q = coeffs.male_a0[a] + coeffs.male_a1[a]*u1 + coeffs.male_a2[a]*u2;
          let q = Math.max(0.0005, Math.min(0.95, Math.exp(ln_q)));
          let n = durations[a];
          let lx_start = m_cum_surv;
          let lx_end = lx_start*(1.0 - q);
          m_cum_surv = lx_end;
          m_nLx[a] = 0.5*(lx_start + lx_end)*n;
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
  module.exports = global.LedermannLifeTables;
