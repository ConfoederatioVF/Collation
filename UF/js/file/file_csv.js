//Initialise functions
{
  if (!global.File)
    /**
     * The namespace for all UF/File utility functions, typically for static methods.
     *
     * @namespace File
     */
    global.File = {};

  /**
   * Loads a CSV file as an array of objects (or positional row arrays when return_arrays is true).
   * @alias File.loadCSVAsArray
   *
   * @param {string} arg0_file_path
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.delimiter=","]
   *  @param {string} [arg1_options.encoding="utf8"]
   *  @param {boolean} [arg1_options.return_arrays=false]
   *  @param {string} [arg1_options.utf] - Encoding alias (e.g. "utf16le").
   *
   * @returns {Array<Object|Array<string>>}
   */
  File.loadCSVAsArray = function (arg0_file_path, arg1_options) {
    //Convert from parameters
    let file_path = arg0_file_path;
    let options = (arg1_options) ? arg1_options : {};

    //Initialise options
    if (!options.delimiter) options.delimiter = ",";
    if (!options.encoding) options.encoding = options.utf ? options.utf : "utf8";

    //Declare local instance variables
    let csv_array;
    let csv_string = fs.readFileSync(file_path, options.encoding).replace(/^\uFEFF/, "");
    let headers;
    let parsed_rows;
    let return_array = [];

    csv_array = csv_string.trim().split(/\r?\n/);
    parsed_rows = csv_array.map(function (arg0_line) {
      return File.parseCSVLine(arg0_line, options);
    });

    if (options.return_arrays) return parsed_rows;
    if (parsed_rows.length === 0) return return_array;

    headers = parsed_rows[0];
    for (let i = 1; i < parsed_rows.length; i++) {
      let local_row = parsed_rows[i];
      let local_row_obj = {};

      for (let x = 0; x < headers.length; x++) {
        let local_header_key = headers[x];
        if (local_header_key)
          local_row_obj[local_header_key] = (local_row[x] !== undefined) ? local_row[x] : null;
      }
      return_array.push(local_row_obj);
    }

    //Return statement
    return return_array;
  };


  /**
   * Loads a CSV file as JSON.
   * @alias File.loadCSVAsJSON
   *
   * @param {string} arg0_file_path
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.delimiter=","]
   *  @param {string} [arg1_options.encoding="utf8"]
   *  @param {string} [arg1_options.mode="vertical"] - Either 'vertical'/'horizontal'. Whether the header is horizontal or vertical.
   *  @param {string} [arg1_options.utf] - Encoding alias (e.g. "utf16le").
   *
   * @returns {Object}
   */
  File.loadCSVAsJSON = function (arg0_file_path, arg1_options) {
    //Convert from parameters
    let file_path = arg0_file_path;
    let options = (arg1_options) ? arg1_options : {};

    //Initialise options
    if (!options.delimiter) options.delimiter = ",";
    if (!options.encoding) options.encoding = options.utf ? options.utf : "utf8";
    if (!options.mode) options.mode = "vertical";

    //Declare local instance variables
    let csv_array;
    let csv_string = fs.readFileSync(file_path, options.encoding).replace(/^\uFEFF/, "");
    let parsed_rows;
    let return_obj = {};

    csv_array = csv_string.trim().split(/\r?\n/);
    parsed_rows = csv_array.map(function (arg0_line) {
      return File.parseCSVLine(arg0_line, options);
    });
    if (parsed_rows.length === 0) return return_obj;

    if (options.mode === "vertical") {
      let headers = parsed_rows[0];
      for (let i = 1; i < parsed_rows.length; i++) {
        let local_row = parsed_rows[i];
        let local_key = local_row[0];
        if (!local_key) continue;

        if (!return_obj[local_key]) {
          return_obj[local_key] = {};
          for (let x = 1; x < headers.length; x++)
            return_obj[local_key][headers[x]] = [];
        }
        for (let x = 1; x < headers.length; x++)
          return_obj[local_key][headers[x]].push((local_row[x] !== undefined) ? local_row[x] : null);
      }
    } else if (options.mode === "horizontal") {
      //In horizontal mode, each column after the first is a key
      let property_names = parsed_rows[0];
      for (let i = 1; i < property_names.length; i++) {
        let local_key = property_names[i];
        if (!local_key) continue;

        if (!return_obj[local_key]) {
          return_obj[local_key] = {};
          for (let x = 1; x < parsed_rows.length; x++) {
            let local_row_label = parsed_rows[x][0];
            return_obj[local_key][local_row_label] = [];
          }
        }
        for (let x = 1; x < parsed_rows.length; x++) {
          let local_row_label = parsed_rows[x][0];
          let local_value = (parsed_rows[x][i] !== undefined) ? parsed_rows[x][i] : null;
          return_obj[local_key][local_row_label].push(local_value);
        }
      }
    }

    //Return statement
    return return_obj;
  };


  /**
   * Parses a single line of CSV.
   * @alias File.parseCSVLine
   *
   * @param {string} arg0_line
   * @param {Object} [arg1_options]
   *  @param {string} [arg1_options.delimiter=","]
   *
   * @returns {Array<string>}
   */
  File.parseCSVLine = function (arg0_line, arg1_options) {
    //Convert from parameters
    let line = arg0_line;
    let options = (arg1_options) ? arg1_options : {};

    //Initialise options
    if (!options.delimiter) options.delimiter = ",";

    //Declare local instance variables
    let current = "";
    let in_quotes = false;
    let result = [];

    for (let i = 0; i < line.length; i++) {
      if (line[i] === '"' && (i === 0 || line[i - 1] !== "\\")) {
        in_quotes = !in_quotes;
      } else if (line[i] === options.delimiter && !in_quotes) {
        result.push(current.trim().replace(/^"|"$/g, "").replace(/""/g, '"'));
        current = "";
      } else {
        current += line[i];
      }
    }
    result.push(current.trim().replace(/^"|"$/g, "").replace(/""/g, '"'));

    //Return statement
    return result;
  };
}
