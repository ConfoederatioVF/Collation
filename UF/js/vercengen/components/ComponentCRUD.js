/**
 * Refer to <span color = "yellow">{@link ve.Component}</span> for methods or fields inherited from this Component's parent such as `.options.attributes` or `.element`.
 *
 * - `arg0_value`: {@link Array}<{@link any}>
 * - `arg1_options`: {@link Object}
 *   - `.draw_function`: {@link function}(v:{@link any}) | {@link Array}<{@link any}> - How to parse Array elements in the dataframe into rows, excluding the selection row.
 *   - `.header`: {@link Array}<{@link string}>
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
 */
ve.CRUD = class extends ve.Component {
  constructor (arg0_value, arg1_options) {
    //Convert from parameters
    let value = (arg0_value) ? arg0_value : [];
    let options = (arg1_options) ? arg1_options : {};
      super(options);
    
    //Initialise options
    if (!options.filters) options.filters = [{ name: "All" }];
    
    //Declare local instance variables
    this.element = document.createElement("div");
      this.element.setAttribute("component", "ve-crud");
      this.element.instance = this;
      HTML.setAttributesObject(this.element, options.attributes);
    this.options = options;
  }
  
  draw () {
    
  }

  filterTable (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
  }
  
  getTable () {
    
  }
};