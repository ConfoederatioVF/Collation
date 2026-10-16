if (typeof fs === "undefined" && typeof require !== "undefined") {
	try { global.fs = require("fs"); } catch (e) {}
}
if (typeof path === "undefined" && typeof require !== "undefined") {
	try { global.path = require("path"); } catch (e) {}
}
if (typeof JSON5 === "undefined" && typeof require !== "undefined") {
	try { global.JSON5 = require("json5"); } catch (e) {}
}
if (typeof cubic_spline === "undefined" && typeof require !== "undefined") {
	try { global.cubic_spline = require("cubic-spline"); } catch (e) {}
}

global.GDP_nominal = class {
	static input_gdp_national_csv = `${h1}/GDP_nominal/gdp_national_eoscala_1.4.csv`;
	static input_gdp_world_json = `${h1}/GDP_nominal/gdp_world_eoscala_1.4.json5`;
	static get intermediate_scaled_to_national () {
		return (global.GDP_pc) ? GDP_pc.intermediate_gdp_scaled_to_national : `${h3}GDP_pc/5.scaled_to_national/`;
	}
	
	/**
	 * Returns estimations of World GDP nominal per capita from DeLong's ex-Nordhaus series.
	 * Dynamically converted to nominal using the moving world GDP deflator (nominal / PPP).
	 * 
	 * @returns {Object}
	 */
	static getDelongBaselineObject () {
		//Declare local instance variables
		let delong_series = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		if (typeof GDP_PPP === "undefined" && typeof require !== "undefined") {
			try {
				let gdp_ppp_path = (global.h3) ?
					path.join(global.h3, "GDP_PPP/GDP_PPP.js") :
					path.join((typeof root_dir !== "undefined") ? root_dir : ".", "histmap/3.data_transform/GDP_PPP/GDP_PPP.js");
				require(gdp_ppp_path);
			} catch (e) {}
		}
		let ppp_baseline_obj = (typeof GDP_PPP !== "undefined" && GDP_PPP.getDelongBaselineObject) ?
			GDP_PPP.getDelongBaselineObject() : {};
		let world_nominal_obj = this.getWorldGDPObject();
		let world_ppp_obj = (typeof GDP_PPP !== "undefined" && GDP_PPP.getWorldGDP_PPPObject) ?
			GDP_PPP.getWorldGDP_PPPObject() : {};
		
		for (let i = 0; i < hyde_years.length; i++) {
			let y = hyde_years[i];
			let deflator = (world_ppp_obj[y] && world_ppp_obj[y] > 0 && world_nominal_obj[y]) ?
				(world_nominal_obj[y] / world_ppp_obj[y]) : 1;
			let ppp_base = ppp_baseline_obj[y];
			if (ppp_base !== undefined)
				delong_series[y] = ppp_base * deflator;
		}
		
		//Return statement
		return delong_series;
	}
	
	/**
	 * Returns estimations of World GDP nominal baseline per capita from DeLong's ex-Nordhaus series.
	 * 
	 * @returns {Object}
	 */
	static getDelongSubsistenceBaselineObject () {
		//Return statement
		return this.getDelongBaselineObject();
	}
	
	/**
	 * Returns the De Long nominal subsistence baseline per capita for a given year.
	 * 
	 * @param {number|string} [arg0_year=-10000]
	 * @returns {number}
	 */
	static getDelongSubsistenceBaseline (arg0_year) {
		//Return statement
		return this.getDelongBaseline(arg0_year);
	}
	
	/**
	 * Returns the De Long world average baseline per capita for a given year (defaults to -10000 BC).
	 * 
	 * @param {number|string} [arg0_year=-10000]
	 * @returns {number}
	 */
	static getDelongBaseline (arg0_year) {
		//Convert from parameters
		let year = (arg0_year !== undefined) ? parseInt(arg0_year) : -10000;
		
		//Declare local instance variables
		let b_obj = this.getDelongBaselineObject();
		
		//Return statement
		return (b_obj[year] !== undefined) ? b_obj[year] : b_obj[-10000];
	}
	
	/**
	 * Fetches a {"<year>": {@link number}} map per geocode for GDP nominal,
	 * incorporating relativistic moving deflator and smooth pre-Maddison upward ramp-up
	 * @returns {Object}
	 */
	static getGDPObject () {
		//Declare local instance variables
		let dev_index_file = path.join(
			(typeof root_dir !== "undefined") ? root_dir : ".",
			"histmap/2.data_cleaning/population_Stadester/stadester_national_development_index.json"
		);
		let dev_index_cache = {};
		if (fs.existsSync(dev_index_file)) {
			try {
				dev_index_cache = JSON.parse(fs.readFileSync(dev_index_file, "utf8"));
			} catch (e) {
				console.error("[GDP_nominal] Failed loading development index cache:", e);
			}
		}
		
		let national_pop_file = path.join(
			(typeof root_dir !== "undefined") ? root_dir : ".",
			"histmap/2.data_cleaning/population_Stadester/stadester_national_populations.json"
		);
		let national_populations = {};
		if (fs.existsSync(national_pop_file)) {
			try {
				national_populations = JSON.parse(fs.readFileSync(national_pop_file, "utf8"));
			} catch (e) {
				console.error("[GDP_nominal] Failed loading national populations cache:", e);
			}
		}
		
		let gdp_csv = File.loadCSVAsJSON(this.input_gdp_national_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let gdp_obj = {};
		let gdp_pc_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let raw_maddison_obj = {};
		let world_gdp_obj = this.getWorldGDPObject();
		let world_avg_pc = {};
		
		for (let i = 0; i < hyde_years.length; i++) {
			let y = hyde_years[i];
			let p = 0;
			if (national_populations[y]) {
				for (let c in national_populations[y]) p += national_populations[y][c];
			}
			world_avg_pc[y] = (p > 0) ? (world_gdp_obj[y] / p) : 0;
		}
		let delong_baseline_obj = this.getDelongBaselineObject();
		let delong_hg_base = delong_baseline_obj[-10000];
		let delong_subsistence_obj = this.getDelongSubsistenceBaselineObject();
		let delong_sub_base = delong_subsistence_obj[-10000];
		
		//Destructure gdp_csv into raw_maddison_obj
		Object.iterate(gdp_csv, (local_key, local_value) => {
			Object.iterate(local_value, (local_geocode, local_string) => {
				if (local_string[0] !== "") {
					let local_gdp = parseFloat(local_string[0]);
					if (!isNaN(local_gdp)) {
						if (!raw_maddison_obj[local_geocode]) raw_maddison_obj[local_geocode] = {};
						raw_maddison_obj[local_geocode][local_key] = local_gdp;
					}
				}
			});
		});
		
		//Map Year 1 empirical entries to Year 0 (HYDE keyframe for 1 AD) and delete key 1
		Object.iterate(raw_maddison_obj, (code, series) => {
			if (series[1] !== undefined) {
				if (series[0] === undefined) series[0] = series[1];
				delete series[1];
			}
		});
		
		//Helper to interpolate national population for any arbitrary year from empirical HYDE timeseries
		let getNationalPopulation = (code, year) => {
			if (national_populations[year]?.[code] > 0) return national_populations[year][code];
			let next_y = null;
			let prev_y = null;
			for (let i = 0; i < hyde_years.length; i++) {
				let hy = hyde_years[i];
				if (national_populations[hy]?.[code] > 0) {
					if (hy <= year) prev_y = hy;
					if (hy >= year && next_y === null) next_y = hy;
				}
			}
			if (prev_y !== null && next_y !== null && prev_y !== next_y) {
				let p0 = national_populations[prev_y][code];
				let p1 = national_populations[next_y][code];
				let fraction = (year - prev_y) / (next_y - prev_y);
				return p0 + fraction * (p1 - p0);
			}
			if (prev_y !== null) return national_populations[prev_y][code];
			if (next_y !== null) return national_populations[next_y][code];
			return 0;
		};
		
		//Process each geocode with intensive per-capita emergence ramp-up
		Object.iterate(raw_maddison_obj, (code, series) => {
			let extant_years = Object.keys(series).map(Number).sort((a, b) => a - b);
			if (extant_years.length === 0) return;
			
			//Convert extant empirical points into intensive per-capita figures
			let pc_series = {};
			extant_years.forEach((yr) => {
				let pop_yr = getNationalPopulation(code, yr);
				if (pop_yr > 0) pc_series[yr] = series[yr] / pop_yr;
			});
			
			let valid_entry_years = Object.keys(pc_series).map(Number).sort((a, b) => a - b);
			if (valid_entry_years.length === 0) return;
			
			let t_first = valid_entry_years[0];
			
			//Pre-entry trajectory: 100% empirical baseline modulated by national development index
			for (let i = 0; i < hyde_years.length; i++) {
				let y = hyde_years[i];
				if (y < t_first) {
					let base_y = delong_baseline_obj[y] || delong_hg_base;
					let sub_y = delong_subsistence_obj[y] || delong_sub_base;
					let d_y = dev_index_cache[y]?.[code]?.dev_index || (delong_hg_base / base_y);
					let target_pc = base_y * d_y;
					pc_series[y] = Math.max(delong_hg_base, target_pc);
				}
			}
			
			//Smooth monotonic interpolation across all HYDE years in per-capita space
			let interpolated_pc = Object.cubicSplineInterpolation(pc_series, {
				years: hyde_years
			});
			
			gdp_pc_obj[code] = {};
			gdp_obj[code] = {};
			
			for (let i = 0; i < hyde_years.length; i++) {
				let y = hyde_years[i];
				let pop_y = national_populations[y]?.[code] || 0;
				let pc_y = Math.max(delong_hg_base, interpolated_pc[y] || delong_hg_base);
				
				gdp_pc_obj[code][y] = pc_y;
				gdp_obj[code][y] = pc_y * pop_y;
			}
		});
		
		//Return statement
		return gdp_obj;
	}
	
	/**
	 * Returns estimations of World GDP nominal as an object map from DeLong's ex-Nordhaus series (gdp_world_eoscala_1.4.json5).
	 *
	 * @returns {Object}
	 */
	static getWorldGDPObject () {
		//Declare local instance variables
		let gdp_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let raw_gdp_obj = JSON5.parse(fs.readFileSync(this.input_gdp_world_json));
		
		//Iterate over raw_gdp_obj; populate raw figures
		Object.iterate(raw_gdp_obj, (local_key, local_value) => {
			if (local_value?.gdp)
				Object.iterate(local_value.gdp, (local_subkey, local_subvalue) => {
					let local_scalar = Math.returnSafeNumber(local_value?.scalar, 1);
					let local_gdp = local_subvalue*local_scalar;
					
					if (!gdp_obj[local_subkey]) {
						gdp_obj[local_subkey] = [local_gdp];
					} else {
						gdp_obj[local_subkey].push(local_gdp);
					}
				});
		});
		Object.iterate(gdp_obj, (local_key, local_value) => 
			gdp_obj[local_key] = Math.weightedGeometricMean(local_value));
		
		//Return statement
		return Object.cubicSplineInterpolation(gdp_obj, { years: hyde_years });
	}
	
	static async A_scaleGDPRastersToGlobal (arg0_input_folder, arg1_output_folder, arg2_options) {
		//Convert from parameters
		let input_folder = arg0_input_folder;
		let output_folder = arg1_output_folder;
		let options = (arg2_options) ? arg2_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(output_folder) : output_folder;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		let world_gdp_obj = this.getWorldGDPObject();
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${input_folder}GDP_${hyde_years[i]}.png`;
			let local_output_path = `${output_folder}GDP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_nominal Scale to Global",
			task_generator: (year) => ({
				format: "float32",
				input_path: `${input_folder}GDP_${year}.png`,
				output_path: `${output_folder}GDP_${year}.png`,
				target: world_gdp_obj[year],
				type: "scale_to_global"
			}),
			handler: async (year) => {
				let local_input_path = `${input_folder}GDP_${year}.png`;
				let local_output_path = `${output_folder}GDP_${year}.png`;
				let local_target = world_gdp_obj[year];
				
				let local_input_png = GeoPNG.loadNumberRasterImage(local_input_path, { format: "float32" });
				let local_input_sum = GeoPNG.getImageSum(local_input_path, { format: "float32" });
				let local_scalar = (local_input_sum > 0) ? local_target/local_input_sum : 1;
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_path,
					format: "float32",
					width: 4320,
					height: 2160,
					function: (local_index) => local_input_png.data[local_index]*local_scalar
				});
			}
		});
	}
	
	static async B_scaleGDPRastersToNational (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocodes_raster_path = admin_modern.input_geocodes_raster;
		let gdp_obj = this.getGDPObject();
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_scaled_to_national) : this.intermediate_scaled_to_national;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${this.intermediate_normalised_to_global}GDP_${hyde_years[i]}.png`;
			let local_output_path = `${this.intermediate_scaled_to_national}GDP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_nominal Scale to National",
			task_generator: (year) => {
				let target_gdp_map = {};
				let all_codes = Object.keys(gdp_obj);
				for (let x = 0; x < all_codes.length; x++) {
					let code = all_codes[x];
					let val = gdp_obj[code]?.[year];
					if (val !== undefined) target_gdp_map[code] = val;
				}
				
				return {
					format: "float32",
					geocode_map: geocode_obj,
					geocodes_raster_path: geocodes_raster_path,
					input_path: `${this.intermediate_normalised_to_global}GDP_${year}.png`,
					output_path: `${this.intermediate_scaled_to_national}GDP_${year}.png`,
					target_gdp_map: target_gdp_map,
					type: "scale_to_national"
				};
			},
			handler: async (year) => {
				let geocode_raster = GeoPNG.loadImage(geocodes_raster_path);
				let local_ols_file_path = `${this.intermediate_normalised_to_global}GDP_${year}.png`;
				let local_output_file = `${this.intermediate_scaled_to_national}GDP_${year}.png`;
				let local_gdp_scalars = {};
				let local_gdp_sums = {};
				let local_ols_raster = GeoPNG.loadNumberRasterImage(local_ols_file_path, { format: "float32" });
				
				GeoPNG.operateNumberRasterImage({
					file_path: local_ols_file_path,
					format: "float32",
					function: (local_index, local_value) => {
						let local_colour_key = [
							geocode_raster.data[local_index],
							geocode_raster.data[local_index + 1],
							geocode_raster.data[local_index + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						
						if (local_geocodes)
							for (let x = 0; x < local_geocodes.length; x++)
								Object.modifyValue(local_gdp_sums, local_geocodes[x], local_value);
					}
				});
				
				Object.iterate(local_gdp_sums, (local_key, local_value) => {
					let local_actual_gdp = gdp_obj[local_key]?.[year];
					local_gdp_scalars[local_key] = (local_actual_gdp && local_value > 0) ? local_actual_gdp/local_value : 1;
				});
				
				GeoPNG.saveNumberRasterImage({
					file_path: local_output_file,
					format: "float32",
					height: 2160,
					width: 4320,
					function: (local_index) => {
						let byte_index = local_index*4;
						let local_colour_key = [
							geocode_raster.data[byte_index], 
							geocode_raster.data[byte_index + 1],
							geocode_raster.data[byte_index + 2]
						].join(",");
						let local_geocodes = geocode_obj[local_colour_key];
						let local_value = local_ols_raster.data[local_index];
						
						if (local_geocodes)
							for (let x = 0; x < local_geocodes.length; x++) {
								let local_gdp = gdp_obj[local_geocodes[x]]?.[year];
								let local_scalar = local_gdp_scalars[local_geocodes[x]];
								if (local_gdp && isFinite(local_scalar))
									return local_value*local_scalar;
							}
						return local_value;
					}
				});
			}
		});
	}
	
	static async processRasters (arg0_options) {
		//Return statement; Delegate to unified GDP_pc pipeline
		if (global.GDP_pc) return GDP_pc.processRasters(arg0_options);
	}
};