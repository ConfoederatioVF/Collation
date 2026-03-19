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
	static input_owid_json = `${h2}/population_KK10LUH2/config/owid_colourmap.json5`;
	static input_owid_raster = `${h2}/population_KK10LUH2/config/owid_continents.png`;
	static intermediate_luh2_rasters = `${h2}/population_KK10LUH2/rasters_LUH2_anthropogenic_mean/`;
	static intermediate_kk10_luh2_greyscale_rasters = `${h2}/population_KK10LUH2/rasters_KK10LUH2_greyscale/`;
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
					let local_input_path = `${this.input_luh2_folder}${luh2_stocks[x]}/output_folder/LUH2_${luh2_stocks[x]}_${i}.png`;
					
					luh2_images[luh2_stocks[x]] = GeoPNG.loadNumberRasterImage(local_input_path, { type: "greyscale" });
				} catch (e) { console.error(e); }
				
				console.log(`- Averaging LUH2 raster for ${i} ..`);
				GeoPNG.saveNumberRasterImage({
					file_path: `${this.intermediate_luh2_rasters}LUH2_${i}.png`,
					type: "greyscale",
					
					height: luh2_images[luh2_stocks[0]].height,
					width: luh2_images[luh2_stocks[1]].width,
					function: function (arg0_index) {
						//Convert from parameters
						let index = arg0_index;
						
						//Declare local instance variables
						let local_sum = 0;
						
						//Average all luh2_images
						for (let x = 0; x < luh2_stocks.length; x++) {
							let local_value = luh2_images[luh2_stocks[x]].data[index];
							
							local_sum += local_value;
						}
						
						//Return statement
						return local_sum/luh2_stocks.length;
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
					let luh2_image = GeoPNG.loadNumberRasterImage(luh2_file_path, { type: "greyscale" });
					let kk10_image = GeoPNG.loadNumberRasterImage(kk10_file_path, { type: "greyscale" });
					
					console.log(`- Averaging KK10 and LUH2 for ${hyde_years[i]} ..`);
					GeoPNG.saveNumberRasterImage({
						file_path: output_file_path,
						type: "greyscale",
						
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
					input_file_path = `${this.intermediate_kk10_luh2_greyscale_rasters}KK10LUH2_${this.input_kk10luh2_domain[0]}.png`;
				} else {
					//Simply copy over the original HYDE raster otherwise
					let hyde_file_path = `${landuse_HYDE.intermediate_rasters_scaled_to_global}popc_${hyde_years[i]}.png`;
					
					console.log(`- Copying HYDE-McEvedy for GeoPNG for ${hyde_years[i]} ..`);
					fs.copyFileSync(hyde_file_path, output_file_path);
					continue;
				}
			
			//Regular non-fallback handling
			if (fs.existsSync(input_file_path)) {
				let greyscale_image = GeoPNG.loadImage(input_file_path);
				let greyscale_sum = 0;
				let local_world_pop = world_pop_obj[hyde_years[i]];
				
				//Iterate over all pixels in greyscale_image
				for (let x = 0; x < greyscale_image.width; x++)
					for (let y = 0; y < greyscale_image.height; y++) {
						let local_index = (greyscale_image.width*y + x) << 2; //4 bytes per pixel (RGBA)
						let r = greyscale_image.data[local_index];
						
						greyscale_sum += r/255;
					}
				
				let population_per_pixel = local_world_pop/greyscale_sum;
				
				//Save number raster image
				console.log(`- Converting KK10_LUH2 from greyscale to GeoPNG for ${hyde_years[i]} ..`);
				GeoPNG.saveNumberRasterImage({
					file_path: output_file_path,
					height: greyscale_image.height,
					width: greyscale_image.width,
					
					function: function (arg0_index) {
						//Convert from parameters
						let local_index = arg0_index*4; //Index must be multiplied by 4 since we are using loadImage(), and not loadNumberRasterImage()
						
						//Return statement
						return (greyscale_image.data[local_index]/255)*population_per_pixel;
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
				file_path: `${landuse_HYDE.intermediate_rasters_scaled_to_global}/popc_${hyde_years[i]}.png`,
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
			let local_input_png = GeoPNG.loadNumberRasterImage(`${this.intermediate_kk10_luh2_rasters}KK10LUH2_${hyde_years[i]}.png`);
			GeoPNG.saveNumberRasterImage({
				file_path: `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`,
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
						return Math.ceil(local_value*local_region.scalar);
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
			//Adjust raster image to OWID/HYDE
			let local_input_file_path = `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`;
			let local_input_raster = GeoPNG.loadNumberRasterImage(local_input_file_path);
			
			console.log(`- Standardising to OWID for ${hyde_years[i]} ..`);
			if (fs.existsSync(local_input_file_path)) {
				let local_owid_obj = {};
				let local_owid_scalars = {};
				
				//Populate local_owid_obj
				GeoPNG.operateNumberRasterImage({
					file_path: `${this.intermediate_kk10_luh2_regional_rasters}popc_${hyde_years[i]}.png`,
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
	
	static async F_scaleKK10LUH2RastersToGlobal () {
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
							let local_input_png = GeoPNG.loadNumberRasterImage(local_input_file_path);
							let local_input_sum = GeoPNG.getImageSum(local_input_file_path);
							local_scalar = world_pop_obj[hyde_years[i]]/local_input_sum;
							
							GeoPNG.saveNumberRasterImage({
								file_path: `${this.output_kk10_luh2_global_rasters}/popc_${hyde_years[i]}.png`,
								width: 4320,
								height: 2160,
								function: (local_index) => Math.ceil(local_input_png.data[local_index]*local_scalar)
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
		
		//1. Average greyscales from KK10/LUH2 climate models
		if (!options.exclude.includes("A")) await this.A_averageLUH2Rasters();
		//2. Convert greyscale images to GeoPNGs
		if (!options.exclude.includes("B")) await this.B_generateKK10LUH2Rasters();
		//3. Convert greyscale images to RGBA
		if (!options.exclude.includes("C")) await this.C_convertKK10LUH2RastersToRGBA({
			fallback_mode: "hyde"
		});
		//4. Scale KK10LUH2 to regional totals from HYDE
		if (!options.exclude.includes("D")) await this.D_scaleKK10LUH2RastersToHYDE();
		//5. Scale KK10LUH2 to regional totals from OWID
		if (!options.exclude.includes("E")) await this.E_scaleKK10LUH2RastersToOWID();
		//6. Scale KK10LUH2 to global totals
		if (!options.exclude.includes("F")) await this.F_scaleKK10LUH2RastersToGlobal();
	}
};