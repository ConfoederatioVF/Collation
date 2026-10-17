//Initialise functions
{
	if (!global.population_Global) global.population_Global = {};
	if (!global.JSON5) try { global.JSON5 = require("json5"); } catch (e) {}
	if (!global.cubic_spline) try { global.cubic_spline = require("cubic-spline"); } catch (e) {}
	
	global.population_Global = class {
		static input_global_population_json = `${h1}/population_Global/global_population_estimates.json5`;
		
		static A_getWorldPopulationObject () {
			//Declare local instance variables
			let hyde_years = landuse_HYDE.hyde_years;
			let return_obj = {};
			let world_pop_obj = JSON5.parse(fs.readFileSync(this.input_global_population_json, "utf8"));
			
			//Iterate over all_estimates and geomean them in return_obj
			Object.iterate(world_pop_obj, (local_key, local_value) => {
				Object.iterate(local_value, (local_subkey, local_subvalue) => {
					if (!return_obj[local_subkey]) return_obj[local_subkey] = [];
						return_obj[local_subkey].push(local_subvalue);
				});
			});
			
			//Iterate over all years in return_obj and set them to their weighted geometric mean
			Object.iterate(return_obj, (local_key, local_value) =>
				return_obj[local_key] = Math.weightedGeometricMean(local_value));
			return_obj = Object.cubicSplineInterpolation(return_obj, { years: hyde_years });
			return_obj = Object.multiply(return_obj, 1000000); //Figures are given in millions, so multiply them by a million
			return_obj = Object.operate(return_obj, `Math.round(n)`);
			
			//Return statement
			return Object.sortKeys(return_obj, { type: "ascending" });
		}
	};
}