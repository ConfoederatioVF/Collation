if (!global.ve) global.ve = {};

//Initialise functions
{
	ve.gc = function () { //[WIP] - Heuristic free needs to be better with exception fields (.no_gc)
		if (!ve.registry.debug_profile_components) return; //Internal guard clause if debug_profile_components doesn't exist
		
		//Declare local instance variables
		let heuristic_free_end = ve.registry.debug_heuristic_free_end*1000;
		let heuristic_free_start = ve.registry.debug_heuristic_free_start*1000;
		let start_timestamp = ve.start_timestamp;
		let timestamp = new Date().getTime();
		
		//Iterate over all ve.Component.instances if possible
		for (let i = 0; i < ve.Component.instances.length; i++) {
			let local_component = ve.Component.instances[i].deref();
			
			//Check if timestamp is valid
			if (local_component._timestamp) {
				if (heuristic_free_start === -1 || local_component._timestamp < start_timestamp + heuristic_free_start) continue;
				if (heuristic_free_end === -1 || local_component._timestamp > timestamp - heuristic_free_end) continue;
			}
			if (local_component.owners) continue; //Internal guard clause if component has .owners
			if (local_component.element && local_component.element.isConnected) continue; //Internal guard clause if element is connected
			
			//Remove component
			if (typeof local_component.remove === "function") local_component.remove();
		}
	};
}