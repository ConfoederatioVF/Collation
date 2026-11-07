/**
 * <span color = "yellow">{@link ve.Component}</span>: Components represent inputs and displays that yield a value via `.v`. They are typically encapsulated by a <span color="yellow">{@link ve.Feature}</span>, but can be manually mounted via <span color=00ffff>{@link ve.Component.bind|bind}</span>(arg0_container_el:{@link HTMLElement}).
 *
 * ##### Constructor:
 * - `arg0_options`: {@link Object}
 *   - All bindings accept 'this'/'global'/'window' variables. Bindings propagate recursively upwards (i.e. a userchange at a lower level will register as a userchange in an upper level).
 *   - `.binding`: {@link string} - Related event: `.onchange`. Bidirectional data binding for both `.from_binding`/`.to_binding`.
 *   - `.from_binding`: {@link string} - Related event: `.onprogramchange`. Unidirectional data binding (`variable -> this.v`).
 *   - `.to_binding`: {@link string} - Related event: `.onuserchange`. Unidirectional data binding (`this.v -> variable`).
 *   - `.do_not_bubble_owners=false`: {@link boolean} - Stops callback propagation up `.owners` past this component boundary.
 *   - `.do_not_display=false`: {@link boolean} - If set to true, Component is not automatically displayed by {@link ve.Class}.
 *   - `.do_not_fire_to_binding=false`: {@link boolean} - Suppresses `.to_binding` writes and userchange emission on this component.
 *   - `.gc=false`: {@link boolean} - Whether to auto-remove the component upon being detached.
 *   - `.onchange`: {@link function}(this.v, this:{@link ve.Component})
 *   - `.onprogramchange`: {@link function}(this.v, this:{@link ve.Component})
 *   - `.onuserchange`: {@link function}(this.v, this:{@link ve.Component})
 *   -
 *   - `.attributes`: {@link Object} - Any attributes to place on the mounted `this.element`.
 *     - `<attribute_key>`: {@link string}
 *   - `.limit=true`: {@link function}(this.v)|{@link undefined} | {@link boolean} - Whether to display the current Component. Immediate mode.
 *   - `.onload`: {@link function}(this:{@link ve.Component})
 *   - `.tooltip`: {@link Object}<{@link ve.Component}>|{@link string}
 *   - `.style`: {@link Object} - The CSS/Telestyle object to use for the current element. Immediate mode CSS if function is declared.
 *     - `<selector_key>`: {@link string} - CSS query selector. :nth-parent() is acceptable.
 *       - `<css_property>`: {@link function}|{@link string}
 *     - `<css_property>`: {@link function}|{@link string}
 *
 *   - `.log_gc=false`: {@link boolean} - Whether to log Vercengen garbage collection for the given component.
 *
 * ##### DOM:
 * - Attributes:
 *   - `data-debug-add-component`: {@link boolean}
 *   - `data-debug-limit`: {@link boolean}
 * - Fields:
 *   - `.instance`: this:{@link ve.Component}
 *
 * ##### Instance:
 * - `.child_class=this.constructor`: {@link ve.Component} - The constructor object of the child class.
 * - `.is_vercengen_component=true`: {@link boolean} - Whether to mark this ve.Component as a Vercengen component.
 * - `.parent_el`: {@link HTMLElement} - The parent element of the current component, should it exist.
 * -
 * - `.height=1`: {@link number}
 * - `.width=1`: {@link number}
 * - `.x=0`: {@link number} - Switches to an n+1 default if only `.y` is defined.
 * - `.y=n + 1`: {@link number} - Switches to 0 if only `.x` is defined.
 * -
 * - The linter/engine guarantees the following fields:
 * - `.element`: {@link HTMLElement} - The HTMLElement that the ve.Component is mounted to.
 * - `.name`: {@link string} - The name to display for the current ve.Component.
 * - `.owner`: {@link any} - The root owner of the current ve.Component. This is typically a {@link ve.Class}, but can also be a {@link ve.Feature} or {@link global}/{@link window}.
 * - `.owners`: {@link Array}<{@link any}> - A list of relevant owners in descending order (outermost to innermost).
 * - `.v`: {@link any} - The value stored by the component. Getter/setter.
 *
 * ##### Methods:
 * - <span color=00ffff>{@link ve.Component.addComponent|addComponent}</span>() - Attempts to mount the current component on its parent_el.
 * - <span color=00ffff>{@link ve.Component.attachFromBindingListener|attachFromBindingListener}</span>(arg0_parent_object:{@link Object}, arg1_final_key:{@link string}, arg2_listener_fn:{@link function})
 * - <span color=00ffff>{@link ve.Component.bind|bind}</span>(arg0_container_el:{@link HTMLElement}) - Manually mounts the current component to arg0_container_el.
 * - <span color=00ffff>{@link ve.Component.copy|copy}</span>() | {@link ve.Component} - Copies the current component.
 * - <span color=00ffff>{@link ve.Component.detachFromBinding|detachFromBinding}</span>() - Detaches any active `from_binding` listener owned by this component.
 * - <span color=00ffff>{@link ve.Component.fireFromBinding|fireFromBinding}</span>() - Programmatic `.v` notification. Syncs `.to_binding` if present and fires `onchange` + `onprogramchange` bottom-up.
 * - <span color=00ffff>{@link ve.Component.fireToBinding|fireToBinding}</span>() - User-driven `.v` notification. Syncs `.to_binding` if present and fires `onchange` + `onuserchange` bottom-up.
 * - <span color=00ffff>{@link ve.Component.gc|gc}</span>() - Adds the component to garbage collection.
 * - <span color=00ffff>{@link ve.Component.remove|remove}</span>() - Removes the component/element from the DOM and detaches bindings.
 * - <span color=00ffff>{@link ve.Component.removeComponent|removeComponent}</span>() - Unmounts the current component from its parent_el.
 * - <span color=00ffff>{@link ve.Component.resolveBindingTarget|resolveBindingTarget}</span>(arg0_variable_string:{@link string}, arg1_options:{@link Object}) | {@link Object}
 * - <span color=00ffff>{@link ve.Component.setValueFromObject|setValueFromObject}</span>(arg0_object:{@link Object}, arg1_object:{@link Object})
 * - <span color=00ffff>{@link ve.Component.setOwner|setOwner}</span>(arg0_value:{@link Object}, arg1_owner_array=[]:{@link Array}<{@link Object}>) - Used by {@link ve.Class}, {@link ve.Feature} and container components to set the owner hierarchy automatically.
 *
 * ##### Static Methods:
 * - <span color=00ffff>{@link ve.Component.cloneBindingValue|cloneBindingValue}</span>(arg0_value:{@link any}, arg1_seen:{@link WeakMap}) | {@link any}
 * - <span color=00ffff>{@link ve.Component.getElement|getElement}</span>(arg0_component_obj:{@link ve.Component}|{@link HTMLElement}) | {@link HTMLElement}
 * - <span color=00ffff>{@link ve.Component.linter|linter}</span>() - Run at startup if {@link ve.registry.debug_mode} is true. Lints all Vercengen components.
 * - <span color=00ffff>{@link ve.Component.wrapPrototypeV|wrapPrototypeV}</span>(arg0_prototype:{@link Object}) - Ensures subclass `set v` implementations emit `fireFromBinding()`.
 *
 * ##### Types:
 * Types are annotated by both their constructor function and what they return after the pipe separator (`.v`).
 *
 * \* indicates a recursive Object of that type.
 * - {@link ve.Component.ve.DatavisSuite|veDatavisSuite}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link Object}
 * - {@link ve.Component.ve.FileExplorer|veFileExplorer}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string} - The file path the File Explorer is currently navigating.
 * - {@link ve.Component.ve.Hierarchy|veHierarchy}(arg0_value:{@link Object}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link ve.Component}> - Note. It is recommended to use {@link ve.HierarchyDatatype} as the specific {@link ve.Component} for `arg0_value`. Tree/scene inspector.
 *   - {@link ve.Component.ve.HierarchyDatatype|veHierarchyDatatype}({@link Object}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link ve.Component}> - Represents individual items in a hierarchy.
 * - {@link ve.Component.ve.NodeEditor|veNodeEditor}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link Object} - Visual node-based DAG editor with async processing.
 *   - {@link ve.Component.ve.NodeEditorDatatype|veNodeEditorDatatype}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link Object}
 * - {@link ve.Component.ve.ScriptManager|veScriptManager}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 *   - {@link ve.Component.ve.ScriptManagerBlockly|veScriptManagerBlockly}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 *   - {@link ve.Component.ve.ScriptManagerMonaco|ScriptManagerMonaco}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 * - {@link ve.Component.ve.Spreadsheet|veSpreadsheet}(arg0_value:{@link Array}<{@link Array}<{@link Array}<{@link any}>>>|{@link Object}, arg1_options:{@link Object}) | {@link Array}<{@link Array}<{@link Array}<{@link any}>>>|{@link Object} - Spreadsheet editor with formulas. Can be converted to {@link ve.Table} on demand.
 * - {@link ve.Component.ve.WordProcessor|WordProcessor}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string} - Word processor.
 *
 * - {@link ve.Component.ve.Button|veButton}(arg0_value:{@link function}, arg1_options:{@link Object}) | {@link function}
 * - {@link ve.Component.ve.Checkbox|veCheckbox}(arg0_value:{@link boolean}|{@link Object}<{@link boolean}>\*, arg1_options: {@link Object}) | {@link boolean}|{@link Object}<{@link boolean}>\* - A recursive list of checkboxes, or a single toggleable input.
 * - {@link ve.Component.ve.Colour|veColour}(arg0_value:{@link Array}<{@link number}, {@link number}, {@link number}|{@link string}, arg1_options: {@link Object}>) | {@link Array}<{@link number}, {@link number}, {@link number}> - RGB colour selector.
 * - {@link ve.Component.ve.CRUD|veCRUD}(arg0_value:{@link Array}<{@link Array}<{@link any}>>, arg1_options:{@link Object}) | {@link Array}<{@link Array}<{@link any}>> - CRUD interface for editing instances in a table.
 * - {@link ve.Component.ve.Datalist|veDatalist}(arg0_value:{@link Object}<{@link string}>, arg1_options: {@link Object})
 * - {@link ve.Component.ve.Date|veDate}(arg0_value:{@link UF.Date}, arg1_options: {@link Object}) | {@link UF.Date}
 * - {@link ve.Component.ve.DateLength|veDateLength}(arg0_value:{@link UF.Date}, arg1_options: {@link Object}) | {@link UF.Date}
 * - {@link ve.Component.ve.File|veFile}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string} - The file/folder path selected by the user.
 * - {@link ve.Component.ve.FlexInterface|veFlexInterface}(arg0_value:{@link Object}<{@link Object}|{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link Object}|{@link ve.Component}>
 * - {@link ve.Component.ve.Graph|veGraph}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link Object}
 * - {@link ve.Component.ve.HTML|veHTML}(arg0_value:{@link function}|{@link HTMLElement}|{@link string}, arg1_options: {@link Object}) | {@link string}
 * - {@link ve.Component.ve.Interface|veInterface}(arg0_value:{@link Object}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link ve.Component}>
 * - {@link ve.Component.ve.Log|veLog}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 * - {@link ve.Component.ve.List|veList}(arg0_value:{@link Array}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Array}<{@link ve.Component}>
 * - {@link ve.Component.ve.Map|veMap}(arg0_value:{@link maptalks.Map}, arg1_options:{@link Object}) | {@link maptalks.Map}
 * - {@link ve.Component.ve.MultiTag|veMultiTag}(arg0_value:{@link Array}<{@link string}>, arg1_options:{@link Object}) | {@link Array}<{@link string}>
 * - {@link ve.Component.ve.Number|veNumber}(arg0_value:{@link number}, arg1_options:{@link Object}) | {@link number}
 * - {@link ve.Component.ve.ObjectEditor|veObjectEditor}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link Object} - Any valid JSON object.
 * - {@link ve.Component.ve.ObjectInspector|veObjectInspector}(arg0_value:{@link any}, arg1_options:{@link Object}) | {@link any}
 * - {@link ve.Component.ve.PageMenu|vePageMenu}(arg0_value:{@link Object}, arg1_options:{@link Object}) | {@link string} - The `.page` key currently displayed.
 * - {@link ve.Component.ve.Password|vePassword}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 * - {@link ve.Component.ve.Radio|veRadio}(arg0_value:{@link Object}<{@link boolean}>\* | {@link Object}<{@link boolean}>\*
 * - {@link ve.Component.ve.Range|veRange}(arg0_value:{@link number}, arg1_options: {@link Object}) | {@link number}
 * - {@link ve.Component.ve.RawInterface|veRawInterface}(arg0_components_obj:{@link Object}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link ve.Component}>
 * - {@link ve.Component.ve.RichText|veRichText}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string} - Single-line rich text input. `.v` is an HTML string.
 * - {@link ve.Component.ve.SearchSelect|veSearchSelect}(arg0_components_obj:{@link Object}<{@link ve.Component}>, arg1_options:{@link Object}) | {@link Object}<{@link ve.Component}>
 * - {@link ve.Component.ve.Select|veSelect}(arg0_value:{@link ve.Object}<{@link string}>, arg1_options:{@link Object}) | {@link string} - The key of the selected option.
 * - {@link ve.Component.ve.Table|veTable}(arg0_value:{@link Array}<{@link Array}<{@link any}>>, arg1_options:{@link Object}) | {@link Array}<{@link Array}<{@link any}>> - Paginated lazy-loaded table. Can be converted to {@link ve.Spreadsheet} on demand.
 * - {@link ve.Component.ve.Telephone|veTelephone}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 * - {@link ve.Component.ve.Text|veText}(arg0_value:{@link string}, arg1_options: {@link Object}) | {@link string}
 * - {@link ve.Component.ve.Time|veTime}(arg0_value:{hour:{@link number}, minute:{@link number}}, arg1_options:{@link Object}) | {hour:{@link number}, minute:{@link number}}
 * - {@link ve.Component.ve.Timeline|veTimeline}(arg0_value:{@link number}|{@link Object}, arg1_options:{@link Object}) | {@link Object} - Returns the date the timeline is currently focused on.
 *   - {@link ve.Component.ve.TimelineChronology|veTimelineChronology}(arg0_value:{@link number}|{@link Object}, arg1_options:{@link Object}) | {@link Object} - Returns the date the timeline chronology is currently focused on.
 * - {@link ve.Component.ve.Toggle|veToggle}(arg0_value:{@link boolean}, arg1_options:{@link Object}) | {@link boolean}
 * - {@link ve.Component.ve.UndoRedo|veUndoRedo}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string} - The {@link DALS.Timeline} ID that the UndoRedo component is currently navigating.
 * - {@link ve.Component.ve.URL|veURL}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 * - {@link ve.Component.ve.Wiki|veWiki}(arg0_value:{@link string}, arg1_options:{@link Object}) | {@link string}
 *
 * @class
 * @memberof ve
 * @namespace ve.Component
 * @type {ve.Component}
 */
ve.Component = class {
	//Declare local static variables
	
	/**
	 * @type {WeakMap<Object, Object<string, Function[]>>}
	 */
	static binding_registry = new WeakMap();
	/**
	 * @type {ve.Component[]}
	 */
	static instances = [];
	static registry = new FinalizationRegistry((v) => {
		//This runs when the component is GC'd
		let index = ve.Component.instances.indexOf(v);
		if (index > -1) ve.Component.instances.splice(index, 1);
	});
	/**
	 * @type {WeakSet<Object>}
	 */
	static wrapped_prototypes = new WeakSet();
	
	
	constructor (arg0_options) {
		//Convert from parameters
		let options = (arg0_options) ? arg0_options : {};
		
		//Ensure subclass prototype set v() triggers fireFromBinding() when omitted
		ve.Component.wrapPrototypeV(Object.getPrototypeOf(this));
		
		//Declare local instance variables
		this.child_class = this.constructor;
		this.class_name = this.constructor.class_name;
		this.do_not_fire_to_binding = Boolean(options.do_not_fire_to_binding);
		this.is_vercengen_component = true;
		if (this.options === undefined)
			this.options = options; //Preferably overridden by lower components
		
		this.height = options.height;
		this.width = options.width;
		this.x = options.x;
		this.y = options.y;
		
		//Push to instances if ve.registry.debug_profile_components is true
		if (ve.registry.debug_profile_components || this.options.gc) this.gc();
		
		//Binding handlers; setTimeout() is necessary to tick a frame until ve.Component child class's constructor populates
		setTimeout(() => {
			if (this._is_removing || !this.options) return; //Internal guard clause if removed or this.options doesn't exist
			if (this.element && this.options.style) HTML.applyTelestyle(this.element, this.options.style);
			if (this.element && this.options.theme) HTML.applyTelestyle(this.element, ve.registry.themes[this.options.theme]);
			
			//Flow control handlers
			//.binding handler (bidirectional)
			if (this.options.binding && this.binding_string === undefined && !this._binding_cleared)
				this.binding = this.options.binding;
			//.from_binding handler (unidirectional, onprogramchange, variable -> this)
			if (this.options.from_binding && this.from_binding_string !== this.options.from_binding && !this._from_binding_cleared)
				this.from_binding = this.options.from_binding;
			//.to_binding handler (unidirectional, onuserchange, this -> variable)
			if (this.options.to_binding && this.to_binding_string !== this.options.to_binding && !this._to_binding_cleared)
				this.to_binding = this.options.to_binding;
			
			//Event handlers
			//.onload handler
			if (this.options.onload)
				setTimeout(() => {
					if (!this._is_removing && this.options?.onload)
						this.options.onload(this.v, this);
				}, 100);
			
			//KEEP AT BOTTOM! - Feature/UI handlers
			//.limit handler
			if (this.options.limit)
				this.limit = this.options.limit;
			if (this.options.name && this.name === "")
				this.name = this.options.name;
			
			//.tooltip handler
			if (this.element && this.options.tooltip) {
				let createTooltip = () => this.tooltip = new ve.Tooltip(this.options.tooltip, {
					element: this.element });
				
				this.element.addEventListener("mouseover", (e) => {
					if (Object.keys(this.tooltip).length === 0) createTooltip();
				});
				createTooltip();
			}
		}, 0);
	}
	
	
	//ve.Component getters/setters
	
	/**
	 * Returns the bidirectional `.binding` variable path if configured.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @returns {string|undefined}
	 */
	get binding () {
		//Return statement
		return this.binding_string;
	}
	
	
	/**
	 * Sets bidirectional `.binding` (`from_binding` + `to_binding`) on the present Component.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @param {string|undefined} arg0_variable_string
	 */
	set binding (arg0_variable_string) {
		//Convert from parameters
		let variable_string = arg0_variable_string;
		
		//Guard clauses
		if (!variable_string) {
			this._binding_cleared = true;
			delete this.binding_string;
			this.from_binding = undefined;
			this.to_binding = undefined;
			return;
		}
		if (typeof variable_string !== "string") {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.binding is an invalid string:`, variable_string);
			return;
		}
		
		delete this._binding_cleared;
		this.binding_string = variable_string;
		this.from_binding = variable_string;
		this.to_binding = variable_string;
	}
	
	
	/**
	 * Returns the unidirectional `.from_binding` variable path if configured.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @returns {string|undefined}
	 */
	get from_binding () {
		//Return statement
		return this.from_binding_string;
	}
	
	
	/**
	 * Internal `.from_binding` setter for handling `.options.from_binding` (`variable -> this.v`). Accepts a string path resolved against `this.owner`, `window` or `global`.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @param {string|undefined} arg0_variable_string
	 */
	set from_binding (arg0_variable_string) {
		//Convert from parameters
		let variable_string = arg0_variable_string;
		
		//Detach any existing listener before rebinding or clearing
		this.detachFromBinding();
		if (!variable_string) {
			this._from_binding_cleared = true;
			delete this.from_binding_string;
			delete this._from_binding_snapshot;
			delete this._pending_owner_from_binding;
			return;
		}
		if (typeof variable_string !== "string") {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.from_binding is an invalid string:`, variable_string);
			return;
		}
		
		delete this._from_binding_cleared;
		this.from_binding_string = variable_string;
		
		try {
			//Defer owner-scoped binding until setOwner() provides this.owner
			let target_obj = this.resolveBindingTarget(variable_string, { create_path: true });
			if (target_obj.is_owner_scoped && !this.owner) {
				this._pending_owner_from_binding = true;
				return;
			}
			if (!target_obj.parent_object || !target_obj.final_key) {
				console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.from_binding failed to resolve target:`, variable_string);
				return;
			}
			delete this._pending_owner_from_binding;
			
			//Silent initial hydration: pull variable -> this.v if bound variable is defined
			let from_value = target_obj.parent_object[target_obj.final_key];
			if (from_value !== undefined) {
				let hydrated_value = ve.Component.cloneBindingValue(from_value);
				this._from_binding_snapshot = ve.Component.cloneBindingValue(from_value);
				let had_silent_flag = Boolean(this.from_binding_fire_silently);
				try {
					this.from_binding_fire_silently = true;
					this.v = hydrated_value;
				} finally {
					if (!had_silent_flag)
						delete this.from_binding_fire_silently;
				}
			} else {
				this._from_binding_snapshot = undefined;
			}
			
			//Attach multiplexed property/deep-proxy listener
			this.attachFromBindingListener(target_obj.parent_object, target_obj.final_key, (arg0_value) => {
				//Convert from parameters
				let local_value = arg0_value;
				
				//Guard clauses
				if (this._is_removing || this.from_binding_fire_silently) return;
				if (typeof local_value !== "object" || local_value === null) {
					if (Object.is(local_value, this.v)) return;
				} else {
					let proto = Object.getPrototypeOf(local_value);
					let is_plain_or_array = (Array.isArray(local_value) || proto === Object.prototype || proto === null);
					if (
						is_plain_or_array &&
						this._from_binding_snapshot !== undefined &&
						typeof this._from_binding_snapshot === "object" &&
						this._from_binding_snapshot !== null &&
						Boolean.strictEquality(local_value, this._from_binding_snapshot)
					) return;
				}
				
				let next_value = ve.Component.cloneBindingValue(local_value);
				this._from_binding_snapshot = ve.Component.cloneBindingValue(local_value);
				
				let had_silent_flag = Boolean(this.from_binding_fire_silently);
				try {
					this.from_binding_fire_silently = true;
					this.v = next_value;
				} finally {
					if (!had_silent_flag)
						delete this.from_binding_fire_silently;
				}
				
				//Relay to a distinct to_binding if configured as a pipe
				let active_to_binding = this.to_binding_string;
				if (active_to_binding && active_to_binding !== this.from_binding_string)
					this._syncToBinding(this.v);
				
				this._fireBindingCallbacks("program");
			});
		} catch (e) {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.from_binding failed for ${variable_string}:`, e);
		}
	}
	
	
	/**
	 * Tests the current {@link this.limit} by calling {@link this.limit_function}({@link this.v}, {@link this}). Otherwise resolves to true if no `.options.limit` is set.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @returns {boolean}
	 */
	get limit () {
		//Return statement
		try {
			return (typeof this.limit_function === "function") ?
				this.limit_function(this.v, this) : true;
		} catch (e) { return false; }
	}
	
	
	/**
	 * Sets the present {@link this.limit} or clears it (if undefined). Calls {@link this.limit_function}({@link this.v}, {@link this}) when polled.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @param {function|undefined} arg0_function
	 */
	set limit (arg0_function) {
		//Convert from parameters
		this.limit_function = arg0_function;
		if (this.limit_logic_loop !== undefined) {
			clearInterval(this.limit_logic_loop);
			delete this.limit_logic_loop;
		}
		
		if (this.limit_function !== undefined) {
			let evaluateLimit = () => {
				if (this.element)
					if (!this.limit) {
						this.element.classList.add("ve-display-none");
						if (this.element.getAttribute("data-debug-limit"))
							console.log(`- .limit: Removing component:`, this);
					} else {
						this.element.classList.remove("ve-display-none");
						if (this.element.getAttribute("data-debug-limit"))
							console.log(`- .limit: Adding component:`, this);
					}
			};
			
			evaluateLimit(); //Evaluate once immediately to prevent flickering (i.e. waiting 100ms)
			this.limit_logic_loop = setInterval(() => evaluateLimit(), 100);
		} else {
			delete this.limit_function;
		}
	}
	
	
	/**
	 * Returns the visual name of the present {@link ve.Component}.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @returns {string}
	 */
	get name () {
		//Internal guard clause for this.components_obj.name.v
		if (this.components_obj && this.components_obj.name)
			return this.components_obj.name.v;
		if (!this.element) return "";
		
		//Declare local instance variables
		let name_el = this.element.querySelector(`#name`);
		
		//Return statement
		if (name_el)
			return name_el.innerHTML;
	}
	
	
	/**
	 * Sets the visual name of the present {@link ve.Component}.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @param {string} arg0_value
	 */
	set name (arg0_value) {
		//Convert from parameters
		let value = (arg0_value) ? arg0_value : "";
		
		//Guard catch for this.components_obj.name.v
		if (this.components_obj && this.components_obj.name) {
			this.components_obj.name.v = (value) ? value : "";
			return;
		}
		if (!this.element) return;
		
		//Declare local instance variables
		let name_el = this.element.querySelector(`#name`);
		
		//Return statement
		if (name_el)
			name_el.innerHTML = (value) ? value.trim() : "";
	}
	
	
	/**
	 * Returns the unidirectional `.to_binding` variable path if configured.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @returns {string|undefined}
	 */
	get to_binding () {
		//Return statement
		return this.to_binding_string;
	}
	
	
	/**
	 * Internal `.to_binding` setter for handling `.options.to_binding` (`this.v -> variable`). Accepts a string path resolved against `this.owner`, `window` or `global`.
	 * - Accessor of: {@link ve.Component}
	 *
	 * @param {string|undefined} arg0_variable_string
	 */
	set to_binding (arg0_variable_string) {
		//Convert from parameters
		let variable_string = arg0_variable_string;
		
		//Guard clauses
		if (!variable_string) {
			this._to_binding_cleared = true;
			delete this.to_binding_string;
			delete this._pending_owner_to_binding;
			return;
		}
		if (typeof variable_string !== "string") {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.to_binding is an invalid string:`, variable_string);
			return;
		}
		
		delete this._to_binding_cleared;
		this.to_binding_string = variable_string;
		
		try {
			//Defer owner-scoped binding until setOwner() provides this.owner
			let target_obj = this.resolveBindingTarget(variable_string, { create_path: true });
			if (target_obj.is_owner_scoped && !this.owner) {
				this._pending_owner_to_binding = true;
				return;
			}
			if (!target_obj.parent_object || !target_obj.final_key) {
				console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.to_binding failed to resolve target:`, variable_string);
				return;
			}
			delete this._pending_owner_to_binding;
			
			//Silent initial hydration: push this.v -> variable only if bound variable is currently undefined
			let current_bound_value = target_obj.parent_object[target_obj.final_key];
			if (current_bound_value === undefined && !this.do_not_fire_to_binding && !this.to_binding_fire_silently)
				this._syncToBinding(this.v);
		} catch (e) {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.to_binding failed for ${variable_string}:`, e);
		}
	}
	
	
	//ve.Component dataflow functions
	
	/**
	 * Fires `onchange` plus either `onprogramchange` or `onuserchange` on `this` first, then bottom-up across `this.owners` (innermost to outermost), syncing ancestor `.to_binding`s along the way.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {string} arg0_mode - Either 'program' or 'user'.
	 * @private
	 */
	_fireBindingCallbacks (arg0_mode) {
		//Convert from parameters
		let mode = arg0_mode;
		
		//Guard clauses
		if (this._is_removing) return;
		
		//Declare local instance variables
		let local_value = this.v;
		if (
			this._active_callback_dispatch &&
			mode === "program" &&
			this._active_callback_dispatch.mode === "program" &&
			ve.Component.isBindingValueEqual(local_value, this._active_callback_dispatch.snapshot)
		)
			return;
		
		let had_self_firing_flag = Boolean(this._is_firing_callbacks);
		let previous_dispatch = this._active_callback_dispatch;
		let visited_owners = new Set([this]);
		
		//1. Fire callbacks on this component first
		this._active_callback_dispatch = {
			mode: mode,
			snapshot: ve.Component.cloneBindingValue(local_value)
		};
		this._is_firing_callbacks = true;
		try {
			if (this.options) {
				if (typeof this.options.onchange === "function")
					this.options.onchange(local_value, this);
				if (mode === "program" && typeof this.options.onprogramchange === "function")
					this.options.onprogramchange(local_value, this);
				if (mode === "user" && typeof this.options.onuserchange === "function")
					this.options.onuserchange(local_value, this);
			}
		} finally {
			if (previous_dispatch !== undefined) {
				this._active_callback_dispatch = previous_dispatch;
			} else {
				delete this._active_callback_dispatch;
			}
			if (!had_self_firing_flag)
				delete this._is_firing_callbacks;
		}
		
		//2. Traverse bottom-up through this.owners (innermost -> outermost)
		if (this.options?.do_not_bubble_owners || !Array.isArray(this.owners)) return;
		
		for (let i = this.owners.length - 1; i >= 0; i--) {
			let local_owner = this.owners[i];
			if (!local_owner || local_owner._is_removing || visited_owners.has(local_owner)) continue;
			visited_owners.add(local_owner);
			
			if (local_owner.is_vercengen_component) {
				if (mode === "user" && (local_owner.do_not_fire_to_binding || local_owner.to_binding_fire_silently)) break;
				if (mode === "program" && (local_owner.from_binding_fire_silently || local_owner._set_v_depth > 0)) break;
				local_owner._syncToBinding(local_owner.v);
			}
			if (local_owner._is_firing_callbacks) break;
			
			if (local_owner.options) {
				let had_owner_firing_flag = Boolean(local_owner._is_firing_callbacks);
				let owner_value = (local_owner.is_vercengen_component || local_owner.v !== undefined) ?
					local_owner.v : local_value;
				
				local_owner._is_firing_callbacks = true;
				try {
					if (typeof local_owner.options.onchange === "function")
						local_owner.options.onchange(owner_value, local_owner);
					if (mode === "program" && typeof local_owner.options.onprogramchange === "function")
						local_owner.options.onprogramchange(owner_value, local_owner);
					if (mode === "user" && typeof local_owner.options.onuserchange === "function")
						local_owner.options.onuserchange(owner_value, local_owner);
				} finally {
					if (!had_owner_firing_flag)
						delete local_owner._is_firing_callbacks;
				}
			}
			
			if (local_owner.options?.do_not_bubble_owners) break;
		}
	}
	
	
	/**
	 * Pushes `arg0_value` into the bound `.to_binding` variable silently with respect to this component's own `from_binding` listener.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {any} arg0_value
	 * @private
	 */
	_syncToBinding (arg0_value) {
		//Convert from parameters
		let value = arg0_value;
		
		//Declare local instance variables
		let fallback_binding = (!this._to_binding_cleared && !this._binding_cleared) ?
			(this.options?.to_binding || this.options?.binding) : undefined;
		let variable_string = (this.to_binding_string !== undefined) ?
			this.to_binding_string : fallback_binding;
		
		//Guard clauses
		if (!variable_string || this._is_removing || this.do_not_fire_to_binding || this.to_binding_fire_silently) return;
		if (typeof variable_string !== "string") {
			console.error(`ve.Component: ${this.child_class?.prototype?.constructor?.name}: this.to_binding is an invalid string:`, variable_string);
			return;
		}
		
		let target_obj = this.resolveBindingTarget(variable_string, { create_path: true });
		if (target_obj.is_owner_scoped && !this.owner) {
			this._pending_owner_to_binding = true;
			return;
		}
		if (!target_obj.parent_object || !target_obj.final_key) return;
		
		let cloned_value = ve.Component.cloneBindingValue(value);
		if (this.from_binding_string === variable_string)
			this._from_binding_snapshot = ve.Component.cloneBindingValue(value);
		
		let had_silent_flag = Boolean(this.from_binding_fire_silently);
		try {
			this.from_binding_fire_silently = true;
			target_obj.parent_object[target_obj.final_key] = cloned_value;
		} finally {
			if (!had_silent_flag)
				delete this.from_binding_fire_silently;
		}
	}
	
	
	/**
	 * Registers a multiplexed setter/deep-proxy listener on `(arg0_parent_object, arg1_final_key)` via {@link ve.Component.binding_registry} so multiple components can observe the same variable and detach cleanly.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {Object} arg0_parent_object
	 * @param {string} arg1_final_key
	 * @param {function} arg2_listener_fn
	 */
	attachFromBindingListener (arg0_parent_object, arg1_final_key, arg2_listener_fn) {
		//Convert from parameters
		let parent_object = arg0_parent_object;
		let final_key = arg1_final_key;
		let listener_fn = arg2_listener_fn;
		
		//Guard clauses
		if (!parent_object || !final_key || typeof listener_fn !== "function") return;
		this.detachFromBinding();
		
		//Declare local instance variables
		let object_listeners = ve.Component.binding_registry.get(parent_object);
		if (!object_listeners) {
			object_listeners = {};
			ve.Component.binding_registry.set(parent_object, object_listeners);
		}
		
		let key_listeners = object_listeners[final_key];
		if (!key_listeners) {
			let existing_value = parent_object[final_key];
			key_listeners = [];
			object_listeners[final_key] = key_listeners;
			
			Object.addGetterSetter(parent_object, final_key, {
				set_function: (arg0_val) => {
					let listeners_snapshot = key_listeners.slice();
					for (let i = 0; i < listeners_snapshot.length; i++)
						listeners_snapshot[i](arg0_val);
				}
			});
			
			//Wrap existing object/array values in Object.addGetterSetter's deep Proxy before any listener is registered
			if (existing_value !== undefined)
				parent_object[final_key] = existing_value;
		}
		
		key_listeners.push(listener_fn);
		this._from_binding_cleanup = () => {
			let listener_index = key_listeners.indexOf(listener_fn);
			if (listener_index > -1)
				key_listeners.splice(listener_index, 1);
		};
	}
	
	
	/**
	 * Detaches any active `from_binding` listener owned by this component.
	 * - Method of: {@link ve.Component}
	 */
	detachFromBinding () {
		if (typeof this._from_binding_cleanup === "function") {
			this._from_binding_cleanup();
			delete this._from_binding_cleanup;
		}
	}
	
	
	/**
	 * Programmatic `.v` notification. Syncs `.to_binding` if present and fires `onchange` + `onprogramchange` bottom-up (`this` first, then `this.owners` innermost-to-outermost). Never writes back to a unidirectional `from_binding`.
	 * - Method of: {@link ve.Component}
	 */
	fireFromBinding () {
		if (this._set_v_depth > 0)
			this._fired_from_binding_in_set_v = true;
		if (this._is_removing || this.from_binding_fire_silently) return;
		
		//Declare local instance variables
		let local_value = this.v;
		
		//Push programmatic .v change to to_binding if set, then emit programchange callbacks
		this._syncToBinding(local_value);
		this._fireBindingCallbacks("program");
	}
	
	
	/**
	 * User-driven `.v` notification. Syncs `.to_binding` if present and fires `onchange` + `onuserchange` bottom-up (`this` first, then `this.owners` innermost-to-outermost).
	 * - Method of: {@link ve.Component}
	 */
	fireToBinding () {
		//Guard clauses
		if (this._is_removing || this.do_not_fire_to_binding || this.to_binding_fire_silently) return;
		
		//Declare local instance variables
		let local_value = this.v;
		
		//Push user .v change to to_binding first so bound state is current inside callbacks
		this._syncToBinding(local_value);
		this._fireBindingCallbacks("user");
	}
	
	
	/**
	 * Adds the current component to the garbage collector.
	 * - Method of: {@link ve.Component}
	 */
	gc () {
		//Declare local instance variables
		let ref = new WeakRef(this);
		this._id = Class.generateRandomID(ve.Component); //Private variable since sub-components have their own .id and .instances
		this._timestamp = new Date().getTime();
		
		//Push the component to be GC-tracked
		ve.Component.instances.push(ref);
		ve.Component.registry.register(this, ref);
	}
	
	
	/**
	 * Parses a binding variable path (`this.*`, `window.*`, `global.*` or bare global path) into its root, parent object and final key.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {string} arg0_variable_string
	 * @param {Object} [arg1_options]
	 *  @param {boolean} [arg1_options.create_path=false] - Whether to initialise missing intermediate objects along a dotted path.
	 *
	 * @returns {{final_key: (string|undefined), is_owner_scoped: boolean, parent_object: (Object|undefined), path_string: string, root_object: (Object|undefined)}}
	 */
	resolveBindingTarget (arg0_variable_string, arg1_options) {
		//Convert from parameters
		let variable_string = (typeof arg0_variable_string === "string") ? arg0_variable_string : "";
		let options = (arg1_options) ? arg1_options : {};
		
		//Declare local instance variables
		let is_owner_scoped = false;
		let path_string = variable_string;
		let root_object = global;
		
		if (variable_string.startsWith("this.")) {
			is_owner_scoped = true;
			path_string = variable_string.slice(5);
			root_object = this.owner;
		} else if (variable_string.startsWith("window.")) {
			path_string = variable_string.slice(7);
			root_object = (typeof window !== "undefined") ? window : global;
		} else if (variable_string.startsWith("global.")) {
			path_string = variable_string.slice(7);
			root_object = global;
		}
		
		if (!root_object || !path_string)
			return {
				final_key: undefined,
				is_owner_scoped: is_owner_scoped,
				parent_object: undefined,
				path_string: path_string,
				root_object: root_object
			};
		
		let all_keys = path_string.split(".");
		let current_obj = root_object;
		
		for (let i = 0; i < all_keys.length - 1; i++) {
			let local_key = all_keys[i];
			if (current_obj[local_key] === undefined || current_obj[local_key] === null)
				if (options.create_path) {
					current_obj[local_key] = {};
				} else {
					//Return statement
					return {
						final_key: all_keys[all_keys.length - 1],
						is_owner_scoped: is_owner_scoped,
						parent_object: undefined,
						path_string: path_string,
						root_object: root_object
					};
				}
			current_obj = current_obj[local_key];
		}
		
		//Return statement
		return {
			final_key: all_keys[all_keys.length - 1],
			is_owner_scoped: is_owner_scoped,
			parent_object: current_obj,
			path_string: path_string,
			root_object: root_object
		};
	}
	
	
	/**
	 * Sets the root owner and ancestor ownership chain (`.owner`, `.owners`), re-hydrating deferred `"this.*"` bindings when `.owner` resolves and propagating ownership to child containers.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {any} arg0_value
	 * @param {Array<any>} [arg1_owner_array]
	 */
	setOwner (arg0_value, arg1_owner_array) {
		//Convert from parameters
		let value = arg0_value;
		let owner_array = arg1_owner_array;
		
		//Declare local instance variables
		let previous_owner = this.owner;
		let resolved_owner = (value === undefined && this.owner !== undefined) ?
			this.owner : value;
		
		this.owner = resolved_owner;
		if (Array.isArray(owner_array)) {
			let merged_owners = [];
			if (value === undefined && Array.isArray(this.owners))
				for (let i = 0; i < this.owners.length; i++)
					if (this.owners[i] && this.owners[i] !== this && !merged_owners.includes(this.owners[i]))
						merged_owners.push(this.owners[i]);
			for (let i = 0; i < owner_array.length; i++)
				if (owner_array[i] && owner_array[i] !== this && !merged_owners.includes(owner_array[i]))
					merged_owners.push(owner_array[i]);
			this.owners = merged_owners;
		} else {
			this.owners = (resolved_owner && resolved_owner !== this) ? [resolved_owner] : [];
		}
		
		//Re-attach owner-scoped bindings when this.owner resolves or changes
		if (this.owner && (this.owner !== previous_owner || this._pending_owner_from_binding || this._pending_owner_to_binding)) {
			if (this.from_binding_string && (this._pending_owner_from_binding || this.from_binding_string.startsWith("this.")))
				this.from_binding = this.from_binding_string;
			if (this.to_binding_string && (this._pending_owner_to_binding || this.to_binding_string.startsWith("this.")))
				this.to_binding = this.to_binding_string;
		}
		
		let child_owners = this.owners.concat([this]);
		let visited_groups = new WeakSet();
		let propagateToObject = (arg0_target_obj, arg1_owners) => {
			if (!arg0_target_obj || typeof arg0_target_obj !== "object" || visited_groups.has(arg0_target_obj)) return;
			visited_groups.add(arg0_target_obj);
			
			Object.iterate(arg0_target_obj, (local_key, local_value) => {
				if (local_key === "options" || !local_value) return;
				if (typeof local_value.setOwner === "function") {
					let target_owners = (local_value.options?.do_not_bubble_owners) ?
						[] : arg1_owners;
					local_value.setOwner(resolved_owner, target_owners);
				} else if (typeof local_value === "object" && Object.getPrototypeOf(local_value) === Object.prototype) {
					propagateToObject(local_value, arg1_owners);
				}
			});
		};
		
		//Propagate down container structures without mutating caller arrays
		if (this.components_obj)
			propagateToObject(this.components_obj, child_owners);
		if (this.interfaces_obj)
			propagateToObject(this.interfaces_obj, this.owners);
		if (this.hierarchy && typeof this.hierarchy.setOwner === "function")
			this.hierarchy.setOwner(resolved_owner, []);
		if (this.list_component && typeof this.list_component.setOwner === "function")
			this.list_component.setOwner(resolved_owner, []);
		if (Array.isArray(this.value))
			for (let i = 0; i < this.value.length; i++)
				if (this.value[i]?.is_vercengen_component && typeof this.value[i].setOwner === "function") {
					let item_owners = (this.value[i].options?.do_not_bubble_owners) ?
						[] : child_owners;
					this.value[i].setOwner(resolved_owner, item_owners);
				}
	}
	
	
	//ve.Component UI functions
	
	/**
	 * Adds the current component to {@link this.parent_el} should it exist.
	 * - Method of: {@link ve.Component}
	 */
	addComponent () {
		if (this.parent_el) try {
			if (!this.parent_el.contains(this.element)) {
				this.parent_el.appendChild(this.element);
				
				if (this.element.getAttribute("data-debug-add-component"))
					console.log(`- addComponent() called for:`, this, `bound to`, this.parent_el);
			}
		} catch (e) { console.error(e); }
	}
	
	
	/**
	 * Manually binds/mounts the present <span color="yellow">{@link ve.Component}</span> into the visual DOM.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {HTMLElement} arg0_container_el
	 */
	bind (arg0_container_el) {
		//Convert from parameters
		let container_el = arg0_container_el;
		
		//Set variable_key, append to container_el
		container_el.append(this.element);
	}
	
	
	/**
	 * Copies the current component and returns a new instance of it.
	 * - Method of: {@link ve.Component}
	 *
	 * @returns {ve.Component}
	 */
	copy () {
		//Declare local instance variables
		let components_obj = {};
		
		if (this.components_obj) {
			Object.iterate(this.components_obj, (local_key, local_value) => {
				if (typeof local_value.copy === "function")
					components_obj[local_key] = local_value.copy();
			});
			
			//Return statement
			return new this.constructor(components_obj, this.options);
		} else {
			//Return statement
			return new this.constructor(this.v, this.options);
		}
	}
	
	
	/**
	 * Removes the component/element from the DOM and detaches any active bindings/intervals.
	 * - Method of: {@link ve.Component}
	 */
	remove () {
		//Guard clause against recursive teardown loops
		if (this._is_removing) return;
		this._is_removing = true;
		
		//Detach active from_binding listener first
		this.detachFromBinding();
		
		//Declare local instance variables
		let all_keys = Object.keys(this);
		if (all_keys.length === 0) return; //Internal guard clause if already cleared
		let child_class_obj;
		try { child_class_obj = ve[this.child_class.prototype.constructor.name]; } catch (e) {}
		
		//Clear element and polling intervals first if available
		if (typeof this.clear === "function")
			this.clear();
		if (this.draw_loop !== undefined)
			clearInterval(this.draw_loop);
		if (this.limit_logic_loop !== undefined)
			clearInterval(this.limit_logic_loop);
		if (this.logic_loop !== undefined)
			clearInterval(this.logic_loop);
		if (this.monaco_initialisation_loop !== undefined)
			clearInterval(this.monaco_initialisation_loop);
		if (this.undo_redo_loop !== undefined)
			clearInterval(this.undo_redo_loop);
		
		//Iterate over all instances in child_class_obj.instances if available
		if (child_class_obj?.instances && this.id)
			for (let i = 0; i < child_class_obj.instances.length; i++)
				if (child_class_obj.instances[i].id === this.id) {
					child_class_obj.instances.splice(i, 1);
					break;
				}
		
		//Remove everything else
		if (this?.options?.onremove) this.options.onremove(this); //Fire .options.onremove if it exists
		
		//Iterate over components_obj and interfaces_obj to clean up child references
		if (this.components_obj) {
			let local_components_obj = this.components_obj;
			this.components_obj = undefined;
			Object.iterate(local_components_obj, (local_key, local_value) => {
				if (local_value && typeof local_value.remove === "function") local_value.remove();
			});
		}
		if (this.interfaces_obj) {
			let local_interfaces_obj = this.interfaces_obj;
			this.interfaces_obj = undefined;
			Object.iterate(local_interfaces_obj, (local_key, local_value) => {
				if (local_value && typeof local_value.remove === "function") local_value.remove();
			});
		}
		
		for (let i = 0; i < all_keys.length; i++) {
			let local_key = all_keys[i];
			let local_value = this[local_key];
			
			if (local_value === undefined || local_key === "_is_removing") continue;
			this[local_key] = undefined; //Unset reference first to break circular dependency before recursion
			
			if (
				(typeof HTMLElement !== "undefined" && local_value instanceof HTMLElement) ||
				local_value instanceof ve.Component
			)
				local_value.remove();
		}
		Object.setPrototypeOf(this, null); //Set this to null - [WARN] - This might not optimise heap; remains to be seen in production
		
		//Clear freed this.instances
		ve.Component.instances = ve.Component.instances.filter((ref) => (
			ref instanceof WeakRef && ref.deref() !== undefined));
	}
	
	
	/**
	 * Removes the current component from {@link this.parent_el} should it exist.
	 * - Method of: {@link ve.Component}
	 */
	removeComponent () {
		if (this.element?.parentElement) try {
			if (this.element.parentElement.contains(this.element)) {
				this.parent_el = this.element.parentElement;
				this.parent_el.removeChild(this.element);
			}
		} catch (e) { console.error(e); }
	}
	
	
	/**
	 * Destructures Object values and transfers them into the `.v` instance fields of each Vercengen component.
	 * - Method of: {@link ve.Component}
	 *
	 * @param {Object} arg0_object - The Vercengen object to transfer to.
	 * @param {Object} arg1_object - The other object to transfer from.
	 */
	setValueFromObject (arg0_object, arg1_object) {
		//Convert from parameters
		let object = (arg0_object) ? arg0_object : {};
		let ot_object = (arg1_object) ? arg1_object : {};
		
		//Iterate over ot_object
		Object.iterate(ot_object, (local_key, local_value) => {
			try {
				if (object[local_key]?.v !== undefined) {
					object[local_key].v = local_value;
				} else if (
					object[local_key] !== undefined && local_value !== undefined &&
					typeof local_value === "object" && !local_value.is_vercengen_component
				) {
					this.setValueFromObject(object[local_key], local_value);
				}
			} catch (e) {}
		});
	}
	
	
	//Static methods
	
	/**
	 * Clones plain objects and arrays (including Proxy-wrapped objects and objects containing functions) while preserving class instances, DOM nodes and functions by reference.
	 * - Static method of: {@link ve.Component}
	 *
	 * @param {any} arg0_value
	 * @param {WeakMap} [arg1_seen]
	 *
	 * @returns {any}
	 */
	static cloneBindingValue (arg0_value, arg1_seen) {
		//Convert from parameters
		let value = arg0_value;
		let seen = (arg1_seen) ? arg1_seen : new WeakMap();
		
		//Guard clauses for primitives, functions, DOM nodes and class instances
		if (typeof value !== "object" || value === null) return value;
		if (seen.has(value)) return seen.get(value);
		if (Array.isArray(value)) {
			let return_array = [];
			seen.set(value, return_array);
			for (let i = 0; i < value.length; i++)
				return_array.push(ve.Component.cloneBindingValue(value[i], seen));
			
			//Return statement
			return return_array;
		}
		let proto = Object.getPrototypeOf(value);
		if (proto !== Object.prototype && proto !== null) return value;
		
		//Declare local instance variables
		let all_keys = Object.keys(value);
		let return_obj = {};
		seen.set(value, return_obj);
		
		for (let i = 0; i < all_keys.length; i++) {
			let local_key = all_keys[i];
			return_obj[local_key] = ve.Component.cloneBindingValue(value[local_key], seen);
		}
		
		//Return statement
		return return_obj;
	}
	
	
	/**
	 * Returns the {@link HTMLElement} of a given Vercengen Component/DOM Node.
	 * - Static method of: {@link ve.Component}
	 *
	 * @param {HTMLElement|ve.Component} arg0_component_obj
	 *
	 * @returns {HTMLElement}
	 */
	static getElement (arg0_component_obj) {
		//Convert from parameters
		let component_obj = arg0_component_obj;
		
		//Return statement
		if (component_obj.is_vercengen_component) {
			return component_obj.element;
		} else if (typeof HTMLElement !== "undefined" && component_obj instanceof HTMLElement) {
			return component_obj;
		}
	}
	
	
	/**
	 * Cycle-safe structural equality check for binding snapshots (primitives, arrays and plain objects).
	 * - Static method of: {@link ve.Component}
	 *
	 * @param {any} arg0_first_value
	 * @param {any} arg1_second_value
	 * @param {WeakMap} [arg2_seen]
	 *
	 * @returns {boolean}
	 */
	static isBindingValueEqual (arg0_first_value, arg1_second_value, arg2_seen) {
		//Convert from parameters
		let first_value = arg0_first_value;
		let second_value = arg1_second_value;
		let seen = (arg2_seen) ? arg2_seen : new WeakMap();
		
		//Guard clauses
		if (Object.is(first_value, second_value)) return true;
		if (
			typeof first_value !== "object" || first_value === null ||
			typeof second_value !== "object" || second_value === null
		)
			return false;
		
		if (seen.has(first_value) && seen.get(first_value) === second_value)
			return true;
		seen.set(first_value, second_value);
		
		if (Array.isArray(first_value) || Array.isArray(second_value)) {
			if (!Array.isArray(first_value) || !Array.isArray(second_value)) return false;
			if (first_value.length !== second_value.length) return false;
			for (let i = 0; i < first_value.length; i++)
				if (!ve.Component.isBindingValueEqual(first_value[i], second_value[i], seen))
					return false;
			
			//Return statement
			return true;
		}
		
		let first_proto = Object.getPrototypeOf(first_value);
		let second_proto = Object.getPrototypeOf(second_value);
		if (
			(first_proto !== Object.prototype && first_proto !== null) ||
			(second_proto !== Object.prototype && second_proto !== null)
		)
			return false;
		
		//Declare local instance variables
		let first_keys = Object.keys(first_value);
		let second_keys = Object.keys(second_value);
		if (first_keys.length !== second_keys.length) return false;
		
		for (let i = 0; i < first_keys.length; i++) {
			let local_key = first_keys[i];
			if (!Object.prototype.hasOwnProperty.call(second_value, local_key)) return false;
			if (!ve.Component.isBindingValueEqual(first_value[local_key], second_value[local_key], seen))
				return false;
		}
		
		//Return statement
		return true;
	}
	
	
	/**
	 * Runs over all Vercengen components that extend <span color="yellow">{@link ve.Component}</span> and lints them in addition to declaring `ve[local_key]`() as a functional binding for each.
	 * - Static method of: {@link ve.Component}
	 *
	 * Ensures the following properties if `ve.registry.debug_mode=true`:
	 * - get v()/set v()
	 * - Not a duplicate component
	 */
	static linter () {
		Object.iterate(global.ve, (local_key, local_value) => {
			try {
				if (Object.getPrototypeOf(local_value) === ve.Component) {
					let local_v = Object.getOwnPropertyDescriptor(local_value.prototype, "v");
					let local_prefix = `ve.Component: ve.${local_key}`;
					
					ve.Component.wrapPrototypeV(local_value.prototype);
					
					if (!global[`ve${local_key}`]) {
						global[`ve${local_key}`] = function () {
							//Return statement
							return new ve[local_key](...arguments);
						};
					} else if (typeof global[`ve${local_key}`] !== "function") {
						console.error(`ve.${local_key} cannot have its functional binding registered, since it is already reserved elsewhere as a non-function. Use Ctrl + F to find where it has been reserved in your codebase.`);
					}
					
					if (ve.registry.debug_mode) {
						if (local_value.demo_value === undefined)
							console.warn(`${local_prefix} does not have a set static .demo_value.`);
						if (local_value.excluded_from_demo)
							console.warn(`${local_prefix} is currently excluded from automated testing. Perhaps it is a singleton?`);
					}
					
					//Check if get()/set() methods exist
					if (!local_v || typeof local_v.get !== "function")
						console.error(`${local_prefix} does not have a valid get v() function.`);
					if (!local_v || typeof local_v.set !== "function")
						console.error(`${local_prefix} does not have a valid set v() function.`);
					
					//Append to ve.registry.components
					if (!ve.registry.components[local_key] && !ve.registry.features[local_key]) {
						local_value.class_name = local_key;
						ve.registry.components[local_key] = local_value;
					} else {
						let error_value = (ve.registry.components[local_key]) ?
							ve.registry.components[local_key] : ve.registry.features[local_key];
						
						console.error(`Could not replace with duplicate component. A component/feature with the key: ${local_key} already exists as:`, error_value, "Duplicate registered as", local_value);
					}
				}
			} catch (e) { console.error(e); }
		});
	}
	
	
	/**
	 * Wraps a subclass prototype's `set v` descriptor so programmatic `.v` assignments automatically invoke `this.fireFromBinding()` once if `set v` did not already call it directly or asynchronously.
	 * - Static method of: {@link ve.Component}
	 *
	 * @param {Object} arg0_prototype
	 */
	static wrapPrototypeV (arg0_prototype) {
		//Convert from parameters
		let prototype = arg0_prototype;
		
		//Guard clauses
		if (!prototype || prototype === ve.Component.prototype || prototype === Object.prototype) return;
		if (ve.Component.wrapped_prototypes.has(prototype)) return;
		
		let parent_prototype = Object.getPrototypeOf(prototype);
		if (parent_prototype && parent_prototype !== ve.Component.prototype && parent_prototype !== Object.prototype)
			ve.Component.wrapPrototypeV(parent_prototype);
		ve.Component.wrapped_prototypes.add(prototype);
		
		//Declare local instance variables
		let descriptor = Object.getOwnPropertyDescriptor(prototype, "v");
		if (!descriptor || typeof descriptor.set !== "function") return;
		
		let setter_source = descriptor.set.toString()
			.replace(/\/\*[\s\S]*?\*\//g, "")
			.replace(/\/\/.*$/gm, "");
		let has_explicit_fire_from_binding = /\bfireFromBinding\s*\(/.test(setter_source);
		
		let original_get = descriptor.get;
		let original_set = descriptor.set;
		
		Object.defineProperty(prototype, "v", {
			configurable: true,
			enumerable: descriptor.enumerable,
			get: original_get,
			set: function (arg0_value) {
				let was_outermost = (!this._set_v_depth);
				if (was_outermost)
					this._fired_from_binding_in_set_v = false;
				this._set_v_depth = (this._set_v_depth || 0) + 1;
				try {
					original_set.call(this, arg0_value);
					if (
						was_outermost &&
						!has_explicit_fire_from_binding &&
						!this._fired_from_binding_in_set_v &&
						!this._defer_from_binding &&
						!this.from_binding_fire_silently
					)
						this.fireFromBinding();
				} finally {
					this._set_v_depth--;
					if (was_outermost)
						delete this._fired_from_binding_in_set_v;
				}
			}
		});
	}
};
