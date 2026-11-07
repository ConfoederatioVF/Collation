/**
 * Refer to <span color = "yellow">{@link ve.Component}</span> for methods or fields inherited from this Component's parent such as `.options.attributes` or `.element`.
 * 
 * Represents a number input that can be set by the user.
 * - Functional binding: <span color=00ffff>veNumber</span>().
 * 
 * ##### Constructor:
 * - `arg0_value=0`: {@link Array}<{@link number}>|{@link number}
 * - `arg1_options`: {@link Object}
 *   - `.disabled=false`: {@link boolean}
 *   - `.list_options`: {@link Object} - Options for {@link ve.List} if an array.
 *   - `.max`: {@link number}
 *   - `.min`: {@link number}
 *   - `.step`: {@link number}
 * 
 * ##### Instance:
 * - `.v`: {@link number} 
 * 
 * ##### Methods:
 * - <span color=00ffff>{@link ve.Number.toString|toString}</span>() | {@link string}
 * - <span color=00ffff>{@link ve.Number.valueOf|valueOf}</span>() | {@link number}
 * 
 * @augments ve.Component
 * @memberof ve.Component
 * @type {ve.Number}
 */
ve.Number = class extends ve.Component {
	static demo_value = 1;
	
	constructor (arg0_value, arg1_options) {
		//Convert from parameters
		let value = (!Array.isArray(arg0_value)) ? Math.returnSafeNumber(arg0_value) : arg0_value;
		let options = (arg1_options) ? arg1_options : {};
			super(options);
		
		//Initialise options
		options.attributes = (options.attributes) ? options.attributes : {};
		
		//Declare local instance variables
		this.element = document.createElement("div");
			this.element.setAttribute("component", "ve-number");
			this.element.instance = this;
			if (options.element_attributes)
				HTML.setAttributesObject(this.element, options.element_attributes);
		this.options = options;
		this.value = value;
		
		//Populate scalar element and initialise handlers
		this._renderScalarInput();
		this.from_binding_fire_silently = true;
		this.v = this.value;
		delete this.from_binding_fire_silently;
	}

	/**
	 * Returns whether the number input is disabled.
	 *
	 * @returns {boolean}
	 */
	get disabled () {
		let input_el = this.element.querySelector("input");
		return (input_el) ? (input_el.disabled || input_el.readOnly) : !!this.options.disabled;
	}

	/**
	 * Sets the disabled state of the number input.
	 *
	 * @param {boolean} arg0_value
	 */
	set disabled (arg0_value) {
		let is_disabled = Boolean(arg0_value);
		let input_el = this.element.querySelector("input");
		if (input_el) {
			if (is_disabled) {
				input_el.setAttribute("disabled", "true");
				input_el.disabled = true;
			} else {
				input_el.removeAttribute("disabled");
				input_el.disabled = false;
			}
		}
	}
	
	/**
	 * Returns the present number stored by the component.
	 * - Accessor of: {@link ve.Number}
	 *
	 * @alias v
	 * @memberof ve.Component.ve.Number
	 * @type {number|number[]}
	 */
	get v () {
		if (this.list_component) {
			//Iterate over this.list_component.v to fetch all_values
			let all_values = [];
			
			for (let i = 0; i < this.list_component.v.length; i++)
				all_values.push(this.list_component.v[i].v);
			
			//Return statement
			return all_values;
		} else {
			//Return statement
			return this.value;
		}
	}
	
	/**
	 * Sets the number stored by the component.
	 * - Accessor of: {@link ve.Number}
	 *
	 * @alias v
	 * @memberof ve.Component.ve.Number
	 * 
	 * @param {number} arg0_value
	 */
	set v (arg0_value) {
		//Convert from parameters
		let value = arg0_value;
		
		if (Array.isArray(value)) {
			//Populate this.list_component with all_components
			let all_components = [];
			if (this.list_component)
				this.list_component.remove();
			
			for (let i = 0; i < value.length; i++)
				all_components.push(new ve.Number(value[i]));
			this.list_component = new ve.List(all_components, {
				...this.options.list_options,
				do_not_bubble_owners: true,
				onuserchange: () => {
					this.value = this.v;
					this.fireToBinding();
				}
			});
			if (this.owner)
				this.list_component.setOwner(this.owner, []);
			
			//Set value and refresh
			this.value = value;
			this.element.innerHTML = "";
			this.element.appendChild(this.list_component.element);
			this.fireFromBinding();
		} else {
			//Restore scalar input in-place if switching from array mode
			if (this.list_component) {
				this.list_component.remove();
				delete this.list_component;
				this._renderScalarInput();
			}
			
			//Set value and update UI
			this.value = value;
			this.element.querySelector("input").value = this.value;
			this.fireFromBinding();
		}
	}
	
	/**
	 * Renders the scalar `<input type="number">` markup and attaches DOM listeners on `this.element`.
	 * - Method of: {@link ve.Number}
	 * @private
	 */
	_renderScalarInput () {
		//Declare local instance variables
		let attributes = {
			readonly: this.options.disabled,
			max: this.options.max,
			min: this.options.min,
			step: this.options.step,
			...this.options.attributes
		};
		let html_string = [];
		
		//Format html_string
		html_string.push(`<span id = "name"></span> `);
		html_string.push(`<input type = "number"${HTML.objectToAttributes(attributes)}>`);
		this.element.innerHTML = html_string.join("");
		
		let input_el = this.element.querySelector("input");
		input_el.addEventListener("input", (e) => {
			let num_val = global.Number(e.target.value);
			if (!isNaN(num_val)) {
				this.value = num_val;
				if (typeof this.options.oninput === "function")
					this.options.oninput(this.value, this);
			}
		});
		input_el.addEventListener("change", (e) => {
			if (this.options.max !== undefined && global.Number(e.target.value) > this.options.max)
				e.target.value = this.options.max;
			if (this.options.min !== undefined && global.Number(e.target.value) < this.options.min)
				e.target.value = this.options.min;
			
			this.from_binding_fire_silently = true;
			this.v = global.Number(e.target.value);
			delete this.from_binding_fire_silently;
			this.fireToBinding();
		});
		this.name = this.options.name;
	}
	
	/**
	 * Converts the present number to a string.
	 * - Method of: {@link ve.Number}
	 *
	 * @alias toString
	 * @memberof ve.Component.ve.Number
	 * 
	 * @returns {string}
	 */
	toString () {
		return String(this.value);
	}
	
	/**
	 * Converts the present value to a number.
	 * - Method of: {@link ve.Number}
	 *
	 * @alias valueOf
	 * @memberof ve.Component.ve.Number
	 * 
	 * @returns {number}
	 */
	valueOf () {
		return this.value;
	}
};

//Functional binding

/**
 * @returns {ve.Number}
 */
veNumber = function () {
	//Return statement
	return new ve.Number(...arguments);
};