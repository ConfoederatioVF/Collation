global.population_Substrata_northern_america = class {
	static northern_america_obj = {
		areal_masks: {
			//0. Agricultural Areas
			//0.1. McEvedy and Jones (Agricultural)
			mcevedy_and_jones_agricultural: {
				colour: `#34cc48`,
				density: 0.4 //(km^2)
			},
			
			//0.2. Nevle and Bird
			nevle_and_bird_agricultural: {
				colour: `#3cf03c`,
				density: 0.35 //(km^2)
			},
			nevle_and_bird_irrigated: {
				colour: `#adcb90`,
				density: 15/2.58999 //(km^2)
			},
			
			//1. Localised Scaling
			//1.1. Driver and Massey
			driver_and_massey_zero_to_two: {
				colour: "#004c6d",
				density: 1/100 //(km^2)
			},
			driver_and_massey_two_to_five: {
				colour: "#346888",
				density: (2+5)/200 //(km^2)
			},
			driver_and_massey_five_to_twelve: {
				colour: "#5886a5",
				density: (5+12)/200 //(km^2)
			},
			driver_and_massey_twelve_to_thirty: {
				colour: "#7aa6c2",
				density: (12+30)/200 //(km^2)
			},
			driver_and_massey_thirty_to_seventyfive: {
				colour: "#9dc6e0",
				density: (30+75)/200 //(km^2)
			},
			driver_and_massey_seventyfive_or_more: {
				colour: "#c1e7ff",
				density: 75/100 //(km^2)
			},
			
			//1.2. E. North American Population (Milner and Chaplin)
			"milner_and_chaplin_0.3": {
				colour: "#938901",
				density: 0.3
			},
			"milner_and_chaplin_0.505": {
				colour: "#b3a642",
				density: 0.505
			},
			"milner_and_chaplin_0.9": {
				colour: "#d2c471",
				density: 0.9
			},
			"milner_and_chaplin_1.1": {
				colour: "#f1e3a0",
				density: 1.1
			},
			
			//2. Regional Scaling
			hawaiian_islands: {
				colour: [170, 154, 88],
				population: {
					"1100": 100,
					"1219": 160,
					"1450": 135,
					"1500": 150,
					"1600": 96,
					"1700": 250,
					"1778": 360,
					"1805": 175,
					"1819": 144,
					"1850": 84.165,
					"1872": 56.897,
					"1896": 109.020
				},
				scalar: 1000,
				special_domain: true
			},
			nelson_northern_america: {
				colour: [175, 63, 34],
				population: {
					'0': 2175925.925925925,
					'100': 2185185.1851851847,
					'200': 2194444.444444444,
					'300': 2203703.7037037034,
					'400': 2212962.962962963,
					'500': 2388888.888888889,
					'600': 2314814.8148148153,
					'700': 2407407.407407408,
					'800': 2305555.555555557,
					'900': 2500000.000000001,
					'1000': 2500000.000000001,
					'1100': 2361111.111111113,
					'1200': 2453703.7037037048,
					'1300': 2569444.444444444,
					'1400': 2666666.666666666,
					'1500': 2916666.666666665,
					'-3000': 2222222.2222222225,
					'-2200': 2222222.222222222,
					'-2000': 2256944.444444445,
					'-1400': 2361111.111111111,
					'-1000': 2361111.111111113,
					'-700': 2222222.222222222,
					'-300': 2222222.222222222,
					'-100': 2166666.6666666665
				}
			},
			nelson_w_north_america: {
				colour: [60, 115, 173],
				population: {
					'0': 2870370.3703703685,
					'100': 2907407.407407406,
					'200': 2944444.444444443,
					'300': 2981481.481481481,
					'400': 3018518.518518518,
					'500': 2888888.8888888867,
					'600': 3055555.5555555555,
					'700': 3055555.5555555555,
					'800': 3055555.5555555555,
					'900': 2986111.11111111,
					'1000': 3124999.999999998,
					'1100': 3194444.444444443,
					'1200': 3287037.037037037,
					'1300': 3374999.999999997,
					'1400': 3645833.333333333,
					'1500': 3416666.6666666637,
					'-3000': 2500000.000000001,
					'-2200': 2500000,
					'-2000': 2506944.4444444454,
					'-1400': 2527777.7777777775,
					'-1000': 2670634.9206349193,
					'-700': 2777777.7777777775,
					'-300': 2777777.7777777775,
					'-100': 2833333.333333333
				},
			},
			nelson_e_north_america: {
				colour: [87, 122, 175],
				population: {
					'0': 3615740.7407407393,
					'100': 3620370.3703703694,
					'200': 3624999.999999999,
					'300': 3629629.629629629,
					'400': 3634259.2592592593,
					'500': 3611111.111111109,
					'600': 3638888.8888888895,
					'700': 3638888.8888888895,
					'800': 3830555.5555555574,
					'900': 3715277.777777779,
					'1000': 3958333.3333333335,
					'1100': 4201388.88888889,
					'1200': 4189814.8148148176,
					'1300': 4444444.444444445,
					'1400': 4513888.888888892,
					'1500': 4444444.444444445,
					'-3000': 2777777.777777775,
					'-2200': 3055555.555555555,
					'-2000': 3090277.7777777775,
					'-1400': 3194444.444444444,
					'-1000': 3353174.6031746026,
					'-700': 3472222.222222222,
					'-300': 3333333.333333333,
					'-100': 3611111.111111111
				}
			},
			
			//3. National Level Scaling
			canada: {
				colour: [175, 63, 76],
				population: {
					"-10000": 0.10,
					"0": 0.12,
					"1000": 0.38,
					"1500": 0.76,
					"1600": 0.2,
					"1800": 0.65
				},
				scalar: 1000000,
				special_domain: true
			},
			the_continental_usa: {
				colour: [67, 134, 175],
				population: {
					"-10000": 0.233969,
					"-9000": 0.259965,
					"-8000": 0.288850,
					"-7000": 0.320945,
					"-6000": 0.356605,
					"-5000": 0.396228,
					"-4000": 0.440253,
					"-3000": 0.489171,
					"-2000": 0.543523,
					"-1000": 0.603915,
					"0": 0.76,
					"500": 0.846755,
					"1000": 1.52,
					"1500": 3.04,
					"1600": 0.8
				},
				scalar: 1000000
			}
		},
		domain: [-10000, 1600]
	};
	
	static bf = `${h3}/population_Substrata.northern_america/`;
	static ef = `${h3}/population_Substrata.outlier_removal/`;
	static input_rasters_regions = `${this.bf}/rasters_regions/`;
	static output_rasters = `${this.ef}rasters_1.northern_america/`;
	
	static async A_getNorthernAmericaPopulationObject () {
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let northern_america_obj = JSON.parse(JSON.stringify(this.northern_america_obj));
		let northern_america_domain = northern_america_obj.domain;
		
		//Iterate over all areal_masks in northern_america_obj
		Object.iterate(northern_america_obj.areal_masks, (local_key, local_value) => {
			if (typeof local_value.colour === "string")
				local_value.colour = Colour.convertHexToRGB(local_value.colour);
			if (local_value.population) {
				let all_local_years = Object.keys(local_value.population)
				.map(Number).sort((a, b) => a - b);
				let local_mask_domain = [all_local_years[0], all_local_years[all_local_years.length - 1]];
				let years_to_interpolate = [];
				
				for (let x = 0; x < hyde_years.length; x++)
					if (hyde_years[x] >= local_mask_domain[0] && hyde_years[x] <= local_mask_domain[1]) {
						let is_in_domain = false;
						if (hyde_years[x] >= northern_america_domain[0] && hyde_years[x] <= northern_america_domain[1])
							is_in_domain = true;
						if (local_value.special_domain) is_in_domain = true;
						
						if (is_in_domain && !local_value.population[hyde_years[x]])
							years_to_interpolate.push(hyde_years[x]);
					}
				
				local_value.population = Object.cubicSplineInterpolation(local_value.population, { years: years_to_interpolate });
				if (local_value.scalar)
					local_value.population = Object.multiply(local_value.population, local_value.scalar);
			}
			
			northern_america_obj.areal_masks[local_key].key = local_key;
		});
		
		//Iterate over all areal_masks in northern_america_obj
		Object.iterate(northern_america_obj.areal_masks, (local_key, local_value) => {
			let local_mask = JSON.parse(JSON.stringify(local_value));
			let actual_key = [local_mask.colour[0], local_mask.colour[1], local_mask.colour[2]].join(",");
			
			northern_america_obj.areal_masks[actual_key] = local_mask;
			northern_america_obj.areal_masks[actual_key].is_clone = true;
		});
		
		//Return statement
		return northern_america_obj;
	}
	
	static async A_generateStadesterNorthernAmericaRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let hyde_years = (options.hyde_years) ? options.hyde_years : landuse_HYDE.sorted_hyde_years;
		let northern_america_obj = await this.A_getNorthernAmericaPopulationObject();
			let northern_america_domain = northern_america_obj.domain;
		let raster_obj = {};
		
		let all_png_files = fs.readdirSync(this.input_rasters_regions)
		.filter((file) => path.extname(file).toLowerCase() === ".png");
		
		//Iterate over all_png_files and populate raster_obj
		for (let i = 0; i < all_png_files.length; i++)
			all_png_files[i] = `${this.input_rasters_regions}/${all_png_files[i]}`;
		for (let i = 0; i < all_png_files.length; i++) {
			console.log(`- Loading ${all_png_files[i]} ..`);
			raster_obj[all_png_files[i]] = GeoPNG.loadImage(all_png_files[i]);
		}
		
		//1. Load Land Area Raster (1:1 pixel array)
		let land_area_raster = GeoPNG.loadNumberRasterImage(metadata_HYDE.input_raster_land_area, {
			format: "int32"
		});
		let raster_height = land_area_raster.height;
		let raster_width = land_area_raster.width;
		let total_pixel_count = raster_width*raster_height;
		let land_area_data = land_area_raster.data;
		
		let all_mask_keys = Object.keys(northern_america_obj.areal_masks);
		
		//2. Pre-index all mask pixel indices and calculate total mask land areas dynamically
		let areal_indexing = GeoPNG.indexArealMasks({
			areal_masks: northern_america_obj.areal_masks,
			land_area_raster: land_area_raster,
			mask_rasters: all_png_files.map((f) => raster_obj[f])
		});
		let mask_pixel_indices = areal_indexing.mask_pixel_indices;
		let mask_areas = areal_indexing.mask_areas;
		
		let checkMaskDomain = function (arg0_mask, arg1_year) {
			let mask_domain = northern_america_domain;
			if (arg0_mask.domain) {
				mask_domain = arg0_mask.domain;
			} else if (arg0_mask.population && typeof arg0_mask.population === "object") {
				let all_years = Object.keys(arg0_mask.population).map(Number).sort((a, b) => a - b);
				if (all_years.length > 0) mask_domain = [all_years[0], all_years[all_years.length - 1]];
			}
			
			let is_in_global_domain = (arg1_year >= northern_america_domain[0] && arg1_year <= northern_america_domain[1]);
			if (arg1_year >= mask_domain[0] && arg1_year <= mask_domain[1]) {
				if (is_in_global_domain || arg0_mask.special_domain) return true;
			}
			return false;
		};
		
		//Iterate over all hyde_years in parallel
		await GeoPNG.processTimeseriesParallel({
			concurrency: 4,
			items: hyde_years,
			name: "Northern America Substrata Dasymetric",
			handler: async (current_year) => {
				let local_input_file_path = `${population_Substrata_outlier_removal.intermediate_outliers_removed_rasters}popc_${current_year}.png`;
				let local_output_file_path = `${this.output_rasters}popc_${current_year}.png`;
				
				if (!fs.existsSync(local_input_file_path)) return;
				
				//Load underlying HYDE population raster asynchronously
				let base_pop_raster = await GeoPNG.loadNumberRasterImageAsync(local_input_file_path, { format: "float32" });
				let pop_buffer = new Float64Array(base_pop_raster.data);
				let year_targets = {};
				let active_mask_indices = {};
				
				//Determine targets for active masks for current year
				for (let x = 0; x < all_mask_keys.length; x++) {
					let mask_key = all_mask_keys[x];
					let local_mask = northern_america_obj.areal_masks[mask_key];
					if (local_mask.is_clone) continue;
					if (!checkMaskDomain(local_mask, current_year)) continue;
					
					let indices = mask_pixel_indices[local_mask.key] || [];
					let total_area = mask_areas[local_mask.key] || 0;
					if (indices.length === 0 || total_area <= 0) continue;
					
					let target_pop = undefined;
					if (local_mask.density !== undefined) {
						target_pop = total_area*local_mask.density;
					} else if (local_mask.population && local_mask.population[current_year] !== undefined) {
						target_pop = local_mask.population[current_year];
					}
					
					if (target_pop !== undefined && target_pop > 0) {
						year_targets[local_mask.key] = target_pop;
						active_mask_indices[local_mask.key] = indices;
					}
				}
				
				//Apply dasymetric scaling
				pop_buffer = GeoPNG.dasymetricScale({
					data: pop_buffer,
					mask_pixel_indices: active_mask_indices,
					targets: year_targets
				});
				
				//Save cleanly and asynchronously
				await GeoPNG.saveNumberRasterImageAsync({
					data: pop_buffer,
					file_path: local_output_file_path,
					format: "float32",
					height: raster_height,
					width: raster_width
				});
				
				console.log(`- Finished processing year ${current_year}.`);
			}
		});
	}
	
	static async processRasters () {
		await this.A_generateStadesterNorthernAmericaRasters();
	}
}