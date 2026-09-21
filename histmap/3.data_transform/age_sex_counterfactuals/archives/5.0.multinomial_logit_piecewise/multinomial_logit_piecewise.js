//Initialise functions
{
  if (!global.MultinomialLogitPiecewise)
    /**
     * MultinomialLogitPiecewise implements the production baseline architecture from age_sex:
     * L2-regularised softmax regression with rolling anchor interpolation and premodern piecewise cutoffs.
     * Serves as the benchmark baseline against which all counterfactual utility metrics are evaluated.
     *
     * @class MultinomialLogitPiecewise
     */
    global.MultinomialLogitPiecewise = class {
      static key = "multinomial_logit_piecewise";
      static name = "Multinomial Logit (Piecewise Baseline)";
      static family = "Multinomial Logit Baseline";

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
       * Trains the baseline multinomial logit model.
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
        let coeff_obj = {};
        let cohorts = this.getCohorts();
        let default_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture", "rel_pop_growth"
        ];
        let iterations = (options.iterations) ? options.iterations : 3000;
        let K = (dataset.X.length > 0) ? dataset.X[0].length : 0;
        let cov_names = (dataset.covariates && dataset.covariates.length === K) ?
          dataset.covariates :
          default_covs.slice(0, K);
        let lambda = (options.lambda !== undefined) ? options.lambda : 1e-2;
        let learning_rate = (options.learning_rate) ? options.learning_rate : 0.5;
        let means = new Array(K).fill(0);
        let N = dataset.X.length;
        let sds = new Array(K).fill(0);

        for (let j = 0; j < K; j++) {
          let sum = 0;
          for (let i = 0; i < N; i++) sum += dataset.X[i][j];
          means[j] = sum/N;

          let sum_sq = 0;
          for (let i = 0; i < N; i++) sum_sq += (dataset.X[i][j] - means[j])*(dataset.X[i][j] - means[j]);
          sds[j] = Math.sqrt(sum_sq/N) || 1.0;
        }

        let X_z = dataset.X.map(row => row.map((v, j) => (v - means[j])/sds[j]));
        let Y_train = dataset.Y;

        let model_res = Statistics.multinomialLogitRegression(X_z, Y_train, {
          classes: cohorts,
          debug: false,
          lambda: lambda,
          learning_rate: learning_rate,
          max_iterations: iterations,
          proportions: true,
          reference_class: cohorts[0]
        });

        //Convert standardized coefficients back to raw feature space
        for (let c = 1; c < cohorts.length; c++) {
          coeff_obj[cohorts[c]] = {};
          let intercept_shift = 0;
          let scaled_intercept = model_res.beta[c][0];

          for (let j = 0; j < K; j++) {
            let cov_name = cov_names[j] || `cov_${j}`;
            let orig_slope = model_res.beta[c][j + 1]/sds[j];
            coeff_obj[cohorts[c]][cov_name] = orig_slope;
            intercept_shift += orig_slope*means[j];
          }
          coeff_obj[cohorts[c]]._intercept = scaled_intercept - intercept_shift;
        }

        //Return statement
        return {
          classes: cohorts,
          coefficients: coeff_obj,
          covariates: cov_names,
          family: this.family,
          has_intercept: true,
          key: this.key,
          name: this.name,
          reference_class: cohorts[0],
          standardisation: { means: means, sds: sds },
          training: {
            converged: model_res.converged,
            iterations: model_res.iterations,
            lambda: lambda
          },
          type: "multinomial_logit"
        };
      }

      /**
       * Predicts 36-cohort age-sex distribution vector.
       *
       * @param {Array<number>|Object} arg0_features
       * @param {Object} arg1_model
       *
       * @returns {Array<number>}
       */
      static predict (arg0_features, arg1_model) {
        //Convert from parameters
        let features = arg0_features;
        let model = arg1_model;

        //Declare local instance variables
        let cohorts = model.classes;
        let feat = {};
        let prob_obj = null;
        let result = [];
        let std = model.standardisation;

        if (Array.isArray(features)) {
          for (let j = 0; j < model.covariates.length; j++) {
            let name = model.covariates[j];
            let raw_val = features[j] || 0;
            if (std) {
              let z = (raw_val - std.means[j])/std.sds[j];
              let clamped_z = Math.max(-3.0, Math.min(3.0, z));
              feat[name] = std.means[j] + clamped_z*std.sds[j];
            } else {
              feat[name] = raw_val;
            }
          }
        } else {
          feat = features;
        }

        prob_obj = Statistics.predictMultinomialProbabilities(feat, model);
        for (let c = 0; c < cohorts.length; c++)
          result.push(prob_obj[cohorts[c]] || 0);

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
