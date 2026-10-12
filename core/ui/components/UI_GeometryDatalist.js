/**
 * ##### Constructor:
 * - `arg0_value`: {@link string} - The `.id` of the geometry to refer to.
 * - `arg1_options`: {@link Object}
 *   - `.filter_types`: {@link Array}<{@string}> - The list of `.class_name`s to filter, i.e. `["GeometryPolygon"]`.
 * 
 * ##### Instance:
 * - `.v`: {@link string}
 * 
 * @type {UI_GeometryDatalist}
 */
global.UI_GeometryDatalist = class extends ve.Component {
  constructor (arg0_value, arg1_options) {
    //Convert from parameters
    let value = arg0_value;
    let options = (arg1_options) ? arg1_options : {};
      super(options);
      
    //Declare local instance variables
    this.options = options;
    this.value = value;
    
    //Loop-draw pattern
    this.draw();
    this.logic_loop = setInterval(() => {
      let is_focused = (this.element) ? this.element.querySelector("input:focus") : null;
      
      if (!is_focused) this.draw();
    }, 1000);
  }
  
  
  get v () {
    //Declare local instance variables
    let current_val = this.value;
    
    if (!current_val && this.datalist)
      current_val = this.datalist.v;
      
    if (!current_val || !String(current_val).trim()) return "";
    
    if (current_val && !naissance.Geometry.instances[current_val]) {
      let norm_val = String(current_val).replace(/\s+/g, "").toLowerCase();
      Object.iterate(naissance.Geometry.instances, (local_id, local_geom) => {
        let geom_id = String(local_id).replace(/\s+/g, "").toLowerCase();
        let geom_name = (local_geom.name) ? String(local_geom.name).replace(/\s+/g, "").toLowerCase() : "";
        if (geom_name === norm_val || geom_id === norm_val) current_val = local_id;
      });
    }
      
    //Return statement
    return current_val;
  }
  
  
  set v (arg0_value) {
    //Convert from parameters
    let value = arg0_value;
    
    this.value = value;
    if (this.datalist) this.datalist.v = value;
    this.fireFromBinding();
  }
  
  
  draw () {
    if (!this.element) {
      this.element = document.createElement("div");
      this.element.setAttribute("component", "naissance-geometry-datalist");
      this.element.instance = this;
    }
    
    //Declare local instance variables
    let geometry_map = {};
    
    //Fetch all current geometries and their names
    Object.iterate(naissance.Geometry.instances, (local_key, local_geometry) => {
      let is_valid = true;

      //Deal with options.filter_types
      if (this.options.filter_types)
        if (!this.options.filter_types.includes(local_geometry.class_name))
          is_valid = false;
      
      //Append to map if valid geometry
      if (is_valid) {
        let clean_name = (local_geometry.name) ?
          String(local_geometry.name).replace(/\r?\n|\r/g, " ").trim() : local_geometry.id;
        geometry_map[local_geometry.id] = clean_name;
      }
    });
    
    let current_value = this.v;
    let selected_name = (current_value && geometry_map[current_value]) ? geometry_map[current_value] : current_value;
    
    if (this.datalist) {
      this.datalist.v = geometry_map;
      let input_el = this.datalist.element.querySelector("input");
      if (input_el && current_value && selected_name !== undefined && input_el.value !== selected_name) {
        let is_focused = this.element.querySelector("input:focus");
        if (!is_focused) input_el.value = selected_name;
      }
    } else {
      this.datalist = veDatalist(geometry_map, {
        name: (this.options.name) ? this.options.name : undefined,
        onuserchange: (v) => {
          let resolved_id = v;
          if (v && String(v).trim()) {
            if (naissance.Geometry.instances[v]) {
              resolved_id = v;
            } else {
              let norm_val = String(v).replace(/\s+/g, "").toLowerCase();
              Object.iterate(naissance.Geometry.instances, (local_id, local_geom) => {
                let geom_id = String(local_id).replace(/\s+/g, "").toLowerCase();
                let geom_name = (local_geom.name) ? String(local_geom.name).replace(/\s+/g, "").toLowerCase() : "";
                if (geom_name === norm_val || geom_id === norm_val) resolved_id = local_id;
              });
            }
          } else {
            resolved_id = "";
          }
          this.value = resolved_id;
          if (typeof this.options?.onuserchange === "function")
            this.options.onuserchange(resolved_id, this);
          this.fireToBinding();
        },
        selected: (current_value) ? selected_name : undefined
      });
      this.datalist.element.style.padding = 0;
      this.datalist.bind(this.element);
    }
  }
};