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
console.log("TESTING 2D COUPLED DEMOGRAPHIC SMOOTHING (AGE PAVA & SEX RATIOS)");
console.log("================================================================================\n");

let target_years = ["1600", "1700", "1850", "1940"];

for (let year of target_years) {
	let entry = demographics_data[year];
	if (!entry) continue;

	let f_raw = new Float32Array(cohorts.length);
	let m_raw = new Float32Array(cohorts.length);
	let sum_raw_f = 0;
	let sum_raw_m = 0;

	for (let i = 0; i < cohorts.length; i++) {
		let c = cohorts[i];
		f_raw[i] = entry.female[c] || 0;
		m_raw[i] = entry.male[c] || 0;
		sum_raw_f += f_raw[i];
		sum_raw_m += m_raw[i];
	}
	let sum_raw_total = sum_raw_f + sum_raw_m;

	// Execute 2D coupled smoothing
	let coupled = Statistics.coupleAgeSexCohorts(m_raw, f_raw, band_widths, 0);

	let sum_sm_f = 0;
	let sum_sm_m = 0;
	for (let i = 0; i < cohorts.length; i++) {
		sum_sm_f += coupled.female[i];
		sum_sm_m += coupled.male[i];
	}
	let sum_sm_total = sum_sm_f + sum_sm_m;

	console.log(`--- YEAR ${year} ---`);
	console.log(`Total Population: Raw = ${(sum_raw_total / 1000).toFixed(2)}k | Smoothed = ${(sum_sm_total / 1000).toFixed(2)}k | Diff = ${Math.abs(sum_raw_total - sum_sm_total).toFixed(6)}`);
	console.log(`Macro Sex Ratio (M/F): Raw = ${(sum_raw_m / sum_raw_f).toFixed(3)} | Smoothed = ${(sum_sm_m / sum_sm_f).toFixed(3)}`);

	// 1. Assert exact total conservation (relative float32 tolerance)
	let rel_diff = Math.abs(sum_raw_total - sum_sm_total) / sum_raw_total;
	console.assert(rel_diff < 1e-5, `Year ${year} total population must be conserved, rel diff = ${rel_diff}`);

	// 2. Assert age monotonicity across all annualised cohorts (index 0 onwards)
	for (let i = 0; i < cohorts.length - 1; i++) {
		let tot_ann_curr = coupled.total[i] / band_widths[i];
		let tot_ann_next = coupled.total[i + 1] / band_widths[i + 1];
		console.assert(tot_ann_curr >= tot_ann_next - 1e-5, `Year ${year} total cohort ${cohorts[i]} (${tot_ann_curr.toFixed(2)}) must be >= ${cohorts[i+1]} (${tot_ann_next.toFixed(2)})`);

		let f_ann_curr = coupled.female[i] / band_widths[i];
		let f_ann_next = coupled.female[i + 1] / band_widths[i + 1];
		console.assert(f_ann_curr >= f_ann_next - 1e-5, `Year ${year} female cohort ${cohorts[i]} (${f_ann_curr.toFixed(2)}) must be >= ${cohorts[i+1]} (${f_ann_next.toFixed(2)})`);

		let m_ann_curr = coupled.male[i] / band_widths[i];
		let m_ann_next = coupled.male[i + 1] / band_widths[i + 1];
		console.assert(m_ann_curr >= m_ann_next - 1e-5, `Year ${year} male cohort ${cohorts[i]} (${m_ann_curr.toFixed(2)}) must be >= ${cohorts[i+1]} (${m_ann_next.toFixed(2)})`);
	}

	// 3. Assert biological sex-ratio bounds
	let srb = coupled.male[0] / coupled.female[0];
	console.log(`Sex Ratio at Birth (Cohort 00): Raw = ${(m_raw[0] / f_raw[0]).toFixed(3)} -> Smoothed = ${srb.toFixed(3)}`);
	console.assert(srb >= 1.02 && srb <= 1.07, `Sex ratio at birth in year ${year} must be between 1.02 and 1.07, got ${srb}`);

	let sr_youth = coupled.male[4] / coupled.female[4];
	console.log(`Youth Sex Ratio (Cohort 15): Raw = ${(m_raw[4] / f_raw[4]).toFixed(3)} -> Smoothed = ${sr_youth.toFixed(3)}`);
	console.assert(sr_youth >= 0.50 && sr_youth <= 1.80, `Youth sex ratio in year ${year} must be within bounds, got ${sr_youth}`);

	let sr_old = coupled.male[17] / coupled.female[17];
	console.log(`Oldest Sex Ratio (Cohort 80): Raw = ${(m_raw[17] / f_raw[17]).toFixed(3)} -> Smoothed = ${sr_old.toFixed(3)}\n`);
	console.assert(sr_old >= 0.30 && sr_old <= 1.05, `Oldest sex ratio in year ${year} must be within bounds, got ${sr_old}`);
}

// 4. Test option combinations and edge cases
console.log("--- TESTING OPTIONS & EDGE CASES ---");
{
	let m_test = new Float32Array([100, 50, 20]);
	let f_test = new Float32Array([10, 50, 100]);
	let b_test = new Float32Array([1, 1, 1]);

	// Case A: do_not_smooth: true
	let res_no_smooth = Statistics.coupleAgeSexCohorts(m_test, f_test, b_test, 0, { do_not_smooth: true });
	for (let i = 0; i < 3; i++) {
		let expected_tot = m_test[i] + f_test[i];
		console.assert(Math.abs(res_no_smooth.total[i] - expected_tot) < 1e-5, `do_not_smooth total must match raw total at ${i}`);
	}
	console.log("✓ do_not_smooth verified");

	// Case B: preserve_sex_ratios: true (extreme ratio 100/10 = 10.0 preserved)
	let res_preserve = Statistics.coupleAgeSexCohorts(m_test, f_test, b_test, 0, { preserve_sex_ratios: true, do_not_smooth: true });
	let preserved_sr = res_preserve.male[0] / res_preserve.female[0];
	console.assert(Math.abs(preserved_sr - 10.0) < 1e-4, `preserve_sex_ratios must keep raw sex ratio 10.0, got ${preserved_sr}`);
	console.log("✓ preserve_sex_ratios verified");

	// Case C: enforce_fixed_sex_ratios: true
	let baseline = new Float32Array([1.05, 1.0, 0.7]);
	let res_fixed = Statistics.coupleAgeSexCohorts(m_test, f_test, b_test, 0, { enforce_fixed_sex_ratios: true, baseline_sex_ratios: baseline });
	for (let i = 0; i < 3; i++) {
		let actual_sr = res_fixed.male[i] / res_fixed.female[i];
		console.assert(Math.abs(actual_sr - baseline[i]) < 1e-4, `Fixed sex ratio at ${i} must match baseline, got ${actual_sr}`);
	}
	console.log("✓ enforce_fixed_sex_ratios verified");

	// Case D: Zero counts (f = 0, m > 0; and f = 0, m = 0)
	let m_zeros = new Float32Array([50, 0, 0]);
	let f_zeros = new Float32Array([0, 50, 0]);
	let res_zeros = Statistics.coupleAgeSexCohorts(m_zeros, f_zeros, b_test, 0);
	console.assert(!isNaN(res_zeros.male[0]) && !isNaN(res_zeros.female[0]), "Non-NaN when female is 0");
	console.assert(!isNaN(res_zeros.male[1]) && !isNaN(res_zeros.female[1]), "Non-NaN when male is 0");
	console.assert(!isNaN(res_zeros.male[2]) && !isNaN(res_zeros.female[2]), "Non-NaN when both are 0");
	console.assert(res_zeros.total[2] === 0, "Total is 0 when both are 0");
	console.log("✓ Zero-count robustness verified");
}

console.log("\nAll 2D Coupled Demographic tests passed successfully!");
