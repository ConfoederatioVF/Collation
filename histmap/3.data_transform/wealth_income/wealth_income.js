global.wealth_income = class {
	static cf = `${h3}/wealth_income/`;
	
	// Final Output Folders
	static output_discretionary_income_folder = `${this.cf}1.discretionary_income/`;
	static output_disposable_income_folder = `${this.cf}1.disposable_income/`;
	static output_net_income_folder = `${this.cf}1.net_income/`;
	static output_net_wealth_folder = `${this.cf}1.net_wealth/`;
	
	// Intermediate Folders
	static intermediate_normalised_rasters = `${this.cf}intermediate/1.normalised/`;
	static intermediate_clamped_rasters = `${this.cf}intermediate/2.clamped/`;
	
	static options = {
		interpolate_to_WID_domain: [1700, 1800]
	};
	
	//[QUARANTINE]
	static getOutputFolder (arg0_variable) {
		switch (arg0_variable) {
			case "discretionary_income": return this.output_discretionary_income_folder;
			case "disposable_income": return this.output_disposable_income_folder;
			case "net_income": return this.output_net_income_folder;
			case "net_wealth": return this.output_net_wealth_folder;
			default: return `${this.cf}1.${arg0_variable}/`;
		}
	}
	
	static async A_normaliseOLSRasters () {
		let variables = wealth_income_WID.options.variables;
		let years = landuse_HYDE.sorted_hyde_years;
		let src_dir = wealth_income_OLS.intermediate_ols_rasters_folder;
		
		let dest_dir = this.intermediate_normalised_rasters;
		if (!fs.existsSync(dest_dir)) fs.mkdirSync(dest_dir, { recursive: true });
		
		let landarea_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, { format: "int32" });
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_src_dir = `${src_dir}${current_variable}/`;
			let local_dest_dir = `${dest_dir}${current_variable}/`;
			if (!fs.existsSync(local_dest_dir)) fs.mkdirSync(local_dest_dir, { recursive: true });
			
			for (let x = 0; x < years.length; x++) {
				let year = years[x];
				let source_path = `${local_src_dir}OLS_${current_variable}_${year}.png`;
				let output_path = `${local_dest_dir}OLS_normalised_${current_variable}_${year}.png`;
				
				if (!fs.existsSync(source_path)) continue;
				
				let raw_raster = GeoPNG.loadNumberRasterImage(source_path, { format: "float32" });
				let format_year = year > 2023 ? 2023 : year;
				let popc_info = wealth_income_OLS.covariates_obj["popc_"](format_year);
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
				
				// 1. Gather valid data & calculate robust statistics
				let valid_pixels = [];
				let sum = 0;
				
				for (let j = 0; j < raw_raster.data.length; j++) {
					if (landarea_raster.data[j] > 0 && popc_raster.data[j] > 0) {
						let val = raw_raster.data[j];
						if (val > 0) {
							valid_pixels.push(val);
							sum += val;
						}
					}
				}
				
				let normalised_map = new Float32Array(raw_raster.data.length);
				
				if (valid_pixels.length > 0) {
					valid_pixels.sort((a, b) => a - b);
					let N = valid_pixels.length;
					
					let mean = sum / N;
					let sq_sum = 0;
					for (let j = 0; j < N; j++) sq_sum += Math.pow(valid_pixels[j] - mean, 2);
					let std = Math.sqrt(sq_sum / N);
					
					let Q1 = valid_pixels[Math.floor(N * 0.25)];
					let Q3 = valid_pixels[Math.floor(N * 0.75)];
					let IQR = Q3 - Q1;
					
					let alpha = (IQR > 1e-5) ? IQR : ((std > 1e-5) ? std : mean * 0.1);
					
					let T_lower = Math.max(0, Q1 - (1.5 * alpha));
					let T_upper = Q3 + (1.5 * alpha);
					
					// 2. C1-Continuous Log-Tail Regularisation
					const regularise = (val) => {
						if (val > T_upper) {
							return T_upper + alpha * Math.log(1 + ((val - T_upper) / alpha));
						} else if (val < T_lower) {
							return Math.max(0, T_lower - alpha * Math.log(1 + ((T_lower - val) / alpha)));
						}
						return val;
					};
					
					for (let j = 0; j < raw_raster.data.length; j++) {
						if (landarea_raster.data[j] > 0 && popc_raster.data[j] > 0) {
							normalised_map[j] = regularise(raw_raster.data[j]);
						} else {
							normalised_map[j] = 0;
						}
					}
					console.log(`Normalising ${current_variable} for ${year} using Log-Tail Regularisation.`);
				} else {
					console.log(`Skipping normalisation for ${current_variable} in ${year} (no inhabited pixels).`);
				}
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: 4320,
					height: 2160,
					function: (local_index) => normalised_map[local_index]
				});
				
				await Blacktraffic.yield();
			}
		}
	}
	
	static async B_clampOLSRasters () {
		let variables = wealth_income_WID.options.variables;
		let years = landuse_HYDE.sorted_hyde_years;
		
		let src_dir = this.intermediate_normalised_rasters;
		let dest_dir = this.intermediate_clamped_rasters;
		if (!fs.existsSync(dest_dir)) fs.mkdirSync(dest_dir, { recursive: true });
		
		let geocode_obj = admin_modern.getWIDColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_iso2_geocodes_raster);
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_src_dir = `${src_dir}${current_variable}/`;
			let local_dest_dir = `${dest_dir}${current_variable}/`;
			if (!fs.existsSync(local_dest_dir)) fs.mkdirSync(local_dest_dir, { recursive: true });
			
			// Load Target WID JSON for the variable
			let wid_json_path = `${wealth_income_WID.input_json}${current_variable}.json`;
			let wid_targets = fs.existsSync(wid_json_path) ? JSON.parse(fs.readFileSync(wid_json_path, "utf8")) : {};
			
			for (let x = 0; x < years.length; x++) {
				let year = years[x];
				let source_path = `${local_src_dir}OLS_normalised_${current_variable}_${year}.png`;
				let output_path = `${local_dest_dir}clamped_${current_variable}_${year}.png`;
				
				if (!fs.existsSync(source_path)) continue;
				
				let normalised_raster = GeoPNG.loadNumberRasterImage(source_path, { format: "float32" });
				let format_year = year > 2023 ? 2023 : year;
				let popc_info = wealth_income_OLS.covariates_obj["popc_"](format_year);
				let popc_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
				
				let target_map = {};
				Object.iterate(geocode_obj, (colour_key, local_geocodes) => {
					if (local_geocodes) {
						for (let c = 0; c < local_geocodes.length; c++) {
							let val = wid_targets[local_geocodes[c]]?.[year];
							if (val !== undefined && !isNaN(val)) {
								target_map[colour_key] = val;
								break;
							}
						}
					}
				});
				
				let region_stats = {};
				
				// 1. Gather Current Pop-Weighted Means
				for (let index = 0; index < normalised_raster.data.length; index++) {
					let val = normalised_raster.data[index];
					let pop = popc_raster.data[index];
					
					if (pop > 0 && val > 0) {
						let byte_index = index * 4;
						let colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index + 1]},${geocode_raster.data[byte_index + 2]}`;
						
						if (!region_stats[colour_key]) {
							region_stats[colour_key] = { total_pop: 0, weighted_sum: 0 };
						}
						
						region_stats[colour_key].total_pop += pop;
						region_stats[colour_key].weighted_sum += (val * pop);
					}
				}
				
				// 2. Compute Target Scalars
				let transform_map = {};
				Object.iterate(region_stats, (colour_key, stats) => {
					let target_per_capita = target_map[colour_key];
					if (target_per_capita !== undefined && stats.total_pop > 0) {
						let current_mean = stats.weighted_sum / stats.total_pop;
						if (current_mean > 0) {
							transform_map[colour_key] = target_per_capita / current_mean;
						}
					}
				});
				
				console.log(`Clamping ${current_variable} for year ${year} against national WID per-capita averages.`);
				
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					width: 4320,
					height: 2160,
					function: (local_index) => {
						let old_val = normalised_raster.data[local_index];
						if (old_val === 0) return 0;
						
						let byte_index = local_index * 4;
						let colour_key = `${geocode_raster.data[byte_index]},${geocode_raster.data[byte_index + 1]},${geocode_raster.data[byte_index + 2]}`;
						
						let scalar = transform_map[colour_key];
						if (scalar !== undefined) {
							let new_val = old_val * scalar;
							
							// Secondary local compression to prevent absurdly wealthy single pixels
							let target_mean = target_map[colour_key];
							let local_threshold = target_mean * 15; // Allow high variance, but compress runaways
							
							if (new_val > local_threshold) {
								let clamp_alpha = target_mean * 2;
								new_val = local_threshold + clamp_alpha * Math.log(1 + ((new_val - local_threshold) / clamp_alpha));
							}
							return new_val;
						}
						
						return old_val;
					}
				});
				
				await Blacktraffic.yield();
			}
		}
	}
	
	static async C_interpolateRasters (arg0_options = {}) {
		let options = arg0_options;
		let variables = wealth_income_WID.options.variables;
		let years = landuse_HYDE.sorted_hyde_years;
		
		let src_dir = this.intermediate_clamped_rasters;
		let interp_domain = this.options.interpolate_to_WID_domain;
		let interp_gap = interp_domain[1] - interp_domain[0];
		
		console.log(`Generating final time-series...`);
		
		for (let i = 0; i < variables.length; i++) {
			let current_variable = variables[i];
			let local_src_dir = `${src_dir}${current_variable}/`;
			let dest_dir = this.getOutputFolder(current_variable);
			
			if (!fs.existsSync(dest_dir)) fs.mkdirSync(dest_dir, { recursive: true });
			
			// Establish the brushed gravity-target for 1800 (or upper domain edge)
			let clamped_target_path = `${local_src_dir}clamped_${current_variable}_${interp_domain[1]}.png`;
			let brushed_target_path = `${local_src_dir}clamped_${current_variable}_${interp_domain[1]}_brushed.png`;
			
			// Removed !fs.existsSync check to force overwrites during final processing if required
			if (fs.existsSync(clamped_target_path)) {
				console.log(`Synthesizing Population-Masked Brush for WID Target (${interp_domain[1]}) for ${current_variable}...`);
				try {
					let wid_mask = GeoPNG.loadImage(admin_modern.input_iso2_geocodes_raster);
					let raw_target = GeoPNG.loadNumberRasterImage(clamped_target_path, { format: "float32" });
					
					let format_year = interp_domain[1] > 2023 ? 2023 : interp_domain[1];
					let popc_info = wealth_income_OLS.covariates_obj["popc_"](format_year);
					let pop_raster = GeoPNG.loadNumberRasterImage(popc_info[0], { format: popc_info[1] });
					
					let brushed_data = GeoPNG.dasymetricBlur({
						mask_data: wid_mask.data,
						pop_data: pop_raster.data,
						target_data: raw_target.data,
						height: raw_target.height,
						width: raw_target.width,
						radius: 64
					});
					
					GeoPNG.saveNumberRasterImage({
						file_path: brushed_target_path,
						format: "float32",
						width: raw_target.width,
						height: raw_target.height,
						function: (idx) => brushed_data[idx]
					});
				} catch (e) {
					console.error(`Brush synthesis failed for ${current_variable} (${interp_domain[1]}):`, e);
				}
			}
			
			for (let x = 0; x < years.length; x++) {
				let year = years[x];
				let source_path = `${this.intermediate_normalised_rasters}${current_variable}/OLS_normalised_${current_variable}_${year}.png`;
				let clamped_source = `${local_src_dir}clamped_${current_variable}_${year}.png`;
				let output_path = `${dest_dir}${current_variable}_${year}.png`;
				
				// Removed `existsSync` check entirely to allow strict overwriting during final processing
				
				try {
					let generated = false;
					if (year < interp_domain[0]) {
						// Purely structural un-clamped predictions for deep antiquity
						if (fs.existsSync(source_path)) {
							console.log(`[Copying] Deep Antiquity OLS format for ${current_variable} (${year})`);
							fs.copyFileSync(source_path, output_path);
							generated = true;
						}
					} else if (year >= interp_domain[0] && year < interp_domain[1]) {
						// Interpolate between normal OLS structure and gravity-blurred WID boundary target
						if (fs.existsSync(source_path) && fs.existsSync(brushed_target_path)) {
							let fraction = (year - interp_domain[0]) / interp_gap;
							console.log(`[Interpolating] ${year} OLS -> WID [Phase: ${fraction.toFixed(3)}]`);
							
							GeoPNG.linearInterpolation(source_path, brushed_target_path, output_path, {
								format: "float32",
								fraction: fraction,
								lower_value_threshold: 0,
								threshold_fraction: 0
							});
							generated = true;
						}
					} else {
						// Standard fully constrained WID domain
						if (fs.existsSync(clamped_source)) {
							console.log(`[Copying] Final processed clamped format for ${current_variable} (${year})`);
							fs.copyFileSync(clamped_source, output_path);
							generated = true;
						}
					}
					
					// Apply Missing Data Fallback: 
					// If the final raster has 0 for a pixel, check clamped source then check OLS source for data
					if (generated && fs.existsSync(output_path)) {
						let out_raster = GeoPNG.loadNumberRasterImage(output_path, { format: "float32" });
						let clamped_raster = fs.existsSync(clamped_source) ? GeoPNG.loadNumberRasterImage(clamped_source, { format: "float32" }) : null;
						let ols_raster = fs.existsSync(source_path) ? GeoPNG.loadNumberRasterImage(source_path, { format: "float32" }) : null;
						
						let modified = false;
						
						for (let j = 0; j < out_raster.data.length; j++) {
							if (out_raster.data[j] === 0) {
								if (clamped_raster && clamped_raster.data[j] !== 0) {
									out_raster.data[j] = clamped_raster.data[j];
									modified = true;
								} else if (ols_raster && ols_raster.data[j] !== 0) {
									out_raster.data[j] = ols_raster.data[j];
									modified = true;
								}
							}
						}
						
						// Save back if the output grid was patched
						if (modified) {
							GeoPNG.saveNumberRasterImage({
								file_path: output_path,
								format: "float32",
								width: out_raster.width,
								height: out_raster.height,
								function: (idx) => out_raster.data[idx]
							});
						}
					}
					
				} catch (e) {
					console.error(`Pass failed for ${current_variable} in year ${year}:`, e);
				}
				
				await Blacktraffic.yield();
			}
		}
		console.log(`Final Interpolation Pass Complete.`);
	}
	
	static async processRasters (arg0_options) {
		let options = (arg0_options) ? arg0_options : {};
		if (!options.exclude) options.exclude = [];
		
		// 1. Regularise the raw OLS rasters using robust Tukey statistics
		if (!options.exclude.includes("A")) await this.A_normaliseOLSRasters();
		
		// 2. Clamp rasters directly against the WID per-capita country averages
		if (!options.exclude.includes("B")) await this.B_clampOLSRasters();
		
		// 3. Spatially interpolate pre-modern rasters to dissolve political borders smoothly
		if (!options.exclude.includes("C")) await this.C_interpolateRasters({ overwrite: true });
	}
};