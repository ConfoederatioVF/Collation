//Initialise functions
{
  if (!global.population_Stadester_rasters) global.population_Stadester_rasters = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  if (!global.StadesterPartitionIO && typeof require !== "undefined")
    try { require(path.join(__dirname, "StadesterPartitionIO.js")); } catch (e) {}

  /**
   * Generates Stadestér Population rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.generatePopulationRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.generatePopulationRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let worker_options = (population_Stadester_rasters.buildWorkerOptions) ?
      population_Stadester_rasters.buildWorkerOptions(options) : Object.assign({}, options);

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Population Rasters",
      task_generator: (year) => {
        return {
          type: "stadester_population_raster",
          options: worker_options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterPopulationRaster(year, options)
    });
  };


  /**
   * Generates Stadestér Rural rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.generateRuralRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.generateRuralRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let worker_options = (population_Stadester_rasters.buildWorkerOptions) ?
      population_Stadester_rasters.buildWorkerOptions(options) : Object.assign({}, options);

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Rural Rasters",
      task_generator: (year) => {
        if (year < -10000) {
          let rural_folder = options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`;
          let output_file_path = path.join(rural_folder, `stadester_rural_${year}.png`);
          let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
          if (fs.existsSync(substrata_file_path)) {
            return {
              type: "copy",
              from_file_path: substrata_file_path,
              output_file_path: output_file_path
            };
          }
        }
        return {
          type: "stadester_rural_raster",
          options: worker_options,
          year: year
        };
      },
      handler: async (year) => population_Stadester_rasters.generateStadesterRuralRaster(year, options)
    });
  };


  /**
   * Generates Stadestér Population raster and reconciles rural population to targets in float32.
   * @alias population_Stadester_rasters.generateStadesterPopulationRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterPopulationRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);

    //Return statement
    return result.pop_file_path;
  };


  /**
   * Generates Stadestér Rural raster for a single year by reconciling with national targets in float32.
   * @alias population_Stadester_rasters.generateStadesterRuralRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.generateStadesterRuralRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let result = await population_Stadester_rasters.reconcileStadesterDemographics(year, options);

    //Return statement
    return result.rural_file_path;
  };


  /**
   * Caches and returns a flat pixel index to ISO3 country code mapping.
   * @alias population_Stadester_rasters.getPixelToGeocodeMapping
   *
   * @returns {Array<string|null>}
   */
  population_Stadester_rasters.getPixelToGeocodeMapping = function () {
    //Declare local instance variables
    let best_dist_sq;
    let colourcodes;
    let geocode_img;
    let geocode_path;
    let land_map;
    let pixel_map;
    let rgb_to_iso3;

    //Guard clauses
    if (global._cached_stadester_pixel_to_geocode)
      return global._cached_stadester_pixel_to_geocode;

    //Function body
    geocode_path = (typeof admin_modern !== "undefined" && admin_modern.input_geocodes_raster) ?
      admin_modern.input_geocodes_raster : `${h1}/admin_modern/geocodes.png`;

    if (!fs.existsSync(geocode_path)) return null;

    colourcodes = (typeof admin_modern !== "undefined" && admin_modern.getISO3ColourcodesObject) ?
      admin_modern.getISO3ColourcodesObject() : {};
    geocode_img = GeoPNG.loadImage(geocode_path);
    pixel_map = new Array(4320*2160);
    rgb_to_iso3 = {};

    for (let colour in colourcodes) {
      let codes = colourcodes[colour];
      if (codes && codes.length > 0) {
        let rgb = colour.split(",").slice(0, 3).join(",");
        rgb_to_iso3[rgb] = codes[0];
      }
    }

    for (let i = 0; i < 4320*2160; i++) {
      let b = i*4;
      let rgb = `${geocode_img.data[b]},${geocode_img.data[b + 1]},${geocode_img.data[b + 2]}`;
      pixel_map[i] = rgb_to_iso3[rgb] || null;
    }

    //Assign 2-pixel coastal fringe so harbour/island cities map to nearest land ISO3 geocode
    best_dist_sq = new Uint8Array(4320*2160);
    land_map = pixel_map.slice();
    best_dist_sq.fill(255);
    for (let i = 0; i < 2160; i++) {
      let row_offset = i*4320;
      for (let x = 0; x < 4320; x++) {
        let idx = row_offset + x;
        let iso = land_map[idx];
        if (!iso) continue;

        let left_iso = land_map[row_offset + ((x + 4319) % 4320)];
        let right_iso = land_map[row_offset + ((x + 1) % 4320)];
        let up_iso = (i > 0) ? land_map[idx - 4320] : iso;
        let down_iso = (i < 2159) ? land_map[idx + 4320] : iso;
        if (left_iso && right_iso && up_iso && down_iso) continue;

        for (let y = -2; y <= 2; y++) {
          let ny = i + y;
          if (ny < 0 || ny >= 2160) continue;
          let n_row = ny*4320;
          for (let z = -2; z <= 2; z++) {
            if (y === 0 && z === 0) continue;
            let nx = (x + z + 4320) % 4320;
            let n_idx = n_row + nx;
            if (!land_map[n_idx]) {
              let dist_sq = y*y + z*z;
              if (dist_sq < best_dist_sq[n_idx]) {
                best_dist_sq[n_idx] = dist_sq;
                pixel_map[n_idx] = iso;
              }
            }
          }
        }
      }
    }

    global._cached_stadester_pixel_to_geocode = pixel_map;

    //Return statement
    return pixel_map;
  };

  population_Stadester_rasters.getPixelToISO2Mapping = population_Stadester_rasters.getPixelToGeocodeMapping;


  /**
   * Prepares density raster (population / land area) in float32.
   * @alias population_Stadester_rasters.prepareDensityRaster
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<string>} output file path
   */
  population_Stadester_rasters.prepareDensityRaster = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;
    let landarea_raster = null;
    let output_file_path = path.join(options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`, `stadester_density_${year}.png`);
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_raster = null;

    //Function body
    if (fs.existsSync(landarea_file))
      landarea_raster = GeoPNG.loadNumberRasterImage(landarea_file, { format: "int32" });
    if (fs.existsSync(pop_file_path))
      pop_raster = GeoPNG.loadNumberRasterImage(pop_file_path, { format: "float32" });

    GeoPNG.saveNumberRasterImage({
      file_path: output_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) {
        let km2 = (landarea_raster && landarea_raster.data[local_index]) ? landarea_raster.data[local_index] : 0;
        let p = (pop_raster && pop_raster.data[local_index]) ? pop_raster.data[local_index] : 0;
        if (km2 <= 0 || p < 0.01) return 0;
        let val = p/km2;
        return isFinite(val) ? val : 0;
      }
    });

    console.log(`- Saved Stadestér Density raster for ${year}: ${output_file_path}`);

    //Return statement
    return output_file_path;
  };


  /**
   * Prepares Stadestér Density rasters in parallel using GeoPNG.processTimeseriesParallel.
   * @alias population_Stadester_rasters.prepareDensityRastersParallel
   *
   * @param {Array<number>} arg0_years
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Array<string>>}
   */
  population_Stadester_rasters.prepareDensityRastersParallel = async function (arg0_years, arg1_options) {
    //Convert from parameters
    let years = arg0_years;
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let default_concurrency = (typeof require !== "undefined") ? Math.min(8, require("os").cpus().length || 4) : 4;
    let input_popc = options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`;
    let intermediate_popd = options.intermediate_popd_folder || `${h2}/population_Stadester/stadester_density_rasters/`;
    let landarea_file = (typeof metadata_HYDE !== "undefined" && metadata_HYDE.input_raster_land_area) ?
      metadata_HYDE.input_raster_land_area : `${h1}/metadata_HYDE/general_rasters/land_area.png`;

    //Function body
    if (!fs.existsSync(intermediate_popd)) fs.mkdirSync(intermediate_popd, { recursive: true });

    //Return statement
    return GeoPNG.processTimeseriesParallel({
      concurrency: options.concurrency || default_concurrency,
      items: years,
      name: "Stadester Density Rasters",
      task_generator: (year) => {
        let output_file_path = path.join(intermediate_popd, `stadester_density_${year}.png`);
        let pop_file_path = path.join(input_popc, `stadester_population_${year}.png`);
        if (!fs.existsSync(pop_file_path) || !fs.existsSync(landarea_file)) return null;

        return {
          type: "raster_operation",
          format: "float32",
          format_1: "float32",
          format_2: "int32",
          input_path_1: pop_file_path,
          input_path_2: landarea_file,
          op: "divide",
          operation: "divide",
          output_path: output_file_path
        };
      },
      handler: async (year) => population_Stadester_rasters.prepareDensityRaster(year, options)
    });
  };


  /**
   * Reconciles Rural and Total Population rasters using national dasymetric rural scaling in float32.
   * Preserves exact urban city populations (`>= 5,000`) and sub-urban settlement populations (`< 5,000`) from `stadester`,
   * anchoring `< 5,000` settlements inside the rural raster so no settlement gridcell ever has less population than the settlement itself.
   * @alias population_Stadester_rasters.reconcileStadesterDemographics
   *
   * @param {number} arg0_year
   * @param {Object} [arg1_options]
   *
   * @returns {Promise<Object>} { pop_file_path, rural_file_path, urban_file_path }
   */
  population_Stadester_rasters.reconcileStadesterDemographics = async function (arg0_year, arg1_options) {
    //Convert from parameters
    let year = parseInt(arg0_year);
    let options = (arg1_options) ? arg1_options : {};

    //Declare local instance variables
    let country_raw_rur = {};
    let country_scalar_r = {};
    let country_scalar_u = {};
    let country_sub = {};
    let country_sub_urb = {};
    let country_urb = {};
    let fallback_scalar_r = 1;
    let fallback_scalar_u = 1;
    let global_raw_rur = 0;
    let global_settled = 0;
    let global_sub = 0;
    let global_sub_urb = 0;
    let global_urb = 0;
    let min_rural_ratio = (options.min_rural_hinterland_ratio !== undefined) ?
      options.min_rural_hinterland_ratio : 0.05;
    let pixel_to_geocode = (options.pixel_to_geocode) ?
      options.pixel_to_geocode : population_Stadester_rasters.getPixelToGeocodeMapping();
    let pop_file_path = path.join(options.input_popc_folder || `${h2}/population_Stadester/stadester_population_rasters/`, `stadester_population_${year}.png`);
    let pop_folder = path.dirname(pop_file_path);
    let raw_rural_data = new Float32Array(4320*2160);
    let rural_data = new Float32Array(4320*2160);
    let rural_file_path = path.join(options.input_rurc_folder || `${h2}/population_Stadester/stadester_rural_rasters/`, `stadester_rural_${year}.png`);
    let rural_folder = path.dirname(rural_file_path);
    let sub_urban_data = null;
    let substrata_file_path = population_Stadester_rasters.getSubstrataRasterPath(year, options);
    let substrata_raster = null;
    let total_data = new Float32Array(4320*2160);
    let total_pixels = 4320*2160;
    let urban_data = new Float32Array(4320*2160);
    let urban_file_path = path.join(options.input_urbc_folder || `${h2}/population_Stadester/stadester_urban_rasters/`, `stadester_urban_${year}.png`);
    let urban_folder = path.dirname(urban_file_path);
    let urban_raster = null;

    //Ensure destination directories exist
    if (!fs.existsSync(pop_folder)) fs.mkdirSync(pop_folder, { recursive: true });
    if (!fs.existsSync(rural_folder)) fs.mkdirSync(rural_folder, { recursive: true });
    if (!fs.existsSync(urban_folder)) fs.mkdirSync(urban_folder, { recursive: true });

    //Guard clauses
    if (year < -10000) {
      if (fs.existsSync(substrata_file_path)) {
        fs.copyFileSync(substrata_file_path, rural_file_path);
        fs.copyFileSync(substrata_file_path, pop_file_path);
        console.log(`- Copied Stadestér Rural & Pop rasters from substrata for ${year}`);
      }
      return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
    }

    //Function body
    if (options.substrata_raster) {
      substrata_raster = options.substrata_raster;
    } else if (fs.existsSync(substrata_file_path)) {
      substrata_raster = GeoPNG.loadNumberRasterImage(substrata_file_path, { format: "float32" });
    }

    if (options.urban_raster) {
      urban_raster = options.urban_raster;
    } else if (fs.existsSync(urban_file_path)) {
      urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    } else {
      await population_Stadester_rasters.generateStadesterUrbanRaster(year, options);
      if (fs.existsSync(urban_file_path))
        urban_raster = GeoPNG.loadNumberRasterImage(urban_file_path, { format: "float32" });
    }

    //Load sub-5k settlement populations from stadester so small settlements are anchored in rural & total rasters
    sub_urban_data = (options.sub_urban_data) ?
      options.sub_urban_data :
      population_Stadester_rasters.getSubUrbanSettlementsData(year, options);

    //Pass 1: Accumulate Substrata target, Urban (5k+) ground truth, Sub-Urban (<5k) settlement ground truth, and Raw Rural hinterland per country
    for (let i = 0; i < total_pixels; i++) {
      let s = (substrata_raster && substrata_raster.data[i]) ? substrata_raster.data[i] : 0;
      let sub_u = (sub_urban_data && sub_urban_data[i]) ? sub_urban_data[i] : 0;
      let u = (urban_raster && urban_raster.data[i]) ? urban_raster.data[i] : 0;
      let settled = u + sub_u;
      let rr = (s > settled) ? (s - settled) : ((s > 0 || settled > 0) ? Math.max(1e-4, ((s > 0) ? s : settled)*0.05) : 0);
      raw_rural_data[i] = rr;

      global_sub += s;
      global_urb += u;
      global_sub_urb += sub_u;
      global_raw_rur += rr;

      if (pixel_to_geocode) {
        let c = pixel_to_geocode[i];
        if (c) {
          country_sub[c] = (country_sub[c] || 0) + s;
          country_urb[c] = (country_urb[c] || 0) + u;
          country_sub_urb[c] = (country_sub_urb[c] || 0) + sub_u;
          country_raw_rur[c] = (country_raw_rur[c] || 0) + rr;
        }
      }
    }

    //Compute per-country scalars
    if (pixel_to_geocode) {
      let all_countries = Object.keys(country_sub);
      for (let i = 0; i < all_countries.length; i++) {
        let c = all_countries[i];
        let raw_r = country_raw_rur[c] || 0;
        let s = country_sub[c];
        let sub_u = country_sub_urb[c] || 0;
        let u = country_urb[c] || 0;
        let settled = u + sub_u;

        if (settled < s) {
          let target_r = s - settled;
          country_scalar_r[c] = (raw_r > 0) ? (target_r/raw_r) : 0;
          country_scalar_u[c] = 1;
        } else {
          let target_r = Math.min(raw_r, settled*min_rural_ratio);
          country_scalar_r[c] = (raw_r > 0) ? (target_r/raw_r) : 0;
          country_scalar_u[c] = 1;
        }
      }
    }

    global_settled = global_urb + global_sub_urb;
    if (global_settled < global_sub) {
      let fallback_target_r = global_sub - global_settled;
      fallback_scalar_r = (global_raw_rur > 0) ? (fallback_target_r/global_raw_rur) : 1;
      fallback_scalar_u = 1;
    } else {
      let fallback_target_r = Math.min(global_raw_rur, global_settled*min_rural_ratio);
      fallback_scalar_r = (global_raw_rur > 0) ? (fallback_target_r/global_raw_rur) : 0;
      fallback_scalar_u = 1;
    }

    //Pass 2: Apply scalars and construct strictly consistent Rural = SubU + Hinterland and Total = Urban + Rural
    for (let i = 0; i < total_pixels; i++) {
      let c = pixel_to_geocode ? pixel_to_geocode[i] : null;
      let sc_r = (c && country_scalar_r[c] !== undefined) ? country_scalar_r[c] : fallback_scalar_r;
      let sc_u = (c && country_scalar_u[c] !== undefined) ? country_scalar_u[c] : fallback_scalar_u;
      let sub_u = (sub_urban_data && sub_urban_data[i]) ? sub_urban_data[i] : 0;
      let r = sub_u + raw_rural_data[i]*sc_r;
      let u = (urban_raster && urban_raster.data[i]) ? urban_raster.data[i]*sc_u : 0;

      rural_data[i] = (r >= 1e-6) ? r : 0;
      urban_data[i] = (u >= 0.01) ? u : 0;
      let tot = urban_data[i] + rural_data[i];
      total_data[i] = (tot >= 1e-6) ? tot : 0;
    }

    //Save Rural, Total Population, and synchronised Urban rasters
    GeoPNG.saveNumberRasterImage({
      file_path: rural_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return rural_data[local_index]; }
    });

    GeoPNG.saveNumberRasterImage({
      file_path: pop_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return total_data[local_index]; }
    });

    GeoPNG.saveNumberRasterImage({
      file_path: urban_file_path,
      format: "float32",
      height: 2160,
      width: 4320,
      function: function (local_index) { return urban_data[local_index]; }
    });

    console.log(`- Saved reconciled Stadestér Urban, Rural & Pop rasters for ${year}: Total=${pop_file_path}`);

    //Return statement
    return { pop_file_path: pop_file_path, rural_file_path: rural_file_path, urban_file_path: urban_file_path };
  };
}
