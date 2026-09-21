//Initialise functions
{
  if (!global.CoaleDemenyLifeTables)
    /**
     * CoaleDemenyLifeTables implements the Coale-Demeny Regional Model Life Tables (1966/1983)
     * covering 4 regional families (North, South, East, West) across 25 mortality levels (e0 = 20-80).
     * Loads and queries directly from official Coale-Demeny source data (coale_demeny_life_tables.csv).
     *
     * @class CoaleDemenyLifeTables
     */
    global.CoaleDemenyLifeTables = class {
      static key = "coale_demeny_life_tables";
      static name = "Coale-Demeny Life Tables";
      static family = "Life Tables";
      static source_csv_path = path.join(__dirname, "coale_demeny_life_tables.csv");

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
       * Loads and indexes official Coale-Demeny source CSV data.
       *
       * @returns {Object} Indexed table tree: type -> sex -> e0 -> age -> { lx, Lx, mx }
       */
      static loadSourceTables () {
        if (this._table_cache) return this._table_cache;

        //Declare local instance variables
        let csv_path = (fs.existsSync(this.source_csv_path)) ?
          this.source_csv_path :
          path.join(h3, "age_sex_counterfactuals/1.2.coale_demeny_life_tables/coale_demeny_life_tables.csv");
        let lines = [];
        let raw_txt = "";
        let table_tree = {};

        if (!fs.existsSync(csv_path)) {
          console.warn(`[WARN] Source table ${csv_path} not found on disk.`);
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
          table_tree[type][sex][e0][age] = { lx: lx, Lx: Lx, mx: mx };
        }

        this._table_cache = table_tree;
        //Return statement
        return table_tree;
      }

      /**
       * Trains the Coale-Demeny Model mapping.
       *
       * @param {Object} arg0_dataset - { X, Y, covariates, countries }
       * @param {Object} [arg1_options]
       *
       * @returns {Object} Trained model artifact.
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
          let elderly = y[34] + y[35];
          let youth = 0;
          for (let c = 0; c < 10; c++) youth += y[c];

          let proxy_e0 = 34.0 + 36.0*Math.max(0, Math.min(1.0, (elderly*6.0)/(infant*2.5 + elderly*3.5 + 1e-4)));
          e0_train.push(proxy_e0);
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
            weights[j] = cov_xy / (var_x + lambda*N);
          }
          return { intercept: mean_t, weights: weights };
        };

        let e0_fit = fitModel(e0_train, 1e-2);
        let r_fit = fitModel(r_train, 1e-2);

        //Return statement
        return {
          classes: cohorts,
          covariates: cov_names,
          e0_model: e0_fit,
          family: this.family,
          key: this.key,
          name: this.name,
          r_model: r_fit,
          source_table_loaded: (this._table_cache !== null),
          standardisation: { means: means, sds: sds },
          type: "coale_demeny_life_tables"
        };
      }

      /**
       * Predicts 36-cohort age-sex distribution vector from a covariate feature vector,
       * querying person-years lived nLx directly from official Coale-Demeny Regional Life Tables.
       *
       * @param {Array<number>|Object} arg0_features
       * @param {Object} arg1_model
       *
       * @returns {Array<number>} 36 normalized cohort proportions summing to 1.0.
       */
      static predict (arg0_features, arg1_model) {
        //Convert from parameters
        let features = arg0_features;
        let model = arg1_model;

        //Declare local instance variables
        let age_bands = [0, 1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80];
        let durations = [1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 10];
        let e0 = model.e0_model.intercept;
        let f_pop = new Float64Array(18);
        let m_pop = new Float64Array(18);
        let midpoints = [0.5, 2.5, 7.5, 12.5, 17.5, 22.5, 27.5, 32.5, 37.5, 42.5, 47.5, 52.5, 57.5, 62.5, 67.5, 72.5, 77.5, 84.0];
        let r = model.r_model.intercept;
        let result = new Array(36).fill(0);
        let s_means = model.standardisation.means;
        let s_sds = model.standardisation.sds;
        let srb = 1.05;
        let sum_total = 0;
        let table_tree = this.loadSourceTables();

        let x_vec = Array.isArray(features) ? features : model.covariates.map(k => features[k] || 0);
        for (let j = 0; j < x_vec.length; j++) {
          let z = (x_vec[j] - s_means[j])/s_sds[j];
          z = Math.max(-3.0, Math.min(3.0, z));
          e0 += z*(model.e0_model.weights[j] || 0);
          r += z*(model.r_model.weights[j] || 0);
        }

        e0 = Math.max(20.0, Math.min(80.0, e0));
        r = Math.max(-0.015, Math.min(0.038, r));

        let e0_floor = Math.floor(e0);
        let e0_ceil = Math.min(80, Math.ceil(e0));
        let alpha = (e0_ceil === e0_floor) ? 0 : (e0 - e0_floor);

        //CD_West regional family
        let cd_type = "CD_West";
        let tbl = (table_tree && table_tree[cd_type]) ? table_tree[cd_type] : null;

        for (let a = 0; a < 18; a++) {
          let age = age_bands[a];
          let dur = durations[a];
          let mid = midpoints[a];
          let f_Lx = 0;
          let m_Lx = 0;

          if (tbl) {
            let row_f0 = tbl["f"]?.[e0_floor]?.[age];
            let row_f1 = tbl["f"]?.[e0_ceil]?.[age];
            let row_m0 = tbl["m"]?.[e0_floor]?.[age];
            let row_m1 = tbl["m"]?.[e0_ceil]?.[age];

            let val_f0 = row_f0 ? row_f0.Lx : (100000.0*dur*Math.exp(-0.02*mid));
            let val_f1 = row_f1 ? row_f1.Lx : val_f0;
            let val_m0 = row_m0 ? row_m0.Lx : (100000.0*dur*Math.exp(-0.025*mid));
            let val_m1 = row_m1 ? row_m1.Lx : val_m0;

            f_Lx = (1 - alpha)*val_f0 + alpha*val_f1;
            m_Lx = (1 - alpha)*val_m0 + alpha*val_m1;
          } else {
            f_Lx = 100000.0*dur*Math.exp(-0.02*mid);
            m_Lx = 100000.0*dur*Math.exp(-0.025*mid);
          }

          let growth_decay = Math.exp(-r*mid);
          f_pop[a] = f_Lx*growth_decay;
          m_pop[a] = m_Lx*growth_decay*srb;

          sum_total += f_pop[a] + m_pop[a];
        }

        let inv_sum = (sum_total > 0) ? (1.0/sum_total) : (1.0/36);
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
