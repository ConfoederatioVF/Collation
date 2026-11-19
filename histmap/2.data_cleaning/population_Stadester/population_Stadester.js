//Initialise functions
{
  if (!global.population_Stadester) global.population_Stadester = {};
  
  if (typeof require !== "undefined") {
    let cur_dir = (typeof __dirname !== "undefined") ? __dirname : path.resolve(`${global.h2 || "./histmap/2.data_cleaning/"}/population_Stadester/`);
    try {
      if (!global.population_Stadester_config && fs.existsSync(path.join(cur_dir, "config", "stadester_config.js")))
        require(path.join(cur_dir, "config", "stadester_config.js"));
      if (!global.StadesterPartitionIO && fs.existsSync(path.join(cur_dir, "StadesterPartitionIO.js")))
        require(path.join(cur_dir, "StadesterPartitionIO.js"));
      if (!global.ViscountGazetteerLoader && fs.existsSync(path.join(cur_dir, "ViscountGazetteerLoader.js")))
        require(path.join(cur_dir, "ViscountGazetteerLoader.js"));
      if ((!global.population_Stadester_uud || !global.population_Stadester_uud.initialiseUUD) && fs.existsSync(path.join(cur_dir, "stadester_uud.js")))
        require(path.join(cur_dir, "stadester_uud.js"));
      if ((!global.population_Stadester_uud || !global.population_Stadester_uud.repairGHSLCityNames) && fs.existsSync(path.join(cur_dir, "stadester_uud_ghsl_names.js")))
        require(path.join(cur_dir, "stadester_uud_ghsl_names.js"));
      if ((!global.population_Stadester_uud || !global.population_Stadester_uud.fixStadesterErrors) && fs.existsSync(path.join(cur_dir, "stadester_uud_fixes.js")))
        require(path.join(cur_dir, "stadester_uud_fixes.js"));
      if ((!global.population_Stadester_ghsl || !global.population_Stadester_ghsl.getNormalisedCityNames) && fs.existsSync(path.join(cur_dir, "stadester_ghsl_helpers.js")))
        require(path.join(cur_dir, "stadester_ghsl_helpers.js"));
      if ((!global.population_Stadester_ghs_pop || !global.population_Stadester_ghs_pop.partitionGHSPopGridcells) && fs.existsSync(path.join(cur_dir, "stadester_ghs_pop.js")))
        require(path.join(cur_dir, "stadester_ghs_pop.js"));
      if ((!global.population_Stadester_ghsl || !global.population_Stadester_ghsl.integrateGHSLIntoStadester) && fs.existsSync(path.join(cur_dir, "stadester_ghsl.js")))
        require(path.join(cur_dir, "stadester_ghsl.js"));
      if ((!global.population_Stadester_density || !global.population_Stadester_density.processCitiesAreas) && fs.existsSync(path.join(cur_dir, "stadester_density.js")))
        require(path.join(cur_dir, "stadester_density.js"));
      if ((!global.population_Stadester_rasters || !global.population_Stadester_rasters.getCoordsPixel) && fs.existsSync(path.join(cur_dir, "stadester_rasters.js")))
        require(path.join(cur_dir, "stadester_rasters.js"));
      if ((!global.population_Stadester_rasters || !global.population_Stadester_rasters.reconcileStadesterDemographics) && fs.existsSync(path.join(cur_dir, "stadester_rasters_reconcile.js")))
        require(path.join(cur_dir, "stadester_rasters_reconcile.js"));
    } catch (e) {
      console.warn(`[population_Stadester] Failed to load companion modules:`, e);
    }
  }
  
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
    static transform_stadester_folder = `${(typeof h3 !== "undefined") ? h3 : "./histmap/3.data_transform"}/population_Stadester.transform/stadester/`;
    
    static file_uud_cities = `${this.bf}uud/processed_uud_cities.json`;
    static file_stadester_cities = `${this.bf}uud/stadester_cities.json`;
    static file_flattened_stadester = `${this.bf}uud/flattened_stadester_cities.json`;
    static file_processed_stadester = `${this.bf}uud/processed_stadester_cities.json`;
    static file_stadester_final = `${this.transform_stadester_folder}`;
    static file_stadester_vis = `${(typeof h5 !== "undefined") ? h5 : "./histmap/5.data_visualisation/"}stadester/stadester_2.0`;
    
    static antiquity_years = Array.from({ length: 101 }, (_, i) => -10000 + i * 100);
    static urban_antiquity_years = Array.from({ length: 31 }, (_, i) => -3000 + i * 100);

    /**
     * Resolves canonical HYDE years from landuse_HYDE or standalone UUD fallback.
     * @returns {Array<number>}
     */
    static get resolved_hyde_years () {
      let default_years = (typeof population_Stadester_uud !== "undefined" && population_Stadester_uud.getDefaultHYDEYears) ?
        population_Stadester_uud.getDefaultHYDEYears() : [1800];
      
      //Return statement
      return (typeof landuse_HYDE !== "undefined" && landuse_HYDE.sorted_hyde_years) ?
        landuse_HYDE.sorted_hyde_years : default_years;
    }

    /**
     * Complete array of urban years: all 100-year antiquity intervals (-10000 to 0) + post-1AD HYDE years.
     * @returns {Array<number>}
     */
    static get all_urban_years () {
      let post_1ad = this.resolved_hyde_years.filter(y => y > 0);
      
      //Return statement
      return [...this.antiquity_years, ...post_1ad];
    }
    
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
      stadester_obj = population_Stadester_uud.integrateGHSLIntoStadester(stadester_obj, {
        raw_folder: this.raw_folder,
        ...options
      });
      if (typeof population_Stadester_uud.reconcileCloseSameCountryTwins === "function")
        stadester_obj = population_Stadester_uud.reconcileCloseSameCountryTwins(stadester_obj);
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(stadester_obj);
      
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.writeJSONSafe === "function") {
        population_Stadester_ghs_pop.writeJSONSafe(this.file_processed_stadester, stadester_obj);
      } else {
        fs.writeFileSync(this.file_processed_stadester, JSON.stringify(stadester_obj, null, 2));
      }
      console.log(`- Saved processed Stadestér dataset to ${this.file_processed_stadester}.`);
      
      if (!options.do_not_sync_vis && this.file_stadester_vis && fs.existsSync(path.dirname(path.resolve(this.file_stadester_vis)))) {
        StadesterPartitionIO.writePartitionedStadester(this.file_stadester_vis, stadester_obj, { version: "2.0" });
        console.log(`- Synchronised processed Stadestér visualisation shards to ${this.file_stadester_vis}.`);
      }
      
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
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(stadester_obj);
      StadesterPartitionIO.writePartitionedStadester(this.file_stadester_final, stadester_obj, { version: "2.0" });
      console.log(`- Saved partitioned Stadestér dataset to ${this.file_stadester_final}.`);
      
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
      if (!stadester_obj && StadesterPartitionIO.hasDataset(this.file_stadester_final))
        stadester_obj = StadesterPartitionIO.readPartitionedStadester(this.file_stadester_final);
      
      stadester_obj = population_Stadester_density.cacheRadialBuffers(stadester_obj);
      if (typeof population_Stadester_ghs_pop !== "undefined" && typeof population_Stadester_ghs_pop.cleanTransientMetadata === "function")
        population_Stadester_ghs_pop.cleanTransientMetadata(stadester_obj);
      if (typeof population_Stadester_rasters !== "undefined" && typeof population_Stadester_rasters.detectOutOfMaskSettlements === "function") {
        let mask_audit = population_Stadester_rasters.detectOutOfMaskSettlements(stadester_obj);
        console.log(`- [Stadestér Land Mask] Actionable out-of-mask settlements: ${mask_audit.actionable.length} (${mask_audit.subpixel_islands.length} sub-pixel remote islands).`);
      }
      StadesterPartitionIO.writePartitionedStadester(this.file_stadester_final, stadester_obj, { version: "2.0" });
      console.log(`- Saved final partitioned Stadestér dataset to ${this.file_stadester_final}.`);
      
      if (this.file_stadester_vis) {
        let vis_dir = path.dirname(path.resolve(this.file_stadester_vis));
        if (!fs.existsSync(vis_dir)) fs.mkdirSync(vis_dir, { recursive: true });
        StadesterPartitionIO.writePartitionedStadester(this.file_stadester_vis, stadester_obj, { version: "2.0" });
        console.log(`- Synchronised final partitioned Stadestér dataset to ${this.file_stadester_vis}.`);
      }
      
      let dataview_targets = [
        "F:/Active Projects/Project 1436 - Dataview/data/stadester/stadester_2.0",
        "D:/Project 1436 - Dataview/data/stadester/stadester_2.0"
      ];
      for (let i = 0; i < dataview_targets.length; i++) {
        let dv_target = dataview_targets[i];
        let dv_dir = path.dirname(dv_target);
        if (fs.existsSync(dv_dir)) {
          StadesterPartitionIO.writePartitionedStadester(dv_target, stadester_obj, { version: "2.0" });
          let dv_cache = path.join(dv_dir, "cache", "stadester_2.0_lite.json");
          let dv_indexed_cache = path.join(dv_dir, "cache", "stadester_2.0_indexed.json");
          let dv_city_cache = path.join(dv_dir, "cache", "stadester_city_cache.json");
          if (fs.existsSync(dv_cache)) try { fs.unlinkSync(dv_cache); } catch (e) {}
          if (fs.existsSync(dv_indexed_cache)) try { fs.unlinkSync(dv_indexed_cache); } catch (e) {}
          if (fs.existsSync(dv_city_cache)) try { fs.unlinkSync(dv_city_cache); } catch (e) {}
          this.syncDataviewCityCoords(dv_dir, stadester_obj);
          console.log(`- Synchronised final partitioned Stadestér dataset to Dataview (${dv_target}).`);
        }
      }
      
      //Return statement
      return stadester_obj;
    }

    /**
     * Synchronises updated coordinates ([lng, lat]), country, and region onto Dataview's `all_cities_coords.json`.
     * @alias population_Stadester.syncDataviewCityCoords
     *
     * @param {string} arg0_dv_dir
     * @param {Object} arg1_stadester_obj
     *
     * @returns {number} Number of updated records
     */
    static syncDataviewCityCoords (arg0_dv_dir, arg1_stadester_obj) {
      //Convert from parameters
      let dv_dir = arg0_dv_dir;
      let stadester_obj = arg1_stadester_obj;

      //Declare local instance variables
      let all_coords;
      let all_keys;
      let cfg = global.population_Stadester_config;
      let colour_to_region = {};
      let coords_path = path.join(dv_dir, "all_cities_coords.json");
      let country_regions = {
        "angola": "sub_saharan_africa",
        "australia": "oceania",
        "chad": "sub_saharan_africa",
        "cook islands": "oceania",
        "eswatini": "sub_saharan_africa",
        "fiji": "oceania",
        "ghana": "sub_saharan_africa",
        "guadeloupe": "latin_america",
        "japan": "eastasia",
        "kiribati": "oceania",
        "marshall islands": "oceania",
        "micronesia": "oceania",
        "nauru": "oceania",
        "new zealand": "oceania",
        "niue": "oceania",
        "norfolk island": "oceania",
        "north korea": "eastasia",
        "north macedonia": "europe",
        "palau": "oceania",
        "poland": "europe",
        "saint barthelemy": "latin_america",
        "saint martin": "latin_america",
        "samoa": "oceania",
        "slovenia": "europe",
        "solomon islands": "oceania",
        "south korea": "eastasia",
        "spain": "europe",
        "sudan": "sub_saharan_africa",
        "taiwan": "eastasia",
        "the bahamas": "latin_america",
        "the gambia": "sub_saharan_africa",
        "tokelau": "oceania",
        "tonga": "oceania",
        "tuvalu": "oceania",
        "united kingdom": "europe",
        "vanuatu": "oceania"
      };
      let pngjs_lib = (typeof pngjs !== "undefined") ? pngjs : (global.pngjs || require("pngjs"));
      let reloc_entries = [];
      let stad_lookup = new Map();
      let updated_count = 0;
      let voronoi_path = path.join(this.raw_folder, "voronoi_subdivisions.png");
      let voronoi_png = null;

      //Guard clauses
      if (!stadester_obj || !fs.existsSync(coords_path)) return 0;

      //Function body
      all_coords = JSON.parse(fs.readFileSync(coords_path, "utf8"));
      all_keys = Object.keys(stadester_obj);

      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let c = stadester_obj[k];
        if (!c || !Array.isArray(c.coords) || c.coords.length < 2) continue;
        stad_lookup.set(k, c);
        if (c.name && c.country) {
          let alt_k = `${c.name}-${c.country}`;
          if (!stad_lookup.has(alt_k)) stad_lookup.set(alt_k, c);
        }
        if (Number.isFinite(Number(c.latitude)) && Number.isFinite(Number(c.longitude))) {
          let o_lat = Number(c.latitude);
          let o_lng = Number(c.longitude);
          let n_lat = Number(c.coords[0]);
          let n_lng = Number(c.coords[1]);
          if (Math.abs(o_lat - n_lat) > 0.04 || Math.abs(o_lng - n_lng) > 0.04) {
            reloc_entries.push({
              is_centroid: false,
              names: [c.name, ...(Array.isArray(c.other_names) ? c.other_names : [])].filter(Boolean),
              new_coords: [n_lat, n_lng],
              old_coords: [o_lat, o_lng],
              target_key: k
            });
          }
        }
      }

      //Register old-country -> new-city fallback aliases from coord_overrides
      if (cfg && cfg.coord_overrides) {
        let pop_ov = cfg.coord_overrides.populstat || {};
        let pop_countries = cfg.populstat_countries || {};
        for (let k of Object.keys(pop_ov)) {
          let ov = pop_ov[k];
          if (ov && ov.country_override) {
            let old_country = pop_countries[ov.raw_country_key] || ov.raw_country_key;
            let target = stadester_obj[`${ov.raw_city_key}-${ov.country_override}`];
            if (target) stad_lookup.set(`${ov.raw_city_key}-${old_country}`, target);
          }
        }
        let wcp_ov = cfg.coord_overrides.worldcitypop || {};
        for (let k of Object.keys(wcp_ov)) {
          let ov = wcp_ov[k];
          let target = stadester_obj[k];
          if (target && ov && ov.country_override && target.name)
            stad_lookup.set(`${target.name}-${ov.country_override}`, target);
        }

        let ov_groups = Object.keys(cfg.coord_overrides);
        for (let i = 0; i < ov_groups.length; i++) {
          let grp_obj = cfg.coord_overrides[ov_groups[i]] || {};
          let grp_keys = Object.keys(grp_obj);
          for (let x = 0; x < grp_keys.length; x++) {
            let ov = grp_obj[grp_keys[x]];
            if (!ov || !ov.note || !Array.isArray(ov.coords) || ov.resolution === "non_settlement") continue;
            let note_match = String(ov.note).match(/\[(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\]/);
            if (!note_match) continue;
            let city_part = ov.raw_city_key || grp_keys[x].replace(/-([^-]+)$/, "");
            let target_obj = stad_lookup.get(grp_keys[x]) || stadester_obj[grp_keys[x]];
            reloc_entries.push({
              is_centroid: /centroid/i.test(ov.note),
              names: [city_part, target_obj && target_obj.name].filter(Boolean),
              new_coords: (target_obj && Array.isArray(target_obj.coords)) ? target_obj.coords : ov.coords,
              old_coords: [Number(note_match[1]), Number(note_match[2])],
              target_key: grp_keys[x]
            });
          }
        }
      }

      if (cfg && cfg.regions && fs.existsSync(voronoi_path)) {
        try {
          voronoi_png = pngjs_lib.PNG.sync.read(fs.readFileSync(voronoi_path));
          let reg_keys = Object.keys(cfg.regions);
          for (let i = 0; i < reg_keys.length; i++) {
            let r_cfg = cfg.regions[reg_keys[i]];
            if (r_cfg && r_cfg.colour)
              colour_to_region[r_cfg.colour.join(",")] = reg_keys[i];
          }
        } catch (e) {}
      }

      for (let i = 0; i < all_coords.length; i++) {
        let item = all_coords[i];
        if (!item || !item.key) continue;

        let match = null;
        let strip_k = String(item.key).replace(/^stadester-/, "");
        if (stad_lookup.has(strip_k)) {
          match = stad_lookup.get(strip_k);
        } else if (Array.isArray(item.dataset_keys)) {
          for (let x = 0; x < item.dataset_keys.length; x++) {
            let dk = String(item.dataset_keys[x]).replace(/^stadester-/, "");
            if (stad_lookup.has(dk)) {
              match = stad_lookup.get(dk);
              break;
            }
          }
        }
        if (!match || !Array.isArray(match.coords) || match.coords.length < 2) continue;

        let lat = Number(match.coords[0]);
        let lng = Number(match.coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;

        let new_lng = Number(lng.toFixed(5));
        let new_lat = Number(lat.toFixed(5));
        let old_lng = Array.isArray(item.coords) ? Number(item.coords[0]) : NaN;
        let old_lat = Array.isArray(item.coords) ? Number(item.coords[1]) : NaN;
        let coords_changed = !Number.isFinite(old_lng) || !Number.isFinite(old_lat) ||
          Math.abs(old_lng - new_lng) > 1e-5 || Math.abs(old_lat - new_lat) > 1e-5;
        let item_changed = false;

        if (coords_changed) {
          if (Number.isFinite(old_lat) && Number.isFinite(old_lng)) {
            reloc_entries.push({
              is_centroid: false,
              names: [item.name, match.name, strip_k.split("-")[0]].filter(Boolean),
              new_coords: [lat, lng],
              old_coords: [old_lat, old_lng],
              target_key: strip_k
            });
          }
          item.coords = [new_lng, new_lat];
          item_changed = true;
        }
        if (match.country && item.country !== match.country && !String(item.key).startsWith("ghsl-")) {
          item.country = match.country;
          item_changed = true;
        }

        let norm_c = String(item.country || match.country || "").toLowerCase().trim();
        let expected_reg = country_regions[norm_c];
        if (!expected_reg && coords_changed && voronoi_png) {
          let vx = Math.min(voronoi_png.width - 1, Math.max(0, Math.floor(((lng + 180)/360)*voronoi_png.width)));
          let vy = Math.min(voronoi_png.height - 1, Math.max(0, Math.floor(((90 - lat)/180)*voronoi_png.height)));
          let v_idx = (vy*voronoi_png.width + vx)*4;
          expected_reg = colour_to_region[`${voronoi_png.data[v_idx]},${voronoi_png.data[v_idx + 1]},${voronoi_png.data[v_idx + 2]}`];
        }
        if (expected_reg && item.region !== expected_reg) {
          item.region = expected_reg;
          item_changed = true;
        }
        if (item_changed) updated_count++;
      }

      if (updated_count > 0) {
        fs.writeFileSync(coords_path, JSON.stringify(all_coords), "utf8");
        console.log(`- Synced ${updated_count} updated records in ${coords_path}.`);
      }

      this.syncDataviewCityMetadata(dv_dir, stad_lookup, reloc_entries);

      //Return statement
      return updated_count;
    }

    /**
     * Keeps Dataview `city_metadata.json` (`[lng, lat]`) coordinates synchronised with relocated `stadester_obj` entries while preserving legitimate homonyms.
     * @alias population_Stadester.syncDataviewCityMetadata
     *
     * @param {string} arg0_dv_dir
     * @param {Map<string, Object>} arg1_stad_lookup
     * @param {Array<Object>} arg2_reloc_entries
     * @returns {number}
     */
    static syncDataviewCityMetadata (arg0_dv_dir, arg1_stad_lookup, arg2_reloc_entries) {
      //Convert from parameters
      let dv_dir = arg0_dv_dir;
      let reloc_entries = Array.isArray(arg2_reloc_entries) ? arg2_reloc_entries : [];
      let stad_lookup = arg1_stad_lookup;

      //Declare local instance variables
      let hav_km = (a_lat, a_lng, b_lat, b_lng) => {
        let to_rad = Math.PI/180;
        let d_lat = (b_lat - a_lat)*to_rad;
        let d_lng = (b_lng - a_lng)*to_rad;
        let hav = Math.sin(d_lat/2)**2 + Math.cos(a_lat*to_rad)*Math.cos(b_lat*to_rad)*Math.sin(d_lng/2)**2;
        return 6371*2*Math.asin(Math.sqrt(Math.min(1, hav)));
      };
      let meta_list;
      let versioned_meta_path = path.join(dv_dir, "stadester_2.0", "city_metadata.json");
      let meta_path = fs.existsSync(versioned_meta_path) ? versioned_meta_path : path.join(dv_dir, "city_metadata.json");
      let meta_updated = 0;
      let norm_name = (s) => String(s || "").replace(/ß/gi, "ss").normalize("NFD").replace(/[\u0300-\u036f`'’]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
      let reloc_grid = new Map();
      let stad_grid = new Map();

      //Guard clauses
      if (!stad_lookup || !fs.existsSync(meta_path)) return 0;

      //Function body
      for (let entry of stad_lookup.values()) {
        if (!entry || !Array.isArray(entry.coords) || entry.coords.length < 2) continue;
        let lat = Number(entry.coords[0]);
        let lng = Number(entry.coords[1]);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) continue;
        let gk = `${Math.floor(lat)}_${Math.floor(lng)}`;
        if (!stad_grid.has(gk)) stad_grid.set(gk, []);
        let names = new Set([norm_name(entry.name), ...(Array.isArray(entry.other_names) ? entry.other_names.map(norm_name) : [])].filter((t) => t.length >= 2));
        stad_grid.get(gk).push({ key: entry.key, lat, lng, names });
      }
      for (let i = 0; i < reloc_entries.length; i++) {
        let r = reloc_entries[i];
        if (!r || !Array.isArray(r.old_coords) || !Array.isArray(r.new_coords)) continue;
        if (hav_km(r.old_coords[0], r.old_coords[1], r.new_coords[0], r.new_coords[1]) <= 5) continue;
        let gk = `${Math.floor(r.old_coords[0])}_${Math.floor(r.old_coords[1])}`;
        if (!reloc_grid.has(gk)) reloc_grid.set(gk, []);
        reloc_grid.get(gk).push({
          is_centroid: Boolean(r.is_centroid),
          names: new Set((r.names || []).map(norm_name).filter((t) => t.length >= 2)),
          new_lat: Number(r.new_coords[0]),
          new_lng: Number(r.new_coords[1]),
          old_lat: Number(r.old_coords[0]),
          old_lng: Number(r.old_coords[1]),
          target_key: r.target_key
        });
      }

      meta_list = JSON.parse(fs.readFileSync(meta_path, "utf8"));
      for (let i = 0; i < meta_list.length; i++) {
        let m = meta_list[i];
        if (!m || !Array.isArray(m.coords) || m.coords.length < 2) continue;
        let m_lat = Number(m.coords[1]);
        let m_lng = Number(m.coords[0]);
        let new_lat = null;
        let new_lng = null;

        if (m.key) {
          let direct = stad_lookup.get(String(m.key).replace(/^stadester-/, ""));
          if (direct && Array.isArray(direct.coords) && direct.coords.length >= 2) {
            new_lat = Number(direct.coords[0]);
            new_lng = Number(direct.coords[1]);
          }
        }
        if (new_lat === null && reloc_grid.size > 0) {
          let m_names = new Set([norm_name(m.name)].filter((t) => t.length >= 2));
          if (Array.isArray(m.historical_names)) {
            for (let x = 0; x < m.historical_names.length; x++) {
              let hn = m.historical_names[x] && norm_name(m.historical_names[x].name);
              if (hn && hn.length >= 2) m_names.add(hn);
            }
          }
          let best_r = null;
          let best_d = 9999;
          for (let x = -1; x <= 1; x++) {
            for (let y = -1; y <= 1; y++) {
              let bucket = reloc_grid.get(`${Math.floor(m_lat) + x}_${Math.floor(m_lng) + y}`);
              if (!bucket) continue;
              for (let z = 0; z < bucket.length; z++) {
                let r = bucket[z];
                let d_old = hav_km(m_lat, m_lng, r.old_lat, r.old_lng);
                if (d_old > 2.0 || d_old >= best_d) continue;
                let has_shared = false;
                for (let n of m_names) if (r.names.has(n)) { has_shared = true; break; }
                if (has_shared) { best_d = d_old; best_r = r; }
              }
            }
          }
          if (best_r) {
            let is_homonym_safe = true;
            if (!(best_r.is_centroid && best_d <= 0.5)) {
              for (let x = -1; x <= 1 && is_homonym_safe; x++) {
                for (let y = -1; y <= 1 && is_homonym_safe; y++) {
                  let sb = stad_grid.get(`${Math.floor(m_lat) + x}_${Math.floor(m_lng) + y}`);
                  if (!sb) continue;
                  for (let z = 0; z < sb.length; z++) {
                    let s = sb[z];
                    if (s.key === best_r.target_key) continue;
                    if (hav_km(s.lat, s.lng, best_r.new_lat, best_r.new_lng) <= 2.0) continue;
                    if (hav_km(m_lat, m_lng, s.lat, s.lng) <= 15.0) {
                      for (let n of m_names) {
                        if (s.names.has(n)) { is_homonym_safe = false; break; }
                      }
                    }
                    if (!is_homonym_safe) break;
                  }
                }
              }
            }
            if (is_homonym_safe) {
              new_lat = best_r.new_lat;
              new_lng = best_r.new_lng;
            }
          }
        }
        if (new_lat !== null && new_lng !== null && hav_km(m_lat, m_lng, new_lat, new_lng) > 1.0) {
          m.coords = [Number(new_lng.toFixed(6)), Number(new_lat.toFixed(6))];
          meta_updated++;
        }
      }

      if (meta_updated > 0) {
        fs.writeFileSync(meta_path, JSON.stringify(meta_list, null, 2), "utf8");
        console.log(`- Synced ${meta_updated} relocated metadata coords in ${meta_path}.`);
      }

      //Return statement
      return meta_updated;
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
      let local_options = {
        intermediate_base_folder: this.intermediate_base_folder,
        ...options
      };
      let years = local_options.years || this.all_urban_years;
      
      this.ensureDirectories();
      
      //Only preload stadester_obj on main thread when running without worker threads so options is never polluted
      if (local_options.use_workers === false && !local_options.stadester_obj && StadesterPartitionIO.hasDataset(this.file_stadester_final)) {
        console.log(`- Preloading Stadestér master dataset (${this.file_stadester_final})...`);
        local_options.stadester_obj = StadesterPartitionIO.readPartitionedStadester(this.file_stadester_final);
      }
      
      //Return statement
      return population_Stadester_rasters.generateBaseRastersParallel(years, local_options);
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
      let years = options.years || this.all_urban_years;
      
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
      let hyde_years = this.resolved_hyde_years;
      let years = options.years || hyde_years.filter(y => y >= -10000 && y <= 2025);
      
      this.ensureDirectories();
      
      //Return statement
      return population_Stadester_rasters.generateRuralRastersParallel(years, {
        input_popc_folder: this.input_popc_folder,
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
      let hyde_years = this.resolved_hyde_years;
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
      let hyde_years = this.resolved_hyde_years;
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
      if (!cities_obj && StadesterPartitionIO.hasDataset(target_file))
        cities_obj = StadesterPartitionIO.readPartitionedStadester(target_file);
      
      if (cities_obj) {
        population_Stadester_uud.repairGHSLCityNames(cities_obj, options);
        if (options.save !== false && target_file)
          StadesterPartitionIO.writePartitionedStadester(target_file, cities_obj, { version: options.version || "2.0" });
      }
      
      //Return statement
      return cities_obj;
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
        if (!options.overwrite && (fs.existsSync(this.file_processed_stadester) || StadesterPartitionIO.hasDataset(this.file_stadester_final)))
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
      if (!options.exclude.includes("I")) {
        //reconcileStadesterDemographics outputs synchronised Urban, Rural and Total Population rasters in one pass
        await this.I_generatePopulationRasters(options);
      } else if (!options.exclude.includes("H")) {
        await this.H_generateRuralRasters(options);
      }
      if (!options.exclude.includes("J")) await this.J_prepareIntermediates(options);
      
      console.log(`- Successfully completed population_Stadester pipeline.`);
    }
  };
}
