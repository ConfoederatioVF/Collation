global.population_GHSL = class { //[WIP] - Finish class body
	//[NOTE] - Láng-Ritter et al. rural pop. underweighting is currently being contested. As of 22 August 2026, it should be waited on to see how the academic debate/response chain around it shakes out before going through with code changes - Kätzchen and Tacitus
	static bf = `${h2}/population_GHSL/`;
	static cleaned_rasters_folder = `${this.bf}cleaned_rasters/`;
	static input_geotiffs_folder = `${h1}/population_GHSL/population_rasters/1.geotiffs/`;
	static input_raw_rasters_folder = `${h1}/population_GHSL/population_rasters/2.rasters/`;
	
	static async A_convertToPNGs () {
		//Declare local instance variables
		let all_files = await File.getAllFiles(this.input_geotiffs_folder);
		
		//Iterate over all_files, convert them to float32
		console.log(`- Attempting conversion from source .tif (5-arcmin). Ensure you have GDAL installed in your Anaconda.`);
		
		for (let i = 0; i < all_files.length; i++) {
			let file_name = path.basename(all_files[i]);
			
			if (file_name.startsWith("GHS_POP_E") && file_name.endsWith(".tif")) {
				let local_year = parseInt(file_name.replace("GHS_POP_E", "")
				.replace(".tif", ""));
				
				let local_output_path = `${this.cleaned_rasters_folder}GHS_POP_${local_year}.png`;
				let temp_tif_path = `${this.cleaned_rasters_folder}temp_${file_name}`;
				
				//Translate 64-bit GeoTIFF to a standard Float32 TIFF to fix the predictor decompression error
				let command = `conda run gdal_translate -ot Float32 "${all_files[i]}" "${temp_tif_path}"`;
					await child_process.execSync(command, { stdio: "ignore" });
				await GeoTIFF.convertToPNG(temp_tif_path, local_output_path, { format: "float32" });
				
				//Clean up temporary converted TIFF
				if (fs.existsSync(temp_tif_path)) fs.unlinkSync(temp_tif_path);
				
				console.log(`- Finished writing ${all_files[i]} to ${local_output_path}.`);
			}
		}
	}
	
	static async A_fixCorruptPixels () {
		//Declare local instance variables
		if (!fs.existsSync(this.cleaned_rasters_folder))
			fs.mkdirSync(this.cleaned_rasters_folder, { recursive: true });
			
		//Initialise cleaned_rasters_folder from input_raw_rasters_folder if not already populated
		if (fs.existsSync(this.input_raw_rasters_folder)) {
			let raw_files = await File.getAllFiles(this.input_raw_rasters_folder);
			for (let i = 0; i < raw_files.length; i++) {
				let file_name = path.basename(raw_files[i]);
				let dest_path = path.join(this.cleaned_rasters_folder, file_name);
				if (!fs.existsSync(dest_path))
					fs.copyFileSync(raw_files[i], dest_path);
			}
		}

		let all_files = await File.getAllFiles(this.cleaned_rasters_folder);
		let corrupt_floats = [];
		let corrupt_raw_bytes = [ //[WIP] - Are these the only corrupt_raw_bytes? Set it as a mask for subsequent rasters
			[57, 13, 4, 233],
			[58, 165, 73, 10],
			[58, 7, 249, 128],
			[59, 15, 12, 72],
			[59, 83, 37, 167],
			[59, 6, 253, 177],
			[58, 19, 101, 94],
			[58, 26, 67, 72],
			[58, 166, 243, 123]
		];
		let image_height = 2160;
		let image_width = 4320;
		
		//Convert corrupt RGBA byte sets to both Little-Endian and Big-Endian float values for exact matching
		for (let i = 0; i < corrupt_raw_bytes.length; i++) {
			let buffer = new ArrayBuffer(4);
			let view = new DataView(buffer);
			
			for (let j = 0; j < 4; j++) view.setUint8(j, corrupt_raw_bytes[i][j]);
			
			corrupt_floats.push(view.getFloat32(0, true));  //Little-endian
			corrupt_floats.push(view.getFloat32(0, false)); //Big-endian
		}
		
		//Iterate over all_files and zero corrupt pixels
		for (let i = 0; i < all_files.length; i++) {
			let file_name = path.basename(all_files[i]);
			
			if (file_name.startsWith("GHS_POP_") && file_name.endsWith(".png")) {
				let local_file_path = all_files[i];
				let local_png = GeoPNG.loadNumberRasterImage(local_file_path, { format: "float32" });
				
				//1. Zero the 1x264 vertical strip at x: 0, y: 1283 to 1546
				for (let y = 1283; y < 1283 + 264; y++) {
					let pixel_index = y*image_width + 0;
					local_png.data[pixel_index] = 0;
				}
				
				//2. Zero matching corrupted float values across the raster
				for (let p = 0; p < local_png.data.length; p++)
					if (corrupt_floats.includes(local_png.data[p]))
						local_png.data[p] = 0;
				
				//Save the cleaned raster
				GeoPNG.saveNumberRasterImage({
					file_path: local_file_path,
					format: "float32",
					width: image_width,
					height: image_height,
					function: (local_index) => local_png.data[local_index]
				});
				
				console.log(`- Cleaned corrupt pixels for ${local_file_path}.`);
			}
		}
	}
	
	static async B_interpolatePNGs () {
		//Declare local instance variables
		this.B_is_interpolating = true;
		let all_files = await File.getAllFiles(this.cleaned_rasters_folder);
		let all_years = [];
		
		//Iterate over all_files and push to all_years
		for (let i = 0; i < all_files.length; i++) {
			let file_name = path.basename(all_files[i]);
			
			if (file_name.startsWith("GHS_POP_"))
				all_years.push(parseInt(file_name.replace("GHS_POP_", "")
					.replace(".png", "")));
		}
		
		//Iterate over all_years and interpolate between them
		all_years.sort((a, b) => a - b); //Sort in ascending order
		
		for (let i = 0; i < all_years.length - 1; i++) {
			let end_year = all_years[i + 1];
			let start_year = all_years[i];
			let year_gap = end_year - start_year;
			
			if (year_gap > 1) {
				let from_file_path = path.join(this.cleaned_rasters_folder, `GHS_POP_${start_year}.png`);
				let to_file_path = path.join(this.cleaned_rasters_folder, `GHS_POP_${end_year}.png`);
				
				for (let x = start_year + 1; x < end_year; x++) {
					let fraction = (x - start_year)/year_gap;
					let output_file_path = path.join(this.cleaned_rasters_folder, `GHS_POP_${x}.png`);
					
					GeoPNG.linearInterpolation(from_file_path, to_file_path, output_file_path, {
						format: "float32",
						fraction
					});
					console.log(`- Finished interpolating ${output_file_path}.`);
				}
			}
		}
		this.B_is_interpolating = false;
	}
	
	static async C_scalePNGsToGlobalPopulation () {
		//Poll until this.B_interpolatePNGs() has finished executing
		while (this.B_is_interpolating) await new Promise((resolve) => setTimeout(resolve, 100));
		
		//Declare local instance variables
		let all_files = await File.getAllFiles(this.cleaned_rasters_folder);
		let world_pop_obj = population_Global.A_getWorldPopulationObject();
		
		//Iterate over all_files in this.cleaned_rasters_folder and scale them
		for (let i = 0; i < all_files.length; i++) {
			let local_input_file_path = all_files[i];
			let local_scalar = 1;
			
			if (fs.existsSync(local_input_file_path))
				await new Promise((resolve, reject) => {
					setImmediate(() => {
						try {
							let file_name = path.basename(local_input_file_path);
							
							if (file_name.startsWith("GHS_POP_") && file_name.endsWith(".png")) {
								let local_year = parseInt(file_name.replace("GHS_POP_", "").replace(".png", ""));
								
								//Only scale if world pop target explicitly exists for this year
								if (world_pop_obj[local_year]) {
									let local_input_png = GeoPNG.loadNumberRasterImage(local_input_file_path, {
										format: "float32"
									});
									let local_input_sum = GeoPNG.getImageSum(local_input_file_path, {
										format: "float32"
									});
									local_scalar = world_pop_obj[local_year]/local_input_sum;
									
									GeoPNG.saveNumberRasterImage({
										file_path: local_input_file_path,
										format: "float32",
										width: 4320,
										height: 2160,
										function: (local_index) => local_input_png.data[local_index]*local_scalar
									});
									console.log(`- ${local_year} - Input Population: ${local_input_sum}, Scalar: ${local_scalar}`);
								}
							}
							
							resolve();
						} catch (e) {
							reject(e);
						}
					});
				});
		}
	}
	
	static async D_printPopulation () {
		//Declare local instance variables
		let all_files = await File.getAllFiles(this.cleaned_rasters_folder);
		let world_pop_obj = population_Global.A_getWorldPopulationObject();
		let year_files = [];
		
		//Iterate over all_files and filter GHS_POP rasters
		for (let i = 0; i < all_files.length; i++) {
			let file_name = path.basename(all_files[i]);
			
			if (file_name.startsWith("GHS_POP_") && file_name.endsWith(".png")) {
				let local_year = parseInt(file_name.replace("GHS_POP_", "").replace(".png", ""));
				
				if (!isNaN(local_year))
					year_files.push({
						file_path: all_files[i],
						year: local_year
					});
			}
		}
		
		//Sort in chronological order
		year_files.sort((a, b) => a.year - b.year);
		
		console.log(`- GHSL Population Series Summary:`);
		for (let i = 0; i < year_files.length; i++) {
			let local_entry = year_files[i];
			let local_sum = GeoPNG.getImageSum(local_entry.file_path, { format: "float32" });
			let target_pop = (world_pop_obj && world_pop_obj[local_entry.year]) ? world_pop_obj[local_entry.year] : "N/A";
			
			console.log(` - Year ${local_entry.year}: ${local_sum} (Target: ${target_pop})`);
		}
	}
	
	/**
	 * Adjusts 2020-2025 modern substrata rasters using WorldPop cohorts (2020-2024) and Worldometer country projections (2025).
	 * @alias population_GHSL.E_adjustModernSubstrata
	 * 
	 * @param {Object} [arg0_options]
	 */
	static async E_adjustModernSubstrata (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let script_path = path.join(__dirname, "adjust_modern_substrata_2020_2025.py");
		
		console.log(`- Running modern substrata adjustment (2020-2025) via WorldPop & Worldometer ..`);
		child_process.execSync(`python "${script_path}"`, { stdio: "inherit" });
	}
	
	static async processRasters (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Initialise options
		if (!options.exclude) options.exclude = [];
		
		//Declare local instance variables
		if (!options.exclude.includes("A")) {
			await this.A_convertToPNGs();
			await this.A_fixCorruptPixels();
		}
		
		//1st Pass C: Normalise raw anchor rasters to their real global population totals first
		if (!options.exclude.includes("C"))
			await this.C_scalePNGsToGlobalPopulation();
		
		//Interpolate spatial distribution linearly using the now properly scaled anchors
		if (!options.exclude.includes("B"))
			await this.B_interpolatePNGs();
		
		//2nd Pass C: Re-scale the newly interpolated frames to map them onto the true non-linear exponential population curve
		if (!options.exclude.includes("C"))
			await this.C_scalePNGsToGlobalPopulation();
		
		//Adjust modern substrata for 2020-2025 using empirical WorldPop and Worldometer projections
		if (!options.exclude.includes("E"))
			await this.E_adjustModernSubstrata(options);
		
		if (!options.exclude.includes("D"))
			await this.D_printPopulation();
	}
};
