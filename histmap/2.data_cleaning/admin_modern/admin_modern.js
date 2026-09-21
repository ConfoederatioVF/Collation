global.admin_modern = class {
	static bf = `${h1}/admin_modern/`;
	static input_hmd_csv = `${this.bf}hmd_geocodes.csv`;
	static input_hmd_raster = `${this.bf}hmd.png`;
	static input_geocodes_csv = `${this.bf}geocodes.csv`;
	static input_geocodes_raster = `${this.bf}geocodes.png`;
	static input_iso2_geocodes_csv = `${this.bf}iso2_geocodes.csv`;
	static input_iso2_geocodes_raster = `${this.bf}iso2.png`;
	static input_iso3_ilo_geocodes_csv = `${this.bf}iso3_ilo_geocodes.csv`;
	static input_regional_geocodes_csv = `${this.bf}iso2_regions.csv`;
	
	static getILOColourcodesObject () {
		//Declare local instance variables
		let geocodes_csv = File.loadCSVAsJSON(admin_modern.input_iso3_ilo_geocodes_csv, {
			delimiter: ",",
			mode: "vertical"
		});
		let iso3_colourcodes_obj = this.getISO3ColourcodesObject();
		let ref_area_labels_obj = {};
		let return_obj = {};
		
		//.ref_area for geocodes_csv is ISO3; populate ref_area_labels_obj with a lookup of ref_area: ref_area.label
		Object.iterate(geocodes_csv, (local_key, local_value) => {
			let local_ref_area = local_value["ref_area"][0];
			
			if (!ref_area_labels_obj[local_ref_area])
				ref_area_labels_obj[local_ref_area] = local_value["ref_area.label"][0];
		});
		
		//Iterate over iso3_colourcodes_obj to populate return_obj with ref_area labels
		Object.iterate(iso3_colourcodes_obj, (local_key, local_value) => {
			return_obj[local_key] = [];
			
			//Iterate over all local_value geocodes, mapping ISO3 to ref_area.label
			for (let i = 0; i < local_value.length; i++)
				if (ref_area_labels_obj[local_value[i]])
					return_obj[local_key].push(ref_area_labels_obj[local_value[i]]);
		});
		
		//Return statement
		return return_obj;
	}
	
	/**
	 * Returns a map of <r,g,b,a>: {@link Array}<{@link string}> - Ordered in terms of precedence; latter indices are fallbacks.
	 *
	 * @returns {Object}
	 */
	static getISO2ColourcodesObject () {
		//Declare local instance variables
		let colourcodes_obj = {};
		let geocodes_csv = File.loadCSVAsJSON(admin_modern.input_iso2_geocodes_csv, {
			delimiter: ";",
			mode: "vertical"
		});
		
		//Iterate over geocodes_csv to populate colourcodes_obj with original 'Colour'
		Object.iterate(geocodes_csv, (local_key, local_value) => {
			if (local_value["Colour"][0] !== "")
				colourcodes_obj[local_value["Colour"][0]] = (!local_key.startsWith("P.")) ? [local_key] : [];
		});
		
		//Iterate over geocodes_csv to populate colourcodes_obj with 'Other Geocodes'
		Object.iterate(geocodes_csv, (local_key, local_value) => {
			if (local_value["Other Geocodes"][0] !== "") {
				let other_geocodes = local_value["Other Geocodes"][0].split(",");
				
				//Iterate over all other_geocodes
				for (let i = 0; i < other_geocodes.length; i++) {
					let local_colour = geocodes_csv[other_geocodes[i]]["Colour"][0];
					
					colourcodes_obj[local_colour].push(local_key);
				}
			}
		});
		
		//Return statement
		return colourcodes_obj;
	}
	
	/**
	 * Returns a map of <r,g,b,a>: {@link Array}<{@link string}> - Ordered in terms of precedence; latter indices are fallbacks.
	 *
	 * @returns {Object}
	 */
	static getISO3ColourcodesObject () {
		//Declare local instance variables
		let colourcodes_obj = {};
		let geocodes_csv = File.loadCSVAsJSON(admin_modern.input_geocodes_csv, {
			delimiter: ";",
			mode: "vertical"
		});
		
		//Iterate over geocodes_csv to populate colourcodes_obj with original 'Colour'
		Object.iterate(geocodes_csv, (local_key, local_value) => {
			if (local_value["Colour"][0] !== "")
				colourcodes_obj[local_value["Colour"][0]] = [local_key];
		});
		
		//Iterate over geocodes_csv to populate colourcodes_obj with 'Current Geocodes'
		Object.iterate(geocodes_csv, (local_key, local_value) => {
			if (local_value["Current Geocodes"][0] !== "") {
				let local_geocodes = local_value["Current Geocodes"][0].split(",");
				
				//Iterate over all local_geocodes
				for (let i = 0; i < local_geocodes.length; i++) {
					let local_colour = geocodes_csv[local_geocodes[i]]["Colour"][0];
					
					colourcodes_obj[local_colour].push(local_key);
				}
			}
		});
		
		//Return statement
		return colourcodes_obj;
	}
	
	/**
	 * Returns a map of <geocode>: {@link Object}
	 * - `.colours`: {@link Array}<{@link string}> - RGB codes per geocode.
	 * - `.domain`: {@link Array}<{@link number}, {@link number}> - If defined, these colourcodes are selected for the target year.
	 * - `.name`: {@link string}
	 */
	static getHMDColourcodesObject () {
		//Declare local instance variables
		let csv_array = File.loadCSVAsArray(this.input_hmd_csv, { delimiter: ";" });
		let last_year = landuse_HYDE.sorted_hyde_years[landuse_HYDE.sorted_hyde_years.length - 1];
		let return_obj = {};
		
		//Iterate over csv_array
		for (let i = 0; i < csv_array.length; i++) {
			let local_domain;
			let local_geocode = csv_array[i]["HMD Geocode"];
			if (local_geocode.includes(".")) {
				let split_geocode = local_geocode.split(".");
				
				let domain = split_geocode[1].split("-").map(Number);
				if (domain.length === 2) {
					if (domain[1] < domain[0]) {
						local_domain = [domain[0], last_year];
					} else {
						local_domain = [domain[0], domain[1]];
					}
				} else if (domain.length === 1) {
					local_domain = [domain[0], domain[0]];
				}
			}
			
			return_obj[csv_array[i]["HMD Geocode"]] = {
				colours: csv_array[i]["Colour"].split(";"),
				name: csv_array[i]["Name"]
			};
			let local_obj = return_obj[csv_array[i]["HMD Geocode"]];
				if (local_domain) local_obj.domain = local_domain;
		}
		
		//Return statement
		return return_obj;
	}
	
	/**
	 * Returns a map of <r,g,b,a>: Array<string>
	 * Inherits ISO2 base mappings and appends regional fallbacks by looking up which colours
	 * represent the member countries (and their sub-entities like Prussia or States).
	 *
	 * @returns {Object}
	 */
	static getWIDColourcodesObject () {
		//Fetch the base ISO2 mapping to ensure we have all sub-national colours (Prussia, US States)
		let colourcodes_obj = admin_modern.getISO2ColourcodesObject();
		
		//Load the regional CSV which contains aggregate definitions
		let regional_csv = File.loadCSVAsJSON(admin_modern.input_regional_geocodes_csv, {
			delimiter: ";",
			mode: "vertical"
		});
		
		//Iterate over each regional aggregate (e.g., QE-MER, XL-MER)
		Object.iterate(regional_csv, (regional_key, local_value) => {
			let member_geocodes_str = local_value["Other Geocodes"][0];
			
			if (member_geocodes_str !== "") {
				let members_list = member_geocodes_str.split(",");
				
				//For every color in our base map, check if any of the geocodes in its array 
				//are members of the current region.
				Object.iterate(colourcodes_obj, (pixel_colour, geocode_array) => {
					let is_member = false;
					
					//Check if the primary geocode or its fallbacks (like 'DE' for 'DD') match
					for (let i = 0; i < members_list.length; i++) {
						let check_code = members_list[i].trim();
						if (geocode_array.includes(check_code)) {
							is_member = true;
							break;
						}
					}
					
					//If this colour represents a member of the region, push the region as a fallback
					if (is_member && !geocode_array.includes(regional_key)) {
						geocode_array.push(regional_key);
					}
				});
			}
		});
		
		return colourcodes_obj;
	}
};