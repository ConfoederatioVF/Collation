let path = require("path");
let fs = require("fs");

//Bootstrap environment
global.Statistics = {};
require("../UF/js/statistics/statistics_isotonic.js");

console.log("=== Running PAVA Demographics Test ===");

//Synthetic cohort test: 18 cohorts (f_00, f_01, f_05, f_10, ..., f_80)
//Infant (00): 100, Child (01): 80 (nadir at 05: 50)
//Then noisy artificial migration/sampling bulges: 65, 40, 55, 30, 35, 20, 15, 10, 8, 5, 4, 3, 2, 1, 0.5
let raw_rates = new Float32Array([
	100, 80, 50, 65, 40, 55, 30, 35, 20, 15, 10, 8, 5, 4, 3, 2, 1, 0.5
]);

let band_widths = new Float32Array([
	1, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5
]);

console.log("Raw Rates:", Array.from(raw_rates));

//Apply PAVA starting at index 2 (cohort 05 onwards, preserving 00 and 01)
let smoothed = Statistics.pavaDecreasing(raw_rates, band_widths, 2);

console.log("Smoothed Rates:", Array.from(smoothed));

//Verify unconstrained nadir
console.assert(smoothed[0] === 100, `Expected smoothed[0] === 100, got ${smoothed[0]}`);
console.assert(smoothed[1] === 80, `Expected smoothed[1] === 80, got ${smoothed[1]}`);

//Verify non-increasing monotonicity from index 2 onwards
let monotonic = true;
for (let i = 2; i < smoothed.length - 1; i++) {
	if (smoothed[i] < smoothed[i + 1]) {
		monotonic = false;
		console.error(`Monotonicity violated at index ${i}: ${smoothed[i]} < ${smoothed[i + 1]}`);
	}
}
console.assert(monotonic, "PAVA output must be strictly non-increasing after index 2");

//Verify conservation of weighted sum across smoothed range
let raw_weighted_sum = 0;
let smoothed_weighted_sum = 0;
for (let i = 2; i < smoothed.length; i++) {
	raw_weighted_sum += raw_rates[i] * band_widths[i];
	smoothed_weighted_sum += smoothed[i] * band_widths[i];
}
let sum_diff = Math.abs(raw_weighted_sum - smoothed_weighted_sum);
console.assert(sum_diff < 1e-3, `Weighted sum conservation failed: diff = ${sum_diff}`);

console.log(`- Weighted sum before: ${raw_weighted_sum}, after: ${smoothed_weighted_sum}`);
console.log(">>> PAVA Demographics Test Passed! <<<\n");
