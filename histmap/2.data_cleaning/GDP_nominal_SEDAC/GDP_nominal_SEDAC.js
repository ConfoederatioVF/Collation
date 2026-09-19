global.GDP_nominal_SEDAC = class {
	static bf = `${h1}/GDP_nominal_SEDAC/`;
	static intermediate_folder = `${h2}/GDP_nominal_SEDAC/`;
	static intermediate_ols_folder = `${h2}/GDP_nominal_SEDAC/OLS/`;
	
	static async A_normaliseSEDACRastersToNominal () {
		//Declare local instance variables
		let all_ppp_files = await File.getAllFiles(GDP_PPP_SEDAC.bf);
		let gdp_obj = GDP_nominal.getGDPObject();
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocode_raster = GeoPNG.loadImage(admin_modern.input_geocodes_raster);
		let world_gdp_obj = GDP_nominal.getWorldGDPObject();
		let years = GDP_PPP_SEDAC.years;
		
		//Copy all_ppp_files into this.bf
		for (let i = 0; i < all_ppp_files.length; i++)
			if (all_ppp_files[i].endsWith(".png")) {
				let local_output_file_path = `${this.bf}${path.basename(all_ppp_files[i]).replace("_PPP", "")}`;
				fs.copyFileSync(all_ppp_files[i], local_output_file_path);
				
				console.log(`Copied ${all_ppp_files[i]} to ${local_output_file_path}.`);
				await Blacktraffic.yield();
			}
		
		//Iterate over all_files; normalise them to world_gdp_obj
		for (let i = 0; i < years.length; i++) {
			let local_file_path = `${this.bf}GDP_${years[i]}.png`;
			let local_input_png = GeoPNG.loadNumberRasterImage(local_file_path, {
				format: "float32"
			});
			let local_input_sum = GeoPNG.getImageSum(local_file_path, {
				format: "float32"
			});
			let local_target = world_gdp_obj[years[i]];
			let local_scalar = local_target / local_input_sum;
			
			GeoPNG.saveNumberRasterImage({
				file_path: local_file_path,
				format: "float32",
				width: 4320,
				height: 2160,
				function: (local_index) => local_input_png.data[local_index] * local_scalar
			});
			console.log(`- ${years[i]} - Input GDP: ${String.formatNumber(local_input_sum)}, Target GDP: ${String.formatNumber(local_target)} - Scalar: ${local_scalar}`);
			await Blacktraffic.yield();
		}
		
		//Iterate over all years
		for (let i = 0; i < years.length; i++) {
			let local_gdp_scalars = {};
			let local_gdp_sums = {};
			let local_file_path = `${this.bf}GDP_${years[i]}.png`;
			let local_raster = GeoPNG.loadNumberRasterImage(local_file_path, {
				format: "float32"
			});
			
			//1. Operate over file; populate local_gdp_sums; calculate local_gdp_scalars
			GeoPNG.operateNumberRasterImage({
				file_path: local_file_path,
				format: "float32",
				function: (local_index, local_value) => {
					let local_byte_index = local_index * 4;
					let local_colour_key = [
						geocode_raster.data[local_byte_index],
						geocode_raster.data[local_byte_index + 1],
						geocode_raster.data[local_byte_index + 2]
					].join(",");
					let local_geocodes = geocode_obj[local_colour_key];
					
					if (local_geocodes)
						for (let x = 0; x < local_geocodes.length; x++)
							Object.modifyValue(local_gdp_sums, local_geocodes[x], local_value);
				}
			});
			Object.iterate(local_gdp_sums, (local_key, local_value) => {
				let local_actual_gdp = gdp_obj[local_key]?.[years[i]];
				local_gdp_scalars[local_key] = (local_actual_gdp) ? local_actual_gdp / local_value : 1;
			});
			
			//2. Scale by local_gdp_scalars
			GeoPNG.saveNumberRasterImage({
				file_path: local_file_path,
				format: "float32",
				height: 2160,
				width: 4320,
				function: (local_index) => {
					let byte_index = local_index * 4;
					let local_colour_key = [
						geocode_raster.data[byte_index],
						geocode_raster.data[byte_index + 1],
						geocode_raster.data[byte_index + 2]
					].join(",");
					let local_geocodes = geocode_obj[local_colour_key];
					let local_value = local_raster.data[local_index];
					
					if (local_geocodes)
						for (let x = 0; x < local_geocodes.length; x++) {
							let local_gdp = gdp_obj[local_geocodes[x]]?.[years[i]];
							if (local_gdp) return local_value * local_gdp_scalars[local_geocodes[x]];
						}
					return local_value;
				}
			});
			console.log(`- Processed ${local_file_path}.`);
			await Blacktraffic.yield();
		}
	}
	
	static async B_loadCovariates (arg0_year) {
		//Convert from parameters
		let year = arg0_year;
		
		//Declare local instance variables
		let input_file_path = `${this.bf}/GDP_${year}.png`;
		
		//Return statement
		return Statistics.loadOLSCovariates(input_file_path, {
			utility_format: "float32",
			
			covariates_obj: GDP_PPP_SEDAC.covariates_obj,
			formatting_parameters: [year]
		});
	}
	
	static async B_trainGDPModel (arg0_year, arg1_options) {
		//Convert from parameters
		let year = parseInt(arg0_year);
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (!options.lambda) options.lambda = 1e11;
		if (!options.key) options.key = year.toString();
		
		//Declare local instance variables
		let covariates_obj = await this.B_loadCovariates(year);
		let output_file_path = `${this.intermediate_ols_folder}/OLS_GDP_${year}.json`;
		
		//Return statement
		return Statistics.trainOLSModel(output_file_path, covariates_obj, options);
	}
	
	static async B_trainGDPModels (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		let years = GDP_PPP_SEDAC.years;
		
		//Declare local instance variables
		let all_covariate_keys = Object.keys(GDP_PPP_SEDAC.covariates_obj);
		let lambda_val = (options.lambda !== undefined) ? options.lambda : 1e11;
		
		//Return statement
		return await Statistics.trainOLSModelsParallel(years, (year) => {
			let covariates_map = {};
			for (let i = 0; i < all_covariate_keys.length; i++) {
				let local_key = all_covariate_keys[i];
				let local_val = GDP_PPP_SEDAC.covariates_obj[local_key](year);
				covariates_map[local_key] = local_val;
			}
			
			return {
				covariates_map: covariates_map,
				options: {
					...options,
					key: year.toString(),
					lambda: lambda_val
				},
				output_file_path: `${this.intermediate_ols_folder}/OLS_GDP_${year}.json`,
				target_file_path: `${this.bf}/GDP_${year}.png`,
				target_format: "float32"
			};
		}, {
			concurrency: options.concurrency,
			name: "GDP Nominal SEDAC OLS Training"
		});
	}
	
	static async C_geomeanGDPModel (arg0_prefix) {
		//Convert from parameters
		let prefix = (arg0_prefix) ? arg0_prefix : "OLS_GDP_";
		
		//Return statement
		return Statistics.geomeanOLSModels(this.intermediate_ols_folder, prefix, {
			weighting_function: (value) => Math.abs(value) //Flip positive to adjust for collinearity
		});
	}
	
	static async D_processGDPModel (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let model_file_path = `${this.intermediate_ols_folder}/geomean_OLS_GDP.json`;
		let output_file_path = `${this.intermediate_ols_folder}/processed_base_model.json`;
		let years = GDP_PPP_SEDAC.years;
		
		//Return statement
		return Statistics.processOLSModel(model_file_path, {
			...options,
			output_file_path,
			
			covariates_obj: GDP_PPP_SEDAC.covariates_obj,
			target: (y) => [`${this.bf}/GDP_${y}.png`, "float32"],
			steps: years,
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		let skip_training = (options.skip_training || options.use_existing_models || options.train === false);
		
		//1. Normalise SEDAC rasters to nominal GDP
		if (!options.exclude.includes("A")) await this.A_normaliseSEDACRastersToNominal();
		
		//2. Train individual yearly OLS models
		if (!options.exclude.includes("B") && !skip_training) await this.B_trainGDPModels(options);
		
		//3. Compute geomean
		if (!options.exclude.includes("C") && !skip_training) try {
			await this.C_geomeanGDPModel("OLS_GDP_");
		} catch (e) { console.error(e); }
		
		//4. Bidirectionally adjust weights
		//if (!options.exclude.includes("D")) await this.D_processGDPModel(options);
	}
};