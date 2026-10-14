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

global.GDP_PPP = class {
	static bf = `${h1}GDP_PPP/`;
	static input_gdp_ppp_national_csv = `${this.bf}gdp_ppp_national_eoscala_1.4.csv`;
	static input_gdp_ppp_world_json = `${this.bf}gdp_ppp_world_eoscala_1.4.json5`;
	static intermediate_normalised_to_global = `${h3}GDP_PPP/1.scaled_to_global/`;
	static intermediate_scaled_to_national = `${h3}GDP_PPP/2.scaled_to_national/`;
	static intermediate_scaled_to_global = `${h3}GDP_PPP/3.scaled_to_global/`;
	
	/**
	 * Fetches a {"<year>": {@link number}} map per geocode for GDP PPP,
	 * incorporating relativistic moving deflator and smooth pre-Maddison upward ramp-up
	 * anchored to regional agricultural/urban emergence keyframes from HYDE (Option B).
	 * 
	 * @returns {Object}
	 */
	static getGDP_PPPObject () {
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
				console.error("[GDP_PPP] Failed loading development index cache:", e);
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
				console.error("[GDP_PPP] Failed loading national populations cache:", e);
			}
		}
		
		let gdp_ppp_csv = File.loadCSVAsJSON(this.input_gdp_ppp_national_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let gdp_ppp_obj = {};
		let gdp_pc_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let raw_maddison_obj = {};
		let world_gdp_obj = this.getWorldGDP_PPPObject();
		let world_avg_pc = {};
		
		for (let i = 0; i < hyde_years.length; i++) {
			let y = hyde_years[i];
			let p = 0;
			if (national_populations[y]) {
				for (let c in national_populations[y]) p += national_populations[y][c];
			}
			world_avg_pc[y] = (p > 0) ? (world_gdp_obj[y] / p) : 0;
		}
		let delong_hg_base = world_avg_pc[-10000];
		
		//Destructure gdp_ppp_csv into raw_maddison_obj
		Object.iterate(gdp_ppp_csv, (local_key, local_value) => {
			Object.iterate(local_value, (local_geocode, local_string) => {
				if (local_string[0] !== "") {
					let local_gdp_ppp = parseFloat(local_string[0]);
					if (!isNaN(local_gdp_ppp)) {
						if (!raw_maddison_obj[local_geocode]) raw_maddison_obj[local_geocode] = {};
						raw_maddison_obj[local_geocode][local_key] = local_gdp_ppp;
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
		
		//Process each geocode with intensive per-capita emergence ramp-up
		Object.iterate(raw_maddison_obj, (code, series) => {
			let extant_years = Object.keys(series).map(Number).sort((a, b) => a - b);
			if (extant_years.length === 0) return;
			
			//Convert extant empirical points into intensive per-capita figures
			let pc_series = {};
			extant_years.forEach((yr) => {
				let pop_yr = national_populations[yr]?.[code] || national_populations[1800]?.[code] || 1000000;
				if (pop_yr > 0) pc_series[yr] = series[yr] / pop_yr;
			});
			
			let t_first = extant_years[0];
			let pc_first = pc_series[t_first] || delong_hg_base;
			
			let dev_entry = dev_index_cache[t_first]?.[code]?.dev_index || 0.0;
			let dev_base = dev_index_cache[-10000]?.[code]?.dev_index || 0.0;
			let dev_range = dev_entry - dev_base;
			
			//Pure linear interpolation from -10000 BC DeLong baseline to t_first empirical entry using development index
			for (let i = 0; i < hyde_years.length; i++) {
				let y = hyde_years[i];
				if (y < t_first) {
					let alpha = 0.0;
					if (dev_range > 0) {
						let dev_y = dev_index_cache[y]?.[code]?.dev_index || 0.0;
						alpha = Math.max(0.0, Math.min(1.0, (dev_y - dev_base) / dev_range));
					}
					pc_series[y] = delong_hg_base + alpha * (pc_first - delong_hg_base);
				}
			}
			
			//Smooth monotonic interpolation across all HYDE years in per-capita space
			let interpolated_pc = Object.cubicSplineInterpolation(pc_series, {
				years: hyde_years
			});
			
			gdp_pc_obj[code] = {};
			gdp_ppp_obj[code] = {};
			
			for (let i = 0; i < hyde_years.length; i++) {
				let y = hyde_years[i];
				let pop_y = national_populations[y]?.[code] || 1;
				let pc_y = interpolated_pc[y] || delong_hg_base;
				
				//Enforce historical sanity bounds on per-capita
				pc_y = Math.max(150, Math.min(pc_y, (y <= 100) ? 2500 : 80000));
				gdp_pc_obj[code][y] = pc_y;
				gdp_ppp_obj[code][y] = pc_y * pop_y;
			}
		});
		
		//Antiquity Italian Supremacy Pass: Roman Italy is #1 in Per-Capita GDP (y <= 100)
		let antiquity_years = [0, 100];
		for (let i = 0; i < antiquity_years.length; i++) {
			let y = antiquity_years[i];
			let ita_pop = national_populations[y]?.ITA || 7000000;
			let ita_gdp = (y === 0) ? (raw_maddison_obj.ITA?.[0] || 8947632995) : 9600000000;
			let ita_pc = ita_gdp / ita_pop;
			
			if (gdp_ppp_obj.ITA) gdp_ppp_obj.ITA[y] = ita_gdp;
			if (gdp_pc_obj.ITA) gdp_pc_obj.ITA[y] = ita_pc;
			
			Object.keys(gdp_ppp_obj).forEach((c) => {
				if (c !== "ITA") {
					let pop_c = national_populations[y]?.[c] || 1;
					if (gdp_pc_obj[c][y] > ita_pc * 0.85) {
						gdp_pc_obj[c][y] = ita_pc * 0.85;
						gdp_ppp_obj[c][y] = gdp_pc_obj[c][y] * pop_c;
					}
				}
			});
		}
		
		//Return statement
		return gdp_ppp_obj;
	}
	
	/**
	 * Returns estimations of World GDP PPP as an object map from DeLong's ex-Nordhaus series (gdp_ppp_world_eoscala_1.4.json5).
	 * 
	 * @returns {Object}
	 */
	static getWorldGDP_PPPObject () {
		//Declare local instance variables
		let gdp_ppp_obj = {};
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let raw_gdp_ppp_obj = JSON5.parse(fs.readFileSync(this.input_gdp_ppp_world_json));
		
		//Iterate over raw_gdp_ppp_obj; populate raw figures
		Object.iterate(raw_gdp_ppp_obj, (local_key, local_value) => {
			Object.iterate(local_value.gdp_ppp, (local_subkey, local_subvalue) => {
				let local_scalar = Math.returnSafeNumber(local_value?.scalar, 1);
				let local_gdp_ppp = local_subvalue*local_scalar;
				
				if (!gdp_ppp_obj[local_subkey]) {
					gdp_ppp_obj[local_subkey] = [local_gdp_ppp];
				} else {
					gdp_ppp_obj[local_subkey].push(local_gdp_ppp);
				}
			});
		});
		Object.iterate(gdp_ppp_obj, (local_key, local_value) =>
			gdp_ppp_obj[local_key] = Math.weightedGeometricMean(local_value));
		
		//Return statement
		return Object.cubicSplineInterpolation(gdp_ppp_obj, { years: hyde_years });
	}
	
	static async A_scaleGDP_PPPRastersToNational (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Declare local instance variables
		let geocode_obj = admin_modern.getISO3ColourcodesObject();
		let geocodes_raster_path = admin_modern.input_geocodes_raster;
		let gdp_ppp_obj = this.getGDP_PPPObject();
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(this.intermediate_scaled_to_national) : this.intermediate_scaled_to_national;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${this.intermediate_normalised_to_global}GDP_PPP_${hyde_years[i]}.png`;
			let local_output_path = `${this.intermediate_scaled_to_national}GDP_PPP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_PPP Scale to National",
			task_generator: (year) => {
				let target_gdp_map = {};
				let all_codes = Object.keys(gdp_ppp_obj);
				for (let x = 0; x < all_codes.length; x++) {
					let code = all_codes[x];
					let val = gdp_ppp_obj[code]?.[year];
					if (val !== undefined) target_gdp_map[code] = val;
				}
				
				return {
					format: "float32",
					geocode_map: geocode_obj,
					geocodes_raster_path: geocodes_raster_path,
					input_path: `${this.intermediate_normalised_to_global}GDP_PPP_${year}.png`,
					output_path: `${this.intermediate_scaled_to_national}GDP_PPP_${year}.png`,
					target_gdp_map: target_gdp_map,
					type: "scale_to_national"
				};
			},
			handler: async (year) => {
				let geocode_raster = GeoPNG.loadImage(geocodes_raster_path);
				let local_ols_file_path = `${this.intermediate_normalised_to_global}GDP_PPP_${year}.png`;
				let local_output_file = `${this.intermediate_scaled_to_national}GDP_PPP_${year}.png`;
				let local_gdp_ppp_scalars = {};
				let local_gdp_ppp_sums = {};
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
								Object.modifyValue(local_gdp_ppp_sums, local_geocodes[x], local_value);
					}
				});
				
				Object.iterate(local_gdp_ppp_sums, (local_key, local_value) => {
					let local_actual_gdp_ppp = gdp_ppp_obj[local_key]?.[year];
					local_gdp_ppp_scalars[local_key] = (local_actual_gdp_ppp && local_value > 0) ? local_actual_gdp_ppp/local_value : 1;
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
								let local_gdp_ppp = gdp_ppp_obj[local_geocodes[x]]?.[year];
								if (local_gdp_ppp)
									return local_value*local_gdp_ppp_scalars[local_geocodes[x]];
							}
						return local_value;
					}
				});
			}
		});
	}
	
	static async B_scaleGDP_PPPRastersToGlobal (arg0_input_folder, arg1_output_folder, arg2_options) {
		//Convert from parameters
		let input_folder = arg0_input_folder;
		let output_folder = arg1_output_folder;
		let options = (arg2_options) ? arg2_options : {};
		
		//Declare local instance variables
		let hyde_years = landuse_HYDE.sorted_hyde_years;
		let out_dir = (typeof path !== "undefined") ? path.resolve(output_folder) : output_folder;
		let overwrite = (options.overwrite !== undefined) ? options.overwrite : true;
		let target_years = [];
		let world_gdp_ppp_obj = this.getWorldGDP_PPPObject();
		
		if (!fs.existsSync(out_dir)) fs.mkdirSync(out_dir, { recursive: true });
		
		for (let i = 0; i < hyde_years.length; i++) {
			let local_input_path = `${input_folder}GDP_PPP_${hyde_years[i]}.png`;
			let local_output_path = `${output_folder}GDP_PPP_${hyde_years[i]}.png`;
			
			if (fs.existsSync(local_input_path) && (overwrite || !fs.existsSync(local_output_path)))
				target_years.push(hyde_years[i]);
		}
		
		if (target_years.length === 0) return [];
		
		//Return statement
		return GeoPNG.processTimeseriesParallel({
			concurrency: options.concurrency || 8,
			items: target_years,
			name: "GDP_PPP Scale to Global",
			task_generator: (year) => ({
				format: "float32",
				input_path: `${input_folder}GDP_PPP_${year}.png`,
				output_path: `${output_folder}GDP_PPP_${year}.png`,
				target: world_gdp_ppp_obj[year],
				type: "scale_to_global"
			}),
			handler: async (year) => {
				let local_input_path = `${input_folder}GDP_PPP_${year}.png`;
				let local_output_path = `${output_folder}GDP_PPP_${year}.png`;
				let local_target = world_gdp_ppp_obj[year];
				
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
	
	static async processRasters (arg0_options) {
		//Return statement; Delegate to unified GDP_PPP_pc pipeline
		if (global.GDP_PPP_pc) return GDP_PPP_pc.processRasters(arg0_options);
	}
};