/**
 * Focused verification for the M1/M2 age_sex_classifier.
 * Usage: node tests/test_age_sex_classifier.js
 */
let fs = require("fs");
let path = require("path");
global.fs = fs;
global.path = path;
global.JSON5 = require("json5");
try { global.mathjs = require("mathjs"); } catch (error) {}
try { global.ml_matrix = require("ml-matrix"); } catch (error) {}

let root = path.resolve(__dirname, "..");
let loadDirectory = function (relative_path) {
	let directory = path.join(root, relative_path);
	if (!fs.existsSync(directory)) return;
	let files = fs.readdirSync(directory).filter((file) => file.endsWith(".js") && !file.includes("worker"));
	for (let i = 0; i < files.length; i++) require(path.join(directory, files[i]));
};
loadDirectory("UF/js/number");
loadDirectory("UF/js/string");
loadDirectory("UF/js/file");
loadDirectory("UF/js/object");
loadDirectory("UF/js/array");
loadDirectory("UF/js/statistics");

global.h1 = path.join(root, "histmap/1.data_raw/");
global.h2 = path.join(root, "histmap/2.data_cleaning/");
global.h3 = path.join(root, "histmap/3.data_transform/");
global.h4 = path.join(root, "histmap/4.data_exports/");
global.h5 = path.join(root, "histmap/5.data_visualisation/");

let classifier_dir = path.join(root, "histmap/3.data_transform/age_sex_counterfactuals/age_sex_classifier");
require(path.join(classifier_dir, "age_sex_classifier_demography.js"));
require(path.join(classifier_dir, "age_sex_classifier_shocks.js"));
require(path.join(classifier_dir, "age_sex_classifier.js"));
require(path.join(classifier_dir, "age_sex_classifier_rasters.js"));

let assert = function (condition, message) {
	if (!condition) throw new Error(message);
};
let nearlyEqual = function (a, b, tolerance) {
	return Math.abs(a - b) <= (tolerance || 1e-8);
};

(async () => {
	console.log("Testing age_sex_classifier...");

	//Population weights must be mathematically equivalent to row replication.
	let weighted = Statistics.multinomialLogitRegression([[0], [2]], [[1, 0], [0, 1]], {
		classes: ["a", "b"],
		fit_intercept: true,
		learning_rate: 0.1,
		max_iterations: 50,
		momentum: 0,
		proportions: true,
		sample_weights: [3, 1]
	});
	let replicated = Statistics.multinomialLogitRegression([[0], [0], [0], [2]], [[1, 0], [1, 0], [1, 0], [0, 1]], {
		classes: ["a", "b"],
		fit_intercept: true,
		learning_rate: 0.1,
		max_iterations: 50,
		momentum: 0,
		proportions: true
	});
	assert(nearlyEqual(weighted.beta[1][0], replicated.beta[1][0]), "Weighted intercept differs from row replication.");
	assert(nearlyEqual(weighted.beta[1][1], replicated.beta[1][1]), "Weighted slope differs from row replication.");
	assert(weighted.iterations <= 50, "Weighted MNL exceeded the 50-iteration ceiling.");

	//HMD fertility reconstruction must conserve births and yield a finite Euler-Lotka root.
	let reconstruction = age_sex_classifier_demography.reconstructFertilitySchedule(
		1000,
		{ 15: 100, 20: 300, 25: 400, 30: 150, 35: 50 },
		{ 15: 10000, 20: 10000, 25: 10000, 30: 10000, 35: 10000 }
	);
	assert(nearlyEqual(reconstruction.total_births, 1000, 1e-6), "Reconstructed HMD births are not conserved.");
	let intrinsic_growth = age_sex_classifier_demography.solveEulerLotka(
		reconstruction.fertility_rates,
		{ 15: 0.95, 20: 0.94, 25: 0.93, 30: 0.92, 35: 0.90 }
	);
	assert(Number.isFinite(intrinsic_growth), "Euler-Lotka solver returned a non-finite result.");

	//A single transition may not jump over a demographic phase.
	let synthetic_rows = [];
	for (let i = 0; i < 5; i++) {
		for (let j = 0; j < 3; j++) {
			synthetic_rows.push({
				features: { development: i + j*0.01 },
				population: 100,
				stage: `CDT${i + 1}`
			});
		}
	}
	let bayes = age_sex_classifier_demography.fitBayesClassifier(synthetic_rows, ["development"]);
	let constrained = age_sex_classifier_demography.constrainStageSequence([
		{ year: 0, features: { development: 0 } },
		{ year: 1, features: { development: 4 } },
		{ year: 2, features: { development: 4 } }
	], bayes, { initial_weights: [1, 0, 0, 0, 0], stay_probability: 0.5 });
	for (let i = 1; i < constrained.length; i++) {
		let previous = Number(constrained[i - 1].stage.slice(3));
		let current = Number(constrained[i].stage.slice(3));
		assert(current - previous <= 1, "Bayesian M1 skipped a CDT phase.");
		assert(current >= previous, "Bayesian M1 moved backwards instead of delegating the shock to M2.");
	}

	//M1 mixing must remain on the probability simplex.
	let cohorts = age_sex_classifier.getCohorts();
	let uniform_model = {
		type: "multinomial_logit",
		classes: cohorts,
		covariates: ["x"],
		coefficients: {}
	};
	let youth_model = JSON.parse(JSON.stringify(uniform_model));
	youth_model.coefficients.f_00 = { _intercept: 2, x: 0 };
	let mixed = age_sex_classifier.predictM1({ x: 1 }, { CDT1: 0.25, CDT2: 0.75 }, {
		CDT1: uniform_model,
		CDT2: youth_model
	});
	let mixed_total = Object.values(mixed).reduce((sum, value) => sum + value, 0);
	assert(nearlyEqual(mixed_total, 1, 1e-8), "M1 archetype mixture left the simplex.");
	assert(mixed.f_00 > mixed.m_00, "M1 weights did not mix archetype probabilities.");

	//M2 must be sex/cohort specific, non-negative and population conserving.
	let base_counts = Object.fromEntries(cohorts.map((cohort) => [cohort, 100]));
	let synthetic_catalogues = {
		fertility: { shocks: [{
			id: "fertility_test", type: "fertility", start_year: 0, geocodes: ["TST"],
			relative_birth_change: -0.5, sex_weights: { female: 0.5, male: 0.5 }
		}] },
		mortality: { shocks: [{
			id: "mortality_test", type: "mortality", start_year: 0, geocodes: ["TST"],
			population_fraction: 0.02, age_sex_profile: [{ sex: "m", min_age: 15, max_age: 25, weight: 1 }]
		}] },
		migration: { shocks: [{
			id: "migration_test", type: "migration", start_year: 0, geocodes: ["TST"],
			population_fraction: 0.02, age_sex_profile: [{ sex: "f", min_age: 20, max_age: 30, weight: 1 }]
		}] }
	};
	let adjusted = age_sex_classifier.applyM2(base_counts, {
		catalogues: synthetic_catalogues,
		empirical_available: false,
		geocode: "TST",
		year: 0
	});
	let base_total = Object.values(base_counts).reduce((sum, value) => sum + value, 0);
	let adjusted_total = Object.values(adjusted).reduce((sum, value) => sum + value, 0);
	assert(nearlyEqual(base_total, adjusted_total, 1e-6), "M2 did not conserve the Stadestér total.");
	assert(Object.values(adjusted).every((value) => value >= 0), "M2 generated a negative cohort.");
	assert(adjusted.f_00 < base_counts.f_00, "Fertility prior did not reduce the newborn cohort.");
	assert(adjusted.m_20 < base_counts.m_20, "Mortality prior did not reduce its male cohort.");
	assert(adjusted.f_25 > base_counts.f_25, "Migration prior did not increase its female cohort.");

	let empirical = age_sex_classifier.applyM2(base_counts, {
		catalogues: synthetic_catalogues,
		empirical_available: true,
		geocode: "TST",
		year: 0
	});
	assert(cohorts.every((cohort) => empirical[cohort] === base_counts[cohort]), "M2 overrode direct empirical data.");

	//All curated entries must carry provenance and the implementation must not call PAVA.
	for (let type of ["fertility", "migration", "mortality"]) {
		let catalogue = age_sex_classifier.loadM2Catalogues()[type];
		let errors = age_sex_classifier_shocks.validateCatalogue(catalogue, type);
		assert(errors.length === 0, `${type} catalogue validation failed: ${errors.join(" ")}`);
	}
	let implementation = [
		"age_sex_classifier.js", "age_sex_classifier_demography.js",
		"age_sex_classifier_rasters.js", "age_sex_classifier_shocks.js"
	].map((file) => fs.readFileSync(path.join(classifier_dir, file), "utf8")).join("\n");
	assert(!/Statistics\.coupleAgeSexCohorts|pavaDecreasing|clamp_cohorts_isotonic/.test(implementation),
		"age_sex_classifier is coupled to PAVA.");

	console.log("All age_sex_classifier tests passed.");
})().catch((error) => {
	console.error(error.stack || error);
	process.exit(1);
});
