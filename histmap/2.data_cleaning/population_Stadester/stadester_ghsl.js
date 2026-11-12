//Initialise functions
{
  if (!global.population_Stadester_ghsl) global.population_Stadester_ghsl = {};
  if (!global.population_Stadester_uud) global.population_Stadester_uud = {};
  if (!global.population_Stadester_config && typeof require !== "undefined")
    try { require(path.join(__dirname, "config", "stadester_config.js")); } catch (e) {}
  
  /**
   * Returns all normalised name tokens for a Stadestér city object for GHSL cluster matching.
   * @alias population_Stadester_ghsl.getNormalisedCityNames
   * 
   * @param {Object} arg0_city_obj
   * 
   * @returns {Array<string>}
   */
  population_Stadester_ghsl.getNormalisedCityNames = function (arg0_city_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    
    //Declare local instance variables
    let all_raw_names;
    let name_set = new Set();
    let norm_name;
    
    //Guard clauses
    if (!city_obj) return [];
    
    //Function body
    all_raw_names = (population_Stadester_uud && population_Stadester_uud.getAllCityNames) ?
      population_Stadester_uud.getAllCityNames(city_obj) : [];
    
    for (let i = 0; i < all_raw_names.length; i++) {
      norm_name = population_Stadester_ghsl.normaliseGHSLName(all_raw_names[i]);
      if (norm_name) name_set.add(norm_name);
    }
    if (city_obj.name) {
      norm_name = population_Stadester_ghsl.normaliseGHSLName(city_obj.name);
      if (norm_name) name_set.add(norm_name);
    }
    
    //Return statement
    return Array.from(name_set);
  };
  
  /**
   * Generates a unified Stadestér GHSL dataset combining historical Stadestér entries and modern GHSL clusters.
   * All GHSL and historical city names are repaired, and .region strings are assigned via Voronoi sampling.
   * @alias population_Stadester_ghsl.getStadesterGHSLObject
   * 
   * @param {Object} [arg0_options]
   *  @param {string} [arg0_options.ghsl_file]
   *  @param {Object} [arg0_options.ghsl_obj]
   *  @param {string} [arg0_options.raw_folder]
   *  @param {Object} [arg0_options.stadester_obj]
   *  @param {string} [arg0_options.voronoi_file]
   * 
   * @returns {Object}
   */
  population_Stadester_ghsl.getStadesterGHSLObject = function (arg0_options) {
    //Convert from parameters
    let options = (arg0_options) ? arg0_options : {};
    
    //Declare local instance variables
    let all_ghsl_cities;
    let all_region_keys;
    let all_return_keys;
    let all_stadester_cities;
    let colour_to_region = {};
    let cutoff_year = (global.population_Stadester_config && global.population_Stadester_config.cutoff_year) ?
      global.population_Stadester_config.cutoff_year : 1975;
    let ghsl_candidates = [];
    let ghsl_obj = options.ghsl_obj;
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let raw_folder = options.raw_folder ? options.raw_folder : `${h1}/population_Stadester/`;
    let region_defines;
    let return_obj = {};
    let stadester_candidates = [];
    let stadester_obj = options.stadester_obj;
    let voronoi_candidates = [];
    let voronoi_png = null;
    
    //Function body
    population_Stadester_uud.loadGHSLCsvNames();
    
    //1. Load GHSL dataset (modern clusters 1975-2025)
    if (!ghsl_obj) {
      ghsl_candidates = [
        options.ghsl_file,
        path.join(raw_folder, "ghsl", "ghsl.json"),
        path.join(h1, "population_GHSL", "ghsl.json"),
        path.join(h1, "population_Stadester", "ghsl", "ghsl.json"),
        "E:/Active Projects/Project 2136 - Stadestér/output/ghsl.json",
        "D:/Project 1436 - Dataview/data/stadester/ghsl.json"
      ];
      for (let i = 0; i < ghsl_candidates.length; i++) {
        if (ghsl_candidates[i] && fs.existsSync(ghsl_candidates[i])) {
          try {
            ghsl_obj = JSON.parse(fs.readFileSync(ghsl_candidates[i], "utf8"));
            console.log(`- Loaded GHSL modern clusters from ${ghsl_candidates[i]}.`);
            break;
          } catch (e) {
            console.warn(`- Failed to read GHSL from ${ghsl_candidates[i]}:`, e);
          }
        }
      }
    }
    
    if (ghsl_obj) {
      all_ghsl_cities = Object.keys(ghsl_obj);
      for (let i = 0; i < all_ghsl_cities.length; i++) {
        let key_str = all_ghsl_cities[i].startsWith("ghsl-") ?
          all_ghsl_cities[i] : `ghsl-${all_ghsl_cities[i]}`;
        let local_city = JSON.parse(JSON.stringify(ghsl_obj[all_ghsl_cities[i]]));
        local_city.key = key_str;
        return_obj[key_str] = local_city;
      }
      console.log(`- Appended ${all_ghsl_cities.length} modern GHSL entries.`);
    }
    
    //2. Load historical Stadestér dataset
    if (!stadester_obj) {
      stadester_candidates = [
        options.stadester_file,
        path.join(raw_folder, "uud", "stadester.json"),
        path.join(raw_folder, "uud", "stadester_areas.json"),
        "E:/Active Projects/Project 2136 - Stadestér/input/uud/stadester.json",
        "E:/Active Projects/Project 2136 - Stadestér/output/stadester.json"
      ];
      
      for (let i = 0; i < stadester_candidates.length; i++) {
        if (stadester_candidates[i] && fs.existsSync(stadester_candidates[i])) {
          try {
            let candidate_data = JSON.parse(fs.readFileSync(stadester_candidates[i], "utf8"));
            let candidate_count = Object.keys(candidate_data).length;
            if (candidate_count > 0) {
              stadester_obj = candidate_data;
              console.log(`- Loaded historical Stadestér cities from ${stadester_candidates[i]} (${candidate_count} cities).`);
              break;
            }
          } catch (e) {
            console.warn(`- Failed to read Stadestér cities from ${stadester_candidates[i]}:`, e);
          }
        }
      }
    }
    
    if (stadester_obj) {
      all_stadester_cities = Object.keys(stadester_obj);
      for (let i = 0; i < all_stadester_cities.length; i++) {
        let key_str = all_stadester_cities[i].startsWith("stadester-") ?
          all_stadester_cities[i] : `stadester-${all_stadester_cities[i]}`;
        let local_city = JSON.parse(JSON.stringify(stadester_obj[all_stadester_cities[i]]));
        if (!local_city.coords) continue;
        
        let keys_to_truncate = ["area", "density", "population"];
        for (let x = 0; x < keys_to_truncate.length; x++) {
          if (local_city[keys_to_truncate[x]]) {
            let year_keys = Object.keys(local_city[keys_to_truncate[x]]);
            for (let y = 0; y < year_keys.length; y++) {
              if (parseInt(year_keys[y]) >= cutoff_year)
                delete local_city[keys_to_truncate[x]][year_keys[y]];
            }
          }
        }
        
        //Lamphun, Thailand geolocation fix
        if (key_str === "stadester-Lamphun-Thailand" || key_str.toLowerCase().includes("lamphun")) {
          if (local_city.coords && local_city.coords[0] < 10)
            local_city.coords = [18.5744357, 99.00369719999999];
        }
        
        //Champotón (Chakanputun), Mexico geolocation fix
        if (key_str === "stadester-Champotón-Mexico" || key_str.toLowerCase().includes("champot") || key_str.toLowerCase().includes("chakanputun"))
          local_city.coords = [19.3471645, -90.7200237];
        
        //Múgica, Michoacán, Mexico geolocation fix
        if (key_str === "stadester-Múgica-Mexico" || key_str.toLowerCase().includes("múgica")) {
          if (local_city.coords && local_city.coords[0] > 20)
            local_city.coords = [19.01944, -102.10889];
        }
        
        //Regularize Trujillo, Peru historical curve to remove cubic spline vacuum sawtooth
        if (key_str.toLowerCase().includes("trujillo") && (key_str.includes("Peru") || key_str.includes("peru"))) {
          if (local_city.population) {
            let trujillo_anchors = {
              1200: 20000,
              1300: 20000,
              1400: 26666,
              1791: 9000,
              1861: 8000,
              1876: 11000,
              1890: 14000,
              1896: 45000,
              1900: 48372,
              1910: 56803,
              1920: 65234,
              1925: 70000,
              1930: 73665,
              1940: 82095,
              1950: 90526,
              1961: 99800,
              1971: 242000,
              1974: 331100
            };
            let anchor_years = Object.keys(trujillo_anchors).map(Number).sort((a, b) => a - b);
            let pop_years = Object.keys(local_city.population).map(Number).sort((a, b) => a - b);
            for (let y = 0; y < pop_years.length; y++) {
              let yr = pop_years[y];
              if (yr >= cutoff_year) continue;
              if (trujillo_anchors[yr] !== undefined) {
                local_city.population[yr] = trujillo_anchors[yr];
              } else if (yr <= anchor_years[0]) {
                local_city.population[yr] = trujillo_anchors[anchor_years[0]];
              } else if (yr >= anchor_years[anchor_years.length - 1]) {
                local_city.population[yr] = trujillo_anchors[anchor_years[anchor_years.length - 1]];
              } else {
                let high = anchor_years[anchor_years.length - 1];
                let low = anchor_years[0];
                for (let a = 0; a < anchor_years.length - 1; a++) {
                  if (yr >= anchor_years[a] && yr <= anchor_years[a + 1]) {
                    low = anchor_years[a];
                    high = anchor_years[a + 1];
                    break;
                  }
                }
                let frac = (yr - low)/(high - low);
                local_city.population[yr] = Math.round(trujillo_anchors[low] + frac*(trujillo_anchors[high] - trujillo_anchors[low]));
              }
            }
          }
        }
        
        //Remove anachronistic antiquity entries (-500, 0) from Taipei
        if (key_str.toLowerCase().includes("taipei") || key_str.toLowerCase().includes("t'aipei")) {
          let taipei_props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let t = 0; t < taipei_props.length; t++) {
            if (local_city[taipei_props[t]]) {
              let yr_keys = Object.keys(local_city[taipei_props[t]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) < 1700)
                  delete local_city[taipei_props[t]][yr_keys[y]];
              }
            }
          }
        }
        
        //Ukrainian archaeological megasites (e.g. Maydanets) lapse after antiquity
        if (key_str.toLowerCase().includes("maydanets") || key_str.toLowerCase().includes("maidanets")) {
          let maydanets_props = ["area", "density", "population", "rni", "radial_buffers", "centre_density"];
          for (let m = 0; m < maydanets_props.length; m++) {
            if (local_city[maydanets_props[m]]) {
              let yr_keys = Object.keys(local_city[maydanets_props[m]]);
              for (let y = 0; y < yr_keys.length; y++) {
                if (parseInt(yr_keys[y]) >= 0)
                  delete local_city[maydanets_props[m]][yr_keys[y]];
              }
            }
          }
          if (local_city.population)
            local_city.population["-999"] = 0;
        }
        
        local_city.key = key_str;
        return_obj[key_str] = local_city;
      }
      
      //Inject Vaduz into Stadestér GHSL dataset if not present
      if (!return_obj["stadester-Vaduz-Liechtenstein"] && (!stadester_obj || !stadester_obj["Vaduz-Liechtenstein"])) {
        return_obj["stadester-Vaduz-Liechtenstein"] = {
          name: "Vaduz",
          country: "Liechtenstein",
          elevation: 455,
          key: "stadester-Vaduz-Liechtenstein",
          coords: [47.141, 9.521],
          original_names: ["vaduz"],
          other_names: ["Vaduz"],
          population: {
            "1400": 300,
            "1500": 400,
            "1600": 500,
            "1700": 600,
            "1800": 800,
            "1900": 1000,
            "1910": 1300,
            "1920": 1400,
            "1930": 1600,
            "1940": 2000,
            "1950": 2700,
            "1960": 3400,
            "1970": 3900,
            "1980": 4600,
            "1990": 4900,
            "2000": 5000,
            "2010": 5200,
            "2020": 5700
          },
          region: "europe",
          type: "manual"
        };
      }
      
      //Inject Macau into Stadestér GHSL dataset if not present
      if (!return_obj["stadester-Macau-Macao"] && (!stadester_obj || !stadester_obj["Macau-Macao"])) {
        return_obj["stadester-Macau-Macao"] = {
          name: "Macau",
          country: "Macao",
          elevation: 10,
          key: "stadester-Macau-Macao",
          coords: [22.1987, 113.5439],
          original_names: ["macau", "macao"],
          other_names: ["Macau", "Macao"],
          population: {
            "1557": 500,
            "1560": 1000,
            "1600": 5000,
            "1635": 35000,
            "1700": 19500,
            "1750": 24000,
            "1800": 30000,
            "1850": 29000,
            "1900": 63000,
            "1910": 75000,
            "1920": 84000,
            "1930": 120000,
            "1940": 150000,
            "1950": 188000,
            "1960": 169000,
            "1970": 249000,
            "1980": 242000,
            "1990": 352000,
            "2000": 432000,
            "2010": 540000,
            "2020": 680000
          },
          region: "eastasia",
          colour: [173, 62, 62],
          type: "manual"
        };
      }
      
      console.log(`- Appended ${all_stadester_cities.length} historical Stadestér entries (truncated < ${cutoff_year}).`);
    }
    
    //3. Assign .region (string) and .colour via Voronoi equirectangular raster sampling
    voronoi_candidates = [
      options.voronoi_file,
      path.join(raw_folder, "voronoi_subdivisions.png"),
      path.join(raw_folder, "regional_subdivisions.png"),
      path.join(h1, "population_Stadester", "voronoi_subdivisions.png"),
      "E:/Active Projects/Project 2136 - Stadestér/input/voronoi_subdivisions.png"
    ];
    for (let i = 0; i < voronoi_candidates.length; i++) {
      if (voronoi_candidates[i] && fs.existsSync(voronoi_candidates[i])) {
        try {
          voronoi_png = pngjs_lib.PNG.sync.read(fs.readFileSync(voronoi_candidates[i]));
          console.log(`- Loaded Voronoi regions raster from ${voronoi_candidates[i]} (${voronoi_png.width}x${voronoi_png.height}).`);
          break;
        } catch (e) {
          console.warn(`- Failed to read Voronoi raster from ${voronoi_candidates[i]}:`, e);
        }
      }
    }
    
    region_defines = (global.config && global.config.defines && global.config.defines.regions) ?
      global.config.defines.regions : {
        northern_america: { colour: [87, 122, 175], name: "Northern America" },
        latin_america: { colour: [71, 165, 101], name: "Latin America" },
        europe: { colour: [47, 97, 170], name: "Europe" },
        eastern_europe_and_russia: { colour: [20, 114, 30], name: "Eastern Europe and Russia" },
        central_asia: { colour: [41, 193, 175], name: "Central Asia" },
        middle_east: { colour: [198, 130, 129], name: "Middle East" },
        maghreb_egypt: { colour: [239, 188, 112], name: "Maghreb and Egypt" },
        sub_saharan_africa: { colour: [155, 101, 77], name: "Sub-Saharan Africa" },
        oceania: { colour: [0, 205, 143], name: "Oceania" },
        indian_subcontinent: { colour: [214, 144, 83], name: "Indian Subcontinent" },
        southeast_asia: { colour: [97, 144, 163], name: "Southeast Asia" },
        eastasia: { colour: [173, 62, 62], name: "East Asia" }
      };
    
    all_region_keys = Object.keys(region_defines);
    for (let i = 0; i < all_region_keys.length; i++) {
      let reg = region_defines[all_region_keys[i]];
      if (reg && reg.colour)
        colour_to_region[reg.colour.join(",")] = { key: all_region_keys[i], colour: reg.colour };
    }
    
    all_return_keys = Object.keys(return_obj);
    for (let i = 0; i < all_return_keys.length; i++) {
      let local_city = return_obj[all_return_keys[i]];
      if (!local_city || !Array.isArray(local_city.coords) || local_city.coords.length < 2) continue;
      
      let lat = Number(local_city.coords[0]);
      let lng = Number(local_city.coords[1]);
      if (isNaN(lat) || isNaN(lng)) continue;
      
      if (voronoi_png) {
        let x = Math.min(voronoi_png.width - 1, Math.max(0, Math.floor(((lng - (-180))/360)*voronoi_png.width)));
        let y = Math.min(voronoi_png.height - 1, Math.max(0, Math.floor(((90 - lat)/180)*voronoi_png.height)));
        local_city.pixel_coords = [x, y];
        
        let idx = (y*voronoi_png.width + x)*4;
        let rgb_key = `${voronoi_png.data[idx]},${voronoi_png.data[idx + 1]},${voronoi_png.data[idx + 2]}`;
        let reg = colour_to_region[rgb_key];
        if (reg) {
          local_city.colour = reg.colour;
          local_city.region = reg.key;
        }
      }
    }
    
    //4. Repair all GHSL and historical city display names
    population_Stadester_uud.repairGHSLCityNames(return_obj);
    
    //Return statement
    return return_obj;
  };
  
  /**
   * Integrates modern GHSL urban centre populations (1975-2025) into Stadestér by subtracting
   * non-primary Stadestér settlements falling within each GHSL DEGURBA areal mask and overwriting
   * the primary city's 1975-2025 population. Leaves all pre-1975 data untouched.
   * @alias population_Stadester_ghsl.integrateGHSLIntoStadester
   * 
   * @param {Object} arg0_stadester_obj
   * @param {Object} [arg1_options]
   * 
   * @returns {Object}
   */
  population_Stadester_ghsl.integrateGHSLIntoStadester = function (arg0_stadester_obj, arg1_options) {
    //Convert from parameters
    let stadester_obj = arg0_stadester_obj;
    let options = (arg1_options) ? arg1_options : {};
    
    //Declare local instance variables
    let all_city_keys;
    let all_ghsl_keys;
    let city_entries = [];
    let city_grid = new Map();
    let cluster_members = new Map();
    let cutoff_year = (global.population_Stadester_config && global.population_Stadester_config.cutoff_year) ?
      global.population_Stadester_config.cutoff_year : 1975;
    let end_year = 2025;
    let epochs = [1975, 1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025];
    let ghsl_by_id = new Map();
    let ghsl_folder = options.ghsl_mask_folder || path.join((typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw", "population_GHSL");
    let ghsl_json_path;
    let ghsl_obj = options.ghsl_obj;
    let integrated_count = 0;
    let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
    let raw_folder = options.raw_folder ? options.raw_folder : `${(typeof h1 !== "undefined") ? h1 : "./histmap/1.data_raw"}/population_Stadester/`;
    
    //Guard clauses
    if (!stadester_obj) return stadester_obj;
    
    //Function body
    if (!ghsl_obj) {
      ghsl_json_path = options.ghsl_file || path.join(raw_folder, "ghsl", "ghsl.json");
      if (!fs.existsSync(ghsl_json_path))
        ghsl_json_path = path.join(ghsl_folder, "ghsl.json");
      if (fs.existsSync(ghsl_json_path))
        ghsl_obj = JSON.parse(fs.readFileSync(ghsl_json_path, "utf8"));
    }
    if (!ghsl_obj) return stadester_obj;
    
    all_ghsl_keys = Object.keys(ghsl_obj);
    for (let i = 0; i < all_ghsl_keys.length; i++) {
      let local_ghsl = ghsl_obj[all_ghsl_keys[i]];
      if (local_ghsl && local_ghsl.id)
        ghsl_by_id.set(Number(local_ghsl.id), local_ghsl);
    }
    
    all_city_keys = Object.keys(stadester_obj);
    for (let i = 0; i < all_city_keys.length; i++) {
      let local_city = stadester_obj[all_city_keys[i]];
      if (!local_city || !Array.isArray(local_city.coords) || local_city.coords.length < 2) continue;
      
      let lat = Number(local_city.coords[0]);
      let lng = Number(local_city.coords[1]);
      if (isNaN(lat) || isNaN(lng)) continue;
      
      //Enforce temporal proximity filter (+/-200 years or HYDE interval at cutoff_year) before matching to 1975-2025 GHSL clusters
      let max_pre_yr = -Infinity;
      if (local_city.population) {
        let pop_keys = Object.keys(local_city.population);
        for (let x = 0; x < pop_keys.length; x++) {
          let yr = Number(pop_keys[x]);
          let val = Array.isArray(local_city.population[pop_keys[x]]) ?
            Number(local_city.population[pop_keys[x]][0]) : Number(local_city.population[pop_keys[x]]);
          if (!isNaN(yr) && yr < cutoff_year && val > 0 && yr > max_pre_yr)
            max_pre_yr = yr;
        }
      }
      let max_ghsl_gap = (typeof population_Stadester_uud !== "undefined" && typeof population_Stadester_uud.getMaxTemporalProximityGap === "function") ?
        population_Stadester_uud.getMaxTemporalProximityGap(max_pre_yr, cutoff_year) : 200;
      if (!Number.isFinite(max_pre_yr) || (cutoff_year - max_pre_yr) > max_ghsl_gap) continue;
      
      let px = Math.min(4319, Math.max(0, Math.floor(((lng + 180)/360)*4320)));
      let py = Math.min(2159, Math.max(0, Math.floor(((90 - lat)/180)*2160)));
      let entry_idx = city_entries.length;
      let cell_key = `${Math.floor(lng)},${Math.floor(lat)}`;
      
      city_entries.push({
        city: local_city,
        epoch_cluster: {},
        key: all_city_keys[i],
        lat: lat,
        lng: lng,
        norm_names: population_Stadester_ghsl.getNormalisedCityNames(local_city),
        px: px,
        py: py
      });
      
      if (!city_grid.has(cell_key)) city_grid.set(cell_key, []);
      city_grid.get(cell_key).push(entry_idx);
    }
    
    //1. Match Stadestér settlements against epoch-specific GHSL GeoJSON and PNG areal masks (1975..2025)
    for (let i = 0; i < epochs.length; i++) {
      let ep = epochs[i];
      let geo_path = path.join(ghsl_folder, "geojson", `GHS_urban_${ep}.geojson`);
      let png_path = path.join(ghsl_folder, "urban_area_rasters", `GHS_urban_${ep}.png`);
      
      if (fs.existsSync(geo_path)) {
        let geo_obj = JSON.parse(fs.readFileSync(geo_path, "utf8"));
        let features = geo_obj.features || [];
        
        for (let x = 0; x < features.length; x++) {
          let feat = features[x];
          let uc_id = feat && feat.properties ? Number(feat.properties.ID_UC_G0) : 0;
          if (!uc_id || !ghsl_by_id.has(uc_id) || !feat.geometry) continue;
          
          let max_x = -180;
          let max_y = -90;
          let min_x = 180;
          let min_y = 90;
          let polys = (feat.geometry.type === "Polygon") ? [feat.geometry.coordinates] : (feat.geometry.coordinates || []);
          
          for (let y = 0; y < polys.length; y++) {
            let outer_ring = polys[y][0] || [];
            for (let z = 0; z < outer_ring.length; z++) {
              let pt_x = outer_ring[z][0];
              let pt_y = outer_ring[z][1];
              if (pt_x < min_x) min_x = pt_x;
              if (pt_x > max_x) max_x = pt_x;
              if (pt_y < min_y) min_y = pt_y;
              if (pt_y > max_y) max_y = pt_y;
            }
          }
          
          let gx_end = Math.floor(max_x);
          let gx_start = Math.floor(min_x);
          let gy_end = Math.floor(max_y);
          let gy_start = Math.floor(min_y);
          
          for (let gx = gx_start; gx <= gx_end; gx++) {
            for (let gy = gy_start; gy <= gy_end; gy++) {
              let cell_list = city_grid.get(`${gx},${gy}`);
              if (!cell_list) continue;
              
              for (let a = 0; a < cell_list.length; a++) {
                let ce = city_entries[cell_list[a]];
                if (ce.epoch_cluster[ep]) continue;
                if (ce.lng < min_x || ce.lng > max_x || ce.lat < min_y || ce.lat > max_y) continue;
                if (population_Stadester_ghsl.pointInGeometry(ce.lng, ce.lat, feat.geometry))
                  ce.epoch_cluster[ep] = uc_id;
              }
            }
          }
        }
      }
      
      if (fs.existsSync(png_path)) {
        let png_obj = pngjs_lib.PNG.sync.read(fs.readFileSync(png_path));
        let height = png_obj.height;
        let width = png_obj.width;
        
        for (let x = 0; x < city_entries.length; x++) {
          let ce = city_entries[x];
          if (ce.epoch_cluster[ep]) continue;
          
          let idx = (ce.py*width + ce.px)*4;
          let center_id = (((png_obj.data[idx] << 24) | (png_obj.data[idx + 1] << 16) | (png_obj.data[idx + 2] << 8) | png_obj.data[idx + 3]) >>> 0);
          if (center_id > 0 && ghsl_by_id.has(center_id)) {
            ce.epoch_cluster[ep] = center_id;
          } else {
            for (let dy = -1; dy <= 1 && !ce.epoch_cluster[ep]; dy++) {
              let ny = ce.py + dy;
              if (ny < 0 || ny >= height) continue;
              for (let dx = -1; dx <= 1; dx++) {
                if (dx === 0 && dy === 0) continue;
                let nx = ce.px + dx;
                if (nx < 0 || nx >= width) continue;
                let n_idx = (ny*width + nx)*4;
                let n_id = (((png_obj.data[n_idx] << 24) | (png_obj.data[n_idx + 1] << 16) | (png_obj.data[n_idx + 2] << 8) | png_obj.data[n_idx + 3]) >>> 0);
                if (n_id > 0 && ghsl_by_id.has(n_id)) {
                  let n_ghsl = ghsl_by_id.get(n_id);
                  let n_toks = String(n_ghsl.name || "").split(";").map(s => population_Stadester_ghsl.normaliseGHSLName(s)).filter(Boolean);
                  if (n_toks.length > 0 && population_Stadester_ghsl.matchesAnyGHSLToken(ce.norm_names, [n_toks[0]])) {
                    ce.epoch_cluster[ep] = n_id;
                    break;
                  }
                }
              }
            }
          }
        }
      }
    }
    
    //2. Group Stadestér settlements by GHSL cluster ID across 1975..2025
    for (let i = 0; i < city_entries.length; i++) {
      let ce = city_entries[i];
      for (let x = 0; x < epochs.length; x++) {
        let uc_id = ce.epoch_cluster[epochs[x]];
        if (uc_id) {
          if (!cluster_members.has(uc_id)) cluster_members.set(uc_id, new Set());
          cluster_members.get(uc_id).add(i);
        }
      }
    }
    
    //3. For each GHSL cluster, identify primary city, subtract non-primary settlements, and overwrite 1975-2025
    let all_cluster_ids = Array.from(cluster_members.keys());
    for (let i = 0; i < all_cluster_ids.length; i++) {
      let uc_id = all_cluster_ids[i];
      let ghsl_city = ghsl_by_id.get(uc_id);
      if (!ghsl_city || !ghsl_city.population) continue;
      
      let earliest_ep = epochs[epochs.length - 1];
      let member_indices = Array.from(cluster_members.get(uc_id));
      let members = [];
      
      for (let x = 0; x < member_indices.length; x++)
        members.push(city_entries[member_indices[x]]);
      
      for (let x = 0; x < epochs.length; x++) {
        let ep = epochs[x];
        let has_ep = false;
        for (let y = 0; y < members.length; y++) {
          if (members[y].epoch_cluster[ep] === uc_id) {
            has_ep = true;
            break;
          }
        }
        if (has_ep) {
          earliest_ep = ep;
          break;
        }
      }
      
      let earliest_pool = [];
      for (let x = 0; x < members.length; x++)
        if (members[x].epoch_cluster[earliest_ep] === uc_id)
          earliest_pool.push(members[x]);
      if (earliest_pool.length === 0) earliest_pool = members.slice();
      
      let ghsl_tokens = String(ghsl_city.name || "").split(";").map(s => population_Stadester_ghsl.normaliseGHSLName(s)).filter(Boolean);
      let first_token = ghsl_tokens.length > 0 ? [ghsl_tokens[0]] : [];
      let primary_candidates = [];
      let token_candidates = [];
      
      for (let x = 0; x < earliest_pool.length; x++) {
        let m = earliest_pool[x];
        let ref_pop = population_Stadester_ghsl.getModernReferencePopulation(m.city);
        if (ref_pop <= 0) continue;
        if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, first_token))
          primary_candidates.push(m);
        if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, ghsl_tokens))
          token_candidates.push(m);
      }
      if (primary_candidates.length === 0 && token_candidates.length === 0) {
        for (let x = 0; x < members.length; x++) {
          let m = members[x];
          let ref_pop = population_Stadester_ghsl.getModernReferencePopulation(m.city);
          if (ref_pop <= 0) continue;
          if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, first_token))
            primary_candidates.push(m);
          if (population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, ghsl_tokens))
            token_candidates.push(m);
        }
      }
      
      primary_candidates.sort((a, b) => population_Stadester_ghsl.getModernReferencePopulation(b.city) - population_Stadester_ghsl.getModernReferencePopulation(a.city));
      token_candidates.sort((a, b) => population_Stadester_ghsl.getModernReferencePopulation(b.city) - population_Stadester_ghsl.getModernReferencePopulation(a.city));
      earliest_pool.sort((a, b) => population_Stadester_ghsl.getModernReferencePopulation(b.city) - population_Stadester_ghsl.getModernReferencePopulation(a.city));
      
      let chosen_list = primary_candidates;
      if (token_candidates.length > 0) {
        let best_tok_pop = population_Stadester_ghsl.getModernReferencePopulation(token_candidates[0].city);
        let best_pri_pop = (chosen_list.length > 0) ? population_Stadester_ghsl.getModernReferencePopulation(chosen_list[0].city) : 0;
        if (chosen_list.length === 0 || best_tok_pop > best_pri_pop*1.5)
          chosen_list = token_candidates;
      }
      if (chosen_list.length === 0) {
        chosen_list = earliest_pool;
      } else if (earliest_pool.length > 0) {
        let best_pool_pop = population_Stadester_ghsl.getModernReferencePopulation(earliest_pool[0].city);
        let best_chosen_pop = population_Stadester_ghsl.getModernReferencePopulation(chosen_list[0].city);
        if (best_pool_pop > best_chosen_pop*2.0)
          chosen_list = earliest_pool;
      }
      
      let primary_entry = chosen_list[0];
      if (!primary_entry) continue;
      
      //Prefer non-agglomeration entry as primary record if both <City> and <City> (agglomeration) exist in the mask
      if (primary_entry.key.toLowerCase().includes("agglomeration")) {
        for (let x = 0; x < members.length; x++) {
          let m = members[x];
          if (
            !m.key.toLowerCase().includes("agglomeration") &&
            population_Stadester_ghsl.getModernReferencePopulation(m.city) > 0 &&
            (
              population_Stadester_uud.checkExactNameMatch(m.city, primary_entry.city) ||
              population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, primary_entry.norm_names)
            )
          ) {
            primary_entry = m;
            break;
          }
        }
      }
      
      //Group co-located same-name / agglomeration twins of the primary city so they do not subtract from primary_entry
      let primary_group = [];
      let primary_set = new Set();
      for (let x = 0; x < members.length; x++) {
        let m = members[x];
        if (
          m === primary_entry ||
          population_Stadester_uud.checkExactNameMatch(m.city, primary_entry.city) ||
          population_Stadester_ghsl.matchesAnyGHSLToken(m.norm_names, primary_entry.norm_names)
        ) {
          primary_group.push(m);
          primary_set.add(m);
        }
      }
      
      let subordinates = [];
      for (let x = 0; x < members.length; x++)
        if (!primary_set.has(members[x]))
          subordinates.push(members[x]);
      
      if (!primary_entry.city.population) primary_entry.city.population = {};
      
      for (let yr = cutoff_year; yr <= end_year; yr++) {
        let g_pop = parseFloat(ghsl_city.population[yr]);
        if (isNaN(g_pop)) continue;
        
        let e0 = epochs[0];
        let e1 = epochs[epochs.length - 1];
        for (let k = 0; k < epochs.length - 1; k++) {
          if (yr >= epochs[k] && yr <= epochs[k + 1]) {
            e0 = epochs[k];
            e1 = epochs[k + 1];
            break;
          }
        }
        
        let frac = (e1 > e0) ? (yr - e0)/(e1 - e0) : 0;
        let sub_sum = 0;
        
        for (let x = 0; x < subordinates.length; x++) {
          let sub = subordinates[x];
          let w0 = (sub.epoch_cluster[e0] === uc_id) ? 1 : 0;
          let w1 = (sub.epoch_cluster[e1] === uc_id) ? 1 : 0;
          let weight = (1 - frac)*w0 + frac*w1;
          
          if (weight > 0 && sub.city.population && sub.city.population[yr] !== undefined) {
            let sub_pop = parseFloat(sub.city.population[yr]) || 0;
            if (sub_pop > 0) sub_sum += weight*sub_pop;
          }
        }
        
        primary_entry.city.population[yr] = Math.max(0, Math.round(g_pop - sub_sum));
        
        //Zero redundant primary twins in 1975-2025 so primary population is not double-counted
        for (let x = 0; x < primary_group.length; x++) {
          let twin = primary_group[x];
          if (twin !== primary_entry && twin.city.population)
            twin.city.population[yr] = 0;
        }
      }
      
      integrated_count++;
    }
    
    console.log(`- Integrated GHSL (1975-2025) DEGURBA areal mask populations into ${integrated_count} primary Stadestér cities.`);
    
    //Return statement
    return stadester_obj;
  };
  
  /**
   * Returns a reference modern population (1975/2000/1970/1980) for ranking primary city candidates.
   * @alias population_Stadester_ghsl.getModernReferencePopulation
   * 
   * @param {Object} arg0_city_obj
   * 
   * @returns {number}
   */
  population_Stadester_ghsl.getModernReferencePopulation = function (arg0_city_obj) {
    //Convert from parameters
    let city_obj = arg0_city_obj;
    
    //Guard clauses
    if (!city_obj || !city_obj.population) return 0;
    
    //Return statement
    return Number(
      city_obj.population[1975] ||
      city_obj.population[2000] ||
      city_obj.population[1970] ||
      city_obj.population[1980] ||
      0
    );
  };
  
  /**
   * Checks whether any normalised city name matches any normalised GHSL token.
   * @alias population_Stadester_ghsl.matchesAnyGHSLToken
   * 
   * @param {Array<string>} arg0_city_names
   * @param {Array<string>} arg1_tokens
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.matchesAnyGHSLToken = function (arg0_city_names, arg1_tokens) {
    //Convert from parameters
    let city_names = arg0_city_names || [];
    let tokens = arg1_tokens || [];
    
    //Function body
    for (let i = 0; i < city_names.length; i++) {
      let c_name = city_names[i];
      if (!c_name) continue;
      for (let x = 0; x < tokens.length; x++) {
        let tok = tokens[x];
        if (!tok) continue;
        if (c_name === tok) return true;
      }
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Normalises a city or GHSL token name by stripping diacritics, parentheticals, and urban suffixes.
   * @alias population_Stadester_ghsl.normaliseGHSLName
   * 
   * @param {string} arg0_name
   * 
   * @returns {string}
   */
  population_Stadester_ghsl.normaliseGHSLName = function (arg0_name) {
    //Convert from parameters
    let name = (arg0_name) ? `${arg0_name}` : "";
    
    //Return statement
    return name
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/\([^)]*\)/g, "")
      .replace(/\b(greater|agglomeration|zona urbana|cdp|city|grad|subtotal)\b/gi, "")
      .replace(/['’`´]/g, "")
      .replace(/[^a-zA-Z0-9\s]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  };
  
  /**
   * Checks whether [lng, lat] falls inside a GeoJSON Polygon or MultiPolygon geometry.
   * @alias population_Stadester_ghsl.pointInGeometry
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Object} arg2_geometry
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInGeometry = function (arg0_lng, arg1_lat, arg2_geometry) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let geometry = arg2_geometry;
    
    //Guard clauses
    if (!geometry || !geometry.coordinates) return false;
    
    //Function body
    if (geometry.type === "Polygon")
      return population_Stadester_ghsl.pointInPolygon(lng, lat, geometry.coordinates);
    if (geometry.type === "MultiPolygon") {
      for (let i = 0; i < geometry.coordinates.length; i++)
        if (population_Stadester_ghsl.pointInPolygon(lng, lat, geometry.coordinates[i]))
          return true;
    }
    
    //Return statement
    return false;
  };
  
  /**
   * Checks whether [lng, lat] falls inside a Polygon ring array (outer ring minus holes).
   * @alias population_Stadester_ghsl.pointInPolygon
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Array<Array<Array<number>>>} arg2_rings
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInPolygon = function (arg0_lng, arg1_lat, arg2_rings) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let rings = arg2_rings;
    
    //Guard clauses
    if (!rings || rings.length === 0) return false;
    if (!population_Stadester_ghsl.pointInRing(lng, lat, rings[0])) return false;
    
    //Function body
    for (let i = 1; i < rings.length; i++)
      if (population_Stadester_ghsl.pointInRing(lng, lat, rings[i]))
        return false;
    
    //Return statement
    return true;
  };
  
  /**
   * Ray-casting point-in-ring test for [lng, lat].
   * @alias population_Stadester_ghsl.pointInRing
   * 
   * @param {number} arg0_lng
   * @param {number} arg1_lat
   * @param {Array<Array<number>>} arg2_ring
   * 
   * @returns {boolean}
   */
  population_Stadester_ghsl.pointInRing = function (arg0_lng, arg1_lat, arg2_ring) {
    //Convert from parameters
    let lng = Number(arg0_lng);
    let lat = Number(arg1_lat);
    let ring = arg2_ring;
    
    //Declare local instance variables
    let inside = false;
    
    //Guard clauses
    if (!ring || ring.length < 3) return false;
    
    //Function body
    for (let i = 0, x = ring.length - 1; i < ring.length; x = i++) {
      let xi = ring[i][0];
      let xj = ring[x][0];
      let yi = ring[i][1];
      let yj = ring[x][1];
      let intersect = ((yi > lat) !== (yj > lat)) && (lng < (xj - xi)*(lat - yi)/((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }
    
    //Return statement
    return inside;
  };
  
  //Expose on population_Stadester_uud for pipeline compatibility
  population_Stadester_uud.getStadesterGHSLObject = population_Stadester_ghsl.getStadesterGHSLObject;
  population_Stadester_uud.integrateGHSLIntoStadester = population_Stadester_ghsl.integrateGHSLIntoStadester;
}

