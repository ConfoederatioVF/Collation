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
 *   - `.onsearch`: {@link function}(v:{@link string}, e:{@link ve.CRUD})
 *   - `.onselect`: {@link function}(v:{@link boolean}, e:{ checkbox:{@link ve.Checkbox}, value:{@link any} })
 *   - `.searchbar_filters`: {@link Array}<{@link number>} - The column indices to target when filtering search results.
 *   - `.searchbar_header_components`: {@link Array}<{@link ve.Component}>
 *   - `.searchbar_options`: {@link Object} - The options to pass to the {@link ve.SearchSelect} for the CRUD.
 *   - `.select_options`: {@link Object}
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
      header_components_obj: {
        filter_columns_when_searching: veButton(() => {
          if (this.filter_window) this.filter_window.close();
          this.filter_window = new ve.Window({
            
          }, {
            name: "Filter Search",
            can_rename: false
          })
        }, {
          name: "<icon>filter_alt</icon>",
          tooltip: "Filter Columns When Searching",
          style: {
            display: "block",
            marginLeft: "auto"
          }
        }),
        ...this.options.searchbar_header_components
      },
      hide_filter: true,
      onuserchange: (v, e) => {
        //Declare local instance variables
        let search_value = e.search_value;
        
        //Filter table by search_value
        if (this.options.onsearch) this.options.onsearch(search_value, this);
        this.filterTable(search_value);
      },
      ...this.options.searchbar_options
    });
    this.table_array = this.getTable();
    this.table = new ve.Table(this.table_array, {
      disable_hide_columns: [0],
      ...this.options.table_options
    });
    
    //Bind elements in order
    this.searchbar.bind(this.element);
    this.table.bind(this.element);
  }
  
  filterTable (arg0_search_string) {
    //Convert from parameters
    let search_string = (arg0_search_string) ? arg0_search_string : "";
      search_string = search_string.trim().toLowerCase();
    
    //Declare local instance variables
    let filtered_table_array = [];
    let searchbar_columns = [];
    
    //Internal guard clause if search_string is empty
    if (search_string.length === 0) {
      filtered_table_array = this.getTable();
      this.table.v = filtered_table_array;
      
      //Return statement
      return filtered_table_array;
    }
    
    //Set searchbar_columns
    if (!this.options.searchbar_filters || this.options.searchbar_filters?.length === 0) {
      for (let i = 0; i < this.options.header.length; i++)
        searchbar_columns.push(i);
    } else {
      searchbar_columns = this.options.searchbar_filters;
    }
    
    //Push header to filtered_table_array first
    filtered_table_array.push(this.options.header);
    
    //Iterate over all rows in this.table_array
    for (let i = 1; i < this.table_array.length; i++) {
      let is_valid = false;
      
      //Iterate over all searchbar_columns in this.table_array for filters to see if "data-value" or .innerText has a valid substring
      for (let x = 0; x < searchbar_columns.length; x++) {
        let local_cell = this.table_array[i][x];
        let local_values = [];
        
        if (local_cell instanceof HTMLElement) {
          let data_value = local_cell.getAttribute("data-value");
          
          if (data_value) local_values.push(data_value);
          local_values.push(local_cell.innerText);
        } else {
          local_values.push(String(local_cell));
        }
        
        //Iterate over local_values and determine if any of them are valid against search_string
        for (let y = 0; y < local_values.length; y++) {
          let local_value = local_values[y].trim().toLowerCase();
          
          if (local_value.indexOf(search_string) !== -1) {
            is_valid = true;
            break;
          }
        }
      }
      
      if (is_valid) filtered_table_array.push(this.table_array[i]);
    }
    
    //Set this.table.v
    this.table.v = filtered_table_array;
    
    //Return statement
    return filtered_table_array;
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
            
            if (this.options.onselect) {
              this.options.onselect(v, {
                checkbox: e,
                value: this.value[i]
              });
            } else {
              this.value[i].selected = v;
            }
            this.redrawSelections();
          },
          ...this.options.select_options
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

//Functional binding

/**
 * @returns {ve.CRUD}
 */
veCRUD = function () {
  //Return statement
  return new ve.CRUD(...arguments);
};