global.births_deaths_Kummu = class {
	static bf = `${h2}/births_deaths_Kummu/`;
	static input_births_raster = `${h1}/births_deaths_Kummu/raster_birth_rate_2000_2019.tif`;
	static input_deaths_raster = `${h1}/births_deaths_Kummu/raster_death_rate_2000_2019.tif`;
	static intermediate_births_folder = `${this.bf}/subnational_birth_rasters/`;
	static intermediate_deaths_folder = `${this.bf}/subnational_death_rasters/`;
	static intermediate_birthrate_folder = `${this.bf}/subnational_birth_masks/`;
	static intermediate_deathrate_folder = `${this.bf}/subnational_death_masks/`;
	static output_births_folder = `${this.bf}/output_birth_rasters/`;
	static output_deaths_folder = `${this.bf}/output_death_rasters/`;
	static scalar = 1000; //Birth and death rates are measured per 1000
	static years = Array.getFilledDomain(2000, 2019);
	
	/**
	 * Converts raw births and deaths GeoTIFF files into individual yearly float32 PNG raster steps.
	 *
	 * @returns {Promise<void>}
	 */
	static async A_convertToPNGs () {
		console.log(`- Converting births GeoTIFF to rasters ...`);
		await GeoTIFF.convertToPNGs(this.input_births_raster, `${this.intermediate_births_folder}births`, {
			format: "float32",
			years: this.years
		});
		console.log(`- Converting deaths GeoTIFF to rasters ...`);
		await GeoTIFF.convertToPNGs(this.input_deaths_raster, `${this.intermediate_deaths_folder}deaths`, {
			format: "float32",
			years: this.years
		});
		
		console.log(`- Finished processing GeoTIFFs to rasters.`);
	}
	
	/**
	 * Shatters temporal birth and death rate rasters into unique spatial-temporal areal mask partitions.
	 * Writes mask rasters to `_masks.png` and trace histories to `_metadata.json`.
	 *
	 * @returns {Promise<Object>} An object containing metadata tracking lineage for births and deaths.
	 */
	static async B_generateArealMasks () {
		//Declare local instance variables
		let births_input_prefix = `${this.intermediate_births_folder}births_`;
		let births_output_prefix = `${this.intermediate_birthrate_folder}births`;
		let deaths_input_prefix = `${this.intermediate_deaths_folder}deaths_`;
		let deaths_output_prefix = `${this.intermediate_deathrate_folder}deaths`;
		
		console.log(`- Shattering subnational births rasters into areal masks ..`);
		let births_metadata = await GeoPNG.shatter(births_input_prefix, births_output_prefix, {
			years: this.years
		});
		
		console.log(`- Shattering subnational deaths rasters into areal masks ..`);
		let deaths_metadata = await GeoPNG.shatter(deaths_input_prefix, deaths_output_prefix, {
			years: this.years
		});
		
		//Return statement
		return {
			births: births_metadata,
			deaths: deaths_metadata
		};
	}
	
	/**
	 * Computes and outputs absolute birth and death count rasters using true gridcell population data.
	 * Formulates output values as: (rate / scalar) * population.
	 *
	 * @returns {Promise<void>}
	 */
	static async C_generateOutputRasters () {
		let years_list = this.years;
		let scalar_val = this.scalar;
		
		for (let i = 0; i < years_list.length; i++) {
			let current_year = years_list[i];
			let local_stadester_path = `${population_Stadester.input_popc_folder}stadester_population_${current_year}.png`;
			
			let local_stadester_popc_raster = GeoPNG.loadNumberRasterImage(local_stadester_path, {
				format: "float32"
			});
			
			let local_births_path = `${this.intermediate_births_folder}births_${current_year}.png`;
			let local_deaths_path = `${this.intermediate_deaths_folder}deaths_${current_year}.png`;
			
			let local_births_raster = GeoPNG.loadNumberRasterImage(local_births_path, {
				format: "float32"
			});
			let local_deaths_raster = GeoPNG.loadNumberRasterImage(local_deaths_path, {
				format: "float32"
			});
			
			let birth_output_path = `${this.output_births_folder}births_${current_year}.png`;
			let death_output_path = `${this.output_deaths_folder}deaths_${current_year}.png`;
			
			console.log(`- Generating absolute subnational output rasters for ${current_year} ..`);
			
			//Write out the absolute yearly births raster
			GeoPNG.saveNumberRasterImage({
				file_path: birth_output_path,
				format: "float32",
				width: local_stadester_popc_raster.width,
				height: local_stadester_popc_raster.height,
				function: function (local_index) {
					let population_val = local_stadester_popc_raster.data[local_index];
					let rate_val = local_births_raster.data[local_index];
					
					//Calculates absolute count: (rate / 1000) * total population
					return (rate_val / scalar_val) * population_val;
				}
			});
			
			//Write out the absolute yearly deaths raster
			GeoPNG.saveNumberRasterImage({
				file_path: death_output_path,
				format: "float32",
				width: local_stadester_popc_raster.width,
				height: local_stadester_popc_raster.height,
				function: function (local_index) {
					let population_val = local_stadester_popc_raster.data[local_index];
					let rate_val = local_deaths_raster.data[local_index];
					
					//Calculates absolute count: (rate / 1000) * total population
					return (rate_val / scalar_val) * population_val;
				}
			});
			await Blacktraffic.yield();
		}
	}
	
	/**
	 * Standard interface method to run the entire processing pipeline sequentially unless stages are specifically bypassed.
	 *
	 * @param {Object} [arg0_options] - Execution configuration parameters.
	 *  @param {string[]} [arg0_options.exclude=[]] - List of step keys to bypass (e.g. ["A", "B"]).
	 *
	 * @returns {Promise<void>}
	 */
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Execute steps sequentially unless skipped
		if (!options.exclude.includes("A")) await this.A_convertToPNGs();
		//[WIP] - Remove deadweight - if (!options.exclude.includes("B")) await this.B_generateArealMasks(); //This doesn't actually make sense, since these rasters are disaggregated
		if (!options.exclude.includes("C")) await this.C_generateOutputRasters();
	}
};