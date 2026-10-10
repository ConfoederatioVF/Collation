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
require(path.join(h3, "professions/professions.js"));

(async () => {
	console.log("Analyzing 1820 Professions for Italy vs Great Britain...");

	let geocode_img = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
	let geo_data = geocode_img.data;
	let width = geocode_img.width;
	let height = geocode_img.height;
	let data_len = width * height;

	let target_countries = {
		"ITA": { name: "Italy", r: 53, g: 206, b: 97 },
		"GBR": { name: "Great Britain", r: 198, g: 69, b: 69 }
	};

	let target_cids = {};
	for (let iso3 in target_countries) {
		let c = target_countries[iso3];
		let cid = (c.r << 16) | (c.g << 8) | c.b;
		target_cids[cid] = iso3;
	}

	let year = 1820;
	let cats = ["agriculture", "manufacturing", "services", "informal_labour", "not_in_work"];
	let olivetti_cats = ["agriculture", "manufacturing", "services", "informal_labour"];

	// Load population for 1820 total working cohorts
	let pop_total = new Float32Array(data_len);
	let pop_sex = { m: new Float32Array(data_len), f: new Float32Array(data_len) };
	let working_cohorts = professions.working_cohorts;
	for (let s of ["m", "f"]) {
		for (let c of working_cohorts) {
			let cp = `${global.age_sex.output_rasters}${s}_${c}_${year}.png`;
			if (fs.existsSync(cp)) {
				let r = GeoPNG.loadNumberRasterImage(cp, { format: "float32" });
				for (let j = 0; j < data_len; j++) {
					if (!isNaN(r.data[j]) && r.data[j] > 0) {
						pop_total[j] += r.data[j];
						pop_sex[s][j] += r.data[j];
					}
				}
			}
		}
	}

	// Load percentages rasters
	let pct_rasters = {};
	for (let cat of cats) {
		let p = `${professions.output_percentages}${cat}_t_${year}.png`;
		if (fs.existsSync(p)) {
			pct_rasters[cat] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
		}
	}

	// Load logit rasters
	let logit_rasters = { m: {}, f: {} };
	for (let s of ["m", "f"]) {
		for (let cat of olivetti_cats) {
			let p = `${professions.intermediate_logit_rasters}logit_${s}_${year}_class_${cat}.png`;
			if (fs.existsSync(p)) {
				logit_rasters[s][cat] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
			}
		}
	}

	// Load GDP per capita and urban/rural
	let gdp_pc_path = `${global.h3}GDP_pc/8.GDP_nominal_pc_rasters/GDP_pc_${year}.png`;
	let urb_path = `${global.h2}population_Stadester/stadester_urban_rasters/stadester_urban_${year}.png`;
	let rur_path = `${global.h2}population_Stadester/stadester_rural_rasters/stadester_rural_${year}.png`;

	let gdp_raster = fs.existsSync(gdp_pc_path) ? GeoPNG.loadNumberRasterImage(gdp_pc_path, { format: "float32" }) : null;
	let urb_raster = fs.existsSync(urb_path) ? GeoPNG.loadNumberRasterImage(urb_path, { format: "float32" }) : null;
	let rur_raster = fs.existsSync(rur_path) ? GeoPNG.loadNumberRasterImage(rur_path, { format: "float32" }) : null;

	let regions = {
		"GBR": { name: "Great Britain", filter: (cid, lat) => cid === target_cids["GBR"] || target_cids[cid] === "GBR" },
		"ITA_ALL": { name: "Italy (All)", filter: (cid, lat) => target_cids[cid] === "ITA" },
		"ITA_NORTH": { name: "Italy (North, lat >= 42)", filter: (cid, lat) => target_cids[cid] === "ITA" && lat >= 42 },
		"ITA_SOUTH": { name: "Italy (South, lat < 42)", filter: (cid, lat) => target_cids[cid] === "ITA" && lat < 42 }
	};

	let stats = {};
	for (let rk in regions) {
		stats[rk] = {
			name: regions[rk].name,
			pop: 0,
			pixels: 0,
			gdp_sum: 0,
			urb_sum: 0,
			rur_sum: 0,
			pct_pop_sum: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0, not_in_work: 0 },
			logit_pop_sum: {
				m: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0 },
				f: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0 }
			}
		};
	}

	for (let j = 0; j < data_len; j++) {
		let b_idx = j * 4;
		let cid = (geo_data[b_idx] << 16) | (geo_data[b_idx + 1] << 8) | geo_data[b_idx + 2];
		
		let y_pix = Math.floor(j / width);
		let lat = 90 - (y_pix + 0.5) * (180 / height);

		let p = pop_total[j];

		for (let rk in regions) {
			if (regions[rk].filter(cid, lat)) {
				let st = stats[rk];
				st.pixels++;
				if (p > 0) {
					st.pop += p;
					if (gdp_raster && !isNaN(gdp_raster.data[j])) st.gdp_sum += gdp_raster.data[j] * p;
					if (urb_raster && !isNaN(urb_raster.data[j])) st.urb_sum += urb_raster.data[j];
					if (rur_raster && !isNaN(rur_raster.data[j])) st.rur_sum += rur_raster.data[j];

					for (let cat of cats) {
						if (pct_rasters[cat]) {
							let val = pct_rasters[cat].data[j];
							if (!isNaN(val)) st.pct_pop_sum[cat] += val * p;
						}
					}
					for (let s of ["m", "f"]) {
						for (let cat of olivetti_cats) {
							if (logit_rasters[s][cat]) {
								let val = logit_rasters[s][cat].data[j];
								if (!isNaN(val)) st.logit_pop_sum[s][cat] += val * p;
							}
						}
					}
				}
			}
		}
	}

	console.log("\n=======================================================");
	console.log("1820 RESULTS SUMMARY");
	console.log("=======================================================");
	for (let rk in stats) {
		let st = stats[rk];
		console.log(`\n--- ${st.name} | Working Pop: ${(st.pop/1e6).toFixed(2)}M, Pixels: ${st.pixels} ---`);
		let avg_gdp = st.pop > 0 ? st.gdp_sum / st.pop : 0;
		let tot_urb_rur = st.urb_sum + st.rur_sum;
		let urb_rate = tot_urb_rur > 0 ? st.urb_sum / tot_urb_rur : 0;
		console.log(`   Avg GDP pc: $${avg_gdp.toFixed(0)}, Urban Rate: ${(urb_rate * 100).toFixed(1)}% (Urb sum: ${(st.urb_sum/1e6).toFixed(2)}M, Rur sum: ${(st.rur_sum/1e6).toFixed(2)}M)`);

		console.log("   Structural baseline (Male):", professions.getCountryStructuralBaselines(avg_gdp, urb_rate, year, "m"));
		console.log("   Structural baseline (Female):", professions.getCountryStructuralBaselines(avg_gdp, urb_rate, year, "f"));

		let active_pop = st.pop - st.pct_pop_sum["not_in_work"];
		console.log(`   Active Labour (% of working labour force, Total):`);
		for (let cat of olivetti_cats) {
			let share = active_pop > 0 ? st.pct_pop_sum[cat] / active_pop : 0;
			console.log(`     ${cat.padEnd(16)}: ${(share * 100).toFixed(2)}%`);
		}
		console.log(`   Share of Total Cohort Population:`);
		for (let cat of cats) {
			let share = st.pop > 0 ? st.pct_pop_sum[cat] / st.pop : 0;
			console.log(`     ${cat.padEnd(16)}: ${(share * 100).toFixed(2)}%`);
		}

		console.log(`   Raw Logit Probabilities (Male / Female mean):`);
		for (let cat of olivetti_cats) {
			let m_p = (st.logit_pop_sum.m[cat] / st.pop) * 100;
			let f_p = (st.logit_pop_sum.f[cat] / st.pop) * 100;
			console.log(`     ${cat.padEnd(16)}: M=${m_p.toFixed(2)}%, F=${f_p.toFixed(2)}%`);
		}
	}
})();
