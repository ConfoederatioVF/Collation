const fs = require("fs");
const path = require("path");

global.fs = fs;
global.path = path;
global.pngjs = require("pngjs");
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
require(path.join(h3, "population_Stadester.transform/population_Stadester_transform.js"));
require(path.join(h2, "population_Stadester/population_Stadester.js"));
require(path.join(h3, "age_sex/age_sex.js"));

(async () => {
	console.log("Loading geocodes.csv...");
	let csv_content = fs.readFileSync(admin_modern.input_geocodes_csv, "utf8");
	let lines = csv_content.split(/\r?\n/).filter(l => l.trim().length > 0);
	let target_iso3 = ["MMR", "IND", "JPN", "DEU", "USA", "RUS", "FRA", "CAN"];
	let iso3_to_color = {};
	let color_to_iso3 = {};

	for (let i = 1; i < lines.length; i++) {
		let parts = lines[i].split(";");
		let iso3 = parts[0].trim();
		let color = parts[4] ? parts[4].trim() : null;
		if (target_iso3.includes(iso3) && color) {
			iso3_to_color[iso3] = color;
			color_to_iso3[color] = iso3;
			console.log(`Found ${iso3}: ${color}`);
		}
	}

	console.log("\nLoading geocodes raster...");
	let geocodes_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
	console.log(`Geocodes raster loaded: ${geocodes_raster.width}x${geocodes_raster.height}`);

	let pixel_counts = {};
	target_iso3.forEach(c => pixel_counts[c] = 0);

	let total_pixels = geocodes_raster.width * geocodes_raster.height;
	for (let i = 0; i < total_pixels; i++) {
		let b = i * 4;
		let key = `${geocodes_raster.data[b]},${geocodes_raster.data[b+1]},${geocodes_raster.data[b+2]}`;
		let iso3 = color_to_iso3[key];
		if (iso3) pixel_counts[iso3]++;
	}

	console.log("Pixel counts per target ISO3:");
	console.log(pixel_counts);
})();
