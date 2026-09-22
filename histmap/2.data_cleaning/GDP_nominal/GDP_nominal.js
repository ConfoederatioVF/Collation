global.GDP_nominal = class {
	static input_gdp_national_csv = `${h1}/GDP_nominal/gdp_national_eoscala_1.4.csv`;
	static input_gdp_world_json = `${h1}/GDP_nominal/gdp_world_eoscala_1.4.json5`;
	static intermediate_normalised_to_global = `${h3}GDP_nominal/1.scaled_to_global/`;
	static intermediate_scaled_to_national = `${h3}GDP_nominal/2.scaled_to_national/`;
	
	/**
	 * Fetches a {"<year>": {@link number}} map per geocode for GDP nominal.
	 *
	 * @returns {Object}
	 */
	static getGDPObject () {
		//Declare local instance variables
		let gdp_csv = File.loadCSVAsJSON(this.input_gdp_national_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let gdp_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
		//Destructure gdp_csv into gdp_obj
		Object.iterate(gdp_csv, (local_key, local_value) => {
			//Iterate over all geocodes in a given year
			Object.iterate(local_value, (local_geocode, local_string) => {
				if (local_string[0] !== "") {
					if (!gdp_obj[local_geocode]) gdp_obj[local_geocode] = {};
					let local_gdp = parseFloat(local_string[0]);
					
					if (!isNaN(local_gdp))
						gdp_obj[local_geocode][local_key] = local_gdp;
				}
			})
		});
		
		//Iterate over all hyde_years, and if it doesn't exist, cubic spline interpolate
		Object.iterate(gdp_obj, (local_key, local_value) => {
			gdp_obj[local_key] = Object.cubicSplineInterpolation(local_value, { 
				years: hyde_years 
			});
		});
		
		//Return statement
		return gdp_obj;
	}
	
	/**
	 * Returns estimations of World GDP PPP as an object map.
	 *
	 * @returns {Object}
	 */
	static getWorldGDPObject () {
		//Declare local instance variables
		let gdp_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let raw_gdp_obj = JSON5.parse(fs.readFileSync(this.input_gdp_world_json));
		
		//Iterate over raw_gdp_obj; populate raw figures
		Object.iterate(raw_gdp_obj, (local_key, local_value) => {
			if (local_value?.gdp)
				Object.iterate(local_value.gdp, (local_subkey, local_subvalue) => {
					let local_scalar = Math.returnSafeNumber(local_value?.scalar, 1);
					let local_gdp = local_subvalue*local_scalar;
					
					if (!gdp_obj[local_subkey]) {
						gdp_obj[local_subkey] = [local_gdp];
					} else {
						gdp_obj[local_subkey].push(local_gdp);
					}
				});
		});
		Object.iterate(gdp_obj, (local_key, local_value) => 
			gdp_obj[local_key] = Math.weightedGeometricMean(local_value));
		
		//Return statement
		return Object.cubicSplineInterpolation(gdp_obj, { years: hyde_years });
	}
	
	static async A_scaleGDPRastersToGlobal (arg0_input_folder, arg1_output_folder, arg2_options) {
		//Convert from parameters
		let input_folder = arg0_input_folder;
		let output_folder = arg1_output_folder;
		let options = (arg2_options) ? arg2_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(output_folder) : output_folder;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		let world_gdp_obj = this.getWorldGDPObject();
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${input_folder}GDP_${hyde_years[i]}.png`;
			let local_output_path = `${output_folder}GDP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_nominal Scale to Global",
			task_generator: (year) => ({
				format: "float32",
				input_path: `${input_folder}GDP_${year}.png`,
				output_path: `${output_folder}GDP_${year}.png`,
				target: world_gdp_obj[year],
				type: "scale_to_global"
			}),
			handler: async (year) => {
				let local_input_path = `${input_folder}GDP_${year}.png`;
				let local_output_path = `${output_folder}GDP_${year}.png`;
				let local_target = world_gdp_obj[year];
				
				let local_input_png = GeoPNG.loadNumberRasterImage(local_input_path, { format: "float32" });
				let local_input_sum = GeoPNG.getImageSum(local_input_path, { format: "float32" });
				let local_scalar = (local_input_sum > 0) ? local_target/local_input_sum : 1;
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_path,
					format: "float32",
					width: 4320,
					height: 2160,
					function: (local_index) => local_input_png.data[local_index]*local_scalar
				});
			}
		});
	}
	
	static async B_scaleGDPRastersToNational (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocodes_raster_path = admin_modern.input_geocodes_raster;
		let gdp_obj = this.getGDPObject();
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_scaled_to_national) : this.intermediate_scaled_to_national;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${this.intermediate_normalised_to_global}GDP_${hyde_years[i]}.png`;
			let local_output_path = `${this.intermediate_scaled_to_national}GDP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_nominal Scale to National",
			task_generator: (year) => {
				let target_gdp_map = {};
				let all_codes = Object.keys(gdp_obj);
				for (let x = 0; x < all_codes.length; x++) {
					let code = all_codes[x];
					let val = gdp_obj[code]?.[year];
					if (val !== undefined) target_gdp_map[code] = val;
				}
				
				return {
					format: "float32",
					geocode_map: geocode_obj,
					geocodes_raster_path: geocodes_raster_path,
					input_path: `${this.intermediate_normalised_to_global}GDP_${year}.png`,
					output_path: `${this.intermediate_scaled_to_national}GDP_${year}.png`,
					target_gdp_map: target_gdp_map,
					type: "scale_to_national"
				};
			},
			handler: async (year) => {
				let geocode_raster = GeoPNG.loadImage(geocodes_raster_path);
				let local_ols_file_path = `${this.intermediate_normalised_to_global}GDP_${year}.png`;
				let local_output_file = `${this.intermediate_scaled_to_national}GDP_${year}.png`;
				let local_gdp_scalars = {};
				let local_gdp_sums = {};
				let local_ols_raster = GeoPNG.loadNumberRasterImage(local_ols_file_path, { format: "float32" });
				
				GeoPNG.operateNumberRasterImage({
					file_path: local_ols_file_path,
					format: "float32",
					function: (local_index, local_value) => {
						let local_colour_key = [
							geocode_raster.data[local_index],
							geocode_raster.data[local_index + 1],
							geocode_raster.data[local_index + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						
						if (local_geocodes)
							for (let x = 0; x < local_geocodes.length; x++)
								Object.modifyValue(local_gdp_sums, local_geocodes[x], local_value);
					}
				});
				
				Object.iterate(local_gdp_sums, (local_key, local_value) => {
					let local_actual_gdp = gdp_obj[local_key]?.[year];
					local_gdp_scalars[local_key] = (local_actual_gdp && local_value > 0) ? local_actual_gdp/local_value : 1;
				});
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_file,
					format: "float32",
					height: 2160,
					width: 4320,
					function: (local_index) => {
						let byte_index = local_index*4;
						let local_colour_key = [
							geocode_raster.data[byte_index], 
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						let local_value = local_ols_raster.data[local_index];
						
						if (local_geocodes)
							for (let x = 0; x < local_geocodes.length; x++) {
								let local_gdp = gdp_obj[local_geocodes[x]]?.[year];
								let local_scalar = local_gdp_scalars[local_geocodes[x]];
								if (local_gdp && isFinite(local_scalar))
									return local_value*local_scalar;
							}
						return local_value;
					}
				});
			}
		});
	}
	
	static async processRasters (arg0_options) {
		// Deprecated: GDP nominal is now dynamically derived from GDP_pc (inverted logic pipeline).
		return;
	}
};