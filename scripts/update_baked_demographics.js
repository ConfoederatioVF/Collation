let fs = require("fs");
let path = require("path");

global.Statistics = {};
require("../UF/js/statistics/statistics_isotonic.js");

let data_path = "D:/Project 1436 - Dataview/data/baked_global_demographics.json";
let backup_path = "D:/Project 1436 - Dataview/data/baked_global_demographics.json.bak";

if (!fs.existsSync(data_path)) {
	console.error(`Error: File not found at ${data_path}`);
	process.exit(1);
}

// 1. Create a backup if not already present
if (!fs.existsSync(backup_path)) {
	fs.copyFileSync(data_path, backup_path);
	console.log(`Backup created at: ${backup_path}`);
}

let demographics_data = JSON.parse(fs.readFileSync(data_path, "utf8"));
let cohorts = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
let band_widths = new Float32Array([1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]);

let years = Object.keys(demographics_data).sort((a, b) => parseInt(a) - parseInt(b));
let updated_count = 0;

console.log("Applying 2D Coupled Demographic Smoothing to pre-1950 historical epochs in baked cache...");

for (let y of years) {
	let yr_num = parseInt(y);
	if (yr_num >= 1950) {
		console.log(`- Year ${y}: Retained empirical UNWPP actuals.`);
		continue;
	}

	let entry = demographics_data[y];
	if (!entry || !entry.female || !entry.male) continue;

	let f_raw = new Float32Array(cohorts.length);
	let m_raw = new Float32Array(cohorts.length);
	let orig_tot = 0;

	for (let i = 0; i < cohorts.length; i++) {
		let c = cohorts[i];
		f_raw[i] = entry.female[c] || 0;
		m_raw[i] = entry.male[c] || 0;
		orig_tot += f_raw[i] + m_raw[i];
	}

	let coupled = Statistics.coupleAgeSexCohorts(m_raw, f_raw, band_widths, 2);
	let new_tot = 0;

	for (let i = 0; i < cohorts.length; i++) {
		let c = cohorts[i];
		// Round to 1 decimal place to match Dataview cache convention
		let f_val = Math.round(coupled.female[i] * 10) / 10;
		let m_val = Math.round(coupled.male[i] * 10) / 10;
		entry.female[c] = f_val;
		entry.male[c] = m_val;
		new_tot += f_val + m_val;
	}

	// Update lastModified timestamp if present
	entry.lastModified = Date.now();
	updated_count++;

	console.log(`- Year ${y}: Smoothed ${cohorts.length} cohorts. Pop: ${(orig_tot / 1000).toFixed(2)}k -> ${(new_tot / 1000).toFixed(2)}k (Rel diff: ${((Math.abs(orig_tot - new_tot) / orig_tot) * 100).toFixed(4)}%)`);
}

fs.writeFileSync(data_path, JSON.stringify(demographics_data, null, 2), "utf8");
console.log(`\nSuccessfully updated ${updated_count} historical epochs in ${data_path}`);
