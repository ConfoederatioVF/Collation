global.migration_OLS = class {
	static bf = `${h2}/migration_OLS/`;
	static covariates_obj = () => ({
		...age_sex.covariates_obj,
		"gini": (y) => [`${gini_Eoscala.output_rasters}gini_${y}.png`, "float32"]
	});
	static intermediate_target = `${this.bf}/0.target/`;
	static intermediate_ols = `${this.bf}/1.OLS/`;
	static intermediate_normalised = `${this.bf}/2.normalised/`;
	static intermediate_bounds = `${this.bf}/2.bounds/`;
	
	static output_female_migration_folder = `${h2}/births_deaths_OLS/4.female_net_migration/`;
	static output_male_migration_folder = `${h2}/births_deaths_OLS/4.male_net_migration/`;
	static output_net_migration_folder = `${h2}/births_deaths_OLS/4.net_migration/`;

	static async A_generateTargetRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let years = landuse_HYDE.sorted_hyde_years.filter(y => y >= 1950);
		
		await GeoPNG.processTimeseriesParallel({
			items: years,
			concurrency: options.concurrency || 4,
			name: "migration_OLS A_generateTargetRasters",
			handler: async (year) => {
				let target_path = `${this.intermediate_target}migration_target_${year}.png`;
				if (!overwrite && fs.existsSync(target_path)) return;
				
				let b_path = `${births_deaths_UNWPP.output_crude_births_folder}births_${year}.png`;
				let fd_path = `${births_deaths_UNWPP.output_female_crude_deaths_folder}female_deaths_${year}.png`;
				let md_path = `${births_deaths_UNWPP.output_male_crude_deaths_folder}male_deaths_${year}.png`;
				let delta_path = `${population_Stadester_transform.delta_total_population_folder}delta_total_population_${year}.png`;
				let popc_path = `${age_sex.sf().input_popc_folder}stadester_population_${year}.png`;
				
				if (!fs.existsSync(b_path) || !fs.existsSync(fd_path) || !fs.existsSync(md_path) || !fs.existsSync(delta_path) || !fs.existsSync(popc_path)) return;
				
				let b_r = GeoPNG.loadNumberRasterImage(b_path, { format: "float32" });
				let fd_r = GeoPNG.loadNumberRasterImage(fd_path, { format: "float32" });
				let md_r = GeoPNG.loadNumberRasterImage(md_path, { format: "float32" });
				let delta_r = GeoPNG.loadNumberRasterImage(delta_path, { format: "float32" });
				let popc_r = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
				
				GeoPNG.saveNumberRasterImage({
					file_path: target_path,
					format: "float32",
					width: b_r.width,
					height: b_r.height,
					function: (i) => {
						let pop = popc_r.data[i];
						if (pop < 1.0 || isNaN(pop)) return 0;
						
						let b = isNaN(b_r.data[i]) ? 0 : Math.max(0, b_r.data[i]);
						let fd = isNaN(fd_r.data[i]) ? 0 : Math.max(0, fd_r.data[i]);
						let md = isNaN(md_r.data[i]) ? 0 : Math.max(0, md_r.data[i]);
						let dpop = isNaN(delta_r.data[i]) ? 0 : delta_r.data[i];
						
						let actual_migration = dpop - (b - (fd + md));
						let ratio = actual_migration / pop;
						
						if (ratio > 10) ratio = 10;
						if (ratio < -10) ratio = -10;
						return ratio;
					}
				});
				console.log(`- Generated migration target raster: ${target_path}`);
			}
		});
	}
	
	static async B_trainOLSModels (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let lambda_val = (options.lambda !== undefined) ? options.lambda : 1;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		let covariates_obj = this.covariates_obj();
		let years = landuse_HYDE.sorted_hyde_years;
		
		let target_years = years.filter((year) => {
			let target_path = `${this.intermediate_target}migration_target_${year}.png`;
			let model_path = `${this.intermediate_ols}OLS_migration_${year}.json`;
			if (!fs.existsSync(target_path)) return false;
			if (!overwrite && fs.existsSync(model_path)) return false;
			return true;
		});
		
		if (target_years.length > 0) {
			await Statistics.trainOLSModelsParallel(target_years, (year) => {
				let covariates_map = {};
				let format_year = Math.min(year, 2023);
				for (let key in covariates_obj) covariates_map[key] = covariates_obj[key](format_year);
				
				return {
					covariates_map: covariates_map,
					options: { key: year.toString(), lambda: lambda_val },
					output_file_path: `${this.intermediate_ols}OLS_migration_${year}.json`,
					target_file_path: `${this.intermediate_target}migration_target_${year}.png`,
					target_format: "float32"
				};
			}, { concurrency: options.concurrency, name: `OLS Training (migration)` });
		}
		
		try {
			await Statistics.geomeanOLSModels(this.intermediate_ols, "OLS_migration_", {
				weighting_function: (value) => Math.abs(value)
			});
		} catch (e) {
			console.error(`Error calculating geomean for migration models:`, e);
		}
	}
	
	static async C_generateOLSRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		
		let covariates_obj = this.covariates_obj();
		let years = landuse_HYDE.sorted_hyde_years;
		let unified_model_path = `${this.intermediate_ols}geomean_OLS_migration.json`;
		
		let target_years = years.filter((year) => {
			let output_path = `${this.intermediate_ols}ols_migration_${year}.png`;
			if (!overwrite && fs.existsSync(output_path)) return false;
			let model_path = `${this.intermediate_ols}OLS_migration_${year}.json`;
			return fs.existsSync(model_path) || fs.existsSync(unified_model_path);
		});
		
		if (target_years.length > 0) {
			await Statistics.generateOLSRastersParallel(target_years, (year) => {
				let covariates_map = {};
				let format_year = Math.min(year, 2023);
				let model_path = `${this.intermediate_ols}OLS_migration_${year}.json`;
				if (!fs.existsSync(model_path)) model_path = unified_model_path;
				for (let key in covariates_obj) covariates_map[key] = covariates_obj[key](format_year);
				
				return {
					covariates_map: covariates_map,
					model_obj: model_path,
					options: { format: "float32" },
					output_file_path: `${this.intermediate_ols}ols_migration_${year}.png`
				};
			}, { concurrency: options.concurrency, name: `OLS Raster Generation (migration)` });
		}
	}
	
	static async D_normaliseOLSRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let years = landuse_HYDE.sorted_hyde_years;
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "int32" });
		
		let global_min = Infinity;
		let global_max = -Infinity;
		let yearly_target_stats = {};
		
		for (let y = 0; y < years.length; y++) {
			let year = years[y];
			let target_path = `${this.intermediate_target}migration_target_${year}.png`;
			if (!fs.existsSync(target_path)) continue;
			
			let target_raster = GeoPNG.loadNumberRasterImage(target_path, { format: "float32" });
			let local_min = Infinity;
			let local_max = -Infinity;
			let local_count = 0;
			
			for (let i = 0; i < target_raster.data.length; i++) {
				let val = target_raster.data[i];
				if (!isNaN(val) && Math.abs(val) > 1e-10) {
					if (val < local_min) local_min = val;
					if (val > local_max) local_max = val;
					local_count++;
				}
			}
			if (local_count > 0) {
				yearly_target_stats[year] = { min: local_min, max: local_max, sample_size: local_count };
				if (local_min < global_min) global_min = local_min;
				if (local_max > global_max) global_max = local_max;
			}
		}
		
		if (global_min === Infinity) return;
		
		await GeoPNG.processTimeseriesParallel({
			items: years,
			concurrency: options.concurrency || 4,
			name: `migration_OLS D_normaliseOLSRasters`,
			handler: async (year) => {
				let popc_path = `${age_sex.sf().input_popc_folder}stadester_population_${year}.png`;
				let ols_path = `${this.intermediate_ols}ols_migration_${year}.png`;
				let normalised_path = `${this.intermediate_normalised}normalised_migration_${year}.png`;
				let bounds_path = `${this.intermediate_bounds}bounds_migration_${year}.json`;
				
				if (!fs.existsSync(popc_path) || !fs.existsSync(ols_path)) return;
				if (!overwrite && fs.existsSync(normalised_path) && fs.existsSync(bounds_path)) return;
				
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
				let ols_raster = GeoPNG.loadNumberRasterImage(ols_path, { format: "float32" });
				
				let local_stats = yearly_target_stats[year];
				let has_targets = (local_stats !== undefined);
				let sample_size = (local_stats) ? local_stats.sample_size : 0;
				let target_min = (local_stats) ? local_stats.min : global_min;
				let target_max = (local_stats) ? local_stats.max : global_max;
				
				let uncertainty_weight = Math.exp(-sample_size/15);
				target_min = target_min - ((target_min - global_min)*uncertainty_weight);
				target_max = target_max + ((global_max - target_max)*uncertainty_weight);
				
				let valid_pixels = [];
				for (let i = 0; i < ols_raster.data.length; i++) {
					if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
						let v = ols_raster.data[i];
						if (!isNaN(v)) valid_pixels.push(v);
					}
				}
				if (valid_pixels.length === 0) return;
				valid_pixels.sort((a, b) => a - b);
				
				let N = valid_pixels.length;
				let sum = valid_pixels.reduce((a,b)=>a+b,0);
				let mean = sum/N;
				let sq_sum = 0;
				for(let i=0;i<N;i++) sq_sum += Math.pow(valid_pixels[i]-mean,2);
				let std = Math.sqrt(sq_sum/N);
				
				let q1 = valid_pixels[Math.floor(N*0.25)];
				let q3 = valid_pixels[Math.floor(N*0.75)];
				let iqr = q3 - q1;
				let alpha = (iqr > 1e-5) ? iqr : ((std > 1e-5) ? std : 0.01);
				
				let t_lower = q1 - (1.5*alpha);
				let t_upper = q3 + (1.5*alpha);
				
				let regularise = (x) => {
					if (x > t_upper) return t_upper + alpha*Math.log(1 + ((x - t_upper)/alpha));
					if (x < t_lower) return t_lower - alpha*Math.log(1 + ((t_lower - x)/alpha));
					return x;
				};
				
				let reg_min = regularise(valid_pixels[0]);
				let reg_max = regularise(valid_pixels[N - 1]);
				let reg_range = reg_max - reg_min;
				
				let normalised_map = new Float32Array(ols_raster.data.length);
				for (let i = 0; i < ols_raster.data.length; i++) {
					if (landarea_raster.data[i] > 0 && popc_raster.data[i] > 0) {
						let v = ols_raster.data[i];
						if (!isNaN(v)) {
							let reg_v = regularise(v);
							let unit_v = (reg_range > 0) ? ((reg_v - reg_min)/reg_range) : 0.5;
							normalised_map[i] = Math.max(0, Math.min(1, unit_v));
						}
					}
				}
				
				GeoPNG.saveNumberRasterImage({
					file_path: normalised_path,
					format: "float32",
					width: ols_raster.width,
					height: ols_raster.height,
					function: (i) => normalised_map[i]
				});
				fs.writeFileSync(bounds_path, JSON.stringify({ year, has_targets, target_min, target_max, sample_size }));
				console.log(`- Normalised migration raster: ${normalised_path}`);
			}
		});
	}
	
	static async E_deriveFinalRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let years = landuse_HYDE.sorted_hyde_years;
		
		await GeoPNG.processTimeseriesParallel({
			items: years,
			concurrency: options.concurrency || 4,
			name: "migration_OLS E_deriveFinalRasters",
			handler: async (year) => {
				let popc_path = `${age_sex.sf().input_popc_folder}stadester_population_${year}.png`;
				if (!fs.existsSync(popc_path)) return;
				
				let normalised_path = `${this.intermediate_normalised}normalised_migration_${year}.png`;
				let bounds_path = `${this.intermediate_bounds}bounds_migration_${year}.json`;
				
				if (!fs.existsSync(normalised_path) || !fs.existsSync(bounds_path)) return;
				
				let net_out = `${this.output_net_migration_folder}net_migration_${year}.png`;
				let female_out = `${this.output_female_migration_folder}female_net_migration_${year}.png`;
				let male_out = `${this.output_male_migration_folder}male_net_migration_${year}.png`;
				
				if (!overwrite && fs.existsSync(net_out) && fs.existsSync(female_out) && fs.existsSync(male_out)) return;
				
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_path, { format: "float32" });
				let normalised_raster = GeoPNG.loadNumberRasterImage(normalised_path, { format: "float32" });
				let bounds_obj = JSON.parse(fs.readFileSync(bounds_path, "utf8"));
				let target_min = bounds_obj.target_min || 0;
				let target_max = bounds_obj.target_max || 0;
				
				let migration_array = new Float32Array(popc_raster.data.length);
				for (let i = 0; i < popc_raster.data.length; i++) {
					let pop = popc_raster.data[i];
					if (pop <= 0) continue;
					
					let norm_val = normalised_raster.data[i];
					if (isNaN(norm_val)) continue;
					
					let ratio = target_min + norm_val * (target_max - target_min);
					migration_array[i] = ratio * pop;
				}
				
				// Apply anchoring if UNWPP target year
				let b_path = `${births_deaths_UNWPP.output_crude_births_folder}births_${year}.png`;
				let fd_path = `${births_deaths_UNWPP.output_female_crude_deaths_folder}female_deaths_${year}.png`;
				let md_path = `${births_deaths_UNWPP.output_male_crude_deaths_folder}male_deaths_${year}.png`;
				let delta_path = `${population_Stadester_transform.delta_total_population_folder}delta_total_population_${year}.png`;
				let actual_migration_raster = null;
				let has_actual = fs.existsSync(b_path) && fs.existsSync(fd_path) && fs.existsSync(md_path) && fs.existsSync(delta_path);
				
				if (has_actual) {
					let b_r = GeoPNG.loadNumberRasterImage(b_path, { format: "float32" });
					let fd_r = GeoPNG.loadNumberRasterImage(fd_path, { format: "float32" });
					let md_r = GeoPNG.loadNumberRasterImage(md_path, { format: "float32" });
					let delta_r = GeoPNG.loadNumberRasterImage(delta_path, { format: "float32" });
					actual_migration_raster = new Float32Array(popc_raster.data.length);
					for(let i=0;i<popc_raster.data.length;i++){
						let dpop = isNaN(delta_r.data[i])?0:delta_r.data[i];
						let b = isNaN(b_r.data[i])?0:Math.max(0,b_r.data[i]);
						let fd = isNaN(fd_r.data[i])?0:Math.max(0,fd_r.data[i]);
						let md = isNaN(md_r.data[i])?0:Math.max(0,md_r.data[i]);
						actual_migration_raster[i] = dpop - (b - (fd+md));
					}
				}
				
				let final_m_array = new Float32Array(popc_raster.data.length);
				let final_mf_array = new Float32Array(popc_raster.data.length);
				let final_mm_array = new Float32Array(popc_raster.data.length);
				
				for (let i = 0; i < popc_raster.data.length; i++) {
					let m = (has_actual && !isNaN(actual_migration_raster[i])) ? actual_migration_raster[i] : migration_array[i];
					if (isNaN(m)) m = 0;
					final_m_array[i] = m;
					final_mf_array[i] = m * 0.488;
					final_mm_array[i] = m * 0.512;
				}
				
				GeoPNG.saveNumberRasterImage({ file_path: net_out, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => final_m_array[i] });
				GeoPNG.saveNumberRasterImage({ file_path: female_out, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => final_mf_array[i] });
				GeoPNG.saveNumberRasterImage({ file_path: male_out, format: "float32", width: popc_raster.width, height: popc_raster.height, function: (i) => final_mm_array[i] });
				console.log(`- Saved final migration rasters for ${year}`);
			}
		});
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		
		let all_folders = [
			this.intermediate_target, this.intermediate_ols, this.intermediate_normalised, this.intermediate_bounds,
			this.output_female_migration_folder, this.output_male_migration_folder, this.output_net_migration_folder
		];
		for (let i = 0; i < all_folders.length; i++) if (!fs.existsSync(all_folders[i])) fs.mkdirSync(all_folders[i], { recursive: true });
		
		if (!options.exclude.includes("A") && !skip_training) await this.A_generateTargetRasters(options);
		if (!options.exclude.includes("B") && !skip_training) await this.B_trainOLSModels(options);
		if (!options.exclude.includes("C")) await this.C_generateOLSRasters(options);
		if (!options.exclude.includes("D")) await this.D_normaliseOLSRasters(options);
		if (!options.exclude.includes("E")) await this.E_deriveFinalRasters(options);
	}
};
