/**
 * Refer to <span color = "yellow">{@link ve.Component}</span> for methods or fields inherited from this Component's parent such as `.options.attributes` or `.element`.
 * 
 * Datalist component, typically a text component with autocomplete suggestions. May sometimes also be used as a primitive for search select.
 * - Functional binding: <span color=00ffff>veDatalist</span>().
 * 
 * ##### Constructor:
 * - `arg0_value`: {@link Object}<{@link string}> - Read-only names are values, internal IDs are keys.
 * - `arg1_options`: {@link Object}
 *   - `.disabled=false`: {@link boolean}
 *   - `.selected`: {@link string} - The name of the selected value.
 * 
 * ##### Instance:
 * - `.v`: {@link string} - The current ID selected by the datalist. If no valid ID is found, the raw `.value` of the datalist element is returned.
 * 
 * @augments ve.Component
 * @memberof ve.Component
 * @type {ve.Datalist}
 */
ve.Datalist = class extends ve.Component {
  static demo_value = {
    "polygon": "Polygon",
    "line": "Line",
    "point": "Point"
  };
  static demo_options = {
    onchange: (e) => {
      console.log(`ve.Datalist:`, e);
    }
  };
  
  constructor (arg0_value, arg1_options) {
    //Convert from parameters
    let value = arg0_value;
    let options = (arg1_options) ? arg1_options : {};
      super(options);
    
    //Initialise options
    options.attributes = (options.attributes) ? options.attributes : {};
    
    //Declare local instance variables
    let attributes = {
      readonly: options.disabled,
      ...options.attributes
    };
    this.element = document.createElement("div");
      this.element.setAttribute("component", "ve-datalist");
      this.element.instance = this;
      this.id = Class.generateRandomID();
    
    this.options = options;
    this.options_map = {};
    this.value = value;
    
    //Format HTML string
    let html_string = [];
    html_string.push(`<span id = "name"></span>`);
    
    html_string.push(`<input list = "datalist-${this.id}" type = "text"${HTML.objectToAttributes(attributes)}>`);
    html_string.push(`<datalist id = "datalist-${this.id}">`);
    html_string.push(`</datalist>`);
    
    //Populate element and initialise handlers
    this.element.innerHTML = html_string.join("");
    
    let input_el = this.element.querySelector("input");
    let handleValueChange = (e) => {
      let current_input_val = (input_el) ? input_el.value : "";
      let is_exact_match = false;
      let resolved_id = current_input_val;
      
      if (this.options_map) {
        Object.iterate(this.options_map, (local_id, local_name) => {
          if (local_name === current_input_val || local_id === current_input_val) {
            is_exact_match = true;
            resolved_id = local_id;
          }
        });
      } else {
        let all_options = this.element.querySelectorAll("option");
        for (let i = 0; i < all_options.length; i++)
          if (all_options[i].value === current_input_val || all_options[i].innerHTML === current_input_val) {
            is_exact_match = true;
            resolved_id = all_options[i].innerHTML;
            break;
          }
      }
      
      if (e.type === "change" || is_exact_match) {
        this.from_binding_fire_silently = true;
        this.value = resolved_id;
        delete this.from_binding_fire_silently;
        this.fireToBinding();
      }
    };
    
    input_el.addEventListener("change", handleValueChange);
    input_el.addEventListener("input", handleValueChange);
    
    this.name = options.name;
    this.v = this.value;
    
    //Set options.selected if available
    if (options.selected) {
      this.from_binding_fire_silently = true;
      this.v = options.selected;
      delete this.from_binding_fire_silently;
    }
  }
  
  
  /**
   * Returns the key/ID of the present datalist.
   * - Accessor of: {@link ve.Datalist}
   *
   * @alias v
   * @memberof ve.Component.ve.Datalist
   * @type {string}
   */
  get v () {
    //Declare local instance variables
    let input_el = this.element.querySelector("input");
    let local_value = (input_el) ? input_el.value : "";
    let resolved_id;
    
    if (this.options_map)
      Object.iterate(this.options_map, (local_id, local_name) => {
        if (local_name === local_value || local_id === local_value)
          resolved_id = local_id;
      });
      
    if (resolved_id === undefined) {
      let all_options = this.element.querySelectorAll("option");
      for (let i = 0; i < all_options.length; i++)
        if (all_options[i].value === local_value) {
          resolved_id = all_options[i].innerHTML;
          break;
        } else if (all_options[i].innerHTML === local_value) {
          resolved_id = all_options[i].innerHTML;
          break;
        }
    }
    
    //Return statement
    return (resolved_id !== undefined) ? resolved_id : local_value;
  }
  
  
  /**
   * Sets the key/ID for the present datalist.
   * - Accessor of: {@link ve.Datalist}
   *
   * @alias v
   * @memberof ve.Component.ve.Datalist
   * 
   * @param {string} arg0_value
   */
  set v (arg0_value) {
    //Convert from parameters
    let value = arg0_value;
    
    //Declare local instance variables
    let html_string = [];
    
    if (typeof value === "object" && value !== null) {
      this.options_map = value;
      
      //Iterate over all keys in value and assign <option> tags to the datalist
      Object.iterate(value, (local_key, local_value) => {
        if (local_key === "selected") {
          let text_input = this.element.querySelector("input");
          if (text_input) text_input.value = local_value;
        } else {
          html_string.push(`<option value = "${local_value}">${local_key}</option>`);
        }
      });
      let datalist_el = this.element.querySelector("datalist");
      if (datalist_el) datalist_el.innerHTML = html_string.join("");
    } else if (typeof value === "string") {
      let display_value = value;
      
      if (this.options_map && this.options_map[value] !== undefined) {
        display_value = this.options_map[value];
      } else {
        let all_options = this.element.querySelectorAll("option");
        for (let i = 0; i < all_options.length; i++)
          if (all_options[i].innerHTML === value) {
            display_value = all_options[i].value;
            break;
          }
      }
      
      let text_input = this.element.querySelector("input");
      if (text_input) text_input.value = display_value;
    }
    
    this.value = value;
    this.fireFromBinding();
  }
};

//Functional binding

/**
 * @returns {ve.Datalist}
 */
veDatalist = function () {
  //Return statement
  return new ve.Datalist(...arguments);
};