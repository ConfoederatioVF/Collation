//Initialise functions
{
  if (!global.population_Stadester) global.population_Stadester = {};
  
  /**
   * Main class interface for the Stadestér Historical GIS City & Raster Demographics pipeline.
   * Synthetically merges Populstat, Chandler-Modelski, DeVries, and Buringh sources into UUD,
   * models concentric walkability buffers, and outputs float32 equirectangular population rasters.
   * 
   * @class population_Stadester
   */
  global.population_Stadester = class {
    static bf = `${h2}/population_Stadester/`;
    static raw_folder = `${h1}/population_Stadester/`;
    
    static input_popc_folder = `${this.bf}stadester_population_rasters/`;
    static input_rurc_folder = `${this.bf}stadester_rural_rasters/`;
    static input_urbc_folder = `${this.bf}stadester_urban_rasters/`;
    
    static intermediate_base_folder = `${this.bf}stadester_base_rasters/`;
    static intermediate_ghsl_folder = `${this.bf}stadester_ghsl_rasters/`;
    static intermediate_popd_folder = `${this.bf}stadester_density_rasters/`;
    
    static input_substrata_folder = `${h3}/population_Substrata.outlier_removal/rasters_4.interpolated_to_GHSL/`;
    static input_substrata_fallback_folder = `${h3}/population_Substrata.outlier_removal/rasters_3.scaled_to_global/`;
    
    static file_uud_cities = `${this.raw_folder}uud/processed_uud_cities.json`;
    static file_stadester_cities = `${this.raw_folder}uud/stadester_cities.json`;
    static file_flattened_stadester = `${this.raw_folder}uud/flattened_stadester_cities.json`;
    static file_processed_stadester = `${this.raw_folder}uud/processed_stadester_cities.json`;
    static file_stadester_areas = `${this.raw_folder}uud/stadester_areas.json`;
    static file_stadester_final = `${this.raw_folder}uud/stadester.json`;
    static file_stadester_ghsl = `${this.raw_folder}uud/stadester_ghsl.json`;
    
    /**
     * Initialises UUD from raw modified sources in 1.data_raw/population_Stadester/.
     * @param {Object} [arg0_options]
     * 
     * @returns {Object}
     */
    static A_initialiseUUD (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let uud_obj = population_Stadester_uud.initialiseUUD({
        raw_folder: this.raw_folder,
        ...options
      });
      
      //Ensure output directory exists
      let parent_dir = path.dirname(path.resolve(this.file_uud_cities));
      if (!fs.existsSync(parent_dir)) fs.mkdirSync(parent_dir, { recursive: true });
      fs.writeFileSync(this.file_uud_cities, JSON.stringify(uud_obj, null, 2));
      console.log(`- Saved raw UUD dataset to ${this.file_uud_cities}.`);
      
      //Return statement
      return uud_obj;
    }
    
    /**
     * Fills temporal gaps via interpolation across HYDE domain years.
     * @param {Object} [arg0_options]
     * 
     * @returns {Object}
     */
    static B_interpolateUUD (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let uud_obj = options.uud_obj;
      if (!uud_obj && fs.existsSync(this.file_uud_cities))
        uud_obj = JSON.parse(fs.readFileSync(this.file_uud_cities, "utf8"));
      
      uud_obj = population_Stadester_uud.interpolateUUD(uud_obj, options);
      fs.writeFileSync(this.file_uud_cities, JSON.stringify(uud_obj, null, 2));
      console.log(`- Saved interpolated UUD dataset to ${this.file_uud_cities}.`);
      
      //Return statement
      return uud_obj;
    }
    
    /**
     * Converts UUD to Stadestér format, flattens overlapping metros, and applies error fixes.
     * @param {Object} [arg0_options]
     * 
     * @returns {Object}
     */
    static C_processUUDToStadester (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let stadester_obj;
      let uud_obj = options.uud_obj;
      if (!uud_obj && fs.existsSync(this.file_uud_cities))
        uud_obj = JSON.parse(fs.readFileSync(this.file_uud_cities, "utf8"));
      
      stadester_obj = population_Stadester_uud.parseUUDToStadester(uud_obj);
      fs.writeFileSync(this.file_stadester_cities, JSON.stringify(stadester_obj, null, 2));
      
      stadester_obj = population_Stadester_uud.flattenStadesterMetros(stadester_obj);
      fs.writeFileSync(this.file_flattened_stadester, JSON.stringify(stadester_obj, null, 2));
      
      stadester_obj = population_Stadester_uud.fixStadesterErrors(stadester_obj);
      fs.writeFileSync(this.file_processed_stadester, JSON.stringify(stadester_obj, null, 2));
      console.log(`- Saved processed Stadestér dataset to ${this.file_processed_stadester}.`);
      
      //Return statement
      return stadester_obj;
    }
    
    /**
     * Processes baseline areas, rolling Angel density, regional typologies, and Clark centre densities.
     * @param {Object} [arg0_options]
     * 
     * @returns {Object}
     */
    static D_processCitiesAreas (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let stadester_obj = options.stadester_obj;
      if (!stadester_obj && fs.existsSync(this.file_processed_stadester))
        stadester_obj = JSON.parse(fs.readFileSync(this.file_processed_stadester, "utf8"));
      
      stadester_obj = population_Stadester_density.processCitiesAreas(stadester_obj, {
        raw_folder: this.raw_folder,
        ...options
      });
      fs.writeFileSync(this.file_stadester_areas, JSON.stringify(stadester_obj, null, 2));
      console.log(`- Saved Stadestér areas to ${this.file_stadester_areas}.`);
      
      //Return statement
      return stadester_obj;
    }
    
    /**
     * Computes and caches concentric radial walkability rings for all cities across years.
     * @param {Object} [arg0_options]
     * 
     * @returns {Object}
     */
    static E_cacheRadialBuffers (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let stadester_obj = options.stadester_obj;
      if (!stadester_obj && fs.existsSync(this.file_stadester_areas))
        stadester_obj = JSON.parse(fs.readFileSync(this.file_stadester_areas, "utf8"));
      
      stadester_obj = population_Stadester_density.cacheRadialBuffers(stadester_obj);
      fs.writeFileSync(this.file_stadester_final, JSON.stringify(stadester_obj, null, 2));
      console.log(`- Saved final radially-buffered Stadestér dataset to ${this.file_stadester_final}.`);
      
      //Return statement
      return stadester_obj;
    }
    
    /**
     * Ensures all input, output, and intermediate directories exist.
     * @alias population_Stadester.ensureDirectories
     */
    static ensureDirectories () {
      let dirs = [
        this.input_popc_folder,
        this.input_rurc_folder,
        this.input_urbc_folder,
        this.intermediate_base_folder,
        this.intermediate_ghsl_folder,
        this.intermediate_popd_folder,
        path.dirname(path.resolve(this.file_uud_cities))
      ];
      for (let i = 0; i < dirs.length; i++)
        if (!fs.existsSync(dirs[i])) fs.mkdirSync(dirs[i], { recursive: true });
    }
    
    /**
     * Generates Base rasters in float32 with 2px south bug fixed and annular sampling corrected.
     * @param {Object} [arg0_options]
     * 
     * @returns {Promise<Array<string>>}
     */
    static async F_generateBaseRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : [1800];
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Preload stadester_obj once if available to avoid multi-thread 300MB re-parsing
      if (!options.stadester_obj && fs.existsSync(this.file_stadester_final)) {
        console.log(`- Preloading Stadestér master dataset (${this.file_stadester_final})...`);
        options.stadester_obj = JSON.parse(fs.readFileSync(this.file_stadester_final, "utf8"));
      }
      
      //Return statement
      return population_Stadester_rasters.generateBaseRastersParallel(years, {
        intermediate_base_folder: this.intermediate_base_folder,
        ...options
      });
    }
    
    /**
     * Merges Base rasters with GHSL urban rasters into float32 Urban rasters.
     * @param {Object} [arg0_options]
     * 
     * @returns {Promise<Array<string>>}
     */
    static async G_generateUrbanRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : [1800];
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Return statement
      return population_Stadester_rasters.generateUrbanRastersParallel(years, {
        input_urbc_folder: this.input_urbc_folder,
        intermediate_base_folder: this.intermediate_base_folder,
        ...options
      });
    }
    
    /**
     * Dasymetrically subtracts Urban from substrata to produce float32 Rural rasters.
     * @param {Object} [arg0_options]
     * 
     * @returns {Promise<Array<string>>}
     */
    static async H_generateRuralRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : [1800];
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Return statement
      return population_Stadester_rasters.generateRuralRastersParallel(years, {
        input_rurc_folder: this.input_rurc_folder,
        input_urbc_folder: this.input_urbc_folder,
        ...options
      });
    }
    
    /**
     * Reconciles Total Population rasters to global targets and regenerates Rural in float32.
     * @param {Object} [arg0_options]
     * 
     * @returns {Promise<Array<string>>}
     */
    static async I_generatePopulationRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : [1800];
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Return statement
      return population_Stadester_rasters.generatePopulationRastersParallel(years, {
        input_popc_folder: this.input_popc_folder,
        input_rurc_folder: this.input_rurc_folder,
        input_urbc_folder: this.input_urbc_folder,
        ...options
      });
    }
    
    /**
     * Prepares Density rasters (pop / land area) in float32 format.
     * @param {Object} [arg0_options]
     * 
     * @returns {Promise<Array<string>>}
     */
    static async J_prepareIntermediates (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let hyde_years = (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : [1800];
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Return statement
      return population_Stadester_rasters.prepareDensityRastersParallel(years, {
        input_popc_folder: this.input_popc_folder,
        intermediate_popd_folder: this.intermediate_popd_folder,
        ...options
      });
    }
    
    /**
     * Repairs GHSL city names across an urban dataset using the GHSL source file.
     * @param {Object} [arg0_options]
     *  @param {Object} [arg0_options.cities_obj]
     *  @param {string} [arg0_options.file]
     *  @param {boolean} [arg0_options.save=true]
     * 
     * @returns {Object}
     */
    static repairGHSLCityNames (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let cities_obj = options.cities_obj;
      let target_file = options.file || this.file_stadester_final;
      
      //Function body
      if (!cities_obj && fs.existsSync(target_file))
        cities_obj = JSON.parse(fs.readFileSync(target_file, "utf8"));
      
      if (cities_obj) {
        population_Stadester_uud.repairGHSLCityNames(cities_obj, options);
        if (options.save !== false && target_file)
          fs.writeFileSync(target_file, JSON.stringify(cities_obj, null, 2));
      }
      
      //Return statement
      return cities_obj;
    }
    
    /**
     * Builds and saves unified Stadestér GHSL dataset with clean repaired city names.
     * @param {Object} [arg0_options]
     *  @param {boolean} [arg0_options.save=true]
     * 
     * @returns {Object}
     */
    static getStadesterGHSLObject (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Declare local instance variables
      let parent_dir;
      let result;
      
      //Function body
      result = population_Stadester_uud.getStadesterGHSLObject({
        raw_folder: this.raw_folder,
        ...options
      });
      
      if (options.save !== false) {
        parent_dir = path.dirname(path.resolve(this.file_stadester_ghsl));
        if (!fs.existsSync(parent_dir)) fs.mkdirSync(parent_dir, { recursive: true });
        fs.writeFileSync(this.file_stadester_ghsl, JSON.stringify(result, null, 2));
        console.log(`- Saved repaired Stadestér GHSL dataset to ${this.file_stadester_ghsl}.`);
      }
      
      //Return statement
      return result;
    }
    
    /**
     * Resolves substrata raster path from population_Substrata.outlier_removal in float32.
     * @alias population_Stadester.getSubstrataRasterPath
     * 
     * @param {number} arg0_year
     * @param {Object} [arg1_options]
     * 
     * @returns {string}
     */
    static getSubstrataRasterPath (arg0_year, arg1_options) {
      //Convert from parameters
      let year = arg0_year;
      let options = (arg1_options) ? arg1_options : {};
      
      //Return statement
      return population_Stadester_rasters.getSubstrataRasterPath(year, options);
    }
    
    /**
     * Master pipeline runner to execute all steps sequentially or selective steps via options.
     * @param {Object} [arg0_options]
     *  @param {Array<string>} [arg0_options.exclude] - Step letters to skip e.g. ["A", "B", "C", "D", "E"]
     *  @param {Array<number>} [arg0_options.years] - Array of years to process
     *  @param {number} [arg0_options.concurrency=4] - Parallel concurrency limit
     */
    static async processRasters (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};
      
      //Initialise options
      if (!options.exclude) {
        options.exclude = [];
        if (fs.existsSync(this.file_processed_stadester) || fs.existsSync(this.file_stadester_areas))
          options.exclude = ["A", "B", "C", "D", "E"];
      }
      
      this.ensureDirectories();
      console.log(`- Launching population_Stadester master pipeline...`);
      
      if (!options.exclude.includes("A")) this.A_initialiseUUD(options);
      if (!options.exclude.includes("B")) this.B_interpolateUUD(options);
      if (!options.exclude.includes("C")) this.C_processUUDToStadester(options);
      if (!options.exclude.includes("D")) this.D_processCitiesAreas(options);
      if (!options.exclude.includes("E")) this.E_cacheRadialBuffers(options);
      
      if (!options.exclude.includes("F")) await this.F_generateBaseRasters(options);
      if (!options.exclude.includes("G")) await this.G_generateUrbanRasters(options);
      if (!options.exclude.includes("H")) await this.H_generateRuralRasters(options);
      if (!options.exclude.includes("I")) await this.I_generatePopulationRasters(options);
      if (!options.exclude.includes("J")) await this.J_prepareIntermediates(options);
      
      console.log(`- Successfully completed population_Stadester pipeline.`);
    }
  };
}
