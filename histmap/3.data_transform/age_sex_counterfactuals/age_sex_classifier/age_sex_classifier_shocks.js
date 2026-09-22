/**
 * Static M2 age/sex shock handling. Shocks operate on cohort counts and are then
 * projected back onto the fixed Stadestér population simplex. No PAVA is used.
 */
global.age_sex_classifier_shocks = class {
	static _safeNumber (arg0_value, arg1_fallback) {
		let value = Number(arg0_value);
		return Number.isFinite(value) ? value : (arg1_fallback || 0);
	}

	static loadCatalogue (arg0_file_path) {
		if (!fs.existsSync(arg0_file_path)) return { shocks: [] };
		let parser = (typeof JSON5 !== "undefined") ? JSON5 : require("json5");
		return parser.parse(fs.readFileSync(arg0_file_path, "utf8"));
	}

	static validateCatalogue (arg0_catalogue, arg1_type) {
		let catalogue = arg0_catalogue || {};
		let errors = [];
		let ids = new Set();
		let shocks = Array.isArray(catalogue.shocks) ? catalogue.shocks : [];
		for (let i = 0; i < shocks.length; i++) {
			let shock = shocks[i];
			if (!shock.id || ids.has(shock.id)) errors.push(`Shock ${i} has a missing or duplicate id.`);
			ids.add(shock.id);
			if (shock.type !== arg1_type) errors.push(`${shock.id || i} must have type '${arg1_type}'.`);
			if (!Number.isFinite(Number(shock.start_year))) errors.push(`${shock.id || i} has no start_year.`);
			if (!shock.source?.url || !shock.source?.citation) errors.push(`${shock.id || i} has incomplete source metadata.`);
			if (!Array.isArray(shock.geocodes) || shock.geocodes.length === 0) errors.push(`${shock.id || i} has no geocodes.`);
		}
		return errors;
	}

	static _cohortMetadata (arg0_cohort) {
		let match = String(arg0_cohort).match(/^([fm])_(\d{2})$/);
		if (!match) return null;
		let start = Number(match[2]);
		let end = start === 0 ? 0 : (start === 1 ? 4 : (start === 80 ? 110 : start + 4));
		return { sex: match[1], start: start, end: end, midpoint: (start + end)/2 };
	}

	static _appliesToGeocode (arg0_shock, arg1_geocode) {
		let shock = arg0_shock || {};
		let geocode = String(arg1_geocode || "");
		let included = shock.geocodes?.includes("*") || shock.geocodes?.includes(geocode);
		let excluded = shock.exclude_geocodes?.includes(geocode);
		return included && !excluded;
	}

	static _getPulseYears (arg0_shock, arg1_target_year) {
		let shock = arg0_shock || {};
		let target_year = Number(arg1_target_year);
		let start = Number(shock.start_year);
		let end = Number.isFinite(Number(shock.end_year)) ? Number(shock.end_year) : start;
		if (target_year < start) return [];
		if (Array.isArray(shock.pulse_years))
			return shock.pulse_years.map(Number).filter((year) => Number.isFinite(year) && year <= target_year);
		if (start === end) return [start];
		let duration = Math.max(1, end - start + 1);
		let step = duration <= 10 ? 1 : (duration <= 60 ? 5 : 10);
		let years = [];
		for (let year = start; year <= Math.min(end, target_year); year += step) years.push(year);
		if (years.length === 0 || years[years.length - 1] !== Math.min(end, target_year))
			years.push(Math.min(end, target_year));
		return years;
	}

	static _profileWeights (arg0_cohorts, arg1_profile, arg2_elapsed_years) {
		let cohorts = arg0_cohorts || [];
		let profile = Array.isArray(arg1_profile) ? arg1_profile : [];
		let elapsed_years = Math.max(0, Number(arg2_elapsed_years) || 0);
		let weights = new Array(cohorts.length).fill(0);
		for (let c = 0; c < cohorts.length; c++) {
			let metadata = this._cohortMetadata(cohorts[c]);
			if (!metadata) continue;
			let event_age = metadata.midpoint - elapsed_years;
			for (let p = 0; p < profile.length; p++) {
				let local = profile[p];
				let sex_matches = !local.sex || local.sex === "*" || local.sex === metadata.sex;
				let minimum_age = Number(local.min_age ?? 0);
				let maximum_age = Number(local.max_age ?? 110);
				if (sex_matches && event_age >= minimum_age && event_age <= maximum_age)
					weights[c] += Math.max(0, this._safeNumber(local.weight, 1));
			}
		}
		let total = weights.reduce((sum, value) => sum + value, 0);
		return total > 0 ? weights.map((value) => value/total) : weights;
	}

	static _applyFertilityShock (arg0_counts, arg1_cohorts, arg2_shock, arg3_target_year) {
		let counts = arg0_counts;
		let cohorts = arg1_cohorts;
		let shock = arg2_shock;
		let pulse_years = this._getPulseYears(shock, arg3_target_year);
		let relative_change = this._safeNumber(shock.relative_birth_change, 0);
		let retention = Math.max(0, Math.min(1, this._safeNumber(shock.annual_retention, 1)));
		for (let p = 0; p < pulse_years.length; p++) {
			let elapsed = Number(arg3_target_year) - pulse_years[p];
			for (let c = 0; c < cohorts.length; c++) {
				let metadata = this._cohortMetadata(cohorts[c]);
				if (!metadata || elapsed < metadata.start || elapsed > metadata.end) continue;
				let band_width = metadata.end - metadata.start + 1;
				counts[c] += counts[c]*(relative_change/band_width)*Math.pow(retention, elapsed);
			}
		}
	}

	static _applyCountShock (arg0_counts, arg1_cohorts, arg2_shock, arg3_target_year, arg4_total_population) {
		let counts = arg0_counts;
		let cohorts = arg1_cohorts;
		let shock = arg2_shock;
		let pulse_years = this._getPulseYears(shock, arg3_target_year);
		let total_fraction = this._safeNumber(shock.population_fraction, 0);
		let retention = Math.max(0, Math.min(1, this._safeNumber(shock.annual_retention, 1)));
		if (pulse_years.length === 0 || total_fraction === 0) return;
		let per_pulse_fraction = total_fraction/pulse_years.length;
		for (let p = 0; p < pulse_years.length; p++) {
			let elapsed = Number(arg3_target_year) - pulse_years[p];
			let profile_weights = this._profileWeights(cohorts, shock.age_sex_profile, elapsed);
			let signed_count = arg4_total_population*per_pulse_fraction*Math.pow(retention, elapsed);
			if (shock.type === "mortality") signed_count = -Math.abs(signed_count);
			for (let c = 0; c < cohorts.length; c++)
				counts[c] += signed_count*profile_weights[c];
		}
	}

	static applyShocks (arg0_counts_obj, arg1_context) {
		let counts_obj = arg0_counts_obj || {};
		let context = arg1_context || {};
		let cohorts = context.cohorts || Object.keys(counts_obj);
		let counts = cohorts.map((cohort) => Math.max(0, this._safeNumber(counts_obj[cohort], 0)));
		let original_total = counts.reduce((sum, value) => sum + value, 0);

		//Direct observations are evidence, not a canvas for historical priors.
		if (context.empirical_available || original_total <= 0)
			return Object.fromEntries(cohorts.map((cohort, index) => [cohort, counts[index]]));

		let catalogues = context.catalogues || {};
		let ordered_types = ["fertility", "mortality", "migration"];
		for (let t = 0; t < ordered_types.length; t++) {
			let type = ordered_types[t];
			let shocks = catalogues[type]?.shocks || [];
			for (let s = 0; s < shocks.length; s++) {
				let shock = shocks[s];
				if (!this._appliesToGeocode(shock, context.geocode)) continue;
				if (Number(context.year) < Number(shock.start_year)) continue;
				if (type === "fertility")
					this._applyFertilityShock(counts, cohorts, shock, context.year);
				else
					this._applyCountShock(counts, cohorts, shock, context.year, original_total);
			}
		}

		for (let c = 0; c < counts.length; c++)
			counts[c] = Math.max(0, this._safeNumber(counts[c], 0));
		let adjusted_total = counts.reduce((sum, value) => sum + value, 0);
		if (adjusted_total > 0) {
			let scalar = original_total/adjusted_total;
			for (let c = 0; c < counts.length; c++) counts[c] *= scalar;
		}
		return Object.fromEntries(cohorts.map((cohort, index) => [cohort, counts[index]]));
	}
};
