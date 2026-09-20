let path = require("path");
let fs = require("fs");

global.Statistics = {};
require("../UF/js/statistics/statistics_isotonic.js");

let data_path = "D:/Project 1436 - Dataview/data/baked_global_demographics.json";
if (!fs.existsSync(data_path)) {
	console.error(`File not found: ${data_path}`);
	process.exit(1);
}

let demographics_data = JSON.parse(fs.readFileSync(data_path, "utf8"));
let cohorts = ["00", "01", "05", "10", "15", "20", "25", "30", "35", "40", "45", "50", "55", "60", "65", "70", "75", "80"];
let band_widths = new Float32Array([1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]);

console.log("================================================================================");
console.log("ANALYSIS OF GLOBAL POPULATION PYRAMIDS WITH PAVA ISOTONIC SMOOTHING");
console.log("================================================================================\n");

let years = Object.keys(demographics_data).sort((a, b) => parseInt(a) - parseInt(b));

let testYear = function (year, start_index) {
	let entry = demographics_data[year];
	if (!entry || !entry.female || !entry.male) return null;
	
	let results = { year: year, start_index: start_index };
	
	for (let sex of ["female", "male"]) {
		let raw_cohorts = new Float32Array(cohorts.length);
		let raw_annualised = new Float32Array(cohorts.length);
		
		for (let i = 0; i < cohorts.length; i++) {
			let val = entry[sex][cohorts[i]];
			raw_cohorts[i] = (val !== undefined) ? val : 0;
			raw_annualised[i] = raw_cohorts[i] / band_widths[i];
		}
		
		// Detect raw monotonicity violations after start_index
		let violations = [];
		for (let i = start_index; i < cohorts.length - 1; i++) {
			if (raw_annualised[i] < raw_annualised[i + 1]) {
				violations.push({
					from_cohort: cohorts[i],
					to_cohort: cohorts[i + 1],
					from_val: raw_annualised[i],
					to_val: raw_annualised[i + 1],
					pct_jump: (((raw_annualised[i + 1] - raw_annualised[i]) / raw_annualised[i]) * 100).toFixed(1)
				});
			}
		}
		
		// Run PAVA
		let smoothed_annualised = Statistics.pavaDecreasing(raw_annualised, band_widths, start_index);
		let smoothed_cohorts = new Float32Array(cohorts.length);
		
		for (let i = 0; i < cohorts.length; i++) {
			smoothed_cohorts[i] = smoothed_annualised[i] * band_widths[i];
		}
		
		// Verify conservation
		let sum_raw = raw_cohorts.reduce((a, b) => a + b, 0);
		let sum_smoothed = smoothed_cohorts.reduce((a, b) => a + b, 0);
		
		results[sex] = {
			raw_cohorts: Array.from(raw_cohorts),
			raw_annualised: Array.from(raw_annualised),
			smoothed_cohorts: Array.from(smoothed_cohorts),
			smoothed_annualised: Array.from(smoothed_annualised),
			violations: violations,
			sum_raw: sum_raw,
			sum_smoothed: sum_smoothed,
			sum_diff: Math.abs(sum_raw - sum_smoothed)
		};
	}
	
	return results;
};

// Summary report across historical timeline
console.log(sprintf("%-8s | %-12s | %-12s | %-20s | %-20s", "Year", "F Violations", "M Violations", "F Worst Bulge", "M Worst Bulge"));
console.log("-".repeat(80));

function sprintf(format, ...args) {
	let i = 0;
	return format.replace(/%(-?\d+)?s/g, (match, width) => {
		let val = String(args[i++]);
		if (!width) return val;
		let w = parseInt(width);
		if (w < 0) return val.padEnd(-w);
		return val.padStart(w);
	});
}

for (let y of years) {
	let res = testYear(y, 2); // Cutoff after child mortality (05 onwards)
	if (!res) continue;
	
	let f_worst = res.female.violations.length > 0 ?
		`${res.female.violations[0].from_cohort}->${res.female.violations[0].to_cohort} (+${res.female.violations[0].pct_jump}%)` : "None";
	let m_worst = res.male.violations.length > 0 ?
		`${res.male.violations[0].from_cohort}->${res.male.violations[0].to_cohort} (+${res.male.violations[0].pct_jump}%)` : "None";
	
	console.log(sprintf("%-8s | %-12s | %-12s | %-20s | %-20s",
		y,
		res.female.violations.length,
		res.male.violations.length,
		f_worst,
		m_worst
	));
}

// Deep dive into key anchor years: 1000, 1700, 1950
console.log("\n================================================================================");
console.log("DETAILED COHORT BREAKDOWNS (RAW vs PAVA SMOOTHED)");
console.log("================================================================================\n");

for (let target_year of ["1000", "1700", "1950"]) {
	let res = testYear(target_year, 2);
	if (!res) continue;
	
	console.log(`--- YEAR ${target_year} ---`);
	console.log(sprintf("%-6s | %-12s | %-12s | %-12s | %-12s | %-8s", "Cohort", "F Raw (k)", "F PAVA (k)", "M Raw (k)", "M PAVA (k)", "Status"));
	console.log("-".repeat(75));
	
	for (let i = 0; i < cohorts.length; i++) {
		let c = cohorts[i];
		let f_raw = (res.female.raw_cohorts[i] / 1000).toFixed(2);
		let f_pava = (res.female.smoothed_cohorts[i] / 1000).toFixed(2);
		let m_raw = (res.male.raw_cohorts[i] / 1000).toFixed(2);
		let m_pava = (res.male.smoothed_cohorts[i] / 1000).toFixed(2);
		let status = (f_raw !== f_pava || m_raw !== m_pava) ? "POOLED" : "OK";
		
		console.log(sprintf("%-6s | %-12s | %-12s | %-12s | %-12s | %-8s", c, f_raw, f_pava, m_raw, m_pava, status));
	}
	console.log(sprintf("TOTAL  | %-12s | %-12s | %-12s | %-12s | %-8s\n",
		(res.female.sum_raw / 1000).toFixed(2),
		(res.female.sum_smoothed / 1000).toFixed(2),
		(res.male.sum_raw / 1000).toFixed(2),
		(res.male.sum_smoothed / 1000).toFixed(2),
		"CONSERVED"
	));
}
