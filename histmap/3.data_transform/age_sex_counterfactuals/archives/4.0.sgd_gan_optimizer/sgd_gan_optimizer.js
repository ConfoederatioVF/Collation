//Initialise functions
{
  if (!global.SGDGANOptimizer)
    /**
     * SGDGANOptimizer implements an adversarial covariate selector and generator.
     * Incorporates a learnable gating layer gamma that selects which covariates (parameters)
     * to train for, optimized jointly against an adversarial discriminator enforcing demographic realism.
     *
     * @class SGDGANOptimizer
     */
    global.SGDGANOptimizer = class {
      static key = "sgd_gan_optimizer";
      static name = "SGD/GAN Parameter Optimiser";
      static family = "Adversarial Optimization";

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
       * Trains the generator with covariate gating and adversarial discriminator.
       *
       * @param {Object} arg0_dataset - { X, Y, covariates, countries }
       * @param {Object} [arg1_options]
       *
       * @returns {Object} Trained generator weights, gating weights, and discriminator state.
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
        let d_H = 16;
        let d_lr = 0.005;
        let epochs = (options.epochs) ? options.epochs : 1000;
        let g_H = 32;
        let g_lr = 0.01;
        let K = (dataset.X.length > 0) ? dataset.X[0].length : 0;
        let cov_names = (dataset.covariates && dataset.covariates.length === K) ?
          dataset.covariates :
          default_covs.slice(0, K);
        let lambda_adv = 0.15;
        let lambda_sparse = 0.005;
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

        //1. Generator weights:
        //Gate vector gamma [K] -> w_gate = sigmoid(gamma)
        let gamma = new Array(K).fill(0.5); //Initially all open
        let W_g1 = []; // [g_H x K]
        let b_g1 = new Array(g_H).fill(0);
        let W_g2 = []; // [36 x g_H]
        let b_g2 = new Array(36).fill(0);

        let g_scale1 = Math.sqrt(2.0/(K + g_H));
        for (let h = 0; h < g_H; h++) {
          W_g1.push(new Array(K));
          for (let j = 0; j < K; j++)
            W_g1[h][j] = (Math.random()*2 - 1)*g_scale1;
        }

        let g_scale2 = Math.sqrt(2.0/(g_H + 36));
        for (let c = 0; c < 36; c++) {
          W_g2.push(new Array(g_H));
          for (let h = 0; h < g_H; h++)
            W_g2[c][h] = (Math.random()*2 - 1)*g_scale2;
        }

        //2. Discriminator weights:
        //Input: 36 cohort proportions -> hidden [d_H] -> 1 logit
        let W_d1 = []; // [d_H x 36]
        let b_d1 = new Array(d_H).fill(0);
        let W_d2 = new Array(d_H); // [1 x d_H]
        let b_d2 = 0;

        let d_scale1 = Math.sqrt(2.0/(36 + d_H));
        for (let h = 0; h < d_H; h++) {
          W_d1.push(new Array(36));
          for (let c = 0; c < 36; c++)
            W_d1[h][c] = (Math.random()*2 - 1)*d_scale1;
          W_d2[h] = (Math.random()*2 - 1)*Math.sqrt(2.0/d_H);
        }

        let sigmoid = function (val) {
          return 1.0 / (1.0 + Math.exp(-Math.max(-10, Math.min(10, val))));
        };

        //Joint adversarial training loop
        for (let epoch = 0; epoch < epochs; epoch++) {
          let batch_size = Math.min(16, N);
          for (let b_start = 0; b_start < N; b_start += batch_size) {
            let b_end = Math.min(N, b_start + batch_size);
            let b_len = b_end - b_start;

            //Compute active gating weights
            let w_gate = gamma.map(g => sigmoid(g));

            for (let b = b_start; b < b_end; b++) {
              let i = b;
              let x_raw = X_z[i];
              let y_real = Y[i];

              //Apply gate: x_gated = x * w_gate
              let x_gated = new Array(K);
              for (let j = 0; j < K; j++) x_gated[j] = x_raw[j]*w_gate[j];

              //Generator forward
              let h_gen = new Array(g_H);
              for (let h = 0; h < g_H; h++) {
                let s = b_g1[h];
                for (let j = 0; j < K; j++) s += W_g1[h][j]*x_gated[j];
                h_gen[h] = (s > 0) ? s : s*0.01;
              }

              let logits_gen = new Array(36);
              let max_l = -Infinity;
              for (let c = 0; c < 36; c++) {
                let s = b_g2[c];
                for (let h = 0; h < g_H; h++) s += W_g2[c][h]*h_gen[h];
                logits_gen[c] = s;
                if (s > max_l) max_l = s;
              }

              let sum_exp = 0;
              let y_fake = new Array(36);
              for (let c = 0; c < 36; c++) {
                let e = Math.exp(logits_gen[c] - max_l);
                y_fake[c] = e;
                sum_exp += e;
              }
              let inv_s = 1.0/sum_exp;
              for (let c = 0; c < 36; c++) y_fake[c] *= inv_s;

              //Discriminator forward on real
              let h_d_real = new Array(d_H);
              for (let h = 0; h < d_H; h++) {
                let s = b_d1[h];
                for (let c = 0; c < 36; c++) s += W_d1[h][c]*y_real[c];
                h_d_real[h] = (s > 0) ? s : s*0.01;
              }
              let d_out_real = b_d2;
              for (let h = 0; h < d_H; h++) d_out_real += W_d2[h]*h_d_real[h];
              let p_real = sigmoid(d_out_real);

              //Discriminator forward on fake
              let h_d_fake = new Array(d_H);
              for (let h = 0; h < d_H; h++) {
                let s = b_d1[h];
                for (let c = 0; c < 36; c++) s += W_d1[h][c]*y_fake[c];
                h_d_fake[h] = (s > 0) ? s : s*0.01;
              }
              let d_out_fake = b_d2;
              for (let h = 0; h < d_H; h++) d_out_fake += W_d2[h]*h_d_fake[h];
              let p_fake = sigmoid(d_out_fake);

              //1. Update Discriminator: minimize -log(p_real) - log(1 - p_fake)
              let grad_d_real = (p_real - 1.0); //dL/d(logit_real)
              let grad_d_fake = p_fake;          //dL/d(logit_fake)

              b_d2 -= d_lr*(grad_d_real + grad_d_fake)/b_len;
              for (let h = 0; h < d_H; h++) {
                W_d2[h] -= d_lr*(grad_d_real*h_d_real[h] + grad_d_fake*h_d_fake[h])/b_len;
                let dh_real = grad_d_real*W_d2[h]*((h_d_real[h] > 0) ? 1.0 : 0.01);
                let dh_fake = grad_d_fake*W_d2[h]*((h_d_fake[h] > 0) ? 1.0 : 0.01);
                b_d1[h] -= d_lr*(dh_real + dh_fake)/b_len;
                for (let c = 0; c < 36; c++)
                  W_d1[h][c] -= d_lr*(dh_real*y_real[c] + dh_fake*y_fake[c])/b_len;
              }

              //2. Update Generator: minimize CrossEntropy(y_fake, y_real) + lambda_adv * -log(p_fake) + lambda_sparse * sum(w_gate)
              let dL_dz = new Array(36);
              //Adversarial gradient backpropagated through discriminator into fake pyramid:
              //dL_adv/dy_fake[c] = (p_fake - 1.0) * sum_h (W_d2[h] * W_d1[h][c] * act')
              for (let c = 0; c < 36; c++) {
                let d_adv_c = 0;
                for (let h = 0; h < d_H; h++) {
                  let act_d = (h_d_fake[h] > 0) ? 1.0 : 0.01;
                  d_adv_c += (p_fake - 1.0)*W_d2[h]*act_d*W_d1[h][c];
                }
                let ce_grad = (y_fake[c] - y_real[c]);
                dL_dz[c] = ce_grad + lambda_adv*d_adv_c;
              }

              //Backprop into generator W_g2, b_g2
              let dL_dhgen = new Array(g_H).fill(0);
              for (let c = 0; c < 36; c++) {
                b_g2[c] -= g_lr*dL_dz[c]/b_len;
                for (let h = 0; h < g_H; h++) {
                  W_g2[c][h] -= g_lr*dL_dz[c]*h_gen[h]/b_len;
                  dL_dhgen[h] += dL_dz[c]*W_g2[c][h];
                }
              }

              //Backprop into generator W_g1, b_g1 and gating gamma
              let dL_dxgated = new Array(K).fill(0);
              for (let h = 0; h < g_H; h++) {
                let dact = (h_gen[h] > 0) ? 1.0 : 0.01;
                let dpre = dL_dhgen[h]*dact;
                b_g1[h] -= g_lr*dpre/b_len;
                for (let j = 0; j < K; j++) {
                  W_g1[h][j] -= g_lr*dpre*x_gated[j]/b_len;
                  dL_dxgated[j] += dpre*W_g1[h][j];
                }
              }

              //Update gating parameter gamma[j]
              for (let j = 0; j < K; j++) {
                let sig = w_gate[j];
                let d_sig = sig*(1.0 - sig);
                let d_gamma = dL_dxgated[j]*x_raw[j]*d_sig + lambda_sparse*d_sig;
                gamma[j] -= g_lr*d_gamma/b_len;
              }
            }
          }
        }

        let final_w_gate = gamma.map(g => sigmoid(g));
        let selected_covariates_obj = {};
        for (let j = 0; j < K; j++) {
          let name = cov_names[j] || `cov_${j}`;
          selected_covariates_obj[name] = final_w_gate[j];
        }

        //Return statement
        return {
          b_g1: b_g1,
          b_g2: b_g2,
          classes: cohorts,
          covariates: cov_names,
          family: this.family,
          gamma: gamma,
          key: this.key,
          name: this.name,
          selected_covariates: selected_covariates_obj,
          standardisation: { means: means, sds: sds },
          type: "sgd_gan_optimizer",
          w_gate: final_w_gate,
          W_g1: W_g1,
          W_g2: W_g2
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
        let b_g1 = model.b_g1;
        let b_g2 = model.b_g2;
        let g_H = b_g1.length;
        let h_gen = new Array(g_H);
        let K = model.standardisation.means.length;
        let max_l = -Infinity;
        let result = new Array(36);
        let s_means = model.standardisation.means;
        let s_sds = model.standardisation.sds;
        let sum_exp = 0;
        let w_gate = model.w_gate;
        let W_g1 = model.W_g1;
        let W_g2 = model.W_g2;

        let x_vec = Array.isArray(features) ? features : model.covariates.map(k => features[k] || 0);
        let x_gated = new Array(K);
        for (let j = 0; j < K; j++) {
          let z = (x_vec[j] - s_means[j])/s_sds[j];
          z = Math.max(-3.0, Math.min(3.0, z));
          x_gated[j] = z*(w_gate[j] || 1.0);
        }

        //Hidden pass
        for (let h = 0; h < g_H; h++) {
          let s = b_g1[h];
          for (let j = 0; j < K; j++) s += W_g1[h][j]*x_gated[j];
          h_gen[h] = (s > 0) ? s : s*0.01;
        }

        //Output logits
        for (let c = 0; c < 36; c++) {
          let s = b_g2[c];
          for (let h = 0; h < g_H; h++) s += W_g2[c][h]*h_gen[h];
          result[c] = s;
          if (s > max_l) max_l = s;
        }

        for (let c = 0; c < 36; c++) {
          let e = Math.exp(result[c] - max_l);
          result[c] = e;
          sum_exp += e;
        }

        let inv_s = (sum_exp > 0) ? (1.0/sum_exp) : (1.0/36);
        for (let c = 0; c < 36; c++)
          result[c] *= inv_s;

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
