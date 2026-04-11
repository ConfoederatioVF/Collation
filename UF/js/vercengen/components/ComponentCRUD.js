/**
 * Refer to <span color = "yellow">{@link ve.Component}</span> for methods or fields inherited from this Component's parent such as `.options.attributes` or `.element`.
 *
 * - `arg0_value`: {@link Array}<{@link any}>
 * - `arg1_options`: {@link Object}
 *   - `.header=["Selected", "Index", ...]`: {@link Array}<{@link string}>
 *   - `.special_function`: {@link function}(v:{@link any}) | {@link Array}<{@link any}> - How to parse Array elements in the dataframe into rows, excluding the selection row.
 *
 *   - `.filters`: {@link Array}<{@link Object}> - [{ name: "All" }] by default.
 *     - `[n].name`: {@link string} - The name of the given tab.
 *     - `[n].special_function`: {@link function}(v:{@link any}) | {@link boolean} - Boolean determines whether to include result in tab. If this field does not exist, all elements are taken as valid.
 *   - `.filter_interface`: {@link ve.Interface} - The interface to provide for the filter.
 *   - `.hide_searchbar=false`: {@link boolean}
 *   - `.searchbar_filters`: {@link Array}<{@link number>} - The column indices to target when filtering search results.
 *   - `.searchbar_options`: {@link Object} - The options to pass to the {@link ve.SearchSelect} for the CRUD.
 *   - `.table_options`: {@link Object} - The options to pass to the {@link ve.Table} for the CRUD.
 *   
 * ##### Instance:
 * - `.page_menu`: {@link ve.PageMenu} - The PageMenu component responsible for containing CRUD sub-pages.
 * - `.searchbar`: {@link ve.SearchSelect}
 * - `.table`: {@link ve.Table}
 * - `.table_array`: {@link Array}<{@link Array}<{@link any}>>
 * - `.table_map`: {@link Array}<{@link Object}{ <value_id>: { value:{@link any}, row:{@link any}[] } }>
 */
ve.CRUD = class extends ve.Component {
  constructor (arg0_value, arg1_options) {
    //Convert from parameters
    let value = (arg0_value) ? Array.toArray(arg0_value) : [];
    let options = (arg1_options) ? arg1_options : {};
      super(options);
    
    //Initialise options
    if (!options.filters) options.filters = [{ name: "All" }];
    let new_header = ["Selected", "Index"];
      if (options.header) new_header = new_header.concat(options.header);
      options.header = new_header;
    
    //Declare local instance variables
    this.element = document.createElement("div");
      this.element.setAttribute("component", "ve-crud");
      this.element.instance = this;
      HTML.setAttributesObject(this.element, options.attributes);
    this.options = options;
    this.value = value;
    
    //Call this.draw()
    this.from_binding_fire_silently = true;
    this.v = value;
    delete this.from_binding_fire_silently;
  }
  
  get v () {
    //Return statement
    return this.value;
  }
  
  set v (arg0_value) {
    //Convert from parameters
    let value = Array.toArray(arg0_value);
    
    //Set value and call draw
    this.value = value;
    this.draw();
  }
  
  draw () {
    //Declare local instance variables
    this.element.innerHTML = "";
    this.searchbar = new ve.SearchSelect({}, {
      hide_filter: true,
      onuserchange: (v, e) => {
        //Declare local instance variables
        let search_value = e.search_value;
      },
      ...this.options.searchbar_options
    });
    this.table = new ve.Table(this.getTable(), {
      disable_hide_columns: [0]
    });
    
    //Bind elements in order
    this.searchbar.bind(this.element);
    this.table.bind(this.element);
  }

  filterTable (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
  }
  
  getTable () {
    //Declare local instance variables
    this.table_array = []; //[[select_button, ...draw_function(value[n])], ...]
    this.table_map = {}; //{ <value_id>: { value: any, row: any[] } }
    
    //Set header
    this.table_array.push(this.options.header);
    
    //Populate table_array from value
    for (let i = 0; i < this.value.length; i++) {
      let local_array = [];
      let select_component;
      
      //Set local_array
      //Select column
      {
        select_component = veCheckbox(this.value[i]?.selected, {
          attributes: {
            "crud-select": "true",
            "data-value": String(this.value[i]?.selected)
          },
          onuserchange: (v, e) => {
            e.element.setAttribute("data-value", String(v));
            this.value[i].selected = v;
          }
        });
        select_component.element.value = this.value[i];
        
        local_array.push(select_component.element);
      }
      
      //Push index
      local_array.push(i);
      
      //Push everything else from this.options.special_function
      let row_value = this.options.special_function(this.value[i]);
      
      if (row_value)
        for (let x = 0; x < row_value.length; x++)
          local_array.push(row_value[x]);
      
      //Push local_array to table_array
      this.table_array.push(local_array);
      
      this.table_map[(this.value[i].id) ? this.value[i].id : i] = {
        value: this.value[i],
        row: local_array
      };
    }
    
    //Return statement
    return this.table_array;
  }
  
  /**
   * Redraws selection boxes for the present component.
   * - Method of: {@link ve.CRUD}
   */
  redrawSelections () {
    Object.iterate(this.table_map, (local_key, local_value) => {
      let is_selected = local_value.value?.selected;
      let local_checkbox = local_value.row[0].instance;
      
      local_checkbox.v = is_selected;
      local_checkbox.element.setAttribute("data-value", is_selected);
    });
  }
};