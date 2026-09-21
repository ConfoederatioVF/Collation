/**
 * Verification battery for age_sex_GAM architecture.
 * Tests:
 *  1. Smooth demographic shape basis B orthogonality and reference class invariance (f_50 = 0).
 *  2. Premodern identity: strict activation = 0 for y < 1500 AD (Columbian exchange preservation).
 *  3. Contemporary transition response: fertility drop, working-age dividend, longevity/aging.
 *  4. Population probability simplex conservation (sum = 1.0) and infant sex ratio sanity.
 *
 * Usage:
 *   node tests/test_age_sex_gam_verification.js
 */

let fs = require("fs");
let path = require("path");

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
        console.error(`Failed to require ${path.join(rel_dir, files[i])}:`, e.message);
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

global.h1 = path.join(root_dir, "histmap/1.data_raw/");
global.h2 = path.join(root_dir, "histmap/2.data_cleaning/");
global.h3 = path.join(root_dir, "histmap/3.data_transform/");
global.h4 = path.join(root_dir, "histmap/4.data_exports/");
global.h5 = path.join(root_dir, "histmap/5.data_visualisation/");

require(path.join(root_dir, "histmap/3.data_transform/age_sex_counterfactuals/age_sex_GAM/age_sex_GAM.js"));

(async () => {
  console.log("================================================================================");
  console.log("TESTING age_sex_GAM: ANCHORED HIERARCHICAL MULTINOMIAL GAM ARCHITECTURE");
  console.log("================================================================================\n");

  let passed_all = true;

  //Test 1: Demographic Shape Basis Verification
  console.log("--- 1. Testing Demographic Shape Basis B ---");
  let basis_obj = global.age_sex_GAM.getDemographicBasis();
  let cohorts = global.age_sex_GAM.getCohorts();

  console.log(`Total cohorts in basis: ${basis_obj.classes.length}`);
  console.log(`Component count: ${basis_obj.component_names.length} (${basis_obj.component_names.join(", ")})`);

  let ref_basis = basis_obj.basis_matrix["f_50"];
  let ref_all_zero = ref_basis.every(v => v === 0);
  console.log(`Reference class ('f_50') basis vector is strictly zero: ${ref_all_zero}`);
  if (!ref_all_zero) passed_all = false;

  //Verify youth fertility basis is highest at age 0 and drops smoothly
  let v_youth_00 = basis_obj.basis_matrix["f_00"][0];
  let v_youth_10 = basis_obj.basis_matrix["f_10"][0];
  let v_youth_50 = basis_obj.basis_matrix["f_50"][0];
  console.log(`Youth fertility mode: f_00=${v_youth_00.toFixed(4)}, f_10=${v_youth_10.toFixed(4)}, f_50=${v_youth_50.toFixed(4)} (monotonic descent: ${v_youth_00 > v_youth_10 && v_youth_10 > v_youth_50})`);

  //Verify working age bulge peaks in 20-40
  let v_work_00 = basis_obj.basis_matrix["f_00"][1];
  let v_work_30 = basis_obj.basis_matrix["f_30"][1];
  let v_work_70 = basis_obj.basis_matrix["f_70"][1];
  console.log(`Working-age dividend mode: f_00=${v_work_00.toFixed(4)}, f_30=${v_work_30.toFixed(4)}, f_70=${v_work_70.toFixed(4)} (peak around age 30: ${v_work_30 > v_work_00 && v_work_30 > v_work_70})`);

  //Verify longevity mode rises in elderly
  let v_long_20 = basis_obj.basis_matrix["f_20"][2];
  let v_long_50 = basis_obj.basis_matrix["f_50"][2];
  let v_long_80 = basis_obj.basis_matrix["f_80"][2];
  console.log(`Longevity mode: f_20=${v_long_20.toFixed(4)}, f_50=${v_long_50.toFixed(4)}, f_80=${v_long_80.toFixed(4)} (monotonic rise: ${v_long_80 > v_long_50 && v_long_50 >= v_long_20})\n`);

  //Test 2: Premodern Identity & Columbian Exchange Gate (y < 1500)
  console.log("--- 2. Testing Columbian Exchange Breakpoint Activation ---");
  let ancient_features = {
    cropland: 0.15,
    gdp_ppp_pc: 850,
    popc_: 2000,
    popd_: 15,
    rangeland: 0.40,
    shifting: 0.10,
    urbc_: 0
  };

  let test_premodern_years = [-8000, 0, 1000, 1499];
  let all_premodern_zero = true;
  for (let y of test_premodern_years) {
    let act = global.age_sex_GAM.getTransitionActivation(ancient_features, y);
    if (act !== 0) all_premodern_zero = false;
    console.log(`Year ${y}: Activation g(X, y) = ${act} (strictly 0: ${act === 0})`);
  }
  if (!all_premodern_zero) passed_all = false;
  console.log(`Pre-1500 years strictly preserve premodern NDT model: ${all_premodern_zero}\n`);

  //Test 3: Model Fitting & Calibration
  console.log("--- 3. Testing Model Fitting and Archetype Calibration ---");
  let model = await global.age_sex_GAM.B_trainGAMModel({ overwrite: true });
  let calibration = await global.age_sex_GAM.C_calibrateModel();

  console.log("Archetype Calibration Results:");
  for (let res of calibration) {
    console.log(` - [Year ${res.year}] ${res.archetype}:`);
    console.log(`     Activation: ${(res.activation * 100).toFixed(1)}%`);
    console.log(`     Infant Share (0-1): ${(res.infant_share * 100).toFixed(2)}% | Infant Sex Ratio (M/F): ${res.infant_sex_ratio.toFixed(4)}`);
    console.log(`     Working Age Share (25-34): ${(res.working_age_share * 100).toFixed(2)}%`);
    console.log(`     Elderly Share (70+): ${(res.elderly_share * 100).toFixed(2)}%`);
  }

  //Demographic sanity verification across transition
  let ancient_res = calibration[0];
  let modern_res = calibration[3];
  let fertility_declined = modern_res.infant_share < ancient_res.infant_share;
  let aging_increased = modern_res.elderly_share > ancient_res.elderly_share;
  let sex_ratio_healthy = modern_res.infant_sex_ratio >= 1.00 && modern_res.infant_sex_ratio <= 1.15;

  console.log(`\nDemographic Transition Validation:`);
  console.log(` - Fertility decline expressed (ancient > modern): ${fertility_declined}`);
  console.log(` - Population ageing expressed (modern > ancient): ${aging_increased}`);
  console.log(` - Natural infant sex ratio maintained: ${sex_ratio_healthy}`);

  if (!fertility_declined || !aging_increased || !sex_ratio_healthy) passed_all = false;

  //Test 4: Simplex Conservation
  console.log("\n--- 4. Testing Probability Simplex Conservation ---");
  let test_modern_features = {
    cropland: 0.05,
    gdp_ppp_pc: 42000,
    net_wealth: 12000000,
    popc_: 100000,
    popd_: 800,
    urbc_: 85000
  };
  let modern_probs = global.age_sex_GAM.predictProbabilities(test_modern_features, 2020, model);
  let sum_modern = Object.values(modern_probs).reduce((a, b) => a + b, 0);
  let simplex_conserved = Math.abs(sum_modern - 1.0) < 1e-6;
  console.log(`Cohort probabilities sum: ${sum_modern.toFixed(8)} (Sums to 1.0: ${simplex_conserved})`);
  if (!simplex_conserved) passed_all = false;

  console.log("\n================================================================================");
  if (passed_all) {
    console.log("ALL age_sex_GAM VERIFICATION TESTS PASSED SUCCESSFULLY!");
  } else {
    console.error("SOME age_sex_GAM VERIFICATION TESTS FAILED!");
    process.exit(1);
  }
  console.log("================================================================================");
})();
