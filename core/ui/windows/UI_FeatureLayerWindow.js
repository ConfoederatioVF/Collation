global.UI_FeatureLayerWindow = class extends ve.Class { //[WIP] - Finish class body
	constructor (arg0_layer_obj) {
		//Convert from parameters
		let layer_obj = arg0_layer_obj;
			super();
			
		//Declare local instance variables
		this.layer = layer_obj;
	}

  /**
   * Returns an {@link Object}<{@link ve.Component}> representing the current UI_FeatureLayerWIndow element that can be bound; removes the previous `.interface` if present.
	 * 
	 * @returns {ve.Interface}
   */
  draw () {
    super.close("instance");
    if (this.interface) this.interface.remove();

    //Declare local instance variables
    let geometry_table_array = this.getGeometryTable({ view_tags: true });

    this.interface = veInterface({
      geometry_table: veTable(geometry_table_array, {
        onrowclick: (v, e) => console.log(v, e)
      })
    }, { is_folder: false });

    super.open("instance", { 
      can_rename: false, //[WIP] - Should be able to rename layers from here in future
      name: (this.layer.name) ? this.layer.name : "Layer" 
    });

    //Return statement
    return this.interface;
  }
	
	filterGeometryTable (arg0_options) {
		
	}
	
  /**
   * Returns a {@link naissance.Geometry} Table array that can be passed to {@link ve.Table}.
   * - Method of: {@link UI_FeatureLayerWindow}
   * 
   * @param {Object} [arg0_options]
   *  @param {boolean} [arg0_options.view_tags=false]
   */
	getGeometryTable (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};

		//Declare local instance variables
		let table_array = []; //[[select_button, index, geometry_type, geometry_name, actions_bar]];
		
		//Populate table_array from entities in this.layer
		let all_entities = this.layer.getAllGeometries();
		
		//Initalise heeader
    if (!options.view_tags) {
		  table_array.push(["Selected", "Index", "Type", "Name", "Actions"]);
    } else {
      table_array.push(["Selected", "Index", "Type", "Name", "Tags", "Actions"]);
    }
		
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
      //Select column
      {
        let select_component = veCheckbox(local_geometry.selected, { //[WIP] - onprogramchange doesn't fire, no binding
          attributes: {
            "data-value": String(local_geometry.selected)
          },
          onuserchange: (v, e) => {
            e.element.setAttribute("data-value", String(v));
            local_geometry.selected = v;
          }
        });

			  local_array.push(select_component.element);
      }
			local_array.push(i);
			local_array.push((local_geometry.class_name) ? local_geometry.class_name : "Geometry");
      //Name column
      {
        let name_component = veText(local_geometry_name, { //[WIP] - onprogramchange doesn't fire, no binding
          attributes: { 
            "data-value": local_geometry_name
          },
          onprogramchange: (v, e) => {
            e.element.setAttribute("data-value", v);
            e.v = v;
          },
          onuserchange: (v, e) => {
            e.element.setAttribute("data-value", v);
            local_geometry.name = v;
          }
        });

        local_array.push(name_component.element);
      }
			
      if (options.view_tags) {
        let local_geometry_tags = local_geometry?.metadata?.tags;

        if (local_geometry_tags && Array.isArray(local_geometry_tags)) {
          local_array.push(local_geometry_tags.join(", "));
        } else {
          local_array.push("");
        }
      }
			local_array.push(local_geometry.getActionsBarElement());
			
			//Push local_array to table_array
			table_array.push(local_array);
		}
		
		//Return statement
		return table_array;
	}
}