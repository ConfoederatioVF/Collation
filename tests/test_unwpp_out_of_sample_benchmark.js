/**
 * Out-of-sample UNWPP benchmark to evaluate model generalization and prevent overfitting.
 * Tests how multinomial logit models (year-specific, global geomean, pooled global, and rolling)
 * predict out-of-sample non-HMD countries across the world in 1950 UNWPP ground truth.
 *
 * Usage:
 *   node tests/test_unwpp_out_of_sample_benchmark.js
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

let calculatePearsonCorrelation = function (x, y) {
  let n = x.length;
  if (n === 0) return 0;

  let sum_x = 0;
  let sum_x_sq = 0;
  let sum_y = 0;
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
  return numerator / Math.sqrt(denom_x * denom_y);
};

//Compute age-band R^2 given predictions and ground truth across countries
let computeAgeBandR2 = function (Y_pred, Y_true, cohorts) {
  let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
  let r2_scores = [];

  for (let b = 0; b < age_bands.length; b++) {
    let band = age_bands[b];
    let f_idx = cohorts.indexOf(`f_${band}`);
    let m_idx = cohorts.indexOf(`m_${band}`);

    let y_t = Y_true.map(row => row[f_idx] + row[m_idx]);
    let y_p = Y_pred.map(row => row[f_idx] + row[m_idx]);

    let mean_true = y_t.reduce((a, b) => a + b, 0) / y_t.length;
    let ss_tot = y_t.reduce((acc, v) => acc + (v - mean_true) ** 2, 0);
    let ss_res = y_t.reduce((acc, v, i) => acc + (v - y_p[i]) ** 2, 0);
    let r2 = (ss_tot > 0) ? 1 - ss_res / ss_tot : 0;
    r2_scores.push(r2);
  }

  let avg_r2 = r2_scores.reduce((a, b) => a + b, 0) / r2_scores.length;
  return { avg_r2, r2_scores };
};

//Train a peer model on given X_raw and Y_train
let trainPeerModel = function (X_raw, Y_train, cohorts, training_covs, options) {
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

  let X_z = X_raw.map(row => row.map((v, j) => (v - means[j]) / sds[j]));

  let model_res = Statistics.multinomialLogitRegression(X_z, Y_train, {
    classes: cohorts,
    debug: false,
    lambda: (options && options.lambda) || 1e-4,
    learning_rate: (options && options.learning_rate) || 0.5,
    max_iterations: (options && options.iterations) || 3000,
    proportions: true,
    reference_class: cohorts[0]
  });

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

  return {
    classes: cohorts,
    coefficients: coeff_obj,
    covariates: training_covs,
    has_intercept: true,
    reference_class: cohorts[0],
    standardisation: { means, sds },
    type: "multinomial_logit"
  };
};

//Predict using a model object for a set of raw feature rows, with outlier clamping
let predictWithModel = function (X_raw, model_data, training_covs, cohorts, options) {
  let Y_pred = [];
  let clamp_z = (options && options.clamp_z !== undefined) ? options.clamp_z : 3.0;
  let std = model_data.standardisation;

  for (let i = 0; i < X_raw.length; i++) {
    let feat = {};
    if (std && clamp_z > 0) {
      //Clamp raw features so their Z-score does not exceed +/- clamp_z
      for (let j = 0; j < training_covs.length; j++) {
        let name = training_covs[j];
        let raw_val = X_raw[i][j];
        let z = (raw_val - std.means[j]) / std.sds[j];
        let clamped_z = Math.max(-clamp_z, Math.min(clamp_z, z));
        feat[name] = std.means[j] + clamped_z * std.sds[j];
      }
    } else {
      for (let j = 0; j < training_covs.length; j++) feat[training_covs[j]] = X_raw[i][j];
    }
    let prob_obj = Statistics.predictMultinomialProbabilities(feat, model_data);
    Y_pred.push(cohorts.map(k => prob_obj[k] || 0));
  }
  return Y_pred;
};

//Construct the Global Geomean Model from an ensemble of trained yearly models
let buildGlobalGeomeanModel = function (models, cohorts, training_covs) {
  let geomean_coeffs = {};
  for (let c = 1; c < cohorts.length; c++) {
    let cohort = cohorts[c];
    geomean_coeffs[cohort] = {};

    let intercept_vals = models.map(m => (m.coefficients && m.coefficients[cohort]) ? m.coefficients[cohort]._intercept : null)
      .filter(v => typeof v === "number" && !isNaN(v));
    geomean_coeffs[cohort]._intercept = Math.weightedGeometricMean(intercept_vals);

    for (let j = 0; j < training_covs.length; j++) {
      let cov_name = training_covs[j];
      let slope_vals = models.map(m => (m.coefficients && m.coefficients[cohort]) ? m.coefficients[cohort][cov_name] : null)
        .filter(v => typeof v === "number" && !isNaN(v));
      geomean_coeffs[cohort][cov_name] = Math.weightedGeometricMean(slope_vals);
    }
  }

  return {
    classes: cohorts,
    coefficients: geomean_coeffs,
    covariates: training_covs,
    has_intercept: true,
    reference_class: cohorts[0],
    type: "multinomial_logit"
  };
};

async function main () {
  console.log("================================================================================");
  console.log("OUT-OF-SAMPLE UNWPP BENCHMARK TEST (1950 GROUND TRUTH)");
  console.log("Evaluating Model Generalization on Unseen Global Countries (Africa, Asia, Americas)");
  console.log("================================================================================\n");

  let cohorts = age_sex.getCohorts();
  let year = 1950;

  console.log("Step 1: Loading UNWPP 1950 Global Demographic Dataset...");
  let unwpp_data = await age_sex_UNWPP.A_getUNWPPGroups();
  let iso3_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
  let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });

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
  let training_covs = [...key_covs, "rel_pop_growth"];

  let cov_rasters = {};
  for (let k = 0; k < key_covs.length; k++) {
    let entry = age_sex.covariates_obj[key_covs[k]](year);
    let fmt = Array.isArray(entry) ? entry[1] : "float32";
    let p = Array.isArray(entry) ? entry[0] : entry;
    if (fs.existsSync(p)) cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
  }

  //Extract population-weighted spatial covariate profiles for every country on Earth in 1950
  let country_covs = {};
  let country_pops = {};
  let total_pixels = geocode_raster.data.length / 4;

  for (let i = 0; i < total_pixels; i++) {
    let r = geocode_raster.data[i * 4];
    let g = geocode_raster.data[i * 4 + 1];
    let b = geocode_raster.data[i * 4 + 2];
    let colour_str = `${r},${g},${b}`;

    let iso_code = iso3_obj[colour_str];
    if (!iso_code) continue;
    if (!unwpp_data[iso_code] || !unwpp_data[iso_code]["1950"]) continue;

    let pop = stadester_raster.data[i];
    if (pop <= 0 || isNaN(pop)) continue;

    if (!country_pops[iso_code]) {
      country_pops[iso_code] = 0;
      country_covs[iso_code] = {};
      for (let k = 0; k < key_covs.length; k++) country_covs[iso_code][key_covs[k]] = 0;
    }

    country_pops[iso_code] += pop;
    for (let k = 0; k < key_covs.length; k++) {
      let c_name = key_covs[k];
      let val = cov_rasters[c_name] ? cov_rasters[c_name].data[i] : 0;
      if (!isNaN(val)) country_covs[iso_code][c_name] += val * pop;
    }
  }

  //HMD Historical Peer ISO3 list (countries that had historical HMD presence)
  let hmd_peer_iso3 = new Set([
    "SWE", "NOR", "DNK", "FIN", "ISL", "GBR", "IRL", "FRA", "BEL", "NLD",
    "CHE", "ITA", "ESP", "PRT", "AUT", "DEU", "USA", "CAN", "AUS", "NZL",
    "CZE", "SVK", "HUN", "BGR", "JPN"
  ]);

  let all_valid_countries = Object.keys(country_pops).filter(c => country_pops[c] > 1e5 && unwpp_data[c] && unwpp_data[c]["1950"]);
  let in_sample_peers = all_valid_countries.filter(c => hmd_peer_iso3.has(c));
  let out_of_sample_countries = all_valid_countries.filter(c => !hmd_peer_iso3.has(c));

  console.log(`Discovered ${all_valid_countries.length} global countries with UNWPP 1950 data.`);
  console.log(` - In-sample HMD peers in 1950: ${in_sample_peers.length} countries (${in_sample_peers.join(", ")})`);
  console.log(` - Out-of-sample UNSEEN countries in 1950: ${out_of_sample_countries.length} countries (e.g. ${out_of_sample_countries.slice(0, 15).join(", ")}...)`);

  //Assemble matrices
  let buildDatasetForCountries = function (country_list) {
    let X = [];
    let Y = [];
    for (let i = 0; i < country_list.length; i++) {
      let code = country_list[i];
      let pop = country_pops[code];
      let x_row = key_covs.map(k => country_covs[code][k] / pop);
      let rel_growth = country_covs[code]["delta_popc_"] / pop;
      x_row.push(rel_growth);
      X.push(x_row);

      let counts = cohorts.map(k => unwpp_data[code]["1950"][k] || 0);
      let tot = counts.reduce((a, b) => a + b, 0);
      Y.push(counts.map(v => (tot > 0 ? v / tot : 0)));
    }
    return { X, Y, countries: country_list };
  };

  let in_sample_data = buildDatasetForCountries(in_sample_peers);
  let out_of_sample_data = buildDatasetForCountries(out_of_sample_countries);
  let all_world_data = buildDatasetForCountries(all_valid_countries);

  console.log("\nStep 2: Training candidate models on in-sample HMD peers...");
  //Model 1: 1950 HMD Peer Model
  let model_1950_peers = trainPeerModel(in_sample_data.X, in_sample_data.Y, cohorts, training_covs, { iterations: 3000 });
  console.log(" - Model 1950 (trained on HMD peers) ready.");

  //Model 2: 1940 Historical HMD Model (load from disk or train)
  let model_1940_path = `${age_sex.intermediate_logit_folder}multinomial_model_1940.json`;
  let model_1940 = fs.existsSync(model_1940_path) ? JSON.parse(fs.readFileSync(model_1940_path, "utf8")) : null;
  console.log(` - Model 1940 Historical loaded: ${!!model_1940}`);

  //Model 3: Global Pooled Model across 1850-1940 anchors
  //Model 3: Global Geomean Model across peer anchors
  let anchor_years = [1850, 1900, 1920, 1940];
  let anchor_models = [];
  for (let y of anchor_years) {
    let p = `${age_sex.intermediate_logit_folder}multinomial_model_${y}.json`;
    if (fs.existsSync(p)) {
      let loaded = JSON.parse(fs.readFileSync(p, "utf8"));
      if (loaded.coefficients && loaded.reference_class === cohorts[0]) {
        anchor_models.push(loaded);
      }
    }
  }
  //Also add 1950 peer model to ensemble
  anchor_models.push(model_1950_peers);
  let global_geomean_model = buildGlobalGeomeanModel(anchor_models, cohorts, training_covs);
  console.log(` - Global Geomean Model synthesized from ${anchor_models.length} peer anchors.`);

  console.log("\nStep 3: Experiment 1 - 50/50 Train/Test Out-of-Sample Cross-Validation on UNWPP 1950...");
  //Shuffle all 144 global countries randomly but deterministically
  let shuffled_countries = [...all_valid_countries].sort((a, b) => a.localeCompare(b));
  //Simple deterministic shuffle
  for (let i = shuffled_countries.length - 1; i > 0; i--) {
    let j = (i * 37 + 13) % (i + 1);
    let temp = shuffled_countries[i];
    shuffled_countries[i] = shuffled_countries[j];
    shuffled_countries[j] = temp;
  }

  let half = Math.floor(shuffled_countries.length / 2);
  let train_countries = shuffled_countries.slice(0, half);
  let test_countries = shuffled_countries.slice(half);

  console.log(` - Training Set: ${train_countries.length} countries (diverse global mix: ${train_countries.slice(0, 8).join(", ")}...)`);
  console.log(` - Out-of-Sample Test Set: ${test_countries.length} countries (held-out: ${test_countries.slice(0, 8).join(", ")}...)`);

  let cv_train_data = buildDatasetForCountries(train_countries);
  let cv_test_data = buildDatasetForCountries(test_countries);

  //Test various regularization lambda values to prevent overfitting
  let lambda_values = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 0.1, 1.0];
  let reg_table = [];

  for (let l = 0; l < lambda_values.length; l++) {
    let lam = lambda_values[l];
    let m = trainPeerModel(cv_train_data.X, cv_train_data.Y, cohorts, training_covs, { iterations: 3000, lambda: lam });

    let pred_train = predictWithModel(cv_train_data.X, m, training_covs, cohorts);
    let pred_test = predictWithModel(cv_test_data.X, m, training_covs, cohorts);

    let res_train = computeAgeBandR2(pred_train, cv_train_data.Y, cohorts);
    let res_test = computeAgeBandR2(pred_test, cv_test_data.Y, cohorts);

    reg_table.push({
      "Regularization Lambda": lam.toExponential(0),
      "In-Sample Train R^2 (72 countries)": (res_train.avg_r2 * 100).toFixed(2) + "%",
      "Out-of-Sample Test R^2 (72 countries)": (res_test.avg_r2 * 100).toFixed(2) + "%",
      "Overfit Gap": ((res_train.avg_r2 - res_test.avg_r2) * 100).toFixed(2) + "%"
    });
  }

  console.table(reg_table);

  console.log("\nStep 4: Experiment 2 - HMD-to-Global Transfer: Blending HMD Model with Global Baseline...");
  //Can an HMD-trained model be blended with a Global Regularizer to achieve strong performance across the globe?
  //Train global baseline model on train_countries
  let best_lambda = 1e-3;
  let global_baseline_model = trainPeerModel(cv_train_data.X, cv_train_data.Y, cohorts, training_covs, { iterations: 3000, lambda: best_lambda });

  //Evaluate on the held-out test_countries
  let pred_hmd_oos = predictWithModel(cv_test_data.X, model_1950_peers, training_covs, cohorts);
  let pred_global_oos = predictWithModel(cv_test_data.X, global_baseline_model, training_covs, cohorts);

  let transfer_table = [];
  let weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];

  for (let w of weights) {
    let w_str = w.toFixed(1);
    let pred_blend = [];
    for (let i = 0; i < cv_test_data.X.length; i++) {
      let r = [];
      for (let c = 0; c < cohorts.length; c++) {
        r.push(w * pred_hmd_oos[i][c] + (1 - w) * pred_global_oos[i][c]);
      }
      pred_blend.push(r);
    }
    let res = computeAgeBandR2(pred_blend, cv_test_data.Y, cohorts);

    transfer_table.push({
      "HMD Model Weight (w)": w_str,
      "Global Model Weight (1-w)": (1 - w).toFixed(1),
      "Out-of-Sample UNWPP R^2 (Held-out 72 countries)": (res.avg_r2 * 100).toFixed(2) + "%"
    });
  }

  console.table(transfer_table);

  console.log("\nStep 5: Cohort Breakdown of the Best Generalizing Model on Out-of-Sample UNWPP Data:");
  let best_test_pred = predictWithModel(cv_test_data.X, global_baseline_model, training_covs, cohorts);
  let best_test_res = computeAgeBandR2(best_test_pred, cv_test_data.Y, cohorts);

  let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
  let breakdown_table = [];
  for (let b = 0; b < age_bands.length; b++) {
    breakdown_table.push({
      age_band: age_bands[b],
      out_of_sample_r2: (best_test_res.r2_scores[b] * 100).toFixed(2) + "%"
    });
  }
  console.table(breakdown_table);
  console.log(`>>> TOTAL OUT-OF-SAMPLE AVERAGE R^2: ${(best_test_res.avg_r2 * 100).toFixed(2)}% <<<\n`);
}

main().catch(console.error);
