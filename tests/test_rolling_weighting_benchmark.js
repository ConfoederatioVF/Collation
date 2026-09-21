/**
 * Benchmark to test optimal weighting between year-specific models and the global geomean model,
 * and to evaluate a rolling temporal approach to determining age/sex structures.
 *
 * Usage:
 *   node tests/test_rolling_weighting_benchmark.js
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

//Extract features and targets for an anchor year
let loadAnchorData = function (year) {
  let cohorts = age_sex.getCohorts();
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

  let active_countries = Object.keys(country_pops).filter(c => country_pops[c] > 0);
  if (active_countries.length === 0) return null;

  let country_truth_props = {};
  for (let c = 0; c < active_countries.length; c++) {
    let code = active_countries[c];
    let t_entry = raw_hmd_data[code][String(year)];
    let counts = cohorts.map(k => t_entry[k] || 0);
    let tot = counts.reduce((a, b) => a + b, 0);
    country_truth_props[code] = counts.map(v => (tot > 0 ? v / tot : 0));
  }

  let training_covs = [...key_covs, "rel_pop_growth"];
  let X_raw = [];
  let Y_train = [];

  for (let c = 0; c < active_countries.length; c++) {
    let code = active_countries[c];
    let pop = country_pops[code];
    let x_row = key_covs.map(k => country_covs[code][k] / pop);
    let rel_pop_growth = country_covs[code]["delta_popc_"] / pop;
    x_row.push(rel_pop_growth);
    X_raw.push(x_row);
    Y_train.push(country_truth_props[code]);
  }

  return {
    active_countries,
    cohorts,
    country_pops,
    country_truth_props,
    training_covs,
    X_raw,
    Y_train,
    year
  };
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

//Compute comprehensive goodness-of-fit metrics (overall R^2, pyramid R^2, and age-band R^2)
let computeComprehensiveGoodnessOfFit = function (Y_pred, Y_true, cohorts) {
  let N = Y_true.length;
  let C = cohorts.length;
  let age_bands = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];

  //1. Overall Demographic R^2 across all N x C observations
  let sum_true = 0;
  let total_pts = N * C;
  for (let i = 0; i < N; i++) {
    for (let c = 0; c < C; c++) sum_true += Y_true[i][c];
  }
  let global_mean = sum_true / total_pts;

  let ss_tot_global = 0;
  let ss_res_global = 0;
  let sum_abs_err = 0;

  for (let i = 0; i < N; i++) {
    for (let c = 0; c < C; c++) {
      let yt = Y_true[i][c];
      let yp = Y_pred[i][c];
      ss_tot_global += (yt - global_mean) ** 2;
      ss_res_global += (yt - yp) ** 2;
      sum_abs_err += Math.abs(yt - yp);
    }
  }

  let r2_overall = (ss_tot_global > 0) ? 1 - ss_res_global / ss_tot_global : 0;
  let mae_pct = (sum_abs_err / total_pts) * 100;
  let rmse_pct = Math.sqrt(ss_res_global / total_pts) * 100;

  //2. Per-country population pyramid R^2 and Pearson r
  let pyramid_r2_list = [];
  let pyramid_r_list = [];
  for (let i = 0; i < N; i++) {
    let yt = Y_true[i];
    let yp = Y_pred[i];
    let mean_i = yt.reduce((a, b) => a + b, 0) / C;
    let ss_tot_i = yt.reduce((acc, v) => acc + (v - mean_i) ** 2, 0);
    let ss_res_i = yt.reduce((acc, v, c) => acc + (v - yp[c]) ** 2, 0);
    let r2_i = (ss_tot_i > 0) ? 1 - ss_res_i / ss_tot_i : 0;
    let r_i = calculatePearsonCorrelation(yp, yt);
    pyramid_r2_list.push(r2_i);
    pyramid_r_list.push(r_i);
  }
  let mean_pyramid_r2 = pyramid_r2_list.reduce((a, b) => a + b, 0) / N;
  let mean_pyramid_r = pyramid_r_list.reduce((a, b) => a + b, 0) / N;

  //3. Per-age-band R^2 across countries
  let age_band_r2 = [];
  for (let b = 0; b < age_bands.length; b++) {
    let band = age_bands[b];
    let f_idx = cohorts.indexOf(`f_${band}`);
    let m_idx = cohorts.indexOf(`m_${band}`);
    let yt_b = Y_true.map(row => row[f_idx] + row[m_idx]);
    let yp_b = Y_pred.map(row => row[f_idx] + row[m_idx]);
    let mean_b = yt_b.reduce((a, b) => a + b, 0) / N;
    let ss_tot_b = yt_b.reduce((acc, v) => acc + (v - mean_b) ** 2, 0);
    let ss_res_b = yt_b.reduce((acc, v, idx) => acc + (v - yp_b[idx]) ** 2, 0);
    let r2_b = (ss_tot_b > 0) ? 1 - ss_res_b / ss_tot_b : 0;
    age_band_r2.push(r2_b);
  }
  let avg_band_r2 = age_band_r2.reduce((a, b) => a + b, 0) / age_bands.length;

  return {
    avg_r2: avg_band_r2,
    avg_band_r2,
    mae_pct,
    mean_pyramid_r,
    mean_pyramid_r2,
    r2_overall,
    r2_scores: age_band_r2,
    rmse_pct
  };
};

let computeAgeBandR2 = function (Y_pred, Y_true, cohorts) {
  return computeComprehensiveGoodnessOfFit(Y_pred, Y_true, cohorts);
};

//Predict using a model object for a set of raw feature rows
let predictWithModel = function (X_raw, model_data, training_covs, cohorts) {
  let Y_pred = [];
  for (let i = 0; i < X_raw.length; i++) {
    let feat = {};
    for (let j = 0; j < training_covs.length; j++) feat[training_covs[j]] = X_raw[i][j];
    let prob_obj = Statistics.predictMultinomialProbabilities(feat, model_data);
    Y_pred.push(cohorts.map(k => prob_obj[k] || 0));
  }
  return Y_pred;
};

//Construct a Pooled Global Model trained on all empirical country-year observations
let buildPooledGlobalModel = function (anchor_data_map, cohorts, training_covs) {
  let X_all = [];
  let Y_all = [];

  for (let y_str in anchor_data_map) {
    let anchor = anchor_data_map[y_str];
    for (let i = 0; i < anchor.X_raw.length; i++) {
      X_all.push(anchor.X_raw[i]);
      Y_all.push(anchor.Y_train[i]);
    }
  }

  return trainPeerModel(X_all, Y_all, cohorts, training_covs, { iterations: 4000 });
};

//Construct the Global Geomean Model in Standardized Space
let buildStandardizedGlobalGeomeanModel = function (models, anchor_data_map, cohorts, training_covs) {
  //Average the standardized betas across all models
  //Then for any evaluation year, unstandardize using that year's mean and sd
  let year_list = Object.keys(anchor_data_map);
  let K_features = training_covs.length;

  return {
    type: "standardized_geomean",
    classes: cohorts,
    reference_class: cohorts[0],
    covariates: training_covs,
    predictForYear: function (X_raw, year_anchor) {
      let means = year_anchor ? year_anchor.X_raw[0].map((_, j) => {
        let s = 0;
        for (let i = 0; i < year_anchor.X_raw.length; i++) s += year_anchor.X_raw[i][j];
        return s / year_anchor.X_raw.length;
      }) : new Array(K_features).fill(0);

      let sds = year_anchor ? year_anchor.X_raw[0].map((_, j) => {
        let s = 0;
        for (let i = 0; i < year_anchor.X_raw.length; i++) s += (year_anchor.X_raw[i][j] - means[j]) ** 2;
        return Math.sqrt(s / year_anchor.X_raw.length) || 1.0;
      }) : new Array(K_features).fill(1);

      //Compute average standardized betas
      let coeff_obj = {};
      for (let c = 1; c < cohorts.length; c++) {
        let cohort = cohorts[c];
        coeff_obj[cohort] = {};

        //Standardized slope for feature j is beta_raw * sd_j
        let std_slopes = [];
        let std_intercepts = [];

        for (let k = 0; k < year_list.length; k++) {
          let m = models[k];
          let y_anc = anchor_data_map[year_list[k]];
          let m_means = m.standardisation.means;
          let m_sds = m.standardisation.sds;

          let raw_intercept = m.coefficients[cohort]._intercept;
          //std_intercept = raw_intercept + sum_j (raw_slope * mean_j)
          let std_int = raw_intercept;
          for (let j = 0; j < K_features; j++) {
            let raw_sl = m.coefficients[cohort][training_covs[j]];
            std_int += raw_sl * m_means[j];
          }
          std_intercepts.push(std_int);
        }

        let mean_std_intercept = Math.weightedGeometricMean(std_intercepts);

        let intercept_shift = 0;
        for (let j = 0; j < K_features; j++) {
          let std_slopes_j = [];
          for (let k = 0; k < year_list.length; k++) {
            let m = models[k];
            let raw_sl = m.coefficients[cohort][training_covs[j]];
            std_slopes_j.push(raw_sl * m.standardisation.sds[j]);
          }
          let mean_std_slope_j = Math.weightedGeometricMean(std_slopes_j);
          let raw_slope = mean_std_slope_j / sds[j];
          coeff_obj[cohort][training_covs[j]] = raw_slope;
          intercept_shift += raw_slope * means[j];
        }
        coeff_obj[cohort]._intercept = mean_std_intercept - intercept_shift;
      }

      let deployable_model = {
        classes: cohorts,
        coefficients: coeff_obj,
        covariates: training_covs,
        has_intercept: true,
        reference_class: cohorts[0],
        type: "multinomial_logit"
      };

      return predictWithModel(X_raw, deployable_model, training_covs, cohorts);
    }
  };
};

//Construct a Rolling Model for year T using a temporal Gaussian kernel across anchor years
let buildRollingModel = function (target_year, anchor_data_map, cohorts, training_covs, sigma_years) {
  let sigma = sigma_years || 25; //25-year bandwidth
  let X_pooled = [];
  let Y_pooled = [];

  for (let y_str in anchor_data_map) {
    let anchor = anchor_data_map[y_str];
    let dt = Math.abs(anchor.year - target_year);
    //Weight samples by repeating or importance scaling
    let w = Math.exp(-(dt * dt) / (2 * sigma * sigma));
    let repeat = Math.max(1, Math.round(w * 10));

    for (let r = 0; r < repeat; r++) {
      for (let i = 0; i < anchor.X_raw.length; i++) {
        X_pooled.push(anchor.X_raw[i]);
        Y_pooled.push(anchor.Y_train[i]);
      }
    }
  }

  return trainPeerModel(X_pooled, Y_pooled, cohorts, training_covs, { iterations: 3000 });
};

async function main () {
  console.log("================================================================================");
  console.log("TEST: OPTIMAL WEIGHTING BENCHMARK & ROLLING TEMPORAL APPROACH");
  console.log("================================================================================\n");

  let anchor_years = [1850, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940];
  let anchor_data_map = {};

  console.log("Step 1: Loading empirical HMD peer data across historical anchor years...");
  for (let i = 0; i < anchor_years.length; i++) {
    let y = anchor_years[i];
    let data = loadAnchorData(y);
    if (data && data.active_countries.length >= 5) {
      anchor_data_map[String(y)] = data;
      console.log(` - Year ${y}: ${data.active_countries.length} empirical HMD peers found (${data.active_countries.join(", ")})`);
    } else {
      console.log(` - Year ${y}: Skipped (insufficient peers)`);
    }
  }

  let cohorts = age_sex.getCohorts();
  let training_covs = Object.values(anchor_data_map)[0].training_covs;

  console.log("\nStep 2: Training year-specific models for each anchor year...");
  let year_models = {};
  let model_array = [];
  for (let y_str in anchor_data_map) {
    let anchor = anchor_data_map[y_str];
    year_models[y_str] = trainPeerModel(anchor.X_raw, anchor.Y_train, cohorts, training_covs, { iterations: 3000 });
    model_array.push(year_models[y_str]);
    console.log(` - Model trained for ${y_str}`);
  }

  console.log("\nStep 3: Building Global Models (Pooled Global & Standardized Geomean)...");
  let pooled_global_model = buildPooledGlobalModel(anchor_data_map, cohorts, training_covs);
  let std_geomean_model = buildStandardizedGlobalGeomeanModel(model_array, anchor_data_map, cohorts, training_covs);
  console.log(" - Pooled Global Model trained successfully.");
  console.log(" - Standardized Global Geomean Model synthesized successfully.");

  console.log("\nStep 4: Evaluating Optimal Weighting Schemes on Key Benchmark Years (1850, 1900, 1920, 1940)...");
  let test_years = [1850, 1900, 1920, 1940];
  let weights = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];

  //A. Evaluate Year-Specific vs Pooled Global Model
  console.log("\n--- BENCHMARK A: YEAR-SPECIFIC MODEL (w) vs POOLED GLOBAL MODEL (1-w) ---");
  let pooled_weight_table = [];
  for (let w of weights) {
    let w_str = w.toFixed(1);
    let row = { "Year Model (w)": w_str, "Pooled Global (1-w)": (1 - w).toFixed(1) };
    let sum_overall_r2 = 0;
    let sum_pyramid_r2 = 0;
    let sum_mae = 0;

    for (let t = 0; t < test_years.length; t++) {
      let year = test_years[t];
      let anchor = anchor_data_map[String(year)];
      let pred_year = predictWithModel(anchor.X_raw, year_models[String(year)], training_covs, cohorts);
      let pred_pooled = predictWithModel(anchor.X_raw, pooled_global_model, training_covs, cohorts);

      let pred_blend = [];
      for (let i = 0; i < anchor.X_raw.length; i++) {
        let r = [];
        for (let c = 0; c < cohorts.length; c++) r.push(w * pred_year[i][c] + (1 - w) * pred_pooled[i][c]);
        pred_blend.push(r);
      }
      let res = computeAgeBandR2(pred_blend, anchor.Y_train, cohorts);
      sum_overall_r2 += res.r2_overall;
      sum_pyramid_r2 += res.mean_pyramid_r2;
      sum_mae += res.mae_pct;
    }
    row["Overall Demographic R^2"] = ((sum_overall_r2 / test_years.length) * 100).toFixed(2) + "%";
    row["Mean Pyramid R^2"] = ((sum_pyramid_r2 / test_years.length) * 100).toFixed(2) + "%";
    row["Mean Cohort MAE%"] = (sum_mae / test_years.length).toFixed(3) + "%";
    pooled_weight_table.push(row);
  }
  console.table(pooled_weight_table);

  //B. Evaluate Year-Specific vs Standardized Global Geomean Model
  console.log("\n--- BENCHMARK B: YEAR-SPECIFIC MODEL (w) vs STANDARDIZED GLOBAL GEOMEAN MODEL (1-w) ---");
  let geomean_weight_table = [];
  for (let w of weights) {
    let w_str = w.toFixed(1);
    let row = { "Year Model (w)": w_str, "Global Geomean (1-w)": (1 - w).toFixed(1) };
    let sum_overall_r2 = 0;
    let sum_pyramid_r2 = 0;
    let sum_mae = 0;

    for (let t = 0; t < test_years.length; t++) {
      let year = test_years[t];
      let anchor = anchor_data_map[String(year)];
      let pred_year = predictWithModel(anchor.X_raw, year_models[String(year)], training_covs, cohorts);
      let pred_geom = std_geomean_model.predictForYear(anchor.X_raw, anchor);

      let pred_blend = [];
      for (let i = 0; i < anchor.X_raw.length; i++) {
        let r = [];
        for (let c = 0; c < cohorts.length; c++) r.push(w * pred_year[i][c] + (1 - w) * pred_geom[i][c]);
        pred_blend.push(r);
      }
      let res = computeAgeBandR2(pred_blend, anchor.Y_train, cohorts);
      sum_overall_r2 += res.r2_overall;
      sum_pyramid_r2 += res.mean_pyramid_r2;
      sum_mae += res.mae_pct;
    }
    row["Overall Demographic R^2"] = ((sum_overall_r2 / test_years.length) * 100).toFixed(2) + "%";
    row["Mean Pyramid R^2"] = ((sum_pyramid_r2 / test_years.length) * 100).toFixed(2) + "%";
    row["Mean Cohort MAE%"] = (sum_mae / test_years.length).toFixed(3) + "%";
    geomean_weight_table.push(row);
  }
  console.table(geomean_weight_table);

  //C. Evaluate Rolling Temporal Window Model (with inclusive and LOYO)
  console.log("\n--- BENCHMARK C: ROLLING TEMPORAL WINDOW MODEL EVALUATION ---");
  let rolling_summary = [];
  let model_totals = {
    year_specific: { overall_r2: 0, pyramid_r2: 0, r: 0, mae: 0, rmse: 0 },
    pooled_global: { overall_r2: 0, pyramid_r2: 0, r: 0, mae: 0, rmse: 0 },
    std_geomean: { overall_r2: 0, pyramid_r2: 0, r: 0, mae: 0, rmse: 0 },
    rolling_narrow: { overall_r2: 0, pyramid_r2: 0, r: 0, mae: 0, rmse: 0 },
    rolling_blend: { overall_r2: 0, pyramid_r2: 0, r: 0, mae: 0, rmse: 0 }
  };

  for (let t = 0; t < test_years.length; t++) {
    let year = test_years[t];
    let anchor = anchor_data_map[String(year)];

    //1. Pure year-specific model
    let pred_year = predictWithModel(anchor.X_raw, year_models[String(year)], training_covs, cohorts);
    let res_year = computeAgeBandR2(pred_year, anchor.Y_train, cohorts);

    //2. Pooled global model
    let pred_pooled = predictWithModel(anchor.X_raw, pooled_global_model, training_covs, cohorts);
    let res_pooled = computeAgeBandR2(pred_pooled, anchor.Y_train, cohorts);

    //3. Standardized global geomean model
    let pred_geom = std_geomean_model.predictForYear(anchor.X_raw, anchor);
    let res_geom = computeAgeBandR2(pred_geom, anchor.Y_train, cohorts);

    //4. Rolling model with 15-year Gaussian bandwidth
    let rolling_narrow = buildRollingModel(year, anchor_data_map, cohorts, training_covs, 15);
    let pred_roll_nar = predictWithModel(anchor.X_raw, rolling_narrow, training_covs, cohorts);
    let res_roll_nar = computeAgeBandR2(pred_roll_nar, anchor.Y_train, cohorts);

    //5. Blend: 80% Rolling (15y) + 20% Global Geomean
    let pred_roll_blend = [];
    for (let i = 0; i < anchor.X_raw.length; i++) {
      let r = [];
      for (let c = 0; c < cohorts.length; c++) r.push(0.8 * pred_roll_nar[i][c] + 0.2 * pred_geom[i][c]);
      pred_roll_blend.push(r);
    }
    let res_roll_blend = computeAgeBandR2(pred_roll_blend, anchor.Y_train, cohorts);

    //Accumulate totals
    let accumulate = function (cat, res) {
      model_totals[cat].overall_r2 += res.r2_overall;
      model_totals[cat].pyramid_r2 += res.mean_pyramid_r2;
      model_totals[cat].r += res.mean_pyramid_r;
      model_totals[cat].mae += res.mae_pct;
      model_totals[cat].rmse += res.rmse_pct;
    };
    accumulate("year_specific", res_year);
    accumulate("pooled_global", res_pooled);
    accumulate("std_geomean", res_geom);
    accumulate("rolling_narrow", res_roll_nar);
    accumulate("rolling_blend", res_roll_blend);

    rolling_summary.push({
      "Test Year": year,
      "Year-Specific Pyramid R^2": (res_year.mean_pyramid_r2 * 100).toFixed(2) + "%",
      "Rolling (15y) Pyramid R^2": (res_roll_nar.mean_pyramid_r2 * 100).toFixed(2) + "%",
      "Rolling 80% + Global 20% Pyramid R^2": (res_roll_blend.mean_pyramid_r2 * 100).toFixed(2) + "%",
      "Overall Demographic R^2 (Blend)": (res_roll_blend.r2_overall * 100).toFixed(2) + "%",
      "Mean Cohort MAE%": res_roll_blend.mae_pct.toFixed(3) + "%"
    });
  }
  console.table(rolling_summary);

  //D. Comprehensive Overall Goodness-of-Fit Performance Summary Table
  let N_tests = test_years.length;
  console.log("\n================================================================================");
  console.log("OVERALL MODEL GOODNESS-OF-FIT (R^2) PERFORMANCE SUMMARY");
  console.log("Averaged across all Historical Epochs (1850, 1900, 1920, 1940)");
  console.log("================================================================================");

  let overall_summary_table = [
    {
      "Model Architecture": "Pure Year-Specific Anchor Model",
      "Overall Demographic R^2": ((model_totals.year_specific.overall_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": ((model_totals.year_specific.pyramid_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": (model_totals.year_specific.r / N_tests).toFixed(4),
      "Mean Cohort MAE%": (model_totals.year_specific.mae / N_tests).toFixed(3) + "%",
      "RMSE%": (model_totals.year_specific.rmse / N_tests).toFixed(3) + "%"
    },
    {
      "Model Architecture": "Pooled Global Historical Model",
      "Overall Demographic R^2": ((model_totals.pooled_global.overall_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": ((model_totals.pooled_global.pyramid_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": (model_totals.pooled_global.r / N_tests).toFixed(4),
      "Mean Cohort MAE%": (model_totals.pooled_global.mae / N_tests).toFixed(3) + "%",
      "RMSE%": (model_totals.pooled_global.rmse / N_tests).toFixed(3) + "%"
    },
    {
      "Model Architecture": "Standardized Global Geomean Model",
      "Overall Demographic R^2": ((model_totals.std_geomean.overall_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": ((model_totals.std_geomean.pyramid_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": (model_totals.std_geomean.r / N_tests).toFixed(4),
      "Mean Cohort MAE%": (model_totals.std_geomean.mae / N_tests).toFixed(3) + "%",
      "RMSE%": (model_totals.std_geomean.rmse / N_tests).toFixed(3) + "%"
    },
    {
      "Model Architecture": "Rolling Temporal Window Model (15y Bandwidth)",
      "Overall Demographic R^2": ((model_totals.rolling_narrow.overall_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": ((model_totals.rolling_narrow.pyramid_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": (model_totals.rolling_narrow.r / N_tests).toFixed(4),
      "Mean Cohort MAE%": (model_totals.rolling_narrow.mae / N_tests).toFixed(3) + "%",
      "RMSE%": (model_totals.rolling_narrow.rmse / N_tests).toFixed(3) + "%"
    },
    {
      "Model Architecture": "Optimal Blend: 80% Rolling Anchor + 20% Global Baseline",
      "Overall Demographic R^2": ((model_totals.rolling_blend.overall_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid R^2": ((model_totals.rolling_blend.pyramid_r2 / N_tests) * 100).toFixed(2) + "%",
      "Mean Pyramid Pearson r": (model_totals.rolling_blend.r / N_tests).toFixed(4),
      "Mean Cohort MAE%": (model_totals.rolling_blend.mae / N_tests).toFixed(3) + "%",
      "RMSE%": (model_totals.rolling_blend.rmse / N_tests).toFixed(3) + "%"
    }
  ];

  console.table(overall_summary_table);
  console.log("Goodness-of-Fit Assessment completed successfully.\n");
}

main().catch(console.error);
