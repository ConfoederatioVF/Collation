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
	console.log("Analyzing 1860 Professions for RUS, GBR, FRA, USA, CHN...");

	let geocode_img = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
	let geo_data = geocode_img.data;
	let width = geocode_img.width;
	let height = geocode_img.height;
	let data_len = width * height;

	let iso3_lookup = admin_modern.getISO3ColourcodesObject();
	let target_countries = {
		"RUS": { name: "Russia", r: 20, g: 114, b: 30 },
		"GBR": { name: "Britain", r: 198, g: 69, b: 69 },
		"FRA": { name: "France", r: 47, g: 97, b: 170 },
		"USA": { name: "USA", r: 87, g: 122, b: 175 },
		"CHN": { name: "China", r: 173, g: 62, b: 62 }
	};

	let target_cids = {};
	for (let iso3 in target_countries) {
		let c = target_countries[iso3];
		let cid = (c.r << 16) | (c.g << 8) | c.b;
		target_cids[cid] = iso3;
	}

	// Also check if any colour map in iso3_lookup matches
	for (let col_str in iso3_lookup) {
		let arr = iso3_lookup[col_str];
		for (let i = 0; i < arr.length; i++) {
			if (target_countries[arr[i]]) {
				let parts = col_str.split(",").map(Number);
				let cid = (parts[0] << 16) | (parts[1] << 8) | parts[2];
				target_cids[cid] = arr[i];
			}
		}
	}

	console.log("Target CIDs:", target_cids);

	let year = 1860;
	let cats = ["agriculture", "manufacturing", "services", "informal_labour", "not_in_work"];
	let olivetti_cats = ["agriculture", "manufacturing", "services", "informal_labour"];

	// Load population for 1860 total working cohorts
	let pop_total = new Float32Array(data_len);
	let working_cohorts = professions.working_cohorts;
	for (let s of ["m", "f"]) {
		for (let c of working_cohorts) {
			let cp = `${global.age_sex.output_rasters}${s}_${c}_${year}.png`;
			if (fs.existsSync(cp)) {
				let r = GeoPNG.loadNumberRasterImage(cp, { format: "float32" });
				for (let j = 0; j < data_len; j++) {
					if (!isNaN(r.data[j]) && r.data[j] > 0) pop_total[j] += r.data[j];
				}
			}
		}
	}

	// Load percentages rasters (both _t_ and sexes, and logit rasters)
	let pct_rasters = {};
	for (let cat of cats) {
		let p = `${professions.output_percentages}${cat}_t_${year}.png`;
		if (fs.existsSync(p)) {
			pct_rasters[cat] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
		} else {
			console.warn(`Missing: ${p}`);
		}
	}

	// Load logit rasters (pre-clamping probabilities in 2.logit_rasters)
	let logit_rasters = { m: {}, f: {} };
	for (let s of ["m", "f"]) {
		for (let cat of olivetti_cats) {
			let p = `${professions.intermediate_logit_rasters}logit_${s}_${year}_class_${cat}.png`;
			if (fs.existsSync(p)) {
				logit_rasters[s][cat] = GeoPNG.loadNumberRasterImage(p, { format: "float32" });
			}
		}
	}

	// Compute country stats
	let stats = {};
	for (let iso3 in target_countries) {
		stats[iso3] = {
			name: target_countries[iso3].name,
			pop: 0,
			pixels: 0,
			pct_pop_sum: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0, not_in_work: 0 },
			pct_vals: { agriculture: [], manufacturing: [], services: [], informal_labour: [], not_in_work: [] },
			logit_prob_pop_sum: { m: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0 }, f: { agriculture: 0, manufacturing: 0, services: 0, informal_labour: 0 } }
		};
	}

	for (let j = 0; j < data_len; j++) {
		let b_idx = j * 4;
		let cid = (geo_data[b_idx] << 16) | (geo_data[b_idx + 1] << 8) | geo_data[b_idx + 2];
		let iso3 = target_cids[cid];
		if (!iso3) continue;

		let st = stats[iso3];
		let p = pop_total[j];
		st.pixels++;
		if (p > 0) {
			st.pop += p;
			for (let cat of cats) {
				if (pct_rasters[cat]) {
					let val = pct_rasters[cat].data[j];
					if (!isNaN(val)) {
						st.pct_pop_sum[cat] += val * p;
						st.pct_vals[cat].push({ val: val, p: p });
					}
				}
			}
			for (let s of ["m", "f"]) {
				for (let cat of olivetti_cats) {
					if (logit_rasters[s][cat]) {
						let val = logit_rasters[s][cat].data[j];
						if (!isNaN(val)) st.logit_prob_pop_sum[s][cat] += val * p;
					}
				}
			}
		}
	}

	console.log("\n=======================================================");
	console.log("1860 COUNTRY BREAKDOWNS (Total Population Weighted)");
	console.log("=======================================================");
	for (let iso3 in stats) {
		let st = stats[iso3];
		console.log(`\n--- ${st.name} (${iso3}) | Pop: ${(st.pop/1e6).toFixed(2)}M, Pixels: ${st.pixels} ---`);
		if (st.pop === 0) {
			console.log("   No population found!");
			continue;
		}
		console.log("   Final Clamped Percentages (relative to total population):");
		let sum_shares = 0;
		for (let cat of cats) {
			let mean_share = st.pct_pop_sum[cat] / st.pop;
			sum_shares += mean_share;
			// Compute standard deviation across cells
			let sum_sq = 0;
			for (let item of st.pct_vals[cat]) {
				let diff = item.val - mean_share;
				sum_sq += item.p * diff * diff;
			}
			let std = Math.sqrt(sum_sq / st.pop);
			console.log(`     ${cat.padEnd(16)}: ${(mean_share * 100).toFixed(2)}% (std: ${(std * 100).toFixed(2)}%)`);
		}
		console.log(`     Total Active Labour Share: ${((sum_shares - (st.pct_pop_sum["not_in_work"]/st.pop))*100).toFixed(2)}%`);
		
		// Also show active labour sectoral breakdown (normalised excluding not_in_work)
		let active_pop = st.pop - st.pct_pop_sum["not_in_work"];
		if (active_pop > 0) {
			console.log("   Active Labour Proportions (% of working labour force):");
			for (let cat of olivetti_cats) {
				let share = st.pct_pop_sum[cat] / active_pop;
				console.log(`     ${cat.padEnd(16)}: ${(share * 100).toFixed(2)}%`);
			}
		}

		console.log("   Pre-clamping Logit Probabilities (Male / Female mean):");
		for (let cat of olivetti_cats) {
			let m_p = (st.logit_prob_pop_sum.m[cat] / st.pop) * 100;
			let f_p = (st.logit_prob_pop_sum.f[cat] / st.pop) * 100;
			console.log(`     ${cat.padEnd(16)}: M=${m_p.toFixed(2)}%, F=${f_p.toFixed(2)}%`);
		}
	}

	// Compare macro sector baseline for 1860
	console.log("\n=======================================================");
	console.log("Global Dynamic Sector Baselines for 1860:");
	console.log("   Male  :", professions.getDynamicSectorBaselines(1860, "m"));
	console.log("   Female:", professions.getDynamicSectorBaselines(1860, "f"));
	console.log("=======================================================");
})();
