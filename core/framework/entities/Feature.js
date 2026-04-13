if (!global.naissance) global.naissance = {};
naissance.Feature = class extends ve.Class {
	static instances = [];
	
	constructor () {
		//Convert from parameters
		super();
		this.id = Class.generateRandomID(naissance.Feature);
		this.instance = this;
		this.is_naissance_feature = true;
		this._is_visible = true;
		
		//Initialise this.options
		if (!this.options) this.options = {};
			this.options.instance = this;
			
		//Declare local instance variables
		this._name = "New Feature";
		this._parent = undefined;
		
		//Push to naissance.Feature.instances
		naissance.Feature.instances.push(this);
		setTimeout(() => {
			if (main.brush.selected_feature?.entities && !this.cannot_nest_self) { //Sanity check to make sure .cannot_nest_self is invalid for nesting
				this.parent = main.brush.selected_feature;
				main.brush.selected_feature.entities.push(this);
			}
		});
	}
	
	get name () {
		//Return statement
		return this._name;
	}
	
	set name (arg0_value) {
		//Convert from parameters
		let value = (arg0_value) ? arg0_value : "";
		
		//Send DALS.Timeline.parseAction() command
		DALS.Timeline.parseAction({
			options: { name: "Rename Feature", key: "rename_Feature" },
			value: [{ type: "Feature", feature_id: this.id, set_name: value }]
		}, this.fire_action_silently);
	}
	
	get parent () {
		//Return statement
		return this._parent;
	}
	
	set parent (arg0_v) {
		//Convert from parameters
		let value = arg0_v;
		
		//Make sure parent cannot be self
		if (value && value.id !== this.id)
			this._parent = value;
		if (value === undefined)
			this._parent = undefined;
	}
	
	drawHierarchyDatatypeGenerics () {
		//Return statement
		return {
			hide_visibility: veButton(() => {
				DALS.Timeline.parseAction({
					options: { name: "Hide Feature", key: "hide_feature" },
					value: [{ type: "Feature", feature_id: this.id, set_visibility: false }]
				});
			}, {
				attributes: { class: "order-99" },
				name: `<icon>visibility</icon>`,
				limit: () => this._is_visible,
				tooltip: "Hide Feature"
			}),
			show_visibility: veButton(() => {
				DALS.Timeline.parseAction({
					options: { name: "Show Feature", key: "show_feature" },
					value: [{ type: "Feature", feature_id: this.id, set_visibility: true }]
				});
			}, {
				attributes: { class: "order-99" },
				name: "<icon>visibility_off</icon>",
				limit: () =>  !this._is_visible,
				tooltip: "Show Feature"
			}),
			delete_button: veButton(() => {
				DALS.Timeline.parseAction({
					options: { name: "Delete Feature", key: "delete_feature" },
					value: [{ type: "Feature", feature_id: this.id, delete_feature: true }]
				});
			}, {
				attributes: { class: "order-100" },
				name: "<icon>delete</icon>", 
				tooltip: "Delete",
			}),
		};
	}
	
	/**
	 * Returns an array of all {@link naissance.Geometry} instances housed in the FeatureLayer.
	 *
	 * @param {naissance.Feature} [arg0_object]
	 * @param {Object} [arg1_options]
	 *  @param {naissance.Feature[]} [arg1_options.owners]
	 *
	 * @returns {naissance.Geometry[]}
	 */
	getAllGeometries (arg0_object, arg1_options) {
		//Convert from parameters
		let object = (arg0_object) ? arg0_object : this;
		let options = (arg1_options) ? arg1_options : {};
		
		//Initialise options
		if (!options.owners) options.owners = [];
		
		//Declare local instance variables
		let all_entities = [];
		let owner_names = [];
		
		//Iterate over options.owners and fetch their .name
		for (let i = 0; i < options.owners.length; i++) {
			let local_name = options.owners[i]?.name;
			
			if (local_name) owner_names.push(local_name);
		}
		
		//Iterate over all .entities and check if they have .entities
		if (object?.entities)
			for (let i = 0; i < object.entities.length; i++)
				if (object.entities[i] instanceof naissance.Geometry) {
					let local_entity = object.entities[i];
					
					//Edit metadata
					if (!local_entity.metadata) local_entity.metadata = {};
					if (!local_entity.metadata.tags) local_entity.metadata.tags = [];
					
					//Iterate over all owner_names and ensure they inherit the proper tags if they don't exist, i.e. convert groups to tags
					for (let x = 0; x < owner_names.length; x++)
						if (!local_entity.metadata.tags.includes(owner_names[x]))
							local_entity.metadata.tags.push(owner_names[x]);
					
					all_entities.push(object.entities[i]);
				} else if (object.entities[i].entities) {
					all_entities = all_entities.concat(this.getAllGeometries(object.entities[i], {
						owners: options.owners.concat([object.entities[i]])
					}));
				}
		
		//Return statement
		return all_entities;
	}
	
	hide () {
		//Declare local instance variables
		this._is_visible = false;
		
		//Iterate over all entities; attempt to hide all entities
		if (this.entities)
			for (let i = 0; i < this.entities.length; i++)
				if (this.entities[i].hide)
					this.entities[i].hide();
	}
	
	remove () {
		//Declare local instance variables
		let delete_keys = ["_entities", "entities"]
		
		//Remove from naissance.Feature.instances
		for (let i = naissance.Feature.instances.length - 1; i >= 0; i--) {
			let local_feature = naissance.Feature.instances[i];
			
			if (local_feature.id === this.id)
				naissance.Feature.instances.splice(i, 1);
			if (local_feature.entities)
				//Iterate over delete_keys and local_feature.entities.length to ensure clean removal
				for (let x = 0; x < delete_keys.length; x++)
					if (local_feature[delete_keys[x]])
						for (let y = local_feature[delete_keys[x]].length - 1; y >= 0; y--)
							if (local_feature[delete_keys[x]][y].id === this.id)
								local_feature[delete_keys[x]].splice(x, 1);
		}
		
		//Remove from local_feature.entities
		if (this.hide) this.hide();
		if (this.entities)
			for (let x = 0; x < this.entities.length; x++)
				if (this.entities[x].id === this.id)
					naissance.Feature.instances.splice(x, 1);
		
		//Rerender deleted feature and remove it from the map
		if (this.draw) this.draw();
		UI_LeftbarHierarchy.refresh();
	}
	
	show () {
		this._is_visible = true;``
		
		//Iterate over all entities; attempt to show all entities
		if (this.entities)
			for (let i = 0; i < this.entities.length; i++)
				if (this.entities[i].show)
					this.entities[i].show();
	}
	
	/**
	 * Parses a JSON action for a target Feature.
	 * - Static method of: {@link naissance.Feature}
	 * 
	 * `arg0_json`: {@link Object|string}
	 * - `.feature_id`: {@link string} - Identifier. The {@link naissance.Feature} ID to target changes for, if any.
	 * <br>
	 * - ##### Extraneous Commands:
	 * - `.delete_feature`: {@link boolean}
	 * - `.set_name`: {@link string}
	 * - `.set_visibility`: {@link boolean}
	 * 
	 * @param {Object|string} arg0_json
	 */
	static parseAction (arg0_json) {
		//Convert from parameters
		let json = (typeof arg0_json === "string") ? JSON.parse(arg0_json) : arg0_json;
		
		//Declare local instance variables
		let feature_obj = naissance.Feature.instances.filter((v) => v.id === json.feature_id)[0];
		
		//Parse commands for feature_obj
		if (feature_obj) {
			//delete_feature
			if (json.delete_feature === true) {
				feature_obj.remove();
				return;
			}
			
			//set_name
			if (typeof json.set_name === "string")
				feature_obj._name = json.set_name;
			
			//set_visibility
			if (json.set_visibility !== undefined)
				if (json.set_visibility === true) {
					feature_obj.show();
				} else if (json.set_visibility === false) {
					feature_obj.hide();
				}
		}
	}
};