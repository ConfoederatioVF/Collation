global.gini_SubNGini = class { //[WIP] - Finish class body
	static bf = `${h1}/gini_SubNGini`;
	static input_subnational_raster = `${this.bf}/rast_adm1_gini_disp_1990_2023.tif`;
	static intermediate_subnational_masks_folder = `${h2}/gini_SubNGini/subnational_masks/`;
	static intermediate_subnational_rasters = `${h2}/gini_SubNGini/subnational_gini_rasters/`;
	static output_areal_json = `${this.intermediate_subnational_masks_folder}areal_metadata.json`;
	static output_areal_raster = `${this.intermediate_subnational_masks_folder}areal_masks.png`;
	static years = Array.getFilledDomain(1990, 2025);
	
	static async A_convertToPNGs () {
		console.log(`- Converting SubNGini to rasters ...`);
		await GeoTIFF.convertToPNGs(this.input_subnational_raster, `${this.intermediate_subnational_rasters}gini`, {
			format: "float32",
			years: this.years
		});
		console.log(`- Finished converting Gini GeoTIFFs to rasters.`);
	}
	
	static async B_generateArealMasks () {
		//Declare local instance variables
		let input_prefix = `${this.intermediate_subnational_masks_folder}gini_`;
		let output_prefix = this.output_areal_raster.replace("_masks.png", "").replace(".png", "");
		
		//Return statement
		return GeoPNG.shatter(input_prefix, output_prefix, {
			years: this.years
		});
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//1. Convert to intermediate_subnational_rasters
		if (!options.exclude.includes("A"))
			await this.A_convertToPNGs();
		if (!options.exclude.includes("B"))
			await this.B_generateArealMasks();
	}
};