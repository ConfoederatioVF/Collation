let fs = require("fs");
let path = require("path");

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
require(path.join(h2, "births_deaths_UNWPP/births_deaths_UNWPP.js"));
require(path.join(h2, "births_deaths_HMD/births_deaths_HMD.js"));
require(path.join(h2, "births_deaths_OLS/births_deaths_OLS.js"));
require(path.join(h2, "migration_OLS/migration_OLS.js"));

(async () => {
	let target_year = process.argv[2] ? parseInt(process.argv[2]) : 1900;
	console.log("================================================================================");
	console.log(`VERIFYING DEMOGRAPHIC ACCOUNTING AND PIPELINE EXECUTION FOR YEAR ${target_year}`);
	console.log("================================================================================\n");

	// Step 1: Run migration_OLS E_deriveFinalRasters
	console.log(`1. Running migration_OLS.E_deriveFinalRasters for ${target_year}...`);
	await migration_OLS.E_deriveFinalRasters({ years: [target_year], overwrite: true });
	console.log("   migration_OLS finished.\n");

	// Step 2: Run births_deaths_OLS E_clampToStadester
	console.log(`2. Running births_deaths_OLS.E_clampToStadester for ${target_year}...`);
	await births_deaths_OLS.E_clampToStadester({ years: [target_year], overwrite: true });
	console.log("   births_deaths_OLS finished.\n");

	// Step 3: Load outputs and verify identities
	console.log("3. Loading rasters to verify demographic accounting identities...");
	let b_path = `${births_deaths_OLS.output_births_folder}births_${target_year}.png`;
	let fd_path = `${births_deaths_OLS.output_female_deaths_folder}female_deaths_${target_year}.png`;
	let md_path = `${births_deaths_OLS.output_male_deaths_folder}male_deaths_${target_year}.png`;
	let m_path = `${births_deaths_OLS.output_net_migration_folder}net_migration_${target_year}.png`;
	let mf_path = `${births_deaths_OLS.output_female_migration_folder}female_net_migration_${target_year}.png`;
	let mm_path = `${births_deaths_OLS.output_male_migration_folder}male_net_migration_${target_year}.png`;
	let delta_path = `${population_Stadester_transform.delta_total_population_folder}delta_total_population_${target_year}.png`;
	let popc_path = `${age_sex.sf().input_popc_folder}stadester_population_${target_year}.png`;

	let b_r = GeoPNG.loadNumberRasterImage(b_path, { format: "float32" });
	let fd_r = GeoPNG.loadNumberRasterImage(fd_path, { format: "float32" });
	let md_r = GeoPNG.loadNumberRasterImage(md_path, { format: "float32" });
	let m_r = GeoPNG.loadNumberRasterImage(m_path, { format: "float32" });
	let mf_r = GeoPNG.loadNumberRasterImage(mf_path, { format: "float32" });
	let mm_r = GeoPNG.loadNumberRasterImage(mm_path, { format: "float32" });
	let delta_r = GeoPNG.loadNumberRasterImage(delta_path, { format: "float32" });
	let popc_r = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });

	let all_years = landuse_HYDE.sorted_hyde_years;
	let y_idx = all_years.indexOf(target_year);
	let year_gap = (y_idx > 0) ? (target_year - all_years[y_idx - 1]) : 1;
	console.log(`   Year gap for ${target_year}: ${year_gap} years`);

	let max_identity_err = 0;
	let sum_identity_err = 0;
	let populated_pixels = 0;
	let identity_violations = 0;

	let total_b = 0;
	let total_fd = 0;
	let total_md = 0;
	let total_m = 0;
	let total_mf = 0;
	let total_mm = 0;
	let total_dpop_annual = 0;
	let total_pop = 0;

	let max_mig_sex_err = 0;
	let max_death_sex_err = 0;

	// Check ground truth actuals preservation
	let variables_obj = births_deaths_OLS._getVariablesObj();
	let actual_b_path = births_deaths_OLS._getActualPath(variables_obj.births, target_year);
	let actual_b_raster = (actual_b_path && fs.existsSync(actual_b_path)) ? GeoPNG.loadNumberRasterImage(actual_b_path, { format: "float32" }) : null;
	let actual_fd_path = births_deaths_OLS._getActualPath(variables_obj.female_deaths, target_year);
	let actual_fd_raster = (actual_fd_path && fs.existsSync(actual_fd_path)) ? GeoPNG.loadNumberRasterImage(actual_fd_path, { format: "float32" }) : null;
	let actual_md_path = births_deaths_OLS._getActualPath(variables_obj.male_deaths, target_year);
	let actual_md_raster = (actual_md_path && fs.existsSync(actual_md_path)) ? GeoPNG.loadNumberRasterImage(actual_md_path, { format: "float32" }) : null;

	let actual_b_checks = 0, actual_b_max_diff = 0;
	let b_denom = births_deaths_OLS._getCohort00Array(target_year);
	let actual_fd_checks = 0, actual_fd_max_diff = 0;
	let actual_md_checks = 0, actual_md_max_diff = 0;

	let actual_b_violations = 0;
	let actual_fd_violations = 0;
	let actual_md_violations = 0;

	let sum_m_min = 0;
	let sum_m_max = 0;

	// Load geocodes for country-level verification
	let geocode_obj = admin_modern.getISO3ColourcodesObject();
	let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
	let country_stats = {};
	let target_countries = ["RUS", "UKR", "BLR", "KAZ", "SWE", "FRA", "GBR", "DEU", "USA"];
	for (let c of target_countries) country_stats[c] = { pop: 0, b: 0, d: 0, m: 0 };

	for (let i = 0; i < popc_r.data.length; i++) {
		let pop = popc_r.data[i];
		if (pop <= 0 || isNaN(pop)) continue;

		populated_pixels++;
		total_pop += pop;

		let b = b_r.data[i] || 0;
		let fd = fd_r.data[i] || 0;
		let md = md_r.data[i] || 0;
		let d = fd + md;
		let m = m_r.data[i] || 0;
		let mf = mf_r.data[i] || 0;
		let mm = mm_r.data[i] || 0;
		let dpop_annual = (delta_r.data[i] || 0) / year_gap;

		total_b += b;
		total_fd += fd;
		total_md += md;
		total_m += m;
		total_mf += mf;
		total_mm += mm;
		total_dpop_annual += dpop_annual;

		// Check accounting identity: dpop/h == B - D + M with magnitude-aware tolerance
		let expected_dpop = b - d + m;
		let err = Math.abs(dpop_annual - expected_dpop);
		let tol = 1e-4 + 1e-6 * (Math.abs(dpop_annual) + Math.abs(b) + Math.abs(d) + Math.abs(m));
		if (err > tol) identity_violations++;

		if (err > max_identity_err) max_identity_err = err;
		sum_identity_err += err;

		// Check sex sum identities
		let mig_sex_err = Math.abs(m - (mf + mm));
		if (mig_sex_err > max_mig_sex_err) max_mig_sex_err = mig_sex_err;

		// Ground truth actuals preservation check (with IEEE 754 float32 round-trip tolerance)
		let is_b_act = false, is_fd_act = false, is_md_act = false;
		if (actual_b_raster && !isNaN(actual_b_raster.data[i]) && actual_b_raster.data[i] > 0) {
			actual_b_checks++;
			is_b_act = true;
			let act_val = actual_b_raster.data[i];
			let diff = Math.abs(b - act_val);
			let act_tol = 1e-4 + 1e-5 * act_val;
			if (diff > act_tol) actual_b_violations++;
			if (diff > actual_b_max_diff) actual_b_max_diff = diff;
		}
		if (actual_fd_raster && !isNaN(actual_fd_raster.data[i]) && actual_fd_raster.data[i] > 0) {
			actual_fd_checks++;
			is_fd_act = true;
			let act_val = actual_fd_raster.data[i];
			let diff = Math.abs(fd - act_val);
			let act_tol = 1e-4 + 1e-5 * act_val;
			if (diff > act_tol) actual_fd_violations++;
			if (diff > actual_fd_max_diff) actual_fd_max_diff = diff;
		}
		if (actual_md_raster && !isNaN(actual_md_raster.data[i]) && actual_md_raster.data[i] > 0) {
			actual_md_checks++;
			is_md_act = true;
			let act_val = actual_md_raster.data[i];
			let diff = Math.abs(md - act_val);
			let act_tol = 1e-4 + 1e-5 * act_val;
			if (diff > act_tol) actual_md_violations++;
			if (diff > actual_md_max_diff) actual_md_max_diff = diff;
		}

		// Track source-aware migration bounds
		let b_min = is_b_act ? b : 0;
		let max_cap = (b_denom && b_denom[i] > 0) ? (1.5 * b_denom[i]) : Math.max(b, pop * 0.06);
		let b_max = is_b_act ? b : Math.max(0, max_cap);
		let d_min = 0, d_max = pop;
		if (is_fd_act && is_md_act) {
			d_min = fd + md;
			d_max = fd + md;
		} else if (is_fd_act) {
			d_min = fd;
			d_max = Math.max(fd, pop);
		} else if (is_md_act) {
			d_min = md;
			d_max = Math.max(md, pop);
		}
		sum_m_min += (dpop_annual - b_max + d_min);
		sum_m_max += (dpop_annual - b_min + d_max);

		// Country aggregations
		if (geocode_raster) {
			let r_idx = i * 4;
			let rgb_key = `${geocode_raster.data[r_idx]},${geocode_raster.data[r_idx + 1]},${geocode_raster.data[r_idx + 2]}`;
			let iso_list = geocode_obj[rgb_key];
			if (iso_list && Array.isArray(iso_list)) {
				for (let c = 0; c < target_countries.length; c++) {
					let target_c = target_countries[c];
					if (iso_list.includes(target_c)) {
						country_stats[target_c].pop += pop;
						country_stats[target_c].b += b;
						country_stats[target_c].d += d;
						country_stats[target_c].m += m;
					}
				}
			}
		}
	}

	console.log(`\n--- RESULTS ACROSS ${populated_pixels.toLocaleString()} POPULATED PIXELS ---`);
	console.log(`Total Global Population:         ${(total_pop / 1e6).toFixed(2)}M`);
	console.log(`Total Annual Population Delta:    ${(total_dpop_annual / 1e6).toFixed(4)}M/yr`);
	console.log(`Total Global Births:             ${(total_b / 1e6).toFixed(4)}M/yr`);
	console.log(`Total Global Deaths:             ${((total_fd + total_md) / 1e6).toFixed(4)}M/yr (Female: ${(total_fd/1e6).toFixed(4)}M, Male: ${(total_md/1e6).toFixed(4)}M)`);
	console.log(`Total Global Net Migration:       ${total_m.toFixed(4)}/yr (Female: ${total_mf.toFixed(4)}, Male: ${total_mm.toFixed(4)})`);
	console.log(`\n--- ACCOUNTING IDENTITY CONVERGENCE ---`);
	console.log(`Max Identity Error |dP/h - (B - D + M)|: ${max_identity_err.toExponential(4)}`);
	console.log(`Mean Identity Error:                     ${(sum_identity_err / populated_pixels).toExponential(4)}`);
	console.log(`Magnitude-Aware Identity Violations:     ${identity_violations}`);
	console.log(`Max Migration Sex Split Error |M - (Mf + Mm)|: ${max_mig_sex_err.toExponential(4)}`);
	console.log(`Global Net Migration Balance (Sum M):    ${total_m.toFixed(6)}`);

	let is_zero_sum_feasible = (sum_m_min <= 0 && sum_m_max >= 0);
	console.log(`\n--- GLOBAL MIGRATION FEASIBILITY & CONSTRAINTS ---`);
	console.log(`Sum M_min:                               ${sum_m_min.toFixed(2)}`);
	console.log(`Sum M_max:                               ${sum_m_max.toFixed(2)}`);
	console.log(`Zero-Sum Net Migration Feasible:         ${is_zero_sum_feasible ? "YES" : "NO (External Dataset Macro Disparity)"}`);

	console.log(`\n--- GROUND TRUTH ACTUALS PRESERVATION ---`);
	if (actual_b_checks > 0) console.log(`Births: ${actual_b_checks.toLocaleString()} actual cells checked, max diff = ${actual_b_max_diff.toExponential(4)} (Violations: ${actual_b_violations})`);
	if (actual_fd_checks > 0) console.log(`Female Deaths: ${actual_fd_checks.toLocaleString()} actual cells checked, max diff = ${actual_fd_max_diff.toExponential(4)} (Violations: ${actual_fd_violations})`);
	if (actual_md_checks > 0) console.log(`Male Deaths: ${actual_md_checks.toLocaleString()} actual cells checked, max diff = ${actual_md_max_diff.toExponential(4)} (Violations: ${actual_md_violations})`);

	console.log(`\n--- COUNTRY-LEVEL COMPARISONS (${target_year}) ---`);
	console.log(`Country | Population | Births (M) | CBR (/1000) | Deaths (M) | CDR (/1000) | Net Mig (k)`);
	console.log(`:------ | :--------- | :--------- | :---------- | :--------- | :---------- | :----------`);
	for (let iso3 of target_countries) {
		let s = country_stats[iso3];
		let cbr = (s.pop > 0) ? (s.b / s.pop) * 1000 : 0;
		let cdr = (s.pop > 0) ? (s.d / s.pop) * 1000 : 0;
		console.log(`${iso3.padEnd(7)} | ${(s.pop / 1e6).toFixed(2).padStart(8)}M | ${(s.b / 1e6).toFixed(3).padStart(8)} | ${cbr.toFixed(2).padStart(11)} | ${(s.d / 1e6).toFixed(3).padStart(8)} | ${cdr.toFixed(2).padStart(11)} | ${(s.m / 1000).toFixed(1).padStart(11)}`);
	}

	console.log("\n================================================================================");
	let passed = (identity_violations === 0 && actual_b_violations === 0 && actual_fd_violations === 0 && actual_md_violations === 0);
	if (is_zero_sum_feasible) {
		if (Math.abs(total_m) >= 0.1) passed = false;
	} else {
		let expected_boundary = (sum_m_min > 0) ? sum_m_min : sum_m_max;
		let boundary_err = Math.abs(total_m - expected_boundary);
		console.log(`Boundary Projection Residual:            ${boundary_err.toExponential(4)}`);
		if (boundary_err > 5.0) passed = false;
	}

	if (passed) {
		console.log("PASSED: Demographic accounting identity, zero-sum migration, and ground truth strictly hold!");
	} else {
		console.error("FAILED: Constraint tolerance exceeded.");
		process.exit(1);
	}
	console.log("================================================================================");
})();
