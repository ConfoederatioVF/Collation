global.population_Stadester_transform = class {
	static delta_population_density_folder = `${h3}/delta_population_density/`;
	static delta_rural_population_folder = `${h3}/delta_rural_population/`;
	static delta_total_population_folder = `${h3}/delta_total_population/`;
	static delta_urban_population_folder = `${h3}/delta_urban_population/`;
	
	static async A_generateDeltaRasters () {
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let stad = population_Stadester;
		
		//Generate delta series for all folders
		console.log(`Generating delta series for ${this.delta_population_density_folder} ..`);
		await GeoPNG.generateDeltaSeries(this.delta_population_density_folder, {
			input_format: "float32",
			input_format_function: (y) => `${stad.intermediate_popd_folder}stadester_density_${y}.png`,
			prefix: "delta_population_density_",
			years: hyde_years
		});
		console.log(`Generating delta series for ${this.delta_rural_population_folder} ..`);
		await GeoPNG.generateDeltaSeries(this.delta_rural_population_folder, {
			input_format: "float32",
			input_format_function: (y) => `${stad.input_rurc_folder}stadester_rural_${y}.png`,
			prefix: "delta_rural_population_",
			years: hyde_years 
		});
		console.log(`Generating delta series for ${this.delta_total_population_folder} ..`);
		await GeoPNG.generateDeltaSeries(this.delta_total_population_folder, {
			input_format: "float32",
			input_format_function: (y) => `${stad.input_popc_folder}stadester_population_${y}.png`,
			prefix: "delta_total_population_",
			years: hyde_years 
		});
		console.log(`Generating delta series for ${this.delta_urban_population_folder} ..`);
		await GeoPNG.generateDeltaSeries(this.delta_urban_population_folder, {
			input_format: "float32",
			input_format_function: (y) => `${stad.input_urbc_folder}stadester_urban_${y}.png`,
			prefix: "delta_urban_population_",
			years: hyde_years
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Process rasters
		if (!options.exclude.includes("A")) await this.A_generateDeltaRasters();
	}
};