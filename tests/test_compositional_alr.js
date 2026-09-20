let path = require("path");
let fs = require("fs");

global.fs = fs;
global.path = path;
global.ml_matrix = require("ml-matrix");

require("../UF/js/number/number_basic.js");
require("../UF/js/object/object_basic.js");
require("../UF/js/array/array_basic.js");
require("../UF/js/array/array_maths.js");
require("../UF/js/statistics/statistics_compositional.js");

async function runALRTest () {
	console.log("=== Running ALR Compositional Regression Test ===");
	
	let categories = ["agriculture", "manufacturing", "services", "informal_labour"];
	let keys = ["cropland", "urbanisation"];
	let N = 200;
	let X = [];
	let Y = [];
	
	for (let i = 0; i < N; i++) {
		let crop = Math.random();
		let urb = Math.random();
		X.push([crop, urb]);
		
		let s_agri = Math.exp(2.5 * crop - 1.5 * urb);
		let s_manu = Math.exp(0.5 * crop + 1.8 * urb);
		let s_serv = Math.exp(-1.0 * crop + 2.5 * urb);
		let s_info = Math.exp(0.2 * crop + 0.2 * urb);
		let s_tot = s_agri + s_manu + s_serv + s_info;
		
		Y.push([s_agri / s_tot, s_manu / s_tot, s_serv / s_tot, s_info / s_tot]);
	}
	
	let model_path = path.join(__dirname, "test_alr_model.json");
	let model = await Statistics.trainALRModel(model_path, {
		categories: categories,
		keys: keys,
		reference_category: "agriculture",
		X: X,
		Y: Y
	}, { lambda: 1e-3 });
	
	console.assert(model !== null, "Model must not be null");
	console.assert(model.has_intercept === true, "Model must have intercept");
	console.assert(Object.keys(model.coefficients).length === 3, "Non-reference categories must have coefficient blocks");
	
	// Test prediction for high cropland, low urbanisation
	let pred_rural = Statistics.predictALRProbabilities({ cropland: 0.9, urbanisation: 0.05 }, model);
	console.log("Predicted Rural Shares (high cropland):", pred_rural);
	
	// Test prediction for low cropland, high urbanisation
	let pred_urban = Statistics.predictALRProbabilities({ cropland: 0.05, urbanisation: 0.95 }, model);
	console.log("Predicted Urban Shares (high urbanisation):", pred_urban);
	
	// Assertions
	let sum_rural = Object.values(pred_rural).reduce((a, b) => a + b, 0);
	let sum_urban = Object.values(pred_urban).reduce((a, b) => a + b, 0);
	console.assert(Math.abs(sum_rural - 1.0) < 1e-6, `Rural shares must sum to 1.0, got ${sum_rural}`);
	console.assert(Math.abs(sum_urban - 1.0) < 1e-6, `Urban shares must sum to 1.0, got ${sum_urban}`);
	
	console.assert(pred_rural.agriculture > pred_rural.services, "Rural environment must have higher agriculture than services");
	console.assert(pred_urban.services > pred_urban.agriculture, "Urban environment must have higher services than agriculture");
	
	// Clean up temporary test model file
	if (fs.existsSync(model_path)) fs.unlinkSync(model_path);
	
	console.log(">>> ALR Compositional Regression Test Passed! <<<\n");
}

runALRTest().catch((err) => {
	console.error("ALR Test Failed:", err);
	process.exit(1);
});
