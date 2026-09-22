/**
 * Pure demographic and Bayesian helpers used by age_sex_classifier.
 * This class deliberately contains no raster I/O so that stage behaviour can be tested cheaply.
 */
global.age_sex_classifier_demography = class {
	static stages = ["CDT1", "CDT2", "CDT3", "CDT4", "CDT5"];

	static _safeNumber (arg0_value, arg1_fallback) {
		let value = Number(arg0_value);
		return Number.isFinite(value) ? value : (arg1_fallback || 0);
	}

	static normalise (arg0_values) {
		let values = Array.from(arg0_values || [], (value) => Math.max(0, this._safeNumber(value, 0)));
		let total = values.reduce((sum, value) => sum + value, 0);
		if (total <= 0) return values.map(() => values.length ? 1/values.length : 0);
		return values.map((value) => value/total);
	}

	/**
	 * Reconstructs age-specific fertility from total births and a donor maternal-age shape.
	 * The donor is normally the nearest UNWPP country/region in 1950 for HMD observations.
	 */
	static reconstructFertilitySchedule (arg0_total_births, arg1_donor_births, arg2_female_exposure) {
		let total_births = Math.max(0, this._safeNumber(arg0_total_births, 0));
		let donor_births = arg1_donor_births || {};
		let female_exposure = arg2_female_exposure || {};
		let ages = Object.keys(donor_births).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
		let donor_total = ages.reduce((sum, age) => sum + Math.max(0, this._safeNumber(donor_births[age], 0)), 0);
		let allocated_births = {};
		let fertility_rates = {};

		for (let i = 0; i < ages.length; i++) {
			let age = ages[i];
			let share = donor_total > 0 ? Math.max(0, this._safeNumber(donor_births[age], 0))/donor_total : 0;
			let births = total_births*share;
			let exposure = Math.max(0, this._safeNumber(female_exposure[age], 0));
			allocated_births[age] = births;
			fertility_rates[age] = exposure > 0 ? births/exposure : 0;
		}

		return {
			ages: ages,
			allocated_births: allocated_births,
			fertility_rates: fertility_rates,
			total_births: Object.values(allocated_births).reduce((sum, value) => sum + value, 0)
		};
	}

	/**
	 * Solves 1 = Σ exp(-r*a) l(a) m_f(a) by bisection.
	 */
	static solveEulerLotka (arg0_fertility_rates, arg1_survivorship, arg2_options) {
		let fertility_rates = arg0_fertility_rates || {};
		let survivorship = arg1_survivorship || {};
		let options = arg2_options || {};
		let ages = Object.keys(fertility_rates).map(Number).filter(Number.isFinite).sort((a, b) => a - b);
		let female_birth_fraction = this._safeNumber(options.female_birth_fraction, 1/2.05);
		let lower = this._safeNumber(options.lower, -0.25);
		let upper = this._safeNumber(options.upper, 0.25);

		let equation = (rate) => {
			let total = 0;
			for (let i = 0; i < ages.length; i++) {
				let age = ages[i];
				let m = Math.max(0, this._safeNumber(fertility_rates[age], 0))*female_birth_fraction;
				let l = Math.max(0, Math.min(1, this._safeNumber(survivorship[age], 0)));
				total += Math.exp(-rate*(age + 2.5))*l*m*5;
			}
			return total - 1;
		};

		let f_lower = equation(lower);
		let f_upper = equation(upper);
		if (f_lower*f_upper > 0) return Math.abs(f_lower) < Math.abs(f_upper) ? lower : upper;

		for (let i = 0; i < 80; i++) {
			let midpoint = (lower + upper)/2;
			let f_midpoint = equation(midpoint);
			if (Math.abs(f_midpoint) < 1e-10) return midpoint;
			if (f_lower*f_midpoint <= 0) {
				upper = midpoint;
				f_upper = f_midpoint;
			} else {
				lower = midpoint;
				f_lower = f_midpoint;
			}
		}
		return (lower + upper)/2;
	}

	static seedStage (arg0_metrics, arg1_thresholds) {
		let metrics = arg0_metrics || {};
		let thresholds = {
			replacement_tfr: 2.15,
			low_tfr: 2.60,
			high_tfr: 4.00,
			low_mortality: 0.015,
			high_mortality: 0.025,
			negative_growth: -0.001,
			rapid_fertility_decline: -0.025,
			mortality_decline: -0.0002,
			...(arg1_thresholds || {})
		};
		let tfr = this._safeNumber(metrics.tfr, 5);
		let mortality = this._safeNumber(metrics.mortality_rate, thresholds.high_mortality);
		let growth = this._safeNumber(metrics.euler_lotka_r, this._safeNumber(metrics.natural_growth, 0));
		let delta_tfr = this._safeNumber(metrics.delta_tfr, 0);
		let delta_mortality = this._safeNumber(metrics.delta_mortality, 0);

		if (tfr <= thresholds.replacement_tfr && growth < thresholds.negative_growth) return "CDT5";
		if (tfr <= thresholds.low_tfr && mortality <= thresholds.low_mortality) return "CDT4";
		if (delta_tfr <= thresholds.rapid_fertility_decline ||
				(tfr < thresholds.high_tfr && mortality < thresholds.high_mortality)) return "CDT3";
		if (delta_mortality <= thresholds.mortality_decline ||
				(tfr >= thresholds.high_tfr && mortality < thresholds.high_mortality && growth > 0)) return "CDT2";
		return "CDT1";
	}

	static selectCovariates (arg0_rows, arg1_options) {
		let rows = arg0_rows || [];
		let options = arg1_options || {};
		let minimum_coverage = this._safeNumber(options.minimum_coverage, 0.80);
		let maximum_correlation = this._safeNumber(options.maximum_correlation, 0.97);
		let candidate_keys = options.candidate_keys || Array.from(new Set(rows.flatMap((row) => Object.keys(row.features || {}))));
		let selected = [];
		let statistics = {};

		for (let k = 0; k < candidate_keys.length; k++) {
			let key = candidate_keys[k];
			let weight_sum = 0;
			let weighted_sum = 0;
			let valid_count = 0;
			for (let i = 0; i < rows.length; i++) {
				let value = Number(rows[i].features?.[key]);
				if (!Number.isFinite(value)) continue;
				let weight = Math.max(0, this._safeNumber(rows[i].population, 1));
				valid_count++;
				weight_sum += weight;
				weighted_sum += weight*value;
			}
			if (rows.length === 0 || valid_count/rows.length < minimum_coverage || weight_sum <= 0) continue;
			let mean = weighted_sum/weight_sum;
			let variance = 0;
			for (let i = 0; i < rows.length; i++) {
				let value = Number(rows[i].features?.[key]);
				if (!Number.isFinite(value)) continue;
				let weight = Math.max(0, this._safeNumber(rows[i].population, 1));
				variance += weight*Math.pow(value - mean, 2);
			}
			variance /= weight_sum;
			if (variance <= 1e-12) continue;
			statistics[key] = { mean: mean, variance: variance };
			selected.push(key);
		}

		let final_keys = [];
		for (let k = 0; k < selected.length; k++) {
			let key = selected[k];
			let keep = true;
			for (let j = 0; j < final_keys.length && keep; j++) {
				let other_key = final_keys[j];
				let covariance = 0;
				let weight_sum = 0;
				for (let i = 0; i < rows.length; i++) {
					let a = Number(rows[i].features?.[key]);
					let b = Number(rows[i].features?.[other_key]);
					if (!Number.isFinite(a) || !Number.isFinite(b)) continue;
					let weight = Math.max(0, this._safeNumber(rows[i].population, 1));
					covariance += weight*(a - statistics[key].mean)*(b - statistics[other_key].mean);
					weight_sum += weight;
				}
				if (weight_sum > 0) covariance /= weight_sum;
				let correlation = covariance/Math.sqrt(statistics[key].variance*statistics[other_key].variance);
				if (Math.abs(correlation) >= maximum_correlation) keep = false;
			}
			if (keep) final_keys.push(key);
		}
		return final_keys;
	}

	static fitBayesClassifier (arg0_rows, arg1_feature_keys) {
		let rows = arg0_rows || [];
		let feature_keys = arg1_feature_keys || [];
		let model = {
			type: "gaussian_bayes_cdt",
			stages: [...this.stages],
			feature_keys: [...feature_keys],
			classes: {}
		};
		let global_weight = rows.reduce((sum, row) => sum + Math.max(0, this._safeNumber(row.population, 1)), 0);

		for (let s = 0; s < this.stages.length; s++) {
			let stage = this.stages[s];
			let stage_rows = rows.filter((row) => row.stage === stage);
			let stage_weight = stage_rows.reduce((sum, row) => sum + Math.max(0, this._safeNumber(row.population, 1)), 0);
			let local_class = {
				prior: global_weight > 0 ? stage_weight/global_weight : 1/this.stages.length,
				features: {}
			};
			for (let k = 0; k < feature_keys.length; k++) {
				let key = feature_keys[k];
				let weight_sum = 0;
				let mean = 0;
				for (let i = 0; i < stage_rows.length; i++) {
					let value = Number(stage_rows[i].features?.[key]);
					if (!Number.isFinite(value)) continue;
					let weight = Math.max(0, this._safeNumber(stage_rows[i].population, 1));
					mean += weight*value;
					weight_sum += weight;
				}
				mean = weight_sum > 0 ? mean/weight_sum : 0;
				let variance = 0;
				for (let i = 0; i < stage_rows.length; i++) {
					let value = Number(stage_rows[i].features?.[key]);
					if (!Number.isFinite(value)) continue;
					let weight = Math.max(0, this._safeNumber(stage_rows[i].population, 1));
					variance += weight*Math.pow(value - mean, 2);
				}
				variance = weight_sum > 0 ? variance/weight_sum : 1;
				local_class.features[key] = { mean: mean, variance: Math.max(variance, 1e-8) };
			}
			model.classes[stage] = local_class;
		}
		return model;
	}

	static predictBayesWeights (arg0_features, arg1_model) {
		let features = arg0_features || {};
		let model = arg1_model || {};
		let stages = model.stages || this.stages;
		let log_probabilities = [];
		for (let s = 0; s < stages.length; s++) {
			let local_class = model.classes?.[stages[s]] || {};
			let log_probability = Math.log(Math.max(this._safeNumber(local_class.prior, 0), 1e-15));
			let keys = model.feature_keys || [];
			for (let k = 0; k < keys.length; k++) {
				let parameter = local_class.features?.[keys[k]];
				let value = Number(features[keys[k]]);
				if (!parameter || !Number.isFinite(value)) continue;
				let variance = Math.max(this._safeNumber(parameter.variance, 1), 1e-8);
				let difference = value - this._safeNumber(parameter.mean, 0);
				log_probability += -0.5*(Math.log(2*Math.PI*variance) + difference*difference/variance);
			}
			log_probabilities.push(log_probability);
		}
		let maximum = Math.max(...log_probabilities);
		return this.normalise(log_probabilities.map((value) => Math.max(1e-300, Math.exp(value - maximum))));
	}

	/**
	 * Forward Bayesian filter. M1 can remain in its stage or advance by one stage only;
	 * temporary reversals belong in M2 rather than in the baseline demographic transition.
	 */
	static constrainStageSequence (arg0_observations, arg1_model, arg2_options) {
		let observations = [...(arg0_observations || [])].sort((a, b) => a.year - b.year);
		let options = arg2_options || {};
		let stay_probability = this._safeNumber(options.stay_probability, 0.85);
		let weights = options.initial_weights ?
			this.normalise(options.initial_weights) : [1, 0, 0, 0, 0];
		let results = [];

		for (let i = 0; i < observations.length; i++) {
			let emission = this.predictBayesWeights(observations[i].features, arg1_model);
			if (i === 0 && options.initial_from_emission)
				weights = emission;
			else {
				let predicted = new Array(this.stages.length).fill(0);
				for (let s = 0; s < this.stages.length; s++) {
					predicted[s] += weights[s]*(s === this.stages.length - 1 ? 1 : stay_probability);
					if (s < this.stages.length - 1) predicted[s + 1] += weights[s]*(1 - stay_probability);
				}
				weights = this.normalise(predicted.map((value, index) => value*emission[index]));
			}
			let maximum_index = weights.indexOf(Math.max(...weights));
			results.push({
				...observations[i],
				stage: this.stages[maximum_index],
				stage_weights: Object.fromEntries(this.stages.map((stage, index) => [stage, weights[index]]))
			});
		}
		return results;
	}
};
