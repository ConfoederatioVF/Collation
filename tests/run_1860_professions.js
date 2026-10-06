const fs = require("fs");
const path = require("path");

let root_dir = path.resolve(".");
global.fs = fs;
global.path = path;
global.pngjs = require(path.join(root_dir, "node_modules/pngjs"));

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
require(path.join(h3, "population_Stadester.transform/population_Stadester_transform.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h2, "GDP_nominal/GDP_nominal.js"));
require(path.join(h3, "GDP_PPP/GDP_PPP.js"));
require(path.join(h2, "GDP_PPP_SEDAC/GDP_PPP_SEDAC.js"));
require(path.join(h3, "GDP_pc/GDP_pc.js"));
require(path.join(h3, "GDP_PPP_pc/GDP_PPP_pc.js"));
require(path.join(h3, "wealth_income/wealth_income.js"));
require(path.join(h2, "gini_Eoscala/gini_Eoscala.js"));
require(path.join(h3, "GDP_Eoscala.transform/GDP_Eoscala_transform.js"));
require(path.join(h2, "LFPR_OLS/LFPR_OLS.js"));
require(path.join(h3, "age_sex/age_sex.js"));
require(path.join(h3, "professions/professions.js"));

(async () => {
	console.log("Re-generating 1860 professions rasters with revised calibration...");

	console.log("\n--- Step D: D_generateEnsembleRasters ---");
	await professions.D_generateEnsembleRasters({ overwrite: true, years: [1860] });

	console.log("\n--- Step E: E_clampToPercentagesAndAggregates ---");
	await professions.E_clampToPercentagesAndAggregates({ overwrite: true, years: [1860] });

	console.log("\nDone! 1860 professions generated successfully.");
	process.exit(0);
})();
