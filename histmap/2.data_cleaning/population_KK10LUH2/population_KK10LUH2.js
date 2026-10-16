global.population_KK10LUH2 = class {
	static kk10_domain = [-6051, 1850];
	static luh2_domain = [900, 2018];
	static luh2_variables = ["c3ann", "c3nfx", "c3per", "c4ann", "c4per", "pasture", "urban"];
	
	static _cache_nelson_data_obj;
	static input_kk10luh2_domain = [-6000, 2018];
	static input_luh2_folder = `${h1}/population_KK10LUH2/LUH2/`;
	static input_kk10_folder = `${h1}/population_KK10LUH2/KK10/`;
	static input_nelson_json = `${h2}/population_KK10LUH2/config/nelson_data.json5`;
	static input_nelson_raster = `${h2}/population_KK10LUH2/config/nelson_regions.png`;
	static input_owid_csv = `${h2}/population_KK10LUH2/config/owid_data.csv`;
	static input_owid_domain = [1800, 2023];
	static input_owid_json = `${h2}/population_KK10LUH2/config/owid_colourmap.json5`;
	static input_owid_raster = `${h2}/population_KK10LUH2/config/owid_continents.png`;
	static intermediate_luh2_rasters = `${h2}/population_KK10LUH2/rasters_LUH2_anthropogenic_mean/`;
	static intermediate_kk10_luh2_greyscale_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2_greyscale/`;
	static intermediate_kk10_luh2_alcc_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2_alcc_km2/`;
	static intermediate_kk10_luh2_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2/`;
	static intermediate_kk10_luh2_regional_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2_1._regional_scaling/`;
	static output_kk10_luh2_global_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2_2._global_scaling/`;
	
	static async A_getNelsonDataObject () {
		//Internal guard clause if _cache_nslon_data_obj is already defined
		if (this._cache_nelson_data_obj) return this._cache_nelson_data_obj;
		
		//Declare local instance variables
		let nelson_data_obj = JSON5.parse(fs.readFileSync(this.input_nelson_json, "utf8"));
		this._cache_nelson_data_obj = nelson_data_obj;
		
		//Return statement
		return nelson_data_obj;
	}
	
	static async A_averageLUH2Rasters () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		
		//Iterate over all hyde_years in this.luh2_domain
		for (let i = this.luh2_domain[0]; i <= this.luh2_domain[1]; i++)
			if (hyde_years.includes(i)) try {
				let luh2_images = {};
				let luh2_stocks = this.luh2_variables;
				
				for (let x = 0; x < luh2_stocks.length; x++) try {
					let local_input_path = `${this.input_luh2_folder}${luh2_stocks[x]}/LUH2_${luh2_stocks[x]}_${i}.png`;
					
					luh2_images[luh2_stocks[x]] = GeoPNG.loadNumberRasterImage(local_input_path, { 
						format: "float32" 
					});
				} catch (e) { console.error(e); }
				
				console.log(`- Summing LUH2 land use rasters for ${i} ..`);
				GeoPNG.saveNumberRasterImage({
					file_path: `${this.intermediate_luh2_rasters}LUH2_${i}.png`,
					format: "float32",
					
					height: luh2_images[luh2_stocks[0]].height,
					width: luh2_images[luh2_stocks[0]].width,
					function: function (arg0_index) {
						//Convert from parameters
						let index = arg0_index;
						
						//Declare local instance variables
						let local_sum = 0;
						
						//Sum all disjoint luh2 land use categories
						for (let x = 0; x < luh2_stocks.length; x++) {
							let local_value = luh2_images[luh2_stocks[x]].data[index];
							
							local_sum += local_value;
						}
						
						//Return statement
						return Math.min(1, Math.max(0, local_sum));
					}
				});
			} catch (e) { console.error(e); }
	}
	
	static async B_generateKK10LUH2Rasters () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) try {
			let in_luh2_domain = (hyde_years[i] >= this.luh2_domain[0] && hyde_years[i] <= this.luh2_domain[1]);
			let in_kk10_domain = (hyde_years[i] >= this.kk10_domain[0] && hyde_years[i] <= this.kk10_domain[1]);
			let output_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${hyde_years[i]}.png`;
			
			if (in_luh2_domain || in_kk10_domain) {
				//1. If this is an intersection of both the luh2_domain and kk10_domain; average rasters
				let luh2_file_path = `${this.intermediate_luh2_rasters}LUH2_${hyde_years[i]}.png`;
				let kk10_file_path = `${this.input_kk10_folder}KK10_${hyde_years[i]}.png`;
				
				if (in_luh2_domain && in_kk10_domain) {
					let luh2_image = GeoPNG.loadNumberRasterImage(luh2_file_path, { 
						format: "float32" 
					});
					let kk10_image = GeoPNG.loadNumberRasterImage(kk10_file_path, { 
						format: "float32" 
					});
					
					console.log(`- Averaging KK10 and LUH2 for ${hyde_years[i]} ..`);
					GeoPNG.saveNumberRasterImage({
						file_path: output_file_path,
						format: "float32",
						
						height: luh2_image.height,
						width: luh2_image.width,
						function: function (arg0_index) {
							//Convert from parameters
							let index = arg0_index;
							
							//Return statement
							return (kk10_image.data[index] + luh2_image.data[index])/2;
						}
					});
					
					console.log(`- File written to ${output_file_path}.`);
					continue;
				}
				
				//2. If this is of only the kk10_domain; merely copy the kk10 raster to its destination
				if (in_kk10_domain && !in_luh2_domain)
					fs.copyFileSync(kk10_file_path, output_file_path);
				
				//3. If this is of only the luh2_domain; merely copy the luh2 raster to its destination
				if (in_luh2_domain && !in_kk10_domain)
					fs.copyFileSync(luh2_file_path, output_file_path);
			}
		} catch (e) { console.error(e); }
	}
	
	static async B2_generateALCCAreaRasters () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let land_area_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, {
			format: "int32"
		});
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) try {
			let input_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${hyde_years[i]}.png`;
			let output_file_path = `${this.intermediate_kk10_luh2_alcc_rasters}KK10LUH2_${hyde_years[i]}.png`;
			
			//Fallback handling for years outside KK10LUH2 domain
			if (!fs.existsSync(input_file_path)) {
				let fallback_year = (hyde_years[i] < this.input_kk10luh2_domain[0]) ?
					this.input_kk10luh2_domain[0] : this.input_kk10luh2_domain[1];
				input_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${fallback_year}.png`;
			}
			
			if (fs.existsSync(input_file_path)) {
				let fraction_raster = GeoPNG.loadNumberRasterImage(input_file_path, {
					format: "float32"
				});
				
				console.log(`- Computing ALCC km^2/cell for ${hyde_years[i]} ..`);
				GeoPNG.saveNumberRasterImage({
					file_path: output_file_path,
					format: "float32",
					height: fraction_raster.height,
					width: fraction_raster.width,
					function: function (arg0_index) {
						//Convert from parameters
						let index = arg0_index;
						let cell_area = land_area_raster.data[index];
						let fraction_val = fraction_raster.data[index];
						
						//Return statement
						if (cell_area <= 0 || fraction_val <= 0) return 0;
						return fraction_val*cell_area;
					}
				});
			}
		} catch (e) { console.error(e); }
	}
	
	static async C_convertKK10LUH2RastersToRGBA (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.fallback_mode) options.fallback_mode = "kk10luh2_domain";
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let world_pop_obj = population_Global.A_getWorldPopulationObject();
		
		//Iterate over all hyde_years and check if the corresponding raster file exists
		for (let i = 0; i < hyde_years.length; i++) {
			let input_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${hyde_years[i]}.png`;
			let output_file_path = `${this.intermediate_kk10_luh2_rasters}KK10LUH2_${hyde_years[i]}.png`;
			
			//Fallback handling
			if (!fs.existsSync(input_file_path)) 
				if (options.fallback_mode === "kk10luh2_domain") {
					let fallback_year = (hyde_years[i] < this.input_kk10luh2_domain[0]) ?
						this.input_kk10luh2_domain[0] : this.input_kk10luh2_domain[1];
					input_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${fallback_year}.png`;
				} else {
					//Simply copy over the original HYDE raster otherwise
					let hyde_file_path = `${landuse_HYDE.intermediate_rasters_scaled_to_global}popc_${hyde_years[i]}.png`;
					
					console.log(`- Copying HYDE-McEvedy for GeoPNG for ${hyde_years[i]} ..`);
					fs.copyFileSync(hyde_file_path, output_file_path);
					continue;
				}
			
			//Regular non-fallback handling
			if (fs.existsSync(input_file_path)) {
				let local_raster = GeoPNG.loadNumberRasterImage(input_file_path, { format: "float32" });
				let raster_sum = GeoPNG.getImageSum(input_file_path, { format: "float32" });
				let local_world_pop = world_pop_obj[hyde_years[i]];
				let population_per_pixel = (raster_sum > 0) ? local_world_pop/raster_sum : 0;
				
				console.log(`- Calibrating KK10LUH2 float32 GeoPNG for ${hyde_years[i]} ..`);
				GeoPNG.saveNumberRasterImage({
					file_path: output_file_path,
					format: "float32",
					height: local_raster.height,
					width: local_raster.width,
					function: function (arg0_index) {
						//Return statement
						return local_raster.data[arg0_index]*population_per_pixel;
					}
				});
			}
		}
	}
	
	static async D_scaleKK10LUH2RastersToHYDE () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let nelson_obj = structuredClone(await this.A_getNelsonDataObject());
		let nelson_png = GeoPNG.loadImage(this.input_nelson_raster);
		
		//Iterate over all hyde_years and fetch the sum per Nelson region
		for (let i = 0; i < hyde_years.length; i++) {
			let local_regions_obj = {};
			
			Object.iterate(nelson_obj.regions, (local_key, local_value) => {
				if (local_value?.colour)
					local_regions_obj[local_value.colour.join(",")] = {
						name: local_key,
						HYDE_population: 0,
						KK10LUH2_population: 0,
						scalar: 1
					};
			});
			
			//Fetch .HYDE_population for all regions
			GeoPNG.operateNumberRasterImage({
				file_path: `${landuse_HYDE.intermediate_rasters_scaled_to_global}popc_${hyde_years[i]}.png`,
				format: "float32",
				function: (local_index, local_value) => {
					let local_key = [
						nelson_png.data[local_index],
						nelson_png.data[local_index + 1],
						nelson_png.data[local_index + 2]
					].join(",");
					let local_region = local_regions_obj[local_key];
					
					if (local_region)
						local_region.HYDE_population += local_value;
				}
			});
			
			//Fetch .KK10LUH2_population for all regions
			GeoPNG.operateNumberRasterImage({
				file_path: `${this.intermediate_kk10_luh2_rasters}KK10LUH2_${hyde_years[i]}.png`,
				format: "float32",
				function: (local_index, local_value) => {
					let local_key = [
						nelson_png.data[local_index],
						nelson_png.data[local_index + 1],
						nelson_png.data[local_index + 2]
					].join(",");
					let local_region = local_regions_obj[local_key];
					
					if (local_region)
						local_region.KK10LUH2_population += local_value;
				}
			});
			
			//Calculate scalars
			Object.iterate(local_regions_obj, (local_key, local_value) => {
				local_value.scalar = Math.returnSafeNumber(local_value.HYDE_population/local_value.KK10LUH2_population, 1);
			});
			
			//Apply scalar to resulting raster
			let local_input_png = GeoPNG.loadNumberRasterImage(`${this.intermediate_kk10_luh2_rasters}KK10LUH2_${hyde_years[i]}.png`, {
				format: "float32"
			});
			
			GeoPNG.saveNumberRasterImage({
				file_path: `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`,
				format: "float32",
				width: 4320,
				height: 2160,
				function: (local_index) => {
					let local_key = [
						nelson_png.data[local_index*4],
						nelson_png.data[local_index*4 + 1],
						nelson_png.data[local_index*4 + 2]
					].join(",");
					let local_region = local_regions_obj[local_key];
					let local_value = local_input_png.data[local_index];
					
					//Return statement
					if (local_region?.scalar !== undefined)
						return local_value*local_region.scalar;
					return local_value;
				}
			});
			
			console.log(`- Finished scaling KK10LUH2 ${hyde_years[i]} to regional HYDE aggregates ..`)
		}
	}
	
	static async E_getOWIDDataObject () {
		//Declare local instance variables
		let owid_colours_obj = {};
		let owid_colourmap = JSON5.parse(fs.readFileSync(this.input_owid_json, "utf8"));
		let owid_obj = File.loadCSVAsJSON(this.input_owid_csv, { mode: "vertical" });
		
		//Iterate over all regions
		Object.iterate(owid_obj, (local_key, local_value) => {
			//Delete .Code, map years and population to numbers
			delete local_value["Code"];
			local_value["Year"] = local_value["Year"].map(Number);
			local_value["Population (historical)"] = local_value["Population (historical)"].map(Number);
			
			//Set local_region.key
			local_value.key = local_key;
			
			if (owid_colourmap[local_key])
				local_value.colour = owid_colourmap[local_key].colour;
			if (local_value.colour)
				owid_colours_obj[local_value.colour.join(",")] = local_value;
		});
		
		//Process .Year, .Population arrays into objects
		Object.iterate(owid_obj, (local_key, local_value) => {
			//Set .population object
			let local_population = {};
			
			//Iterate over all .Year elements
			console.log(local_key, local_value)
			if (local_value?.Year)
				for (let x = 0; x < local_value.Year.length; x++)
					local_population[local_value.Year[x]] = Math.returnSafeNumber(local_value["Population (historical)"][x]);
			
			//Delete un-necessary fields
			local_value.population = local_population;
			
			delete local_value["Population (historical)"];
			delete local_value.Year;
		});
		
		//Return statement
		return {
			...owid_obj,
			...owid_colours_obj
		};
	}
	
	static async E_scaleKK10LUH2RastersToOWID () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let owid_obj = structuredClone(await this.E_getOWIDDataObject());
		let owid_png = GeoPNG.loadImage(this.input_owid_raster);
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) {
			//Check for valid domain
			if (!(hyde_years[i] >= this.input_owid_domain[0] && hyde_years[i] <= this.input_owid_domain[1])) continue;
			
			//Adjust raster image to OWID/HYDE
			let local_input_file_path = `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`;
			let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path, {
				format: "float32"
			});
			
			console.log(`- Standardising to OWID for ${hyde_years[i]} ..`);
			if (fs.existsSync(local_input_file_path)) {
				let local_owid_obj = {};
				let local_owid_scalars = {};
				
				//Populate local_owid_obj
				GeoPNG.operateNumberRasterImage({
					file_path: `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`,
					format: "float32",
					function: (local_index, local_value) => {
						let local_colour_key = [
							owid_png.data[local_index],
							owid_png.data[local_index + 1],
							owid_png.data[local_index + 2]
						].join(",");
						let local_region = owid_obj[local_colour_key];
						
						if (local_region)
							Object.modifyValue(local_owid_obj, local_colour_key, local_value);
					}
				});
				
				//Iterate over all_owid_regions, populate local_owid_scalars
				Object.iterate(owid_obj, (local_key, local_value) => {
					let local_actual_population = Math.returnSafeNumber(local_value.population[hyde_years[i]], 1);
					let local_current_population = local_owid_obj[local_key];
					
					local_owid_scalars[local_value.colour.join(",")] = Math.returnSafeNumber(local_actual_population/local_current_population, 1);
				});
				console.log(` - Local OWID object:`, local_owid_obj);
				console.log(` - Local OWID scalars:`, local_owid_scalars);
				
				GeoPNG.saveNumberRasterImage({
					file_path: `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`,
					format: "float32",
					height: 2160,
					width: 4320,
					function: (local_index) => {
						let byte_index = local_index*4;
						let local_colour_key = [
							owid_png.data[byte_index],
							owid_png.data[byte_index + 1],
							owid_png.data[byte_index + 2]
						].join(",");
						let local_region = owid_obj[local_colour_key];
						let local_value = local_input_raster.data[local_index];
						
						//Adjust to OWID if possible
						if (local_region) {
							local_value *= local_owid_scalars[local_colour_key];
						} else {
							local_value = 0;
						}
						
						//Return statement
						return local_value;
					}
				});
				
				//Force a yield, perform GC
				await new Promise(resolve => setImmediate(resolve));
				if (global.gc) global.gc();
			} else {
				console.log(` - Could not find input raster.`)
			}
		}
	}
	
	//[QUARANTINE] - Duplicated code
	static async F_scaleKK10LUH2RastersToStatista () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let regions_mask = GeoPNG.loadImage(
			population_Substrata_outlier_removal.statista_regions_raster,
		);
		let regions_map = {};
		let statista_raw = population_Substrata_outlier_removal.statista_obj;
		let statista_obj = structuredClone(
			(typeof statista_raw === "function") ? statista_raw() : statista_raw
		);
		
		let global_min_year = Infinity;
		let global_max_year = -Infinity;
		
		//1. Prepare mapping and interpolate missing years in the Statista dataset
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
			
			if (local_mask_domain[0] < global_min_year)
				global_min_year = local_mask_domain[0];
			if (local_mask_domain[1] > global_max_year)
				global_max_year = local_mask_domain[1];
			
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
		
		//2. Iterate over all hyde_years to apply scaling
		for (let i = 0; i < hyde_years.length; i++) {
			let year = hyde_years[i];
			let file_path = `${this.intermediate_kk10_luh2_regional_rasters}popc_${year}.png`;
			
			if (fs.existsSync(file_path)) {
				//Skip if year is entirely outside the Statista domain
				if (year < global_min_year || year > global_max_year) continue;
				
				console.log(`- Scaling KK10LUH2 to Statista regions for year ${year} ..`);
				let current_raster = GeoPNG.loadNumberRasterImage(file_path, { 
					format: "float32" 
				});
				let regional_sums = {};
				let regional_scalars = {};
				
				//Calculate current pixel sums per Statista region
				for (let x = 0; x < current_raster.data.length; x++) {
					let val = current_raster.data[x];
					if (val > 0) {
						let byte_index = x * 4;
						let color_key = [
							regions_mask.data[byte_index],
							regions_mask.data[byte_index + 1],
							regions_mask.data[byte_index + 2],
						].join(",");
						
						let region_match = regions_map[color_key];
						if (region_match)
							regional_sums[region_match.key] =
								(regional_sums[region_match.key] || 0) + val;
					}
				}
				
				//Calculate scalars per region based on interpolated Statista targets
				Object.keys(statista_obj).forEach((region_key) => {
					let region_data = statista_obj[region_key];
					let color_key = region_data.colour.join(",");
					let mapped_region = regions_map[color_key];
					let current_sum = regional_sums[region_key] || 0;
					
					if (year >= mapped_region.domain[0] && year <= mapped_region.domain[1]) {
						let target_pop =
							(mapped_region.population[year] || 0) * mapped_region.scalar;
						regional_scalars[region_key] =
							current_sum > 0 ? target_pop / current_sum : 1;
					} else {
						regional_scalars[region_key] = 1;
					}
				});
				
				//Apply regional scaling and overwrite the regional raster
				GeoPNG.saveNumberRasterImage({
					file_path: file_path,
					format: "float32",
					height: current_raster.height,
					width: current_raster.width,
					function: (index) => {
						let val = current_raster.data[index];
						if (val === 0) return 0;
						
						let byte_index = index * 4;
						let color_key = [
							regions_mask.data[byte_index],
							regions_mask.data[byte_index + 1],
							regions_mask.data[byte_index + 2],
						].join(",");
						
						let region_match = regions_map[color_key];
						if (region_match)
							return val*regional_scalars[region_match.key];
						
						return val;
					},
				});
				
				//Force a yield, perform GC
				await new Promise(resolve => setImmediate(resolve));
				if (global.gc) global.gc();
			}
		}
	}
	
	static async G_scaleKK10LUH2RastersToGlobal () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.hyde_years;
		let world_pop_obj = population_Global.A_getWorldPopulationObject();
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_file_path = `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`;
			let local_scalar = 1;
			
			if (fs.existsSync(local_input_file_path))
				await new Promise((resolve, reject) => {
					setImmediate(() => {
						try {
							let local_input_png = GeoPNG.loadNumberRasterImage(local_input_file_path, {
								format: "float32"
							});
							let local_input_sum = GeoPNG.getImageSum(local_input_file_path, {
								format: "float32"
							});
							local_scalar = world_pop_obj[hyde_years[i]]/local_input_sum;
							
							GeoPNG.saveNumberRasterImage({
								file_path: `${this.output_kk10_luh2_global_rasters}/popc_${hyde_years[i]}.png`,
								format: "float32",
								width: 4320,
								height: 2160,
								function: (local_index) => local_input_png.data[local_index]*local_scalar
							});
							
							console.log(`- ${hyde_years[i]} - Input Population: ${local_input_sum}, Scalar: ${local_scalar}`);
							resolve();
						} catch (err) {
							reject(err);
						}
					});
				});
		}
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		if (!options.exclude) options.exclude = [];
		
		//0. Extract raw NetCDF files to 5-arcmin float32 GeoPNGs if requested
		if (options.extract_raw || options.reextract) {
			let extractor_script = path.join(this.input_kk10_folder, "..", "extract_kk10luh2.py");
			if (fs.existsSync(extractor_script)) {
				console.log(`[population_KK10LUH2] Extracting KK10 & LUH2 from NetCDF to float32 GeoPNGs ...`);
				await Blacktraffic.Python_run(extractor_script);
			}
		}
		
		//1. Sum land use fractions from LUH2 climate model in float32
		if (!options.exclude.includes("A")) await this.A_averageLUH2Rasters();
		//2. Combine KK10 and LUH2 rasters in float32
		if (!options.exclude.includes("B")) await this.B_generateKK10LUH2Rasters();
		//2b. Generate ALCC physical area rasters (km^2/cell) for Dataview
		if (!options.exclude.includes("B2")) await this.B2_generateALCCAreaRasters();
		//3. Calibrate KK10LUH2 rasters to world population totals in float32
		if (!options.exclude.includes("C")) await this.C_convertKK10LUH2RastersToRGBA({
			fallback_mode: "kk10luh2_domain"
		});
		//4. Scale KK10LUH2 to regional totals from HYDE
		if (!options.exclude.includes("D")) await this.D_scaleKK10LUH2RastersToHYDE();
		//5. Scale KK10LUH2 to regional totals from OWID; Statista
		if (!options.exclude.includes("E")) await this.E_scaleKK10LUH2RastersToOWID();
		if (!options.exclude.includes("F")) await this.F_scaleKK10LUH2RastersToStatista();
		
		//6. Scale KK10LUH2 to global totals
		if (!options.exclude.includes("G")) await this.G_scaleKK10LUH2RastersToGlobal();
	}
};