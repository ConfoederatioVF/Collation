(function () {
  if (!global.ve) global.ve = { registry: { settings: {} } };
  let fs = (typeof require !== "undefined") ? require("fs") : global.fs;
  let path = (typeof require !== "undefined") ? require("path") : global.path;
  let turf = global.turf || ((typeof require !== "undefined") ? require(path.resolve(process.cwd(), "UF/js/geospatiale/turf.min.js")) : null);

  if (typeof require !== "undefined") {
    try { require(path.resolve(process.cwd(), "UF/js/date/date_basic.js")); } catch (e) {}
    try { require(path.resolve(process.cwd(), "UF/js/date/date_conversion.js")); } catch (e) {}
  }

  /**
   * CShapesAtlasJoin spatiotemporally joins CShapes-Europe (1816-1886) and CShapes-2.0 (1886+)
   * into atlas_simplified.naissance, ensuring CShapes names take precedence, colours are inherited
   * via pole of inaccessibility, non-European polities (like Turkey-in-Asia and Siberia) are preserved,
   * canonical Seshat IDs are accurately assigned, and underlying CShapes-Europe entities are cleanly
   * deactivated after 1886.
   *
   * @class CShapesAtlasJoin
   */
  global.CShapesAtlasJoin = class {
    static c2_path = "saves/CShapes-2.0.geojson";
    static c2_txt_path = "histmap/2.data_cleaning/cshapes_join/cshapes_2_polities.txt";
    static eu_path = "saves/CShapes-Europe.geojson";
    static eu_txt_path = "histmap/2.data_cleaning/cshapes_join/cshapes_europe_polities.txt";
    static out_atlas_path = "saves/atlas_simplified.naissance";
    static raw_atlas_path = "saves/atlas.naissance";
    static simp_atlas_path = (typeof fs !== "undefined" && fs.existsSync("saves/atlas_simplified.naissance.bak"))
      ? "saves/atlas_simplified.naissance.bak"
      : "saves/atlas_simplified.naissance";

    static cow_seshat_map = {
      2: "us_united_states_modern",
      210: "nl_dutch_emp_2",
      225: "ch_swiss_conf_4",
      230: "es_spanish_emp_3",
      235: "pt_portugal_modern_1",
      300: "at_habsburg_2",
      305: "at_austrian_rep_2",
      325: "it_italy_k_modern",
      345: "sr_yugoslavia",
      360: "ro_romania_modern",
      390: "dk_danish_emp_modern",
      750: "in_british_raj",
      775: "mm_konbaung_dyn"
    };

    /**
     * Builds a fast spatial bounding-box index of active Atlas polygons at a target timestamp.
     *
     * @param {Object} arg0_atlas_data
     * @param {number} arg1_target_ts
     *
     * @returns {Array<Object>} List of indexed active features with bounding boxes
     */
    static buildSpatialIndex (arg0_atlas_data, arg1_target_ts) {
      //Convert from parameters
      let atlas_data = arg0_atlas_data;
      let target_ts = arg1_target_ts;

      //Declare local instance variables
      let bbox;
      let ent;
      let feat;
      let indexed = [];
      let keys;
      let state;

      keys = Object.keys(atlas_data);
      for (let i = 0; i < keys.length; i++) {
        ent = atlas_data[keys[i]];
        if (ent.class_name !== "GeometryPolygon" || !ent.history) continue;

        state = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, target_ts);
        if (!state || !state.geometry) continue;

        try {
          feat = turf.feature(state.geometry);
          bbox = turf.bbox(feat);
          indexed.push({
            bbox: bbox,
            feature: feat,
            id: ent.id,
            symbol: state.symbol
          });
        } catch (e) {}
      }

      //Return statement
      return indexed;
    }

    /**
     * Computes a fast string signature of geometry rings and coordinate sums to detect topological changes.
     *
     * @param {Object} arg0_geom
     *
     * @returns {string} Deterministic geometry signature
     */
    static computeGeomSignature (arg0_geom) {
      //Convert from parameters
      let geom = arg0_geom;

      //Guard clause
      if (!geom) return "null";

      //Declare local instance variables
      let count = 0;
      let polys = (geom.type === "MultiPolygon") ? geom.coordinates : [geom.coordinates];
      let ring;
      let sum_x = 0;
      let sum_y = 0;

      for (let p = 0; p < polys.length; p++) {
        for (let r = 0; r < polys[p].length; r++) {
          ring = polys[p][r];
          count += ring.length;
          if (ring.length > 0) {
            sum_x += ring[0][0] + ring[ring.length - 1][0];
            sum_y += ring[0][1] + ring[ring.length - 1][1];
          }
        }
      }

      //Return statement
      return polys.length + "|" + count + "|" + sum_x.toFixed(2) + "|" + sum_y.toFixed(2);
    }

    /**
     * Deactivates an active entity, appending a null keyframe.
     *
     * @param {string} arg0_id
     * @param {number} arg1_ts
     * @param {Map<string, Object>} arg2_history_map
     * @param {Map<string, Object>} arg3_state_tracker
     */
    static deactivateEntity (arg0_id, arg1_ts, arg2_history_map, arg3_state_tracker) {
      //Convert from parameters
      let history_map = arg2_history_map;
      let id = arg0_id;
      let state_tracker = arg3_state_tracker;
      let ts = String(arg1_ts);

      //Declare local instance variables
      let prev = state_tracker.get(id);

      if (prev && prev.is_active) {
        if (!history_map.has(id)) history_map.set(id, {});
        history_map.get(id)[ts] = [null];
        prev.is_active = false;
        prev.last_geom = null;
        prev.last_geom_sig = null;
      }
    }

    /**
     * Helper to assemble and emit a CShapes polity feature group into the savefile.
     *
     * @param {string} arg0_target_id
     * @param {number} arg1_ts
     * @param {Object} arg2_grp
     * @param {Array<Object>} arg3_spatial_index
     * @param {Map<string, Object>} arg4_meta_map
     * @param {Map<string, Object>} arg5_history_map
     * @param {Map<string, Object>} arg6_state_tracker
     * @param {Map<string, string>} [arg7_name_map]
     */
    static emitCShapesPolity (arg0_target_id, arg1_ts, arg2_grp, arg3_spatial_index, arg4_meta_map, arg5_history_map, arg6_state_tracker, arg7_name_map) {
      let grp = arg2_grp;
      let history_map = arg5_history_map;
      let meta_map = arg4_meta_map;
      let name_map = arg7_name_map;
      let spatial_index = arg3_spatial_index;
      let state_tracker = arg6_state_tracker;
      let target_id = arg0_target_id;
      let ts = arg1_ts;

      let merged_geom = grp.combined_geom;
      if (!merged_geom) {
        let combined_polys = [];
        for (let f = 0; f < grp.features.length; f++) {
          let g = grp.features[f].geometry;
          if (g.type === "Polygon") combined_polys.push(g.coordinates);
          else if (g.type === "MultiPolygon") {
            for (let m = 0; m < g.coordinates.length; m++) combined_polys.push(g.coordinates[m]);
          }
        }

        merged_geom = (combined_polys.length === 1)
          ? { coordinates: combined_polys[0], type: "Polygon" }
          : { coordinates: combined_polys, type: "MultiPolygon" };
      }

      let color = this.inheritColorViaPOI(grp.features[0], spatial_index, "#7289da");
      let sym = { polygonFill: color, textSize: 14 };

      //Prevent name mutations across keyframes by preserving existing canonical name
      let canon_name = (name_map && name_map.has(target_id)) ? name_map.get(target_id) : (grp.name || grp.meta.name);
      if (name_map && !name_map.has(target_id)) name_map.set(target_id, canon_name);

      let props = {
        cow: grp.meta.cow || grp.meta.cow_code,
        cow_code: grp.meta.cow_code || grp.meta.cow,
        name: canon_name,
        seshat_id: grp.meta.seshat_id
      };

      if (!meta_map.has(target_id)) {
        meta_map.set(target_id, {
          class_name: "GeometryPolygon",
          id: target_id,
          metadata: {
            description: `Simplified Polity: ${props.name}\nSeshatID: ${props.seshat_id}\nCOW: ${props.cow_code}\nBase Source: CShapes`,
            tags: ["Polities"]
          },
          type: "geometry"
        });
      }

      this.emitKeyframe(target_id, ts, merged_geom, sym, props, history_map, state_tracker);
    }

    /**
     * Emits a sparse diff keyframe, omitting unchanged properties/symbols to prevent duplication.
     *
     * @param {string} arg0_id
     * @param {number} arg1_ts
     * @param {Object} arg2_geom
     * @param {Object} arg3_symbol
     * @param {Object} arg4_props
     * @param {Map<string, Object>} arg5_history_map
     * @param {Map<string, Object>} arg6_state_tracker
     */
    static emitKeyframe (arg0_id, arg1_ts, arg2_geom, arg3_symbol, arg4_props, arg5_history_map, arg6_state_tracker) {
      //Convert from parameters
      let geom = arg2_geom;
      let history_map = arg5_history_map;
      let id = arg0_id;
      let props = arg4_props;
      let state_tracker = arg6_state_tracker;
      let symbol = arg3_symbol;
      let ts = String(arg1_ts);

      //Declare local instance variables
      let diff_props = {};
      let feat_obj = { feature: { geometry: geom, properties: {}, type: "Feature" } };
      let geom_changed = false;
      let prev = state_tracker.get(id);
      let props_changed = false;
      let sig = this.computeGeomSignature(geom);
      let symbol_changed = false;

      if (!history_map.has(id)) history_map.set(id, {});

      if (!prev || !prev.is_active) {
        //Activation keyframe: emit full geometry, symbol, and properties
        history_map.get(id)[ts] = [feat_obj, symbol, props];
        state_tracker.set(id, {
          is_active: true,
          last_geom: geom,
          last_geom_sig: sig,
          last_props: Object.assign({}, props),
          last_symbol: Object.assign({}, symbol)
        });
        return;
      }

      geom_changed = (sig !== prev.last_geom_sig);
      symbol_changed = (symbol && prev.last_symbol && symbol.polygonFill !== prev.last_symbol.polygonFill);

      for (let p in props) {
        if (props[p] !== prev.last_props[p]) {
          props_changed = true;
          diff_props[p] = props[p];
        }
      }

      //Sparse check: if nothing changed, do not emit redundant keyframe
      if (!geom_changed && !symbol_changed && !props_changed) return;

      if (props_changed) {
        history_map.get(id)[ts] = [feat_obj, (symbol_changed ? symbol : null), diff_props];
        prev.last_props = Object.assign({}, prev.last_props, diff_props);
        if (symbol_changed) prev.last_symbol = Object.assign({}, symbol);
        prev.last_geom = geom;
        prev.last_geom_sig = sig;
      } else if (symbol_changed) {
        history_map.get(id)[ts] = [feat_obj, symbol];
        prev.last_symbol = Object.assign({}, symbol);
        prev.last_geom = geom;
        prev.last_geom_sig = sig;
      } else {
        //Sparse keyframe: boundary geometry only
        history_map.get(id)[ts] = [feat_obj];
        prev.last_geom = geom;
        prev.last_geom_sig = sig;
      }
    }

    /**
     * Resolves the canonical, time-varying Seshat ID for historical polities.
     *
     * @param {number|string} arg0_cow_code
     * @param {number} arg1_year
     * @param {string} [arg2_default_seshat]
     *
     * @returns {string} Canonical Seshat ID
     */
    static getCanonicalSeshatId (arg0_cow_code, arg1_year, arg2_default_seshat) {
      //Convert from parameters
      let cow_code = Number(arg0_cow_code);
      let default_seshat = (arg2_default_seshat !== undefined) ? String(arg2_default_seshat) : "";
      let year = Number(arg1_year);

      //Declare local instance variables
      let seshat_id = default_seshat;

      if (cow_code === 255) {
        //Prussia pre-1871; Germany post-1871
        if (year < 1871) {
          seshat_id = "de_hohenzollern_2";
        } else if (year < 1918) {
          seshat_id = "de_hohenzollern_3";
        } else if (year < 1933) {
          seshat_id = "de_weimar_rep";
        } else if (year <= 1945) {
          seshat_id = "de_ns_germany";
        } else {
          seshat_id = "de_germany_unified_1";
        }
      } else if (cow_code === 200) {
        seshat_id = (year <= 1852) ? "gb_british_emp_1" : "gb_british_emp_2";
      } else if (cow_code === 365) {
        if (year < 1917) {
          seshat_id = "ru_romanov_dyn_2";
        } else if (year <= 1991) {
          seshat_id = "ru_soviet_union";
        } else {
          seshat_id = "ru_russian_federation";
        }
      } else if (cow_code === 640) {
        seshat_id = (year <= 1922) ? "tr_ottoman_emp_4" : "tr_turkey_rep";
      } else if (cow_code === 220) {
        seshat_id = (year < 1870) ? "fr_france_modern_1" : "fr_france_modern_2";
      } else if (cow_code === 710) {
        if (year < 1912) {
          seshat_id = "cn_qing_dyn_1";
        } else if (year < 1949) {
          seshat_id = "cn_rep_china_1";
        } else {
          seshat_id = "cn_chinese_peoples_rep";
        }
      } else if (cow_code === 380) {
        seshat_id = (year <= 1905) ? "sv_united_k_sweden_and_norway" : "sv_sweden_k_modern";
      } else if (cow_code === 2) {
        seshat_id = (year < 1865) ? "us_antebellum" : "us_united_states_modern";
      } else if (CShapesAtlasJoin.cow_seshat_map[cow_code]) {
        seshat_id = CShapesAtlasJoin.cow_seshat_map[cow_code];
      }

      //Return statement
      return seshat_id;
    }

    /**
     * Computes the pole of inaccessibility of a feature and samples colour from the Atlas spatial index.
     *
     * @param {Object} arg0_feature
     * @param {Array<Object>} arg1_spatial_index
     * @param {string} [arg2_default_color]
     *
     * @returns {string} Inherited hex colour string
     */
    static inheritColorViaPOI (arg0_feature, arg1_spatial_index, arg2_default_color) {
      //Convert from parameters
      let default_color = arg2_default_color || "#7289da";
      let feature = arg0_feature;
      let spatial_index = arg1_spatial_index;

      //Guard clause
      if (!feature || !spatial_index) return default_color;

      //Declare local instance variables
      let b;
      let c;
      let item;
      let pt;

      try {
        pt = turf.pointOnFeature(feature);
        c = pt.geometry.coordinates;

        for (let i = 0; i < spatial_index.length; i++) {
          item = spatial_index[i];
          b = item.bbox;
          if (c[0] >= b[0] && c[0] <= b[2] && c[1] >= b[1] && c[1] <= b[3]) {
            if (turf.booleanPointInPolygon(pt, item.feature)) {
              if (item.symbol && item.symbol.polygonFill)
                //Return statement
                return item.symbol.polygonFill;
            }
          }
        }
      } catch (e) {}

      //Return statement
      return default_color;
    }

    /**
     * Determines whether a feature intersects the active European land footprint of CShapes-Europe.
     *
     * @param {Object} arg0_feat
     * @param {Array<Object>} arg1_active_eu
     * @param {Array<Array<number>>} arg2_eu_bboxes
     *
     * @returns {boolean} True if feature intersects active CShapes-Europe land
     */
    static intersectsActiveEU (arg0_feat, arg1_active_eu, arg2_eu_bboxes) {
      //Convert from parameters
      let active_eu = arg1_active_eu;
      let eu_bboxes = arg2_eu_bboxes;
      let feat = arg0_feat;

      //Guard clause
      if (!feat || !feat.geometry) return false;

      //Declare local instance variables
      let b;
      let bb;

      try {
        bb = turf.bbox(feat);
        for (let i = 0; i < active_eu.length; i++) {
          b = eu_bboxes[i];
          if (!(bb[2] < b[0] || bb[0] > b[2] || bb[3] < b[1] || bb[1] > b[3])) {
            if (turf.booleanIntersects(feat, active_eu[i])) return true;
          }
        }
      } catch (e) {}

      //Return statement
      return false;
    }


    /**
     * Parses the CShapes metadata text file mapping names and codes to Seshat IDs and COW codes.
     *
     * @param {string} arg0_file_path
     *
     * @returns {Map<string, Object>} Map keyed by code/name to metadata object
     */
    static loadMetadataTable (arg0_file_path) {
      //Convert from parameters
      let file_path = arg0_file_path;

      //Declare local instance variables
      let cow;
      let from;
      let lines;
      let name;
      let parts;
      let raw;
      let seshat;
      let table = new Map();
      let to;

      raw = fs.readFileSync(file_path, "utf8");
      lines = raw.trim().split("\n");

      for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith("#") || !line) continue;

        parts = line.split(" | ");
        if (parts.length >= 6) {
          let code = parts[0].trim();
          name = parts[1].trim();
          from = parseInt(parts[2].trim());
          to = parseInt(parts[3].trim());
          seshat = parts[4].trim();
          cow = parseInt(parts[5].trim()) || null;

          let entry = {
            code: code,
            cow: cow,
            cow_code: cow,
            from: from,
            name: name,
            seshat_id: seshat,
            to: to
          };

          table.set(code + "|" + name, entry);
          table.set(name.toLowerCase(), entry);
          if (!table.has(code)) table.set(code, entry);
        }
      }

      //Return statement
      return table;
    }

    /**
     * Loads all source savefiles, GeoJSON layers, and metadata correlation mappings.
     *
     * @returns {Object} Loaded datasets
     */
    static loadSources () {
      //Declare local instance variables
      let atlas_data;
      let c2_geo;
      let c2_meta;
      let eu_geo;
      let eu_meta;
      let simp_data;

      console.log(`[CShapesAtlasJoin] Loading source datasets (base: ${this.simp_atlas_path})...`);
      simp_data = JSON.parse(fs.readFileSync(this.simp_atlas_path, "utf8"));
      atlas_data = JSON.parse(fs.readFileSync(this.raw_atlas_path, "utf8"));
      eu_geo = JSON.parse(fs.readFileSync(this.eu_path, "utf8"));
      c2_geo = JSON.parse(fs.readFileSync(this.c2_path, "utf8"));
      eu_meta = this.loadMetadataTable(this.eu_txt_path);
      c2_meta = this.loadMetadataTable(this.c2_txt_path);

      console.log(`[CShapesAtlasJoin] Loaded ${eu_geo.features.length} EU features, ${c2_geo.features.length} C2 features.`);

      //Return statement
      return {
        atlas_data: atlas_data,
        c2_geo: c2_geo,
        c2_meta: c2_meta,
        eu_geo: eu_geo,
        eu_meta: eu_meta,
        simp_data: simp_data
      };
    }

    /**
     * Main execution routine: spatiotemporally joins CShapes-Europe (1816-1886) and CShapes-2.0 (1886+),
     * inherits pole-of-inaccessibility colours, and outputs compliant sparse keyframes.
     *
     * @returns {Promise<void>}
     */
    static async run () {
      //Declare local instance variables
      let active_c2;
      let active_eu;
      let all_timestamps = new Set();
      let c2_by_polity;
      let entity_history_map = new Map();
      let entity_meta_map = new Map();
      let entity_name_map = new Map();
      let entity_state_tracker = new Map();
      let eu_by_polity;
      let last_log = Date.now();
      let out_stream;
      let polities_join = require(path.resolve(process.cwd(), "histmap/3.data_transform/polities_atlas_join/polities_atlas_join.js"));
      let seshat_to_entity_id = new Map();
      let sources = this.loadSources();
      let ts_keys;

      //1. Index all base entities in existing atlas_simplified
      for (let k in sources.simp_data) {
        let ent = sources.simp_data[k];
        if (ent.class_name === "GeometryPolygon" && ent.history) {
          entity_meta_map.set(k, {
            class_name: "GeometryPolygon",
            id: ent.id,
            metadata: ent.metadata,
            type: "geometry"
          });
          entity_history_map.set(k, {});

          let init_name = null;
          let init_seshat = null;
          let ts_arr = Object.keys(ent.history).sort((a, b) => Number(a) - Number(b));
          for (let i = 0; i < ts_arr.length; i++) {
            let kf = ent.history[ts_arr[i]];
            if (kf && kf[2] && kf[2].name) {
              init_name = kf[2].name;
              init_seshat = kf[2].seshat_id;
              break;
            }
          }

          if (init_name) entity_name_map.set(k, init_name);

          let desc = (ent.metadata && ent.metadata.description) || "";
          let match = desc.match(/SeshatID:\s*([^\n]+)/);
          if (match) {
            let s_id = match[1].trim();
            if (!seshat_to_entity_id.has(s_id)) seshat_to_entity_id.set(s_id, k);
          }

          for (let ts in ent.history) all_timestamps.add(Number(ts));
        }
      }

      //Explicit canonical metropole mappings
      seshat_to_entity_id.set("gb_british_emp_1", "87693477140");
      seshat_to_entity_id.set("gb_british_emp_2", "87692477137");
      seshat_to_entity_id.set("us_antebellum", "999152906");
      seshat_to_entity_id.set("fr_france_modern_1", "82079236664");
      seshat_to_entity_id.set("ru_romanov_dyn_2", "10264500703");
      seshat_to_entity_id.set("ru_soviet_union", "10264500703");
      seshat_to_entity_id.set("ru_russian_federation", "10264500703");
      seshat_to_entity_id.set("tr_ottoman_emp_3", "52817277008");
      seshat_to_entity_id.set("tr_ottoman_emp_4", "52816277001");

      ts_keys = Array.from(all_timestamps).sort((a, b) => a - b);
      console.log(`[CShapesAtlasJoin] Processing ${ts_keys.length} discrete historical timestamps...`);

      //2. Iterate through all timestamps
      for (let t_idx = 0; t_idx < ts_keys.length; t_idx++) {
        let ts = ts_keys[t_idx];
        let date = (Date.convertTimestampToDate) ? Date.convertTimestampToDate(ts) : null;
        let year = (date) ? date.year : Math.round(ts / 8766);
        let spatial_index = null;

        if (year >= 1816) {
          spatial_index = this.buildSpatialIndex(sources.atlas_data, ts);
        }

        //Epoch A: Pre-1816 (Keep original simplified entities unmodified)
        if (year < 1816) {
          for (let id of entity_meta_map.keys()) {
            let orig = sources.simp_data[id];
            if (orig && orig.history && orig.history[String(ts)]) {
              entity_history_map.get(id)[String(ts)] = orig.history[String(ts)];
              let kf = orig.history[String(ts)];
              if (kf && kf[0] !== null) {
                let geom = kf[0].feature ? kf[0].feature.geometry : null;
                let prev_st = entity_state_tracker.get(id);
                entity_state_tracker.set(id, {
                  is_active: true,
                  last_geom: geom,
                  last_geom_sig: this.computeGeomSignature(geom),
                  last_props: Object.assign({}, prev_st ? prev_st.last_props : {}, kf[2] || {}),
                  last_symbol: Object.assign({}, prev_st ? prev_st.last_symbol : {}, kf[1] || {})
                });
              } else if (kf && kf[0] === null) {
                entity_state_tracker.set(id, { is_active: false, last_geom: null, last_geom_sig: null });
              }
            }
          }
        } else if (year >= 1816 && year <= 1886) {
          //Epoch B: 1816-1886 (Spatiotemporally merge CShapes-Europe + preserve non-European territory)
          active_eu = sources.eu_geo.features.filter((f) => f.properties.From <= year && f.properties.To >= year);
          let eu_bboxes = active_eu.map((f) => turf.bbox(f));

          //B1. Index CShapes-Europe features by country name and ID
          eu_by_polity = new Map();
          for (let i = 0; i < active_eu.length; i++) {
            let feat = active_eu[i];
            let p = feat.properties;
            let meta = sources.eu_meta.get(String(p.Id)) || sources.eu_meta.get(p.Id + "|" + p.Name) || sources.eu_meta.get(p.Name.toLowerCase()) || {
              cow: p.Id, cow_code: p.Id, name: p.Name, seshat_id: `(${p.Name})`
            };

            let key = String(p.Id);
            let polity_name = p.Name;
            let seshat_id = this.getCanonicalSeshatId(p.Id, year, meta.seshat_id || `(${p.Name})`);

            //Handle Prussia (pre-1871) vs Germany (1871+)
            if (p.Id === 255) {
              if (year < 1871) {
                polity_name = "Prussia";
                seshat_id = "de_hohenzollern_2";
              } else {
                polity_name = "Germany";
                seshat_id = this.getCanonicalSeshatId(255, year, "de_hohenzollern_3");
              }
            } else if (p.Id === 220) {
              polity_name = "French Republic";
            } else if (p.Id === 325) {
              polity_name = "Italy";
            } else if (p.Id === 360) {
              polity_name = "Romania";
            }

            if (!eu_by_polity.has(key)) {
              eu_by_polity.set(key, {
                features: [],
                meta: Object.assign({}, meta, { cow: p.Id, cow_code: p.Id, name: polity_name, seshat_id: seshat_id }),
                name: polity_name
              });
            }
            eu_by_polity.get(key).features.push(feat);
          }

          //B2. Process base polities: identify transcontinental empires, preserve non-European polities
          let active_outside_eu_ids = new Set();
          for (let id of entity_meta_map.keys()) {
            let ent = sources.simp_data[id];
            if (!ent || !ent.history) continue;

            let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(ent, ts);
            if (!st || !st.geometry) {
              this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
              continue;
            }

            let name = (st.properties && st.properties.name) || "";
            let is_russia = (id === "10264500703" || name.includes("Russian Empire"));
            let is_ottoman = (id === "52816277001" || id === "52817277008" || name.includes("Ottoman Empire"));
            let is_uk = (id === "87693477140" || id === "87692477137");
            let is_france = (id === "82079236664" || id === "64690686363" || id === "11726742237");

            let trans_code = null;
            if (is_ottoman) trans_code = "640";
            else if (is_russia) trans_code = "365";
            else if (is_uk) trans_code = "200";
            else if (is_france) trans_code = "220";
            else if (id === "98053051772" || name === "Spanish Empire" || name === "Kingdom of Spain") trans_code = "230";
            else if (id === "93731444700" || name === "Kingdom of Portugal" || name === "Portugal") trans_code = "235";
            else if (id === "86136600825" || id === "45749774697" || name === "Netherlands") trans_code = "210";
            else if (id === "58904326755" || id === "65372656937" || name === "Denmark" || name === "Denmark-Norway") trans_code = "390";
            else if (id === "43745445780" || id === "92931798598" || name.includes("Tunis")) trans_code = "616";

            if (trans_code) {
              let eu_grp = eu_by_polity.get(trans_code);
              if (eu_grp && eu_grp.features.length > 0) {
                let f_atlas = turf.feature(st.geometry);
                try {
                  let feats_to_union = [f_atlas];
                  if (eu_grp.combined_geom) {
                    feats_to_union.push(turf.feature(eu_grp.combined_geom));
                  } else {
                    feats_to_union = feats_to_union.concat(eu_grp.features);
                  }
                  let un = turf.union(turf.featureCollection(feats_to_union));
                  if (un && un.geometry) {
                    let un_bb = turf.bbox(un);
                    for (let f = 0; f < active_eu.length; f++) {
                      let f_other = active_eu[f];
                      if (String(f_other.properties.Id) === trans_code) continue;
                      let b = eu_bboxes[f];
                      if (!(un_bb[2] < b[0] || un_bb[0] > b[2] || un_bb[3] < b[1] || un_bb[1] > b[3])) {
                        try {
                          let inter = turf.intersect(turf.featureCollection([un, f_other]));
                          if (inter && inter.geometry && (turf.area(inter) / 1e6) > 20) {
                            let diff = turf.difference(turf.featureCollection([un, f_other]));
                            if (diff && diff.geometry) un = diff;
                          }
                        } catch (e) {}
                      }
                    }
                    eu_grp.combined_geom = un.geometry;
                  }
                } catch (e) {}
              }

              //Base atlas_simplified polity merges UP into the CShapes-Europe transcontinental empire
              this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
              continue;
            } else {
              //Check if entity is located outside of Europe
              let feat = turf.feature(st.geometry);
              let in_eu = this.intersectsActiveEU(feat, active_eu, eu_bboxes);

              if (!in_eu) {
                //Polity is outside Europe (USA, Canada, Brazil, China, Khiva, Tunis, British Guiana, French Gabon, etc.)
                active_outside_eu_ids.add(id);
                let s_props = Object.assign({}, st.properties);
                let meta = sources.eu_meta.get(String(s_props.cow)) || sources.c2_meta.get(String(s_props.cow)) ||
                           sources.eu_meta.get((s_props.name || "").toLowerCase()) || sources.c2_meta.get((s_props.name || "").toLowerCase());
                if (meta && meta.cow) {
                  s_props.cow = meta.cow;
                  s_props.cow_code = meta.cow;
                }
                s_props.seshat_id = this.getCanonicalSeshatId(s_props.cow || (meta && meta.cow), year, s_props.seshat_id);
                if (entity_name_map.has(id)) s_props.name = entity_name_map.get(id);
                this.emitKeyframe(id, ts, st.geometry, st.symbol, s_props, entity_history_map, entity_state_tracker);
              } else {
                //Polity is inside Europe: superseded by CShapes-Europe; deactivate cleanly
                this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
              }
            }
          }

          //B3. Emit all CShapes-Europe polities
          let active_eu_target_ids = new Set();
          for (let code of eu_by_polity.keys()) {
            let grp = eu_by_polity.get(code);
            let target_id = (code === "255" && year < 1871)
              ? global.PolitiesAtlasJoin.hashToSnowflakeId("cshapes_255_prussia")
              : global.PolitiesAtlasJoin.hashToSnowflakeId("cshapes_" + code);
            active_eu_target_ids.add(target_id);

            this.emitCShapesPolity(target_id, ts, grp, spatial_index, entity_meta_map, entity_history_map, entity_state_tracker, entity_name_map);
          }

          //B4. Deactivate any previously active entities that are no longer active at this timestamp
          for (let [id, state] of entity_state_tracker.entries()) {
            if (state && state.is_active) {
              if (!active_eu_target_ids.has(id) && !active_outside_eu_ids.has(id)) {
                this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
              }
            }
          }
        } else {
          //Epoch C: Post-1886 (Replace the entire timeframe with CShapes-2.0.geojson)
          let curr_date_num = (date) ? (date.year * 10000 + (date.month || 1) * 100 + (date.day || 1)) : (year * 10000 + 101);
          active_c2 = sources.c2_geo.features.filter((f) => {
            let p = f.properties;
            let s = p.gwsyear * 10000 + p.gwsmonth * 100 + p.gwsday;
            let e = p.gweyear * 10000 + p.gwemonth * 100 + p.gweday;
            return curr_date_num >= s && curr_date_num <= e;
          });

          //C1. Group active CShapes-2.0 features by country
          c2_by_polity = new Map();
          for (let i = 0; i < active_c2.length; i++) {
            let feat = active_c2[i];
            let p = feat.properties;
            let meta = sources.c2_meta.get(String(p.gwcode)) || sources.c2_meta.get(p.gwcode + "|" + p.cntry_name) || sources.c2_meta.get(p.cntry_name.toLowerCase()) || {
              cow: p.gwcode, cow_code: p.gwcode, name: p.cntry_name, seshat_id: `(${p.cntry_name})`
            };

            let s_key = meta.seshat_id;
            let polity_name = p.cntry_name;
            let cow_code = p.gwcode;

            //Special historical grouping for Burma and British Raj
            if (p.cntry_name.includes("Burma") || p.cntry_name.includes("Myanmar")) {
              cow_code = 775;
              polity_name = "Burma";
              s_key = "(Burma)";
            } else if (p.cntry_name === "India" && year < 1947) {
              cow_code = 750;
              polity_name = "British Raj";
              s_key = "(British Raj)";
            } else if (p.gwcode === 255) {
              polity_name = "Germany";
            } else if (p.gwcode === 220) {
              polity_name = "French Republic";
            } else if (p.gwcode === 325) {
              polity_name = "Italy";
            } else if (p.gwcode === 360) {
              polity_name = "Romania";
            } else if (p.gwcode === 710) {
              polity_name = "China";
            }

            let seshat_id = (s_key === "(Burma)" || s_key === "(British Raj)")
              ? s_key
              : this.getCanonicalSeshatId(cow_code, year, s_key);
            meta = Object.assign({}, meta, { cow: cow_code, cow_code: cow_code, name: polity_name, seshat_id: seshat_id });

            let code_key = (s_key === "(Burma)" || s_key === "(British Raj)") ? s_key : String(cow_code);
            if (!c2_by_polity.has(code_key)) {
              c2_by_polity.set(code_key, {
                cow_code: cow_code,
                features: [],
                meta: meta,
                name: polity_name
              });
            }
            c2_by_polity.get(code_key).features.push(feat);
          }

          let c2_active_ids = new Set();

          //C2. Emit CShapes-2.0 polities with CShapes names taking precedence
          for (let code_key of c2_by_polity.keys()) {
            let grp = c2_by_polity.get(code_key);
            let target_id = (code_key === "(Burma)")
              ? "79315678680"
              : ((code_key === "(British Raj)")
                ? "562205920"
                : global.PolitiesAtlasJoin.hashToSnowflakeId("cshapes_" + code_key));
            c2_active_ids.add(target_id);

            this.emitCShapesPolity(target_id, ts, grp, spatial_index, entity_meta_map, entity_history_map, entity_state_tracker, entity_name_map);
          }

          //C2b. Special case: Burma prior to 1937 in Epoch C (when CShapes-2.0 has not yet started tracking Burma)
          if (year < 1937) {
            let burma_id = "79315678680";
            let burma_ent = sources.simp_data[burma_id];
            if (burma_ent && burma_ent.history) {
              let st = global.PolitiesAtlasJoin.getEntityStateAtTimestamp(burma_ent, ts);
              if (st && st.geometry) {
                c2_active_ids.add(burma_id);
                let s_props = Object.assign({}, st.properties, { name: "Burma", seshat_id: "(Burma)" });
                this.emitKeyframe(burma_id, ts, st.geometry, st.symbol, s_props, entity_history_map, entity_state_tracker);
              }
            }
          }

          //C3. Deactivate ALL pre-1887 entities (including all CShapes-Europe entities) so 0 linger after 1886
          for (let [id, state] of entity_state_tracker.entries()) {
            if (state && state.is_active && !c2_active_ids.has(id)) {
              this.deactivateEntity(id, ts, entity_history_map, entity_state_tracker);
            }
          }
        }

        if (Date.now() - last_log > 5000 || t_idx === ts_keys.length - 1) {
          let pct = Math.round(((t_idx + 1) / ts_keys.length) * 100);
          console.log(`[CShapesAtlasJoin] Progress: ${pct}% (TS ${t_idx + 1}/${ts_keys.length}, Year ${year})`);
          last_log = Date.now();
        }
      }

      //3. Reassemble finalized savefile
      console.log(`[CShapesAtlasJoin] Assembling finalized atlas_simplified.naissance savefile...`);
      let final_savefile = {};
      if (sources.simp_data.map_settings) final_savefile.map_settings = sources.simp_data.map_settings;

      //Preserve FeatureGroups and settings
      for (let k in sources.simp_data) {
        let orig = sources.simp_data[k];
        if (orig.class_name !== "GeometryPolygon" && k !== "map_settings") {
          final_savefile[k] = orig;
        }
      }

      //Attach all GeometryPolygons
      for (let id of entity_meta_map.keys()) {
        let hist = entity_history_map.get(id);
        if (hist && Object.keys(hist).length > 0) {
          let ent_meta = entity_meta_map.get(id);
          final_savefile[id] = {
            class_name: "GeometryPolygon",
            history: hist,
            id: id,
            metadata: ent_meta.metadata || { description: "Simplified Polity", tags: ["Polities"] },
            type: "geometry"
          };
        }
      }

      console.log(`[CShapesAtlasJoin] Writing output to ${this.out_atlas_path}...`);
      out_stream = fs.createWriteStream(this.out_atlas_path, { encoding: "utf8" });
      out_stream.write("{\n");
      let all_keys = Object.keys(final_savefile);
      for (let i = 0; i < all_keys.length; i++) {
        let k = all_keys[i];
        let val_str = JSON.stringify(final_savefile[k]);
        let comma = (i < all_keys.length - 1) ? "," : "";
        out_stream.write(`  ${JSON.stringify(k)}: ${val_str}${comma}\n`);
      }
      out_stream.write("}\n");
      out_stream.end();

      await new Promise((resolve) => out_stream.on("finish", resolve));
      let stat = fs.statSync(this.out_atlas_path);
      console.log(`[CShapesAtlasJoin] Finished successfully! Written ${(stat.size / 1024 / 1024).toFixed(2)} MB to ${this.out_atlas_path}`);
    }
  };

  //Auto-execute if executed directly via Node CLI
  if (typeof require !== "undefined" && typeof module !== "undefined" && require.main === module) {
    global.CShapesAtlasJoin.run()
      .then(() => process.exit(0))
      .catch((err) => {
        console.error("[CShapesAtlasJoin] Fatal execution error:", err);
        process.exit(1);
      });
  }
})();
