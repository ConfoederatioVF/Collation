//Initialise functions
{
	if (!global.String) global.String = {};
	
	/**
	 * 
	 * @param {string} arg0_string - The original line to edit.
	 * @param {string} arg1_string - The line to add to the original.
	 * @param {Object} [arg2_options]
	 *  @param {boolean} [arg2_options.avoid_duplicates=true]
	 *  @param {boolean} [arg2_options.case_sensitive=false]
	 *  @param {string} [arg2_options.insert_at="append"] - Either 'append'/'prepend'.
	 *  @param {boolean} [arg2_options.insert_newline=true]
	 *  @param {string} [arg2_options.newline_character="<br>"]
	 *  @param {string} [arg2_options.search="substring"] - Either 'substring'/'whole_line'.
	 */
	String.editAddToString = function (arg0_string, arg1_string, arg2_options) {
		//Convert from parameters
		let string = (arg0_string) ? arg0_string : "";
		let ot_string = (arg1_string) ? arg1_string : "";
		let options = (arg2_options) ? arg2_options : {};
		
		//Initialise options
		if (options.avoid_duplicates === undefined) options.avoid_duplicates = true;
		if (options.case_sensitive === undefined) options.case_sensitive = false;
		if (options.insert_at === undefined) options.insert_at = "append";
		if (options.insert_newline === undefined) options.insert_newline = true;
		if (options.newline_character === undefined) options.newline_character = "<br>";
		if (options.search === undefined) options.search = "substring";
		
		//Declare local instance variables
		let do_not_insert = false;
		let newline = (options.insert_newline) ? options.newline_character : "";
		
		if (options.avoid_duplicates)
			if (options.search === "substring") {
				if (options.case_sensitive) {
					if (string.includes(ot_string)) do_not_insert = true;
				} else {
					if (string.trim().toLowerCase().includes(ot_string.trim().toLowerCase())) 
						do_not_insert = true;
				}
			} else if (options.search === "whole_line") {
				let all_lines = string.split(options.newline_character);
				
				for (let i = 0; i < all_lines.length; i++) {
					if (options.case_sensitive) {
						if (all_lines[i].trim() === ot_string.trim())
							do_not_insert = true;
					} else {
						if (String.equalsIgnoreCase(all_lines[i], ot_string, { trim: true }))
							do_not_insert = true;
					}
					if (do_not_insert) break;
				}
			}
		
		//Mutate string if do_not_insert check is false
		if (!do_not_insert) {
			if (options.insert_at === "append") string += `${newline}${ot_string}`;
			if (options.insert_at === "prepend") string = `${ot_string}${newline}${string}`;
		}
		
		//Return statement
		return string;
	};
}