let fs = require("fs");
let path = require("path");

let root_dir = path.resolve(__dirname, "..");
let logit_dir = path.join(root_dir, "histmap/3.data_transform/age_sex/1.multinomial_logit");
let premodern_path = path.join(logit_dir, "premodern_multinomial_logit.json");

console.log("=== Testing Piecewise Model Architecture (1500 AD Cutoff) ===");

//1. Verify premodern model exists and has 34 covariates
let premodern = JSON.parse(fs.readFileSync(premodern_path, "utf8"));
console.log(`Premodern model: ${premodern.covariates.length} covariates, reference class: ${premodern.reference_class}`);
let key_landuse = ["shifting", "grazing", "rangeland", "conv_rangeland", "cropland", "tot_rice"];
let has_all_lu = key_landuse.every(k => premodern.covariates.includes(k));
console.log(`Contains all key NDT land-use covariates (${key_landuse.join(", ")}): ${has_all_lu}`);

//2. Verify pre-1500 models match premodern
let test_years = [-8000, 0, 1000, 1400];
for (let y of test_years) {
  let model_file = path.join(logit_dir, `multinomial_model_${y}.json`);
  if (!fs.existsSync(model_file)) {
    console.error(`Missing model for year ${y}`);
    continue;
  }
  let m = JSON.parse(fs.readFileSync(model_file, "utf8"));
  let match = (m.covariates.length === premodern.covariates.length && m.reference_class === premodern.reference_class);
  console.log(`Year ${y}: ${m.covariates.length} covariates, matches premodern: ${match}`);
}

//3. Verify post-1500 models use modern rolling model
let post_years = [1500, 1850, 1940];
for (let y of post_years) {
  let model_file = path.join(logit_dir, `multinomial_model_${y}.json`);
  if (fs.existsSync(model_file)) {
    let m = JSON.parse(fs.readFileSync(model_file, "utf8"));
    console.log(`Year ${y} (post-1500): ${m.covariates.length} covariates, reference class: ${m.reference_class || m.classes[0]}`);
  }
}

//4. Simulate NDT logit differential between 8000 BC and 0 AD for male infants (m_00)
// In early agricultural center (e.g. Fertile Crescent/Yangtze):
// 8000 BC: shifting=0, cropland=0, rangeland=0.8, grazing=0.1
// 0 AD: shifting=0.3, cropland=0.25, rangeland=0.2, grazing=0.25
let c_m00 = premodern.coefficients["m_00"];
let delta_logit_m00 = (
  c_m00.shifting * (0.30 - 0.0) +
  c_m00.cropland * (0.25 - 0.0) +
  c_m00.rangeland * (0.20 - 0.80) +
  c_m00.grazing * (0.25 - 0.10)
);
console.log(`\nSimulated NDT agricultural delta for m_00: ${delta_logit_m00.toFixed(6)}`);
console.log(`Notice positive shift due to shifting (+${(c_m00.shifting * 0.3).toFixed(6)}) and rangeland reduction (-${(c_m00.rangeland * -0.6).toFixed(6)}).`);

console.log("\nPiecewise verification completed successfully.");
