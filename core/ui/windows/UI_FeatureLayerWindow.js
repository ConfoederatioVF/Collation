global.UI_FeatureLayerWindow = class extends ve.Class {
	constructor (arg0_layer_obj) {
		// Convert from parameters
		let layer_obj = arg0_layer_obj;
		super();
		
		//Declare local instance variables
		this.layer = layer_obj;
	}
	
	/**
	 * Returns an Object<ve.Component> representing the current UI_FeatureLayerWindow
	 * element that can be bound; removes the previous .interface if present.
	 *
	 * @returns {ve.Interface}
	 */
	draw () {
		//Close the current instance
		super.close("instance");
		
		//Declare local instance variables
		let all_geometries = this.layer.getAllGeometries();
		
		this.CRUD = new ve.CRUD(all_geometries, {
			header: ["Type", "Name", "Tags", "Actions"],
			special_function: (local_geometry) => {
				let local_array = [];
				
				//1. Type column
				local_array.push((local_geometry.class_name) ? local_geometry.class_name : "Geometry");
				
				//2. Name column
				let name_component = veText(local_geometry.name, {
					attributes: {
						"data-value": local_geometry.name,
					},
					onprogramchange: (v, e) => {
						e.element.setAttribute("data-value", v);
						e.v = v;
					},
					onuserchange: (v, e) => {
						e.element.setAttribute("data-value", v);
						local_geometry.name = v;
					},
				});
				local_array.push(name_component.element);
				
				//3. Tags column
				let local_geometry_tags = local_geometry?.metadata?.tags;
				local_array.push((Array.isArray(local_geometry_tags)) ? local_geometry_tags.join(", ") : "");
				
				//4. Actions column
				let actions_bar_el = local_geometry.getActionsBarElement();
				let brush_button = veButton((v, e) => {
					if (main.brush.selected_geometry?.id !== e.element.geometry?.id) {
						main.brush.selected_geometry = e.element.geometry;
						local_geometry.selected = true;
						this.CRUD.redrawSelections();
					}
				}, {
					name: "<icon>brush</icon>",
					tooltip: "Move to Brush",
				});
				brush_button.element.geometry = local_geometry;
				actions_bar_el.prepend(brush_button.element);
				
				local_array.push(actions_bar_el);
				
				//Return statement
				return local_array;
			},
			table_options: {
				disable_hide_columns: [0],
				page_size: 10
			},
		});
		
		this.interface = veInterface({ 
			crud: this.CRUD, 
		}, { 
			is_folder: false 
		});
		
		super.open("instance", {
			can_rename: false,
			name: this.layer.name ? this.layer.name : "Layer",
			height: "45rem",
			width: "60rem"
		});
		
		// Return statement
		return this.interface;
	}
};