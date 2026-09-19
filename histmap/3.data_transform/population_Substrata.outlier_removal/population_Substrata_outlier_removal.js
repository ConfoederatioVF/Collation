global.population_Substrata_outlier_removal = class {
	static bf = `${h3}/population_Substrata.outlier_removal/`;
	static input_GHSL_rasters = `${h1}/population_GHSL/population_rasters/2.rasters/`;
	static input_outlier_rasters = `${this.bf}rasters_outliers/`;
	static input_outlier_rasters_to_scale = `${this.bf}rasters_outliers_to_scale/`;
	static intermediate_outliers_removed_rasters = `${this.bf}rasters_outliers_removed/`;
	static intermediate_rasters_northern_america = `${this.bf}rasters_1.northern_america/`;
	static intermediate_rasters_scaled_to_statista = `${this.bf}rasters_2.scaled_to_regions/`;
	static intermediate_rasters_scaled_to_global = `${this.bf}rasters_3.scaled_to_global/`;
	
	static intermediate_rasters_interpolated = `${this.bf}rasters_4.interpolated_to_GHSL/`;
	static intermediate_rasters_geopng_int32 = `${this.bf}rasters_5.geopng_int32/`;
	static options = {
		interpolate_to_GHSL_domain: [1800, 1975],
		interpolate_to_GHSL1_domain: [1800, 1950],
		interpolate_to_GHSL2_domain: [1950, 1975]
	};
	
	static statista_obj = () => JSON.parse(fs.readFileSync(`${this.bf}.config/statista_regions.json`, "utf8"));
	static statista_regions_raster = `${this.bf}/config/statista_regions.png`;
	
	static async _printPopulation () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		
		for (let i  = 0; i < hyde_years.length; i++) {
			let local_input_path = `${this.intermediate_rasters_geopng_int32}popc_${hyde_years[i]}.png`;
			let local_sum = GeoPNG.getImageSum(local_input_path, { format: "int32" });
			
			console.log(`- Year: ${hyde_years[i]}, Sum: ${local_sum}`);
			await Blacktraffic.yield();
		}
	}
	
	static async A_getHYDEOutlierMasksObject (arg0_folder) {
		//Declare local instance variables
		let input_folder = (arg0_folder) ? 
			arg0_folder : this.input_outlier_rasters;
		
		//Check if folder exists before reading
		if (!fs.existsSync(input_folder)) return {};
		
		let all_files = fs.readdirSync(input_folder);
		let return_obj = {};
		
		//Iterate over all_files and fetch time domains per file_path
		for (let i = 0; i < all_files.length; i++) {
			let local_file_path = path.join(input_folder, all_files[i]);
			
			if (!fs.statSync(local_file_path).isDirectory() && local_file_path.endsWith(".png")) {
				let split_file_name = path.basename(local_file_path).replace(".png", "").split("_");
				
				if (split_file_name.length >= 2) {
					let end_year = parseInt(split_file_name[split_file_name.length - 1]);
					let start_year = parseInt(split_file_name[split_file_name.length - 2]);
					
					return_obj[local_file_path] = {
						file_path: local_file_path,
						end_year: end_year,
						start_year: start_year
					};
				} else {
					console.error(`${local_file_path} has less than 2 arguments. It must include a _<start_year>_<end_year> formatter as a suffix.`);
				}
			}
		}
		
		//Return statement
		return return_obj;
	}
	
	static async A_removeOutliersForHYDEYear (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let fallback_file_path = `${population_KK10LUH2.output_kk10_luh2_global_rasters}popc_${year}.png`;
		let fallback_raster = GeoPNG.loadNumberRasterImage(fallback_file_path, {
			format: "float32"
		});
		let hyde_input_file_path = `${landuse_HYDE.intermediate_rasters_scaled_to_global}popc_${year}.png`;
		let hyde_output_file_path = `${this.intermediate_outliers_removed_rasters}popc_${year}.png`;
		
		let hyde_outlier_masks = await this.A_getHYDEOutlierMasksObject();
		let hyde_outlier_rasters = {};
		let hyde_pixel_outliers = new Set();
		let hyde_raster = GeoPNG.loadNumberRasterImage(hyde_input_file_path, {
			format: "float32"
		});
		
		//Iterate over all_hyde_outlier_masks; load hyde_outlier_rasters
		Object.iterate(hyde_outlier_masks, (local_key, local_value) => {
			if (year >= local_value?.start_year && year <= local_value?.end_year)
				hyde_outlier_rasters[local_key] = GeoPNG.loadImage(local_key);
		});
		
		//Operate over current image; check if number is an outlier compared to neighbouring pixels; iterate over all pixels in hyde_raster, excluding border pixels
		for (let i = 1; i < hyde_raster.height - 1; i++)
			for (let x = 1; x < hyde_raster.width - 1; x++) {
				let local_index = i*hyde_raster.width + x;
				let neighbour_average = GeoPNG.getRasterNeighbourAverage(hyde_raster.data, i, x, hyde_raster.height, hyde_raster.width);
				
				if (!isNaN(neighbour_average) && neighbour_average > 0 && hyde_raster.data[local_index] > 8*neighbour_average)
					hyde_pixel_outliers.add(local_index);
			}
		
		console.log(` - Outliers detected:`, hyde_pixel_outliers.size);
		
		//Save number raster image
		GeoPNG.saveNumberRasterImage({
			file_path: hyde_output_file_path,
			format: "float32",
			height: hyde_raster.height,
			width: hyde_raster.width,
			function: (local_index) => {
				//Declare local instance variables
				let byte_index = local_index*4;
				let is_outlier = (hyde_pixel_outliers.has(local_index));
				
				//Check if any of hyde_outlier_rasters contains [0, 0, 0] masking for this pixel
				if (!is_outlier) {
					let all_hyde_outlier_rasters = Object.keys(hyde_outlier_rasters);
					
					for (let i = 0; i < all_hyde_outlier_rasters.length; i++) {
						let local_raster = hyde_outlier_rasters[all_hyde_outlier_rasters[i]];
						let local_raster_colour = [
							local_raster.data[byte_index],
							local_raster.data[byte_index + 1],
							local_raster.data[byte_index + 2],
							local_raster.data[byte_index + 3]
						].join(",");
						
						//Break if outlier is detected
						if (local_raster_colour === "0,0,0,255") {
							is_outlier = true;
							break;
						}
					}
				}
				
				//If this pixel is an outlier, overwrite it with the equivalent content in fallback_image
				//Return statement
				if (is_outlier) {
					return fallback_raster.data[local_index];
				} else {
					return hyde_raster.data[local_index];
				}
			}
		});
	}
	
	static async A_removeOutliersForHYDE () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) try {
			console.log(`- Removing HYDE outliers for ${landuse_HYDE._getHYDEYearName(hyde_years[i])} ..`);
			await this.A_removeOutliersForHYDEYear(hyde_years[i]);
		} catch (e) { console.error(e); }
	}
	
	//[QUARANTINE]
	static async B_scaleProcessedHYDEToStatistaRegions () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let regions_mask = GeoPNG.loadImage(this.statista_regions_raster);
		let regions_map = {};
		let statista_obj = this.statista_obj();
		
		let global_min_year = Infinity;
		let global_max_year = -Infinity;
		
		// Create color-to-region mapping and determine domains
		Object.keys(statista_obj).forEach((key) => {
			let region = statista_obj[key];
			let color_key = region.colour.join(",");
			
			let all_local_years = Object.keys(region.population)
			.map(Number)
			.sort((a, b) => a - b);
			let local_mask_domain = [
				all_local_years[0],
				all_local_years[all_local_years.length - 1],
			];
			
			if (local_mask_domain[0] < global_min_year) global_min_year = local_mask_domain[0];
			if (local_mask_domain[1] > global_max_year) global_max_year = local_mask_domain[1];
			
			let years_to_interpolate = [];
			for (let x = 0; x < hyde_years.length; x++) {
				if (
					hyde_years[x] >= local_mask_domain[0] &&
					hyde_years[x] <= local_mask_domain[1] &&
					region.population[hyde_years[x]] === undefined
				) {
					years_to_interpolate.push(hyde_years[x]);
				}
			}
			
			if (years_to_interpolate.length > 0)
				region.population = Object.cubicSplineInterpolation(region.population, {
					years: years_to_interpolate,
				});
			
			regions_map[color_key] = {
				key: key,
				domain: local_mask_domain,
				...region,
			};
		});
		
		// Fetch outlier mask metadata from both directories
		let standard_outlier_masks = await this.A_getHYDEOutlierMasksObject(this.input_outlier_rasters);
		let scalable_outlier_masks = await this.A_getHYDEOutlierMasksObject(this.input_outlier_rasters_to_scale);
		
		// Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) {
			let year = hyde_years[i];
			let input_path = `${this.intermediate_rasters_northern_america}popc_${year}.png`;
			let fallback_path = `${this.intermediate_outliers_removed_rasters}popc_${year}.png`;
			let output_path = `${this.intermediate_rasters_scaled_to_statista}popc_${year}.png`;
			
			let source_path = fs.existsSync(input_path)
				? input_path
				: fs.existsSync(fallback_path)
					? fallback_path
					: null;
			
			if (source_path) {
				if (year < global_min_year || year > global_max_year) {
					fs.copyFileSync(source_path, output_path);
					continue;
				}
				
				console.log(`- Scaling Statista regions for year ${year} ..`);
				
				let current_raster = GeoPNG.loadNumberRasterImage(source_path, {
					format: "float32"
				});
				
				// Helper to filter active masks for current year
				let get_active_rasters = (mask_obj) => {
					let active = [];
					Object.values(mask_obj).forEach((m) => {
						if (year >= m.start_year && year <= m.end_year) active.push(GeoPNG.loadImage(m.file_path));
					});
					return active;
				};
				
				let active_standard_rasters = get_active_rasters(standard_outlier_masks);
				let active_scalable_rasters = get_active_rasters(scalable_outlier_masks);
				
				let regional_sums = {};
				let regional_scalars = {};
				
				// 1. Calculate current pixel sums per region
				for (let x = 0; x < current_raster.data.length; x++) {
					let val = current_raster.data[x];
					if (val > 0) {
						let byte_index = x * 4;
						
						// Check if pixel is a standard outlier
						let is_standard_outlier = active_standard_rasters.some(r =>
							r.data[byte_index] === 0 && r.data[byte_index+1] === 0 && r.data[byte_index+2] === 0 && r.data[byte_index+3] === 255
						);
						// Check if pixel is explicitly marked to be scaled
						let is_scalable_outlier = active_scalable_rasters.some(r =>
							r.data[byte_index] === 0 && r.data[byte_index+1] === 0 && r.data[byte_index+2] === 0 && r.data[byte_index+3] === 255
						);
						
						// Logic: If it is a standard outlier and NOT explicitly scalable, exclude it from the sum
						if (!is_standard_outlier || is_scalable_outlier) {
							let color_key = [
								regions_mask.data[byte_index],
								regions_mask.data[byte_index + 1],
								regions_mask.data[byte_index + 2],
							].join(",");
							
							let region_match = regions_map[color_key];
							if (region_match)
								regional_sums[region_match.key] = (regional_sums[region_match.key] || 0) + val;
						}
					}
				}
				
				// 2. Calculate scalars per region
				Object.keys(statista_obj).forEach((region_key) => {
					let mapped_region = regions_map[statista_obj[region_key].colour.join(",")];
					let current_sum = regional_sums[region_key] || 0;
					
					if (year >= mapped_region.domain[0] && year <= mapped_region.domain[1]) {
						let target_pop = (mapped_region.population[year] || 0) * mapped_region.scalar;
						regional_scalars[region_key] = current_sum > 0 ? target_pop / current_sum : 1;
					} else {
						regional_scalars[region_key] = 1;
					}
				});
				
				// 3. Apply regional scaling
				GeoPNG.saveNumberRasterImage({
					file_path: output_path,
					format: "float32",
					height: current_raster.height,
					width: current_raster.width,
					function: (index) => {
						let val = current_raster.data[index];
						if (val === 0) return 0;
						let byte_index = index * 4;
						
						let is_standard_outlier = active_standard_rasters.some(r =>
							r.data[byte_index] === 0 && r.data[byte_index+1] === 0 && r.data[byte_index+2] === 0 && r.data[byte_index+3] === 255
						);
						let is_scalable_outlier = active_scalable_rasters.some(r =>
							r.data[byte_index] === 0 && r.data[byte_index+1] === 0 && r.data[byte_index+2] === 0 && r.data[byte_index+3] === 255
						);
						
						// If it's an outlier that isn't in the "to scale" folder, return original value
						if (is_standard_outlier && !is_scalable_outlier) return val;
						
						let color_key = [
							regions_mask.data[byte_index],
							regions_mask.data[byte_index + 1],
							regions_mask.data[byte_index + 2],
						].join(",");
						
						let region_match = regions_map[color_key];
						if (region_match) {
							return val*(regional_scalars[region_match.key] || 1);
						}
						
						return val;
					},
				});
			}
		}
	}
	
	static async C_scaleProcessedHYDEToGlobal (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let world_pop_obj = population_Global.A_getWorldPopulationObject();

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: hyde_years,
			name: "population_Substrata C_scaleProcessedHYDEToGlobal",
			task_generator: (year) => {
				let local_hyde_input_path = `${this.intermediate_rasters_scaled_to_statista}popc_${year}.png`;
				let local_output_path = `${this.intermediate_rasters_scaled_to_global}popc_${year}.png`;
				let local_world_pop = world_pop_obj[year];

				if (!fs.existsSync(local_hyde_input_path)) return null;

				return {
					type: "scale_to_global",
					format: "float32",
					input_path: local_hyde_input_path,
					output_path: local_output_path,
					target_sum: local_world_pop
				};
			},
			handler: async (year) => {
				let local_hyde_input_path = `${this.intermediate_rasters_scaled_to_statista}popc_${year}.png`;
				let local_output_path = `${this.intermediate_rasters_scaled_to_global}popc_${year}.png`;
				let local_world_pop = world_pop_obj[year];

				if (fs.existsSync(local_hyde_input_path)) {
					let local_hyde_sum = GeoPNG.getImageSum(local_hyde_input_path, {
						format: "float32"
					});
					let local_scalar = local_world_pop / local_hyde_sum;

					let local_hyde_image = GeoPNG.loadNumberRasterImage(local_hyde_input_path, {
						format: "float32"
					});
					GeoPNG.saveNumberRasterImage({
						file_path: local_output_path,
						format: "float32",
						height: local_hyde_image.height,
						width: local_hyde_image.width,
						function: (local_index) => local_hyde_image.data[local_index]*local_scalar
					});
				}
			}
		});
	}
	
	static async D_interpolateToGHSL (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let GHSL_domain = this.options.interpolate_to_GHSL_domain;
		let GHSL1_domain = this.options.interpolate_to_GHSL1_domain;
		let GHSL2_domain = this.options.interpolate_to_GHSL2_domain;
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let land_area_path = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
			metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;
		let target_years = hyde_years.filter((y) => y >= GHSL_domain[0]);
		let to_path = `${this.input_GHSL_rasters}GHS_POP_${GHSL_domain[1]}.png`;
		let year_gap = GHSL_domain[1] - GHSL_domain[0];
		let year_gap2 = GHSL2_domain[1] - GHSL2_domain[0];

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "population_Substrata D_interpolateToGHSL",
			task_generator: (current_year) => {
				let fraction = (current_year - GHSL_domain[0])/year_gap;
				let local_from_path = `${this.intermediate_rasters_scaled_to_global}popc_${current_year}.png`;
				let local_ghsl_path = `${this.input_GHSL_rasters}GHS_POP_${current_year}.png`;
				let local_output_path = `${this.intermediate_rasters_interpolated}popc_${current_year}.png`;

				if (current_year < GHSL1_domain[1]) {
					return {
						type: "linear_interpolation",
						from_file_path: local_from_path,
						options: {
							buffer_distance: 5,
							format: "float32",
							fraction: fraction,
							land_area_file: land_area_path,
							upper_value_threshold: 256
						},
						output_file_path: local_output_path,
						to_file_path: to_path
					};
				} else if (current_year >= GHSL2_domain[0] && current_year < GHSL2_domain[1]) {
					let threshold_fraction = (current_year - GHSL2_domain[0])/year_gap2;
					return {
						type: "linear_interpolation",
						from_file_path: local_from_path,
						options: {
							buffer_distance: 5,
							format: "float32",
							fraction: fraction,
							land_area_file: land_area_path,
							threshold_fraction: threshold_fraction,
							upper_value_threshold: 256
						},
						output_file_path: local_output_path,
						to_file_path: to_path
					};
				} else {
					if (fs.existsSync(local_ghsl_path)) {
						return {
							type: "copy",
							from_file_path: local_ghsl_path,
							output_file_path: local_output_path
						};
					}
					return null;
				}
			},
			handler: async (current_year) => {
				let fraction = (current_year - GHSL_domain[0])/year_gap;
				let local_from_path = `${this.intermediate_rasters_scaled_to_global}popc_${current_year}.png`;
				let local_ghsl_path = `${this.input_GHSL_rasters}GHS_POP_${current_year}.png`;
				let local_output_path = `${this.intermediate_rasters_interpolated}popc_${current_year}.png`;

				if (current_year < GHSL1_domain[1]) {
					GeoPNG.linearInterpolation(local_from_path, to_path, local_output_path, {
						buffer_distance: 5,
						format: "float32",
						fraction: fraction,
						land_area_file: land_area_path,
						upper_value_threshold: 256
					});
				} else if (current_year >= GHSL2_domain[0] && current_year < GHSL2_domain[1]) {
					let threshold_fraction = (current_year - GHSL2_domain[0])/year_gap2;
					GeoPNG.linearInterpolation(local_from_path, to_path, local_output_path, {
						buffer_distance: 5,
						format: "float32",
						fraction: fraction,
						land_area_file: land_area_path,
						threshold_fraction: threshold_fraction,
						upper_value_threshold: 256
					});
				} else {
					if (fs.existsSync(local_ghsl_path)) {
						fs.copyFileSync(local_ghsl_path, local_output_path);
					}
				}
			}
		});
	}
	
	static async D_convertToGeoPNG_int32 (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;

		console.log(`Converting from float32 to int32 for older versions of SVE.`);

		//Return statement
		return await GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: hyde_years,
			name: "population_Substrata D_convertToGeoPNG_int32",
			task_generator: (year) => {
				let local_input_path = `${this.intermediate_rasters_interpolated}popc_${year}.png`;
				let local_output_path = `${this.intermediate_rasters_geopng_int32}popc_${year}.png`;
				if (!fs.existsSync(local_input_path))
					local_input_path = `${this.intermediate_rasters_scaled_to_global}popc_${year}.png`;

				let rounding_method = (year < 1600) ? "ceil" : "round";

				return {
					type: "convert_to_int32",
					input_path: local_input_path,
					output_path: local_output_path,
					rounding_method: rounding_method
				};
			},
			handler: async (year) => {
				let local_input_path = `${this.intermediate_rasters_interpolated}popc_${year}.png`;
				let local_output_path = `${this.intermediate_rasters_geopng_int32}popc_${year}.png`;
				if (!fs.existsSync(local_input_path))
					local_input_path = `${this.intermediate_rasters_scaled_to_global}popc_${year}.png`;

				let current_raster = GeoPNG.loadNumberRasterImage(local_input_path, {
					format: "float32"
				});
				let rounding_method = (year < 1600) ? "ceil" : "round";

				GeoPNG.saveNumberRasterImage({
					file_path: local_output_path,
					format: "int32",
					height: 2160,
					width: 4320,
					function: (local_index) => Math[rounding_method](current_raster.data[local_index])
				});
			}
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//1. Remove outliers for HYDE
		if (!options.exclude.includes("A")) await this.A_removeOutliersForHYDE();
		//2. Handle continental regions, i.e. Northern America; Statista regions
		if (!options.exclude.includes("B1")) await population_Substrata_northern_america.processRasters();
		if (!options.exclude.includes("B2")) await this.B_scaleProcessedHYDEToStatistaRegions();
		//3. Scale processed outliers to global population
		if (!options.exclude.includes("C")) await this.C_scaleProcessedHYDEToGlobal(options);
		//4. Conversion to int32 for backwards compatibility
		if (!options.exclude.includes("D")) {
			await this.D_interpolateToGHSL(options);
			await this.D_convertToGeoPNG_int32(options);
		}
	}
};