/**
 * Helper test CLI to train multinomial logit models for historical years and
 * verify resultant population pyramids across age bands directly against empirical HMD ground truth.
 *
 * Usage:
 *   node tests/test_hmd_multinomial_comparison.js [--year=1940] [--years=1850,1900,1920,1940] [--train] [--mode=peer|raster] [--iterations=3000] [--learning_rate=0.5] [--lambda=1e-4]
 */

let fs = require("fs");
let path = require("path");

//Bootstrap UF environment
global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");

try { global.JSON5 = require("json5"); } catch (e) {}
try { global.mathjs = require("mathjs"); } catch (e) {}
try { global.ml_matrix = require("ml-matrix"); } catch (e) {}

let root_dir = path.resolve(__dirname, "..");

let loadDirectory = function (rel_dir) {
  let full_dir = path.join(root_dir, rel_dir);
  if (fs.existsSync(full_dir)) {
    let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
    for (let i = 0; i < files.length; i++) {
      try {
        require(path.join(full_dir, files[i]));
      } catch (e) {
        console.error(`Failed to require ${path.join(rel_dir, files[i])}:`, e);
      }
    }
  }
};

loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/colour");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/blacktraffic");
loadDirectory("UF/js/statistics");
loadDirectory("UF/js/geospatiale/coords");
loadDirectory("UF/js/geospatiale/operations");
loadDirectory("UF/js/geospatiale/files");
loadDirectory("UF/js/geospatiale/files/png");

//Define Histmap paths
global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

let safeRequire = function (rel_path) {
  let full_path = path.join(root_dir, rel_path);
  if (fs.existsSync(full_path)) {
    try {
      require(full_path);
    } catch (e) {
      console.error(`Failed to require ${rel_path}:`, e);
    }
  }
};

safeRequire("histmap/2.data_cleaning/landuse_HYDE/landuse_HYDE.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/population_Stadester.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_rasters.js");
safeRequire("histmap/2.data_cleaning/population_Stadester/stadester_uud.js");
safeRequire("histmap/2.data_cleaning/metadata_HYDE/metadata_HYDE.js");
safeRequire("histmap/2.data_cleaning/admin_modern/admin_modern.js");
safeRequire("histmap/2.data_cleaning/age_sex_HMD/age_sex_HMD.js");
safeRequire("histmap/2.data_cleaning/age_sex_UNWPP/age_sex_UNWPP.js");
safeRequire("histmap/3.data_transform/age_sex/age_sex.js");
safeRequire("histmap/3.data_transform/GDP_pc/GDP_pc.js");
safeRequire("histmap/3.data_transform/GDP_PPP_pc/GDP_PPP_pc.js");
safeRequire("histmap/3.data_transform/wealth_income/wealth_income.js");
safeRequire("histmap/3.data_transform/GDP_Eoscala.transform/GDP_Eoscala_transform.js");
safeRequire("histmap/3.data_transform/population_Stadester.transform/population_Stadester_transform.js");

/**
 * Calculates Pearson correlation coefficient between two numeric vectors.
 * @param {Array<number>} arg0_x
 * @param {Array<number>} arg1_y
 * @returns {number}
 */
function calculatePearsonCorrelation (arg0_x, arg1_y) {
  //Convert from parameters
  let x = arg0_x;
  let y = arg1_y;

  //Declare local instance variables
  let n = x.length;
  let sum_x = 0;
  let sum_y = 0;
  let sum_x_sq = 0;
  let sum_y_sq = 0;
  let sum_xy = 0;

  for (let i = 0; i < n; i++) {
    sum_x += x[i];
    sum_y += y[i];
    sum_x_sq += x[i] * x[i];
    sum_y_sq += y[i] * y[i];
    sum_xy += x[i] * y[i];
  }

  let numerator = n * sum_xy - sum_x * sum_y;
  let denom_x = n * sum_x_sq - sum_x * sum_x;
  let denom_y = n * sum_y_sq - sum_y * sum_y;

  if (denom_x <= 0 || denom_y <= 0) return 0;

  //Return statement
  return numerator / Math.sqrt(denom_x * denom_y);
}

/**
 * Runs the HMD comparison benchmark for a single year.
 * Evaluates the logical results of the multinomial logit model across all age bands.
 *
 * @param {number} arg0_year
 * @param {Object} [arg1_options]
 */
async function evaluateHMDYear (arg0_year, arg1_options) {
  //Convert from parameters
  let year = arg0_year;
  let options = (arg1_options) ? arg1_options : {};

  //Declare local instance variables
  let cohorts = age_sex.getCohorts();
  let do_train = options.train === true;
  let iterations = options.iterations || 3000;
  let lambda = options.lambda || 1e-4;
  let learning_rate = options.learning_rate || 0.5;
  let mode = options.mode || "peer";
  let model_path = `${age_sex.intermediate_logit_folder}multinomial_model_${year}.json`;

  console.log(`\n================================================================================`);
  console.log(`HMD MULTINOMIAL LOGIT VERIFICATION BENCHMARK - YEAR ${year} (Mode: ${mode.toUpperCase()})`);
  console.log(`Parameters: train = ${do_train}, iterations = ${iterations}, lr = ${learning_rate}, lambda = ${lambda}`);
  console.log(`================================================================================\n`);

  //Load HMD ground truth and spatial index
  let raw_hmd_data = age_sex_HMD.A_getHMDObject();
  let geocode_obj = admin_modern.getHMDColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
  let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
  let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });

  //Map colour strings to geocodes valid for this year
  let colour_to_geocode = {};
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

  //Identify candidate key demographic/economic covariates
  let key_covs = [
    "gdp_pc",
    "gdp_ppp_pc",
    "popd_",
    "urbc_",
    "rurc_",
    "delta_popc_",
    "delta_gdp_pc",
    "cropland",
    "pasture"
  ];

  let cov_rasters = {};
  for (let k = 0; k < key_covs.length; k++) {
    let entry = age_sex.covariates_obj[key_covs[k]](year);
    let fmt = Array.isArray(entry) ? entry[1] : "float32";
    let p = Array.isArray(entry) ? entry[0] : entry;
    if (fs.existsSync(p)) {
      cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
    }
  }

  //Extract population-weighted national spatial covariate profiles for all active HMD peers
  let country_covs = {};
  let country_pixel_indices = {};
  let country_pops = {};
  let total_pixels = geocode_raster.data.length / 4;

  for (let i = 0; i < total_pixels; i++) {
    let w = stadester_raster.data[i];
    if (w <= 0 || isNaN(w)) continue;

    let byte_index = i * 4;
    let colour_key = [
      geocode_raster.data[byte_index],
      geocode_raster.data[byte_index + 1],
      geocode_raster.data[byte_index + 2]
    ].join(",");

    let geocodes = colour_to_geocode[colour_key];
    if (geocodes) {
      let seen_codes = {};
      for (let g = 0; g < geocodes.length; g++) {
        let code = geocodes[g].split(".")[0];
        if (seen_codes[code]) continue;
        seen_codes[code] = true;

        if (!raw_hmd_data[code] || !raw_hmd_data[code][String(year)]) continue;

        if (!country_pixel_indices[code]) country_pixel_indices[code] = [];
        country_pixel_indices[code].push(i);

        country_pops[code] = (country_pops[code] || 0) + w;
        if (!country_covs[code]) {
          country_covs[code] = {};
          for (let k = 0; k < key_covs.length; k++) country_covs[code][key_covs[k]] = 0;
        }
        for (let k = 0; k < key_covs.length; k++) {
          let c_val = cov_rasters[key_covs[k]] ? cov_rasters[key_covs[k]].data[i] : 0;
          country_covs[code][key_covs[k]] += (isNaN(c_val) ? 0 : c_val) * w;
        }
      }
    }
  }

  let active_hmd_countries = Object.keys(country_pops);
  console.log(`Discovered ${active_hmd_countries.length} empirical HMD peer countries in ${year}: ${active_hmd_countries.join(", ")}`);

  //Ground truth country proportions
  let country_truth_props = {};
  for (let c = 0; c < active_hmd_countries.length; c++) {
    let code = active_hmd_countries[c];
    let t_entry = raw_hmd_data[code][String(year)];
    let counts = cohorts.map(k => t_entry[k] || 0);
    let tot = counts.reduce((a, b) => a + b, 0);
    country_truth_props[code] = counts.map(v => (tot > 0 ? v / tot : 0));
  }

  //Assemble training matrix X and Y
  let training_covs = [...key_covs, "rel_pop_growth"];
  let X_raw = [];
  let Y_train = [];

  for (let c = 0; c < active_hmd_countries.length; c++) {
    let code = active_hmd_countries[c];
    let pop = country_pops[code];
    let x_row = key_covs.map(k => country_covs[code][k] / pop);
    let rel_pop_growth = country_covs[code]["delta_popc_"] / pop;
    x_row.push(rel_pop_growth);
    X_raw.push(x_row);
    Y_train.push(country_truth_props[code]);
  }

  //Compute standardisation parameters (mean and standard deviation)
  let N_samples = X_raw.length;
  let K_features = training_covs.length;
  let means = new Array(K_features).fill(0);
  let sds = new Array(K_features).fill(0);

  for (let j = 0; j < K_features; j++) {
    let sum = 0;
    for (let i = 0; i < N_samples; i++) sum += X_raw[i][j];
    means[j] = sum / N_samples;

    let sum_sq = 0;
    for (let i = 0; i < N_samples; i++) sum_sq += (X_raw[i][j] - means[j]) * (X_raw[i][j] - means[j]);
    sds[j] = Math.sqrt(sum_sq / N_samples) || 1.0;
  }

  //Standardise X into Z-scores
  let X_z = X_raw.map(row => row.map((v, j) => (v - means[j]) / sds[j]));

  let model_data = null;

  if (do_train || !fs.existsSync(model_path)) {
    console.log(`[TRAIN] Training country-level peer multinomial logit on ${active_hmd_countries.length} HMD peers...`);

    let model_res = Statistics.multinomialLogitRegression(X_z, Y_train, {
      classes: cohorts,
      debug: false,
      lambda: lambda,
      learning_rate: learning_rate,
      max_iterations: iterations,
      proportions: true,
      reference_class: cohorts[0]
    });

    console.log(`[TRAIN] Peer logit halted: converged = ${model_res.converged} (${model_res.iterations} iterations).`);

    //Convert standardised coefficients back to raw feature space for standard deployment
    //beta_orig[c][j] = beta_scaled[c][j] / sds[j]
    //beta_orig[c][0] = beta_scaled[c][0] - sum_j (beta_scaled[c][j] * means[j] / sds[j])
    let coeff_obj = {};
    for (let c = 1; c < cohorts.length; c++) {
      coeff_obj[cohorts[c]] = {};
      let scaled_intercept = model_res.beta[c][0];
      let intercept_shift = 0;

      for (let j = 0; j < K_features; j++) {
        let cov_name = training_covs[j];
        let orig_slope = model_res.beta[c][j + 1] / sds[j];
        coeff_obj[cohorts[c]][cov_name] = orig_slope;
        intercept_shift += orig_slope * means[j];
      }
      coeff_obj[cohorts[c]]._intercept = scaled_intercept - intercept_shift;
    }

    model_data = {
      key: model_path,
      type: "multinomial_logit",
      classes: cohorts,
      reference_class: cohorts[0],
      covariates: training_covs,
      has_intercept: true,
      coefficients: coeff_obj,
      standardisation: {
        means: means,
        sds: sds
      },
      training: {
        converged: model_res.converged,
        iterations: model_res.iterations,
        lambda: lambda,
        mode: "peer",
        peer_count: active_hmd_countries.length
      }
    };

    if (!fs.existsSync(path.dirname(model_path))) fs.mkdirSync(path.dirname(model_path), { recursive: true });
    fs.writeFileSync(model_path, JSON.stringify(model_data, null, 2));
    console.log(`[MODEL] Saved peer multinomial logit model to ${model_path}.`);
  } else {
    model_data = JSON.parse(fs.readFileSync(model_path, "utf8"));
  }

  //2. Evaluate the direct logical results of the logit model for all HMD peers
  let Y_pred_logit = [];
  for (let i = 0; i < active_hmd_countries.length; i++) {
    let feat = {};
    for (let j = 0; j < K_features; j++) feat[training_covs[j]] = X_raw[i][j];
    let prob_obj = Statistics.predictMultinomialProbabilities(feat, model_data);
    Y_pred_logit.push(cohorts.map(k => prob_obj[k] || 0));
  }

  //3. Compute Overall Demographic R^2 across all N x C observations
  let total_points = active_hmd_countries.length * cohorts.length;
  let sum_true = 0;
  for (let i = 0; i < active_hmd_countries.length; i++) {
    for (let c = 0; c < cohorts.length; c++) sum_true += Y_train[i][c];
  }
  let global_mean = sum_true / total_points;

  let global_ss_tot = 0;
  let global_ss_res = 0;
  let total_abs_err = 0;

  for (let i = 0; i < active_hmd_countries.length; i++) {
    for (let c = 0; c < cohorts.length; c++) {
      let yt = Y_train[i][c];
      let yp = Y_pred_logit[i][c];
      global_ss_tot += (yt - global_mean) ** 2;
      global_ss_res += (yt - yp) ** 2;
      total_abs_err += Math.abs(yt - yp);
    }
  }

  let r2_overall = (global_ss_tot > 0) ? 1 - global_ss_res / global_ss_tot : 0;
  let overall_mae_pct = (total_abs_err / total_points) * 100;
  let overall_rmse_pct = Math.sqrt(global_ss_res / total_points) * 100;

  //4. Compute Age-Band R^2 across all HMD peer countries
  let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
  let age_band_metrics = [];
  let r2_scores = [];

  for (let b = 0; b < age_bands.length; b++) {
    let band = age_bands[b];
    let f_idx = cohorts.indexOf(`f_${band}`);
    let m_idx = cohorts.indexOf(`m_${band}`);

    let y_true = active_hmd_countries.map((_, i) => Y_train[i][f_idx] + Y_train[i][m_idx]);
    let y_pred = active_hmd_countries.map((_, i) => Y_pred_logit[i][f_idx] + Y_pred_logit[i][m_idx]);

    let mean_true = y_true.reduce((a, b) => a + b, 0) / y_true.length;
    let mean_pred = y_pred.reduce((a, b) => a + b, 0) / y_pred.length;

    let ss_tot = y_true.reduce((acc, v) => acc + (v - mean_true) ** 2, 0);
    let ss_res = y_true.reduce((acc, v, i) => acc + (v - y_pred[i]) ** 2, 0);
    let r2 = (ss_tot > 0) ? 1 - ss_res / ss_tot : 0;
    let pearson_r = calculatePearsonCorrelation(y_pred, y_true);

    r2_scores.push(r2);
    age_band_metrics.push({
      age_band: band,
      "hmd_mean_%": (mean_true * 100).toFixed(2) + "%",
      "logit_mean_%": (mean_pred * 100).toFixed(2) + "%",
      ss_res: ss_res.toExponential(2),
      ss_tot: ss_tot.toExponential(2),
      r_squared: r2.toFixed(3),
      pearson_r: pearson_r.toFixed(3)
    });
  }

  let avg_r2 = r2_scores.reduce((a, b) => a + b, 0) / r2_scores.length;

  console.log("--------------------------------------------------------------------------------");
  console.log(`AGE-BAND R^2 ANALYSIS: HMD GROUND TRUTH VS LOGIT LOGICAL RESULTS (${year})`);
  console.log("--------------------------------------------------------------------------------");
  console.table(age_band_metrics);
  console.log(`>>> AVERAGE CROSS-COUNTRY R^2 FOR ISOLATED AGE BANDS (${year}): ${avg_r2.toFixed(4)} (${(avg_r2 * 100).toFixed(2)}% variance explained) <<<\n`);

  //5. Per-Country Evaluation Table with Pyramid R^2
  let country_summary = [];
  let pyramid_r2_list = [];
  let pyramid_r_list = [];

  for (let i = 0; i < active_hmd_countries.length; i++) {
    let country_code = active_hmd_countries[i];
    let y_true = Y_train[i];
    let y_pred = Y_pred_logit[i];

    let mean_i = y_true.reduce((a, b) => a + b, 0) / cohorts.length;
    let ss_tot_i = y_true.reduce((acc, v) => acc + (v - mean_i) ** 2, 0);
    let ss_res_i = y_true.reduce((acc, v, idx) => acc + (v - y_pred[idx]) ** 2, 0);
    let pyramid_r2_i = (ss_tot_i > 0) ? 1 - ss_res_i / ss_tot_i : 0;

    let country_r = calculatePearsonCorrelation(y_pred, y_true);
    let mae = y_pred.reduce((acc, v, idx) => acc + Math.abs(v - y_true[idx]), 0) / cohorts.length;

    pyramid_r2_list.push(pyramid_r2_i);
    pyramid_r_list.push(country_r);

    let pred_d01 = (y_pred[cohorts.indexOf("f_01")] + y_pred[cohorts.indexOf("m_01")]) / 4;
    let pred_d05 = (y_pred[cohorts.indexOf("f_05")] + y_pred[cohorts.indexOf("m_05")]) / 5;
    let truth_d01 = (y_true[cohorts.indexOf("f_01")] + y_true[cohorts.indexOf("m_01")]) / 4;
    let truth_d05 = (y_true[cohorts.indexOf("f_05")] + y_true[cohorts.indexOf("m_05")]) / 5;

    let pred_ratio = (pred_d01 > 0) ? pred_d05 / pred_d01 : 0;
    let truth_ratio = (truth_d01 > 0) ? truth_d05 / truth_d01 : 0;

    country_summary.push({
      country: country_code,
      stadester_pop_m: (country_pops[country_code] / 1e6).toFixed(2),
      pyramid_r2: (pyramid_r2_i * 100).toFixed(2) + "%",
      pearson_r: country_r.toFixed(4),
      mae_pct: (mae * 100).toFixed(3) + "%",
      pred_d05_to_d01: pred_ratio.toFixed(3),
      truth_d05_to_d01: truth_ratio.toFixed(3),
      bulge_status: (pred_ratio > 1.2 && truth_ratio <= 1.1) ? "FAIL" : "PASS"
    });
  }

  let mean_pyramid_r2 = pyramid_r2_list.reduce((a, b) => a + b, 0) / active_hmd_countries.length;
  let mean_pyramid_r = pyramid_r_list.reduce((a, b) => a + b, 0) / active_hmd_countries.length;

  console.log("--------------------------------------------------------------------------------");
  console.log(`PER-COUNTRY POPULATION PYRAMID SUMMARY & GOODNESS-OF-FIT (${year})`);
  console.log("--------------------------------------------------------------------------------");
  console.table(country_summary);

  console.log("\n================================================================================");
  console.log(`OVERALL GOODNESS-OF-FIT (R^2) ASSESSMENT REPORT (${year})`);
  console.log("================================================================================");
  console.log(` - Overall Demographic R^2 (Total Variance Explained):   ${(r2_overall * 100).toFixed(2)}%`);
  console.log(` - Mean Population Pyramid R^2 (Across Peer Nations):    ${(mean_pyramid_r2 * 100).toFixed(2)}%`);
  console.log(` - Mean Population Pyramid Pearson Correlation (r):      ${mean_pyramid_r.toFixed(4)}`);
  console.log(` - Mean Cohort Absolute Error (MAE%):                    ${overall_mae_pct.toFixed(3)}%`);
  console.log(` - Root Mean Squared Error (RMSE%):                      ${overall_rmse_pct.toFixed(3)}%`);
  console.log(` - Average Single-Band Cross-Country R^2:                ${(avg_r2 * 100).toFixed(2)}%`);
  console.log("================================================================================\n");
}

/**
 * Main entry point for CLI.
 */
async function main () {
  let args = process.argv.slice(2);
  let cli_options = {};
  for (let i = 0; i < args.length; i++) {
    let arg = args[i];
    if (arg.startsWith("--")) {
      let parts = arg.slice(2).split("=");
      cli_options[parts[0]] = (parts.length > 1) ? parts[1] : true;
    }
  }

  let years_str = cli_options.years || cli_options.year || "1940";
  let years_list = years_str.split(",").map(s => parseInt(s.trim()));

  for (let i = 0; i < years_list.length; i++) {
    await evaluateHMDYear(years_list[i], {
      iterations: parseInt(cli_options.iterations || 3000),
      lambda: parseFloat(cli_options.lambda || 1e-4),
      learning_rate: parseFloat(cli_options.learning_rate || 0.5),
      mode: cli_options.mode || "peer",
      train: cli_options.train === true || cli_options.train === "true"
    });
  }

  console.log("\nAll requested HMD verification evaluations completed successfully.");
}

main().catch(err => {
  console.error("Fatal error during HMD verification benchmark:", err);
  process.exit(1);
});
