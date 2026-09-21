//Initialise functions
{
  if (!global.age_sex_counterfactuals)
    /**
     * age_sex_counterfactuals orchestrates the counterfactual demographic battery framework.
     * Evaluates 9 candidate models across 5 methodological families to identify the model
     * with the highest out-of-sample Utility = [R^2(male) + R^2(female)]/2, and generates
     * population rasters clamped to Stadestér with isotonic PAVA smoothing.
     *
     * @class age_sex_counterfactuals
     */
    global.age_sex_counterfactuals = class {
      static cf = `${h3}/age_sex_counterfactuals/`;
      static standardised_targets_folder = `${this.cf}/0.standardised_targets/`;
      static models_folder = `${this.cf}/1.models/`;
      static intermediate_rasters = `${this.cf}/2.rasters/`;
      static intermediate_clamped_rasters = `${this.cf}/3.clamped_to_stadester/`;
      static output_rasters = `${this.cf}/4.composite_cohorts/`;
      static benchmarks_folder = `${this.cf}/benchmarks/`;

      static cases = [
        { folder: "1.1.un_model_life_tables", id: "un_model_life_tables", name: "UN Model Life Tables", file: "un_model_life_tables.js", class_name: "UNModelLifeTables" },
        { folder: "1.2.coale_demeny_life_tables", id: "coale_demeny_life_tables", name: "Coale-Demeny Life Tables", file: "coale_demeny_life_tables.js", class_name: "CoaleDemenyLifeTables" },
        { folder: "1.3.ledermann_life_tables", id: "ledermann_life_tables", name: "Ledermann's Life Tables", file: "ledermann_life_tables.js", class_name: "LedermannLifeTables" },
        { folder: "1.4.brass_logit_life_tables", id: "brass_logit_life_tables", name: "Brass-Logit Model Life Tables", file: "brass_logit_life_tables.js", class_name: "BrassLogitLifeTables" },
        { folder: "1.5.un_developing_life_tables", id: "un_developing_life_tables", name: "UN Life Tables for Developing Countries", file: "un_developing_life_tables.js", class_name: "UNDevelopingLifeTables" },
        { folder: "2.0.gompertz_makeham_siler", id: "gompertz_makeham_siler", name: "Gompertz-Makeham + Siler Modelling", file: "gompertz_makeham_siler.js", class_name: "GompertzMakehamSiler" },
        { folder: "3.0.sgd_separate_curves", id: "sgd_separate_curves", name: "SGD (Separate Curves, Naive Covariates)", file: "sgd_separate_curves.js", class_name: "SGDSeparateCurves" },
        { folder: "4.0.sgd_gan_optimizer", id: "sgd_gan_optimizer", name: "SGD/GAN Parameter Optimiser", file: "sgd_gan_optimizer.js", class_name: "SGDGANOptimizer" },
        { folder: "5.0.multinomial_logit_piecewise", id: "multinomial_logit_piecewise", name: "Multinomial Logit (Piecewise Baseline)", file: "multinomial_logit_piecewise.js", class_name: "MultinomialLogitPiecewise" }
      ];

      /**
       * Initialises all required subdirectories and requires case model definitions.
       */
      static init () {
        //Declare local instance variables
        let dirs = [
          this.standardised_targets_folder,
          this.models_folder,
          this.intermediate_rasters,
          this.intermediate_clamped_rasters,
          this.output_rasters,
          this.benchmarks_folder
        ];

        for (let i = 0; i < dirs.length; i++) {
          if (!fs.existsSync(dirs[i]))
            fs.mkdirSync(dirs[i], { recursive: true });
        }

        //Load sub-case model classes
        for (let i = 0; i < this.cases.length; i++) {
          let item = this.cases[i];
          let p = path.join(this.cf, item.folder, item.file);
          if (fs.existsSync(p)) {
            try {
              require(p);
            } catch (e) {
              console.error(`[age_sex_counterfactuals] Failed to load ${item.id}:`, e);
            }
          }
        }
      }

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
       * Executes the comprehensive battery benchmark across all 9 candidate models.
       * Evaluates out-of-sample R^2(male), R^2(female), and Utility = [R^2(male) + R^2(female)]/2.
       * Ranks all models and designates the winner with highest utility.
       *
       * @param {Object} [arg0_options]
       *
       * @returns {Promise<Object>} Leaderboard report and winning model.
       */
      static async runBatteryBenchmark (arg0_options) {
        //Convert from parameters
        let options = (arg0_options) ? arg0_options : {};

        //Declare local instance variables
        let baseline_utility = 0;
        let dataset = null;
        let leaderboard = [];
        let report_json_path = path.join(this.benchmarks_folder, "battery_benchmark_report.json");
        let report_md_path = path.join(this.benchmarks_folder, "battery_benchmark_report.md");
        let winner_json_path = path.join(this.cf, "active_winner.json");

        this.init();

        console.log("\n================================================================================");
        console.log("AGE/SEX COUNTERFACTUALS BATTERY BENCHMARK");
        console.log("Running Out-of-Sample Utility Evaluation: [R^2(male) + R^2(female)] / 2");
        console.log("================================================================================\n");

        console.log("[age_sex_counterfactuals] Loading empirical HMD and UNWPP evaluation datasets...");
        dataset = await CounterfactualsEvaluator.getEvaluationDataset(options);
        console.log(`[age_sex_counterfactuals] Loaded ${dataset.train.X.length} historical HMD training samples and ${dataset.test.X.length} out-of-sample UNWPP evaluation countries.\n`);

        for (let i = 0; i < this.cases.length; i++) {
          let item = this.cases[i];
          let model_class = global[item.class_name];

          if (!model_class) {
            console.warn(`[WARN] Model class ${item.class_name} not found. Skipping.`);
            continue;
          }

          console.log(`[BATTERY ${i + 1}/${this.cases.length}] Training and evaluating ${item.name}...`);
          let start_time = Date.now();

          let trained_model = model_class.train(dataset.train, options);
          let y_pred = model_class.predictBatch(dataset.test.X, trained_model);
          let elapsed = ((Date.now() - start_time)/1000).toFixed(2);

          let eval_metrics = CounterfactualsEvaluator.evaluateDemographicUtility(
            y_pred,
            dataset.test.Y,
            dataset.cohorts,
            dataset.test.countries
          );

          //Save artifact in model folder and in 1.models/
          let case_artifact_path = path.join(this.cf, item.folder, "model_artifact.json");
          let models_artifact_path = path.join(this.models_folder, `${item.id}_artifact.json`);
          fs.writeFileSync(case_artifact_path, JSON.stringify(trained_model, null, 2));
          fs.writeFileSync(models_artifact_path, JSON.stringify(trained_model, null, 2));

          let entry = {
            id: item.id,
            name: item.name,
            folder: item.folder,
            elapsed_sec: parseFloat(elapsed),
            r2_male: eval_metrics.r2_male,
            r2_female: eval_metrics.r2_female,
            utility: eval_metrics.utility,
            mean_country_utility: eval_metrics.mean_country_utility,
            mean_pyramid_r2: eval_metrics.mean_country_pyramid_r2,
            mae_pct: eval_metrics.mae_pct,
            rmse_pct: eval_metrics.rmse_pct,
            per_country_table: eval_metrics.per_country_table
          };

          if (item.id === "multinomial_logit_piecewise")
            baseline_utility = eval_metrics.utility;

          leaderboard.push(entry);
          console.log(`   -> Utility: ${(entry.utility*100).toFixed(2)}% | R^2(male): ${(entry.r2_male*100).toFixed(2)}% | R^2(female): ${(entry.r2_female*100).toFixed(2)}% | MAE: ${entry.mae_pct.toFixed(3)}% (${elapsed}s)`);
        }

        //Sort leaderboard descending by utility
        leaderboard.sort((a, b) => b.utility - a.utility);

        //Compute delta vs baseline
        for (let i = 0; i < leaderboard.length; i++) {
          leaderboard[i].rank = i + 1;
          leaderboard[i].delta_vs_baseline_pct = (leaderboard[i].utility - baseline_utility)*100;
        }

        let winner = leaderboard[0];
        console.log("\n================================================================================");
        console.log(`WINNING COUNTERFACTUAL MODEL: ${winner.name} (Utility: ${(winner.utility*100).toFixed(2)}%)`);
        console.log("================================================================================\n");

        let summary_table = leaderboard.map(m => ({
          Rank: m.rank,
          Model: m.name,
          "Utility Metric": (m.utility*100).toFixed(2) + "%",
          "R^2 (Male)": (m.r2_male*100).toFixed(2) + "%",
          "R^2 (Female)": (m.r2_female*100).toFixed(2) + "%",
          "MAE%": m.mae_pct.toFixed(3) + "%",
          "RMSE%": m.rmse_pct.toFixed(3) + "%",
          "Delta vs Base": (m.delta_vs_baseline_pct >= 0 ? "+" : "") + m.delta_vs_baseline_pct.toFixed(2) + "%"
        }));
        console.table(summary_table);

        //Save outputs
        let report_data = {
          date: new Date().toISOString(),
          out_of_sample_countries: dataset.test.countries.length,
          historical_hmd_samples: dataset.train.X.length,
          baseline_utility: baseline_utility,
          winner: {
            id: winner.id,
            name: winner.name,
            utility: winner.utility,
            folder: winner.folder
          },
          leaderboard: leaderboard
        };

        fs.writeFileSync(report_json_path, JSON.stringify(report_data, null, 2));
        fs.writeFileSync(winner_json_path, JSON.stringify(report_data.winner, null, 2));

        //Format Markdown report
        let md_content = `# Age/Sex Counterfactuals Battery Benchmark Report\n\n` +
          `**Generated**: ${report_data.date}\n` +
          `**Evaluation**: Out-of-sample across ${report_data.out_of_sample_countries} UNWPP nations (1950)\n` +
          `**Winning Model**: **${winner.name}** with **${(winner.utility*100).toFixed(2)}%** utility metric.\n\n` +
          `| Rank | Model | Utility Metric | R^2 (Male) | R^2 (Female) | MAE (%) | RMSE (%) | Delta vs Base |\n` +
          `|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|\n` +
          summary_table.map(r => `| ${r.Rank} | ${r.Model} | ${r["Utility Metric"]} | ${r["R^2 (Male)"]} | ${r["R^2 (Female)"]} | ${r["MAE%"]} | ${r["RMSE%"]} | ${r["Delta vs Base"]} |`).join("\n") +
          `\n\n*Demographic Utility Function*: [R^2(male) + R^2(female)] / 2\n`;

        fs.writeFileSync(report_md_path, md_content);
        console.log(`[REPORT] Saved benchmark reports to ${report_json_path} and ${report_md_path}`);

        //Return statement
        return {
          leaderboard: leaderboard,
          report: report_data,
          winner: winner
        };
      }

      /**
       * Returns the active winning model, reading from cached active_winner.json or running benchmark.
       *
       * @returns {Promise<Object>}
       */
      static async selectWinningModel () {
        //Declare local instance variables
        let winner_json_path = path.join(this.cf, "active_winner.json");

        if (fs.existsSync(winner_json_path)) {
          try {
            return JSON.parse(fs.readFileSync(winner_json_path, "utf8"));
          } catch (e) {}
        }

        let bench = await this.runBatteryBenchmark();
        //Return statement
        return bench.winner;
      }

      /**
       * Generates cohort probability rasters for specified years using a selected model.
       *
       * @param {string} arg0_model_id
       * @param {Object} [arg1_options]
       *
       * @returns {Promise<Array>}
       */
      static async generateModelRasters (arg0_model_id, arg1_options) {
        //Convert from parameters
        let model_id = arg0_model_id;
        let options = (arg1_options) ? arg1_options : {};

        //Declare local instance variables
        let cohorts = this.getCohorts();
        let model_case = this.cases.find(c => c.id === model_id) || this.cases[0];
        let model_class = global[model_case.class_name];
        let model_path = path.join(this.models_folder, `${model_case.id}_artifact.json`);
        let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
        let years = (options.years) ? options.years : [1850, 1900, 1950];

        this.init();
        if (!fs.existsSync(model_path))
          await this.runBatteryBenchmark(options);

        let model_data = JSON.parse(fs.readFileSync(model_path, "utf8"));
        let out_dir = path.join(this.intermediate_rasters, model_case.id);
        if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

        console.log(`[age_sex_counterfactuals] Generating probability rasters for ${model_case.name} across ${years.length} years...`);

        for (let y = 0; y < years.length; y++) {
          let year = years[y];
          let format_year = (year > 2023) ? 2023 : year;
          let popc_info = age_sex.covariates_obj["popc_"](format_year);

          if (!popc_info || !fs.existsSync(popc_info[0])) {
            console.warn(`[WARN] Stadestér popc raster missing for year ${year}. Skipping.`);
            continue;
          }

          let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
          let total_pixels = popc_raster.data.length;
          let width = popc_raster.width || 4320;
          let height = popc_raster.height || 2160;

          //Load available key covariates
          let key_covs = [
            "gdp_pc", "gdp_ppp_pc", "popd_", "urbc_", "rurc_",
            "delta_popc_", "delta_gdp_pc", "cropland", "pasture"
          ];
          let cov_rasters = {};
          for (let k = 0; k < key_covs.length; k++) {
            let entry = age_sex.covariates_obj[key_covs[k]](format_year);
            let fmt = Array.isArray(entry) ? entry[1] : "float32";
            let p = Array.isArray(entry) ? entry[0] : entry;
            if (fs.existsSync(p))
              cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
          }

          let cohort_buffers = new Array(36);
          for (let c = 0; c < 36; c++)
            cohort_buffers[c] = new Float32Array(total_pixels);

          for (let i = 0; i < total_pixels; i++) {
            let stade_pop = popc_raster.data[i];
            if (stade_pop <= 0 || isNaN(stade_pop)) continue;

            let feat_row = [];
            for (let k = 0; k < key_covs.length; k++) {
              let val = (cov_rasters[key_covs[k]]) ? cov_rasters[key_covs[k]].data[i] : 0;
              feat_row.push(isNaN(val) ? 0 : val);
            }
            //Relative pop growth proxy
            let delta_pop = (cov_rasters["delta_popc_"]) ? cov_rasters["delta_popc_"].data[i] : 0;
            feat_row.push(stade_pop > 0 ? (delta_pop/stade_pop) : 0);

            let pred_dist = model_class.predict(feat_row, model_data);
            for (let c = 0; c < 36; c++)
              cohort_buffers[c][i] = pred_dist[c];
          }

          for (let c = 0; c < 36; c++) {
            let out_file = path.join(out_dir, `prob_${cohorts[c]}_${year}.png`);
            if (!overwrite && fs.existsSync(out_file)) continue;

            await GeoPNG.saveNumberRasterImageAsync({
              data: cohort_buffers[c],
              file_path: out_file,
              format: "float32",
              height: height,
              width: width
            });
          }
          console.log(`[age_sex_counterfactuals] Generated probability rasters for year ${year}.`);
        }
      }

      /**
       * Clamps cohort probabilities to Stadestér total population with PAVA isotonic smoothing.
       *
       * @param {string} arg0_model_id
       * @param {Object} [arg1_options]
       */
      static async clampToStadester (arg0_model_id, arg1_options) {
        //Convert from parameters
        let model_id = arg0_model_id;
        let options = (arg1_options) ? arg1_options : {};

        //Declare local instance variables
        let cohorts = this.getCohorts();
        let in_dir = path.join(this.intermediate_rasters, model_id);
        let out_dir = path.join(this.intermediate_clamped_rasters, model_id);
        let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
        let years = (options.years) ? options.years : [1850, 1900, 1950];

        if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });

        console.log(`[age_sex_counterfactuals] Clamping to Stadestér with isotonic PAVA smoothing (${model_id})...`);

        let num_cohorts = cohorts.length;
        let band_widths = new Float32Array(num_cohorts);
        for (let c = 0; c < num_cohorts; c++)
          band_widths[c] = cohorts[c].endsWith("_00") ? 1 : (cohorts[c].endsWith("_01") ? 4 : 5);

        let f_indices = [];
        let m_indices = [];
        for (let c = 0; c < num_cohorts; c++) {
          if (cohorts[c].startsWith("f_")) f_indices.push(c);
          else m_indices.push(c);
        }

        let age_count = f_indices.length;
        let age_band_widths = new Float32Array(age_count);
        for (let k = 0; k < age_count; k++)
          age_band_widths[k] = band_widths[f_indices[k]];

        for (let y = 0; y < years.length; y++) {
          let year = years[y];
          let format_year = (year > 2023) ? 2023 : year;
          let popc_info = age_sex.covariates_obj["popc_"](format_year);
          if (!popc_info || !fs.existsSync(popc_info[0])) continue;

          let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
          let prob_rasters = {};
          let missing = false;

          for (let c = 0; c < num_cohorts; c++) {
            let p = path.join(in_dir, `prob_${cohorts[c]}_${year}.png`);
            if (!fs.existsSync(p)) { missing = true; break; }
            prob_rasters[cohorts[c]] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
          }
          if (missing) {
            console.warn(`[WARN] Missing prob rasters for year ${year}. Skipping clamping.`);
            continue;
          }

          let total_pixels = popc_raster.data.length;
          let output_buffers = new Array(num_cohorts);
          for (let c = 0; c < num_cohorts; c++)
            output_buffers[c] = new Float32Array(total_pixels);

          let raw_f = new Float32Array(age_count);
          let raw_m = new Float32Array(age_count);
          let f_coupled = new Float32Array(age_count);
          let m_coupled = new Float32Array(age_count);
          let tot_coupled = new Float32Array(age_count);

          for (let i = 0; i < total_pixels; i++) {
            let stade_pop = popc_raster.data[i];
            if (stade_pop <= 0 || isNaN(stade_pop)) continue;

            for (let k = 0; k < age_count; k++) {
              let f_val = prob_rasters[cohorts[f_indices[k]]].data[i];
              let m_val = prob_rasters[cohorts[m_indices[k]]].data[i];
              raw_f[k] = (f_val > 0 && isFinite(f_val)) ? f_val : 0;
              raw_m[k] = (m_val > 0 && isFinite(m_val)) ? m_val : 0;
            }

            Statistics.coupleAgeSexCohorts(raw_m, raw_f, age_band_widths, 0, {
              female_output: f_coupled,
              male_output: m_coupled,
              total_output: tot_coupled
            });

            let sum_rates = 0;
            for (let k = 0; k < age_count; k++) sum_rates += tot_coupled[k];

            if (sum_rates > 0) {
              let scale = stade_pop / sum_rates;
              for (let k = 0; k < age_count; k++) {
                output_buffers[f_indices[k]][i] = f_coupled[k]*scale;
                output_buffers[m_indices[k]][i] = m_coupled[k]*scale;
              }
            } else {
              let even_share = stade_pop / num_cohorts;
              for (let c = 0; c < num_cohorts; c++)
                output_buffers[c][i] = even_share;
            }
          }

          for (let c = 0; c < num_cohorts; c++) {
            let out_p = path.join(out_dir, `global_${cohorts[c]}_${year}.png`);
            if (!overwrite && fs.existsSync(out_p)) continue;

            await GeoPNG.saveNumberRasterImageAsync({
              data: output_buffers[c],
              file_path: out_p,
              format: "float32",
              height: popc_raster.height || 2160,
              width: popc_raster.width || 4320
            });
          }
          console.log(`[age_sex_counterfactuals] Saved clamped rasters for year ${year}.`);
        }
      }

      /**
       * End-to-end processing pipeline for counterfactual rasters.
       *
       * @param {Object} [arg0_options]
       */
      static async processRasters (arg0_options) {
        //Convert from parameters
        let options = (arg0_options) ? arg0_options : {};

        //Declare local instance variables
        let selected_model = options.model_id;

        if (!selected_model) {
          let win = await this.selectWinningModel();
          selected_model = win.id;
        }

        console.log(`[age_sex_counterfactuals] Running full raster pipeline for model: ${selected_model}`);
        await this.generateModelRasters(selected_model, options);
        await this.clampToStadester(selected_model, options);
        console.log(`[age_sex_counterfactuals] Pipeline completed successfully for ${selected_model}.`);
      }
    };
}
