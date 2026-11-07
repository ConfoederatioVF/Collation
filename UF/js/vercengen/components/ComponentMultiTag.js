/**
 * Refer to <span color = "yellow">{@link ve.Component}</span> for methods or fields inherited from this Component's parent such as `.options.attributes` or `.element`.
 * 
 * Represents a multi tag input with unique metadata attributes for keywording.
 * - Functional binding: <span color=00ffff>veMultiTag</span>().
 * 
 * ##### Constructor:
 * - `arg0_value`: {@link Array}<{@link string}>
 * - `arg1_options`: {@link Object}
 *   - `.tags_key="global"`: {@link string} - The namespace to assign to the current MultiTag component to be shared between instances.
 * 
 * ##### Instance:
 * - `.registry_array`: {@link Array}<{@link string}> - Read-only. Global registry array shared between instances.
 * - `.v`: {@link Array}<{@link string}>
 *   
 * ##### Methods:
 * - <span color=00ffff>{@link ve.MultiTag.notifyAllInstances|notifyAllInstances}</span>()
 * - <span color=00ffff>{@link ve.MultiTag.refresh|refresh}</span>()
 * - <span color=00ffff>{@link ve.MultiTag.updateLocalTags|updateLocalTags}</span>()
 * 
 * @augments ve.Component
 * @memberof ve.Component
 * @type {ve.MultiTag}
 */
ve.MultiTag = class extends ve.Component {
	static instances = {};
	
	constructor (arg0_value, arg1_options) {
		//Convert from parameters
		let value = Array.toArray(arg0_value);
		let options = (arg1_options) ? arg1_options : {};
			super(options);
		
		//Initialise options
		options.attributes = (options.attributes) ? options.attributes : {};
		
		//Declare local instance variables
		this.element = document.createElement("div");
			this.element.setAttribute("component", "ve-multi-tag");
			Object.iterate(options.attributes, (local_key, local_value) => {
				this.element.setAttribute(local_key, local_value.toString());
			});
			this.element.instance = this;
		this.options = options;
		
		this.components_obj = {};
		/**
		 * @type {string[]}
		 */
		this.local_tags = value.filter(v => v != null && v !== "");
		
		//Register the current instance for synchronisation
		let key = this.options.tags_key || "global";
		if (!ve.MultiTag.instances[key])
			ve.MultiTag.instances[key] = [];
		ve.MultiTag.instances[key].push(this);
		
		//Populate registry with initial local_tags; call this.refresh()
		for (let tag of this.local_tags)
			if (!this.registry_array.includes(tag))
				this.registry_array.push(tag);
		this.refresh();
	}
	
	/**
	 * Returns the global registry array shared by all {@link ve.MultiTag} components with this namespace.
	 * - Accessor of: {@link ve.MultiTag}
	 *
	 * @alias registry_array
	 * @memberof ve.Component.ve.MultiTag
	 * @type {string[]}
	 * 
	 * @returns {string[]}
	 */
	get registry_array () {
		//Declare local instance variables
		let key = this.options.tags_key || "global";
		
		//Initialise registry array first if not defined
		if (!ve.registry.settings.MultiTag[key])
			ve.registry.settings.MultiTag[key] = [];
		
		//Return statement
		return ve.registry.settings.MultiTag[key];
	}
	
	/**
	 * Returns the string array stored by the component.
	 * - Accessor of: {@link ve.MultiTag}
	 *
	 * @alias v
	 * @memberof ve.Component.ve.MultiTag
	 * @type {string[]}
	 */
	get v () {
		//Return statement
		return this.local_tags;
	}
	
	/**
	 * Sets the string array stored by the component.
	 * - Accessor of: {@link ve.MultiTag}
	 *
	 * @alias v
	 * @memberof ve.Component.ve.MultiTag
	 * 
	 * @param {string[]} arg0_value
	 */
	set v (arg0_value) {
		//Convert from parameters
		let value = (arg0_value !== undefined && arg0_value !== null) ?
			Array.toArray(arg0_value).filter((local_tag) => local_tag !== null && local_tag !== undefined && local_tag !== "") : [];
		
		//Refresh, set value, then fire from binding
		this.local_tags = value;
		for (let i = 0; i < this.local_tags.length; i++)
			if (!this.registry_array.includes(this.local_tags[i]))
				this.registry_array.push(this.local_tags[i]);
		this.refresh();
		this.fireFromBinding();
	}
	
	/**
	 * Notifies all instances sharing the same `.options.tags_key` and updates their tag suggestions.
	 * - Method of: {@link ve.MultiTag}
	 *
	 * @alias notifyAllInstances
	 * @memberof ve.Component.ve.MultiTag
	 */
	notifyAllInstances () {
		//Declare local instance variables
		let key = this.options.tags_key || "global";
		let instances = ve.MultiTag.instances[key] || [];
		
		//Refresh datalist suggestions across all instances with this key without resetting list items
		for (let i = 0; i < instances.length; i++)
			if (typeof instances[i].refreshSuggestions === "function")
				instances[i].refreshSuggestions();
	}
	
	/**
	 * Refreshes the current {@link ve.List} display as well as any {@link ve.Datalist} components attached to it.
	 * - Method of: {@link ve.MultiTag}
	 *
	 * @alias refresh
	 * @memberof ve.Component.ve.MultiTag
	 */
	refresh () {
		//Declare local instance variables
		this.datalist_options = {};
		
		//Iterate over this.registry_array; build suggestions from registry_array
		for (let i = 0; i < this.registry_array.length; i++)
			this.datalist_options[this.registry_array[i]] = this.registry_array[i];
		
		//Create this.components_obj.datalist if ill-defined
		if (!this.components_obj.datalist) {
			this.components_obj.datalist = new ve.Datalist(this.datalist_options);
		} else {
			this.components_obj.datalist.v = this.datalist_options;
		}
		
		//Create this.components_obj.list if ill-defined, otherwise sync items to this.local_tags
		if (!this.components_obj.list) {
			this._initialising = true;
			let element_options = {
				onuserchange: (v, e) => {
					if (this._initialising) return;
					if (this.local_tags) {
						//Count how many times v already appears in the list excluding the current input
						let duplicate_count = 0;
						
						for (let i = 0; i < this.components_obj.list.v.length; i++) {
							let item = this.components_obj.list.v[i];
							if (item.element !== e.element && item.v === v)
								duplicate_count++;
						}
						
						if (duplicate_count > 0 && v !== "") {
							veToast(`<icon>warning</icon> This tag is a duplicate of a previous tag, and will not be registered.`);
							this._suppress_list_userchange = true;
							e.from_binding_fire_silently = true;
							e.v = "";
							delete e.from_binding_fire_silently;
						} else if (v !== "" && !this.registry_array.includes(v)) {
							this.registry_array.push(v);
						}
					}
				}
			};
			this._element_options = element_options;
			this.components_obj.datalist.options = element_options;
			this.components_obj.list = new ve.List([this.components_obj.datalist], {
				do_not_bubble_owners: true,
				onuserchange: (v, e) => {
					if (this._initialising) return;
					if (this._suppress_list_userchange) {
						delete this._suppress_list_userchange;
						return;
					}
					this.updateLocalTags();
					this.notifyAllInstances();
					this.fireToBinding();
				},
				style: {
					padding: 0
				},
				options: element_options
			});
			this.components_obj.list.bind(this.element);
			this._syncListItems();
			this._initialising = false;
		} else {
			this._initialising = true;
			this.refreshSuggestions();
			this._syncListItems();
			this._initialising = false;
		}
	}
	
	/**
	 * Updates suggestion `<datalist>` options on all items in this MultiTag without altering selected tag values.
	 * - Method of: {@link ve.MultiTag}
	 */
	refreshSuggestions () {
		//Declare local instance variables
		this.datalist_options = {};
		for (let i = 0; i < this.registry_array.length; i++)
			this.datalist_options[this.registry_array[i]] = this.registry_array[i];
		
		if (this.components_obj.datalist)
			this.components_obj.datalist.v = this.datalist_options;
		if (this.components_obj.list) {
			this.components_obj.list.placeholder = this.datalist_options;
			for (let i = 0; i < this.components_obj.list.v.length; i++)
				this.components_obj.list.v[i].v = this.datalist_options;
		}
	}
	
	/**
	 * Synchronises `this.components_obj.list` items to match `this.local_tags` silently.
	 * - Method of: {@link ve.MultiTag}
	 * @private
	 */
	_syncListItems () {
		if (!this.components_obj.list) return;
		
		//Declare local instance variables
		let target_tags = Array.isArray(this.local_tags) ? this.local_tags : [];
		let desired_count = Math.max(target_tags.length, 1);
		let items = [];
		
		for (let i = 0; i < desired_count; i++) {
			let item_datalist = new ve.Datalist(this.datalist_options, this._element_options);
			item_datalist.from_binding_fire_silently = true;
			item_datalist.v = (target_tags[i] !== undefined) ? String(target_tags[i]) : "";
			delete item_datalist.from_binding_fire_silently;
			items.push(item_datalist);
		}
		this.components_obj.datalist = items[0];
		this.components_obj.list.from_binding_fire_silently = true;
		this.components_obj.list.v = items;
		delete this.components_obj.list.from_binding_fire_silently;
		if (this.owner)
			this.components_obj.list.setOwner(this.owner, []);
	}
	
	/**
	 * Updates tags locally and ensures that {@link this.registry_array} is synchronised correctly to account for them.
	 * - Method of: {@link ve.MultiTag}
	 *
	 * @alias updateLocalTags
	 * @memberof ve.Component.ve.MultiTag	
	 */
	updateLocalTags () {
		//Declare local instance variables
		let new_array = [];
		
		//Iterate over all entries in the current list
		if (this.components_obj.list)
			for (let i = 0; i < this.components_obj.list.v.length; i++) {
				let local_value = this.components_obj.list.v[i].v;
				if (local_value && local_value.length > 0)
					new_array.push(local_value);
			}
		
		//Refresh this.local_tags
		this.local_tags = new_array;
		
		//Add new tags to registry
		for (let tag of new_array)
			if (!this.registry_array.includes(tag))
				this.registry_array.push(tag);
	}
};

//Functional binding

/**
 * @returns {ve.MultiTag}
 */
veMultiTag = function () {
	//Return statement
	return new ve.MultiTag(...arguments);
};