(function () {
  if (!global.ve) global.ve = { registry: { settings: {} } };
  let fs = (typeof require !== "undefined") ? require("fs") : global.fs;
  let json5 = (typeof require !== "undefined") ? require("json5") : (global.JSON5 || global.json5);
  let path = (typeof require !== "undefined") ? require("path") : global.path;
  let polylabel = (typeof require !== "undefined") ? require("polylabel") : global.polylabel;
  let turf = global.turf || ((typeof require !== "undefined") ? require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js")) : null);

  if (typeof require !== "undefined") {
    try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
    try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
  }


  /**
   * PolitiesAtlasJoin executes a spatio-temporal join and topological simplification
   * between atlas.naissance and the Cliopatria historical dataset, generating atlas_simplified.naissance.
   *
   * It maps fine-grained Atlas entities and polygon components down to canonical Seshat polities,
   * merges constituents into unified MultiPolygons per polity at each epoch, preserves authentic
   * metropolitan colours, respects military occupation overrides, and produces sparse timeline keyframes.
   *
   * @class PolitiesAtlasJoin
   */
  global.PolitiesAtlasJoin = class {
    static config_path = "histmap/2.data_cleaning/polities_atlas_join/polities_atlas_join.json5";

    static country_prefixes = {
      "america": "us", "american": "us", "anatolia": "tr", "aquitaine": "fr", "aragon": "es",
      "assyria": "iq", "athens": "gr", "austria": "at", "austrian": "at", "aztec": "mx",
      "babylon": "iq", "bavaria": "de", "belgian": "be", "belgium": "be", "brazil": "br",
      "brazilian": "br", "britain": "gb", "british": "gb", "burgundy": "fr", "canada": "ca",
      "canadian": "ca", "castile": "es", "china": "cn", "chinese": "cn", "chola": "in",
      "danish": "dk", "denmark": "dk", "dutch": "nl", "egypt": "eg", "egyptian": "eg",
      "england": "gb", "florence": "it", "france": "fr", "french": "fr", "german": "de",
      "germany": "de", "greece": "gr", "greek": "gr", "greenland": "gl", "habsburg": "at",
      "han": "cn", "india": "in", "indian": "in", "ireland": "ie", "irish": "ie",
      "italian": "it", "italy": "it", "japan": "jp", "japanese": "jp", "maratha": "in",
      "maya": "mx", "mesopotamia": "iq", "mexican": "mx", "mexico": "mx", "ming": "cn",
      "moscow": "ru", "mughal": "in", "netherlands": "nl", "normandy": "fr", "norway": "no",
      "norwegian": "no", "ottoman": "tr", "poland": "pl", "polish": "pl", "portugal": "pt",
      "portuguese": "pt", "prussia": "de", "qing": "cn", "rome": "it", "russia": "ru",
      "russian": "ru", "saxony": "de", "scotland": "gb", "song": "cn", "soviet": "ru",
      "spain": "es", "spanish": "es", "sparta": "gr", "sumer": "iq", "sweden": "se",
      "swedish": "se", "tang": "cn", "tokugawa": "jp", "turkey": "tr", "united states": "us",
      "venice": "it", "wales": "gb", "weimar": "de"
    };


    /**
     * Converts arbitrary string to clean snake_case slug.
     *
     * @param {string} arg0_text
     *
     * @returns {string}
     */
    static slugify (arg0_text) {
      //Convert from parameters
      let text = (arg0_text !== undefined && arg0_text !== null) ? String(arg0_text) : "";

      //Declare local instance variables
      let cleaned;

      cleaned = text.toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");

      //Return statement
      return cleaned || "unknown";
    }


    /**
     * Derives a canonical, non-blank Seshat ID for a Cliopatria feature.
     *
     * @param {Object} arg0_feature
     *
     * @returns {string}
     */
    static getCanonicalSeshatId (arg0_feature) {
      //Convert from parameters
      let feature = arg0_feature;

      //Declare local instance variables
      let existing_id;
      let is_metropolitan_britain;
      let is_metropolitan_denmark;
      let is_metropolitan_france;
      let is_metropolitan_netherlands;
      let is_metropolitan_spain;
      let name;
      let name_lower;
      let prefix = "pl";
      let props;
      let slug;

      props = (feature && feature.properties) ? feature.properties : {};
      name = (props.Name || "unknown").trim();
      name_lower = name.toLowerCase();
      existing_id = (props.SeshatID || "").trim();

      //Identify metropolitan nations to ensure overseas colonies/mandates get distinct IDs
      is_metropolitan_britain = (name === "Kingdom of Great Britain" || name === "United Kingdom" || name === "Kingdom of England");
      is_metropolitan_france = (name.startsWith("French ") || name === "Kingdom of France") &&
        !name.includes("Mandate") && !name.includes("Africa") && !name.includes("Indochina") &&
        !name.includes("Antilles") && !name.includes("Oceania") && !name.includes("Establishments") &&
        !name.includes("Louisiana") && !name.includes("Guyana") && !name.includes("Gabon") &&
        !name.includes("Congo") && !name.includes("Sudan") && !name.includes("Dahomey") && !name.includes("Madagascar");
      is_metropolitan_netherlands = (name === "Netherlands" || name === "Dutch Republic");
      is_metropolitan_denmark = (name === "Kingdom of Denmark" || name === "Denmark" || name === "Denmark-Norway");
      is_metropolitan_spain = (name === "Kingdom of Spain" || name.includes("Spanish Republic") || name === "Crown of Castile" || name === "Crown of Aragon");

      if (existing_id) {
        if (existing_id.startsWith("gb_british_emp") && !is_metropolitan_britain) existing_id = "";
        if (existing_id.startsWith("fr_") && !is_metropolitan_france && !name_lower.includes("france")) existing_id = "";
        if (existing_id.startsWith("nl_dutch_emp") && !is_metropolitan_netherlands) existing_id = "";
        if (existing_id.startsWith("dk_") && !is_metropolitan_denmark) existing_id = "";
        if (existing_id.startsWith("es_") && !is_metropolitan_spain && !name_lower.includes("spain")) existing_id = "";
      }

      if (existing_id) return existing_id;

      //Derive country code prefix
      for (let kw in this.country_prefixes) {
        if (name_lower.includes(kw)) {
          prefix = this.country_prefixes[kw];
          break;
        }
      }

      slug = this.slugify(name);

      //Return statement
      return `${prefix}_${slug}`;
    }


    /**
     * Loads configuration, atlas.naissance, and Cliopatria GeoJSON datasets.
     *
     * @param {Object} [arg0_options]
     * @param {string} [arg0_options.config_path]
     *
     * @returns {Object} Loaded datasets and configuration
     */
    static A_loadData (arg0_options) {
      //Convert from parameters
      let options = (arg0_options) ? arg0_options : {};

      //Declare local instance variables
      let atlas_data;
      let cliopatria_data;
      let config;
      let config_file_path;

      config_file_path = options.config_path || this.config_path;
      console.log(`[PolitiesAtlasJoin] Loading configuration from: ${config_file_path}...`);
      config = json5.parse(fs.readFileSync(config_file_path, "utf8"));

      console.log(`[PolitiesAtlasJoin] Loading Atlas savefile from: ${config.input_atlas_path}...`);
      atlas_data = JSON.parse(fs.readFileSync(config.input_atlas_path, "utf8"));

      console.log(`[PolitiesAtlasJoin] Loading Cliopatria dataset from: ${config.input_cliopatria_path}...`);
      cliopatria_data = JSON.parse(fs.readFileSync(config.input_cliopatria_path, "utf8"));

      //Return statement
      return {
        atlas_data: atlas_data,
        cliopatria_data: cliopatria_data,
        config: config
      };
    }


    /**
     * Indexes Cliopatria polities with bounding boxes, spatial POIs, and canonical Seshat IDs.
     *
     * @param {Object} arg0_cliopatria_data
     *
     * @returns {Array<Object>} Indexed Cliopatria features
     */
    static B_indexCliopatria (arg0_cliopatria_data) {
      //Convert from parameters
      let cliopatria_data = arg0_cliopatria_data;

      //Declare local instance variables
      let features;
      let indexed = [];

      features = (cliopatria_data && cliopatria_data.features) ? cliopatria_data.features : [];
      console.log(`[PolitiesAtlasJoin] Indexing ${features.length} Cliopatria features...`);

      for (let i = 0; i < features.length; i++) {
        let f = features[i];
        let p = f.properties || {};

        //Filter out aggregate super-containers with parentheses
        if (p.Name && (p.Name.startsWith("(") || (p.Components && p.Components.trim() !== "")))
          continue;

        let bbox;
        try {
          bbox = turf.bbox(f);
        } catch (e) {
          continue;
        }

        let seshat_id = this.getCanonicalSeshatId(f);

        indexed.push({
          bbox: bbox,
          feature: f,
          from_year: p.FromYear,
          name: p.Name,
          poi: p.poi || [0, 0],
          seshat_id: seshat_id,
          to_year: p.ToYear
        });
      }

      console.log(`[PolitiesAtlasJoin] Successfully indexed ${indexed.length} non-aggregate polities.`);

      //Return statement
      return indexed;
    }


    /**
     * Spatially resolves the canonical polity identity for a constituent polygon at a specific year.
     *
     * @param {Array} arg0_polygon_coords
     * @param {number} arg1_year
     * @param {Array<Object>} arg2_indexed_clio
     * @param {Object} arg3_config
     * @param {Object} arg4_entity_context
     *
     * @returns {Object} Resolved polity identity
     */
    static C_matchPolygonToPolity (arg0_polygon_coords, arg1_year, arg2_indexed_clio, arg3_config, arg4_entity_context) {
      //Convert from parameters
      let polygon_coords = arg0_polygon_coords;
      let year = arg1_year;
      let indexed_clio = arg2_indexed_clio;
      let config = arg3_config;
      let entity_context = arg4_entity_context || {};

      //Guard clause: validate polygon ring
      if (!polygon_coords || !polygon_coords[0] || polygon_coords[0].length < 4) return null;

      //Declare local instance variables
      let atlas_name;
      let best_candidate = null;
      let best_distance = Infinity;
      let matching_candidates = [];
      let occupation_overrides;
      let poly_bbox;
      let poly_feat;
      let pt;
      let pt_coords;

      atlas_name = entity_context.name || "";
      occupation_overrides = config.occupation_overrides || [];

      try {
        poly_feat = turf.polygon(polygon_coords);
        pt = turf.pointOnFeature(poly_feat);
        pt_coords = pt.geometry.coordinates;
        poly_bbox = turf.bbox(poly_feat);
      } catch (e) {
        return null;
      }

      //1. Sovereign Integrity Shield: Check for historical military occupations
      for (let i = 0; i < occupation_overrides.length; i++) {
        let ovr = occupation_overrides[i];
        if (year >= ovr.start_year && year <= ovr.end_year) {
          let patterns = ovr.territory_patterns || [ovr.territory.toLowerCase()];
          let is_territory_match = patterns.some((p) => atlas_name.toLowerCase().includes(p.toLowerCase()));
          if (is_territory_match) {
            //Return statement: sovereign identity preserved
            return {
              is_protected: true,
              name: ovr.preserved_name || atlas_name,
              seshat_id: ovr.seshat_id || ("pl_" + this.slugify(ovr.preserved_name || atlas_name))
            };
          }
        }
      }

      //2. Spatial Point-in-Polygon Search against Cliopatria features active at current year
      for (let i = 0; i < indexed_clio.length; i++) {
        let c = indexed_clio[i];
        if (year < c.from_year || year > c.to_year) continue;

        //Bounding box overlap pre-check
        if (pt_coords[0] < c.bbox[0] || pt_coords[0] > c.bbox[2] ||
            pt_coords[1] < c.bbox[1] || pt_coords[1] > c.bbox[3]) {
          continue;
        }

        try {
          if (turf.booleanPointInPolygon(pt, c.feature)) {
            //Calculate distance to POI to rank candidates
            let poi_dist = Math.hypot(c.poi[0] - pt_coords[1], c.poi[1] - pt_coords[0]);
            matching_candidates.push({
              candidate: c,
              poi_dist: poi_dist
            });
          }
        } catch (err) {}
      }

      //Pick best matching candidate by POI proximity
      if (matching_candidates.length > 0) {
        matching_candidates.sort((a, b) => a.poi_dist - b.poi_dist);
        let chosen = matching_candidates[0].candidate;

        //Return statement
        return {
          is_protected: false,
          name: chosen.name,
          seshat_id: chosen.seshat_id
        };
      }

      //3. Spatial Proximity Fallback for coastal slivers and islands within 1.5 degrees (~150 km)
      for (let i = 0; i < indexed_clio.length; i++) {
        let c = indexed_clio[i];
        if (year < c.from_year || year > c.to_year) continue;

        let dx = Math.max(c.bbox[0] - pt_coords[0], 0, pt_coords[0] - c.bbox[2]);
        let dy = Math.max(c.bbox[1] - pt_coords[1], 0, pt_coords[1] - c.bbox[3]);
        let dist = Math.hypot(dx, dy);

        if (dist < 1.5 && dist < best_distance) {
          best_distance = dist;
          best_candidate = c;
        }
      }

      if (best_candidate) {
        //Return statement
        return {
          is_protected: false,
          name: best_candidate.name,
          seshat_id: best_candidate.seshat_id
        };
      }

      //4. Fallback: Retain native Atlas identity, assigning clean canonical seshat_id
      let fallback_slug = this.slugify(atlas_name || entity_context.id || "polity");

      //Return statement
      return {
        is_protected: false,
        name: atlas_name || "Unknown Polity",
        seshat_id: "at_" + fallback_slug
      };
    }


    /**
     * Performs topological union over an array of polygon coordinate arrays.
     *
     * @param {Array} arg0_polygons
     *
     * @returns {Object} Unified GeoJSON geometry
     */
    static D_unionPolygons (arg0_polygons) {
      //Convert from parameters
      let polygons = arg0_polygons || [];

      //Guard clauses
      if (polygons.length === 0) return null;
      if (polygons.length === 1) {
        return {
          coordinates: polygons[0],
          type: "Polygon"
        };
      }

      //Declare local instance variables
      let fc;
      let features = [];
      let union_result;

      for (let i = 0; i < polygons.length; i++) {
        try {
          features.push(turf.polygon(polygons[i]));
        } catch (e) {}
      }

      if (features.length === 1) return features[0].geometry;

      try {
        fc = turf.featureCollection(features);
        union_result = turf.union(fc);
        if (union_result && union_result.geometry) return union_result.geometry;
      } catch (e) {}

      //Fallback: Combine into MultiPolygon if union topological calculation fails
      //Return statement
      return {
        coordinates: polygons,
        type: "MultiPolygon"
      };
    }


    /**
     * Resolves the active state of an Atlas entity at a target timestamp.
     *
     * @param {Object} arg0_entity
     * @param {number} arg1_target_ts
     *
     * @returns {Object|null}
     */
    static getEntityStateAtTimestamp (arg0_entity, arg1_target_ts) {
      //Convert from parameters
      let entity = arg0_entity;
      let target_ts = arg1_target_ts;

      //Guard clause
      if (!entity || !entity.history) return null;

      //Declare local instance variables
      let active_geom = null;
      let active_props = {};
      let active_symbol = null;
      let active_ts = null;
      let is_hidden = false;
      let timestamps;

      timestamps = Object.keys(entity.history).map(Number).sort((a, b) => a - b);
      if (timestamps.length === 0 || target_ts < timestamps[0]) return null;

      for (let i = 0; i < timestamps.length; i++) {
        let ts = timestamps[i];
        if (ts > target_ts) break;

        let kf = entity.history[String(ts)];
        if (!kf) continue;

        if (kf[0] !== undefined && kf[0] !== "undefined") {
          if (kf[0] === null) {
            active_geom = null;
            active_ts = ts;
          } else if (kf[0].feature) {
            active_geom = kf[0].feature;
            active_ts = ts;
            is_hidden = false;
          }
        }

        if (kf[1] !== undefined && kf[1] !== null && kf[1] !== "undefined")
          active_symbol = Object.assign({}, active_symbol, kf[1]);

        if (kf[2] !== undefined && kf[2] !== null && kf[2] !== "undefined") {
          active_props = Object.assign({}, active_props, kf[2]);
          if (kf[2].hidden === true) {
            is_hidden = true;
            active_geom = null;
          }
        }
      }

      if (is_hidden || !active_geom || !active_geom.geometry) return null;

      //Lifespan check: if entity ceased recording before modern era and has ended, derender
      let last_entity_ts = timestamps[timestamps.length - 1];
      if (target_ts > last_entity_ts) {
        let last_kf = entity.history[String(last_entity_ts)];
        if (last_kf && (last_kf[0] === null || (last_kf[2] && last_kf[2].hidden === true)))
          return null;

        let last_date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(last_entity_ts) : null;
        let last_year = (last_date) ? last_date.year : Math.round(last_entity_ts / 8766);
        let target_date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(target_ts) : null;
        let target_year = (target_date) ? target_date.year : Math.round(target_ts / 8766);

        if (last_year < 1900 && target_year > last_year + 5) return null;
      }

      //Return statement
      return {
        active_ts: active_ts,
        geometry: active_geom.geometry,
        id: entity.id,
        metadata: entity.metadata,
        properties: active_props,
        symbol: active_symbol
      };
    }


    /**
     * Iterates through all discrete timestamps, matching and unioning polygons per Seshat polity.
     *
     * @param {Object} arg0_atlas_data
     * @param {Array<Object>} arg1_indexed_clio
     * @param {Object} arg2_config
     *
     * @returns {Map<string, Object>} Reconstructed unified polities
     */
    static E_processAllTimestamps (arg0_atlas_data, arg1_indexed_clio, arg2_config) {
      //Convert from parameters
      let atlas_data = arg0_atlas_data;
      let indexed_clio = arg1_indexed_clio;
      let config = arg2_config;

      //Declare local instance variables
      let all_timestamps = new Set();
      let entity_keys = Object.keys(atlas_data).filter((k) => k !== "map_settings");
      let last_log_time = Date.now();
      let polygon_entities = {};
      let sorted_timestamps;
      let total_keyframes_recorded = 0;
      let total_unions_performed = 0;
      let unified_polities = new Map();

      for (let i = 0; i < entity_keys.length; i++) {
        let e = atlas_data[entity_keys[i]];
        if (e.class_name === "GeometryPolygon" && e.history) {
          polygon_entities[entity_keys[i]] = e;
          let ts_keys = Object.keys(e.history);
          for (let x = 0; x < ts_keys.length; x++)
            all_timestamps.add(parseInt(ts_keys[x]));
        }
      }

      sorted_timestamps = Array.from(all_timestamps).sort((a, b) => a - b);
      console.log(`[PolitiesAtlasJoin] Processing ${sorted_timestamps.length} timestamps across ${Object.keys(polygon_entities).length} Atlas polygons...`);

      for (let t_idx = 0; t_idx < sorted_timestamps.length; t_idx++) {
        let current_ts = sorted_timestamps[t_idx];
        let current_date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(current_ts) : null;
        let current_year = (current_date) ? current_date.year : Math.round(current_ts / 8766);

        //Gather active polygon entities at current timestamp
        let active_states = [];
        let poly_ids = Object.keys(polygon_entities);

        for (let i = 0; i < poly_ids.length; i++) {
          let state = this.getEntityStateAtTimestamp(polygon_entities[poly_ids[i]], current_ts);
          if (state) active_states.push(state);
        }

        //Break each active entity into constituent polygons and match to canonical Seshat polities
        let groups = new Map();

        for (let i = 0; i < active_states.length; i++) {
          let state = active_states[i];
          let g = state.geometry;
          let poly_coords_array = (g.type === "Polygon") ? [g.coordinates] : g.coordinates;

          for (let p_idx = 0; p_idx < poly_coords_array.length; p_idx++) {
            let coords = poly_coords_array[p_idx];
            let identity = this.C_matchPolygonToPolity(coords, current_year, indexed_clio, config, {
              id: state.id,
              name: (state.properties && state.properties.name) ? state.properties.name : ""
            });

            if (!identity) continue;
            let g_key = identity.seshat_id;

            if (!groups.has(g_key)) {
              groups.set(g_key, {
                identity: identity,
                polygons: [],
                primary_state: state,
                states: []
              });
            }

            let g_entry = groups.get(g_key);
            g_entry.polygons.push(coords);
            g_entry.states.push(state);
          }
        }

        //Process each active group
        groups.forEach((group_val, g_key) => {
          let primary_state = group_val.primary_state;

          //Authentic colour preservation from metropolitan constituent
          let authentic_fill = (primary_state && primary_state.symbol && primary_state.symbol.polygonFill)
            ? primary_state.symbol.polygonFill
            : "#7289da";

          let current_symbol = {
            polygonFill: authentic_fill,
            textSize: (primary_state && primary_state.symbol && primary_state.symbol.textSize) || 14
          };

          //Constituent signature based on polygon count and names
          let current_signature = `${group_val.polygons.length}|${group_val.identity.name}|${authentic_fill}`;

          if (!unified_polities.has(g_key)) {
            unified_polities.set(g_key, {
              first_ts: current_ts,
              identity: group_val.identity,
              is_active: false,
              keyframes: {},
              last_geom: null,
              last_props: null,
              last_signature: null,
              last_symbol: null,
              last_ts: current_ts,
              primary_atlas_id: primary_state.id
            });
          }

          let pol_entry = unified_polities.get(g_key);
          pol_entry.last_ts = current_ts;

          if (pol_entry.last_signature !== current_signature) {
            let merged_geom = this.D_unionPolygons(group_val.polygons);
            total_unions_performed++;

            let current_props = {
              cliopatria_name: group_val.identity.name,
              name: group_val.identity.name,
              seshat_id: group_val.identity.seshat_id
            };

            //Sparse Keyframe Rule
            if (!pol_entry.is_active || !pol_entry.last_props) {
              pol_entry.keyframes[String(current_ts)] = [
                {
                  feature: {
                    geometry: merged_geom,
                    properties: {},
                    type: "Feature"
                  }
                },
                current_symbol,
                current_props
              ];
              pol_entry.last_symbol = current_symbol;
              pol_entry.last_props = current_props;
            } else {
              let symbol_changed = (JSON.stringify(current_symbol) !== JSON.stringify(pol_entry.last_symbol));
              let props_changed = (JSON.stringify(current_props) !== JSON.stringify(pol_entry.last_props));

              if (symbol_changed || props_changed) {
                pol_entry.keyframes[String(current_ts)] = [
                  {
                    feature: {
                      geometry: merged_geom,
                      properties: {},
                      type: "Feature"
                    }
                  },
                  current_symbol,
                  current_props
                ];
                pol_entry.last_symbol = current_symbol;
                pol_entry.last_props = current_props;
              } else {
                pol_entry.keyframes[String(current_ts)] = [
                  {
                    feature: {
                      geometry: merged_geom,
                      properties: {},
                      type: "Feature"
                    }
                  }
                ];
              }
            }

            pol_entry.is_active = true;
            pol_entry.last_geom = merged_geom;
            pol_entry.last_signature = current_signature;
            total_keyframes_recorded++;
          }
        });

        //Terminate polities that ceased to be active
        unified_polities.forEach((pol_entry, g_key) => {
          if (!groups.has(g_key) && pol_entry.is_active) {
            pol_entry.keyframes[String(current_ts)] = [null];
            pol_entry.is_active = false;
            pol_entry.last_geom = null;
            pol_entry.last_signature = null;
            total_keyframes_recorded++;
          }
        });

        //Periodic progress logging
        if (Date.now() - last_log_time > 5000 || t_idx === sorted_timestamps.length - 1) {
          let pct = Math.round((t_idx / sorted_timestamps.length) * 100);
          console.log(`[PolitiesAtlasJoin] Progress: ${pct}% (Epoch: Year ${current_year}, TS ${t_idx + 1}/${sorted_timestamps.length}, KFs: ${total_keyframes_recorded})`);
          last_log_time = Date.now();
        }
      }

      console.log(`[PolitiesAtlasJoin] Finished timestamp processing. Generated ${unified_polities.size} consolidated polities with ${total_keyframes_recorded} sparse keyframes.`);

      //Return statement
      return unified_polities;
    }


    /**
     * Reassembles the final savefile containing consolidated polities, FeatureGroups, and layers.
     *
     * @param {Map<string, Object>} arg0_unified_polities
     * @param {Object} arg1_atlas_data
     * @param {Object} arg2_config
     *
     * @returns {Object} Complete savefile object
     */
    static F_assembleSavefile (arg0_unified_polities, arg1_atlas_data, arg2_config) {
      //Convert from parameters
      let unified_polities = arg0_unified_polities;
      let atlas_data = arg1_atlas_data;
      let config = arg2_config;

      //Declare local instance variables
      let final_savefile = {};
      let group_entities_map = new Map();
      let original_entity_to_group = new Map();

      console.log(`[PolitiesAtlasJoin] Assembling savefile structure...`);

      //1. Preserve map_settings
      if (atlas_data.map_settings) final_savefile.map_settings = atlas_data.map_settings;

      //2. Map original entity IDs to FeatureGroups
      for (let k in atlas_data) {
        if (atlas_data[k].class_name === "FeatureGroup") {
          let fg_val = (typeof atlas_data[k].value === "string") ?
            JSON.parse(atlas_data[k].value) : atlas_data[k].value;

          if (fg_val && fg_val.entities) {
            for (let i = 0; i < fg_val.entities.length; i++) {
              original_entity_to_group.set(fg_val.entities[i].id, k);
            }
          }
          group_entities_map.set(k, []);
        }
      }

      //3. Reconstruct GeometryPolygon entities
      let pol_keys = Array.from(unified_polities.keys());
      let used_ids = new Set();

      for (let i = 0; i < pol_keys.length; i++) {
        let g_key = pol_keys[i];
        let pol_entry = unified_polities.get(g_key);

        let entity_id = pol_entry.primary_atlas_id;
        if (!entity_id || used_ids.has(entity_id)) {
          entity_id = String(Math.floor(Math.random() * 90000000000 + 10000000000));
        }
        used_ids.add(entity_id);

        let new_entity = {
          class_name: "GeometryPolygon",
          history: pol_entry.keyframes,
          id: entity_id,
          metadata: {
            description: `Simplified Polity: ${pol_entry.identity.name}\nSeshatID: ${pol_entry.identity.seshat_id}\nBase Source: Cliopatria`,
            tags: ["Polities"]
          },
          type: "geometry"
        };

        final_savefile[entity_id] = new_entity;

        //Anchor into regional FeatureGroup
        let assigned_group = original_entity_to_group.get(pol_entry.primary_atlas_id);
        if (!assigned_group) assigned_group = "94350264119"; //Default to 3. Europe

        if (group_entities_map.has(assigned_group)) {
          group_entities_map.get(assigned_group).push({
            class_name: "GeometryPolygon",
            id: entity_id
          });
        }
      }

      //4. Reconstruct FeatureGroups and other non-polygon entities
      for (let k in atlas_data) {
        let orig = atlas_data[k];
        if (orig.class_name === "FeatureGroup") {
          let fg_val = (typeof orig.value === "string") ? JSON.parse(orig.value) : orig.value;

          if (group_entities_map.has(k) && fg_val && fg_val.name !== "Atlas") {
            fg_val.entities = group_entities_map.get(k);
            orig.value = JSON.stringify(fg_val);
          }
          final_savefile[k] = orig;
        } else if (orig.class_name !== "GeometryPolygon" && k !== "map_settings") {
          final_savefile[k] = orig;
        }
      }

      console.log(`[PolitiesAtlasJoin] Assembled savefile with ${Object.keys(final_savefile).length} top-level entities.`);

      //Return statement
      return final_savefile;
    }


    /**
     * Main pipeline entry point.
     */
    static async run () {
      let loaded = this.A_loadData();
      let indexed_clio = this.B_indexCliopatria(loaded.cliopatria_data);
      let unified_polities = this.E_processAllTimestamps(loaded.atlas_data, indexed_clio, loaded.config);
      let final_savefile = this.F_assembleSavefile(unified_polities, loaded.atlas_data, loaded.config);

      let output_path = loaded.config.output_atlas_path;
      console.log(`[PolitiesAtlasJoin] Writing output to: ${output_path}...`);

      let out_stream = fs.createWriteStream(output_path, { encoding: "utf8" });
      out_stream.write("{\n");
      let keys = Object.keys(final_savefile);
      for (let i = 0; i < keys.length; i++) {
        let k = keys[i];
        let val_str = JSON.stringify(final_savefile[k]);
        let comma = (i < keys.length - 1) ? "," : "";
        out_stream.write(`  ${JSON.stringify(k)}: ${val_str}${comma}\n`);
      }
      out_stream.write("}\n");
      out_stream.end();

      await new Promise((resolve) => out_stream.on("finish", resolve));
      let stat = fs.statSync(output_path);
      console.log(`[PolitiesAtlasJoin] Finished successfully! Saved ${(stat.size / 1024 / 1024).toFixed(2)} MB to ${output_path}`);
    }
  };

  //Auto-execute if executed directly via Node CLI
  if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    global.PolitiesAtlasJoin.run()
      .then(() => process.exit(0))
      .catch((err) => {
        console.error("[PolitiesAtlasJoin] Fatal error:", err);
        process.exit(1);
      });
  }
})();
