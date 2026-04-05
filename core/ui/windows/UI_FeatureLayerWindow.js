global.UI_FeatureLayerWindow = class extends ve.Class { //[WIP] - Finish class body
	constructor (arg0_layer_obj) {
		//Convert from parameters
		let layer_obj = arg0_layer_obj;
			super();
			
		//Declare local instance variables
		this.layer = layer_obj;
			
		//Draw interface
	}
	
	filterGeometryTable (arg0_options) {
		
	}
	
	getGeometryTable () {
		//Declare local instance variables
		let table_array = []; //[[select_button, index, geometry_type, geometry_name, actions_bar]];
		
		//Populate table_array from entities in this.layer
		let all_entities = this.layer.getAllGeometries();
		
		//Initalise heeader
		table_array.push(["Selected", "Index", "Type", "Name", "Actions"]);
		
		//Iterate over all_entities and push it to table_array
		for (let i = 0; i < all_entities.length; i++) {
			let local_array = [];
			let local_geometry = all_entities[i];
			let local_geometry_name = local_geometry.name;
				if (!local_geometry_name)
					if (local_geometry.class_name) {
						local_geometry_name = local_geometry.class_name;
					} else {
						local_geometry_name = `Geometry`;
					}
			
			//Set local_array
			local_array[0] = veCheckbox().element;
			local_array[1] = i;
			local_array[2] = (local_geometry.class_name) ? local_geometry.class_name : "Geometry";
			local_array[3] = local_geometry_name;
			local_array[4] = local_geometry.getActionsBarElement();
			
			//Push local_array to table_array
			table_array.push(local_array);
		}
		
		//Return statement
		return table_array;
	}
}