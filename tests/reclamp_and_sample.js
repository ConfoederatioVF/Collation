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
	console.log("================================================================================");
	console.log("RECLAMPING RASTERS FOR 1600 & 1940 WITH WHITTAKER-HENDERSON GRADUATION");
	console.log("================================================================================\n");

	// Step 1: Execute reclamping
	console.log("1. Starting age_sex.E_clampToStadester...");
	let t0 = Date.now();
	await age_sex.E_clampToStadester({
		years: [1600, 1940],
		overwrite: true,
		smoothing_method: "whittaker_henderson",
		wh_lambda: 20.0,
		wh_mu: 1500.0,
		wh_huber_delta: 0.05
	});
	console.log(`   Reclamping finished in ${((Date.now() - t0)/1000).toFixed(1)}s.\n`);

	// Step 2: Index ISO3 country mask pixels
	console.log("2. Indexing ISO3 country masks from geocodes.png...");
	let csv_content = fs.readFileSync(admin_modern.input_geocodes_csv, "utf8");
	let lines = csv_content.split(/\r?\n/).filter(l => l.trim().length > 0);
	let target_iso3 = ["MMR", "IND", "JPN", "DEU", "USA", "RUS", "FRA", "CAN"];
	let color_to_iso3 = {};

	for (let i = 1; i < lines.length; i++) {
		let parts = lines[i].split(";");
		let iso3 = parts[0].trim();
		let color = parts[4] ? parts[4].trim() : null;
		if (target_iso3.includes(iso3) && color) color_to_iso3[color] = iso3;
	}

	let geocodes_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
	let total_pixels = geocodes_raster.width * geocodes_raster.height;
	let iso3_pixel_indices = {};
	target_iso3.forEach(c => iso3_pixel_indices[c] = []);

	for (let i = 0; i < total_pixels; i++) {
		let b = i * 4;
		let key = `${geocodes_raster.data[b]},${geocodes_raster.data[b+1]},${geocodes_raster.data[b+2]}`;
		let iso3 = color_to_iso3[key];
		if (iso3) iso3_pixel_indices[iso3].push(i);
	}

	// Step 3: Sample the reclamped rasters for target countries
	let cohorts = age_sex.getCohorts();
	let age_labels = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
	let clamped_dir = age_sex.intermediate_clamped_rasters;

	let country_names = {
		"MMR": "Myanmar",
		"IND": "India",
		"JPN": "Japan",
		"DEU": "Germany",
		"USA": "The United States",
		"RUS": "Russia",
		"FRA": "France",
		"CAN": "Canada"
	};

	let years_setup = {
		1940: ["MMR", "IND", "JPN", "DEU", "USA", "RUS"],
		1600: ["FRA", "IND", "CAN", "JPN"]
	};

	let results = {};

	for (let year of [1600, 1940]) {
		console.log(`3. Sampling reclamped rasters for Year ${year}...`);
		results[year] = {};
		let active_countries = years_setup[year];

		for (let iso3 of active_countries) {
			results[year][iso3] = {
				name: country_names[iso3],
				male: new Float64Array(18),
				female: new Float64Array(18),
				total: new Float64Array(18),
				sum_pop: 0
			};
		}

		for (let a = 0; a < 18; a++) {
			let age = age_labels[a];
			let f_path = path.join(clamped_dir, `global_f_${age}_${year}.png`);
			let m_path = path.join(clamped_dir, `global_m_${age}_${year}.png`);

			let f_rast = GeoPNG.loadNumberRasterImage(f_path, { format: "float32" });
			let m_rast = GeoPNG.loadNumberRasterImage(m_path, { format: "float32" });

			for (let iso3 of active_countries) {
				let indices = iso3_pixel_indices[iso3];
				let f_sum = 0;
				let m_sum = 0;

				for (let idx of indices) {
					let f_val = f_rast.data[idx];
					let m_val = m_rast.data[idx];
					if (f_val > 0) f_sum += f_val;
					if (m_val > 0) m_sum += m_val;
				}

				results[year][iso3].female[a] = f_sum;
				results[year][iso3].male[a] = m_sum;
				results[year][iso3].total[a] = f_sum + m_sum;
				results[year][iso3].sum_pop += f_sum + m_sum;
			}
		}
	}

	// Step 4: Output formatted tables
	console.log("\n================================================================================");
	console.log("RECLAMPED POPULATION PYRAMID RESULTS OVER REAL ISO3 AREAL MASKS");
	console.log("================================================================================\n");

	for (let year of [1600, 1940]) {
		console.log(`\n################################################################################`);
		console.log(`YEAR ${year}`);
		console.log(`################################################################################`);

		for (let iso3 of years_setup[year]) {
			let data = results[year][iso3];
			let total_m = (data.sum_pop / 1e6).toFixed(3);
			console.log(`\n================================================================================`);
			console.log(`Country: ${data.name} [${iso3}] | Year: ${year} | Total Population: ${total_m} M`);
			console.log(`================================================================================`);
			console.log(`Cohort | Male Pop     | Female Pop   | Total Pop    | Sex Ratio (M/F) | % Total`);
			console.log(`-------+--------------+--------------+--------------+-----------------+--------`);

			for (let a = 0; a < 18; a++) {
				let m_str = Math.round(data.male[a]).toLocaleString().padStart(12);
				let f_str = Math.round(data.female[a]).toLocaleString().padStart(12);
				let t_str = Math.round(data.total[a]).toLocaleString().padStart(12);
				let ratio = (data.female[a] > 0) ? (data.male[a] / data.female[a]).toFixed(3) : "N/A";
				let pct = ((data.total[a] / data.sum_pop) * 100).toFixed(2);

				console.log(`${age_labels[a].padStart(6)} | ${m_str} | ${f_str} | ${t_str} | ${ratio.padStart(15)} | ${pct.padStart(6)}%`);
			}
		}
	}

	// Save raw JSON for downstream analysis
	fs.writeFileSync("C:/Users/htmlp/.gemini/antigravity-ide/brain/49d17da0-5342-4f63-84eb-c73030cc0833/reclamped_results.json", JSON.stringify(results, null, 2));
	console.log("\nSaved results to reclamped_results.json");
})();
