const fs = require("fs");
const path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
global.mathjs = require("mathjs");
let root_dir = path.resolve(".");

let loadDirectory = function (rel_dir) {
	let full_dir = path.join(root_dir, rel_dir);
	if (fs.existsSync(full_dir)) {
		let files = fs.readdirSync(full_dir).filter(f => f.endsWith(".js") && !f.includes("worker"));
		for (let i = 0; i < files.length; i++) require(path.join(full_dir, files[i]));
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

require(path.join(h2, "metadata_HYDE/metadata_HYDE.js"));
require(path.join(h2, "landuse_HYDE/landuse_HYDE.js"));
require(path.join(h2, "admin_modern/admin_modern.js"));
require(path.join(h2, "GDP_PPP_SEDAC/GDP_PPP_SEDAC.js"));
require(path.join(h2, "GDP_nominal_SEDAC/GDP_nominal_SEDAC.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "GDP_nominal/GDP_nominal.js"));
require(path.join(h3, "GDP_PPP/GDP_PPP.js"));
require(path.join(h3, "GDP_pc/GDP_pc.js"));
require(path.join(h3, "GDP_PPP_pc/GDP_PPP_pc.js"));

(async () => {
	console.log("=== Validating Updated GDP_pc & GDP_PPP_pc OLS Training ===");
	let year = 2000;

	console.log("\n1. Testing GDP_pc.B_trainGDP_pcModel (Year 2000)...");
	let cov_obj = GDP_pc.input_covariates_obj();
	console.log("Covariates in stack:", Object.keys(cov_obj));
	if (cov_obj["uopp_"] || cov_obj["popd_"]) {
		throw new Error("FAIL: uopp_ or popd_ still present in input_covariates_obj!");
	}

	let res_nominal = await GDP_pc.B_trainGDP_pcModel(year, {
		key: `test_nominal_${year}`,
		lambda: 1e6
	});
	let coeffs_nom = res_nominal.coefficients;
	console.log("Trained GDP_pc Nominal Coefficients (Year 2000):", coeffs_nom);

	if (coeffs_nom["urbc_"] <= 0) throw new Error(`FAIL: urbc_ is non-positive: ${coeffs_nom["urbc_"]}`);
	if (coeffs_nom["rurc_"] <= 0) throw new Error(`FAIL: rurc_ is non-positive: ${coeffs_nom["rurc_"]}`);
	if (coeffs_nom["urbc_"] <= coeffs_nom["rurc_"]) {
		throw new Error(`FAIL: urbc_ (${coeffs_nom["urbc_"]}) <= rurc_ (${coeffs_nom["rurc_"]})!`);
	}
	let ratio_nom = coeffs_nom["urbc_"] / coeffs_nom["rurc_"];
	console.log(`PASS: Nominal Urban-Rural ratio = ${ratio_nom.toFixed(2)}x (urbc_: ${coeffs_nom["urbc_"]}, rurc_: ${coeffs_nom["rurc_"]})`);

	console.log("\n2. Testing GDP_PPP_pc.B_trainGDP_PPP_pcModel (Year 2000)...");
	let res_ppp = await GDP_PPP_pc.B_trainGDP_PPP_pcModel(year, {
		key: `test_ppp_${year}`,
		lambda: 1e6
	});
	let coeffs_ppp = res_ppp.coefficients;
	console.log("Trained GDP_PPP_pc Coefficients (Year 2000):", coeffs_ppp);

	if (coeffs_ppp["urbc_"] <= 0) throw new Error(`FAIL: PPP urbc_ is non-positive: ${coeffs_ppp["urbc_"]}`);
	if (coeffs_ppp["rurc_"] <= 0) throw new Error(`FAIL: PPP rurc_ is non-positive: ${coeffs_ppp["rurc_"]}`);
	if (coeffs_ppp["urbc_"] <= coeffs_ppp["rurc_"]) {
		throw new Error(`FAIL: PPP urbc_ (${coeffs_ppp["urbc_"]}) <= rurc_ (${coeffs_ppp["rurc_"]})!`);
	}
	let ratio_ppp = coeffs_ppp["urbc_"] / coeffs_ppp["rurc_"];
	console.log(`PASS: PPP Urban-Rural ratio = ${ratio_ppp.toFixed(2)}x (urbc_: ${coeffs_ppp["urbc_"]}, rurc_: ${coeffs_ppp["rurc_"]})`);

	console.log("\n=== ALL ASSERTIONS PASSED SUCCESSFULLY! ===");
})();
