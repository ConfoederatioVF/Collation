//Initialise functions
{
  if (!global.SGDSeparateCurves)
    /**
     * SGDSeparateCurves implements a neural Universal Function Approximator trained via Stochastic
     * Gradient Descent (SGD) with separate projection heads for male and female population curves.
     * Takes raw naive demographic and macroeconomic covariates.
     *
     * @class SGDSeparateCurves
     */
    global.SGDSeparateCurves = class {
      static key = "sgd_separate_curves";
      static name = "SGD (Separate Curves, Naive Covariates)";
      static family = "SGD Function Approximator";

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
       * Trains the neural function approximator via mini-batch SGD with Adam optimisation.
       *
       * @param {Object} arg0_dataset - { X, Y, covariates, countries }
       * @param {Object} [arg1_options]
       *
       * @returns {Object} Trained model parameters and weights.
       */
      static train (arg0_dataset, arg1_options) {
        //Convert from parameters
        let dataset = arg0_dataset;
        let options = (arg1_options) ? arg1_options : {};

        //Declare local instance variables
        let beta1 = 0.9;
        let beta2 = 0.999;
        let cohorts = this.getCohorts();
        let default_covs = [
          "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
          "delta_popc_", "delta_gdp_pc", "cropland", "pasture", "rel_pop_growth"
        ];
        let eps = 1e-8;
        let epochs = (options.epochs) ? options.epochs : 1200;
        let H = 32; //Hidden layer units
        let K = (dataset.X.length > 0) ? dataset.X[0].length : 0;
        let cov_names = (dataset.covariates && dataset.covariates.length === K) ?
          dataset.covariates :
          default_covs.slice(0, K);
        let lambda = (options.lambda !== undefined) ? options.lambda : 1e-4;
        let lr = (options.learning_rate) ? options.learning_rate : 0.01;
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
        let Y = dataset.Y;

        //Initialise weights using Xavier/Glorot scaling
        let W1 = []; // [H x K]
        let b1 = new Array(H).fill(0);
        let W_f = []; // [18 x H] female head
        let b_f = new Array(18).fill(0);
        let W_m = []; // [18 x H] male head
        let b_m = new Array(18).fill(0);

        let scale1 = Math.sqrt(2.0/(K + H));
        for (let h = 0; h < H; h++) {
          W1.push(new Array(K));
          for (let j = 0; j < K; j++)
            W1[h][j] = (Math.random()*2 - 1)*scale1;
        }

        let scale2 = Math.sqrt(2.0/(H + 18));
        for (let a = 0; a < 18; a++) {
          W_f.push(new Array(H));
          W_m.push(new Array(H));
          for (let h = 0; h < H; h++) {
            W_f[a][h] = (Math.random()*2 - 1)*scale2;
            W_m[a][h] = (Math.random()*2 - 1)*scale2;
          }
        }

        //Adam moment accumulators
        let mW1 = W1.map(r => new Array(K).fill(0));
        let vW1 = W1.map(r => new Array(K).fill(0));
        let mb1 = new Array(H).fill(0);
        let vb1 = new Array(H).fill(0);

        let mW_f = W_f.map(r => new Array(H).fill(0));
        let vW_f = W_f.map(r => new Array(H).fill(0));
        let mb_f = new Array(18).fill(0);
        let vb_f = new Array(18).fill(0);

        let mW_m = W_m.map(r => new Array(H).fill(0));
        let vW_m = W_m.map(r => new Array(H).fill(0));
        let mb_m = new Array(18).fill(0);
        let vb_m = new Array(18).fill(0);

        //Adam training loop
        let step = 0;
        for (let epoch = 0; epoch < epochs; epoch++) {
          //Shuffle sample indices
          let indices = [];
          for (let i = 0; i < N; i++) indices.push(i);
          for (let i = N - 1; i > 0; i--) {
            let swap_idx = Math.floor(Math.random()*(i + 1));
            let temp = indices[i];
            indices[i] = indices[swap_idx];
            indices[swap_idx] = temp;
          }

          let batch_size = Math.min(16, N);
          for (let b_start = 0; b_start < N; b_start += batch_size) {
            step++;
            let b_end = Math.min(N, b_start + batch_size);
            let b_len = b_end - b_start;

            let grad_W1 = W1.map(r => new Array(K).fill(0));
            let grad_b1 = new Array(H).fill(0);
            let grad_W_f = W_f.map(r => new Array(H).fill(0));
            let grad_b_f = new Array(18).fill(0);
            let grad_W_m = W_m.map(r => new Array(H).fill(0));
            let grad_b_m = new Array(18).fill(0);

            for (let b = b_start; b < b_end; b++) {
              let i = indices[b];
              let x = X_z[i];
              let y = Y[i];

              //Forward pass
              let h_act = new Array(H);
              for (let h = 0; h < H; h++) {
                let sum = b1[h];
                for (let j = 0; j < K; j++) sum += W1[h][j]*x[j];
                //Leaky ReLU activation
                h_act[h] = (sum > 0) ? sum : sum*0.01;
              }

              //Separate heads for female and male logits
              let logits_f = new Array(18);
              let logits_m = new Array(18);
              let max_l = -Infinity;

              for (let a = 0; a < 18; a++) {
                let sum_f = b_f[a];
                let sum_m = b_m[a];
                for (let h = 0; h < H; h++) {
                  sum_f += W_f[a][h]*h_act[h];
                  sum_m += W_m[a][h]*h_act[h];
                }
                logits_f[a] = sum_f;
                logits_m[a] = sum_m;
                if (sum_f > max_l) max_l = sum_f;
                if (sum_m > max_l) max_l = sum_m;
              }

              //Softmax normalization across 36 classes
              let sum_exp = 0;
              let probs_f = new Array(18);
              let probs_m = new Array(18);

              for (let a = 0; a < 18; a++) {
                probs_f[a] = Math.exp(logits_f[a] - max_l);
                probs_m[a] = Math.exp(logits_m[a] - max_l);
                sum_exp += probs_f[a] + probs_m[a];
              }

              let inv_sum = 1.0/sum_exp;
              for (let a = 0; a < 18; a++) {
                probs_f[a] *= inv_sum;
                probs_m[a] *= inv_sum;
              }

              //Gradients of Cross-Entropy / Softmax: dL/dz_c = prob_c - y_c
              let dL_dz_f = new Array(18);
              let dL_dz_m = new Array(18);
              for (let a = 0; a < 18; a++) {
                let y_f = y[a*2];
                let y_m = y[a*2 + 1];
                dL_dz_f[a] = (probs_f[a] - y_f);
                dL_dz_m[a] = (probs_m[a] - y_m);

                grad_b_f[a] += dL_dz_f[a];
                grad_b_m[a] += dL_dz_m[a];

                for (let h = 0; h < H; h++) {
                  grad_W_f[a][h] += dL_dz_f[a]*h_act[h];
                  grad_W_m[a][h] += dL_dz_m[a]*h_act[h];
                }
              }

              //Backprop to hidden layer
              for (let h = 0; h < H; h++) {
                let dL_dh = 0;
                for (let a = 0; a < 18; a++) {
                  dL_dh += dL_dz_f[a]*W_f[a][h];
                  dL_dh += dL_dz_m[a]*W_m[a][h];
                }
                //Leaky ReLU derivative
                let dact = (h_act[h] > 0) ? 1.0 : 0.01;
                let dL_dpre = dL_dh*dact;

                grad_b1[h] += dL_dpre;
                for (let j = 0; j < K; j++)
                  grad_W1[h][j] += dL_dpre*x[j];
              }
            }

            //Apply Adam weight update with L2 weight decay
            let scale_b = 1.0/b_len;
            let corr1 = 1.0 - Math.pow(beta1, step);
            let corr2 = 1.0 - Math.pow(beta2, step);

            let updateAdam = function (w_matrix, grad_matrix, m_matrix, v_matrix) {
              for (let r = 0; r < w_matrix.length; r++) {
                for (let c = 0; c < w_matrix[r].length; c++) {
                  let g = grad_matrix[r][c]*scale_b + lambda*w_matrix[r][c];
                  m_matrix[r][c] = beta1*m_matrix[r][c] + (1 - beta1)*g;
                  v_matrix[r][c] = beta2*v_matrix[r][c] + (1 - beta2)*g*g;
                  let m_hat = m_matrix[r][c]/corr1;
                  let v_hat = v_matrix[r][c]/corr2;
                  w_matrix[r][c] -= lr*(m_hat / (Math.sqrt(v_hat) + eps));
                }
              }
            };

            let updateAdamVector = function (w_vec, grad_vec, m_vec, v_vec) {
              for (let r = 0; r < w_vec.length; r++) {
                let g = grad_vec[r]*scale_b;
                m_vec[r] = beta1*m_vec[r] + (1 - beta1)*g;
                v_vec[r] = beta2*v_vec[r] + (1 - beta2)*g*g;
                let m_hat = m_vec[r]/corr1;
                let v_hat = v_vec[r]/corr2;
                w_vec[r] -= lr*(m_hat / (Math.sqrt(v_hat) + eps));
              }
            };

            updateAdam(W1, grad_W1, mW1, vW1);
            updateAdamVector(b1, grad_b1, mb1, vb1);
            updateAdam(W_f, grad_W_f, mW_f, vW_f);
            updateAdamVector(b_f, grad_b_f, mb_f, vb_f);
            updateAdam(W_m, grad_W_m, mW_m, vW_m);
            updateAdamVector(b_m, grad_b_m, mb_m, vb_m);
          }
        }

        //Return statement
        return {
          b1: b1,
          b_f: b_f,
          b_m: b_m,
          classes: cohorts,
          covariates: cov_names,
          family: this.family,
          key: this.key,
          name: this.name,
          standardisation: { means: means, sds: sds },
          type: "sgd_separate_curves",
          W1: W1,
          W_f: W_f,
          W_m: W_m
        };
      }

      /**
       * Predicts 36-cohort age-sex distribution vector from a feature vector.
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
        let b1 = model.b1;
        let b_f = model.b_f;
        let b_m = model.b_m;
        let H = b1.length;
        let h_act = new Array(H);
        let K = model.standardisation.means.length;
        let max_l = -Infinity;
        let probs_f = new Array(18);
        let probs_m = new Array(18);
        let result = new Array(36);
        let s_means = model.standardisation.means;
        let s_sds = model.standardisation.sds;
        let sum_exp = 0;
        let W1 = model.W1;
        let W_f = model.W_f;
        let W_m = model.W_m;

        let x_vec = Array.isArray(features) ? features : model.covariates.map(k => features[k] || 0);
        let x_z = new Array(K);
        for (let j = 0; j < K; j++) {
          let z = (x_vec[j] - s_means[j])/s_sds[j];
          x_z[j] = Math.max(-3.0, Math.min(3.0, z));
        }

        //Hidden forward pass
        for (let h = 0; h < H; h++) {
          let sum = b1[h];
          for (let j = 0; j < K; j++) sum += W1[h][j]*x_z[j];
          h_act[h] = (sum > 0) ? sum : sum*0.01;
        }

        //Output logits
        for (let a = 0; a < 18; a++) {
          let sum_f = b_f[a];
          let sum_m = b_m[a];
          for (let h = 0; h < H; h++) {
            sum_f += W_f[a][h]*h_act[h];
            sum_m += W_m[a][h]*h_act[h];
          }
          probs_f[a] = sum_f;
          probs_m[a] = sum_m;
          if (sum_f > max_l) max_l = sum_f;
          if (sum_m > max_l) max_l = sum_m;
        }

        for (let a = 0; a < 18; a++) {
          let ef = Math.exp(probs_f[a] - max_l);
          let em = Math.exp(probs_m[a] - max_l);
          probs_f[a] = ef;
          probs_m[a] = em;
          sum_exp += ef + em;
        }

        let inv_sum = 1.0/sum_exp;
        for (let a = 0; a < 18; a++) {
          result[a*2] = probs_f[a]*inv_sum;
          result[a*2 + 1] = probs_m[a]*inv_sum;
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
