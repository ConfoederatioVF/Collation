if (!global.ve) global.ve = {};

//Initialise functions
{
	ve.gc = function () {
		if (!ve.debug_profile_components) return; //Internal guard clause if debug_profile_components doesn't exist
		
		//Declare local instance variables
		let heuristic_free_end = ve.registry.debug_heuristic_free_end;
		let heuristic_free_start = ve.registry.debug_heuristic_free_start;
		let timestamp = new Date().getTime();
		
		//Iterate over all ve.Component.instances if possible
		for (let i = 0; i < ve.Component.instances.length; i++) {
			let local_component = ve.Component.instances[i].deref();
			
		}
	};
}