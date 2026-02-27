//Initialise functions
{
	/**
	 * Represents Ontologies which have been hydrated and streamed-in from a set database.
	 * 
	 * ##### Constructor:
	 * - `arg0_type="Ontology"`: {@link string} - The Ontology subclass/type to reference.
	 * 
	 * @type {Ontology}
	 */
	global.Ontology = class {
		/**
		 * @type {string}
		 */
		static ontology_folder_path = "";
		
		/**
		 * @type {Ontology[]}
		 */
		static queue = [];
		
		constructor (arg0_type, arg1_state_array, arg2_options) {
			//Convert from parameters
			let type = (arg0_type) ? arg0_type : "Ontology";
			let state_array = (arg1_state_array) ? arg1_state_array : [];
			let options = (arg2_options) ? arg2_options : {};
		}
	};
}