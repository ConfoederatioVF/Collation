global.landuse_HYDE = class {
	static _cache_mcevedy_obj;
	static hyde_dictionary = {
		//LU (Land Use)
		"conv_rangeland": "Converted Rangeland (km^2/cell)",
		"cropland": "Cropland (km^2/cell)",
		"grazing": "Grazing Land (km^2/cell)",
		"ir_norice": "Irrigated Non-Rice Cropland (km^2/cell)",
		"ir_rice": "Irrigated Rice Cropland (km^2/cell)",
		"pasture": "Pasture Area (km^2/cell)",
		"rangeland": "Rangeland Area (km^2/cell)",
		"rf_norice": "Rainfed Non-Rice Cropland (km^2/cell)",
		"rf_rice": "Rice Cropland (km^2/cell)",
		"shifting": "Manual Weight Changes (Unknown)",
		"tot_irri": "Irrigated Area (km^2/cell)",
		"tot_rainfed": "Rainfed Non-Rice Cropland (km^2)",
		"tot_rice": "Rice Cropland (km^2)",
		
		//POP (Demographics)
		"popc_": "Total Population (pop/cell)",
		"popd_": "Population Density (pop/km^2)",
		"rurc_": "Rural Population (pop/cell)",
		"uopp_": "Built-Up Area (km^2/cell)",
		"urbc_": "Urban Population (pop/cell)"
	};
	static hyde_original_years = [
		//100-year intervals
		0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
		
		//10-year intervals
		1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950,
		
		//1-year intervals
		1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2019, 2020, 2021, 2022, 2023,
		
		//Post-addendum (1000-year intervals except 10000BC in base dataset)
		-1000, -3000, -4000, -5000, -6000, -7000, -8000, -9000
	];
	static hyde_years = [
		//100-year intervals
		0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700,
		
		//10-year intervals
		1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890, 1900, 1910, 1920, 1930, 1940, 1950,
		
		//1-year intervals
		1951, 1952, 1953, 1954, 1955, 1956, 1957, 1958, 1959, 1960, 1961, 1962, 1963, 1964, 1965, 1966, 1967, 1968, 1969, 1970, 1971, 1972, 1973, 1974, 1975, 1976, 1977, 1978, 1979, 1980, 1981, 1982, 1983, 1984, 1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023,
		
		//Post-addendum
		-1000, -2000, -3000, -4000, -5000, -6000, -7000, -8000, -9000, -10000
	];
	static sorted_hyde_years = this.hyde_years.concat([2024, 2025])
		.sort((a, b) => a - b);
	
	static input_mcevedy_json = `${h2}/landuse_HYDE/config/mcevedy_data.json`;
	static input_raster_mcevedy = `${h2}/landuse_HYDE/config/mcevedy_subdivisions.png`;
	static input_rasters_equirectangular = `${h1}/landuse_HYDE/`;
	static intermediate_rasters_equirectangular = `${h2}/landuse_HYDE/rasters/`;
	static intermediate_rasters_mcevedy = `${h2}/landuse_HYDE/rasters_mcevedy/`;
	static intermediate_rasters_scaled_to_global = `${h2}/landuse_HYDE/rasters_scaled_to_global/`;
	
	static async _checkGlobalPopulation () {
		//Declare local instance variables
		let hyde_years = this.hyde_years;
		
		//Iterate over all hyde_years before 1500AD and clamp them
		for (let i = 0; i < hyde_years.length; i++)
			await new Promise((resolve, reject) => {
				setImmediate(() => {
					try {
						console.log(`Global population for ${this._getHYDEYearName(hyde_years[i])}:`, String.formatNumber(
							GeoPNG.getImageSum(`${this.intermediate_rasters_scaled_to_global}/popc_${hyde_years[i]}.png`)
						));
						resolve();
					} catch (err) {
						reject(err);
					}
				});
			});
	}
	
	/**
	 * @param {number|string} arg0_year
	 *
	 * @returns {string}
	 */
	static _getHYDEYearName (arg0_year) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		
		//Return statement
		return `${Math.abs(year)}${(year >= 0) ? "AD" : "BC"}`;
	}
	
	static async A_convertToPNGs (arg0_input_folder, arg1_output_folder, arg2_options) {
		//Convert from parameters
		let input_folder = arg0_input_folder;
		let output_folder = arg1_output_folder;
		let options = arg2_options ? arg2_options : {};
		
		//Declare local instance variables
		let all_input_files = await File.getAllFiles(input_folder);
		
		//Iterate over all_input_files
		for (let i = 0; i < all_input_files.length; i++) {
			let current_path = all_input_files[i];
			
			//Use the promise-based lstat
			let stats = await fs.promises.lstat(current_path);
			
			if (stats.isDirectory()) {
				console.log(`Parsing HYDE folder: ${current_path}`);
				
				//Await the recursive call so the folders are processed in order
				await this.A_convertToPNGs(current_path, output_folder, options);
			} else if (current_path.endsWith(".asc")) {
				let local_suffix = (options.mode === "percentage") ? 
					"_percentage" : "_number";
				
				// Extract filename without extension and build output path
				let local_file_name = path.basename(current_path, ".asc");
				let output_path = path.join(
					output_folder,
					`${local_file_name}${local_suffix}.png`
				);
				console.log(`Converting: ${local_file_name}.asc`);
				
				//setImmediate wrapper
				await new Promise((resolve, reject) => {
					setImmediate(() => {
						try {
							GeoASC.convertToPNG(current_path, output_path, options);
							resolve();
						} catch (err) {
							reject(err);
						}
					});
				});
			}
		}
	}
	
	/**
	 * Fills in missing HYDE years by performing linear or polynomial interpolation.
	 * 
	 * @param {number|string} arg0_year - The year to generate the raster set for.
	 * @param {Object} [arg1_options]
	 *  @param {Array<String>} [arg1_options.hyde_keys] - The keys to generate the raster set for. All by default.
	 *  @param {String} [arg1_options.mode="linear"] - The mode to use for interpolation. Either 'linear' or 'polynomial'.
	 *  @param {boolean} [arg1_options.skip_file_if_it_exists=false] - Whether to skip the file if it already exists.
	 */
	static async B_interpolateHYDEYearRaster (arg0_year, arg1_options) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let actual_hyde_years = this.hyde_original_years;
		let hyde_dictionary = this.hyde_dictionary;
		let hyde_domain = Array.findDomain(actual_hyde_years, year);
		
		//Iterate over all keys in hyde_dictionary and perform linear interpolation
		let all_hyde_keys = (options.hyde_keys) ?
			Array.toArray(options.hyde_keys) : Object.keys(hyde_dictionary);
		
		console.log(`Generating Rasters for year ${year} ..`);
		
		for (let i = 0; i < all_hyde_keys.length; i++) {
			let local_left_image_path = `${this.intermediate_rasters_equirectangular}${all_hyde_keys[i]}${this._getHYDEYearName(hyde_domain[0])}_number.png`;
			let local_right_image_path = `${this.intermediate_rasters_equirectangular}${all_hyde_keys[i]}${this._getHYDEYearName(hyde_domain[1])}_number.png`;
			
			let local_left_image = GeoPNG.loadNumberRasterImage(local_left_image_path);
			let local_right_image = GeoPNG.loadNumberRasterImage(local_right_image_path);
			
			let local_number_output_file_path = `${this.intermediate_rasters_equirectangular}${all_hyde_keys[i]}${this._getHYDEYearName(year)}_number.png`;
			let local_percentage_output_file_path = `${this.intermediate_rasters_equirectangular}${all_hyde_keys[i]}${this._getHYDEYearName(year)}_percentage.png`;
			let skip_file = false;
			if (options.skip_file_if_it_exists)
				skip_file = fs.existsSync(local_number_output_file_path);
			
			console.log(`- Saving ${all_hyde_keys[i]}`);
			
			if (!skip_file)
				GeoPNG.saveNumberRasterImage({
					file_path: local_number_output_file_path,
					width: local_left_image.width,
					height: local_left_image.height,
					function: function (arg0_index) {
						//Convert from parameters
						let local_index = arg0_index;
						
						//Interpolate growth rate between left and right images at pixel value
						let left_number = local_left_image.data[local_index];
						let right_number = local_right_image.data[local_index];
						
						let local_value = Math.ceil(Array.linearInterpolation([hyde_domain[0], hyde_domain[1]], [left_number, right_number], year));
						if (local_value < 0) local_value = 0;
						
						//Return statement
						return local_value;
					}
				});
			GeoPNG.savePercentageRasterImage(local_number_output_file_path, local_percentage_output_file_path);
		}
	}
	
	/**
	 * Interpolates missing HYDE rasters.
	 */
	static async B_interpolateHYDEYearRasters () {
		//Declare local instance variables
		let actual_hyde_years = this.hyde_original_years;
		let hyde_years = this.hyde_years;
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++)
			if (!actual_hyde_years.includes(hyde_years[i]))
				this.B_interpolateHYDEYearRaster(hyde_years[i]);
	}
	
	static async C_clampHYDEToMcEvedy (arg0_year, arg1_options) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let hyde_population_file_path = `${this.intermediate_rasters_equirectangular}popc_${this._getHYDEYearName(year)}_number.png`;
		let hyde_urbc_file_path = `${this.intermediate_rasters_equirectangular}urbc_${this._getHYDEYearName(year)}_number.png`;
		let hyde_rurc_file_path = `${this.intermediate_rasters_equirectangular}rurc_${this._getHYDEYearName(year)}_number.png`;
		
		if (!fs.existsSync(hyde_population_file_path) || !fs.existsSync(hyde_urbc_file_path) || !fs.existsSync(hyde_rurc_file_path)) {
			console.error(`Could not find files for year:`, year);
			return; //Internal guard clause if file paths do not exist
		}
		
		let mcevedy_colourmap_obj = {};
		let mcevedy_obj = (options.mcevedy_obj) ? options.mcevedy_obj : await this.C_getMcEvedyObject();
		let mcevedy_subdivisions_file_path = this.input_raster_mcevedy;
		let mcevedy_subdivisions_image = pngjs.PNG.sync.read(fs.readFileSync(mcevedy_subdivisions_file_path));
		
		//1. Process mcevedy_obj
		Object.iterate(mcevedy_obj, (local_key, local_value) => {
			if (local_value.colour)
				mcevedy_colourmap_obj[local_value.colour.join(",")] = local_key;
			if (local_value.hyde_population === undefined) local_value.hyde_population = 0;
			if (local_value.hyde_pixels === undefined) local_value.hyde_pixels = 0;
		});
		
		//2. Process popc to sum up .hyde_population for year and calculate hyde_scalar_obj
		GeoPNG.operateNumberRasterImage({
			file_path: hyde_population_file_path,
			function: (local_index, local_value) => {
				let local_key = [
					mcevedy_subdivisions_image.data[local_index],
					mcevedy_subdivisions_image.data[local_index + 1],
					mcevedy_subdivisions_image.data[local_index + 2]
				].join(",");
				
				if (mcevedy_colourmap_obj[local_key]) {
					let local_country = mcevedy_obj[mcevedy_colourmap_obj[local_key]];
					local_country.hyde_pixels++;
					local_country.hyde_population += local_value;
				}
			}
		});
		Object.iterate(mcevedy_obj, (local_key, local_value) => {
			if (local_value?.population)
				if (local_value.population[year.toString()] !== undefined) {
					let local_mcevedy_population = local_value.population[year.toString()];
					
					if (local_mcevedy_population !== 0) {
						local_value.hyde_scalar = Math.returnSafeNumber(local_mcevedy_population/local_value.hyde_population, 1);
					} else {
						local_value.hyde_scalar = 0;
					}
				}
		});
		
		//3. Process hyde_population_file_path, hyde_urbc_file_path, hyde_rurc_file_path
		let input_output_map = [
			[hyde_population_file_path, `${this.intermediate_rasters_mcevedy}popc_${year}.png`],
			[hyde_urbc_file_path, `${this.intermediate_rasters_mcevedy}urbc_${year}.png`],
			[hyde_rurc_file_path, `${this.intermediate_rasters_mcevedy}rurc_${year}.png`]
		];
		
		//Iterate over input_output_map and scale by .hyde_scalar
		for (let i = 0; i < input_output_map.length; i++) {
			let local_input_png = GeoPNG.loadNumberRasterImage(input_output_map[i][0]);
			
			GeoPNG.saveNumberRasterImage({
				file_path: input_output_map[i][1],
				width: 4320,
				height: 2160,
				function: (local_index) => {
					let local_key = [
						mcevedy_subdivisions_image.data[local_index*4],
						mcevedy_subdivisions_image.data[local_index*4 + 1],
						mcevedy_subdivisions_image.data[local_index*4 + 2]
					].join(",");
					let local_value = local_input_png.data[local_index];
					
					//Implement hyde_scalar
					if (mcevedy_colourmap_obj[local_key]) {
						let local_country = mcevedy_obj[mcevedy_colourmap_obj[local_key]];
						
						//Return statement
						if (local_country.hyde_scalar !== undefined)
							return Math.ceil(local_value*local_country.hyde_scalar);
					}
					return local_value;
				}
			});
			
			console.log(`Finished processing ${input_output_map[i][1]}`);
			console.log(`- Input Sum:`, GeoPNG.getImageSum(input_output_map[i][0]));
			console.log(`- Output Sum:`, GeoPNG.getImageSum(input_output_map[i][1]));
		}
	};
	
	static async C_getMcEvedyObject () {
		if (this._cache_mcevedy_obj) return this._cache_mcevedy_obj; //Internal guard clause if this._cache_mcevedy_obj has already been calculated
		
		//Declare local instance variables
		let all_hyde_years = [];
		let hyde_years = this.hyde_years;
		let mcevedy_obj = JSON.parse(fs.readFileSync(this.input_mcevedy_json, "utf8"));
		
		//Populate all_hyde_years
		all_hyde_years = all_hyde_years.concat(hyde_years);
		all_hyde_years = Array.sort(all_hyde_years, { mode: "ascending" });
		
		//Perform polynomial interpolation on McEvedy data
		Object.iterate(mcevedy_obj, (local_key, local_value) => {
			if (local_value.population) {
				//Iterate over local_value.population to convert it from millions to base units
				local_value.population = Object.multiply(local_value.population, 1000000);
				let values = Object.values(local_value.population).map((value) => value);
				let years = Object.keys(local_value.population).map((year) => parseInt(year));
				
				//Ensure values; years are sorted properly
				let sorted_indices = years.map((_, i) => i).sort((a, b) => years[a] - years[b]);
					years = sorted_indices.map(i => years[i]);
					values = sorted_indices.map(i => values[i]);
				
				//Iterate over all_hyde_years and perform interpolation if within the given domain
				if (values.length > 0 && years.length > 0)
					for (let x = 0; x < all_hyde_years.length; x++)
						if (all_hyde_years[x] >= years[0] && all_hyde_years[x] <= years[years.length - 1])
							local_value.population[all_hyde_years[x]] = Math.ceil(
								Math.returnSafeNumber(Array.cubicSplineInterpolation(years, values, all_hyde_years[x]))
							);
				
				//Iterate over all hyde_years and set to 0 if first local_country.population year is < 0.0001
				let first_population_value = local_value.population[years[0]];
				
				if (first_population_value < 0.0001)
					for (let x = 0; x < all_hyde_years.length; x++)
						if (all_hyde_years[x] <= years[0])
							local_value.population[all_hyde_years[x]] = 0;
				
				//Remove any McEvedy data projected after 1975
				Object.iterate(local_value.population, (local_subkey) => {
					if (parseInt(local_subkey) > 1975)
						delete local_value.population[local_key];
				});
			}
		});
		this._cache_mcevedy_obj = mcevedy_obj;
		
		//Return statement
		return mcevedy_obj;
	}
	
	static async C_clampHYDERastersToMcEvedy () {
		//Declare local instance variables
		let hyde_years = this.hyde_years;
		let mcevedy_obj = await this.C_getMcEvedyObject();
		
		//Iterate over all hyde_years before 1500AD and clamp them
		for (let i = 0; i < hyde_years.length; i++)
			if (hyde_years[i] <= 1500)
				await this.C_clampHYDEToMcEvedy(hyde_years[i], {
					mcevedy_obj: mcevedy_obj
				});
	}
	
	static async D_scaleRastersToGlobalEstimates () {
		//Declare local instance variables
		let hyde_years = this.hyde_years;
		let world_pop_obj = population_Global.A_getWorldPopulationObject();
		
		//Iterate over all hyde_years
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_raster = `${this.intermediate_rasters_mcevedy}/popc_${hyde_years[i]}.png`;
			let local_scalar = 1;
			
			if (!fs.existsSync(local_input_raster)) //Load HYDE raster as fallback
				local_input_raster = `${this.intermediate_rasters_equirectangular}/popc_${this._getHYDEYearName(hyde_years[i])}_number.png`;
			if (fs.existsSync(local_input_raster)) 
				await new Promise((resolve, reject) => {
					setImmediate(() => {
						try {
							let local_input_png = GeoPNG.loadNumberRasterImage(local_input_raster);
							let local_input_sum = GeoPNG.getImageSum(local_input_raster);
							local_scalar = world_pop_obj[hyde_years[i]]/local_input_sum;
							
							GeoPNG.saveNumberRasterImage({
								file_path: `${this.intermediate_rasters_scaled_to_global}/popc_${hyde_years[i]}.png`,
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
		let options = (arg0_options) ? arg0_options : {};
		
		if (!options.exclude) options.exclude = [];
		
		//1. Convert equirectangular rasters
		if (!options.exclude.includes("A"))
			await this.A_convertToPNGs(this.input_rasters_equirectangular, this.intermediate_rasters_equirectangular, {
				mode: "number"
			});
		//2. Interpolate missing years
		if (!options.exclude.includes("B")) await this.B_interpolateHYDEYearRasters();
		//3. Clamp to McEvedy
		if (!options.exclude.includes("C")) await this.C_clampHYDERastersToMcEvedy();
		//4. Clamp to global population estimates
		if (!options.exclude.includes("D")) await this.D_scaleRastersToGlobalEstimates();
	}
};