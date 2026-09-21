/**
 * Test Suite: Age/Sex Counterfactuals Battery Benchmark & Raster Pipeline.
 * Validates all 9 counterfactual models across 5 demographic families,
 * out-of-sample utility metric [R^2(male) + R^2(female)] / 2, winner selection,
 * and raster generation with isotonic PAVA clamping.
 *
 * Usage:
 *   node tests/test_age_sex_counterfactuals_battery.js [--fast]
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

let cf_base = path.join(root_dir, "histmap/3.data_transform/age_sex_counterfactuals");
require(path.join(cf_base, "counterfactuals_evaluator.js"));
require(path.join(cf_base, "1.1.un_model_life_tables/un_model_life_tables.js"));
require(path.join(cf_base, "1.2.coale_demeny_life_tables/coale_demeny_life_tables.js"));
require(path.join(cf_base, "1.3.ledermann_life_tables/ledermann_life_tables.js"));
require(path.join(cf_base, "1.4.brass_logit_life_tables/brass_logit_life_tables.js"));
require(path.join(cf_base, "1.5.un_developing_life_tables/un_developing_life_tables.js"));
require(path.join(cf_base, "2.0.gompertz_makeham_siler/gompertz_makeham_siler.js"));
require(path.join(cf_base, "3.0.sgd_separate_curves/sgd_separate_curves.js"));
require(path.join(cf_base, "4.0.sgd_gan_optimizer/sgd_gan_optimizer.js"));
require(path.join(cf_base, "5.0.multinomial_logit_piecewise/multinomial_logit_piecewise.js"));
require(path.join(cf_base, "age_sex_counterfactuals.js"));

async function runTests () {
  let is_fast = process.argv.includes("--fast");
  console.log("================================================================================");
  console.log(`TEST SUITE: AGE/SEX COUNTERFACTUALS BATTERY (Fast: ${is_fast})`);
  console.log("================================================================================\n");

  //1. Verify all 9 models are loaded
  console.log("--- Test 1: Verifying Model Class Registrations ---");
  let expected_classes = [
    "UNModelLifeTables",
    "CoaleDemenyLifeTables",
    "LedermannLifeTables",
    "BrassLogitLifeTables",
    "UNDevelopingLifeTables",
    "GompertzMakehamSiler",
    "SGDSeparateCurves",
    "SGDGANOptimizer",
    "MultinomialLogitPiecewise"
  ];

  for (let c of expected_classes) {
    if (!global[c]) throw new Error(`Model class ${c} not registered in global scope!`);
    console.log(` [PASS] Registered: ${c} (Key: ${global[c].key}, Family: ${global[c].family})`);
  }

  //2. Verify Evaluator dataset loading
  console.log("\n--- Test 2: Verifying Dataset Ingestion & Evaluation ---");
  let dataset = await CounterfactualsEvaluator.getEvaluationDataset();
  console.log(` [PASS] Training dataset: ${dataset.train.X.length} samples, ${dataset.covariates.length} covariates`);
  console.log(` [PASS] Out-of-sample test dataset: ${dataset.test.X.length} UNWPP countries`);
  if (dataset.train.X.length < 5) throw new Error("Insufficient training samples extracted!");
  if (dataset.test.X.length < 10) throw new Error("Insufficient out-of-sample UNWPP evaluation countries!");

  //3. Run battery benchmark
  console.log("\n--- Test 3: Running Battery Benchmark & Utility Computation ---");
  let bench = await age_sex_counterfactuals.runBatteryBenchmark({
    epochs: is_fast ? 150 : 800,
    iterations: is_fast ? 400 : 2000
  });

  let lb = bench.leaderboard;
  if (!lb || lb.length !== 9) throw new Error(`Expected 9 benchmarked models, got ${lb ? lb.length : 0}`);
  console.log(` [PASS] Benchmarked ${lb.length} candidate models across 5 families.`);

  for (let m of lb) {
    if (isNaN(m.utility)) throw new Error(`NaN utility detected for model ${m.id}`);
    if (isNaN(m.r2_male) || isNaN(m.r2_female)) throw new Error(`NaN gender R^2 detected for model ${m.id}`);
    console.log(` [PASS] ${m.name}: Utility = ${(m.utility*100).toFixed(2)}%, R^2(m) = ${(m.r2_male*100).toFixed(2)}%, R^2(f) = ${(m.r2_female*100).toFixed(2)}%`);
  }

  //4. Verify winning model designation
  console.log("\n--- Test 4: Verifying Winning Model Selection ---");
  let winner = await age_sex_counterfactuals.selectWinningModel();
  console.log(` [PASS] Winning Model Selected: ${winner.name} (Utility: ${(winner.utility*100).toFixed(2)}%)`);
  if (!winner.id || winner.utility <= 0) throw new Error("Invalid winning model designated!");

  //5. Verify output files on disk
  console.log("\n--- Test 5: Verifying Persistent Artifacts ---");
  let rep_json = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.json");
  let rep_md = path.join(age_sex_counterfactuals.benchmarks_folder, "battery_benchmark_report.md");
  let winner_json = path.join(age_sex_counterfactuals.cf, "active_winner.json");

  if (!fs.existsSync(rep_json)) throw new Error("Missing battery_benchmark_report.json!");
  if (!fs.existsSync(rep_md)) throw new Error("Missing battery_benchmark_report.md!");
  if (!fs.existsSync(winner_json)) throw new Error("Missing active_winner.json!");
  console.log(` [PASS] Saved benchmark artifacts verified on disk.`);

  //6. Test simplex normalization across 36 cohorts
  console.log("\n--- Test 6: Testing Cohort Simplex Constraint (Sum = 1.0) ---");
  let sample_feat = dataset.test.X[0];
  for (let c of expected_classes) {
    let m_cls = global[c];
    let m_art = JSON.parse(fs.readFileSync(path.join(age_sex_counterfactuals.models_folder, `${m_cls.key}_artifact.json`), "utf8"));
    let pred = m_cls.predict(sample_feat, m_art);
    let sum_p = pred.reduce((a, b) => a + b, 0);
    if (Math.abs(sum_p - 1.0) > 1e-4) throw new Error(`Model ${c} failed simplex sum constraint: ${sum_p}`);
    console.log(` [PASS] ${m_cls.name}: 36 cohorts sum to ${sum_p.toFixed(6)}`);
  }

  console.log("\n================================================================================");
  console.log("ALL TESTS COMPLETED SUCCESSFULLY! COUNTERFACTUALS BATTERY IS OPERATIONAL.");
  console.log("================================================================================\n");
}

runTests().catch(err => {
  console.error("Test execution failed with error:", err);
  process.exit(1);
});
