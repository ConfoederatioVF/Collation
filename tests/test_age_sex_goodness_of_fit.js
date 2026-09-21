/**
 * Comprehensive Goodness-of-Fit (R^2) Assessment Report for Historical Age/Sex Estimation.
 * Evaluates overall model performance across age-gender curves on both:
 *   1. Historical HMD ground truth (1850, 1900, 1920, 1940)
 *   2. Out-of-sample UNWPP global ground truth (144 countries in 1950)
 *
 * Usage:
 *   node tests/test_age_sex_goodness_of_fit.js
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

let cohorts = age_sex.getCohorts();
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

/**
 * Computes multi-level goodness-of-fit metrics comparing predicted vs actual age-gender distributions:
 *   1. Overall R^2 across all country-cohort data points (total demographic variance explained)
 *   2. Per-country pyramid R^2 (average variance of population pyramid explained per country)
 *   3. Average age-band R^2 (cross-country variance explained per age cohort)
 *   4. Mean Absolute Error (MAE%) and Root Mean Squared Error (RMSE%)
 *   5. Pearson correlation r
 */
let evaluateComprehensiveGoodnessOfFit = function (Y_pred, Y_true, country_labels) {
  let N = Y_true.length;
  let C = cohorts.length; //36 age-gender cohorts

  //1. Global pooled variance explained (Total R^2 across all N x C observations)
  let sum_true = 0;
  let total_points = N * C;
  for (let i = 0; i < N; i++) {
    for (let c = 0; c < C; c++) sum_true += Y_true[i][c];
  }
  let global_mean = sum_true / total_points;

  let global_ss_tot = 0;
  let global_ss_res = 0;
  let sum_abs_err = 0;

  for (let i = 0; i < N; i++) {
    for (let c = 0; c < C; c++) {
      let yt = Y_true[i][c];
      let yp = Y_pred[i][c];
      global_ss_tot += (yt - global_mean) ** 2;
      global_ss_res += (yt - yp) ** 2;
      sum_abs_err += Math.abs(yt - yp);
    }
  }

  let r2_overall = (global_ss_tot > 0) ? 1 - global_ss_res / global_ss_tot : 0;
  let mae_pct = (sum_abs_err / total_points) * 100;
  let rmse_pct = Math.sqrt(global_ss_res / total_points) * 100;

  //2. Per-country population pyramid R^2 and Pearson r
  let country_pyramid_r2 = [];
  let country_pyramid_r = [];
  let per_country_table = [];

  for (let i = 0; i < N; i++) {
    let yt = Y_true[i];
    let yp = Y_pred[i];
    let mean_i = yt.reduce((a, b) => a + b, 0) / C;

    let ss_tot_i = yt.reduce((acc, v) => acc + (v - mean_i) ** 2, 0);
    let ss_res_i = yt.reduce((acc, v, c) => acc + (v - yp[c]) ** 2, 0);
    let r2_i = (ss_tot_i > 0) ? 1 - ss_res_i / ss_tot_i : 0;
    let r_i = calculatePearsonCorrelation(yp, yt);

    country_pyramid_r2.push(r2_i);
    country_pyramid_r.push(r_i);

    let mae_i = yt.reduce((acc, v, c) => acc + Math.abs(v - yp[c]), 0) / C;

    per_country_table.push({
      country: country_labels[i],
      pyramid_r2: (r2_i * 100).toFixed(2) + "%",
      pearson_r: r_i.toFixed(4),
      mae_pct: (mae_i * 100).toFixed(3) + "%"
    });
  }

  let avg_country_r2 = country_pyramid_r2.reduce((a, b) => a + b, 0) / N;
  let avg_country_r = country_pyramid_r.reduce((a, b) => a + b, 0) / N;

  //3. Per-age-band R^2 (18 age groups)
  let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
  let age_band_r2 = [];
  let band_metrics_table = [];

  for (let b = 0; b < age_bands.length; b++) {
    let band = age_bands[b];
    let f_idx = cohorts.indexOf(`f_${band}`);
    let m_idx = cohorts.indexOf(`m_${band}`);

    let yt_band = Y_true.map(row => row[f_idx] + row[m_idx]);
    let yp_band = Y_pred.map(row => row[f_idx] + row[m_idx]);

    let mean_b = yt_band.reduce((a, b) => a + b, 0) / N;
    let ss_tot_b = yt_band.reduce((acc, v) => acc + (v - mean_b) ** 2, 0);
    let ss_res_b = yt_band.reduce((acc, v, idx) => acc + (v - yp_band[idx]) ** 2, 0);
    let r2_b = (ss_tot_b > 0) ? 1 - ss_res_b / ss_tot_b : 0;
    let r_b = calculatePearsonCorrelation(yp_band, yt_band);

    age_band_r2.push(r2_b);
    band_metrics_table.push({
      age_band: band,
      true_mean: (mean_b * 100).toFixed(2) + "%",
      pred_mean: ((yp_band.reduce((a, b) => a + b, 0) / N) * 100).toFixed(2) + "%",
      band_r2: (r2_b * 100).toFixed(2) + "%",
      pearson_r: r_b.toFixed(4)
    });
  }

  let avg_band_r2 = age_band_r2.reduce((a, b) => a + b, 0) / age_bands.length;

  return {
    r2_overall,
    avg_country_r2,
    avg_country_r,
    avg_band_r2,
    mae_pct,
    rmse_pct,
    band_metrics_table,
    per_country_table
  };
};

let trainRegularizedModel = function (X_raw, Y_train, options) {
  let N = X_raw.length;
  let K = training_covs.length;
  let means = new Array(K).fill(0);
  let sds = new Array(K).fill(0);

  for (let j = 0; j < K; j++) {
    let sum = 0;
    for (let i = 0; i < N; i++) sum += X_raw[i][j];
    means[j] = sum / N;
    let sum_sq = 0;
    for (let i = 0; i < N; i++) sum_sq += (X_raw[i][j] - means[j]) ** 2;
    sds[j] = Math.sqrt(sum_sq / N) || 1.0;
  }

  let X_z = X_raw.map(row => row.map((v, j) => (v - means[j]) / sds[j]));

  let model_res = Statistics.multinomialLogitRegression(X_z, Y_train, {
    classes: cohorts,
    debug: false,
    lambda: (options && options.lambda !== undefined) ? options.lambda : 1e-2,
    learning_rate: (options && options.learning_rate !== undefined) ? options.learning_rate : 0.5,
    max_iterations: (options && options.iterations) || 3000,
    proportions: true,
    reference_class: cohorts[0]
  });

  let coeff_obj = {};
  for (let c = 1; c < cohorts.length; c++) {
    coeff_obj[cohorts[c]] = {};
    let scaled_intercept = model_res.beta[c][0];
    let intercept_shift = 0;
    for (let j = 0; j < K; j++) {
      let name = training_covs[j];
      let orig_slope = model_res.beta[c][j + 1] / sds[j];
      coeff_obj[cohorts[c]][name] = orig_slope;
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

let predictModel = function (X_raw, model, clamp_z) {
  let Y_pred = [];
  let clamp = (clamp_z !== undefined) ? clamp_z : 3.0;
  let std = model.standardisation;

  for (let i = 0; i < X_raw.length; i++) {
    let feat = {};
    if (std && clamp > 0) {
      for (let j = 0; j < training_covs.length; j++) {
        let name = training_covs[j];
        let z = (X_raw[i][j] - std.means[j]) / std.sds[j];
        let clamped_z = Math.max(-clamp, Math.min(clamp, z));
        feat[name] = std.means[j] + clamped_z * std.sds[j];
      }
    } else {
      for (let j = 0; j < training_covs.length; j++) feat[training_covs[j]] = X_raw[i][j];
    }
    let prob_obj = Statistics.predictMultinomialProbabilities(feat, model);
    Y_pred.push(cohorts.map(k => prob_obj[k] || 0));
  }
  return Y_pred;
};

//Load HMD data for year
let loadHMDYear = function (year) {
  let raw_hmd_data = age_sex_HMD.A_getHMDObject();
  let geocode_obj = admin_modern.getHMDColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_hmd_raster);
  let pop_path = `${population_Stadester.input_popc_folder}stadester_population_${year}.png`;
  if (!fs.existsSync(pop_path)) return null;
  let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });

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

  let cov_rasters = {};
  for (let k = 0; k < key_covs.length; k++) {
    let entry = age_sex.covariates_obj[key_covs[k]](year);
    let fmt = Array.isArray(entry) ? entry[1] : "float32";
    let p = Array.isArray(entry) ? entry[0] : entry;
    if (fs.existsSync(p)) cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
  }

  let country_covs = {};
  let country_pops = {};
  let total_pixels = geocode_raster.data.length / 4;

  for (let i = 0; i < total_pixels; i++) {
    let r = geocode_raster.data[i * 4];
    let g = geocode_raster.data[i * 4 + 1];
    let b = geocode_raster.data[i * 4 + 2];
    let colour_str = `${r},${g},${b}`;
    let geocodes = colour_to_geocode[colour_str];
    if (!geocodes || geocodes.length === 0) continue;
    let country_code = geocodes[0];
    if (!raw_hmd_data[country_code] || !raw_hmd_data[country_code][String(year)]) continue;

    let pop = stadester_raster.data[i];
    if (pop <= 0 || isNaN(pop)) continue;

    if (!country_pops[country_code]) {
      country_pops[country_code] = 0;
      country_covs[country_code] = {};
      for (let k = 0; k < key_covs.length; k++) country_covs[country_code][key_covs[k]] = 0;
    }

    country_pops[country_code] += pop;
    for (let k = 0; k < key_covs.length; k++) {
      let c_name = key_covs[k];
      let val = cov_rasters[c_name] ? cov_rasters[c_name].data[i] : 0;
      if (!isNaN(val)) country_covs[country_code][c_name] += val * pop;
    }
  }

  let countries = Object.keys(country_pops).filter(c => country_pops[c] > 0);
  let X = [];
  let Y = [];

  for (let c = 0; c < countries.length; c++) {
    let code = countries[c];
    let pop = country_pops[code];
    let x_row = key_covs.map(k => country_covs[code][k] / pop);
    let rel_growth = country_covs[code]["delta_popc_"] / pop;
    x_row.push(rel_growth);
    X.push(x_row);

    let t_entry = raw_hmd_data[code][String(year)];
    let counts = cohorts.map(k => t_entry[k] || 0);
    let tot = counts.reduce((a, b) => a + b, 0);
    Y.push(counts.map(v => (tot > 0 ? v / tot : 0)));
  }

  return { countries, X, Y, year };
};

//Load UNWPP 1950 data
let loadUNWPP1950 = async function () {
  let unwpp_data = await age_sex_UNWPP.A_getUNWPPGroups();
  let iso3_obj = admin_modern.getISO3ColourcodesObject();
  let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
  let pop_path = `${population_Stadester.input_popc_folder}stadester_population_1950.png`;
  let stadester_raster = GeoPNG.loadNumberRasterImage(pop_path, { format: "float32" });

  let cov_rasters = {};
  for (let k = 0; k < key_covs.length; k++) {
    let entry = age_sex.covariates_obj[key_covs[k]](1950);
    let fmt = Array.isArray(entry) ? entry[1] : "float32";
    let p = Array.isArray(entry) ? entry[0] : entry;
    if (fs.existsSync(p)) cov_rasters[key_covs[k]] = GeoPNG.loadNumberRasterImage(p, { format: fmt });
  }

  let country_covs = {};
  let country_pops = {};
  let total_pixels = geocode_raster.data.length / 4;

  for (let i = 0; i < total_pixels; i++) {
    let r = geocode_raster.data[i * 4];
    let g = geocode_raster.data[i * 4 + 1];
    let b = geocode_raster.data[i * 4 + 2];
    let colour_str = `${r},${g},${b}`;
    let iso_code = iso3_obj[colour_str];
    if (!iso_code || !unwpp_data[iso_code] || !unwpp_data[iso_code]["1950"]) continue;

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

  let countries = Object.keys(country_pops).filter(c => country_pops[c] > 1e5 && unwpp_data[c] && unwpp_data[c]["1950"]);
  let X = [];
  let Y = [];

  for (let i = 0; i < countries.length; i++) {
    let code = countries[i];
    let pop = country_pops[code];
    let x_row = key_covs.map(k => country_covs[code][k] / pop);
    let rel_growth = country_covs[code]["delta_popc_"] / pop;
    x_row.push(rel_growth);
    X.push(x_row);

    let counts = cohorts.map(k => unwpp_data[code]["1950"][k] || 0);
    let tot = counts.reduce((a, b) => a + b, 0);
    Y.push(counts.map(v => (tot > 0 ? v / tot : 0)));
  }

  return { countries, X, Y };
};

async function main () {
  console.log("================================================================================");
  console.log("OVERALL DEMOGRAPHIC GOODNESS-OF-FIT (R^2) ASSESSMENT REPORT");
  console.log("Assessing Goodness-of-Fit Across Age-Gender Curves, Pyramids & Age Cohorts");
  console.log("================================================================================\n");

  //SECTION 1: Historical HMD Ground Truth Performance across Epochs
  console.log("--------------------------------------------------------------------------------");
  console.log("PART 1: HISTORICAL EPOCH GOODNESS-OF-FIT (HMD Ground Truth)");
  console.log("--------------------------------------------------------------------------------");

  let test_years = [1850, 1900, 1920, 1940];
  let hmd_summary_table = [];

  for (let y of test_years) {
    let hmd_data = loadHMDYear(y);
    if (!hmd_data) continue;

    //Train peer model with lambda = 1e-2 and evaluate
    let model = trainRegularizedModel(hmd_data.X, hmd_data.Y, { lambda: 1e-2 });
    let Y_pred = predictModel(hmd_data.X, model, 3.0);

    let fit = evaluateComprehensiveGoodnessOfFit(Y_pred, hmd_data.Y, hmd_data.countries);

    hmd_summary_table.push({
      "Historical Epoch": y,
      "HMD Peers": hmd_data.countries.length,
      "Overall Demographic R^2": (fit.r2_overall * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": (fit.avg_country_r2 * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": fit.avg_country_r.toFixed(4),
      "Average Age-Band R^2": (fit.avg_band_r2 * 100).toFixed(2) + "%",
      "Mean Cohort Absolute Error (MAE)": fit.mae_pct.toFixed(3) + "%",
      "RMSE": fit.rmse_pct.toFixed(3) + "%"
    });
  }

  console.table(hmd_summary_table);

  //Detailed 1940 Country-by-Country Pyramid Fit
  console.log("\nYear 1940: Detailed Per-Country Population Pyramid Goodness-of-Fit (17 HMD Peers):");
  let hmd_1940 = loadHMDYear(1940);
  let model_1940 = trainRegularizedModel(hmd_1940.X, hmd_1940.Y, { lambda: 1e-2 });
  let pred_1940 = predictModel(hmd_1940.X, model_1940, 3.0);
  let fit_1940 = evaluateComprehensiveGoodnessOfFit(pred_1940, hmd_1940.Y, hmd_1940.countries);
  console.table(fit_1940.per_country_table);

  //SECTION 2: Out-of-Sample Global UNWPP Performance (144 Countries in 1950)
  console.log("\n--------------------------------------------------------------------------------");
  console.log("PART 2: OUT-OF-SAMPLE GLOBAL GOODNESS-OF-FIT (1950 UNWPP - 144 Countries)");
  console.log("Evaluating Out-of-Sample Generalization on 50/50 Held-out World Countries");
  console.log("--------------------------------------------------------------------------------");

  let unwpp_data = await loadUNWPP1950();
  let N_total = unwpp_data.countries.length;

  //Split into 50% Train (72 countries) and 50% Test (72 held-out countries)
  let indices = [...Array(N_total).keys()];
  for (let i = indices.length - 1; i > 0; i--) {
    let j = (i * 37 + 13) % (i + 1);
    let temp = indices[i];
    indices[i] = indices[j];
    indices[j] = temp;
  }

  let train_idx = indices.slice(0, Math.floor(N_total / 2));
  let test_idx = indices.slice(Math.floor(N_total / 2));

  let X_train = train_idx.map(i => unwpp_data.X[i]);
  let Y_train = train_idx.map(i => unwpp_data.Y[i]);
  let train_countries = train_idx.map(i => unwpp_data.countries[i]);

  let X_test = test_idx.map(i => unwpp_data.X[i]);
  let Y_test = test_idx.map(i => unwpp_data.Y[i]);
  let test_countries = test_idx.map(i => unwpp_data.countries[i]);

  //Train model on 72 countries with optimal lambda = 1e-2
  let global_model = trainRegularizedModel(X_train, Y_train, { lambda: 1e-2 });

  //Evaluate on IN-SAMPLE train countries
  let pred_train = predictModel(X_train, global_model, 3.0);
  let fit_train = evaluateComprehensiveGoodnessOfFit(pred_train, Y_train, train_countries);

  //Evaluate on OUT-OF-SAMPLE held-out test countries
  let pred_test = predictModel(X_test, global_model, 3.0);
  let fit_test = evaluateComprehensiveGoodnessOfFit(pred_test, Y_test, test_countries);

  let unwpp_comparison_table = [
    {
      "Evaluation Dataset": `In-Sample Train (${train_countries.length} countries)`,
      "Overall Demographic R^2": (fit_train.r2_overall * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": (fit_train.avg_country_r2 * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": fit_train.avg_country_r.toFixed(4),
      "Average Age-Band R^2": (fit_train.avg_band_r2 * 100).toFixed(2) + "%",
      "MAE%": fit_train.mae_pct.toFixed(3) + "%",
      "RMSE%": fit_train.rmse_pct.toFixed(3) + "%"
    },
    {
      "Evaluation Dataset": `Out-of-Sample Test (${test_countries.length} held-out countries)`,
      "Overall Demographic R^2": (fit_test.r2_overall * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": (fit_test.avg_country_r2 * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": fit_test.avg_country_r.toFixed(4),
      "Average Age-Band R^2": (fit_test.avg_band_r2 * 100).toFixed(2) + "%",
      "MAE%": fit_test.mae_pct.toFixed(3) + "%",
      "RMSE%": fit_test.rmse_pct.toFixed(3) + "%"
    }
  ];

  console.table(unwpp_comparison_table);

  //Show sample out-of-sample countries from diverse regions
  console.log("\nSample Out-of-Sample Held-out Countries (Pyramid Fit):");
  let sample_countries = ["IND", "BRA", "EGY", "MEX", "ZAF", "IDN", "TUR", "GRC", "POL", "CHL"];
  let sample_table = [];
  for (let sc of sample_countries) {
    let match = fit_test.per_country_table.find(r => r.country === sc);
    if (match) sample_table.push(match);
  }
  console.table(sample_table);

  console.log("\nGoodness-of-Fit Assessment completed successfully.\n");
}

main().catch(console.error);
